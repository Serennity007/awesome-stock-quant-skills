"""
metrics.py - 性能指标计算模块

功能：
1. 回测性能指标计算
2. 风险指标计算

设计原则：
- 函数功能单一、最小粒度
- 基于权益曲线和交易记录计算
"""

from typing import List, Dict, Tuple
from track_logger import TrackLogger

def get_max_drawdown(equity_curve: List[float]) -> Tuple[float, int, int]:
    """计算最大回撤

    遍历权益曲线，找出从最高峰到随后最低谷的最大下跌幅度（比例）。

    Args:
        equity_curve: 权益曲线，每个元素为当日账户总价值（元）

    Returns:
        Tuple[float, int, int]:
            - float: 最大回撤比例（0~1），如 0.2 表示回撤 20%
            - int:   最低谷索引（回撤结束位置）
            - int:   最高峰索引（回撤开始位置）
        equity_curve 为空时返回 (0, 0, 0)
    """
    if not equity_curve:
        return 0, 0, 0

    max_dd = 0
    max_idx, min_idx = 0, 0
    peak = equity_curve[0]
    peak_idx = 0

    for i, value in enumerate(equity_curve):
        if value > peak:
            peak, peak_idx = value, i

        dd = (peak - value) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd, max_idx, min_idx = dd, i, peak_idx

    return max_dd, max_idx, min_idx


def get_max_drawdown_pct(equity_curve: List[float]) -> float:
    """获取最大回撤比例

    get_max_drawdown 的简化版本，只返回最大回撤比例。

    Args:
        equity_curve: 权益曲线，每个元素为当日账户总价值（元）

    Returns:
        float: 最大回撤比例（0~1），equity_curve 为空时返回 0
    """
    dd, _, _ = get_max_drawdown(equity_curve)
    return dd


def get_annualized_return(total_return: float, days: int) -> float:
    """计算年化收益率

    以 252 个交易日为一年，将持有期总收益折算为年化复利收益率。
    公式：(1 + total_return) ^ (252 / days) - 1

    Args:
        total_return: 持有期总收益率（小数形式，如 0.5 表示 50%）
        days:         实际持有交易日数

    Returns:
        float: 年化收益率（小数形式）；days <= 0 时返回 0
    """
    if days <= 0:
        return 0
    years = days / 252
    if years <= 0:
        return 0
    return ((1 + total_return) ** (1 / years) - 1)


def get_total_return(initial_value: float, final_value: float) -> float:
    """计算总收益率

    Args:
        initial_value: 初始账户价值（元）
        final_value:   最终账户价值（元）

    Returns:
        float: 总收益率（小数形式，如 0.3 表示盈利 30%）；
        initial_value <= 0 时返回 0
    """
    if initial_value <= 0:
        return 0
    return (final_value - initial_value) / initial_value


def get_sharpe_ratio(equity_curve: List[float], risk_free_rate: float = 0.03) -> float:
    """计算夏普比率 (Sharpe Ratio)

    衡量策略每承担一单位风险所获得的超额收益。
    夏普比率越高越好，>1 为良好，>2 为优秀，<0 表示跑不赢无风险利率。
    公式：(日均超额收益 / 日收益标准差) * sqrt(252)

    Args:
        equity_curve:   权益曲线，每个元素为当日账户总价值（元）
        risk_free_rate: 年化无风险利率（小数形式），默认 0.03（即 3%）

    Returns:
        float: 年化夏普比率；数据不足或波动率为 0 时返回 0
    """
    if len(equity_curve) < 2:
        return 0

    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i-1] > 0:
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)

    if not returns:
        return 0

    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
    std_dev = variance ** 0.5

    if std_dev == 0:
        return 0

    daily_rf = risk_free_rate / 252
    sharpe = (avg_return - daily_rf) / std_dev * (252 ** 0.5)
    return sharpe


def get_win_rate(trades: List[Dict]) -> float:
    """计算胜率

    盈利交易笔数占总交易笔数的百分比。

    Args:
        trades: 交易记录列表，每条记录为 dict，需包含 'profit' 键（盈亏金额，元）

    Returns:
        float: 胜率百分比（0~100）；trades 为空时返回 0
    """
    if not trades:
        return 0
    wins = sum(1 for t in trades if t.get('profit', 0) > 0)
    return (wins / len(trades)) * 100


def get_profit_loss_ratio(trades: List[Dict]) -> float:
    """计算盈亏比

    平均每笔盈利 / 平均每笔亏损，反映策略的风险回报结构。
    盈亏比 > 1 表示平均盈利大于平均亏损，结合胜率共同衡量策略质量。

    Args:
        trades: 交易记录列表，每条记录为 dict，需包含 'profit' 键（盈亏金额，元）

    Returns:
        float: 盈亏比；无亏损交易时若有盈利返回 inf，否则返回 0
    """
    profits = [t['profit'] for t in trades if t.get('profit', 0) > 0]
    losses = [abs(t['profit']) for t in trades if t.get('profit', 0) < 0]

    avg_profit = sum(profits) / len(profits) if profits else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

    if avg_loss == 0:
        return float('inf') if avg_profit > 0 else 0
    return avg_profit / avg_loss


def get_calmar_ratio(equity_curve: List[float], days: int) -> float:
    """计算卡尔玛比率 (Calmar Ratio)

    年化收益率与最大回撤之比，衡量每单位最大亏损所对应的年化收益。
    卡尔玛比率越高越好，>3 为优秀。

    Args:
        equity_curve: 权益曲线，每个元素为当日账户总价值（元）
        days:         实际持有交易日数

    Returns:
        float: 卡尔玛比率；equity_curve 不足 2 条或最大回撤为 0 时返回 0
    """
    if len(equity_curve) < 2:
        return 0

    total_return = get_total_return(equity_curve[0], equity_curve[-1])
    annualized = get_annualized_return(total_return, days)
    max_dd = get_max_drawdown_pct(equity_curve)

    if max_dd == 0:
        return 0
    return annualized / max_dd


def get_volatility(equity_curve: List[float]) -> float:
    """计算年化波动率

    日收益率的标准差乘以 sqrt(252)，反映策略收益的波动程度。
    波动率越低、夏普比率越高，策略稳定性越好。

    Args:
        equity_curve: 权益曲线，每个元素为当日账户总价值（元）

    Returns:
        float: 年化波动率（小数形式，如 0.2 表示 20%）；数据不足时返回 0
    """
    if len(equity_curve) < 2:
        return 0

    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i-1] > 0:
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)

    if not returns:
        return 0

    variance = sum((r - sum(returns)/len(returns)) ** 2 for r in returns) / len(returns)
    daily_vol = variance ** 0.5
    return daily_vol * (252 ** 0.5)


def get_trade_stats(trades: List[Dict]) -> Dict:
    """统计交易明细汇总

    Args:
        trades: 交易记录列表，每条记录为 dict，需包含 'profit' 键（盈亏金额，元）

    Returns:
        Dict: 包含以下字段：
            - total_trades (int):   总交易笔数
            - wins (int):           盈利笔数
            - losses (int):         亏损笔数
            - win_rate (float):     胜率百分比（0~100）
            - profit_loss_ratio (float): 盈亏比
            - total_profit (float): 所有盈利交易的盈利总额（元）
            - total_loss (float):   所有亏损交易的亏损总额（元，负数）
            - avg_profit (float):   平均每笔盈利（元）
            - avg_loss (float):     平均每笔亏损（元，负数）
        trades 为空时各字段均返回 0
    """
    if not trades:
        return {
            'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
            'profit_loss_ratio': 0, 'total_profit': 0, 'total_loss': 0,
            'avg_profit': 0, 'avg_loss': 0,
        }

    wins = [t for t in trades if t.get('profit', 0) > 0]
    losses = [t for t in trades if t.get('profit', 0) < 0]

    return {
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': get_win_rate(trades),
        'profit_loss_ratio': get_profit_loss_ratio(trades),
        'total_profit': sum(t['profit'] for t in wins),
        'total_loss': sum(t['profit'] for t in losses),
        'avg_profit': sum(t['profit'] for t in wins) / len(wins) if wins else 0,
        'avg_loss': sum(t['profit'] for t in losses) / len(losses) if losses else 0,
    }


def generate_report(equity_curve: List[float], trades: List[Dict], initial_cash: float, days: int, track_logger:TrackLogger) -> Dict:
    """生成完整的回测绩效报告

    汇总权益曲线和交易记录，一次性计算所有常用绩效指标。

    Args:
        equity_curve: 权益曲线，每个元素为当日账户总价值（元）
        trades:       交易记录列表，每条记录为 dict，需包含 'profit' 键（盈亏金额，元）
        initial_cash: 初始资金（元）
        days:         回测持有的实际交易日数

    Returns:
        Dict: 包含以下字段：
            - initial_cash (float):          初始资金（元）
            - final_value (float):           最终账户价值（元）
            - total_return (float):          总收益率（小数）
            - total_return_pct (float):      总收益率百分比
            - annualized_return (float):     年化收益率（小数）
            - annualized_return_pct (float): 年化收益率百分比
            - max_drawdown (float):          最大回撤（小数）
            - max_drawdown_pct (float):      最大回撤百分比
            - sharpe_ratio (float):          夏普比率
            - calmar_ratio (float):          卡尔玛比率
            - volatility (float):            年化波动率（小数）
            - trading_days (int):            交易日数
            - trade_stats (Dict):            交易统计汇总，见 get_trade_stats 返回说明
    """
    final_value = equity_curve[-1] if equity_curve else initial_cash
    total_return = get_total_return(initial_cash, final_value)
    return {
        'initial_cash': initial_cash,
        'final_value': final_value,
        'total_return': total_return,
        'total_return_pct': total_return * 100,
        'annualized_return': get_annualized_return(total_return, days),
        'annualized_return_pct': get_annualized_return(total_return, days) * 100,
        'max_drawdown': get_max_drawdown_pct(equity_curve),
        'max_drawdown_pct': get_max_drawdown_pct(equity_curve) * 100,
        'sharpe_ratio': get_sharpe_ratio(equity_curve),
        'calmar_ratio': get_calmar_ratio(equity_curve, days),
        'volatility': get_volatility(equity_curve),
        'trading_days': days,
        'trade_stats': get_trade_stats(trades),
    }
