"""
Effective cost basis calculator for wheel-strategy positions.

The IBKR broker-reported average cost (`avg_cost`) does not subtract option
premiums collected during a wheel cycle. For a trader who sells cash-secured
puts and covered calls, the effective cost basis (and thus the true breakeven)
is materially lower than what the broker shows. This script computes the
effective cost basis by:

  1. Reading current STK positions (avg_cost, shares held) via ib.positions().
  2. Pulling option fills for that underlying from the current session
     (ib.fills(), ~2 days of history).
  3. Optionally augmenting with older history from Flex Statement CSVs
     (~/.ibkr_flex/*.csv).

Premium accounting convention:
  - Selling an option (BOT side = "SLD") -> credit (premiums_collected += |price * qty * 100| - commission)
  - Buying back an option (BOT side = "BOT") -> debit (premiums_paid_back  += |price * qty * 100| + commission)

Effective cost basis = (broker_total_cost - net_premium_credit) / shares_held.

Usage:
    python cost_basis.py MU
    python cost_basis.py MU NVDA AAPL
    python cost_basis.py --portfolio-file /tmp/portfolio.json
    python cost_basis.py MU --flex-dir ~/.ibkr_flex --output /tmp/cb.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from ib_client import ib_connect, log

CLIENT_ID_OFFSET = 17


def _is_sell(side: str) -> bool:
    return (side or "").upper() in ("SLD", "SELL", "SS")


def _is_buy(side: str) -> bool:
    return (side or "").upper() in ("BOT", "BUY")


def fetch_session_option_fills(ib, symbols: set[str]) -> list[dict]:
    """Read option fills for the given symbols from the current IBKR session."""
    ib.reqExecutions()
    ib.sleep(1)
    fills = ib.fills()

    out: list[dict] = []
    for fill in fills:
        c = fill.contract
        if c.secType != "OPT":
            continue
        if c.symbol not in symbols:
            continue
        e = fill.execution
        cr = fill.commissionReport
        out.append({
            "symbol": c.symbol,
            "right": c.right,
            "strike": float(c.strike) if c.strike else None,
            "expiration": c.lastTradeDateOrContractMonth,
            "side": e.side,
            "qty": float(e.shares),
            "price": float(e.price),
            "commission": float(getattr(cr, "commission", 0.0) or 0.0),
            "trade_date": getattr(e, "time", None).strftime("%Y%m%d") if getattr(e, "time", None) else None,
            "exec_id": getattr(e, "execId", None),
            "source": "session",
        })
    return out


def _dedup_fills(session_fills: list[dict], flex_fills: list[dict]) -> list[dict]:
    """Merge session + flex fills, dropping any flex row that duplicates a
    session row. Session is preferred (more authoritative, fresher).

    Same-day partial fills at identical price are common (TWS splits a market
    order across exchanges), so the dedup key includes an occurrence index
    counted within each source. (`exec_id` is not used here because session
    emits `e.execId` like "00018037.xxx" while Flex emits a numeric
    `TradeID` — the two formats can't be compared directly.)
    """
    def _base(f: dict) -> tuple:
        return (
            f.get("symbol"),
            f.get("right"),
            round(float(f.get("strike") or 0), 2),
            f.get("expiration"),
            f.get("side"),
            round(float(f.get("qty") or 0), 4),
            round(float(f.get("price") or 0), 4),
            f.get("trade_date"),
        )

    def _keyed(fills: list[dict]) -> list[tuple]:
        seen: dict[tuple, int] = {}
        out = []
        for f in fills:
            b = _base(f)
            idx = seen.get(b, 0)
            seen[b] = idx + 1
            out.append((*b, idx))
        return out

    session_keys = set(_keyed(session_fills))
    flex_keyed = _keyed(flex_fills)
    deduped_flex = [f for f, k in zip(flex_fills, flex_keyed) if k not in session_keys]
    return session_fills + deduped_flex


def fetch_flex_option_fills(flex_dir: Path, symbols: set[str]) -> list[dict]:
    """Read option fills for the given symbols from Flex Statement CSVs."""
    if not flex_dir.exists():
        return []

    out: list[dict] = []
    for csv_path in sorted(flex_dir.glob("*.csv")):
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sec_type = (row.get("AssetClass") or row.get("SecType") or "").upper()
                    if sec_type and sec_type != "OPT":
                        continue
                    sym = (row.get("UnderlyingSymbol") or row.get("Symbol") or "").upper()
                    if not sym or sym not in symbols:
                        continue
                    right = (row.get("Put/Call") or row.get("Right") or "").upper()
                    if right not in ("P", "C"):
                        # Skip non-options rows when AssetClass column is missing
                        if not sec_type:
                            continue
                    try:
                        qty = float(row.get("Quantity") or row.get("Qty") or 0)
                        price = float(row.get("TradePrice") or row.get("Price") or 0)
                        commission = float(row.get("IBCommission") or 0)
                    except ValueError:
                        continue
                    trade_date_raw = (row.get("TradeDate") or row.get("Date/Time")
                                      or row.get("Date") or "")
                    # Flex emits YYYYMMDD, YYYY-MM-DD, or YYYYMMDD;HHMMSS — extract
                    # the leading date only.
                    m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})", trade_date_raw)
                    trade_date = (m.group(1) + m.group(2) + m.group(3)) if m else None
                    out.append({
                        "symbol": sym,
                        "right": right or None,
                        "strike": float(row["Strike"]) if row.get("Strike") else None,
                        "expiration": row.get("Expiry") or row.get("Expiration"),
                        "side": row.get("Buy/Sell") or row.get("Side") or "",
                        "qty": qty,
                        "price": price,
                        "commission": commission,
                        "trade_date": trade_date,
                        "exec_id": row.get("TradeID") or row.get("OrderID"),
                        "source": f"flex:{csv_path.name}",
                    })
        except Exception as e:
            log(f"  skip {csv_path.name}: {e}")
    return out


def compute_cost_basis(symbol: str, stk_positions: list[dict],
                       option_fills: list[dict]) -> dict:
    """Build the effective cost-basis report for a single symbol."""
    sym = symbol.upper()
    stk = next((p for p in stk_positions if p.get("symbol") == sym), None)
    shares_held = float(stk["position"]) if stk else 0.0
    broker_avg = float(stk["avg_cost"]) if stk else 0.0
    broker_total = round(shares_held * broker_avg, 2)

    sym_fills = [f for f in option_fills if f["symbol"] == sym]

    premiums_collected = 0.0
    premiums_paid_back = 0.0
    counts = {"puts_sold": 0, "puts_bought_back": 0,
              "calls_sold": 0, "calls_bought_back": 0}

    for f in sym_fills:
        notional = abs(f["price"] * f["qty"]) * 100.0  # one contract = 100 shares
        commission = abs(f["commission"])
        right = (f.get("right") or "").upper()
        if _is_sell(f["side"]):
            premiums_collected += notional - commission
            if right == "P":
                counts["puts_sold"] += 1
            elif right == "C":
                counts["calls_sold"] += 1
        elif _is_buy(f["side"]):
            premiums_paid_back += notional + commission
            if right == "P":
                counts["puts_bought_back"] += 1
            elif right == "C":
                counts["calls_bought_back"] += 1

    net_credit = premiums_collected - premiums_paid_back

    if shares_held > 0:
        effective_total = broker_total - net_credit
        effective_basis = round(effective_total / shares_held, 4)
    else:
        effective_basis = None  # only premium accumulation, no shares

    return {
        "symbol": sym,
        "shares_held": shares_held,
        "broker_avg_cost": round(broker_avg, 4) if stk else None,
        "broker_total_cost": broker_total if stk else 0.0,
        "premiums_collected": round(premiums_collected, 2),
        "premiums_paid_back": round(premiums_paid_back, 2),
        "net_premium_credit": round(net_credit, 2),
        "effective_cost_basis": effective_basis,
        "effective_breakeven": effective_basis,
        "premium_count": counts,
    }


def load_portfolio_file(path: Path) -> list[dict]:
    """Read positions from a portfolio_positions.py JSON dump."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("positions", [])


def _write_output(result: dict, output: str | None) -> None:
    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    if output:
        tmp = output + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json_str)
        os.rename(tmp, output)
        log(f"saved to {output}")
    else:
        print(json_str)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Effective cost basis (broker cost - net option premium)"
    )
    parser.add_argument("symbols", nargs="*",
                        help="One or more symbols. Omit when using --portfolio-file.")
    parser.add_argument("--portfolio-file",
                        help="JSON from portfolio_positions.py; auto-discover all STK symbols.")
    parser.add_argument("--flex-dir", default="~/.ibkr_flex",
                        help="Flex Statement CSV directory (default ~/.ibkr_flex)")
    parser.add_argument("--output", help="Output file path (default stdout)")
    args = parser.parse_args()

    flex_dir = Path(os.path.expanduser(args.flex_dir))

    if not args.symbols and not args.portfolio_file:
        log("ERROR: provide one or more SYMBOLs, or --portfolio-file")
        return 1

    # Resolve target symbols + STK positions
    stk_positions: list[dict] = []
    target_symbols: set[str] = {s.upper() for s in args.symbols}

    if args.portfolio_file:
        positions = load_portfolio_file(Path(args.portfolio_file))
        stk_positions = [p for p in positions if p.get("sec_type") == "STK"]
        if not args.symbols:
            target_symbols = {p["symbol"] for p in stk_positions}
        log(f"loaded {len(stk_positions)} STK positions from {args.portfolio_file}")

    log(f"target symbols: {sorted(target_symbols)}")

    # Pull session fills (and live STK positions if we didn't get them from file)
    session_fills: list[dict] = []
    try:
        with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
            if not args.portfolio_file:
                ib.reqPositions()
                ib.sleep(1)
                for pos in ib.positions():
                    if pos.contract.secType == "STK" and pos.contract.symbol in target_symbols:
                        stk_positions.append({
                            "symbol": pos.contract.symbol,
                            "sec_type": "STK",
                            "position": pos.position,
                            "avg_cost": pos.avgCost,
                        })
            session_fills = fetch_session_option_fills(ib, target_symbols)
            log(f"session option fills: {len(session_fills)}")
    except Exception as e:
        log(f"  warning: IBKR session unavailable: {e}")

    flex_fills = fetch_flex_option_fills(flex_dir, target_symbols)
    log(f"flex option fills: {len(flex_fills)}")

    option_fills = _dedup_fills(session_fills, flex_fills)
    n_dropped = len(session_fills) + len(flex_fills) - len(option_fills)
    if n_dropped:
        log(f"  deduped {n_dropped} flex fills already present in session")
    source_window = "session"
    if flex_fills:
        source_window += f" + flex({len(flex_fills)} rows, {n_dropped} dup)"

    reports = []
    for sym in sorted(target_symbols):
        report = compute_cost_basis(sym, stk_positions, option_fills)
        report["source_window"] = source_window
        reports.append(report)

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "flex_dir": str(flex_dir),
        "source_window": source_window,
        "symbols": reports,
    }

    _write_output(result, args.output)
    log(f"done: {len(reports)} symbol(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
