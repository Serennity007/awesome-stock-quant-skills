# 🚀 William O'Neil CANSLIM｜A 7-Letter Checklist Screener for A-Shares

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (Sina / East Money public APIs)

> **"All the great stocks in history exploded out of chart bases with identifiable common characteristics."**

This skill mechanizes William O'Neil's (*How to Make Money in Stocks*) CANSLIM system for A-shares: C (quarterly earnings yoy ≥25%), A (annual growth), N (within 15% of the 250-day high), S (volume surge), L (excess relative strength vs CSI 300), I (institutional holdings), M (market trend vs 50-day MA) — letter-by-letter pass table plus scores (max 100), with an in-pool RPS percentile in pool mode. Complementary to the value-style skills: momentum names score high here, steady compounders don't — by design.

## Contents

- `SKILL.md` — Skill definition, 7-letter scoring logic, and usage
- `scripts/screen.py` — A-share CANSLIM screener (CSV + terminal table)
- `references/oneil_canslim_rules.md` — O'Neil's rules: the 7 letters in depth, cup-with-handle, sell discipline and the 7% stop-loss
- `canslim_test_result.csv` — Small-sample test output

## Quick Start

```bash
pip install akshare pandas

# Default pool: CSI 300 constituents, top 20 output (with RPS percentile)
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# Custom small pool for testing
python scripts/screen.py --codes 600519,300760,002415 --out result.csv
```

## 7-Letter Scorecard

| Letter | Standard | Weight |
|---|---|---|
| C | Latest quarter net-profit yoy ≥25% scores full | 20 |
| A | 3-year average annual profit growth ≥25% scores full | 15 |
| N | Close within 15% of the 250-day high scores full | 15 |
| S | 5-day vs 60-day average volume ratio ≥1.5 scores full | 10 |
| L | 120-day excess return over CSI 300 ≥30pp scores full | 20 |
| I | Institutional holdings ≥10% of float scores full; neutral 5 if no data | 10 |
| M | CSI 300 close above its 50-day MA (pool-wide) | 10 |

Verdict lines: **≥70 with C/A/N/L all passed → CANSLIM candidate** (see `passed_letters`); **50–69 watch list**; **<50 outside the framework**.

## Output Fields

- `code` / `name` / `industry` / `total` / `passed_letters`: Basics and the letter pass table
- `C_score` / `A_score` / `N_score` / `S_score` / `L_score` / `I_score` / `M_score`: Letter scores
- `quarter_yoy` / `annual_growth_3y` / `dist_from_250d_high` / `vol_ratio_5_60` / `excess_ret_120d` / `inst_hold_ratio`: Raw metrics
- `rps_percentile`: In-pool RPS percentile (pool mode only)
- `close` / `a_source` / `note` / `data_date`: Auxiliary info

## Data Sources & Fallbacks

Sina daily bars (forward-adjusted) + East Money earnings reports (quarterly yoy, one pool-level call) + East Money institutional holdings (neutral score when unavailable) + Sina index daily for M; annual growth falls back to Sina income statements; system proxies disabled at startup, exponential-backoff retries on all network calls.

## Disclaimer

For learning and research only; not investment advice. CANSLIM is a high-turnover growth-momentum system; historical patterns do not guarantee future results.
