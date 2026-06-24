"""验证 SortedBidArray 的 insert/delete 方法在 _compare 语义变更后的 bug

用户将 _compare 从 "返回1表示高优先级" 改为 "返回-1表示高优先级"（标准比较函数语义），
并正确更新了 batch_insert/batch_delete 的分支条件。
但 _bisearch、insert、delete 中的二分搜索方向未同步更新，导致：
  - insert 将订单插入错误位置
  - delete 无法找到并删除订单
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.orderbook.sl_orderbook import SortedBidArray, SortedAskArray
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


def test_bid_insert_order():
    """insert 后验证数组是否按降序排列"""
    arr = SortedBidArray(max_size=10)
    orders = [
        make_order(100.0, 1, "a"),
        make_order(102.0, 2, "b"),
        make_order(101.0, 3, "c"),
        make_order(100.0, 2, "d"),  # 同价不同时戳
    ]
    for order in orders:
        arr.insert(order)

    # 验证数组顺序：降序价格，同价升序 timestamp
    prices_ts = [(arr._values[i][1], arr._values[i][2]) for i in range(arr.size())]
    expected = [(102.0, 2), (101.0, 3), (100.0, 1), (100.0, 2)]
    assert prices_ts == expected, f"数组顺序错误: {prices_ts}, 期望: {expected}"


def test_bid_insert_same_price():
    """同价订单 insert 后验证 timestamp 升序"""
    arr = SortedBidArray(max_size=10)
    orders = [
        make_order(100.0, 3, "c"),
        make_order(100.0, 1, "a"),
        make_order(100.0, 2, "b"),
    ]
    for order in orders:
        arr.insert(order)

    timestamps = [arr._values[i][2] for i in range(arr.size())]
    assert timestamps == [1, 2, 3], f"timestamp 顺序错误: {timestamps}, 期望: [1, 2, 3]"


def test_bid_delete_order():
    """insert 后 delete 能否正确找到并删除"""
    arr = SortedBidArray(max_size=10)
    orders = [
        make_order(100.0, 1, "a"),
        make_order(102.0, 2, "b"),
        make_order(101.0, 3, "c"),
    ]
    for order in orders:
        arr.insert(order)

    # 删除中间价位的订单
    result = arr.delete(make_order(101.0, 3, "c"))
    assert result == True, "delete 应返回 True"
    assert arr.size() == 2, f"删除后应剩2个，实际 {arr.size()}"

    # 验证剩余订单
    remaining = [(arr._values[i][1], arr._values[i][2]) for i in range(arr.size())]
    assert (102.0, 2) in remaining, f"102.0 应在剩余订单中: {remaining}"
    assert (100.0, 1) in remaining, f"100.0 应在剩余订单中: {remaining}"


def test_bid_delete_same_price():
    """同价订单 delete 能否正确找到并删除"""
    arr = SortedBidArray(max_size=10)
    orders = [
        make_order(100.0, 1, "a"),
        make_order(100.0, 2, "b"),
        make_order(100.0, 3, "c"),
    ]
    for order in orders:
        arr.insert(order)

    # 删除中间的订单
    result = arr.delete(make_order(100.0, 2, "b"))
    assert result == True, "delete 应返回 True"
    assert arr.size() == 2, f"删除后应剩2个，实际 {arr.size()}"

    remaining_ids = [arr._values[i][0] for i in range(arr.size())]
    assert "a" in remaining_ids, f"a 应在剩余订单中: {remaining_ids}"
    assert "c" in remaining_ids, f"c 应在剩余订单中: {remaining_ids}"
    assert "b" not in remaining_ids, f"b 不应在剩余订单中: {remaining_ids}"


def test_bid_delete_not_found():
    """delete 不存在的订单应返回 False"""
    arr = SortedBidArray(max_size=10)
    arr.insert(make_order(100.0, 1, "a"))
    arr.insert(make_order(102.0, 2, "b"))

    result = arr.delete(make_order(101.0, 3, "x"))
    assert result == False, "delete 不存在的订单应返回 False"
    assert arr.size() == 2, f"数组大小不应变，实际 {arr.size()}"


def test_ask_insert_delete_still_works():
    """验证 AskArray 的 insert/delete 仍然正常（语义未变）"""
    arr = SortedAskArray(max_size=10)
    orders = [
        make_order(100.0, 1, "a", side=OrderSide.SELL),
        make_order(102.0, 2, "b", side=OrderSide.SELL),
        make_order(101.0, 3, "c", side=OrderSide.SELL),
    ]
    for order in orders:
        arr.insert(order)

    prices = [arr._values[i][1] for i in range(arr.size())]
    assert prices == [100.0, 101.0, 102.0], f"Ask 升序错误: {prices}"

    result = arr.delete(make_order(101.0, 3, "c", side=OrderSide.SELL))
    assert result == True
    assert arr.size() == 2


if __name__ == "__main__":
    print("=" * 70)
    print("验证 SortedBidArray insert/delete 方法")
    print("=" * 70)

    all_pass = True

    print("\n--- SortedBidArray.insert ---")
    all_pass &= run_test("insert 乱序后验证降序", test_bid_insert_order)
    all_pass &= run_test("insert 同价验证timestamp升序", test_bid_insert_same_price)

    print("\n--- SortedBidArray.delete ---")
    all_pass &= run_test("delete 中间价位订单", test_bid_delete_order)
    all_pass &= run_test("delete 同价中间订单", test_bid_delete_same_price)
    all_pass &= run_test("delete 不存在订单", test_bid_delete_not_found)

    print("\n--- SortedAskArray (对照) ---")
    all_pass &= run_test("Ask insert/delete 正常", test_ask_insert_delete_still_works)

    print("\n" + "=" * 70)
    if all_pass:
        print("全部通过")
    else:
        print("存在失败用例 — bug 已确认")
    print("=" * 70)
