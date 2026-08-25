"""
signal.py - 裸K形态信号模块

功能：
1. 识别经典K线形态，输出形态信号
2. 形态出现当日信号值为 1，未出现为 0
3. 计算结果缓存到数据库（cached_signals 表）

支持形态：
- 早晨之星 / 启明星（Morning Star） ：底部三K线看涨反转
- 黄昏之星 / 黄昏星（Evening Star） ：顶部三K线看跌反转
- 红三兵（Three White Soldiers）   ：底部三根连续阳线看涨确认
- 三只乌鸦（Three Black Crows）    ：顶部三根连续阴线看跌确认
- 乌云盖顶（Dark Cloud Cover）     ：顶部两K线看跌反转
- 圆弧底（Rounding Bottom）        ：多K线底部圆弧形态（默认20日）
- 上升三角形（Ascending Triangle） ：整理后向上突破前夕（默认20日）
- 顶部形态（Top Pattern）          ：双重顶等多K线顶部反转结构（默认30日）

设计原则：
- 函数接口与 indicators.py 统一（code/date/params/use_adjusted）
- 查询优先使用缓存，计算后存入数据库
- 默认使用后复权价格，避免除权日跳空干扰形态识别
- 缓存键仅包含 period 参数；修改 body_ratio 等形态阈值时需手动清缓存

缓存表 cached_signals 结构：
    UNIQUE(code, signal_type, param, use_adjusted, date)
    value INTEGER：1 表示形态出现，0 表示未出现
"""

from typing import Dict, List, Optional
from sqlalchemy import text
from data_fetcher import getEngine
from data_fetcher import query_daily_kline, query_daily_basic
from define import DailyKline


# ── 缓存机制 ─────────────────────────────────────────────────────────────────

def init_signals_db() -> None:
    """初始化信号缓存数据库表

    创建 cached_signals 表（如不存在），用于缓存形态信号计算结果，并建立查询索引。
    每次计算前先查缓存，命中则直接返回，避免对相同参数重复计算。
    """
    with getEngine().connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cached_signals (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                code         TEXT    NOT NULL,
                signal_type  TEXT    NOT NULL,
                param        INTEGER NOT NULL DEFAULT 0,
                use_adjusted INTEGER NOT NULL DEFAULT 1,
                date         TEXT    NOT NULL,
                value        INTEGER NOT NULL,
                created_at   TEXT    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, signal_type, param, use_adjusted, date)
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_signals_lookup "
            "ON cached_signals(code, signal_type, param, use_adjusted, date)"
        ))
        conn.commit()


_signals_table_ready: bool = False


def _ensure_table() -> None:
    global _signals_table_ready
    if not _signals_table_ready:
        init_signals_db()
        _signals_table_ready = True


def _get_cached_signal(
    code: str, signal_type: str, param: int, date: str, use_adjusted: bool
) -> Optional[int]:
    """从缓存表查询信号值

    Args:
        code:         股票代码
        signal_type:  信号类型字符串，如 'MORNING_STAR'
        param:        主要周期参数（无周期的形态传 0）
        date:         查询日期，格式 'YYYY-MM-DD'
        use_adjusted: 是否为复权计算结果

    Returns:
        int: 缓存的信号值（0 或 1），未命中返回 None
    """
    _ensure_table()
    with getEngine().connect() as conn:
        cursor = conn.execute(text(
            "SELECT value FROM cached_signals "
            "WHERE code=:code AND signal_type=:st AND param=:p "
            "  AND use_adjusted=:adj AND date=:d"
        ), {"code": code, "st": signal_type, "p": param,
            "adj": 1 if use_adjusted else 0, "d": date})
        row = cursor.fetchone()
    return int(row[0]) if row else None


def _save_signal(
    code: str, signal_type: str, param: int, date: str, value: int, use_adjusted: bool
) -> None:
    """将信号值保存到缓存表

    已存在则替换（INSERT OR REPLACE），确保缓存始终为最新值。

    Args:
        code:         股票代码
        signal_type:  信号类型字符串
        param:        主要周期参数（无周期的形态传 0）
        date:         计算日期，格式 'YYYY-MM-DD'
        value:        信号值，0 或 1
        use_adjusted: 是否为复权计算结果
    """
    _ensure_table()
    with getEngine().connect() as conn:
        conn.execute(text(
            "INSERT OR REPLACE INTO cached_signals "
            "(code, signal_type, param, use_adjusted, date, value) "
            "VALUES (:code, :st, :p, :adj, :d, :v)"
        ), {"code": code, "st": signal_type, "p": param,
            "adj": 1 if use_adjusted else 0, "d": date, "v": value})
        conn.commit()


# ── K 线获取与复权（与 indicators.py 保持一致）─────────────────────────────

def _get_klines_before_date(code: str, date: str, limit: int) -> List[DailyKline]:
    """获取指定日期（含）前最近 limit 根K线，按时间升序排列"""
    klines = query_daily_kline(codes=[code], end_date=date, limit=limit, order_by="date DESC")
    return klines[::-1]


def _get_adj_factors_for_klines(klines: List[DailyKline]) -> Dict[str, float]:
    """批量获取K线覆盖日期范围内的复权因子"""
    if not klines:
        return {}
    code       = klines[0].code
    start_date = klines[0].date
    end_date   = klines[-1].date
    daily_basics = query_daily_basic(ts_codes=[code], start_date=start_date, end_date=end_date)
    return {b.trade_date: b.adj_factor for b in daily_basics}


def _adjust_klines(klines: List[DailyKline], adj_factors: Dict[str, float]) -> List[DailyKline]:
    """后复权处理：adjusted_price = raw_price × adj_factor

    成交量不做调整，价格字段（open/high/low/close/pre_close/change/amount）全部乘以因子。
    """
    if not klines or not adj_factors:
        return klines
    result = []
    for k in klines:
        f = adj_factors.get(k.date) or 1.0
        result.append(DailyKline(
            date=k.date, code=k.code,
            open=k.open   * f,
            high=k.high   * f,
            low=k.low     * f,
            close=k.close * f,
            volume=k.volume,
            amount=k.amount    * f if k.amount    else 0.0,
            adjustflag=k.adjustflag,
            turn=k.turn,
            pctChg=k.pctChg,
            pre_close=k.pre_close * f if k.pre_close else 0.0,
            change=k.change       * f if k.change    else 0.0,
        ))
    return result


# ── 内部辅助函数 ─────────────────────────────────────────────────────────────

def _body_ratio(k: DailyKline) -> float:
    """实体比：K线实体大小 / 总振幅（0~1）；振幅为 0 时返回 0"""
    rng = k.high - k.low
    return abs(k.close - k.open) / rng if rng > 0 else 0.0


def _upper_shadow_ratio(k: DailyKline) -> float:
    """上影线比：上影线长度 / 总振幅（0~1）；振幅为 0 时返回 0"""
    rng = k.high - k.low
    return (k.high - max(k.open, k.close)) / rng if rng > 0 else 0.0


def _lower_shadow_ratio(k: DailyKline) -> float:
    """下影线比：下影线长度 / 总振幅（0~1）；振幅为 0 时返回 0"""
    rng = k.high - k.low
    return (min(k.open, k.close) - k.low) / rng if rng > 0 else 0.0


def _is_bullish(k: DailyKline) -> bool:
    """阳线判断：收盘价 > 开盘价"""
    return k.close > k.open


def _is_bearish(k: DailyKline) -> bool:
    """阴线判断：收盘价 < 开盘价"""
    return k.close < k.open


def _linear_slope(values: List[float]) -> float:
    """最小二乘线性回归斜率（每格的平均变化量）；数据不足 2 个时返回 0"""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den > 0 else 0.0


def _find_local_highs(values: List[float], window: int = 3) -> List[int]:
    """返回局部极大值的索引列表

    在 [i-window, i+window] 范围内，values[i] 是最大值则认为是局部极大值。
    """
    result = []
    n = len(values)
    for i in range(window, n - window):
        if values[i] == max(values[i - window: i + window + 1]):
            result.append(i)
    return result


def _find_local_lows(values: List[float], window: int = 3) -> List[int]:
    """返回局部极小值的索引列表

    在 [i-window, i+window] 范围内，values[i] 是最小值则认为是局部极小值。
    """
    result = []
    n = len(values)
    for i in range(window, n - window):
        if values[i] == min(values[i - window: i + window + 1]):
            result.append(i)
    return result


# ── 形态信号函数 ─────────────────────────────────────────────────────────────

def get_morning_star(
    code: str,
    date: str,
    large_body_ratio: float = 0.6,
    doji_ratio: float = 0.3,
    penetrate_ratio: float = 0.5,
    use_adjusted: bool = True,
) -> Optional[int]:
    """早晨之星 / 启明星（Morning Star）—— 底部三K线看涨反转信号

    由三根连续K线构成的经典底部反转形态，信号在第三根K线（确认阳线）日期触发：
      · 第1根：大阴线（实体比 >= large_body_ratio），确认此前下跌趋势；
      · 第2根：十字星或小实体（实体比 <= doji_ratio），多空力量均衡，市场犹豫；
      · 第3根：大阳线（实体比 >= large_body_ratio），收盘高于第1根阴线实体
               底部向上 penetrate_ratio 处（默认刺穿中点），确认买方入场。

    使用复权价格可避免除权日产生的价格跳空被误判为星线间隙。

    Args:
        code:             股票代码，如 '000001.SZ'
        date:             计算截止日期（信号触发日期），格式 'YYYY-MM-DD'
        large_body_ratio: 大实体最小实体比阈值，默认 0.6
        doji_ratio:       星线（第2根）最大实体比阈值，默认 0.3
        penetrate_ratio:  第3根K线需从第1根阴线底部（close）向上穿透的比例，
                          默认 0.5（即收盘至少在第1根实体中点以上）
        use_adjusted:     是否使用后复权价格，默认 True

    Returns:
        int:  1 表示当日出现早晨之星（启明星），0 表示未出现；数据不足 3 根时返回 None
    """
    cached = _get_cached_signal(code, 'MORNING_STAR', 0, date, use_adjusted)
    if cached is not None:
        return cached

    klines = _get_klines_before_date(code, date, 3)
    if len(klines) < 3:
        return None

    if use_adjusted:
        klines = _adjust_klines(klines, _get_adj_factors_for_klines(klines))

    k1, k2, k3 = klines[-3], klines[-2], klines[-1]
    # k1 阴线：open > close；实体从 close（底）到 open（顶）
    k1_body = abs(k1.open - k1.close)

    value = 1 if (
        _is_bearish(k1) and _body_ratio(k1) >= large_body_ratio
        and _body_ratio(k2) <= doji_ratio
        and _is_bullish(k3) and _body_ratio(k3) >= large_body_ratio
        and k3.close >= k1.close + penetrate_ratio * k1_body
    ) else 0

    _save_signal(code, 'MORNING_STAR', 0, date, value, use_adjusted)
    return value


def get_evening_star(
    code: str,
    date: str,
    large_body_ratio: float = 0.6,
    doji_ratio: float = 0.3,
    penetrate_ratio: float = 0.5,
    use_adjusted: bool = True,
) -> Optional[int]:
    """黄昏之星 / 黄昏星（Evening Star）—— 顶部三K线看跌反转信号

    早晨之星（启明星）的镜像形态，信号在第三根K线（确认阴线）日期触发：
      · 第1根：大阳线（实体比 >= large_body_ratio），确认此前上涨趋势；
      · 第2根：十字星或小实体（实体比 <= doji_ratio），多空犹豫；
      · 第3根：大阴线（实体比 >= large_body_ratio），收盘低于第1根阳线实体
               顶部向下 penetrate_ratio 处（默认刺穿中点），确认卖方入场。

    Args:
        code:             股票代码，如 '000001.SZ'
        date:             计算截止日期（信号触发日期），格式 'YYYY-MM-DD'
        large_body_ratio: 大实体最小实体比阈值，默认 0.6
        doji_ratio:       星线（第2根）最大实体比阈值，默认 0.3
        penetrate_ratio:  第3根K线需从第1根阳线顶部（close）向下穿透的比例，
                          默认 0.5（即收盘至少在第1根实体中点以下）
        use_adjusted:     是否使用后复权价格，默认 True

    Returns:
        int:  1 表示当日出现黄昏之星（黄昏星），0 表示未出现；数据不足 3 根时返回 None
    """
    cached = _get_cached_signal(code, 'EVENING_STAR', 0, date, use_adjusted)
    if cached is not None:
        return cached

    klines = _get_klines_before_date(code, date, 3)
    if len(klines) < 3:
        return None

    if use_adjusted:
        klines = _adjust_klines(klines, _get_adj_factors_for_klines(klines))

    k1, k2, k3 = klines[-3], klines[-2], klines[-1]
    # k1 阳线：close > open；实体从 open（底）到 close（顶）
    k1_body = abs(k1.close - k1.open)

    value = 1 if (
        _is_bullish(k1) and _body_ratio(k1) >= large_body_ratio
        and _body_ratio(k2) <= doji_ratio
        and _is_bearish(k3) and _body_ratio(k3) >= large_body_ratio
        and k3.close <= k1.close - penetrate_ratio * k1_body
    ) else 0

    _save_signal(code, 'EVENING_STAR', 0, date, value, use_adjusted)
    return value


def get_three_white_soldiers(
    code: str,
    date: str,
    body_ratio: float = 0.5,
    shadow_ratio: float = 0.2,
    use_adjusted: bool = True,
) -> Optional[int]:
    """红三兵（Three White Soldiers）—— 底部连续三阳看涨确认信号

    三根连续上涨的大实体阳线，表明多方持续主导：
      · 三根全为阳线（close > open）；
      · 每根收盘价高于前一根；
      · 每根开盘价在前一根阳线实体内（逐步递进，拒绝跳空）；
      · 实体比均 >= body_ratio；
      · 上影线比均 <= shadow_ratio（收盘接近当日最高价，多方强势）。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        body_ratio:   每根K线的最小实体比阈值，默认 0.5
        shadow_ratio: 每根K线的最大上影线比阈值，默认 0.2
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        int: 1 表示当日出现红三兵，0 表示未出现；数据不足 3 根时返回 None
    """
    cached = _get_cached_signal(code, 'THREE_WHITE_SOLDIERS', 0, date, use_adjusted)
    if cached is not None:
        return cached

    klines = _get_klines_before_date(code, date, 3)
    if len(klines) < 3:
        return None

    if use_adjusted:
        klines = _adjust_klines(klines, _get_adj_factors_for_klines(klines))

    k1, k2, k3 = klines[-3], klines[-2], klines[-1]

    value = 1 if (
        _is_bullish(k1) and _is_bullish(k2) and _is_bullish(k3)
        and _body_ratio(k1) >= body_ratio
        and _body_ratio(k2) >= body_ratio
        and _body_ratio(k3) >= body_ratio
        and _upper_shadow_ratio(k1) <= shadow_ratio
        and _upper_shadow_ratio(k2) <= shadow_ratio
        and _upper_shadow_ratio(k3) <= shadow_ratio
        and k2.close > k1.close and k3.close > k2.close    # 逐步创新高
        and k1.open <= k2.open <= k1.close                  # k2 开盘在 k1 实体内
        and k2.open <= k3.open <= k2.close                  # k3 开盘在 k2 实体内
    ) else 0

    _save_signal(code, 'THREE_WHITE_SOLDIERS', 0, date, value, use_adjusted)
    return value


def get_three_black_crows(
    code: str,
    date: str,
    body_ratio: float = 0.5,
    shadow_ratio: float = 0.2,
    use_adjusted: bool = True,
) -> Optional[int]:
    """三只乌鸦（Three Black Crows）—— 顶部连续三阴看跌确认信号

    红三兵的镜像形态，三根连续下跌的大实体阴线，表明空方持续主导：
      · 三根全为阴线（close < open）；
      · 每根收盘价低于前一根；
      · 每根开盘价在前一根阴线实体内（逐步递进，拒绝跳空）；
      · 实体比均 >= body_ratio；
      · 下影线比均 <= shadow_ratio（收盘接近当日最低价，空方强势）。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        body_ratio:   每根K线的最小实体比阈值，默认 0.5
        shadow_ratio: 每根K线的最大下影线比阈值，默认 0.2
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        int: 1 表示当日出现三只乌鸦，0 表示未出现；数据不足 3 根时返回 None
    """
    cached = _get_cached_signal(code, 'THREE_BLACK_CROWS', 0, date, use_adjusted)
    if cached is not None:
        return cached

    klines = _get_klines_before_date(code, date, 3)
    if len(klines) < 3:
        return None

    if use_adjusted:
        klines = _adjust_klines(klines, _get_adj_factors_for_klines(klines))

    k1, k2, k3 = klines[-3], klines[-2], klines[-1]

    value = 1 if (
        _is_bearish(k1) and _is_bearish(k2) and _is_bearish(k3)
        and _body_ratio(k1) >= body_ratio
        and _body_ratio(k2) >= body_ratio
        and _body_ratio(k3) >= body_ratio
        and _lower_shadow_ratio(k1) <= shadow_ratio
        and _lower_shadow_ratio(k2) <= shadow_ratio
        and _lower_shadow_ratio(k3) <= shadow_ratio
        and k2.close < k1.close and k3.close < k2.close    # 逐步创新低
        and k1.close <= k2.open <= k1.open                  # k2 开盘在 k1 实体内
        and k2.close <= k3.open <= k2.open                  # k3 开盘在 k2 实体内
    ) else 0

    _save_signal(code, 'THREE_BLACK_CROWS', 0, date, value, use_adjusted)
    return value


def get_dark_cloud_cover(
    code: str,
    date: str,
    body_ratio: float = 0.5,
    penetrate_ratio: float = 0.5,
    use_adjusted: bool = True,
) -> Optional[int]:
    """乌云盖顶（Dark Cloud Cover）—— 顶部两K线看跌反转信号

    两根K线构成的顶部反转形态：
      · 第1根：大阳线（实体比 >= body_ratio），确认此前上涨；
      · 第2根：阴线，开盘价高于第1根收盘价（高位开盘），随后大幅回落，
               收盘低于第1根阳线实体顶部向下 penetrate_ratio 处（默认中点），
               且高于第1根开盘价（未完全吞没，否则为吞噬形态）。

    乌云盖顶说明多方在高位遭遇强力抛压，多空转换信号明显。

    Args:
        code:             股票代码，如 '000001.SZ'
        date:             计算截止日期，格式 'YYYY-MM-DD'
        body_ratio:       第1根阳线的最小实体比阈值，默认 0.5
        penetrate_ratio:  第2根阴线向下穿透第1根实体的最小比例，
                          默认 0.5（收盘须低于第1根实体中点）
        use_adjusted:     是否使用后复权价格，默认 True

    Returns:
        int: 1 表示当日出现乌云盖顶，0 表示未出现；数据不足 2 根时返回 None
    """
    cached = _get_cached_signal(code, 'DARK_CLOUD_COVER', 0, date, use_adjusted)
    if cached is not None:
        return cached

    klines = _get_klines_before_date(code, date, 2)
    if len(klines) < 2:
        return None

    if use_adjusted:
        klines = _adjust_klines(klines, _get_adj_factors_for_klines(klines))

    k1, k2 = klines[-2], klines[-1]
    k1_body = k1.close - k1.open   # k1 阳线：close > open，k1_body > 0

    value = 1 if (
        _is_bullish(k1) and _body_ratio(k1) >= body_ratio
        and _is_bearish(k2)
        and k2.open  >  k1.close                              # 向上跳空开盘（高于前收）
        and k2.close <  k1.close - penetrate_ratio * k1_body  # 刺入 k1 实体下半段
        and k2.close >  k1.open                               # 未完全吞没 k1（区别于吞噬形态）
    ) else 0

    _save_signal(code, 'DARK_CLOUD_COVER', 0, date, value, use_adjusted)
    return value


def get_rounding_bottom(
    code: str,
    date: str,
    period: int = 20,
    symmetry_tol: float = 0.1,
    use_adjusted: bool = True,
) -> Optional[int]:
    """圆弧底（Rounding Bottom）—— 多K线底部圆弧反转形态

    收盘价在 period 根K线内呈平滑"U"形分布，反映多空力量的渐进转换：
      · 左侧（前 1/3）平均收盘 > 中部（中 1/3）平均收盘（价格从高位缓慢下行）；
      · 右侧（后 1/3）平均收盘 > 中部平均收盘（价格从低位缓慢回升）；
      · 期间最低收盘价出现在中间三分之一区域（底部圆弧的谷底在中部）；
      · 右侧平均收盘 >= 左侧平均收盘 × (1 - symmetry_tol)（右侧已充分回升）；
      · 最近 3 根K线收盘价呈上升趋势（线性斜率 > 0，当前处于上升右侧）。

    Args:
        code:          股票代码，如 '000001.SZ'
        date:          计算截止日期，格式 'YYYY-MM-DD'
        period:        回溯K线根数，默认 20
        symmetry_tol:  右侧回升相对左侧的最小比例容差，默认 0.1（即右侧须恢复至左侧 90% 以上）
        use_adjusted:  是否使用后复权价格，默认 True

    Returns:
        int: 1 表示当日出现圆弧底，0 表示未出现；数据不足 period 根时返回 None
    """
    cached = _get_cached_signal(code, 'ROUNDING_BOTTOM', period, date, use_adjusted)
    if cached is not None:
        return cached

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        klines = _adjust_klines(klines, _get_adj_factors_for_klines(klines))

    closes = [k.close for k in klines]
    n = len(closes)
    t = n // 3

    left   = closes[:t]
    mid    = closes[t: 2 * t]
    right  = closes[2 * t:]

    avg_left  = sum(left)  / len(left)
    avg_mid   = sum(mid)   / len(mid)
    avg_right = sum(right) / len(right)

    min_idx = closes.index(min(closes))

    value = 1 if (
        avg_left  > avg_mid                              # 左侧高于底部
        and avg_right > avg_mid                          # 右侧高于底部
        and t <= min_idx < 2 * t                         # 最低点在中间三分之一
        and avg_right >= avg_left * (1 - symmetry_tol)  # 右侧已充分回升
        and _linear_slope(closes[-3:]) > 0               # 近期处于上升趋势
    ) else 0

    _save_signal(code, 'ROUNDING_BOTTOM', period, date, value, use_adjusted)
    return value


def get_ascending_triangle(
    code: str,
    date: str,
    period: int = 20,
    resistance_tol: float = 0.02,
    use_adjusted: bool = True,
) -> Optional[int]:
    """上升三角形（Ascending Triangle）—— 突破前夕看涨整理形态

    价格在一段时间内呈现"水平阻力 + 上升支撑"的三角形收敛结构：
      · 阻力线：期间局部高点聚集在同一水平（局部极大值的标准差/均值 <= resistance_tol）；
      · 支撑线：期间局部低点依次抬高（局部极小值的线性回归斜率 > 0）；
      · 当前收盘价接近阻力位（>= 阻力位 × (1 - resistance_tol)），处于突破蓄势阶段。

    判断局部极大/极小值时采用 window=3（左右各3根K线），period 至少应为 10 才能
    检测到足够数量的极值点。

    Args:
        code:            股票代码，如 '000001.SZ'
        date:            计算截止日期，格式 'YYYY-MM-DD'
        period:          回溯K线根数，默认 20
        resistance_tol:  阻力位水平性判断的最大变异系数（std/mean），默认 0.02（即 2%）
        use_adjusted:    是否使用后复权价格，默认 True

    Returns:
        int: 1 表示当日存在上升三角形形态，0 表示未出现；数据不足 period 根时返回 None
    """
    cached = _get_cached_signal(code, 'ASCENDING_TRIANGLE', period, date, use_adjusted)
    if cached is not None:
        return cached

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        klines = _adjust_klines(klines, _get_adj_factors_for_klines(klines))

    highs  = [k.high  for k in klines]
    lows   = [k.low   for k in klines]
    closes = [k.close for k in klines]

    # 阻力线：局部高点需聚集在同一水平（至少 2 个局部极大值）
    peak_idxs = _find_local_highs(highs, window=3)
    if len(peak_idxs) < 2:
        _save_signal(code, 'ASCENDING_TRIANGLE', period, date, 0, use_adjusted)
        return 0

    peak_vals = [highs[i] for i in peak_idxs]
    mean_peak = sum(peak_vals) / len(peak_vals)
    if mean_peak == 0:
        _save_signal(code, 'ASCENDING_TRIANGLE', period, date, 0, use_adjusted)
        return 0

    variance = sum((v - mean_peak) ** 2 for v in peak_vals) / len(peak_vals)
    std_peak = variance ** 0.5
    flat_resistance = (std_peak / mean_peak) <= resistance_tol

    # 支撑线：局部低点斜率 > 0（至少 2 个局部极小值）
    trough_idxs = _find_local_lows(lows, window=3)
    if len(trough_idxs) < 2:
        _save_signal(code, 'ASCENDING_TRIANGLE', period, date, 0, use_adjusted)
        return 0

    trough_vals  = [lows[i] for i in trough_idxs]
    rising_support = _linear_slope(trough_vals) > 0

    # 当前价格接近阻力位（突破前夕）
    resistance    = max(highs)
    near_breakout = closes[-1] >= resistance * (1 - resistance_tol)

    value = 1 if (flat_resistance and rising_support and near_breakout) else 0

    _save_signal(code, 'ASCENDING_TRIANGLE', period, date, value, use_adjusted)
    return value


def get_top_pattern(
    code: str,
    date: str,
    period: int = 30,
    tolerance: float = 0.03,
    min_decline: float = 0.03,
    use_adjusted: bool = True,
) -> Optional[int]:
    """顶部形态（Top Pattern）—— 双重顶等多K线顶部反转结构

    以双重顶（Double Top）为核心，检测 period 根K线内的顶部反转结构：
      · 在期间内找到至少 2 个局部高点；
      · 取高度最高的两个局部高点，其价差 / 均值 <= tolerance（两顶高度相近）；
      · 两顶之间存在有意义的颈线回调：颈线最低价低于两顶均价的 min_decline 比例；
      · 第二个高点出现在期间后半段；
      · 当前收盘价已从第二个高点回落（< 第二高点 × (1 - tolerance)），确认顶部形成。

    Args:
        code:         股票代码，如 '000001.SZ'
        date:         计算截止日期，格式 'YYYY-MM-DD'
        period:       回溯K线根数，默认 30
        tolerance:    两高点价格允许偏差比例 及 回落确认比例，默认 0.03（即 3%）
        min_decline:  颈线相对两顶均价的最小回落比例，默认 0.03（即 3%）
        use_adjusted: 是否使用后复权价格，默认 True

    Returns:
        int: 1 表示当日存在顶部形态，0 表示未出现；数据不足 period 根时返回 None
    """
    cached = _get_cached_signal(code, 'TOP_PATTERN', period, date, use_adjusted)
    if cached is not None:
        return cached

    klines = _get_klines_before_date(code, date, period)
    if len(klines) < period:
        return None

    if use_adjusted:
        klines = _adjust_klines(klines, _get_adj_factors_for_klines(klines))

    highs  = [k.high for k in klines]
    lows   = [k.low  for k in klines]
    closes = [k.close for k in klines]

    # 找局部高点（至少需要 2 个）
    peak_idxs = _find_local_highs(highs, window=3)
    if len(peak_idxs) < 2:
        _save_signal(code, 'TOP_PATTERN', period, date, 0, use_adjusted)
        return 0

    # 取高度最高的两个局部高点，按时间排序（idx1 更早，idx2 更晚）
    sorted_by_height = sorted(peak_idxs, key=lambda i: highs[i], reverse=True)
    idx1, idx2 = sorted(sorted_by_height[:2])  # 按时间先后排序

    peak1    = highs[idx1]
    peak2    = highs[idx2]
    avg_peak = (peak1 + peak2) / 2.0

    # 两顶高度相近
    if avg_peak == 0 or abs(peak1 - peak2) / avg_peak > tolerance:
        _save_signal(code, 'TOP_PATTERN', period, date, 0, use_adjusted)
        return 0

    # 两顶之间的颈线（最低价）
    neckline = min(lows[idx1: idx2 + 1])
    if (avg_peak - neckline) / avg_peak < min_decline:
        _save_signal(code, 'TOP_PATTERN', period, date, 0, use_adjusted)
        return 0

    # 第二高点在后半段，且当前价格已从第二顶回落
    half = period // 2
    value = 1 if (
        idx2 >= half
        and closes[-1] < peak2 * (1 - tolerance)
    ) else 0

    _save_signal(code, 'TOP_PATTERN', period, date, value, use_adjusted)
    return value


# ── 别名函数 ─────────────────────────────────────────────────────────────────

def get_qiming_star(
    code: str,
    date: str,
    large_body_ratio: float = 0.6,
    doji_ratio: float = 0.3,
    penetrate_ratio: float = 0.5,
    use_adjusted: bool = True,
) -> Optional[int]:
    """启明星（早晨之星，Morning Star）—— get_morning_star 的别名

    与 get_morning_star 完全等价，共享同一缓存键（MORNING_STAR）。

    Returns:
        int: 1 表示当日出现启明星（早晨之星），0 表示未出现；数据不足 3 根时返回 None
    """
    return get_morning_star(code, date, large_body_ratio, doji_ratio, penetrate_ratio, use_adjusted)


def get_huanghun_star(
    code: str,
    date: str,
    large_body_ratio: float = 0.6,
    doji_ratio: float = 0.3,
    penetrate_ratio: float = 0.5,
    use_adjusted: bool = True,
) -> Optional[int]:
    """黄昏星（黄昏之星，Evening Star）—— get_evening_star 的别名

    与 get_evening_star 完全等价，共享同一缓存键（EVENING_STAR）。

    Returns:
        int: 1 表示当日出现黄昏星（黄昏之星），0 表示未出现；数据不足 3 根时返回 None
    """
    return get_evening_star(code, date, large_body_ratio, doji_ratio, penetrate_ratio, use_adjusted)
