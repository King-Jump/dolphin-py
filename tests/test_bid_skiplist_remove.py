"""验证 BidSkipList 和 remove_order 在 compare_bid_order 语义变更后的 bug

compare_bid_order 从 "返回1=高优先级" 改为 "返回-1=高优先级"（标准比较），
但 BidSkipList.search/insert/delete 和 OrderBook.remove_order 中的 > 0 未改为 < 0。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.orderbook.sl_orderbook import OrderBook, BidSkipList
from src.engine.types.types import Order, OrderSide, OrderType, OrderTimeInForce


def make_order(price, timestamp, order_id=None, side=OrderSide.BUY):
    order = Order("u1", "BTCUSDT", side, OrderType.LIMIT, OrderTimeInForce.GTC, 1.0, price)
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


def test_skiplist_insert_and_peek():
    """BidSkipList insert 后 peek 应返回最高优先级（最高价）"""
    sl = BidSkipList(max_nodes=100)
    orders = [
        make_order(100.0, 1, "a"),
        make_order(103.0, 2, "b"),
        make_order(101.0, 3, "c"),
    ]
    for order in orders:
        sl.insert(order)

    best = sl.peek()
    assert best is not None, "peek 不应返回 None"
    assert best.price == 103.0, f"最高价应为 103.0，实际 {best.price}"


def test_skiplist_delete():
    """BidSkipList delete 应能找到并删除指定订单"""
    sl = BidSkipList(max_nodes=100)
    orders = [
        make_order(100.0, 1, "a"),
        make_order(103.0, 2, "b"),
        make_order(101.0, 3, "c"),
    ]
    for order in orders:
        sl.insert(order)

    # 删除最高价
    result = sl.delete(make_order(103.0, 2, "b"))
    assert result == True, "delete 应返回 True"
    assert sl.size() == 2, f"删除后应剩2个，实际 {sl.size()}"

    best = sl.peek()
    assert best.price == 101.0, f"删除103后最高价应为101，实际 {best.price}"


def test_skiplist_search():
    """BidSkipList search 应能找到指定订单"""
    sl = BidSkipList(max_nodes=100)
    orders = [
        make_order(100.0, 1, "a"),
        make_order(103.0, 2, "b"),
        make_order(101.0, 3, "c"),
    ]
    for order in orders:
        sl.insert(order)

    result = sl.search(make_order(101.0, 3, "c"))
    assert result is not None, "search 应找到订单 c"
    assert result.order_id == "c", f"应找到 id=c，实际 {result.order_id}"


def test_skiplist_order_descending():
    """BidSkipList 底层链表应按降序排列"""
    sl = BidSkipList(max_nodes=100)
    orders = [
        make_order(100.0, 1, "a"),
        make_order(103.0, 2, "b"),
        make_order(101.0, 3, "c"),
        make_order(102.0, 4, "d"),
    ]
    for order in orders:
        sl.insert(order)

    # 遍历底层链表
    prices = []
    current = sl.head.forward[0]
    while current:
        prices.append(current.order.price)
        current = current.forward[0]

    assert prices == [103.0, 102.0, 101.0, 100.0], f"降序错误: {prices}"


def test_remove_order_with_far_end():
    """remove_order 在远盘有订单时应能正确删除近盘和远盘订单"""
    ob = OrderBook("BTCUSDT", max_nodes=10000)
    uid = "user1"

    # 添加超过 MAX_NEAR_SIZE 的订单，使部分进入远盘
    orders = []
    for i in range(1200):
        price = 100.0 + (i % 100)
        ts = i
        orders.append(make_order(price, ts, f"bid_{i}"))

    ob.batch_add_orders(OrderSide.BUY, orders)
    assert len(ob.orders) == 1200, f"应有1200订单，实际 {len(ob.orders)}"
    assert ob.far_bids.size() > 0, "远盘应有订单"

    # 删除一个近盘订单（高优先级）
    near_best = ob.near_bids.peek()
    near_order = ob.orders[near_best]
    removed = ob.remove_order(near_best)
    assert removed is not None, f"应能删除近盘订单 {near_best}"
    assert near_best not in ob.orders, "近盘订单应从 orders 删除"

    # 删除一个远盘订单
    # 远盘订单是优先级较低的，找一个远盘中的订单
    far_best = ob.far_bids.peek()
    if far_best:
        far_order_id = far_best.order_id
        removed = ob.remove_order(far_order_id)
        assert removed is not None, f"应能删除远盘订单 {far_order_id}"
        assert far_order_id not in ob.orders, "远盘订单应从 orders 删除"


def test_remove_order_ask_far_end():
    """remove_order 卖单远盘也应正常工作"""
    ob = OrderBook("BTCUSDT", max_nodes=10000)
    uid = "user1"

    orders = []
    for i in range(1200):
        price = 100.0 + (i % 100)
        ts = i
        orders.append(make_order(price, ts, f"ask_{i}", side=OrderSide.SELL))

    ob.batch_add_orders(OrderSide.SELL, orders)
    assert len(ob.orders) == 1200
    assert ob.far_asks.size() > 0, "远盘应有订单"

    # 删除近盘
    near_best = ob.near_asks.peek()
    removed = ob.remove_order(near_best)
    assert removed is not None, f"应能删除近盘卖单 {near_best}"

    # 删除远盘
    far_best = ob.far_asks.peek()
    if far_best:
        far_id = far_best.order_id
        removed = ob.remove_order(far_id)
        assert removed is not None, f"应能删除远盘卖单 {far_id}"


if __name__ == "__main__":
    print("=" * 70)
    print("验证 BidSkipList 和 remove_order")
    print("=" * 70)

    all_pass = True

    print("\n--- BidSkipList ---")
    all_pass &= run_test("insert + peek 最高价", test_skiplist_insert_and_peek)
    all_pass &= run_test("delete 指定订单", test_skiplist_delete)
    all_pass &= run_test("search 指定订单", test_skiplist_search)
    all_pass &= run_test("底层链表降序", test_skiplist_order_descending)

    print("\n--- remove_order (远盘有订单) ---")
    all_pass &= run_test("买单近盘+远盘删除", test_remove_order_with_far_end)
    all_pass &= run_test("卖单近盘+远盘删除", test_remove_order_ask_far_end)

    print("\n" + "=" * 70)
    if all_pass:
        print("全部通过")
    else:
        print("存在失败用例 — bug 已确认")
    print("=" * 70)
