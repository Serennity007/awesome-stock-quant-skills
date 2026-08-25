"""
Risk simulator — overlays a proposed trade on the current portfolio and shows the change in portfolio Greeks.

Input: --add "SYMBOL STRIKE EXPIRY RIGHT ACTION QTY" (repeatable)
Example: --add "AAPL 200 2026-06-26 P SELL 2"

Warning rules:
  - |vega| doubles
  - net delta changes sign
  - any single symbol's |delta| exceeds 30% of total |delta|

Usage:
  python risk_simulator.py --add "AAPL 200 2026-06-26 P SELL 2"
  python risk_simulator.py --add "TSLA 300 2026-07-17 C BUY 1" --add "..." --output /tmp/sim.json
"""

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime

from ib_async import Option

from contracts import resolve
from ib_client import ib_connect, log, qualify
from portfolio_positions import fetch_positions

CLIENT_ID_OFFSET = 13


def _parse_leg(spec: str) -> dict:
    parts = spec.split()
    if len(parts) != 6:
        raise ValueError(
            f'--add requires 6 fields "SYMBOL STRIKE EXPIRY RIGHT ACTION QTY"; got: {spec!r}'
        )
    symbol, strike_s, expiry, right, action, qty_s = parts
    right = right.upper()
    action = action.upper()
    if right not in ("C", "P"):
        raise ValueError(f"RIGHT must be C or P; got {right!r}")
    if action not in ("BUY", "SELL"):
        raise ValueError(f"ACTION must be BUY or SELL; got {action!r}")
    # accept either 2026-06-26 or 20260626
    expiry_compact = expiry.replace("-", "")
    return {
        "symbol": symbol.upper(),
        "strike": float(strike_s),
        "expiration": expiry_compact,
        "right": right,
        "action": action,
        "qty": int(qty_s),
    }


def _signed_qty(leg: dict) -> int:
    return leg["qty"] if leg["action"] == "BUY" else -leg["qty"]


def _safe(val, ndigits=4):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return round(val, ndigits)


def fetch_leg_greeks(ib, leg: dict) -> dict:
    """Qualify the proposed leg and reqMktData to retrieve Greeks."""
    und = resolve(leg["symbol"])
    und_q = qualify(ib, und)

    opt = Option(
        und_q.symbol, leg["expiration"], leg["strike"], leg["right"],
        "SMART", currency=und_q.currency,
    )
    opt_q = qualify(ib, opt)

    ib.reqMktData(opt_q, genericTickList="106", snapshot=False)
    deadline = time.monotonic() + 10
    g = None
    while time.monotonic() < deadline:
        ib.sleep(1)
        t = ib.ticker(opt_q)
        if t and t.modelGreeks and t.modelGreeks.delta is not None:
            g = t.modelGreeks
            break
    ib.cancelMktData(opt_q)

    if g is None:
        return {"delta": None, "gamma": None, "vega": None, "theta": None, "iv": None}
    return {
        "delta": _safe(g.delta),
        "gamma": _safe(g.gamma, 6),
        "vega": _safe(g.vega),
        "theta": _safe(g.theta),
        "iv": _safe(g.impliedVol),
        "und_price": _safe(g.undPrice, 2),
    }


def leg_position_greeks(leg: dict, greeks: dict) -> dict:
    """Per-contract Greeks × quantity × contract multiplier (100)."""
    mult = 100.0
    qty = _signed_qty(leg)
    return {
        "delta": round((greeks["delta"] or 0) * qty * mult, 2),
        "gamma": round((greeks["gamma"] or 0) * qty * mult, 4),
        "vega": round((greeks["vega"] or 0) * qty * mult, 2),
        "theta": round((greeks["theta"] or 0) * qty * mult, 2),
    }


def detect_warnings(current: dict, simulated: dict,
                    per_symbol_delta: dict) -> list[str]:
    warnings = []

    cur_vega = abs(current["net_vega"] or 0)
    sim_vega = abs(simulated["net_vega"] or 0)
    if cur_vega > 0 and sim_vega >= 2 * cur_vega:
        warnings.append(
            f"vega doubled: {round(current['net_vega'], 2)} → {round(simulated['net_vega'], 2)}"
        )

    cur_delta = current["net_delta"] or 0
    sim_delta = simulated["net_delta"] or 0
    if cur_delta != 0 and (cur_delta * sim_delta < 0):
        warnings.append(
            f"delta sign flipped: {round(cur_delta, 2)} → {round(sim_delta, 2)}"
        )

    total_abs = sum(abs(v) for v in per_symbol_delta.values()) or 1
    for sym, d in per_symbol_delta.items():
        share = abs(d) / total_abs
        if share > 0.3 and total_abs > 10:
            warnings.append(
                f"{sym} concentration {round(share * 100, 1)}% (|delta|={round(abs(d), 1)})"
            )

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Portfolio Greeks risk simulator")
    parser.add_argument("--add", action="append", default=[],
                        help='proposed leg, repeatable: "SYMBOL STRIKE EXPIRY RIGHT ACTION QTY"')
    parser.add_argument("--output", help="output file path (default stdout)")
    args = parser.parse_args()

    if not args.add:
        log("❌ At least one --add is required")
        return 1

    try:
        legs = [_parse_leg(s) for s in args.add]
    except ValueError as e:
        log(f"❌ {e}")
        return 1

    log(f"🔄 Simulating {len(legs)} leg(s) ...")

    try:
        with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
            portfolio = fetch_positions(ib)
            current_greeks = portfolio["portfolio_greeks"]

            # current per-symbol delta contribution
            per_sym_delta: dict[str, float] = defaultdict(float)
            for p in portfolio["positions"]:
                if p.get("sec_type") == "OPT" and p.get("position_greeks"):
                    per_sym_delta[p["symbol"]] += p["position_greeks"]["delta"]
                elif p.get("sec_type") == "STK":
                    per_sym_delta[p["symbol"]] += p["position"]

            proposed = []
            for leg in legs:
                log(f"  → {leg['symbol']} {leg['strike']} {leg['expiration']} "
                    f"{leg['right']} {leg['action']} x{leg['qty']}")
                g = fetch_leg_greeks(ib, leg)
                pg = leg_position_greeks(leg, g)
                proposed.append({**leg, "per_contract_greeks": g, "position_greeks": pg})
                per_sym_delta[leg["symbol"]] += pg["delta"]
    except Exception as e:
        log(f"❌ Failed: {e}")
        return 1

    sim_delta = (current_greeks["net_delta"] or 0) + sum(p["position_greeks"]["delta"] for p in proposed)
    sim_gamma = (current_greeks["net_gamma"] or 0) + sum(p["position_greeks"]["gamma"] for p in proposed)
    sim_vega = (current_greeks["net_vega"] or 0) + sum(p["position_greeks"]["vega"] for p in proposed)
    sim_theta = (current_greeks["net_theta"] or 0) + sum(p["position_greeks"]["theta"] for p in proposed)

    simulated_greeks = {
        "net_delta": round(sim_delta, 2),
        "net_gamma": round(sim_gamma, 4),
        "net_vega": round(sim_vega, 2),
        "net_theta": round(sim_theta, 2),
    }

    warnings = detect_warnings(current_greeks, simulated_greeks, per_sym_delta)

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_greeks": current_greeks,
        "proposed_legs": proposed,
        "simulated_greeks": simulated_greeks,
        "delta_change": round(sim_delta - (current_greeks["net_delta"] or 0), 2),
        "vega_change": round(sim_vega - (current_greeks["net_vega"] or 0), 2),
        "warnings": warnings,
    }

    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        tmp = args.output + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json_str)
        os.rename(tmp, args.output)
        log(f"📁 Saved to {args.output}")
    else:
        print(json_str)

    log(f"✅ Done: Δ {current_greeks['net_delta']} → {simulated_greeks['net_delta']}, "
        f"{len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
