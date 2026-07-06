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

    def _settlement_spot_new(self, account: UniMarginAccount, order: Order) -> Tuple[bool, str]:
        """ 进入撮合前，现货订单资产验证
        1. 用户提交限价单后，系统检查现货钱包中可用余额
        2. 若余额充足，立即冻结订单全额对应的资产（买入冻结报价货币USDT，卖出冻结基础货币BTC）
        3. 市价单卖出，传入参数为基础货币数量，并冻结相应基础货币；市价单买入，传入参数为报价货币数量，并冻结相应报价货币
        """
        base, quote = get_base_quote(order.symbol)

        if order.side == OrderSide.BUY:
            if order.order_type == OrderType.MARKET:
                # for market buy: quantity is the amount of quote currency to buy
                amount = order.quantity
            else:
                amount = order.price * order.quantity

            if amount > account.balances[quote]:
                return False, f"Insufficient {quote} balance"
            account.frozen_balances[quote] += amount
            account.balances[quote] -= amount
        else:
            if order.quantity > account.balances[base]:
                return False, f"Insufficient {base} balance"
            account.frozen_balances[base] += order.quantity
            account.balances[base] -= order.quantity
        
        account.version += 1
        return True, ""

    def _settlement_spot_cancel(self, account: UniMarginAccount, order: Order) -> Tuple[bool, str]:
        """ 若订单未成交，冻结资产在订单取消或过期后解冻
            市价单和限价单都有可能被取消，对于市价买单的撤单，解冻的是quote资产
        """
        base, quote = get_base_quote(order.symbol)
        
        if order.side == OrderSide.BUY:
            if order.order_type == OrderType.MARKET:
                leave_amount = order.quantity - order.filled_quantity
            else:
                leave_amount = order.price * (order.quantity - order.filled_quantity)
            if leave_amount > account.frozen_balances[quote]:
                return False, f"{order.uid} Insufficient {quote} frozen balance"

            if leave_amount:
                account.frozen_balances[quote] -= leave_amount
                account.balances[quote] += leave_amount
        else: # sell side
            leave_quantity = order.quantity - order.filled_quantity
            if leave_quantity > account.frozen_balances[base]:
                return False, f"{order.uid} Insufficient {base} frozen balance"

            if leave_quantity:
                account.frozen_balances[base] -= leave_quantity
                account.balances[base] += leave_quantity

        account.version += 1
        return True, ""



    ### RPC interface
    def put_spot_order(
        self, uid, symbol, side, order_type, time_in_force, quantity,
        price=None, client_order_id=None, is_futures=False
    ) -> Tuple[bool, Order]:
        """ RPC interface
        """
        if uid not in self.accounts:
            return False, f"Account {uid} is not found"
        
        account = self.accounts[uid]
        order = Order(uid,
            symbol=symbol, side=side, order_type=order_type,
            time_in_force=time_in_force, quantity=quantity, price=price,
            client_order_id=client_order_id,
            is_futures=is_futures)
        if not account.is_inner_maker:
            result, msg = self._settlement_spot_new(account, order)
            if not result:
                return False, msg

        # produce spot new order to match engine
        FUNDING_MATCH_MQ.produce(MMQTopic.MATCH_IN_SPOT_NEW, json.dumps(order.to_dict()))
        return True, order

    def put_spot_orders(self, uid: str, params: list) -> Tuple[bool, List[Order]]:
        """ batch put spot orders, only for internal market maker
            * escape asset freezing process
            * drop market orders
            * drop orders whose time in force is FOK or IOC
        """
        if uid not in self.accounts:
            return False, f"Account {uid} is not found"
        
        account = self.accounts[uid]
        if not account.is_inner_maker:
            return False, f"Account {uid} is not internal market maker, batch API is not allowed"

        orders = [Order(uid,
            symbol=param.get('symbol'),
            client_order_id=param.get('client_order_id') or str(int(time.time() * 1000)),
            side=param.get('side'),
            order_type=param.get('type'),
            time_in_force=param.get('time_in_force'),
            quantity=float(param.get('quantity')),
            price=float(param.get('price')) if param.get('price') else 0,
        ) for param in params if param.get('type') == OrderType.LIMIT and param.get('time_in_force') not in [OrderTimeInForce.FOK, OrderTimeInForce.IOC]]
        
        # produce spot new orders to match engine
        FUNDING_MATCH_MQ.produce(MMQTopic.MATCH_IN_SPOT_NEW, json.dumps([order.to_dict() for order in orders]))
        return True, orders

    def cancel_spot_orders(self, uid: str, symbol: str, order_ids: list) -> Tuple[bool, List[Order]]:
        """ batch cancel spot orders, only for internal market maker
        """
        if uid not in self.accounts:
            return False, f"Account {uid} is not found"
        
        account = self.accounts[uid]

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
            if not account.is_inner_maker:
                for order in orders:
                    if order.order_id in valid_order_ids:
                        result, msg = self._settlement_spot_cancel(account, order)
                        if not result:
                            return False, msg
            FUNDING_MATCH_MQ.produce(MMQTopic.MATCH_IN_SPOT_CANCEL, json.dumps({'uid': uid, 'symbol': symbol, 'order_ids': valid_order_ids}))
        return True, orders

    def _settlement_spot_trade(self, trade: Trade) -> bool:
        """ 订单成交后，冻结资产划转至对方账户，用户收到对应资产
        """
        base, quote = get_base_quote(trade.symbol)

        taker = self.accounts.get(trade.taker_uid)
        maker = self.accounts.get(trade.maker_uid)
        if not taker and not maker:
            logger.error(f"Taker {trade.taker_uid} and Maker {trade.maker_uid} is not found of Trade {trade.to_dict()}")
            return False

        if trade.is_taker_buyer:
            # move quote from taker to maker, move base from maker to taker
            amount = trade.quantity * trade.price
            if taker:
                taker.frozen_balances[quote] -= amount
                if base not in taker.balances:
                    taker.balances[base] = 0
                taker.balances[base] += trade.quantity
            if maker:
                maker.frozen_balances[quote] += amount
                maker.balances[base] -= trade.quantity
        else:
            # move quote from maker to taker, move base from taker to maker
            amount = trade.quantity * trade.price
            if maker:
                maker.frozen_balances[quote] -= amount
                if base not in maker.balances:
                    maker.balances[base] = 0
                maker.balances[base] += trade.quantity
            if taker:
                taker.frozen_balances[quote] += amount
                taker.balances[base] -= trade.quantity
        return True

    ### MMQ interface
    def on_spot_trades(self, trades: List[Trade]):
        """ 订单成交
            订单成交后，冻结资产划转至对方账户，用户收到对应资产
        """
        for trade in trades:
            if not self._settlement_spot_trade(trade):
                continue
        

    def on_spot_order(self, order: Order):
        """ 铺单成功：记录订单ID
        """
        self.exist_order_ids.add(order.order_id)

    def on_spot_orders(self, orders: List[Order]):
        """ 批量铺单成功：记录订单ID
        """
        for order in orders:
            self.exist_order_ids.add(order.order_id)

    def on_removed_orders(self, orders: List[Order]):
        """ 现货订单删除: 解冻资产
            必须是非做市商账户，且未完全成交
        """
        for order in orders:
            account = self.accounts.get(order.uid)
            if account and not account.is_inner_maker and order.filled_quantity < order.quantity:
                self._settlement_spot_cancel(account, order)



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


FEE_ACCOUNT = UniMarginAccount("60000000")
SPOT_FUNDING = Funding([UniMarginAccount("60000001", is_inner_maker=True), UniMarginAccount("60000002")])
FUTURE_FUNDING = Funding([UniMarginAccount("60000003", is_inner_maker=True)])
