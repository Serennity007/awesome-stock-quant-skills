"""
operators.py — Alpha 101 基础运算符

所有运算符均以 pandas DataFrame 为工作单元：
  - 行（index） = 交易日期
  - 列（columns） = 股票代码

横截面运算（rank / scale / ind_neutralize）在"股票"轴（axis=1）上操作；
时间序列运算（ts_* / delay / delta / correlation 等）在"时间"轴（axis=0）上操作。

运算符命名与论文保持一致；Python 内建函数冲突时加下划线后缀（如 abs_）。
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Union

# 类型别名：行=日期，列=股票代码
Panel = pd.DataFrame

# ─────────────────────────────────────────────────────────────────────────────
# 横截面运算
# ─────────────────────────────────────────────────────────────────────────────

def rank(x: Panel) -> Panel:
    """横截面百分位排名：每个交易日内，股票间的相对排名（0~1）。"""
    return x.rank(axis=1, pct=True, na_option='keep')


def scale(x: Panel, a: float = 1.0) -> Panel:
    """横截面标准化：使每日各股绝对值之和等于 a。"""
    abs_sum = x.abs().sum(axis=1).replace(0, np.nan)
    return x.div(abs_sum, axis=0).mul(a)


def ind_neutralize(x: Panel, ind: Panel) -> Panel:
    """行业中性化：减去同日同行业均值。ind 与 x 同形，值为行业代码字符串。"""
    result = x.copy().astype(float)
    for date in x.index:
        row = x.loc[date]
        ind_row = ind.loc[date] if date in ind.index else pd.Series(dtype=str)
        if ind_row.empty:
            continue
        means = row.groupby(ind_row).transform('mean')
        result.loc[date] = row.values - means.values
    return result

# ─────────────────────────────────────────────────────────────────────────────
# 时间序列运算
# ─────────────────────────────────────────────────────────────────────────────

def delay(x: Panel, d: int) -> Panel:
    """d 期前的值。"""
    return x.shift(int(d))


def delta(x: Panel, d: int) -> Panel:
    """x 与 d 期前的差：x - delay(x, d)。"""
    return x.diff(int(d))


def ts_sum(x: Panel, d: int) -> Panel:
    """过去 d 期滚动求和（含当期）。"""
    return x.rolling(int(d), min_periods=int(d)).sum()


def mean(x: Panel, d: int) -> Panel:
    """过去 d 期滚动均值。"""
    return x.rolling(int(d), min_periods=int(d)).mean()


def stddev(x: Panel, d: int) -> Panel:
    """过去 d 期滚动标准差（样本标准差，ddof=1）。"""
    return x.rolling(int(d), min_periods=int(d)).std(ddof=1)


def ts_max(x: Panel, d: int) -> Panel:
    """过去 d 期滚动最大值。"""
    return x.rolling(int(d), min_periods=int(d)).max()


def ts_min(x: Panel, d: int) -> Panel:
    """过去 d 期滚动最小值。"""
    return x.rolling(int(d), min_periods=int(d)).min()


def ts_rank(x: Panel, d: int) -> Panel:
    """时间序列百分位排名：当期值在过去 d 期中的排名（0~1）。"""
    d = int(d)
    def _rank_last(arr: np.ndarray) -> float:
        if np.all(np.isnan(arr)):
            return np.nan
        s = pd.Series(arr)
        return float(s.rank(pct=True).iloc[-1])
    return x.rolling(d, min_periods=d).apply(_rank_last, raw=False)


def ts_argmax(x: Panel, d: int) -> Panel:
    """过去 d 期内最大值所在位置（1 = 最老，d = 最新）。"""
    d = int(d)
    return x.rolling(d, min_periods=d).apply(
        lambda a: int(np.argmax(a)) + 1, raw=True
    )


def ts_argmin(x: Panel, d: int) -> Panel:
    """过去 d 期内最小值所在位置（1 = 最老，d = 最新）。"""
    d = int(d)
    return x.rolling(d, min_periods=d).apply(
        lambda a: int(np.argmin(a)) + 1, raw=True
    )


def correlation(x: Panel, y: Panel, d: int) -> Panel:
    """各股票列的滚动 d 期皮尔逊相关系数（x 与 y 对应列）。
    当某列方差为 0（常量序列）时，相关系数未定义，填充为 0（中性值）。"""
    d = int(d)
    # pandas rolling.corr on aligned DataFrames returns element-wise corr
    result = x.rolling(d, min_periods=d).corr(y)
    # 裁剪异常值，并将未定义的 NaN（零方差）填充为 0
    return result.clip(-1, 1).fillna(0)


def covariance(x: Panel, y: Panel, d: int) -> Panel:
    """各股票列的滚动 d 期协方差。"""
    d = int(d)
    return x.rolling(d, min_periods=d).cov(y)


def decay_linear(x: Panel, d: int) -> Panel:
    """线性衰减加权移动平均：权重为 1,2,...,d（归一化后较新权重更大）。"""
    d = int(max(1, round(d)))
    weights = np.arange(1, d + 1, dtype=float)
    weights /= weights.sum()

    def _wavg(arr: np.ndarray) -> float:
        mask = ~np.isnan(arr)
        if not mask.any():
            return np.nan
        w = weights[mask]
        return float(np.dot(arr[mask], w / w.sum()))

    return x.rolling(d, min_periods=d).apply(_wavg, raw=True)


def product(x: Panel, d: int) -> Panel:
    """过去 d 期滚动乘积。"""
    return x.rolling(int(d), min_periods=int(d)).apply(np.prod, raw=True)

# ─────────────────────────────────────────────────────────────────────────────
# 逐元素运算
# ─────────────────────────────────────────────────────────────────────────────

def signedpower(x: Panel, t: float) -> Panel:
    """保号指数：sign(x) * |x|^t。"""
    return np.sign(x) * (np.abs(x) ** t)


def log(x: Panel) -> Panel:
    """自然对数（对非正值做保护性裁剪）。"""
    return np.log(x.clip(lower=1e-10))


def sign(x: Panel) -> Panel:
    return np.sign(x)


def abs_(x: Panel) -> Panel:
    return x.abs()


def adv(volume: Panel, d: int) -> Panel:
    """过去 d 日平均成交量（Average Daily Volume）。"""
    return volume.rolling(int(d), min_periods=int(d)).mean()


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────

def where(cond: Panel, a: Union[Panel, float], b: Union[Panel, float]) -> Panel:
    """三元条件：cond 为 True 时取 a，否则取 b（等价于论文中的 ? :）。"""
    if isinstance(cond, pd.DataFrame):
        result = pd.DataFrame(np.where(cond, a, b),
                              index=cond.index, columns=cond.columns)
    else:
        result = pd.DataFrame(np.where(cond, a, b))
    return result
