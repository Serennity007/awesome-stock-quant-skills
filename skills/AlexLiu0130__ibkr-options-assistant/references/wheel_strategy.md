# The Wheel Strategy — Full Guide

The Wheel is a four-stage premium-selling cycle that turns a willingness to own a stock into a recurring income stream. `wheel_tracker.py` in this toolkit tracks each cycle from entry to exit.

## Table of Contents

- [What is the Wheel?](#what-is-the-wheel)
- [The four stages](#the-four-stages)
- [When the wheel works (and when it fails)](#when-the-wheel-works-and-when-it-fails)
- [Strike selection](#strike-selection)
- [DTE selection](#dte-selection)
- [Roll vs. accept assignment](#roll-vs-accept-assignment-decision-tree)
- [Cost basis math](#cost-basis-math)
- [Position sizing](#position-sizing)
- [How `wheel_tracker.py` helps](#how-wheel_trackerpy-helps)
- [Pitfalls](#pitfalls)

---

## What is the Wheel?

Pick a stock you genuinely want to own. Sell a cash-secured put. Collect premium. If the put expires worthless, sell another. If it gets assigned, take the shares and sell covered calls against them. If the calls get assigned, take the gain plus all the premium and start the next cycle.

```
   ┌────────────────────────────────────────────────────────┐
   │                                                        │
   ▼                                                        │
[Stage 1] Sell cash-secured put                            │
   │                                                        │
   │ ─ Put expires OTM ──► collect premium, back to Stage 1│
   │                                                        │
   ▼ Put expires ITM                                        │
[Stage 2] Assigned 100 shares at the put strike            │
   │                                                        │
   ▼                                                        │
[Stage 3] Sell covered call against the shares             │
   │                                                        │
   │ ─ Call expires OTM ──► collect premium, repeat Stage 3│
   │                                                        │
   ▼ Call expires ITM                                       │
[Stage 4] Called away — shares sold at the call strike     │
   │                                                        │
   └────────────────────────────────────────────────────────┘
   Cycle complete: total P&L = stock P&L + all premium collected
```

The Wheel pays the trader to wait — first to enter, then to exit.

---

## The four stages

| Stage | What's happening | Greeks profile | Risk |
|---|---|---|---|
| **1. Short Put** | Selling premium, hoping put expires worthless. | Long delta · short gamma · short vega · long theta. | Stock drops below strike → assignment at a paper loss. |
| **2. Assigned** | Hold 100 shares per contract at strike − total_premium_collected effective cost. | Long delta (100 per contract) · no option Greeks. | Stock keeps falling — full stock-ownership risk. |
| **3. Covered Call** | Selling premium against the stock you now own. | Long delta (capped) · short gamma · short vega · long theta. | Stock rips above strike → called away, capped upside. |
| **4. Called Away** | Shares sold at call_strike. Cycle ends. | Cash. | Re-entry timing — IV may be low when you want back in. |

---

## When the wheel works (and when it fails)

### Works

- **Range-bound, mildly bullish quality names** (think large-cap dividend payers, ETFs you'd hold anyway).
- **High but not extreme IV** — enough premium to be worth the risk, not so much that it signals a regime change.
- **Sufficient capital** to take assignment without forced liquidation.
- **Patience**: the wheel is slow. 1–2% per cycle is typical.

### Fails

- **Falling knives** — a stock that drops 30% leaves you with a stock position so far underwater that covered calls can't pay you enough above your cost basis to be worth selling. *You can't wheel out of a bad pick.*
- **Earnings dates inside the cycle** — IV crush hands you a paper win but also volatile assignment risk. `earnings_calendar.py` will flag these.
- **Acquisitions / spin-offs** — corporate actions break the option contracts and can leave you stuck.
- **Concentration** — wheeling one ticker with 50% of capital. One bad event ruins the entire portfolio.

**Rule:** never sell a put on a stock you wouldn't be happy to own for two years.

---

## Strike selection

The dominant convention is **delta-based strike selection**:

| Delta band | Probability of assignment | Premium | Use when |
|---|---|---|---|
| 0.15 – 0.20 | ~15–20% | low | You really don't want assignment; just want income. |
| **0.20 – 0.30** | **~20–30%** | **balanced** | **Default wheel band.** Good income, fair assignment probability. |
| 0.30 – 0.40 | ~30–40% | high | Want assignment; using the put as a buy order. |
| > 0.40 | ATM-ish | highest | Aggressive; effectively buying the stock with a discount. |

**Why delta and not "% OTM"?** Delta normalizes for IV. A 5%-OTM put on a low-IV stock is far less risky than a 5%-OTM put on a high-IV stock; their deltas reflect that.

**Strike workflow with the toolkit:**

```bash
python scripts/options_chain.py SYM --dte-min 25 --dte-max 45
# read the chain; find the put whose delta is closest to your target band
```

`options_chain.py` returns per-strike delta, so you don't have to estimate.

---

## DTE selection

| DTE band | Theta/day | Gamma risk | Roll flexibility | Notes |
|---|---|---|---|---|
| 0–14 days | high (last-week curve) | severe | low | Gamma is the enemy; one earnings gap is disaster. |
| **30–45 days** | **good** | **manageable** | **good** | **Sweet spot for most wheelers.** |
| 60–90 days | moderate | low | great | Tied up longer; useful if VIX is elevated and you want to lock in vol. |
| > 90 days | low | minimal | maximum | Effectively a synthetic long position; rare for wheel. |

**Default:** 30–45 DTE puts, roll/close at 21 DTE or 50% max profit, whichever comes first. This is the tastytrade-popularized convention; it concentrates theta in the steepest part of the curve while leaving room to react.

---

## Roll vs. accept assignment (decision tree)

When a short put is ITM and approaching expiry:

```
Short put ITM at 5 DTE?
│
├── Q1: Is the thesis on the stock still intact?
│   │
│   ├── No  → Close the position. Take the loss. Move on.
│   │         (Wheeling a broken story is throwing good money after bad.)
│   │
│   └── Yes → continue to Q2
│
├── Q2: Can I roll for a net credit, to a later date, at the same or lower strike?
│   │
│   ├── Yes → Roll. Document the new strike/DTE/credit in wheel_tracker.
│   │         Typical: roll 30 days out, same strike, collect more premium.
│   │
│   └── No  → continue to Q3
│
├── Q3: Am I willing to own 100 shares at this strike given my current portfolio?
│   │
│   ├── Yes → Accept assignment. Begin Stage 2. Switch to covered calls.
│   │
│   └── No  → Close the put at market. Move on. Don't roll defensively into a worse position.
```

**Rolling rules:**

- **Never roll for a debit.** If you can't collect more premium, the trade is signaling that you should close.
- **Never roll inverted** (strike above current price for a put). It feels like a hedge but it locks in a loss with extra obligation.
- **Cap rolls at 2.** If a position has been rolled twice and is still in trouble, the thesis is wrong.

---

## Cost basis math

This is what new wheelers miss: your effective cost is **not** the strike, it's the strike minus all premium ever collected on that ticker in this cycle.

```
Effective cost basis = strike - Σ (all puts and calls collected in this cycle)
```

**Example:**

| Trade | Premium |
|---|---|
| Sold 30 DTE put, strike 100 | +$1.50 |
| Rolled out 30 days, strike 100 | +$0.80 |
| Assigned at 100 | — |
| Sold 30 DTE covered call at 105 | +$1.20 |
| Called away at 105 | — |

```
Effective cost basis = 100 - 1.50 - 0.80 - 1.20 = 96.50
Final P&L per share = 105 (call away) - 96.50 = +8.50  ≈ +8.8%
```

`wheel_tracker.py summary` does this math automatically per cycle.

---

## Position sizing

Hard rules:

- **No single wheel > 10% of account.** A single position blowing up shouldn't be portfolio-defining.
- **No single sector > 30%.** Energy and tech can correlate to near-1 in a sell-off.
- **Total wheel margin usage < 50% of buying power.** Leaves room to respond to assignments without forced sells.

If you're full on wheels, the answer to "should I wheel this great new ticker?" is "close an existing one first."

---

## How `wheel_tracker.py` helps

The script reads `~/.ibkr_wheel_journal.json` (your manual entries) and cross-references live positions from IBKR to figure out which stage each wheel is in.

**Add a new wheel entry:**

```bash
python scripts/wheel_tracker.py add-entry SYM STRIKE EXPIRY PREMIUM
# e.g.
python scripts/wheel_tracker.py add-entry MU 100 2026-06-19 1.45
```

**Get a summary:**

```bash
python scripts/wheel_tracker.py summary
```

Output (one row per active wheel):

```json
[
  {
    "symbol": "MU",
    "stage": "short_put",
    "current_strike": 100,
    "current_dte": 32,
    "premium_collected": 1.45,
    "effective_cost_basis": 98.55,
    "days_in_cycle": 8,
    "annualized_yield_pct": 16.5
  }
]
```

Use this weekly to spot wheels that are stuck (no progress in 60+ days) or that have under-collected premium relative to the time they've consumed.

---

## Pitfalls

| Pitfall | Why it hurts | Fix |
|---|---|---|
| Wheeling into earnings without realizing | IV crush + gap risk on assignment | `earnings_calendar.py` before every new put |
| Picking high-IV junk for premium | The premium is high because the stock is broken | Quality > yield. Filter by fundamentals first. |
| Rolling defensively forever | You compound a bad position | Cap rolls at 2; then close or accept. |
| Selling covered calls below cost basis | Locks in a loss when called away | Always set the call strike ≥ effective cost basis. |
| No exit plan at 50% max profit | Letting winners turn into losers | Close shorts at 50% of max profit on rolls of comparable strikes/DTEs. |
| Concentration in one ticker | One earnings miss = catastrophic | Position-size limits above. |

---

The wheel is a slow, mechanical strategy. Done badly it's a way to compound mistakes. Done well it's a 10–15% annualized strategy with defined exits at every stage. Use the tools, log every cycle, and let the math be the decider — not the urge to "make back" a losing leg.
