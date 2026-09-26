# 🏦 John Neff Low-P/E Investing｜A-Share "Unloced But Solid" Screener via Total Return Ratio ≥2

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / CNINFO / Tencent public APIs)

> **"Well-positioned companies in unloved industries."**

This skill mechanizes John Neff's low-P/E system (31 years at Windsor Fund, beating the market by ~3.1 points annually) for the A-share market: each stock's P/E discount versus the all-market median, his signature total-return ratio (growth + dividend yield) / P/E ≥ 2, sustained dividends, and fundamental floors. The script outputs a CSV; the human job is answering "is it cheap because it's unloved, or because it's broken?"

## Contents

- `SKILL.md` — Skill definition, 7-dimension scoring logic, and usage
- `scripts/screen.py` — A-share low-P/E screener (CSV + terminal table)
- `references/neff_principles.md` — Neff's core ideas: low-P/E philosophy, total-return formula, contrarian design, sell discipline
- `neff_test_result.csv` — Small-sample test output (2026-09-26, CMB / Moutai / Wuliangye)

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
- `--out`: CSV output path (default `neff_result.csv`).
- `--sleep`: Seconds between per-stock calls (default 0.3, rate-limit friendly).

## 7-Dimension Low-P/E Radar

| Dimension | Metric | Notes |
|---|---|---|
| Low P/E | Stock PE(TTM) / all-market median | Windsor ran at 40–60% of market P/E (max 25) |
| Total return ratio | (profit-growth mean + dividend yield) / PE | Neff's golden standard ≥2 (max 25) |
| Dividend yield | Last 5 payouts annualized by actual time span / price | Wages while waiting for the market to agree (max 15) |
| Growth floor | Mean profit growth >0 and ≥3 positive years | Unloved vs broken (max 10) |
| Return on capital | 5-year average ROE | Business quality (max 10) |
| Low leverage | Latest debt-to-asset ratio | Financial soundness (max 10) |
| Cash quality | Operating cash flow / net profit | Real profits (max 5) |

Verdict lines: **≥75 Neff-style candidate**; **55–74 watchlist**; **<55 outside the framework**. Falls back to absolute P/E bands if the market median is unavailable.

## Output Fields

- `code` / `name` / `industry`: Stock code / name / industry
- `total`: Composite score (max 100)
- `low_pe_score` / `trr_score` / `dividend_score` / `growth_score` / `roe_score` / `debt_score` / `cash_score`: Dimension scores
- `pe_ttm` / `pe_market_ratio` / `pe_percentile`: P/E(TTM) / ratio to market median / historical percentile
- `total_return_ratio` / `dividend_yield` / `dividend_events` / `dividend_span_years`: TRR / annualized yield / payout count / measurement span
- `profit_growth_mean` / `roe_mean` / `debt_latest` / `ocf_mean`: Other financial metrics
- `data_years` / `val_source` / `fin_source` / `note`: Valid years / sources / fallback notes

## Sample Results (2026-09-26, 3-stock sample)

China Merchants Bank 88 (PE 6.76, only 0.18× the market median; yield 6.34%; TRR 2.33 clears the golden line), Kweichow Moutai 76, Wuliangye 65 — unloved low-P/E, high-dividend sectors like banks fit the Neff framework naturally.

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always validate why a stock is cheap before acting.
