import time
from src.engine.types.types import Order, OrderSide, OrderStatus, OrderLevel, OrderBook as OrderBookModel
import threading


class RBNode:
    """
    红黑树节点类
    
    红黑树是一种自平衡的二叉搜索树，每个节点都有一个颜色属性（红色或黑色）。
    通过颜色属性和特定的旋转操作，树能够在插入和删除操作后保持近似平衡，
    从而保证各种操作的时间复杂度为 O(log n)。
    
    属性:
        RED: 红色节点标识
        BLACK: 黑色节点标识
        key: 节点的键值（用于排序）
        value: 节点存储的值（订单对象）
        color: 节点的颜色
        left: 左子节点指针
        right: 右子节点指针
        parent: 父节点指针
    """
    RED = True
    BLACK = False

    def __init__(self, key, value, color=RED):
        self.key = key
        self.value = value
        self.color = color
        self.left = None
        self.right = None
        self.parent = None


class RedBlackTree:
    """
    红黑树实现类
    
    红黑树是一种自平衡二叉搜索树，具有以下性质：
    
    1. 每个节点非红即黑
    2. 根节点是黑色
    3. 所有叶子节点（NIL节点）是黑色
    4. 如果一个节点是红色，则它的两个子节点都是黑色（不能有两个连续的红色节点）
    5. 从任一节点到其每个叶子的所有路径都包含相同数量的黑色节点
    
    这些性质保证了红黑树的高度最多是 2*log2(n+1)，因此各种操作的时间复杂度为 O(log n)。
    
    在订单簿应用中的优势:
    - 插入订单: O(log n)
    - 删除订单: O(log n)
    - 查找订单: O(log n)
    - 按价格排序遍历: O(n)，但天然有序
    - 获取最优价格: O(1)（最小值节点）
    
    旋转操作:
    - 左旋: 将右子节点提升为父节点，原父节点降为左子节点
    - 右旋: 将左子节点提升为父节点，原父节点降为右子节点
    旋转操作是红黑树保持平衡的核心手段，不影响二叉搜索树的性质。
    
    插入修复:
    当插入新节点时，可能违反红黑树性质（主要是连续红色节点）。
    通过以下情况处理：
    - Case 1: 叔父节点是红色 -> 变色
    - Case 2: 叔父节点是黑色，且当前节点是右子 -> 左旋
    - Case 3: 叔父节点是黑色，且当前节点是左子 -> 右旋 + 变色
    
    删除修复:
    删除黑色节点可能破坏路径黑色节点数量一致的性质，
    通过旋转和变色操作修复。
    """
    
    def __init__(self, reverse=False):
        # NIL节点是哨兵节点，用于简化边界条件处理
        # 所有空位置都指向NIL，NIL节点颜色为黑色
        self.NIL = RBNode(None, None, RBNode.BLACK)
        self.NIL.left = self.NIL
        self.NIL.right = self.NIL
        self.root = self.NIL
        self.reverse = reverse  # 是否反转排序顺序（用于买单降序/卖单升序）

    def _compare(self, key1, key2):
        """
        比较两个键的大小
        
        参数:
            key1: 第一个键
            key2: 第二个键
        
        返回:
            负数表示 key1 < key2
            0 表示 key1 == key2
            正数表示 key1 > key2
        """
        if self.reverse:
            return key2 - key1 if isinstance(key1, (int, float)) and isinstance(key2, (int, float)) else (key2 > key1) - (key1 > key2)
        return key1 - key2 if isinstance(key1, (int, float)) and isinstance(key2, (int, float)) else (key1 > key2) - (key1 < key2)

    def _rotate_left(self, x):
        """
        左旋操作
        
        对节点 x 进行左旋，使其右子节点 y 替代 x 的位置，
        x 成为 y 的左子节点，y 的左子节点成为 x 的右子节点。
        
        左旋示意图:
              x               y
             / \             / \
            A   y    ==>    x   C
               / \         / \
              B   C       A   B
        """
        y = x.right
        x.right = y.left
        if y.left != self.NIL:
            y.left.parent = x
        y.parent = x.parent
        if x.parent == self.NIL:
            self.root = y
        elif x == x.parent.left:
            x.parent.left = y
        else:
            x.parent.right = y
        y.left = x
        x.parent = y

    def _rotate_right(self, x):
        """
        右旋操作
        
        对节点 x 进行右旋，使其左子节点 y 替代 x 的位置，
        x 成为 y 的右子节点，y 的右子节点成为 x 的左子节点。
        
        右旋示意图:
              x               y
             / \             / \
            y   C    ==>    A   x
           / \                 / \
          A   B               B   C
        """
        y = x.left
        x.left = y.right
        if y.right != self.NIL:
            y.right.parent = x
        y.parent = x.parent
        if x.parent == self.NIL:
            self.root = y
        elif x == x.parent.right:
            x.parent.right = y
        else:
            x.parent.left = y
        y.right = x
        x.parent = y

    def _insert_fixup(self, node):
        """
        插入修复操作
        
        插入新节点后，可能违反红黑树性质：
        - 性质4: 红色节点的子节点必须是黑色
        
        处理三种情况：
        1. 叔父节点是红色：变色（父节点、叔父节点变黑，祖父节点变红）
        2. 叔父节点是黑色，当前节点是右子：左旋转变为情况3
        3. 叔父节点是黑色，当前节点是左子：右旋 + 变色
        """
        while node.parent.color == RBNode.RED:
            if node.parent == node.parent.parent.left:
                uncle = node.parent.parent.right
                if uncle.color == RBNode.RED:
                    node.parent.color = RBNode.BLACK
                    uncle.color = RBNode.BLACK
                    node.parent.parent.color = RBNode.RED
                    node = node.parent.parent
                else:
                    if node == node.parent.right:
                        node = node.parent
                        self._rotate_left(node)
                    node.parent.color = RBNode.BLACK
                    node.parent.parent.color = RBNode.RED
                    self._rotate_right(node.parent.parent)
            else:
                uncle = node.parent.parent.left
                if uncle.color == RBNode.RED:
                    node.parent.color = RBNode.BLACK
                    uncle.color = RBNode.BLACK
                    node.parent.parent.color = RBNode.RED
                    node = node.parent.parent
                else:
                    if node == node.parent.left:
                        node = node.parent
                        self._rotate_right(node)
                    node.parent.color = RBNode.BLACK
                    node.parent.parent.color = RBNode.RED
                    self._rotate_left(node.parent.parent)
        self.root.color = RBNode.BLACK

    def insert(self, key, value):
        """
        插入节点
        
        步骤：
        1. 按照二叉搜索树的规则找到插入位置
        2. 创建新节点（默认红色）
        3. 调用插入修复操作恢复红黑树性质
        
        参数:
            key: 节点的键
            value: 节点的值
        """
        node = RBNode(key, value)
        node.left = self.NIL
        node.right = self.NIL

        parent = self.NIL
        current = self.root

        while current != self.NIL:
            parent = current
            if self._compare(node.key, current.key) < 0:
                current = current.left
            else:
                current = current.right

        node.parent = parent
        if parent == self.NIL:
            self.root = node
        elif self._compare(node.key, parent.key) < 0:
            parent.left = node
        else:
            parent.right = node

        self._insert_fixup(node)

    def _delete_fixup(self, node):
        """
        删除修复操作
        
        删除黑色节点可能破坏性质5（路径黑色节点数量一致）。
        
        处理四种情况：
        1. 兄弟节点是红色 -> 变色 + 旋转，转变为其他情况
        2. 兄弟节点是黑色，两个侄子都是黑色 -> 兄弟变红，向上处理
        3. 兄弟节点是黑色，左侄子红色，右侄子黑色 -> 旋转 + 变色
        4. 兄弟节点是黑色，右侄子红色 -> 旋转 + 变色
        """
        while node != self.root and node.color == RBNode.BLACK:
            if node == node.parent.left:
                sibling = node.parent.right
                if sibling.color == RBNode.RED:
                    sibling.color = RBNode.BLACK
                    node.parent.color = RBNode.RED
                    self._rotate_left(node.parent)
                    sibling = node.parent.right
                if sibling.left.color == RBNode.BLACK and sibling.right.color == RBNode.BLACK:
                    sibling.color = RBNode.RED
                    node = node.parent
                else:
                    if sibling.right.color == RBNode.BLACK:
                        sibling.left.color = RBNode.BLACK
                        sibling.color = RBNode.RED
                        self._rotate_right(sibling)
                        sibling = node.parent.right
                    sibling.color = node.parent.color
                    node.parent.color = RBNode.BLACK
                    sibling.right.color = RBNode.BLACK
                    self._rotate_left(node.parent)
                    node = self.root
            else:
                sibling = node.parent.left
                if sibling.color == RBNode.RED:
                    sibling.color = RBNode.BLACK
                    node.parent.color = RBNode.RED
                    self._rotate_right(node.parent)
                    sibling = node.parent.left
                if sibling.left.color == RBNode.BLACK and sibling.right.color == RBNode.BLACK:
                    sibling.color = RBNode.RED
                    node = node.parent
                else:
                    if sibling.left.color == RBNode.BLACK:
                        sibling.right.color = RBNode.BLACK
                        sibling.color = RBNode.RED
                        self._rotate_left(sibling)
                        sibling = node.parent.left
                    sibling.color = node.parent.color
                    node.parent.color = RBNode.BLACK
                    sibling.left.color = RBNode.BLACK
                    self._rotate_right(node.parent)
                    node = self.root
        node.color = RBNode.BLACK

    def _transplant(self, u, v):
        """
        节点替换操作
        
        用节点 v 替换节点 u 的位置
        """
        if u.parent == self.NIL:
            self.root = v
        elif u == u.parent.left:
            u.parent.left = v
        else:
            u.parent.right = v
        v.parent = u.parent

    def _minimum(self, node):
        """
        查找最小节点
        
        从给定节点开始，一直向左走直到无法继续为止
        """
        while node.left != self.NIL:
            node = node.left
        return node

    def delete(self, key):
        """
        删除节点
        
        步骤：
        1. 找到要删除的节点
        2. 保存原始颜色
        3. 根据节点子节点情况进行删除（类似普通二叉搜索树）
        4. 如果删除的是黑色节点，调用删除修复操作
        
        参数:
            key: 要删除的键
        
        返回:
            是否成功删除
        """
        node = self._search(key)
        if node == self.NIL:
            return False

        y = node
        y_original_color = y.color
        if node.left == self.NIL:
            x = node.right
            self._transplant(node, node.right)
        elif node.right == self.NIL:
            x = node.left
            self._transplant(node, node.left)
        else:
            y = self._minimum(node.right)
            y_original_color = y.color
            x = y.right
            if y.parent == node:
                x.parent = y
            else:
                self._transplant(y, y.right)
                y.right = node.right
                y.right.parent = y
            self._transplant(node, y)
            y.left = node.left
            y.left.parent = y
            y.color = node.color

        if y_original_color == RBNode.BLACK:
            self._delete_fixup(x)
        return True

    def _search(self, key):
        """
        搜索节点
        
        按照二叉搜索树的规则进行查找
        """
        current = self.root
        while current != self.NIL:
            cmp = self._compare(key, current.key)
            if cmp == 0:
                return current
            elif cmp < 0:
                current = current.left
            else:
                current = current.right
        return self.NIL

    def search(self, key):
        """
        搜索并返回节点值
        
        参数:
            key: 要搜索的键
        
        返回:
            节点的值，如果未找到返回 None
        """
        node = self._search(key)
        return node.value if node != self.NIL else None

    def get_min(self):
        """
        获取最小节点的值
        
        返回:
            最左叶子节点的值（即最小键对应的值）
        """
        if self.root == self.NIL:
            return None
        node = self._minimum(self.root)
        return node.value

    def get_all(self):
        """
        获取所有节点的值（按排序顺序）
        
        返回:
            所有值的列表
        """
        result = []
        self._inorder_traversal(self.root, result)
        return result

    def _inorder_traversal(self, node, result):
        """
        中序遍历
        
        按键的升序遍历所有节点
        """
        if node != self.NIL:
            self._inorder_traversal(node.left, result)
            result.append(node.value)
            self._inorder_traversal(node.right, result)

    def get_range(self, start_key, end_key):
        """
        范围查询
        
        获取键在指定范围内的所有节点值
        
        参数:
            start_key: 起始键
            end_key: 结束键
        
        返回:
            符合范围的所有值
        """
        result = []
        self._range_query(self.root, start_key, end_key, result)
        return result

    def _range_query(self, node, start_key, end_key, result):
        """
        递归范围查询
        """
        if node == self.NIL:
            return
        if self._compare(node.key, start_key) > 0:
            self._range_query(node.left, start_key, end_key, result)
        if self._compare(node.key, start_key) >= 0 and self._compare(node.key, end_key) <= 0:
            result.append(node.value)
        if self._compare(node.key, end_key) < 0:
            self._range_query(node.right, start_key, end_key, result)

    def __len__(self):
        return len(self.get_all())

    def is_empty(self):
        return self.root == self.NIL


class BidRedBlackTree(RedBlackTree):
    """
    买单红黑树
    
    买单按价格降序排列，最高价格在前（最佳买单）
    使用 (price, order_id) 作为键，价格相同时按订单创建时间升序排列（先进先出）
    """

    def __init__(self):
        super().__init__(reverse=True)

    def push(self, order: Order):
        """添加订单"""
        key = (order.price, order.timestamp)
        self.insert(key, order)

    def pop(self):
        """弹出最佳买单（最高价）"""
        order = self.get_min()
        if order:
            key = (order.price, order.order_id)
            self.delete(key)
        return order

    def peek(self):
        """查看最佳买单但不移除"""
        return self.get_min()

    def peek_order(self, size) -> list[Order]:
        """获取最佳买单但不移除"""
        return self.get_all()[:size]

    def peek_depth(self, size):
        """获取订单簿深度（聚合相同价格）"""
        orders = self.get_all()
        depth = []
        for order in orders[:size]:
            qty = order.quantity - order.filled_quantity
            if qty <= 0:
                continue
            if depth and depth[-1][0] == order.price:
                depth[-1] = (depth[-1][0], depth[-1][1] + qty)
            else:
                depth.append((order.price, qty))
            if len(depth) >= size:
                break
        return depth


class AskRedBlackTree(RedBlackTree):
    """
    卖单红黑树
    
    卖单按价格升序排列，最低价格在前（最佳卖单）
    使用 (price, order_id) 作为键，价格相同时按订单ID升序排列（先进先出）
    """

    def __init__(self):
        super().__init__(reverse=False)

    def push(self, order):
        """添加订单"""
        key = (order.price, order.order_id)
        self.insert(key, order)

    def pop(self):
        """弹出最佳卖单（最低价）"""
        order = self.get_min()
        if order:
            key = (order.price, order.order_id)
            self.delete(key)
        return order

    def peek(self):
        """查看最佳卖单但不移除"""
        return self.get_min()

    def peek_order(self, size) -> list[Order]:
        """获取最佳卖单但不移除"""
        return self.get_all()[:size]

    def peek_depth(self, size):
        """获取订单簿深度（聚合相同价格）"""
        orders = self.get_all()
        depth = []
        for order in orders:
            qty = order.quantity - order.filled_quantity
            if qty <= 0:
                continue
            if depth and depth[-1][0] == order.price:
                depth[-1] = (depth[-1][0], depth[-1][1] + qty)
            else:
                depth.append((order.price, qty))
            if len(depth) >= size:
                break
        return depth


class OrderBook:
    """
    基于红黑树的订单簿
    
    使用两个红黑树分别管理买单和卖单：
    - BidRedBlackTree: 买单，按价格降序排列
    - AskRedBlackTree: 卖单，按价格升序排列
    
    特点：
    - O(log n) 的订单插入和删除
    - O(1) 获取最优价格
    - 天然有序，支持高效的范围查询
    - 线程安全（使用 RLock）
    """
    
    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol
        self.bids = BidRedBlackTree()
        self.asks = AskRedBlackTree()
        self.orders = {}
        self.lock = threading.RLock()

    def add_order(self, order):
        """添加订单到订单簿"""
        with self.lock:
            self.orders[order.order_id] = order
            if order.side == OrderSide.BUY:
                self.bids.push(order)
            else:
                self.asks.push(order)

    def remove_order(self, order_id):
        """从订单簿移除订单"""
        with self.lock:
            order = self.orders.get(order_id)
            if not order:
                return None

            key = (order.price, order.timestamp)
            if order.side == OrderSide.BUY:
                self.bids.delete(key)
            else:
                self.asks.delete(key)

            del self.orders[order_id]
            return order

    def get_order(self, order_id):
        """获取指定订单"""
        with self.lock:
            return self.orders.get(order_id)

    def get_order_book(self, depth=30) -> OrderBookModel:
        """获取订单簿数据"""
        with self.lock:
            order_book = OrderBookModel(self.symbol)
            order_book.bids = self.bids.peek_depth(depth)
            order_book.asks = self.asks.peek_depth(depth)
            order_book.timestamp = int(time.time() * 1000)
            return order_book

    def get_best_bid(self):
        """获取最佳买价"""
        with self.lock:
            best_bid = self.bids.peek()
            return best_bid.price if best_bid else 0

    def get_best_ask(self):
        """获取最佳卖价"""
        with self.lock:
            best_ask = self.asks.peek()
            return best_ask.price if best_ask else 0

    def update_order(self, order_id, filled_quantity):
        """更新订单成交数量"""
        with self.lock:
            order = self.orders.get(order_id)
            if not order:
                return None
            order.filled_quantity = filled_quantity
            if order.filled_quantity >= order.quantity:
                self.remove_order(order_id)
            return order
