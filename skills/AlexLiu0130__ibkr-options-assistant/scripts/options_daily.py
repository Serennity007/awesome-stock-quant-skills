"""
Options daily report — after each market open, analyzes the state of current option positions and emits concrete action suggestions.

Output has three sections:
  1. Expiry warnings (DTE≤7): close vs. roll comparison
  2. IV environment for held symbols: current IV vs. 20-day historical vol — rich/cheap
  3. Concrete action suggestions: which contract, which price, max profit/loss/win-rate

Usage:
  python options_daily.py
  python options_daily.py --symbols ARM MRVL ORCL   # extra symbols to watch
  python options_daily.py --output /tmp/daily.json
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, date

from contracts import resolve
from ib_client import ib_connect, log, qualify, req_historical_safe
from options_chain import fetch_chain
from options_analyzer import compute_historical_vol, assess_iv_environment, STRATEGIES, SELECTION_MATRIX

CLIENT_ID_OFFSET = 11


# ── Portfolio reader (inlined to avoid a second connection) ─────────────

def _fetch_portfolio(ib) -> dict:
    import time
    ib.reqPositions()
    time.sleep(1)
    positions = ib.positions()

    portfolio_items = ib.portfolio()
    pnl_map = {}
    for item in portfolio_items:
        pnl_map[(item.contract.conId, item.account)] = {
            "market_price": item.marketPrice,
            "unrealized_pnl": item.unrealizedPNL,
            "average_cost": item.averageCost,
        }

    option_contracts = [p.contract for p in positions if p.contract.secType == "OPT"]
    greeks_map = {}
    if option_contracts:
        for c in option_contracts:
            ib.reqMktData(c, genericTickList="106", snapshot=False)
        ib.sleep(5)
        for c in option_contracts:
            t = ib.ticker(c)
            if t and t.modelGreeks:
                g = t.modelGreeks
                greeks_map[c.conId] = {
                    "iv": g.impliedVol,
                    "delta": g.delta,
                    "theta": g.theta,
                    "und_price": g.undPrice,
                }
        for c in option_contracts:
            ib.cancelMktData(c)

    result = []
    for pos in positions:
        c = pos.contract
        pnl = pnl_map.get((c.conId, pos.account), {})
        entry = {
            "symbol": c.symbol,
            "sec_type": c.secType,
            "position": pos.position,
            "avg_cost": pos.avgCost,
            "market_price": pnl.get("market_price"),
            "unrealized_pnl": pnl.get("unrealized_pnl"),
        }
        if c.secType == "OPT":
            exp = c.lastTradeDateOrContractMonth
            exp_date = datetime.strptime(exp, "%Y%m%d").date()
            g = greeks_map.get(c.conId)
            und_price = g["und_price"] if g else None
            if und_price is not None:
                itm = (und_price > c.strike) if c.right == "C" else (und_price < c.strike) if c.right == "P" else None
                moneyness = round(und_price - c.strike, 2)
            else:
                itm = None
                moneyness = None
            # `market_price` (above) is the OPTION's price — not the underlying.
            # Expose `option_price` explicitly and lift `und_price` to the top.
            entry["option_price"] = entry["market_price"]
            entry.update({
                "expiration": exp_date.isoformat(),
                "dte": (exp_date - date.today()).days,
                "strike": c.strike,
                "right": c.right,
                "multiplier": float(c.multiplier) if c.multiplier else 100.0,
                "und_price": und_price,
                "itm": itm,
                "moneyness": moneyness,
                "greeks": g,
            })
        result.append(entry)
    return result


# ── Expiry warning analysis ─────────────────────────────────────────────

def _expiry_warning(pos: dict, chain_data: dict) -> dict:
    dte = pos["dte"]
    strike = pos["strike"]
    right = pos["right"]
    qty = abs(pos["position"])
    mult = pos.get("multiplier", 100.0)
    is_short = pos["position"] < 0
    option_price = pos.get("option_price") or pos.get("market_price") or 0
    upnl = pos.get("unrealized_pnl") or 0
    und_price = pos.get("und_price")
    itm = pos.get("itm")

    # short: close_cost = cost to buy back (positive = cash you must pay)
    # long:  close_cost = sale proceeds (positive = cash you receive)
    close_cost = round(option_price * qty * mult, 2) if option_price else None

    roll_target = None
    for exp_group in chain_data.get("chain", []):
        if exp_group["dte"] >= 21:
            side = "calls" if right == "C" else "puts"
            candidates = [o for o in exp_group.get(side, [])
                          if abs(o["strike"] - strike) < 0.01 and o.get("bid")]
            if candidates:
                opt = candidates[0]
                # roll_net: net credit when rolling a short position (far-month bid - near-month buyback ask).
                # Positive = net premium received.
                roll_net = round((opt["bid"] - option_price) * qty * mult, 2) if is_short else None
                roll_target = {
                    "expiration": exp_group["expiration"],
                    "dte": exp_group["dte"],
                    "strike": opt["strike"],
                    "bid": opt.get("bid"),
                    "ask": opt.get("ask"),
                    "roll_net_credit": roll_net,
                }
                break

    urgency = "expires today" if dte <= 0 else f"DTE {dte} days"

    return {
        "urgency": urgency,
        "is_short": is_short,
        "option_price": option_price,
        "und_price": und_price,
        "itm": itm,
        "strike": strike,
        "right": right,
        "close_cost": close_cost,
        "unrealized_pnl": upnl,
        "roll_target": roll_target,
    }


# ── Concrete contract recommendations ───────────────────────────────────

def _recommend_contracts(symbol: str, chain_data: dict, iv_env: dict,
                         has_stock: bool) -> list[dict]:
    """Pick best contracts given the IV environment and produce concrete buy/sell suggestions."""
    bias = iv_env.get("iv_bias", "neutral")
    underlying = chain_data["underlying_price"]

    # IV high → favor selling; IV low → favor buying; neutral → favor spreads
    if bias == "high":
        strategies = (["covered_call"] if has_stock else []) + ["cash_secured_put", "bull_put_spread", "bear_call_spread"]
    elif bias == "low":
        strategies = ["long_call", "long_put", "long_straddle"]
    else:
        strategies = (["covered_call"] if has_stock else []) + ["bull_call_spread", "bear_put_spread"]

    recs = []
    for exp_group in chain_data.get("chain", []):
        if exp_group["dte"] < 14:
            continue

        side_data = {"C": exp_group.get("calls", []), "P": exp_group.get("puts", [])}

        for strat_key in strategies[:3]:
            strat = STRATEGIES.get(strat_key)
            if not strat or len(strat["legs"]) != 1:
                continue

            right = strat["legs"][0]["right"]
            action = strat["legs"][0]["action"]
            offset = strat["legs"][0].get("strike_offset", 0)

            # find candidate contracts near ATM
            all_opts = side_data[right]
            if not all_opts:
                continue
            atm = min(all_opts, key=lambda o: abs(o["strike"] - underlying))
            atm_idx = all_opts.index(atm)

            # offset is measured in strike steps
            target_idx = max(0, min(len(all_opts) - 1, atm_idx + offset))
            opt = all_opts[target_idx]

            bid = opt.get("bid")
            ask = opt.get("ask")
            delta = opt.get("delta")
            iv = opt.get("iv")
            if not bid or not ask:
                continue

            mid = round((bid + ask) / 2, 2)
            # Probability-of-profit approximation: seller = 1 - |delta|, buyer = |delta|
            if delta is not None:
                pop = round((1 - abs(delta)) * 100, 1) if action == "SELL" else round(abs(delta) * 100, 1)
            else:
                pop = None

            max_profit = round(mid * 100, 2) if action == "SELL" else None
            # Short put max loss = -(strike - premium) * 100, NOT -strike * 100.
            # (Stock can go to 0; assignment cost = strike, but you keep the premium.)
            max_loss = round(-(opt["strike"] - mid) * 100, 2) if action == "SELL" and right == "P" else (
                round(-mid * 100, 2) if action == "BUY" else None
            )

            recs.append({
                "strategy": strat["name"],
                "action": "SELL" if action == "SELL" else "BUY",
                "right": "Call" if right == "C" else "Put",
                "strike": opt["strike"],
                "expiration": exp_group["expiration"],
                "dte": exp_group["dte"],
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "iv": round(iv, 4) if iv is not None else None,
                "delta": round(delta, 3) if delta is not None else None,
                "probability_of_profit": pop,
                "max_profit_per_contract": max_profit,
                "max_loss_per_contract": max_loss,
                "description": strat["description"],
            })

        if recs:
            break  # only take the nearest suitable expiration

    # sort by probability-of-profit
    recs.sort(key=lambda r: r.get("probability_of_profit") or 0, reverse=True)
    return recs[:3]


# ── Main flow ───────────────────────────────────────────────────────────

def run_daily(ib, extra_symbols: list[str]) -> dict:
    log("  reading positions...")
    positions = _fetch_portfolio(ib)

    opt_positions = [p for p in positions if p["sec_type"] == "OPT"]
    stk_positions = {p["symbol"] for p in positions if p["sec_type"] == "STK"}

    # symbols to analyze: option underlyings + stock holdings + user-supplied extras
    symbols_to_analyze = list({p["symbol"] for p in opt_positions} | set(extra_symbols))

    warnings = []
    iv_analysis = {}
    recommendations = {}

    for symbol in symbols_to_analyze:
        log(f"  analyzing {symbol}...")
        try:
            chain = fetch_chain(ib, symbol, num_strikes=8, dte_min=7, dte_max=60, max_expirations=3)
        except Exception as e:
            log(f"    chain fetch failed: {e}")
            continue

        # IV environment
        hist_vol = compute_historical_vol(ib, symbol, days=20)
        iv_env = assess_iv_environment(chain, hist_vol)
        iv_analysis[symbol] = {
            "underlying_price": chain["underlying_price"],
            "current_iv": iv_env.get("current_iv"),
            "hist_vol_20d": hist_vol,
            "iv_to_hv_ratio": iv_env.get("iv_to_hv_ratio"),
            "assessment": iv_env.get("assessment"),
            "iv_bias": iv_env.get("iv_bias"),
        }

        # expiry warnings
        sym_opts = [p for p in opt_positions if p["symbol"] == symbol]
        for pos in sym_opts:
            if pos["dte"] <= 7:
                w = _expiry_warning(pos, chain)
                w.update({
                    "symbol": symbol,
                    "strike": pos["strike"],
                    "right": pos["right"],
                    "expiration": pos["expiration"],
                    "dte": pos["dte"],
                    "position": pos["position"],
                })
                warnings.append(w)

        # concrete contract recommendations
        has_stock = symbol in stk_positions
        recs = _recommend_contracts(symbol, chain, iv_env, has_stock)
        if recs:
            recommendations[symbol] = recs

    return {
        "date": date.today().isoformat(),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expiry_warnings": sorted(warnings, key=lambda w: w["dte"]),
        "iv_analysis": iv_analysis,
        "recommendations": recommendations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Options daily report")
    parser.add_argument("--symbols", nargs="*", default=[],
                        help="extra symbols to watch (option underlyings are auto-included)")
    parser.add_argument("--output", help="output file path (default stdout)")
    args = parser.parse_args()

    log("🔄 Generating options daily report...")

    try:
        with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
            result = run_daily(ib, args.symbols)
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

    n_warn = len(result["expiry_warnings"])
    n_rec = sum(len(v) for v in result["recommendations"].values())
    log(f"✅ Done: {n_warn} expiry warnings, {n_rec} contract recommendations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
