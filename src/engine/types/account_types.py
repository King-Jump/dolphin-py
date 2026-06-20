import time

class SpotAccount:
    def __init__(self, uid: str):
        self.uid = uid
        self.balances = {}
        self.frozen_balances = {}
        self.version = 0
        self.uptime = int(1000 * time.time())