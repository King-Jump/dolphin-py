""" SkipList Linked Order Book
    * 用skip list存储价格索引
    * 相同价格的orders使用循环数组存储
    * 统一内存管理，避免GC
    * 需要上层保证订单严格时序，即先加入order book的订单时间优先
    * 新加入订单首先查询跳表，找到相同价格的PriceLevel，然后插入到该挡位orders的末尾
"""
from src.engine.orderbook.orderbook import OrderBookInterface
from src.engine.types.types import Order, OrderSide, OrdderBook as OrderBookModel
from typing import List, Optional, Tuple
import threading
import random
import time



class PriceLevel:
    def __init__(self, price: float, level: int, level_index: int = 0, orders_head: LevelOrder = None):
        self.forward = [None] * level  # 指向各层下一个节点的指针列表
        # forward[0] 指向底层下一个节点，forward[1] 指向第1层下一个节点...
        self.level_index = level_index  # index in free_levels list

        # price is the key of the skip list
        self.price = price
        self.level_head = orders_head

class LevelOrder:
    """ 相同价格的订单列表，使用预分配的数组链表，数组默认大小为size，超出size时扩容，数组为0时释放
    """
    def __init__(self, order_index: int, order: Order = None):
        self.prev = None
        self.next = None
        # 指向OrderPool.orders数组的索引
        self.order_index = order_index
        self.order = order  # 订单对象

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
        node.order_index = self.free_ptr_head
        node.order = order

        # remove the node from free node list
        self.free_ptr_head = self.free_levels_ptr[self.free_ptr_head]
        self.capacity += 1
        return node

    def free(self, node: LevelOrder):
        # add the node to free node list
        self.free_orders_ptr[node.order_index] = self.free_ptr_head
        self.free_ptr_head = node.order_index
        node.order = None
        node.order_index = -1
        self.capacity -= 1


class PriceLevelPool:
    """ 价格挡位对象池，用于存储所有价格挡位，预分配内存避免GC
    """
    def __init__(self, max_price_level: int):
        self.max_level_size = max_price_level  # max number of nodes
        self.level_capacity = 0   # number of price levels

        # list of price levels
        self.free_levels = [PriceLevel(0, max_price_level, i) for i in range(max_level_size)]
        self.free_levels_ptr = list(range(1, max_level_size+1))
        self.free_ptr_head = 0

    def is_full(self) -> bool:
        return self.level_capacity >= self.max_level_size

    def new(self, price: float, level: int) -> Optional[PriceLevel]:
        if self.level_capacity >= self.max_level_size:
            return None

        # allocate a new node from free node list
        node = self.free_levels[self.free_ptr_head]
        node.price = price
        node.level_head.prev = None
        node.level_head.next = None
        node.forward = [None] * level

        # remove the node from free node list
        self.free_ptr_head = self.free_levels_ptr[self.free_ptr_head]
        self.level_capacity += 1
        return node

    def free(self, node: PriceLevel) -> LevelOrder:
        # add the node to free node list
        self.free_levels_ptr[node.level_index] = self.free_ptr_head
        self.free_ptr_head = node.level_index
        self.level_capacity -= 1

        node.price = 0
        return node.level_head


class SkipList:
    def __init__(self, max_index_level=16, pN=4, price_level_pool: PriceLevelPool=None, order_pool: OrderPool=None):
        self.max_index_level = max_index_level     # 最大层数限制（防止无限增长）
        self.pN = pN                     # 向上提升的概率1/pN（通常0.5或0.25）
        self.head = PriceLevel(0, max_index_level)  # 头节点，贯穿所有层
        self.level = 1                 # 当前跳表的有效最大层数（从1开始）
        self.price_level_pool = price_level_pool
        self.order_pool = order_pool

    def _random_level(self):
        """随机生成新节点的层数（1 到 max_level 之间）"""
        lvl = 1
        # 每次以概率1/pN 增加一层，直到达到上限
        for _ in range(self.max_index_level-1):
            if random.randint(1, 100) % self.pN == 0:
                lvl += 1
        return lvl

    def _clear(self, target: PriceLevel, update: List[PriceLevel]):
        """ clear the target PriceLevel from skip list
        """
        for lvl in range(len(target.forward)):
            update[lvl].forward[lvl] = target.forward[lvl]

        # 调整跳表的当前有效最大层数：若顶层已空，则降低 level
        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        self._free_node(target)

    def search(self, order: Order) -> Optional[PriceLevel]:
        """查找指定键，返回值，不存在则返回 None"""
        current = self.head
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and self._compare(current.forward[lvl].price, order.price) < 0:
                current = current.forward[lvl]
        # 到达底层，current 指向最后一个键 < key 的节点
        candidate = current.forward[0]
        if candidate and candidate.price == order.price:
            return candidate
        return None

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
        candidate = current.forward[0]
        if candidate and candidate.price == order.price:

            return True

        if self.price_level_pool.is_full():
            # 超过最大挡位，删除最远价格
            farest_level = self.head.forward[0]
            while farest_level.forward[0]:
                farest_level = farest_level.forward[0]

            update = [None] * self.max_index_level
            current = self.head

            # 从最高层开始查找，记录每一层的前驱
            for lvl in range(self.level - 1, -1, -1):
                while current.forward[lvl] and self._compare(current.forward[lvl].price, order.price) < 0:
                    current = current.forward[lvl]
                update[lvl] = current
            self._clear(farest_level, update)

        # 生成新price level数
        rand_level = self._random_level()
        # 如果新节点的层数超过当前跳表的最高层，需要将多出的层的前驱指向头节点
        if rand_level > self.level:
            for lvl in range(self.level, rand_level):
                update[lvl] = self.head
            self.level = rand_level

        if self.order_pool.is_full():
            # 超过最大订单数量，删除最远订单
            farest_level = self.head.forward[0]
            while farest_level.forward[0]:
                farest_level = farest_level.forward[0]

            update = [None] * self.max_index_level
            current = self.head

            # 从最高层开始查找，记录每一层的前驱
            for lvl in range(self.level - 1, -1, -1):
                while current.forward[lvl] and self._compare(current.forward[lvl].price, order.price) < 0:
                    current = current.forward[lvl]
                update[lvl] = current
            self._clear(farest_level, update)

        new_price_level = self._new_node(order.price, rand_level)
        # 将新节点插入到各层链表中
        for lvl in range(rand_level):
            new_price_level.forward[lvl] = update[lvl].forward[lvl]
            update[lvl].forward[lvl] = new_price_level

        return True

    def delete(self, order: Order) -> bool:
        """删除指定键, 返回 True 表示成功, False 表示键不存在"""
        update = [None] * self.max_level
        current = self.head

        # 查找并记录各层前驱
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and self._compare(current.forward[lvl].price, order.price) < 0:
                current = current.forward[lvl]
            update[lvl] = current

        target = current.forward[0]
        if not target or target.order.order_id != order.order_id:
            return False

        self._clear(target, update)

        return True

    def batch_insert(self, orders: List[Order]) -> List[Order]:
        results = []
        for order in orders:
            if self.insert(order):
                results.append(order)
        return results

    def batch_delete(self, orders: List[Order]) -> List[str]:
        ids = []
        for order in orders:
            if self.delete(order):
                ids.append(order.order_id)
        return ids

    def peek(self) -> Optional[Order]:
        """ peek the first order in the array
        """
        if self.capacity == 0:
            return None
        return self.head.forward[0].order

    def pop(self) -> Optional[Order]:
        """ pop the first order in the array
        """
        if self.capacity == 0:
            return None

        node = self.head.forward[0]
        order = node.order
        for lvl in range(self.level):
            if self.head.forward[lvl] and self.head.forward[lvl].order.order_id == order.order_id:
                self.head.forward[lvl] = self.head.forward[lvl].forward[lvl]

        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        self._free_node(node)
        return order

    def peek_depth(self, depth: int) -> List[Tuple[float, float]]:
        """ peek the first depth orders in the array
        """
        if self.capacity == 0:
            return []

        level = 0
        levels = []
        current = self.head.forward[0]
        curr_price, curr_qty = current.order.price, current.order.quantity - current.order.filled_quantity
        while current.forward[0]:
            current = current.forward[0]
            price, qty = current.order.price, current.order.quantity - current.order.filled_quantity
            if price != curr_price:
                levels.append((curr_price, curr_qty))
                level += 1
                if level > depth:
                    break

                curr_price = price
                curr_qty = qty
            else:
                curr_qty += qty
        if level <= depth:
            levels.append((curr_price, curr_qty))
        return levels

class AskSkipList(SkipList):
    def __init__(self, max_level=16, pN=4, price_level_pool: PriceLevelPool=None, order_pool: OrderPool=None):
        super().__init__(max_level, pN, price_level_pool, order_pool)

    def _compare(self, a: float, b: float) -> int:
        """ compare two orders, first by price, second by timestamp
        1. price is ascending
        """
        if a == b:
            return 0
        elif a > b:
            return 1
        else: # a < b
            return -1

class BidSkipList(SkipList):
    def __init__(self, max_level=16, pN=4, price_level_pool: PriceLevelPool=None, order_pool: OrderPool=None):
        super().__init__(max_level, pN, price_level_pool, order_pool)

    def _compare(self, a: float, b: float) -> int:
        """ compare two orders, first by price, second by timestamp
        1. price is descending
        """
        if a == b:
            return 0
        elif a > b:
            return -1
        else: # a < b
            return 1


class OrderBook(OrderBookInterface):
    """ 单币对最多支持max_nodes个订单，超出限制则主动撤最远的订单
    """
    def __init__(self, symbol,  max_price_level=1_000, max_orders=100_000, logger=None):
        self.symbol = symbol
        self.price_level_pool = PriceLevelPool(max_price_level)
        self.order_pool = OrderPool(max_orders)

        self.asks = AskSkipList(self.price_level_pool, self.order_pool)
        self.bids = BidSkipList(self.price_level_pool, self.order_pool)
        self.orders = {}
        self.ask_lock = threading.Lock()
        self.bid_lock = threading.Lock()

        self.logger = logger

    def add_order(self, order: Order) -> Optional[Order]:
        """ 添加订单到order book
        """
        if order.order_id in self.orders:
            return None

        self.orders[order.order_id] = order
        if order.side == OrderSide.Buy:
            with self.ask_lock:
                self.asks.insert(order)
                if self.asks.is_full():
                    # 订单薄打满后，主动撤掉1%的远单
                    self.asks.pop(int(self.max_nodes * 0.01))
        else:
            with self.bid_lock:
                self.bids.insert(order)
                if self.bids.is_full():
                    # 订单薄打满后，主动撤掉1%的远单
                    self.bids.pop(int(self.max_nodes * 0.01))
        return order

    def remove_order(self, order_id: str) -> Optional[Order]:
        """ 删除订单
        """
        if order_id not in self.orders:
            return None
        order = self.orders[order_id]

        if order.side == OrderSide.Buy:
            with self.ask_lock:
                self.asks.delete(order)
        else:
            self.bids.delete(order)
        del self.orders[order_id]
        return order

    def batch_add_orders(self, orders: List[Order]) -> List[Order]:
        """ 批量添加订单
        """
        results = []
        for order in orders:
            if self.add_order(order):
                results.append(order)
        return results

    def batch_remove_orders(self, orders: List[Order]) -> List[str]:
        """ 批量删除订单
        """
        ids = []
        for order in orders:
            if self.remove_order(order.order_id):
                ids.append(order.order_id)
        return ids

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
        ob.asks = self.asks.peek_depth(depth)
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
        """ 更新订单
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
