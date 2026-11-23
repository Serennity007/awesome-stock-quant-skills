#!/usr/bin/env python3
"""Describe a futures contract curve from a local CSV. No quote fetching, forecasting or trade instructions."""
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path

SCHEMA_VERSION = 1
DAY_BASIS = 365
REQUIRED_COLUMNS = {"contract", "expiry", "last"}
SCOPE = "Offline descriptive curve snapshot for one product from a user-supplied CSV; no live quotes, price forecast, roll execution or trade instruction."
STRUCTURE_NOTE = "Classification compares the signs of adjacent calendar spreads only; total_annualized_change_pct uses the first and last contract and is descriptive, not a forecast or a trade signal."
LIMITATIONS = [
    "The last price may be a settlement, close or last-trade value; the CSV does not declare which and no provider verification is performed",
    "Annualization uses a fixed 365-day calendar basis and ignores exchange trading calendars, holidays and settlement conventions",
    "No contract multiplier, currency, price unit, tick size, margin or explicit roll-cost modeling is applied",
    "Volume and open-interest units, aggregation scope and vendor definitions are unverified",
    "Curve shape is a descriptive snapshot, not a price forecast or a trade signal, and roll yield is not realized return",
]


def is_iso_date(text):
    """Return True only for the exact YYYY-MM-DD calendar-date form."""
    return (len(text) == 10 and text[4] == "-" and text[7] == "-"
            and text[:4].isdigit() and text[5:7].isdigit() and text[8:].isdigit())


def parse_as_of(value):
    """Return the UTC calendar date used for day counts."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("as-of must be YYYY-MM-DD or an ISO-8601 datetime with timezone")
    text = value.strip()
    if is_iso_date(text):
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"invalid as-of date: {text}") from exc
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("as-of must be YYYY-MM-DD or an ISO-8601 datetime with timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as-of datetime requires an explicit timezone")
    return parsed.astimezone(timezone.utc).date()


def require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def positive_spot(value):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("spot must be numeric") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError("spot must be finite and positive")
    return number


def parse_expiry(value, contract):
    if not isinstance(value, str) or not is_iso_date(value.strip()):
        raise ValueError(f"contract {contract!r}: expiry must be YYYY-MM-DD")
    text = value.strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"contract {contract!r}: invalid expiry date") from exc


def parse_last(value, contract):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"contract {contract!r}: last is required")
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"contract {contract!r}: invalid last") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"contract {contract!r}: last must be finite and positive")
    return number


def optional_count(value, contract, label):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"contract {contract!r}: invalid {label}")
    text = value.strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(f"contract {contract!r}: invalid {label}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"contract {contract!r}: {label} must be finite and non-negative")
    return number


def load_unexpired(raw, cutoff):
    """Validate every row, then keep only contracts expiring after the cutoff date."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError("raw CSV input must be bytes")
    try:
        text = bytes(raw).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded text") from exc
    reader = csv.DictReader(io.StringIO(text))
    columns = set(reader.fieldnames or [])
    if not REQUIRED_COLUMNS.issubset(columns):
        raise ValueError("CSV requires contract,expiry,last columns")
    has_volume = "volume" in columns
    has_open_interest = "open_interest" in columns
    seen, rows, excluded = set(), [], 0
    for row in reader:
        raw_contract = row.get("contract")
        contract = raw_contract.strip() if isinstance(raw_contract, str) else ""
        if not contract:
            raise ValueError("every row requires a non-empty contract")
        if contract in seen:
            raise ValueError(f"duplicate contract: {contract}")
        seen.add(contract)
        expiry = parse_expiry(row.get("expiry"), contract)
        last = parse_last(row.get("last"), contract)
        volume = optional_count(row.get("volume"), contract, "volume") if has_volume else None
        open_interest = optional_count(row.get("open_interest"), contract, "open_interest") if has_open_interest else None
        # Expired rows are validated above but never enter the curve calculation.
        if expiry <= cutoff:
            excluded += 1
            continue
        rows.append({"contract": contract, "expiry_date": expiry, "last": last,
                     "volume": volume, "open_interest": open_interest})
    if len(rows) < 2:
        raise ValueError("at least two unexpired contracts are required")
    rows.sort(key=lambda entry: entry["expiry_date"])
    if len({entry["expiry_date"] for entry in rows}) != len(rows):
        raise ValueError("unexpired contracts must have unique expiry dates")
    return rows, excluded


def analyze(raw, product, as_of, spot=None):
    """Return descriptive curve facts for one product without source_file/generated_at_utc."""
    product = require_text(product, "product identity")
    cutoff = parse_as_of(as_of)
    spot_value = None if spot is None else positive_spot(spot)
    rows, excluded = load_unexpired(raw, cutoff)
    curve = [{"contract": entry["contract"], "expiry": entry["expiry_date"].isoformat(),
              "days_to_expiry": (entry["expiry_date"] - cutoff).days, "last": entry["last"],
              "volume": entry["volume"], "open_interest": entry["open_interest"]} for entry in rows]
    spreads = []
    for near, far in zip(curve, curve[1:]):
        spread = far["last"] - near["last"]
        days_between = far["days_to_expiry"] - near["days_to_expiry"]
        spreads.append({"near_contract": near["contract"], "far_contract": far["contract"],
                        "spread": spread, "spread_pct_of_near": spread / near["last"] * 100,
                        "days_between": days_between,
                        "annualized_slope_pct": spread / near["last"] * DAY_BASIS / days_between * 100})
    if all(entry["spread"] > 0 for entry in spreads):
        classification = "contango"
    elif all(entry["spread"] < 0 for entry in spreads):
        classification = "backwardation"
    elif all(entry["spread"] == 0 for entry in spreads):
        classification = "flat"
    else:
        classification = "mixed"
    first, last = curve[0], curve[-1]
    total_change = (last["last"] - first["last"]) / first["last"] * DAY_BASIS / (last["days_to_expiry"] - first["days_to_expiry"]) * 100
    basis = None
    if spot_value is not None:
        difference = spot_value - first["last"]
        basis = {"spot": spot_value, "nearest_contract": first["contract"], "nearest_expiry": first["expiry"],
                 "nearest_days_to_expiry": first["days_to_expiry"], "basis": difference,
                 "basis_pct_of_futures": difference / first["last"] * 100,
                 "annualized_basis_pct": difference / first["last"] * DAY_BASIS / first["days_to_expiry"] * 100}
    raw_bytes = bytes(raw) if isinstance(raw, (bytes, bytearray)) else raw.encode("utf-8")
    return {"schema_version": SCHEMA_VERSION, "product": product, "as_of_date": cutoff.isoformat(),
            "source_sha256": hashlib.sha256(raw_bytes).hexdigest(), "excluded_expired": excluded,
            "curve": curve, "adjacent_spreads": spreads,
            "structure": {"classification": classification, "total_annualized_change_pct": total_change,
                          "note": STRUCTURE_NOTE},
            "basis": basis, "scope": SCOPE, "limitations": list(LIMITATIONS)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--spot", type=float)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = args.csv.read_bytes()
        result = analyze(raw, args.product, args.as_of, args.spot)
        if args.out.resolve() == args.csv.resolve():
            raise ValueError("output must not overwrite input")
        result["source_file"] = args.csv.name
        result["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        body = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    basis_state = "included" if result["basis"] is not None else "not_supplied"
    print(f"Saved futures curve: {len(result['curve'])} unexpired contracts, "
          f"{result['excluded_expired']} expired excluded, "
          f"classification={result['structure']['classification']}, basis={basis_state} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
