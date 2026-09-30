# 📊 Master-Framework Backtest Validator｜Monthly-Rebalanced Evidence for the Master Frameworks

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina public APIs) + local cache

> **"A backtest is the demon-revealing mirror of a strategy — returns you can't show are just stories."**

This skill turns the repo's master frameworks into **falsifiable strategies**: score the whole pool at each month-end → equal-weight the top N → hold to next month-end → compare cumulative NAV against CSI 300. Scoring is strictly point-in-time (only annual reports published ≥120 days prior + contemporaneous valuations), no look-ahead. v1 supports danbin (6-dim), lilu (6-dim), and mom12_1 (12-1 month momentum benchmark).

## Contents

- `SKILL.md` — Skill definition, backtest conventions, and usage
- `scripts/fetch_history.py` — Per-stock history cacher (valuation / annual indicators / income statement; resumable, chunkable)
- `scripts/backtest.py` — Monthly-rebalance backtest engine
- `references/backtest_methodology.md` — Methodology: point-in-time principle, survivorship bias, why relative comparison is the honest read
- `results/` — Backtest outputs (summary / monthly NAV / yearly table)
- `cache/` — Data cache (.gitignored)

## Quick Start

```bash
pip install akshare pandas numpy

# Step 1: fetch pool history (~25 min, resumable)
python scripts/fetch_history.py --pool hs300

# Step 2: backtest all three frameworks
python scripts/backtest.py
```

## Known Limitations (read before reading results)

1. **Survivorship bias**: the universe is fixed to today's CSI 300 — absolute returns are systematically flattered; **use for cross-framework comparison only**.
2. No transaction costs (~1-2pp/year for monthly top-10 turnover).
3. PE/PB history starts ~2018.
4. Annual-report publication lag approximated at 120 days.

## Disclaimer

For learning and research only; not investment advice. Backtested returns do not represent future results.
