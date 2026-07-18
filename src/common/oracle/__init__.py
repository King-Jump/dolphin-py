
INDEX_PRICE = {}
def get_latest_index_price() -> dict:
    """ 获取所有币对的最新价格(指数价格)，暂时用最新成交价替代 """
    return INDEX_PRICE

def update_index_price(symbol: str, price: float):
    """ 更新所有币对的最新价格(指数价格)，暂时用最新成交价替代 """
    INDEX_PRICE[symbol] = price