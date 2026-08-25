"""
Option chain fetcher — fetches the option chain near the underlying's ATM, with Greeks.

Output JSON: symbol, underlying_price, chain[{expiration, dte, calls[...], puts[...]}]
Each call/put: strike, bid, ask, last, volume, open_interest, iv, delta, gamma, vega, theta

Usage:
  python options_chain.py SPY
  python options_chain.py AAPL --strikes 15 --dte-min 14 --dte-max 90
  python options_chain.py SPY --max-expirations 5 --output /tmp/spy_chain.json
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, date

from ib_async import Option

from contracts import resolve
from ib_client import ib_connect, log, qualify

CLIENT_ID_OFFSET = 8
BATCH_SIZE = 50
BATCH_SLEEP = 2.0


def _parse_expiration(exp_str: str) -> date:
    return datetime.strptime(exp_str, "%Y%m%d").date()


def _pick_expirations(
    all_expirations: list[str],
    dte_min: int,
    dte_max: int,
    max_count: int,
) -> list[str]:
    today = date.today()
    candidates = []
    for exp_str in sorted(all_expirations):
        exp_date = _parse_expiration(exp_str)
        dte = (exp_date - today).days
        if dte_min <= dte <= dte_max:
            candidates.append((dte, exp_str))
    if not candidates:
        return []
    if len(candidates) <= max_count:
        return [e for _, e in candidates]
    if max_count == 1:
        return [candidates[len(candidates) // 2][1]]
    step = (len(candidates) - 1) / (max_count - 1)
    indices = [round(i * step) for i in range(max_count)]
    return [candidates[i][1] for i in sorted(set(indices))]


def _pick_strikes(
    all_strikes: list[float],
    atm_price: float,
    num_strikes: int,
) -> list[float]:
    if not all_strikes:
        return []
    sorted_strikes = sorted(all_strikes)
    atm_idx = min(range(len(sorted_strikes)),
                  key=lambda i: abs(sorted_strikes[i] - atm_price))
    lo = max(0, atm_idx - num_strikes)
    hi = min(len(sorted_strikes), atm_idx + num_strikes + 1)
    return sorted_strikes[lo:hi]


def _batch_qualify_and_tick(ib, contracts):
    all_valid = []
    for i in range(0, len(contracts), BATCH_SIZE):
        batch = contracts[i:i + BATCH_SIZE]
        qualified = ib.qualifyContracts(*batch)
        valid = [c for c in qualified if c is not None and getattr(c, 'conId', 0) > 0]
        all_valid.extend(valid)
        if i + BATCH_SIZE < len(contracts):
            time.sleep(0.5)
    log(f"  qualify done: {len(all_valid)}/{len(contracts)} valid")
    if not all_valid:
        return {}

    for c in all_valid:
        ib.reqMktData(c, genericTickList="106", snapshot=False)

    max_wait = max(10, len(all_valid) * 0.5)
    waited = 0.0
    while waited < max_wait:
        ib.sleep(2)
        waited += 2
        got = sum(1 for c in all_valid
                  if (t := ib.ticker(c)) and t.modelGreeks is not None)
        if got >= len(all_valid):
            break
    log(f"  Greeks: {got}/{len(all_valid)} (waited {waited:.0f}s)")

    results = {}
    for c in all_valid:
        ticker = ib.ticker(c)
        if ticker is None:
            continue
        key = (c.lastTradeDateOrContractMonth, c.strike, c.right)
        greeks = ticker.modelGreeks
        results[key] = {
            "strike": c.strike,
            "bid": _safe_price(ticker.bid),
            "ask": _safe_price(ticker.ask),
            "last": _safe_price(ticker.last) or _safe_price(ticker.close),
            "volume": _safe_int(ticker.volume),
            "open_interest": None,
            "iv": round(greeks.impliedVol, 4) if greeks and greeks.impliedVol is not None else None,
            "delta": round(greeks.delta, 4) if greeks and greeks.delta is not None else None,
            "gamma": round(greeks.gamma, 6) if greeks and greeks.gamma is not None else None,
            "vega": round(greeks.vega, 4) if greeks and greeks.vega is not None else None,
            "theta": round(greeks.theta, 4) if greeks and greeks.theta is not None else None,
        }

    for c in all_valid:
        ib.cancelMktData(c)

    return results


def _safe_price(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    if val <= 0:
        return None
    return round(float(val), 2)


def _safe_int(val) -> int | None:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return int(val)


def fetch_chain(
    ib,
    symbol: str,
    num_strikes: int = 10,
    dte_min: int = 7,
    dte_max: int = 60,
    max_expirations: int = 3,
) -> dict:
    contract = resolve(symbol)
    q = qualify(ib, contract)
    log(f"  underlying conId={q.conId}, secType={q.secType}")

    tickers = ib.reqTickers(q)
    ib.sleep(2)
    t = tickers[0] if tickers else None
    if t is None:
        raise RuntimeError(f"Could not fetch current price for {symbol}")
    underlying_price = None
    for val in (t.last, t.close, t.midpoint()):
        if val is not None and not math.isnan(val) and val > 0:
            underlying_price = round(val, 2)
            break
    if underlying_price is None:
        raise RuntimeError(f"Could not fetch current price for {symbol}")
    log(f"  underlying price: {underlying_price}")

    # IBKR auto-upgrades requested type 3 (delayed) to 1 (live) for subscribed
    # tickers; reflect what actually came back, not what was requested.
    _DT_NAMES = {1: "realtime", 2: "frozen", 3: "delayed", 4: "delayed-frozen"}
    data_type = _DT_NAMES.get(getattr(t, "marketDataType", None), "unknown")

    chains = ib.reqSecDefOptParams(
        q.symbol, "", q.secType, q.conId,
    )
    if not chains:
        raise RuntimeError(f"reqSecDefOptParams returned empty: {symbol}")

    chain = max(chains, key=lambda c: len(c.strikes))
    log(f"  option chain: exchange={chain.exchange}, "
        f"{len(chain.expirations)} expirations, {len(chain.strikes)} strikes")

    expirations = _pick_expirations(
        list(chain.expirations), dte_min, dte_max, max_expirations,
    )
    if not expirations:
        raise RuntimeError(
            f"No expirations within DTE [{dte_min}, {dte_max}] "
            f"(available: {sorted(chain.expirations)[:5]}...)"
        )
    log(f"  selected expirations: {expirations}")

    strikes = _pick_strikes(list(chain.strikes), underlying_price, num_strikes)
    log(f"  selected strikes: {len(strikes)} "
        f"({strikes[0]:.1f} ~ {strikes[-1]:.1f})")

    all_contracts = []
    for exp in expirations:
        for strike in strikes:
            for right in ("C", "P"):
                all_contracts.append(Option(
                    q.symbol, exp, strike, right,
                    "SMART", currency=q.currency,
                    tradingClass=chain.tradingClass,
                ))
    log(f"  built {len(all_contracts)} option contracts, fetching in batches...")

    tick_data = _batch_qualify_and_tick(ib, all_contracts)
    log(f"  got data for {len(tick_data)} contracts")

    today = date.today()
    chain_output = []
    for exp in expirations:
        exp_date = _parse_expiration(exp)
        dte = (exp_date - today).days
        calls = []
        puts = []
        for strike in strikes:
            call_key = (exp, strike, "C")
            put_key = (exp, strike, "P")
            if call_key in tick_data:
                calls.append(tick_data[call_key])
            if put_key in tick_data:
                puts.append(tick_data[put_key])
        chain_output.append({
            "expiration": exp_date.isoformat(),
            "dte": dte,
            "calls": calls,
            "puts": puts,
        })

    return {
        "symbol": symbol,
        "underlying_price": underlying_price,
        "data_type": data_type,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chain": chain_output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="IBKR Options Chain Fetcher")
    parser.add_argument("symbol", help="underlying ticker (e.g. SPY, AAPL, QQQ)")
    parser.add_argument("--strikes", type=int, default=10,
                        help="number of strikes on each side of ATM (default: 10)")
    parser.add_argument("--dte-min", type=int, default=7,
                        help="minimum days to expiration (default: 7)")
    parser.add_argument("--dte-max", type=int, default=60,
                        help="maximum days to expiration (default: 60)")
    parser.add_argument("--max-expirations", type=int, default=3,
                        help="maximum number of expirations to pick (default: 3)")
    parser.add_argument("--output", help="output file path (default stdout)")
    args = parser.parse_args()

    log(f"🔄 Fetching {args.symbol} option chain...")

    try:
        with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
            result = fetch_chain(
                ib,
                args.symbol,
                num_strikes=args.strikes,
                dte_min=args.dte_min,
                dte_max=args.dte_max,
                max_expirations=args.max_expirations,
            )
    except Exception as e:
        log(f"❌ Failed: {e}")
        return 1

    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        tmp = args.output + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json_str)
        os.rename(tmp, args.output)
        log(f"📁 Saved to {args.output}")
    else:
        print(json_str)

    total_opts = sum(len(e["calls"]) + len(e["puts"]) for e in result["chain"])
    log(f"✅ Done: {len(result['chain'])} expirations, {total_opts} contracts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
