# 🎯 John Bogle Index Investing｜A-Share Index Valuation Thermometer + DCA Backtest

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (LeguLegu / Sina / Tencent public APIs)

> **"Don't look for the needle in the haystack. Just buy the haystack."**

This skill mechanizes John Bogle's (Vanguard founder, father of index investing) framework for A-shares: a PE/PB 10-year-percentile valuation thermometer for broad indexes, the three-component Bogle expected-return decomposition (dividend yield + earnings growth + valuation reversion), a DCA pacing guide, and a monthly-DCA vs lump-sum backtest. Supports CSI 300 / CSI 500 / SSE 50 / CSI 1000.

## Contents

- `SKILL.md` — Skill definition, thermometer rules, and usage
- `scripts/index_thermometer.py` — Index valuation thermometer + DCA backtest (CSV + terminal table)
- `references/bogle_principles.md` — Bogle's philosophy: cost, diversification, discipline, the Bogle formula, mean reversion
- `bogle_test_result.csv` — Full-index test output (with DCA backtest)

## Quick Start

```bash
pip install akshare pandas

# Thermometer for all supported indexes
python scripts/index_thermometer.py --out bogle_thermometer.csv

# Single index + 5-year monthly DCA backtest
python scripts/index_thermometer.py --index 沪深300 --dca --years 5 --out result.csv

# Calibrate Bogle formula assumptions (dividend yield / earnings growth)
python scripts/index_thermometer.py --div 3.0 --growth 6.0
```

## DCA Pacing Guide

| PE 10-year percentile | Pacing |
|---|---|
| < 20% | Cold: double your monthly investment |
| 20–40% | Cool: invest as usual, slightly aggressive |
| 40–60% | Neutral: invest as usual |
| 60–80% | Warm: halve new purchases |
| ≥ 80% | Hot: pause new purchases (keep holding) |

## Output Fields

- `pe_ttm` / `pe_pct_10y` / `pe_pct_all` / `pe_median_10y`: Current PE and historical percentiles
- `pb` / `pb_pct_10y`: PB and percentile
- `temperature` / `action`: Thermometer reading and pacing guide
- `bogle_expected_return` / `speculative_component`: Expected-return decomposition
- `dca_annualized` / `lumpsum_annualized` / `period_max_drawdown`: DCA and lump-sum backtest results

## Disclaimer

For learning and research only; not investment advice. Dividend yield and earnings growth are assumption parameters; valuation percentiles do not predict future returns.
