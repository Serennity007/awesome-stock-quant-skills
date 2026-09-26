#!/usr/bin/env python3
"""screen.py — 张磊高瓴长期结构性价值投资 A 股初筛。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out result.csv

筛选维度（张磊长期结构性价值风格）:
    1. 连续 5 年营收/利润双增长 —— 增长质量。
    2. 长期投入 —— 研发费用率 或 资本开支/营收 高且趋势向上。
    3. 行业空间 —— 营收增速高于所处行业平均（近似）。
    4. ROE 趋势向上 —— 资本回报改善。

数据源: akshare（优先东方财富财务指标表；东财失败自动降级新浪三大报表）。
"""
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Optional

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import numpy as np
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

# ---------------- 基础设施 ----------------


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理阻断东财/同花顺直连。"""
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


def _ak_call(func, *args, **kwargs):
    """所有 akshare 调用的统一包装：指数退避 3 次 + 调用间 sleep 0.15。"""
    result = _retry_call(lambda: func(*args, **kwargs))
    time.sleep(0.15)
    return result


def normalize_date(date_str: str) -> str:
    """兼容 20231231 与 2023-12-31，统一返回 2023-12-31。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return date_str


def safe_div(a, b, default=float("nan")) -> float:
    """除零防护：b 为 0 或 nan 时返回 default（标量版本）。"""
    try:
        if pd.isna(a) or pd.isna(b):
            return default
        b = float(b)
        if b == 0:
            return default
        return float(a) / b
    except Exception:
        return default


def safe_div_series(a, b, default=0.0) -> pd.Series:
    """除零防护（Series 版本）：b 为 0 或 nan 时返回 default。"""
    a = pd.to_numeric(a, errors="coerce")
    b = pd.to_numeric(b, errors="coerce")
    res = np.where((b == 0) | (b.isna()) | (a.isna()), default, a / b)
    return pd.Series(res, index=a.index)


def _find_col(candidates: list, df: pd.DataFrame) -> Optional[str]:
    """按候选子串在 df 列名中查找第一个匹配列。"""
    for c in df.columns:
        cs = str(c)
        for cand in candidates:
            if cand in cs:
                return c
    return None


def _to_float_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


# ---------------- 数据获取 ----------------


def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """东财主要财务指标（年报），失败抛异常。"""
    start_year = datetime.now().year - YEARS - 2
    df = _ak_call(ak.stock_financial_analysis_indicator, symbol=code, start_year=str(start_year))
    if df is None or df.empty:
        raise RuntimeError("财务指标为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df) or df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col].astype(str).apply(normalize_date), errors="coerce")
    today = pd.Timestamp.now()
    df = df[(df[date_col].dt.month == 12) & (df[date_col] <= today)].sort_values(date_col).tail(YEARS)
    if df.empty:
        raise RuntimeError("无年度财务指标数据")
    return df.reset_index(drop=True)


def fetch_sina_report(code: str, report_type: str) -> pd.DataFrame:
    """新浪三大报表（年报），失败返回空 DataFrame。"""
    try:
        df = _ak_call(ak.stock_financial_report_sina, stock=code, symbol=report_type)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["报告日"] = df["报告日"].astype(str).str.replace("-", "")
    today = pd.Timestamp.now().strftime("%Y%m%d")
    df = df[(df["报告日"].str.endswith("1231")) & (df["报告日"] <= today)]
    df = df.sort_values("报告日").tail(YEARS)
    return df.reset_index(drop=True)


# ---------------- 业绩快报/行业映射（一次性加载） ----------------

_YJBB_CACHE = None


def fetch_yjbb_snapshot():
    """获取最新一期业绩快报，返回 (meta_df, industry_avg_rev_growth, market_avg_rev_growth)。

    meta_df 列：code, name, industry
    industry_avg_rev_growth: Series(industry -> mean 营业总收入-同比增长)
    market_avg_rev_growth: 全市场平均营收增速
    """
    global _YJBB_CACHE
    if _YJBB_CACHE is not None:
        return _YJBB_CACHE

    now = datetime.now()
    candidates = []
    for y in range(now.year, now.year - 2, -1):
        for m, d in ((12, 31), (9, 30), (6, 30), (3, 31)):
            candidates.append(f"{y}{m:02d}{d:02d}")

    errs = []
    for date in candidates:
        try:
            df = _ak_call(ak.stock_yjbb_em, date=date)
        except Exception as e:
            errs.append(f"{date}: {e}")
            continue
        if df is None or df.empty:
            continue
        df.columns = [str(c).strip() for c in df.columns]
        code_col = _find_col(["股票代码"], df)
        name_col = _find_col(["股票简称"], df)
        ind_col = _find_col(["所处行业"], df)
        rev_growth_col = _find_col(["营业总收入-同比增长"], df)
        if code_col is None:
            continue

        s = df.copy()
        s["code"] = s[code_col].astype(str).str.strip().str.zfill(6)
        s = s.drop_duplicates("code")
        meta = pd.DataFrame({"code": s["code"].values})
        if name_col is not None:
            meta["name"] = s[name_col].astype(str).values
        if ind_col is not None:
            meta["industry"] = s[ind_col].astype(str).values

        industry_avg = pd.Series(dtype=float)
        market_median = float("nan")
        if rev_growth_col is not None:
            s["rev_growth"] = _to_float_series(s[rev_growth_col])
            valid = s[s["rev_growth"].notna()]
            if not valid.empty:
                market_median = float(valid["rev_growth"].median())
            if ind_col is not None:
                industry_avg = valid.groupby(ind_col)["rev_growth"].mean()

        _YJBB_CACHE = (meta, industry_avg, market_median)
        return _YJBB_CACHE

    # 全部失败时返回空结构
    _YJBB_CACHE = (pd.DataFrame(columns=["code", "name", "industry"]), pd.Series(dtype=float), float("nan"))
    return _YJBB_CACHE


# ---------------- 指标抽取 ----------------


def _from_indicator(code: str) -> pd.DataFrame:
    """从东财财务指标表提取年度营收增速、利润增速、ROE。"""
    df = fetch_financial_indicator(code)
    rev_col = _find_col(["主营业务收入增长率"], df)
    prof_col = _find_col(["净利润增长率"], df)
    roe_col = _find_col(["净资产收益率(%)"], df)
    if rev_col is None or prof_col is None or roe_col is None:
        raise RuntimeError("财务指标表缺少必要列")
    return pd.DataFrame({
        "date": df.iloc[:, 0].astype(str),
        "rev_growth": _to_float_series(df[rev_col]),
        "profit_growth": _to_float_series(df[prof_col]),
        "roe": _to_float_series(df[roe_col]),
    })


def _build_sina_annual(code: str) -> pd.DataFrame:
    """从新浪三大报表提取年度数据并合并。"""
    bs = fetch_sina_report(code, "资产负债表")
    inc = fetch_sina_report(code, "利润表")
    cf = fetch_sina_report(code, "现金流量表")
    if inc.empty:
        raise RuntimeError("新浪利润表为空")

    base = inc[["报告日"]].copy()

    # 利润表字段
    rev_col = _find_col(["营业收入"], inc)
    rd_col = _find_col(["研发费用"], inc)
    profit_col = _find_col(["净利润"], inc)
    for col_name, src_col in [("revenue", rev_col), ("rd", rd_col), ("profit", profit_col)]:
        if src_col is not None:
            base[col_name] = _to_float_series(inc[src_col])
        else:
            base[col_name] = float("nan")

    # 资产负债表字段
    if not bs.empty:
        equity_col = _find_col(["所有者权益(或股东权益)合计"], bs)
        shares_col = _find_col(["实收资本(或股本)"], bs) or _find_col(["股本"], bs)
        for col_name, src_col in [("equity", equity_col), ("shares", shares_col)]:
            if src_col is not None:
                base = base.merge(bs[["报告日", src_col]].rename(columns={src_col: col_name}), on="报告日", how="left")
                base[col_name] = _to_float_series(base[col_name])
            else:
                base[col_name] = float("nan")
    else:
        base["equity"] = float("nan")
        base["shares"] = float("nan")

    # 现金流量表字段：资本开支
    if not cf.empty:
        capex_col = _find_col(["购建固定资产、无形资产和其他长期资产所支付的现金"], cf)
        if capex_col is None:
            capex_col = _find_col(["购建固定资产"], cf)
        if capex_col is not None:
            base = base.merge(cf[["报告日", capex_col]].rename(columns={capex_col: "capex"}), on="报告日", how="left")
            base["capex"] = _to_float_series(base["capex"])
        else:
            base["capex"] = float("nan")
    else:
        base["capex"] = float("nan")

    base = base.sort_values("报告日").tail(YEARS).reset_index(drop=True)
    base["rev_growth"] = base["revenue"].pct_change() * 100
    base["profit_growth"] = base["profit"].pct_change() * 100
    base["roe"] = safe_div_series(base["profit"], base["equity"]) * 100
    base["rd_ratio"] = safe_div_series(base["rd"], base["revenue"]) * 100
    base["capex_to_rev"] = safe_div_series(base["capex"], base["revenue"]) * 100
    return base


def _merge_indicator_with_sina(code: str, indicator_df: pd.DataFrame) -> pd.DataFrame:
    """用东财指标表做主数据源，用新浪报表补长期投入指标。"""
    sina = _build_sina_annual(code)
    if sina.empty:
        indicator_df["rd_ratio"] = float("nan")
        indicator_df["capex_to_rev"] = float("nan")
        return indicator_df

    # 按年份对齐：东财日期为 2023-12-31，新浪报告日为 20231231
    sina["year"] = sina["报告日"].astype(str).str[:4].astype(int)
    indicator_df["year"] = pd.to_datetime(indicator_df["date"], errors="coerce").dt.year

    merged = indicator_df.merge(
        sina[["year", "rd_ratio", "capex_to_rev", "revenue", "profit", "equity"]],
        on="year", how="left", suffixes=("", "_sina")
    )

    # 当东财指标缺失时（如金融股的主营收入、ROE），用新浪三大报表手工值补全
    merged["rev_growth_sina"] = merged["revenue"].pct_change() * 100
    merged["profit_growth_sina"] = merged["profit"].pct_change() * 100
    merged["roe_sina"] = safe_div_series(merged["profit"], merged["equity"]) * 100

    merged["rev_growth"] = merged["rev_growth"].fillna(merged["rev_growth_sina"])
    merged["profit_growth"] = merged["profit_growth"].fillna(merged["profit_growth_sina"])
    merged["roe"] = merged["roe"].fillna(merged["roe_sina"])

    merged = merged.drop(columns=["year", "rev_growth_sina", "profit_growth_sina", "roe_sina"])
    return merged


def get_metrics(code: str) -> tuple[pd.DataFrame, str, str]:
    """获取一只股票的综合指标 DataFrame，返回 (df, source, note)。"""
    errs = []

    try:
        ind = _from_indicator(code)
        df = _merge_indicator_with_sina(code, ind)
        return df, "akshare.stock_financial_analysis_indicator + 新浪三大报表", ""
    except Exception as e:
        errs.append(f"东财指标表: {e}")

    try:
        df = _build_sina_annual(code)
        return df, "akshare.stock_financial_report_sina（东财降级）", "营收/利润/ROE 由新浪三大报表手工计算"
    except Exception as e:
        errs.append(f"新浪三大报表: {e}")

    raise RuntimeError("; ".join(errs))


# ---------------- 打分 ----------------


def score_double_growth(df: pd.DataFrame) -> tuple[int, int, int]:
    """连续 5 年营收/利润双增长打分（40 分）。

    返回 (score, double_years, consecutive_double_years)
    """
    if df.empty:
        return 0, 0, 0
    valid = df[(df["rev_growth"].notna()) & (df["profit_growth"].notna())]
    double = (valid["rev_growth"] > 0) & (valid["profit_growth"] > 0)
    double_years = int(double.sum())

    consecutive = 0
    for v in reversed(double.tolist()):
        if v:
            consecutive += 1
        else:
            break

    return min(double_years * 8, 40), double_years, consecutive


def score_longterm_investment(df: pd.DataFrame) -> tuple[int, dict]:
    """长期投入打分（25 分）：研发占比或资本开支扩张。"""
    rd = df["rd_ratio"].dropna()
    capex = df["capex_to_rev"].dropna()

    base_score = 0
    if not rd.empty:
        avg_rd = float(rd.mean())
        latest_rd = float(rd.iloc[-1])
        if avg_rd >= 5 or latest_rd >= 5:
            base_score = max(base_score, 20)
        elif avg_rd >= 3 or latest_rd >= 3:
            base_score = max(base_score, 14)
        elif avg_rd >= 1 or latest_rd >= 1:
            base_score = max(base_score, 8)

    if not capex.empty:
        avg_capex = float(capex.mean())
        latest_capex = float(capex.iloc[-1])
        if avg_capex >= 10 or latest_capex >= 10:
            base_score = max(base_score, 20)
        elif avg_capex >= 5 or latest_capex >= 5:
            base_score = max(base_score, 14)
        elif avg_capex >= 2 or latest_capex >= 2:
            base_score = max(base_score, 8)

    # 趋势加分
    trend_bonus = 0
    rd_trend = False
    capex_trend = False
    if not rd.empty and len(rd) >= 2:
        rd_trend = float(rd.iloc[-1]) > float(rd.mean())
    if not capex.empty and len(capex) >= 2:
        capex_trend = float(capex.iloc[-1]) > float(capex.mean())
    if rd_trend or capex_trend:
        trend_bonus = 5

    # 如果完全没数据，给中性分 5 分，避免金融/周期股被过度惩罚
    if rd.empty and capex.empty:
        return 5, {
            "rd_ratio_avg": None,
            "rd_ratio_latest": None,
            "capex_to_rev_avg": None,
            "capex_to_rev_latest": None,
            "investment_trend": None,
            "investment_note": "长期投入数据缺失（金融/周期股常见）",
        }

    return min(base_score + trend_bonus, 25), {
        "rd_ratio_avg": round(float(rd.mean()), 2) if not rd.empty else None,
        "rd_ratio_latest": round(float(rd.iloc[-1]), 2) if not rd.empty else None,
        "capex_to_rev_avg": round(float(capex.mean()), 2) if not capex.empty else None,
        "capex_to_rev_latest": round(float(capex.iloc[-1]), 2) if not capex.empty else None,
        "investment_trend": "up" if (rd_trend or capex_trend) else "flat/down",
        "investment_note": "",
    }


def score_industry_space(stock_avg_rev: Optional[float], industry_avg: Optional[float], market_avg: Optional[float]) -> tuple[int, dict]:
    """行业空间打分（20 分）：营收增速高于行业平均。"""
    bench = industry_avg if pd.notna(industry_avg) else market_avg
    if pd.notna(bench) and pd.notna(stock_avg_rev):
        if stock_avg_rev > bench * 1.3:
            score = 20
        elif stock_avg_rev > bench * 1.1:
            score = 15
        elif stock_avg_rev > bench:
            score = 10
        elif stock_avg_rev > bench * 0.8:
            score = 5
        else:
            score = 0
        note = "industry" if pd.notna(industry_avg) else "market"
    else:
        score = 10  # 基准缺失时给中性分
        note = "benchmark_missing"

    return score, {
        "stock_avg_rev_growth": round(stock_avg_rev, 2) if pd.notna(stock_avg_rev) else None,
        "industry_avg_rev_growth": round(float(industry_avg), 2) if pd.notna(industry_avg) else None,
        "market_median_rev_growth": round(float(market_avg), 2) if pd.notna(market_avg) else None,
        "industry_space_note": note,
    }


def score_roe_trend(roe: pd.Series) -> tuple[int, dict]:
    """ROE 趋势向上打分（15 分）。"""
    roe = roe.dropna()
    if roe.empty:
        return 0, {"roe_avg": None, "roe_latest": None, "roe_trend_up": False, "roe_5y": ""}
    latest = float(roe.iloc[-1])
    first = float(roe.iloc[0])
    mean_v = float(roe.mean())
    trend_up = latest > first and latest > mean_v

    if trend_up:
        score = 15
    elif latest > mean_v or (latest > first and latest > 10):
        score = 10
    elif latest > 10:
        score = 5
    else:
        score = 0

    info = {
        "roe_avg": round(mean_v, 2),
        "roe_latest": round(latest, 2),
        "roe_trend_up": trend_up,
        "roe_5y": ",".join(f"{v:.1f}" for v in roe.tolist()),
    }
    return score, info


# ---------------- 单只股票分析 ----------------


def analyze_one(code: str, meta: pd.DataFrame, industry_avg: pd.Series, market_median: float) -> dict:
    df, source, note = get_metrics(code)

    meta_row = meta[meta["code"] == code]
    name = str(meta_row["name"].iloc[0]) if not meta_row.empty else ""
    industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty else ""

    growth_score, double_years, consecutive_double = score_double_growth(df)
    invest_score, invest_info = score_longterm_investment(df)

    # 用于行业空间对比的营收增速：优先用最新年度增速，缺失时用 5 年均值
    rev_series = df["rev_growth"].dropna()
    latest_rev = float(rev_series.iloc[-1]) if not rev_series.empty else float("nan")
    avg_rev = float(rev_series.mean()) if not rev_series.empty else float("nan")
    rev_for_space = latest_rev if pd.notna(latest_rev) else avg_rev

    prof_series = df["profit_growth"].dropna()
    latest_prof = float(prof_series.iloc[-1]) if not prof_series.empty else float("nan")
    avg_prof = float(prof_series.mean()) if not prof_series.empty else float("nan")

    industry_score, industry_info = score_industry_space(rev_for_space, industry_avg.get(industry), market_median)
    roe_score, roe_info = score_roe_trend(df["roe"])

    total = growth_score + invest_score + industry_score + roe_score

    row = {
        "code": code,
        "name": name,
        "industry": industry,
        "score_total": total,
        "score_growth": growth_score,
        "score_investment": invest_score,
        "score_industry": industry_score,
        "score_roe_trend": roe_score,
        "double_growth_years": double_years,
        "consecutive_double_years": consecutive_double,
        "latest_rev_growth": round(latest_rev, 2) if pd.notna(latest_rev) else None,
        "avg_rev_growth": round(avg_rev, 2) if pd.notna(avg_rev) else None,
        "latest_profit_growth": round(latest_prof, 2) if pd.notna(latest_prof) else None,
        "avg_profit_growth": round(avg_prof, 2) if pd.notna(avg_prof) else None,
        "data_years": len(df),
        "source": source,
        "note": note,
        "data_date": normalize_date(datetime.now().strftime("%Y%m%d")),
    }
    row.update(invest_info)
    row.update(industry_info)
    row.update(roe_info)
    return row


# ---------------- 股票池 ----------------


def get_pool(pool: str) -> list:
    if pool == "hs300":
        errs = []
        try:
            df = _ak_call(ak.index_stock_cons_csindex, symbol="000300")
            col = _find_col(["成分券代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"csindex: {e}")

        try:
            df = _ak_call(ak.index_stock_cons_weight_csindex, symbol="000300")
            col = _find_col(["成分券代码"], df) or _find_col(["股票代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"weight csindex: {e}")

        sys.exit(f"ERROR: 获取沪深300成分股失败: {'; '.join(errs)}")

    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


# ---------------- CLI ----------------


def main():
    ap = argparse.ArgumentParser(description="张磊高瓴长期结构性价值投资 A 股初筛")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="zhang_lei_screen_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防接口限流)")
    args = ap.parse_args()

    _disable_proxies()

    codes = [c.strip().zfill(6) for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)

    print(f"股票池共 {len(codes)} 只，开始加载行业映射与业绩快报...")
    meta, industry_avg, market_median = fetch_yjbb_snapshot()
    print(f"行业映射覆盖 {len(meta)} 只股票，市场中位营收增速 {market_median:.2f}%（若数据有效）。")
    print("开始逐一打分（财务接口较慢，请耐心）...")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = analyze_one(code, meta, industry_avg, market_median)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} 成长质量得分 {r['score_total']} | 行业: {r['industry'] or '—'}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("score_total", ascending=False).reset_index(drop=True)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "code", "name", "score_total", "score_growth", "score_investment",
        "score_industry", "score_roe_trend", "double_growth_years",
        "avg_rev_growth", "avg_profit_growth", "rd_ratio_avg", "capex_to_rev_avg",
        "industry_avg_rev_growth", "roe_latest", "industry",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df.head(args.top)[display_cols].copy()
    print(display_df.to_string(index=False))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    if failed:
        print("失败股票（前 10）:", ", ".join(f"{c}({e})" for c, e in failed[:10]))

    print("\n判定线: >=75 长期结构性价值优；55–74 有亮点但需复核；<55 与框架差距较大。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
