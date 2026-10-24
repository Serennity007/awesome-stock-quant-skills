#!/usr/bin/env python3
"""Merge framework scores; reject ambiguous inputs and write a provenance manifest."""
import argparse
import hashlib
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

SUFFIXES = ["_hs300_result", "_test_result", "_result", "_demo", "_hs300"]


def framework_name(path):
    stem = Path(path).stem
    for suffix in SUFFIXES:
        if stem.endswith(suffix):
            return stem[:-len(suffix)]
    return stem


def load_one(path):
    df = pd.read_csv(path, dtype={"code": str})
    for col in ("code", "total"):
        if col not in df.columns:
            raise ValueError(f"{path}: missing column '{col}'")
    if df.empty:
        raise ValueError(f"{path}: no rows")
    codes = df["code"].fillna("").str.strip()
    if not codes.str.fullmatch(r"[0-9]{1,6}").all():
        raise ValueError(f"{path}: code must be 1–6 ASCII digits (A-share codes)")
    df["code"] = codes.str.zfill(6)
    if df["code"].duplicated().any():
        raise ValueError(f"{path}: duplicate stock codes")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    if not df["total"].map(lambda x: pd.notna(x) and math.isfinite(x)).all():
        raise ValueError(f"{path}: total contains missing or non-finite scores")
    return framework_name(path), df


def combine(paths, top_pct=10.0, min_frameworks=2, allow_partial_pools=False):
    if len(paths) < 2:
        raise ValueError("at least two framework CSVs are required")
    if not math.isfinite(top_pct) or not 0 < top_pct <= 100:
        raise ValueError("top-pct must be in (0, 100]")
    if not 2 <= min_frameworks <= len(paths):
        raise ValueError("min-frameworks must be between 2 and the number of inputs")
    loaded = [load_one(path) for path in paths]
    names = [name for name, _ in loaded]
    if len(set(names)) != len(names):
        raise ValueError("framework names collide; rename input files to distinct framework names")
    pools = [set(df["code"]) for _, df in loaded]
    pools_match = all(pool == pools[0] for pool in pools)
    if not pools_match and not allow_partial_pools:
        raise ValueError("stock pools differ; align inputs or explicitly use --allow-partial-pools")
    frames = []
    for name, df in loaded:
        frame = df.set_index("code")[["total"]].rename(columns={"total": f"{name}_raw"})
        frame[f"{name}_pct"] = frame[f"{name}_raw"].rank(method="average", pct=True) * 100
        frames.append(frame)
    merged = pd.concat(frames, axis=1)
    pct_cols = [f"{name}_pct" for name in names]
    merged["frameworks"] = merged[pct_cols].notna().sum(axis=1).astype(int)
    merged["consensus_score"] = merged[pct_cols].mean(axis=1)
    merged["top_hits"] = (merged[pct_cols] >= 100 - top_pct).sum(axis=1).astype(int)
    out = merged[merged["frameworks"] >= min_frameworks].copy()
    for _, df in loaded:
        labels = df.set_index("code")
        for col in ("name", "industry"):
            if col in labels:
                out[col] = out[col].combine_first(labels[col]) if col in out else labels[col]
    out = out.reset_index().sort_values(
        ["consensus_score", "top_hits", "code"], ascending=[False, False, True]
    )
    out[pct_cols + ["consensus_score"]] = out[pct_cols + ["consensus_score"]].round(1)
    cols = ["code"] + [c for c in ("name", "industry") if c in out]
    cols += ["consensus_score", "top_hits", "frameworks"]
    cols += [c for n in names for c in (f"{n}_pct", f"{n}_raw")]
    return out[cols], pools_match


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csvs", nargs="+", required=True)
    parser.add_argument("--top-pct", type=float, default=10.0)
    parser.add_argument("--min-frameworks", type=int, default=2)
    parser.add_argument("--allow-partial-pools", action="store_true")
    parser.add_argument("--as-of", type=date.fromisoformat, help="User-declared data date; not inferred from file mtime")
    parser.add_argument("--out", default="consensus.csv")
    args = parser.parse_args()
    try:
        out, pools_match = combine(args.csvs, args.top_pct, args.min_frameworks, args.allow_partial_pools)
        target = Path(args.out)
        manifest_path = target.with_suffix(target.suffix + ".meta.json")
        input_paths = {Path(p).resolve() for p in args.csvs}
        if target.resolve() in input_paths or manifest_path.resolve() in input_paths:
            raise ValueError("output paths must not overwrite inputs")
        manifest = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "as_of": str(args.as_of) if args.as_of else None,
            "as_of_verified": False,
            "pandas_version": pd.__version__,
            "top_pct": args.top_pct, "min_frameworks": args.min_frameworks,
            "pools_match": pools_match, "rows": len(out),
            "inputs": [{"file": Path(p).name, "framework": framework_name(p),
                        "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in args.csvs],
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(target, index=False, encoding="utf-8-sig")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(out.head(20).to_string(index=False))
    print(f"{len(out)} rows -> {target}; provenance -> {manifest_path}")
    if not pools_match:
        print("WARNING: partial pools enabled; ranks are relative to different populations.")
    print("Consensus ranks are research aids, not independent evidence or expected returns.")


if __name__ == "__main__":
    main()
