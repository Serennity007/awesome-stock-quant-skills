#!/usr/bin/env python3
"""Describe closed OHLC bars at an explicit cutoff. No quote fetching or trade instructions."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError("timestamps must be ISO-8601 with a timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps require an explicit timezone")
    return parsed.astimezone(timezone.utc)


def positive(value, label):
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid {label}") from exc
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return result


def load_bars(raw, cutoff):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not {"close_time", "open", "high", "low", "close"}.issubset(reader.fieldnames or []):
        raise ValueError("CSV requires close_time,open,high,low,close")
    selected, previous, excluded = [], None, 0
    for row in reader:
        close_time = timestamp(row["close_time"])
        if previous is not None and close_time <= previous:
            raise ValueError("bar closing times must be strictly increasing and unique")
        previous = close_time
        # Values after the decision cutoff never enter the indicator calculation.
        if close_time > cutoff:
            excluded += 1
            continue
        values = {key: positive(row[key], key) for key in ("open", "high", "low", "close")}
        if values["high"] < max(values["open"], values["close"], values["low"]) or values["low"] > min(values["open"], values["close"], values["high"]):
            raise ValueError("OHLC high/low bounds are inconsistent")
        selected.append({"close_time": close_time, **values})
    if not selected:
        raise ValueError("no completed bars on/before the decision cutoff")
    return selected, excluded


def ema(values, period):
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def macd(values):
    if len(values) < 35:
        return {"ready": False, "minimum_bars": 35, "reason": "insufficient completed bars"}
    fast, slow = ema(values, 12), ema(values, 26)
    dif = [left - right for left, right in zip(fast, slow)]
    dea = ema(dif, 9)
    histogram = [2 * (left - right) for left, right in zip(dif, dea)]
    current, previous = histogram[-1], histogram[-2]
    sign = "positive" if current > 0 else "negative" if current < 0 else "zero"
    magnitude = "expanding" if abs(current) > abs(previous) else "shrinking" if abs(current) < abs(previous) else "unchanged"
    flip = "to_positive" if previous <= 0 < current else "to_negative" if previous >= 0 > current else None
    return {"ready": True, "dif": dif[-1], "dea": dea[-1], "histogram": current,
            "histogram_previous": previous, "sign": sign, "absolute_magnitude": magnitude, "flip": flip,
            "definition": "EMA12-EMA26; EMA9 signal; histogram=2*(DIF-DEA); first-close EMA seed"}


def boundaries(bars, support, resistance):
    current = bars[-1]
    previous = bars[-2] if len(bars) > 1 else None
    result = {}
    if support is not None:
        pattern = "above_support_no_reclaim_pattern"
        if current["close"] < support:
            pattern = "closed_below_support"
        elif previous and previous["close"] < support:
            pattern = "reclaimed_after_closed_break"
        elif current["low"] < support:
            pattern = "wick_below_then_close_at_or_above"
        result["support"] = {"level": support, "observation": pattern}
    if resistance is not None:
        pattern = "below_resistance_no_rejection_pattern"
        if current["close"] > resistance:
            pattern = "closed_above_resistance"
        elif previous and previous["close"] > resistance:
            pattern = "rejected_after_closed_break"
        elif current["high"] > resistance:
            pattern = "wick_above_then_close_at_or_below"
        result["resistance"] = {"level": resistance, "observation": pattern}
    return result


def analyze(raw, instrument, timeframe, as_of, data_kind, support=None, resistance=None,
            reference_time=None, window_bars=None):
    if not instrument or not instrument.strip():
        raise ValueError("instrument identity is required")
    if timeframe not in ("M30", "H1", "H4", "D1", "W1", "MN1"):
        raise ValueError("unsupported declared timeframe")
    if data_kind not in ("synthetic", "imported_observations"):
        raise ValueError("explicit data kind required")
    cutoff = timestamp(as_of)
    support = positive(support, "support") if support is not None else None
    resistance = positive(resistance, "resistance") if resistance is not None else None
    if support is not None and resistance is not None and support >= resistance:
        raise ValueError("support must be below resistance")
    if window_bars is not None and (window_bars <= 0 or reference_time is None):
        raise ValueError("a positive bar window requires a reference time")
    bars, excluded = load_bars(raw, cutoff)
    closes = [bar["close"] for bar in bars]
    averages = {f"ma{n}": sum(closes[-n:]) / n if len(closes) >= n else None for n in (5, 10, 20)}
    alignment = "insufficient_history"
    if all(value is not None for value in averages.values()):
        a, b, c = averages.values()
        alignment = "ascending" if a > b > c else "descending" if a < b < c else "mixed_or_flat"
    anchor = None
    if reference_time is not None:
        reference = timestamp(reference_time)
        indices = [index for index, bar in enumerate(bars) if bar["close_time"] == reference]
        if not indices:
            raise ValueError("reference must match an included completed bar closing time")
        elapsed = len(bars) - 1 - indices[0]
        anchor = {"reference_close_time": reference.isoformat(), "completed_bars_after_reference": elapsed,
                  "includes_reference_bar": False, "window_bars": window_bars,
                  "window_state": None if window_bars is None else "expired" if elapsed > window_bars else "due_now" if elapsed == window_bars else "within_window"}
    latest = {key: value.isoformat() if isinstance(value, datetime) else value for key, value in bars[-1].items()}
    return {"schema_version": 1, "instrument": instrument.strip(), "declared_timeframe": timeframe,
            "data_kind": data_kind, "as_of_utc": cutoff.isoformat(),
            "source_sha256": hashlib.sha256(raw).hexdigest(), "completed_bar_count": len(bars),
            "excluded_after_cutoff": excluded, "latest_completed_bar": latest,
            "observation_age_seconds": (cutoff - bars[-1]["close_time"]).total_seconds(),
            "moving_averages": averages, "ma_ordering": alignment, "macd": macd(closes),
            "boundary_observations": boundaries(bars, support, resistance), "reference_window": anchor,
            "scope": "Descriptive facts only; no live quotes, price target, trade instruction or win-rate estimate.",
            "limitations": ["Input close_time is assumed to mean bar close, not bar open; provider convention must be checked",
                            "No session-calendar, missing-bar, contract-roll, unit or quote-source verification",
                            "Manual support/resistance and analog anchors are not validated predictive features",
                            "A reclaim/rejection observation does not establish a confirmed reversal or successful retest"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--data-kind", choices=("synthetic", "imported_observations"), required=True)
    parser.add_argument("--support", type=float)
    parser.add_argument("--resistance", type=float)
    parser.add_argument("--reference-time")
    parser.add_argument("--window-bars", type=int)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.csv.read_bytes(), args.instrument, args.timeframe, args.as_of, args.data_kind,
                         args.support, args.resistance, args.reference_time, args.window_bars)
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
    print(f"Saved {result['completed_bar_count']} completed bars; {result['data_kind']}; descriptive research only -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
