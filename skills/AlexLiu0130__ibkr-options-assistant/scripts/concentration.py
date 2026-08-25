"""
Portfolio concentration risk analysis.

Three concentration metrics that simple position-list browsing misses:

  1. Herfindahl-Hirschman Index (HHI)
       sum of squared position weights (in pct, 0-100).
       Scale: 0  = perfectly diversified
              <1500  = unconcentrated
              1500-2500 = moderate concentration
              >2500  = high concentration
              10000  = single holding

  2. Sector concentration (% of equity per GICS sector)
       Uses a small in-file ticker -> sector map for the ~50 most common
       tickers. Unknown tickers are bucketed as "Unknown" with a warning
       if the bucket grows large.

  3. Top-N concentration (top 3 / top 5 holdings, % of equity)

Only STK positions count toward the weights. OPT (derivative) positions are
excluded -- they will surface via the dedicated greeks/exposure scripts.

Usage:
    python concentration.py
    python concentration.py --portfolio-file /tmp/portfolio.json
    python concentration.py --output /tmp/concentration.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from ib_client import ib_connect, log
from portfolio_positions import fetch_positions

CLIENT_ID_OFFSET = 18

# Hardcoded ticker -> sector map. Kept small and inline by design --
# anything missing falls into "Unknown" and we warn if Unknown is large.
TICKER_SECTOR: dict[str, str] = {
    # Semiconductors (separated from broader Technology for finer-grained warnings)
    "NVDA": "Semiconductors", "AMD": "Semiconductors", "INTC": "Semiconductors",
    "MU": "Semiconductors", "MRVL": "Semiconductors", "ARM": "Semiconductors",
    "TSM": "Semiconductors", "AVGO": "Semiconductors", "QCOM": "Semiconductors",
    "ASML": "Semiconductors", "AMAT": "Semiconductors", "LRCX": "Semiconductors",
    "KLAC": "Semiconductors", "ON": "Semiconductors", "TXN": "Semiconductors",
    "MCHP": "Semiconductors", "SMCI": "Semiconductors",
    # Software / Hardware / Internet (Technology)
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "GOOG": "Technology", "AMZN": "Consumer Discretionary", "META": "Technology",
    "NFLX": "Communication Services", "ORCL": "Technology", "CRM": "Technology",
    "ADBE": "Technology", "NOW": "Technology", "SHOP": "Technology",
    "PLTR": "Technology", "SNOW": "Technology", "CRWD": "Technology",
    "PANW": "Technology", "NET": "Technology", "DDOG": "Technology",
    # EV / Automotive
    "TSLA": "Consumer Discretionary", "RIVN": "Consumer Discretionary",
    "LCID": "Consumer Discretionary", "F": "Consumer Discretionary",
    "GM": "Consumer Discretionary",
    # Financials
    "JPM": "Financials", "GS": "Financials", "BAC": "Financials",
    "MS": "Financials", "WFC": "Financials", "C": "Financials",
    "BLK": "Financials", "SCHW": "Financials", "V": "Financials",
    "MA": "Financials", "AXP": "Financials", "PYPL": "Financials",
    "COIN": "Financials",
    # Healthcare
    "UNH": "Healthcare", "JNJ": "Healthcare", "LLY": "Healthcare",
    "PFE": "Healthcare", "ABBV": "Healthcare", "MRK": "Healthcare",
    "TMO": "Healthcare", "ABT": "Healthcare", "NVO": "Healthcare",
    # Energy
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    # Consumer Staples
    "WMT": "Consumer Staples", "COST": "Consumer Staples", "PG": "Consumer Staples",
    "KO": "Consumer Staples", "PEP": "Consumer Staples",
    # Industrials
    "BA": "Industrials", "CAT": "Industrials", "GE": "Industrials",
    "RTX": "Industrials", "LMT": "Industrials", "UPS": "Industrials",
    # Diversified ETFs (sector-agnostic; counted toward concentration as their own bucket)
    "SPY": "Diversified", "QQQ": "Diversified", "IWM": "Diversified",
    "VOO": "Diversified", "VTI": "Diversified", "DIA": "Diversified",
    # Crypto-adjacent
    "MSTR": "Technology", "MARA": "Technology", "RIOT": "Technology",
}


def hhi_interpretation(hhi: float) -> str:
    if hhi < 1500:
        return "low concentration"
    if hhi < 2500:
        return "moderate concentration"
    if hhi < 5000:
        return "high concentration"
    return "extreme concentration"


def lookup_sector(symbol: str) -> str:
    return TICKER_SECTOR.get(symbol.upper(), "Unknown")


def compute_concentration(positions: list[dict]) -> dict:
    """Compute HHI, sector and top-N concentration from a list of positions.

    Only STK positions count toward the weights.
    """
    stk = [p for p in positions
           if p.get("sec_type") == "STK"
           and p.get("market_value") not in (None, 0)
           and (p.get("position") or 0) > 0]

    total = sum(float(p["market_value"]) for p in stk)
    if total <= 0:
        return {
            "total_equity_value": 0.0,
            "hhi": 0.0,
            "hhi_interpretation": "no equity holdings",
            "top_holdings": [],
            "top_3_pct": 0.0,
            "top_5_pct": 0.0,
            "sectors": {},
            "warnings": ["No equity holdings to analyze"],
        }

    enriched = []
    for p in stk:
        mv = float(p["market_value"])
        weight_pct = mv / total * 100.0
        enriched.append({
            "symbol": p["symbol"],
            "market_value": round(mv, 2),
            "weight_pct": round(weight_pct, 2),
            "sector": lookup_sector(p["symbol"]),
        })

    enriched.sort(key=lambda x: x["market_value"], reverse=True)

    hhi = sum(p["weight_pct"] ** 2 for p in enriched)

    top_3_pct = round(sum(p["weight_pct"] for p in enriched[:3]), 2)
    top_5_pct = round(sum(p["weight_pct"] for p in enriched[:5]), 2)

    sectors: dict[str, float] = {}
    for p in enriched:
        sectors[p["sector"]] = sectors.get(p["sector"], 0.0) + p["weight_pct"]
    sectors = {k: round(v, 2) for k, v in
               sorted(sectors.items(), key=lambda kv: kv[1], reverse=True)}

    warnings: list[str] = []
    if top_3_pct > 30:
        warnings.append(
            f"Top 3 holdings = {top_3_pct}% of equity (risk concentration)"
        )
    if top_5_pct > 50:
        warnings.append(
            f"Top 5 holdings = {top_5_pct}% of equity"
        )
    for sector, pct in sectors.items():
        if sector == "Unknown" and pct > 15:
            warnings.append(
                f"Unknown sector = {pct}% -- consider mapping these tickers"
            )
            continue
        if sector == "Diversified":
            continue
        if pct > 20:
            warnings.append(
                f"{sector} = {pct}% -- single-sector exposure"
            )
    if enriched and enriched[0]["weight_pct"] > 20:
        top = enriched[0]
        warnings.append(
            f"Single position {top['symbol']} = {top['weight_pct']}% of equity"
        )

    return {
        "total_equity_value": round(total, 2),
        "hhi": round(hhi, 2),
        "hhi_interpretation": hhi_interpretation(hhi),
        "top_holdings": enriched,
        "top_3_pct": top_3_pct,
        "top_5_pct": top_5_pct,
        "sectors": sectors,
        "warnings": warnings,
    }


def load_portfolio_file(path: Path) -> list[dict]:
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
        description="Portfolio concentration risk (HHI + sector + top-N)"
    )
    parser.add_argument("--portfolio-file",
                        help="Read positions from this JSON instead of live IBKR fetch")
    parser.add_argument("--output", help="Output file path (default stdout)")
    args = parser.parse_args()

    if args.portfolio_file:
        log(f"reading positions from {args.portfolio_file}")
        positions = load_portfolio_file(Path(args.portfolio_file))
    else:
        log("fetching live positions from IB Gateway ...")
        try:
            with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
                portfolio = fetch_positions(ib)
                positions = portfolio["positions"]
        except Exception as e:
            log(f"ERROR: {e}")
            return 1

    metrics = compute_concentration(positions)
    result = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **metrics,
    }

    _write_output(result, args.output)
    log(
        f"done: HHI={result['hhi']} ({result['hhi_interpretation']}); "
        f"top3={result['top_3_pct']}%; warnings={len(result['warnings'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
