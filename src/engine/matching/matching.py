from src.engine.orderbook.orderbook import OrderBook
from src.engine.types.types import (
    Order,
    OrderType, OrderSide, OrderStatus, new_trade, empty_order
)
import threading
import traceback
import time

class MatchingEngine:
    def __init__(self):
        self.order_books = {}
        self.lock = threading.RLock()
        # Store trades by symbol
        self.trades = {}
        # WebSocket clients for trade updates
        self.ws_clients = []

        self.prev_kline_update_minute = 0
        self.prev_kline_update_hour = 0
        self.prev_kline_update_day = 0
        self.max_kline_size = 200
        self.klines = {}
    
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
            self._notify_ws_clients(order.symbol, trades)
        
        return trades
    
    def _process_limit_order(self, order_book, order):
        trades = []
        
        if order.side == OrderSide.BUY:
            # Buy order matches sell orders
            while True:
                best_ask = order_book.asks.peek()
                if not best_ask or best_ask.price > order.price:
                    break
                
                # Calculate match quantity
                match_quantity = order.quantity - order.filled_quantity
                if match_quantity > best_ask.quantity - best_ask.filled_quantity:
                    match_quantity = best_ask.quantity - best_ask.filled_quantity
                
                # Generate trade
                trade = new_trade(
                    order.symbol,
                    best_ask.price,
                    match_quantity,
                    order.order_id,
                    best_ask.order_id
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
                best_bid = order_book.bids.peek()
                if not best_bid or best_bid.price < order.price:
                    break
                
                # Calculate match quantity
                match_quantity = order.quantity - order.filled_quantity
                if match_quantity > best_bid.quantity - best_bid.filled_quantity:
                    match_quantity = best_bid.quantity - best_bid.filled_quantity
                
                # Generate trade
                trade = new_trade(
                    order.symbol,
                    best_bid.price,
                    match_quantity,
                    best_bid.order_id,
                    order.order_id
                )
                trades.append(trade)
                self.update_klines(order.symbol, best_bid.price, match_quantity)

                # Update order filled quantity
                order.filled_quantity += match_quantity
                best_bid.filled_quantity += match_quantity
                
                # Check if buy order is fully filled
                if best_bid.filled_quantity >= best_bid.quantity:
                    best_bid.status = OrderStatus.FILLED
                    order_book.remove_order(best_bid.order_id)
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
                best_ask = order_book.asks.peek()
                if not best_ask:
                    break
                
                # Calculate match quantity
                match_quantity = order.quantity - order.filled_quantity
                if match_quantity > best_ask.quantity - best_ask.filled_quantity:
                    match_quantity = best_ask.quantity - best_ask.filled_quantity
                
                # Generate trade
                trade = new_trade(
                    order.symbol,
                    best_ask.price,
                    match_quantity,
                    order.order_id,
                    best_ask.order_id
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
        
        else:  # OrderSide.SELL
            # Market sell order matches all buy orders
            while order.filled_quantity < order.quantity:
                best_bid = order_book.bids.peek()
                if not best_bid:
                    break
                
                # Calculate match quantity
                match_quantity = order.quantity - order.filled_quantity
                if match_quantity > best_bid.quantity - best_bid.filled_quantity:
                    match_quantity = best_bid.quantity - best_bid.filled_quantity
                
                # Generate trade
                trade = new_trade(
                    order.symbol,
                    best_bid.price,
                    match_quantity,
                    best_bid.order_id,
                    order.order_id
                )
                trades.append(trade)
                self.update_klines(order.symbol, best_bid.price, match_quantity)
                
                # Update order filled quantity
                order.filled_quantity += match_quantity
                best_bid.filled_quantity += match_quantity
                
                # Check if buy order is fully filled
                if best_bid.filled_quantity >= best_bid.quantity:
                    best_bid.status = OrderStatus.FILLED
                    order_book.remove_order(best_bid.order_id)
                else:
                    best_bid.status = OrderStatus.PARTIALLY_FILLED
        
        # Market orders are marked as filled regardless of whether they are fully executed
        if order.filled_quantity > 0:
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIALLY_FILLED
        
        return trades
    
    def cancel_order(self, symbol, order_id):
        order_book = self.get_order_book(symbol)
        order = order_book.remove_order(order_id)
        if order:
            order.status = OrderStatus.CANCELED
        else:
            # If the order doesn't exist, return an empty order with canceled status
            order = empty_order(order_id, symbol)
        return order
    
    def get_order_book_data(self, symbol, depth=30):
        order_book = self.get_order_book(symbol)
        return order_book.get_order_book(depth)
    
    def create_order(self, symbol, side, order_type, quantity, price=None, client_order_id=None, is_futures=False):        
        print(f"create_order called with: symbol={symbol}, side={side}, order_type={order_type}, quantity={quantity}, price={price}, client_order_id={client_order_id}, is_futures={is_futures}")
        try:
            print(f"About to create Order with order_type={order_type}")
            # Let's try calling with positional arguments instead
            order = Order(symbol, side, order_type, quantity, price, client_order_id, is_futures)
            print(f"Order created successfully: {order.order_id}")
        except Exception as e:
            print(f"Error creating order: {e}")
            traceback.print_exc()
            raise
        
        trades = self.process_order(order)
        return trades, order
        
    def create_orders(self, params, is_futures=False):
        # batch create orders
        print(f"Creating orders with params: {params}")
        buy_orders = [Order(
                symbol=param.get('symbol'),
                side=param.get('side'),
                order_type=param.get('type'),
                quantity=param.get('quantity'),
                price=param.get('price'),
                is_futures=is_futures
            ) for param in params if param.get('side') == OrderSide.BUY]
        buy_orders.sort(key=lambda x: x.price, reverse=True)

        sell_orders = [Order(
                symbol=param.get('symbol'),
                side=param.get('side'),
                order_type=param.get('type'),
                quantity=param.get('quantity'),
                price=param.get('price'),
                is_futures=is_futures
            ) for param in params if param.get('side') == OrderSide.SELL]
        sell_orders.sort(key=lambda x: x.price)
        
        order_book = self.get_order_book(buy_orders[0].symbol if buy_orders else sell_orders[0].symbol)
        
        total_trades = []
        skip_match = False 
        for order in buy_orders:
            # Batch orders, simplified matching process
            if skip_match:
                order.status = OrderStatus.NEW
                order_book.add_order(order)
            else:
                trades = self.process_order(order)
                total_trades.extend(trades)
            
            if order.status != OrderStatus.FILLED:
                skip_match = True
        
        skip_match = False 
        for order in sell_orders:
            # Batch orders, simplified matching process
            if skip_match:
                order.status = OrderStatus.NEW
                order_book.add_order(order)
            else:
                trades = self.process_order(order)
                total_trades.extend(trades)
            
            if order.status != OrderStatus.FILLED:
                skip_match = True

        return total_trades, buy_orders + sell_orders

    def cancel_orders(self, symbol, order_ids):
        # Simplified implementation, should find the corresponding order book based on order_id in practice
        order_book = self.get_order_book(symbol)
        results = []
        for order_id in order_ids:
            order = order_book.remove_order(order_id)
            if order:
                order.status = OrderStatus.CANCELED
                results.append(order)
            else:
                results.append(empty_order(order_id, symbol))
        
        return results
    
    def get_open_orders(self, symbol=None):
        order_book = self.get_order_book(symbol)
        return order_book.asks.peek_order(10) + order_book.bids.peek_order(10)
    
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

    def update_klines(self, symbol, price, quantity):
        # Update klines for the given symbol with the latest trade price and quantity
        if symbol not in self.klines:
            self.klines[symbol] = {
                '1m': [],
                '1h': [],
                '1d': [],
            }
        
        klines = self.klines[symbol]
        minute = time.time() // 60
        if self.prev_kline_update_minute != minute:
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

        hour = minute // 60
        if self.prev_kline_update_hour == hour:
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
        if self.prev_kline_update_day == day:
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
        
        self.prev_kline_update_minute = minute
        self.prev_kline_update_hour = hour
        self.prev_kline_update_day = day

    def get_klines(self, symbol, interval, limit=50):
        with self.lock:
            if symbol not in self.klines:
                return []
            return self.klines[symbol][interval][-limit:]

# Global trading engine instance
global_engine = MatchingEngine()
