# Promotion Copy (English: Reddit r/algotrading, X)

## Reddit r/algotrading

**Title**: Awesome list of stock/quant AI agent skills — 16 open-source trading skills collected, plus 2 original ones with real demo outputs

I put together a curated collection of stock analysis / quant trading / screening "agent skills" (Claude Code / Agent Skills format):
https://github.com/Serennity007/awesome-stock-quant-skills

What's in it:

- 16 open-source trading skills collected from GitHub, license-compliant (MIT/Apache-2.0/BSD/CC0 only — each keeps its original LICENSE and a SOURCE.md attribution; GPL/no-license projects are index-only, not copied)
- A structured review of each skill: does it have a proper SKILL.md, what dependencies, which API keys are required, and whether we actually ran it this round (skills needing paid keys or external setups like QMT/IBKR are honestly marked "not tested, requires external environment")
- 2 original skills I wrote, with real (not fabricated) run outputs in the docs:
  - **buffett-value-investing**: scores A-share stocks on Buffett criteria — 5 consecutive years of ROE>15%, stable gross margin, low debt, positive operating cash flow, low historical PE/PB percentile. In the recorded demo run Kweichow Moutai scored 100/100 while China Merchants Bank scored 47 (correctly penalized for financial-sector leverage)
  - **technical-pattern-recognition**: MA alignment, MACD golden/death cross, volume breakout to N-day highs, low-volume pullbacks — outputs a signal table
- Both original skills run on free akshare data — no paid API key needed
- A GitHub Action re-runs the Buffett screen on 20 representative A-shares daily (01:00 UTC) and commits the report to `reports/`
- Docs in Chinese / English / Japanese

For learning/research only, not investment advice. Feedback and issues welcome.

## X (Twitter)

Built an awesome-list of stock/quant AI agent skills 📊
- 16 open-source trading skills collected (license-compliant, with attribution)
- 2 original skills: Buffett-style A-share screening + technical pattern recognition
- Real demo outputs, free data (akshare), no paid keys
- Daily auto-generated screening report via GitHub Actions
- EN/中文/日本語 docs
https://github.com/Serennity007/awesome-stock-quant-skills
