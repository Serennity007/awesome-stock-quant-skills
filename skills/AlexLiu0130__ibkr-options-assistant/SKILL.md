---
name: ibkr-options-assistant
description: Interactive Brokers options & stock trading assistant. Provides real-time portfolio Greeks, option chain analysis, McMillan/Overby strategy recommendations, P&L statistics, Wheel strategy tracking, earnings warnings, risk simulation, and a complete toolkit for options traders. Use this skill whenever the user asks about specific options trades, position risk, buy/sell recommendations, IV environment, P&L, wheel strategy, earnings impact on options, or any IBKR account data — even if they don't explicitly mention "IBKR". For stock price queries, always use market_quote.py instead of web search.
---

# IBKR Trader Toolkit

Real-time data, options analysis, and portfolio risk for Interactive Brokers — all via JSON-emitting CLI scripts.

**Core rule:** Scripts produce data. You (the model) produce the analysis.

---

## When to trigger this skill

| User asks about... | Example phrasing |
|---|---|
| Stock / ETF prices | "What's SPY at?" "Current AAPL price" |
| Option chains, Greeks, IV | "Show me AAPL puts for next month" |
| Strategy ideas | "Should I sell a put on MU?" |
| Position risk | "Am I too long delta?" |
| P&L, win rate, history | "How are my wheel trades doing?" |
| Earnings risk | "Does ARM report before my call expires?" |
| Alerts / monitoring | "Warn me if SPY IV > 80%ile" |

Fire **even if the user doesn't mention IBKR** — if they're asking about *their* positions or P&L, this skill is the source of truth.

**Critical:** For stock prices, always use `market_quote.py`. **Never** web-search a stock price — the web is minutes-to-hours stale.

---

## Workflows

### "What's my account state right now?" / "Status update"

For a one-glance snapshot (positions, Greeks, ITM, this-week expiries, wheel
stages):

```bash
status_dashboard.py --output telegram   # in chat-style channels
status_dashboard.py --output json       # parse and recompose freely
status_dashboard.py                     # rich ANSI for terminals
```

Add `--full` to also include IV environment per held symbol and recent P&L
(slower — extra IBKR calls). Use `--output json` when you (the agent) want
to organize the reply yourself instead of inheriting the script's layout.

### "Should I sell a put on $SYM?"

Run these in order, then synthesize:

| Step | Command | Why |
|------|---------|-----|
| 1 | `portfolio_positions.py` | Know existing exposure first |
| 2 | `earnings_calendar.py SYM --days 60` | Avoid earnings inside DTE |
| 3 | `options_analyzer.py SYM --outlook bullish --risk-profile conservative --iv-context` | Get IV environment + candidate strikes |
| 4 | `options_chain.py SYM --dte-min 25 --dte-max 45` | Live mid prices for chosen strikes |

**Your recommendation must include:** strike • delta • premium • breakeven • annualized yield • earnings/IV warnings.

---

### "What's my portfolio looking like?"

| Step | Command |
|------|---------|
| 1 | `portfolio_positions.py` → positions + Greeks |
| 2 | `options_daily.py` → expiry warnings + IV summary |
| 3 | `pnl_analytics.py --days 7` → recent realized P&L |

---

### "I'm thinking of adding trade X — is it safe?"

```bash
risk_simulator.py --add "SYM STRIKE EXPIRY R ACTION QTY"
```

Flag any of:
- **Vega magnitude doubles** → much more IV-exposed
- **Net delta flips sign** → directional bet now opposite
- **One symbol > 30% of capital** → concentration risk

---

### "How's my wheel doing?"

```bash
wheel_tracker.py summary
```

Returns per-symbol: stage (`short_put` / `assigned` / `covered_call` / `closed`), cumulative premium, days in cycle, annualized return.

---

### "Should I roll position X?"

| Step | Command | Why |
|------|---------|-----|
| 1 | `portfolio_positions.py` | Confirm the leg's current strike, expiry, P&L, delta |
| 2 | `options_chain.py SYM --dte-min 25 --dte-max 60` | Survey roll candidates further out |
| 3 | Consult [`references/wheel_strategy.md`](references/wheel_strategy.md) | "Roll vs accept assignment" decision tree |

**Your recommendation must include:** new strike • new DTE • net credit (new premium − close cost) • effective basis change vs current leg • roll count so far (cap at 2).

---

## Script reference

| Script | When to use |
|--------|-------------|
| `status_dashboard.py [--full] [--output ansi/telegram/json]` | "What's the state of my account right now?" — one-glance snapshot for terminal, Telegram, or agent consumption |
| `market_quote.py SYM [SYM2 ...]` | Any stock/ETF price question |
| `portfolio_positions.py` | What do I own? Portfolio Greeks |
| `options_chain.py SYM` | Strikes survey + IV by expiry |
| `options_analyzer.py SYM --outlook X --risk-profile Y --iv-context` | Strategy ideas given outlook |
| `options_daily.py` | Morning/EOD options report (start here) |
| `pnl_analytics.py [--days N]` | Realized P&L, win rate, best/worst |
| `risk_simulator.py --add "..."` | Pre-trade Greeks impact |
| `earnings_calendar.py SYM ...` | Earnings within N days |
| `technical_indicators.py SYM` | RSI / MA / BB / ATR |
| `wheel_tracker.py summary` | Wheel cycle status & yield |
| `alerts_monitor.py` | Threshold rules (cron-friendly) |
| `cost_basis.py SYM [...]` | Premium-adjusted effective cost basis (wheel) |
| `concentration.py` | HHI, sector mix, top-N portfolio concentration |
| `flex_import.py [--flex-dir ...]` | Parse IBKR Flex CSV/XML history into JSON |
| `trade.py <stock\|option\|combo\|...>` | **Place orders** (opt-in, dual-gate). See `references/trading.md` |

All read-only scripts:
- Output JSON to stdout (or to `--output FILE`)
- Read IBKR config from env vars (`IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID_BASE`, `IBKR_MARKET_DATA_TYPE`)
- Cannot place orders — only `trade.py` can, and only when both `IBKR_TRADING_ENABLED=1` and `--confirm-trade` are present

---

## Pre-trade checklist (every options recommendation)

Before suggesting any options trade, verify all three:

1. **IV environment** — from `options_analyzer.py --iv-context`. Don't sell premium in low-IV; don't buy premium in high-IV.
2. **Earnings inside DTE** — from `earnings_calendar.py`. IV crush after earnings flips the math.
3. **Existing position Greeks** — from `portfolio_positions.py`. If already +5000 delta, adding more is wrong direction-of-thesis or not.

State each check explicitly:
> "IV environment: low (ratio 0.7); earnings: none in next 45 days; current net delta: +1,200."

This lets the user audit the reasoning.

---

## Operating constraints

| Constraint | What it means |
|------------|---------------|
| **JSON in, judgement out** | The script's `recommendations` list is candidate data, not a final answer. Re-rank against the user's situation. |
| **Smart data type** | `IBKR_MARKET_DATA_TYPE=3` by default — IBKR auto-upgrades to realtime when user is subscribed, falls back to delayed otherwise. If quotes look stale, check market hours + subscriptions. |
| **One clientId per script** | If you see `clientId already in use`, wait a few seconds or bump `IBKR_CLIENT_ID_BASE`. |
| **Cache chains across calls** | `options_chain.py --output /tmp/chain.json` then `options_analyzer.py --chain-file /tmp/chain.json` saves IBKR roundtrips. |

---

## Deeper references

Read on demand when the user's question warrants it:

- [`references/strategies.md`](references/strategies.md) — full McMillan/Overby strategy library + selection matrix
- [`references/greeks_primer.md`](references/greeks_primer.md) — practical Delta/Gamma/Vega/Theta interpretation
- [`references/wheel_strategy.md`](references/wheel_strategy.md) — strike/DTE selection, roll-vs-assign decision tree
- [`references/options_book_summary.md`](references/options_book_summary.md) — McMillan/Overby/Natenberg/Sinclair operational rules
- [`references/troubleshooting.md`](references/troubleshooting.md) — connection errors, subscription issues
