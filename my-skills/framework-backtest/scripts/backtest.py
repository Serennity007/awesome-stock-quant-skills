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

数据: fetch_history.py 的本地缓存（cache/），打分只用调仓日 T 已发布 ≥120 天的
年报数据 + T 时点的 PE/PB——时点正确（point-in-time），无未来函数。

已知局限（务必先读 references/backtest_methodology.md）:
    1. 幸存者偏差: 股票池固定为当前沪深300名单，历史成分未回溯，收益被系统性高估。
    2. 无交易成本/冲击成本。
    3. PE/PB 历史约自 2018 年起，分位窗口短于 5 年。
    4. 年报发布滞后按 120 天近似（实际 1-4 月底发布）。
    结果用于框架间相对比较，不能当作绝对收益预期。
"""
import os
import sys
import glob
import time
import argparse
from datetime import datetime

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
    sys.exit("ERROR: 未安装 akshare")

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(SKILL_DIR, "cache")
RESULTS_DIR = os.path.join(SKILL_DIR, "results")

FRAMEWORKS = ["danbin", "lilu", "mom12_1"]


def _disable_proxies():
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
    """沪深300 月末收盘（本地缓存优先）。"""
    path = os.path.join(cache_dir, "bench_sh000300.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["date"])
    else:
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
    return s.resample("ME").last().dropna()


# ---------------------------------------------------------------------------
# 打分（与各 screen.py 同一套档位，输入为时点正确的年报切片）
# ---------------------------------------------------------------------------

def _annual_slice(stock: dict, t: pd.Timestamp, lag_days: int = 120) -> tuple:
    """取 T 时点已发布(≥lag_days)的最近 5 个年报行。"""
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
    g = g[g > 0]
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
                  start: str, top_n: int) -> tuple:
    grid = [d for d in panel.index if d >= pd.Timestamp(start)]
    rows = []
    codes = [c for c in panel.columns]

    for i in range(len(grid) - 1):
        t, t_next = grid[i], grid[i + 1]
        scores = {}
        for code in codes:
            px = panel.at[t, code] if code in panel.columns else np.nan
            px_next = panel.at[t_next, code] if code in panel.columns else np.nan
            if pd.isna(px) or pd.isna(px_next) or px <= 0:
                continue
            if name == "mom12_1":
                idx_t = panel.index.get_loc(t)
                if idx_t < 12:
                    continue
                px_12 = panel.iloc[idx_t - 12][code] if code in panel.columns else np.nan
                px_1m = panel.iloc[idx_t - 1][code] if code in panel.columns else np.nan
                if pd.isna(px_12) or pd.isna(px_1m) or px_1m <= 0 or px_12 <= 0:
                    continue
                scores[code] = (px_1m / px_12 - 1) * 100
            else:
                sl, profit_sl = _annual_slice(stocks[code], t)
                if name == "danbin":
                    sc = score_danbin(sl, profit_sl)
                else:  # lilu
                    v = stocks[code]["value"]
                    m = v.loc[v["数据日期"] <= t]
                    cur_pb = float(m["市净率"].dropna().iloc[-1]) if not m["市净率"].dropna().empty else np.nan
                    pb_pct = pb_percentile_at(stocks[code], t, cur_pb)
                    sc = np.nan if pd.isna(pb_pct) else score_lilu(sl, profit_sl, pb_pct)
                if pd.notna(sc):
                    scores[code] = sc
        if len(scores) < top_n:
            continue
        top = sorted(scores, key=scores.get, reverse=True)[:top_n]
        rets = [panel.at[t_next, c] / panel.at[t, c] - 1 for c in top]
        rows.append({"date": t_next, "ret": float(np.mean(rets))})

    if not rows:
        return name, pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(rows).set_index("date").sort_index()
    bench = bench_m.reindex(df.index).pct_change()
    # 第一个月的收益以调仓日为基准（bench 用同日网格重算）
    bench0 = pd.Series(index=df.index, dtype=float)
    for j, d in enumerate(df.index):
        if d in bench_m.index and (pd.Timestamp(start) in bench_m.index or True):
            prev = bench_m.index[bench_m.index <= d]
            if len(prev) >= 2 and prev[-2] >= pd.Timestamp(start):
                bench0.loc[d] = bench_m[d] / bench_m[prev[-2]] - 1
    bench = bench0
    nav = (1 + df["ret"]).cumprod()
    bnav = (1 + bench.fillna(0)).cumprod()
    out = pd.DataFrame({"ret": df["ret"], "nav": nav, "bench_ret": bench, "bench_nav": bnav})
    return name, out, pd.DataFrame()


def metrics(nav: pd.Series, rets: pd.Series, bench_nav: pd.Series) -> dict:
    years = len(rets) / 12.0
    cagr = (nav.iloc[-1]) ** (1 / years) - 1 if years > 0 else np.nan
    bcagr = (bench_nav.iloc[-1]) ** (1 / years) - 1 if years > 0 else np.nan
    dd = (nav / nav.cummax() - 1).min()
    bdd = (bench_nav / bench_nav.cummax() - 1).min()
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
    args = ap.parse_args()

    _disable_proxies()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    stocks = load_stocks(CACHE_DIR)
    print(f"缓存加载: {len(stocks)} 只股票")
    if len(stocks) < args.min_stocks:
        sys.exit(f"ERROR: 缓存不足（{len(stocks)} < {args.min_stocks}），请先运行 fetch_history.py")

    bench_d = fetch_benchmark(CACHE_DIR)
    print(f"基准: 沪深300 {bench_d.index[0].date()} → {bench_d.index[-1].date()}")

    grid = month_end_grid(stocks)
    print("构建月末收盘面板...")
    panel = build_close_panel(stocks, grid)
    print(f"面板: {panel.shape[0]} 个月末 × {panel.shape[1]} 只")

    prefix = args.out_prefix + "_" if args.out_prefix else ""
    summary_rows = []
    for fw in [x.strip() for x in args.frameworks.split(",") if x.strip()]:
        if fw not in FRAMEWORKS:
            print(f"跳过未知框架 {fw}", file=sys.stderr)
            continue
        t0 = time.time()
        name, out, _ = run_framework(fw, stocks, panel, bench_d, args.start, args.top)
        if out.empty:
            print(f"{fw}: 无结果")
            continue
        m = metrics(out["nav"], out["ret"], out["bench_nav"])
        m["framework"] = name
        summary_rows.append(m)
        out.round(4).to_csv(os.path.join(RESULTS_DIR, f"{prefix}bt_result_{fw}.csv"), encoding="utf-8-sig")
        yt = yearly_table(out)
        yt.to_csv(os.path.join(RESULTS_DIR, f"{prefix}bt_yearly_{fw}.csv"), encoding="utf-8-sig")
        print(f"\n=== {fw}（{m['months']} 个月，耗时 {time.time()-t0:.0f}s）===")
        print(f"策略年化 {m['cagr']}% vs 沪深300 {m['bench_cagr']}% | 超额 {m['excess']}pp | "
              f"最大回撤 {m['max_dd']}%（基准 {m['bench_max_dd']}%）| 夏普 {m['sharpe']}")
        print(yt.to_string())

    if summary_rows:
        sdf = pd.DataFrame(summary_rows)[["framework", "cagr", "bench_cagr", "excess",
                                          "max_dd", "bench_max_dd", "sharpe", "months"]]
        sdf.to_csv(os.path.join(RESULTS_DIR, f"{prefix}bt_summary.csv"), index=False, encoding="utf-8-sig")
        print("\n=== 汇总 ===")
        print(sdf.to_string(index=False))
        print("\n提醒: 存在幸存者偏差（固定当前沪深300名单）、无交易成本，"
              "结果用于框架间相对比较而非绝对收益预期。")
        print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
