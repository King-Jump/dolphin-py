""" 用户下单 → 冻结资产 → 订单入簿 → 撮合匹配 → 逐笔结算 → 更新账本 → 推送通知
"""
from engine.types.account_types import UniMarginAccount
from engine.types.types import Order

class Liquidating:
    def __init__(self, account: UniMarginAccount):
        self.account = account

    def liquidate(self, order: Order):
        """ 处理订单
        """
        pass
