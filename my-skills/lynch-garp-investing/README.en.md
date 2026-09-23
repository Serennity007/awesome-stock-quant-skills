# 🚀 Peter Lynch GARP / Ten-Bagger A-Share Screener | Shop for Stocks Like Lynch

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / 10jqka / Tencent public APIs)

Peter Lynch turned stock-picking into a trip to the supermarket: start with products, services, and brands you know, then find growth at a reasonable price. This skill automates that lens for A-shares: it computes PEG, consecutive profit growth, debt ratio, and ROE stability, labels each stock with one of Lynch's six categories (Slow Grower / Stalwart / Fast Grower / Cyclical / Turnaround / Asset Play), and outputs a structured table ready for deeper AI analysis.

## Quick start

```bash
pip install akshare pandas

# Default CSI 300 pool, top 20
python scripts/screen.py --pool hs300 --top 20 --out garp_result.csv

# Custom small pool for a quick test
python scripts/screen.py --codes 600519,000858,600036 --out garp_result.csv
```

## Screening criteria

| Dimension | Great | Acceptable | Note |
|---|---|---|---|
| PEG | < 1.0 | < 1.5 | PE(TTM) / earnings growth; if latest growth is negative, a reference PEG based on 5-year average is provided |
| Consecutive profit growth | ≥ 3 years | ≥ 2 years | Latest N years of positive net-profit growth |
| Debt ratio | < 40% | < 60% | Default `--max-debt 60`; banks and other leveraged sectors need separate judgment |
| ROE | > 15% | > 10% | Relatively stable over 5 years |
| Lynch label | Fast Grower / Stalwart | Asset Play / Turnaround | Cyclicals and Slow Growers need extra caution |

## Output fields

| Field | Description |
|---|---|
| `code` / `name` | Stock code / short name |
| `score` | Composite GARP score (max 100) |
| `lynch_tag` | One of Lynch's six categories |
| `garp_pass` | Meets PEG<1, consecutive profit growth ≥2 years, debt ratio below threshold |
| `peg` / `peg_note` | Computed PEG and note |
| `pe_ttm` / `pb` | Current PE(TTM) and price-to-book |
| `avg_profit_growth` | 5-year average net-profit growth |
| `consecutive_profit_years` | Consecutive years of positive profit growth |
| `debt_ratio` / `roe_latest` | Debt ratio / latest ROE |
| `industry` | Industry classification |

## Files

- `SKILL.md` — Skill definition and usage
- `scripts/screen.py` — GARP screener script
- `references/lynch_principles.md` — Summary of Lynch's ten-bagger methodology

## Disclaimer

For study and research only — not investment advice. Historical financial metrics do not guarantee future performance. Lynch labels are mechanical tags; real decisions require business understanding, industry-cycle judgment, and risk-appetite confirmation.
