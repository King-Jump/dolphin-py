"""直接运行测试，不依赖 pytest"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
random.seed(42)  # 固定随机种子以便复现

from src.engine.orderbook.sl_orderbook import SortedAskArray, SortedBidArray, OrderBook
from src.engine.types.types import Order, OrderSide, OrderType, OrderTimeInForce


def make_order(uid, side, price, timestamp, order_id=None, quantity=1.0):
    order = Order(uid, "BTCUSDT", side, OrderType.LIMIT, OrderTimeInForce.GTC,
                  quantity, price)
    if order_id:
        order.order_id = order_id
    order.timestamp = timestamp
    return order


def run_test(name, func):
    try:
        func()
        print(f"  PASS: {name}")
        return True
    except AssertionError as e:
        print(f"  FAIL: {name}")
        print(f"        {e}")
        return False
    except Exception as e:
        print(f"  ERROR: {name}")
        print(f"        {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


# ========== SortedAskArray.batch_delete 测试 ==========

def test_ask_same_price_same_timestamp():
    arr = SortedAskArray(max_size=100)
    orders = [make_order("u1", OrderSide.SELL, 100.0, 1, f"order_{i}") for i in range(10)]
    for order in orders:
        arr.insert(order)
    assert arr.size() == 10
    random.shuffle(orders)
    deleted = arr.batch_delete(orders)
    assert len(deleted) == 10, f"应删除 10 个，实际删除 {len(deleted)}：{deleted}"
    assert arr.size() == 0, f"数组应为空，实际剩余 {arr.size()}"


def test_ask_same_price_different_timestamp():
    arr = SortedAskArray(max_size=100)
    orders = [make_order("u1", OrderSide.SELL, 100.0, i, f"order_{i}") for i in range(1, 11)]
    shuffled = orders[:]
    random.shuffle(shuffled)
    for order in shuffled:
        arr.insert(order)
    assert arr.size() == 10
    random.shuffle(orders)
    deleted = arr.batch_delete(orders)
    assert len(deleted) == 10, f"应删除 10 个，实际删除 {len(deleted)}"
    assert arr.size() == 0


def test_ask_mixed_prices():
    arr = SortedAskArray(max_size=100)
    orders = []
    for price in [100.0, 101.0, 102.0]:
        for ts in range(1, 6):
            orders.append(make_order("u1", OrderSide.SELL, price, ts, f"o_{price}_{ts}"))
    shuffled = orders[:]
    random.shuffle(shuffled)
    for order in shuffled:
        arr.insert(order)
    assert arr.size() == 15
    random.shuffle(orders)
    deleted = arr.batch_delete(orders)
    assert len(deleted) == 15, f"应删除 15 个，实际删除 {len(deleted)}"
    assert arr.size() == 0


# ========== SortedBidArray.batch_delete 测试 ==========

def test_bid_same_price_same_timestamp():
    arr = SortedBidArray(max_size=100)
    orders = [make_order("u1", OrderSide.BUY, 100.0, 1, f"order_{i}") for i in range(10)]
    for order in orders:
        arr.insert(order)
    assert arr.size() == 10
    random.shuffle(orders)
    deleted = arr.batch_delete(orders)
    assert len(deleted) == 10, f"应删除 10 个，实际删除 {len(deleted)}：{deleted}"
    assert arr.size() == 0, f"数组应为空，实际剩余 {arr.size()}"


def test_bid_same_price_different_timestamp():
    arr = SortedBidArray(max_size=100)
    orders = [make_order("u1", OrderSide.BUY, 100.0, i, f"order_{i}") for i in range(1, 11)]
    shuffled = orders[:]
    random.shuffle(shuffled)
    for order in shuffled:
        arr.insert(order)
    assert arr.size() == 10
    random.shuffle(orders)
    deleted = arr.batch_delete(orders)
    assert len(deleted) == 10, f"应删除 10 个，实际删除 {len(deleted)}"
    assert arr.size() == 0


def test_bid_mixed_prices():
    arr = SortedBidArray(max_size=100)
    orders = []
    for price in [100.0, 101.0, 102.0]:
        for ts in range(1, 6):
            orders.append(make_order("u1", OrderSide.BUY, price, ts, f"o_{price}_{ts}"))
    shuffled = orders[:]
    random.shuffle(shuffled)
    for order in shuffled:
        arr.insert(order)
    assert arr.size() == 15
    random.shuffle(orders)
    deleted = arr.batch_delete(orders)
    assert len(deleted) == 15, f"应删除 15 个，实际删除 {len(deleted)}"
    assert arr.size() == 0


# ========== OrderBook 完整流程测试 ==========

def test_orderbook_batch_remove_asks():
    ob = OrderBook("BTCUSDT")
    uid = "user1"
    orders = []
    for i in range(120):
        price = 100.0 + (i % 10)
        ts = i
        orders.append(make_order(uid, OrderSide.SELL, price, ts, f"ask_{i}"))
    ob.batch_add_orders(OrderSide.SELL, orders)
    assert len(ob.orders) == 120, f"应有 120 个订单，实际 {len(ob.orders)}"
    order_ids = [o.order_id for o in orders]
    removed = ob.batch_remove_orders(uid, order_ids)
    assert len(removed) == 120, f"应删除 120 个，实际删除 {len(removed)}"
    assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"
    assert ob.near_asks.size() == 0, f"近盘应为空，实际 {ob.near_asks.size()}"
    assert ob.far_asks.size() == 0, f"远盘应为空，实际 {ob.far_asks.size()}"


def test_orderbook_batch_remove_bids():
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


def test_orderbook_batch_remove_both_sides():
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


def test_orderbook_large_batch_same_price():
    ob = OrderBook("BTCUSDT")
    uid = "user1"
    orders = [make_order(uid, OrderSide.SELL, 100.0, i, f"ask_{i}") for i in range(150)]
    ob.batch_add_orders(OrderSide.SELL, orders)
    assert len(ob.orders) == 150
    order_ids = [o.order_id for o in orders]
    removed = ob.batch_remove_orders(uid, order_ids)
    assert len(removed) == 150, f"应删除 150 个，实际删除 {len(removed)}"
    assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"
    assert ob.near_asks.size() == 0
    assert ob.far_asks.size() == 0


def test_orderbook_shuffled_remove_asks():
    """打乱删除顺序，同价同时戳卖单 — 暴露 order_id 缺失 bug"""
    ob = OrderBook("BTCUSDT")
    uid = "user1"
    orders = [make_order(uid, OrderSide.SELL, 100.0, 1, f"ask_{i}") for i in range(50)]
    ob.batch_add_orders(OrderSide.SELL, orders)
    assert len(ob.orders) == 50
    order_ids = [o.order_id for o in orders]
    random.shuffle(order_ids)  # 打乱删除顺序
    removed = ob.batch_remove_orders(uid, order_ids)
    assert len(removed) == 50, f"应删除 50 个，实际删除 {len(removed)}"
    assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"


def test_orderbook_shuffled_remove_bids():
    """打乱删除顺序，同价同时戳买单 — 暴露 order_id 缺失 bug"""
    ob = OrderBook("BTCUSDT")
    uid = "user1"
    orders = [make_order(uid, OrderSide.BUY, 100.0, 1, f"bid_{i}") for i in range(50)]
    ob.batch_add_orders(OrderSide.BUY, orders)
    assert len(ob.orders) == 50
    order_ids = [o.order_id for o in orders]
    random.shuffle(order_ids)  # 打乱删除顺序
    removed = ob.batch_remove_orders(uid, order_ids)
    assert len(removed) == 50, f"应删除 50 个，实际删除 {len(removed)}"
    assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"


def test_orderbook_bid_same_price_diff_ts_shuffled():
    """买单同价不同时戳，打乱删除顺序 — 暴露 reverse=True 导致 timestamp 排序反向 bug"""
    ob = OrderBook("BTCUSDT")
    uid = "user1"
    orders = [make_order(uid, OrderSide.BUY, 100.0, i, f"bid_{i}") for i in range(50)]
    ob.batch_add_orders(OrderSide.BUY, orders)
    assert len(ob.orders) == 50
    order_ids = [o.order_id for o in orders]
    random.shuffle(order_ids)
    removed = ob.batch_remove_orders(uid, order_ids)
    assert len(removed) == 50, f"应删除 50 个，实际删除 {len(removed)}"
    assert len(ob.orders) == 0, f"订单簿应为空，实际剩余 {len(ob.orders)}"


if __name__ == "__main__":
    print("=" * 70)
    print("测试 batch_remove_orders 漏删 bug")
    print("=" * 70)

    all_pass = True

    print("\n--- SortedAskArray.batch_delete ---")
    all_pass &= run_test("同价同时戳", test_ask_same_price_same_timestamp)
    all_pass &= run_test("同价不同时戳", test_ask_same_price_different_timestamp)
    all_pass &= run_test("混合价格", test_ask_mixed_prices)

    print("\n--- SortedBidArray.batch_delete ---")
    all_pass &= run_test("同价同时戳", test_bid_same_price_same_timestamp)
    all_pass &= run_test("同价不同时戳", test_bid_same_price_different_timestamp)
    all_pass &= run_test("混合价格", test_bid_mixed_prices)

    print("\n--- OrderBook 完整流程 ---")
    all_pass &= run_test("120卖单添加+全删", test_orderbook_batch_remove_asks)
    all_pass &= run_test("120买单添加+全删", test_orderbook_batch_remove_bids)
    all_pass &= run_test("120买+120卖添加+全删", test_orderbook_batch_remove_both_sides)
    all_pass &= run_test("150同价卖单添加+全删", test_orderbook_large_batch_same_price)
    all_pass &= run_test("50同价同时戳卖单-打乱删除", test_orderbook_shuffled_remove_asks)
    all_pass &= run_test("50同价同时戳买单-打乱删除", test_orderbook_shuffled_remove_bids)
    all_pass &= run_test("50同价不同时戳买单-打乱删除", test_orderbook_bid_same_price_diff_ts_shuffled)

    print("\n" + "=" * 70)
    if all_pass:
        print("全部通过 — 未发现 bug")
    else:
        print("存在失败用例 — bug 已确认")
    print("=" * 70)
