# 🔥 A-Share Hot Theme Scanner | Spot the Strongest Market Narrative in Seconds

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / 10jqka public APIs)

Start your trading day with this heatmap. Built around 10 current hot-theme dictionaries — storage, optical modules, PCB, MLCC, commercial aerospace, controlled nuclear fusion, solid-state batteries, innovative drugs, and military restructuring — it scans board gains, main-force capital flow, and leading stocks, then outputs a structured table of theme × gain × capital flow × leader, so you can see where A-share money is flowing at a glance.

## Quick start

```bash
pip install akshare pandas

# Default: 5-day window, top 20, output CSV
python scripts/hot_themes.py --days 5 --top 20 --out hot_themes.csv

# Intraday ranking only
python scripts/hot_themes.py --days 1 --top 15
```

## Parameters

- `--days`: Window length, supports 1/3/5/10 (default 5); falls back to the nearest available window
- `--top`: Rank threshold to be considered hot (default 20)
- `--out`: CSV output path (default `hot_themes.csv`)
- `--no-proxy`: Disable system proxy (the script already bypasses system proxies by default; kept for backward compatibility)

> Proxy note: on startup the script clears `HTTP_PROXY` / `HTTPS_PROXY` environment variables to avoid local proxies (e.g. `127.0.0.1:7890`) blocking East Money / 10jqka APIs. It tries East Money first and falls back to 10jqka if unavailable.

## Output fields

| Field | Description |
|---|---|
| `题材` | Built-in hot theme name |
| `匹配板块` | Matched akshare concept board name |
| `阶段涨幅%` | Theme change over the selected window |
| `主力净流入（亿元）` | Main-force net inflow over the selected window |
| `领涨股` | Leading stock in the window |
| `领涨股涨幅%` | Leading-stock change |
| `连续上榜天数` | Estimated consecutive days in the top N of 1/3/5/10-day rankings |

## Files

- `SKILL.md` — Skill definition and usage
- `scripts/hot_themes.py` — Hot-theme scanner script
- `references/theme_glossary.md` — Current hot-theme glossary (time-sensitive, update regularly)

## Disclaimer

For study and research only — not investment advice. Theme heat is derived from historical capital-flow and price statistics, not future performance; always verify results against your own understanding of the business and risk appetite.
