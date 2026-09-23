# 🌀 Soros Reflexivity Scanner (A-Shares)

> Price is not a mirror of reality — it is part of reality itself.

This skill turns George Soros’s **theory of reflexivity** into a quant scanner for China A-shares. It compares **price momentum** against **fundamental growth**, measures **volume crowding**, and detects **trend inflection signals**, then labels each stock with its reflexivity stage.

It does **not** predict tomorrow’s move. It helps you ask: *Is the market currently reinforcing itself, or is it beginning to self-destruct?*

## Core capabilities

| Capability | Description |
|---|---|
| Price–fundamental divergence scan | Strong price + weakening earnings → “fragile bubble candidate”; weak price + improving earnings → “expectation-gap candidate” |
| Volume crowding gauge | Current turnover divided by 20-day average turnover; warns when > 2 |
| Inflection signals | MACD golden/dead cross, RSI overbought/oversold, bullish/bearish MA alignment |
| Reflexivity stage labels | Reinforcing positive feedback, fragile positive feedback, deepening negative feedback, oversold negative feedback, equilibrium/watch zone |

## Quick start

```bash
pip install akshare pandas

# Small-sample test
python scripts/reflexivity_scan.py --codes 600519,000858,600036 --out scan.csv

# Scan the CSI 300 universe
python scripts/reflexivity_scan.py --pool hs300 --top 30 --out scan.csv
```

## Companion docs

- `references/soros_framework.md`: Soros’s reflexivity framework, boom-bust sequence, human uncertainty principle, the discipline of admitting mistakes, and macro-hedge thinking.
- `SKILL.md`: Full field reference and workflow.

## Disclaimer

This tool is for educational and research purposes only, not investment advice. Markets carry risk; the scanner is a mechanical summary of historical data and rules, not a forecast of future prices.
