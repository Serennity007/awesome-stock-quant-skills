#!/usr/bin/env python3
"""screen.py — 巴菲特标准 A 股初筛。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,000858 --out result.csv

数据源: akshare。所有网络调用失败都会给出清晰报错。
打分规则见 references/scoring_rules.md。
"""
import os

os.environ.setdefault("TQDM_DISABLE", "1")

import argparse
import sys
import time

import pandas as pd
from research_data import annual_rows, numeric, valuation_snapshot

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import akshare as ak
except ImportError:
    ak = None

YEARS = 5


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


def annual_fin_indicator(code: str) -> pd.DataFrame:
    """近 YEARS 年年报主要财务指标。失败抛异常。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_analysis_indicator(
            symbol=code, start_year=str(pd.Timestamp.now().year - YEARS - 1)))
    except Exception as e:
        raise RuntimeError(f"获取 {code} 财务指标失败: {e}")
    if df is None or df.empty:
        raise RuntimeError(f"获取 {code} 财务指标为空（可能接口限流或代码有误）")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = next((c for c in df.columns if "日期" in c), df.columns[0])
    df = annual_rows(df, date_col, YEARS)
    if df.empty:
        raise RuntimeError(f"{code} 无年度财务数据")
    return df


def annual_report(code: str, symbol: str) -> pd.DataFrame:
    """新浪三大报表（年度行，近 YEARS 年）。失败返回空表。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol=symbol))
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    return annual_rows(df, "报告日", YEARS)


def gross_margins(code: str) -> pd.Series:
    """由利润表计算近 YEARS 年毛利率(%)。"""
    inc = annual_report(code, "利润表")
    revenue_col = next((col for col in ("营业收入", "营业总收入") if col in inc), None)
    if inc.empty or revenue_col is None or "营业成本" not in inc.columns:
        return pd.Series(dtype=float)
    rev = numeric(inc[revenue_col])
    cost = numeric(inc["营业成本"])
    gm = ((rev - cost) / rev.where(rev > 0, float("nan")) * 100)
    gm.index = pd.DatetimeIndex(inc["报告日"])
    return gm.dropna()


def cashflow_values(code: str) -> pd.Series:
    """Known cash-flow observations; missing data remains distinct from losses."""
    cf = annual_report(code, "现金流量表")
    col = next((c for c in cf.columns if "经营活动产生的现金流量净额" in str(c)), None)
    if col is None:
        return pd.Series(dtype=float)
    vals = numeric(cf[col])
    vals.index = pd.DatetimeIndex(cf["报告日"])
    return vals.dropna()


def cashflow_positive_years(code: str) -> int:
    return int((cashflow_values(code) > 0).sum())


def valuation_data(code: str):
    try:
        return valuation_snapshot(_retry_call(lambda: ak.stock_value_em(symbol=code)))
    except Exception:
        return None


def valuation_percentile(code: str):
    """(PE 分位, PB 分位)，基于近 5 年每日估值，0-1；失败返回 (None, None)。"""
    snapshot = valuation_data(code)
    return (snapshot["pe_pct"], snapshot["pb_pct"]) if snapshot else (None, None)


def score_one(code: str) -> dict:
    ind = annual_fin_indicator(code)
    time.sleep(0.15)

    def series(*keys):
        for k in keys:
            col = next((c for c in ind.columns if k in c), None)
            if col is not None:
                return numeric(ind[col])
        return pd.Series(dtype=float)

    roe = series("净资产收益率").dropna()
    debt = series("资产负债率")
    gross = gross_margins(code).dropna()
    date_col = next((c for c in ind if "日期" in c), ind.columns[0])
    periods = pd.DatetimeIndex(ind[date_col])
    consecutive_periods = len(periods) == YEARS and periods.year.max() - periods.year.min() == YEARS - 1
    if isinstance(gross.index, pd.DatetimeIndex):
        gross = gross.reindex(periods).dropna()

    roe_score = sum(6 if v > 15 else (3 if v > 12 else 0) for v in roe)

    gross_score = 0
    if len(gross):
        mean_g = gross.mean()
        gross_score += 10 if mean_g > 40 else (6 if mean_g > 30 else 0)
        spread = gross.max() - gross.min()
        # One observation has a zero spread but proves no multi-year stability.
        if len(gross) >= YEARS and consecutive_periods:
            gross_score += 10 if spread < 5 else (5 if spread < 10 else 0)

    debt_score = 0
    if len(debt) and pd.notna(debt.iloc[-1]):
        latest_d = debt.iloc[-1]
        debt_score = 15 if latest_d < 40 else (8 if latest_d < 50 else (3 if latest_d < 65 else 0))

    cash = cashflow_values(code)
    if isinstance(cash.index, pd.DatetimeIndex):
        cash = cash.reindex(periods).dropna()
    cf_years = int((cash > 0).sum())
    cf_score = min(cf_years, YEARS) * 4
    time.sleep(0.15)

    valuation = valuation_data(code)
    pe_pct, pb_pct = (valuation["pe_pct"], valuation["pb_pct"]) if valuation else (None, None)
    val_score = 0
    if pe_pct is not None:
        val_score += 8 if pe_pct < 0.3 else (4 if pe_pct < 0.5 else 0)
    if pb_pct is not None:
        val_score += 7 if pb_pct < 0.3 else (3 if pb_pct < 0.5 else 0)

    total = roe_score + gross_score + debt_score + cf_score + val_score
    data_years = int(len(roe))
    issues = []
    if data_years < YEARS or not consecutive_periods:
        issues.append("roe_history_incomplete_or_nonconsecutive")
    if len(gross) < YEARS:
        issues.append("gross_history_incomplete_or_not_applicable")
    if len(cash) < YEARS:
        issues.append("cashflow_history_incomplete")
    if debt.empty or pd.isna(debt.iloc[-1]):
        issues.append("latest_debt_missing")
    if pe_pct is None or pb_pct is None:
        issues.append("valuation_incomplete")
    return {
        "code": code,
        "total": total,
        "roe_score": roe_score,
        "roe_annual": ",".join(f"{v:.1f}" for v in roe.tolist()) if len(roe) else "—",
        "gross_score": gross_score,
        "gross_mean": round(float(gross.mean()), 1) if len(gross) else None,
        "debt_score": debt_score,
        "debt_latest": round(float(debt.iloc[-1]), 1) if len(debt) else None,
        "cashflow_score": cf_score,
        "cashflow_pos_years": cf_years,
        "valuation_score": val_score,
        "pe_pct": round(pe_pct, 2) if pe_pct is not None else None,
        "pb_pct": round(pb_pct, 2) if pb_pct is not None else None,
        "data_years": data_years,
        "gross_years": len(gross), "cashflow_data_years": len(cash),
        "score_status": "partial" if issues else "complete",
        "decision": "needs_data" if issues else ("review_moat" if total >= 70 else "review_weakness" if total >= 50 else "below_threshold"),
        "data_issues": ";".join(issues),
        "financial_periods": ",".join(d.date().isoformat() for d in periods),
        "valuation_date": valuation["date"] if valuation else None,
        "valuation_history_start": valuation.get("history_start") if valuation else None,
        "valuation_observations": valuation.get("observations") if valuation else None,
    }


def get_pool(pool: str) -> list:
    if pool == "hs300":
        try:
            df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
        except Exception as e:
            sys.exit(f"ERROR: 获取沪深300成分股失败: {e}")
        col = next((c for c in df.columns if "成分券代码" in str(c)), None)
        if col is None:
            sys.exit("ERROR: 沪深300成分股返回格式变化，找不到代码列")
        return [str(x).zfill(6) for x in df[col].tolist()]
    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


def main():
    ap = argparse.ArgumentParser(description="巴菲特标准 A 股初筛")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="screen_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()
    if ak is None:
        ap.exit(2, "ERROR: 未安装 akshare，请执行 python -m pip install akshare pandas\n")
    if args.top <= 0 or args.sleep < 0:
        ap.error("--top 必须为正整数，--sleep 不能为负")

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    if not codes or any(len(c) != 6 or not c.isascii() or not c.isdigit() for c in codes):
        ap.error("股票池须为非空的六位 ASCII 数字代码列表")
    codes = list(dict.fromkeys(codes))
    print(f"股票池共 {len(codes)} 只，开始逐一打分（财务接口较慢，请耐心）...")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} 得分 {r['total']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("total", ascending=False)
    from pathlib import Path
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    import json
    from datetime import datetime, timezone
    manifest = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "akshare_version": getattr(ak, "__version__", "unknown"), "codes": codes,
                "success": len(rows), "failed": [{"code": code, "error": error} for code, error in failed],
                "partial": int((df["score_status"] == "partial").sum()),
                "historical_point_in_time": False}
    Path(args.out + ".meta.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = ["code", "total", "roe_score", "gross_score", "debt_score",
                    "cashflow_score", "valuation_score", "pe_pct", "pb_pct", "data_years"]
    display_df = df.head(args.top)[display_cols].copy()
    display_df["pe_pct"] = display_df["pe_pct"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    display_df["pb_pct"] = display_df["pb_pct"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    print(display_df.to_string(index=False))
    incomplete = df[df["data_years"] < YEARS]
    if not incomplete.empty:
        print(f"\n注意: 以下 {len(incomplete)} 只股票财务数据未满 {YEARS} 年，分数基于部分年份，参考性下降：")
        print(", ".join(incomplete["code"].tolist()))
    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print(f"数据不完整 {manifest['partial']} 只：decision=needs_data，不按总分自动列为候选。")
    print("判定线: >=70 进入人工护城河核查; 50-69 有短板; <50 不符合框架。")


if __name__ == "__main__":
    main()
