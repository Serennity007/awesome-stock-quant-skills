# 🌱 Philip Fisher Growth Stocks｜A 6-Dimension Screener Feeding "Scuttlebutt" Research on A-Shares

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina public APIs)

> **"The stock market is filled with individuals who know the price of everything and the value of nothing."**

This skill mechanizes the quantifiable checks from Fisher's *Common Stocks and Uncommon Profits* for the A-share market: growth runway (revenue CAGR), R&D intensity, margin trend, return on capital, cash quality, and financial conservatism. The script only narrows thousands of stocks down to a shortlist — the decisive qualitative part of Fisher's 15 points (scuttlebutt research) remains a human job.

## Contents

- `SKILL.md` — Skill definition, 6-dimension scoring logic, and usage
- `scripts/screen.py` — A-share growth-stock screener (CSV + terminal table)
- `references/fisher_15_points.md` — The full 15 points: growth potential, management & culture, scuttlebutt, buy/sell discipline
- `fisher_test_result.csv` — Small-sample test output (2026-09-26, Mindray / Hikvision / Moutai)

## Quick Start

```bash
pip install akshare pandas

# Default pool: CSI 300 constituents, top 20 output
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# Custom small pool for testing
python scripts/screen.py --codes 600519,300760,002415 --out result.csv
```

## Parameters

- `--pool`: Stock universe; currently supports `hs300`.
- `--codes`: Comma-separated custom codes; takes precedence over `--pool`.
- `--top`: Number of top results to display (default 20).
- `--out`: CSV output path (default `fisher_result.csv`).
- `--sleep`: Seconds between per-stock calls (default 0.3, rate-limit friendly).

## 6-Dimension Growth-Quality Radar

| Dimension | Metric | Notes |
|---|---|---|
| Growth runway | 5-year revenue CAGR + years of positive profit growth | Sales growth is the defining trait (max 25) |
| R&D intensity | R&D expense / revenue | Proxy for management investing in tomorrow (max 20) |
| Margin trend | Gross-margin level + latest-vs-mean trend | Maintained or improving margins (max 15) |
| Return on capital | 5-year average ROE | Shareholder-return validation (max 15) |
| Cash quality | Operating cash flow / net profit | Are profits real? (max 15) |
| Financial conservatism | Latest debt-to-asset ratio | Proxy for point 14 (max 10) |

Verdict lines: **≥75 Fisher-style growth candidate**; **55–74 mixed strengths and weaknesses**; **<55 outside the framework**. Financials/industries without R&D data get a neutral 5 on that dimension.

## Output Fields

- `code` / `name` / `industry`: Stock code / name / industry
- `total`: Composite score (max 100)
- `growth_score` / `rd_score` / `margin_score` / `roe_score` / `cash_score` / `debt_score`: Dimension scores
- `rev_cagr` / `profit_pos_years`: Revenue CAGR / years of positive profit growth
- `rd_ratio_avg` / `rd_annual`: Average R&D ratio / yearly series
- `gross_mean` / `gross_annual` / `roe_mean` / `ocf_to_profit_mean` / `debt_latest`: Other financial metrics
- `data_years` / `source` / `note`: Valid years / data source / fallback notes

## Sample Results (2026-09-26, 3-stock sample)

Mindray 78 (R&D 9.84%, GM 63.6%, ROE 29.7%), Hikvision 76 (R&D 11.71%) lead; Kweichow Moutai 63 (R&D 0.09% penalized) — the Fisher framework naturally favors R&D-heavy growth companies over mature consumer names, matching intuition.

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always validate screening results through independent scuttlebutt-style research.
