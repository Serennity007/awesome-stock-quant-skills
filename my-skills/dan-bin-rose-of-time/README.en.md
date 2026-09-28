# 🌹 Dan Bin "Rose of Time"｜A 7-Dimension Great-Enterprise Screener for A-Shares

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / CNINFO / Tencent public APIs)

> **"Time is the most valuable asset; we should grow together with great enterprises."**

This skill mechanizes Dan Bin's (founder of Oriental Harbor, author of *The Rose of Time*) great-enterprise framework for A-shares: long slope (revenue CAGR runway), thick snow (high gross margin = pricing power), compounding engine (5-year ROE), the rose of time (sustained dividends), cash quality, financial health, and growth consistency — 7 dimensions in total. The script only narrows the list; "is this a business you can pass to the next generation" remains a human judgment.

## Contents

- `SKILL.md` — Skill definition, 7-dimension scoring logic, and usage
- `scripts/screen.py` — A-share great-enterprise screener (CSV + terminal table)
- `references/danbin_rose_principles.md` — Dan Bin's philosophy: the rose of time, what makes an enterprise great, two routes (brand consumer vs. tech), buy/sell discipline
- `danbin_test_result.csv` — Small-sample test output

## Quick Start

```bash
pip install akshare pandas

# Default pool: CSI 300 constituents, top 20 output
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# Custom small pool for testing
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

## Parameters

- `--pool`: Stock universe; currently supports `hs300`.
- `--codes`: Comma-separated custom codes; takes precedence over `--pool`.
- `--top`: Number of top results to display (default 20).
- `--out`: CSV output path (default `danbin_result.csv`).
- `--sleep`: Seconds between per-stock calls (default 0.3, rate-limit friendly).

## 7-Dimension Great-Enterprise Radar

| Dimension | Metric | Notes |
|---|---|---|
| Long slope | 5-year revenue CAGR | Growth runway (max 15) |
| Thick snow | Average gross margin | Brand pricing power (max 20) |
| Compounding engine | 5-year average ROE | The compounding motor (max 20) |
| Rose of time | Annualized dividend yield (span-based) | Sharing the compounding (max 15) |
| Cash quality | Operating cash flow / net profit | Are profits real? (max 10) |
| Financial health | Latest debt-to-asset ratio | Low leverage (max 10) |
| Growth quality | Years of positive profit growth | Consistency (max 10) |

Verdict lines: **≥75 great-enterprise candidate**; **55–74 watch list**; **<55 outside the framework**.

## Output Fields

- `code` / `name` / `industry`: Stock code / name / industry
- `total`: Composite score (max 100)
- `runway_score` / `snow_score` / `roe_engine_score` / `rose_score` / `cash_score` / `debt_score` / `growth_quality_score`: Dimension scores
- `rev_cagr` / `gross_mean` / `roe_mean` / `dividend_yield` / `ocf_mean` / `debt_latest` / `profit_pos_years` / `close`: Raw metrics
- `data_years` / `fin_source` / `note`: Valid years / data source / fallback notes

## Data Sources & Fallbacks

East Money financial indicators + CNINFO dividends + Tencent snapshot; falls back to Sina statements recomputed by hand when the primary source fails; dividend yield is annualized over the actual span of the last 5 payouts so special dividends don't inflate it; system proxies disabled at startup, exponential-backoff retries on all network calls.

## Disclaimer

For learning and research only; not investment advice. "Greatness" extends far beyond quantification — always validate screening results through qualitative research on the business itself.
