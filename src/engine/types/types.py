import time
import uuid

# Order types
class OrderType:
    LIMIT = "LIMIT"
    MARKET = "MARKET"

# Order sides
class OrderSide:
    BUY = "BUY"
    SELL = "SELL"

# Order statuses
class OrderStatus:
    PENDING = "PENDING"
    NEW = "NEW"
    FILLED = "FILLED"
    CANCELED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"

# Order model
class Order:
    def __init__(self, symbol, side, order_type, quantity, price=None, client_order_id=None, is_futures=False):
        self.order_id = str(uuid.uuid4())
        self.client_order_id = client_order_id or str(uuid.uuid4())
        self.symbol = symbol
        self.side = side
        self.type = order_type
        self.price = price
        self.quantity = quantity
        self.is_futures = is_futures
        self.filled_quantity = 0
        self.status = OrderStatus.PENDING
        self.timestamp = int(time.time() * 1000)
        self.update_timestamp = int(time.time() * 1000)

    def to_dict(self):
        return {
            "orderId": self.order_id,
            "clientOrderId": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "type": self.type,
            "price": self.price,
            "origQty": self.quantity,
            "filled_quantity": self.filled_quantity,
            "status": self.status,
            "timestamp": self.timestamp,
            "update_timestamp": self.update_timestamp
        }

# Trade model
class Trade:
    def __init__(self, trade_id, symbol, price, quantity, buy_order_id, sell_order_id):
        self.trade_id = trade_id
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.timestamp = int(time.time() * 1000)

    def to_dict(self):
        return {
            "tradeId": self.trade_id,
            "symbol": self.symbol,
            "price": self.price,
            "quantity": self.quantity,
            "buyOrderId": self.buy_order_id,
            "sellOrderId": self.sell_order_id,
            "timestamp": self.timestamp
        }

# Order price level
class OrderLevel:
    def __init__(self, price, quantity):
        self.price = price
        self.quantity = quantity

    def to_dict(self):
        return {
            "price": self.price,
            "quantity": self.quantity
        }

# Order book model
class OrderBook:
    def __init__(self, symbol):
        self.symbol = symbol
        self.bids = []
        self.asks = []
        self.timestamp = int(time.time() * 1000)

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "bids": [bid.to_dict() for bid in self.bids],
            "asks": [ask.to_dict() for ask in self.asks],
            "timestamp": self.timestamp
        }

# Ticker model
class Ticker:
    def __init__(self, symbol, price, quantity):
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.timestamp = int(time.time() * 1000)

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "price": self.price,
            "quantity": self.quantity,
            "timestamp": self.timestamp
        }

# Create new order
def new_order(symbol, side, order_type, quantity, price):
    return Order(symbol, side, order_type, quantity, price)

# Create empty order, i.e., order not in order book
def empty_order(order_id, symbol):
    order = Order(symbol, "BUY", "LIMIT", 0)
    order.order_id = order_id
    order.status = OrderStatus.CANCELED
    return order

# Create new trade
def new_trade(symbol, price, quantity, buy_order_id, sell_order_id):
    trade_id = str(uuid.uuid4())
    return Trade(trade_id, symbol, price, quantity, buy_order_id, sell_order_id)

# Create new order book
def new_order_book(symbol):
    return OrderBook(symbol)

# Create new ticker
def new_ticker(symbol, price, quantity):
    return Ticker(symbol, price, quantity)
