import time
from src.engine.types.types import Order, OrderSide, OrderStatus, OrderLevel, OrderBook as OrderBookModel
import threading

class BaseSortedCircularArray:
    def __init__(self, max_size=200):
        # Use circular list for efficient order addition and removal
        self.orders = [None] * max_size
        self.max_size = max_size
        self.head = 0
        self.tail = 0
    
    def pop(self):
        # Get the best order (head of queue)
        if self.head == self.tail:
            # Queue is empty
            return None
        order = self.orders[self.head]
        self.orders[self.head] = None
        self.head = (self.head + 1) % self.max_size
        return order
    
    def peek(self):
        if self.head == self.tail:
            # Queue is empty
            return None
        return self.orders[self.head]
    
    def remove(self, order_id):
        # Linear search and remove order by order_id
        head, tail = self.head, self.tail
        if head == tail:
            # Queue is empty
            return False
        
        if head < tail:
            for i in range(head, tail):
                if self.orders[i].order_id == order_id:
                    for j in range(i+1, tail):
                        self.orders[j-1] = self.orders[j]
                    self.tail -= 1
                    self.orders[tail] = None
                    return True
        else:
            # Process in two segments: first from head to max_size-1, second from 0 to tail-1
            for i in range(head, self.max_size):
                if self.orders[i].order_id == order_id:
                    for j in range(i+1, self.max_size):
                        self.orders[j-1] = self.orders[j]
                    self.orders[self.max_size-1] = self.orders[0]

                    for j in range(0, tail - 1):
                        self.orders[j] = self.orders[j+1]
                    if tail == 0:
                        tail = self.max_size - 1
                    else:
                        tail -= 1
                    self.orders[tail] = None
                    self.tail = tail
                    return True

            # Search and remove order in the second segment
            for i in range(0, tail):
                if self.orders[i].order_id == order_id:
                    for j in range(i+1, tail):
                        self.orders[j-1] = self.orders[j]
                    self.orders[tail-1] = None
                    self.tail -= 1
                    return True
        return False
    
    def __len__(self):
        return (self.tail - self.head + self.max_size) % self.max_size

class BidSortedCircularArray(BaseSortedCircularArray):
    def push(self, order):
        # Buy orders sorted by price descending, same price by time ascending
        head, tail = self.head, self.tail
        if head == tail:
            # Queue is empty, insert directly
            self.orders[self.tail] = order
            self.tail = (self.tail + 1) % self.max_size
            return
        
        order_price = order.price
        if (tail + 1) % self.max_size == head:
            # Queue is full, remove lowest price order
            if order_price <= self.orders[tail - 1].price:
                # New order price is not higher than tail order, discard new order
                order.status = OrderStatus.CANCELED
                return
            else:
                # Remove tail order
                self.orders[tail - 1].status = OrderStatus.CANCELED
                self.orders[tail - 1] = None
                tail = (tail - 1 + self.max_size) % self.max_size

        if head < tail:
            insert_idx = tail - 1
            while insert_idx != head:
                existing_order = self.orders[insert_idx]
                if order_price <= existing_order.price:
                    break

                self.orders[insert_idx + 1] = self.orders[insert_idx]
                insert_idx -= 1
            # Insert order
            self.orders[insert_idx + 1] = order
            self.tail = (self.tail + 1) % self.max_size
        else:
            # Process in two segments: first from 0 to tail-1, second from head to max_size-1
            if tail == 0:
                if order_price <= self.orders[self.max_size - 1].price:
                    self.orders[0] = order
                    self.tail += 1
                    return
            else:
                insert_idx = tail - 1
                while insert_idx >= 0:
                    existing_order = self.orders[insert_idx]
                    if order_price <= existing_order.price:
                        break
                    self.orders[insert_idx + 1] = self.orders[insert_idx]
                    insert_idx -= 1
                
                # Insert order
                if insert_idx >= 0:
                    self.orders[insert_idx] = order
                    self.tail += 1
                    return
                
                if self.orders[self.max_size - 1].price >= order_price:
                    self.orders[0] = order
                    self.tail += 1
                    return
                
                self.orders[0] = self.orders[self.max_size - 1]
                # Find insertion position in the second segment
                insert_idx = self.max_size - 2
                while insert_idx != head:
                    existing_order = self.orders[insert_idx]
                    if order_price <= existing_order.price:
                        break
                    self.orders[insert_idx + 1] = self.orders[insert_idx]
                    insert_idx -= 1
                
                # Insert order
                self.orders[insert_idx + 1] = order
                self.tail += 1
                return

        
class AskSortedCircularArray(BaseSortedCircularArray):
    def push(self, order):
        # Sell orders sorted by price ascending, same price by time ascending
        head, tail = self.head, self.tail
        if head == tail:
            # Queue is empty, insert directly
            self.orders[self.tail] = order
            self.tail = (self.tail + 1) % self.max_size
            return

        order_price = order.price
        if (tail + 1) % self.max_size == head:
            # Queue is full, remove highest price order
            if order_price >= self.orders[tail - 1].price:
                # New order price is not lower than head order, discard new order
                order.status = OrderStatus.CANCELED
                return
            else:
                # Remove tail order
                self.orders[tail - 1].status = OrderStatus.CANCELED
                self.orders[tail - 1] = None
                tail = (tail - 1 + self.max_size) % self.max_size

        if head < tail:
            insert_idx = tail - 1
            while insert_idx != head:
                existing_order = self.orders[insert_idx]
                if order_price >= existing_order.price:
                    break

                self.orders[insert_idx + 1] = self.orders[insert_idx]
                insert_idx -= 1
            # Insert order
            self.orders[insert_idx + 1] = order
            self.tail = (self.tail + 1) % self.max_size
        else:
            # Process in two segments: first from 0 to tail-1, second from head to max_size-1
            if tail == 0:
                if order_price >= self.orders[self.max_size - 1].price:
                    self.orders[0] = order
                    self.tail += 1
                    return
            else:
                insert_idx = tail - 1
                while insert_idx >= 0:
                    existing_order = self.orders[insert_idx]
                    if order_price >= existing_order.price:
                        break
                    self.orders[insert_idx + 1] = self.orders[insert_idx]
                    insert_idx -= 1
                
                # Insert order
                if insert_idx >= 0:
                    self.orders[insert_idx] = order
                    self.tail += 1
                    return
                
                if self.orders[self.max_size - 1].price <= order_price:
                    self.orders[0] = order
                    self.tail += 1
                    return
                
                self.orders[0] = self.orders[self.max_size - 1]
                # Find insertion position in the second segment
                insert_idx = self.max_size - 2
                while insert_idx != head:
                    existing_order = self.orders[insert_idx]
                    if order_price >= existing_order.price:
                        break
                    self.orders[insert_idx + 1] = self.orders[insert_idx]
                    insert_idx -= 1
                
                # Insert order
                self.orders[insert_idx + 1] = order
                self.tail += 1
                return



class OrderBook:
    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol
        self.bids = BidSortedCircularArray()
        self.asks = AskSortedCircularArray()
        self.orders = {}
        self.lock = threading.RLock()
    
    def add_order(self, order):
        with self.lock:
            self.orders[order.order_id] = order
            if order.side == OrderSide.BUY:
                self.bids.push(order)
            else:
                self.asks.push(order)
    
    def remove_order(self, order_id):
        with self.lock:
            order = self.orders.get(order_id)
            if not order:
                return None
            
            # Remove from order book
            if order.side == OrderSide.BUY:
                self.bids.remove(order_id)
            else:
                self.asks.remove(order_id)
            
            del self.orders[order_id]
            return order
    
    def get_order(self, order_id):
        with self.lock:
            return self.orders.get(order_id)
    
    def get_order_book(self, depth=30):
        with self.lock:
            order_book = OrderBookModel(self.symbol)
            
            # Build buy price levels
            bid_map = {}
            for order in self.bids.orders:
                if order.status == OrderStatus.PENDING:
                    remaining = order.quantity - order.filled_quantity
                    if remaining > 0:
                        if order.price in bid_map:
                            bid_map[order.price] += remaining
                        else:
                            bid_map[order.price] = remaining
            
            # Sort by price descending
            sorted_bids = sorted(bid_map.items(), key=lambda x: -x[0])[:depth]
            for price, quantity in sorted_bids:
                order_book.bids.append(OrderLevel(price, quantity))
            
            # Build sell price levels
            ask_map = {}
            for order in self.asks.orders:
                if order.status == OrderStatus.PENDING:
                    remaining = order.quantity - order.filled_quantity
                    if remaining > 0:
                        if order.price in ask_map:
                            ask_map[order.price] += remaining
                        else:
                            ask_map[order.price] = remaining
            
            # Sort by price ascending
            sorted_asks = sorted(ask_map.items(), key=lambda x: x[0])[:depth]
            for price, quantity in sorted_asks:
                order_book.asks.append(OrderLevel(price, quantity))
            
            order_book.timestamp = int(time.time() * 1000)
            return order_book
    
    def get_best_bid(self):
        with self.lock:
            best_bid = self.bids.peek()
            return best_bid.price if best_bid else 0
    
    def get_best_ask(self):
        with self.lock:
            best_ask = self.asks.peek()
            return best_ask.price if best_ask else 0
    
    def get_depth(self, symbol, limit=30):
        # Simplified implementation, return mock data
        return {
            "lastUpdateId": int(time.time() * 1000),
            "bids": [["59000.00", "1.0"], ["58999.00", "2.0"]],
            "asks": [["59001.00", "1.0"], ["59002.00", "2.0"]]
        }
    
    def get_ticker(self, symbol):
        # Simplified implementation, return mock data
        return {
            "price": 59000.00
        }
