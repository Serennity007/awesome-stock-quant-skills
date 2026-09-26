# 🏭 Duan Yongping "Business Model First" Investing｜A 6-Dimension Screener for A-Share Great Businesses

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina / Tencent public APIs)

> **"Buying a stock is buying the company; buying the company is buying the present value of its future cash flows. Period."**

This skill brings Duan Yongping's investing philosophy to the A-share market: no price prediction, no theme chasing—just six financial yardsticks applied consistently to answer "is this a great business?" Business-model quality, return on capital, cash conversion, low leverage, earnings stability, and industry leadership ("dare to be the follower, then win as a fast follower"). The output is a structured CSV ready for your qualitative follow-up on integrity, circle of competence, and corporate culture.

## Contents

- `SKILL.md` — Skill definition, 6-dimension scoring logic, and usage
- `scripts/screen.py` — A-share business-model screener (CSV + terminal table)
- `references/duan_methods.md` — Duan Yongping's core ideas: buy the company not the ticker, business model first, dare to be the follower, circle of competence, culture & Stop Doing List
- `duan_test_result.csv` — Small-sample test output (2026-09-26, Moutai / Wuliangye / CMB)

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
- `--out`: CSV output path (default `duan_screen_result.csv`).
- `--sleep`: Seconds between per-stock calls (default 0.3, rate-limit friendly).

## 6-Dimension Business-Model Radar

| Dimension | Metric | Notes |
|---|---|---|
| Business model | 5-year average gross margin + stability | High and stable = pricing power (max 25) |
| Return on capital | Consecutive annual ROE | ROIC-style proxy (max 20) |
| Cash conversion | Operating cash flow / net profit | Are profits real cash? (max 20) |
| Low leverage | Latest debt-to-asset ratio | Stay away from financial risk (max 15) |
| Earnings stability | CV of profit/revenue growth | Predictable long-term results (max 10) |
| Industry leader | Market-cap rank within SW industry | Dare to be the follower (max 10) |

Verdict lines: **≥75 excellent business model**; **55–74 mixed strengths and weaknesses**; **<55 outside the framework**.

## Output Fields

- `code` / `name` / `industry`: Stock code / name / industry
- `total`: Composite score (max 100)
- `business_score` / `roe_score` / `cash_score` / `debt_score` / `stability_score` / `leader_score`: Dimension scores
- `gross_mean` / `gross_annual` / `roe_mean` / `roe_annual`: Gross-margin & ROE averages and yearly series
- `ocf_to_profit_mean` / `debt_latest`: Average OCF-to-profit ratio / latest debt ratio
- `ind_rank` / `ind_total` / `leader_ratio` / `total_mv_yi`: In-industry rank / industry size / cap share of leader / total cap (¥100M)
- `data_years` / `source` / `note`: Valid years / data source / fallback notes

## Sample Results (2026-09-26, full CSI 300, 300 stocks)

Shanxi Fenjiu 86, Mindray Medical 83, Kweichow Moutai 82, Wuliangye 81, CNOOC 81, Aimeike 80, Hithink RoyalFlush 80, Focus Media 79—high-margin, high-ROE cash cows cluster at the top, matching the "great business" intuition.

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always validate screening results through your own understanding of the business (circle of competence).
