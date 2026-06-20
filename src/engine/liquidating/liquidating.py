""" 用户下单 → 冻结资产 → 订单入簿 → 撮合匹配 → 逐笔结算 → 更新账本 → 推送通知
"""
from engine.types.account_types import SpotAccount
from engine.types.types import Order, OrderType

MARKET_ORDER_SLIPPAGE = 0.05

class Liquidating:
    def __init__(self, account: SpotAccount):
        self.account = account

    def liquidate(self, order: Order):
        """ 处理订单
        """
        pass

    def check_order(self, order: Order) -> Tuple[bool, str]:
        """ 
        验证订单参数（价格、数量、交易对合法性）
        检查账户可用余额是否充足
        冻结对应资产：

        买单：冻结 数量 × 价格 的计价货币（如 USDT）
        卖单：冻结对应数量的基础货币（如 BTC）
        订单进入订单簿等待撮合
        """
        base, quote = self.get_base_quote(order.symbol)

        if order.type == OrderType.MARKET:
            price = self.get_price(order.symbol)
            price *= (1 + MARKET_ORDER_SLIPPAGE) if order.side == OrderSide.BUY else (1 - MARKET_ORDER_SLIPPAGE)
        else:
            price = order.price
        
        if order.side == OrderSide.BUY:
            amount = price * order.quantity
            if amount > self.account.balances[quote]:
                return False, f"Insufficient {quote} balance"
            self.account.frozen_balances[quote] += amount
            self.account.balances[quote] -= amount
        else:
            if order.quantity > self.account.balances[base]:
                return False, f"Insufficient {base} balance"
            self.account.frozen_balances[base] += order.quantity
            self.account.balances[base] -= order.quantity
        
        self.account.version += 1
        return True, "Order checked successfully"