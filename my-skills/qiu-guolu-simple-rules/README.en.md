# 🌙 Count Moons, Not Stars｜Qiu Guolu "Three-Good" A-Share Leader Screener

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / 10jqka / Tencent / Sina public APIs)

> **Industry structure matters more than individual alpha. Cheapness is the hard truth. Fight only after you have already won.**

This skill turns Qiu Guolu's *The Simplest Things in Investing* into a mechanical A-share screener. It screens CSI 300 or a custom stock list through three lenses — good industry, good company, good price — and scores only the top 3 market-cap leaders in each industry (the "moons"), ignoring the second- and third-tier "stars."

## Contents

- `SKILL.md` — Skill definition, 3-dimensional scoring logic, and usage
- `scripts/screen.py` — A-share "three-good" leader screener (CSV + terminal table)
- `references/qiu_principles.md` — Summary of Qiu Guolu's core investment principles

## Quick Start

```bash
pip install akshare pandas

# Default pool: CSI 300 constituents, top 20 output
python scripts/screen.py --pool hs300 --top 20 --out qiu_result.csv

# Custom small pool for testing
python scripts/screen.py --codes 600519,000858,600036 --out qiu_result.csv
```

## Parameters

- `--pool`: Stock universe; currently supports `hs300`.
- `--codes`: Comma-separated custom codes; takes precedence over `--pool`.
- `--top`: Number of top results to display (default 20).
- `--out`: CSV output path (default `qiu_result.csv`).
- `--sleep`: Interval between per-stock requests (default 0.3s, for rate limiting).

## 3-Dimensional Scoring Radar

| Dimension | Metric | Notes |
|---|---|---|
| Good Industry | Market-cap rank within industry | Top 3 get 25/20/15 points; non-leaders get 0 — "count moons, not stars" |
| Good Company | 5-year ROE + revenue growth | High and stable ROE scores best; positive and stable revenue growth proxies market-share/competitive edge |
| Good Price | PE/PB historical percentile | Lower percentile scores higher; absolute PE/PB fallback when historical percentile is unavailable |

## Output Fields

- `code` / `name` / `industry`: Stock code / short name / industry
- `total_score`: Composite score (max 100)
- `industry_rank` / `industry_score`: Market-cap rank within industry / industry score
- `roe_score` / `growth_score`: ROE dimension score / revenue-growth dimension score
- `price_score` / `pe_score` / `pb_score`: Total price score / PE percentile score / PB percentile score
- `pe_ttm` / `pb` / `pe_percentile` / `pb_percentile`: Current valuation and historical percentile
- `roe_avg` / `roe_std` / `revenue_growth_avg`: Mean ROE / ROE standard deviation / mean revenue growth
- `total_mv_yi`: Total market cap (100M CNY)
- `data_years`: Number of years with valid data
- `val_source` / `fin_source` / `note`: Data source and fallback notes

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics and valuation percentiles do not guarantee future performance. Always validate screening results through your own understanding of industry structure and business models.
