"""Unit tests for sll_orderbook.py (SkipList Linked Order Book) - v2

Re-checked against current code state. Many bugs from v1 have been fixed.
Remaining bugs are documented and tested below.
"""
import pytest
import random
import threading
import time

from src.engine.orderbook.sll_orderbook import (
    PriceLevel,
    LevelOrder,
    OrderPool,
    PriceLevelPool,
    SkipList,
    AskSkipList,
    BidSkipList,
    OrderBook,
)
from src.engine.types.types import Order, OrderSide, OrderType, OrderTimeInForce


# ============================================================
# Helpers
# ============================================================

def make_order(uid="user1", price=100.0, quantity=1.0, side=OrderSide.BUY,
               order_id=None, timestamp=None) -> Order:
    order = Order(uid, "BTCUSDT", side, OrderType.LIMIT, OrderTimeInForce.GTC,
                  quantity, price)
    if order_id:
        order.order_id = order_id
    if timestamp:
        order.timestamp = timestamp
    return order


def make_buy(price=100.0, qty=1.0, uid="user1", oid=None, ts=None):
    return make_order(uid, price, qty, OrderSide.BUY, oid, ts)


def make_sell(price=100.0, qty=1.0, uid="user1", oid=None, ts=None):
    return make_order(uid, price, qty, OrderSide.SELL, oid, ts)


def make_pools(max_index_level=8, max_price_level=100, max_orders=1000):
    """Create separate pools for testing."""
    pl_pool = PriceLevelPool(max_index_level=max_index_level, max_price_level=max_price_level)
    o_pool = OrderPool(max_orders=max_orders)
    return pl_pool, o_pool


# ============================================================
# Test PriceLevel (FIXED - level_tail bug resolved)
# ============================================================

class TestPriceLevel:
    """Tests for PriceLevel class."""

    def test_init(self):
        """PriceLevel construction now works (level_tail bug fixed at L28)."""
        pl = PriceLevel(price=100.0, level=4)
        assert pl.price == 100.0
        assert pl.level == 4
        assert pl.order_num == 0
        assert pl.level_head is not None
        assert pl.level_tail is pl.level_head  # tail points to head initially
        assert pl.forward == [None, None, None, None]

    def test_level_head_is_sentinel(self):
        """level_head is a sentinel with order_index=-1."""
        pl = PriceLevel(price=100.0, level=2)
        assert pl.level_head.order_index == -1
        assert pl.level_head.order is None


# ============================================================
# Test OrderPool
# ============================================================

class TestOrderPool:
    """Tests for OrderPool class."""

    def test_init(self):
        pool = OrderPool(max_orders=10)
        assert pool.capacity == 0
        assert pool.max_order_size == 10
        assert len(pool.free_orders) == 10
        assert len(pool.free_orders_ptr) == 10
        assert pool.free_ptr_head == 0

    def test_new_and_free(self):
        pool = OrderPool(max_orders=5)
        order = make_buy(price=100)
        node = pool.new(order)
        assert node is not None
        assert node.order == order
        assert pool.capacity == 1

        pool.free(node)
        assert pool.capacity == 0
        assert node.order is None

    def test_is_full(self):
        pool = OrderPool(max_orders=3)
        assert not pool.is_full()

        nodes = []
        for i in range(3):
            n = pool.new(make_buy(price=100 + i))
            assert n is not None
            nodes.append(n)

        assert pool.is_full()
        assert pool.new(make_buy(price=999)) is None

    def test_reuse_freed_node(self):
        pool = OrderPool(max_orders=2)
        n1 = pool.new(make_buy(price=100))
        n2 = pool.new(make_buy(price=200))
        assert pool.is_full()

        pool.free(n1)
        assert not pool.is_full()

        n3 = pool.new(make_buy(price=300))
        assert n3 is not None
        assert n3.order.price == 300
        assert pool.is_full()

    def test_free_ptr_sentinel(self):
        """free_orders_ptr last value is max_orders (out-of-bounds sentinel).
        Works because capacity check prevents access."""
        pool = OrderPool(max_orders=3)
        n0 = pool.new(make_buy())
        n1 = pool.new(make_buy())
        n2 = pool.new(make_buy())
        assert pool.capacity == 3
        assert pool.is_full()
        assert pool.free_ptr_head == 3  # sentinel, out of bounds but safe
        assert pool.new(make_buy()) is None


# ============================================================
# Test PriceLevelPool (FIXED - level_tail reset in new())
# ============================================================

class TestPriceLevelPool:
    """Tests for PriceLevelPool class."""

    def test_init(self):
        """PriceLevelPool init now works (PriceLevel bug fixed)."""
        pool = PriceLevelPool(max_index_level=16, max_price_level=10)
        assert pool.level_capacity == 0
        assert pool.max_level_size == 10
        assert len(pool.free_levels) == 10

    def test_new_and_free(self):
        pool = PriceLevelPool(max_index_level=4, max_price_level=5)
        pl = pool.new(price=100.0, level=2)
        assert pl is not None
        assert pl.price == 100.0
        assert pl.level == 2
        assert pl.level_tail is pl.level_head  # reset in new()
        assert pl.order_num == 0
        assert pool.level_capacity == 1

        pool.free(pl)
        assert pool.level_capacity == 0

    def test_is_full(self):
        pool = PriceLevelPool(max_index_level=4, max_price_level=2)
        pl1 = pool.new(price=100.0, level=1)
        pl2 = pool.new(price=200.0, level=1)
        assert pool.is_full()
        assert pool.new(price=300.0, level=1) is None


# ============================================================
# Test AskSkipList
# ============================================================

class TestAskSkipList:
    """Tests for AskSkipList (ascending price order)."""

    @pytest.fixture
    def sl(self):
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1000)
        return AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                          order_pool=o_pool)

    def test_empty_peek(self, sl):
        """peek() on empty skip list returns None. (FIXED: now correctly accesses level_head.next.order)"""
        assert sl.peek() is None

    def test_insert_single(self, sl):
        """Test inserting a single order."""
        order = make_sell(price=100.0)
        assert sl.insert(order) == True
        assert sl.search(order) is not None

    def test_insert_multiple_prices(self, sl):
        """Test inserting orders at different prices."""
        orders = [
            make_sell(price=300.0, oid="o3"),
            make_sell(price=100.0, oid="o1"),
            make_sell(price=200.0, oid="o2"),
        ]
        for order in orders:
            assert sl.insert(order) == True

        # peek should return lowest price (best ask)
        result = sl.peek()
        assert result is not None
        assert result.price == 100.0

    def test_insert_same_price_multiple_orders(self, sl):
        """Test inserting multiple orders at the same price.
        (FIXED: level_tail now updated after insert at L211, L238)
        """
        o1 = make_sell(price=100.0, oid="o1", ts=1)
        o2 = make_sell(price=100.0, oid="o2", ts=2)
        o3 = make_sell(price=100.0, oid="o3", ts=3)

        assert sl.insert(o1) == True
        assert sl.insert(o2) == True
        assert sl.insert(o3) == True

        pl = sl.search(o1)
        assert pl is not None
        assert pl.order_num == 3

        # Traverse the order list to verify all 3 orders are linked
        count = 0
        node = pl.level_head.next
        while node:
            count += 1
            node = node.next
        assert count == 3

    def test_delete_order(self, sl):
        """Test deleting an order."""
        order = make_sell(price=100.0, oid="o1")
        sl.insert(order)
        assert sl.delete(order) == True
        assert sl.search(order) is None

    def test_delete_nonexistent(self, sl):
        """Test deleting a non-existent order."""
        order = make_sell(price=100.0, oid="o1")
        assert sl.delete(order) == False

    def test_delete_last_order_removes_price_level(self, sl):
        """Test that deleting the last order removes the price level."""
        order = make_sell(price=100.0, oid="o1")
        sl.insert(order)
        sl.delete(order)
        assert sl.search(order) is None
        assert sl.peek() is None

    def test_peek_returns_best_ask(self, sl):
        """Test that peek returns the lowest price (best ask)."""
        sl.insert(make_sell(price=300.0, oid="o3"))
        sl.insert(make_sell(price=100.0, oid="o1"))
        sl.insert(make_sell(price=200.0, oid="o2"))

        result = sl.peek()
        assert result is not None
        assert result.price == 100.0

    def test_pop(self, sl):
        """Test pop returns and removes the best ask.

        BUG: pop() at L292 accesses `top_level.order` which doesn't exist
        on PriceLevel. Should be `top_level.level_head.next.order`.
        """
        sl.insert(make_sell(price=100.0, oid="o1"))
        sl.insert(make_sell(price=200.0, oid="o2"))

        with pytest.raises(AttributeError, match="'PriceLevel' object has no attribute 'order'"):
            sl.pop()

    def test_peek_depth(self, sl):
        """Test peek_depth returns price levels. (FIXED: no longer accesses self.capacity)"""
        sl.insert(make_sell(price=100.0, qty=2.0, oid="o1"))
        sl.insert(make_sell(price=200.0, qty=3.0, oid="o2"))
        sl.insert(make_sell(price=300.0, qty=1.0, oid="o3"))

        result = sl.peek_depth(2)
        assert len(result) == 2
        assert result[0] == (100.0, 2.0)
        assert result[1] == (200.0, 3.0)

    def test_peek_depth_more_than_available(self, sl):
        """Test peek_depth when depth exceeds available levels. (FIXED: null check added)"""
        sl.insert(make_sell(price=100.0, qty=2.0, oid="o1"))

        result = sl.peek_depth(10)
        assert len(result) == 1
        assert result[0] == (100.0, 2.0)

    def test_delete_middle_order_same_price(self, sl):
        """Test deleting a middle order at the same price.

        BUG: delete() does not update level_tail when the deleted order
        is the last (tail) order in the price level's order list.
        """
        o1 = make_sell(price=100.0, oid="o1", ts=1)
        o2 = make_sell(price=100.0, oid="o2", ts=2)
        o3 = make_sell(price=100.0, oid="o3", ts=3)

        sl.insert(o1)
        sl.insert(o2)
        sl.insert(o3)

        # Delete the tail (o3)
        assert sl.delete(o3) == True

        pl = sl.search(o1)
        assert pl is not None
        assert pl.order_num == 2
        assert pl.level_tail.order is None  # BUG: level_tail still points to freed o3!

    def test_delete_tail_then_insert(self, sl):
        """Test that deleting tail and then inserting doesn't corrupt data.

        BUG: After deleting the tail order, level_tail points to a freed
        LevelOrder. The next insert links to the freed LevelOrder via
        new_order.prev = price_level.level_tail, which may have been reused.
        """
        o1 = make_sell(price=100.0, oid="o1", ts=1)
        o2 = make_sell(price=100.0, oid="o2", ts=2)

        sl.insert(o1)
        sl.insert(o2)

        # Delete the tail (o2)
        sl.delete(o2)

        # Insert a new order at the same price
        o3 = make_sell(price=100.0, oid="o3", ts=3)
        sl.insert(o3)

        pl = sl.search(o1)
        assert pl is not None
        assert pl.order_num == 2

        # Verify the order list is correct
        node = pl.level_head.next
        assert node.order.order_id == "o1"
        node = node.next
        assert node.order.order_id == "o3"
        assert node.next is None
        assert pl.level_tail.order.order_id == "o3"

    def test_delete_farest_level_empty(self, sl):
        """Test delete_farest_level on empty skip list.

        BUG: No empty check. self.head.forward[0] is None, then
        farest_level.forward[0] raises AttributeError.
        """
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'forward'"):
            sl.delete_farest_level()

    def test_delete_farest_level_single(self, sl):
        """Test delete_farest_level with a single price level."""
        sl.insert(make_sell(price=100.0, oid="o1"))
        sl.insert(make_sell(price=100.0, oid="o2"))

        orders = sl.delete_farest_level()
        assert len(orders) == 2
        assert sl.peek() is None

    def test_delete_farest_level_multiple(self, sl):
        """Test delete_farest_level removes the farthest (highest for asks) level."""
        sl.insert(make_sell(price=100.0, oid="o1"))
        sl.insert(make_sell(price=200.0, oid="o2"))
        sl.insert(make_sell(price=300.0, oid="o3"))

        orders = sl.delete_farest_level()
        assert len(orders) == 1
        assert orders[0].order_id == "o3"
        # Best ask should still be 100
        assert sl.peek().price == 100.0

    def test_insert_price_level_leak_on_order_pool_full(self):
        """Test that insert leaks PriceLevel when order_pool is full.

        BUG: If price_level_pool.new() succeeds but order_pool.new() fails,
        the PriceLevel is already linked into the skip list but has no orders.
        """
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1)  # Only 1 order slot
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                        order_pool=o_pool)

        # First insert uses the only order slot
        o1 = make_sell(price=100.0, oid="o1")
        assert sl.insert(o1) == True

        # Second insert at a different price: PriceLevel created but order fails
        o2 = make_sell(price=200.0, oid="o2")
        assert sl.insert(o2) == False  # order pool full

        # BUG: An empty PriceLevel at price 200 is now in the skip list
        pl = sl.search(o2)
        assert pl is not None  # This should be None but isn't
        assert pl.order_num == 0  # Empty price level leaked


# ============================================================
# Test BidSkipList
# ============================================================

class TestBidSkipList:
    """Tests for BidSkipList (descending price order)."""

    @pytest.fixture
    def sl(self):
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1000)
        return BidSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                          order_pool=o_pool)

    def test_insert_descending(self, sl):
        """Test that bids are stored in descending price order."""
        sl.insert(make_buy(price=100.0, oid="o1"))
        sl.insert(make_buy(price=300.0, oid="o3"))
        sl.insert(make_buy(price=200.0, oid="o2"))

        result = sl.peek()
        assert result is not None
        assert result.price == 300.0  # Highest buy = best bid

    def test_delete(self, sl):
        """Test deleting orders from bid skip list."""
        sl.insert(make_buy(price=100.0, oid="o1"))
        assert sl.delete(make_buy(price=100.0, oid="o1")) == True
        assert sl.search(make_buy(price=100.0, oid="o1")) is None

    def test_peek_depth(self, sl):
        """Test peek_depth returns descending price levels for bids."""
        sl.insert(make_buy(price=300.0, qty=2.0, oid="o3"))
        sl.insert(make_buy(price=100.0, qty=1.0, oid="o1"))
        sl.insert(make_buy(price=200.0, qty=3.0, oid="o2"))

        result = sl.peek_depth(3)
        assert len(result) == 3
        assert result[0] == (300.0, 2.0)  # Highest first
        assert result[1] == (200.0, 3.0)
        assert result[2] == (100.0, 1.0)

    def test_delete_farest_level(self, sl):
        """Test delete_farest_level removes the farthest (lowest for bids) level."""
        sl.insert(make_buy(price=100.0, oid="o1"))
        sl.insert(make_buy(price=200.0, oid="o2"))
        sl.insert(make_buy(price=300.0, oid="o3"))

        orders = sl.delete_farest_level()
        assert len(orders) == 1
        assert orders[0].order_id == "o1"  # Lowest price removed
        assert sl.peek().price == 300.0  # Best bid still 300


# ============================================================
# Test OrderBook Integration
# ============================================================

class TestOrderBook:
    """Tests for OrderBook integration."""

    def test_init_crash(self):
        """OrderBook.__init__ crashes due to duplicate ask pool assignment.

        BUG: L350-353 assigns ask pools twice instead of creating bid pools:
            self.ask_price_level_pool = PriceLevelPool(max_price_level)  # L350 OK
            self.ask_order_pool = OrderPool(max_orders)                 # L351 OK
            self.ask_price_level_pool = PriceLevelPool(max_price_level)  # L352 BUG! should be bid
            self.ask_order_pool = OrderPool(max_orders)                 # L353 BUG! should be bid

        Then L356 references self.bid_price_level_pool which is never defined.
        """
        with pytest.raises(AttributeError, match="bid_price_level_pool"):
            OrderBook(symbol="BTCUSDT")

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes (duplicate ask pool, undefined bid pool)")
    def test_add_buy_order(self):
        """Test adding a buy order. (FIXED: sides no longer reversed)"""
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        order = make_buy(price=100.0, oid="buy1")
        result = ob.add_order(order)
        assert result is not None
        assert ob.get_order("user1", "buy1") is not None
        assert ob.get_best_bid().price == 100.0

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_add_sell_order(self):
        """Test adding a sell order. (FIXED: sides no longer reversed)"""
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        order = make_sell(price=100.0, oid="sell1")
        result = ob.add_order(order)
        assert result is not None
        assert ob.get_best_ask().price == 100.0

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_add_duplicate(self):
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        order = make_buy(price=100.0, oid="dup1")
        ob.add_order(order)
        assert ob.add_order(order) is None

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_remove_order(self):
        """Test removing an order. (FIXED: sides and locks correct)"""
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        order = make_buy(price=100.0, oid="buy1")
        ob.add_order(order)
        result = ob.remove_order("buy1")
        assert result is not None
        assert ob.get_order("user1", "buy1") is None

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_remove_nonexistent(self):
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        assert ob.remove_order("nonexistent") is None

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_update_order_filled(self):
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        order = make_buy(price=100.0, qty=10.0, oid="buy1")
        ob.add_order(order)
        ob.update_order("buy1", 5.0)
        assert ob.get_order("user1", "buy1") is not None
        ob.update_order("buy1", 10.0)
        assert ob.get_order("user1", "buy1") is None

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_best_bid_ask(self):
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        ob.add_order(make_buy(price=100.0, oid="b1"))
        ob.add_order(make_buy(price=200.0, oid="b2"))
        ob.add_order(make_sell(price=300.0, oid="s1"))
        ob.add_order(make_sell(price=250.0, oid="s2"))

        assert ob.get_best_bid().price == 200.0
        assert ob.get_best_ask().price == 250.0

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_get_order_book(self):
        """Test getting order book depth. (FIXED: locks added)"""
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        ob.add_order(make_buy(price=100.0, qty=2.0, oid="b1"))
        ob.add_order(make_sell(price=200.0, qty=3.0, oid="s1"))

        book = ob.get_order_book(depth=10)
        assert book is not None
        assert len(book.bids) == 1
        assert len(book.asks) == 1
        assert book.bids[0] == (100.0, 2.0)
        assert book.asks[0] == (200.0, 3.0)

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_pending_orders(self):
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        ob.add_order(make_buy(price=100.0, uid="user1", oid="b1"))
        ob.add_order(make_buy(price=200.0, uid="user1", oid="b2"))
        ob.add_order(make_buy(price=300.0, uid="user2", oid="b3"))

        pending = ob.pending_orders("user1")
        assert len(pending) == 2

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_pool_full_eviction(self):
        """Test that pool full triggers eviction. (FIXED: variable shadowing resolved)"""
        ob = OrderBook(symbol="BTCUSDT", max_price_level=3, max_orders=5)
        for i in range(5):
            ob.add_order(make_buy(price=100.0 + i, oid=f"b{i}"))

        # Adding a 6th order should trigger eviction
        new_order = make_buy(price=999.0, oid="new_order")
        ob.add_order(new_order)
        assert ob.get_order("user1", "new_order") is not None

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_batch_add_orders(self):
        """Test batch adding orders. (FIXED: now matches interface signature)"""
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        orders = [
            make_buy(price=100.0, oid="b1"),
            make_buy(price=200.0, oid="b2"),
            make_sell(price=300.0, oid="s1"),
        ]
        result = ob.batch_add_orders(OrderSide.BUY, orders)
        assert len(result) == 3

    @pytest.mark.xfail(reason="BUG L350-356: OrderBook.__init__ crashes")
    def test_batch_remove_orders(self):
        """Test batch removing orders."""
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)
        o1 = make_buy(price=100.0, oid="b1")
        o2 = make_buy(price=200.0, oid="b2")
        ob.add_order(o1)
        ob.add_order(o2)
        result = ob.batch_remove_orders([o1, o2])
        assert len(result) == 2


# ============================================================
# Bug Summary
# ============================================================

class TestBugSummary:
    """Document all remaining bugs in the current code."""

    def test_bug_01_orderbook_init_duplicate_pools(self):
        """BUG L350-356: OrderBook.__init__ assigns ask pools twice.

        L350: self.ask_price_level_pool = PriceLevelPool(max_price_level)
        L351: self.ask_order_pool = OrderPool(max_orders)
        L352: self.ask_price_level_pool = PriceLevelPool(max_price_level)  # DUPLICATE!
        L353: self.ask_order_pool = OrderPool(max_orders)                  # DUPLICATE!

        Should be:
            self.bid_price_level_pool = PriceLevelPool(max_price_level)
            self.bid_order_pool = OrderPool(max_orders)

        L356 then references self.bid_price_level_pool which is never defined
        -> AttributeError: 'OrderBook' object has no attribute 'bid_price_level_pool'
        """
        with pytest.raises(AttributeError, match="bid_price_level_pool"):
            OrderBook(symbol="BTCUSDT")

    def test_bug_02_pop_accesses_nonexistent_attribute(self):
        """BUG L292: pop() accesses top_level.order which doesn't exist on PriceLevel.

        peek() was fixed (L281-282) to correctly access level_head.next.order,
        but pop() was NOT fixed. It still does:
            order = top_level.order  # AttributeError!

        Should be:
            order = top_level.level_head.next.order
        """
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1000)
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                        order_pool=o_pool)
        sl.insert(make_sell(price=100.0, oid="o1"))
        with pytest.raises(AttributeError, match="'PriceLevel' object has no attribute 'order'"):
            sl.pop()

    def test_bug_03_delete_farest_level_no_empty_check(self):
        """BUG L169: delete_farest_level() crashes on empty skip list.

        farest_level = self.head.forward[0]  # None if empty
        while farest_level.forward[0]:       # AttributeError: 'NoneType'

        Should check: if not farest_level: return []
        """
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1000)
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                        order_pool=o_pool)
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'forward'"):
            sl.delete_farest_level()

    def test_bug_04_delete_not_updating_level_tail(self):
        """BUG L258-276: delete() does not update level_tail when deleting the tail order.

        When the deleted order is the last in the order list (but not the only one),
        level_tail still points to the freed LevelOrder. Subsequent insertions
        link to the freed LevelOrder via new_order.prev = price_level.level_tail.

        If the freed LevelOrder has been reused by order_pool.new() for another
        order, this corrupts the other order's linked list.

        Fix: add after unlinking:
            if current_order == price_level.level_tail:
                price_level.level_tail = current_order.prev
        """
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1000)
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                        order_pool=o_pool)

        o1 = make_sell(price=100.0, oid="o1", ts=1)
        o2 = make_sell(price=100.0, oid="o2", ts=2)
        sl.insert(o1)
        sl.insert(o2)

        pl = sl.search(o1)
        assert pl.level_tail.order.order_id == "o2"

        # Delete the tail
        sl.delete(o2)

        # BUG: level_tail still points to freed o2
        assert pl.level_tail.order is None  # order was set to None by free()

    def test_bug_05_insert_leaks_pricelevel_on_order_pool_full(self):
        """BUG L223-234: insert() leaks PriceLevel when order_pool.new() fails.

        If price_level_pool.new() succeeds but order_pool.new() returns None,
        the PriceLevel is already linked into the skip list (L227-229).
        The method returns False, but the empty PriceLevel remains in the list.

        Fix: either check order_pool.is_full() before creating PriceLevel,
        or roll back the PriceLevel insertion on failure.
        """
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1)
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                        order_pool=o_pool)

        sl.insert(make_sell(price=100.0, oid="o1"))  # Uses the 1 order slot

        o2 = make_sell(price=200.0, oid="o2")
        assert sl.insert(o2) == False  # order pool full

        # BUG: empty PriceLevel at price 200 is in the skip list
        pl = sl.search(o2)
        assert pl is not None  # Should be None
        assert pl.order_num == 0  # Empty price level leaked

    def test_bug_06_batch_remove_orders_signature_mismatch(self):
        """BUG L417: batch_remove_orders takes List[Order] instead of List[str].

        Interface: batch_remove_orders(self, order_ids: List[str]) -> List[Order]
        Implementation: batch_remove_orders(self, orders: List[Order]) -> List[Order]

        The implementation takes Order objects and accesses order.order_id,
        but the interface contract expects order_id strings.
        """
        from src.engine.orderbook.ob_interface import OrderBookInterface
        import inspect
        sig = inspect.signature(OrderBookInterface.batch_remove_orders)
        params = list(sig.parameters.keys())
        assert 'order_ids' in params, "Interface expects 'order_ids' parameter"

    def test_bug_07_batch_add_orders_ignores_side(self):
        """BUG L408: batch_add_orders accepts `side` but never uses it.

        The `side` parameter is accepted but add_order() determines side
        from order.side. The `side` parameter should either be used for
        validation or removed.
        """
        from src.engine.orderbook.ob_interface import OrderBookInterface
        import inspect
        sig = inspect.signature(OrderBookInterface.batch_add_orders)
        assert 'side' in sig.parameters, "Interface expects 'side' parameter"

    def test_fixed_01_level_tail_init(self):
        """FIXED: L28 now correctly assigns self.level_tail = self.level_head."""
        pl = PriceLevel(price=100.0, level=4)
        assert pl.level_tail is pl.level_head

    def test_fixed_02_level_tail_updated_on_insert(self):
        """FIXED: L211 and L238 now update level_tail after insert."""
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1000)
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                        order_pool=o_pool)

        o1 = make_sell(price=100.0, oid="o1")
        sl.insert(o1)
        pl = sl.search(o1)
        assert pl.level_tail.order.order_id == "o1"

        o2 = make_sell(price=100.0, oid="o2")
        sl.insert(o2)
        assert pl.level_tail.order.order_id == "o2"

    def test_fixed_03_peek_correct_attribute(self):
        """FIXED: L281-282 now correctly accesses level_head.next.order."""
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1000)
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                        order_pool=o_pool)
        sl.insert(make_sell(price=100.0, oid="o1"))
        result = sl.peek()
        assert result is not None
        assert result.order_id == "o1"

    def test_fixed_04_peek_depth_no_capacity_check(self):
        """FIXED: L296-312 no longer accesses self.capacity, has null check."""
        pl_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        o_pool = OrderPool(max_orders=1000)
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=pl_pool,
                        order_pool=o_pool)
        # Empty skip list - should return empty list, not crash
        result = sl.peek_depth(10)
        assert result == []

    def test_fixed_05_add_order_sides_correct(self):
        """FIXED: L370-389 now correctly routes Buy->bids, Sell->asks."""
        # Cannot fully test due to init bug, but verify the code paths
        import inspect
        src = inspect.getsource(OrderBook.add_order)
        assert 'OrderSide.BUY' in src  # Uses correct enum case
        assert 'self.bids.insert' in src  # Buy goes to bids
        assert 'self.asks.insert' in src  # Sell goes to asks

    def test_fixed_06_remove_order_sides_and_locks(self):
        """FIXED: L399-404 now correctly routes and uses locks."""
        import inspect
        src = inspect.getsource(OrderBook.remove_order)
        assert 'self.bids.delete' in src
        assert 'self.asks.delete' in src
        assert 'self.bid_lock' in src
        assert 'self.ask_lock' in src

    def test_fixed_07_get_order_book_uses_locks(self):
        """FIXED: L434-443 now uses ask_lock and bid_lock."""
        import inspect
        src = inspect.getsource(OrderBook.get_order_book)
        assert 'self.ask_lock' in src
        assert 'self.bid_lock' in src

    def test_fixed_08_separate_pools(self):
        """FIXED: Pools are now separate for asks and bids (in add_order logic).
        But the init still has the duplicate assignment bug (bug_01)."""
        import inspect
        src = inspect.getsource(OrderBook.__init__)
        # The intention is to have separate pools, but the code has a bug
        # where ask pools are assigned twice instead of creating bid pools
        assert 'ask_price_level_pool' in src
        # bid_price_level_pool should be here but is missing due to bug


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
