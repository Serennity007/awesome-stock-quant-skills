# 🌧️ All-Weather Allocator: A Dalio-Style Reference for A-Shares

> The economy has only four weathers: growth ↑/↓ × inflation ↑/↓. This script uses common A-share proxies for the four quadrants and outputs risk-parity-style reference weights plus a backtest summary.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![akshare](https://img.shields.io/badge/akshare-1.18.96-green)](https://www.akshare.xyz/)

---

## Quick Start

```bash
pip install akshare==1.18.96 pandas

# Default: all-weather four-asset pool (stocks / bonds / gold / commodities)
python scripts/allocation.py --lookback 252 --out allocation.csv

# Small sample test with a few stocks
python scripts/allocation.py --codes 600519,000858,600036 --lookback 60 --out test_alloc.csv
```

---

## Default Asset Pool

| Asset Class | Proxy | Notes |
|---|---|---|
| Stocks | CSI 300 `000300`, CSI 500 `000905` | Broad A-share indices |
| Bonds | Treasury ETF `511010` | Benefits from falling growth / inflation |
| Gold | Gold ETF `518880` | Inflation hedge & safe haven |
| Commodities | CSI Commodity Futures Index | Inflation beneficiary |

---

## Sample Output

The script prints to the terminal:

- 1-year annualized return, volatility, and Sharpe for each asset
- Asset correlation matrix
- Risk-parity-style weights (per-asset weights + aggregated stock/bond/gold/commodity weights)
- Portfolio backtest summary: CAGR, max drawdown, Sharpe ratio

It also writes the result to `allocation.csv` (or your `--out` path) in `utf-8-sig` encoding for easy Excel opening.

---

## Core Logic

1. Fetch daily close prices for each asset and align trading dates.
2. Compute daily returns and annualized volatility.
3. Allocate weights using **inverse volatility**: lower volatility gets higher weight.
4. Sum weights within each asset class to get stock / bond / gold / commodity class weights.
5. Build a weighted portfolio, then compute CAGR, max drawdown, and Sharpe ratio.

---

## Risk Notice

- This script is a **simplified illustration**, not Ray Dalio's or Bridgewater's live strategy.
- It does **not** account for transaction costs, slippage, fees, taxes, dividend reinvestment, leverage, or FX rates.
- Past performance does not guarantee future results. All outputs are for educational and research purposes only and **do not constitute investment advice**.
