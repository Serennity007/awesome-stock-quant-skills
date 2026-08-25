# buffett-value-investing

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 (original work).

A-share Buffett-style value investing skill: moat assessment, 5-year ROE / gross margin / debt ratio / free cash flow screening, and margin-of-safety valuation.

## Contents

- `SKILL.md` — Skill definition and usage
- `scripts/screen.py` — Batch screening by Buffett criteria with scoring (CSV + terminal table)
- `scripts/analyze.py` — Single-stock full analysis (moat checklist + financial trends + valuation range)
- `references/buffett_principles.md` — Summary of Buffett's core principles
- `references/scoring_rules.md` — Scoring rules and known limitations

## Quick Start

```bash
pip install akshare pandas

# Screening (default pool: CSI 300 constituents)
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# Custom pool
python scripts/screen.py --codes 600519,000858,600036

# Single-stock analysis
python scripts/analyze.py 600519
```

Dependencies: `akshare`, `pandas` (Python 3.9+).

## Disclaimer

For learning and research only; not investment advice. Scoring is just a first-pass filter — final decisions must rest on your own understanding of the business (circle of competence).
