import time

class UniMarginAccount:
    def __init__(self, uid: str, is_inner_maker: bool = False):
        self.uid = uid
        self.is_inner_maker = is_inner_maker
        self.balances = {}
        self.frozen_balances = {}
        self.version = 0
        self.uptime = int(1000 * time.time())

        self.air_drop()

    def air_drop(self):
        self.balances['USDT'] = 1_000_000_000
        self.balances['BTC'] = 10_000
        self.balances['ETH'] = 100_000
        self.balances['JPM'] = 1_000_000_000
