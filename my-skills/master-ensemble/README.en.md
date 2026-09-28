# 🤝 Master-Consensus Screener｜Cross-Framework Intersection Merger

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Dependency: pandas only (pure local CSV merging, no network calls)

> **"When several independent methodologies point at the same stock at the same time, you are weighting probability."**

This skill merges scoring-result CSVs from any of the repo's master skills (each `screen.py` output with `code`/`total` columns) into a cross-framework consensus list: percentile-normalize within each framework → consensus score (mean percentile) + top-hit count + framework coverage, then output the intersection.

## Contents

- `SKILL.md` — Skill definition, consensus logic, and usage
- `scripts/ensemble.py` — The consensus merger (finishes in seconds, no network calls)
- `references/ensemble_methodology.md` — Methodology: why percentile normalization, how to read framework conflicts, limits of consensus
- `consensus_hs300_demo.csv` — Demo: 3-framework (Dan Bin + Li Lu + O'Neil) full CSI-300 consensus

## Quick Start

```bash
pip install pandas

# Step 1: run full-pool screens for each master framework (same universe, e.g. --pool hs300)
python ../dan-bin-rose-of-time/scripts/screen.py --pool hs300 --out danbin_hs300_result.csv
python ../li-lu-value-compounding/scripts/screen.py --pool hs300 --out lilu_hs300_result.csv
python ../oneil-canslim/scripts/screen.py --pool hs300 --out canslim_hs300_result.csv

# Step 2: merge into a consensus list
python scripts/ensemble.py \
    --csvs ../dan-bin-rose-of-time/danbin_hs300_result.csv \
           ../li-lu-value-compounding/lilu_hs300_result.csv \
           ../oneil-canslim/canslim_hs300_result.csv \
    --min-frameworks 2 --out consensus.csv
```

## Parameters

- `--csvs`: At least 2 result CSVs; the filename (minus `_result`-style suffixes) becomes the framework name.
- `--top-pct`: "Top hit" percentile line within each framework (default top 10%).
- `--min-frameworks`: Minimum frameworks covering a stock for it to be output (default 2).
- `--out`: Consensus CSV output path (default `consensus.csv`).

## Output Fields

- `code` / `name` / `industry`: Code / name / industry (meta from the first CSV containing the column)
- `consensus_score`: Mean percentile across covering frameworks (0-100)
- `top_hits`: Number of frameworks where the stock sits in the top 10%
- `frameworks`: Number of covering frameworks
- `<framework>_pct` / `<framework>_raw`: Within-framework percentile and raw score

## Disclaimer

For learning and research only; not investment advice. A consensus score does not check for shared data errors, frameworks are not fully independent, and historical agreement does not imply future agreement.
