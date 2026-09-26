# 🍶 Lin Yuan-Style Monopoly + Addictive Consumer Investing｜Only "Mouth-Related Necessity Moats"

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

Author: Serennity007 | License: MIT | Data: akshare (East Money / CNINFO / Tencent public APIs)

> **"I only invest in mouth-related, addictive, monopolistic companies whose gross margin is the only metric that never lies."**

This skill brings Lin Yuan's publicly stated investment framework to the A-share market. No hot-theme chasing, no chart guessing—just four financial yardsticks applied consistently: **mouth-related necessities, gross margin >50%, persistently high ROE, and high dividend yield**. The screener identifies candidates with "monopoly + addiction" characteristics, which you then validate with qualitative analysis (moat, valuation, circle of competence).

## Contents

- `SKILL.md` — Skill definition, 4-rule scoring logic, and usage
- `scripts/screen.py` — A-share Lin Yuan-style screener (CSV + terminal table)
- `references/lin_yuan_rules.md` — Lin Yuan investment principles: monopoly, mouth-related, gross margin, buy-and-hold, discipline

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
- `--out`: CSV output path (default `lin_yuan_screen_result.csv`).
- `--min-gross`: Gross-margin hard threshold (default 50%).
- `--min-roe`: ROE hard threshold (default 15%).
- `--min-div`: Trailing 12-month dividend yield threshold (default 1.0%).
- `--sleep`: Request interval per stock (default 0.3 s, for rate-limiting).

## 4 Screening Rules

| Dimension | Proxy Metric | Weight |
|---|---|---|
| Monopoly / pricing power | 5-year gross margin mean >50% and low volatility | 30 |
| Persistent high ROE | Years with ROE ≥15% over 5 years and mean ROE | 25 |
| Shareholder returns | Trailing 12-month dividend yield + 5-year payout consistency | 20 |
| Addictive / necessity industry | White-list match: baijiu, TCM, condiments, dairy, beer, etc. | 15 |
| Financial soundness | Latest debt-to-asset ratio | 10 |

## Output Fields

- `code` / `name`: Stock code / short name
- `score`: Composite score (max 100)
- `linyuan_pass`: Passes hard thresholds
- `sw_industry` / `sw_sector`: Shenwan industry classification
- `gross_mean` / `gross_annual`: Gross margin mean / 5-year series
- `roe_mean` / `roe_annual`: ROE mean / 5-year series
- `dividend_yield` / `payout_recent`: Dividend yield / latest annual payout
- `debt_latest`: Latest debt-to-asset ratio
- `addictive_tag`: Addictive / necessity industry tag
- `data_years` / `source` / `note`: Valid years, data source, fallback notes

## Disclaimer

For learning and research only; not investment advice. Historical financial metrics do not guarantee future performance. Always validate screening results through your own understanding of the business (circle of competence). Lin Yuan's views are based on public interviews, speeches, and writings; this summary may contain interpretation bias.
