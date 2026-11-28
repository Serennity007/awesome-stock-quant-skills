#!/usr/bin/env python3
"""Compute convertible-bond conversion premium, straight-bond floor, YTM, double-low and a redemption trigger count from local CSVs. No quotes, forecasts or trade instructions."""
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import statistics

SCHEMA_VERSION = 1
BOND_COLUMNS = ("code", "name", "price", "conv_price", "stock_price", "coupons", "years_left", "redemption_price")
STOCK_COLUMNS = ("date", "code", "close")
DISCOUNT_COLUMNS = ("rating", "rate")
CODE_CHARS = frozenset("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz._-")
YTM_LOW = -0.9999
YTM_HIGH = 10.0
YTM_TOLERANCE = 1e-12
YTM_ITERATIONS = 400
DEFAULT_DISCOUNT_RATE = 0.035
DEFAULT_TRIGGER_RATIO = 1.3
DEFAULT_TRIGGER_WINDOW = 30
DEFAULT_TRIGGER_DAYS = 15
SCOPE = ("Offline arithmetic on user-supplied convertible-bond rows: conversion value and premium, straight-bond floor, "
         "YTM, double-low and a redemption trigger count; no quote fetching, forecasting, credit analysis or trade advice.")
YTM_NOTE = ("no root in [-0.9999, 10.0]: the discounted cash flows do not bracket the market price under the "
            "declared schedule, so YTM is not defined within the search interval")
LIMITATIONS = [
    "Prices, conversion prices, stock prices, coupons, redemption prices and ratings are user inputs, not verified quotes, "
    "prospectus terms or exchange data",
    "Coupon times follow the fixed schedule t_k = years_left - (m - k); no day-count convention, accrued interest, "
    "ex-coupon adjustment or holiday calendar is modeled",
    "redemption_price is taken to include the final-period interest, so the script does not detect or correct a double-counted "
    "last coupon; the cash-flow convention is the user's responsibility",
    "The straight-bond floor discounts at one flat rate per bond and models no credit risk, default, rating migration, "
    "liquidity premium, tax or transaction cost",
    "YTM assumes the bond is held to maturity with all coupons and the redemption price paid in full and on time; "
    "no put, call, reset or other embedded optionality, reinvestment or fee is modeled",
    "Trigger counting only compares closes with trigger_ratio * conv_price over the supplied rows and the last trigger_window "
    "trading days; no down-reset (下修), clause variation, redemption notice, adjustment or missing-session handling is modeled",
    "Double-low is the fixed linear score price + 100 * conversion_premium, a screening ordinal rather than a valuation or "
    "expected-return measure",
    "Not a trade recommendation, forecast or performance proof; no market data is fetched and no path is simulated",
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


def _as_bytes(raw, label):
    """Return raw CSV input as bytes so hashing and decoding share one view."""
    if isinstance(raw, str):
        return raw.encode("utf-8")
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    raise ValueError(f"{label} CSV input must be bytes or text")


def _decode(raw, label):
    """Decode UTF-8 (BOM tolerated) CSV bytes and reject empty files."""
    data = _as_bytes(raw, label)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} CSV must be UTF-8 encoded text") from exc
    if not text.strip():
        raise ValueError(f"{label} CSV input is empty")
    return text


def _column_map(reader, required, label):
    """Map lower-case column names to the actual header spelling; require every column."""
    columns = {}
    for name in reader.fieldnames or []:
        if isinstance(name, str) and name.strip():
            columns.setdefault(name.strip().lower(), name)
    missing = [column for column in required if column not in columns]
    if missing:
        raise ValueError(f"{label} CSV requires columns: " + ",".join(required))
    return columns


def _all_blank(values):
    """Return True when every cell in a row is blank, so filler rows can be skipped."""
    return all(not _text(value) for value in values)


def _coupon_rates(value, code):
    """Parse the pipe-separated coupon schedule; a blank field means a zero-coupon bond."""
    text = _text(value)
    if not text:
        return []
    rates = []
    for index, item in enumerate(text.split("|"), start=1):
        token = item.strip()
        if not token:
            raise ValueError(f"bond {code}: coupons item {index} is empty")
        rates.append(_number(token, f"bond {code}: coupon {index}", allow_zero=True))
    return rates


def _parse_bond(values, face_value, has_face, rating_value, seen):
    """Validate one bond row and return its normalized record."""
    code = _text(values["code"])
    if not code:
        raise ValueError("bond code must be non-empty")
    if any(character not in CODE_CHARS for character in code):
        raise ValueError(f"bond {code}: code may contain only letters, digits, '.', '_' and '-'")
    if code in seen:
        raise ValueError(f"duplicate bond code: {code}")
    name = _text(values["name"])
    if not name:
        raise ValueError(f"bond {code}: name must be non-empty")
    price = _number(values["price"], f"bond {code}: price", allow_zero=False)
    conv_price = _number(values["conv_price"], f"bond {code}: conversion price", allow_zero=False)
    stock_price = _number(values["stock_price"], f"bond {code}: stock price", allow_zero=False)
    years_left = _number(values["years_left"], f"bond {code}: years left", allow_zero=False)
    redemption_price = _number(values["redemption_price"], f"bond {code}: redemption price", allow_zero=False)
    if has_face and _text(face_value):
        face = _number(face_value, f"bond {code}: face", allow_zero=False)
    else:
        face = 100.0
    coupons = _coupon_rates(values["coupons"], code)
    count = len(coupons)
    times = [years_left - (count - index) for index in range(1, count + 1)]
    if any(time <= 0 for time in times):
        raise ValueError(f"bond {code}: {count} coupons need years left greater than {count - 1}, "
                         f"got {years_left}; a non-positive coupon time cannot be discounted")
    cashflows = [coupon * face for coupon in coupons]
    seen.add(code)
    return {"code": code, "name": name, "price": price, "conv_price": conv_price,
            "stock_price": stock_price, "face": face, "rating": _text(rating_value),
            "years_left": years_left, "redemption_price": redemption_price, "coupons": coupons,
            "coupon_times": times, "coupon_cashflows": cashflows}


def parse_bonds(raw):
    """Validate raw bond CSV bytes and return normalized bond records in file order."""
    text = _decode(raw, "bond")
    reader = csv.DictReader(io.StringIO(text))
    columns = _column_map(reader, BOND_COLUMNS, "bond")
    has_face = "face" in columns
    has_rating = "rating" in columns
    seen, bonds = set(), []
    try:
        for row in reader:
            values = {column: row.get(columns[column]) for column in BOND_COLUMNS}
            face_value = row.get(columns["face"]) if has_face else None
            rating_value = row.get(columns["rating"]) if has_rating else None
            if _all_blank(values.values()) and not _text(face_value) and not _text(rating_value):
                continue
            bonds.append(_parse_bond(values, face_value, has_face, rating_value, seen))
    except csv.Error as exc:
        raise ValueError(f"invalid bond CSV data: {exc}") from exc
    if not bonds:
        raise ValueError("at least one bond is required")
    return bonds


def _parse_date(value, code):
    """Parse the exact YYYY-MM-DD calendar-date form used by the stock CSV."""
    text = _text(value)
    shaped = (len(text) == 10 and text[4] == "-" and text[7] == "-"
              and text[:4].isdigit() and text[5:7].isdigit() and text[8:].isdigit())
    if not shaped:
        raise ValueError(f"stock {code}: date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"stock {code}: invalid date {text}") from exc


def parse_stock(raw):
    """Validate raw stock CSV bytes and return code -> ascending close series."""
    text = _decode(raw, "stock")
    reader = csv.DictReader(io.StringIO(text))
    columns = _column_map(reader, STOCK_COLUMNS, "stock")
    series_by_code = {}
    try:
        for row in reader:
            values = {column: row.get(columns[column]) for column in STOCK_COLUMNS}
            if _all_blank(values.values()):
                continue
            code = _text(values["code"])
            if not code:
                raise ValueError("stock CSV: every row requires a non-empty code")
            trading_day = _parse_date(values["date"], code)
            close = _number(values["close"], f"stock {code} {trading_day.isoformat()}: close", allow_zero=False)
            series = series_by_code.setdefault(code, {})
            if trading_day in series:
                raise ValueError(f"stock {code}: duplicate date {trading_day.isoformat()}")
            series[trading_day] = close
    except csv.Error as exc:
        raise ValueError(f"invalid stock CSV data: {exc}") from exc
    if not series_by_code:
        raise ValueError("stock CSV requires at least one data row")
    return {code: [close for _, close in sorted(series.items())] for code, series in series_by_code.items()}


def parse_discount_curve(raw):
    """Validate raw rating/rate CSV bytes and return the rating -> rate table."""
    text = _decode(raw, "discount-curve")
    reader = csv.DictReader(io.StringIO(text))
    columns = _column_map(reader, DISCOUNT_COLUMNS, "discount-curve")
    curve = {}
    try:
        for row in reader:
            rating = _text(row.get(columns["rating"]))
            rate_value = row.get(columns["rate"])
            if not rating and not _text(rate_value):
                continue
            if not rating:
                raise ValueError("discount-curve CSV: every row requires a non-empty rating")
            if rating in curve:
                raise ValueError(f"discount-curve CSV: duplicate rating {rating}")
            curve[rating] = _number(rate_value, f"discount-curve rating {rating}: rate", allow_zero=False)
    except csv.Error as exc:
        raise ValueError(f"invalid discount-curve CSV data: {exc}") from exc
    if not curve:
        raise ValueError("discount-curve CSV requires at least one data row")
    return curve


def _present_value(rate, times, cashflows):
    """Discount every cash flow at one rate; return infinity when a factor overflows."""
    contributions = []
    for years, cashflow in zip(times, cashflows):
        try:
            factor = (1.0 + rate) ** (-years)
        except OverflowError:
            return math.inf
        contributions.append(cashflow * factor)
    return math.fsum(contributions)


def solve_ytm(price, times, cashflows):
    """Return (ytm, note); YTM is None when the search interval does not bracket a root."""
    low, high = YTM_LOW, YTM_HIGH
    low_gap = _present_value(low, times, cashflows) - price
    high_gap = _present_value(high, times, cashflows) - price
    if low_gap == 0.0:
        return low, None
    if high_gap == 0.0:
        return high, None
    if low_gap < 0.0 or high_gap > 0.0:
        return None, YTM_NOTE
    for _ in range(YTM_ITERATIONS):
        middle = (low + high) / 2.0
        gap = _present_value(middle, times, cashflows) - price
        if gap == 0.0:
            return middle, None
        if gap > 0.0:
            low = middle
        else:
            high = middle
        if high - low <= YTM_TOLERANCE:
            break
    return (low + high) / 2.0, None


def _trigger(series, conv_price, trigger_ratio, trigger_window, trigger_days):
    """Count closes at or above trigger_ratio * conv_price over the last trigger_window rows."""
    threshold = trigger_ratio * conv_price
    if series is None:
        return {"status": "no-stock-series", "window": trigger_window, "observed_days": None,
                "count": None, "trigger_days": trigger_days, "ratio": trigger_ratio,
                "price_threshold": threshold}
    observed = series[-trigger_window:]
    count = sum(1 for close in observed if close >= threshold)
    if len(series) < trigger_window:
        status = "insufficient-history"
    elif count >= trigger_days:
        status = "triggered"
    else:
        status = "below"
    return {"status": status, "window": trigger_window, "observed_days": len(observed),
            "count": count, "trigger_days": trigger_days, "ratio": trigger_ratio,
            "price_threshold": threshold}


def _build_row(bond, series, curve, default_rate, trigger_ratio, trigger_window, trigger_days):
    """Return one output row with conversion, bond-floor, YTM, double-low and trigger facts."""
    rate = curve.get(bond["rating"]) if bond["rating"] else None
    if rate is None:
        rate, source = default_rate, "default"
    else:
        source = "rating-curve"
    shares = bond["face"] / bond["conv_price"]
    conversion_value = shares * bond["stock_price"]
    conversion_premium = bond["price"] / conversion_value - 1.0
    times = bond["coupon_times"] + [bond["years_left"]]
    cashflows = bond["coupon_cashflows"] + [bond["redemption_price"]]
    pure_bond_value = _present_value(rate, times, cashflows)
    if not math.isfinite(pure_bond_value) or pure_bond_value <= 0.0:
        raise ValueError(f"bond {bond['code']}: discounted cash flows are not positive and finite; check the discount rate")
    bond_floor_premium = bond["price"] / pure_bond_value - 1.0
    ytm, ytm_note = solve_ytm(bond["price"], times, cashflows)
    double_low = bond["price"] + 100.0 * conversion_premium
    return {"code": bond["code"], "name": bond["name"], "price": bond["price"],
            "conv_price": bond["conv_price"], "stock_price": bond["stock_price"],
            "face": bond["face"], "rating": bond["rating"], "years_left": bond["years_left"],
            "redemption_price": bond["redemption_price"], "coupons": list(bond["coupons"]),
            "conversion_shares": shares, "conversion_value": conversion_value,
            "conversion_premium": conversion_premium, "coupon_times": list(bond["coupon_times"]),
            "coupon_cashflows": list(bond["coupon_cashflows"]), "discount_rate": rate,
            "discount_rate_source": source, "pure_bond_value": pure_bond_value,
            "bond_floor_premium": bond_floor_premium, "ytm": ytm, "ytm_note": ytm_note,
            "double_low": double_low,
            "trigger": _trigger(series, bond["conv_price"], trigger_ratio, trigger_window, trigger_days)}


def _summarize(rows):
    """Aggregate cross-sectional facts; empty categories stay empty lists."""
    premiums = [row["conversion_premium"] for row in rows]
    best = sorted(rows, key=lambda row: row["double_low"])[:5]
    return {"bond_count": len(rows), "conversion_premium_min": min(premiums),
            "conversion_premium_max": max(premiums),
            "conversion_premium_median": statistics.median(premiums),
            "pure_bond_value_min": min(row["pure_bond_value"] for row in rows),
            "double_low_best": [{"code": row["code"], "double_low": row["double_low"]} for row in best],
            "triggered": [row["code"] for row in rows if row["trigger"]["status"] == "triggered"],
            "insufficient_history": [row["code"] for row in rows if row["trigger"]["status"] == "insufficient-history"],
            "no_stock_series": [row["code"] for row in rows if row["trigger"]["status"] == "no-stock-series"]}


def _positive_integer(value, label):
    """Validate a strictly positive integer CLI/API parameter."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def analyze(bonds_raw, stock_raw=None, discount_raw=None, discount_rate=DEFAULT_DISCOUNT_RATE,
            trigger_ratio=DEFAULT_TRIGGER_RATIO, trigger_window=DEFAULT_TRIGGER_WINDOW,
            trigger_days=DEFAULT_TRIGGER_DAYS, stock_name=None, discount_name=None):
    """Return rows, parameters and summary without the CLI provenance fields."""
    default_rate = _number(discount_rate, "discount rate", allow_zero=False)
    ratio = _number(trigger_ratio, "trigger ratio", allow_zero=False)
    window = _positive_integer(trigger_window, "trigger window")
    days = _positive_integer(trigger_days, "trigger days")
    if days > window:
        raise ValueError("trigger days must not exceed trigger window")
    bonds = parse_bonds(bonds_raw)
    curve = parse_discount_curve(discount_raw) if discount_raw is not None else {}
    series = parse_stock(stock_raw) if stock_raw is not None else {}
    rows = [_build_row(bond, series.get(bond["code"]), curve, default_rate, ratio, window, days)
            for bond in bonds]
    stock_sha256 = hashlib.sha256(_as_bytes(stock_raw, "stock")).hexdigest() if stock_raw is not None else None
    parameters = {"discount_rate_default": default_rate, "discount_csv": discount_name,
                  "trigger_ratio": ratio, "trigger_window": window, "trigger_days": days,
                  "stock_csv": stock_name, "stock_sha256": stock_sha256}
    return {"schema_version": SCHEMA_VERSION, "parameters": parameters, "rows": rows,
            "summary": _summarize(rows), "scope": SCOPE, "limitations": list(LIMITATIONS)}


def _write_new_file(path, body):
    """Create the output path exclusively; remove it again if the write fails."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(f"cannot create output directory {path.parent}: {exc}") from exc
    try:
        handle = path.open("x", encoding="utf-8", newline="\n")
    except FileExistsError as exc:
        raise ValueError(f"output already exists: {path}") from exc
    try:
        with handle:
            handle.write(body)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--stock-csv", type=Path)
    parser.add_argument("--discount-csv", type=Path)
    parser.add_argument("--discount-rate", type=float, default=DEFAULT_DISCOUNT_RATE)
    parser.add_argument("--trigger-ratio", type=float, default=DEFAULT_TRIGGER_RATIO)
    parser.add_argument("--trigger-window", type=int, default=DEFAULT_TRIGGER_WINDOW)
    parser.add_argument("--trigger-days", type=int, default=DEFAULT_TRIGGER_DAYS)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ValueError(f"output already exists: {args.out}")
        bonds_raw = args.csv.read_bytes()
        stock_raw = args.stock_csv.read_bytes() if args.stock_csv is not None else None
        discount_raw = args.discount_csv.read_bytes() if args.discount_csv is not None else None
        result = analyze(bonds_raw, stock_raw=stock_raw, discount_raw=discount_raw,
                         discount_rate=args.discount_rate, trigger_ratio=args.trigger_ratio,
                         trigger_window=args.trigger_window, trigger_days=args.trigger_days,
                         stock_name=args.stock_csv.name if args.stock_csv is not None else None,
                         discount_name=args.discount_csv.name if args.discount_csv is not None else None)
        payload = {"schema_version": SCHEMA_VERSION, "source_file": args.csv.name,
                   "source_sha256": hashlib.sha256(bonds_raw).hexdigest(),
                   "generated_at_utc": datetime.now(timezone.utc).isoformat()}
        payload.update(result)
        body = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        _write_new_file(args.out, body)
    except (ValueError, OSError, KeyError, ArithmeticError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    summary = result["summary"]
    print(f"Saved convertible-bond premium: bonds={summary['bond_count']}, "
          f"triggered={len(summary['triggered'])}, "
          f"median_conversion_premium={summary['conversion_premium_median']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
