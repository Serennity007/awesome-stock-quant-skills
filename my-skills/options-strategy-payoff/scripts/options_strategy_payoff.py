#!/usr/bin/env python3
"""Evaluate the expiry payoff of a multi-leg futures/options strategy from a local CSV. No quotes, path simulation or trade instructions."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path

SCHEMA_VERSION = 1
REQUIRED_COLUMNS = ("leg_id", "instrument", "side", "strike", "quantity", "premium")
INSTRUMENTS = ("call", "put", "futures")
SIDES = ("buy", "sell")
SCOPE = "Expiry-only profit/loss arithmetic from user-supplied legs; no live quotes, path simulation, position sizing, win-rate estimate or trade recommendation."
NET_PREMIUM_NOTE = ("Positive net_premium is a net debit paid for option premium; negative is a net credit received. "
                    "Only option legs enter this sum; a futures leg's premium column is its entry futures price, "
                    "not a premium, so futures legs carry no premium cash flow and are excluded from net_premium.")
BREAKEVEN_BASIS = ("Exact roots of the expiry profit/loss as a function of underlying price over S>0 only; "
                   "piecewise-linear between option strikes; reported as isolated zero levels plus finite boundaries "
                   "of identically-zero intervals, sorted and rounded to 6 decimal places.")
LIMITATIONS = [
    "Expiry-only payoff: no early exercise, assignment, position close-out or any intermediate path is modeled",
    "No margin, collateral, borrow, fees, slippage, funding, taxes or currency conversion is modeled",
    "Premiums, strikes, quantities and multipliers are user inputs, not verified quotes or contract specifications",
    "The strategy label is user-declared text and is not validated against the leg structure",
    "The price domain is S>0: the S=0 payoff is a finite boundary limit, so only the rising-price tail can be marked unbounded; negative futures settlement prices (seen in WTI 2020) are not modeled",
    "Unbounded markers are mathematical asymptotes, not risk limits, capital requirements or probability statements",
    "No implied volatility, Greeks, time decay before expiry, path dependence or probability-of-profit is estimated",
    "Not a trade recommendation; the output is not a win-rate, expected-return or performance proof",
]


def _text(value):
    """Return a stripped cell value; missing cells become empty strings."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _number(value, label, allow_zero):
    """Parse a finite number and enforce the declared sign rule."""
    text = _text(value)
    if not text:
        raise ValueError(f"{label} is required")
    try:
        number = float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    if allow_zero:
        if number < 0:
            raise ValueError(f"{label} must be finite and non-negative")
    elif number <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return number


def _parse_leg(values, multiplier_value, has_multiplier, seen):
    """Validate one CSV row and return the normalized leg record."""
    leg_id = _text(values["leg_id"])
    if not leg_id:
        raise ValueError("leg_id must be non-empty")
    if leg_id in seen:
        raise ValueError(f"duplicate leg_id: {leg_id}")
    instrument = _text(values["instrument"]).lower()
    if instrument not in INSTRUMENTS:
        raise ValueError(f"leg {leg_id}: instrument must be call, put or futures")
    side = _text(values["side"]).lower()
    if side not in SIDES:
        raise ValueError(f"leg {leg_id}: side must be buy or sell")
    strike_text = _text(values["strike"])
    if instrument == "futures":
        if strike_text not in ("", "-"):
            raise ValueError(f"leg {leg_id}: futures legs must leave strike blank or '-'")
        strike = None
        premium = _number(values["premium"], f"leg {leg_id}: futures entry price", allow_zero=False)
    else:
        if strike_text in ("", "-"):
            raise ValueError(f"leg {leg_id}: calls and puts require a positive strike")
        strike = _number(strike_text, f"leg {leg_id}: strike", allow_zero=False)
        premium = _number(values["premium"], f"leg {leg_id}: premium", allow_zero=True)
    quantity = _number(values["quantity"], f"leg {leg_id}: quantity", allow_zero=False)
    if has_multiplier and _text(multiplier_value):
        multiplier = _number(multiplier_value, f"leg {leg_id}: multiplier", allow_zero=False)
    else:
        multiplier = 1.0
    sign = 1.0 if side == "buy" else -1.0
    # An option premium is a cash flow at entry; an entry futures price is not.
    cash_flow = -sign * quantity * premium * multiplier if instrument != "futures" else 0.0
    seen.add(leg_id)
    return {"leg_id": leg_id, "instrument": instrument, "side": side, "strike": strike,
            "quantity": quantity, "premium": premium, "multiplier": multiplier,
            "sign": sign, "signed_quantity": sign * quantity, "cash_flow_at_entry": cash_flow}


def parse_legs(raw):
    """Validate raw CSV bytes and return normalized leg records in file order."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("CSV input must be bytes")
    try:
        text = bytes(raw).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded text") from exc
    if not text.strip():
        raise ValueError("CSV input is empty")
    reader = csv.DictReader(io.StringIO(text))
    header = {}
    for name in reader.fieldnames or []:
        if isinstance(name, str) and name.strip():
            header.setdefault(name.strip().lower(), name)
    if any(column not in header for column in REQUIRED_COLUMNS):
        raise ValueError("CSV requires columns: " + ",".join(REQUIRED_COLUMNS))
    has_multiplier = "multiplier" in header
    seen, legs = set(), []
    try:
        for row in reader:
            values = {column: row.get(header[column]) for column in REQUIRED_COLUMNS}
            multiplier_value = row.get(header["multiplier"]) if has_multiplier else None
            # Skip blank filler rows; a partially empty row still fails field validation.
            if all(not _text(value) for value in list(values.values()) + [multiplier_value]):
                continue
            legs.append(_parse_leg(values, multiplier_value, has_multiplier, seen))
    except csv.Error as exc:
        raise ValueError(f"invalid CSV data: {exc}") from exc
    if not legs:
        raise ValueError("at least one leg is required")
    return legs


def option_strikes(legs):
    """Return the sorted unique positive strikes of option legs."""
    return sorted({leg["strike"] for leg in legs if leg["strike"] is not None})


def option_net_premium(legs):
    """Net option premium per strategy unit; positive means a net debit was paid."""
    contributions = [leg["sign"] * leg["quantity"] * leg["premium"] * leg["multiplier"]
                     for leg in legs if leg["instrument"] != "futures"]
    return math.fsum(contributions)


def payoff(legs, underlying_price):
    """Expiry profit/loss per strategy unit at one underlying price S."""
    contributions = []
    for leg in legs:
        unit = leg["sign"] * leg["quantity"] * leg["multiplier"]
        if leg["instrument"] == "futures":
            contributions.append(unit * (underlying_price - leg["premium"]))
        elif leg["instrument"] == "call":
            intrinsic = max(underlying_price - leg["strike"], 0.0)
            contributions.append(unit * (intrinsic - leg["premium"]))
        else:
            intrinsic = max(leg["strike"] - underlying_price, 0.0)
            contributions.append(unit * (intrinsic - leg["premium"]))
    return math.fsum(contributions)


def slope_high(legs):
    """Slope of expiry payoff as the underlying price tends to positive infinity."""
    contributions = []
    for leg in legs:
        unit = leg["sign"] * leg["quantity"] * leg["multiplier"]
        if leg["instrument"] in ("call", "futures"):
            contributions.append(unit)
    return math.fsum(contributions)


def slope_low(legs):
    """Slope of expiry payoff as the underlying price approaches zero from above."""
    contributions = []
    for leg in legs:
        unit = leg["sign"] * leg["quantity"] * leg["multiplier"]
        if leg["instrument"] == "futures":
            contributions.append(unit)
        elif leg["instrument"] == "put":
            contributions.append(-unit)
    return math.fsum(contributions)


def _segment_slope(legs, low, high):
    """Analytic payoff slope on an interval between two consecutive option strikes."""
    contributions = []
    for leg in legs:
        unit = leg["sign"] * leg["quantity"] * leg["multiplier"]
        if leg["instrument"] == "futures":
            contributions.append(unit)
        elif leg["instrument"] == "call" and leg["strike"] <= low:
            contributions.append(unit)
        elif leg["instrument"] == "put" and leg["strike"] >= high:
            contributions.append(-unit)
    return math.fsum(contributions)


def _identically_zero(legs, bounds):
    """Return True when the payoff is zero at every positive underlying price."""
    return slope_high(legs) == 0 and all(payoff(legs, point) == 0 for point in bounds)


def breakeven_levels(legs):
    """Return sorted breakeven prices over S>0 only, rounded to 6 decimals."""
    bounds = [0.0] + option_strikes(legs)
    if _identically_zero(legs, bounds):
        raise ValueError("expiry payoff is zero at every underlying price; breakeven levels are undefined")
    roots, states = [], []
    for low, high in zip(bounds, bounds[1:]):
        low_value = payoff(legs, low)
        slope = _segment_slope(legs, low, high)
        if slope == 0:
            states.append("zero" if low_value == 0 else "nonzero")
        else:
            states.append("nonzero")
            root = low - low_value / slope
            if low < root < high:
                roots.append(root)
    last = bounds[-1]
    last_value = payoff(legs, last)
    high_slope = slope_high(legs)
    if high_slope == 0:
        last_state = "zero" if last_value == 0 else "nonzero"
    else:
        last_state = "nonzero"
        root = last - last_value / high_slope
        if root > last:
            roots.append(root)
    # Kinks where the payoff touches zero; plateau interiors are skipped because they are not isolated.
    for index in range(1, len(bounds)):
        point = bounds[index]
        if payoff(legs, point) != 0:
            continue
        left_state = states[index - 1]
        right_state = states[index] if index < len(states) else last_state
        if left_state == "zero" and right_state == "zero":
            continue
        roots.append(point)
    return sorted({round(root, 6) for root in roots if root > 0})


def default_price_grid(legs):
    """Return the deterministic default grid: sorted unique 0.8x, 1.0x and 1.2x each option strike."""
    strikes = option_strikes(legs)
    if not strikes:
        raise ValueError("no option strikes to derive a default price grid; provide --prices")
    prices = set()
    for strike in strikes:
        prices.update((strike * 0.8, strike, strike * 1.2))
    return sorted(prices)


def normalize_prices(prices):
    """Validate a user-supplied underlying price list, preserving its order."""
    try:
        items = list(prices)
    except TypeError as exc:
        raise ValueError("prices must be a sequence of finite positive numbers") from exc
    if not items:
        raise ValueError("at least one underlying price is required when prices are supplied")
    normalized = []
    for value in items:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("prices must be numeric") from exc
        if not math.isfinite(number) or number <= 0:
            raise ValueError("prices must be finite and positive")
        normalized.append(number)
    return normalized


def analyze(raw, strategy, prices=None):
    """Return expiry payoff facts from raw CSV bytes without CLI bookkeeping fields."""
    if not isinstance(strategy, str) or not strategy.strip():
        raise ValueError("strategy label must be non-empty")
    legs = parse_legs(raw)
    grid = normalize_prices(prices) if prices is not None else default_price_grid(legs)
    roots = breakeven_levels(legs)
    high_slope = slope_high(legs)
    candidates = [0.0] + option_strikes(legs)
    values = [payoff(legs, point) for point in candidates]
    # The price domain is S>0, so the S=0 payoff is the finite low-boundary limit.
    # Only the right tail can be unbounded: rising payoff means unbounded profit,
    # falling payoff means unbounded loss.
    max_profit = "unbounded" if high_slope > 0 else max(values)
    max_loss = "unbounded" if high_slope < 0 else min(values)
    echoed = [{"leg_id": leg["leg_id"], "instrument": leg["instrument"], "side": leg["side"],
               "strike": leg["strike"], "quantity": leg["quantity"], "premium": leg["premium"],
               "multiplier": leg["multiplier"], "signed_quantity": leg["signed_quantity"],
               "cash_flow_at_entry": leg["cash_flow_at_entry"]} for leg in legs]
    return {"schema_version": SCHEMA_VERSION, "strategy": strategy.strip(), "leg_count": len(legs),
            "legs": echoed, "net_premium": option_net_premium(legs),
            "net_premium_note": NET_PREMIUM_NOTE, "breakevens": roots,
            "breakeven_basis": BREAKEVEN_BASIS, "max_profit": max_profit, "max_loss": max_loss,
            "price_grid": list(grid),
            "payoff_at_prices": [{"underlying_price": price, "profit_loss": payoff(legs, price)}
                                 for price in grid],
            "scope": SCOPE, "limitations": list(LIMITATIONS)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--prices", type=float, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = args.csv.read_bytes()
        result = analyze(raw, args.strategy, args.prices)
        if args.out.resolve() == args.csv.resolve():
            raise ValueError("output must not overwrite input")
        result["source_sha256"] = hashlib.sha256(raw).hexdigest()
        result["source_file"] = args.csv.name
        result["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        body = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"Saved payoff: {result['leg_count']} legs; net_premium={result['net_premium']}; "
          f"breakevens={len(result['breakevens'])}; max_profit={result['max_profit']}; "
          f"max_loss={result['max_loss']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
