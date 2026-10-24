"""Date and valuation contracts shared by this skill's screening and analysis."""
import math

import pandas as pd


def numeric(values):
    cleaned = values.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce").replace([float("inf"), -float("inf")], float("nan"))


def dated_rows(frame, date_column, as_of=None):
    """Sort dates, reject conflicting duplicates, exclude invalid/future rows."""
    if date_column not in frame:
        raise ValueError(f"missing date column: {date_column}")
    out = frame.copy()
    raw = out[date_column].astype(str).str.replace(r"\.0$", "", regex=True)
    out[date_column] = pd.to_datetime(raw, errors="coerce", format="mixed").dt.normalize()
    cutoff = pd.Timestamp(as_of).normalize() if as_of is not None else pd.Timestamp.now().normalize()
    out = out.dropna(subset=[date_column])
    out = out[out[date_column] <= cutoff].drop_duplicates()
    if out[date_column].duplicated().any():
        raise ValueError(f"conflicting rows for the same {date_column}")
    return out.sort_values(date_column).reset_index(drop=True)


def annual_rows(frame, date_column, years=5, as_of=None):
    out = dated_rows(frame, date_column, as_of)
    return out[(out[date_column].dt.month == 12) & (out[date_column].dt.day == 31)].tail(years).copy()


def valuation_snapshot(frame, as_of=None, years=5, min_points=60):
    """Latest row and positive TTM/PB history inside the requested calendar window.

    Invalid latest values remain missing: never substitute an older positive value.
    This filters observation dates, not financial publication/revision timestamps.
    """
    frame = frame.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    out = dated_rows(frame, "数据日期", as_of)
    if out.empty:
        raise ValueError("no dated valuation observations on or before the cutoff")
    cutoff = pd.Timestamp(as_of).normalize() if as_of is not None else pd.Timestamp.now().normalize()
    out = out[out["数据日期"] >= cutoff - pd.DateOffset(years=years)].copy()
    if out.empty:
        raise ValueError("no valuation observations inside the lookback window")
    result = {"date": out["数据日期"].iloc[-1].date().isoformat(),
              "history_start": out["数据日期"].iloc[0].date().isoformat(),
              "window_start": (cutoff - pd.DateOffset(years=years)).date().isoformat(),
              "window_end": cutoff.date().isoformat(), "observations": len(out)}
    # Exact aliases only: static PE and PEG are not substitutes for trailing PE.
    for key, aliases in (("pe", ("PE(TTM)", "PE（TTM）")), ("pb", ("市净率", "PB")),
                         ("close", ("当日收盘价", "close", "CLOSE"))):
        column = next((col for col in aliases if col in out), None)
        values = numeric(out[column]) if column else pd.Series(float("nan"), index=out.index)
        current = values.iloc[-1]
        current = float(current) if pd.notna(current) and math.isfinite(current) and current > 0 else None
        history = values[values > 0].dropna()
        result[key] = current
        if key != "close":
            usable = current is not None and len(history) >= min_points
            result[key + "_observations"] = len(history)
            result[key + "_pct"] = float((history <= current).mean()) if usable else None
            result[key + "_q25"] = float(history.quantile(0.25)) if usable else None
            result[key + "_q50"] = float(history.quantile(0.5)) if usable else None
    return result
