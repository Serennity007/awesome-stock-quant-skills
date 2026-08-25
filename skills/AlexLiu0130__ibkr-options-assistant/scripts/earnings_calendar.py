"""
Earnings calendar lookup — fetches the next earnings date for given symbols, optionally merging with portfolio data to flag at-risk option positions.

Data sources (by priority):
  - Nasdaq /api/calendar/earnings (public, no API key, queried by date)
  - Finnhub /calendar/earnings (fallback, if FINNHUB_API_KEY is set)

Usage:
  python earnings_calendar.py AAPL MSFT NVDA
  python earnings_calendar.py AAPL --days 14
  python earnings_calendar.py --portfolio-file /tmp/portfolio.json --output /tmp/earn.json
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _parse_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.utcfromtimestamp(val).date()
        except Exception:
            return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def fetch_nasdaq_range(days: int) -> dict[str, date]:
    """Fetch all earnings in the next N days; returns {symbol: earnings_date}."""
    today = date.today()
    result: dict[str, date] = {}
    for offset in range(days + 1):
        d = today + timedelta(days=offset)
        url = f"https://api.nasdaq.com/api/calendar/earnings?date={d.isoformat()}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        except Exception as e:
            log(f"  Nasdaq {d}: {e}")
            continue
        rows = (data.get("data") or {}).get("rows") or []
        for row in rows:
            sym = (row.get("symbol") or "").strip().upper()
            if sym and sym not in result:
                result[sym] = d
    return result


def fetch_finnhub_one(symbol: str, days: int) -> dict | None:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None
    today = date.today()
    cutoff = today + timedelta(days=days)
    params = urllib.parse.urlencode({
        "symbol": symbol,
        "from": today.isoformat(),
        "to": cutoff.isoformat(),
        "token": api_key,
    })
    url = f"https://finnhub.io/api/v1/calendar/earnings?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        log(f"  Finnhub {symbol}: {e}")
        return None

    items = data.get("earningsCalendar", [])
    if not items:
        return None
    items.sort(key=lambda i: i.get("date", ""))
    item = items[0]
    edate = _parse_date(item.get("date"))
    if not edate:
        return None
    return {
        "symbol": symbol,
        "next_earnings_date": edate.isoformat(),
        "days_until": (edate - today).days,
        "fiscal_period": f"{item.get('year')}Q{item.get('quarter')}",
        "source": "finnhub",
    }


def at_risk_positions(portfolio: dict, earnings: list[dict]) -> list[dict]:
    """Find option positions whose DTE straddles the earnings date."""
    earn_map = {e["symbol"]: e for e in earnings if e.get("days_until") is not None}
    at_risk = []
    for pos in portfolio.get("positions", []):
        if pos.get("sec_type") != "OPT":
            continue
        sym = pos.get("symbol")
        info = earn_map.get(sym)
        if not info:
            continue

        exp = pos.get("expiration")
        try:
            if exp and "-" in exp:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
            elif exp:
                exp_date = datetime.strptime(exp, "%Y%m%d").date()
            else:
                continue
        except Exception:
            continue

        dte = (exp_date - date.today()).days
        if 0 <= info["days_until"] <= dte:
            at_risk.append({
                "symbol": sym,
                "strike": pos.get("strike"),
                "right": pos.get("right"),
                "expiration": exp_date.isoformat(),
                "dte": dte,
                "earnings_date": info["next_earnings_date"],
                "earnings_days_until": info["days_until"],
                "position": pos.get("position"),
            })
    return at_risk


def main() -> int:
    parser = argparse.ArgumentParser(description="Earnings calendar lookup")
    parser.add_argument("symbols", nargs="*", help="list of tickers")
    parser.add_argument("--days", type=int, default=30, help="next N days (default 30)")
    parser.add_argument("--portfolio-file", help="path to portfolio JSON file")
    parser.add_argument("--output", help="output file path (default stdout)")
    args = parser.parse_args()

    symbols = set(args.symbols)

    portfolio = None
    if args.portfolio_file:
        try:
            with open(args.portfolio_file, encoding="utf-8") as f:
                portfolio = json.load(f)
            for pos in portfolio.get("positions", []):
                if pos.get("symbol"):
                    symbols.add(pos["symbol"])
        except Exception as e:
            log(f"⚠️  Could not read {args.portfolio_file}: {e}")

    if not symbols:
        log("❌ No symbols to query")
        return 1

    log(f"🔄 Querying earnings for {len(symbols)} symbols ({args.days}-day window) ...")
    today = date.today()

    log("  fetching Nasdaq earnings calendar ...")
    nasdaq_map = fetch_nasdaq_range(args.days)
    log(f"  Nasdaq returned {len(nasdaq_map)} upcoming earnings")

    earnings = []
    for sym in sorted(symbols):
        sym_u = sym.upper()
        edate = nasdaq_map.get(sym_u)
        if edate:
            earnings.append({
                "symbol": sym,
                "next_earnings_date": edate.isoformat(),
                "days_until": (edate - today).days,
                "fiscal_period": None,
                "source": "nasdaq",
            })
            continue
        # Fallback: Finnhub
        info = fetch_finnhub_one(sym, args.days)
        if info:
            earnings.append(info)
        else:
            earnings.append({
                "symbol": sym,
                "next_earnings_date": None,
                "days_until": None,
                "fiscal_period": None,
                "source": None,
            })

    risk = at_risk_positions(portfolio, earnings) if portfolio else []

    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "window_days": args.days,
        "symbols": earnings,
        "at_risk_positions": risk,
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

    found = sum(1 for e in earnings if e["next_earnings_date"])
    log(f"✅ Done: {found}/{len(earnings)} earnings dates found, {len(risk)} at-risk option positions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
