#!/usr/bin/env python3
"""screen.py — 巴菲特标准 A 股初筛。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,000858 --out result.csv

数据源: akshare。所有网络调用失败都会给出清晰报错。
打分规则见 references/scoring_rules.md。
"""
import argparse
import sys
import time

import pandas as pd

try:
    import akshare as ak
except ImportError:
    sys.exit("ERROR: 未安装 akshare，请先执行: pip install akshare pandas")

YEARS = 5


def annual_fin_indicator(code: str) -> pd.DataFrame:
    """近 YEARS 年年报主要财务指标。失败抛异常。"""
    try:
        df = ak.stock_financial_analysis_indicator(
            symbol=code, start_year=str(pd.Timestamp.now().year - YEARS - 1))
    except Exception as e:
        raise RuntimeError(f"获取 {code} 财务指标失败: {e}")
    if df is None or df.empty:
        raise RuntimeError(f"获取 {code} 财务指标为空（可能接口限流或代码有误）")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = next((c for c in df.columns if "日期" in c), df.columns[0])
    df[date_col] = df[date_col].astype(str)
    df = df[df[date_col].str.endswith("12-31")].sort_values(date_col).tail(YEARS)
    if df.empty:
        raise RuntimeError(f"{code} 无年度财务数据")
    return df


def annual_report(code: str, symbol: str) -> pd.DataFrame:
    """新浪三大报表（年度行，近 YEARS 年）。失败返回空表。"""
    try:
        df = ak.stock_financial_report_sina(stock=code, symbol=symbol)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    df["报告日"] = df["报告日"].astype(str)
    df = df[df["报告日"].str.endswith("1231")].sort_values("报告日").tail(YEARS)
    return df


def gross_margins(code: str) -> pd.Series:
    """由利润表计算近 YEARS 年毛利率(%)。"""
    inc = annual_report(code, "利润表")
    if inc.empty or "营业收入" not in inc.columns or "营业成本" not in inc.columns:
        return pd.Series(dtype=float)
    rev = pd.to_numeric(inc["营业收入"], errors="coerce")
    cost = pd.to_numeric(inc["营业成本"], errors="coerce")
    gm = (rev - cost) / rev * 100
    return gm.dropna()


def cashflow_positive_years(code: str) -> int:
    """近 YEARS 年年报经营现金流净额为正的年数。"""
    cf = annual_report(code, "现金流量表")
    col = next((c for c in cf.columns if "经营活动产生的现金流量净额" in str(c)), None)
    if col is None:
        return 0
    vals = pd.to_numeric(cf[col], errors="coerce").dropna()
    return int((vals > 0).sum())


def valuation_percentile(code: str):
    """(PE 分位, PB 分位)，基于近 5 年每日估值，0-1；失败返回 (None, None)。"""
    try:
        df = ak.stock_value_em(symbol=code)
    except Exception:
        return None, None
    if df is None or df.empty:
        return None, None
    df.columns = [str(c).strip().upper() for c in df.columns]
    out = []
    for key, names in (("PE", ("PE",)), ("PB", ("PB", "市净率"))):
        col = next((c for n in names for c in df.columns if c.startswith(n)), None)
        if col is None:
            out.append(None)
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        s = s[s > 0]
        if len(s) < 60:
            out.append(None)
            continue
        out.append(float((s < s.iloc[-1]).mean()))
    return out[0], out[1]


def score_one(code: str) -> dict:
    ind = annual_fin_indicator(code)

    def series(*keys):
        for k in keys:
            col = next((c for c in ind.columns if k in c), None)
            if col is not None:
                return pd.to_numeric(ind[col], errors="coerce")
        return pd.Series(dtype=float)

    roe = series("净资产收益率").dropna()
    debt = series("资产负债率").dropna()
    gross = gross_margins(code).dropna()

    roe_score = sum(6 if v > 15 else (3 if v > 12 else 0) for v in roe)

    gross_score = 0
    if len(gross):
        mean_g = gross.mean()
        gross_score += 10 if mean_g > 40 else (6 if mean_g > 30 else 0)
        spread = gross.max() - gross.min()
        gross_score += 10 if spread < 5 else (5 if spread < 10 else 0)

    debt_score = 0
    if len(debt):
        latest_d = debt.iloc[-1]
        debt_score = 15 if latest_d < 40 else (8 if latest_d < 50 else (3 if latest_d < 65 else 0))

    cf_years = cashflow_positive_years(code)
    cf_score = cf_years * 4

    pe_pct, pb_pct = valuation_percentile(code)
    val_score = 0
    if pe_pct is not None:
        val_score += 8 if pe_pct < 0.3 else (4 if pe_pct < 0.5 else 0)
    if pb_pct is not None:
        val_score += 7 if pb_pct < 0.3 else (3 if pb_pct < 0.5 else 0)

    total = roe_score + gross_score + debt_score + cf_score + val_score
    return {
        "code": code,
        "total": total,
        "roe_score": roe_score,
        "roe_annual": ",".join(f"{v:.1f}" for v in roe.tolist()),
        "gross_score": gross_score,
        "gross_mean": round(float(gross.mean()), 1) if len(gross) else None,
        "debt_score": debt_score,
        "debt_latest": round(float(debt.iloc[-1]), 1) if len(debt) else None,
        "cashflow_score": cf_score,
        "cashflow_pos_years": cf_years,
        "valuation_score": val_score,
        "pe_pct": round(pe_pct, 2) if pe_pct is not None else None,
        "pb_pct": round(pb_pct, 2) if pb_pct is not None else None,
    }


def get_pool(pool: str) -> list:
    if pool == "hs300":
        try:
            df = ak.index_stock_cons_csindex(symbol="000300")
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

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
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
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    print(df.head(args.top).to_string(index=False))
    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=70 进入人工护城河核查; 50-69 有短板; <50 不符合框架。")


if __name__ == "__main__":
    main()
