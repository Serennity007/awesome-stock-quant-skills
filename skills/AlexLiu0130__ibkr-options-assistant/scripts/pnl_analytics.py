"""
Realized P&L analytics — aggregates the current session's fills, optionally combined with Flex Statement CSVs.

Data sources:
  1. ib.reqExecutions() + ib.fills() — current session fills (IBKR limit ~2 days)
  2. ~/.ibkr_flex/*.csv — Flex Statements the user exported from Account Management (optional)

Aggregation dimensions: symbol / direction (long|short) / right (call|put)
Statistics: win rate, average win/loss, total realized P&L, best/worst single trade

Usage:
  python pnl_analytics.py
  python pnl_analytics.py --by right
  python pnl_analytics.py --days 60 --flex-dir ~/.ibkr_flex --output /tmp/pnl.json
"""

import argparse
import csv
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path

from ib_client import ib_connect, log

CLIENT_ID_OFFSET = 12


def _direction(side: str, qty: float) -> str:
    """Infer direction from side (BOT/SLD)."""
    s = (side or "").upper()
    if s in ("BOT", "BUY"):
        return "long"
    if s in ("SLD", "SELL", "SS"):
        return "short"
    return "long" if qty > 0 else "short"


def _trade_key(group_by: str, trade: dict) -> str:
    if group_by == "symbol":
        return trade["symbol"]
    if group_by == "right":
        return trade.get("right") or trade.get("sec_type") or "STK"
    if group_by == "expiration":
        return trade.get("expiration") or "n/a"
    return trade["symbol"]


def fetch_session_trades(ib, since_date: date) -> list[dict]:
    """Pull fills from the current IB Gateway session."""
    ib.reqExecutions()
    ib.sleep(1)
    fills = ib.fills()
    log(f"  IBKR session fills: {len(fills)}")

    trades = []
    for fill in fills:
        c = fill.contract
        e = fill.execution
        cr = fill.commissionReport

        try:
            dt = datetime.strptime(e.time[:8], "%Y%m%d").date() if e.time else None
        except Exception:
            dt = None
        if dt and dt < since_date:
            continue

        realized = getattr(cr, "realizedPNL", None)
        if realized is None or (isinstance(realized, float) and realized != realized):
            realized = 0.0
        # IBKR sometimes returns very-large sentinel; treat as 0
        if abs(realized) > 1e15:
            realized = 0.0

        trades.append({
            "symbol": c.symbol,
            "sec_type": c.secType,
            "right": getattr(c, "right", None) or None,
            "strike": getattr(c, "strike", None) or None,
            "expiration": getattr(c, "lastTradeDateOrContractMonth", None) or None,
            "side": e.side,
            "direction": _direction(e.side, e.shares),
            "shares": e.shares,
            "price": e.price,
            "commission": getattr(cr, "commission", 0.0) or 0.0,
            "realized_pnl": float(realized),
            "date": dt.isoformat() if dt else None,
            "source": "session",
        })
    return trades


def fetch_flex_trades(flex_dir: Path, since_date: date) -> list[dict]:
    """Read fills from ~/.ibkr_flex/*.csv. Flex field names vary by template; be tolerant."""
    if not flex_dir.exists():
        return []

    trades = []
    for csv_path in sorted(flex_dir.glob("*.csv")):
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sym = row.get("Symbol") or row.get("UnderlyingSymbol")
                    if not sym:
                        continue
                    sec_type = row.get("AssetClass") or row.get("SecType") or "STK"
                    realized = row.get("FifoPnlRealized") or row.get("RealizedPL") or row.get("Realized") or "0"
                    qty_raw = row.get("Quantity") or row.get("Qty") or "0"
                    price_raw = row.get("TradePrice") or row.get("Price") or "0"
                    side = row.get("Buy/Sell") or row.get("Side") or ""
                    dt_raw = row.get("TradeDate") or row.get("Date") or ""
                    try:
                        dt = datetime.strptime(dt_raw[:8], "%Y%m%d").date()
                    except Exception:
                        try:
                            dt = datetime.strptime(dt_raw, "%Y-%m-%d").date()
                        except Exception:
                            dt = None
                    if dt and dt < since_date:
                        continue

                    try:
                        qty = float(qty_raw)
                        price = float(price_raw)
                        realized_f = float(realized) if realized else 0.0
                    except ValueError:
                        continue

                    trades.append({
                        "symbol": sym,
                        "sec_type": sec_type,
                        "right": row.get("Put/Call") or row.get("Right") or None,
                        "strike": float(row["Strike"]) if row.get("Strike") else None,
                        "expiration": row.get("Expiry") or row.get("Expiration") or None,
                        "side": side,
                        "direction": _direction(side, qty),
                        "shares": qty,
                        "price": price,
                        "commission": float(row.get("IBCommission") or 0),
                        "realized_pnl": realized_f,
                        "date": dt.isoformat() if dt else None,
                        "source": f"flex:{csv_path.name}",
                    })
        except Exception as e:
            log(f"  skipped {csv_path.name}: {e}")
    log(f"  Flex files: {len(trades)} trades")
    return trades


def _dedup_trades(session_trades: list[dict], flex_trades: list[dict]) -> list[dict]:
    """Drop flex trades that duplicate session trades. Session is preferred.

    Same-day partial fills at identical price are common (TWS splits a market
    order across exchanges), so the dedup key includes an occurrence index
    counted within each source. That way 3 session fills + 3 flex copies of
    the same partial-fill set match 1:1 without collapsing the legitimate
    multi-fill into one.
    """
    def _key(t: dict, idx: int) -> tuple:
        return (
            t.get("symbol"),
            t.get("sec_type"),
            t.get("right"),
            round(float(t.get("strike") or 0), 2),
            t.get("expiration"),
            t.get("side"),
            round(float(t.get("shares") or 0), 4),
            round(float(t.get("price") or 0), 4),
            t.get("date"),
            idx,
        )

    def _keyed(trades: list[dict]) -> list[tuple]:
        seen: dict[tuple, int] = {}
        out = []
        for t in trades:
            base = (
                t.get("symbol"), t.get("sec_type"), t.get("right"),
                round(float(t.get("strike") or 0), 2), t.get("expiration"),
                t.get("side"),
                round(float(t.get("shares") or 0), 4),
                round(float(t.get("price") or 0), 4),
                t.get("date"),
            )
            idx = seen.get(base, 0)
            seen[base] = idx + 1
            out.append(_key(t, idx))
        return out

    session_keys = set(_keyed(session_trades))
    flex_keyed = _keyed(flex_trades)
    deduped_flex = [t for t, k in zip(flex_trades, flex_keyed) if k not in session_keys]
    return session_trades + deduped_flex


def aggregate(trades: list[dict], group_by: str) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        groups[_trade_key(group_by, t)].append(t)

    result = {}
    for key, items in groups.items():
        realized = [t["realized_pnl"] for t in items if t["realized_pnl"]]
        wins = [p for p in realized if p > 0]
        losses = [p for p in realized if p < 0]
        result[key] = {
            "trades": len(items),
            "closed_trades": len(realized),
            "total_realized_pnl": round(sum(realized), 2),
            "win_rate": round(len(wins) / len(realized), 3) if realized else None,
            "avg_gain": round(sum(wins) / len(wins), 2) if wins else None,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else None,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Realized P&L analytics")
    parser.add_argument("--days", type=int, default=30, help="lookback days (default 30)")
    parser.add_argument("--by", choices=["symbol", "right", "expiration"],
                        default="symbol", help="aggregation dimension (default symbol)")
    parser.add_argument("--flex-dir", default="~/.ibkr_flex",
                        help="Flex Statement CSV directory (default ~/.ibkr_flex)")
    parser.add_argument("--output", help="output file path (default stdout)")
    args = parser.parse_args()

    since_date = date.today() - timedelta(days=args.days)
    flex_dir = Path(os.path.expanduser(args.flex_dir))

    log(f"🔄 PnL analytics: since {since_date.isoformat()} ...")

    session_trades: list[dict] = []
    try:
        with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
            session_trades = fetch_session_trades(ib, since_date)
    except Exception as e:
        log(f"  ⚠️  Session fills fetch failed: {e}")

    flex_trades = fetch_flex_trades(flex_dir, since_date)

    trades = _dedup_trades(session_trades, flex_trades)
    n_dropped = len(session_trades) + len(flex_trades) - len(trades)
    if n_dropped:
        log(f"  deduped {n_dropped} flex trades already present in session")

    if not trades:
        log("  ⚠️  No fills available (empty session and no Flex files)")

    realized_only = [t["realized_pnl"] for t in trades if t["realized_pnl"]]
    best = max(trades, key=lambda t: t["realized_pnl"]) if realized_only else None
    worst = min(trades, key=lambda t: t["realized_pnl"]) if realized_only else None
    wins = [p for p in realized_only if p > 0]

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_window": {
            "since": since_date.isoformat(),
            "days": args.days,
            "session_trades": sum(1 for t in trades if t["source"] == "session"),
            "flex_trades": sum(1 for t in trades if t["source"].startswith("flex")),
        },
        "total_trades": len(trades),
        "total_realized_pnl": round(sum(realized_only), 2),
        "win_rate": round(len(wins) / len(realized_only), 3) if realized_only else None,
        "group_by": args.by,
        "by_group": aggregate(trades, args.by),
        "best_trade": best,
        "worst_trade": worst,
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

    log(f"✅ Done: {len(trades)} trades, total PnL={result['total_realized_pnl']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
