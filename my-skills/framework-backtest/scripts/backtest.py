#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backtest.py — 大师框架月度调仓回测引擎。

用法:
    python scripts/backtest.py --frameworks danbin,lilu,mom12_1 --start 2021-09-30
    python scripts/backtest.py --frameworks danbin --top 10 --out-prefix myrun

逻辑（每月末调仓，等权持有前 N 名到下月末）:
    danbin   但斌框架（长坡/厚雪/复利引擎/含金量/财务健康/成长质量六维；
             历史分红数据成本高，"时间的玫瑰"维度 v1 剔除，其余 85 分重标定到 100）
    lilu     李录框架（ROE质量/复利趋势/再投资成长/含金量/PB历史分位安全边际/财务纪律）
    mom12_1  价格动量基准（12-1 月动量，即 12 个月前到 1 个月前的涨幅；作为价值框架的对照组）

数据: fetch_history.py 的本地缓存（cache/），财务切片仅按报告期末 +120 天近似可得日，
配合 T 时点的 PE/PB；未核对实际披露日与历史修订，不保证严格 point-in-time。

已知局限（务必先读 references/backtest_methodology.md）:
    1. 幸存者偏差: 股票池固定为当前沪深300名单，历史成分未回溯，收益被系统性高估。
    2. 支持简化成交额成本，仍未建模冲击成本和可成交约束。
    3. PE/PB 历史约自 2018 年起，分位窗口短于 5 年。
    4. 年报发布滞后按 120 天近似（实际 1-4 月底发布）。
    结果仅供探索；不同框架的相对排名也可能受偏差影响。
"""
import os
import sys
import glob
import time
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import numpy as np
import pandas as pd

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

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(SKILL_DIR, "cache")
RESULTS_DIR = os.path.join(SKILL_DIR, "results")

FRAMEWORKS = ["danbin", "lilu", "mom12_1"]


def _disable_proxies():
    import requests
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(k, None)
    _orig = requests.Session.request

    def _wt(self, *a, **k):
        k.setdefault("timeout", 20)
        return _orig(self, *a, **k)

    requests.Session.request = _wt


def _retry(func, n=3):
    last = None
    for i in range(n):
        try:
            return func()
        except Exception as e:
            last = e
            if i < n - 1:
                time.sleep(1.5 * (2 ** i))
    raise last


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def load_stocks(cache_dir: str) -> dict:
    """加载缓存，返回 {code: {value, ind, profit}}。"""
    stocks = {}
    for path in glob.glob(os.path.join(cache_dir, "value_*.csv")):
        code = os.path.basename(path)[len("value_"):-4]
        try:
            v = pd.read_csv(path)
            v["数据日期"] = pd.to_datetime(v["数据日期"], errors="coerce")
            v = v.dropna(subset=["数据日期"]).sort_values("数据日期")
            v.columns = [c if c != "PE(TTM)" else "pe" for c in v.columns]
            for c in ("当日收盘价", "pe", "市净率"):
                if c in v.columns:
                    v[c] = pd.to_numeric(v[c], errors="coerce")

            d = pd.read_csv(os.path.join(cache_dir, f"ind_{code}.csv"))
            d["日期"] = pd.to_datetime(d["日期"], errors="coerce")
            d = d.dropna(subset=["日期"]).sort_values("日期")
            for c in d.columns:
                if c != "日期":
                    d[c] = pd.to_numeric(d[c].astype(str).str.replace(",", ""), errors="coerce")

            p = pd.read_csv(os.path.join(cache_dir, f"profit_{code}.csv"))
            p["REPORT_DATE"] = pd.to_datetime(p["REPORT_DATE"], errors="coerce")
            p = p.dropna(subset=["REPORT_DATE"]).sort_values("REPORT_DATE")
            for c in p.columns:
                if c != "REPORT_DATE":
                    p[c] = pd.to_numeric(p[c], errors="coerce")

            stocks[code] = {"value": v, "ind": d, "profit": p}
        except Exception as e:
            print(f"加载 {code} 失败: {e}", file=sys.stderr)
    return stocks


def fetch_benchmark(cache_dir: str) -> pd.Series:
    """沪深300实际交易日收盘；不改标成自然月末。"""
    path = os.path.join(cache_dir, "bench_sh000300.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["date"])
    else:
        if ak is None:
            raise RuntimeError("benchmark cache missing; install akshare to fetch live data")
        try:
            df = _retry(lambda: ak.stock_zh_index_daily(symbol="sh000300"))
        except Exception:
            df = _retry(lambda: ak.stock_zh_index_daily_tx(symbol="sh000300"))
        df = df[["date", "close"]].copy()
        df["date"] = pd.to_datetime(df["date"])
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df.dropna()
        df.to_csv(path, index=False)
    s = df.set_index("date")["close"].sort_index()
    if s.index.duplicated().any():
        raise ValueError("duplicate benchmark dates")
    return s.dropna()


# ---------------------------------------------------------------------------
# 打分（独立实现的档位近似，财务切片使用固定可得时间近似）
# ---------------------------------------------------------------------------

def _annual_slice(stock: dict, t: pd.Timestamp, lag_days: int = 120) -> tuple:
    """按报告期末 +lag_days 近似可得日切片；不校验真实披露或修订时间。"""
    cutoff = t - pd.Timedelta(days=lag_days)
    ind = stock["ind"]
    sl = ind[ind["日期"] <= cutoff].tail(5)
    prof = stock["profit"]
    profit_sl = prof[prof["REPORT_DATE"] <= cutoff].tail(5)
    return sl, profit_sl


def _gross_series(profit_sl: pd.DataFrame) -> pd.Series:
    if "营业成本" not in profit_sl.columns or "营业总收入" not in profit_sl.columns:
        return pd.Series(dtype=float)  # 银行等无毛利率行业
    inc = pd.to_numeric(profit_sl["营业总收入"], errors="coerce")
    cost = pd.to_numeric(profit_sl["营业成本"], errors="coerce")
    g = ((inc - cost) / inc.replace(0, np.nan) * 100).dropna()
    return g


def score_danbin(sl: pd.DataFrame, profit_sl: pd.DataFrame) -> float:
    """六维 85 分制重标定到 100（v1 剔除分红维度）。"""
    if sl.empty:
        return np.nan
    def mean(col):
        s = pd.to_numeric(sl[col], errors="coerce").dropna() if col in sl.columns else pd.Series(dtype=float)
        return float(s.tail(5).mean()) if not s.empty else np.nan

    s = 0.0
    rev = mean("主营业务收入增长率(%)")
    s += 15 if rev >= 25 else 12 if rev >= 15 else 9 if rev >= 10 else 6 if rev >= 5 else 3 if rev > 0 else 0
    gross = _gross_series(profit_sl)
    if gross.empty:
        s += 8  # 金融业等无毛利率，中性分（与 screen.py 一致）
    else:
        v = float(gross.tail(5).mean())
        s += 20 if v >= 60 else 16 if v >= 45 else 12 if v >= 30 else 8 if v >= 20 else 4 if v >= 10 else 0
    roe = mean("净资产收益率(%)")
    s += 20 if roe >= 25 else 17 if roe >= 20 else 13 if roe >= 15 else 8 if roe >= 10 else 4 if roe >= 5 else 0
    ocf = mean("经营现金净流量与净利润的比率(%)")
    s += 10 if ocf >= 1.0 else 7 if ocf >= 0.8 else 4 if ocf >= 0.5 else 2 if ocf > 0 else 0
    debt = mean("资产负债率(%)")
    s += 10 if debt < 35 else 7 if debt < 50 else 4 if debt < 65 else 2 if debt < 75 else 0
    pg = pd.to_numeric(sl["净利润增长率(%)"], errors="coerce").dropna()
    n = int((pg > 0).sum())
    s += 10 if n >= 4 else 7 if n >= 3 else 4 if n >= 2 else 2 if n >= 1 else 0
    return s / 85 * 100


def score_lilu(sl: pd.DataFrame, profit_sl: pd.DataFrame, pb_pct: float) -> float:
    if sl.empty:
        return np.nan
    def mean(col):
        s = pd.to_numeric(sl[col], errors="coerce").dropna() if col in sl.columns else pd.Series(dtype=float)
        return float(s.tail(5).mean()) if not s.empty else np.nan

    s = 0.0
    roe = mean("净资产收益率(%)")
    s += 25 if roe >= 20 else 20 if roe >= 15 else 15 if roe >= 12 else 10 if roe >= 8 else 5 if roe >= 5 else 0
    roe_series = pd.to_numeric(sl["净资产收益率(%)"], errors="coerce").dropna()
    if len(roe_series) < 4:
        s += 7  # 次新数据不足，中性
    else:
        diff = float(roe_series.iloc[-2:].mean() - roe_series.iloc[:-2].mean())
        s += 15 if diff >= 2 else 10 if diff >= 0 else 6 if diff >= -3 else 0
    pg = mean("净利润增长率(%)")
    s += 20 if pg >= 25 else 16 if pg >= 15 else 12 if pg >= 10 else 8 if pg >= 5 else 4 if pg > 0 else 0
    ocf = mean("经营现金净流量与净利润的比率(%)")
    s += 15 if ocf >= 1.0 else 11 if ocf >= 0.8 else 7 if ocf >= 0.5 else 3 if ocf > 0 else 0
    s += 15 if pb_pct <= 30 else 11 if pb_pct <= 40 else 7 if pb_pct <= 60 else 4 if pb_pct <= 80 else 0
    debt = mean("资产负债率(%)")
    s += 10 if debt < 35 else 7 if debt < 50 else 4 if debt < 65 else 2 if debt < 75 else 0
    return s


def pb_percentile_at(stock: dict, t: pd.Timestamp, cur_pb: float) -> float:
    """当前 PB 在 ≤T 的全部可得历史中的分位（0-100）。"""
    if pd.isna(cur_pb):
        return np.nan
    v = stock["value"]
    hist = v.loc[v["数据日期"] <= t, "市净率"].dropna()
    hist = hist[hist > 0]
    if hist.empty:
        return np.nan
    return float((hist < cur_pb).mean() * 100)


# ---------------------------------------------------------------------------
# 回测引擎
# ---------------------------------------------------------------------------

def month_end_grid(stocks: dict) -> list:
    """全部股票估值日期并集的月末（每月最后一个交易日）。"""
    all_dates = pd.concat([s["value"]["数据日期"] for s in stocks.values()])
    months = pd.PeriodIndex(sorted(set(all_dates.dt.to_period("M"))), freq="M")
    grid = []
    for m in months:
        sub = all_dates[all_dates.dt.to_period("M") == m]
        grid.append(sub.max().normalize())
    return sorted(set(grid))


def build_close_panel(stocks: dict, grid: list) -> pd.DataFrame:
    """月末收盘面板（index=月末日期, columns=code），只记录交易日实价。"""
    panel = pd.DataFrame(index=grid)
    for code, s in stocks.items():
        v = s["value"].dropna(subset=["当日收盘价"])
        if v.empty:
            continue
        by_month = v.groupby(v["数据日期"].dt.to_period("M"))["当日收盘价"].last()
        closes = {}
        for m, close in by_month.items():
            # 该月最后一个有价的交易日
            sub = v[v["数据日期"].dt.to_period("M") == m]
            closes[sub["数据日期"].max().normalize()] = close
        for d, c in closes.items():
            if d in panel.index:
                panel.loc[d, code] = c
    return panel


def run_framework(name: str, stocks: dict, panel: pd.DataFrame, bench_m: pd.Series,
                  start: str, top_n: int, cost_bps: float = 0.0) -> tuple:
    if name not in FRAMEWORKS or top_n <= 0:
        raise ValueError("unknown framework or non-positive top_n")
    if not np.isfinite(cost_bps) or not 0 <= cost_bps < 10000:
        raise ValueError("cost_bps must be finite and in [0, 10000)")
    if panel.index.has_duplicates or not panel.index.is_monotonic_increasing:
        raise ValueError("price dates must be sorted and unique")
    grid = [d for d in panel.index if d >= pd.Timestamp(start)]
    for left, right in zip(grid, grid[1:]):
        if right.to_period("M").ordinal - left.to_period("M").ordinal != 1:
            raise ValueError("monthly price grid contains a gap or duplicate month")
    rows, audit = [], []
    previous_weights = {}
    for t, t_next in zip(grid, grid[1:]):
        scores = {}
        # Eligibility and ranking depend only on information at t, never t_next.
        for code in panel.columns:
            px = panel.at[t, code]
            if pd.isna(px) or not np.isfinite(px) or px <= 0:
                continue
            if name == "mom12_1":
                idx_t = panel.index.get_loc(t)
                if idx_t < 12:
                    continue
                px_12, px_1m = panel.iloc[idx_t - 12][code], panel.iloc[idx_t - 1][code]
                if not all(pd.notna(p) and np.isfinite(p) and p > 0 for p in (px_12, px_1m)):
                    continue
                sc = (px_1m / px_12 - 1) * 100
            else:
                sl, profit_sl = _annual_slice(stocks[code], t)
                if name == "danbin":
                    sc = score_danbin(sl, profit_sl)
                else:
                    values = stocks[code]["value"]
                    available = values.loc[values["数据日期"] <= t]
                    cur_pb = available["市净率"].iloc[-1] if not available.empty else np.nan
                    pct = pb_percentile_at(stocks[code], t, cur_pb)
                    sc = score_lilu(sl, profit_sl, pct) if pd.notna(pct) else np.nan
            if pd.notna(sc) and np.isfinite(sc):
                scores[code] = float(sc)
        if len(scores) < top_n:
            if rows:
                raise ValueError(f"insufficient eligible stocks at {t.date()}; cannot silently skip a month")
            continue  # Explicit initial warm-up, before the first invested month.
        top = sorted(scores, key=lambda c: (-scores[c], c))[:top_n]
        target = {code: 1.0 / top_n for code in top}
        turnover = sum(abs(target.get(code, 0) - previous_weights.get(code, 0))
                       for code in set(target) | set(previous_weights))
        cost = turnover * cost_bps / 10000
        if cost >= 1:
            raise ValueError("transaction costs consume all capital")
        returns = {}
        for code in top:
            exit_price = panel.at[t_next, code]
            if pd.isna(exit_price) or not np.isfinite(exit_price) or exit_price <= 0:
                raise ValueError(f"missing valid exit price for selected holding {code} at {t_next.date()}; fix data or model delisting explicitly")
            returns[code] = float(exit_price / panel.at[t, code] - 1)
            audit.append({"rebalance_date": t, "exit_date": t_next, "code": code,
                          "score": scores[code], "weight": target[code],
                          "entry_price": panel.at[t, code], "exit_price": exit_price,
                          "asset_return": returns[code]})
        for date in (t, t_next):
            if date not in bench_m.index or not np.isfinite(bench_m.loc[date]) or bench_m.loc[date] <= 0:
                raise ValueError(f"missing benchmark price at actual trading date {date.date()}")
        gross = sum(target[code] * returns[code] for code in top)
        net = (1 - cost) * (1 + gross) - 1
        benchmark_return = float(bench_m.loc[t_next] / bench_m.loc[t] - 1)
        rows.append({"date": t_next, "rebalance_date": t, "ret": net, "gross_ret": gross,
                     "turnover": turnover, "cost_fraction": cost, "bench_ret": benchmark_return,
                     "holdings": ",".join(top)})
        previous_weights = {code: target[code] * (1 + returns[code]) / (1 + gross) for code in top}
    if not rows:
        return name, pd.DataFrame(), pd.DataFrame()
    out = pd.DataFrame(rows).set_index("date")
    out["nav"] = (1 + out["ret"]).cumprod()
    out["gross_nav"] = (1 + out["gross_ret"]).cumprod()
    out["bench_nav"] = (1 + out["bench_ret"]).cumprod()
    return name, out, pd.DataFrame(audit)


def metrics(nav: pd.Series, rets: pd.Series, bench_nav: pd.Series) -> dict:
    if nav.empty or len(nav) != len(rets) or len(nav) != len(bench_nav):
        raise ValueError("metrics require nonempty aligned monthly series")
    if not nav.index.equals(rets.index) or not nav.index.equals(bench_nav.index):
        raise ValueError("metrics series dates must match")
    if any(not np.isfinite(series.to_numpy(dtype=float)).all() for series in (nav, rets, bench_nav)):
        raise ValueError("metrics cannot fill missing returns or benchmark observations")
    years = len(rets) / 12.0
    cagr = nav.iloc[-1] ** (1 / years) - 1
    bcagr = bench_nav.iloc[-1] ** (1 / years) - 1
    # Initial capital is an observed peak even if the first month loses money.
    n = pd.Series([1.0] + nav.tolist())
    bn = pd.Series([1.0] + bench_nav.tolist())
    dd = (n / n.cummax() - 1).min()
    bdd = (bn / bn.cummax() - 1).min()
    sharpe = rets.mean() / rets.std() * np.sqrt(12) if rets.std() > 0 else np.nan
    return {"cagr": round(cagr * 100, 2), "bench_cagr": round(bcagr * 100, 2),
            "excess": round((cagr - bcagr) * 100, 2),
            "max_dd": round(dd * 100, 1), "bench_max_dd": round(bdd * 100, 1),
            "sharpe": round(float(sharpe), 2), "months": len(rets)}


def yearly_table(out: pd.DataFrame) -> pd.DataFrame:
    y = out.copy()
    y["year"] = y.index.year
    g = y.groupby("year").apply(lambda x: pd.Series({
        "strat_ret": (1 + x["ret"]).prod() - 1,
        "bench_ret": (1 + x["bench_ret"].fillna(0)).prod() - 1,
    }), include_groups=False)
    g["excess"] = g["strat_ret"] - g["bench_ret"]
    return (g * 100).round(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="大师框架月度调仓回测")
    ap.add_argument("--frameworks", default="danbin,lilu,mom12_1")
    ap.add_argument("--start", default="2021-09-30", help="首个调仓月（默认 2021-09）")
    ap.add_argument("--top", type=int, default=10, help="每月等权持有前 N 名")
    ap.add_argument("--min-stocks", type=int, default=50, help="缓存少于该数量时报错退出")
    ap.add_argument("--out-prefix", default="")
    ap.add_argument("--cache-dir", default=CACHE_DIR, help="历史 CSV 缓存目录")
    ap.add_argument("--results-dir", default=RESULTS_DIR, help="输出目录")
    ap.add_argument("--cost-bps", type=float, default=10.0,
                    help="按每单位买卖成交额收取的成本基点（默认10；0表示忽略；非市场费率承诺）")
    args = ap.parse_args()
    frameworks = [x.strip() for x in args.frameworks.split(",") if x.strip()]
    if not frameworks or any(fw not in FRAMEWORKS for fw in frameworks):
        ap.error("--frameworks 必须为 danbin,lilu,mom12_1 的非空子集")
    if args.top <= 0 or args.min_stocks <= 0 or not np.isfinite(args.cost_bps) or not 0 <= args.cost_bps < 10000:
        ap.error("数量须为正数，成本须有限且处于 [0,10000) 基点")
    if args.out_prefix and Path(args.out_prefix).name != args.out_prefix:
        ap.error("--out-prefix 只能是文件名前缀；输出目录请用 --results-dir")
    try:
        pd.Timestamp(args.start)
    except ValueError:
        ap.error("--start 必须为有效日期")
    os.makedirs(args.results_dir, exist_ok=True)

    stocks = load_stocks(args.cache_dir)
    print(f"缓存加载: {len(stocks)} 只股票")
    if len(stocks) < args.min_stocks:
        sys.exit(f"ERROR: 缓存不足（{len(stocks)} < {args.min_stocks}），请先运行 fetch_history.py")

    bench_d = fetch_benchmark(args.cache_dir)
    print(f"基准: 沪深300 {bench_d.index[0].date()} → {bench_d.index[-1].date()}")

    grid = month_end_grid(stocks)
    print("构建月末收盘面板...")
    panel = build_close_panel(stocks, grid)
    print(f"面板: {panel.shape[0]} 个月末 × {panel.shape[1]} 只")

    prefix = args.out_prefix + "_" if args.out_prefix else ""
    summary_rows = []
    for fw in dict.fromkeys(frameworks):
        t0 = time.time()
        try:
            name, out, holdings = run_framework(fw, stocks, panel, bench_d, args.start, args.top, args.cost_bps)
        except ValueError as exc:
            ap.exit(2, f"ERROR: {fw}: {exc}\n")
        if out.empty:
            print(f"{fw}: 无结果")
            continue
        m = metrics(out["nav"], out["ret"], out["bench_nav"])
        m["framework"] = name
        summary_rows.append(m)
        out.to_csv(os.path.join(args.results_dir, f"{prefix}bt_result_{fw}.csv"), encoding="utf-8-sig")
        holdings.to_csv(os.path.join(args.results_dir, f"{prefix}bt_holdings_{fw}.csv"), index=False, encoding="utf-8-sig")
        yt = yearly_table(out)
        yt.to_csv(os.path.join(args.results_dir, f"{prefix}bt_yearly_{fw}.csv"), encoding="utf-8-sig")
        print(f"\n=== {fw}（{m['months']} 个月，耗时 {time.time()-t0:.0f}s）===")
        print(f"策略年化 {m['cagr']}% vs 沪深300 {m['bench_cagr']}% | 超额 {m['excess']}pp | "
              f"最大回撤 {m['max_dd']}%（基准 {m['bench_max_dd']}%）| 夏普 {m['sharpe']}")
        print(yt.to_string())

    if summary_rows:
        sdf = pd.DataFrame(summary_rows)[["framework", "cagr", "bench_cagr", "excess",
                                          "max_dd", "bench_max_dd", "sharpe", "months"]]
        sdf.to_csv(os.path.join(args.results_dir, f"{prefix}bt_summary.csv"), index=False, encoding="utf-8-sig")
        cache_files = sorted(Path(args.cache_dir).glob("*.csv"))
        manifest = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "frameworks": list(dict.fromkeys(frameworks)), "start": args.start, "top": args.top,
                    "cost_bps_per_traded_notional": args.cost_bps, "final_liquidation_charged": False,
                    "pandas_version": pd.__version__, "numpy_version": np.__version__,
                    "cache_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in cache_files},
                    "limitations": ["present-day universe", "report-period-end plus 120-day availability approximation",
                                    "financial revisions unverified", "unadjusted stock price returns; no dividend reinvestment",
                                    "same-close rebalance assumption", "no market impact, suspension or limit-price execution model"]}
        Path(args.results_dir, f"{prefix}bt_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\n=== 汇总 ===")
        print(sdf.to_string(index=False))
        print(f"\n成本假设: 每单位买卖成交额 {args.cost_bps:g} bps；首期建仓计费，期末不强制清仓。")
        print("提醒: 固定当前池、120天财报滞后近似、未复权价格与同收盘成交假设仍有限制；相对排名也可能有偏。")
        print("免责声明: 本工具仅供学习研究，不构成投资建议。")
    else:
        ap.exit(2, "ERROR: 无框架产生结果；检查缓存、开始日期与股票数量\n")


if __name__ == "__main__":
    main()
