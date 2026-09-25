# 🔻 Klarman Margin of Safety｜4 Yardsticks for Deep Value Opportunities in A-Shares

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina public APIs)

> **Risk before return, cash is an option, cheap is only the starting point, and a catalyst is the ticket back to fair value.**

This skill brings Seth Klarman's risk-averse deep-value framework from *Margin of Safety* to the A-share market. No theme chasing, no chart guessing—just a disciplined hunt for stocks trading well below a conservative estimate of intrinsic value, with a plausible path back to that value.

## Contents

- `SKILL.md` — Skill definition, 4-dimensional scoring logic, and usage
- `scripts/deep_value.py` — A-share deep-value screener (CSV + terminal table)
- `references/klarman_principles.md` — Core ideas from *Margin of Safety*: absolute return, risk first, catalyst-driven, cash as an option, contrarian independence

## Quick Start

```bash
pip install akshare pandas

# Default pool: CSI 300 constituents, top 20 output
python scripts/deep_value.py --pool hs300 --top 20 --out result.csv

# Custom small pool for testing (recommended)
python scripts/deep_value.py --codes 600519,000858,600036 --out result.csv
```

## Parameters

- `--pool`: Stock universe; currently supports `hs300`.
- `--codes`: Comma-separated custom codes; takes precedence over `--pool`.
- `--top`: Number of top results to display (default 20).
- `--out`: CSV output path (default `klarman_screen_result.csv`).

## 4-Dimensional Deep-Value Radar

| Dimension | Metric | Notes |
|---|---|---|
| PB absolute & historical percentile | Current PB, 5-year PB percentile | Highest score when PB<1 or at historical lows |
| Low PE percentile | 5-year PE(TTM) percentile | Lower percentile = higher score |
| Market cap / net cash | Market cap ÷ (cash - interest-bearing debt) | <1 means market cap below net cash, a thick cushion |
| 52-week high drawdown | Current price vs 52-week high | Klarman loves opportunities created by price declines |
| Risk filter | ST / latest annual loss | Forced to 0 points |

> For banks, real estate, and other highly leveraged sectors the "net cash" concept is not meaningful; the script marks it as missing but still scores PB/PE/drawdown.

## Output Fields

- `code / name`: Stock code and name
- `total`: Composite margin-of-safety score (max 100)
- `pb_score / pb / pb_percentile`: PB score / current PB / 5-year percentile
- `pe_score / pe / pe_percentile`: PE score / current PE / 5-year percentile
- `netcash_score / market_cap / net_cash / market_cap_to_net_cash`: Net-cash dimension
- `drawdown_score / current_price / high_52w / drawdown_pct`: Drawdown dimension
- `is_st / is_loss`: Risk flags
- `val_source / price_source`: Data source and fallback notes

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always validate screening results through your own understanding of the business (circle of competence) and a conservative intrinsic-value estimate.
