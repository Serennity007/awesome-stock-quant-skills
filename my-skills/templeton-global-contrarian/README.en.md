# templeton-global-contrarian

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 (original work).

A-share Templeton-style global contrarian scanner: screen for stocks near 52-week lows, with PE/PB below the 10th percentile of their own history, volume-contracted stabilization, and still-positive earnings — producing a watchlist of pessimism-driven buying candidates.

## Contents

- `SKILL.md` — Skill definition and usage
- `scripts/contrarian_scan.py` — Batch scan for Templeton-style contrarian signals (CSV + terminal table)
- `references/templeton_rules.md` — Templeton's principle of maximum pessimism, 16 rules, global bargain hunting, and cycle view

## Quick Start

```bash
pip install akshare pandas

# Screening (default pool: CSI 300 constituents)
python scripts/contrarian_scan.py --pool hs300 --top 20 --out result.csv

# Custom pool
python scripts/contrarian_scan.py --codes 600519,000858,600036 --out result.csv
```

Dependencies: `akshare` 1.18.96, `pandas` (Python 3.11+).

## Disclaimer

For learning and research only; not investment advice. The scan output is only a watchlist — final decisions must rest on your own understanding of the business, industry cycle, and balance sheet (circle of competence).
