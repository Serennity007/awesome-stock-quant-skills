#!/usr/bin/env python3
"""us_hot.py — 美股热门 AI 股追踪器。

用法:
    python scripts/us_hot.py
    python scripts/us_hot.py --tickers NVDA,AAPL,MSFT
    python scripts/us_hot.py --tickers NVDA,AVGO --out us_hot.csv

数据源: akshare stock_us_daily（新浪财经美股日线）。
  - 现价 / 涨跌幅 / 成交量：使用未复权日线（adjust=""）。
  - 20/60 日动量、52 周高低位距离：使用前复权日线（adjust="qfq"）。
输出: 现价、涨跌幅、20/60 日动量、52 周高低位距离、成交量异动，按 20 日动量排序。
"""
import os

os.environ.setdefault("TQDM_DISABLE", "1")

import argparse
import sys
import time

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
    sys.exit("ERROR: 未安装 akshare，请先执行: pip install akshare pandas")

DEFAULT_TICKERS = ["NVDA", "AVGO", "ORCL", "GOOGL", "SNDK", "WDC", "PLTR", "TSLA"]

THEME_MAP = {
    "NVDA": "AI算力",
    "AVGO": "AI算力",
    "ORCL": "AI算力",
    "GOOGL": "AI算力",
    "SNDK": "存储",
    "WDC": "存储",
    "PLTR": "AI应用",
    "TSLA": "robotaxi",
}


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


def normalize_date(date_val) -> str:
    """兼容 20231231 与 2023-12-31 两种格式，统一返回 2023-12-31。"""
    if date_val is None:
        return ""
    s = str(date_val).strip().replace("/", "-")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def safe_div(numerator, denominator, default=float("nan")):
    """除零保护。"""
    try:
        if denominator and abs(float(denominator)) > 1e-12:
            return float(numerator) / float(denominator)
    except Exception:
        pass
    return default


def fetch_daily(ticker: str, adjust: str = "qfq") -> pd.DataFrame:
    """获取单个美股日线，失败抛异常。"""
    try:
        df = _retry_call(lambda: ak.stock_us_daily(symbol=ticker, adjust=adjust))
    except Exception as e:
        raise RuntimeError(f"获取 {ticker} 日线(adjust={adjust!r})失败: {e}")
    if df is None or df.empty:
        raise RuntimeError(f"获取 {ticker} 日线(adjust={adjust!r})为空（可能接口限流或代码有误）")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ("open", "high", "low", "close", "volume"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date", "close", "volume"]).sort_values("date").reset_index(drop=True)
    return df


def analyze_one(ticker: str) -> dict:
    """对单个 ticker 计算快照指标。"""
    df_unadj = fetch_daily(ticker, adjust="")
    df_qfq = fetch_daily(ticker, adjust="qfq")
    time.sleep(0.15)

    if len(df_unadj) < 2:
        raise RuntimeError(f"{ticker} 未复权日线不足 2 条，无法计算涨跌幅")
    if len(df_qfq) < 70:
        raise RuntimeError(f"{ticker} 前复权日线不足 70 条，无法计算 60 日动量")

    last_unadj = df_unadj.iloc[-1]
    prev_unadj = df_unadj.iloc[-2]
    price = float(last_unadj["close"])
    prev_close = float(prev_unadj["close"])
    change_pct = safe_div(price - prev_close, prev_close, default=float("nan")) * 100

    last_qfq = df_qfq.iloc[-1]
    price_qfq = float(last_qfq["close"])
    mom_20 = safe_div(price_qfq, float(df_qfq.iloc[-21]["close"]), default=float("nan")) * 100 - 100
    mom_60 = safe_div(price_qfq, float(df_qfq.iloc[-61]["close"]), default=float("nan")) * 100 - 100

    window_52w = df_qfq.tail(252)
    high_52w = float(window_52w["high"].max())
    low_52w = float(window_52w["low"].min())
    dist_high = safe_div(price_qfq, high_52w, default=float("nan")) * 100 - 100
    dist_low = safe_div(price_qfq, low_52w, default=float("nan")) * 100 - 100

    vol_last = float(last_unadj["volume"])
    vol_ma20 = float(df_unadj["volume"].tail(20).mean())
    vol_ratio = safe_div(vol_last, vol_ma20, default=float("nan"))

    return {
        "ticker": ticker,
        "theme": THEME_MAP.get(ticker.upper(), "其他"),
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "mom_20": round(mom_20, 2),
        "mom_60": round(mom_60, 2),
        "dist_52w_high": round(dist_high, 2),
        "dist_52w_low": round(dist_low, 2),
        "vol_ratio": round(vol_ratio, 2),
        "date": normalize_date(last_unadj["date"]),
    }


def main():
    ap = argparse.ArgumentParser(description="美股热门 AI 股追踪器")
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                    help="逗号分隔的美股代码（默认: NVDA,AVGO,ORCL,GOOGL,SNDK,WDC,PLTR,TSLA）")
    ap.add_argument("--out", default=None, help="CSV 输出路径（可选）")
    ap.add_argument("--sort", default="mom_20", choices=["mom_20", "mom_60", "change_pct", "vol_ratio"],
                    help="排序字段（默认 mom_20）")
    args = ap.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        sys.exit("ERROR: 请至少提供一个 ticker")

    rows, failed = [], []
    for t in tickers:
        try:
            r = analyze_one(t)
            rows.append(r)
            print(f"{t} OK  date={r['date']} price={r['price']} mom_20={r['mom_20']}%")
        except Exception as e:
            failed.append(t)
            print(f"{t} 失败: {e}", file=sys.stderr)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows)
    sort_col = args.sort
    ascending = sort_col in ("dist_52w_high",)
    df = df.sort_values(sort_col, ascending=ascending).reset_index(drop=True)

    display_cols = ["ticker", "theme", "price", "change_pct", "mom_20", "mom_60",
                    "dist_52w_high", "dist_52w_low", "vol_ratio"]
    if args.out:
        df.to_csv(args.out, index=False, encoding="utf-8-sig")
        print(f"\n快照表已写入 {args.out}")

    print(f"\n=== 美股热门 AI 股快照（按 {sort_col} 排序）===")
    print(df[display_cols].to_string(index=False))
    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    if failed:
        print(f"失败列表: {', '.join(failed)}")
    print("\n数据说明：现价为日线未复权最新收盘价；20/60日动量、52周高低位距离基于前复权；成交量异动 = 最新成交量 / 20 日均量。")
    print("仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
