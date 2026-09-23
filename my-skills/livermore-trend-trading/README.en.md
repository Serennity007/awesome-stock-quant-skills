# 🎯 Livermore Trend Speculation in A-Shares | 5 Disciplines for Key Breakouts and Stop-Losses

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina public APIs)

"The big money is made by sitting — not thinking." This skill turns Jesse Livermore's trend-speculation discipline into a mechanical scanner: it identifies **N-day new-high pivotal-point breakouts, volume-confirmed thrusts, low-volume pullbacks for secondary entries**, and warns of **one-day reversal / volume-stagnation** danger signals. It also outputs a **pyramid position-probe framework** so that "probe → confirm → add" becomes a set of numbers rather than a feeling.

## Quick start

```bash
pip install akshare pandas

# Default: 3 sample stocks, last 250 trading days, 60-day breakout window
python scripts/pivotal_points.py --codes 600519,000858,600036 --out signals.csv

# Shorter window for more recent breakouts
python scripts/pivotal_points.py --codes 600519,000858 --days 120 --window 30 --out signals.csv
```

## Parameters

- `--codes`: Comma-separated 6-digit A-share codes (required)
- `--days`: Number of recent trading days to load (default 250)
- `--window`: N-day new-high breakout window (default 60)
- `--out`: CSV output path (default `livermore_signals.csv`)
- `--no-proxy`: Disable system proxy (the script already bypasses system proxies by default; kept for backward compatibility)

> Proxy note: on startup the script clears `HTTP_PROXY` / `HTTPS_PROXY` environment variables to avoid local proxies (e.g. `127.0.0.1:7890`) blocking East Money / Sina APIs. It tries the East Money daily-history API first and falls back to Sina daily data if unavailable.

## Output fields

| Field | Description |
|---|---|
| `code` | 6-digit stock code |
| `name` | Stock name |
| `date` | Signal date |
| `close` | Latest closing price |
| `close_chg_pct` | Daily change (%) |
| `volume_ratio` | Volume / 20-day average volume |
| `ma20` | 20-day moving average |
| `ma60` | 60-day moving average |
| `window_high` | Highest close within the breakout window |
| `dist_to_high_pct` | Distance from current price to the window high (%) |
| `signals` | Triggered signals, comma-separated |
| `position_plan` | Pyramid position-sizing suggestion based on the signal |

## Signal meanings

| Signal | Meaning |
|---|---|
| `KEY_BREAKOUT` | Volume-confirmed breakout to an N-day new high |
| `WEAK_BREAKOUT` | New high without sufficient volume; watch for false breakout |
| `PULLBACK_ENTRY` | Low-volume pullback to MA20 within an uptrend |
| `ONE_DAY_REVERSAL` | One-day reversal: sharp intraday rally reversed, close near the low |
| `VOLUME_STAGNATION` | Volume surge with little price progress and an upper shadow |
| `NO_SIGNAL` | No clear signal |

## Files

- `SKILL.md` — Skill definition and usage
- `scripts/pivotal_points.py` — Trend-speculation signal scanner
- `references/livermore_rules.md` — Summary of Livermore's principles

## Disclaimer

For study and research only — not investment advice. Historical price action does not predict future performance. Mechanical signals must be combined with market context, fundamentals, and risk management. Any trading decision is the user's own responsibility.
