import logging
#from src.engine.orderbook.orderbook import OrderBook
from src.engine.orderbook.sl_orderbook import OrderBook
from src.engine.types.types import (
    Order,
    OrderTimeInForce,
    OrderType, OrderSide, OrderStatus, new_trade, empty_order
)
from src.common.mmq import FUNDING_MATCH_MQ, MATCH_FUNDING_MQ, MMQTopic
from typing import List, Dict
import asyncio
import threading
import time
import json

logger = logging.getLogger(__name__)

class MatchingEngine:
    def __init__(self):
        self.order_books = {}
        self.lock = threading.RLock()
        # Store trades by symbol
        self.trades = {}
        # WebSocket clients for trade updates
        self.ws_clients = []

        self.max_kline_size = 200
        self.klines = {}


    ### RPC interface
    def get_order_book(self, symbol) -> OrderBook:
        with self.lock:
            if symbol not in self.order_books:
                self.order_books[symbol] = OrderBook(symbol)
            return self.order_books[symbol]

    def process_order(self, order):
        trades = []
        order_book = self.get_order_book(order.symbol)
        
        # Process market order
        if order.type == OrderType.MARKET:
            trades = self._process_market_order(order_book, order)
        # Process limit order
        else:
            trades = self._process_limit_order(order_book, order)

        # Store trades and notify WebSocket clients
        if trades:
            self._store_trades(order.symbol, trades)
        
        return trades

    def _process_limit_order(self, order_book, order):
        trades = []

        if order.side == OrderSide.BUY:
            # Buy order matches sell orders
            while True:
                best_ask = order_book.get_best_ask()
                if not best_ask or best_ask.price > order.price:
                    break

                # Calculate match quantity
                match_quantity = order.quantity - order.filled_quantity
                if match_quantity > best_ask.quantity - best_ask.filled_quantity:
                    match_quantity = best_ask.quantity - best_ask.filled_quantity

                # Generate trade
                trade = new_trade(
                    taker_uid=order.uid,
                    maker_uid=best_ask.uid,
                    symbol=order.symbol,
                    price=best_ask.price,
                    quantity=match_quantity,
                    buy_order_id=order.order_id,
                    sell_order_id=best_ask.order_id
                )
                trades.append(trade)
                self.update_klines(order.symbol, best_ask.price, match_quantity)
                
                # Update order filled quantity
                order.filled_quantity += match_quantity
                best_ask.filled_quantity += match_quantity

                # Check if sell order is fully filled
                if best_ask.filled_quantity >= best_ask.quantity:
                    best_ask.status = OrderStatus.FILLED
                    order_book.remove_order(best_ask.order_id)
                else:
                    best_ask.status = OrderStatus.PARTIALLY_FILLED

                # Check if buy order is fully filled
                if order.filled_quantity >= order.quantity:
                    order.status = OrderStatus.FILLED
                    break

            # If order is not fully filled, add to order book
            if order.status != OrderStatus.FILLED:
                if order.filled_quantity > 0:
                    order.status = OrderStatus.PARTIALLY_FILLED
                else:
                    order.status = OrderStatus.NEW
                order_book.add_order(order)

        else:  # OrderSide.SELL
            # Sell order matches buy orders
            while True:
                best_bid = order_book.get_best_bid()
                if not best_bid or best_bid.price < order.price:
                    break

                # Calculate match quantity
                match_quantity = order.quantity - order.filled_quantity
                if match_quantity > best_bid.quantity - best_bid.filled_quantity:
                    match_quantity = best_bid.quantity - best_bid.filled_quantity

                # Generate trade
                trade = new_trade(
                    taker_uid=order.uid,
                    maker_uid=best_bid.uid,
                    symbol=order.symbol,
                    price=best_bid.price,
                    quantity=match_quantity,
                    buy_order_id=best_bid.order_id,
                    sell_order_id=order.order_id
                )
                trades.append(trade)
                self.update_klines(order.symbol, best_bid.price, match_quantity)

                # Update order filled quantity
                order.filled_quantity += match_quantity
                best_bid.filled_quantity += match_quantity

                # Check if buy order is fully filled
                if best_bid.filled_quantity >= best_bid.quantity:
                    best_bid.status = OrderStatus.FILLED
                    order_book.remove_order(best_bid.uid, best_bid.order_id)
                else:
                    best_bid.status = OrderStatus.PARTIALLY_FILLED

                # Check if sell order is fully filled
                if order.filled_quantity >= order.quantity:
                    order.status = OrderStatus.FILLED
                    break

            # If order is not fully filled, add to order book
            if order.status != OrderStatus.FILLED:
                if order.filled_quantity > 0:
                    order.status = OrderStatus.PARTIALLY_FILLED
                else:
                    order.status = OrderStatus.NEW
                order_book.add_order(order)

        return trades

    def _process_market_order(self, order_book, order):
        trades = []

        if order.side == OrderSide.BUY:
            # Market buy order matches all sell orders
            while order.filled_quantity < order.quantity:
                best_ask = order_book.get_best_ask()
                if not best_ask:
                    break

                # Calculate match quantity
                match_quantity = order.quantity - order.filled_quantity
                if match_quantity > best_ask.quantity - best_ask.filled_quantity:
                    match_quantity = best_ask.quantity - best_ask.filled_quantity

                # Generate trade
                trade = new_trade(
                    taker_uid=order.uid,
                    maker_uid=best_ask.uid,
                    symbol=order.symbol,
                    price=best_ask.price,
                    quantity=match_quantity,
                    buy_order_id=order.order_id,
                    sell_order_id=best_ask.order_id
                )
                trades.append(trade)
                self.update_klines(order.symbol, best_ask.price, match_quantity)

                # Update order filled quantity
                order.filled_quantity += match_quantity
                best_ask.filled_quantity += match_quantity

                # Check if sell order is fully filled
                if best_ask.filled_quantity >= best_ask.quantity:
                    best_ask.status = OrderStatus.FILLED
                    order_book.remove_order(best_ask.uid, best_ask.order_id)
                else:
                    best_ask.status = OrderStatus.PARTIALLY_FILLED

        else:  # OrderSide.SELL
            # Market sell order matches all buy orders
            while order.filled_quantity < order.quantity:
                best_bid = order_book.get_best_bid()
                if not best_bid:
                    break

                # Calculate match quantity
                match_quantity = order.quantity - order.filled_quantity
                if match_quantity > best_bid.quantity - best_bid.filled_quantity:
                    match_quantity = best_bid.quantity - best_bid.filled_quantity

                # Generate trade
                trade = new_trade(
                    taker_uid=order.uid,
                    maker_uid=best_bid.uid,
                    symbol=order.symbol,
                    price=best_bid.price,
                    quantity=match_quantity,
                    buy_order_id=best_bid.order_id,
                    sell_order_id=order.order_id
                )
                trades.append(trade)
                self.update_klines(order.symbol, best_bid.price, match_quantity)
                
                # Update order filled quantity
                order.filled_quantity += match_quantity
                best_bid.filled_quantity += match_quantity

                # Check if buy order is fully filled
                if best_bid.filled_quantity >= best_bid.quantity:
                    best_bid.status = OrderStatus.FILLED
                    order_book.remove_order(best_bid.uid, best_bid.order_id)
                else:
                    best_bid.status = OrderStatus.PARTIALLY_FILLED

        # Market orders are marked as filled regardless of whether they are fully executed
        if order.filled_quantity > 0:
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIALLY_FILLED

        return trades

    def cancel_order(self, uid, symbol, order_id):
        """ RPC interface
            cancel single order
        """
        order_book = self.get_order_book(symbol)
        order = order_book.remove_order(uid, order_id)
        if order and order.uid == uid:
            order.status = OrderStatus.CANCELLED
        else:
            # If the order doesn't exist, return an empty order with canceled status
            order = empty_order(uid, order_id, symbol)
        return order

    def get_order(self, uid, symbol, order_id):
        """ RPC interface
            get single order
        """
        order_book = self.get_order_book(symbol)
        return order_book.get_order(uid, order_id)

    def get_order_book_data(self, symbol, depth=30):
        order_book = self.get_order_book(symbol)
        return order_book.get_order_book(depth)

    def create_order(self, uid, symbol, side, order_type, time_in_force, quantity, price=None, client_order_id=None, is_futures=False):
        """ RPC interface
        """
        logger.debug(f"create_order called with: symbol={symbol}, side={side}, order_type={order_type}, quantity={quantity}, price={price}, client_order_id={client_order_id}, is_futures={is_futures}")
        try:
            logger.debug(f"About to create Order with order_type={order_type}")
            order = Order(uid, symbol, side, order_type, time_in_force, quantity, price, client_order_id, is_futures)
            logger.debug(f"Order created successfully: {order.order_id} - {order.client_order_id}")
        except Exception as e:
            import traceback
            logger.debug(f"Error creating order: {e}")
            traceback.print_exc()
            raise

        trades = self.process_order(order)
        return trades, order

    def create_orders(self, uid, params, is_futures=False):
        """ RPC interface
            batch create orders, discard market orders and IOC/FOK orders
        """
        logger.debug(f"Creating orders with params: {params}")
        buy_orders = [Order(uid,
                symbol=param.get('symbol'),
                client_order_id=param.get('client_order_id') or str(int(time.time() * 1000)),
                side=param.get('side'),
                order_type=param.get('type'),
                time_in_force=param.get('time_in_force'),
                quantity=float(param.get('quantity')),
                price=float(param.get('price')) if param.get('price') else 0,
                is_futures=is_futures
            ) for param in params if param.get('side') == OrderSide.BUY and param.get('type') == OrderType.LIMIT and param.get('time_in_force') != OrderTimeInForce.IOC and param.get('time_in_force') != OrderTimeInForce.FOK]
        buy_orders.sort(key=lambda x: x.price, reverse=True)

        sell_orders = [Order(uid,
                symbol=param.get('symbol'),
                client_order_id=param.get('client_order_id') or str(int(time.time() * 1000)),
                side=param.get('side'),
                order_type=param.get('type'),
                time_in_force=param.get('time_in_force'),
                quantity=float(param.get('quantity')),
                price=float(param.get('price')) if param.get('price') else 0,
                is_futures=is_futures
            ) for param in params if param.get('side') == OrderSide.SELL and param.get('type') == OrderType.LIMIT and param.get('time_in_force') != OrderTimeInForce.IOC and param.get('time_in_force') != OrderTimeInForce.FOK]
        sell_orders.sort(key=lambda x: x.price)
 
        order_book = self.get_order_book(buy_orders[0].symbol if buy_orders else sell_orders[0].symbol)

        total_trades = []
        for idx, order in enumerate(sell_orders):
            # Batch orders, simplified matching process
            best_bid = order_book.get_best_bid()
            if best_bid and best_bid.price >= order.price:
                if order.time_in_force == OrderTimeInForce.GTC and order.is_selftrade:
                    trades = self.process_order(order)
                    total_trades.extend(trades)
                continue

            order_book.batch_add_orders(OrderSide.SELL, sell_orders[idx:])
            break

        for idx, order in enumerate(buy_orders):
            # Batch orders, simplified matching process
            best_ask = order_book.get_best_ask()
            if best_ask and best_ask.price <= order.price:
                if order.time_in_force == OrderTimeInForce.GTC and order.is_selftrade:
                    trades = self.process_order(order)
                    total_trades.extend(trades)
                continue

            order_book.batch_add_orders(OrderSide.BUY, buy_orders[idx:])
            break

        return total_trades, buy_orders + sell_orders

    def cancel_orders(self, uid, symbol, order_ids):
        # Simplified implementation, should find the corresponding order book based on order_id in practice
        order_book = self.get_order_book(symbol)
        return order_book.batch_remove_orders(uid, order_ids)

    def get_open_orders(self, uid, symbol=None):
        order_book = self.get_order_book(symbol)
        return order_book.pending_orders(uid)

    def _store_trades(self, symbol, trades):
        with self.lock:
            if symbol not in self.trades:
                self.trades[symbol] = []
            # Store last 1000 trades per symbol
            self.trades[symbol].extend(trades)
            if len(self.trades[symbol]) > 1000:
                self.trades[symbol] = self.trades[symbol][-1000:]

    def get_trades(self, symbol, limit=50):
        with self.lock:
            if symbol not in self.trades:
                return []
            return self.trades[symbol][-limit:]

    def append_trade(self, uid, symbol, price, quantity):
        if symbol not in self.trades:
            self.trades[symbol] = []
        trade = new_trade(
            uid,
            uid,
            symbol,
            price,
            quantity,
            int(time.time() * 1000),
            int(time.time() * 1000)
        )
        with self.lock:
            self.trades[symbol].append(trade)

    def update_klines(self, symbol, price, quantity):
        # Update klines for the given symbol with the latest trade price and quantity
        if symbol not in self.klines:
            self.klines[symbol] = {
                '1m': [],
                '1h': [],
                '1d': [],
                'prev_update_minute': 0,
                'prev_update_hour': 0,
                'prev_update_day': 0,
            }

        klines = self.klines[symbol]
        minute = time.time() // 60
        logger.debug(f"Updating klines for {symbol} at minute={minute}, prev_update_minute={klines['prev_update_minute']}")
        logger.debug(f"previous klines: {klines['1m']}")
        if klines['prev_update_minute'] != minute:
            ts = int(time.time() * 1000)
            klines['1m'].append([
                ts,      # Open time
                price,        # Open price
                price,        # High price
                price,        # Low price
                price,        # Close price
                quantity,      # Volume
                ts + 60 * 1000,        # Close time
                quantity * price # Quote asset volume
            ])

            if len(klines['1m']) > self.max_kline_size * 2:
                klines['1m'] = klines['1m'][-self.max_kline_size:]
        else:
            # update latest bar
            latest_bar = klines['1m'][-1]
            latest_bar[2] = max(price, latest_bar[2])  # High price
            latest_bar[3] = min(price, latest_bar[3])  # Low price
            latest_bar[4] = price  # Close price
            latest_bar[5] += quantity  # Volume
            latest_bar[7] += quantity * price  # Quote asset volume
        logger.debug(f"updated klines: {klines['1m']}")

        hour = minute // 60
        logger.debug(f"Updating klines for {symbol} at hour={hour}, prev_update_hour={klines['prev_update_hour']}")
        if klines['prev_update_hour'] == hour:
            # update latest bar
            latest_bar = klines['1h'][-1]
            latest_bar[2] = max(price, latest_bar[2])  # High price
            latest_bar[3] = min(price, latest_bar[3])  # Low price
            latest_bar[4] = price  # Close price
            latest_bar[5] += quantity  # Volume
            latest_bar[7] += quantity * price  # Quote asset volume
        else:
            ts = int(time.time() * 1000)
            klines['1h'].append([
                ts,           # Open time
                price,        # Open price
                price,        # High price
                price,        # Low price
                price,        # Close price
                quantity,     # Volume
                ts + 3600 * 1000,        # Close time
                quantity * price # Quote asset volume
            ])

            if len(klines['1h']) > self.max_kline_size * 1.5:
                klines['1h'] = klines['1h'][-self.max_kline_size:]


        day = hour // 24
        logger.debug(f"Updating klines for {symbol} at day={day}, prev_update_day={klines['prev_update_day']}")
        if klines['prev_update_day'] == day:
            # update latest bar
            latest_bar = klines['1d'][-1]
            latest_bar[2] = max(price, latest_bar[2])  # High price
            latest_bar[3] = min(price, latest_bar[3])  # Low price
            latest_bar[4] = price  # Close price
            latest_bar[5] += quantity  # Volume
            latest_bar[7] += quantity * price  # Quote asset volume
        else:
            ts = int(time.time() * 1000)
            klines['1d'].append([
                ts,      # Open time
                price,        # Open price
                price,        # High price
                price,        # Low price
                price,        # Close price
                quantity,      # Volume
                ts + 24 * 3600 * 1000,        # Close time
                quantity * price # Quote asset volume
            ])

            if len(klines['1d']) > self.max_kline_size * 1.2:
                klines['1d'] = klines['1d'][-self.max_kline_size:]
        
        klines['prev_update_minute'] = minute
        klines['prev_update_hour'] = hour
        klines['prev_update_day'] = day

    def get_klines(self, symbol, interval, limit=50):
        with self.lock:
            if symbol not in self.klines:
                return []
            return self.klines[symbol][interval][-limit:]



    ### MMQ interface
    def on_order(self, order: Order):
        """ MQ interface
            process single order
        """
        logger.debug(f"on_order called with: {order.to_dict()}")
        trades = self.process_order(order)
        MATCH_FUNDING_MQ.produce(MMQTopic.SPOT_MATCH_OUT, json.dumps({'trades': [tr.to_dict() for tr in trades], 'order': order.to_dict()}))

    def on_orders(self, orders: List[Order]):
        """ MQ interface
            batch create orders, discard market orders and IOC/FOK orders
        """
        logger.debug(f"on_orders called with: {orders}")
        buy_orders = [order for order in orders if order.side == OrderSide.BUY]
        buy_orders.sort(key=lambda x: x.price, reverse=True)

        sell_orders = [order for order in orders if order.side == OrderSide.SELL]
        sell_orders.sort(key=lambda x: x.price)
 
        order_book = self.get_order_book(buy_orders[0].symbol if buy_orders else sell_orders[0].symbol)

        total_trades = []
        for idx, order in enumerate(sell_orders):
            # Batch orders, simplified matching process
            best_bid = order_book.get_best_bid()
            if best_bid and best_bid.price >= order.price:
                if order.time_in_force == OrderTimeInForce.GTC and order.is_selftrade:
                    trades = self.process_order(order)
                    total_trades.extend(trades)
                continue

            order_book.batch_add_orders(OrderSide.SELL, sell_orders[idx:])
            break

        for idx, order in enumerate(buy_orders):
            # Batch orders, simplified matching process
            best_ask = order_book.get_best_ask()
            if best_ask and best_ask.price <= order.price:
                if order.time_in_force == OrderTimeInForce.GTC and order.is_selftrade:
                    trades = self.process_order(order)
                    total_trades.extend(trades)
                continue

            order_book.batch_add_orders(OrderSide.BUY, buy_orders[idx:])
            break

        MATCH_FUNDING_MQ.produce(MMQTopic.SPOT_MATCH_OUT, json.dumps({'trades': [tr.to_dict() for tr in total_trades], 'orders': [order.to_dict() for order in buy_orders + sell_orders]}))

    def on_cancel_orders(self, data: Dict):
        """ MQ interface
            batch cancel orders
        """
        uid = data['uid']
        symbol = data['symbol']
        order_ids = data['order_ids']
        order_book = self.get_order_book(symbol)
        removed_ids = order_book.batch_remove_orders(uid, order_ids)
        MATCH_FUNDING_MQ.produce(MMQTopic.SPOT_MATCH_OUT, json.dumps({'removed_orders': [order_book.get_order(uid, order_id) for order_id in removed_ids]}))

    async def run_forever(self, topics: List[MMQTopic]):
        """ Get messages from the MMQ and process them
        """
        prev_topic_offsets = {
            topic: 0 for topic in topics
        }
        while True:
            has_message = False
            for topic in topics:
                prev_offset = prev_topic_offsets[topic]
                queue_offset, message = FUNDING_MATCH_MQ.consume(topic, prev_offset)
                logger.debug(f"Consumed message from {topic} offset={queue_offset}: {message}")
                if message:
                    prev_topic_offsets[topic] = queue_offset + 1
                    data = json.loads(message)
                    if type(data) is list:
                        self.on_orders([Order.from_dict(order) for order in data])
                    else:
                        self.on_order(Order.from_dict(data))
                    has_message = True

            if has_message:
                await asyncio.sleep(0.05)
            else:
                await asyncio.sleep(0.1)

# Global trading engine instance
global_spot_engine = MatchingEngine()
global_futures_engine = MatchingEngine()
