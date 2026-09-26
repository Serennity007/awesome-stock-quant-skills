# 🚀 Zhang Lei / Hillhouse Long-Term Structural Value Investing｜A 4-D Radar for A-Share "Friends of Time"

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina public APIs)

> **"We are entrepreneurs, except that we happen to be investors."**

This skill brings Zhang Lei's long-term structural value investing framework (from his book *Value*) to the A-share market. No chart guessing, no hot-theme chasing—just four financial yardsticks applied consistently to identify companies with the characteristics of "friends of time": sustained double growth, long-term reinvestment, industry headroom, and an improving ROE trend. The output is a structured CSV ready for your qualitative follow-up on people, moat, and circle of competence.

## Contents

- `SKILL.md` — Skill definition, 4-dimensional scoring logic, and usage
- `scripts/screen.py` — A-share long-term structural value screener (CSV + terminal table)
- `references/zhang_lei_principles.md` — Zhang Lei's core principles: long-termism, dynamic moat, people as the ultimate risk control, heavy China / tech innovation, barbell strategy

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
- `--out`: CSV output path (default `zhang_lei_screen_result.csv`).

## 4-Dimensional Growth-Quality Radar

| Dimension | Metric | Notes |
|---|---|---|
| Sustained double growth | Years in last 5 with both revenue and net-profit growth > 0 | 4–5 years is best |
| Long-term reinvestment | R&D ratio or capex-to-revenue ratio | High and trending up means the company is betting on the future |
| Industry headroom | Latest annual revenue growth vs industry average | Outpacing the industry suggests structural share gain |
| ROE trend | 5-year ROE trajectory | Latest ROE above the 5-year mean and trending up is best |

## Output Fields

- `code` / `name` / `industry`: Stock code / name / industry
- `score_total`: Composite score (max 100)
- `score_growth` / `score_investment` / `score_industry` / `score_roe_trend`: Dimension scores
- `double_growth_years`: Years with both revenue and profit growth > 0
- `avg_rev_growth` / `avg_profit_growth`: 5-year average growth rates
- `rd_ratio_avg` / `capex_to_rev_avg`: Average R&D ratio / capex-to-revenue ratio
- `industry_avg_rev_growth` / `market_median_rev_growth`: Industry average / market median revenue growth
- `roe_latest` / `roe_5y`: Latest ROE / 5-year ROE series
- `data_years` / `source` / `note`: Valid years / data source / fallback notes

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always validate screening results through your own understanding of the business (circle of competence).
