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
        
        self.lock = threading.Lock()

        self.air_drop()

    def air_drop(self):
        with self.lock:
            self.balances['USDT'] = 1_000_000_000
            self.balances['BTC'] = 10_000
            self.balances['ETH'] = 100_000
            self.balances['JPM'] = 1_000_000_000

    def add_balance(self, asset: str, amount: float):
        with self.lock:
            self.balances[asset] += amount

    def sub_balance(self, asset: str, amount: float):
        with self.lock:
            self.balances[asset] -= amount
    
    def add_frozen_balance(self, order_id: str, asset: str, amount: float):
        with self.lock:
            if order_id not in self.frozen_balances:
                self.frozen_balances[order_id] = {}
            self.frozen_balances[order_id][asset] += amount
    
    def sub_frozen_balance(self, order_id: str, asset: str, amount: float) -> bool:
        with self.lock:
            if self.free_frozen_balance[order_id][asset] < amount:
                return False
            self.frozen_balances[order_id][asset] -= amount
            return True

    def free_frozen_balance(self, order_id: str):
        with self.lock:
            del self.frozen_balances[order_id]
