from rbloom import Bloom

from src.engine.types.types import Market, OrderType, OrderSide, Order, Trade, SpotAccount
from typing import Tuple
import time



class Funding:
    def __init__(self, account: SpotAccount):
        self.account = account
        self.order_ids = Bloom()


    def on_order(self, order: Order) -> Tuple[bool, str]:
        """ 新订单
        1. 用户提交订单后，系统检查订单类型是否合法
        2. 若订单类型合法，根据订单市场类型调用不同的订单验证函数
        """
        if order.get_market() == Market.SPOT:
            if order.type == OrderType.DELETE:
                return self.handle_spot_delete_order(order)
            return self.handle_spot_order(order)
        elif order.get_market() == Market.SPOT_LEVERAGE:
            if order.type == OrderType.DELETE:
                return self.handle_spot_leverage_delete_order(order)
            return self.handle_spot_leverage_order(order)
        elif order.get_market() == Market.FUTURE:
            return self.handle_future_order(order)

    def on_trade(self, trade: Trade) -> Tuple[bool, str]:
        """ 订单成交
        1. 订单成交后，冻结资产划转至对方账户，用户收到对应资产
        2. 冻结资产在订单取消或过期后解冻
        """
        if trade.market == Market.SPOT:
            return self.handle_spot_trade(trade)
        elif trade.market == Market.SPOT_LEVERAGE:
            return self.handle_spot_leverage_trade(trade)
        elif trade.market == Market.FUTURE:
            return self.handle_future_trade(trade)

    def handle_spot_delete_order(self, order: Order) -> Tuple[bool, str]:
        """ 现货订单删除
        2. 若订单存在，系统删除订单
        3. 若订单不存在，系统返回错误信息
        """
        if order.order_id not in self.order_ids:
            return False, "Order ID not found"
        self.order_ids.remove(order.order_id)
        return True, "Order deleted successfully"

    def handle_spot_order(self, order: Order) -> Tuple[bool, str]:
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