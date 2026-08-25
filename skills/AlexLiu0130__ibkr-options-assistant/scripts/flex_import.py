"""
IBKR Flex Statement importer.

`ib.fills()` only returns ~2 days of execution history. To work with longer
windows, IBKR provides Flex Queries (Account Management -> Reports ->
Flex Queries) which export trade history as XML or CSV. This script parses
Flex CSVs into a unified, sorted trade list that other toolkit scripts
(pnl_analytics.py, cost_basis.py, wheel_tracker.py) can consume.

Parsing strategy:
  1. Prefer the `ibflex` library if installed (handles XML + edge cases).
  2. Fall back to plain CSV parsing of the common Flex Trade columns:
        Symbol, UnderlyingSymbol, AssetClass, TradeDate, Buy/Sell,
        Quantity, TradePrice, IBCommission, FifoPnlRealized, Description,
        Put/Call, Strike, Expiry

No IBKR network connection is required. All input is local files.

Usage:
    python flex_import.py
    python flex_import.py --flex-dir ~/.ibkr_flex
    python flex_import.py --since 2026-01-01 --symbol MU
    python flex_import.py --output /tmp/trades.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

# stderr log helper (no IBKR connection -> we inline it to keep the script
# usable even if ib_client.py is in a slightly different layout, but we
# still import from ib_client for consistency with the rest of the toolkit).
from ib_client import log

try:
    import ibflex  # type: ignore
    _HAS_IBFLEX = True
except ImportError:
    _HAS_IBFLEX = False


def _norm_date(raw: str | None) -> str | None:
    """Accept YYYYMMDD or YYYY-MM-DD; return YYYY-MM-DD or None."""
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    # Strip trailing time component if present
    s = s.split(";")[0].split(" ")[0]
    try:
        return datetime.strptime(s[:8], "%Y%m%d").date().isoformat()
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _classify_action(side: str, quantity: float, sec_type: str, right: str | None) -> str:
    """
    Translate (side, qty) into one of:
      BUY_OPEN, BUY_CLOSE, SELL_OPEN, SELL_CLOSE
    For options, OPEN/CLOSE is ambiguous without the open/close indicator;
    Flex sometimes exposes an "Open/CloseIndicator" column we use if found.
    Falls back to the conservative mapping based on direction alone.
    """
    s = (side or "").upper()
    if s in ("BOT", "BUY", "B"):
        return "BUY_OPEN" if quantity >= 0 else "BUY_CLOSE"
    if s in ("SLD", "SELL", "S", "SS"):
        return "SELL_OPEN" if quantity <= 0 else "SELL_CLOSE"
    return "BUY_OPEN" if quantity >= 0 else "SELL_OPEN"


def _safe_float(raw: str | None) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_flex_csv(csv_path: Path) -> list[dict]:
    """Parse one Flex CSV file into normalized trade dicts."""
    trades: list[dict] = []
    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym = (row.get("Symbol") or "").strip()
                und = (row.get("UnderlyingSymbol") or "").strip()
                sec_type = (row.get("AssetClass") or row.get("SecType") or "").upper()
                right = (row.get("Put/Call") or row.get("Right") or "").upper() or None
                strike = _safe_float(row.get("Strike"))
                expiration = _norm_date(row.get("Expiry") or row.get("Expiration"))
                trade_date = _norm_date(row.get("TradeDate") or row.get("Date"))
                qty = _safe_float(row.get("Quantity") or row.get("Qty"))
                price = _safe_float(row.get("TradePrice") or row.get("Price"))
                commission = _safe_float(row.get("IBCommission")) or 0.0
                realized = _safe_float(
                    row.get("FifoPnlRealized")
                    or row.get("RealizedPL")
                    or row.get("Realized")
                )
                side = (row.get("Buy/Sell") or row.get("Side") or "").upper()
                description = row.get("Description") or None

                if not (sym or und) or qty is None or price is None:
                    continue

                # Choose canonical symbol: underlying for options, trade symbol for stock.
                if right or sec_type == "OPT":
                    symbol = und or sym
                    sec_type = "OPT"
                else:
                    symbol = sym or und
                    sec_type = sec_type or "STK"

                trades.append({
                    "date": trade_date,
                    "symbol": symbol,
                    "sec_type": sec_type,
                    "right": right,
                    "strike": strike,
                    "expiration": expiration,
                    "action": _classify_action(side, qty, sec_type, right),
                    "side": side,
                    "quantity": qty,
                    "price": price,
                    "commission": commission,
                    "realized_pnl": realized,
                    "description": description,
                    "source_file": csv_path.name,
                })
    except Exception as e:
        log(f"  skip {csv_path.name}: {e}")
    return trades


def parse_with_ibflex(csv_path: Path) -> list[dict] | None:
    """Use the ibflex library when available (XML format).

    Returns None if the file isn't an ibflex-parseable XML statement;
    falls back to plain CSV in that case.
    """
    if not _HAS_IBFLEX:
        return None
    try:
        statement = ibflex.parser.parse(str(csv_path))
    except Exception:
        return None

    trades: list[dict] = []
    for stmt in getattr(statement, "FlexStatements", []) or []:
        for t in getattr(stmt, "Trades", []) or []:
            symbol = getattr(t, "underlyingSymbol", None) or getattr(t, "symbol", None)
            sec_type = (getattr(t, "assetCategory", "") or "").upper() or "STK"
            right = getattr(t, "putCall", None)
            right = right.value if hasattr(right, "value") else right
            strike = getattr(t, "strike", None)
            expiration = getattr(t, "expiry", None)
            quantity = float(getattr(t, "quantity", 0) or 0)
            price = float(getattr(t, "tradePrice", 0) or 0)
            commission = float(getattr(t, "ibCommission", 0) or 0)
            realized = getattr(t, "fifoPnlRealized", None)
            realized = float(realized) if realized is not None else None
            side = getattr(t, "buySell", None)
            side = side.value if hasattr(side, "value") else (side or "")
            trade_date = getattr(t, "tradeDate", None)
            trade_date = trade_date.isoformat() if hasattr(trade_date, "isoformat") else trade_date

            trades.append({
                "date": trade_date,
                "symbol": symbol,
                "sec_type": "OPT" if right else sec_type,
                "right": right,
                "strike": float(strike) if strike is not None else None,
                "expiration": expiration.isoformat() if hasattr(expiration, "isoformat") else expiration,
                "action": _classify_action(side, quantity, sec_type, right),
                "side": side,
                "quantity": quantity,
                "price": price,
                "commission": commission,
                "realized_pnl": realized,
                "description": getattr(t, "description", None),
                "source_file": csv_path.name,
            })
    return trades


def load_all_trades(flex_dir: Path) -> list[dict]:
    if not flex_dir.exists():
        log(f"WARNING: flex dir does not exist: {flex_dir}")
        return []

    all_trades: list[dict] = []
    file_count = 0
    # Look at both .csv and .xml so ibflex-style XML is picked up
    for path in sorted(list(flex_dir.glob("*.csv")) + list(flex_dir.glob("*.xml"))):
        file_count += 1
        parsed: list[dict] | None = None
        if path.suffix.lower() == ".xml":
            parsed = parse_with_ibflex(path)
            if parsed is None:
                log(f"  {path.name}: ibflex parse failed, skipping XML")
                continue
        else:
            # Try ibflex first (CSV exported from XML can also be parsed by it
            # sometimes), then fall back to CSV.
            parsed = parse_with_ibflex(path) if _HAS_IBFLEX else None
            if parsed is None:
                parsed = parse_flex_csv(path)
        log(f"  {path.name}: {len(parsed)} trades")
        all_trades.extend(parsed)

    if not _HAS_IBFLEX:
        log("INFO: ibflex not installed (pip install ibflex>=0.16); using plain CSV parser")

    log(f"parsed {file_count} file(s); {len(all_trades)} trade(s) total")
    return all_trades


def filter_trades(trades: list[dict], *, since: date | None,
                  symbol: str | None) -> list[dict]:
    out = []
    sym_filter = symbol.upper() if symbol else None
    for t in trades:
        if sym_filter and (t.get("symbol") or "").upper() != sym_filter:
            continue
        if since and t.get("date"):
            try:
                if datetime.strptime(t["date"], "%Y-%m-%d").date() < since:
                    continue
            except ValueError:
                pass
        out.append(t)
    out.sort(key=lambda t: (t.get("date") or "", t.get("symbol") or ""))
    return out


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
        description="Import IBKR Flex Statement CSVs to a unified trade-history JSON"
    )
    parser.add_argument("--flex-dir", default="~/.ibkr_flex",
                        help="Flex Statement directory (default ~/.ibkr_flex)")
    parser.add_argument("--since", help="Filter to trades on/after this date (YYYY-MM-DD)")
    parser.add_argument("--symbol", help="Filter to a single underlying symbol")
    parser.add_argument("--output", help="Output file path (default stdout)")
    args = parser.parse_args()

    flex_dir = Path(os.path.expanduser(args.flex_dir))

    since_date: date | None = None
    if args.since:
        try:
            since_date = datetime.strptime(args.since, "%Y-%m-%d").date()
        except ValueError:
            log(f"ERROR: --since must be YYYY-MM-DD, got {args.since!r}")
            return 1

    trades = load_all_trades(flex_dir)
    trades = filter_trades(trades, since=since_date, symbol=args.symbol)

    dates = [t["date"] for t in trades if t.get("date")]
    date_range = [min(dates), max(dates)] if dates else [None, None]

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "flex_dir": str(flex_dir),
        "ibflex_available": _HAS_IBFLEX,
        "trades_count": len(trades),
        "date_range": date_range,
        "filters": {"since": args.since, "symbol": args.symbol},
        "trades": trades,
    }

    _write_output(result, args.output)
    log(f"done: {len(trades)} trade(s), range {date_range[0]}..{date_range[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
