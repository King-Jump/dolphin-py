""" 基于跳表和数组的订单薄算法
    1. 近盘使用一维排序数组，数组规模为N
    2. 远盘使用基于多维数组的链表+跳表
    3. 使用HashMap存储订单详情
"""
import time
import random
import threading
import logging
from typing import Tuple, List, Optional, Dict

from src.engine.types.types import Order, OrderSide, OrderBook as OrderBookModel
from src.engine.orderbook.ob_interface import OrderBookInterface

MAX_NEAR_SIZE = 1_000

def compare(a: Tuple[str, float, int], b: Order) -> int:
    """ compare two orders, first by price, second by timestamp
    """
    if a[0] == b.order_id:
        return 0

    if a[1] == b.price:
        if a[2] < b.timestamp:
            return -1
        elif a[2] > b.timestamp:
            return 1
        else:
            if a[0] < b.order_id:
                return -1
            else: # a[0] > b.order_id:
                return 1
    elif a[1] > b.price:
        return 1
    else: # a.price < b.price
        return -1

def compare_order(a: Order, b: Order) -> int:
    """ compare two orders, first by price, second by timestamp
    """
    if a.order_id == b.order_id:
        return 0

    if a.price == b.price:
        if a.timestamp < b.timestamp:
            return -1
        elif a.timestamp > b.timestamp:
            return 1
        else:
            if a.order_id < b.order_id:
                return -1
            #elif a.order_id > b.order_id:
            return 1
    elif a.price > b.price:
        return 1
    else: # a.price < b.price
        return -1


class SortedBaseArray:
    def __init__(self, max_size=1_000, logger=None):
        self.logger = logger
        self._values = [0] * max_size
        self._capacity = 0
        self.max_size = max_size

        # If capacity is less than MIN_CAPACITY_RATIO * max_size, then move far-end orders in the array
        self.MIN_CAPACITY_RATIO = 0.75
        self.MOVE_IN_RATIO = 0.95

    def size(self) -> int:
        return self._capacity

    def move_in_num(self) -> int:
        if self._capacity < self.MIN_CAPACITY_RATIO * self.max_size:
            return 0
        return int((self.MOVE_IN_RATIO - self.MIN_CAPACITY_RATIO) * self.max_size)

    def is_full(self) -> bool:
        return self._capacity >= self.max_size

    def is_empty(self) -> bool:
        return self._capacity == 0

    def peek(self) -> Optional[str]:
        """ peek the first order in the array
        """
        if self._capacity == 0:
            return None
        return self._values[0][0] # order id, price, timestamp

    def peek_depth(self, depth: int, order_info: Dict[str, Order]) -> List[Tuple[float, float]]:
        """ peek the first depth orders in the array
        """
        if self._capacity == 0:
            return []

        level = 0
        depth = []
        oid, price, _ = self._values[0]
        curr_price, curr_qty = price, order_info[oid].quantity - order_info[oid].filled_quantity
        for i in range(1, self._capacity):
            oid, price, _ = self._values[i]
            if price != curr_price:
                depth.append((curr_price, curr_qty))
                level += 1
                if level > len(depth):
                    break
                curr_price, curr_qty = price, order_info[oid].quantity - order_info[oid].filled_quantity
            curr_qty += order_info[oid].quantity - order_info[oid].filled_quantity

        if level <= len(depth):
            depth.append((curr_price, curr_qty))
        return depth


class SortedAskArray(SortedBaseArray):
    """ Sorted array for ask orders, in ascending order
    """
    def __init__(self, max_size=1_000, logger=None):
        super().__init__(max_size, logger)

    def _bisearch(self, order: Order) -> Tuple[int, int]:
        """ binary search and return the offset and condition, in ascending order
            Assert: _values is not empty and not full, order < _values[-1]
        """
        start, end = 0, self._capacity - 1
        while start <= end:
            mid = int((start + end) * 0.5)
            condition = compare(self._values[mid], order)
            if condition < 0:
                # mid < order
                start = mid + 1
            elif condition > 0:
                # mid > order
                end = mid - 1
            else: # condition == 0
                self.logger.error("%s is already in the near-end array", order.order_id)
                return -1, 0

        return mid, condition

    def insert(self, order: Order) -> bool:
        """ binary search and insert order, assert the array is not full
        """
        if self.is_full():
            return False

        if self._capacity == 0: # empty array
            self._values[0] = (order.order_id,order.price, order.timestamp)
            self._capacity += 1
            return True

        if compare(self._values[self._capacity-1], order) < 0:
            # append new order
            self._values[self._capacity] = (order.order_id,order.price, order.timestamp)
            self._capacity += 1
            return True

        offset, condition = self._bisearch(order)
        if offset == -1:
            return False

        if condition < 0:
            # insert after offset, move array
            for i in range(self._capacity, offset+1, -1):
                self._values[i] = self._values[i-1]
            self._values[offset+1] = (order.order_id, order.price, order.timestamp)
        else: # condition > 0
            # insert before offset, move array
            for i in range(self._capacity, offset, -1):
                self._values[i] = self._values[i-1]
            self._values[offset] = (order.order_id, order.price, order.timestamp)

        self._capacity += 1
        return True

    def delete(self, order: Order) -> bool:
        """ delete order from the array
        """
        if self._capacity == 0: # empty array
            return False

        start, end = 0, self._capacity - 1
        while start <= end:
            mid = int((start + end) * 0.5)
            condition = compare(self._values[mid], order)
            if condition < 0:
                # mid < order
                start = mid + 1
            elif condition > 0:
                # mid > order
                end = mid - 1
            else: # condition == 0
                # found and delte
                for idx in range(mid, self._capacity - 1):
                    self._values[idx] = self._values[idx+1]
                self._capacity -= 1
                return True
        return False

    def batch_insert(self, orders: List[Order]) -> Tuple[bool, List[str], List[Order]]:
        """ batch insert orders by merge sort
            return success or fail, orders to move out to far-end array, sub-orders not inserted
        """
        if self._capacity == 0:
            sorted_orders = sorted(orders, key=lambda x: (x.price, x.timestamp))
            if len(sorted_orders) > self.max_size:
                self._values = [(order.order_id, order.price, order.timestamp) for order in sorted_orders[:self.max_size]]
                self._capacity = self.max_size
                return True, [], sorted_orders[self.max_size:]
            else:
                for idx, order in enumerate(sorted_orders):
                    self._values[idx] = (order.order_id, order.price, order.timestamp)
                self._capacity = len(sorted_orders)
                return True, [], []

        if len(orders) + self._capacity > self.max_size:
            # create a new near-end array, since near-end array is not enough
            new_values = [0] * self.max_size
            sorted_orders = sorted(orders, key=lambda x: (x.price, x.timestamp))
            write_idx = 0
            read_idx = 0
            far_end_orders = [] # order_id list
            sub_orders = [] # orders not inserted to new-end array
            for order in sorted_orders:
                if write_idx >= self.max_size:
                    # new_values is full
                    sub_orders.append(order)
                    continue
                while read_idx < self._capacity:
                    condition = compare(self._values[read_idx], order)
                    if condition < 0:
                        # insert order at read_idx
                        new_values[write_idx] = self._values[read_idx]
                        read_idx += 1
                        write_idx += 1
                    else: # condition > 0
                        # insert order
                        new_values[write_idx] = (order.order_id, order.price, order.timestamp)
                        write_idx += 1
                        break
                if read_idx >= self._capacity:
                    new_values[write_idx] = (order.order_id, order.price, order.timestamp)
                    write_idx += 1

            for idx in range(read_idx, self._capacity):
                far_end_orders.append(self._values[idx][0])

            self._values = new_values
            self._capacity = write_idx
            return True, far_end_orders, sub_orders
        else:
            # insert all orders to new-end array, first sort orders in descending order
            reverse_sorted_orders = sorted(orders, key=lambda x: (x.price, x.timestamp), reverse=True)
            write_idx = self._capacity - 1 + len(reverse_sorted_orders)
            read_idx = self._capacity - 1
            for order in reverse_sorted_orders:
                while read_idx >= 0:
                    condition = compare(self._values[read_idx], order)
                    if condition < 0:
                        # append order
                        self._values[write_idx] = (order.order_id, order.price, order.timestamp)
                        write_idx -= 1
                        break
                    # else: condition > 0
                    # append read idx
                    self._values[write_idx] = self._values[read_idx]
                    write_idx -= 1
                    read_idx -= 1

                if read_idx < 0:
                    self._values[write_idx] = (order.order_id, order.price, order.timestamp)
                    write_idx -= 1
            self._capacity += len(reverse_sorted_orders)
            return True, [], []

    def batch_delete(self, orders: List[Order]) -> List[str]:
        """ batch delete orders from the array
            return deleted order ids
        """
        deleted_orders = []
        if self._capacity == 0:
            return deleted_orders

        sorted_orders = sorted(orders, key=lambda x: (x.price, x.timestamp))
        read_idx = 0
        write_idx = 0
        for order in sorted_orders:
            while read_idx < self._capacity:
                condition = compare(self._values[read_idx], order)
                if condition < 0:
                    # skip read_idx, move write_idx to next position
                    if read_idx > write_idx:
                        # move read_idx to write_idx
                        self._values[write_idx] = self._values[read_idx]
                    read_idx += 1
                    write_idx += 1
                elif condition > 0:
                    # skip order
                    break
                else: # condition == 0
                    # delete order
                    deleted_orders.append(order.order_id)
                    read_idx += 1
                    break
            if read_idx >= self._capacity:
                break

        for i in range(read_idx, self._capacity):
            self._values[write_idx] = self._values[i]
            write_idx += 1

        self._capacity -= len(deleted_orders)
        return deleted_orders


class SortedBidArray(SortedBaseArray):
    """ Sorted array for bid orders, in descending order
    """
    def __init__(self, max_size=1_000, logger=None):
        super().__init__(max_size, logger)

    def _bisearch(self, order: Order) -> Tuple[int, int]:
        """ binary search the position to insert order, in descending order
            Assert _values is not full and is not empty, and _valuse[-1] < order
        """
        start, end = 0, self._capacity - 1
        while start <= end:
            mid = int((start + end) * 0.5)
            condition = compare(self._values[mid], order)
            if condition > 0:
                # mid > order
                start = mid + 1
            elif condition < 0:
                # mid < order
                end = mid - 1
            else: # condition == 0
                self.logger.error("%s is already in the near-end array", order.order_id)
                return -1, 0

        return mid, condition

    def insert(self, order: Order) -> bool:
        """ binary search and insert order, assert the array is not full
        """
        if self.is_full():
            return False

        if self._capacity == 0: # empty array
            self._values[0] = (order.order_id,order.price, order.timestamp)
            self._capacity += 1
            return True

        if compare(self._values[self._capacity-1], order) > 0:
            # append new order
            self._values[self._capacity] = (order.order_id,order.price, order.timestamp)
            self._capacity += 1
            return True

        offset, condition = self._bisearch(order)
        if offset == -1:
            return False

        if condition < 0:
            # insert at offset, move array
            for i in range(self._capacity, offset, -1):
                self._values[i] = self._values[i-1]
            self._values[offset] = (order.order_id, order.price, order.timestamp)
        else: # condition > 0
            # insert after offset, move array
            for i in range(self._capacity, offset+1, -1):
                self._values[i] = self._values[i-1]
            self._values[offset+1] = (order.order_id, order.price, order.timestamp)

        self._capacity += 1
        return True

    def delete(self, order: Order) -> bool:
        """ delete order from the array
        """
        if self._capacity == 0: # empty array
            return False

        start, end = 0, self._capacity - 1
        while start <= end:
            mid = int((start + end) * 0.5)
            condition = compare(self._values[mid], order)
            if condition > 0:
                # mid < order
                start = mid + 1
            elif condition < 0:
                # mid > order
                end = mid - 1
            else: # condition == 0
                # found and delte
                for idx in range(mid, self._capacity - 1):
                    self._values[idx] = self._values[idx+1]
                self._capacity -= 1
                return True
        return False

    def batch_insert(self, orders: List[Order]) -> Tuple[bool, List[str], List[Order]]:
        """ batch insert orders by merge sort
            return success or fail, orders to move out to far-end array, sub-orders not inserted to new-end array
        """
        if self._capacity == 0:
            sorted_orders = sorted(orders, key=lambda x: (x.price, x.timestamp), reverse=True)
            if len(sorted_orders) > self.max_size:
                self._values = [(order.order_id, order.price, order.timestamp) for order in sorted_orders[:self.max_size]]
                self._capacity = self.max_size
                return True, [], sorted_orders[self.max_size:]
            # else
            for idx, order in enumerate(sorted_orders):
                self._values[idx] = (order.order_id, order.price, order.timestamp)
            self._capacity = len(sorted_orders)
            return True, [], []

        if len(orders) + self._capacity > self.max_size:
            # create a new near-end array, since near-end array is not enough
            new_values = [0] * self.max_size
            sorted_orders = sorted(orders, key=lambda x: (x.price, x.timestamp), reverse=True)
            write_idx = 0
            read_idx = 0
            far_end_orders = [] # order_id list
            sub_orders = [] # orders not inserted to new-end array
            for order in sorted_orders:
                if write_idx >= self.max_size:
                    # new_values is full
                    sub_orders.append(order)
                    continue
                while read_idx < self._capacity:
                    condition = compare(self._values[read_idx], order)
                    if condition > 0:
                        # insert order at read_idx
                        new_values[write_idx] = self._values[read_idx]
                        read_idx += 1
                        write_idx += 1
                    else: # condition < 0
                        # insert order
                        new_values[write_idx] = (order.order_id, order.price, order.timestamp)
                        write_idx += 1
                        break
                if read_idx >= self._capacity:
                    new_values[write_idx] = (order.order_id, order.price, order.timestamp)
                    write_idx += 1

            for idx in range(read_idx, self._capacity):
                far_end_orders.append(self._values[idx][0])

            self._values = new_values
            self._capacity = write_idx
            return True, far_end_orders, sub_orders
        else:
            # insert all orders to new-end array, first sort orders in descending order
            reverse_sorted_orders = sorted(orders, key=lambda x: (x.price, x.timestamp), reverse=True)
            write_idx = self._capacity - 1 + len(reverse_sorted_orders)
            read_idx = self._capacity - 1
            for order in reverse_sorted_orders:
                while read_idx >= 0:
                    condition = compare(self._values[read_idx], order)
                    if condition > 0:
                        # append read idx
                        self._values[write_idx] = self._values[read_idx]
                        write_idx -= 1
                        read_idx -= 1
                    else: # condition < 0
                        # append order
                        self._values[write_idx] = (order.order_id, order.price, order.timestamp)
                        write_idx -= 1
                        break

                if read_idx < 0:
                    self._values[write_idx] = (order.order_id, order.price, order.timestamp)
                    write_idx -= 1
            self._capacity += len(reverse_sorted_orders)
            return True, [], []

    def batch_delete(self, orders: List[Order]) -> List[str]:
        """ batch delete orders from the array
            return deleted order ids
        """
        deleted_orders = []
        if self._capacity == 0:
            return deleted_orders

        sorted_orders = sorted(orders, key=lambda x: (x.price, x.timestamp), reverse=True)
        read_idx = 0
        write_idx = 0
        for order in sorted_orders:
            while read_idx < self._capacity:
                condition = compare(self._values[read_idx], order)
                if condition > 0:
                    # skip read_idx, move write_idx to next position
                    if read_idx > write_idx:
                        # move read_idx to write_idx
                        self._values[write_idx] = self._values[read_idx]
                    read_idx += 1
                    write_idx += 1
                elif condition < 0:
                    # skip order
                    break
                else: # condition == 0
                    # delete order
                    deleted_orders.append(order.order_id)
                    read_idx += 1
                    break
            if read_idx >= self._capacity:
                break

        for i in range(read_idx, self._capacity):
            self._values[write_idx] = self._values[i]
            write_idx += 1

        self._capacity -= len(deleted_orders)
        return deleted_orders


class SkipNode:
    def __init__(self, order: Order, level: int, index: int = 0):
        self.order = order
        self.forward = [None] * level  # 指向各层下一个节点的指针列表
        # forward[0] 指向底层下一个节点，forward[1] 指向第1层下一个节点...
        self.index = index  # index in free_nodes list

class SkipList:
    def __init__(self, max_level=16, pN=4, max_nodes=100_000):
        self.max_level = max_level     # 最大层数限制（防止无限增长）
        self.pN = pN                     # 向上提升的概率1/pN（通常0.5或0.25）
        self.head = SkipNode(None, max_level)  # 头节点，贯穿所有层
        self.level = 1                 # 当前跳表的有效最大层数（从1开始）

        self.capacity = 0   # number of nodes
        self.max_node_size = max_nodes  # max number of nodes
        self.free_nodes = [SkipNode(None, max_level, i) for i in range(self.max_node_size)]  # list of free nodes
        self.free_nodes_ptr = list(range(1, self.max_node_size+1))
        self.free_ptr_head = 0

    def size(self) -> int:
        return self.capacity

    def _new_node(self, order: Order, level: int):
        if self.capacity >= self.max_node_size:
            self.free_nodes.extend([SkipNode(None, self.max_level, i+self.capacity) for i in range(self.max_node_size)])
            self.free_nodes_ptr.extend(range(self.max_node_size+1, self.max_node_size*2+1))
            self.max_node_size *= 2

        # allocate a new node from free node list
        node = self.free_nodes[self.free_ptr_head]
        node.order = order
        node.forward = [None] * level

        # remove the node from free node list
        self.free_ptr_head = self.free_nodes_ptr[self.free_ptr_head]
        self.capacity += 1
        return node

    def _free_node(self, node: SkipNode):
        # add the node to free node list
        node.order = None
        self.free_nodes_ptr[node.index] = self.free_ptr_head
        self.free_ptr_head = node.index
        self.capacity -= 1

    def _random_level(self):
        """随机生成新节点的层数（1 到 max_level 之间）"""
        lvl = 1
        # 每次以概率1/pN 增加一层，直到达到上限
        for _ in range(self.max_level-1):
            if random.randint(1, 100) % self.pN == 0:
                lvl += 1
        return lvl

    def _clear(self, target: SkipNode, update: List[SkipNode]):
        """ clear the target node from skip list
        """
        for lvl in range(len(target.forward)):
            update[lvl].forward[lvl] = target.forward[lvl]

        # 调整跳表的当前有效最大层数：若顶层已空，则降低 level
        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        self._free_node(target)

    def insert(self, order: Order) -> bool:
        """ insert the order into skip list
        """
        return False

    def delete(self, order: Order) -> bool:
        """ delete the order from skip list
        """
        return False

    def batch_insert(self, orders):
        for order in orders:
            self.insert(order)

    def batch_delete(self, orders):
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
        depth = []
        current = self.head.forward[0]
        curr_price, curr_qty = current.order.price, current.order.quantity - current.order.filled_quantity
        while current.forward[0]:
            current = current.forward[0]
            price, qty = current.order.price, current.order.quantity - current.order.filled_quantity
            if price != curr_price:
                depth.append((curr_price, curr_qty))
                level += 1
                if level > len(depth):
                    break

                curr_price = price
                curr_qty = qty
            else:
                curr_qty += qty
        if level <= len(depth):
            depth.append((curr_price, curr_qty))
        return depth

class AskSkipList(SkipList):
    def __init__(self, max_level=16, pN=4, max_nodes=100_000):
        super().__init__(max_level, pN, max_nodes)

    def search(self, order: Order) -> Optional[Order]:
        """查找指定键，返回值，不存在则返回 None"""
        current = self.head
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and compare_order(current.forward[lvl].order, order) < 0:
                current = current.forward[lvl]
        # 到达底层，current 指向最后一个键 < key 的节点
        candidate = current.forward[0]
        if candidate and candidate.order.order_id == order.order_id:
            return candidate.order
        return None

    def insert(self, order: Order) -> bool:
        """插入键值对，若键已存在则更新值"""
        # update 数组用于记录每一层插入位置的前驱节点
        update = [None] * self.max_level
        current = self.head

        # 从最高层开始查找，记录每一层的前驱
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and compare_order(current.forward[lvl].order, order) < 0:
                current = current.forward[lvl]
            update[lvl] = current

        # 检查键是否已存在（底层下一个节点）
        candidate = current.forward[0]
        if candidate and candidate.order.order_id == order.order_id:
            candidate.order = order
            return False

        # 生成新节点的层数
        new_level = self._random_level()
        # 如果新节点的层数超过当前跳表的最高层，需要将多出的层的前驱指向头节点
        if new_level > self.level:
            for lvl in range(self.level, new_level):
                update[lvl] = self.head
            self.level = new_level

        new_node = self._new_node(order, new_level)

        # 将新节点插入到各层链表中
        for lvl in range(new_level):
            new_node.forward[lvl] = update[lvl].forward[lvl]
            update[lvl].forward[lvl] = new_node

        return True

    def delete(self, order: Order) -> bool:
        """删除指定键, 返回 True 表示成功, False 表示键不存在"""
        update = [None] * self.max_level
        current = self.head

        # 查找并记录各层前驱
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and compare_order(current.forward[lvl].order, order) < 0:
                current = current.forward[lvl]
            update[lvl] = current

        target = current.forward[0]
        if not target or target.order.order_id != order.order_id:
            return False

        self._clear(target, update)

        return True


class BidSkipList(SkipList):
    def __init__(self, max_level=16, pN=4, max_nodes=100_000):
        super().__init__(max_level, pN, max_nodes)

    def search(self, order: Order) -> Optional[Order]:
        """查找指定键，返回值，不存在则返回 None"""
        current = self.head
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and compare_order(current.forward[lvl].order, order) > 0:
                current = current.forward[lvl]
        # 到达底层，current 指向最后一个键 < key 的节点
        candidate = current.forward[0]
        if candidate and candidate.order.order_id == order.order_id:
            return candidate.order
        return None

    def insert(self, order: Order) -> bool:
        """插入键值对，若键已存在则更新值"""
        # update 数组用于记录每一层插入位置的前驱节点
        update = [None] * self.max_level
        current = self.head

        # 从最高层开始查找，记录每一层的前驱
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and compare_order(current.forward[lvl].order, order) > 0:
                current = current.forward[lvl]
            update[lvl] = current

        # 检查键是否已存在（底层下一个节点）
        candidate = current.forward[0]
        if candidate and candidate.order.order_id == order.order_id:
            candidate.order = order
            return False

        # 生成新节点的层数
        new_level = self._random_level()
        # 如果新节点的层数超过当前跳表的最高层，需要将多出的层的前驱指向头节点
        if new_level > self.level:
            for lvl in range(self.level, new_level):
                update[lvl] = self.head
            self.level = new_level

        new_node = self._new_node(order, new_level)

        # 将新节点插入到各层链表中
        for lvl in range(new_level):
            new_node.forward[lvl] = update[lvl].forward[lvl]
            update[lvl].forward[lvl] = new_node

        return True

    def delete(self, order: Order) -> bool:
        """删除指定键，返回 True 表示成功，False 表示键不存在"""
        update = [None] * self.max_level
        current = self.head

        # 查找并记录各层前驱
        for lvl in range(self.level - 1, -1, -1):
            while current.forward[lvl] and compare_order(current.forward[lvl].order, order) > 0:
                current = current.forward[lvl]
            update[lvl] = current

        target = current.forward[0]
        if not target or target.order.order_id != order.order_id:
            return False

        self._clear(target, update)

        return True


class OrderBook(OrderBookInterface):
    """
    基于双向队列和跳表的订单簿
    
    使用四个链表分别管理买单和卖单：
    - BidNearList: 近盘买单，按价格降序排列，使用数组存储，数量少但更新频繁
    - BidFarList: 远盘卖单，按价格降序排列，使用循环队列存储，数量多但更新频率低
    - AskNearList: 近盘卖单，按价格升序排列，使用数组存储，数量少且更新频繁
    - AskFarList: 远盘卖单，按价格升序排列，使用循环队列存储，数量多且更新频率低
    
    特点：
    - 近盘订单数量N，远盘订单数量n
    - 插入操作成本
        - 近盘O(N)，遍历搜索
        - 远盘O(log n)，借助跳表搜索
    - 删除成本
        - 近盘O(N)
        - 远盘O(1)
    """

    def __init__(self, symbol="BTCUSDT", max_nodes=100_000, logger=None):
        self.symbol = symbol
        self.near_bids = SortedBidArray(MAX_NEAR_SIZE, logger)
        self.far_bids = BidSkipList(max_level=16, pN=4, max_nodes=max_nodes)
        self.near_asks = SortedAskArray(MAX_NEAR_SIZE, logger)
        self.far_asks = AskSkipList(max_level=16, pN=4, max_nodes=max_nodes)
        self.orders = {}
        self.ask_lock = threading.RLock()
        self.bid_lock = threading.RLock()
        self.logger = logger or logging.getLogger(__name__)

    def add_order(self, order):
        """添加订单到订单簿"""
        self.orders[order.order_id] = order

        if order.side == OrderSide.BUY:
            with self.bid_lock:
                if self.near_bids.is_full():
                    self.far_bids.insert(order)
                else:
                    self.near_bids.insert(order)
        else:
            with self.ask_lock:
                if self.near_asks.is_full():
                    self.far_asks.insert(order)
                else:
                    self.near_asks.insert(order)

    def remove_order(self, order_id):
        """从订单簿移除订单"""
        order = self.orders.get(order_id)
        if not order:
            self.logger.error(f"[remove order] cannot find order {order_id}")
            return None

        result = False
        if order.side == OrderSide.BUY:
            with self.bid_lock:
                if self.far_bids.size() == 0 or compare_order(order, self.far_bids.peek()) > 0:
                    # order > first bid in far-end orders
                    result = self.near_bids.delete(order)
                    move_in_num = self.near_bids.move_in_num()
                    move_in_orders = []
                    for _ in range(move_in_num):
                        order = self.far_bids.pop()
                        if not order:
                            break
                        move_in_orders.append(order)
                    self.near_bids.batch_insert(move_in_orders)
                else:
                    result = self.far_bids.delete(order)
        else:
            with self.ask_lock:
                if self.far_asks.size() == 0 or compare_order(order, self.far_asks.peek()) < 0:
                    # order < first ask in far-end orders
                    result = self.near_asks.delete(order)
                    move_in_num = self.near_asks.move_in_num()
                    move_in_orders = []
                    for _ in range(move_in_num):
                        order = self.far_asks.pop()
                        if not order:
                            break
                        move_in_orders.append(order)
                    self.near_asks.batch_insert(move_in_orders)
                else:
                    result = self.far_asks.delete(order)

        if result:
            del self.orders[order_id]
            return order

        self.logger.error(f"[remove order] cannot find order {order_id}")
        return None

    def batch_add_orders(self, side: str, orders: List[Order]):
        """批量添加订单"""
        if side == OrderSide.BUY:
            with self.bid_lock:
                result, move_out_ids, remain_orders = self.near_bids.batch_insert(orders)
                if result:
                    # batch insert success
                    for order in orders:
                        if order.order_id in remain_orders:
                            continue
                        self.orders[order.order_id] = order
                    if move_out_ids:
                        remain_orders.extend([self.orders[oid] for oid in move_out_ids])
                    if remain_orders:
                        self.far_bids.batch_insert(remain_orders)
        else:
            with self.ask_lock:
                result, move_out_ids, remain_orders = self.near_asks.batch_insert(orders)
                if result:
                    # batch insert success
                    for order in orders:
                        if order.order_id in remain_orders:
                            continue
                        self.orders[order.order_id] = order
                    if move_out_ids:
                        remain_orders.extend([self.orders[oid] for oid in move_out_ids])
                    if remain_orders:
                        self.far_asks.batch_insert(remain_orders)

    def batch_remove_orders(self, order_ids: List[str]) -> List[str]:
        """批量移除订单"""
        cancel_buy_orders = []
        cancel_sell_orders = []
        for order_id in order_ids:
            order = self.orders.get(order_id)
            if not order:
                continue
            if order.side == OrderSide.BUY:
                cancel_buy_orders.append(order)
            else:
                cancel_sell_orders.append(order)

        total_removed_orders = []
        if cancel_buy_orders:
            with self.bid_lock:
                removed_ids = self.near_bids.batch_delete(cancel_buy_orders)
                total_removed_orders.extend([order for order in cancel_buy_orders if order.order_id in removed_ids])
                for order_id in removed_ids:
                    del self.orders[order_id]
                remained_ids = [oid for oid in order_ids if oid not in removed_ids]
                if remained_ids:
                    far_removed_ids = self.far_bids.batch_delete([self.orders[oid] for oid in remained_ids])
                    total_removed_orders.extend([order for order in far_removed_orders if order.order_id in far_removed_ids])
                    for order_id in far_removed_ids:
                        del self.orders[order_id]

        if cancel_sell_orders:
            with self.ask_lock:
                removed_ids = self.near_asks.batch_delete(cancel_sell_orders)
                total_removed_orders.extend([order for order in cancel_sell_orders if order.order_id in removed_ids])
                for order_id in removed_ids:
                    del self.orders[order_id]
                remained_ids = [oid for oid in order_ids if oid not in removed_ids]
                if remained_ids:
                    far_removed_ids = self.far_asks.batch_delete([self.orders[oid] for oid in remained_ids])
                    total_removed_orders.extend([order for order in far_removed_orders if order.order_id in far_removed_ids])
                    for order_id in far_removed_ids:
                        del self.orders[order_id]

        return total_removed_orders

    def get_order(self, order_id: str) -> Optional[Order]:
        """ 获取指定订单
        """
        return self.orders.get(order_id)

    def get_order_book(self, depth=30) -> OrderBookModel:
        """获取订单簿数据"""
        order_book = OrderBookModel(self.symbol)
        with self.ask_lock:
            asks = self.near_asks.peek_depth(depth, self.orders)
            if len(asks) >= depth:
                if self.far_asks.peek() == asks[-1][0]:
                    far_asks = self.far_asks.peek_depth(1)
                    asks[-1][1] += far_asks[0][1]
            else:
                far_asks = self.far_asks.peek_depth(depth - len(asks) + 1)
                if far_asks and far_asks[0][0] == asks[-1][0]:
                    asks[-1][1] += far_asks[0][1]
                    asks.extend(far_asks[1:])
            order_book.asks = asks
        with self.bid_lock:
            bids = self.near_bids.peek_depth(depth, self.orders)
            if len(bids) >= depth:
                if self.far_bids.peek() == bids[-1][0]:
                    far_bids = self.far_bids.peek_depth(1)
                    bids[-1][1] += far_bids[0][1]
            else:
                far_bids = self.far_bids.peek_depth(depth - len(bids) + 1)
                if far_bids and far_bids[0][0] == bids[-1][0]:
                    bids[-1][1] += far_bids[0][1]
                    bids.extend(far_bids[1:])
            order_book.bids = bids

        order_book.timestamp = int(time.time() * 1000)
        return order_book

    def get_best_bid(self) -> Optional[Order]:
        """ 获取最佳买单价格
        """
        with self.bid_lock:
            if not self.near_bids.is_empty():
                oid = self.near_bids.peek()
                return self.orders[oid]

            return self.far_bids.peek()

    def get_best_ask(self) -> Optional[Order]:
        """获取最佳卖价"""
        with self.ask_lock:
            if not self.near_asks.is_empty():
                oid = self.near_asks.peek()
                return self.orders[oid]

            return self.far_asks.peek()

    def update_order(self, order_id, filled_quantity):
        """更新订单成交数量"""
        order = self.orders.get(order_id)
        if not order:
            return None

        order.filled_quantity = filled_quantity
        if order.filled_quantity >= order.quantity:
            self.remove_order(order_id)
        return order

    def pending_orders(self, uid):
        """获取用户所有待处理订单"""
        return [order for order in self.orders.values() if order.uid == uid]