# 🌡️ A-Share Cycle Gauge | Howard Marks Pendulum Positioning

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (legulegu / CSIndex / East Money public APIs)

Be fearful when others are greedy, and greedy when others are fearful — but first you need a thermometer. This skill turns Howard Marks’s cycle thinking into a quantified A-share dashboard: CSI 300 / CSI All Share valuation percentiles, equity-bond yield spread, turnover heat, and margin-balance trend are combined into a single **0-100 cycle-position score** (0 = ice-cold, 100 = overheated), plus an action framework.

## Quick start

```bash
pip install akshare pandas

# Default: today, 10-year lookback
python scripts/cycle_gauge.py

# With sample stocks
python scripts/cycle_gauge.py --codes 600519,000858,600036 --out cycle_gauge.csv

# Backtest a historical date
python scripts/cycle_gauge.py --date 2023-12-31 --lookback 5 --out 2023_gauge.csv
```

Verified on Python 3.11 + akshare 1.18.96 + pandas.

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `--date` | today | Report date, accepts `20231231` or `2023-12-31` |
| `--lookback` | 10 | Years of history for percentile calculation |
| `--codes` | — | Comma-separated sample stock codes (observation only) |
| `--out` | `cycle_gauge.csv` | CSV output path |
| `--no-proxy` | — | Backward-compatible flag; proxies are disabled by default |

> Proxy note: the script clears `HTTP_PROXY` / `HTTPS_PROXY` etc. on startup to avoid local proxies (e.g. `127.0.0.1:7890`) blocking the data sources.

## Output fields

The CSV is a long-format table for easy parsing:

| category | item | value | score | note |
|---|---|---|---|---|
| GAUGE | cycle_position | composite score | 0-100 | action suggestion |
| COMPONENT | valuation / spread / turnover / margin | current value | sub-score | calculation note |
| INDEX | CSI300_PE-TTM, CSI300_PB, CSI_AllShare_PE-TTM, etc. | current valuation | historical percentile | — |
| SAMPLE | code + name | close / PE / PB | — | sample observation |

## Scoring logic

- **Valuation (30%)**: historical percentiles of CSI 300 PE/PB and CSI All Share PE; higher percentile = hotter. Broad-market PB is proxied by CSI 800 PB because CSI All Share historical PB is unavailable.
- **Equity-bond spread (25%)**: CSI All Share earnings yield minus 10-year Chinese government bond yield. A higher spread means equities are cheap relative to bonds, so the score moves colder.
- **Turnover heat (25%)**: CSI All Share turnover amount vs 20-day / 60-day averages; elevated turnover = hotter.
- **Margin trend (20%)**: total market margin balance vs recent trends; rising = hotter.

## Files

- `SKILL.md` — Skill definition and usage
- `scripts/cycle_gauge.py` — Main cycle gauge script
- `references/marks_memos.md` — Howard Marks core ideas (second-level thinking, cycles/contrarianism, risk)

## Disclaimer

For study and research only — not investment advice. Cycle positioning is based on historical statistics, not future performance. Always verify scores and action suggestions against your own risk appetite and independent judgment.
