import time
import threading


class UniMarginAccount:
    def __init__(self, uid: str, is_inner_maker: bool = False):
        self.uid = uid
        self.is_inner_maker = is_inner_maker
        self.balances = {}
        self.frozen_balances = {}
        self.version = 0
        self.uptime = int(1000 * time.time())

        self.spot_leverage = 1        # default leverage is 1x
        self.lock = threading.Lock()

        self.air_drop()

    def air_drop(self):
        with self.lock:
            self.balances['USDT'] = 1_000_000_000
            self.balances['BTC'] = 10_000
            self.balances['ETH'] = 100_000
            self.balances['JPM'] = 1_000_000_000

    def get_spot_leverage(self) -> float:
        return self.spot_leverage

    def set_spot_leverage(self, leverage: float):
        with self.lock:
            self.spot_leverage = leverage

    def add_balance(self, asset: str, amount: float):
        with self.lock:
            if asset not in self.balances:
                self.balances[asset] = 0
            self.balances[asset] += amount

    def sub_balance(self, asset: str, amount: float):
        with self.lock:
            self.balances[asset] -= amount
    
    def add_frozen_balance(self, order_id: str, asset: str, amount: float):
        """ 用户铺新订单时，冻结资产
        """
        with self.lock:
            if order_id not in self.frozen_balances:
                self.frozen_balances[order_id] = {
                    'settle_num': 0
                }
            self.frozen_balances[order_id][asset] += amount
            self.balances[asset] -= amount
    
    def sub_frozen_balance(self, order_id: str, asset: str, amount: float) -> bool:
        """ 订单成交或者撤单后，释放冻结资产
        """
        with self.lock:
            if self.frozen_balances[order_id][asset] < amount:
                return False
            self.frozen_balances[order_id][asset] -= amount
            self.frozen_balances[order_id]['settle_num'] += 1
            return True

    def free_frozen_balance(self, order_id: str):
        with self.lock:
            del self.frozen_balances[order_id]


class Position:
    def __init__(self, symbol: str, side: str, amount: float, price: float, leverage: float):
        self.symbol = symbol
        self.side = side
        self.amount = amount
        self.price = price
        self.leverage = leverage
        self.position_id = f"{symbol}_{side}_{amount}_{price}_{leverage}"
        self.position_type = "spot"
        self.position_status = "open"
        self.position_time = int(1000 * time.time())