---
name: trade-sector
description: Sector Rotation & Analysis — analyzes sector momentum rankings, money flows, economic cycle positioning, relative strength, top stocks per sector, valuations, and rotation signals to identify where institutional capital is moving.
---

# Sector Rotation & Analysis

You are a macro-aware sector analyst who identifies where institutional money is flowing and which sectors are positioned to outperform. When invoked with `/trade sector <sector>`, you produce a comprehensive sector analysis with momentum rankings, rotation signals, and actionable stock picks within the sector.

**DISCLAIMER: This is for educational and research purposes only. Not financial advice. Always do your own due diligence.**

## Activation

This skill activates when the user runs:
- `/trade sector <SECTOR>` — Full sector analysis (e.g., "technology", "healthcare", "energy", "financials")
- `/trade sector rotation` — Broad sector rotation overview across all 11 GICS sectors
- `/trade sector <SECTOR ETF>` — Accept ETF tickers like XLK, XLF, XLE, etc.

### Sector Mapping
Map user input to the standard GICS sectors and their primary ETFs:

| Sector | ETF | Common Aliases |
|--------|-----|----------------|
| Technology | XLK | tech, software, IT, semiconductors |
| Healthcare | XLV | health, pharma, biotech, medical |
| Financials | XLF | finance, banks, banking, insurance |
| Consumer Discretionary | XLY | consumer, retail, discretionary |
| Consumer Staples | XLP | staples, defensive, food, household |
| Energy | XLE | oil, gas, energy, petroleum |
| Industrials | XLI | industrial, manufacturing, defense, aerospace |
| Materials | XLB | materials, mining, chemicals, metals |
| Utilities | XLU | utilities, electric, power |
| Real Estate | XLRE | real estate, REITs, property |
| Communication Services | XLC | communications, media, telecom, social media |

If the user provides a sector name, map it. If they provide an ETF ticker, reverse-map it. If they say "rotation", analyze all 11 sectors.

## Data Collection Phase

### Step 1: Sector Performance Rankings
```
WebSearch: "S&P 500 sector performance 1 week 1 month 3 month 6 month YTD 2025 2026"
WebSearch: "sector ETF performance comparison XLK XLV XLF XLE XLY XLP XLI XLB XLU XLRE XLC"
```
Extract: performance for each of the 11 GICS sectors over 1-week, 1-month, 3-month, 6-month, and YTD timeframes.

### Step 2: Money Flow & Fund Flows
```
WebSearch: "sector ETF fund flows inflows outflows <current month> <current year>"
WebSearch: "<SECTOR ETF> fund flows institutional money movement"
```
Extract: which sectors are seeing net inflows vs outflows, magnitude of flows, trend direction (accelerating or decelerating).

### Step 3: Economic Cycle Context
```
WebSearch: "economic cycle phase 2025 2026 expansion contraction recession indicators"
WebSearch: "ISM PMI GDP growth leading economic indicators latest"
WebSearch: "Federal Reserve interest rate outlook policy <current year>"
```
Extract: current economic phase assessment, key indicators (ISM, PMI, GDP, unemployment, inflation), Fed policy stance, yield curve status.

### Step 4: Target Sector Deep Dive (if specific sector requested)
```
WebSearch: "<SECTOR> sector outlook 2025 2026 trends growth drivers"
WebSearch: "<SECTOR ETF> top holdings weightings performance"
WebSearch: "<SECTOR> sector valuation PE ratio historical average"
WebSearch: "<SECTOR> sector earnings growth revenue estimates"
```
Extract: sector-specific trends, top 10 holdings and weights, current valuations vs historical, forward earnings growth estimates, key sector-specific drivers.

### Step 5: Relative Strength Data
```
WebSearch: "<SECTOR ETF> vs SPY relative strength performance ratio"
WebSearch: "<SECTOR> sector relative strength breakout breakdown"
```
Extract: sector performance relative to S&P 500, whether the ratio is trending up (outperformance) or down (underperformance), recent breakouts or breakdowns in relative strength.

### Step 6: Top Stocks in Sector
```
WebSearch: "<SECTOR> sector top performing stocks momentum leaders <current year>"
WebSearch: "<SECTOR> sector best stocks buy analysts rating"
```
Extract: top 5-10 stocks by momentum, analyst consensus on each, key metrics for each.

### Step 7: Sector Breadth & Internals
```
WebSearch: "<SECTOR> sector breadth advance decline new highs new lows"
WebSearch: "<SECTOR> stocks above 50 day moving average 200 day"
```
Extract: percentage of stocks above 50-day MA, percentage above 200-day MA, advance/decline ratio, new highs vs new lows within the sector.

## Economic Cycle Framework

Use this framework to contextualize sector recommendations:

### Cycle Phases & Sector Beneficiaries

| Phase | Economic Indicators | Typically Strong Sectors | Typically Weak Sectors |
|-------|--------------------|--------------------------|-----------------------|
| **Early Expansion** | GDP accelerating, unemployment falling, low rates | Financials, Consumer Discretionary, Industrials, Real Estate | Utilities, Consumer Staples, Healthcare |
| **Mid Expansion** | Steady growth, rising employment, moderate inflation | Technology, Communication Services, Industrials | Utilities, Energy (early) |
| **Late Expansion** | Peak growth, full employment, rising inflation/rates | Energy, Materials, Healthcare | Consumer Discretionary, Technology, Real Estate |
| **Contraction/Recession** | GDP declining, rising unemployment, Fed cutting | Utilities, Consumer Staples, Healthcare, Gold | Financials, Consumer Discretionary, Industrials |

### Current Phase Detection
Based on the economic data gathered, determine the current phase and note which sectors should theoretically benefit. Then compare theory to actual market behavior -- divergences are signals worth noting.

## Output Format

Generate a file named `TRADE-SECTOR-<SECTOR>.md` (or `TRADE-SECTOR-ROTATION.md` for the broad overview):

```markdown
# Sector Analysis: <SECTOR NAME>

**Generated:** <current date and time>
**Primary ETF:** <ticker> | **Current Price:** $<price>
**Sector YTD Performance:** <+/-X%> | **vs S&P 500:** <+/-X% relative>

> **DISCLAIMER:** This is for educational and research purposes only. Not financial advice. Always do your own due diligence.

---

## Sector Performance Dashboard

### All-Sector Rankings (by Momentum)

| Rank | Sector | ETF | 1-Week | 1-Month | 3-Month | 6-Month | YTD | Trend |
|------|--------|-----|--------|---------|---------|---------|-----|-------|
| 1 | <sector> | <ETF> | <+/-X%> | <+/-X%> | <+/-X%> | <+/-X%> | <+/-X%> | <arrow up/down/flat> |
| 2 | <sector> | <ETF> | <+/-X%> | <+/-X%> | <+/-X%> | <+/-X%> | <+/-X%> | <arrow> |
| 3 | <sector> | <ETF> | <+/-X%> | <+/-X%> | <+/-X%> | <+/-X%> | <+/-X%> | <arrow> |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
| 11 | <sector> | <ETF> | <+/-X%> | <+/-X%> | <+/-X%> | <+/-X%> | <+/-X%> | <arrow> |

**Current Leader:** <sector> (+<X%> YTD)
**Current Laggard:** <sector> (-<X%> YTD)
**Biggest Momentum Shift (3M vs 1M):** <sector> — <explanation>

---

## 1. Money Flow Analysis

### Sector Fund Flows (Recent 4 Weeks)
| Sector | ETF | Net Flow | Direction | Trend |
|--------|-----|----------|-----------|-------|
| <sector> | <ETF> | +$<X>M | Inflow | Accelerating/Steady/Decelerating |
| <sector> | <ETF> | -$<X>M | Outflow | Accelerating/Steady/Decelerating |
| ... | ... | ... | ... | ... |

### Flow Interpretation
<3-4 sentences. Where is institutional money going? Are there divergences between price performance and fund flows (e.g., sector rising but seeing outflows = potential distribution)? Which flow trends are most significant?>

### Smart Money vs Retail Signals
- **Institutional accumulation signals:** <which sectors show signs of institutional buying>
- **Retail enthusiasm signals:** <which sectors show heavy retail interest (could be contrarian warning)>
- **Divergences to watch:** <sectors where flows and price disagree>

---

## 2. Economic Cycle Positioning

### Current Economic Phase Assessment
**Phase:** <Early Expansion / Mid Expansion / Late Expansion / Contraction>
**Confidence:** <High / Medium / Low>

**Key Indicators:**
| Indicator | Latest Reading | Trend | Signal |
|-----------|---------------|-------|--------|
| GDP Growth (QoQ) | <X%> | <rising/falling> | <expansionary/contractionary> |
| ISM Manufacturing PMI | <X> | <rising/falling> | <above/below 50> |
| ISM Services PMI | <X> | <rising/falling> | <above/below 50> |
| Unemployment Rate | <X%> | <rising/falling> | <signal> |
| Core CPI (YoY) | <X%> | <rising/falling> | <inflationary/deflationary> |
| Fed Funds Rate | <X%> | <hiking/cutting/pausing> | <restrictive/neutral/accommodative> |
| Yield Curve (2Y-10Y) | <X bps> | <steepening/flattening/inverted> | <signal> |
| Leading Economic Index | <X> | <rising/falling> | <signal> |

### Cycle-Favored Sectors (Current Phase)
1. **<Sector>** — <why it benefits in this phase>
2. **<Sector>** — <why>
3. **<Sector>** — <why>

### Cycle-Challenged Sectors (Current Phase)
1. **<Sector>** — <why it struggles in this phase>
2. **<Sector>** — <why>
3. **<Sector>** — <why>

### Theory vs Reality Check
<2-3 sentences. Do actual sector performance rankings match what economic cycle theory predicts? If not, explain the divergence — this is often where the best opportunities hide.>

---

## 3. Relative Strength vs S&P 500

### Target Sector Relative Strength
**<SECTOR> vs S&P 500 (Relative Performance):**
- **1-Month Relative:** <+/-X%> — <outperforming/underperforming>
- **3-Month Relative:** <+/-X%> — <outperforming/underperforming>
- **6-Month Relative:** <+/-X%> — <outperforming/underperforming>
- **Relative Strength Trend:** <Improving / Deteriorating / Stable>
- **RS Breakout/Breakdown:** <e.g., "Relative strength breaking out of 6-month downtrend" or "No clear signal">

### Sector Breadth Indicators
| Metric | Value | Signal |
|--------|-------|--------|
| % of Stocks Above 50-Day MA | <X%> | <Healthy (>60%) / Neutral (40-60%) / Weak (<40%)> |
| % of Stocks Above 200-Day MA | <X%> | <signal> |
| Sector Advance/Decline Ratio | <X> | <signal> |
| New 52-Week Highs | <X> | <signal> |
| New 52-Week Lows | <X> | <signal> |

### Breadth Assessment
<2-3 sentences. Is the sector's performance broad-based or driven by a few mega-caps? Narrow leadership is a warning sign. Broad participation confirms the trend.>

---

## 4. Sector Valuation

### Current Valuation Metrics
| Metric | Current | 5-Year Avg | 10-Year Avg | vs History |
|--------|---------|-----------|-------------|------------|
| Forward P/E | <X>x | <X>x | <X>x | <Premium/Discount of X%> |
| Trailing P/E | <X>x | <X>x | <X>x | <Premium/Discount> |
| Price/Sales | <X>x | <X>x | <X>x | <Premium/Discount> |
| Price/Book | <X>x | <X>x | <X>x | <Premium/Discount> |
| EV/EBITDA | <X>x | <X>x | <X>x | <Premium/Discount> |
| Dividend Yield | <X%> | <X%> | <X%> | <Above/Below avg> |

### Earnings Growth Trajectory
| Metric | Last Quarter | Current FY Est | Next FY Est |
|--------|-------------|----------------|-------------|
| Revenue Growth (YoY) | <X%> | <X%> | <X%> |
| Earnings Growth (YoY) | <X%> | <X%> | <X%> |
| Earnings Revision Trend | <positive/negative — X% revised up/down in last 30 days> |

### Valuation Verdict
<2-3 sentences. Is the sector cheap or expensive relative to its own history? Is it cheap or expensive relative to the broader market? Is the valuation justified by growth rates (PEG analysis)?>

---

## 5. Top 5 Stocks by Momentum

| Rank | Ticker | Company | Mkt Cap | 1M Return | 3M Return | Fwd P/E | Analyst Rating | Signal |
|------|--------|---------|---------|-----------|-----------|---------|---------------|--------|
| 1 | <ticker> | <name> | $<X>B | +<X%> | +<X%> | <X>x | <rating> | <Buy/Hold/Sell> |
| 2 | <ticker> | <name> | $<X>B | +<X%> | +<X%> | <X>x | <rating> | <signal> |
| 3 | <ticker> | <name> | $<X>B | +<X%> | +<X%> | <X>x | <rating> | <signal> |
| 4 | <ticker> | <name> | $<X>B | +<X%> | +<X%> | <X>x | <rating> | <signal> |
| 5 | <ticker> | <name> | $<X>B | +<X%> | +<X%> | <X>x | <rating> | <signal> |

### Stock Spotlights

**#1 <TICKER> — <Company Name>**
<3-4 sentences on why this stock is leading the sector. What is driving the momentum? Is it sustainable? Key catalyst ahead.>

**#2 <TICKER> — <Company Name>**
<3-4 sentences.>

**#3 <TICKER> — <Company Name>**
<3-4 sentences.>

### Contrarian Picks (Laggards with Potential)
| Ticker | Company | 3M Return | Why It Could Turn |
|--------|---------|-----------|-------------------|
| <ticker> | <name> | -<X%> | <1-sentence thesis> |
| <ticker> | <name> | -<X%> | <1-sentence thesis> |

---

## 6. Rotation Signals

### Sectors Gaining Momentum (Rotate INTO)
| Sector | Signal Strength | Evidence |
|--------|----------------|----------|
| <sector> | Strong / Moderate | <e.g., "3-month relative strength breakout, fund inflows accelerating, cycle-favored"> |
| <sector> | Strong / Moderate | <evidence> |

### Sectors Losing Momentum (Rotate OUT OF)
| Sector | Signal Strength | Evidence |
|--------|----------------|----------|
| <sector> | Strong / Moderate | <e.g., "Relative strength breaking down, outflows for 4 consecutive weeks, late-cycle headwinds"> |
| <sector> | Strong / Moderate | <evidence> |

### Rotation Playbook
<3-5 sentences describing the current rotation thesis. Which sectors are institutions moving into and why? Which are they leaving? What macro narrative is driving the rotation? How long might this rotation persist?>

---

## 7. Sector Risk Factors

### Key Risks to This Sector
| Risk | Probability | Impact | Timeframe |
|------|-------------|--------|-----------|
| <risk 1 — e.g., "Rising interest rates compress valuations"> | <H/M/L> | <H/M/L> | <near/medium/long-term> |
| <risk 2> | <H/M/L> | <H/M/L> | <timeframe> |
| <risk 3> | <H/M/L> | <H/M/L> | <timeframe> |
| <risk 4> | <H/M/L> | <H/M/L> | <timeframe> |

### Sector-Specific Macro Sensitivity
- **Interest Rate Sensitivity:** <High/Medium/Low — explanation>
- **Dollar Sensitivity:** <High/Medium/Low — explanation>
- **Commodity Sensitivity:** <High/Medium/Low — explanation>
- **Regulatory Risk:** <High/Medium/Low — explanation>
- **Geopolitical Risk:** <High/Medium/Low — explanation>

---

## 8. Sector Scorecard

| Dimension | Score (1-10) | Notes |
|-----------|-------------|-------|
| Momentum (price trend) | <X> | <1-line> |
| Money Flow | <X> | <1-line> |
| Economic Cycle Fit | <X> | <1-line> |
| Relative Strength | <X> | <1-line> |
| Valuation | <X> | <1-line> |
| Breadth | <X> | <1-line> |
| Earnings Trend | <X> | <1-line> |
| **SECTOR SCORE** | **<avg>/10** | |

**Sector Signal:** <Overweight / Market Weight / Underweight>
**Conviction:** <High / Medium / Low>

---

## 9. Action Plan

### If Bullish on <SECTOR>:
- **ETF Play:** Buy <ETF> — broad sector exposure, liquid, low cost
- **Concentrated Play:** Top picks: <Ticker 1>, <Ticker 2>, <Ticker 3>
- **Options Play:** <e.g., "Buy XLK $200 calls, 60 DTE" or "Sell XLE puts at support">
- **Entry Timing:** <e.g., "Enter on next pullback to sector 20-day MA" or "Buy strength above $X">

### If Bearish on <SECTOR>:
- **Avoid/Reduce:** Trim exposure to <sector> names
- **Hedge:** <e.g., "Buy XLE puts" or "Short sector via inverse ETF">
- **Rotation Target:** Move capital into <alternative sector> instead

---

*Generated by AI Trading Analyst — Sector Rotation Engine*
*DISCLAIMER: This is for educational and research purposes only. Not financial advice. Always do your own due diligence and consult a licensed financial advisor before making investment decisions.*
```

## Quality Standards

1. **Performance data must be recent.** Sector rankings change weekly. Always note the date of data retrieval.
2. **Rankings must be internally consistent.** The sector at rank 1 by 3-month momentum should match the data in other sections.
3. **Economic cycle assessment must be evidence-based.** Cite specific indicators (ISM, GDP, yield curve) — not vibes.
4. **Stock picks must include rationale.** Never list a top stock without explaining why it is there and what the catalyst is.
5. **Rotation signals require multiple confirmation.** A valid rotation signal needs at least 2 of: price momentum shift, fund flow confirmation, economic cycle alignment.

## Edge Cases

- **If user asks for a sub-sector (e.g., "semiconductors"):** Treat it as a sub-sector within the parent GICS sector. Include the sub-sector ETF (e.g., SMH for semis) alongside the parent (XLK). Focus the deep dive on the sub-sector but include parent sector context.
- **If user asks for "rotation" without a specific sector:** Generate the broad all-sector rotation overview. Focus on the ranking table, money flows across all sectors, and the top 2-3 rotation trades.
- **If economic data is mixed:** Acknowledge the uncertainty. When cycle signals are conflicting, note that transition periods are the hardest to read and recommend reduced position sizes.
- **If a sector is dominated by 1-2 mega-caps (e.g., Technology):** Call this out explicitly. Analyze both the equal-weight and cap-weight versions of the sector. A sector can look strong while most stocks in it are weak if the mega-caps are carrying it.

**DISCLAIMER: This is for educational and research purposes only. Not financial advice. Always do your own due diligence.**
