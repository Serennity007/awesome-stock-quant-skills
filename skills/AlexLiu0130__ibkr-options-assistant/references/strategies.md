# Options Strategy Library

Combined library from Larry McMillan's *Options as a Strategic Investment* and Brian Overby's *The Options Playbook*. The `options_analyzer.py` script selects from this set based on **outlook × risk_profile × IV environment**.

## Table of Contents

- [How to read this doc](#how-to-read-this-doc)
- [IV environment guidance](#iv-environment-guidance)
- [Selection matrix](#selection-matrix-outlook--risk_profile)
- [Tier 1 — Rookie (single-leg)](#tier-1--rookie-single-leg)
- [Tier 2 — Intermediate (two-leg spreads)](#tier-2--intermediate-two-leg-spreads)
- [Tier 3 — Advanced (3–4 leg)](#tier-3--advanced-34-leg)
- [Tier 4 — Expert (ratio & synthetic)](#tier-4--expert-ratio--synthetic)

---

## How to read this doc

Each strategy entry has:

| Field | Meaning |
|---|---|
| **Name (EN / CN)** | English / Chinese name. |
| **Direction** | `bullish` / `bearish` / `neutral` / `volatile` market view. |
| **Construction** | Legs (`BUY`/`SELL`, `Call`/`Put`, strike offset relative to ATM). |
| **When to use** | The setup this strategy is built for. |
| **IV preference** | `low` (buy premium) · `high` (sell premium) · `neutral` (spreads). |
| **Max profit / loss** | Per 1 contract; multiply by 100 for $ on US equity options. |
| **Risk profile** | `conservative` / `moderate` / `aggressive` — who should consider it. |

Strike offsets are measured in **strike steps** (the gap between adjacent listed strikes). `0` = ATM, `+2` = two strikes OTM call side, `-2` = two strikes OTM put side, etc.

---

## IV environment guidance

`options_analyzer.py --iv-context` compares the current average IV across the chain to 20-day realized volatility and returns one of three regimes:

| Regime | Trigger | Bias |
|---|---|---|
| **IV high** | `IV / HV > 1.3` | Sell premium — credit spreads, CSPs, covered calls, iron condors. |
| **IV neutral** | `0.8 ≤ IV / HV ≤ 1.3` | Spread-driven — directional debit/credit spreads. |
| **IV low** | `IV / HV < 0.8` | Buy premium — long options, straddles/strangles, ratio backspreads. |

The analyzer re-ranks candidates inside a given outlook × risk_profile cell so that IV-matched strategies come first.

---

## Selection matrix (outlook × risk_profile)

This is the literal mapping inside `options_analyzer.py` — the first strategy in each cell is the default suggestion.

| Outlook | Conservative | Moderate | Aggressive |
|---|---|---|---|
| **Bullish** | Covered Call · Cash-Secured Put · Collar | Bull Call Spread · Bull Put Spread | Long Call · Call Ratio Backspread · Risk Reversal |
| **Bearish** | Protective Put · Bear Call Spread | Bear Put Spread | Long Put · Put Ratio Backspread |
| **Neutral** | Covered Call · Iron Condor | Iron Condor · Iron Butterfly · Jade Lizard | Short Straddle · Short Strangle |
| **Volatile** | Long Strangle | Long Straddle · Long Strangle | Long Straddle · Call Ratio Backspread |

> **Note on "Aggressive Bearish":** selling unhedged calls (Short Call) is intentionally excluded because of unlimited upside risk. Use a defined-risk bear call spread instead.

---

## Tier 1 — Rookie (single-leg)

### Long Call · 买入看涨

- **Direction:** bullish · aggressive.
- **Construction:** BUY 1 Call ATM.
- **When to use:** strong directional conviction, expecting a sharp move up before expiry.
- **IV preference:** low (you're long vega).
- **Max profit:** unlimited.
- **Max loss:** premium paid.
- **Breakeven:** strike + premium.

### Long Put · 买入看跌

- **Direction:** bearish · aggressive.
- **Construction:** BUY 1 Put ATM.
- **When to use:** strong downside conviction.
- **IV preference:** low.
- **Max profit:** strike − premium (down to zero).
- **Max loss:** premium paid.
- **Breakeven:** strike − premium.

### Cash-Secured Put (CSP) · 现金担保卖出看跌

- **Direction:** bullish (or neutral-to-bullish) · conservative / moderate.
- **Construction:** SELL 1 Put, typically 2 strikes OTM; reserve cash to buy 100 shares at the strike.
- **When to use:** willing to own the stock at a discount; collect premium otherwise. **Stage 1 of the wheel.**
- **IV preference:** high.
- **Max profit:** premium collected.
- **Max loss:** (strike − premium) × 100 if the stock goes to zero.
- **Breakeven:** strike − premium.

### Covered Call · 备兑看涨

- **Direction:** bullish (mildly) · conservative.
- **Construction:** OWN 100 shares + SELL 1 OTM Call.
- **When to use:** generate yield on existing stock; OK with capping upside. **Stage 3 of the wheel.**
- **IV preference:** high.
- **Max profit:** (call_strike − cost_basis + premium) × 100.
- **Max loss:** stock fall − premium (downside is the same as owning the stock, minus what you collected).
- **Breakeven:** cost_basis − premium.

### Protective Put · 保护性看跌

- **Direction:** neutral (insurance) · conservative.
- **Construction:** OWN 100 shares + BUY 1 OTM Put.
- **When to use:** worried about a near-term drawdown but don't want to sell.
- **IV preference:** low.
- **Max profit:** unlimited (stock upside) − premium.
- **Max loss:** capped at (cost_basis − put_strike + premium) × 100.

---

## Tier 2 — Intermediate (two-leg spreads)

### Bull Call Spread · 牛市看涨价差

- **Direction:** bullish · moderate.
- **Construction:** BUY Call at ATM, SELL Call 3 strikes higher.
- **When to use:** moderate upside view; want to cap cost vs. long call.
- **IV preference:** neutral.
- **Max profit:** (width − net_debit) × 100.
- **Max loss:** net_debit × 100.
- **Breakeven:** long_strike + net_debit.

### Bear Put Spread · 熊市看跌价差

- **Direction:** bearish · moderate.
- **Construction:** BUY Put at ATM, SELL Put 3 strikes lower.
- **When to use:** moderate downside view; cheaper than long put.
- **IV preference:** neutral.
- **Max profit:** (width − net_debit) × 100.
- **Max loss:** net_debit × 100.
- **Breakeven:** long_strike − net_debit.

### Bull Put Spread (credit) · 牛市看跌价差

- **Direction:** bullish · moderate.
- **Construction:** SELL Put 1 strike OTM, BUY Put 4 strikes OTM.
- **When to use:** bullish AND high IV — get paid to be right.
- **IV preference:** high.
- **Max profit:** net_credit × 100.
- **Max loss:** (width − net_credit) × 100.
- **Breakeven:** short_put_strike − net_credit.

### Bear Call Spread (credit) · 熊市看涨价差

- **Direction:** bearish · moderate (conservative-friendly).
- **Construction:** SELL Call 1 strike OTM, BUY Call 4 strikes OTM.
- **When to use:** bearish-to-neutral AND high IV.
- **IV preference:** high.
- **Max profit:** net_credit × 100.
- **Max loss:** (width − net_credit) × 100.
- **Breakeven:** short_call_strike + net_credit.

### Long Straddle · 买入跨式

- **Direction:** volatile · moderate / aggressive.
- **Construction:** BUY Call ATM + BUY Put ATM.
- **When to use:** expecting a big move, unsure direction (e.g. binary event).
- **IV preference:** low (vega risk — IV crush on earnings kills it).
- **Max profit:** unlimited (up); large (down).
- **Max loss:** total premium paid.
- **Breakeven:** strike ± total_premium.

### Short Straddle · 卖出跨式

- **Direction:** neutral · aggressive (unlimited risk).
- **Construction:** SELL Call ATM + SELL Put ATM.
- **When to use:** expecting tight range; high IV that will collapse.
- **IV preference:** high.
- **Max profit:** total premium received.
- **Max loss:** unlimited.
- **Breakeven:** strike ± total_premium.

### Long Strangle · 买入宽跨式

- **Direction:** volatile · moderate.
- **Construction:** BUY OTM Call (+2) + BUY OTM Put (−2).
- **When to use:** big move expected, cheaper than straddle but needs larger move.
- **IV preference:** low.
- **Max profit:** unlimited.
- **Max loss:** total premium.
- **Breakeven:** call_strike + prem · put_strike − prem.

### Short Strangle · 卖出宽跨式

- **Direction:** neutral · moderate / aggressive.
- **Construction:** SELL OTM Call (+3) + SELL OTM Put (−3).
- **When to use:** range-bound with high IV; wider safety than short straddle.
- **IV preference:** high.
- **Max profit:** total premium.
- **Max loss:** unlimited (both sides).
- **Breakeven:** call_strike + prem · put_strike − prem.

### Collar · 领口策略

- **Direction:** neutral (hedged) · conservative.
- **Construction:** OWN stock + BUY OTM Put (−2) + SELL OTM Call (+2). Often near zero cost.
- **When to use:** lock in a gain; protect against a drop without paying for the put.
- **IV preference:** neutral.
- **Max profit:** capped at call_strike − cost_basis ± net_credit.
- **Max loss:** capped at cost_basis − put_strike ∓ net_credit.

---

## Tier 3 — Advanced (3–4 leg)

### Iron Condor · 铁秃鹰

- **Direction:** neutral · conservative / moderate.
- **Construction:** SELL OTM Put + BUY further OTM Put **AND** SELL OTM Call + BUY further OTM Call.
- **When to use:** range-bound stock, want defined risk on a short strangle.
- **IV preference:** high.
- **Max profit:** net_credit × 100.
- **Max loss:** (max(put_width, call_width) − net_credit) × 100.
- **Breakeven:** short_put − net_credit · short_call + net_credit.

### Iron Butterfly · 铁蝶式

- **Direction:** neutral · moderate.
- **Construction:** SELL ATM Put + SELL ATM Call + BUY OTM Put (−3) + BUY OTM Call (+3).
- **When to use:** stock will pin near ATM by expiry; want bigger credit than iron condor.
- **IV preference:** high.
- **Max profit:** net_credit × 100 (at ATM at expiry).
- **Max loss:** (wing_width − net_credit) × 100.

### Long Call Butterfly · 买入蝶式

- **Direction:** neutral · moderate (defined risk).
- **Construction:** BUY 1 ITM Call (−3) + SELL 2 ATM Calls + BUY 1 OTM Call (+3).
- **When to use:** pin play, low cost. Loves time decay if price stays near middle strike.
- **IV preference:** neutral.
- **Max profit:** at middle strike at expiry — (wing_width − net_debit) × 100.
- **Max loss:** net_debit × 100.

### Jade Lizard · 翡翠蜥蜴

- **Direction:** bullish (with upside protection) · moderate.
- **Construction:** SELL OTM Put + SELL OTM Call + BUY further OTM Call. Net credit ≥ call spread width → **no upside risk**.
- **When to use:** bullish AND high IV, but want a hedge in case of upside gap.
- **IV preference:** high.
- **Max profit:** net_credit × 100 (in the no-touch range).
- **Max loss:** put-side: strike_put − net_credit. Upside loss zero by construction.

---

## Tier 4 — Expert (ratio & synthetic)

### Call Ratio Backspread · 看涨比率反向价差

- **Direction:** bullish (sharp move) · aggressive.
- **Construction:** SELL 1 Call near ATM + BUY 2 Calls 3 strikes OTM.
- **When to use:** convex upside bet; profits on big rallies, small loss on tight range.
- **IV preference:** low (long vega net).
- **Max profit:** unlimited.
- **Max loss:** between strikes (zone of pain). Bounded.

### Put Ratio Backspread · 看跌比率反向价差

- **Direction:** bearish (sharp drop) · aggressive.
- **Construction:** SELL 1 Put near ATM + BUY 2 Puts 3 strikes OTM.
- **When to use:** crash protection / convex downside bet.
- **IV preference:** low.
- **Max profit:** large (down to zero).
- **Max loss:** between strikes.

### Risk Reversal · 风险反转

- **Direction:** bullish · aggressive.
- **Construction:** BUY OTM Call (+2) + SELL OTM Put (−2). Often near zero cost.
- **When to use:** strong upside conviction, willing to be assigned at the put strike. Synthetic long stock with a gap.
- **IV preference:** neutral.
- **Max profit:** unlimited.
- **Max loss:** put_strike × 100 (if stock goes to zero, minus net credit).

---

## Cheat sheet — choose by intent

| If you want to… | Look at |
|---|---|
| Get paid to wait for a buy entry | Cash-Secured Put |
| Earn yield on stock you own | Covered Call |
| Hedge a winning stock position | Collar / Protective Put |
| Bet on direction cheaply | Long Call / Long Put |
| Bet on direction with capped cost | Bull/Bear Call/Put Spreads |
| Get paid for range-bound view (defined risk) | Iron Condor / Iron Butterfly |
| Get paid for range-bound view (max premium) | Short Straddle / Strangle |
| Bet on a big move (direction unknown) | Long Straddle / Strangle |
| Convex bullish or bearish bet | Ratio Backspread |
| Bullish with disaster hedge upside | Jade Lizard |
