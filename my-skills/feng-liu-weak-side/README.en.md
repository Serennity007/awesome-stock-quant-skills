# 🥊 Feng Liu Weak-Side Investing｜Buy When Nobody Wants It: A 4-Dimension Contrarian Screener for A-Shares

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / 10jqka / Sina public APIs)

> **Assume you are the weakest information receiver in the market: odds first, buy against the crowd, concentrate—but admit mistakes fast.**

This skill brings Feng Liu's "weak-side" contrarian framework to the A-share market. No chasing hot themes, no racing for faster information—just a systematic hunt for stocks that have fallen hard but are not dead. The core script `scripts/screen.py` scores candidates across four dimensions—drawdown, valuation, fundamentals, and attention—and labels each with an **odds / probability** framework.

## Contents

- `SKILL.md` — Skill definition, 4-dimension scoring logic, and usage
- `scripts/screen.py` — A-share weak-side contrarian screener (CSV + terminal table)
- `references/feng_liu_framework.md` — Core ideas of the weak-side system: weak-player assumption, odds-first thinking, contrarian buying, concentrated positions, fast mistake admission, and value-trap recognition

## Quick Start

```bash
pip install akshare pandas

# Default pool: CSI 300 constituents, top 20 output
python scripts/screen.py --pool hs300 --top 20 --out weak_side_result.csv

# Custom small pool for testing
python scripts/screen.py --codes 600519,000858,600036 --out weak_side_result.csv
```

## Parameters

- `--pool`: Stock universe; currently supports `hs300`.
- `--codes`: Comma-separated custom codes; takes precedence over `--pool`.
- `--top`: Number of top results to display (default 20).
- `--out`: CSV output path (default `weak_side_result.csv`).

## 4-Dimension Contrarian Radar

| Dimension | Metric | Notes |
|---|---|---|
| Odds (drawdown) | Drawdown from 52-week high | > 40% drawdown is treated as a high-odds starting point |
| Odds (valuation) | PE/PB 3-year percentile | < 20% percentile is treated as historically cheap |
| Probability (fundamentals) | Positive profit, revenue/profit not collapsing, ROE/debt under control | Excludes permanent-fundamental-deterioration value traps |
| Low attention | Turnover (%) | Lower turnover means the market has forgotten or hates it |

## Output Fields

- `code` / `name` / `industry`: Code / name / industry
- `close` / `high_52w` / `drawdown_pct`: Current price / 52-week high / drawdown
- `pe_ttm` / `pb` / `pe_percentile_3y` / `pb_percentile_3y`: Valuation and 3-year percentile
- `turnover_pct`: Latest turnover (%)
- `latest_revenue` / `latest_profit` / `revenue_yoy` / `profit_yoy`: Latest report revenue/profit (100M CNY) and YoY growth
- `weak_score` / `odds_label` / `probability_label`: Composite score / odds label / probability label
- `framework_note`: Explanation of odds and probability sources
- `weak_pass`: Whether the hard threshold is met

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always validate screening results through your own understanding of the business (circle of competence). Contrarian investing carries risks such as value traps, liquidity traps, and long-term industry decline; please exercise independent judgment.
