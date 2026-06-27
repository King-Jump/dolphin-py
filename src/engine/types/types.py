import time
import uuid

# Market types
class Market:
    SPOT = "SPOT"
    SPOT_LEVERAGE = "SPOT_LEVERAGE"
    FUTURE = "FUTURE"

# Order types
class OrderType:
    # for new order
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    # for delete order
    DELETE = "DELETE"

# Order sides
class OrderSide:
    BUY = "BUY"
    SELL = "SELL"

# Order statuses
class OrderStatus:
    PENDING = "PENDING"
    NEW = "NEW"
    FILLED = "FILLED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"

# Time in force
class OrderTimeInForce:
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    BAIT = "BAIT"
    GTX = "GTX"

# Order model
class Order:
    def __init__(self, uid,symbol, side, order_type, time_in_force, quantity, price=None, client_order_id=None, is_futures=False, is_selftrade=False):
        self.order_id = str(uuid.uuid4())
        self.uid = uid
        self.client_order_id = client_order_id or str(uuid.uuid4())
        self.symbol = symbol
        self.side = side
        self.type = order_type
        self.price = price
        self.quantity = quantity
        self.time_in_force = time_in_force
        self.is_futures = is_futures
        self.filled_quantity = 0
        self.status = OrderStatus.PENDING
        self.timestamp = int(time.time() * 1000)
        self.update_timestamp = int(time.time() * 1000)
        self.is_selftrade = is_selftrade

    def __repr__(self) -> str:
        return self.order_id

    def to_dict(self):
        return {
            "uid": self.uid,
            "orderId": self.order_id,
            "clientOrderId": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "type": self.type,
            "price": self.price,
            "origQty": self.quantity,
            "timeInForce": self.time_in_force,
            "filled_quantity": self.filled_quantity,
            "status": self.status,
            "timestamp": self.timestamp,
            "update_timestamp": self.update_timestamp,
            "isSelfTrade": self.is_selftrade,
            "isFutures": self.is_futures,
        }

    def from_dict(self, data: dict):
        self.uid = data["uid"]
        self.order_id = data["orderId"]
        self.client_order_id = data["clientOrderId"]
        self.symbol = data["symbol"]
        self.side = data["side"]
        self.type = data["type"]
        self.price = data["price"]
        self.quantity = data["origQty"]
        self.time_in_force = data["timeInForce"]
        self.filled_quantity = data["filled_quantity"]
        self.status = data["status"]
        self.timestamp = data["timestamp"]
        self.update_timestamp = data["update_timestamp"]
        self.is_selftrade = data["isSelfTrade"]
        self.is_futures = data["isFutures"]

    def get_market(self) -> Market:
        """ just for prototype """
        if self.symbol == '90000001':
            return Market.SPOT
        elif self.symbol == '90000002':
            return Market.SPOT_LEVERAGE
        else:
            return Market.FUTURE
        
# Trade model
class Trade:
    def __init__(self, trade_id, taker_uid, maker_uid, symbol, price, quantity, buy_order_id, sell_order_id):
        self.trade_id = trade_id
        self.taker_uid = taker_uid
        self.maker_uid = maker_uid
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.timestamp = int(time.time() * 1000)

    def to_dict(self):
        return {
            "tradeId": self.trade_id,
            "takerUid": self.taker_uid,
            "makerUid": self.maker_uid,
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
def new_order(uid, symbol, side, order_type, time_in_force, quantity, price):
    return Order(uid, symbol, side, order_type, time_in_force, quantity, price)

# Create empty order, i.e., order not in order book
def empty_order(uid, order_id, symbol):
    order = Order(uid, symbol, "BUY", "LIMIT", OrderTimeInForce.GTC, 0)
    order.order_id = order_id
    order.status = OrderStatus.CANCELLED
    return order

# Create new trade
def new_trade(taker_uid, maker_uid, symbol, price, quantity, buy_order_id, sell_order_id):
    trade_id = str(uuid.uuid4())
    return Trade(trade_id, taker_uid, maker_uid, symbol, price, quantity, buy_order_id, sell_order_id)

# Create new order book
def new_order_book(symbol):
    return OrderBook(symbol)

# Create new ticker
def new_ticker(symbol, price, quantity):
    return Ticker(symbol, price, quantity)
