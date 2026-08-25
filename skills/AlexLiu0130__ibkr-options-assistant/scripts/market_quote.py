"""
market_quote.py — single-point quote (IBKR).

Usage:
  python market_quote.py AAPL
  python market_quote.py ^GSPC
  python market_quote.py EURUSD
  python market_quote.py 0700.HK
  python market_quote.py ES              # continuous futures contract

Output JSON schema (stdout):
  {
    "symbol":   "AAPL",
    "kind":     "stock" | "index" | "fx" | "future",
    "price":    263.4,
    "currency": "USD",
    "asof":     "2026-04-17 13:30:05",
    "source":   "IBKR via ib_async (delayed)",
    "extra":    {exchange, primaryExchange, conId, contract_name, ...}
  }
"""

import argparse
import json
import sys
from datetime import datetime

from contracts import resolve
from ib_async import ContFuture, Forex, Index, Stock
from ib_client import ib_connect, log, qualify, req_historical_safe

CLIENT_ID_OFFSET = 7


def _kind_of(contract) -> str:
    if isinstance(contract, Index):
        return "index"
    if isinstance(contract, Forex):
        return "fx"
    if isinstance(contract, ContFuture):
        return "future"
    return "stock"


def _fetch_last_close(ib, contract) -> dict:
    q = qualify(ib, contract)
    what = "MIDPOINT" if isinstance(contract, Forex) else "TRADES"
    bars = req_historical_safe(
        ib, q,
        endDateTime="",
        durationStr="5 D",
        barSizeSetting="1 day",
        whatToShow=what,
        useRTH=True,
        formatDate=1,
    )
    if not bars:
        raise RuntimeError("Historical data returned empty (missing subscription or permissions)")

    latest = bars[-1]
    return {
        "price": round(latest.close, 6),
        "asof_date": str(latest.date),
        "qualified": q,
        "last_bar": {
            "open":   round(latest.open, 6),
            "high":   round(latest.high, 6),
            "low":    round(latest.low, 6),
            "close":  round(latest.close, 6),
            "volume": int(latest.volume) if latest.volume else 0,
        },
    }


def quote(ib, symbol: str) -> dict:
    contract = resolve(symbol)
    kind = _kind_of(contract)
    result = _fetch_last_close(ib, contract)
    q = result["qualified"]

    return {
        "symbol":   symbol,
        "kind":     kind,
        "price":    result["price"],
        "currency": q.currency,
        "asof":     result["asof_date"],
        "source":   "IBKR via ib_async (delayed)",
        "extra": {
            "ibkr_symbol":     q.symbol,
            "secType":         q.secType,
            "exchange":        q.exchange,
            "primaryExchange": getattr(q, "primaryExchange", ""),
            "conId":           q.conId,
            "last_bar":        result["last_bar"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="IBKR single-point quote")
    parser.add_argument("symbol", nargs="+", help="ticker / index / FX pair / future key (one or more)")
    args = parser.parse_args()

    with ib_connect(client_id_offset=CLIENT_ID_OFFSET, verbose=False) as ib:
        results = []
        for sym in args.symbol:
            try:
                results.append(quote(ib, sym))
            except Exception as e:
                results.append({
                    "symbol": sym,
                    "error": f"{type(e).__name__}: {e}",
                    "source": "IBKR via ib_async",
                })

    output = results[0] if len(results) == 1 else results
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
