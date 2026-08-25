"""
backtest_tools.py - 回测工具模块

功能：
1. 交易模拟
2. 持仓管理
3. 组合价值计算

设计原则：
- 函数功能单一、最小粒度
- 纯函数，无副作用
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Position:
    """持仓记录

    Attributes:
        code:        股票代码，如 '000001.SZ'
        shares:      持仓股数（股）
        entry_price: 建仓均价（元），加仓时自动更新为加权均价
        entry_date:  初次建仓日期，格式 'YYYY-MM-DD'
        hold_days:   已持有天数，默认 0
    """
    code: str
    shares: int
    entry_price: float
    entry_date: str
    hold_days: int = 0

    def __repr__(self) -> str:
        return (f"Position(code={self.code!r}, shares={self.shares}, "
                f"entry_price={self.entry_price}, entry_date={self.entry_date!r}, "
                f"hold_days={self.hold_days})")


@dataclass
class TradeResult:
    """单笔交易执行结果

    Attributes:
        success:      是否成交，False 时 reason 字段说明原因
        code:         股票代码
        action:       交易方向，'BUY' 或 'SELL'
        price:        成交价格（元）
        quantity:     成交数量（股）
        cost:         买入总成本，含手续费（元）；卖出时为 0
        fee:          本次手续费（元）
        net_proceeds: 卖出净收款，已扣手续费（元）；买入时为 0
        reason:       失败原因描述；成功时为空字符串
        position:     交易后该股票的最新持仓；清仓后为 None
    """
    success: bool
    code: str
    action: str
    price: float
    quantity: int
    cost: float = 0.0
    fee: float = 0.0
    net_proceeds: float = 0.0
    reason: str = ""
    position: Position = None

    def __repr__(self) -> str:
        return (f"TradeResult(success={self.success}, code={self.code!r}, "
                f"action={self.action!r}, price={self.price}, quantity={self.quantity}, "
                f"cost={self.cost}, fee={self.fee}, net_proceeds={self.net_proceeds}, "
                f"reason={self.reason!r}, position={self.position!r})")


def simulate_trade(action: str, price: float, quantity: int, fee_rate: float = 0.0003) -> Dict:
    """模拟单笔交易，计算成本与手续费

    买入：总成本 = 价格 × 数量 × (1 + 手续费率)
    卖出：净收款 = 价格 × 数量 × (1 - 手续费率)

    Args:
        action:   交易方向，'BUY' 或 'SELL'（大小写不敏感）
        price:    成交价格（元）
        quantity: 成交数量（股）
        fee_rate: 手续费率，默认 0.0003（即万三）

    Returns:
        Dict:
            - cost (float):         买入总成本（元）；卖出时为 0
            - fee (float):          手续费（元）
            - net_proceeds (float): 卖出净收款（元）；买入时为 0
    """
    action = action.upper()
    fee = price * quantity * fee_rate

    if action == 'BUY':
        cost = price * quantity * (1 + fee_rate)
        return {'cost': cost, 'fee': fee, 'net_proceeds': 0}
    else:
        net = price * quantity * (1 - fee_rate)
        return {'cost': 0, 'fee': fee, 'net_proceeds': net}


def calculate_trade_cost(action: str, price: float, quantity: int, fee_rate: float = 0.0003, slippage: float = 0.0) -> float:
    """计算含滑点的交易总成本

    在手续费基础上叠加滑点：买入价上浮、卖出价下浮。
    仅返回总成本金额，不区分手续费与滑点。

    Args:
        action:   交易方向，'BUY' 或 'SELL'（大小写不敏感）
        price:    名义价格（元）
        quantity: 成交数量（股）
        fee_rate: 手续费率，默认 0.0003（万三）
        slippage: 滑点比例，默认 0.0；如 0.001 表示 0.1% 的价格偏移

    Returns:
        float: 含滑点与手续费的总成本（元）
    """
    if action.upper() == 'BUY':
        actual_price = price * (1 + slippage)
    else:
        actual_price = price * (1 - slippage)
    return actual_price * quantity * (1 + fee_rate)


def create_position(code: str, shares: int, price: float, date: str) -> Position:
    """创建新持仓记录

    Args:
        code:   股票代码，如 '000001.SZ'
        shares: 持仓股数（股）
        price:  建仓价格（元）
        date:   建仓日期，格式 'YYYY-MM-DD'

    Returns:
        Position: hold_days=0 的新持仓对象
    """
    return Position(code=code, shares=shares, entry_price=price, entry_date=date, hold_days=0)


def update_position(position: Position, days: int = 1) -> Position:
    """更新持仓持有天数

    Args:
        position: 待更新的持仓对象
        days:     本次新增天数，默认 1

    Returns:
        Position: 已更新 hold_days 的同一持仓对象（原地修改后返回）
    """
    position.hold_days += days
    return position


def get_position_value(position: Position, current_price: float) -> float:
    """计算持仓当前市值

    Args:
        position:      持仓对象
        current_price: 当前市场价格（元）

    Returns:
        float: 持仓市值 = 持股数 × 当前价（元）
    """
    return position.shares * current_price


def get_position_profit(position: Position, current_price: float) -> Tuple[float, float]:
    """计算持仓浮动盈亏

    Args:
        position:      持仓对象
        current_price: 当前市场价格（元）

    Returns:
        Tuple[float, float]:
            - float: 浮动盈亏金额（元），正数盈利，负数亏损
            - float: 浮动盈亏比例（小数），如 0.1 表示盈利 10%
    """
    profit = (current_price - position.entry_price) * position.shares
    profit_pct = (current_price - position.entry_price) / position.entry_price
    return profit, profit_pct


def calculate_portfolio_value(cash: float, positions: Dict[str, Position], prices: Dict[str, float]) -> float:
    """计算组合总价值

    总价值 = 现金 + 各持仓市值之和。
    若某股票当日无行情，则以建仓价代替当前价。

    Args:
        cash:      当前现金余额（元）
        positions: 持仓字典 {股票代码: Position}
        prices:    当日收盘价字典 {股票代码: 价格（元）}

    Returns:
        float: 组合总价值（元）
    """
    position_value = sum(
        p.shares * prices.get(p.code, p.entry_price)
        for p in positions.values()
    )
    return cash + position_value


def get_portfolio_positions(positions: Dict[str, Position]) -> List[Dict]:
    """获取组合持仓详情列表

    Args:
        positions: 持仓字典 {股票代码: Position}

    Returns:
        List[Dict]: 每个元素包含以下字段：
            - code (str):         股票代码
            - shares (int):       持仓股数
            - entry_price (float): 建仓均价（元）
            - entry_date (str):   建仓日期
            - hold_days (int):    已持有天数
    """
    return [
        {
            'code': p.code,
            'shares': p.shares,
            'entry_price': p.entry_price,
            'entry_date': p.entry_date,
            'hold_days': p.hold_days,
        }
        for p in positions.values()
    ]


def build_equity_curve(daily_values: List[Tuple[str, float]]) -> List[float]:
    """从日期-价值序列提取权益曲线

    Args:
        daily_values: 每日 (日期, 账户总价值) 的有序列表

    Returns:
        List[float]: 仅含账户总价值的权益曲线，与 metrics.py 中各函数兼容
    """
    return [value for _, value in daily_values]


def calculate_daily_returns(equity_curve: List[float]) -> List[float]:
    """计算逐日收益率序列

    Args:
        equity_curve: 权益曲线，每个元素为当日账户总价值（元）

    Returns:
        List[float]: 日收益率列表（小数形式），长度比 equity_curve 少 1；
        equity_curve 不足 2 条时返回空列表
    """
    if len(equity_curve) < 2:
        return []
    return [
        (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
        for i in range(1, len(equity_curve))
        if equity_curve[i-1] > 0
    ]


def should_buy(current_price: float, ma_short: float, ma_long: float, rsi: float = 50, rsi_oversold: float = 30) -> bool:
    """买入信号判断：均线金叉且 RSI 超卖

    同时满足以下两个条件时触发买入：
    1. 短期均线 > 长期均线（金叉，趋势向上）
    2. RSI < rsi_oversold（超卖，价格低估）

    Args:
        current_price: 当前价格（元，本函数暂未使用，预留扩展）
        ma_short:      短期均线值
        ma_long:       长期均线值
        rsi:           当前 RSI 值（0~100）
        rsi_oversold:  超卖阈值，默认 30

    Returns:
        bool: True 表示触发买入信号
    """
    return ma_short > ma_long and rsi < rsi_oversold


def should_sell(current_price: float, ma_short: float, ma_long: float, rsi: float = 50, rsi_overbought: float = 70) -> bool:
    """卖出信号判断：均线死叉或 RSI 超买

    满足以下任意一个条件时触发卖出：
    1. 短期均线 < 长期均线（死叉，趋势向下）
    2. RSI > rsi_overbought（超买，价格高估）

    Args:
        current_price:  当前价格（元，本函数暂未使用，预留扩展）
        ma_short:       短期均线值
        ma_long:        长期均线值
        rsi:            当前 RSI 值（0~100）
        rsi_overbought: 超买阈值，默认 70

    Returns:
        bool: True 表示触发卖出信号
    """
    return ma_short < ma_long or rsi > rsi_overbought


def calculate_drawdown(equity_curve: List[float]) -> List[float]:
    """计算逐日回撤序列

    对每个时间点，计算从此前最高点到当日的回撤比例。
    与 metrics.get_max_drawdown 的区别：该函数返回完整序列，可用于绘图。

    Args:
        equity_curve: 权益曲线，每个元素为当日账户总价值（元）

    Returns:
        List[float]: 与 equity_curve 等长的回撤比例序列（0~1）；
        equity_curve 为空时返回空列表
    """
    if not equity_curve:
        return []

    drawdowns = []
    peak = equity_curve[0]

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        drawdowns.append(dd)

    return drawdowns


def buy(cash: float, positions: Dict[str, Position], code: str, price: float, quantity: int, date: str, fee_rate: float = 0.0003) -> Tuple[float, Dict[str, Position], TradeResult]:
    """买入股票

    扣除买入成本后更新现金和持仓。若该股票已有持仓，以加权均价合并。
    现金不足时不成交，返回失败的 TradeResult。

    Args:
        cash:      当前现金余额（元）
        positions: 持仓字典 {股票代码: Position}，会被原地修改
        code:      股票代码，如 '000001.SZ'
        price:     买入价格（元）
        quantity:  买入数量（股）
        date:      交易日期，格式 'YYYY-MM-DD'
        fee_rate:  手续费率，默认 0.0003（万三）

    Returns:
        Tuple[float, Dict[str, Position], TradeResult]:
            - float:                     交易后现金余额（元）
            - Dict[str, Position]:       交易后持仓字典
            - TradeResult:               交易结果，success=False 时 reason='资金不足'
    """
    trade = simulate_trade('BUY', price, quantity, fee_rate)
    cost = trade['cost']

    if cash < cost:
        return cash, positions, TradeResult(
            success=False,
            code=code,
            action='BUY',
            price=price,
            quantity=quantity,
            reason='资金不足',
        )

    new_cash = cash - cost

    if code in positions:
        pos = positions[code]
        total_cost = pos.entry_price * pos.shares + cost
        new_shares = pos.shares + quantity
        new_entry_price = total_cost / new_shares
        positions[code] = Position(
            code=code,
            shares=new_shares,
            entry_price=new_entry_price,
            entry_date=pos.entry_date,
            hold_days=0,
        )
    else:
        positions[code] = Position(
            code=code,
            shares=quantity,
            entry_price=price,
            entry_date=date,
            hold_days=0,
        )

    return new_cash, positions, TradeResult(
        success=True,
        code=code,
        action='BUY',
        price=price,
        quantity=quantity,
        cost=cost,
        fee=trade['fee'],
        position=positions[code],
    )


def sell(cash: float, positions: Dict[str, Position], code: str, price: float, quantity: int, fee_rate: float = 0.0003) -> Tuple[float, Dict[str, Position], TradeResult]:
    """卖出股票

    将卖出净收款加回现金，并减少对应持仓股数。全部卖出时自动删除持仓记录。
    无持仓或持仓不足时不成交，返回失败的 TradeResult。

    Args:
        cash:      当前现金余额（元）
        positions: 持仓字典 {股票代码: Position}，会被原地修改
        code:      股票代码，如 '000001.SZ'
        price:     卖出价格（元）
        quantity:  卖出数量（股）
        fee_rate:  手续费率，默认 0.0003（万三）

    Returns:
        Tuple[float, Dict[str, Position], TradeResult]:
            - float:                     交易后现金余额（元）
            - Dict[str, Position]:       交易后持仓字典（清仓后该 code 键被删除）
            - TradeResult:               交易结果，success=False 时 reason 说明原因
    """
    if code not in positions:
        return cash, positions, TradeResult(
            success=False,
            code=code,
            action='SELL',
            price=price,
            quantity=quantity,
            reason='无持仓',
        )

    pos = positions[code]
    if pos.shares < quantity:
        return cash, positions, TradeResult(
            success=False,
            code=code,
            action='SELL',
            price=price,
            quantity=quantity,
            reason=f'持仓不足(持有{pos.shares}股)',
        )

    trade = simulate_trade('SELL', price, quantity, fee_rate)
    new_cash = cash + trade['net_proceeds']

    new_shares = pos.shares - quantity
    if new_shares == 0:
        del positions[code]
    else:
        positions[code] = Position(
            code=code,
            shares=new_shares,
            entry_price=pos.entry_price,
            entry_date=pos.entry_date,
            hold_days=pos.hold_days,
        )

    return new_cash, positions, TradeResult(
        success=True,
        code=code,
        action='SELL',
        price=price,
        quantity=quantity,
        fee=trade['fee'],
        net_proceeds=trade['net_proceeds'],
        position=positions.get(code),
    )
