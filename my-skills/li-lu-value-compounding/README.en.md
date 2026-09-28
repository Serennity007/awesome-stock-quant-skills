# 🏔️ Li Lu Value Compounding｜A 6-Dimension "Compounding Machine" Screener for A-Shares

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina public APIs)

> **"Investing is a game of prediction, and the only reliable approach is to study things that don't change."**

This skill mechanizes Li Lu's (founder of Himalaya Capital, Charlie Munger's protégé) value-investing framework for A-shares: sustained high ROE, a non-stalling compounding trend (recent 2-year vs prior 3-year ROE), reinvestment-driven growth, real cash earnings, margin of safety at historically low PE/PB percentiles, and low leverage — 6 dimensions in total. The script only narrows the list; whether a business falls inside your circle of competence remains your call.

## Contents

- `SKILL.md` — Skill definition, 6-dimension scoring logic, and usage
- `scripts/screen.py` — A-share value-compounding screener (CSV + terminal table)
- `references/lilu_value_principles.md` — Li Lu's philosophy: stocks as ownership, Mr. Market, margin of safety, circle of competence, the compounding machine
- `lilu_test_result.csv` — Small-sample test output

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
- `--out`: CSV output path (default `lilu_result.csv`).
- `--sleep`: Seconds between per-stock calls (default 0.3, rate-limit friendly).

## 6-Dimension Value-Compounding Radar

| Dimension | Metric | Notes |
|---|---|---|
| Capital-return quality | 5-year average ROE | The business itself earns (max 25) |
| Compounding trend | Recent 2yr ROE − prior 3yr ROE | Compounding not stalling (max 15) |
| Reinvestment growth | Average profit growth | Retained earnings still compound (max 20) |
| Cash quality | Operating cash flow / net profit | Are profits real? (max 15) |
| Margin of safety | PB historical percentile (PE percentile auxiliary) | Mr. Market's panic price (max 15) |
| Financial discipline | Latest debt-to-asset ratio | Low leverage (max 10) |

Verdict lines: **≥75 value-compounding candidate**; **55–74 watch list**; **<55 outside the framework**.

## Output Fields

- `code` / `name` / `industry`: Stock code / name / industry
- `total`: Composite score (max 100)
- `roe_quality_score` / `roe_trend_score` / `reinvest_growth_score` / `cash_score` / `margin_safety_score` / `debt_score`: Dimension scores
- `roe_mean` / `roe_trend_diff` / `profit_growth_mean` / `ocf_mean` / `debt_latest`: Raw financials
- `pe_ttm` / `pb` / `pe_percentile` / `pb_percentile` / `val_years`: Valuation and historical percentiles
- `data_years` / `fin_source` / `note`: Valid years / data source / fallback notes

## Data Sources & Fallbacks

East Money financial indicators + East Money valuation history (PE/PB percentiles) + Sina statements fallback; recent-2yr-vs-prior-3yr trend gets a neutral score for young listings with under 4 years of data; system proxies disabled at startup, exponential-backoff retries on all network calls.

## Disclaimer

For learning and research only; not investment advice. A high score outside your circle of competence should still be passed over — invest only on independent research.
