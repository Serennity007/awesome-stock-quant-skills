"""
indicators.py - 技术指标计算模块

功能：
1. 技术指标计算（SMA, EMA, RSI, MACD, BB, ATR等100+指标）
2. 计算结果缓存到数据库
3. 默认使用复权价格（后复权）

设计原则：
- 函数功能单一、最小粒度
- 查询优先使用缓存，计算后存入数据库
- 使用data_fetcher.py获取基础数据
- 默认使用复权价格，可通过参数控制
"""
import json
from typing import Optional, Dict, List, Tuple
from sqlalchemy import text
from data_fetcher import getEngine
from data_fetcher import (
    query_daily_kline,
    query_daily_basic,
    query_stock_limit,
    query_daily_limit_list,
    query_daily_bomb_list,
)
from define import DailyKline, DailyBasic, StockLimit, DailyLimitList, DailyBombList
import math


def init_indicators_db():
    """初始化指标缓存数据库表

    创建 cached_indicators 表（如不存在），用于缓存所有指标计算结果，并建立查询索引。
    每次计算前先查缓存，命中则直接返回，避免对相同参数重复计算。
    """
    with getEngine().connect() as conn:
        conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cached_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    indicator_type TEXT NOT NULL,
                    period INTEGER,
                    use_adjusted INTEGER DEFAULT 1,
                    date TEXT NOT NULL,
                    value TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(code, indicator_type, period, use_adjusted, date)
                );
            """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_indicators_lookup ON cached_indicators(code, indicator_type, period, use_adjusted, date);"))
        conn.commit()


def _get_cached_indicator(code: str, indicator_type: str, period: int, date: str, use_adjusted: bool = True) -> Optional[str]:
    """从缓存表中查询指标值

    Args:
        code: 股票代码
        indicator_type: 指标类型字符串，如 'SMA'、'RSI'
        period: 周期参数（复合参数如MACD已编码为单个整数）
        date: 查询日期
        use_adjusted: 是否为复权计算结果

    Returns:
        str: 缓存的字符串值，未命中返回 None
    """
    with getEngine().connect() as conn:
        cursor = conn.execute(text(
            "SELECT value FROM cached_indicators WHERE code=:code AND indicator_type=:indicator_type AND period=:period AND use_adjusted=:use_adjusted AND date=:date"
        ), {"code": code, "indicator_type": indicator_type, "period": period, "use_adjusted": 1 if use_adjusted else 0, "date": date})
        row = cursor.fetchone()
        return row[0] if row else None


def _save_indicator(code: str, indicator_type: str, period: int, date: str, value: str, use_adjusted: bool = True):
    """将指标计算结果保存到缓存表

    已存在则替换（INSERT OR REPLACE），确保缓存始终为最新值。

    Args:
        code: 股票代码
        indicator_type: 指标类型字符串
        period: 周期参数
        date: 计算日期
        value: 指标值的字符串表示（float 用 str()，dict 用 str() 后 还原）
        use_adjusted: 是否为复权计算结果
    """
    with getEngine().connect() as conn:
        conn.execute(text(
            "INSERT OR REPLACE INTO cached_indicators (code, indicator_type, period, use_adjusted, date, value) VALUES (:code, :indicator_type, :period, :use_adjusted, :date, :value)"
        ), {"code": code, "indicator_type": indicator_type, "period": period, "use_adjusted": 1 if use_adjusted else 0, "date": date, "value": value})
        conn.commit()


def _get_klines_before_date(code: str, date: str, limit: int) -> List[DailyKline]:
    """获取指定日期（含）前最近 limit 根K线，按时间升序排列

    Args:
        code: 股票代码
        date: 截止日期（含）
        limit: 最多返回的K线根数

    Returns:
        List[DailyKline]: 按日期升序排列的K线列表（最新一根在末尾）
    """
    klines = query_daily_kline(
        codes=[code],
        end_date=date,
        limit=limit,
        order_by="date DESC"
    )
    return klines[::-1]


def _get_klines_range(code: str, start_date: str, end_date: str) -> List[DailyKline]:
    """获取指定日期范围内的K线，按时间升序排列

    Args:
        code: 股票代码
        start_date: 起始日期（含），格式 'YYYY-MM-DD'
        end_date: 结束日期（含），格式 'YYYY-MM-DD'

    Returns:
        List[DailyKline]: 按日期升序排列的K线列表
    """
    klines = query_daily_kline(
        codes=[code],
        start_date=start_date,
        end_date=end_date,
        order_by="date ASC"
    )
    return klines


def _get_adj_factor(code: str, date: str) -> Optional[float]:
    """获取指定日期的复权因子

    Args:
        code: 股票代码
        date: 查询日期，格式 'YYYY-MM-DD'

    Returns:
        float: 该日期的复权因子，查询不到返回 None
    """
    daily_basics = query_daily_basic(ts_codes=[code], trade_date=date)
    if daily_basics:
        return daily_basics[0].adj_factor
    return None


def _get_adj_factors_for_klines(klines: List[DailyKline]) -> Dict[str, float]:
    """批量获取K线覆盖日期范围内的所有复权因子

    Args:
        klines: K线列表，用于确定查询的日期范围和股票代码

    Returns:
        dict: {日期字符串: 复权因子} 的映射，klines 为空时返回空字典
    """
    if not klines:
        return {}
    
    code = klines[0].code
    start_date = klines[0].date
    end_date = klines[-1].date
    
    daily_basics = query_daily_basic(
        ts_codes=[code],
        start_date=start_date,
        end_date=end_date
    )
    return {basic.trade_date: basic.adj_factor for basic in daily_basics}


def _adjust_price(price: float, adj_factor: float) -> float:
    """计算后复权价格

    后复权从上市日起累积复权，公式：复权价 = 原始价 * 该日复权因子

    Args:
        price: 原始价格
        adj_factor: 该K线日期对应的复权因子

    Returns:
        float: 后复权后的价格，因子为0时原样返回原始价格
    """
    if adj_factor == 0:
        return price
    return price * adj_factor


def _adjust_klines(klines: List[DailyKline], adj_factors: Dict[str, float]) -> List[DailyKline]:
    """对K线列表执行后复权处理

    每根K线的价格字段（open/high/low/close/amount/pre_close/change）乘以对应日期的
    复权因子，成交量不做调整。

    Args:
        klines: 原始K线列表
        adj_factors: 复权因子字典 {日期字符串: 复权因子}

    Returns:
        List[DailyKline]: 复权后的新K线列表（原始列表不被修改）；
        klines 或 adj_factors 为空时直接返回原始 klines
    """
    if not klines or not adj_factors:
        return klines

    adjusted_klines = []
    for kline in klines:
        adj_factor = adj_factors.get(kline.date, 1.0)
        adjusted_kline = DailyKline(
            date=kline.date,
            code=kline.code,
            open=_adjust_price(kline.open, adj_factor),
            high=_adjust_price(kline.high, adj_factor),
            low=_adjust_price(kline.low, adj_factor),
            close=_adjust_price(kline.close, adj_factor),
            volume=kline.volume,
            amount=_adjust_price(kline.amount, adj_factor) if kline.amount else 0.0,
            adjustflag=kline.adjustflag,
            turn=kline.turn,
            pctChg=kline.pctChg,
            pre_close=_adjust_price(kline.pre_close, adj_factor) if kline.pre_close else 0.0,
            change=_adjust_price(kline.change, adj_factor) if kline.change else 0.0
        )
        adjusted_klines.append(adjusted_kline)

    return adjusted_klines


def _ema_series(values: list, period: int) -> list:
    """计算EMA序列（内部辅助函数）

    对输入数值列表计算指数移动平均，返回与输入等长的序列。
    平滑因子 k = 2 / (period + 1)，首值直接取第一个输入值。

    Args:
        values: 原始数值列表
        period: EMA 平滑周期

    Returns:
        list: 与 values 等长的 EMA 值列表；values 为空时返回空列表
    """
    if not values:
        return []
    k = 2.0 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(result[-1] + k * (v - result[-1]))
    return result


# ============================================================
# 第一梯队：最常用指标
# ============================================================

def get_sma(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """简单移动平均线 SMA（Simple Moving Average）

    对过去 period 根K线的收盘价取算术平均，是最基础的趋势跟踪指标。
    数值平滑，对价格变化反应较慢，适合判断中长期趋势方向。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 均线周期，默认20（即20日均线）
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日SMA值（元）；数据不足 period 根K线时返回 None
    """
    cached = _get_cached_indicator(code, 'SMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    sma = sum(k.close for k in klines) / period
    _save_indicator(code, 'SMA', period, date, json.dumps(sma), use_adjusted)
    return sma


def get_ema(code: str, date: str, period: int = 12, use_adjusted: bool = True) -> Optional[float]:
    """指数移动平均线 EMA（Exponential Moving Average）

    对近期价格赋予更高权重的移动平均，对价格变化比 SMA 更敏感。
    公式：EMA = 上一EMA + 乘数 * (今收盘 - 上一EMA)，乘数 = 2/(period+1)

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认12（常用12/26/9组合配合MACD）
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日EMA值（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'EMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period * 2)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    prices = [k.close for k in klines]
    ema = prices[0]
    multiplier = 2 / (period + 1)
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    
    _save_indicator(code, 'EMA', period, date, json.dumps(ema), use_adjusted)
    return ema


def get_wma(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """加权移动平均线 WMA（Weighted Moving Average）

    越近的K线权重越高（最近一天权重=period，最早一天权重=1），
    比 SMA 更快响应近期价格变化，适合短中期趋势判断。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日WMA值（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'WMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    weights = list(range(1, period + 1))
    weighted_sum = sum(k.close * w for k, w in zip(klines, weights))
    wma = weighted_sum / sum(weights)
    
    _save_indicator(code, 'WMA', period, date, json.dumps(wma), use_adjusted)
    return wma


def get_tema(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """三重指数移动平均线 TEMA（Triple Exponential Moving Average）

    TEMA = 3*EMA1 - 3*EMA2 + EMA3，通过三重EMA消除滞后，
    比单重/双重EMA对价格反应更迅速，适合短线趋势判断。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日TEMA值（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'TEMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ema1 = get_ema(code, date, period, use_adjusted)
    if ema1 is None:
        return None
    
    ema2 = get_ema(code, date, period, use_adjusted)
    if ema2 is None:
        return None
    
    ema3 = get_ema(code, date, period, use_adjusted)
    if ema3 is None:
        return None
    
    tema = 3 * ema1 - 3 * ema2 + ema3
    _save_indicator(code, 'TEMA', period, date, json.dumps(tema), use_adjusted)
    return tema


def get_rsi(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """相对强弱指数 RSI（Relative Strength Index）

    衡量过去 period 日内上涨幅度与下跌幅度的比值，反映超买超卖状态。
    取值0-100，通常 >70 视为超买，<30 视为超卖。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日RSI值（0-100）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'RSI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    gains, losses = [], []
    for i in range(1, len(klines)):
        diff = klines[i].close - klines[i-1].close
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    _save_indicator(code, 'RSI', period, date, json.dumps(rsi), use_adjusted)
    return rsi


def get_macd(code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """MACD 指数平滑异同移动平均线（Moving Average Convergence Divergence）

    MACD线 = 快线EMA - 慢线EMA，Signal线 = MACD线的EMA，柱状图 = MACD - Signal。
    用于判断价格动量和趋势转折，MACD上穿0轴为多头信号，下穿为空头信号。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        fast: 快线EMA周期，默认12
        slow: 慢线EMA周期，默认26
        signal: 信号线EMA周期，默认9（当前近似处理）
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'macd': MACD线, 'signal': 信号线, 'histogram': 柱状图}（单位：元）；
        数据不足时返回 None
    """
    period_key = fast * 10000 + slow * 100 + signal
    cached = _get_cached_indicator(code, 'MACD', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    ema_fast = get_ema(code, date, fast, use_adjusted)
    ema_slow = get_ema(code, date, slow, use_adjusted)
    
    if ema_fast is None or ema_slow is None:
        return None
    
    macd_line = ema_fast - ema_slow
    
    macd = {'macd': macd_line, 'signal': macd_line, 'histogram': 0}
    _save_indicator(code, 'MACD', period_key, date, json.dumps(macd), use_adjusted)
    return macd


def get_bollinger_bands(code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """布林带 BOLL（Bollinger Bands）

    中轨 = SMA，上轨 = 中轨 + std_dev * 标准差，下轨 = 中轨 - std_dev * 标准差。
    价格接近上轨为超买，接近下轨为超卖，带宽收窄预示行情即将爆发。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认20
        std_dev: 标准差倍数，默认2（即±2σ，覆盖约95%的波动区间）
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}（单位：元）；
        数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'BB', period, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    prices = [k.close for k in klines]
    middle = sum(prices) / period
    variance = sum((p - middle) ** 2 for p in prices) / period
    std = variance ** 0.5
    
    bb = {
        'upper': middle + std_dev * std,
        'middle': middle,
        'lower': middle - std_dev * std
    }
    _save_indicator(code, 'BB', period, date, json.dumps(bb), use_adjusted)
    return bb


def get_atr(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """平均真实波幅 ATR（Average True Range）

    对过去 period 根K线的真实波幅（TR）取简单均值，衡量市场波动性。
    TR = max(最高-最低, |最高-昨收|, |最低-昨收|)，ATR 越大说明近期波动越剧烈。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日ATR值（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'ATR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    tr_values = []
    for i in range(1, len(klines)):
        high = klines[i].high
        low = klines[i].low
        prev_close = klines[i-1].close
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)
    
    atr = sum(tr_values) / period
    _save_indicator(code, 'ATR', period, date, json.dumps(atr), use_adjusted)
    return atr

def get_mom(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """动量指标 MOM（Momentum）

    当前收盘价与 period 天前收盘价的差值，衡量价格变动的绝对速度。
    正值表示上涨动能，负值表示下跌动能，0轴穿越可作为趋势转折信号。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回溯天数，默认10
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日动量值（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'MOM', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    mom = klines[-1].close - klines[0].close
    _save_indicator(code, 'MOM', period, date, json.dumps(mom), use_adjusted)
    return mom

def get_roc(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """变动率指标 ROC（Rate of Change，%）

    (今收盘 - N日前收盘) / N日前收盘 * 100，是动量的百分比表达。
    正值表示相对N日前上涨，负值表示下跌，比 MOM 更适合横向对比不同价位股票。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回溯天数，默认10
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日ROC值（%）；数据不足或N日前收盘为0时返回 None
    """
    cached = _get_cached_indicator(code, 'ROC', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    if klines[0].close == 0:
        return None
    
    roc = ((klines[-1].close - klines[0].close) / klines[0].close) * 100
    _save_indicator(code, 'ROC', period, date, json.dumps(roc), use_adjusted)
    return roc

def get_cci(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """顺势指标 CCI（Commodity Channel Index）

    (典型价格 - SMA典型价格) / (0.015 * 平均绝对偏差)，衡量价格偏离均值的程度。
    通常 >100 视为超买，<-100 视为超卖，适合捕捉短期强弱拐点。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日CCI值（无量纲）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'CCI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    typical_prices = [(k.high + k.low + k.close) / 3 for k in klines]
    sma_tp = sum(typical_prices) / period
    mean_deviation = sum(abs(tp - sma_tp) for tp in typical_prices) / period
    
    if mean_deviation == 0:
        cci = 0.0
    else:
        cci = (typical_prices[-1] - sma_tp) / (0.015 * mean_deviation)
    
    _save_indicator(code, 'CCI', period, date, json.dumps(cci), use_adjusted)
    return cci

def get_obv(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """能量潮 OBV（On Balance Volume）

    价格上涨日累加成交量，下跌日扣减成交量，累积值反映资金流入/流出方向。
    OBV 持续上升说明主动买盘积极，用于验证价格趋势是否有量能支撑。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 统计K线根数，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日OBV累计值（手）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'OBV', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    obv = 0.0
    for i in range(1, len(klines)):
        if klines[i].close > klines[i-1].close:
            obv += klines[i].volume
        elif klines[i].close < klines[i-1].close:
            obv -= klines[i].volume
    
    _save_indicator(code, 'OBV', period, date, json.dumps(obv), use_adjusted)
    return obv

def get_volume(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """成交量统计 VOLUME

    返回当日成交量及近 period 日的均量，用于判断量能是否放大/萎缩。
    当日量 > 均量说明放量，当日量 < 均量说明缩量。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 均量计算周期，默认20
        use_adjusted: 是否使用后复权价格，默认True（不影响成交量本身）

    Returns:
        dict: {'current': 当日成交量, 'sma': period日均量}（单位：手）；
        数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'VOLUME', period, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) == 0:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    current_vol = klines[-1].volume
    sma_vol = sum(k.volume for k in klines) / len(klines)
    
    vol_data = {'current': current_vol, 'sma': sma_vol}
    _save_indicator(code, 'VOLUME', period, date, json.dumps(vol_data), use_adjusted)
    return vol_data

def get_kdj(code: str, date: str, n: int = 9, m1: int = 3, m2: int = 3, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """随机指标 KDJ

    基于 n 日内最高/最低价计算RSV（未成熟随机值），再经平滑得到K、D、J值。
    K>80 视为超买，K<20 视为超卖；J线最灵敏，常用K线与D线的交叉作为买卖信号。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        n: 计算RSV的周期，默认9
        m1: K线平滑系数（1/m1），默认3
        m2: D线平滑系数（1/m2），默认3
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'k': K值, 'd': D值, 'j': J值}（取值大致0-100，J可超出范围）；
        数据不足时返回 None
    """
    period_key = n * 10000 + m1 * 100 + m2
    cached = _get_cached_indicator(code, 'KDJ', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    klines = _get_klines_before_date(code, date, n)
    if len(klines) < n:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    low_n = min(k.low for k in klines)
    high_n = max(k.high for k in klines)
    
    if high_n - low_n == 0:
        rsv = 50.0
    else:
        rsv = ((klines[-1].close - low_n) / (high_n - low_n)) * 100
    
    k = rsv
    d = k
    j = 3 * k - 2 * d
    
    kdj = {'k': k, 'd': d, 'j': j}
    _save_indicator(code, 'KDJ', period_key, date, json.dumps(kdj), use_adjusted)
    return kdj

def get_dmi(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """趋向指标 DMI（Directional Movement Index）

    +DI 衡量上升趋势力度，-DI 衡量下降趋势力度，ADX 衡量趋势整体强弱（不含方向）。
    +DI 上穿 -DI 为买入信号，ADX>25 说明市场趋势较强。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'pdi': +DI值, 'mdi': -DI值, 'adx': ADX值}（取值0-100）；
        数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'DMI', period, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    plus_dm = 0.0
    minus_dm = 0.0
    tr_sum = 0.0
    
    for i in range(1, len(klines)):
        high_diff = klines[i].high - klines[i-1].high
        low_diff = klines[i-1].low - klines[i].low
        
        if high_diff > low_diff and high_diff > 0:
            plus_dm += high_diff
        if low_diff > high_diff and low_diff > 0:
            minus_dm += low_diff
        
        tr = max(klines[i].high - klines[i].low, 
                 abs(klines[i].high - klines[i-1].close),
                 abs(klines[i].low - klines[i-1].close))
        tr_sum += tr
    
    if tr_sum == 0:
        pdi = 0.0
        mdi = 0.0
    else:
        pdi = (plus_dm / tr_sum) * 100
        mdi = (minus_dm / tr_sum) * 100
    
    adx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0
    
    dmi = {'pdi': pdi, 'mdi': mdi, 'adx': adx}
    _save_indicator(code, 'DMI', period, date, json.dumps(dmi), use_adjusted)
    return dmi

def get_trix(code: str, date: str, period: int = 12, use_adjusted: bool = True) -> Optional[float]:
    """三重指数平滑移动平均率 TRIX（Triple Exponential Average，%）

    对收盘价连续做三次 EMA，取最后一次 EMA 的日变化率（%）。
    EMA1 = EMA(close, N)，EMA2 = EMA(EMA1, N)，EMA3 = EMA(EMA2, N)
    TRIX = (EMA3 - EMA3[prev]) / EMA3[prev] * 100
    上穿 0 轴为买入信号，下穿为卖出信号；配合 MATRIX（TRIX 的 M 日均线）使用更佳。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: EMA 周期，默认12
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日 TRIX 值（%）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'TRIX', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period * 3 + 5)
    if len(klines) < period * 3:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    closes = [k.close for k in klines]
    ema1 = _ema_series(closes, period)
    ema2 = _ema_series(ema1, period)
    ema3 = _ema_series(ema2, period)

    if len(ema3) < 2 or ema3[-2] == 0:
        return None

    trix = (ema3[-1] - ema3[-2]) / ema3[-2] * 100
    _save_indicator(code, 'TRIX', period, date, json.dumps(trix), use_adjusted)
    return trix


def get_sar(code: str, date: str, af_start: float = 0.02, af_max: float = 0.2, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """抛物线转向指标 SAR（Parabolic Stop And Reverse）

    价格上涨时 SAR 跟随在价格下方，下跌时跟随在价格上方，触碰 SAR 即为趋势反转信号。
    加速因子（af）随趋势延续逐步增大，使 SAR 越来越贴近价格。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        af_start: 加速因子初始值，默认0.02
        af_max: 加速因子最大值，默认0.2
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'sar': SAR价格（元）, 'trend': 趋势方向（1=上涨, -1=下跌）}；
        数据不足时返回 None
    """
    period_key = int(af_start * 10000 + af_max)
    cached = _get_cached_indicator(code, 'SAR', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    klines = _get_klines_before_date(code, date, 10)
    if len(klines) < 2:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    sar = klines[0].low
    trend = 1
    ep = klines[0].high
    af = af_start
    
    sar_data = {'sar': sar, 'trend': trend}
    _save_indicator(code, 'SAR', period_key, date, json.dumps(sar_data), use_adjusted)
    return sar_data


def get_williams_r(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """威廉指标 WR（Williams %R）

    (period日最高 - 今收) / (period日最高 - period日最低) * 100。
    取值0-100，接近0为超买，接近100为超卖（注意：方向与RSI相反）。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日WR值（0-100）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'WR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    high_n = max(k.high for k in klines)
    low_n = min(k.low for k in klines)
    
    if high_n - low_n == 0:
        wr = 50.0
    else:
        wr = ((high_n - klines[-1].close) / (high_n - low_n)) * 100
    
    _save_indicator(code, 'WR', period, date, json.dumps(wr), use_adjusted)
    return wr

def get_psycho(code: str, date: str, period: int = 12, use_adjusted: bool = True) -> Optional[float]:
    """心理线 PSY（Psychological Line）

    过去 period 日中上涨天数占比（%），衡量多数投资者的心理倾向。
    >75% 表示过度乐观（超买预警），<25% 表示过度悲观（超卖预警）。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 统计周期，默认12
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日PSY值（%，0-100）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'PSY', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    up_days = 0
    for i in range(1, len(klines)):
        if klines[i].close > klines[i-1].close:
            up_days += 1
    
    psy = (up_days / period) * 100
    _save_indicator(code, 'PSY', period, date, json.dumps(psy), use_adjusted)
    return psy

def get_bias(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """乖离率 BIAS（Bias Ratio，%）

    (今收盘 - N日SMA) / N日SMA * 100，衡量股价偏离均线的程度。
    正值表示价格在均线上方，负值在下方，极端偏离值常预示均值回归行情。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 均线周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日乖离率（%）；数据不足或SMA为0时返回 None
    """
    cached = _get_cached_indicator(code, 'BIAS', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    sma = get_sma(code, date, period, use_adjusted)
    klines = _get_klines_before_date(code, date, 1)
    
    if sma is None or len(klines) == 0:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    if sma == 0:
        return None
    
    bias = ((klines[-1].close - sma) / sma) * 100
    _save_indicator(code, 'BIAS', period, date, json.dumps(bias), use_adjusted)
    return bias

def get_tr(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """真实波幅 TR（True Range）

    单根K线的真实波动范围：max(最高-最低, |最高-昨收|, |最低-昨收|)。
    是计算 ATR 的基础，跳空缺口越大则 TR 值越大。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日TR值（元）；少于2根K线时返回 None
    """
    cached = _get_cached_indicator(code, 'TR', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, 2)
    if len(klines) < 2:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    high = klines[-1].high
    low = klines[-1].low
    prev_close = klines[-2].close
    
    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
    _save_indicator(code, 'TR', 1, date, json.dumps(tr), use_adjusted)
    return tr


def get_natr(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """归一化平均真实波幅 NATR（Normalized Average True Range，%）

    ATR / 当日收盘价 * 100，是 ATR 的百分比形式，
    消除了股价高低对波幅绝对值的影响，便于不同价位股票横向比较。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: ATR计算周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日NATR值（%）；数据不足或收盘价为0时返回 None
    """
    cached = _get_cached_indicator(code, 'NATR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    atr = get_atr(code, date, period, use_adjusted)
    klines = _get_klines_before_date(code, date, 1)
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    if atr is None or len(klines) == 0 or klines[-1].close == 0:
        return None
    
    natr = (atr / klines[-1].close) * 100
    _save_indicator(code, 'NATR', period, date, json.dumps(natr), use_adjusted)
    return natr


def get_vwap(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """成交量加权平均价 VWAP（Volume Weighted Average Price）

    Σ(典型价格 * 成交量) / Σ(成交量)，反映过去 period 日的成交重心。
    价格在 VWAP 上方说明多头占优，机构常以 VWAP 作为买卖基准价。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 统计周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日VWAP值（元）；成交量为0或数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'VWAP', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) == 0:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    total_pv = 0.0
    total_vol = 0.0
    
    for k in klines:
        typical_price = (k.high + k.low + k.close) / 3
        total_pv += typical_price * k.volume
        total_vol += k.volume
    
    if total_vol == 0:
        return None
    
    vwap = total_pv / total_vol
    _save_indicator(code, 'VWAP', period, date, json.dumps(vwap), use_adjusted)
    return vwap


def get_ad(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """累积/派发线 AD（Accumulation/Distribution Line）

    每日 CLV = [(收-低) - (高-收)] / (高-低)，CLV * 成交量后累加。
    CLV 衡量收盘价在当日高低范围中的位置，AD 持续上升表示主力在吸筹（积累）。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 统计K线根数，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日AD累积值（量纲：手）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'AD', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) == 0:
        return None
    
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)
    
    ad_line = 0.0
    for k in klines:
        high_low = k.high - k.low
        if high_low == 0:
            clv = 0.0
        else:
            clv = ((k.close - k.low) - (k.high - k.close)) / high_low
        ad_line += clv * k.volume
    
    _save_indicator(code, 'AD', period, date, json.dumps(ad_line), use_adjusted)
    return ad_line


def get_adosc(code: str, date: str, fast: int = 3, slow: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """AD震荡指标 ADOSC（Accumulation/Distribution Oscillator）

    快周期AD - 慢周期AD，衡量资金流向的变化速度（AD的动量）。
    正值且上升表示买盘在增强，负值且下降表示卖盘在增强。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        fast: 快速AD的周期，默认3
        slow: 慢速AD的周期，默认10
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日ADOSC值；数据不足时返回 None
    """
    period_key = fast * 100 + slow
    cached = _get_cached_indicator(code, 'ADOSC', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ad_fast = get_ad(code, date, fast, use_adjusted)
    ad_slow = get_ad(code, date, slow, use_adjusted)
    
    if ad_fast is None or ad_slow is None:
        return None
    
    adosc = ad_fast - ad_slow
    _save_indicator(code, 'ADOSC', period_key, date, json.dumps(adosc), use_adjusted)
    return adosc


def get_mfi(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """资金流量指标 MFI（Money Flow Index，0-100）

    结合典型价格和成交量的动量指标，原理类似 RSI 但加入了成交量权重（量价共振）。
    取值0-100，>80 视为超买，<20 视为超卖。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日MFI值（0-100）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'MFI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    positive_mf = 0.0
    negative_mf = 0.0
    
    for i in range(1, len(klines)):
        typical_price = (klines[i].high + klines[i].low + klines[i].close) / 3
        prev_tp = (klines[i-1].high + klines[i-1].low + klines[i-1].close) / 3
        money_flow = typical_price * klines[i].volume
        
        if typical_price > prev_tp:
            positive_mf += money_flow
        elif typical_price < prev_tp:
            negative_mf += money_flow
    
    if negative_mf == 0:
        mfi = 100.0
    else:
        mfr = positive_mf / negative_mf
        mfi = 100 - (100 / (1 + mfr))
    
    _save_indicator(code, 'MFI', period, date, json.dumps(mfi), use_adjusted)
    return mfi


def get_cmo(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """钱德动量摆动指标 CMO（Chande Momentum Oscillator，-100到100）

    (上涨幅度总和 - 下跌幅度总和) / (上涨+下跌幅度总和) * 100。
    取值-100到100，>50 超买，<-50 超卖，穿越0轴视为趋势转变信号。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日CMO值（-100到100）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'CMO', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    up_sum = 0.0
    down_sum = 0.0
    
    for i in range(1, len(klines)):
        diff = klines[i].close - klines[i-1].close
        if diff > 0:
            up_sum += diff
        else:
            down_sum += abs(diff)
    
    if up_sum + down_sum == 0:
        cmo = 0.0
    else:
        cmo = ((up_sum - down_sum) / (up_sum + down_sum)) * 100
    
    _save_indicator(code, 'CMO', period, date, json.dumps(cmo), use_adjusted)
    return cmo


def get_rocp(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """价格变动率 ROCP（Rate of Change Percentage）

    (今收盘 - N日前收盘) / N日前收盘，结果为小数而非百分比（区别于 ROC）。
    例：上涨5%返回0.05，下跌3%返回-0.03。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回溯天数，默认10
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日ROCP值（小数，非百分比）；数据不足或N日前收盘为0时返回 None
    """
    cached = _get_cached_indicator(code, 'ROCP', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1 or klines[0].close == 0:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    rocp = (klines[-1].close - klines[0].close) / klines[0].close
    _save_indicator(code, 'ROCP', period, date, json.dumps(rocp), use_adjusted)
    return rocp


def get_rocr(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """价格变动率比 ROCR（Rate of Change Ratio）

    今收盘 / N日前收盘，即价格的倍数比。
    =1.0 表示与N日前持平，=1.05 表示上涨5%，=0.95 表示下跌5%。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回溯天数，默认10
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日ROCR值（倍数）；数据不足或N日前收盘为0时返回 None
    """
    cached = _get_cached_indicator(code, 'ROCR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1 or klines[0].close == 0:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    rocr = klines[-1].close / klines[0].close
    _save_indicator(code, 'ROCR', period, date, json.dumps(rocr), use_adjusted)
    return rocr


def get_aroon(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """阿隆指标 AROON（Aroon Indicator）

    AROON_UP = (period - 距最高点天数) / period * 100
    AROON_DOWN = (period - 距最低点天数) / period * 100
    AROON_OSC = UP - DOWN，取值-100到100，衡量趋势强度和方向变化。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'up': 上行强度（0-100）, 'down': 下行强度（0-100）, 'osc': 震荡值（-100到100）}；
        数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'AROON', period, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    highs = [k.high for k in klines]
    lows = [k.low for k in klines]

    high_idx = highs.index(max(highs))
    low_idx = lows.index(min(lows))

    aroon_up = ((period - high_idx) / period) * 100
    aroon_down = ((period - low_idx) / period) * 100
    aroon_osc = aroon_up - aroon_down

    aroon = {'up': aroon_up, 'down': aroon_down, 'osc': aroon_osc}
    _save_indicator(code, 'AROON', period, date, json.dumps(aroon), use_adjusted)
    return aroon
def get_ultosc(code: str, date: str, period1: int = 7, period2: int = 14, period3: int = 28, use_adjusted: bool = True) -> Optional[float]:
    """终极振荡器 ULTOSC（Ultimate Oscillator，0-100）

    [存根函数] 理论上综合三个不同周期的买盘压力计算超买超卖，
    >70 超买，<30 超卖；当前固定返回 50.0（中性值）。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period1: 短周期，默认7
        period2: 中周期，默认14
        period3: 长周期，默认28
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当前固定返回 50.0（未完整实现）；数据不足时返回 None
    """
    period_key = period1 * 10000 + period2 * 100 + period3
    cached = _get_cached_indicator(code, 'ULTOSC', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, max(period1, period2, period3) + 1)
    if len(klines) < max(period1, period2, period3) + 1:
        return None
    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    ultosc = 50.0
    _save_indicator(code, 'ULTOSC', period_key, date, json.dumps(ultosc), use_adjusted)
    return ultosc


# ============================================================
# 第四梯队：专业指标
# ============================================================

def get_dema(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """双重指数移动平均线 DEMA（Double Exponential Moving Average）

    DEMA = 2 * EMA - EMA(EMA)，比单重 EMA 减少滞后，对价格变化响应更快。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日DEMA值（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'DEMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ema1 = get_ema(code, date, period, use_adjusted)
    ema2 = get_ema(code, date, period, use_adjusted)

    if ema1 is None or ema2 is None:
        return None

    dema = 2 * ema1 - ema2
    _save_indicator(code, 'DEMA', period, date, json.dumps(dema), use_adjusted)
    return dema


def get_kama(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """考夫曼自适应移动平均线 KAMA（Kaufman Adaptive Moving Average）

    [存根函数] 理论上根据市场效率比率自动调整平滑系数，
    趋势行情时快速跟踪，震荡行情时近乎平坦；当前直接返回最新收盘价。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 效率比率计算周期，默认10
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日KAMA值（元），当前近似为最新收盘价；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'KAMA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    kama = klines[-1].close
    _save_indicator(code, 'KAMA', period, date, json.dumps(kama), use_adjusted)
    return kama


def get_midpoint(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """中点价格 MIDPOINT

    过去 period 日内 (最高价极值 + 最低价极值) / 2，代表价格区间的中心位置。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回看周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 过去period日的中点价格（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'MIDPOINT', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    highest = max(k.high for k in klines)
    lowest = min(k.low for k in klines)
    
    midpoint = (highest + lowest) / 2
    _save_indicator(code, 'MIDPOINT', period, date, json.dumps(midpoint), use_adjusted)
    return midpoint


def get_midprice(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """中点价格别名 MIDPRICE（等同于 MIDPOINT）

    直接委托给 get_midpoint，两者完全等价。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回看周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 过去period日的中点价格（元）；数据不足时返回 None
    """
    return get_midpoint(code, date, period, use_adjusted)


def get_pvi(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """正成交量指标 PVI（Positive Volume Index）

    [存根函数] 理论上只在成交量增大时更新累计价格变化，反映跟风散户的行为；
    当前固定返回 100.0。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 统计K线根数，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当前固定返回 100.0（未完整实现）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'PVI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    pvi = 100.0
    _save_indicator(code, 'PVI', period, date, json.dumps(pvi), use_adjusted)
    return pvi


def get_nvi(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """负成交量指标 NVI（Negative Volume Index）

    [存根函数] 理论上只在成交量缩小时更新累计价格变化，反映主力资金的悄然动向；
    当前固定返回 100.0。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 统计K线根数，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当前固定返回 100.0（未完整实现）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'NVI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None
    
    nvi = 100.0
    _save_indicator(code, 'NVI', period, date, json.dumps(nvi), use_adjusted)
    return nvi


def get_ppo(code: str, date: str, fast: int = 12, slow: int = 26, signal: int = 9, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """价格震荡百分比指标 PPO（Percentage Price Oscillator）

    (快EMA - 慢EMA) / 慢EMA * 100，是 MACD 的百分比版本，
    消除了股价绝对值差异，便于不同价位股票横向比较。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        fast: 快线EMA周期，默认12
        slow: 慢线EMA周期，默认26
        signal: 信号线周期，默认9（当前近似处理）
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'ppo': PPO线(%), 'signal': 信号线(%), 'histogram': 柱状图}；
        数据不足或慢EMA为0时返回 None
    """
    period_key = fast * 10000 + slow * 100 + signal
    cached = _get_cached_indicator(code, 'PPO', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    ema_fast = get_ema(code, date, fast, use_adjusted)
    ema_slow = get_ema(code, date, slow, use_adjusted)

    if ema_fast is None or ema_slow is None or ema_slow == 0:
        return None

    ppo_line = ((ema_fast - ema_slow) / ema_slow) * 100
    ppo = {'ppo': ppo_line, 'signal': ppo_line, 'histogram': 0}
    _save_indicator(code, 'PPO', period_key, date, json.dumps(ppo), use_adjusted)
    return ppo


def get_roc_r(code: str, date: str, period: int = 10, use_adjusted: bool = True) -> Optional[float]:
    """变动率比别名 ROC_R（等同于 ROCR）

    直接委托给 get_rocr，两者完全等价。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回溯天数，默认10
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 今收盘 / N日前收盘的比值；数据不足时返回 None
    """
    return get_rocr(code, date, period, use_adjusted)


def get_stoch(code: str, date: str, fastk_period: int = 14, slowk_period: int = 3, slowd_period: int = 3, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """慢速随机指标 STOCH（Stochastic Oscillator）

    基于 fastk_period 日高低价范围计算快速K，再经平滑得到慢速K和D值。
    slowk>80 超买，slowk<20 超卖，K线上穿D线为买入信号，下穿为卖出信号。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        fastk_period: 快速K值计算的高低价范围周期，默认14
        slowk_period: 慢速K的平滑周期，默认3（当前近似处理）
        slowd_period: 慢速D的平滑周期，默认3（当前近似处理）
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'slowk': 慢速K值, 'slowd': 慢速D值}（0-100）；数据不足时返回 None
    """
    period_key = fastk_period * 10000 + slowk_period * 100 + slowd_period
    cached = _get_cached_indicator(code, 'STOCH', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    klines = _get_klines_before_date(code, date, fastk_period)
    if len(klines) < fastk_period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    low_n = min(k.low for k in klines)
    high_n = max(k.high for k in klines)
    
    if high_n - low_n == 0:
        fastk = 50.0
    else:
        fastk = ((klines[-1].close - low_n) / (high_n - low_n)) * 100
    
    stoch = {'slowk': fastk, 'slowd': fastk}
    _save_indicator(code, 'STOCH', period_key, date, json.dumps(stoch), use_adjusted)
    return stoch


def get_stochf(code: str, date: str, fastk_period: int = 14, fastd_period: int = 3, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """快速随机指标 STOCHF（Fast Stochastic Oscillator）

    [存根函数] 与 STOCH 类似但不做慢速平滑，反应更灵敏；
    当前固定返回 {'fastk': 50.0, 'fastd': 50.0}。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        fastk_period: 快速K值计算周期，默认14
        fastd_period: 快速D的平滑周期，默认3
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'fastk': 快速K值, 'fastd': 快速D值}；当前固定返回各50.0（未完整实现）
    """
    period_key = fastk_period * 100 + fastd_period
    cached = _get_cached_indicator(code, 'STOCHF', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    stochf = {'fastk': 50.0, 'fastd': 50.0}
    _save_indicator(code, 'STOCHF', period_key, date, json.dumps(stochf), use_adjusted)
    return stochf


def get_stochrsi(code: str, date: str, rsi_period: int = 14, stoch_period: int = 14, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """随机RSI STOCHRSI（Stochastic RSI）

    [存根函数] 将 RSI 值再经随机指标公式处理，对超买超卖更敏感；
    当前固定返回 {'fastk': 50.0, 'fastd': 50.0}。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        rsi_period: RSI计算周期，默认14
        stoch_period: STOCH计算周期，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'fastk': K值, 'fastd': D值}；当前固定返回各50.0（未完整实现）
    """
    period_key = rsi_period * 100 + stoch_period
    cached = _get_cached_indicator(code, 'STOCHRSI', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    stochrsi = {'fastk': 50.0, 'fastd': 50.0}
    _save_indicator(code, 'STOCHRSI', period_key, date, json.dumps(stochrsi), use_adjusted)
    return stochrsi


def get_trange(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """真实波幅别名 TRANGE（等同于 TR）

    直接委托给 get_tr，两者完全等价。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日TR值（元）；数据不足时返回 None
    """
    return get_tr(code, date, use_adjusted)


# ============================================================
# 第五梯队：通道和其他指标
# ============================================================

def get_ma_channel(code: str, date: str, period: int = 20, multiplier: float = 2.0, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """移动平均通道 MA_CHANNEL

    以 SMA 为中轨，上下各扩展 multiplier 倍 ATR 作为上下轨，形成动态通道。
    价格突破上轨可能是超强趋势信号，跌破下轨可能是弱势信号，通道宽度随波动率变化。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: SMA和ATR的计算周期，默认20
        multiplier: ATR倍数，控制通道宽窄，默认2.0
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'upper': 上轨, 'middle': 中轨(SMA), 'lower': 下轨}（单位：元）；
        数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'MA_CHANNEL', period, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    sma = get_sma(code, date, period, use_adjusted)
    atr = get_atr(code, date, period, use_adjusted)

    if sma is None or atr is None:
        return None

    channel = {
        'upper': sma + multiplier * atr,
        'middle': sma,
        'lower': sma - multiplier * atr
    }
    _save_indicator(code, 'MA_CHANNEL', period, date, json.dumps(channel), use_adjusted)
    return channel


def get_donchian(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """唐奇安通道 DONCHIAN（Donchian Channel）

    上轨 = 过去 period 日最高价，下轨 = 过去 period 日最低价，中轨 = (上+下)/2。
    价格突破上轨为买入信号，突破下轨为卖出信号（海龟交易系统的核心）。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 通道计算周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}（单位：元）；
        数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'DONCHIAN', period, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    upper = max(k.high for k in klines)
    lower = min(k.low for k in klines)
    middle = (upper + lower) / 2
    
    donchian = {'upper': upper, 'middle': middle, 'lower': lower}
    _save_indicator(code, 'DONCHIAN', period, date, json.dumps(donchian), use_adjusted)
    return donchian


def get_keltner(code: str, date: str, ma_period: int = 20, atr_period: int = 10, multiplier: float = 2.0, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """凯尔特纳通道 KELTNER（Keltner Channel）

    以 EMA 为中轨，上下各扩展 multiplier 倍 ATR。
    布林带在内、凯特纳在外时称"挤压"（Squeeze），是大行情前兆的判断依据之一。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        ma_period: EMA计算周期，默认20
        atr_period: ATR计算周期，默认10
        multiplier: ATR倍数，控制通道宽窄，默认2.0
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'upper': 上轨, 'middle': 中轨(EMA), 'lower': 下轨}（单位：元）；
        数据不足时返回 None
    """
    period_key = ma_period * 10000 + atr_period * 100 + int(multiplier * 10)
    cached = _get_cached_indicator(code, 'KELTNER', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    ema = get_ema(code, date, ma_period, use_adjusted)
    atr = get_atr(code, date, atr_period, use_adjusted)

    if ema is None or atr is None:
        return None

    keltner = {
        'upper': ema + multiplier * atr,
        'middle': ema,
        'lower': ema - multiplier * atr
    }
    _save_indicator(code, 'KELTNER', period_key, date, json.dumps(keltner), use_adjusted)
    return keltner


def get_bbands_width(code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[float]:
    """布林带宽度 BBANDS_WIDTH（%）

    (上轨 - 下轨) / 中轨 * 100，衡量布林带的相对宽窄程度（标准化后的带宽）。
    带宽极度收窄（挤压）通常预示即将发生大行情；带宽扩大表示行情波动加剧。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 布林带周期，默认20
        std_dev: 标准差倍数，默认2
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日布林带宽度（%）；数据不足或中轨为0时返回 None
    """
    period_key = period * 10 + std_dev
    cached = _get_cached_indicator(code, 'BBANDS_WIDTH', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    bb = get_bollinger_bands(code, date, period, std_dev, use_adjusted)
    if bb is None or bb['middle'] == 0:
        return None

    width = ((bb['upper'] - bb['lower']) / bb['middle']) * 100
    _save_indicator(code, 'BBANDS_WIDTH', period_key, date, json.dumps(width), use_adjusted)
    return width


def get_bbands_pct(code: str, date: str, period: int = 20, std_dev: int = 2, use_adjusted: bool = True) -> Optional[float]:
    """布林带百分比位置 BBANDS_PCT（Bollinger Bands %B）

    (今收 - 下轨) / (上轨 - 下轨)，衡量价格在布林带中的相对位置。
    =1.0 表示触及上轨（超买），=0.0 触及下轨（超卖），=0.5 在中轨；极端时可超出[0,1]范围。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 布林带周期，默认20
        std_dev: 标准差倍数，默认2
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日%B值（通常0-1，极端时可超出范围）；数据不足时返回 None
    """
    period_key = period * 10 + std_dev
    cached = _get_cached_indicator(code, 'BBANDS_PCT', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    bb = get_bollinger_bands(code, date, period, std_dev, use_adjusted)
    klines = _get_klines_before_date(code, date, 1)

    if bb is None or len(klines) == 0:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    if bb['upper'] - bb['lower'] == 0:
        pct = 0.5
    else:
        pct = (klines[-1].close - bb['lower']) / (bb['upper'] - bb['lower'])
    
    _save_indicator(code, 'BBANDS_PCT', period_key, date, json.dumps(pct), use_adjusted)
    return pct


# ============================================================
# 第六梯队：其他指标
# ============================================================

def get_linearreg(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """线性回归预测值 LINEARREG

    对过去 period 日收盘价做最小二乘线性回归，返回回归线在最后一天的预测值。
    可理解为去噪后的"理论收盘价"，与实际价格的偏差反映超买超卖程度。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回归窗口大小，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日线性回归预测价（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'LINEARREG', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    prices = [k.close for k in klines]
    x = list(range(period))
    mean_x = sum(x) / period
    mean_y = sum(prices) / period
    
    numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(period))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(period))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    linearreg = intercept + slope * (period - 1)
    
    _save_indicator(code, 'LINEARREG', period, date, json.dumps(linearreg), use_adjusted)
    return linearreg


def get_linearreg_angle(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """线性回归角度 LINEARREG_ANGLE（度）

    对过去 period 日收盘价做线性回归，将斜率转换为角度（arctan）。
    正角度表示上升趋势，负角度表示下降趋势，角度绝对值越大趋势越陡峭。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回归窗口大小，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日回归线角度（度，-90到90）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'LINEARREG_ANGLE', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    prices = [k.close for k in klines]
    x = list(range(period))
    mean_x = sum(x) / period
    mean_y = sum(prices) / period
    
    numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(period))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(period))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    angle = math.degrees(math.atan(slope))
    
    _save_indicator(code, 'LINEARREG_ANGLE', period, date, json.dumps(angle), use_adjusted)
    return angle


def get_linearreg_intercept(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """线性回归截距 LINEARREG_INTERCEPT（元）

    过去 period 日收盘价线性回归直线的Y轴截距（x=0时的理论价格）。
    通常配合 LINEARREG_SLOPE 和 LINEARREG 一起使用，单独使用意义不大。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回归窗口大小，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 线性回归截距值（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'LINEARREG_INTERCEPT', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    prices = [k.close for k in klines]
    x = list(range(period))
    mean_x = sum(x) / period
    mean_y = sum(prices) / period
    
    numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(period))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(period))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    
    _save_indicator(code, 'LINEARREG_INTERCEPT', period, date, json.dumps(intercept), use_adjusted)
    return intercept


def get_linearreg_slope(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """线性回归斜率 LINEARREG_SLOPE（元/天）

    过去 period 日收盘价线性回归直线的斜率（每交易日平均涨跌幅）。
    正值表示上升趋势，负值表示下降趋势，绝对值越大趋势越强劲。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回归窗口大小，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 线性回归斜率（元/天）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'LINEARREG_SLOPE', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    prices = [k.close for k in klines]
    x = list(range(period))
    mean_x = sum(x) / period
    mean_y = sum(prices) / period
    
    numerator = sum((x[i] - mean_x) * (prices[i] - mean_y) for i in range(period))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(period))
    
    if denominator == 0:
        return None
    
    slope = numerator / denominator
    _save_indicator(code, 'LINEARREG_SLOPE', period, date, json.dumps(slope), use_adjusted)
    return slope


def get_stddev(code: str, date: str, period: int = 20, nbdev: int = 1, use_adjusted: bool = True) -> Optional[float]:
    """标准差 STDDEV（Standard Deviation）

    过去 period 日收盘价的总体标准差，乘以 nbdev 倍数。
    衡量价格的离散程度，是布林带计算的基础；nbdev=1为原始标准差，=2则与布林带2σ对应。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 计算周期，默认20
        nbdev: 标准差倍数，默认1
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日标准差值（元）；数据不足时返回 None
    """
    period_key = period * 10 + nbdev
    cached = _get_cached_indicator(code, 'STDDEV', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    prices = [k.close for k in klines]
    mean = sum(prices) / period
    variance = sum((p - mean) ** 2 for p in prices) / period
    stddev = (variance ** 0.5) * nbdev
    
    _save_indicator(code, 'STDDEV', period_key, date, json.dumps(stddev), use_adjusted)
    return stddev


def get_tsf(code: str, date: str, period: int = 14, use_adjusted: bool = True) -> Optional[float]:
    """时间序列预测别名 TSF（Time Series Forecast，等同于 LINEARREG）

    直接委托给 get_linearreg，两者完全等价。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 回归窗口大小，默认14
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日线性回归预测价（元）；数据不足时返回 None
    """
    return get_linearreg(code, date, period, use_adjusted)


def get_var(code: str, date: str, period: int = 20, nbdev: int = 1, use_adjusted: bool = True) -> Optional[float]:
    """方差 VAR（Variance）

    过去 period 日收盘价的总体方差，乘以 nbdev² 倍数。
    方差 = 标准差²，是 STDDEV 的平方，衡量价格离散程度；与 STDDEV 配合使用。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 计算周期，默认20
        nbdev: 倍数，默认1（实际方差再乘以nbdev²）
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日方差值（元²）；数据不足时返回 None
    """
    period_key = period * 10 + nbdev
    cached = _get_cached_indicator(code, 'VAR', period_key, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    prices = [k.close for k in klines]
    mean = sum(prices) / period
    variance = sum((p - mean) ** 2 for p in prices) / period
    var = variance * nbdev * nbdev
    
    _save_indicator(code, 'VAR', period_key, date, json.dumps(var), use_adjusted)
    return var


def get_correl(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """相关系数 CORREL（Pearson Correlation Coefficient）

    [存根函数] 理论上计算两个价格序列的皮尔逊相关系数（-1到1）；
    当前仅支持单只股票（与自身序列相关，结果恒为1.0）。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 统计周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当前固定返回 1.0（未完整实现）
    """
    cached = _get_cached_indicator(code, 'CORREL', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    correl = 1.0
    _save_indicator(code, 'CORREL', period, date, json.dumps(correl), use_adjusted)
    return correl


def get_beta(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """贝塔系数 BETA

    [存根函数] 理论上衡量个股相对市场指数的系统性风险（>1波动大于市场，<1反之）；
    需要基准指数数据，当前仅支持单只股票（与自身比较，固定返回1.0）。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        period: 统计周期，默认20
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当前固定返回 1.0（未完整实现）
    """
    cached = _get_cached_indicator(code, 'BETA', period, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    beta = 1.0
    _save_indicator(code, 'BETA', period, date, json.dumps(beta), use_adjusted)
    return beta


def get_ht_dcperiod(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """希尔伯特变换-主导周期 HT_DCPERIOD

    [存根函数] 通过希尔伯特变换检测价格序列当前的主导振荡周期（天数），
    用于自适应指标的动态周期参数；当前固定返回 10.0。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当前固定返回 10.0（未完整实现），单位：天
    """
    cached = _get_cached_indicator(code, 'HT_DCPERIOD', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ht_dcperiod = 10.0
    _save_indicator(code, 'HT_DCPERIOD', 1, date, json.dumps(ht_dcperiod), use_adjusted)
    return ht_dcperiod


def get_ht_dcphase(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """希尔伯特变换-主导相位 HT_DCPHASE

    [存根函数] 当前价格在主导周期中所处的相位角（度），
    配合 HT_DCPERIOD 使用，可判断周期性行情的位置；当前固定返回 0.0。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当前固定返回 0.0（未完整实现），单位：度
    """
    cached = _get_cached_indicator(code, 'HT_DCPHASE', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    ht_dcphase = 0.0
    _save_indicator(code, 'HT_DCPHASE', 1, date, json.dumps(ht_dcphase), use_adjusted)
    return ht_dcphase


def get_ht_phasor(code: str, date: str, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """希尔伯特变换-相位分量 HT_PHASOR

    [存根函数] 将价格信号分解为同相（InPhase）和正交（Quadrature）两个正交分量，
    用于计算相位和主导周期；当前固定返回零值。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'inphase': 同相分量, 'quadrature': 正交分量}；当前固定返回各0.0（未完整实现）
    """
    cached = _get_cached_indicator(code, 'HT_PHASOR', 1, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    ht_phasor = {'inphase': 0.0, 'quadrature': 0.0}
    _save_indicator(code, 'HT_PHASOR', 1, date, json.dumps(ht_phasor), use_adjusted)
    return ht_phasor


def get_ht_sine(code: str, date: str, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """希尔伯特变换-正弦波 HT_SINE

    [存根函数] 基于希尔伯特变换输出正弦波和超前正弦波（领先约45度），
    两线交叉预示周期性趋势转折；当前固定返回零值。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        dict: {'sine': 正弦值, 'leadsine': 超前正弦值}；当前固定返回各0.0（未完整实现）
    """
    cached = _get_cached_indicator(code, 'HT_SINE', 1, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)
    
    ht_sine = {'sine': 0.0, 'leadsine': 0.0}
    _save_indicator(code, 'HT_SINE', 1, date, json.dumps(ht_sine), use_adjusted)
    return ht_sine


def get_ht_trendmode(code: str, date: str, use_adjusted: bool = True) -> Optional[int]:
    """希尔伯特变换-趋势模式 HT_TRENDMODE

    [存根函数] 判断当前市场处于趋势行情（1）还是周期性震荡行情（0），
    用于切换使用趋势类或震荡类指标；当前固定返回1（趋势模式）。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        int: 1=趋势行情，0=周期性震荡；当前固定返回 1（未完整实现）
    """
    cached = _get_cached_indicator(code, 'HT_TRENDMODE', 1, date, use_adjusted)
    if cached is not None:
        return int(float(cached))
    
    ht_trendmode = 1
    _save_indicator(code, 'HT_TRENDMODE', 1, date, json.dumps(ht_trendmode), use_adjusted)
    return ht_trendmode


# ============================================================
# 辅助指标
# ============================================================

def get_typical_price(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """典型价格 TP（Typical Price）

    当日 (最高价 + 最低价 + 收盘价) / 3，是 MFI、CCI、VWAP 等指标的基础计算单元，
    比单纯收盘价更能代表当日的价格重心。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日典型价格（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'TYPICAL', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, 1)
    if len(klines) == 0:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    tp = (klines[-1].high + klines[-1].low + klines[-1].close) / 3
    _save_indicator(code, 'TYPICAL', 1, date, json.dumps(tp), use_adjusted)
    return tp


def get_median_price(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """中位数价格 MEDPRICE（Median Price）

    当日 (最高价 + 最低价) / 2，代表当日价格区间的中心点，
    不考虑收盘价位置，适合作为对称通道的基准价格。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日中位数价格（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'MEDIAN', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, 1)
    if len(klines) == 0:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    mp = (klines[-1].high + klines[-1].low) / 2
    _save_indicator(code, 'MEDIAN', 1, date, json.dumps(mp), use_adjusted)
    return mp


def get_weighted_close(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """加权收盘价 WCL（Weighted Close Price）

    当日 (最高价 + 最低价 + 2 * 收盘价) / 4，给收盘价赋予双倍权重，
    比典型价格更强调收盘价的重要性，反映市场对当日收盘位置的认可。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日加权收盘价（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'WCL', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, 1)
    if len(klines) == 0:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    wcl = (klines[-1].high + klines[-1].low + 2 * klines[-1].close) / 4
    _save_indicator(code, 'WCL', 1, date, json.dumps(wcl), use_adjusted)
    return wcl


def get_avgp(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """平均价格 AVGP（Average Price）

    当日 (开盘价 + 最高价 + 最低价 + 收盘价) / 4，四价平均，
    综合反映当日全程的价格水平，可用于判断当日多空博弈的均衡点。

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认True

    Returns:
        float: 当日四价平均价格（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'AVGP', 1, date, use_adjusted)
    if cached is not None:
        return float(cached)
    
    klines = _get_klines_before_date(code, date, 1)
    if len(klines) == 0:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    avgp = (klines[-1].open + klines[-1].high + klines[-1].low + klines[-1].close) / 4
    _save_indicator(code, 'AVGP', 1, date, json.dumps(avgp), use_adjusted)
    return avgp


# ============================================================
# 新增指标
# ============================================================

def get_asi(code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[float]:
    """振动升降指标 ASI（Accumulation Swing Index）

    由 Wilder 提出，综合 open/high/low/close 计算每日摆动指数 SI，再累计求和。
    ASI 上穿前高为强烈买入信号，下穿前低为卖出信号，常用于确认趋势突破的真实性。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       累计 SI 的 K 线根数，默认 26
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        float: 当日 ASI 值；数据不足（< period+1 根）时返回 None
    """
    cached = _get_cached_indicator(code, 'ASI', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    asi = 0.0
    for i in range(1, len(klines)):
        cur  = klines[i]
        prev = klines[i - 1]
        A = abs(cur.high  - prev.close)
        B = abs(cur.low   - prev.close)
        C = abs(cur.high  - prev.low)
        D = abs(prev.close - prev.open) if prev.open else 0.0

        if A >= B and A >= C:
            R = A - 0.5 * B + 0.25 * D
        elif B >= A and B >= C:
            R = B - 0.5 * A + 0.25 * D
        else:
            R = C + 0.25 * D

        X = (cur.close - prev.close) + 0.5 * (cur.close - cur.open) + 0.25 * (prev.close - prev.open if prev.open else 0.0)
        si = (50.0 * X / R) if R != 0 else 0.0
        asi += si

    _save_indicator(code, 'ASI', period, date, json.dumps(asi), use_adjusted)
    return asi


def get_vr(code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[float]:
    """成交量变异率 VR（Volume Ratio）

    将过去 period 日的成交量按涨/跌/平分类累加，计算多空力量之比。
    VR = (上涨日成交量 + 平盘日成交量/2) / (下跌日成交量 + 平盘日成交量/2) * 100
    VR 在 70~150 为盘整区，>250 超买，<70 超卖，<40 极度超卖（可能反弹）。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       统计周期，默认 26
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        float: 当日 VR 值；数据不足或分母为 0 时返回 None
    """
    cached = _get_cached_indicator(code, 'VR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    avs = bvs = cvs = 0.0
    for i in range(1, len(klines)):
        vol = klines[i].volume or 0.0
        if klines[i].close > klines[i - 1].close:
            avs += vol
        elif klines[i].close < klines[i - 1].close:
            bvs += vol
        else:
            cvs += vol

    denominator = bvs + cvs / 2.0
    if denominator == 0:
        return None

    vr = (avs + cvs / 2.0) / denominator * 100.0
    _save_indicator(code, 'VR', period, date, json.dumps(vr), use_adjusted)
    return vr


def get_ar(code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[float]:
    """AR 人气指标（Atmosphere Ratio）

    衡量当前市场人气，反映多空双方争夺的激烈程度。
    AR = sum(High - Open) / sum(Open - Low) * 100，值越高说明买方越强势。
    AR > 180 为超买区，AR < 40 为超卖区，一般在 80~120 间震荡。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       统计周期，默认 26
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        float: 当日 AR 值；数据不足或分母为 0 时返回 None
    """
    cached = _get_cached_indicator(code, 'AR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    sum_ho = sum(k.high - k.open for k in klines)
    sum_ol = sum(k.open - k.low  for k in klines)

    if sum_ol == 0:
        return None

    ar = sum_ho / sum_ol * 100.0
    _save_indicator(code, 'AR', period, date, json.dumps(ar), use_adjusted)
    return ar


def get_br(code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[float]:
    """BR 意愿指标（Willingness Ratio）

    衡量市场买卖意愿，以前收盘价为参考基准区分主动多空力量。
    BR = sum(max(0, High - prevClose)) / sum(max(0, prevClose - Low)) * 100
    BR > 400 超买，BR < 40 超卖。与 AR 配合使用可判断主力意图。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       统计周期，默认 26
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        float: 当日 BR 值；数据不足或分母为 0 时返回 None
    """
    cached = _get_cached_indicator(code, 'BR', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, period + 1)
    if len(klines) < period + 1:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    sum_hpc = sum_pcl = 0.0
    for i in range(1, len(klines)):
        pc = klines[i - 1].close
        sum_hpc += max(0.0, klines[i].high - pc)
        sum_pcl += max(0.0, pc - klines[i].low)

    if sum_pcl == 0:
        return None

    br = sum_hpc / sum_pcl * 100.0
    _save_indicator(code, 'BR', period, date, json.dumps(br), use_adjusted)
    return br


def get_brar(code: str, date: str, period: int = 26, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """BRAR 情绪指标（BR + AR 组合）

    同时返回 AR（人气指标）和 BR（意愿指标），综合衡量市场情绪。
    AR 反映多空争夺强度，BR 反映主力买卖意愿；两者配合判断超买超卖。
    AR/BR 同时超买 → 市场过热；AR/BR 同时超卖 → 可能见底。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       统计周期，默认 26
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        dict: {'ar': AR值, 'br': BR值}；任一指标无法计算时返回 None
    """
    cached = _get_cached_indicator(code, 'BRAR', period, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)

    ar = get_ar(code, date, period, use_adjusted)
    br = get_br(code, date, period, use_adjusted)

    if ar is None or br is None:
        return None

    result = {'ar': ar, 'br': br}
    _save_indicator(code, 'BRAR', period, date, json.dumps(result), use_adjusted)
    return result


def get_dpo(code: str, date: str, period: int = 20, use_adjusted: bool = True) -> Optional[float]:
    """区间震荡线 DPO（Detrended Price Oscillator）

    通过去除价格中的趋势成分，突出周期性波动。
    DPO = 今收盘 - SMA(close, N) 向前偏移 (N/2 + 1) 根K线
    偏移后的 SMA 反映 N/2+1 天前的均价水平，DPO > 0 表示价格高于历史均值。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       周期，默认 20
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        float: 当日 DPO 值（元）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'DPO', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    shift = period // 2 + 1
    needed = period + shift + 1
    klines = _get_klines_before_date(code, date, needed)
    if len(klines) < needed:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    # SMA 使用 shift 根前的那段 N 根 K 线
    sma_klines = klines[-(period + shift):-shift]
    sma_old = sum(k.close for k in sma_klines) / period

    dpo = klines[-1].close - sma_old
    _save_indicator(code, 'DPO', period, date, json.dumps(dpo), use_adjusted)
    return dpo


def get_bbi(code: str, date: str, use_adjusted: bool = True) -> Optional[float]:
    """多空指标 BBI（Bull and Bear Index）

    四条均线（3/6/12/24日）的简单平均，综合短中长期趋势。
    BBI = (MA3 + MA6 + MA12 + MA24) / 4
    价格上穿 BBI 为买入信号，下穿为卖出信号；比单一均线更平滑稳定。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        float: 当日 BBI 值（元）；数据不足 24 根时返回 None
    """
    cached = _get_cached_indicator(code, 'BBI', 24, date, use_adjusted)
    if cached is not None:
        return float(cached)

    klines = _get_klines_before_date(code, date, 24)
    if len(klines) < 24:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    closes = [k.close for k in klines]
    ma3  = sum(closes[-3:])  / 3
    ma6  = sum(closes[-6:])  / 6
    ma12 = sum(closes[-12:]) / 12
    ma24 = sum(closes[-24:]) / 24

    bbi = (ma3 + ma6 + ma12 + ma24) / 4.0
    _save_indicator(code, 'BBI', 24, date, json.dumps(bbi), use_adjusted)
    return bbi


def get_mass(code: str, date: str, period: int = 25, use_adjusted: bool = True) -> Optional[float]:
    """梅斯线 MASS（Mass Index）

    通过计算高低价之差的两次 EMA 之比，并累加，识别价格反转信号。
    EMA1 = EMA(High-Low, 9)，EMA2 = EMA(EMA1, 9)，MASS = sum(EMA1/EMA2, period)
    MASS 超过 27 后回落至 26.5 以下，为"反转隆起"，预示趋势反转。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       累加周期，默认 25
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        float: 当日 MASS 值；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'MASS', period, date, use_adjusted)
    if cached is not None:
        return float(cached)

    ema_period = 9
    needed = ema_period * 2 + period
    klines = _get_klines_before_date(code, date, needed)
    if len(klines) < needed:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    hl = [k.high - k.low for k in klines]
    ema1 = _ema_series(hl, ema_period)
    ema2 = _ema_series(ema1, ema_period)

    ratios = [e1 / e2 if e2 != 0 else 1.0 for e1, e2 in zip(ema1, ema2)]
    if len(ratios) < period:
        return None

    mass = sum(ratios[-period:])
    _save_indicator(code, 'MASS', period, date, json.dumps(mass), use_adjusted)
    return mass


def get_xue_channel(code: str, date: str, period: int = 20, pct: float = 3.0, use_adjusted: bool = True) -> Optional[Dict[str, float]]:
    """薛斯通道（Xue's Channel）

    以 SMA 为中轨，向上/下按固定百分比扩展形成通道，类似布林带但用固定比例替代标准差。
    上轨 = SMA * (1 + pct/100)，下轨 = SMA * (1 - pct/100)
    价格触及上轨为短期超买，触及下轨为超卖，通道内震荡则看中轨支撑/压力。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       SMA 周期，默认 20
        pct:          通道偏移百分比，默认 3.0（即 ±3%）
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        dict: {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}（元）；数据不足时返回 None
    """
    period_key = period * 1000 + int(pct * 10)
    cached = _get_cached_indicator(code, 'XUE', period_key, date, use_adjusted)
    if cached is not None:
        return json.loads(cached)

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    middle = sum(k.close for k in klines) / period
    upper  = middle * (1.0 + pct / 100.0)
    lower  = middle * (1.0 - pct / 100.0)

    result = {'upper': upper, 'middle': middle, 'lower': lower}
    _save_indicator(code, 'XUE', period_key, date, json.dumps(result), use_adjusted)
    return result


def get_consecutive_rise(code: str, date: str, max_days: int = 60, use_adjusted: bool = True) -> Optional[int]:
    """连涨天数

    从 date 向前数，连续收盘价高于前一日的天数。
    使用复权价格，避免除权除息日的价格跳空被误判为下跌。
    连涨天数过长（如 >7）往往预示短期超买，注意回调风险。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         统计截止日期，格式 'YYYY-MM-DD'
        max_days:     最多回溯天数，默认 60（防止数据量过大）
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        int: 连涨天数（0 表示当日未上涨）；数据不足时返回 None
    """
    klines = _get_klines_before_date(code, date, max_days + 1)
    if len(klines) < 2:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    count = 0
    for i in range(len(klines) - 1, 0, -1):
        if klines[i].close > klines[i - 1].close:
            count += 1
        else:
            break
    return count


def get_consecutive_fall(code: str, date: str, max_days: int = 60, use_adjusted: bool = True) -> Optional[int]:
    """连跌天数

    从 date 向前数，连续收盘价低于前一日的天数。
    使用复权价格，避免除权除息日的价格跳空被误判为下跌。
    连跌天数过长（如 >7）往往预示短期超卖，可能存在反弹机会。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         统计截止日期，格式 'YYYY-MM-DD'
        max_days:     最多回溯天数，默认 60（防止数据量过大）
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        int: 连跌天数（0 表示当日未下跌）；数据不足时返回 None
    """
    klines = _get_klines_before_date(code, date, max_days + 1)
    if len(klines) < 2:
        return None

    if use_adjusted:
        adj_factors = _get_adj_factors_for_klines(klines)
        klines = _adjust_klines(klines, adj_factors)

    count = 0
    for i in range(len(klines) - 1, 0, -1):
        if klines[i].close < klines[i - 1].close:
            count += 1
        else:
            break
    return count


def get_bomb_board(code: str, date: str) -> Optional[int]:
    """炸板判断

    判断指定日期该股票是否发生炸板：当日价格曾触及涨停价，但收盘时未封住（收盘价 < 涨停价）。
    炸板往往意味着多头动能不足，短期筹码松动，可作为规避信号。

    不使用复权价格——炸板依据的是市场实际涨停价，与复权无关。

    数据来源：
    - 有效交易日判断：stock_limit 表
    - 炸板记录：daily_bomb_list 表（bomb_type='U'，曾涨停炸板）

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 判断日期，格式 'YYYY-MM-DD'

    Returns:
        int: 1=当日炸板，0=当日未炸板；无数据（非交易日/数据缺失）返回 None
    """
    cached = _get_cached_indicator(code, 'BOMB_BOARD', 0, date, False)
    if cached is not None:
        return int(cached)

    # 用 stock_limit 确认是否为有效交易日
    limits = query_stock_limit(ts_codes=[code], trade_date=date)
    if not limits:
        return None

    bombs = query_daily_bomb_list(ts_codes=[code], trade_date=date, bomb_type='U')
    result = 1 if bombs else 0

    _save_indicator(code, 'BOMB_BOARD', 0, date, json.dumps(result), False)
    return result


def get_bomb_board_count(code: str, date: str, period: int = 20) -> Optional[int]:
    """近N个交易日炸板次数

    统计截至指定日期最近 period 个交易日内的炸板次数（含当日）。
    炸板频繁说明股票多次冲板失败，多头信心不足，高频炸板个股追高风险较大。

    不使用复权价格——炸板依据的是市场实际涨停价，与复权无关。

    数据来源：daily_bomb_list 表（bomb_type='U'）

    Args:
        code:   股票代码，如 '000001.SZ'
        date:   统计截止日期，格式 'YYYY-MM-DD'
        period: 回溯的交易日天数，默认 20

    Returns:
        int: 近 period 个交易日内炸板次数（0 表示无炸板）；数据不足时返回 None
    """
    cached = _get_cached_indicator(code, 'BOMB_BOARD_COUNT', period, date, False)
    if cached is not None:
        return int(cached)

    klines = _get_klines_before_date(code, date, period)
    if not klines:
        return None

    start_date = klines[0].date
    bombs = query_daily_bomb_list(ts_codes=[code], start_date=start_date, end_date=date, bomb_type='U')
    result = len(bombs)

    _save_indicator(code, 'BOMB_BOARD_COUNT', period, date, json.dumps(result), False)
    return result


def get_consecutive_limit_up(code: str, date: str) -> Optional[int]:
    """连续涨停天数（连板数）

    返回截至指定日期连续收盘涨停的天数。直接读取 daily_limit_list.limit_streak 字段，
    该字段由数据源维护，是官方连板计数，比自行计算更准确（含一字板等特殊情形）。

    连板数可用于：
    - 筛选高位连板股（>= 3 板往往已属强势）
    - 衡量涨停板的持续性与封板质量

    不使用复权价格——涨停判断基于市场实际价格。

    数据来源：
    - 有效交易日判断：stock_limit 表
    - 连板数：daily_limit_list 表（limit_type='U'，limit_streak 字段）

    Args:
        code: 股票代码，如 '000001.SZ'
        date: 判断日期，格式 'YYYY-MM-DD'

    Returns:
        int: 连板数（0 表示当日未涨停）；无数据（非交易日/数据缺失）返回 None
    """
    cached = _get_cached_indicator(code, 'CONSEC_LIMIT_UP', 0, date, False)
    if cached is not None:
        return int(cached)

    # 用 stock_limit 确认是否为有效交易日
    limits = query_stock_limit(ts_codes=[code], trade_date=date)
    if not limits:
        return None

    records = query_daily_limit_list(ts_codes=[code], trade_date=date, limit_type='U')
    result = records[0].limit_streak if records else 0

    _save_indicator(code, 'CONSEC_LIMIT_UP', 0, date, json.dumps(result), False)
    return result


if __name__ == "__main__":
    init_indicators_db()
    print("指标数据库初始化完成")
    print(f"已实现指标数量: 100+")
