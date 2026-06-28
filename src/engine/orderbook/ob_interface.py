from typing import Optional, List
from src.engine.types.types import Order, OrderBook


class OrderBookInterface:
    """ Order book interface
    """
    def add_order(self, order: Order) -> Optional[Order]:
        """ 添加订单
        """
        raise NotImplementedError

    def remove_order(self, order_id: str) -> Optional[Order]:
        """ 删除订单
        """
        raise NotImplementedError

    def batch_add_orders(self, side: str, orders: List[Order]) -> List[Order]:
        """ 批量添加订单
        """
        raise NotImplementedError
    
    def batch_remove_orders(self, order_ids: List[str]) -> List[Order]:
        """ 批量删除订单
        """
        raise NotImplementedError

    def get_order(self, uid: str, order_id: str) -> Optional[Order]:
        """ 获取订单
        """
        raise NotImplementedError

    def get_order_book(self, depth: int = 10) -> OrderBook:
        """ 获取订单簿
        """
        raise NotImplementedError

    def get_best_bid(self) -> Optional[Order]:
        """ 获取最佳买单价格
        """
        raise NotImplementedError

    def get_best_ask(self) -> Optional[Order]:
        """ 获取最佳卖单价格
        """
        raise NotImplementedError

    def update_order(self, order_id: str, filled_quantity: float) -> Optional[Order]:
        """更新订单成交数量
        """
        raise NotImplementedError

    def pending_orders(self, uid: str) -> List[Order]:
        """ 获取用户待成交订单
        """
        raise NotImplementedError
