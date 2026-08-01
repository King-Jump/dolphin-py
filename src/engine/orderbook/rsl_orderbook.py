""" Reduced SkipList Order Book
    * 用skip list存储价格索引
    * 使用二维数组压缩存储跳表数据
    * 统一内存管理，避免GC
    * 需要上层保证订单严格时序，即先加入order book的订单时间优先
    * 注意：skip list的最大层数max_index_level必须满足pow(2, max_index_level) <= max_orders（最大订单数量）
"""
from src.engine.orderbook.orderbook import OrderBookInterface
from src.engine.types.types import Order, OrderSide, OrderBookModel
from typing import List, Optional, Tuple
import threading
import random
import time


class OrderPool:
    """ 订单池，用于存储所有订单，预分配内存避免GC
    """
    def __init__(self, max_orders: int):
        self.max_order_size = max_orders  # max number of orders
        self.capacity = 0   # number of orders

        # list of orders with the same price
        self.free_orders = [LevelOrder(i) for i in range(max_orders)]
        self.free_orders_ptr = list(range(1, max_orders+1))
        self.free_ptr_head = 0

    def is_full(self) -> bool:
        return self.capacity >= self.max_order_size

    def new(self, order: Order) -> Optional[LevelOrder]:
        if self.capacity >= self.max_order_size:
            return None

        # allocate a new node from free node list
        node = self.free_orders[self.free_ptr_head]
        node.order = order

        # remove the node from free node list
        self.free_ptr_head = self.free_orders_ptr[self.free_ptr_head]
        self.capacity += 1
        return node

    def free(self, node: LevelOrder):
        # add the node to free node list
        self.free_orders_ptr[node.order_index] = self.free_ptr_head
        self.free_ptr_head = node.order_index
        node.order = None
        self.capacity -= 1


class SkipList:
    def __init__(self, max_index_level=16, pN=4, order_pool: OrderPool=None):
        if pN <= 2:
            raise ValueError("pN must be greater than 2")

        self.max_index_level = max_index_level     # 最大层数限制（防止无限增长）
        self.pN = pN                     # 向上提升的概率1/pN（通常0.5或0.25）
        self.level = 1                   # 当前跳表的有效最大层数（从1开始）
        self.order_pool = order_pool     # 订单对象池，用于对象重用，避免GC
        
        self._gen_headers()

    def _gen_headers(self):
        """ 生成所有层的头节点
            level 0 的header是0
            level 1 的header是一半
            level 2 的header是四分之三
            ...
        """
        self.headers = [0] * self.max_index_level
        self.level_size = [0] * self.max_index_level    # 每一层的索引数量上限
        self.level_num = [0] * self.max_index_level     # 每一层的索引数量

        start, end = 0, self.max_index_level
        size = self.max_index_level
        for lvl in range(1, self.max_index_level):
            mid = (start + end) // 2
            self.headers[lvl] = mid
            start = mid

            size //= 2
            self.level_size[lvl] = size - 1

    def _random_level(self):
        """随机生成新节点的层数（1 到 max_level 之间）"""
        lvl = 1
        # 每次以概率1/pN 增加一层，直到达到上限
        for _ in range(self.max_index_level-1):
            if random.randint(1, 100) % self.pN == 0:
                lvl += 1
        return lvl

    def _free_price_level(self, target: PriceLevel, update: List[PriceLevel]):
        """ clear the target PriceLevel from skip list
        """
        for lvl in range(target.level):
            update[lvl].forward[lvl] = target.forward[lvl]

        # 调整跳表的当前有效最大层数：若顶层已空，则降低 level
        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        self.price_level_pool.free(target)

    def search(self, order: Order) -> Optional[PriceLevel]:
        """查找指定价格对应的挡位，返回挡位head，不存在则返回 None"""
        current = self.head
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and self._compare(current.forward[lvl].price, order.price) < 0:
                current = current.forward[lvl]
        # 到达底层，current 指向最后一个键 < order.price 的节点
        candidate = current.forward[0]
        if candidate and candidate.price == order.price:
            return candidate
        return None

    def delete_farest_level(self) -> List[Order]:
        """删除最远挡位的全部订单，返回删除的订单列表
        """
        # 定位最远挡位
        farest_level = self.head
        while farest_level.forward[0]:
            farest_level = farest_level.forward[0]
        # 释放该挡位下的所有订单，不包括head节点
        orders = []
        if not farest_level.level_head.next:
            # 防御编程，该档位没有订单，异常！
            return orders

        order_node = farest_level.level_head.next
        while order_node:
            orders.append(order_node.order)
            self.order_pool.free(order_node)
            order_node = order_node.next

        update = [None] * self.max_index_level
        current = self.head
        # 从最高层开始查找，记录每一层的前驱
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and self._compare(current.forward[lvl].price, farest_level.price) < 0:
                current = current.forward[lvl]
            update[lvl] = current
        self._free_price_level(farest_level, update)
        return orders

    def insert(self, order: Order) -> bool:
        # update 数组用于记录每一层插入位置的前驱节点
        update = [None] * self.max_index_level
        current = self.head

        # 从最高层开始查找，记录每一层的前驱
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and self._compare(current.forward[lvl].price, order.price) < 0:
                current = current.forward[lvl]
            update[lvl] = current

        # 检查键是否已存在（底层下一个节点）
        price_level = current.forward[0]
        if price_level and price_level.price == order.price:
            # 找到当前价格挡位，首先申请订单对象，再将新订单插入PriceLevel的order列表末尾
            new_order = self.order_pool.new(order)
            if not new_order:
                return False
            new_order.prev = price_level.level_tail
            new_order.next = None
            price_level.level_tail.next = new_order
            price_level.level_tail = new_order
            price_level.order_num += 1
            return True

        # 生成新price level
        rand_level = self._random_level()
        # 如果新节点的层数超过当前跳表的最高层，需要将多出的层的前驱指向头节点
        if rand_level > self.level:
            for lvl in range(self.level, rand_level):
                update[lvl] = self.head
            self.level = rand_level

        new_price_level = self.price_level_pool.new(order.price, rand_level)
        if not new_price_level:
            return False
        new_order = self.order_pool.new(order)
        if not new_order:
            self.price_level_pool.free(new_price_level)
            return False

        # 将新PriceLevel节点插入到跳表各层链表中
        for lvl in range(rand_level):
            new_price_level.forward[lvl] = update[lvl].forward[lvl]
            update[lvl].forward[lvl] = new_price_level

        # 将新订单插入到price level的order列表末尾
        new_order.prev = new_price_level.level_tail
        new_order.next = None
        new_price_level.level_tail.next = new_order
        new_price_level.level_tail = new_order
        new_price_level.order_num += 1
        return True

    def delete(self, order: Order) -> bool:
        """删除指定订单, 返回 True 表示成功, False 表示键不存在"""
        # 首先找到订单所属的price level
        update = [None] * self.max_index_level
        current = self.head

        # 从最高层开始查找，记录每一层的前驱
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and self._compare(current.forward[lvl].price, order.price) < 0:
                current = current.forward[lvl]
            update[lvl] = current

        price_level = current.forward[0]
        if not price_level or price_level.price != order.price:
            return False

        # 释放LevelOrder对象
        current_order = price_level.level_head.next
        while current_order:
            if current_order.order.order_id == order.order_id:
                current_order.prev.next = current_order.next
                if current_order.next:
                    current_order.next.prev = current_order.prev
                if current_order == price_level.level_tail:
                    price_level.level_tail = current_order.prev
                break
            current_order = current_order.next

        if not current_order:
            return False

        self.order_pool.free(current_order)
        price_level.order_num -= 1
        if price_level.order_num == 0:
            # 当前价格挡位已经没有订单，删除该挡位
            self._free_price_level(price_level, update)
        return True

    def peek(self) -> Optional[Order]:
        """ peek the first order in the array
        """
        if self.head.forward[0] and self.head.forward[0].level_head.next:
            return self.head.forward[0].level_head.next.order
        return None

    def pop(self) -> Optional[Order]:
        """ pop the first order in the array
        """
        if not self.head.forward[0] or not self.head.forward[0].level_head.next:
            return None

        top_level = self.head.forward[0]
        order = top_level.level_head.next.order
        self.delete(order)
        return order

    def peek_depth(self, depth: int) -> List[Tuple[float, float]]:
        """ peek the first depth orders in the array
        """
        levels = []
        current_level = self.head.forward[0]
        for _ in range(depth):
            if not current_level:
                break
            level_qty = 0
            curr_order = current_level.level_head.next
            while curr_order:
                level_qty += curr_order.order.quantity - curr_order.order.filled_quantity
                curr_order = curr_order.next
            levels.append((current_level.price, level_qty))
            current_level = current_level.forward[0]

        return levels

class AskSkipList(SkipList):
    def __init__(self, max_level=16, pN=4, order_pool: OrderPool=None):
        super().__init__(max_level, pN, order_pool)

    def _compare(self, a: Order, b: Order) -> int:
        """ compare two orders, first by price, second by timestamp
        1. price is ascending
        """
        if a.price == b.price:
            if a.timestamp < b.timestamp:
                return -1
            elif a.timestamp > b.timestamp:
                return 1
            else:
                if a.order_id < b.order_id:
                    return -1
                elif a.order_id > b.order_id:
                    return 1
                else:
                    return 0
        elif a.price > b.price:
            return 1
        else: # a.price < b.price
            return -1

class BidSkipList(SkipList):
    def __init__(self, max_level=16, pN=4, order_pool: OrderPool=None):
        super().__init__(max_level, pN, order_pool)

    def _compare(self, a: Order, b: Order) -> int:
        """ compare two orders, first by price, second by timestamp
        1. price is descending
        """
        if a.price == b.price:
            if a.timestamp < b.timestamp:
                return -1
            elif a.timestamp > b.timestamp:
                return 1
            else:
                if a.order_id < b.order_id:
                    return -1
                elif a.order_id > b.order_id:
                    return 1
                else:
                    return 0
        elif a.price > b.price:
            return -1
        else: # a.price < b.price
            return 1


class OrderBook(OrderBookInterface):
    """ 单币对最多支持max_nodes个订单，超出限制则主动撤最远的订单
    """
    def __init__(self, symbol, max_index_level=14, max_price_level=1_000, max_orders=20_000, logger=None):
        self.symbol = symbol
        self.ask_order_pool = OrderPool(max_orders)
        self.bid_order_pool = OrderPool(max_orders)
        
        self.asks = AskSkipList(max_level=max_index_level, order_pool=self.ask_order_pool)
        self.bids = BidSkipList(max_level=max_index_level, order_pool=self.bid_order_pool)
        self.orders = {}
        self.ask_lock = threading.Lock()
        self.bid_lock = threading.Lock()

        self.logger = logger

    def add_order(self, order: Order) -> Optional[Order]:
        """ 添加订单到order book
        """
        if order.order_id in self.orders:
            return None

        if order.side == OrderSide.BUY:
            with self.bid_lock:
                if self.bid_order_pool.is_full():
                    # 超过最大订单数限制，删除最远档位下所有订单
                    removed_orders = self.bids.delete_farest_level()
                    for ro in removed_orders:
                        if ro.order_id in self.orders:
                            del self.orders[ro.order_id]

                if not self.bids.insert(order):
                    return None
        else:
            with self.ask_lock:
                if self.ask_order_pool.is_full():
                    # 超过最大订单数限制，删除最远档位下所有订单
                    removed_orders = self.asks.delete_farest_level()
                    for ro in removed_orders:
                        if ro.order_id in self.orders:
                            del self.orders[ro.order_id]

                if not self.asks.insert(order):
                    return None

        self.orders[order.order_id] = order
        return order

    def remove_order(self, order_id: str) -> Optional[Order]:
        """ 删除订单
        """
        if order_id not in self.orders:
            return None
        order = self.orders[order_id]

        if order.side == OrderSide.BUY:
            with self.bid_lock:
                self.bids.delete(order)
        else:
            with self.ask_lock:
                self.asks.delete(order)
        del self.orders[order_id]
        return order

    def batch_add_orders(self, side: str, orders: List[Order]) -> List[Order]:
        """ 批量添加订单
        """
        results = []
        for order in orders:
            if self.add_order(order):
                results.append(order)
        return results

    def batch_remove_orders(self, uid: str, order_ids: List[str]) -> List[Order]:
        """ 批量删除订单
        """
        results = []
        for order_id in order_ids:
            order = self.orders.get(order_id)
            if not order or order.uid != uid:
                continue
            if order and self.remove_order(order_id):
                results.append(order)
        return results

    def get_order(self, uid: str, order_id: str) -> Optional[Order]:
        """ 获取订单
        """
        order = self.orders.get(order_id)
        if order and order.uid == uid:
            return order
        return None

    def get_order_book(self, depth=30) -> OrderBookModel:
        """ 获取订单薄
        """
        ob = OrderBookModel(self.symbol)
        with self.ask_lock:
            ob.asks = self.asks.peek_depth(depth)
        with self.bid_lock:
            ob.bids = self.bids.peek_depth(depth)
        ob.timestamp = int(time.time() * 1000)
        return ob

    def get_best_bid(self) -> Optional[Order]:
        with self.bid_lock:
            return self.bids.peek()

    def get_best_ask(self) -> Optional[Order]:
        with self.ask_lock:
            return self.asks.peek()

    def update_order(self, order_id: str, filled_quantity: float) -> Optional[Order]:
        """ 更新maker订单
        """
        order = self.orders.get(order_id)
        if not order:
            return None

        order.filled_quantity = filled_quantity
        if order.filled_quantity >= order.quantity:
            self.remove_order(order.order_id)
        return order

    def pending_orders(self, uid):
        """获取用户所有待处理订单"""
        return [order for order in self.orders.values() if order.uid == uid]
