# 🚀 US Hot AI Stocks Tracker | 8-Ticker Momentum Snapshot

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 (original) | License: MIT | Data: akshare (Sina Finance US stock daily bars)

Track the US AI money flow on one screen. Covers 8 core tickers — NVDA, AVGO, ORCL, GOOGL, SNDK, WDC, PLTR, TSLA — based on akshare Sina Finance US daily bars, and mechanically outputs price, daily change, 20/60-day momentum, 52-week position, and volume anomaly, sorted by 20-day momentum so you can instantly see who is leading and who is lagging.

## Quick start

```bash
pip install akshare pandas

# Default watchlist (AI compute / storage / AI application / robotaxi)
python scripts/us_hot.py

# Custom tickers
python scripts/us_hot.py --tickers NVDA,AAPL,MSFT,AMD

# Output CSV
python scripts/us_hot.py --out us_hot.csv
```

## Default watchlist

| Theme | Tickers | Key figure |
|---|---|---|
| AI compute | NVDA, AVGO, ORCL, GOOGL | Jensen Huang (NVDA) |
| Storage | SNDK, WDC | — |
| AI application | PLTR | Alex Karp |
| robotaxi / personality play | TSLA | Elon Musk |

See `references/watchlist.md` for theme notes, key figures, recent catalysts, and risk reminders.

## Output fields

| Field | Description |
|---|---|
| `ticker` | Stock symbol |
| `theme` | Theme tag |
| `price` | Latest closing price (unadjusted daily close, `adjust=""`) |
| `change_pct` | Change from previous close (%, based on unadjusted closes) |
| `mom_20` | 20-day momentum (%, based on forward-adjusted closes) |
| `mom_60` | 60-day momentum (%, based on forward-adjusted closes) |
| `dist_52w_high` | Distance from the 252-day high (%, based on adjusted highs/lows) |
| `dist_52w_low` | Distance from the 252-day low (%, based on adjusted highs/lows) |
| `vol_ratio` | Latest volume / 20-day average volume (based on unadjusted volume) |

## Files

- `SKILL.md` — Skill definition and usage
- `scripts/us_hot.py` — Main script (supports `--tickers`, `--out`, `--sort`)
- `references/watchlist.md` — Theme tags, key figures, and recent catalysts for each ticker

## Data notes

- Daily bars come from akshare `stock_us_daily` (Sina Finance US stocks).
- Current price, change %, and volume use **unadjusted** daily bars (`adjust=""`) to avoid price distortions caused by faulty adjustment factors.
- 20/60-day momentum and 52-week high/low distance use **forward-adjusted** daily bars (`adjust="qfq"`) for long-term comparability.

## Disclaimer

For educational and research purposes only — not investment advice. Historical prices and momentum do not guarantee future performance. Any trading decision must be based on your own assessment of fundamentals, market conditions, and risk tolerance.
