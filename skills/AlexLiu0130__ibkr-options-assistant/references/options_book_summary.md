# Options Book Summary — Operational Rules

A lookup of operational rules distilled from four canonical options books, written as decision-ready heuristics rather than theory. Use this when reasoning about strategy selection, position sizing, adjustment, or risk.

**Sources cited per rule:**
- **(McMillan)** — Lawrence McMillan, *Options as a Strategic Investment*, 5th ed.
- **(Overby)** — Brian Overby, *The Options Playbook* (TastyTrade lineage).
- **(Natenberg)** — Sheldon Natenberg, *Option Volatility & Pricing*, 2nd ed.
- **(Sinclair)** — Euan Sinclair, *Volatility Trading*, 2nd ed.

This is a **rule book**, not a textbook. For mechanics of Greeks see [`greeks_primer.md`](greeks_primer.md); for the strategy catalog see [`strategies.md`](strategies.md).

---

## Table of Contents

1. [IV Environment Playbook](#1-iv-environment-playbook)
2. [Strike Selection Rules](#2-strike-selection-rules)
3. [DTE Selection Rules](#3-dte-selection-rules)
4. [Adjustment Decision Tree](#4-adjustment-decision-tree)
5. [Position Sizing](#5-position-sizing)
6. [Skew Interpretation](#6-skew-interpretation)
7. [Earnings IV Crush](#7-earnings-iv-crush)
8. [Volatility Estimation](#8-volatility-estimation)
9. [Greeks-vs-Greeks Relationships](#9-greeks-vs-greeks-relationships)
10. [Common Mistakes (each book's "don't")](#10-common-mistakes)

---

## 1. IV Environment Playbook

The single most important question before opening an options trade: **is implied volatility rich or cheap?** Get this wrong and a directionally correct view still loses money.

### Core rule

> **Rule (McMillan):** When current IV is in the bottom 20% of its trailing-1-year range, **buy** premium (long straddle, long calendar, long single leg). When in the top 20%, **sell** premium (short strangle, iron condor, credit spread). Middle 60%: use **spreads** — debit spreads when you have directional conviction at low IV, credit spreads when you have directional conviction at high IV. (McMillan)

### IV percentile vs IV rank — use both

| Metric | Definition | When it helps |
|---|---|---|
| **IV rank** | (current IV − 52w low) / (52w high − 52w low) | Quick sense of where IV sits in its full year range |
| **IV percentile** | % of trading days in the past year where IV was below today's | More robust to single-day spikes (e.g. earnings) |

> **Rule (Sinclair):** Prefer IV percentile to IV rank in symbols with episodic volatility spikes (earnings, biotech catalysts). A single-day Vol spike inflates IV rank but barely moves IV percentile. (Sinclair)

### Strategy → IV environment matrix

| IV environment | Bullish | Bearish | Neutral | Volatile (expect a move) |
|---|---|---|---|---|
| **Low IV** (≤20%ile) | Long call, call debit spread, call ratio backspread | Long put, put debit spread | Long calendar, long butterfly | Long straddle, long strangle |
| **Mid IV** (20–80%ile) | Bull call spread | Bear put spread | Iron condor (mild), short strangle (wide) | Long strangle |
| **High IV** (≥80%ile) | Cash-secured put, bull put spread, jade lizard | Bear call spread | Short strangle, iron condor, iron butterfly | Avoid — wait for IV mean-reversion |

> **Rule (Overby):** Don't sell premium for the sake of "income" when IV percentile is below 30. The premium you collect doesn't compensate for the gamma risk near expiry. Wait for IV to expand or switch to a defined-risk spread. (Overby)

### Term structure

Implied volatility varies by expiry. The shape tells you what the market is pricing.

| Term structure | What it means | Trade idea |
|---|---|---|
| **Contango** (front IV < back IV) | Calm now, uncertainty later. The normal state in low-vol regimes. | Long calendars, short front / long back |
| **Backwardation** (front IV > back IV) | Imminent event priced into front-month (earnings, FOMC, war). | Short front / long back ("event vol harvest"); never long front-month in this regime |
| **Flat** | No view; spreads will be near fair value | Spreads, no edge for calendars |

> **Rule (Natenberg):** A 10% drop in IV reduces a 30-DTE ATM option's price by roughly vega × 10. For typical equity ATM options that's ~30% of premium. This is why selling front-month into earnings backwardation is the **highest-Sharpe** vol trade — IV crush is mechanical, not random. (Natenberg)

---

## 2. Strike Selection Rules

Choose strikes by **delta**, not by absolute price. Delta is comparable across symbols, expiries, and IV regimes; absolute strikes are not.

### Delta targets by strategy

| Strategy | Short-leg target delta | Notes |
|---|---|---|
| Cash-secured put | 0.20 – 0.30 | 0.30 = ~30% chance of assignment. Lower delta = lower premium but lower assignment risk. |
| Covered call | 0.20 – 0.30 | 0.30 means ~30% chance the stock gets called away. |
| Short strangle | 0.16 – 0.20 each side | 0.16 ≈ 1-σ OTM; standard TastyTrade default. |
| Iron condor (short legs) | 0.16 – 0.30 each side | Tighten when IV is mid-range. |
| Bull put / bear call (short leg) | 0.25 – 0.35 | Higher delta = higher premium but more touches. |
| Long debit spread (long leg) | 0.50 – 0.70 | ITM legs hold more intrinsic value; less theta decay. |
| Long debit spread (short leg) | 0.20 – 0.30 | Sells the OTM wing to cheapen the long. |
| Protective put | 0.20 – 0.30 (5–10% OTM) | Insurance. Don't over-protect. |

> **Rule (Overby):** A 0.30-delta short option roughly equals a 30% probability of being ITM at expiration. Use this as your "win-rate envelope" — never trade a strategy whose long-run win-rate doesn't beat the assignment cost. (Overby)

### When to bend the rule

> **Rule (McMillan):** In a stock you'd happily own at the strike, you can use a higher-delta short put (up to 0.40) — the "loss" of assignment is acquiring stock at a discount. In a stock you'd hate to own (poor balance sheet, secular decline), drop to 0.10–0.15 delta and accept lower premium. (McMillan)

### Strike spacing rule

> **Rule (Natenberg):** In a put credit spread, the optimal width is **1 to 1.5 standard deviations** of the underlying's expected move over the DTE. Wider spreads collect more premium but have worse risk/reward; tighter spreads have better R:R but are too narrow for normal noise. (Natenberg)

---

## 3. DTE Selection Rules

Theta decay is not linear. Knowing the curve picks the sweet spot.

### The theta-decay curve

| DTE | Theta behavior | Trade implication |
|---|---|---|
| > 90 | Slow, linear theta. Vega dominates. | LEAPS for synthetic stock; calendars; long verticals when IV is low. |
| 45–90 | Theta accelerating. Vega still meaningful. | The classic "premium-selling" window. Best risk/reward for short strangles, iron condors, cash-secured puts. |
| 21–45 | Theta near maximum, gamma rising. | Most active management window — adjust here. |
| 7–21 | Theta still high but **gamma is dangerous**. | Roll, close, or convert to a defined-risk spread. Don't open new naked short premium in this window. |
| < 7 | Gamma extreme. A 1% underlying move = huge P&L swing. | Close. Period. Unless you're explicitly running 0-DTE on intraday timeframes. |

> **Rule (Overby):** **45 DTE is the canonical short-premium entry point.** You collect 50–70% of the maximum premium before gamma turns on you. Close at 21 DTE (or 50% of max profit, whichever comes first). (Overby — TastyTrade convention)

> **Rule (McMillan):** Calendars want **30–60 DTE on the long leg and 15–30 on the short leg.** The short leg decays faster (good); the long leg holds vega exposure to benefit from IV rise. Avoid calendars in front of expected IV drops (earnings IV crush will hurt the long leg). (McMillan)

### Weekly vs monthly

| Type | When to use |
|---|---|
| **Weeklies** | Only for: (a) 0–7 DTE income strategies you actively manage intraday, (b) hedging known events, (c) low-cost lottery tickets on news catalysts. Never sell weekly premium "to collect theta" — gamma will eat you. |
| **Monthlies** | The default for credit spreads, iron condors, calendar spreads. More liquid, tighter bid/ask. |
| **Quarterlies / LEAPS (60+ DTE)** | Synthetic stock, poor man's covered calls, long-vol bets ahead of high-IV regimes. |

---

## 4. Adjustment Decision Tree

The single hardest skill in options trading. Get this wrong and small losses become catastrophic; get it right and short-premium becomes durable.

### Roll vs cut vs add: the three-question filter

Ask in order:

1. **Has the original thesis changed?** If yes → **CUT.** A roll on a broken thesis is throwing good money after bad.
2. **Is there enough premium in the next expiry to re-establish the position at improved strikes?** If no → **CUT.** Rolling for a tiny credit just defers the problem.
3. **Are you under 21 DTE and >50% of strike threatened?** If yes → **ROLL.** This is the canonical roll window.

### Rolling a short put

> **Rule (McMillan):** Roll **out and down** (further DTE, lower strike) only if you can do so for a **net credit**. If the roll requires a debit, you're better off closing and re-deploying capital. Track total credits across rolls — if cumulative credit drops below 0, you've extended the position too far. Cap at 2 rolls maximum. (McMillan)

### Rolling a short call (when called-away risk is rising)

> **Rule (Overby):** Roll **out and up** (further DTE, higher strike). If the underlying has rallied past your strike by more than 5%, ask: would I keep selling calls at this new strike if I weren't already in the trade? If no, let it be called away. The wheel's whole point is participating in upside that escapes your strike. (Overby)

### Iron condor adjustments

| Threat | Action |
|---|---|
| One side breached (e.g. underlying through put-side short strike) | Roll the **untested** side closer to current price for additional credit. Don't move the breached side — wait for mean-reversion or close. |
| Both sides threatened (volatility expansion) | Close. The iron condor's edge depends on price staying inside the range; if it's gone, no roll fixes it. |
| Underlying pinned at a short strike near expiry | Close 1 day before expiry; gamma assignment risk is too high. |

### When to **add** (rarely)

> **Rule (McMillan):** Add to a winning position only at structurally better prices, never to "average down." If a short strangle is profitable and IV has expanded since entry, you can layer a second strangle at wider strikes for compounded premium. Never add to a losing strangle — that's catching a falling vol knife. (McMillan)

### The "Texas Hedge" warning

> **Rule (McMillan):** A "Texas Hedge" is a position that **adds risk in the same direction as the existing exposure** while pretending to hedge. Example: long stock + long call (both delta-positive). If your portfolio is already long-delta, buying more calls is not a hedge — it's leverage. Real hedges reduce net Greeks; Texas Hedges concentrate them. (McMillan)

---

## 5. Position Sizing

Most options blowups are sizing problems, not strategy problems.

### Max loss per trade

> **Rule (Overby):** **No single defined-risk trade should risk more than 1–2% of account capital.** For an iron condor with $400 max loss and a $40,000 account, that's exactly one contract. (Overby)

> **Rule (McMillan):** For undefined-risk trades (naked short strangle, short straddle), use a **margin-based 5% rule**: the maintenance margin requirement should not exceed 5% of account equity per position, with total undefined-risk margin capped at 25% of account. (McMillan)

### Kelly-fraction caveats

> **Rule (Sinclair):** Kelly suggests sizing positions by edge/variance. In options, **edge is hard to measure** and **variance is fat-tailed**. Use a **fractional Kelly** of 0.25–0.5 of the full Kelly bet. Going full-Kelly assumes you've correctly estimated both edge and variance; one bad estimate and you're ruined. (Sinclair)

### Concentration

> **Rule (Overby):** No single underlying should account for more than **20% of total portfolio delta**. Even if you have high conviction, a single-stock blow-up event (fraud, surprise miss, regulatory action) at 20%+ concentration is account-threatening. (Overby)

### Defined vs undefined risk allocation

| Account size | Max % in undefined-risk options |
|---|---|
| < $25k | 0% — use only defined-risk spreads |
| $25k – $100k | ≤ 10% of net liq |
| $100k – $500k | ≤ 20% of net liq |
| > $500k | ≤ 30%, with diversification across uncorrelated underlyings |

> **Rule (Natenberg):** The professional trader's mental sizing question is not "how much will I make?" but "what's the worst-case Greeks exposure if vol expands 50% overnight?" If you can't answer in dollars, your position is too large. (Natenberg)

---

## 6. Skew Interpretation

Put skew = the market's price of crash insurance. Reading it tells you what professional dealers think.

### What skew measures

| Skew shape | Reading |
|---|---|
| **Steep put skew** (OTM puts much more expensive than OTM calls) | Crash risk priced in. Common in equities, especially after a recent selloff. Buying OTM puts here is **expensive insurance** — consider put spreads instead. |
| **Flat skew** | Market sees symmetric risk. Rare in single stocks; common in FX and some commodities. |
| **Call skew** (OTM calls more expensive than OTM puts) | Squeeze risk / takeover speculation / commodity scarcity. Common in GME-style situations and in some commodities (natural gas summer). |
| **Smile** (both wings expensive) | Big move expected but direction unclear. Pre-event positioning. |

> **Rule (Natenberg):** In equity index options, **put skew is the norm, not the anomaly**. A flat skew in SPX is itself a signal — usually that complacency has reached a top. The 1987 crash was preceded by historically flat skew. (Natenberg)

### Trading the skew

> **Rule (Sinclair):** When equity put skew steepens past its 1-year 90th percentile, **sell put spreads** (sell the high-IV near-money put, buy the lower-IV further-OTM put). The skew premium is your edge. When skew flattens to the 10th percentile, **buy puts outright** — the protection is cheap relative to history. (Sinclair)

### Risk reversal as a skew gauge

A 25-delta risk reversal (= 25Δ call IV − 25Δ put IV) is the cleanest single number for equity skew.

| 25Δ RR | Interpretation |
|---|---|
| Strongly negative | Heavy put skew; put-buyers dominant; crash priced |
| Near zero | Symmetric pricing |
| Strongly positive | Call premium; squeeze/takeover priced |

---

## 7. Earnings IV Crush

Earnings is the single most predictable IV event in equity options. Use it.

### The mechanic

Before an earnings release, IV in the front-month expands to price the expected move (usually 5–15% for individual stocks). Within minutes after the release, IV collapses ("crush") back toward the longer-dated term-structure baseline. Whether the stock moves or not, **the option premium gets cut roughly in half**.

### The trade-offs

> **Rule (McMillan):** Long premium into earnings is a **−EV trade** unless your move estimate exceeds the option-implied move by a meaningful margin. The implied move is priced *exactly* to make long premium fair — and after crush, even a directionally correct move can lose money. (McMillan)

> **Rule (Natenberg):** Selling premium into earnings is a **positive-vega-decay bet that the move will be smaller than implied**. Historical analysis: in liquid US equity options, the realized move beats the implied move only ~40% of the time, meaning sellers win ~60% of the time. **But the loser-tail can be very large** (gap moves >2σ happen 5–10% of the time). Size accordingly. (Natenberg)

### Strategies by earnings stance

| View | Strategy | Why |
|---|---|---|
| "Stock moves less than implied" | Iron condor or short strangle straddling the expected move, expire after the report | Captures full IV crush |
| "Stock moves more than implied" | Long straddle/strangle, **close before earnings** | Long premium peaks the day before earnings; sell into the IV expansion |
| "Stock moves a specific amount in a specific direction" | Calendar spread or directional debit spread | Pure direction bet, less vega risk |
| "I have no view, but I want IV crush exposure with limited risk" | Short iron condor 1σ wide | Defined risk; profit if stock stays in range |

> **Rule (Overby):** Never hold long options through earnings unless you're prepared to lose 50–70% of premium even if you're directionally right. The implied move is calibrated to your detriment. (Overby)

### Pre-earnings IV ramp

> **Rule (Sinclair):** Front-month IV typically rises ~30–60% in the 5 trading days before earnings (relative to non-earnings baseline IV). Selling 7-DTE puts 5 days before earnings → closing the day before earnings can harvest a portion of that ramp **without** taking event risk. (Sinclair)

### Implied move vs straddle price (quick estimate)

The market's implied move for an event is approximated by the **ATM straddle price ÷ stock price**, multiplied by ~85% (a small correction because the straddle slightly over-prices the breakeven distance).

> **Rule (Sinclair):** Implied move ≈ 0.85 × (ATM call price + ATM put price) / underlying price. Example: AAPL at $200 with ATM straddle worth $12 → implied move ≈ 0.85 × $12 / $200 = 5.1%. Compare against historical post-earnings moves: if AAPL's 8-quarter median post-earnings move is 3.5%, the market is overpricing the event by ~46% — that's a vol-selling setup. (Sinclair)

---

## 8. Volatility Estimation

Which estimator should you use?

### The four ways volatility shows up

> **Rule (Natenberg):** Four distinct measurements of volatility, all important:
> 1. **Historical (realized) volatility** — what the underlying actually did. Backwards-looking.
> 2. **Implied volatility** — what options are priced for. Forward-looking.
> 3. **Implied skew** — how IV varies by strike. Tells you who's hedging what.
> 4. **Term structure** — how IV varies by expiry. Tells you the timing of expected risk.
>
> A trader who reads only one of these is trading blind. (Natenberg)

### Choosing a historical-vol estimator

| Estimator | Pros | Cons | Use when |
|---|---|---|---|
| **Close-to-close** | Simplest; matches statistical theory | Ignores intraday range; high variance estimate | You need a quick baseline; have only daily closes |
| **Parkinson** | Uses high-low range; ~5x more efficient than close-to-close | Assumes no drift, no overnight gaps | Pure intraday-vol estimation |
| **Garman-Klass** | Uses OHLC; more efficient than Parkinson | Still no overnight gap handling | Liquid markets without significant overnight moves |
| **Rogers-Satchell** | Handles drift | More complex; still no jump handling | Trending markets |
| **Yang-Zhang** | Handles drift AND overnight gaps; ~14x more efficient than close-to-close | More complex calculation | The default for modern equity-vol research |
| **GARCH(1,1)** | Models vol clustering and mean reversion | Parameters drift; needs refitting | Forecasting next-period vol, not just measurement |

> **Rule (Sinclair):** Use **Yang-Zhang** as the default historical-vol estimator for daily equity data — it dominates simpler estimators for any series with overnight risk. Use **GARCH(1,1)** when you need a forecast, not just a measurement, but accept that GARCH systematically under-predicts large moves. (Sinclair)

### Vol-of-vol

The volatility of volatility itself. High vol-of-vol → vol mean-reverts faster; low vol-of-vol → vol persists.

> **Rule (Sinclair):** When vol-of-vol is high (VVIX rising), short-vol strategies become more dangerous: even small underlying moves trigger big IV swings, which means defined-risk spreads should be preferred over naked short premium. Conversely, low vol-of-vol regimes (calm-market, summer 2017-style) favor short premium because IV won't whip you. (Sinclair)

### Variance swap intuition

A variance swap pays the difference between **realized** variance and **strike** variance over a period. The variance-swap strike is computed from an option-strip portfolio.

> **Rule (Sinclair):** The 30-day variance-swap strike is roughly **VIX squared**, scaled to daily. When VIX is 16, the market is pricing about 16% annualized realized vol over the next 30 days. If your forecast (from GARCH, recent history, or a view on macro) says realized vol will be ≤14, sell variance (short VIX/short strangle); if ≥18, buy variance. (Sinclair)

---

## 9. Greeks-vs-Greeks Relationships

The non-obvious interactions that catch new traders.

### Gamma scalping math

A delta-hedged long-gamma position profits when realized volatility exceeds implied volatility.

> **Rule (Natenberg):** The expected daily P&L of a delta-hedged long-gamma position is:
>
>     P&L ≈ 0.5 × Γ × S² × (σ_realized² − σ_implied²) / 252
>
> where Γ is dollar gamma, S is stock price. Positive only when realized vol exceeds implied. This is **the entire reason** delta-hedged long-straddle positions exist as a trade — you're betting realized > implied over the holding period. (Natenberg)

### Delta-Vega coupling

> **Rule (Natenberg):** ATM options have the **highest vega**. OTM options have **lower vega but higher percentage IV sensitivity**. A 1-point IV move on an ATM call moves the price more in dollars, but a 1-point move on a 20-delta call moves the price more in % terms — important when sizing tail-vol trades. (Natenberg)

### Theta vs Gamma trade-off

> **Rule (Overby):** Every options trade is a bet on the relationship: **realized vol vs implied vol** is **theta vs gamma**. If you're collecting theta (short premium), you're paying gamma — meaning you lose if realized vol > implied. If you're paying theta (long premium), you're collecting gamma — meaning you win if realized vol > implied. There's no free lunch. (Overby)

### Vega and DTE

> **Rule (Natenberg):** Vega scales roughly with **√DTE**. A 90-DTE option has ~√3 ≈ 1.73x the vega of a 30-DTE option at the same strike. So when you want vega exposure (long volatility view), use longer DTE; when you want to avoid vega risk (short premium views), use shorter DTE — but trade off against gamma risk. (Natenberg)

### Position-level vs single-leg Greeks

> **Rule (McMillan):** Never think of an iron condor as "selling premium." Think of it as a position with **net negative vega, net negative gamma, net positive theta, and bounded delta**. The decision to enter is not "do I want to sell premium" — it's "do I want all four of those exposures right now?" (McMillan)

### Charm and color (the second-order Greeks)

- **Charm** = dδ/dt = rate at which delta decays toward 0 (OTM) or ±1 (ITM) as time passes.
- **Color** = dγ/dt = rate at which gamma changes over time.

> **Rule (Natenberg):** Near expiry, charm and color **dominate** P&L for short-premium positions. A 1-DTE short straddle's gamma can triple intraday from a single 0.5% move. Manage 0–7 DTE positions in **delta terms hourly**, not daily. (Natenberg)

### Delta-equivalent share thinking

Convert option deltas to "equivalent shares" for portfolio-level risk:
- A short put with 0.30 delta and quantity 1 contract = `+0.30 × 100 = +30 delta-equivalent shares`.
- A long call with 0.70 delta and quantity 2 contracts = `+0.70 × 100 × 2 = +140 delta-equivalent shares`.

> **Rule (McMillan):** Compute portfolio-level **net delta** as a single number. If it's +5000 on a $100k account, you have leverage of 50× the underlying — a 2% move costs $10k. Most retail blowups happen when net delta drifts past 1× capital without the trader noticing. (McMillan)

---

## 10. Common Mistakes

Each book has its "don't" list. The overlap is instructive — these are the canonical retail-options errors.

### McMillan's list

1. **Buying out-of-the-money options "because they're cheap."** Low premium ≠ high expected value. OTM options have low probability of profit and high theta percentage decay.
2. **Holding losers and selling winners.** Standard prospect-theory error. Have a cut-loss plan **before** entry.
3. **Selling naked options without margin awareness.** A 10x margin spike during a vol event can force liquidation at the worst time.
4. **Ignoring early-assignment risk on ITM short calls before ex-dividend.** If the dividend exceeds the time value remaining, you will be assigned.
5. **Trading illiquid options.** Wide bid/ask spreads can cost 20–30% on round-trip.

### Overby's "5 mistakes new options traders make"

1. **Trading too big.** New traders typically risk 5–10% per trade; they should risk 1–2%.
2. **Trading too short DTE.** Weeklies feel exciting but gamma punishes mistakes immediately. Start at 45 DTE.
3. **Not knowing the risk graph before entry.** If you can't sketch the payoff diagram from memory, you'll panic when the position moves.
4. **Trading in low-liquidity underlyings.** Bid/ask spreads eat all the edge in obscure tickers. Stick to liquid names.
5. **Never closing winners early.** A short option at 50% of max profit has used 80% of the time but holds 50% of the remaining risk. Close at 50% and redeploy.

> **Rule (Overby):** **Never trade a strategy you can't draw on paper.** If you can't sketch the risk graph from memory, you'll panic when the position moves against you. (Overby)

### Natenberg's list

1. **Confusing IV with HV.** They measure different things. Sell premium when IV >> HV; buy premium when IV << HV.
2. **Underestimating skew.** OTM puts in equities are systematically more expensive than OTM calls. Pretending they're symmetric leads to mispriced credit spreads.
3. **Ignoring early-exercise risk on American options.** ITM puts can be optimally exercised early when interest rates are high; calls before dividends.
4. **Believing Black-Scholes prices the wings correctly.** It doesn't. The model assumes lognormal returns; reality has fat tails. Always check fat-tail-adjusted models for OTM wings.
5. **Trading vol without a vol forecast.** "Vol is high" is not a trade; "vol will be 18% over the next 30 days versus 22% priced" is a trade.

> **Rule (Natenberg):** A 30-DTE ATM option's price is approximately `S × σ × √(T/365) × 0.4`. Memorize this — it lets you sanity-check option quotes mentally. If a quote diverges from the back-of-envelope estimate by >30%, something's off (wrong contract, illiquidity, mispriced vol). (Natenberg)

### Sinclair's list

1. **Over-fitting GARCH on small samples.** Vol forecasts from <2 years of data are essentially noise.
2. **Sizing by intuition rather than Kelly fraction.** Most retail traders are 2-3x too large.
3. **Trading low-edge structures (ATM straddles) as if they're high-edge.** ATM straddles are nearly market-neutral on vol; the edge is small.
4. **Holding through earnings on long premium positions.** IV crush dominates direction.
5. **Ignoring transaction costs.** Bid/ask spreads + commission + slippage often eat 15–25% of expected edge on retail options trades.

> **Rule (Sinclair):** **Volatility trading is statistics, not directional speculation.** If your trade thesis doesn't include a number (forecast vol, expected variance, IV percentile threshold), you're not vol trading — you're directional trading with options on top. (Sinclair)

---

## Appendix: Quick decision card

When the user asks "should I trade options on X?" — run this checklist:

| Step | Check | Source |
|---|---|---|
| 1 | What's the IV percentile? (≤20 → buy; ≥80 → sell; 20–80 → spread) | McMillan |
| 2 | What's the term structure? (Backwardation → upcoming event; contango → calm) | Natenberg |
| 3 | What's the put skew? (Steep → sell put spreads; flat → buy puts outright) | Sinclair |
| 4 | Earnings inside DTE? (If yes → assume IV crush will dominate) | McMillan |
| 5 | What target delta for short legs? (Match the strategy: see table §2) | Overby |
| 6 | What DTE? (45 default for short premium; 60–90 for calendars) | Overby |
| 7 | Position size: ≤2% account on defined-risk; ≤5% margin on undefined | McMillan/Overby |
| 8 | Can I draw the risk graph from memory? If no → don't trade it | Overby |
| 9 | What's my exit rule (% profit and % loss) before entry? | All books |
| 10 | What adjustment will I make if it moves against me, and at what trigger? | McMillan |

If you can answer all 10 with concrete numbers, the trade is well-specified. If any answer is "I don't know" — wait, study, or skip the trade.

---

## 11. Pricing Model Limitations

When does Black-Scholes lie? Often. Knowing where the model breaks tells you where the edge lives.

### Where Black-Scholes is reliable

| Condition | BS quality |
|---|---|
| ATM, liquid, 30–90 DTE | Excellent — model and market agree to within bid/ask |
| Far OTM puts in equities | **Poor** — market prices fat-tail risk that BS understates |
| Far OTM calls in equities | Often overpriced vs BS (squeeze/takeover premium) |
| Short-dated (<7 DTE) | **Poor** — jump-diffusion effects dominate Brownian motion assumption |
| Right before earnings | **Poor** — market prices an event-jump that BS can't represent |
| In high-rates / dividend regimes | OK for European; poor for American without early-exercise adjustment |

> **Rule (Natenberg):** Black-Scholes assumes (a) lognormal returns, (b) no jumps, (c) constant volatility, (d) constant interest rate, (e) continuous trading, (f) no transaction costs. Real markets violate every assumption. The model is most-wrong at the tails (far OTM) and around events. **The model's "implied volatility" is not a forecast — it's the volatility that makes the (wrong) BS formula match the (right) market price.** (Natenberg)

### The volatility smile = BS error map

A volatility smile or skew is literally a map of where Black-Scholes is wrong. If BS were correct, all strikes on the same expiry would have the same IV.

> **Rule (Sinclair):** A useful mental model: BS-implied IV at strike K is a **probability-weighted average** of vol scenarios in which the underlying ends near K. Steep put skew → market assigns high probability to crash scenarios. Flat skew → market assigns symmetric outcome probabilities. **Don't trade against the skew without understanding why it's there.** (Sinclair)

### When to use jump-diffusion or stochastic-vol models

> **Rule (Natenberg):** For OTM wings and binary-event-pricing (earnings, FDA approvals, court rulings), use a **jump-diffusion model** (Merton, SVJ) or a **Heston-style stochastic-vol model**. BS systematically under-prices tail risk by 30–60% in equities. The retail trader's cheap edge: **buying OTM tail wings when implied skew is at the 10th percentile.** (Natenberg)

---

## 12. The Trading Plan Template

Before opening any options trade, fill in these blanks. If you can't, don't trade.

| Field | Example |
|---|---|
| Underlying | SPY |
| Strategy | Iron condor |
| Outlook | Range-bound between 590 and 620 over next 30 days |
| IV environment | IV percentile = 62 (mid-range, slight premium-sell bias) |
| Earnings inside DTE? | No earnings until Q2 next quarter |
| Strikes | -2σ put / +2σ call (each ~0.16 delta) |
| DTE | 38 |
| Net credit | $1.20 |
| Max loss | $3.80 (= $5 wing − $1.20 credit) |
| Max profit | $1.20 |
| Win rate (probability of full credit) | ~68% (1 − 2 × 0.16) |
| Position size (contracts) | 1 (= 1% of $38k account at max loss) |
| Profit-take exit | Close at 50% of max profit ($0.60) |
| Stop-loss exit | Close at 2x credit loss ($2.40) |
| Adjustment trigger | If one side reaches ~30 delta, roll untested side for credit |
| Roll cap | 1 roll maximum |
| Time-stop | Close at 21 DTE regardless of P&L |

> **Rule (McMillan):** Writing this down is not bureaucracy — it's the difference between a trade and a gamble. If you can't fill in the **stop-loss** and **time-stop** lines, your "trade idea" is actually an open-ended bet, which is the structural cause of most account drawdowns. (McMillan)

---

## 13. Behavioral Pitfalls (cross-cutting)

The four traps that recur in all four books.

### 1. Anchoring to entry price

Once a trade is open, your reference price should be **current market** — not your entry. A short put at $1.20 credit, now trading $0.40 to close, is the same risk-reward as opening a new short put at $0.40 with $0.40 max profit, $4.60 max loss. You'd never open that trade fresh. Close it.

> **Rule (Overby):** **The 50% profit-take rule (close at half of max profit) is the single highest-Sharpe behavior change a short-premium trader can adopt.** It exploits the asymmetry that early profits are easy to capture, while the last 20–30% of premium carries 50%+ of the remaining gamma risk. (Overby)

### 2. Doubling down on losers

> **Rule (McMillan):** "Averaging down" works for value investors who can hold indefinitely. In options it is **the textbook way to blow up an account**. Each leg's max loss is bounded; each addition adds new max loss; theta works against you on all of them. Cut, don't average. (McMillan)

### 3. Selling cheap options for "safety"

Selling a 0.05-delta put feels safe — 95% probability of profit. But the premium is tiny, and one black-swan event wipes out 20+ "winning" trades. The math: 95% × $10 + 5% × $-500 = +$9.50 − $25 = **−$15.50 expected value.** Negative-EV with high win rate is the most common trap in options.

> **Rule (Sinclair):** Win rate is meaningless without expected value. A 99% win rate strategy is a disaster if the 1% loss is 200x the average win. Calculate expected value, not win rate. (Sinclair)

### 4. Trading because you're bored

> **Rule (Overby):** The single most expensive psychological state in options is **boredom**. There is no penalty for sitting in cash. There is enormous penalty for trading sub-optimal setups to feel productive. (Overby)

---

## Cross-references

- For the strategy catalog (long call, iron condor, jade lizard, etc.) with payoff structures: [`strategies.md`](strategies.md)
- For Greeks interpretation (delta, gamma, vega, theta, rho): [`greeks_primer.md`](greeks_primer.md)
- For the wheel-strategy roll-vs-assign decision tree: [`wheel_strategy.md`](wheel_strategy.md)
- For IBKR/connectivity errors: [`troubleshooting.md`](troubleshooting.md)
