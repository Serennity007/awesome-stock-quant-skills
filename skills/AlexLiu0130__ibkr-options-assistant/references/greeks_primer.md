# Greeks Primer — Practical Interpretation

The "Greeks" measure how an option's price moves when something else moves. The toolkit reports them per-position and aggregates them across the portfolio in `portfolio_positions.py`. This is a working interpretation, not a textbook derivation.

## The five Greeks at a glance

| Greek | Measures | Per-unit move | Sign for long call | Sign for long put |
|---|---|---|---|---|
| **Delta** | Price sensitivity to underlying | $1 move in underlying | + (0 → +1) | − (0 → −1) |
| **Gamma** | How fast delta changes | $1 move in underlying | + | + |
| **Vega** | Price sensitivity to implied vol | 1 vol-point (1% IV) | + | + |
| **Theta** | Time decay | 1 calendar day | − | − |
| **Rho** | Sensitivity to interest rates | 1 percentage point | + | − |

Short positions flip the sign of all Greeks (short call: negative delta, negative gamma, negative vega, positive theta).

---

## Delta — the directional one

**What it tells you:** *"If the stock moves $1, my option moves $delta."* For a 0.30-delta call: stock +$1 → call +$0.30 (× 100 shares = $30 per contract).

**Common rules of thumb:**

- Delta is also a rough probability of finishing ITM at expiry. A 0.30-delta put has ≈30% probability of expiring ITM — this is what wheel sellers use to pick strikes.
- ATM options sit near ±0.50 delta. Deep ITM approach ±1.00. Deep OTM approach 0.
- Stock has delta 1.00 per share (100 per round lot).

**Portfolio level (`portfolio_positions.py`'s `net_delta`):**

> *"Net delta = +1,200" means your account moves like +1,200 shares of the underlying basket.* If SPY drops $1, you lose ≈$1,200. Always reconcile this with your sizing.

**When delta matters most:**

- Directional trades — it's literally your directional exposure.
- Wheel selection — pick the strike whose delta matches your acceptable assignment probability (typical wheel: 0.20–0.30 delta short put).

---

## Gamma — delta's accelerator

**What it tells you:** *"Delta itself isn't constant. Gamma is how much delta changes per $1 move."*

Long options have **positive gamma**: a good thing — your delta increases when the move goes your way and decreases when it goes against you. Short options have **negative gamma**: brutal in fast moves.

**Where it bites:**

- **Gamma scalping** is the upside of long options.
- **Gamma risk** on short options near expiry is the downside: a 0.20-delta short put can turn into a 0.70-delta short put overnight on an earnings gap.

**Rule:** gamma is highest for **ATM options close to expiry**. If you're short premium with under a week to expiry, the gamma is screaming and a single bad day can blow through weeks of theta.

---

## Vega — the IV gauge

**What it tells you:** *"For every 1 percentage point increase in implied vol, the option price changes by $vega."* Long options are long vega; short options are short vega.

**Worked example:**

> If your portfolio shows `net_vega = +500`, then a 1% IV drop costs you $500. A 1% IV rise gains you $500. Across earnings, IV often drops 20–40% — a long-vega position can lose $10,000+ in seconds even if the stock goes the right way ("IV crush").

**When vega matters most:**

- **Holding through earnings:** check vega before, not after.
- **Buying premium when IV is high:** you're paying up — even if you're right on direction you can lose to IV mean-reversion.
- **Selling premium when IV is low:** you're getting nothing — and a vol spike will hurt.

`options_analyzer.py --iv-context` reports the IV-to-HV ratio so you can avoid this trap.

---

## Theta — time decay

**What it tells you:** *"My option loses $theta in value each calendar day, holding everything else constant."* Theta is the **rent** the long pays the short for keeping the optionality alive.

**Signs:**

- Long options: theta < 0 (you pay).
- Short options: theta > 0 (you collect).

**Worked example:**

> A short put with theta = +18 collects ≈$18/day. Over 30 days = $540 — assuming nothing else moves (which is the catch).

**When theta matters most:**

- **Premium-selling strategies** (CSP, covered call, iron condor, wheel): theta is your income; everything else is a risk against it.
- **Long-premium directional bets**: you're fighting theta every day. Stocks need to move enough, in the right direction, fast enough.
- **Theta accelerates as expiry approaches** — most theta decay happens in the last 30 days, and the very last week is dramatic.

**Practical:** for a wheel, picking 30–45 DTE balances "enough theta per day" against "still room to roll if it goes against me."

---

## Rho — the one you mostly ignore

**What it tells you:** *"For every 1% change in interest rates, my option changes by $rho."*

For typical 30–60 DTE retail options on US equities, rho is small enough to ignore — usually under $5 per contract per 1% rate move. It starts to matter for:

- **LEAPS** (long-dated options, 1+ years). 
- **Cash-settled index options** in a rate-cut/hike cycle.
- **Synthetic stock positions** (long call + short put at same strike) — rho is the carry cost.

Most retail wheel and short-premium traders can treat rho as decoration.

---

## Portfolio-level Greeks

`portfolio_positions.py` sums Greeks across all positions, normalized to share-equivalents:

```json
{
  "portfolio_greeks": {
    "net_delta": +1240.5,
    "net_gamma": -18.2,
    "net_vega": +452.0,
    "net_theta": -84.1
  }
}
```

**How to read this:**

| Greek | Interpretation |
|---|---|
| `net_delta = +1240` | Account moves like +1,240 shares of the underlying mix. SPY −$1 ≈ −$1,240. |
| `net_gamma = −18` | For every $1 the underlying moves, my delta moves against me by 18. Risk concentrates near short strikes close to expiry. |
| `net_vega = +452` | Long vega: +1% IV = +$452. -1% IV = −$452. |
| `net_theta = −84` | Net long premium overall — I'm paying ≈$84/day in time decay. |

**A net-vega-positive portfolio that you didn't intend to build is a common mistake** — easy to drift into by buying too many long calls. Run `portfolio_positions.py` weekly.

---

## When each Greek matters most

| Scenario | Watch |
|---|---|
| Picking a wheel strike | **Delta** (0.20–0.30 target) |
| Holding short premium through earnings | **Vega** (and don't) |
| 0–7 DTE positions | **Gamma** (high — re-check intra-day) |
| Premium-selling P&L attribution | **Theta** (income) + **Vega** (risk) |
| LEAPS | **Rho** + Theta + Vega |
| Stock + protective put | **Delta** of put (target around −0.20 to −0.30) |

---

## One last warning

Greeks are model outputs (Black-Scholes-ish). They are accurate in normal markets and wrong in fast/illiquid markets. They depend on an IV input that itself moves. Treat them as **direction and rough magnitude**, not as a guarantee — especially for short-dated and far-OTM options where modelGreeks can return `None` or stale values.
