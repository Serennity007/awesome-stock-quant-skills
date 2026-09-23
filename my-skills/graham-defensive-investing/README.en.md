# 🛡️ A-Share Graham Defensive Screener | 7 Gates to Protect Your Capital

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina Finance public APIs)

Bring Benjamin Graham's defensive stock-selection framework to the A-share market. This tool applies seven quantitative gates — size, current ratio, earnings stability, dividend record, earnings growth, PE < 15, and PB < 1.5 or PE × PB < 22.5 — to screen stocks mechanically. It automatically labels whether the data window is 10 years or downgraded to 5 years, so you can quickly see which names meet Graham's "first, do no harm" standard.

## Quick start

```bash
pip install akshare pandas

# Screen CSI 300 constituents
python scripts/screen.py --pool hs300 --top 20 --out graham_result.csv

# Small-sample test
python scripts/screen.py --codes 600519,000858,600036 --out graham_result.csv
```

## Parameters

- `--pool`: Stock universe; currently supports `hs300`
- `--codes`: Comma-separated custom stock codes; overrides `--pool`
- `--top`: Number of top results to display (default 20)
- `--out`: CSV output path (default `graham_result.csv`)
- `--min-cap`: Minimum total market cap in CNY 100 million (default 200)
- `--sleep`: Delay between stocks in seconds (default 0.5, for rate-limiting)

## The 7 defensive gates

| Gate | Criterion |
|---|---|
| Adequate size | Total market cap ≥ CNY 20 billion (adjustable) |
| Current ratio | Latest annual current ratio > 2 |
| Earnings stability | Positive ex-nonrecurring EPS every year in the window |
| Dividend record | Cash dividend paid every year in the window |
| Earnings growth | End-of-window EPS / start-of-window EPS > 4/3 |
| Low PE | PE (static) < 15 |
| Low PB | PB < 1.5 or PE × PB < 22.5 |

> If 10 years of data are unavailable, the script downgrades to a 5-year window and labels it; fewer than 5 years is marked `NA`.

## Files

- `SKILL.md` — Skill definition and detailed usage
- `scripts/screen.py` — Graham defensive screener script
- `references/graham_principles.md` — Graham core principles: margin of safety, Mr. Market, defensive vs. enterprising investing, cigar-butt risk

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always verify screening results with your own understanding of the business and its valuation.
