#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index_thermometer.py — 约翰·博格指数投资法：A股指数估值温度计 + 定投回测。

用法:
    python scripts/index_thermometer.py                      # 全部宽基指数温度计
    python scripts/index_thermometer.py --index 沪深300      # 单个指数
    python scripts/index_thermometer.py --dca --years 5     # 附带月定投回测
    python scripts/index_thermometer.py --div 2.5 --growth 5

逻辑（博格《共同基金常识》框架的 A 股机械化近似）:
    1. 估值温度计：指数 PE(TTM)/PB 相对近 10 年（及全历史）的分位。
    2. 博格公式收益拆解：预期年化 ≈ 股息率 + 盈利增速 + 估值回归贡献。
       （股息率与盈利增速为保守假设参数，估值回归按 5 年向 10 年中位回归计）
    3. 定投档位参考：分位 <20 加倍定投 / <40 正常偏积极 / <60 正常 /
       <80 减半 / >=80 暂停新买入（博格原教旨是持有不动，此为本土化定投增强）。
    4. 定投回测：近 N 年按月等额定投 vs 期初一次性买入。

数据源: akshare（乐咕乐股指数估值月度历史 + 新浪/腾讯指数日线，失败自动降级）。
"""
import os
import sys
import time
import argparse
from datetime import datetime

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


# 支持的宽基指数：lg估值接口名 / 新浪-腾讯行情代码
INDEXES = {
    "沪深300": "sh000300",
    "中证500": "sh000905",
    "上证50": "sh000016",
    "中证1000": "sh000852",
}


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理阻断数据源直连。"""
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(k, None)


def _retry_call(func, max_retries: int = 3, sleep_base: float = 1.5):
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


def _find_col(candidates: list, df: pd.DataFrame):
    for c in df.columns:
        cs = str(c)
        for cand in candidates:
            if cand in cs:
                return c
    return None


# ---------------------------------------------------------------------------
# 估值历史（乐咕乐股，2005 至今的月度序列）
# ---------------------------------------------------------------------------

def _pick_exact_then_substring(df: pd.DataFrame, exact: str, substr: str):
    """先精确匹配列名（避免'等权滚动市盈率'抢在'滚动市盈率'之前），再子串匹配。"""
    for c in df.columns:
        if str(c).strip() == exact:
            return c
    return _find_col([substr], df)


def fetch_pe_history(lg_name: str) -> pd.DataFrame:
    """指数 PE(TTM) 月度历史。失败抛异常。"""
    df = _retry_call(lambda: ak.stock_index_pe_lg(symbol=lg_name))
    time.sleep(0.3)
    if df is None or df.empty:
        raise RuntimeError("PE 历史为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df)
    pe_col = _pick_exact_then_substring(df, "滚动市盈率", "滚动市盈率")  # TTM 口径（加权）
    if date_col is None or pe_col is None:
        raise RuntimeError("PE 历史缺列")
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    out = df[[date_col, pe_col]].rename(columns={date_col: "date", pe_col: "pe"})
    out["pe"] = pd.to_numeric(out["pe"].astype(str).str.replace(",", ""), errors="coerce")
    return out.dropna().sort_values("date").reset_index(drop=True)


def fetch_pb_history(lg_name: str) -> pd.DataFrame:
    """指数 PB 月度历史。失败返回空 DataFrame。"""
    try:
        df = _retry_call(lambda: ak.stock_index_pb_lg(symbol=lg_name))
        time.sleep(0.3)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df)
    pb_col = _pick_exact_then_substring(df, "市净率", "市净率")  # 加权口径
    if date_col is None or pb_col is None:
        return pd.DataFrame()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    out = df[[date_col, pb_col]].rename(columns={date_col: "date", pb_col: "pb"})
    out["pb"] = pd.to_numeric(out["pb"].astype(str).str.replace(",", ""), errors="coerce")
    return out.dropna().sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 指数行情（新浪优先，腾讯降级）——用于定投回测与当前点位
# ---------------------------------------------------------------------------

def fetch_index_daily(tx_symbol: str) -> pd.DataFrame:
    try:
        df = _retry_call(lambda: ak.stock_zh_index_daily(symbol=tx_symbol))
        time.sleep(0.3)
    except Exception:
        df = None
    if df is None or df.empty:
        tencent = tx_symbol.replace("sh", "sh").replace("sz", "sz")
        df = _retry_call(lambda: ak.stock_zh_index_daily_tx(symbol=tencent))
        time.sleep(0.3)
    if df is None or df.empty:
        raise RuntimeError("指数行情为空")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df[["date", "close"]].dropna().sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 博格分析
# ---------------------------------------------------------------------------

def percentile(series: pd.Series, cur: float) -> float:
    """当前值在历史序列中的分位（0-100）。"""
    s = series.dropna()
    if s.empty or pd.isna(cur):
        return float("nan")
    return float((s < cur).mean() * 100)


def bogle_expected_return(pe_hist: pd.DataFrame, cur_pe: float, div: float, growth: float,
                          horizon: int = 5) -> tuple:
    """博格公式三项拆解，返回 (预期年化%, 估值回归贡献%)。

    预期年化 ≈ 股息率 + 盈利增速 + 估值回归贡献；
    估值回归 = (PE中位数/当前PE)^(1/horizon) - 1，向近10年中位回归。
    """
    recent = pe_hist.tail(120)  # 近10年月度
    median_pe = float(recent["pe"].median()) if not recent.empty else float("nan")
    if pd.isna(cur_pe) or cur_pe <= 0 or pd.isna(median_pe) or median_pe <= 0:
        est = div + growth
        return est, float("nan")
    spec = ((median_pe / cur_pe) ** (1.0 / horizon) - 1) * 100
    return div + growth + spec, spec


def temperature_action(pe_pct10: float) -> tuple[int, str]:
    """估值温度（0-100，越低越冷）与定投档位参考。"""
    if pd.isna(pe_pct10):
        return 50, "数据不足，默认正常定投"
    if pe_pct10 < 20:
        return int(pe_pct10), "低温：加倍定投区"
    elif pe_pct10 < 40:
        return int(pe_pct10), "偏低：正常偏积极定投"
    elif pe_pct10 < 60:
        return int(pe_pct10), "中性：正常定投"
    elif pe_pct10 < 80:
        return int(pe_pct10), "偏高：减半定投"
    return int(pe_pct10), "高温：暂停新买入（持仓不动）"


def dca_backtest(daily: pd.DataFrame, years: int, monthly_amount: float = 1000.0) -> dict:
    """近 years 年按月等额定投 vs 期初一次性买入（不含交易成本与分红）。"""
    start = daily["date"].iloc[-1] - pd.DateOffset(years=years)
    sub = daily[daily["date"] >= start].reset_index(drop=True)
    if len(sub) < 60:
        return {}
    monthly = sub.set_index("date")["close"].resample("ME").last().dropna()
    if len(monthly) < 6:
        return {}
    invested = monthly_amount * len(monthly)
    units = (monthly_amount / monthly).sum()
    final_value = units * monthly.iloc[-1]
    n_years = len(monthly) / 12.0
    dca_annual = ((final_value / invested) ** (1 / n_years) - 1) * 100 if invested > 0 else float("nan")
    lump_annual = ((monthly.iloc[-1] / monthly.iloc[0]) ** (1 / n_years) - 1) * 100
    roll_max = monthly.cummax()
    max_dd = ((monthly / roll_max) - 1).min() * 100
    return {
        "dca_months": len(monthly),
        "dca_invested": round(invested, 0),
        "dca_final_value": round(final_value, 0),
        "dca_total_return": round((final_value / invested - 1) * 100, 1) if invested > 0 else None,
        "dca_annualized": round(float(dca_annual), 2) if pd.notna(dca_annual) else None,
        "lumpsum_annualized": round(float(lump_annual), 2) if pd.notna(lump_annual) else None,
        "period_max_drawdown": round(float(max_dd), 1) if pd.notna(max_dd) else None,
    }


def analyze_index(lg_name: str, tx_symbol: str, args) -> dict:
    row = {"index": lg_name, "tx_symbol": tx_symbol}

    pe_hist = fetch_pe_history(lg_name)
    cur_pe = float(pe_hist["pe"].iloc[-1])
    row["pe_ttm"] = round(cur_pe, 2)
    row["pe_pct_10y"] = round(percentile(pe_hist.tail(120)["pe"], cur_pe), 1)
    row["pe_pct_all"] = round(percentile(pe_hist["pe"], cur_pe), 1)
    row["pe_median_10y"] = round(float(pe_hist.tail(120)["pe"].median()), 2)
    row["pe_hist_years"] = round((pe_hist["date"].iloc[-1] - pe_hist["date"].iloc[0]).days / 365.25, 1)

    pb_hist = fetch_pb_history(lg_name)
    if not pb_hist.empty:
        cur_pb = float(pb_hist["pb"].iloc[-1])
        row["pb"] = round(cur_pb, 2)
        row["pb_pct_10y"] = round(percentile(pb_hist.tail(120)["pb"], cur_pb), 1)
    else:
        row["pb"], row["pb_pct_10y"] = None, None

    est, spec = bogle_expected_return(pe_hist, cur_pe, args.div, args.growth)
    row["bogle_expected_return"] = round(est, 2) if pd.notna(est) else None
    row["speculative_component"] = round(spec, 2) if pd.notna(spec) else None
    temp, action = temperature_action(row["pe_pct_10y"])
    row["temperature"] = temp
    row["action"] = action

    if args.dca:
        daily = fetch_index_daily(tx_symbol)
        bt = dca_backtest(daily, args.years)
        row["index_close"] = round(float(daily["close"].iloc[-1]), 2)
        row.update(bt)
    return row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="约翰·博格指数投资法：估值温度计 + 定投回测")
    ap.add_argument("--index", default=None, help="指数名: 沪深300/中证500/上证50/创业板指，默认全部")
    ap.add_argument("--div", type=float, default=2.5, help="假设的指数长期股息率%%(默认2.5)")
    ap.add_argument("--growth", type=float, default=5.0, help="假设的长期盈利增速%%(默认5)")
    ap.add_argument("--dca", action="store_true", help="附带近 N 年月定投回测")
    ap.add_argument("--years", type=int, default=5, help="定投回测年数(默认5)")
    ap.add_argument("--out", default="bogle_thermometer.csv", help="CSV 输出路径")
    args = ap.parse_args()

    _disable_proxies()

    if args.index:
        if args.index not in INDEXES:
            sys.exit(f"ERROR: 未知指数 '{args.index}'，支持: {', '.join(INDEXES)}")
        targets = [(args.index, INDEXES[args.index])]
    else:
        targets = list(INDEXES.items())

    print(f"分析 {len(targets)} 个指数（估值历史 + 博格收益拆解{' + 定投回测' if args.dca else ''}）...")
    rows, failed = [], []
    for i, (lg_name, tx_symbol) in enumerate(targets, 1):
        try:
            r = analyze_index(lg_name, tx_symbol, args)
            rows.append(r)
            print(f"[{i}/{len(targets)}] {lg_name}: PE {r['pe_ttm']}（10年分位 {r['pe_pct_10y']}%）温度 {r['temperature']} → {r['action']} | 博格预期年化 {r['bogle_expected_return']}%")
        except Exception as e:
            failed.append((lg_name, str(e)))
            print(f"[{i}/{len(targets)}] {lg_name} 失败: {e}", file=sys.stderr)
        time.sleep(0.5)

    if not rows:
        sys.exit("ERROR: 全部指数分析失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    show_cols = ["index", "pe_ttm", "pe_pct_10y", "pb", "pb_pct_10y", "temperature",
                 "bogle_expected_return", "action"]
    if args.dca:
        show_cols += ["dca_annualized", "lumpsum_annualized", "period_max_drawdown"]
    show_cols = [c for c in show_cols if c in df.columns]
    print(f"\n=== 指数估值温度计（完整结果见 {args.out}）===")
    print(df[show_cols].to_string(index=False))

    print("\n博格三原则提醒:")
    print("  1. 成本至关重要——优先选低费率宽基指数基金/ETF，长期费率差足以改变结局。")
    print("  2. 分散是免费的午餐——宽基指数本身就是对个股风险的对冲。")
    print("  3. 别理噪音——'Don't just do something, stand there!' 温度计只是定投节奏参考，")
    print("     博格的原教旨答案是：无论估值如何，按纪律定投并持有到底。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。股息率与盈利增速为假设参数，请自行校准。")


if __name__ == "__main__":
    main()
