from rbloom import Bloom
from typing import Tuple, List
import time
import json

from src.engine.types.types import Market, OrderType, OrderSide, Order, Trade, TimeInForce
from src.engine.types.account_types import UniMarginAccount
from src.common.config.metadata import get_base_quote
from src.common.mmq import FUNDING_MATCH_MQ, MMQTopic



class Funding:
    def __init__(self, accounts: List[UniMarginAccount]):
        self.accounts = accounts
        self.order_ids = Bloom()


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

    def on_order(self, order: Order) -> Tuple[bool, str]:
        """ 现货订单删除
        2. 若订单存在，系统删除订单
        3. 若订单不存在，系统返回错误信息
        """
        if order.order_id not in self.order_ids:
            return False, "Order ID not found"
        self.order_ids.remove(order.order_id)
        return True, "Order deleted successfully"

    def put_spot_order(
        self, uid, symbol, side, order_type, time_in_force, quantity,
        price=None, client_order_id=None, is_futures=False
        ) -> Tuple[bool, str|Order]:
        """ 现货订单验证
        1. 用户提交限价单后，系统检查现货钱包中可用余额
        2. 若余额充足，立即冻结订单全额对应的资产（买入冻结报价货币USDT，卖出冻结基础货币BTC）
        3. 订单成交后，冻结资产划转至对方账户，用户收到对应资产
        4. 若订单未成交，冻结资产在订单取消或过期后解冻
        5. 止损限价单：触发止损价后转为限价单
        6. 市价单卖出，传入参数为基础货币数量，并冻结相应基础货币；市价单买入，传入参数为报价货币数量，并冻结相应报价货币
        """
        base, quote = get_base_quote(symbol)
        
        if side == OrderSide.BUY:
            if order_type == OrderType.MARKET:
                # for market buy: quantity is the amount of quote currency to buy
                amount = quantity
            else:
                amount = price * quantity

            if amount > self.account.balances[quote]:
                return False, f"Insufficient {quote} balance"
            self.account.frozen_balances[quote] += amount
            self.account.balances[quote] -= amount
        else:
            if quantity > self.account.balances[base]:
                return False, f"Insufficient {base} balance"
            self.account.frozen_balances[base] += quantity
            self.account.balances[base] -= quantity
        
        self.account.version += 1
        order = Order(
            uid, symbol, side, order_type, time_in_force, quantity, price,
            client_order_id, is_futures)
        FUNDING_MATCH_MQ.produce(MMQTopic.SPOT_NEW, json.dumps(order.to_dict()))
        return True, order

    def put_spot_orders(self, uid: str, params: list) -> Tuple[bool, List[Order]]:
        """ batch put spot orders, only for internal market maker
            * escape asset freezing process
            * drop market orders
            * drop orders whose time in force is FOK or IOC
        """
        orders = [Order(uid,
            client_order_id=param.get('client_order_id') or str(int(time.time() * 1000)),
            side=param.get('side'),
            order_type=param.get('type'),
            time_in_force=param.get('time_in_force'),
            quantity=float(param.get('quantity')),
            price=float(param.get('price')) if param.get('price') else 0,
        ) for param in params if param.get('type') == OrderType.LIMIT and param.get('time_in_force') not in [TimeInForce.FOK, TimeInForce.IOC]]
        FUNDING_MATCH_MQ.produce(MMQTopic.SPOT_NEW, json.dumps([order.to_dict() for order in orders]))
        return True, orders

    def cancel_spot_orders(self, uid: str, symbol: str, order_ids: list) -> Tuple[bool, List[Order]]:
        """ batch cancel spot orders, only for internal market maker
        """
        valid_orders = []
        orders = []
        for oid in order_ids:
            order = Order(uid,
                symbol=symbol,
                side='',
                order_type='',
                time_in_force='',
                quantity=0,
                price=None,
                status=OrderStatus.CANCELLING,
                )
            order.order_id = oid
            orders.append(order)
            
            if not oid in self.order_ids:
                order.status = OrderStatus.UNKNOWN
                continue
            valid_orders.append(order)

        if valid_order_ids:
            FUNDING_MATCH_MQ.produce(MMQTopic.SPOT_CANCEL, json.dumps(valid_order_ids))
        return True, orders


SPOT_FUNDING = Funding([UniMarginAccount("60000001", is_inner_maker=True), UniMarginAccount("60000002")])
FUTURE_FUNDING = Funding([UniMarginAccount("60000003", is_inner_maker=True)])
