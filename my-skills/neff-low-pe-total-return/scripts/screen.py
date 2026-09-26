#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen.py — 约翰·聂夫低市盈率+总回报率 A 股打分器。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out neff_result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out neff_result.csv

筛选逻辑（聂夫温莎基金规则的机械化近似）:
    1. 低市盈率：个股 PE(TTM) 相对全市场中位数的折价（聂夫:买入价格是收益的一半）。
    2. 总回报率：(净利润增速均值 + 股息率) / PE >= 2 为聂夫的黄金标准。
    3. 股息率：持续分红是"被无人喜爱的好公司"的特征。
    4. 基本面底线：盈利增长为正、ROE 达标、低负债、利润含金量。
    打分排序输出 CSV，供进一步定性复核（"遭人嫌弃的好生意"）。

数据源: akshare（东财估值/财务指标 + 巨潮分红 + 腾讯全市场快照，失败自动降级）。
"""
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Optional

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

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


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理阻断数据源直连。"""
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
        cs = str(c)
        for cand in candidates:
            if cand in cs:
                return c
    return None


def _to_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


# ---------------------------------------------------------------------------
# 股票池与市场基准
# ---------------------------------------------------------------------------

def get_pool(pool: str) -> list:
    if pool == "hs300":
        errs = []
        try:
            df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
            time.sleep(0.15)
            col = _find_col(["成分券代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"csindex: {e}")
        try:
            df = _retry_call(lambda: ak.index_stock_cons_weight_csindex(symbol="000300"))
            time.sleep(0.15)
            col = _find_col(["成分券代码", "股票代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"weight csindex: {e}")
        sys.exit(f"ERROR: 获取沪深300成分股失败: {'; '.join(errs)}")
    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


def fetch_market_median_pe() -> tuple[Optional[float], str]:
    """腾讯全市场快照计算全市场 PE(TTM) 中位数，作为低市盈率的基准。失败返回 None。"""
    try:
        df = _retry_call(lambda: ak.stock_zh_a_spot_tx())
        time.sleep(0.15)
        if df is None or df.empty or "pe_ttm" not in df.columns:
            return None, ""
        pe = pd.to_numeric(df["pe_ttm"], errors="coerce")
        pe = pe[(pe > 0) & (pe < 300)]  # 排除亏损与极端值
        if pe.empty:
            return None, ""
        return float(pe.median()), "akshare.stock_zh_a_spot_tx"
    except Exception:
        return None, ""


def fetch_industry_map() -> pd.DataFrame:
    """从最新业绩报表获取代码->名称/行业映射。失败返回空 DataFrame。"""
    now = datetime.now()
    candidates = []
    for y in range(now.year, now.year - 3, -1):
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
        if "industry" in out.columns and out["industry"].notna().sum() > 0:
            return out.dropna(subset=["industry"]).reset_index(drop=True)
    return pd.DataFrame(columns=["code", "name", "industry"])


# ---------------------------------------------------------------------------
# 个股数据
# ---------------------------------------------------------------------------

def fetch_value_em(code: str) -> pd.DataFrame:
    """东财个股历史估值表，过滤未来日期。失败抛异常。"""
    df = _retry_call(lambda: ak.stock_value_em(symbol=code))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("估值数据为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["数据日期"], df) or df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[df[date_col] <= pd.Timestamp.now()]
    if df.empty:
        raise RuntimeError("无有效历史估值数据")
    return df.sort_values(date_col).reset_index(drop=True)


def fetch_tx_fallback(code: str) -> dict:
    """腾讯全市场快照降级取 PE/收盘价。"""
    prefix = "sh" if code.startswith("6") or code.startswith("5") else "sz"
    full = f"{prefix}{code}"
    try:
        df = _retry_call(lambda: ak.stock_zh_a_spot_tx())
        time.sleep(0.15)
    except Exception:
        return {}
    if df is None or df.empty or "code" not in df.columns:
        return {}
    row = df[df["code"].astype(str).str.lower() == full]
    if row.empty:
        return {}
    r = row.iloc[-1]
    return {
        "pe_ttm": pd.to_numeric(r.get("pe_ttm"), errors="coerce"),
        "close": pd.to_numeric(r.get("zxj"), errors="coerce"),
    }


def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """近 YEARS 年主要财务指标（年报）。失败抛异常。"""
    start_year = datetime.now().year - YEARS - 2
    df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=str(start_year)))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("财务指标为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df) or df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col].astype(str).apply(normalize_date), errors="coerce")
    today = pd.Timestamp.now()
    df = df[(df[date_col].dt.month == 12) & (df[date_col] <= today)]
    df = df.sort_values(date_col).tail(YEARS)
    if df.empty:
        raise RuntimeError("无年度财务数据")
    return df.reset_index(drop=True)


def fetch_sina_report(code: str, report_type: str) -> pd.DataFrame:
    """新浪三大报表（年报）。失败返回空 DataFrame。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol=report_type))
    except Exception:
        return pd.DataFrame()
    time.sleep(0.15)
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["报告日"] = df["报告日"].astype(str).str.replace("-", "")
    today = pd.Timestamp.now().strftime("%Y%m%d")
    df = df[(df["报告日"].str.endswith("1231")) & (df["报告日"] <= today)]
    df = df.sort_values("报告日").tail(YEARS)
    return df.reset_index(drop=True)


def fetch_dividend_cninfo(code: str) -> pd.DataFrame:
    """巨潮资讯分红数据，失败返回空 DataFrame；过滤未来日期。"""
    try:
        df = _retry_call(lambda: ak.stock_dividend_cninfo(symbol=code))
    except Exception:
        return pd.DataFrame()
    time.sleep(0.15)
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["实施方案公告日期"], df)
    if date_col is None:
        return pd.DataFrame()
    df[date_col] = df[date_col].astype(str).apply(normalize_date)
    df = df[df[date_col] <= datetime.now().strftime("%Y-%m-%d")]
    return df.reset_index(drop=True)


def _annual_dividend_per_share(div_df: pd.DataFrame) -> tuple:
    """按最近 5 次派息的实际时间跨度年化每股分红（元），返回 (年化DPS, 次数, 跨度年)。

    一年分红两次的银行股、含特别分红的公司，直接把 5 次相加会虚高 2~3 倍，
    这里按跨度年化：年化DPS = (5次合计/10) / max(跨度年, 0.8)。
    """
    if div_df.empty:
        return float("nan"), 0, float("nan")
    ratio_col = _find_col(["派息比例"], div_df)
    date_col = _find_col(["实施方案公告日期"], div_df)
    if ratio_col is None or date_col is None:
        return float("nan"), 0, float("nan")
    sub = div_df[[ratio_col, date_col]].copy()
    sub[ratio_col] = _to_numeric_series(sub[ratio_col])
    sub[date_col] = pd.to_datetime(sub[date_col], errors="coerce")
    sub = sub.dropna().sort_values(date_col)
    if sub.empty:
        return float("nan"), 0, float("nan")
    last5 = sub.tail(5)
    total_per_share = float(last5[ratio_col].sum()) / 10.0  # 每 10 股派 X 元 -> 每股
    span_years = max((last5[date_col].iloc[-1] - last5[date_col].iloc[0]).days / 365.25, 0.8)
    return total_per_share / span_years, len(last5), span_years


def get_financials(code: str) -> dict:
    """ROE / 净利润增速 / 负债率 / 现金流含金量，东财优先，新浪降级。"""
    errs = []
    try:
        df = fetch_financial_indicator(code)
        roe_col = _find_col(["净资产收益率(%)"], df)
        debt_col = _find_col(["资产负债率(%)"], df)
        ocf_col = _find_col(["经营现金净流量与净利润的比率(%)"], df)
        growth_col = _find_col(["净利润增长率(%)"], df)
        if roe_col is None:
            raise RuntimeError("财务指标表缺少 ROE 列")
        out = {
            "roe": _to_numeric_series(df[roe_col]).dropna(),
            "debt": _to_numeric_series(df[debt_col]).dropna() if debt_col is not None else pd.Series(dtype=float),
            "ocf": _to_numeric_series(df[ocf_col]).dropna() if ocf_col is not None else pd.Series(dtype=float),
            "profit_growth": _to_numeric_series(df[growth_col]).dropna() if growth_col is not None else pd.Series(dtype=float),
            "source": "akshare.stock_financial_analysis_indicator",
            "note": "",
        }
        if out["profit_growth"].empty:
            time.sleep(0.15)
            inc = fetch_sina_report(code, "利润表")
            if not inc.empty:
                profit_col = _find_col(["净利润"], inc)
                if profit_col is not None:
                    profit = _to_numeric_series(inc[profit_col]).dropna()
                    if len(profit) >= 2:
                        out["profit_growth"] = (profit.pct_change().dropna() * 100).dropna()
                        out["note"] = "净利润增速由新浪利润表补充"
        return out
    except Exception as e:
        errs.append(f"财务指标表: {e}")

    time.sleep(0.15)
    try:
        inc = fetch_sina_report(code, "利润表")
        bs = fetch_sina_report(code, "资产负债表")
        if inc.empty or bs.empty:
            raise RuntimeError("新浪三大报表不足以计算指标")
        profit_col = _find_col(["净利润"], inc)
        equity_col = _find_col(["所有者权益(或股东权益)合计"], bs)
        out = {"roe": pd.Series(dtype=float), "debt": pd.Series(dtype=float),
               "ocf": pd.Series(dtype=float), "profit_growth": pd.Series(dtype=float),
               "source": "akshare.stock_financial_report_sina（降级）", "note": ""}
        if profit_col is not None:
            profit = _to_numeric_series(inc[profit_col]).dropna()
            if len(profit) >= 2:
                out["profit_growth"] = (profit.pct_change().dropna() * 100).dropna()
            if equity_col is not None:
                equity = _to_numeric_series(bs[equity_col])
                out["roe"] = (profit / equity.replace(0, float("nan")) * 100).dropna()
        liab_col = _find_col(["负债合计"], bs)
        asset_col = _find_col(["资产总计"], bs)
        if liab_col is not None and asset_col is not None:
            out["debt"] = (_to_numeric_series(bs[liab_col]) / _to_numeric_series(bs[asset_col]).replace(0, float("nan")) * 100).dropna()
        out["note"] = "新浪三大报表降级计算"
        return out
    except Exception as e:
        errs.append(f"新浪三大报表: {e}")

    raise RuntimeError("; ".join(errs))


def get_valuation(code: str) -> dict:
    """当前 PE(TTM)、收盘价与 PE 历史分位，东财优先，腾讯降级。"""
    try:
        df = fetch_value_em(code)
        pe_col = _find_col(["PE(TTM)"], df)
        close_col = _find_col(["当日收盘价"], df)
        pe_series = _to_numeric_series(df[pe_col]).dropna() if pe_col else pd.Series(dtype=float)
        close_series = _to_numeric_series(df[close_col]).dropna() if close_col else pd.Series(dtype=float)
        cur_pe = float(pe_series.iloc[-1]) if not pe_series.empty else float("nan")
        cur_close = float(close_series.iloc[-1]) if not close_series.empty else float("nan")
        pe_pct = (pe_series < cur_pe).mean() * 100 if not pe_series.empty and pd.notna(cur_pe) else float("nan")
        return {"pe_ttm": cur_pe, "close": cur_close, "pe_percentile": pe_pct,
                "val_source": "akshare.stock_value_em", "val_note": ""}
    except Exception:
        pass
    time.sleep(0.15)
    data = fetch_tx_fallback(code)
    if not data:
        raise RuntimeError("无法获取估值数据")
    data.update({"pe_percentile": float("nan"), "val_source": "akshare.stock_zh_a_spot_tx（降级）",
                 "val_note": "腾讯快照，无历史分位"})
    return data


# ---------------------------------------------------------------------------
# 打分
# ---------------------------------------------------------------------------

def score_low_pe(pe: float, market_median: Optional[float]) -> tuple[int, float]:
    """低市盈率（满分 25）：相对全市场中位数折价越深越好。"""
    if pd.isna(pe) or pe <= 0:
        return 0, float("nan")
    ratio = safe_div(pe, market_median, default=float("nan")) if market_median else float("nan")
    if pd.notna(ratio):
        if ratio <= 0.5:
            return 25, ratio
        elif ratio <= 0.65:
            return 20, ratio
        elif ratio <= 0.8:
            return 15, ratio
        elif ratio <= 1.0:
            return 8, ratio
        return 0, ratio
    # 降级：无市场中位数时按绝对 PE
    if pe <= 10:
        return 25, ratio
    elif pe <= 15:
        return 18, ratio
    elif pe <= 20:
        return 12, ratio
    elif pe <= 25:
        return 6, ratio
    return 0, ratio


def score_total_return(profit_growth_mean: float, div_yield: float, pe: float) -> tuple[int, float]:
    """总回报率（满分 25）：(增速 + 股息率) / PE，聂夫黄金标准 >= 2。"""
    trr = safe_div(profit_growth_mean + div_yield, pe, default=float("nan"))
    if pd.isna(trr):
        return 0, float("nan")
    if trr >= 2:
        return 25, trr
    elif trr >= 1.5:
        return 20, trr
    elif trr >= 1.0:
        return 14, trr
    elif trr >= 0.6:
        return 8, trr
    return 0, trr


def score_dividend(div_yield: float, div_count: int) -> int:
    """股息率（满分 15）：高且持续分红加分。"""
    if pd.isna(div_yield) or div_count == 0:
        return 0
    if div_yield >= 4:
        return 15
    elif div_yield >= 3:
        return 12
    elif div_yield >= 2:
        return 9
    elif div_yield >= 1:
        return 5
    elif div_yield > 0:
        return 2
    return 0


def score_growth_floor(profit_growth: pd.Series) -> int:
    """盈利增长底线（满分 10）：均值 >0 且正增长年数充足。"""
    s = profit_growth.dropna()
    if s.empty:
        return 0
    score = 0
    if s.mean() > 0:
        score += 5
    if (s > 0).sum() >= 3:
        score += 5
    return score


def score_roe(roe: pd.Series) -> int:
    """资本回报（满分 10）。"""
    s = roe.dropna()
    if s.empty:
        return 0
    mean_v = s.mean()
    if mean_v >= 15:
        return 10
    elif mean_v >= 12:
        return 8
    elif mean_v >= 10:
        return 6
    elif mean_v >= 8:
        return 4
    elif mean_v >= 5:
        return 2
    return 0


def score_debt(debt: pd.Series) -> int:
    """低负债（满分 10）。"""
    s = debt.dropna()
    if s.empty:
        return 0
    latest = s.iloc[-1]
    if latest < 45:
        return 10
    elif latest < 60:
        return 6
    elif latest < 70:
        return 3
    return 0


def score_cash(ocf: pd.Series) -> int:
    """盈利含金量（满分 5）。"""
    s = ocf.dropna()
    if s.empty:
        return 0
    mean_v = s.mean()
    if mean_v >= 1.0:
        return 5
    elif mean_v >= 0.8:
        return 3
    elif mean_v >= 0.5:
        return 1
    return 0


def score_one(code: str, meta: pd.DataFrame, market_median: Optional[float]) -> dict:
    val = get_valuation(code)
    fin = get_financials(code)
    time.sleep(0.15)
    div_df = fetch_dividend_cninfo(code)
    div_per_share, div_count, div_span_years = _annual_dividend_per_share(div_df)
    close = val.get("close", float("nan"))
    div_yield = safe_div(div_per_share, close, default=float("nan")) * 100 if div_count else float("nan")

    meta_row = meta[meta["code"] == code]
    name = str(meta_row["name"].iloc[0]) if not meta_row.empty and "name" in meta.columns else ""
    industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty and "industry" in meta.columns else ""

    pe = val.get("pe_ttm", float("nan"))
    low_pe_score, pe_ratio = score_low_pe(pe, market_median)
    growth_mean = fin["profit_growth"].mean() if not fin["profit_growth"].dropna().empty else float("nan")
    trr_score, trr = score_total_return(growth_mean if pd.notna(growth_mean) else 0.0,
                                        div_yield if pd.notna(div_yield) else 0.0, pe)
    div_score = score_dividend(div_yield, div_count)
    growth_score = score_growth_floor(fin["profit_growth"])
    roe_score = score_roe(fin["roe"])
    debt_score = score_debt(fin["debt"])
    cash_score = score_cash(fin["ocf"])
    total = low_pe_score + trr_score + div_score + growth_score + roe_score + debt_score + cash_score

    data_years = max(len(fin["roe"]), len(fin["profit_growth"]), len(fin["debt"]), len(fin["ocf"]))
    note = "; ".join(x for x in [fin.get("note", ""), val.get("val_note", "")] if x)

    return {
        "code": code,
        "name": name,
        "industry": industry,
        "total": total,
        "low_pe_score": low_pe_score,
        "trr_score": trr_score,
        "dividend_score": div_score,
        "growth_score": growth_score,
        "roe_score": roe_score,
        "debt_score": debt_score,
        "cash_score": cash_score,
        "pe_ttm": round(pe, 2) if pd.notna(pe) else None,
        "pe_market_ratio": round(pe_ratio, 2) if pd.notna(pe_ratio) else None,
        "pe_percentile": round(val["pe_percentile"], 1) if pd.notna(val.get("pe_percentile")) else None,
        "total_return_ratio": round(trr, 2) if pd.notna(trr) else None,
        "dividend_yield": round(div_yield, 2) if pd.notna(div_yield) else None,
        "dividend_events": div_count,
        "dividend_span_years": round(div_span_years, 1) if pd.notna(div_span_years) else None,
        "profit_growth_mean": round(float(growth_mean), 1) if pd.notna(growth_mean) else None,
        "roe_mean": round(float(fin["roe"].mean()), 1) if len(fin["roe"]) else None,
        "debt_latest": round(float(fin["debt"].iloc[-1]), 1) if len(fin["debt"]) else None,
        "ocf_mean": round(float(fin["ocf"].mean()), 2) if len(fin["ocf"]) else None,
        "data_years": data_years,
        "val_source": val.get("val_source", ""),
        "fin_source": fin["source"],
        "note": note,
        "data_date": normalize_date(datetime.now().strftime("%Y%m%d")),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="约翰·聂夫低市盈率+总回报率 A 股打分器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="neff_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    codes = [c.zfill(6) for c in codes]

    print(f"股票池共 {len(codes)} 只，加载名称/行业映射与全市场 PE 中位数...")
    meta = fetch_industry_map()
    market_median, market_source = fetch_market_median_pe()
    if market_median:
        print(f"全市场 PE(TTM) 中位数: {market_median:.1f}（来源 {market_source}），相对折价以此为准")
    else:
        print("警告: 全市场中位数获取失败，低市盈率维度降级为绝对 PE 评分", file=sys.stderr)

    print("开始逐一打分（估值+财务+分红三个接口，请耐心）...")
    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, meta, market_median)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} {r['name']} 得分 {r['total']} | PE {r['pe_ttm']} | 股息率 {r['dividend_yield']} | TRR {r['total_return_ratio']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("total", ascending=False)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "code", "name", "total", "low_pe_score", "trr_score", "dividend_score",
        "pe_ttm", "pe_market_ratio", "dividend_yield", "total_return_ratio",
        "profit_growth_mean", "roe_mean", "data_years",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    print(df.head(args.top)[display_cols].to_string(index=False))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=75 聂夫式'遭人嫌弃的好公司'候选; 55-74 观察; <55 不符合框架。")
    print("提醒: 股息率按最近 5 次派息的实际时间跨度年化，特别分红/分红政策变化需人工复核。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
