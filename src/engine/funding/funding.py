from rbloom import Bloom
from typing import Tuple, List
import time
import json
import asyncio
import logging

from src.engine.types.types import Market, OrderType, OrderSide, Order, Trade, OrderTimeInForce, OrderStatus
from src.engine.types.account_types import UniMarginAccount
from src.common.config.metadata import get_base_quote
from src.common.mmq import FUNDING_MATCH_MQ, MATCH_FUNDING_MQ, MMQTopic
#from src.engine.matching.matching import global_spot_engine

logger = logging.getLogger(__name__)

class Funding:
    def __init__(self, accounts: List[UniMarginAccount]):
        self.accounts = {account.uid: account for account in accounts}
        self.exist_order_ids = Bloom(1_000_000, 0.01)
        #self.cancelled_order_ids = Bloom()

    ### RPC interface
    def put_spot_order(
        self, uid, symbol, side, order_type, time_in_force, quantity,
        price=None, client_order_id=None, is_futures=False
        ) -> Tuple[bool, Order]:
        """ RPC interface
        现货订单验证
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

            account = self.accounts[uid]
            if amount > account.balances[quote]:
                return False, f"Insufficient {quote} balance"
            account.frozen_balances[quote] += amount
            account.balances[quote] -= amount
        else:
            if quantity > account.balances[base]:
                return False, f"Insufficient {base} balance"
            account.frozen_balances[base] += quantity
            account.balances[base] -= quantity
        
        account.version += 1
        order = Order(uid,
            symbol=symbol, side=side, order_type=order_type,
            time_in_force=time_in_force, quantity=quantity, price=price,
            client_order_id=client_order_id,
            is_futures=is_futures)
        FUNDING_MATCH_MQ.produce(MMQTopic.SPOT_NEW, json.dumps(order.to_dict()))
        return True, order

    def put_spot_orders(self, uid: str, params: list) -> Tuple[bool, List[Order]]:
        """ batch put spot orders, only for internal market maker
            * escape asset freezing process
            * drop market orders
            * drop orders whose time in force is FOK or IOC
        """
        orders = [Order(uid,
            symbol=param.get('symbol'),
            client_order_id=param.get('client_order_id') or str(int(time.time() * 1000)),
            side=param.get('side'),
            order_type=param.get('type'),
            time_in_force=param.get('time_in_force'),
            quantity=float(param.get('quantity')),
            price=float(param.get('price')) if param.get('price') else 0,
        ) for param in params if param.get('type') == OrderType.LIMIT and param.get('time_in_force') not in [OrderTimeInForce.FOK, OrderTimeInForce.IOC]]
        FUNDING_MATCH_MQ.produce(MMQTopic.SPOT_NEW, json.dumps([order.to_dict() for order in orders]))
        return True, orders

    def cancel_spot_orders(self, uid: str, symbol: str, order_ids: list) -> Tuple[bool, List[Order]]:
        """ batch cancel spot orders, only for internal market maker
        """
        valid_order_ids = []
        orders = []
        for oid in order_ids:
            order = Order(uid,
                symbol=symbol,
                side='',
                order_type='',
                time_in_force='',
                quantity=0,
                price=None,
                )
            order.order_id = oid
            order.status = OrderStatus.CANCELLING
            orders.append(order)
            
            if not oid in self.exist_order_ids:
                order.status = OrderStatus.UNKNOWN
                continue
            valid_order_ids.append(oid)

        if valid_order_ids:
            FUNDING_MATCH_MQ.produce(MMQTopic.SPOT_CANCEL, json.dumps({'uid': uid, 'symbol': symbol, 'order_ids': valid_order_ids}))
        return True, orders


    ### MMQ interface
    def on_spot_trades(self, trades: List[Trade]):
        """ 订单成交
        1. 订单成交后，冻结资产划转至对方账户，用户收到对应资产
        2. 冻结资产在订单取消或过期后解冻
        """
        

    def on_spot_order(self, order: Order):
        """ 现货订单删除
        2. 若订单存在，系统删除订单
        3. 若订单不存在，系统返回错误信息
        """
        self.exist_order_ids.add(order.order_id)

    def on_spot_orders(self, orders: List[Order]):
        """ 现货订单删除
        2. 若订单存在，系统删除订单
        3. 若订单不存在，系统返回错误信息
        """
        for order in orders:
            self.exist_order_ids.add(order.order_id)

    def on_removed_orders(self, orders: List[Order]):
        """ 现货订单删除
        2. 若订单存在，系统删除订单
        3. 若订单不存在，系统返回错误信息
        """



    async def run_forever(self, topics: List[MMQTopic]):
        """ run funding engine forever
        """
        prev_topic_offsets = {
            topic: 0 for topic in topics
        }
        while True:
            has_message = False
            for topic in topics:
                prev_offset = prev_topic_offsets[topic]
                queue_offset, message = MATCH_FUNDING_MQ.consume(topic, prev_offset)
                logger.debug(f"Consumed message from {topic} offset={queue_offset}: {message}")
                if message:
                    prev_topic_offsets[topic] = queue_offset + 1
                    data = json.loads(message)
                    if 'trades' in data:
                        self.on_spot_trades([Trade.from_dict(trade) for trade in data['trades']])

                    if 'orders' in data:
                        # batch put orders
                        self.on_spot_orders([Order.from_dict(order) for order in data['orders']])
                    elif 'order' in data:
                        # put single order for normal users
                        self.on_spot_order(Order.from_dict(data['order']))
                    if 'removed_orders' in data:
                        self.on_removed_orders([Order.from_dict(oid) for oid in data['removed_orders']])
                        
                    has_message = True

            if has_message:
                await asyncio.sleep(0.05)
            else:
                await asyncio.sleep(0.1)


SPOT_FUNDING = Funding([UniMarginAccount("60000001", is_inner_maker=True), UniMarginAccount("60000002")])
FUTURE_FUNDING = Funding([UniMarginAccount("60000003", is_inner_maker=True)])
