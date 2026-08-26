# Demo: Real Output of technical-pattern-recognition

**[中文](demo.md) | [English](demo.en.md) | [日本語](demo.ja.md)**

The output below comes from a real run on 2026-08-26 (Windows + Python 3.11 + akshare 1.18.94), using Sina forward-adjusted daily bars (close of 2026-08-25). Demonstration only — not investment advice.

```bash
$ python scripts/patterns.py 600519,000858,600036,601318,300750,000001
```

```
600519  [2026-08-25] close 1304.0  vol-ratio 0.51  signals: NO_SIGNAL
000858  [2026-08-25] close 71.52   vol-ratio 0.53  signals: NO_SIGNAL
600036  [2026-08-25] close 39.5    vol-ratio 0.74  signals: NO_SIGNAL
601318  [2026-08-25] close 55.01   vol-ratio 0.98  signals: MACD_GOLDEN
300750  [2026-08-25] close 376.73  vol-ratio 1.02  signals: NO_SIGNAL
000001  [2026-08-25] close 11.59   vol-ratio 0.86  signals: MACD_GOLDEN

=== Signal table ===
  code       date   close     ma5     ma20     ma60    dif     dea  vol_ratio     signals
600519 2026-08-25 1304.00 1296.17  1322.63  1262.83  4.440  11.772       0.51   NO_SIGNAL
000858 2026-08-25   71.52   71.63    74.52    74.04 -0.855  -0.419       0.53   NO_SIGNAL
600036 2026-08-25   39.50   39.20    39.12    37.82  0.260   0.275       0.74   NO_SIGNAL
601318 2026-08-25   55.01   53.50    53.45    51.95  0.319   0.197       0.98 MACD_GOLDEN
300750 2026-08-25  376.73  385.95   392.39   387.84  0.068   1.783       1.02   NO_SIGNAL
000001 2026-08-25   11.59   11.45    11.34    10.90  0.129   0.117       0.86 MACD_GOLDEN

Succeeded: 6, failed: 0.
```

(The script prints in Chinese; labels above are translated, numbers are verbatim.)

## Reading the results

- **601318 Ping An / 000001 Ping An Bank**: DIF crossed above DEA within the last 3 bars, triggering `MACD_GOLDEN`, with DIF positive (above-zero cross) and normal volume (ratio ≈ 0.9–1.0).
- **600036 China Merchants Bank**: MA5 (39.20) > MA20 (39.12) and price above MA60, but the strict four-line bullish alignment is not met (MA10 sits in between), so no `MA_BULLISH` — the script enforces its definitions exactly.
- **600519 Kweichow Moutai**: MA5 (1296) < MA20 (1322), DIF still above DEA but converging — consolidation, `NO_SIGNAL`.
- None of the six hit `VOL_BREAKOUT` / `PULLBACK_MA` that day: the market was in low-volume consolidation (ratios mostly < 1), an honest demonstration that "no signal" is a valid output.
