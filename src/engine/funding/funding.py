from src.engine.types.types import Market, OrderType, OrderSide


class Funding:
    def __init__(self, account: SpotAccount):
        self.account = account


    def check_order(self, order: Order) -> Tuple[bool, str]:
        if order.market == Market.SPOT:
            return self.check_spot_order(order)
        elif order.market == Market.SPOT_LEVERAGE:
            return self.check_spot_leverage_order(order)
        elif order.market == Market.FUTURE:
            return self.check_future_order(order)

    def check_spot_order(self, order: Order) -> Tuple[bool, str]:
        """ 现货订单验证
        1. 用户提交限价单后，系统检查现货钱包中可用余额
        2. 若余额充足，立即冻结订单全额对应的资产（买入冻结报价货币USDT，卖出冻结基础货币BTC）
        3. 订单成交后，冻结资产划转至对方账户，用户收到对应资产
        4. 若订单未成交，冻结资产在订单取消或过期后解冻
        5. 止损限价单：触发止损价后转为限价单
        6. 市价单卖出，传入参数为基础货币数量，并冻结相应基础货币；市价单买入，传入参数为报价货币数量，并冻结相应报价货币
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