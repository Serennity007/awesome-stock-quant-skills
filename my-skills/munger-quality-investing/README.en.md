# 🧠 Munger-Style Quality Investing｜A 5-Dimensional Radar for Great A-Share Companies

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / Sina public APIs)

> **It is better to buy a great company at a fair price than a fair company at a great price.**

This skill brings Charlie Munger's quality-investing framework to the A-share market. No hot-theme chasing, no chart guessing—just five financial yardsticks applied consistently to identify companies with the characteristics of "great businesses," which you then validate with qualitative analysis (moat, management, circle of competence).

## Contents

- `SKILL.md` — Skill definition, 5-dimensional scoring logic, and usage
- `scripts/screen.py` — A-share quality screener (CSV + terminal table)
- `references/munger_checklist.md` — Munger's latticework of mental models, inversion, circle of competence, 25 cognitive biases, and investment checklist

## Quick Start

```bash
pip install akshare pandas

# Default pool: CSI 300 constituents, top 20 output
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# Custom small pool for testing
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

## Parameters

- `--pool`: Stock universe; currently supports `hs300`.
- `--codes`: Comma-separated custom codes; takes precedence over `--pool`.
- `--top`: Number of top results to display (default 20).
- `--out`: CSV output path (default `munger_screen_result.csv`).

## 5-Dimensional Quality Radar

| Dimension | Metric | Notes |
|---|---|---|
| Capital returns | 5-year ROIC-style indicator | Proxied by ROE because akshare does not expose ROIC directly |
| Gross margin | 5-year mean and stability | Best: mean >40% and swing <3 percentage points |
| Low leverage | Latest debt-to-asset ratio | Full points if <30%; financials need separate judgment |
| Earnings quality | Operating cash flow / net profit ratio | Mean >1.0 means profits are backed by cash |
| Low dilution | 5-year total share growth | Full points if <5%; beware frequent equity raises |

## Output Fields

- `code`: Stock code
- `total`: Composite score (max 100)
- `roic_score / roic_annual`: Capital-return score / 5-year ROE series
- `gross_score / gross_mean / gross_annual`: Gross-margin score / mean / series
- `debt_score / debt_latest`: Leverage score / latest debt ratio
- `quality_score / quality_mean`: Earnings-quality score / mean OCF-to-profit ratio
- `dilution_score / shares_growth_pct`: Dilution score / share-count growth
- `data_years`: Number of years with valid data
- `source / note`: Data source and fallback notes

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always validate screening results through your own understanding of the business (circle of competence).
