#!/usr/bin/env python3
"""patterns.py — A股技术形态识别。

用法:
    python scripts/patterns.py 600519
    python scripts/patterns.py 600519,000858 --days 250 --window 60 --out signals.csv

数据源: akshare 新浪日线 (stock_zh_a_daily)。所有网络调用失败都会给出清晰报错。
形态说明见 references/patterns.md。
"""
import argparse
import sys

import pandas as pd

try:
    import akshare as ak
except ImportError:
    sys.exit("ERROR: 未安装 akshare，请先执行: pip install akshare pandas")


def fetch_daily(code: str, days: int) -> pd.DataFrame:
    """近 days 个交易日的日线（新浪前复权）。失败抛异常。"""
    symbol = ("sh" if code.startswith("6") else "sz") + code
    try:
        df = ak.stock_zh_a_daily(symbol=symbol, adjust="qfq")
    except Exception as e:
        raise RuntimeError(f"获取 {code} 日线失败: {e}")
    if df is None or df.empty:
        raise RuntimeError(f"获取 {code} 日线为空（可能接口限流或代码有误）")
    df = df.tail(days).reset_index(drop=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["close", "volume"])


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    for n in (5, 10, 20, 60):
        df[f"ma{n}"] = df["close"].rolling(n).mean()
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["dif"] = ema12 - ema26
    df["dea"] = df["dif"].ewm(span=9, adjust=False).mean()
    return df


def detect_signals(df: pd.DataFrame, window: int) -> list:
    """对最后一根K线做形态判定，返回信号代码列表。"""
    if len(df) < max(65, window + 2):
        return ["INSUFFICIENT_DATA"]
    row = df.iloc[-1]
    signals = []

    ma_bull = row["ma5"] > row["ma10"] > row["ma20"] > row["ma60"]
    ma_bear = row["ma5"] < row["ma10"] < row["ma20"] < row["ma60"]
    if ma_bull:
        signals.append("MA_BULLISH")
    elif ma_bear:
        signals.append("MA_BEARISH")

    # MACD 金叉/死叉：近 3 日内 DIF 与 DEA 发生交叉
    dif, dea = df["dif"], df["dea"]
    recent = df.tail(3).index
    crossed_up = any(dif[i - 1] <= dea[i - 1] and dif[i] > dea[i] for i in recent if i > 0)
    crossed_dn = any(dif[i - 1] >= dea[i - 1] and dif[i] < dea[i] for i in recent if i > 0)
    if crossed_up:
        signals.append("MACD_GOLDEN")
    elif crossed_dn:
        signals.append("MACD_DEATH")

    # 放量突破 N 日新高（不含当日的前 N 日最高收盘价）
    prev_high = df["close"].iloc[-(window + 1):-1].max()
    if row["close"] > prev_high and row["volume"] >= row["vol_ma20"] * 1.5:
        signals.append("VOL_BREAKOUT")

    # 缩量回踩 MA20（前提是大方向多头）
    near_ma20 = abs(row["close"] / row["ma20"] - 1) <= 0.02
    shrink = row["volume"] <= row["vol_ma20"] * 0.8
    if ma_bull and near_ma20 and shrink:
        signals.append("PULLBACK_MA")

    return signals or ["NO_SIGNAL"]


def analyze_one(code: str, days: int, window: int) -> dict:
    df = add_indicators(fetch_daily(code, days))
    row = df.iloc[-1]
    signals = detect_signals(df, window)
    return {
        "code": code,
        "date": str(row["date"])[:10],
        "close": round(float(row["close"]), 2),
        "ma5": round(float(row["ma5"]), 2),
        "ma20": round(float(row["ma20"]), 2),
        "ma60": round(float(row["ma60"]), 2),
        "dif": round(float(row["dif"]), 3),
        "dea": round(float(row["dea"]), 3),
        "vol_ratio": round(float(row["volume"] / row["vol_ma20"]), 2),
        "signals": ",".join(signals),
    }


def main():
    ap = argparse.ArgumentParser(description="A股技术形态识别")
    ap.add_argument("codes", help="逗号分隔的股票代码，如 600519,000858")
    ap.add_argument("--days", type=int, default=250, help="取近 N 个交易日(默认250)")
    ap.add_argument("--window", type=int, default=60, help="新高突破窗口(默认60日)")
    ap.add_argument("--out", default=None, help="CSV 输出路径（可选）")
    args = ap.parse_args()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    rows, failed = [], []
    for code in codes:
        try:
            r = analyze_one(code, args.days, args.window)
            rows.append(r)
            print(f"{code}  [{r['date']}] 收盘 {r['close']}  量比 {r['vol_ratio']}  信号: {r['signals']}")
        except Exception as e:
            failed.append(code)
            print(f"{code} 失败: {e}", file=sys.stderr)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows)
    if args.out:
        df.to_csv(args.out, index=False, encoding="utf-8-sig")
        print(f"\n信号表已写入 {args.out}")
    print("\n=== 信号表 ===")
    print(df.to_string(index=False))
    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("信号含义见 references/patterns.md；形态为滞后指标，不构成投资建议。")


if __name__ == "__main__":
    main()
