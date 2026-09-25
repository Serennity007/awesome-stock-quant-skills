# 🧮 Simons-Style Factor Quant｜5-Dimensional Signals for A-Share Short-Term Statistical Patterns

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina public APIs)

> **Signals over narratives, data over intuition.**

This skill is inspired by the published investment philosophy of James Simons and the Medallion Fund. It converts A-share market data into five quantifiable statistical signals—momentum, reversal, low volatility, volume trend, and moving-average deviation. `scripts/factor_scan.py` scores each stock in a universe and outputs a composite factor ranking for further portfolio validation and risk-control design.

> ⚠️ The Medallion Fund's real models are not public. This skill is a stylized learning framework only and is not investment advice.

## Contents

- `SKILL.md` — Skill definition, 5-dimensional factor logic, and usage
- `scripts/factor_scan.py` — A-share multi-factor scanner (CSV + terminal table)
- `references/simons_methods.md` — Learning notes on James Simons / Medallion Fund thinking

## Quick Start

```bash
pip install akshare pandas

# Default pool: CSI 300 constituents, top 20 output
python scripts/factor_scan.py --pool hs300 --top 20 --out result.csv

# Custom small pool for testing
python scripts/factor_scan.py --codes 600519,000858,600036 --top 10 --out result.csv
```

## Parameters

- `--pool`: Stock universe; currently supports `hs300`.
- `--codes`: Comma-separated custom codes; takes precedence over `--pool`.
- `--top`: Number of top results to display (default 20).
- `--out`: CSV output path (default `simons_factor_result.csv`).
- `--end-date`: End date, accepts both `20231231` and `2023-12-31` (default today).
- `--lookback`: Calendar days to look back (default 150).

## 5-Dimensional Factor Radar

| Dimension | Proxy Metric | Notes |
|---|---|---|
| Momentum | 20-day & 60-day returns | Trend continuation score |
| Reversal | Negative 5-day return | Short-term oversold mean-reversion candidate |
| Low volatility | Negative 20-day annualized volatility | Low-vol anomaly, risk control |
| Volume trend | 5-day avg volume / 20-day avg volume | Volume confirming price action |
| MA deviation | Negative absolute price-to-60-day-MA deviation | Smaller deviation favored |

## Output Fields

- `code / name`: Stock code and name
- `total`: Composite factor score (0–100)
- `momentum_score / reversal_score / volatility_score / volume_score / ma_deviation_score`: Five dimension scores
- `ret_5d / ret_20d / ret_60d / vol_20d_annual / volume_ratio_5_20 / ma60_deviation`: Raw factor values
- `close / latest_date`: Latest close price and date
- `data_days / source`: Valid data length and data source

## Disclaimer

For learning and research only; not investment advice. Historical price patterns and statistical regularities do not guarantee future performance. Always validate screening results through independent research and assess your own risk tolerance. The Medallion Fund's real strategies are not public; this skill is a stylized educational tribute.
