from typing import Tuple
from src.engine.types.types import Market

FEE_DECIMAL = 5

def get_base_quote(symbol: str) -> Tuple[str, str]:
    """ 获取交易对的基币和引币 """
    if symbol == '90000001':
        return 'BTC', 'USDT'
    if symbol == '90000002':
        return 'ETH', 'USDT'
    if symbol == '90000003':
        return 'JPM', 'USDT'
    
    return None, None

def get_fee_rate(market: Market, symbol: str, is_maker: bool, uid: str) -> Tuple[float, int]:
    """ 获取交易对的手续费 """
    if is_maker:
        return 0.002, FEE_DECIMAL
    return 0.005, FEE_DECIMAL
