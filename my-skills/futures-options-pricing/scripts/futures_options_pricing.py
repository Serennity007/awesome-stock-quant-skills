#!/usr/bin/env python3
"""Price European options on one futures contract with Black-76. Local CSV only; no quotes or trade advice."""
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path

DAY_COUNT = 365
IV_LOW = 1e-6
IV_HIGH = 5.0
IV_ITERATIONS = 200
IV_PRICE_TOLERANCE = 1e-12
BAND_TOLERANCE = 1e-12
MAX_ABS_RATE = 1.0
SQRT_TWO = math.sqrt(2.0)
SQRT_TWO_PI = math.sqrt(2.0 * math.pi)
OPTION_TYPES = ("call", "put")


def normal_cdf(value):
    """Return the standard normal cumulative distribution N(x) = 0.5 * (1 + erf(x / sqrt(2)))."""
    return 0.5 * (1.0 + math.erf(value / SQRT_TWO))


def normal_pdf(value):
    """Return the standard normal density n(x) = exp(-x * x / 2) / sqrt(2 * pi)."""
    return math.exp(-0.5 * value * value) / SQRT_TWO_PI


def _number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {label}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _positive(value, label):
    number = _number(value, label)
    if number <= 0.0:
        raise ValueError(f"{label} must be greater than zero")
    return number


def _option_type(value):
    if not isinstance(value, str) or value.strip().lower() not in OPTION_TYPES:
        raise ValueError(f"option_type must be call or put, got {value!r}")
    return value.strip().lower()


def _d1_d2(futures_price, strike, time_to_expiry, volatility):
    root_t = math.sqrt(time_to_expiry)
    sigma_root_t = volatility * root_t
    d1 = (math.log(futures_price) - math.log(strike) + 0.5 * volatility * volatility * time_to_expiry) / sigma_root_t
    return d1, d1 - sigma_root_t, root_t


def _no_arbitrage_band(futures_price, strike, time_to_expiry, rate, option_type):
    discount = math.exp(-rate * time_to_expiry)
    if option_type == "call":
        return max(0.0, discount * (futures_price - strike)), discount * futures_price
    return max(0.0, discount * (strike - futures_price)), discount * strike


def black76_price(futures_price, strike, time_to_expiry, rate, volatility, option_type):
    """Return the Black-76 theoretical price of a European call or put on a futures contract.

    Undiscounted forward/intrinsic style formulas: call = e^(-rT) * (F * N(d1) - K * N(d2)),
    put = e^(-rT) * (K * N(-d2) - F * N(-d1)).
    """
    option = _option_type(option_type)
    futures = _positive(futures_price, "futures_price")
    strike_value = _positive(strike, "strike")
    expiry = _positive(time_to_expiry, "time_to_expiry")
    rate_value = _number(rate, "rate")
    sigma = _positive(volatility, "volatility")
    d1, d2, _ = _d1_d2(futures, strike_value, expiry, sigma)
    discount = math.exp(-rate_value * expiry)
    if option == "call":
        return discount * (futures * normal_cdf(d1) - strike_value * normal_cdf(d2))
    return discount * (strike_value * normal_cdf(-d2) - futures * normal_cdf(-d1))


def greeks(futures_price, strike, time_to_expiry, rate, volatility, option_type):
    """Return Black-76 delta, gamma, vega, theta and rho for one European option.

    theta is -dPrice/dT per one calendar year; rho is -T * price per 1.00 rate change;
    vega_per_unit_vol is per 1.00 change in sigma and vega_per_vol_point is that value / 100.
    """
    option = _option_type(option_type)
    futures = _positive(futures_price, "futures_price")
    strike_value = _positive(strike, "strike")
    expiry = _positive(time_to_expiry, "time_to_expiry")
    rate_value = _number(rate, "rate")
    sigma = _positive(volatility, "volatility")
    price = black76_price(futures, strike_value, expiry, rate_value, sigma, option)
    d1, _d2, root_t = _d1_d2(futures, strike_value, expiry, sigma)
    discount = math.exp(-rate_value * expiry)
    density = normal_pdf(d1)
    decay_per_year = -discount * futures * density * sigma / (2.0 * root_t)
    vega_unit = discount * futures * density * root_t
    if option == "call":
        delta = discount * normal_cdf(d1)
    else:
        delta = -discount * normal_cdf(-d1)
    return {
        "delta": delta,
        "gamma": discount * density / (futures * sigma * root_t),
        "vega_per_unit_vol": vega_unit,
        "vega_per_vol_point": vega_unit / 100.0,
        "theta_per_year": decay_per_year + rate_value * price,
        "theta_per_day": (decay_per_year + rate_value * price) / DAY_COUNT,
        "rho_per_1_rate": -expiry * price,
    }


def implied_vol(price, futures_price, strike, time_to_expiry, rate, option_type):
    """Solve implied volatility from a market price by bounded bisection on [1e-6, 5.0].

    The price must sit strictly inside the no-arbitrage band, otherwise ValueError is raised.
    The search is capped at 200 bisection steps, so it always terminates.
    """
    option = _option_type(option_type)
    futures = _positive(futures_price, "futures_price")
    strike_value = _positive(strike, "strike")
    expiry = _positive(time_to_expiry, "time_to_expiry")
    rate_value = _number(rate, "rate")
    target = _positive(price, "market_price")
    lower, upper = _no_arbitrage_band(futures, strike_value, expiry, rate_value, option)
    if target <= lower + BAND_TOLERANCE or target >= upper - BAND_TOLERANCE:
        raise ValueError(
            f"market_price {target!r} is outside the no-arbitrage band ({lower!r}, {upper!r}) for a {option}"
        )
    low, high = IV_LOW, IV_HIGH
    low_price = black76_price(futures, strike_value, expiry, rate_value, low, option)
    high_price = black76_price(futures, strike_value, expiry, rate_value, high, option)
    if target <= low_price:
        raise ValueError(f"market_price {target!r} is below the price attainable at the {IV_LOW!r} volatility floor")
    if target >= high_price:
        raise ValueError(f"market_price {target!r} is above the price attainable at the {IV_HIGH!r} volatility cap")
    middle = (low + high) / 2.0
    for _ in range(IV_ITERATIONS):
        middle = (low + high) / 2.0
        difference = black76_price(futures, strike_value, expiry, rate_value, middle, option) - target
        if abs(difference) <= IV_PRICE_TOLERANCE or high - low <= 1e-15:
            return middle
        if difference > 0.0:
            high = middle
        else:
            low = middle
    return middle


def _calendar_date(value, label):
    if isinstance(value, datetime):
        raise ValueError(f"{label} must be a YYYY-MM-DD calendar date, not a datetime")
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a YYYY-MM-DD calendar date") from exc


def _as_of_calendar_date(value):
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of datetime requires an explicit timezone")
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if "T" in text or " " in text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("as_of must be YYYY-MM-DD or a timezone-aware ISO-8601 datetime") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("as_of datetime requires an explicit timezone")
        return parsed.astimezone(timezone.utc).date()
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("as_of must be YYYY-MM-DD or a timezone-aware ISO-8601 datetime") from exc


def _optional_positive(value, label):
    if value is None or not str(value).strip():
        return None
    return _positive(value, label)


def _read_rows(raw):
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("raw_csv must be bytes")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded text") from exc
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    if not {"option_id", "option_type", "strike"}.issubset(set(fields)):
        raise ValueError("CSV requires option_id,option_type,strike columns")
    rows, seen = [], set()
    for line_number, record in enumerate(reader, start=2):
        if not record or all(value is None for value in record.values()):
            continue
        option_id = (record.get("option_id") or "").strip()
        if not option_id:
            raise ValueError(f"row {line_number}: option_id is required")
        if option_id in seen:
            raise ValueError(f"row {line_number}: duplicate option_id {option_id!r}")
        seen.add(option_id)
        try:
            option_type = _option_type(record.get("option_type"))
            strike = _positive(record.get("strike"), "strike")
            market_price = _optional_positive(record.get("market_price"), "market_price")
            volatility = _optional_positive(record.get("volatility"), "volatility")
        except ValueError as exc:
            raise ValueError(f"row {line_number} ({option_id}): {exc}") from exc
        if market_price is None and volatility is None:
            raise ValueError(f"row {line_number} ({option_id}): requires market_price or volatility")
        rows.append({"option_id": option_id, "option_type": option_type, "strike": strike,
                     "market_price": market_price, "volatility": volatility})
    if not rows:
        raise ValueError("CSV contains no option rows")
    return rows


def _price_row(row, futures_price, time_to_expiry, rate):
    option = row["option_type"]
    strike = row["strike"]
    quoted = row["market_price"]
    implied = None
    status = "not_requested"
    if quoted is not None:
        implied = implied_vol(quoted, futures_price, strike, time_to_expiry, rate, option)
        status = "solved"
    pricing_volatility = row["volatility"] if row["volatility"] is not None else implied
    model_price = black76_price(futures_price, strike, time_to_expiry, rate, pricing_volatility, option)
    return {
        "option_id": row["option_id"],
        "option_type": option,
        "strike": strike,
        "moneyness_ln_F_over_K": math.log(futures_price) - math.log(strike),
        "days_to_expiry": None,
        "time_to_expiry_years": time_to_expiry,
        "market_price": quoted,
        "pricing_volatility": pricing_volatility,
        "model_price": model_price,
        "price_difference_vs_market": None if quoted is None else model_price - quoted,
        "implied_volatility": implied,
        "implied_volatility_status": status,
        "greeks": greeks(futures_price, strike, time_to_expiry, rate, pricing_volatility, option),
    }


def _parity_checks(options, futures_price, time_to_expiry, rate):
    discount = math.exp(-rate * time_to_expiry)
    grouped = {}
    for option in options:
        grouped.setdefault(option["strike"], []).append(option)
    checks = []
    for strike in sorted(grouped):
        calls = [option for option in grouped[strike] if option["option_type"] == "call"]
        puts = [option for option in grouped[strike] if option["option_type"] == "put"]
        for call in calls:
            for put in puts:
                call_minus_put = call["model_price"] - put["model_price"]
                discounted_intrinsic = discount * (futures_price - strike)
                checks.append({
                    "strike": strike,
                    "call_option_id": call["option_id"],
                    "put_option_id": put["option_id"],
                    "call_minus_put": call_minus_put,
                    "discounted_forward_intrinsic": discounted_intrinsic,
                    "residual": call_minus_put - discounted_intrinsic,
                })
    return checks


def analyze(raw_bytes, futures_price, expiry, as_of, rate):
    """Analyze a local European-option CSV batch on one futures contract and return the JSON-ready result."""
    futures = _positive(futures_price, "futures_price")
    rate_value = _number(rate, "rate")
    if abs(rate_value) > MAX_ABS_RATE:
        raise ValueError("rate magnitude must be at most 1.0 as a fractional annual rate")
    expiry_date = _calendar_date(expiry, "expiry")
    as_of_date = _as_of_calendar_date(as_of)
    days = (expiry_date - as_of_date).days
    if days <= 0:
        raise ValueError("time to expiry must be positive; the as-of date must be before expiry")
    years = days / DAY_COUNT
    rows = _read_rows(raw_bytes)
    options = []
    for row in rows:
        try:
            priced = _price_row(row, futures, years, rate_value)
        except ValueError as exc:
            raise ValueError(f"row {row['option_id']}: {exc}") from exc
        priced["days_to_expiry"] = days
        options.append(priced)
    return {
        "schema_version": 1,
        "futures_price": futures,
        "as_of_date": as_of_date.isoformat(),
        "expiry": expiry_date.isoformat(),
        "days_to_expiry": days,
        "time_to_expiry_years": years,
        "rate": rate_value,
        "day_count_basis": "calendar_365",
        "source_sha256": hashlib.sha256(bytes(raw_bytes)).hexdigest(),
        "options": options,
        "parity_checks": _parity_checks(options, futures, years, rate_value),
        "scope": ("Local Black-76 theoretical pricing for one futures contract and one expiry; "
                  "no live quotes, no executable price, no trade instruction and no return claim."),
        "limitations": [
            "European exercise approximation only; exchange-traded American-style options can differ because early exercise is not modeled",
            "One constant pricing volatility per row; no volatility smile, term structure, stochastic volatility or jumps",
            "Calendar-365 year count; no business-day, session, holiday or exchange calendar adjustment",
            "No dividends, lease rates, storage costs, transaction costs, fees or bid-ask spread",
            "The theoretical price is not an executable quote, settlement value or mark that can be traded",
            "One implied-volatility root inside a bounded search range is not proof of uniqueness or of a correct market volatility",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--futures-price", type=float, required=True)
    parser.add_argument("--expiry", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--rate", type=float, default=0.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.out.resolve() == args.csv.resolve():
            raise ValueError("output must not overwrite the input CSV")
        raw = args.csv.read_bytes()
        result = analyze(raw, args.futures_price, args.expiry, args.as_of, args.rate)
        result["source_file"] = args.csv.name
        result["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        body = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
    except (ValueError, OSError, KeyError, OverflowError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"Priced {len(result['options'])} option rows and {len(result['parity_checks'])} parity checks; "
          f"theoretical research only -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
