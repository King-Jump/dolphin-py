"""测试 batch_remove_orders 在同价订单场景下的漏删 bug

Bug 根因:
  SortedAskArray.batch_delete 排序键为 (price, timestamp)，缺少 order_id。
  当多个订单 price 和 timestamp 相同时，排序顺序与数组顺序不一致，
  导致双指针合并算法跳过部分订单，漏删。

  SortedBidArray.batch_delete 排序键为 (price, timestamp) + reverse=True。
  但 bid 数组中同价订单按 timestamp 升序排列（低 timestamp 在前），
  而 reverse=True 使高 timestamp 排在前，与数组顺序完全相反，导致大量漏删。
"""

import pytest
import uuid
from src.engine.orderbook.sl_orderbook import (
    SortedAskArray,
    SortedBidArray,
    OrderBook,
)
from src.engine.types.types import Order, OrderSide, OrderType, OrderTimeInForce


def make_order(uid, side, price, timestamp, order_id=None, quantity=1.0):
    """创建指定属性的订单"""
    order = Order(uid, "BTCUSDT", side, OrderType.LIMIT, OrderTimeInForce.GTC,
                  quantity, price)
    if order_id:
        order.order_id = order_id
    order.timestamp = timestamp
    return order


class TestAskBatchDeleteSamePrice:
    """测试 SortedAskArray.batch_delete 同价订单漏删"""

    def test_same_price_same_timestamp(self):
        """同价同时戳订单，batch_delete 应全部删除"""
        arr = SortedAskArray(max_size=100)
        orders = [
            make_order("u1", OrderSide.SELL, 100.0, 1, f"order_{i}")
            for i in range(10)
        ]
        for order in orders:
            arr.insert(order)

        assert arr.size() == 10

        # 打乱顺序删除
        import random
        random.shuffle(orders)
        deleted = arr.batch_delete(orders)

        assert len(deleted) == 10, f"应删除 10 个，实际删除 {len(deleted)}：{deleted}"
        assert arr.size() == 0, f"数组应为空，实际剩余 {arr.size()}"

    def test_same_price_different_timestamp(self):
        """同价不同时戳订单，batch_delete 应全部删除"""
        arr = SortedAskArray(max_size=100)
        orders = [
            make_order("u1", OrderSide.SELL, 100.0, i, f"order_{i}")
            for i in range(1, 11)
        ]
        # 打乱插入顺序
        import random
        shuffled = orders[:]
        random.shuffle(shuffled)
        for order in shuffled:
            arr.insert(order)

        assert arr.size() == 10

        random.shuffle(orders)
        deleted = arr.batch_delete(orders)

        assert len(deleted) == 10, f"应删除 10 个，实际删除 {len(deleted)}"
        assert arr.size() == 0

    def test_mixed_prices_batch_delete_all(self):
        """混合价格，批量删除全部"""
        arr = SortedAskArray(max_size=100)
        orders = []
        for price in [100.0, 101.0, 102.0]:
            for ts in range(1, 6):
                orders.append(make_order("u1", OrderSide.SELL, price, ts, f"o_{price}_{ts}"))

        import random
        shuffled = orders[:]
        random.shuffle(shuffled)
        for order in shuffled:
            arr.insert(order)

        assert arr.size() == 15

        random.shuffle(orders)
        deleted = arr.batch_delete(orders)

        assert len(deleted) == 15, f"应删除 15 个，实际删除 {len(deleted)}"
        assert arr.size() == 0


class TestBidBatchDeleteSamePrice:
    """测试 SortedBidArray.batch_delete 同价订单漏删"""

    def test_same_price_same_timestamp(self):
        """同价同时戳订单，batch_delete 应全部删除"""
        arr = SortedBidArray(max_size=100)
        orders = [
            make_order("u1", OrderSide.BUY, 100.0, 1, f"order_{i}")
            for i in range(10)
        ]
        for order in orders:
            arr.insert(order)

        assert arr.size() == 10

        import random
        random.shuffle(orders)
        deleted = arr.batch_delete(orders)

        assert len(deleted) == 10, f"应删除 10 个，实际删除 {len(deleted)}：{deleted}"
        assert arr.size() == 0, f"数组应为空，实际剩余 {arr.size()}"

    def test_same_price_different_timestamp(self):
        """同价不同时戳订单，batch_delete 应全部删除"""
        arr = SortedBidArray(max_size=100)
        orders = [
            make_order("u1", OrderSide.BUY, 100.0, i, f"order_{i}")
            for i in range(1, 11)
        ]
        import random
        shuffled = orders[:]
        random.shuffle(shuffled)
        for order in shuffled:
            arr.insert(order)

        assert arr.size() == 10

        random.shuffle(orders)
        deleted = arr.batch_delete(orders)

        assert len(deleted) == 10, f"应删除 10 个，实际删除 {len(deleted)}"
        assert arr.size() == 0

    def test_mixed_prices_batch_delete_all(self):
        """混合价格，批量删除全部"""
        arr = SortedBidArray(max_size=100)
        orders = []
        for price in [100.0, 101.0, 102.0]:
            for ts in range(1, 6):
                orders.append(make_order("u1", OrderSide.BUY, price, ts, f"o_{price}_{ts}"))

        import random
        shuffled = orders[:]
        random.shuffle(shuffled)
        for order in shuffled:
            arr.insert(order)

        assert arr.size() == 15

        random.shuffle(orders)
        deleted = arr.batch_delete(orders)

        assert len(deleted) == 15, f"应删除 15 个，实际删除 {len(deleted)}"
        assert arr.size() == 0


class TestOrderBookBatchRemove:
    """测试 OrderBook.batch_add_orders + batch_remove_orders 完整流程"""

    def test_batch_add_then_remove_all_asks(self):
        """批量添加 120 个卖单，再全部删除，验证无残留"""
        ob = OrderBook("BTCUSDT")
        uid = "user1"

        orders = []
        for i in range(120):
            price = 100.0 + (i % 10)  # 10 个价格档位，每档 12 个订单
            ts = i
            orders.append(make_order(uid, OrderSide.SELL, price, ts, f"ask_{i}"))

        ob.batch_add_orders(OrderSide.SELL, orders)

        # 确认全部入簿
        assert len(ob.orders) == 120, f"应有 120 个订单，实际 {len(ob.orders)}"

        # 全部删除
        order_ids = [o.order_id for o in orders]
        removed = ob.batch_remove_orders(uid, order_ids)

        assert len(removed) == 120, f"应删除 120 个，实际删除 {len(removed)}"
        assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"
        assert ob.near_asks.size() == 0, f"近盘应为空，实际 {ob.near_asks.size()}"
        assert ob.far_asks.size() == 0, f"远盘应为空，实际 {ob.far_asks.size()}"

    def test_batch_add_then_remove_all_bids(self):
        """批量添加 120 个买单，再全部删除，验证无残留"""
        ob = OrderBook("BTCUSDT")
        uid = "user1"

        orders = []
        for i in range(120):
            price = 100.0 + (i % 10)
            ts = i
            orders.append(make_order(uid, OrderSide.BUY, price, ts, f"bid_{i}"))

        ob.batch_add_orders(OrderSide.BUY, orders)

        assert len(ob.orders) == 120, f"应有 120 个订单，实际 {len(ob.orders)}"

        order_ids = [o.order_id for o in orders]
        removed = ob.batch_remove_orders(uid, order_ids)

        assert len(removed) == 120, f"应删除 120 个，实际删除 {len(removed)}"
        assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"
        assert ob.near_bids.size() == 0, f"近盘应为空，实际 {ob.near_bids.size()}"
        assert ob.far_bids.size() == 0, f"远盘应为空，实际 {ob.far_bids.size()}"

    def test_batch_add_then_remove_all_both_sides(self):
        """同时添加 120 买单 + 120 卖单，再全部删除"""
        ob = OrderBook("BTCUSDT")
        uid = "user1"

        bids = []
        asks = []
        for i in range(120):
            price = 100.0 + (i % 10)
            ts = i
            bids.append(make_order(uid, OrderSide.BUY, price, ts, f"bid_{i}"))
            asks.append(make_order(uid, OrderSide.SELL, price + 50, ts, f"ask_{i}"))

        ob.batch_add_orders(OrderSide.BUY, bids)
        ob.batch_add_orders(OrderSide.SELL, asks)

        assert len(ob.orders) == 240

        all_ids = [o.order_id for o in bids + asks]
        removed = ob.batch_remove_orders(uid, all_ids)

        assert len(removed) == 240, f"应删除 240 个，实际删除 {len(removed)}"
        assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"

    def test_large_batch_same_price(self):
        """同价位大量订单的添加和删除"""
        ob = OrderBook("BTCUSDT")
        uid = "user1"

        # 150 个同价卖单
        orders = [
            make_order(uid, OrderSide.SELL, 100.0, i, f"ask_{i}")
            for i in range(150)
        ]
        ob.batch_add_orders(OrderSide.SELL, orders)

        assert len(ob.orders) == 150

        order_ids = [o.order_id for o in orders]
        removed = ob.batch_remove_orders(uid, order_ids)

        assert len(removed) == 150, f"应删除 150 个，实际删除 {len(removed)}"
        assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"
        assert ob.near_asks.size() == 0
        assert ob.far_asks.size() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
