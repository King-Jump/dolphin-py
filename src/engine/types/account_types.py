import time
import threading

class MarginMode:
    CROSS = 1  # 全仓
    ISOLATED = 2  # 逐仓

# default leverage is 5x
DEFAULT_LEVERAGEAGE = 5

class UniMarginAccount:
    def __init__(self, uid: str, is_inner_maker: bool = False):
        self.uid = uid
        self.is_inner_maker = is_inner_maker

        # spot balance
        self.balances = {}
        self.frozen_balances = {}
        self.version = 0
        self.uptime = int(1000 * time.time())

        # leverage balance
        self.spot_margin_mode = MarginMode.ISOLATED
        self.spot_leverage = {}
        # 以symbol为key的资产，对于全仓模式，value为资产余额；对于逐仓模式，value为该逐仓资产
        self.leverage_balance = {}
        self.leverage_position = {}
        
        # perpetual balance
        self.perpetual_positions = {}
        
        self.lock = threading.Lock()
        self.air_drop()

    def get_margin_level(self) -> float:
        """ 保证金水平 = 全仓杠杆账户资产总额 / (负债总额 + 未偿利息)
        """
        if self.margin_mode == MarginMode.CROSS:
            return self.balances['USDT'] / (self.balances['BTC'] * self.spot_leverage)
        else:
            return self.balances['USDT'] / (self.balances['BTC'] * self.spot_leverage)

    def set_leverage(self, symbol: str, leverage: int):
        """ 设置杠杆倍数
            :param symbol: 币对
            :param leverage: 杠杆倍数
        """
        if leverage <= 1 or leverage > 100:
            raise ValueError("leverage must be greater than 1 and less than 100")

        if self.spot_margin_mode == MarginMode.ISOLATED:
            self.spot_leverage[symbol] = leverage
        else:
            self.spot_leverage['ACCOUNT'] = leverage

    def max_borrow_amount(self, symbol_price: dict, collateral_rate: dict) -> float:
        """ 计算最大可借款金额
            :param symbol_price: 所有币对的最新价格(指数价格)，逐仓则只有一个symbol
            :param collateral_rate: 所有币对的折算率(haircut / collateral rate)
            :return: 最大可借款金额
        """
        max_borrow_amount = 0
        if self.spot_margin_mode == MarginMode.ISOLATED:
            # 逐仓：最大可借 = 逐仓净资产 × (该档最大杠杆倍数 n − 1) − 已借未还
            last_price = symbol_price.get(symbol, 0)
            # symbolUSDT代表每个symbol逐仓独立的USDT资产
            total_equity = self.leverage_balance.get(f'{symbol}USDT', 0) + last_price * self.leverage_balance.get(symbol, 0)
            total_borrowed = self.leverage_position.get(f'{symbol}USDT', 0) + last_price * self.leverage_position.get(symbol, 0)
            max_borrow_amount = total_equity * (self.spot_leverage.get(symbol, DEFAULT_LEVERAGEAGE) - 1) - total_borrowed
        else:
            # 全仓：最大可借 ≈ 全仓净资产 × (杠杆倍数 − 1) - 已借未还
            # 全仓分子经折算率（haircut / collateral rate）与指数价处理——净正持仓打折计入、负持仓按全额计负债
            total_equity = self.leverage_balance.get('USDT', 0)
            for symbol, qty in self.leverage_balance.items():
                total_equity += symbol_price.get(symbol, 0) * qty * collateral_rate.get(symbol, 0)

            total_borrowed = self.leverage_position.get('USDT', 0)
            for symbol, qty in self.leverage_position.items():
                total_borrowed += qty * symbol_price.get(symbol, 0)
            max_borrow_amount = total_equity * (self.spot_leverage.get('ACCOUNT', DEFAULT_LEVERAGEAGE) - 1) - total_borrowed

        return max_borrow_amount

    def air_drop(self):
        with self.lock:
            self.balances['USDT'] = 1_000_000_000
            self.balances['BTC'] = 10_000
            self.balances['ETH'] = 100_000
            self.balances['JPM'] = 1_000_000_000

    def get_spot_leverage(self) -> float:
        return self.spot_leverage

    def set_spot_leverage(self, leverage: float):
        with self.lock:
            self.spot_leverage = leverage

    def get_margin_mode(self) -> MarginMode:
        return self.margin_mode

    def set_margin_mode(self, margin_mode: MarginMode):
        with self.lock:
            self.margin_mode = margin_mode

    def add_balance(self, asset: str, amount: float):
        with self.lock:
            if asset not in self.balances:
                self.balances[asset] = 0
            self.balances[asset] += amount

    def sub_balance(self, asset: str, amount: float):
        with self.lock:
            self.balances[asset] -= amount
    
    def add_frozen_balance(self, order_id: str, asset: str, amount: float):
        """ 用户铺新订单时，冻结资产
        """
        with self.lock:
            if order_id not in self.frozen_balances:
                self.frozen_balances[order_id] = {
                    'settle_num': 0
                }
            self.frozen_balances[order_id][asset] += amount
            self.balances[asset] -= amount
    
    def sub_frozen_balance(self, order_id: str, asset: str, amount: float) -> bool:
        """ 订单成交或者撤单后，释放冻结资产
        """
        with self.lock:
            if self.frozen_balances[order_id][asset] < amount:
                return False
            self.frozen_balances[order_id][asset] -= amount
            self.frozen_balances[order_id]['settle_num'] += 1
            return True

    def free_frozen_balance(self, order_id: str):
        with self.lock:
            del self.frozen_balances[order_id]

    def borrow(self, symbol: str, side: str, amount: float):
        """ 借款
            :param symbol: 币对
            :param side: 借款方向，BUY借入USDT，SELL借出BASE coin
            :param amount: 借款金额
        """
        if side == 'BUY':
            key = f'{symbol}USDT' if self.margin_mode == MarginMode.ISATED else 'BUY'
        else:
            key = symbol

        with self.lock:
            if key not in self.leverage_balance:
                self.leverage_balance[key] = 0
            self.leverage_balance[key] += amount



class Position:
    def __init__(self, symbol: str, side: str, amount: float, price: float, leverage: float):
        self.symbol = symbol
        self.side = side
        self.amount = amount
        self.price = price
        self.leverage = leverage
        self.position_id = f"{symbol}_{side}_{amount}_{price}_{leverage}"
        self.position_type = "spot"
        self.position_status = "open"
        self.position_time = int(1000 * time.time())