"""
Technical indicators — computes RSI(14)/MA(20,50,200)/Bollinger(20,2)/ATR(14) from 250 daily bars.

Depends on numpy; no talib or other heavy deps.

Usage:
  python technical_indicators.py AAPL
  python technical_indicators.py SPY --indicators rsi,ma
  python technical_indicators.py NVDA --output /tmp/nvda_ta.json
"""

import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np

from contracts import resolve
from ib_client import ib_connect, log, qualify, req_historical_safe

CLIENT_ID_OFFSET = 14


def rsi(closes: np.ndarray, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    diff = np.diff(closes)
    gain = np.where(diff > 0, diff, 0.0)
    loss = np.where(diff < 0, -diff, 0.0)
    # Wilder's smoothing
    avg_gain = gain[:period].mean()
    avg_loss = loss[:period].mean()
    for i in range(period, len(diff)):
        avg_gain = (avg_gain * (period - 1) + gain[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def ma(closes: np.ndarray, period: int) -> float | None:
    if len(closes) < period:
        return None
    return round(float(closes[-period:].mean()), 4)


def bollinger(closes: np.ndarray, period: int = 20, k: float = 2.0) -> dict:
    if len(closes) < period:
        return {"upper": None, "middle": None, "lower": None}
    window = closes[-period:]
    middle = float(window.mean())
    sd = float(window.std(ddof=0))
    return {
        "upper": round(middle + k * sd, 4),
        "middle": round(middle, 4),
        "lower": round(middle - k * sd, 4),
    }


def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
        period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    prev_close = closes[:-1]
    h = highs[1:]
    l = lows[1:]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_close), np.abs(l - prev_close)))
    if len(tr) < period:
        return None
    # Wilder smoothing
    atr_val = tr[:period].mean()
    for i in range(period, len(tr)):
        atr_val = (atr_val * (period - 1) + tr[i]) / period
    return round(float(atr_val), 4)


def summarize(price: float, ind: dict) -> str:
    pieces = []
    r = ind.get("rsi_14")
    if r is not None:
        if r >= 70:
            pieces.append("overbought")
        elif r <= 30:
            pieces.append("oversold")
        else:
            pieces.append(f"RSI {r}")

    ma50 = ind.get("ma_50")
    if ma50 is not None:
        if price > ma50:
            pieces.append("above MA50")
        else:
            pieces.append("below MA50")

    ma200 = ind.get("ma_200")
    if ma50 and ma200:
        if ma50 > ma200:
            pieces.append("golden cross trend")
        else:
            pieces.append("death cross trend")

    upper = ind.get("bb_upper")
    lower = ind.get("bb_lower")
    if upper and lower:
        if price >= upper:
            pieces.append("at upper band")
        elif price <= lower:
            pieces.append("at lower band")

    return ", ".join(pieces) if pieces else "no signal"


def compute_indicators(highs, lows, closes, wanted: set[str]) -> dict:
    out: dict = {}
    if "rsi" in wanted:
        out["rsi_14"] = rsi(closes, 14)
    if "ma" in wanted:
        out["ma_20"] = ma(closes, 20)
        out["ma_50"] = ma(closes, 50)
        out["ma_200"] = ma(closes, 200)
    if "bb" in wanted:
        bb = bollinger(closes, 20, 2.0)
        out["bb_upper"] = bb["upper"]
        out["bb_middle"] = bb["middle"]
        out["bb_lower"] = bb["lower"]
    if "atr" in wanted:
        out["atr_14"] = atr(highs, lows, closes, 14)
    return out


def fetch_indicators(ib, symbol: str, wanted: set[str]) -> dict:
    contract = resolve(symbol)
    q = qualify(ib, contract)
    bars = req_historical_safe(
        ib, q,
        endDateTime="",
        durationStr="1 Y",
        barSizeSetting="1 day",
        whatToShow="TRADES",
        useRTH=True,
        formatDate=1,
    )
    if not bars:
        raise RuntimeError(f"No historical data returned for {symbol}")

    highs = np.array([b.high for b in bars], dtype=float)
    lows = np.array([b.low for b in bars], dtype=float)
    closes = np.array([b.close for b in bars], dtype=float)
    log(f"  {symbol}: {len(closes)} daily bars")

    indicators = compute_indicators(highs, lows, closes, wanted)
    current_price = round(float(closes[-1]), 4)
    return {
        "symbol": symbol,
        "asof": str(bars[-1].date),
        "current_price": current_price,
        "bars_used": len(closes),
        "indicators": indicators,
        "summary": summarize(current_price, indicators),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Technical indicators")
    parser.add_argument("symbol", help="ticker symbol")
    parser.add_argument("--indicators", default="rsi,ma,bb,atr",
                        help="comma-separated (rsi,ma,bb,atr)")
    parser.add_argument("--output", help="output file path (default stdout)")
    args = parser.parse_args()

    wanted = {s.strip().lower() for s in args.indicators.split(",") if s.strip()}

    log(f"🔄 {args.symbol} technical indicators ({','.join(sorted(wanted))}) ...")

    try:
        with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
            result = fetch_indicators(ib, args.symbol, wanted)
    except Exception as e:
        log(f"❌ Failed: {e}")
        return 1

    result["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        tmp = args.output + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json_str)
        os.rename(tmp, args.output)
        log(f"📁 Saved to {args.output}")
    else:
        print(json_str)

    log(f"✅ Done: {result['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
