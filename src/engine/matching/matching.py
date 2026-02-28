from src.engine.orderbook.orderbook import OrderBook
from src.engine.types.types import (
    Order,
    OrderType, OrderSide, OrderStatus, new_trade, empty_order
)
import threading

class MatchingEngine:
    def __init__(self):
        self.order_books = {}
        self.lock = threading.RLock()
    
    def get_order_book(self, symbol):
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
    
    def create_order(self, symbol, side, type, quantity, price=None, client_order_id=None, is_futures=False):        
        order = Order(
            symbol=symbol,
            side=side,
            type=type,
            quantity=quantity,
            price=price,
            client_order_id=client_order_id,
            is_futures=is_futures
        )
        
        trades = self.process_order(order)
        return trades, order
        
    def create_orders(self, params, is_futures=False):
        # batch create orders
        buy_orders = [Order(
                symbol=param['symbol'],
                side=param['side'],
                type=param['type'],
                quantity=param['quantity'],
                price=param.get('price'),
                is_futures=is_futures
            ) for param in params if param['side'] == OrderSide.BUY]
        buy_orders.sort(key=lambda x: x.price, reverse=True)

        sell_orders = [Order(
                symbol=param['symbol'],
                side=param['side'],
                type=param['type'],
                quantity=param['quantity'],
                price=param.get('price'),
                is_futures=is_futures
            ) for param in params if param['side'] == OrderSide.SELL]
        sell_orders.sort(key=lambda x: x.price)
        
        total_trades = []
        skip_match = False 
        for order in buy_orders:
            # Batch orders, simplified matching process
            if skip_match:
                order.status = OrderStatus.NEW
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
    
    def get_open_orders(self, symbol=None, is_futures=False):
        open_orders = []
        order_book = self.get_order_book(symbol)
        if order_book:
            open_orders = order_book.get_open_orders()
        return open_orders


# Global trading engine instance
global_engine = MatchingEngine()
