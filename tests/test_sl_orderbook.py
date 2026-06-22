"""Unit tests for sl_orderbook.py

Tests cover the following classes:
- SortedAskArray
- SortedBidArray
- BaseSortedCircularArray
- BidSortedCircularArray
- AskSortedCircularArray

Note: The source file has a bug in imports (from ast import Tuple, List)
which should be fixed to: from typing import Tuple, List
"""

import pytest
import time
import sys
import typing

# Fix the import bug in the source file temporarily
import ast
ast.Tuple = typing.Tuple
ast.List = typing.List

from src.engine.orderbook.sl_orderbook import (
    SortedAskArray,
    SortedBidArray,
    BaseSortedCircularArray,
    BidSortedCircularArray,
    AskSortedCircularArray,
)
from src.engine.types.types import Order, OrderSide, OrderType, OrderStatus


def create_order(uid: str, price: float, timestamp: int, order_id: str = None, quantity: float = 1.0) -> Order:
    """Helper function to create an order with specific price and timestamp."""
    order = Order(uid, "BTCUSDT", OrderSide.BUY, OrderType.LIMIT, quantity, price)
    if order_id:
        order.order_id = order_id
    order.timestamp = timestamp
    return order


class TestSortedAskArray:
    """Tests for SortedAskArray (ascending order by price, then by timestamp)."""

    def test_insert_empty_array(self):
        """Test inserting into an empty array."""
        arr = SortedAskArray(max_size=10)
        order = create_order(uid="uid1", price=100.0, timestamp=1)

        result = arr.insert(order)

        assert result is True
        assert arr._capacity == 1
        assert arr._values[0] == (order.order_id, 100.0, 1)

    def test_insert_multiple_orders_ascending(self):
        """Test inserting multiple orders in ascending price order."""
        arr = SortedAskArray(max_size=10)
        orders = [
            create_order(uid="uid1", price=100.0, timestamp=1),
            create_order(uid="uid2", price=101.0, timestamp=2),
            create_order(uid="uid3", price=102.0, timestamp=3),
        ]

        for order in orders:
            result = arr.insert(order)
            assert result is True

        assert arr._capacity == 3
        # Verify ascending order
        assert arr._values[0][1] == 100.0
        assert arr._values[1][1] == 101.0
        assert arr._values[2][1] == 102.0

    def test_insert_orders_out_of_order(self):
        """Test inserting orders out of order."""
        arr = SortedAskArray(max_size=10)
        orders = [
            create_order(uid="uid1", price=102.0, timestamp=1),
            create_order(uid="uid2", price=100.0, timestamp=2),
            create_order(uid="uid3", price=101.0, timestamp=3),
        ]

        for order in orders:
            result = arr.insert(order)
            assert result is True

        assert arr._capacity == 3
        # Verify ascending order
        assert arr._values[0][1] == 100.0
        assert arr._values[1][1] == 101.0
        assert arr._values[2][1] == 102.0

    def test_insert_same_price_different_timestamp(self):
        """Test inserting orders with same price but different timestamps."""
        arr = SortedAskArray(max_size=10)
        uid = "uid1"
        orders = [
            create_order(uid=uid, price=100.0, timestamp=3),
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=100.0, timestamp=2),
        ]

        for order in orders:
            result = arr.insert(order)
            assert result is True

        assert arr._capacity == 3
        # Verify timestamp order (ascending)
        assert arr._values[0][2] == 1
        assert arr._values[1][2] == 2
        assert arr._values[2][2] == 3

    def test_insert_full_array(self):
        """Test inserting into a full array returns False."""
        arr = SortedAskArray(max_size=3)
        for i in range(3):
            arr.insert(create_order(uid="uid1", price=float(i), timestamp=i))

        result = arr.insert(create_order(uid="uid1", price=100.0, timestamp=100))

        assert result is False
        assert arr._capacity == 3

    def test_batch_insert_empty_array(self):
        """Test batch inserting into an empty array."""
        arr = SortedAskArray(max_size=10)
        orders = [
            create_order(uid="uid1", price=102.0, timestamp=1),
            create_order(uid="uid2", price=100.0, timestamp=2),
            create_order(uid="uid3", price=101.0, timestamp=3),
        ]

        result, far_end_orders = arr.batch_insert(orders)

        assert result is True
        assert len(far_end_orders) == 0
        assert arr._capacity == 3
        # Verify ascending order
        assert arr._values[0][1] == 100.0
        assert arr._values[1][1] == 101.0
        assert arr._values[2][1] == 102.0

    def test_batch_insert_exceeds_max_size(self):
        """Test batch insert when orders exceed max_size."""
        arr = SortedAskArray(max_size=3)
        orders = [
            create_order(uid="uid1", price=100.0, timestamp=1),
            create_order(uid="uid2", price=101.0, timestamp=2),
            create_order(uid="uid3", price=102.0, timestamp=3),
            create_order(uid="uid4", price=103.0, timestamp=4),
        ]

        result, far_end_orders = arr.batch_insert(orders)

        assert result is True
        assert arr._capacity == 3
        assert len(far_end_orders) == 1
        # Highest price should be in far_end_orders
        assert far_end_orders[0] == orders[3].order_id

    def test_batch_insert_with_existing_orders(self):
        """Test batch insert when array already has orders."""
        arr = SortedAskArray(max_size=10)
        arr.insert(create_order(uid="uid1", price=101.0, timestamp=1))
        arr.insert(create_order(uid="uid1", price=103.0, timestamp=2))

        orders = [
            create_order(uid="uid1", price=100.0, timestamp=3),
            create_order(uid="uid1", price=102.0, timestamp=4),
            create_order(uid="uid1", price=104.0, timestamp=5),
        ]

        result, far_end_orders = arr.batch_insert(orders)

        assert result is True
        assert arr._capacity == 5
        # Verify ascending order
        for i in range(4):
            assert arr._values[i][1] < arr._values[i + 1][1]

    def test_batch_delete_existing_orders(self):
        """Test batch deleting existing orders."""
        uid = "uid1"
        arr = SortedAskArray(max_size=10)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=101.0, timestamp=2),
            create_order(uid=uid, price=102.0, timestamp=3),    
        ]
        for order in orders:
            arr.insert(order)

        deleted = arr.batch_delete([orders[0], orders[2]])

        assert len(deleted) == 2
        assert orders[0].order_id in deleted
        assert orders[2].order_id in deleted
        assert arr._capacity == 1

    def test_batch_delete_non_existing_orders(self):
        """Test batch deleting non-existing orders."""
        uid = "uid1"
        arr = SortedAskArray(max_size=10)
        arr.insert(create_order(uid=uid, price=100.0, timestamp=1))

        deleted = arr.batch_delete([
            create_order(uid=uid, price=999.0, timestamp=999),
        ])

        assert len(deleted) == 0
        assert arr._capacity == 1


class TestSortedBidArray:
    """Tests for SortedBidArray (descending order by price, then by timestamp ascending)."""

    def test_insert_empty_array(self):
        """Test inserting into an empty array."""
        arr = SortedBidArray(max_size=10)
        order = create_order(uid="uid1", price=100.0, timestamp=1)

        result = arr.insert(order)

        assert result is True
        assert arr._capacity == 1
        assert arr._values[0] == (order.order_id, 100.0, 1)

    def test_insert_multiple_orders_descending(self):
        """Test inserting multiple orders in descending price order."""
        arr = SortedBidArray(max_size=10)
        uid = "uid1"
        orders = [
            create_order(uid=uid, price=102.0, timestamp=1),
            create_order(uid=uid, price=101.0, timestamp=2),
            create_order(uid=uid, price=100.0, timestamp=3),
        ]

        for order in orders:
            result = arr.insert(order)
            assert result is True

        assert arr._capacity == 3
        # Verify descending order
        assert arr._values[0][1] == 102.0
        assert arr._values[1][1] == 101.0
        assert arr._values[2][1] == 100.0

    def test_insert_orders_out_of_order(self):
        """Test inserting orders out of order."""
        arr = SortedBidArray(max_size=10)
        uid = "uid1"
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=102.0, timestamp=2),
            create_order(uid=uid, price=101.0, timestamp=3),
        ]

        for order in orders:
            result = arr.insert(order)
            assert result is True

        assert arr._capacity == 3
        # Verify descending order
        assert arr._values[0][1] == 102.0
        assert arr._values[1][1] == 101.0
        assert arr._values[2][1] == 100.0

    def test_insert_same_price_different_timestamp(self):
        """Test inserting orders with same price but different timestamps."""
        arr = SortedBidArray(max_size=10)
        uid = "uid1"
        orders = [
            create_order(uid=uid, price=100.0, timestamp=3),
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=100.0, timestamp=2),
        ]

        for order in orders:
            result = arr.insert(order)
            assert result is True

        assert arr._capacity == 3
        # Verify timestamp order (ascending for same price)
        assert arr._values[0][2] == 1
        assert arr._values[1][2] == 2
        assert arr._values[2][2] == 3

    def test_insert_full_array(self):
        """Test inserting into a full array returns False."""
        uid = "uid1"
        arr = SortedBidArray(max_size=3)
        for i in range(3):
            arr.insert(create_order(uid=uid, price=float(i), timestamp=i))

        result = arr.insert(create_order(uid=uid, price=100.0, timestamp=100))

        assert result is False
        assert arr._capacity == 3

    def test_batch_insert_empty_array(self):
        """Test batch inserting into an empty array."""
        uid = "uid1"
        arr = SortedBidArray(max_size=10)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=102.0, timestamp=2),
            create_order(uid=uid, price=101.0, timestamp=3),
        ]

        result, far_end_orders = arr.batch_insert(orders)

        assert result is True
        assert len(far_end_orders) == 0
        assert arr._capacity == 3
        # Verify descending order
        assert arr._values[0][1] == 102.0
        assert arr._values[1][1] == 101.0
        assert arr._values[2][1] == 100.0

    def test_batch_insert_exceeds_max_size(self):
        """Test batch insert when orders exceed max_size."""
        uid = "uid1"
        arr = SortedBidArray(max_size=3)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=101.0, timestamp=2),
            create_order(uid=uid, price=102.0, timestamp=3),
            create_order(uid=uid, price=103.0, timestamp=4),
        ]

        result, far_end_orders = arr.batch_insert(orders)

        assert result is True
        assert arr._capacity == 3
        assert len(far_end_orders) == 1
        # Lowest price should be in far_end_orders (for bids, we keep highest)
        assert far_end_orders[0] == orders[0].order_id

    def test_batch_insert_with_existing_orders(self):
        """Test batch insert when array already has orders."""
        uid = "uid1"
        arr = SortedBidArray(max_size=10)
        arr.insert(create_order(uid=uid, price=101.0, timestamp=1))
        arr.insert(create_order(uid=uid, price=99.0, timestamp=2))

        orders = [
            create_order(uid=uid, price=100.0, timestamp=3),
            create_order(uid=uid, price=102.0, timestamp=4),
            create_order(uid=uid, price=98.0, timestamp=5),
        ]

        result, far_end_orders = arr.batch_insert(orders)

        assert result is True
        assert arr._capacity == 5
        # Verify descending order
        for i in range(4):
            assert arr._values[i][1] > arr._values[i + 1][1]

    def test_batch_delete_existing_orders(self):
        """Test batch deleting existing orders."""
        uid = "uid1"
        arr = SortedBidArray(max_size=10)
        orders = [
            create_order(uid=uid, price=102.0, timestamp=1),
            create_order(uid=uid, price=101.0, timestamp=2),
            create_order(uid=uid, price=100.0, timestamp=3),
        ]
        for order in orders:
            arr.insert(order)

        deleted = arr.batch_delete([orders[0], orders[2]])

        assert len(deleted) == 2
        assert orders[0].order_id in deleted
        assert orders[2].order_id in deleted
        assert arr._capacity == 1


class TestBaseSortedCircularArray:
    """Tests for BaseSortedCircularArray."""

    def test_pop_empty_array(self):
        """Test popping from an empty array."""
        arr = BaseSortedCircularArray(max_size=10)

        result = arr.pop()

        assert result is None

    def test_pop_single_element(self):
        """Test popping a single element."""
        uid = "uid1"
        arr = BaseSortedCircularArray(max_size=10)
        order = create_order(uid=uid, price=100.0, timestamp=1)
        arr.orders[0] = order
        arr.tail = 1

        result = arr.pop()

        assert result == order
        assert arr.head == 1
        assert arr.orders[0] is None

    def test_pop_multiple_elements(self):
        """Test popping multiple elements in order."""
        uid = "uid1"
        arr = BaseSortedCircularArray(max_size=10)
        orders = [create_order(uid=uid, price=float(i), timestamp=i) for i in range(3)]
        for i, order in enumerate(orders):
            arr.orders[i] = order
        arr.tail = 3

        for i, order in enumerate(orders):
            result = arr.pop()
            assert result == order

        assert arr.head == 3
        assert arr.tail == 3

    def test_peek_empty_array(self):
        """Test peeking at an empty array."""
        arr = BaseSortedCircularArray(max_size=10)

        result = arr.peek()

        assert result is None

    def test_peek_non_empty_array(self):
        """Test peeking at a non-empty array."""
        uid = "uid1"
        arr = BaseSortedCircularArray(max_size=10)
        order = create_order(uid=uid, price=100.0, timestamp=1)
        arr.orders[0] = order
        arr.tail = 1

        result = arr.peek()

        assert result == order
        assert arr.head == 0  # peek should not modify the array

        uid = "uid1"
        arr = BaseSortedCircularArray(max_size=10)
        orders = [create_order(uid=uid, price=float(i), timestamp=i) for i in range(5)]
        arr = BaseSortedCircularArray(max_size=10)
        orders = [create_order(price=float(i), timestamp=i) for i in range(5)]
        for i, order in enumerate(orders):
            arr.orders[i] = order
        arr.tail = 5

        result = arr.peek_order(3)

        assert len(result) == 3
        assert result == orders[:3]

    def test_peek_order_more_than_available(self):
        """Test peeking at more orders than available."""
        arr = BaseSortedCircularArray(max_size=10)
        orders = [create_order(price=float(i), timestamp=i) for i in range(3)]
        for i, order in enumerate(orders):
            arr.orders[i] = order
        arr.tail = 3

        result = arr.peek_order(10)

        assert len(result) == 3
        assert result == orders

    def test_peek_depth(self):
        """Test peeking at order depth."""
        arr = BaseSortedCircularArray(max_size=10)
        orders = [
            create_order(price=100.0, timestamp=1, quantity=1.0),
            create_order(price=100.0, timestamp=2, quantity=1.0),
            create_order(price=101.0, timestamp=3, quantity=2.0),
        ]
        for i, order in enumerate(orders):
            arr.orders[i] = order
        arr.tail = 3

        result = arr.peek_depth(10)

        # Should aggregate orders at same price
        assert len(result) == 2
        assert result[0] == (100.0, 2.0)  # Two orders at price 100.0
        assert result[1] == (101.0, 2.0)  # One order at price 101.0

    def test_remove_from_empty_array(self):
        """Test removing from an empty array."""
        arr = BaseSortedCircularArray(max_size=10)

        result = arr.remove("non-existent-id")

        assert result is False

    def test_remove_existing_order(self):
        """Test removing an existing order."""
        uid = "uid1"
        arr = BaseSortedCircularArray(max_size=10)
        orders = [create_order(uid=uid, price=float(i), timestamp=i) for i in range(3)]
        for i, order in enumerate(orders):
            arr.orders[i] = order
        arr.tail = 3

        result = arr.remove(orders[1].order_id)

        assert result is True
        assert arr.tail == 2
        assert arr.orders[0] == orders[0]
        assert arr.orders[1] == orders[2]

    def test_remove_non_existing_order(self):
        """Test removing a non-existing order."""
        arr = BaseSortedCircularArray(max_size=10)
        orders = [create_order(price=float(i), timestamp=i) for i in range(3)]
        for i, order in enumerate(orders):
            arr.orders[i] = order
        arr.tail = 3

        result = arr.remove("non-existent-id")

        assert result is False
        assert arr.tail == 3

    def test_len(self):
        """Test __len__ method."""
        arr = BaseSortedCircularArray(max_size=10)
        assert len(arr) == 0

        uid = "uid1"
        arr = BaseSortedCircularArray(max_size=10)
        arr.orders[0] = create_order(uid=uid, price=100.0, timestamp=1)
        arr.tail = 1
        assert len(arr) == 1

        arr.orders[1] = create_order(uid=uid, price=101.0, timestamp=2)
        arr.tail = 2
        assert len(arr) == 2

    def test_circular_behavior(self):
        """Test circular array behavior when wrapping around."""
        uid = "uid1"
        arr = BaseSortedCircularArray(max_size=5)
        # Fill array
        orders = [create_order(uid=uid, price=float(i), timestamp=i) for i in range(5)]
        for i, order in enumerate(orders):
            arr.orders[i] = order
        arr.tail = 5

        # Pop 3 elements
        for _ in range(3):
            arr.pop()

        # Add 2 more elements (should wrap around)
        arr.orders[arr.tail] = create_order(uid=uid, price=100.0, timestamp=100)
        arr.tail = (arr.tail + 1) % arr.max_size
        arr.orders[arr.tail] = create_order(uid=uid, price=101.0, timestamp=101)
        arr.tail = (arr.tail + 1) % arr.max_size

        assert len(arr) == 4  # 5 - 3 + 2 = 4


class TestBidSortedCircularArray:
    """Tests for BidSortedCircularArray (descending order by price)."""

    def test_push_empty_array(self):
        """Test pushing to an empty array."""
        uid = "uid1"
        arr = BidSortedCircularArray(max_size=10)
        order = create_order(uid=uid, price=100.0, timestamp=1)

        arr.push(order)

        assert len(arr) == 1
        assert arr.orders[0] == order

    def test_push_higher_price_first(self):
        """Test pushing orders with higher price first."""
        arr = BidSortedCircularArray(max_size=10)
        uid = "uid1"
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=99.0, timestamp=2),
            create_order(uid=uid, price=98.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3
        # Verify descending order
        assert arr.orders[0].price == 100.0
        assert arr.orders[1].price == 99.0
        assert arr.orders[2].price == 98.0

    def test_push_lower_price_first(self):
        """Test pushing orders with lower price first."""
        uid = "uid1"
        arr = BidSortedCircularArray(max_size=10)
        orders = [
            create_order(uid=uid, price=98.0, timestamp=1),
            create_order(uid=uid, price=99.0, timestamp=2),
            create_order(uid=uid, price=100.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3
        # Verify descending order
        assert arr.orders[0].price == 100.0
        assert arr.orders[1].price == 99.0
        assert arr.orders[2].price == 98.0

    def test_push_same_price_different_timestamp(self):
        """Test pushing orders with same price but different timestamps."""
        uid = "uid1"
        arr = BidSortedCircularArray(max_size=10)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=3),
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=100.0, timestamp=2),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3
        # Verify timestamp order (ascending for same price)
        assert arr.orders[0].timestamp == 1
        assert arr.orders[1].timestamp == 2
        assert arr.orders[2].timestamp == 3

    def test_push_full_array_discard_lower_price(self):
        """Test that pushing to a full array discards lower price orders."""
        uid = "uid1"
        arr = BidSortedCircularArray(max_size=3)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=99.0, timestamp=2),
            create_order(uid=uid, price=98.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3

        # Push a lower price order
        lower_order = create_order(uid=uid, price=97.0, timestamp=4)
        arr.push(lower_order)

        # Lower price order should be discarded
        assert lower_order.status == OrderStatus.CANCELLED
        assert len(arr) == 3

    def test_push_full_array_accept_higher_price(self):
        """Test that pushing to a full array accepts higher price orders."""
        uid = "uid1"
        arr = BidSortedCircularArray(max_size=3)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=99.0, timestamp=2),
            create_order(uid=uid, price=98.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3

        # Push a higher price order
        higher_order = create_order(uid=uid, price=101.0, timestamp=4)
        arr.push(higher_order)

        # Higher price order should be accepted
        assert higher_order.status != OrderStatus.CANCELLED
        assert len(arr) == 3
        # Verify the lowest price order was removed
        assert arr.orders[2].price == 99.0


class TestAskSortedCircularArray:
    """Tests for AskSortedCircularArray (ascending order by price)."""

    def test_push_empty_array(self):
        """Test pushing to an empty array."""
        uid = "uid1"
        arr = AskSortedCircularArray(max_size=10)
        order = create_order(uid=uid, price=100.0, timestamp=1)

        arr.push(order)

        assert len(arr) == 1
        assert arr.orders[0] == order

    def test_push_lower_price_first(self):
        """Test pushing orders with lower price first."""
        uid = "uid1"
        arr = AskSortedCircularArray(max_size=10)
        orders = [
            create_order(uid=uid, price=98.0, timestamp=1),
            create_order(uid=uid, price=99.0, timestamp=2),
            create_order(uid=uid, price=100.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3
        # Verify ascending order
        assert arr.orders[0].price == 98.0
        assert arr.orders[1].price == 99.0
        assert arr.orders[2].price == 100.0

    def test_push_higher_price_first(self):
        """Test pushing orders with higher price first."""
        uid = "uid1"
        arr = AskSortedCircularArray(max_size=10)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=99.0, timestamp=2),
            create_order(uid=uid, price=98.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3
        # Verify ascending order
        assert arr.orders[0].price == 98.0
        assert arr.orders[1].price == 99.0
        assert arr.orders[2].price == 100.0

    def test_push_same_price_different_timestamp(self):
        """Test pushing orders with same price but different timestamps."""
        uid = "uid1"
        arr = AskSortedCircularArray(max_size=10)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=3),
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=100.0, timestamp=2),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3
        # Verify timestamp order (ascending for same price)
        assert arr.orders[0].timestamp == 1
        assert arr.orders[1].timestamp == 2
        assert arr.orders[2].timestamp == 3

    def test_push_full_array_discard_higher_price(self):
        """Test that pushing to a full array discards higher price orders."""
        uid = "uid1"
        arr = AskSortedCircularArray(max_size=3)
        orders = [
            create_order(uid=uid, price=98.0, timestamp=1),
            create_order(uid=uid, price=99.0, timestamp=2),
            create_order(uid=uid, price=100.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3

        # Push a higher price order
        higher_order = create_order(uid=uid, price=101.0, timestamp=4)
        arr.push(higher_order)

        # Higher price order should be discarded
        assert higher_order.status == OrderStatus.CANCELLED
        assert len(arr) == 3

    def test_push_full_array_accept_lower_price(self):
        """Test that pushing to a full array accepts lower price orders."""
        uid = "uid1"
        arr = AskSortedCircularArray(max_size=3)
        orders = [
            create_order(uid=uid, price=100.0, timestamp=1),
            create_order(uid=uid, price=99.0, timestamp=2),
            create_order(uid=uid, price=98.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        assert len(arr) == 3

        # Push a lower price order
        lower_order = create_order(uid=uid, price=97.0, timestamp=4)
        arr.push(lower_order)

        # Lower price order should be accepted
        assert lower_order.status != OrderStatus.CANCELLED
        assert len(arr) == 3
        # Verify the highest price order was removed
        assert arr.orders[2].price == 99.0


class TestBugReproduction:
    """Tests that reproduce the identified bugs."""

    def test_bug_sorted_base_array_bisearch_undefined_variable(self):
        """Bug: _bisearch uses undefined variable 'ts' and 'self.logger'."""
        arr = SortedAskArray(max_size=10)
        order1 = create_order(price=100.0, timestamp=1)
        order2 = create_order(price=100.0, timestamp=1)  # Same price and timestamp

        arr.insert(order1)

        # This should either raise NameError for 'ts' or AttributeError for 'logger'
        # when trying to insert an order with same price and timestamp
        with pytest.raises((NameError, AttributeError)):
            arr.insert(order2)

    def test_bug_sorted_base_array_delete_not_removing_element(self):
        """Bug: delete method only decrements capacity but doesn't remove element."""
        arr = SortedAskArray(max_size=10)
        order = create_order(price=100.0, timestamp=1)
        arr.insert(order)

        # After delete, the element should be removed from the array
        arr.delete(order)

        # Bug: capacity is decremented but element is still in array
        # This test will fail if the bug exists
        assert arr._values[0] == 0 or arr._values[0] is None, \
            "Bug: delete() doesn't remove the element from array"

    def test_bug_sorted_bid_array_insert_stores_object_instead_of_tuple(self):
        """Bug: SortedBidArray.insert stores Order object instead of tuple."""
        arr = SortedBidArray(max_size=10)
        order1 = create_order(price=100.0, timestamp=1)
        order2 = create_order(price=101.0, timestamp=2)

        arr.insert(order1)
        arr.insert(order2)

        # Check if stored as tuple (order_id, price, timestamp)
        # Bug: line 260 stores 'order' instead of tuple
        assert isinstance(arr._values[0], tuple), \
            "Bug: insert() stores Order object instead of tuple"
        assert isinstance(arr._values[1], tuple), \
            "Bug: insert() stores Order object instead of tuple"

    def test_bug_sorted_ask_array_insert_condition_zero(self):
        """Bug: insert method doesn't handle condition == 0 (duplicate order)."""
        arr = SortedAskArray(max_size=10)
        order = create_order(price=100.0, timestamp=1)

        arr.insert(order)

        # Try to insert the same order again
        # Bug: This should return False but might insert duplicate
        result = arr.insert(order)

        # Expected: result should be False and capacity should be 1
        # Bug: condition == 0 is not handled, so it might insert duplicate
        assert arr._capacity == 1, \
            "Bug: insert() doesn't handle duplicate orders correctly"

    def test_bug_base_sorted_circular_array_remove_tail_variable(self):
        """Bug: remove method uses old 'tail' value instead of updated self.tail."""
        arr = BaseSortedCircularArray(max_size=10)
        orders = [create_order(price=float(i), timestamp=i) for i in range(3)]
        for i, order in enumerate(orders):
            arr.orders[i] = order
        arr.tail = 3

        # Remove middle order
        arr.remove(orders[1].order_id)

        # Bug: line 437 uses 'tail' instead of 'self.tail'
        # This might cause the wrong element to be set to None
        assert arr.orders[arr.tail] is None or arr.orders[2] is None, \
            "Bug: remove() uses wrong tail variable"

    def test_bug_bid_sorted_circular_array_push_tail_not_synced(self):
        """Bug: push method updates local 'tail' but not 'self.tail' when array is full."""
        arr = BidSortedCircularArray(max_size=3)
        orders = [
            create_order(price=100.0, timestamp=1),
            create_order(price=99.0, timestamp=2),
            create_order(price=98.0, timestamp=3),
        ]

        for order in orders:
            arr.push(order)

        # Push a higher price order when array is full
        higher_order = create_order(price=101.0, timestamp=4)
        arr.push(higher_order)

        # Bug: local 'tail' is updated but self.tail might not be synced correctly
        # This could cause incorrect array length
        assert len(arr) == 3, \
            "Bug: push() doesn't sync local tail with self.tail correctly"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])