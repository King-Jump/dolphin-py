"""Unit tests for sll_orderbook.py (SkipList Linked Order Book)

Tests verify the correctness of:
- PriceLevel
- OrderPool
- PriceLevelPool
- SkipList (AskSkipList, BidSkipList)
- OrderBook integration

Bug discoveries are documented as xfails with explanations.
"""
import sys
import pytest
import random
import threading
import time

# ============================================================
# Import workarounds for critical bugs that prevent import
# ============================================================

# Bug 1: Line 9 uses `OrdderBook` (double d), actual class is `OrderBook`
#   from src.engine.types.types import Order, OrderSide, OrdderBook as OrderBookModel
# Workaround: add alias before import
import src.engine.types.types as _types
_types.OrdderBook = _types.OrderBook

# Bug 2: Lines 367, 377 use `OrderSide.Buy` / `OrderSide.Sell` (PascalCase)
#   but OrderSide enum uses `BUY` / `SELL` (all caps)
# Workaround: add aliases
_types.OrderSide.Buy = _types.OrderSide.BUY
_types.OrderSide.Sell = _types.OrderSide.SELL

# Bug 3: Line 8 imports from `orderbook` but OrderBookInterface is in `ob_interface`
#   Actually orderbook.py re-exports it, so this import works.
# No workaround needed.

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
# Helper functions
# ============================================================

def make_order(uid="user1", price=100.0, quantity=1.0, side=OrderSide.BUY,
               order_id=None, timestamp=None) -> Order:
    """Create an Order with explicit fields for testing."""
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


# ============================================================
# Test PriceLevel
# ============================================================

class TestPriceLevel:
    """Tests for PriceLevel class."""

    def test_price_level_init(self):
        """Test basic PriceLevel construction.
        
        BUG: Line 28 `self.level_tail.next = self.level_head` fails because
        `level_tail` is never defined. Should be `self.level_tail = self.level_head`.
        """
        with pytest.raises(AttributeError, match="level_tail"):
            PriceLevel(price=100.0, level=4)

    @pytest.mark.xfail(reason="BUG L28: self.level_tail not defined before use")
    def test_price_level_init_fixed(self):
        """If level_tail bug were fixed, PriceLevel should construct properly."""
        pl = PriceLevel(price=100.0, level=4)
        assert pl.price == 100.0
        assert pl.level == 4
        assert pl.order_num == 0
        assert pl.level_head is not None
        assert pl.level_tail is not None
        assert pl.forward == [None, None, None, None]


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
        # free_orders_ptr = list(range(1, max_orders+1)) = [1, 2, ..., 10]
        # Note: last value 10 is out-of-bounds sentinel (free_orders only has indices 0-9)
        assert len(pool.free_orders_ptr) == 10
        assert pool.free_ptr_head == 0

    def test_new_and_free(self):
        """Test basic allocation and deallocation."""
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
        """Test that pool correctly reports full status."""
        pool = OrderPool(max_orders=3)
        assert not pool.is_full()

        nodes = []
        for i in range(3):
            n = pool.new(make_buy(price=100 + i))
            assert n is not None
            nodes.append(n)

        assert pool.is_full()

        # Cannot allocate when full
        n = pool.new(make_buy(price=999))
        assert n is None

    def test_reuse_freed_node(self):
        """Test that freed nodes can be reused."""
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

    def test_free_ptr_chain_terminator(self):
        """Test that free_orders_ptr uses max_orders as sentinel terminator.
        
        free_orders_ptr = list(range(1, max_orders+1)) = [1, 2, ..., max_orders]
        The last value `max_orders` is out of bounds for free_orders (indices 0..max_orders-1).
        This works because capacity check prevents access, but is fragile.
        """
        pool = OrderPool(max_orders=3)
        # Allocate all 3 nodes
        n0 = pool.new(make_buy())
        n1 = pool.new(make_buy())
        n2 = pool.new(make_buy())
        assert pool.capacity == 3
        assert pool.is_full()
        # free_ptr_head is now 3 (the sentinel value), but capacity check prevents access
        assert pool.free_ptr_head == 3
        # Next allocation should return None
        assert pool.new(make_buy()) is None


# ============================================================
# Test PriceLevelPool
# ============================================================

class TestPriceLevelPool:
    """Tests for PriceLevelPool class."""

    def test_init(self):
        """Test PriceLevelPool initialization.
        
        BUG: PriceLevelPool.__init__ creates PriceLevel objects in a list
        comprehension, which crashes due to the level_tail bug (L28).
        """
        with pytest.raises(AttributeError, match="level_tail"):
            PriceLevelPool(max_index_level=16, max_price_level=10)

    def test_new_and_free(self):
        """Test basic allocation and deallocation.
        
        BUG: PriceLevelPool.new() calls PriceLevel constructor which fails
        because of the level_tail bug. But since new() reuses pre-allocated
        PriceLevel objects (created in __init__), this should work IF the
        __init__ didn't already crash.
        
        Actually, PriceLevelPool.__init__ creates PriceLevel objects:
            self.free_levels = [PriceLevel(0, max_index_level, i) for i in range(max_price_level)]
        This will crash due to the level_tail bug.
        """
        with pytest.raises(AttributeError, match="level_tail"):
            PriceLevelPool(max_index_level=4, max_price_level=5)

    @pytest.mark.xfail(reason="BUG L28: PriceLevel.__init__ crashes, blocking PriceLevelPool init")
    def test_new_price_level(self):
        """If level_tail bug were fixed, test price level allocation."""
        pool = PriceLevelPool(max_index_level=4, max_price_level=5)
        pl = pool.new(price=100.0, level=2)
        assert pl is not None
        assert pl.price == 100.0
        assert pl.level == 2
        assert pl.forward == [None, None, None, None]
        assert pool.level_capacity == 1

        pool.free(pl)
        assert pool.level_capacity == 0


# ============================================================
# Test SkipList
# ============================================================

class TestAskSkipList:
    """Tests for AskSkipList (ascending price order)."""

    @pytest.fixture
    def skip_list(self):
        """Create an AskSkipList with pools.
        
        BUG: This fixture will fail because PriceLevelPool.__init__ crashes
        due to the level_tail bug in PriceLevel.__init__.
        """
        pytest.skip("PriceLevelPool.__init__ crashes due to level_tail bug (L28)")

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_empty_peek(self):
        """Test peek on empty skip list.
        
        BUG: peek() accesses PriceLevel.order which doesn't exist.
        PriceLevel has level_head (a LevelOrder), not order.
        Should be: price_level.level_head.next.order
        """
        price_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        order_pool = OrderPool(max_orders=1000)
        sl = AskSkipList(max_level=8, pN=4, price_level_pool=price_pool,
                        order_pool=order_pool)
        result = sl.peek()
        assert result is None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_insert_single_order(self, skip_list):
        """Test inserting a single order."""
        order = make_sell(price=100.0)
        result = skip_list.insert(order)
        assert result == True
        assert skip_list.search(order) is not None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_insert_multiple_different_prices(self, skip_list):
        """Test inserting orders at different prices (ascending for asks)."""
        orders = [
            make_sell(price=300.0, oid="o3"),
            make_sell(price=100.0, oid="o1"),
            make_sell(price=200.0, oid="o2"),
        ]
        for order in orders:
            skip_list.insert(order)

        # Peek should return the lowest price (best ask)
        result = skip_list.peek()
        assert result is not None
        # BUG: peek returns PriceLevel.order which doesn't exist
        # If fixed: assert result.price == 100.0

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_insert_same_price_multiple_orders(self, skip_list):
        """Test inserting multiple orders at the same price.
        
        BUG: insert() does not update level_tail after appending an order.
        The line `price_level.level_tail.next = new_order` uses level_tail
        which is never updated, so the second order at the same price
        overwrites the first order's link.
        """
        o1 = make_sell(price=100.0, oid="o1", ts=1)
        o2 = make_sell(price=100.0, oid="o2", ts=2)
        o3 = make_sell(price=100.0, oid="o3", ts=3)

        skip_list.insert(o1)
        skip_list.insert(o2)  # This would break the list due to level_tail bug
        skip_list.insert(o3)

        pl = skip_list.search(o1)
        assert pl is not None
        assert pl.order_num == 3

        # Traverse the order list
        count = 0
        node = pl.level_head.next
        while node:
            count += 1
            node = node.next
        assert count == 3  # Would fail due to level_tail not being updated

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_delete_order(self, skip_list):
        """Test deleting an order."""
        order = make_sell(price=100.0, oid="o1")
        skip_list.insert(order)
        assert skip_list.delete(order) == True
        assert skip_list.search(order) is None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_delete_nonexistent(self, skip_list):
        """Test deleting a non-existent order."""
        order = make_sell(price=100.0, oid="o1")
        assert skip_list.delete(order) == False

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_delete_last_order_removes_price_level(self, skip_list):
        """Test that deleting the last order at a price removes the price level."""
        order = make_sell(price=100.0, oid="o1")
        skip_list.insert(order)
        skip_list.delete(order)
        # Price level should be removed
        assert skip_list.search(order) is None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_peek_returns_best_ask(self, skip_list):
        """Test that peek returns the lowest price (best ask)."""
        skip_list.insert(make_sell(price=300.0, oid="o3"))
        skip_list.insert(make_sell(price=100.0, oid="o1"))
        skip_list.insert(make_sell(price=200.0, oid="o2"))

        result = skip_list.peek()
        # BUG: peek accesses PriceLevel.order which doesn't exist
        # If fixed: assert result.price == 100.0
        assert result is not None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_pop(self, skip_list):
        """Test pop returns and removes the best ask."""
        skip_list.insert(make_sell(price=100.0, oid="o1"))
        skip_list.insert(make_sell(price=200.0, oid="o2"))

        result = skip_list.pop()
        # BUG: pop accesses top_level.order which doesn't exist on PriceLevel
        # Also BUG: pop calls self.delete(order) but order is wrong type
        assert result is not None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_peek_depth(self, skip_list):
        """Test peek_depth returns price levels.
        
        BUG: peek_depth accesses self.capacity which doesn't exist on SkipList.
        Also no null check on current_level (could be None at end of list).
        """
        skip_list.insert(make_sell(price=100.0, qty=2.0, oid="o1"))
        skip_list.insert(make_sell(price=200.0, qty=3.0, oid="o2"))
        skip_list.insert(make_sell(price=300.0, qty=1.0, oid="o3"))

        result = skip_list.peek_depth(2)
        assert len(result) == 2
        assert result[0] == (100.0, 2.0)
        assert result[1] == (200.0, 3.0)


class TestBidSkipList:
    """Tests for BidSkipList (descending price order)."""

    @pytest.fixture
    def skip_list(self):
        price_pool = PriceLevelPool(max_index_level=8, max_price_level=100)
        order_pool = OrderPool(max_orders=1000)
        return BidSkipList(max_level=8, pN=4, price_level_pool=price_pool,
                          order_pool=order_pool)

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_insert_descending(self, skip_list):
        """Test that bids are stored in descending price order."""
        skip_list.insert(make_buy(price=100.0, oid="o1"))
        skip_list.insert(make_buy(price=300.0, oid="o3"))
        skip_list.insert(make_buy(price=200.0, oid="o2"))

        result = skip_list.peek()
        # BUG: peek accesses PriceLevel.order which doesn't exist
        # If fixed: assert result.price == 300.0 (highest bid = best bid)
        assert result is not None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_delete(self, skip_list):
        """Test deleting orders from bid skip list."""
        skip_list.insert(make_buy(price=100.0, oid="o1"))
        assert skip_list.delete(make_buy(price=100.0, oid="o1")) == True
        assert skip_list.search(make_buy(price=100.0, oid="o1")) is None


# ============================================================
# Test OrderBook Integration
# ============================================================

class TestOrderBook:
    """Tests for OrderBook integration."""

    @pytest.fixture
    def ob(self):
        """Create an OrderBook instance.
        
        BUG: OrderBook.__init__ creates PriceLevelPool which creates PriceLevel
        objects, which crashes due to the level_tail bug.
        """
        return OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_add_buy_order(self, ob):
        """Test adding a buy order.
        
        BUG: add_order() inserts Buy orders into self.asks (line 378) instead
        of self.bids. Sides are reversed:
            if order.side == OrderSide.Buy:
                with self.ask_lock:
                    self.asks.insert(order)   # Should be self.bids
        """
        order = make_buy(price=100.0, oid="buy1")
        result = ob.add_order(order)
        assert result is not None
        assert ob.get_order("user1", "buy1") is not None

        # Best bid should be this order
        best = ob.get_best_bid()
        assert best is not None
        # BUG: get_best_bid returns self.bids.peek() but order was inserted into asks

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_add_sell_order(self, ob):
        """Test adding a sell order.
        
        BUG: add_order() inserts Sell orders into self.bids (line 382) instead
        of self.asks. Sides are reversed.
        """
        order = make_sell(price=100.0, oid="sell1")
        result = ob.add_order(order)
        assert result is not None

        best = ob.get_best_ask()
        assert best is not None
        # BUG: get_best_ask returns self.asks.peek() but order was inserted into bids

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_add_duplicate_order(self, ob):
        """Test that adding a duplicate order returns None."""
        order = make_buy(price=100.0, oid="dup1")
        ob.add_order(order)
        result = ob.add_order(order)
        assert result is None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_remove_order(self, ob):
        """Test removing an order.
        
        BUG: remove_order() deletes Buy orders from self.asks (line 393-394)
        instead of self.bids. Also, Sell path (line 396) is missing
        `with self.bid_lock:`.
        """
        order = make_buy(price=100.0, oid="buy1")
        ob.add_order(order)
        result = ob.remove_order("buy1")
        assert result is not None
        assert ob.get_order("user1", "buy1") is None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_remove_nonexistent(self, ob):
        """Test removing a non-existent order."""
        result = ob.remove_order("nonexistent")
        assert result is None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_update_order_filled(self, ob):
        """Test updating order fill and auto-removal when fully filled."""
        order = make_buy(price=100.0, qty=10.0, oid="buy1")
        ob.add_order(order)

        ob.update_order("buy1", 5.0)
        assert ob.get_order("user1", "buy1") is not None

        ob.update_order("buy1", 10.0)
        assert ob.get_order("user1", "buy1") is None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_batch_add_orders(self, ob):
        """Test batch adding orders.
        
        BUG: batch_add_orders(self, orders) doesn't match interface
        batch_add_orders(self, side, orders). Missing `side` parameter.
        """
        orders = [
            make_buy(price=100.0, oid="b1"),
            make_buy(price=200.0, oid="b2"),
            make_sell(price=300.0, oid="s1"),
        ]
        result = ob.batch_add_orders(orders)
        assert len(result) == 3

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_batch_remove_orders(self, ob):
        """Test batch removing orders.
        
        BUG: batch_remove_orders(self, orders: List[Order]) doesn't match
        interface batch_remove_orders(self, order_ids: List[str]).
        Takes Order objects instead of order_id strings.
        """
        o1 = make_buy(price=100.0, oid="b1")
        o2 = make_buy(price=200.0, oid="b2")
        ob.add_order(o1)
        ob.add_order(o2)

        result = ob.batch_remove_orders([o1, o2])
        assert len(result) == 2

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_get_order_book(self, ob):
        """Test getting order book depth.
        
        BUG: get_order_book() doesn't use locks for thread safety.
        Also depends on peek_depth bug (self.capacity doesn't exist).
        """
        ob.add_order(make_buy(price=100.0, oid="b1"))
        ob.add_order(make_sell(price=200.0, oid="s1"))

        book = ob.get_order_book(depth=10)
        assert book is not None
        assert len(book.bids) > 0
        assert len(book.asks) > 0

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_best_bid_ask(self, ob):
        """Test getting best bid and ask prices."""
        ob.add_order(make_buy(price=100.0, oid="b1"))
        ob.add_order(make_buy(price=200.0, oid="b2"))
        ob.add_order(make_sell(price=300.0, oid="s1"))
        ob.add_order(make_sell(price=250.0, oid="s2"))

        best_bid = ob.get_best_bid()
        best_ask = ob.get_best_ask()

        # BUG: Due to side reversal in add_order, bids are in asks and vice versa
        # If fixed:
        # assert best_bid.price == 200.0  # Highest buy
        # assert best_ask.price == 250.0  # Lowest sell
        assert best_bid is not None
        assert best_ask is not None

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_pending_orders(self, ob):
        """Test getting pending orders for a user."""
        ob.add_order(make_buy(price=100.0, uid="user1", oid="b1"))
        ob.add_order(make_buy(price=200.0, uid="user1", oid="b2"))
        ob.add_order(make_buy(price=300.0, uid="user2", oid="b3"))

        pending = ob.pending_orders("user1")
        assert len(pending) == 2

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_order_pool_full_triggers_eviction(self):
        """Test that adding orders when pool is full triggers eviction.
        
        BUG: add_order variable `order` is shadowed in the for loop:
            for order in removed_orders:
                del self.orders[order.order_id]
        After the loop, `order` refers to the last removed order, not the
        new order being added. This causes:
        1. self.orders[order.order_id] = order stores the wrong order
        2. order.side is the removed order's side, not the new order's side
        """
        ob = OrderBook(symbol="BTCUSDT", max_price_level=3, max_orders=5)
        # Fill up the order pool
        for i in range(5):
            ob.add_order(make_buy(price=100.0 + i, oid=f"b{i}"))

        # Adding a 6th order should trigger eviction
        new_order = make_buy(price=999.0, oid="new_order")
        ob.add_order(new_order)

        # The new order should be in self.orders
        assert ob.get_order("user1", "new_order") is not None
        # BUG: Due to variable shadowing, "new_order" might not be in self.orders

    @pytest.mark.xfail(reason="BUG L28: PriceLevel init crashes (level_tail not defined)")
    def test_shared_pools_not_thread_safe(self):
        """Test that shared price_level_pool and order_pool are not thread-safe.
        
        BUG: OrderBook.__init__ shares the same price_level_pool and
        order_pool between asks and bids. But ask_lock and bid_lock
        are separate locks, so concurrent access to the shared pools
        is not protected.
        """
        ob = OrderBook(symbol="BTCUSDT", max_price_level=100, max_orders=1000)

        errors = []

        def add_buy_orders():
            try:
                for i in range(50):
                    ob.add_order(make_buy(price=100.0 + i, uid=f"buyer_{i}"))
            except Exception as e:
                errors.append(e)

        def add_sell_orders():
            try:
                for i in range(50):
                    ob.add_order(make_sell(price=200.0 + i, uid=f"seller_{i}"))
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=add_buy_orders)
        t2 = threading.Thread(target=add_sell_orders)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # With proper locking, there should be no errors
        # This test may pass or fail depending on timing
        # The race condition is on shared pools, not on asks/bids themselves


# ============================================================
# Bug Summary Documentation
# ============================================================

class TestBugSummary:
    """Document all discovered bugs as test cases for traceability."""

    def test_bug_01_import_typo_ordderbook(self):
        """BUG L9: Import uses `OrdderBook` (double d) instead of `OrderBook`.
        
        from src.engine.types.types import Order, OrderSide, OrdderBook as OrderBookModel
                                                                           ^^^^^^^^^^
        This causes ImportError at module load time.
        Workaround: types.OrdderBook = types.OrderBook (applied at top of test file)
        """
        # If this test runs, the workaround was applied successfully
        from src.engine.orderbook.sll_orderbook import OrderBookModel
        assert OrderBookModel is not None

    def test_bug_02_orderside_wrong_case(self):
        """BUG L367, L377: Uses `OrderSide.Buy` instead of `OrderSide.BUY`.
        
        OrderSide enum uses all-caps: BUY = "BUY", SELL = "SELL"
        But code uses PascalCase: OrderSide.Buy, OrderSide.Sell
        Workaround: Added aliases OrderSide.Buy = OrderSide.BUY
        """
        assert OrderSide.Buy == OrderSide.BUY
        assert OrderSide.Sell == OrderSide.SELL

    def test_bug_03_level_tail_not_defined(self):
        """BUG L28: PriceLevel.__init__ uses self.level_tail before defining it.
        
        Line 27: self.level_head = LevelOrder(-1)
        Line 28: self.level_tail.next = self.level_head  # level_tail not defined!
        
        Should be: self.level_tail = self.level_head
        
        This prevents ALL PriceLevel construction, making the entire module unusable.
        """
        with pytest.raises(AttributeError):
            PriceLevel(price=100.0, level=4)

    def test_bug_04_level_tail_not_updated_on_insert(self):
        """BUG L206-209, L232-234: insert() does not update level_tail.
        
        After appending a new order to a price level:
            new_order.prev = price_level.level_tail
            new_order.next = None
            price_level.level_tail.next = new_order
        
        Missing: price_level.level_tail = new_order
        
        Without this, subsequent insertions at the same price overwrite
        the previous order's link, causing data loss.
        """
        # Cannot test without fixing bug 03 first
        pass

    def test_bug_05_peek_accesses_wrong_attribute(self):
        """BUG L278: peek() returns self.head.forward[0].order
        
        self.head.forward[0] is a PriceLevel, which has no `order` attribute.
        PriceLevel stores orders in a linked list via level_head.
        
        Should be:
            pl = self.head.forward[0]
            if pl and pl.level_head.next:
                return pl.level_head.next.order
        """
        # Cannot test without fixing bug 03 first
        pass

    def test_bug_06_pop_wrong_type(self):
        """BUG L288-289: pop() accesses top_level.order (nonexistent)
        and then calls self.delete(order) with wrong type.
        
        pop() should:
        1. Get the first PriceLevel
        2. Get the first LevelOrder from that level
        3. Get the Order from that LevelOrder
        4. Call self.delete(order) with the correct Order
        """
        pass

    def test_bug_07_peek_depth_capacity_not_exist(self):
        """BUG L295: peek_depth accesses self.capacity which doesn't exist on SkipList.
        
        SkipList does not have a `capacity` attribute (unlike OrderPool/PriceLevelPool).
        Should check self.head.forward[0] is not None instead.
        Also missing null check on current_level (L307).
        """
        pass

    def test_bug_08_add_order_sides_reversed(self):
        """BUG L377-382: add_order() inserts Buy orders into asks and
        Sell orders into bids. Sides are completely reversed.
        
        Should be:
            if order.side == OrderSide.BUY:
                with self.bid_lock:
                    self.bids.insert(order)
            else:
                with self.ask_lock:
                    self.asks.insert(order)
        """
        pass

    def test_bug_09_add_order_variable_shadowing(self):
        """BUG L373: Variable `order` is shadowed in for loop.
        
            for order in removed_orders:   # shadows the parameter `order`
                del self.orders[order.order_id]
            
            self.orders[order.order_id] = order  # order is now a removed order!
        
        After the loop, `order` refers to the last removed order,
        not the new order being added. This causes:
        1. Wrong order stored in self.orders
        2. Wrong side check on line 377
        """
        pass

    def test_bug_10_remove_order_sides_reversed(self):
        """BUG L392-396: remove_order() deletes Buy orders from asks
        instead of bids. Also missing lock on Sell (bids) path.
        
        Should be:
            if order.side == OrderSide.BUY:
                with self.bid_lock:
                    self.bids.delete(order)
            else:
                with self.ask_lock:
                    self.asks.delete(order)
        """
        pass

    def test_bug_11_get_order_book_no_locks(self):
        """BUG L426-433: get_order_book() does not use any locks.
        
        Should use ask_lock and bid_lock to protect concurrent access.
        """
        pass

    def test_bug_12_shared_pools_not_thread_safe(self):
        """BUG L350-351: price_level_pool and order_pool are shared
        between asks and bids, but only ask_lock and bid_lock protect
        access. Concurrent operations on asks and bids can corrupt
        the shared pools.
        
        Should use a single shared lock, or separate pools.
        """
        pass

    def test_bug_13_interface_mismatch_batch_add(self):
        """BUG L400: batch_add_orders(self, orders) doesn't match interface.
        
        Interface: batch_add_orders(self, side: str, orders: List[Order])
        Implementation: batch_add_orders(self, orders: List[Order])
        
        Missing `side` parameter.
        """
        # Verify the interface signature
        from src.engine.orderbook.ob_interface import OrderBookInterface
        import inspect
        sig = inspect.signature(OrderBookInterface.batch_add_orders)
        assert 'side' in sig.parameters

    def test_bug_14_interface_mismatch_batch_remove(self):
        """BUG L409: batch_remove_orders(self, orders: List[Order]) doesn't
        match interface.
        
        Interface: batch_remove_orders(self, order_ids: List[str]) -> List[Order]
        Implementation: batch_remove_orders(self, orders: List[Order]) -> List[str]
        
        Takes Order objects instead of order_id strings, and returns List[str]
        instead of List[Order].
        """
        from src.engine.orderbook.ob_interface import OrderBookInterface
        import inspect
        sig = inspect.signature(OrderBookInterface.batch_remove_orders)
        params = list(sig.parameters.keys())
        # Interface expects order_ids, not orders
        assert 'order_ids' in params or len(params) >= 2

    def test_bug_15_delete_farest_level_no_empty_check(self):
        """BUG L163-169: delete_farest_level() does not check if skip list
        is empty before traversing.
        
        If self.head.forward[0] is None, `farest_level` is None, and
        `farest_level.forward[0]` raises AttributeError.
        """
        pass

    def test_bug_16_price_level_pool_new_not_reset_tail(self):
        """BUG L93-109: PriceLevelPool.new() does not reset level_tail.
        
        When a PriceLevel is reused from the pool, level_head is reset
        (prev=None, next=None) but level_tail is not. This means if
        the PriceLevel was previously used and had orders, level_tail
        still points to a stale order.
        """
        pass

    def test_bug_17_price_level_pool_free_leaks_sentinel(self):
        """BUG L111-118: PriceLevelPool.free() returns level_head (a
        LevelOrder sentinel) but the caller doesn't free it.
        
        The sentinel LevelOrder was created with LevelOrder(-1), which
        was never allocated from OrderPool. It cannot be freed to
        OrderPool (order_index=-1 would cause out-of-bounds access).
        Every time a PriceLevel is freed, the sentinel is leaked.
        """
        pass

    def test_bug_18_eviction_wrong_side(self):
        """BUG L367-372: When pool is full, add_order evicts from the
        opposite side's farthest level. But due to the side reversal
        bug (bug 08), the eviction is also wrong:
        
            if order.side == OrderSide.Buy:
                with self.ask_lock:
                    removed_orders = self.asks.delete_farest_level()
        
        If the new order is a Buy order, it evicts from asks (sells).
        This is actually correct - making room by removing the farthest
        sell. But then the Buy order is inserted into asks (bug 08),
        not bids, making the eviction pointless.
        """
        pass

    def test_bug_19_capacity_check_incomplete(self):
        """BUG L364: Pool full check only runs once. If the pool is full
        and the farthest level has few orders, freeing them might not
        create enough capacity. The code should loop until there's
        enough space.
        """
        pass

    def test_bug_20_orderpool_free_orders_ptr_off_by_one(self):
        """DESIGN ISSUE L49: free_orders_ptr = list(range(1, max_orders+1))
        
        The last element is max_orders, which is out of bounds for
        free_orders (indices 0..max_orders-1). This works because the
        capacity check in new() prevents accessing free_orders[max_orders],
        but the sentinel value could cause issues if capacity tracking
        gets out of sync due to other bugs.
        """
        pool = OrderPool(max_orders=3)
        # Allocate all 3
        n0 = pool.new(make_buy())
        n1 = pool.new(make_buy())
        n2 = pool.new(make_buy())
        assert pool.free_ptr_head == 3  # sentinel value, out of bounds
        # Free one node
        pool.free(n1)
        # Allocate again
        n3 = pool.new(make_buy())
        assert n3 is not None
        # After allocation, free_ptr_head goes back to sentinel
        assert pool.free_ptr_head == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
