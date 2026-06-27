from typing import Tuple

def get_base_quote(symbol: str) -> Tuple[str, str]:
    """ 获取交易对的基币和引币 """
    if symbol == '90000001':
        return 'BTC', 'USDT'
    if symbol == '90000002':
        return 'ETH', 'USDT'
    if symbol == '90000003':
        return 'JPM', 'USDT'
    
    return None, None
