#!/usr/bin/env python3
"""screen.py — 冯柳“弱者体系”/逆向投资 A 股初筛。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out weak_side_result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out weak_side_result.csv

弱者视角核心逻辑:
    1. 股价大幅下跌：距 52 周高点回撤 > 40%，市场对负面信息已较充分定价。
    2. 基本面未崩：最近报告期净利润为正、营收同比未大幅下滑。
    3. 估值打到历史低位：PE/PB 处于近 3 年历史估值区间的下沿。
    4. 市场关注度低：换手率低于市场平均水平，属于“没人愿意讨论”的标的。
    5. 输出“赔率 / 概率”框架：赔率来自跌幅与估值，概率来自基本面韧性。

数据源: akshare（东方财富估值/财务为主，东财失败自动降级同花顺/新浪行情）。
"""
import os

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import argparse
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import akshare as ak
except ImportError:
    sys.exit("ERROR: 未安装 akshare，请先执行: pip install akshare pandas")

YEARS = 5
DRAWDOWN_THRESHOLD = 40.0


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理干扰东财/同花顺直连。"""
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(k, None)


def _retry_call(func, max_retries: int = 3, sleep_base: float = 1.0):
    """带指数退避的简单重试，最后一次失败抛出原异常。"""
    last_err = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(sleep_base * (2 ** attempt))
    raise last_err


def normalize_date(date_str: str) -> str:
    """兼容 20231231 与 2023-12-31，统一返回 2023-12-31。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return date_str


def safe_div(a, b, default=float("nan")):
    """除零防护：b 为 0 或 nan 时返回 default。"""
    try:
        if pd.isna(a) or pd.isna(b):
            return default
        b = float(b)
        if b == 0:
            return default
        return float(a) / b
    except Exception:
        return default


def _find_col(candidates: list, df: pd.DataFrame) -> Optional[str]:
    """按候选子串在 df 列名中查找第一个匹配列。"""
    for c in df.columns:
        for cand in candidates:
            if cand in str(c):
                return c
    return None


def _to_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


def _market_prefix(code: str) -> str:
    """A 股代码前缀：6/5 开头为 sh，其余为 sz。"""
    c = str(code).strip()
    if c.startswith("6") or c.startswith("5"):
        return "sh"
    return "sz"


# ---------------------------------------------------------------------------
# 股票池
# ---------------------------------------------------------------------------

def get_pool(pool: str) -> list:
    if pool == "hs300":
        errs = []
        try:
            df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
            col = _find_col(["成分券代码", "股票代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"csindex: {e}")

        time.sleep(0.15)
        try:
            df = _retry_call(lambda: ak.index_stock_cons_weight_csindex(symbol="000300"))
            col = _find_col(["成分券代码", "股票代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"weight csindex: {e}")

        sys.exit(f"ERROR: 获取沪深300成分股失败: {'; '.join(errs)}")

    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


# ---------------------------------------------------------------------------
# 市场快照（同花顺/腾讯，东财行情不可达时的主要行情来源）
# ---------------------------------------------------------------------------

def fetch_spot_tx() -> dict:
    """全市场快照，返回 {code6: {...}}。字段全部为字符串，使用方负责转换。"""
    df = _retry_call(lambda: ak.stock_zh_a_spot_tx())
    time.sleep(0.15)
    if df is None or df.empty:
        return {}
    out = {}
    for _, row in df.iterrows():
        full = str(row.get("code", "")).strip().lower()
        if len(full) < 8:
            continue
        code6 = full[-6:]
        out[code6] = {
            "name": str(row.get("name", "")),
            "pe_ttm": str(row.get("pe_ttm", "")),
            "pb": str(row.get("pn", "")),
            "close": str(row.get("zxj", "")),
            "turnover_pct": str(row.get("hsl", "")),
            "total_mv": str(row.get("zsz", "")),
            "zdf_w52": str(row.get("zdf_w52", "")),
        }
    return out


# ---------------------------------------------------------------------------
# 基本面：最新业绩报表 + 5 年财务指标
# ---------------------------------------------------------------------------

def fetch_yjbb_meta() -> pd.DataFrame:
    """全市场最新业绩报表中的代码、名称、行业、营收/利润映射。"""
    now = datetime.now()
    candidates = []
    for y in range(now.year, now.year - 2, -1):
        for m, d in ((12, 31), (9, 30), (6, 30), (3, 31)):
            candidates.append(f"{y}{m:02d}{d:02d}")

    for date in candidates:
        try:
            df = _retry_call(lambda d=date: ak.stock_yjbb_em(date=d))
            time.sleep(0.15)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        code_col = _find_col(["股票代码"], df)
        name_col = _find_col(["股票简称"], df)
        ind_col = _find_col(["所处行业"], df)
        rev_col = _find_col(["营业总收入-营业总收入"], df)
        profit_col = _find_col(["净利润-净利润"], df)
        rev_yoy_col = _find_col(["营业总收入-同比增长"], df)
        profit_yoy_col = _find_col(["净利润-同比增长"], df)
        if code_col is None:
            continue

        s = df.copy()
        s["code"] = s[code_col].astype(str).str.strip().str.zfill(6)
        s = s.drop_duplicates("code")
        out = pd.DataFrame({"code": s["code"].values})
        if name_col is not None:
            out["name"] = s[name_col].astype(str).values
        if ind_col is not None:
            out["industry"] = s[ind_col].astype(str).values
        if rev_col is not None:
            out["total_revenue"] = _to_numeric_series(s[rev_col]).values
        if profit_col is not None:
            out["net_profit"] = _to_numeric_series(s[profit_col]).values
        if rev_yoy_col is not None:
            out["revenue_yoy"] = _to_numeric_series(s[rev_yoy_col]).values
        if profit_yoy_col is not None:
            out["profit_yoy"] = _to_numeric_series(s[profit_yoy_col]).values
        return out

    return pd.DataFrame(columns=["code", "name", "industry", "total_revenue", "net_profit", "revenue_yoy", "profit_yoy"])


def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """获取主要财务指标（年报），失败抛异常。"""
    start_year = datetime.now().year - YEARS - 2
    df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=str(start_year)))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("财务指标为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df) or df.columns[0]
    df[date_col] = df[date_col].astype(str).apply(normalize_date)
    today = datetime.now().strftime("%Y-%m-%d")
    df = df[(df[date_col].str.endswith("12-31")) & (df[date_col] <= today)]
    df = df.sort_values(date_col).tail(YEARS)
    if df.empty:
        raise RuntimeError("无年度财务指标数据")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 行情：日线（52 周高点、换手率）与估值历史
# ---------------------------------------------------------------------------

def fetch_daily(code: str) -> pd.DataFrame:
    """新浪日线。失败抛异常；过滤掉未来日期。"""
    symbol = f"{_market_prefix(code)}{code}"
    df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=symbol))
    time.sleep(0.15)
    if df is None or df.empty or "date" not in df.columns:
        raise RuntimeError("日线为空或格式异常")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    today = pd.Timestamp.now().normalize()
    df = df[df["date"] <= today]
    if df.empty:
        raise RuntimeError("日线无有效历史数据")
    return df.sort_values("date").reset_index(drop=True)


def fetch_value_history(code: str) -> pd.DataFrame:
    """东财历史估值序列。失败抛异常；过滤未来日期。"""
    df = _retry_call(lambda: ak.stock_value_em(symbol=code))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("估值序列为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    today = pd.Timestamp.now().normalize()
    df = df[(df[date_col].notna()) & (df[date_col] <= today)]
    if df.empty:
        raise RuntimeError("估值序列无有效数据")
    return df.sort_values(date_col).reset_index(drop=True)


def compute_drawdown(daily_df: pd.DataFrame, current_close: float) -> tuple:
    """基于日线 high 计算 52 周高点回撤。返回 (high_52w, drawdown_pct)。"""
    if daily_df is None or daily_df.empty or len(daily_df) < 20:
        return None, None
    lookback = daily_df.tail(252)
    high = lookback["high"].max()
    if pd.isna(high) or high == 0:
        return None, None
    drawdown = (high - current_close) / high * 100
    return high, drawdown


def compute_valuation_percentile(value_df: pd.DataFrame, pe_current: Optional[float], pb_current: Optional[float]) -> dict:
    """计算当前 PE/PB 在近 3 年估值历史中的百分位（越小越便宜）。"""
    out = {"pe_percentile": None, "pb_percentile": None, "pe_low": None, "pe_high": None, "pb_low": None, "pb_high": None}
    if value_df is None or value_df.empty:
        return out
    date_col = value_df.columns[0]
    cutoff = pd.Timestamp.now().normalize() - timedelta(days=365 * 3)
    sub = value_df[value_df[date_col] >= cutoff].copy()
    if sub.empty:
        sub = value_df.tail(252).copy()

    pe_col = _find_col(["PE(TTM)"], sub)
    pb_col = _find_col(["市净率"], sub)

    if pe_col is not None:
        pe = _to_numeric_series(sub[pe_col]).dropna()
        pe = pe[pe > 0]
        if not pe.empty:
            out["pe_low"] = round(float(pe.min()), 2)
            out["pe_high"] = round(float(pe.max()), 2)
            if pd.notna(pe_current) and pe_current > 0:
                out["pe_percentile"] = round(float((pe < pe_current).mean() * 100), 2)

    if pb_col is not None:
        pb = _to_numeric_series(sub[pb_col]).dropna()
        pb = pb[pb > 0]
        if not pb.empty:
            out["pb_low"] = round(float(pb.min()), 3)
            out["pb_high"] = round(float(pb.max()), 3)
            if pd.notna(pb_current) and pb_current > 0:
                out["pb_percentile"] = round(float((pb < pb_current).mean() * 100), 2)

    return out


# ---------------------------------------------------------------------------
# 单只股票分析
# ---------------------------------------------------------------------------

def analyze_one(code: str, spot_map: dict, meta_map: pd.DataFrame) -> dict:
    # 1. 名称/行业/最新业绩
    meta_row = meta_map[meta_map["code"] == code]
    name = str(meta_row["name"].iloc[0]) if not meta_row.empty else ""
    industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty else ""
    latest_revenue = float(meta_row["total_revenue"].iloc[0]) if not meta_row.empty and pd.notna(meta_row["total_revenue"].iloc[0]) else None
    latest_profit = float(meta_row["net_profit"].iloc[0]) if not meta_row.empty and pd.notna(meta_row["net_profit"].iloc[0]) else None
    revenue_yoy = float(meta_row["revenue_yoy"].iloc[0]) if not meta_row.empty and pd.notna(meta_row["revenue_yoy"].iloc[0]) else None
    profit_yoy = float(meta_row["profit_yoy"].iloc[0]) if not meta_row.empty and pd.notna(meta_row["profit_yoy"].iloc[0]) else None

    # 2. 当前行情
    spot = spot_map.get(code, {})
    close = pd.to_numeric(spot.get("close"), errors="coerce")
    pe_ttm = pd.to_numeric(spot.get("pe_ttm"), errors="coerce")
    pb = pd.to_numeric(spot.get("pb"), errors="coerce")
    turnover_pct = pd.to_numeric(spot.get("turnover_pct"), errors="coerce")
    total_mv = pd.to_numeric(spot.get("total_mv"), errors="coerce")

    # 3. 日线：52 周高点回撤 + 最新换手率兜底
    daily_df = None
    daily_turnover = None
    try:
        daily_df = fetch_daily(code)
        if daily_df is not None and not daily_df.empty:
            close = pd.to_numeric(daily_df["close"].iloc[-1], errors="coerce") if pd.isna(close) else close
            daily_turnover = pd.to_numeric(daily_df["turnover"].iloc[-1], errors="coerce")
            daily_turnover = daily_turnover * 100 if pd.notna(daily_turnover) else None
    except Exception as e:
        daily_df = None
        daily_turnover = None

    high_52w, drawdown = compute_drawdown(daily_df, close) if daily_df is not None else (None, None)

    # 4. 估值历史百分位
    value_df = None
    val_percentile = {}
    val_source = "spot_tx（当前估值）"
    try:
        value_df = fetch_value_history(code)
        val_percentile = compute_valuation_percentile(value_df, pe_ttm, pb)
        val_source = "akshare.stock_value_em"
    except Exception as e:
        # 东财估值历史失败时，仅保留当前估值
        pass

    # 5. 5 年财务指标
    fin = fetch_financial_indicator(code)
    rev_growth = series_or_empty(fin, "主营业务收入增长率(%)")
    profit_growth = series_or_empty(fin, "净利润增长率(%)")
    roe = series_or_empty(fin, "净资产收益率(%)")
    gross = series_or_empty(fin, "销售毛利率(%)")
    debt = series_or_empty(fin, "资产负债率(%)")

    avg_rev_growth = round(float(rev_growth.mean()), 2) if not rev_growth.empty else None
    avg_profit_growth = round(float(profit_growth.mean()), 2) if not profit_growth.empty else None
    avg_roe = round(float(roe.mean()), 2) if not roe.empty else None
    avg_gross = round(float(gross.mean()), 2) if not gross.empty else None
    latest_debt = round(float(debt.iloc[-1]), 2) if not debt.empty else None

    # 6. 赔率 / 概率框架
    score, odds_label, prob_label, framework_note = build_framework(
        drawdown, val_percentile.get("pe_percentile"), val_percentile.get("pb_percentile"),
        pe_ttm, pb, latest_profit, revenue_yoy, profit_yoy, avg_roe, latest_debt, turnover_pct
    )

    # 7. 硬门槛标记
    weak_pass = 0
    if (
        drawdown is not None and drawdown > DRAWDOWN_THRESHOLD
        and latest_profit is not None and latest_profit > 0
        and (revenue_yoy is None or revenue_yoy > -20)
        and (val_percentile.get("pe_percentile") is not None or val_percentile.get("pb_percentile") is not None)
    ):
        weak_pass = 1

    return {
        "code": code,
        "name": name,
        "industry": industry,
        "close": round(float(close), 2) if pd.notna(close) else None,
        "high_52w": round(float(high_52w), 2) if pd.notna(high_52w) else None,
        "drawdown_pct": round(float(drawdown), 2) if pd.notna(drawdown) else None,
        "pe_ttm": round(float(pe_ttm), 2) if pd.notna(pe_ttm) else None,
        "pb": round(float(pb), 3) if pd.notna(pb) else None,
        "pe_percentile_3y": val_percentile.get("pe_percentile"),
        "pb_percentile_3y": val_percentile.get("pb_percentile"),
        "pe_low_3y": val_percentile.get("pe_low"),
        "pe_high_3y": val_percentile.get("pe_high"),
        "pb_low_3y": val_percentile.get("pb_low"),
        "pb_high_3y": val_percentile.get("pb_high"),
        "turnover_pct": round(float(turnover_pct), 2) if pd.notna(turnover_pct) else round(float(daily_turnover), 2) if daily_turnover is not None else None,
        "total_mv": round(float(total_mv), 2) if pd.notna(total_mv) else None,
        "latest_revenue": round(float(latest_revenue / 1e8), 2) if latest_revenue is not None else None,
        "latest_profit": round(float(latest_profit / 1e8), 2) if latest_profit is not None else None,
        "revenue_yoy": round(float(revenue_yoy), 2) if revenue_yoy is not None else None,
        "profit_yoy": round(float(profit_yoy), 2) if profit_yoy is not None else None,
        "avg_rev_growth_5y": avg_rev_growth,
        "avg_profit_growth_5y": avg_profit_growth,
        "avg_roe_5y": avg_roe,
        "avg_gross_5y": avg_gross,
        "latest_debt": latest_debt,
        "weak_score": score,
        "odds_label": odds_label,
        "probability_label": prob_label,
        "framework_note": framework_note,
        "weak_pass": weak_pass,
        "data_years": min(len(rev_growth), len(profit_growth), len(roe), len(debt)),
        "val_source": val_source,
    }


def series_or_empty(df: pd.DataFrame, *keys) -> pd.Series:
    col = _find_col(list(keys), df)
    if col is None:
        return pd.Series(dtype=float)
    return _to_numeric_series(df[col])


def build_framework(
    drawdown: Optional[float],
    pe_pct: Optional[float],
    pb_pct: Optional[float],
    pe_ttm: Optional[float],
    pb: Optional[float],
    latest_profit: Optional[float],
    revenue_yoy: Optional[float],
    profit_yoy: Optional[float],
    avg_roe: Optional[float],
    latest_debt: Optional[float],
    turnover_pct: Optional[float],
) -> tuple:
    """返回 (weak_score, odds_label, probability_label, framework_note)。"""
    # 赔率：由跌幅深度 + 估值低位决定
    odds_score = 0
    odds_notes = []
    if drawdown is not None:
        if drawdown >= 50:
            odds_score += 15
            odds_notes.append(f"回撤{drawdown:.1f}%")
        elif drawdown >= 40:
            odds_score += 12
            odds_notes.append(f"回撤{drawdown:.1f}%")
        elif drawdown >= 30:
            odds_score += 7
            odds_notes.append(f"回撤{drawdown:.1f}%")
        elif drawdown >= 20:
            odds_score += 3

    # 估值低位：用 PE/PB 百分位，越小越便宜
    low_pct = None
    if pe_pct is not None and pb_pct is not None:
        low_pct = min(pe_pct, pb_pct)
    elif pe_pct is not None:
        low_pct = pe_pct
    elif pb_pct is not None:
        low_pct = pb_pct

    if low_pct is not None:
        if low_pct <= 10:
            odds_score += 15
            odds_notes.append(f"估值百分位{low_pct:.1f}%")
        elif low_pct <= 20:
            odds_score += 10
            odds_notes.append(f"估值百分位{low_pct:.1f}%")
        elif low_pct <= 30:
            odds_score += 5
    else:
        # 无历史百分位时，用绝对估值兜底
        if pe_ttm is not None and pe_ttm > 0 and pe_ttm < 15:
            odds_score += 5
            odds_notes.append(f"PE(TTM){pe_ttm:.1f}")
        if pb is not None and pb > 0 and pb < 1.5:
            odds_score += 5
            odds_notes.append(f"PB{pb:.2f}")

    # 概率：由基本面韧性决定
    prob_score = 0
    prob_notes = []
    if latest_profit is not None and latest_profit > 0:
        prob_score += 10
        prob_notes.append("盈利为正")
    if revenue_yoy is not None:
        if revenue_yoy > 0:
            prob_score += 10
            prob_notes.append(f"营收同比{revenue_yoy:.1f}%")
        elif revenue_yoy > -10:
            prob_score += 5
            prob_notes.append(f"营收微降{revenue_yoy:.1f}%")
        else:
            prob_notes.append(f"营收下滑{revenue_yoy:.1f}%")
    else:
        prob_score += 3

    if profit_yoy is not None:
        if profit_yoy > 0:
            prob_score += 10
            prob_notes.append(f"利润同比{profit_yoy:.1f}%")
        elif profit_yoy > -20:
            prob_score += 5
            prob_notes.append(f"利润微降{profit_yoy:.1f}%")
        else:
            prob_notes.append(f"利润下滑{profit_yoy:.1f}%")
    else:
        prob_score += 3

    if avg_roe is not None:
        if avg_roe > 15:
            prob_score += 10
        elif avg_roe > 10:
            prob_score += 6
        elif avg_roe > 5:
            prob_score += 3

    if latest_debt is not None and latest_debt < 60:
        prob_score += 5

    # 市场关注度：换手率越低，越符合“弱者视角”中被遗忘的标的
    attention_score = 0
    if turnover_pct is not None:
        if turnover_pct < 0.5:
            attention_score += 10
        elif turnover_pct < 1.0:
            attention_score += 7
        elif turnover_pct < 2.0:
            attention_score += 4

    total = min(odds_score + prob_score + attention_score, 100)

    # 标签
    if odds_score >= 20:
        odds_label = "高赔率"
    elif odds_score >= 12:
        odds_label = "中高赔率"
    elif odds_score >= 6:
        odds_label = "中等赔率"
    else:
        odds_label = "赔率不足"

    if prob_score >= 35:
        prob_label = "高概率"
    elif prob_score >= 25:
        prob_label = "中高概率"
    elif prob_score >= 15:
        prob_label = "中等概率"
    else:
        prob_label = "概率偏低"

    note = f"赔率来源：{', '.join(odds_notes) if odds_notes else '待观察'}；概率来源：{', '.join(prob_notes) if prob_notes else '待验证'}"
    return total, odds_label, prob_label, note


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="冯柳弱者体系 / 逆向投资 A 股初筛")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="weak_side_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    _disable_proxies()

    codes = [c.strip().zfill(6) for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    print(f"股票池共 {len(codes)} 只，开始加载行情与基本面映射...")

    spot_map = fetch_spot_tx()
    print(f"行情快照加载完成，覆盖 {len(spot_map)} 只股票。")

    meta_map = fetch_yjbb_meta()
    print(f"业绩报表加载完成，覆盖 {len(meta_map)} 只股票。开始逐一分析...")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = analyze_one(code, spot_map, meta_map)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} {r['name']} 得分 {r['weak_score']} | 赔率{r['odds_label']} / 概率{r['probability_label']} | 回撤{r['drawdown_pct']}%")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("weak_score", ascending=False).reset_index(drop=True)
    df["data_date"] = normalize_date(datetime.now().strftime("%Y%m%d"))
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "code", "name", "weak_score", "odds_label", "probability_label", "drawdown_pct",
        "pe_ttm", "pe_percentile_3y", "pb", "pb_percentile_3y", "turnover_pct",
        "latest_profit", "profit_yoy", "revenue_yoy", "latest_debt", "weak_pass",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    print(df.head(args.top)[display_cols].to_string(index=False))

    pass_df = df[df["weak_pass"] == 1]
    if not pass_df.empty:
        print(f"\n通过弱者体系硬门槛（回撤>{DRAWDOWN_THRESHOLD}% + 盈利为正 + 营收未大幅下滑）: {len(pass_df)} 只")
        print(", ".join(pass_df["code"].tolist()))
    else:
        print(f"\n本次筛选没有股票通过硬门槛（回撤>{DRAWDOWN_THRESHOLD}% + 盈利为正 + 营收未大幅下滑）。")

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    if failed:
        print("失败股票:", ", ".join(f"{c}({e})" for c, e in failed[:10]))
    print("判定线: >=70 重点关注；50-69 观察池；<50 暂不符合框架。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
