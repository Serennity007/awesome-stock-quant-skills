# technical-pattern-recognition

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

A-share technical pattern recognition Skill (Claude Code / Agent Skills format): based on akshare Sina daily bars, it mechanically detects MA bullish/bearish alignment, MACD golden/death cross, volume-confirmed breakout to an N-day high, and low-volume pullback to the MA, outputting a structured signal table for AI interpretation.

Author: Serennity007 | License: MIT | Data: akshare (Sina daily bars, forward-adjusted)

## Quick start

```bash
pip install akshare pandas
python scripts/patterns.py 600519,601318 --days 250 --window 60 --out signals.csv
```

## Signals

| Signal | Meaning |
|---|---|
| `MA_BULLISH` / `MA_BEARISH` | MA bullish / bearish alignment |
| `MACD_GOLDEN` / `MACD_DEATH` | MACD golden / death cross (within last 3 bars) |
| `VOL_BREAKOUT` | Volume breakout to N-day high (volume ratio ≥ 1.5) |
| `PULLBACK_MA` | Low-volume pullback to MA20 inside a bullish trend |

Detection details: [references/patterns.md](references/patterns.md); real run output: [docs/demo.md](docs/demo.md).

## Disclaimer

For study and research only — not investment advice. Technical patterns are lagging indicators and any signal can fail.
