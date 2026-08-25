"""
Wheel-strategy tracker — maintains ~/.ibkr_wheel_journal.json and reports cumulative premium and annualized yield.

Sub-commands:
  add-entry SYMBOL STRIKE EXPIRATION PREMIUM   record a new short-put entry
  summary                                       read positions + journal, group by symbol

Stage definitions:
  short_put     short put open, not yet assigned
  assigned      holds the stock, waiting to write a covered call
  covered_call  short call written against the stock (covered)
  closed        no current positions; cycle ended (called away, expired
                worthless, or bought back — can't tell which from positions alone)

Usage:
  python wheel_tracker.py add-entry AAPL 200 2026-06-26 3.50
  python wheel_tracker.py summary
  python wheel_tracker.py summary --output /tmp/wheel.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

from ib_client import ib_connect, log
from portfolio_positions import fetch_positions

CLIENT_ID_OFFSET = 15
JOURNAL_PATH = Path(os.path.expanduser("~/.ibkr_wheel_journal.json"))


def _load_journal() -> list[dict]:
    if not JOURNAL_PATH.exists():
        JOURNAL_PATH.write_text("[]", encoding="utf-8")
        return []
    try:
        with open(JOURNAL_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_journal(entries: list[dict]) -> None:
    tmp = str(JOURNAL_PATH) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    os.rename(tmp, JOURNAL_PATH)


def add_entry(symbol: str, strike: float, expiration: str, premium: float) -> dict:
    entries = _load_journal()
    entry = {
        "symbol": symbol.upper(),
        "action": "sell_put",
        "strike": float(strike),
        "expiration": expiration,
        "premium": float(premium),
        "date": date.today().isoformat(),
        "status": "open",
    }
    entries.append(entry)
    _save_journal(entries)
    return entry


def _current_stage(symbol: str, positions: list[dict]) -> str:
    """Infer wheel stage from IBKR positions."""
    sym_pos = [p for p in positions if p.get("symbol") == symbol]
    short_puts = [p for p in sym_pos if p.get("sec_type") == "OPT"
                  and p.get("right") == "P" and (p.get("position") or 0) < 0]
    short_calls = [p for p in sym_pos if p.get("sec_type") == "OPT"
                   and p.get("right") == "C" and (p.get("position") or 0) < 0]
    stock = [p for p in sym_pos if p.get("sec_type") == "STK"
             and (p.get("position") or 0) > 0]

    if short_calls and stock:
        return "covered_call"
    if stock:
        return "assigned"
    if short_puts:
        return "short_put"
    # No positions but journal exists → cycle closed. Can't reliably tell
    # whether the underlying was called away vs. the put expired worthless
    # vs. the put was bought back without seeing the closing fill, so use
    # a neutral label.
    return "closed"


def _annualized_return(total_premium: float, total_capital: float,
                       first_date: date) -> float | None:
    if total_capital <= 0:
        return None
    days = max((date.today() - first_date).days, 1)
    period_return = total_premium / total_capital
    annualized = period_return * (365.0 / days)
    return round(annualized * 100, 2)


def summary(ib) -> dict:
    entries = _load_journal()
    portfolio = fetch_positions(ib)
    positions = portfolio["positions"]

    by_sym: dict[str, list[dict]] = {}
    for e in entries:
        by_sym.setdefault(e["symbol"], []).append(e)

    # also include symbols that appear in positions but have no journal entry
    sym_with_pos = {p["symbol"] for p in positions
                    if p.get("sec_type") in ("OPT", "STK")}
    for s in sym_with_pos:
        by_sym.setdefault(s, [])

    wheels = []
    for sym, sym_entries in sorted(by_sym.items()):
        total_premium = sum(e.get("premium", 0) * 100 for e in sym_entries)
        if sym_entries:
            try:
                first_date = min(
                    datetime.strptime(e["date"], "%Y-%m-%d").date() for e in sym_entries
                )
                # Capital reflects the current open leg (rolls reuse capital,
                # they don't multiply it). Use the latest entry's strike × 100.
                latest_entry = max(
                    sym_entries,
                    key=lambda e: datetime.strptime(e["date"], "%Y-%m-%d").date(),
                )
                total_capital = latest_entry["strike"] * 100
                ann_ret = _annualized_return(total_premium, total_capital, first_date)
            except Exception:
                ann_ret = None
        else:
            ann_ret = None

        wheels.append({
            "symbol": sym,
            "total_premium": round(total_premium, 2),
            "annualized_return_pct": ann_ret,
            "current_stage": _current_stage(sym, positions),
            "entries_count": len(sym_entries),
        })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "journal_path": str(JOURNAL_PATH),
        "wheels": wheels,
    }


def _write_output(result: dict, output: str | None) -> None:
    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    if output:
        tmp = output + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json_str)
        os.rename(tmp, output)
        log(f"📁 Saved to {output}")
    else:
        print(json_str)


def main() -> int:
    parser = argparse.ArgumentParser(description="Wheel-strategy tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add-entry", help="record a new short put")
    p_add.add_argument("symbol")
    p_add.add_argument("strike", type=float)
    p_add.add_argument("expiration", help="YYYY-MM-DD or YYYYMMDD")
    p_add.add_argument("premium", type=float)
    p_add.add_argument("--output", help="output file path (default stdout)")

    p_sum = sub.add_parser("summary", help="summarize current wheels")
    p_sum.add_argument("--output", help="output file path (default stdout)")

    args = parser.parse_args()

    if args.cmd == "add-entry":
        entry = add_entry(args.symbol, args.strike, args.expiration, args.premium)
        result = {"added": entry, "journal_path": str(JOURNAL_PATH)}
        _write_output(result, args.output)
        log(f"✅ Recorded {entry['symbol']} short put @ {entry['strike']}")
        return 0

    if args.cmd == "summary":
        log("🔄 Wheel summary ...")
        try:
            with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
                result = summary(ib)
        except Exception as e:
            log(f"❌ Failed: {e}")
            return 1
        _write_output(result, args.output)
        log(f"✅ Done: {len(result['wheels'])} wheel(s)")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
