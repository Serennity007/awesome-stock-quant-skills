"""
Account positions reader — lists all positions, with Greeks on option legs, and computes portfolio-level net Greeks.

Output JSON: positions[...], portfolio_greeks{net_delta, net_gamma, net_vega, net_theta}

Usage:
  python portfolio_positions.py
  python portfolio_positions.py --output /tmp/portfolio.json
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime

from ib_client import ib_connect, log

CLIENT_ID_OFFSET = 9
BATCH_SIZE = 50
BATCH_SLEEP = 2.0


def _safe(val, ndigits=4):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return round(val, ndigits)


def fetch_positions(ib) -> dict:
    ib.reqPositions()
    time.sleep(1)
    positions = ib.positions()
    log(f"  {len(positions)} positions total")

    portfolio_items = ib.portfolio()
    pnl_map = {}
    for item in portfolio_items:
        key = (item.contract.conId, item.account)
        pnl_map[key] = {
            "market_price": _safe(item.marketPrice, 2),
            "market_value": _safe(item.marketValue, 2),
            "average_cost": _safe(item.averageCost, 4),
            "unrealized_pnl": _safe(item.unrealizedPNL, 2),
            "realized_pnl": _safe(item.realizedPNL, 2),
        }

    option_contracts = [
        p.contract for p in positions if p.contract.secType == "OPT"
    ]

    greeks_map = {}
    if option_contracts:
        log(f"  fetching Greeks for {len(option_contracts)} option contracts...")
        for i in range(0, len(option_contracts), BATCH_SIZE):
            batch = option_contracts[i:i + BATCH_SIZE]
            qualified = ib.qualifyContracts(*batch)
            valid = [c for c in qualified if c is not None and getattr(c, 'conId', 0) > 0]
            if valid:
                tickers = ib.reqTickers(*valid)
                ib.sleep(2)
                for ticker in tickers:
                    g = ticker.modelGreeks
                    if g:
                        greeks_map[ticker.contract.conId] = {
                            "iv": _safe(g.impliedVol),
                            "delta": _safe(g.delta),
                            "gamma": _safe(g.gamma, 6),
                            "vega": _safe(g.vega),
                            "theta": _safe(g.theta),
                            "und_price": _safe(g.undPrice, 2),
                        }
            if i + BATCH_SIZE < len(option_contracts):
                time.sleep(BATCH_SLEEP)

    net_delta = 0.0
    net_gamma = 0.0
    net_vega = 0.0
    net_theta = 0.0

    result_positions = []
    for pos in positions:
        c = pos.contract
        qty = pos.position
        pnl_info = pnl_map.get((c.conId, pos.account), {})

        entry = {
            "symbol": c.symbol,
            "sec_type": c.secType,
            "con_id": c.conId,
            "position": qty,
            "avg_cost": round(pos.avgCost, 4),
            "account": pos.account,
            **pnl_info,
        }

        if c.secType == "OPT":
            entry["expiration"] = c.lastTradeDateOrContractMonth
            entry["strike"] = c.strike
            entry["right"] = c.right
            multiplier = float(c.multiplier) if c.multiplier else 100.0
            entry["multiplier"] = multiplier
            # On OPT entries, `market_price` is the OPTION's mid/last price (NOT the
            # underlying spot). We expose it explicitly as `option_price` to remove
            # any ambiguity, and lift `und_price` to the top level so ITM/OTM
            # judgement always uses the right two numbers.
            entry["option_price"] = entry.get("market_price")

            g = greeks_map.get(c.conId)
            und_price = g["und_price"] if g else None
            entry["und_price"] = und_price
            if und_price is not None:
                if c.right == "C":
                    entry["itm"] = und_price > c.strike
                elif c.right == "P":
                    entry["itm"] = und_price < c.strike
                else:
                    entry["itm"] = None
                # signed distance: positive = call-side of strike, negative = put-side
                entry["moneyness"] = round(und_price - c.strike, 2)
            else:
                entry["itm"] = None
                entry["moneyness"] = None

            if g:
                entry["greeks"] = g
                pos_delta = (g["delta"] or 0) * qty * multiplier
                pos_gamma = (g["gamma"] or 0) * qty * multiplier
                pos_vega = (g["vega"] or 0) * qty * multiplier
                pos_theta = (g["theta"] or 0) * qty * multiplier
                entry["position_greeks"] = {
                    "delta": round(pos_delta, 2),
                    "gamma": round(pos_gamma, 4),
                    "vega": round(pos_vega, 2),
                    "theta": round(pos_theta, 2),
                }
                net_delta += pos_delta
                net_gamma += pos_gamma
                net_vega += pos_vega
                net_theta += pos_theta

        elif c.secType == "STK":
            net_delta += qty

        result_positions.append(entry)

    return {
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions": result_positions,
        "portfolio_greeks": {
            "net_delta": round(net_delta, 2),
            "net_gamma": round(net_gamma, 4),
            "net_vega": round(net_vega, 2),
            "net_theta": round(net_theta, 2),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="IBKR Portfolio Positions Reader")
    parser.add_argument("--output", help="output file path (default stdout)")
    args = parser.parse_args()

    log("🔄 Reading account positions...")

    try:
        with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
            result = fetch_positions(ib)
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

    n_opt = sum(1 for p in result["positions"] if p["sec_type"] == "OPT")
    n_stk = sum(1 for p in result["positions"] if p["sec_type"] == "STK")
    log(f"✅ Done: {n_stk} stocks + {n_opt} options, "
        f"net Δ={result['portfolio_greeks']['net_delta']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
