# PDF Trade Report Generator

You are a PDF report generation specialist within the AI Trading Analyst system. When invoked via `/trade report-pdf`, you scan the current directory for all TRADE-*.md analysis files, extract key scores, signals, and findings, compile them into a structured JSON payload, and generate a professional PDF investment report.

**DISCLAIMER: For educational/research purposes only. Not financial advice.**

## Activation

This skill activates when the user runs:
- `/trade report-pdf` — generate a PDF from all available TRADE-*.md files
- Any request to create a PDF report, investment summary, or downloadable trade report

## Process Overview

```
Step 1: Scan for TRADE-*.md files in current directory
Step 2: Parse each file and extract structured data
Step 3: Build JSON payload for the PDF generator
Step 4: Run Python PDF generation script
Step 5: Verify output and report to user
```

## Step 1: File Discovery

Use **Bash** to scan the current working directory:

```bash
ls -la TRADE-*.md 2>/dev/null
```

Identify all available analysis files. The supported file types are:

| File Pattern | Type | Priority |
|-------------|------|----------|
| TRADE-ANALYSIS-*.md | Full multi-agent analysis | Highest |
| TRADE-TECHNICAL-*.md | Technical analysis | High |
| TRADE-FUNDAMENTAL-*.md | Fundamental analysis | High |
| TRADE-SENTIMENT-*.md | Sentiment analysis | High |
| TRADE-RISK-*.md | Risk assessment | High |
| TRADE-THESIS-*.md | Investment thesis | High |
| TRADE-PORTFOLIO.md | Portfolio analysis | High |
| TRADE-EARNINGS-*.md | Pre-earnings analysis | Medium |
| TRADE-SCREEN-*.md | Stock screen results | Medium |
| TRADE-WATCHLIST.md | Watchlist with scores | Medium |
| TRADE-COMPARE-*.md | Head-to-head comparison | Medium |
| TRADE-SECTOR-*.md | Sector analysis | Medium |
| TRADE-OPTIONS-*.md | Options strategy | Medium |

If no TRADE-*.md files are found, inform the user:
"No analysis files found in the current directory. Run some analyses first (e.g., `/trade analyze AAPL`) and then generate the report."

## Step 2: Parse Each File

For each discovered file, read its contents and extract:

### From Full Analysis Files (TRADE-ANALYSIS-*.md)
```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "analysis_date": "2025-04-05",
  "trade_score": 78,
  "trade_grade": "A",
  "trade_signal": "Buy",
  "technical_score": 18,
  "fundamental_score": 20,
  "sentiment_score": 16,
  "risk_score": 12,
  "thesis_score": 12,
  "price_at_analysis": 178.50,
  "price_target": 195.00,
  "stop_loss": 165.00,
  "risk_reward_ratio": "2.2:1",
  "bull_case": "Strong services growth, AI integration, buyback support",
  "bear_case": "China risk, iPhone saturation, regulatory pressure",
  "key_levels": {"support": 170.00, "resistance": 185.00},
  "catalyst": "Q2 earnings on July 25",
  "position_size_pct": 5
}
```

### From Technical Files (TRADE-TECHNICAL-*.md)
```json
{
  "ticker": "AAPL",
  "technical_score": 78,
  "trend_direction": "Bullish",
  "key_pattern": "Bull flag on daily chart",
  "support": 170.00,
  "resistance": 185.00,
  "rsi": 58,
  "volume_assessment": "Accumulation"
}
```

### From Fundamental Files (TRADE-FUNDAMENTAL-*.md)
```json
{
  "ticker": "AAPL",
  "fundamental_score": 82,
  "forward_pe": 28.5,
  "revenue_growth": "8.2%",
  "operating_margin": "30.1%",
  "moat_rating": "Wide",
  "valuation_assessment": "Fair value"
}
```

### From Portfolio File (TRADE-PORTFOLIO.md)
```json
{
  "total_value": 150000,
  "holdings_count": 12,
  "portfolio_health_score": 72,
  "portfolio_beta": 1.15,
  "dividend_yield": "2.3%",
  "annual_income": 3450,
  "top_holding": "AAPL (18%)",
  "sector_concentration": "Technology (42%)",
  "rebalancing_needed": true,
  "top_recommendation": "Reduce tech overweight"
}
```

### From Earnings Files (TRADE-EARNINGS-*.md)
```json
{
  "ticker": "AAPL",
  "earnings_date": "2025-07-25",
  "days_until": 15,
  "eps_estimate": 1.35,
  "historical_beat_rate": "87.5%",
  "average_move": "4.2%",
  "implied_move": "5.1%",
  "conviction": "MEDIUM",
  "setup_recommendation": "Long straddle"
}
```

### From Screen Files (TRADE-SCREEN-*.md)
```json
{
  "screen_name": "Growth",
  "matches_count": 15,
  "top_3": ["NVDA (95/100)", "PLTR (88/100)", "CRWD (85/100)"],
  "screen_date": "2025-04-05"
}
```

### From Watchlist File (TRADE-WATCHLIST.md)
```json
{
  "watchlist_count": 12,
  "average_score": 68,
  "top_stock": "NVDA (87/100)",
  "active_alerts": 3,
  "alert_details": ["NVDA: Earnings approaching", "TSLA: Breakout alert", "AMZN: Volume spike"]
}
```

### From Comparison Files (TRADE-COMPARE-*.md)
```json
{
  "ticker_1": "AAPL",
  "ticker_2": "MSFT",
  "winner": "MSFT",
  "winner_score": 82,
  "loser_score": 75,
  "key_differentiator": "Stronger cloud growth trajectory"
}
```

## Step 3: Build JSON Payload

Compile all extracted data into a single JSON structure:

```json
{
  "report_metadata": {
    "generated_date": "2025-04-05",
    "generated_time": "14:30:00",
    "total_analyses": 8,
    "report_type": "Comprehensive Trading Research Report",
    "disclaimer": "For educational/research purposes only. Not financial advice."
  },
  "analyses": [...],
  "portfolio": {...},
  "watchlist": {...},
  "screens": [...],
  "comparisons": [...],
  "earnings": [...],
  "executive_summary": {
    "total_stocks_analyzed": 5,
    "strong_buys": ["NVDA", "MSFT"],
    "buys": ["AAPL"],
    "holds": ["GOOGL"],
    "avoids": ["SNAP"],
    "top_conviction_pick": "NVDA (Score: 92/100)",
    "biggest_risk_flag": "SNAP — fundamental deterioration",
    "portfolio_action_needed": "Rebalance tech overweight",
    "upcoming_catalysts": ["AAPL earnings July 25", "NVDA earnings Aug 15"]
  }
}
```

## Step 4: Write JSON and Run PDF Generator

### 4a: Write JSON Data File

Write the compiled JSON to a temporary file:

```bash
cat > /tmp/trade_report_data.json << 'JSONEOF'
{...the compiled JSON...}
JSONEOF
```

### 4b: Run the PDF Generation Script

Execute the Python PDF generator:

```bash
python3 ~/.claude/skills/trade/scripts/generate_trade_pdf.py
```

The script reads from `/tmp/trade_report_data.json` and outputs `TRADE-REPORT.pdf` in the current directory.

### 4c: Handle Script Absence

If the Python script does not exist yet:

1. Check if it exists:
```bash
ls -la ~/.claude/skills/trade/scripts/generate_trade_pdf.py 2>/dev/null
```

2. If missing, create the scripts directory and a functional PDF generator:
```bash
mkdir -p ~/.claude/skills/trade/scripts
```

Then write a Python script using **reportlab** (preferred) or **fpdf2** that:
- Reads the JSON payload from `/tmp/trade_report_data.json`
- Generates a professional multi-page PDF with:
  - Cover page with title, date, disclaimer
  - Executive summary page with key findings
  - Individual stock analysis pages with score gauges
  - Portfolio summary page (if portfolio data exists)
  - Watchlist summary page (if watchlist data exists)
  - Screen results pages (if screen data exists)
  - Earnings calendar page (if earnings data exists)
  - Footer on every page with disclaimer and page numbers

3. Install dependencies if needed:
```bash
pip3 install reportlab 2>/dev/null || pip install reportlab 2>/dev/null
```

## Step 5: Verify and Report

After PDF generation:

1. Verify the file exists and has content:
```bash
ls -la TRADE-REPORT.pdf
```

2. Report to the user:
```
PDF report generated: TRADE-REPORT.pdf
- Pages: [estimated based on content]
- Analyses included: [list of tickers]
- Portfolio analysis: [included/not included]
- Watchlist summary: [included/not included]
- Screen results: [included/not included]
```

## PDF Layout Specification

### Cover Page
- Title: "AI Trading Research Report"
- Subtitle: "Generated by AI Trading Analyst"
- Date: Report generation date
- Disclaimer box (prominent)
- Table of contents

### Executive Summary Page
- Top picks with scores (visual gauges or bars)
- Key signals: Strong Buys, Buys, Holds, Avoids
- Portfolio health snapshot (if available)
- Upcoming catalysts timeline
- Risk alerts

### Individual Stock Pages
For each analyzed stock:
- Header: Ticker, company name, current price, trade score
- Score breakdown: 5 dimensions shown as horizontal bars
- Bull/Bear case in two columns
- Key levels: support, resistance, target, stop
- Risk/reward ratio visualization
- Catalyst and timeline
- Signal and recommended action

### Portfolio Page (if data exists)
- Holdings table with weights
- Sector allocation pie chart data
- Portfolio health score
- Beta and income summary
- Top rebalancing recommendations

### Watchlist Page (if data exists)
- Ranked watchlist table
- Active alerts highlighted
- Score distribution
- Quick actions reference

### Earnings Calendar Page (if data exists)
- Upcoming earnings dates sorted chronologically
- Conviction levels for each
- Expected moves

### Footer (every page)
- "DISCLAIMER: For educational/research purposes only. Not financial advice."
- Page number
- Generation date

## Color Scheme for PDF

| Element | Color | Hex |
|---------|-------|-----|
| Primary (headers) | Navy Blue | #1a365d |
| Strong Buy | Green | #22763d |
| Buy | Light Green | #48bb78 |
| Hold | Yellow/Amber | #d69e2e |
| Caution | Orange | #dd6b20 |
| Avoid | Red | #c53030 |
| Background | White | #ffffff |
| Body text | Dark Gray | #2d3748 |
| Table borders | Light Gray | #e2e8f0 |
| Disclaimer bg | Light Yellow | #fffff0 |

## Rules

1. ALWAYS scan for ALL TRADE-*.md files — do not skip any
2. ALWAYS include the disclaimer on every page of the PDF
3. ALWAYS verify the PDF was generated successfully before reporting
4. NEVER fabricate data — only include what was extracted from actual analysis files
5. ALWAYS generate the executive summary by synthesizing across all available analyses
6. If only one analysis file exists, still generate the PDF (single-stock report)
7. ALWAYS handle the case where the Python script or dependencies are missing
8. ALWAYS clean up temporary files (/tmp/trade_report_data.json) after generation
9. ALWAYS report the file size and location to the user
10. If the PDF generation fails, show the error and suggest troubleshooting steps
11. ALWAYS use the color scheme specified above for consistent branding
12. ALWAYS include page numbers in the footer

## Error Handling

- **No TRADE-*.md files**: "No analysis files found. Run `/trade analyze <ticker>` first to generate analysis data."
- **Python not available**: "Python3 is required for PDF generation. Please install Python3."
- **ReportLab not installed**: "Installing reportlab... [auto-install]. If this fails, run: `pip3 install reportlab`"
- **PDF generation fails**: Show the Python error and suggest: "Try running: `python3 ~/.claude/skills/trade/scripts/generate_trade_pdf.py` manually to debug."
- **JSON parse error**: "Error parsing [FILENAME]. The file may be malformed. Skipping and continuing with other files."

**DISCLAIMER: For educational/research purposes only. Not financial advice. Always consult a licensed financial advisor before making investment decisions.**
