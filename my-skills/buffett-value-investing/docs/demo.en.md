# Demo: Real Output of buffett-value-investing

**[中文](demo.md) | [English](demo.en.md) | [日本語](demo.ja.md)**

The outputs below were produced by a real run on 2026-08-26 (Windows + Python 3.11 + akshare 1.18.94), using akshare public APIs (Sina financials/quotes + East Money historical valuation). The numbers are genuine results as of that day, shown for demonstration only — not investment advice.

## 1. Single-stock analysis: `analyze.py 600519` (Kweichow Moutai)

```bash
$ python scripts/analyze.py 600519
```

```
===== Kweichow Moutai (600519) Buffett-style Analysis =====

[1] Moat checklist (human/AI scores each item 0-2; the script never fakes scores)
  [ ] Brand / intangibles: will consumers pay a premium? do sales hold after price hikes?  -> score _/2
  [ ] Cost advantage: unit costs below main rivals? does scale keep diluting costs?        -> score _/2
  [ ] Switching costs: how expensive/risky is it for customers to switch suppliers?       -> score _/2
  [ ] Network effects: does each new user add value to existing users?                    -> score _/2
  Total >= 5/8 indicates a strong moat.

[2] Financial quality trend (last 5 annual reports)
        year    ROE%  gross%  debt%
2021-12-31  27.7  91.5    22.8
2022-12-31  31.8  91.9    19.4
2023-12-31  34.6  92.0    18.0
2024-12-31  37.0  91.9    19.0
2025-12-31  33.6  91.2    16.4
  Years with ROE > 15%: 5/5 (fully meets Buffett's preference)

[3] Valuation range & margin of safety
  Price: 1304.00 CNY | latest PE: 20.0 | EPS (est.): 65.14 CNY
  5-year PE 25/50 percentile: 23.8 / 32.4
  Conservative value (PE25 x EPS): 1547.89 CNY | Neutral value (PE50 x EPS): 2111.00 CNY
  Margin-of-safety reference buy price (conservative x 0.7): 1083.52 CNY
  => Price is below conservative value, but the margin of safety is under 30% — small position or wait.
```

(The script prints this report in Chinese; headers above are translated for readability, numbers are verbatim.)

## 2. Screening: `screen.py --codes 600519,000858,600036`

```bash
$ python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

```
Pool: 3 stocks, scoring one by one (financial APIs are slow, please wait)...
[1/3] 600519 score 100
[2/3] 000858 score 94
[3/3] 600036 score 47

=== Top 3 (full results in result.csv) ===
  code  total  roe_score               roe_annual  gross_score  gross_mean  debt_score  debt_latest  cashflow_score  cashflow_pos_years  valuation_score  pe_pct  pb_pct
600519    100         30 27.7,31.8,34.6,37.0,33.6           20        91.7          15         16.4              20                   5               15    0.07    0.03
000858     94         24  23.6,23.4,23.3,23.9,7.5           20        76.2          15         35.7              20                   5               15    0.28    0.00
600036     47         12 14.0,14.6,13.6,12.1,11.8            0         NaN           0         90.2              20                   5               15    0.27    0.12

Succeeded: 3, failed: 0.
Thresholds: >=70 enters manual moat review; 50-69 has weaknesses; <50 fails the framework.
```

## Reading the results

- **600519 Kweichow Moutai**: 100/100 — five straight years of 27.7%–37.0% ROE, ~91.7% gross margin, 16.4% debt ratio, positive operating cash flow every year, PE/PB percentiles just 0.07/0.03. Passes every financial gate; proceeds to the manual moat review.
- **000858 Wuliangye**: 94 — main weakness is the latest-year ROE falling to 7.5% (-6 on roe_score).
- **600036 China Merchants Bank**: 47 — high financial-sector leverage (90.2% debt) zeroes debt_score, and ROE dropped below 15%. A textbook case of the framework's "financial stocks need manual/separate evaluation" caveat.

A daily automated version of this screen is published to the `reports/` directory by a GitHub Action.
