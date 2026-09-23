# 🦎 Macro Chameleon | Druckenmiller-Style Flex Dashboard

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (BOC / Sina / East Money / 10jqka public APIs)

Check the global capital wind direction before the market opens. This skill frames a Stanley Druckenmiller-style macro view into a single trend-following snapshot covering **7 asset classes**: USD/CNY, China/US 10-year Treasury yields, gold, crude oil, copper, major A-share indices, and optional individual stocks. The output is not a trading signal — it is a long/short bias snapshot from a trend-follower's perspective.

## Quick start

```bash
pip install akshare pandas

# Default 20-day window, output macro_dashboard.csv
python scripts/macro_dashboard.py

# Custom window + output
python scripts/macro_dashboard.py --days 20 --out macro_dashboard.csv

# Add optional stock codes
python scripts/macro_dashboard.py --days 20 --codes 600519,000858,600036 --out my_dashboard.csv
```

## Parameters

- `--days`: Trend/momentum window in trading days (default 20)
- `--codes`: Comma-separated A-share stock codes (optional)
- `--out`: CSV output path (default `macro_dashboard.csv`)
- `--no-proxy`: Disable system proxy (the script already bypasses proxies by default; kept for backward compatibility)

> Proxy note: on startup the script clears `HTTP_PROXY` / `HTTPS_PROXY` environment variables to avoid local proxies (e.g. `127.0.0.1:7890`) blocking data sources. It tries East Money / primary APIs first and falls back to Sina / BOC / 10jqka if unavailable.

## Output fields

| Field | Description |
|---|---|
| `asset` | Asset name |
| `category` | Asset category (fx / bond_cn / bond_us / commodity / equity / stock) |
| `current` | Latest close / yield / rate |
| `ma_n` | N-day moving average |
| `roc_n` | N-day return % |
| `roc_5` | Latest 5-day return % |
| `trend` | Trend description (rising / falling / choppy / turning) |
| `signal` | Trend signal (BULLISH / BEARISH / NEUTRAL) |
| `bias` | Long/short bias description (e.g. "USD bearish", "China bonds bullish") |
| `source` | Actual data source used |

## Logic

```
BULLISH = close > N-day MA  and  N-day return > 0
BEARISH = close < N-day MA  and  N-day return < 0
NEUTRAL = otherwise
```

Bond-yield direction is opposite to bond-price direction: rising yield = bearish for bonds. The script ends with an aggregate macro score and an overall stance hint.

## Files

- `SKILL.md` — Skill definition and full usage notes
- `scripts/macro_dashboard.py` — Macro dashboard script
- `references/druckenmiller_style.md` — Summary of Druckenmiller's investment principles

## Disclaimer

For study and research only — not investment advice. Macro trends and momentum are derived from historical price statistics, not future performance; always verify results against your own understanding of the macro environment, liquidity, and risk appetite.
