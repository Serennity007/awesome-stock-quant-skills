# awesome-stock-quant-skills

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

![GitHub stars](https://img.shields.io/github/stars/Serennity007/awesome-stock-quant-skills?style=flat-square) ![License](https://img.shields.io/github/license/Serennity007/awesome-stock-quant-skills?style=flat-square) ![Collected skills](https://img.shields.io/badge/collected%20skills-16-blue?style=flat-square) ![Original skills](https://img.shields.io/badge/original%20skills-23-green?style=flat-square) ![Languages](https://img.shields.io/badge/languages-ZH%20%7C%20EN%20%7C%20JA-orange?style=flat-square)

A curated collection of stock trading / quantitative trading / stock screening AI Skills: Agent Skills (Claude Code / Agent Skills format) for stock analysis, quant trading, and screening strategies from GitHub projects in China and abroad, with an index and license-compliant reprints.

- **Compliance principle**: the `skills/` directory only includes projects licensed under MIT / Apache-2.0 / BSD / CC0, keeping the original LICENSE file and a SOURCE.md attribution note. Projects with no license, GPL, AGPL, or NOASSERTION are index-only — no files are copied.
- Collection date: 2026-08-25.

## Disclaimer

All content in this repository is for learning and research purposes only and does not constitute investment advice. Markets carry risk; invest with caution. All skills belong to their original authors and repositories; contact us for removal if needed.

## Usage

Copy the skill directory you need from `skills/` into your skills directory:

```bash
# Claude Code
cp -r skills/<author>__<skill-name> ~/.claude/skills/

# or the generic agents skills directory
cp -r skills/<author>__<skill-name> ~/.agents/skills/
```

For multi-skill collections (e.g. `agiprolabs__claude-trading-skills/skills/...`), copy the specific skill subdirectories inside them. The `SOURCE.md` in each collected directory records the original repository URL, author, and license.

## Collected Skills

| Directory | Description | Source | License |
|---|---|---|---|
| [simonlin1212__a-stock-data](skills/simonlin1212__a-stock-data) | Full-stack A-share data SKILL | [simonlin1212/a-stock-data](https://github.com/simonlin1212/a-stock-data) | Apache-2.0 |
| [wbh604__UZI-Skill](skills/wbh604__UZI-Skill) | "Hot money UZI" trading skills (deep analysis / dragon-tiger list / trap detection, etc.) | [wbh604/UZI-Skill](https://github.com/wbh604/UZI-Skill) | MIT |
| [BitSoulTech__BitSoulStockSkill](skills/BitSoulTech__BitSoulStockSkill) | A-share screening + factors + backtesting (core directory only; assets not collected) | [BitSoulTech/BitSoulStockSkill](https://github.com/BitSoulTech/BitSoulStockSkill) | Apache-2.0 |
| [fadewalk__serenity-stock-choke](skills/fadewalk__serenity-stock-choke) | A-share "chokepoint" stock screening | [fadewalk/serenity-stock-choke](https://github.com/fadewalk/serenity-stock-choke) | MIT |
| [shouldnotappearcalm__a-share-skill](skills/shouldnotappearcalm__a-share-skill) | A-share analysis + screening + paper trading (multiple skill subdirectories) | [shouldnotappearcalm/a-share-skill](https://github.com/shouldnotappearcalm/a-share-skill) | MIT |
| [StanleyChanH__Tushare-Finance-Skill](skills/StanleyChanH__Tushare-Finance-Skill) | Tushare data skill pack | [StanleyChanH/Tushare-Finance-Skill-for-Claude-Code](https://github.com/StanleyChanH/Tushare-Finance-Skill-for-Claude-Code) | MIT |
| [Geralt-L__Stock-Analysis-3D](skills/Geralt-L__Stock-Analysis-3D) | 3D-scored stock analysis | [Geralt-L/Stock-Analysis-3D](https://github.com/Geralt-L/Stock-Analysis-3D) | MIT |
| [atorber__qmt-trading-skill](skills/atorber__qmt-trading-skill) | 21 QMT trading skills | [atorber/qmt-trading-skill](https://github.com/atorber/qmt-trading-skill) | MIT |
| [staruhub__a-share-analyst](skills/staruhub__a-share-analyst) | A-share analyst skill (from ClaudeSkills) | [staruhub/ClaudeSkills](https://github.com/staruhub/ClaudeSkills) | MIT |
| [tradermonty__claude-trading-skills](skills/tradermonty__claude-trading-skills) | US stock analysis / CANSLIM screening, etc. | [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) | MIT |
| [agiprolabs__claude-trading-skills](skills/agiprolabs__claude-trading-skills) | 67 trading skills (crypto / options / risk management) | [agiprolabs/claude-trading-skills](https://github.com/agiprolabs/claude-trading-skills) | MIT |
| [zubair-trabzada__ai-trading-claude](skills/zubair-trabzada__ai-trading-claude) | 16 trade-* skills + 5 agents | [zubair-trabzada/ai-trading-claude](https://github.com/zubair-trabzada/ai-trading-claude) | MIT |
| [yennanliu__InvestSkill](skills/yennanliu__InvestSkill) | US stock analysis + stock-screener, etc. | [yennanliu/InvestSkill](https://github.com/yennanliu/InvestSkill) | MIT |
| [tellmefrankie__ai-investment-skills](skills/tellmefrankie__ai-investment-skills) | 5 investment skills: options flow / news sentiment / price alerts, etc. | [tellmefrankie/ai-investment-skills](https://github.com/tellmefrankie/ai-investment-skills) | MIT |
| [cruisekkk__trading-ledger](skills/cruisekkk__trading-ledger) | Trading journal skill | [cruisekkk/trading-ledger](https://github.com/cruisekkk/trading-ledger) | MIT |
| [AlexLiu0130__ibkr-options-assistant](skills/AlexLiu0130__ibkr-options-assistant) | IBKR options assistant | [AlexLiu0130/ibkr-options-assistant](https://github.com/AlexLiu0130/ibkr-options-assistant) | MIT |

## Original Skills

Skills originally created by this repository's author (Serennity007), placed under `my-skills/` to distinguish them from the collected `skills/`:

### Investment Master Methodology Series

| Directory | Description | License |
|---|---|---|
| [buffett-value-investing](my-skills/buffett-value-investing) | A-share Buffett-style value investing analysis: moat assessment, 5-year ROE / gross margin / debt ratio / operating cash flow screening, margin-of-safety valuation (based on akshare, with screening and single-stock analysis scripts) | MIT |
| [munger-quality-investing](my-skills/munger-quality-investing) | A-share Munger-style quality investing: 5-dimensional quality scoring on 5-year ROIC/ROE, low debt, high & stable gross margin, earnings quality, and low share dilution | MIT |
| [lynch-garp-investing](my-skills/lynch-garp-investing) | A-share Peter Lynch GARP/ten-bagger screener: PEG, continuous profit growth, low debt, six Lynch category labels | MIT |
| [graham-defensive-investing](my-skills/graham-defensive-investing) | A-share Graham defensive investing screener: size, current ratio, earnings stability, dividend record, earnings growth, low PE/PB quantitative filter | MIT |
| [dalio-all-weather](my-skills/dalio-all-weather) | A-share Ray Dalio all-weather / debt-cycle reference allocator: computes correlations, volatilities, risk-parity-style weights across stocks/bonds/gold/commodities, and backtests CAGR/max-drawdown/Sharpe | MIT |
| [howard-marks-cycle](my-skills/howard-marks-cycle) | A-share Howard Marks cycle gauge: CSI 300 / CSI All Share valuation percentiles, equity-bond spread, turnover heat, margin balance trend, synthesizes a 0-100 cycle-position score with action framework | MIT |
| [soros-reflexivity](my-skills/soros-reflexivity) | A-share Soros reflexivity / macro speculation scanner: labels positive/negative feedback stages and potential inflection points from the gap between price momentum and fundamentals | MIT |
| [druckenmiller-macro-flex](my-skills/druckenmiller-macro-flex) | Druckenmiller-style macro-flex dashboard: tracks USD/CNY, China/US 10Y yields, gold, crude oil, copper, A-share indices and individual stocks' N-day trend/momentum, outputs a long/short bias snapshot | MIT |
| [livermore-trend-trading](my-skills/livermore-trend-trading) | A-share Jesse Livermore trend speculation: identifies N-day new-high pivotal-point breakout, volume confirmation, low-volume pullback secondary entry, and one-day reversal/volume-stagnation danger signals, outputs a signal table and pyramid position-probe framework | MIT |
| [simons-factor-quant](my-skills/simons-factor-quant) | A-share Simons-style multi-factor scorer: momentum/reversal/volatility/volume/MA-deviation combined into a composite factor score | MIT |
| [klarman-margin-safety](my-skills/klarman-margin-safety) | A-share Klarman margin-of-safety deep-value screener: PB/PE historical percentiles, market-cap-to-net-cash, 52-week-high drawdown, excluding ST/loss-making stocks | MIT |
| [templeton-global-contrarian](my-skills/templeton-global-contrarian) | A-share Templeton max-pessimism contrarian scanner: 52-week position, PE/PB self-history low percentiles, volume-dry-up stabilization, positive earnings | MIT |
| [fisher-growth-15](my-skills/fisher-growth-15) | A-share Philip Fisher growth-stock scoring: revenue-CAGR runway, R&D intensity, margin trend, sustained ROE, cash quality, financial conservatism — a shortlist for scuttlebutt research | MIT |
| [neff-low-pe-total-return](my-skills/neff-low-pe-total-return) | A-share John Neff low-P/E investing: P/E discount vs all-market median, total-return ratio ≥2 golden standard, span-annualized dividend yield, fundamental floors | MIT |

### Chinese Investment Masters Series

| Directory | Description | License |
|---|---|---|
| [duan-yongping-business-first](my-skills/duan-yongping-business-first) | A-share Duan Yongping "business model first" 6-dimension scoring: gross-margin stability, sustained ROE, OCF/net profit, low leverage, earnings stability, in-industry leadership ("dare to be the follower") | MIT |
| [zhang-lei-longterm](my-skills/zhang-lei-longterm) | A-share Zhang Lei Hillhouse long-term structural value investing: 4-dimensional growth-quality radar on sustained double growth, R&D/capex investment, industry headroom, and rising ROE | MIT |
| [qiu-guolu-simple-rules](my-skills/qiu-guolu-simple-rules) | A-share Qiu Guolu "the simplest thing in investing" triple-good scorer: good industry (count moons, not stars), good company (leader + high ROE), good price (PE/PB historical percentiles) | MIT |
| [feng-liu-weak-side](my-skills/feng-liu-weak-side) | A-share Feng Liu weak-side contrarian scanner: 52-week drawdown, PE/PB 3-year percentiles, intact fundamentals (positive earnings, no revenue collapse), low attention — odds/probability watchlist | MIT |
| [lin-yuan-monopoly-consumer](my-skills/lin-yuan-monopoly-consumer) | A-share Lin Yuan monopoly + addictive consumer investing: mouth-related necessity leaders, gross margin ≥50%, ROE ≥15%, high dividend, SW consumer/pharma industry filter scoring | MIT |

### Hot Theme Series

| Directory | Description | License |
|---|---|---|
| [hot-theme-scanner](my-skills/hot-theme-scanner) | A-share hot theme scanner: identifies the hottest themes over N days, lists leading stocks, and outputs a structured heat table based on akshare concept-board and capital-flow APIs | MIT |
| [us-hot-stocks-tracker](my-skills/us-hot-stocks-tracker) | US hot AI stocks tracker: built-in AI compute/storage/AI application/robotaxi watchlist, outputs current price, change%, 20/60-day momentum, 52-week high/low distance, volume anomaly snapshot | MIT |
| [concept-stock-mapper](my-skills/concept-stock-mapper) | A-share theme keyword → concept stock mapper: fuzzy-match concept boards via akshare, extract constituents and sort by gain/turnover/main-force capital, supports multi-keyword theme strength comparison | MIT |

### Original

| Directory | Description | License |
|---|---|---|
| [technical-pattern-recognition](my-skills/technical-pattern-recognition) | A-share technical pattern recognition: MA bullish/bearish alignment, MACD golden/death cross, volume-breakout to N-day high, low-volume pullback to MA, outputting a signal table (based on akshare Sina daily bars) | MIT |

## Demo

All original skills are runnable code with real captured outputs (tested 2026-08-26, akshare 1.18.94, genuine market and financial data of that day):

- **Buffett screen run**: `screen.py --codes 600519,000858,600036` → Kweichow Moutai 100 (5-year ROE 27.7%–37.0%, gross margin 91.7%, PE/PB percentile 0.07/0.03), Wuliangye 94, China Merchants Bank 47 (financial-sector leverage correctly penalized). Full output: [my-skills/buffett-value-investing/docs/demo.en.md](my-skills/buffett-value-investing/docs/demo.en.md)
- **Single-stock analysis run**: `analyze.py 600519` → moat checklist + 5-year financial trend + valuation range (conservative value 1547.89 CNY / margin-of-safety reference 1083.52 CNY).
- **Pattern recognition run**: `patterns.py` on 6 stocks → `MACD_GOLDEN` for 601318/000001, `NO_SIGNAL` for the rest. Full output: [my-skills/technical-pattern-recognition/docs/demo.en.md](my-skills/technical-pattern-recognition/docs/demo.en.md)
- **Daily automated report**: a GitHub Action runs the Buffett screen on 20 representative A-shares every day at 01:00 UTC and commits the results to [`reports/`](reports/) (latest: [reports/latest.md](reports/latest.md)).
- **Duan Yongping full-pool run** (2026-09-26): `screen.py --pool hs300` (300 stocks) → Shanxi Fenjiu 86, Mindray 83, Kweichow Moutai 82, Wuliangye 81, CNOOC 81 — high-margin cash-cow industries lead overall.
- **Fisher / Neff sample runs** (2026-09-26): Fisher framework — Mindray 78, Hikvision 76 (R&D-heavy growth stocks lead), Moutai penalized for low R&D; Neff framework — China Merchants Bank 88 (P/E only 0.18× the market median, yield 6.34%, total-return ratio 2.33 clears the golden line).
- **Collected-skills review**: a structured checklist of the 16 collected skills (SKILL.md compliance, dependencies, API keys, whether actually tested) is in [docs/skill-review.en.md](docs/skill-review.en.md).

## Index

The following projects are index-only (license does not permit reprinting, too large, or a full application/framework). Stars were queried on 2026-08-25.

### A. Chinese Skill / Agent Projects

| Project | Description | Stars | License | Note |
|---|---|---|---|---|
| [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) | LLM-driven multi-market intelligent analysis system | 63.8k | MIT | Full application; use the original repo. Index only, not reprinted |
| [jwangkun/claude-for-financial-services-cn](https://github.com/jwangkun/claude-for-financial-services-cn) | 63 A-share finance Claude Skills | 720 | Apache-2.0 | Too large; index only, not reprinted |
| [liangdabiao/Claude-Code-Stock-Deep-Research-Agent](https://github.com/liangdabiao/Claude-Code-Stock-Deep-Research-Agent) | 8-stage stock due diligence + 28 parallel research agents | 367 | No license | Index only, not reprinted |
| [MobiusQuant/Gendangzou-skill](https://github.com/MobiusQuant/Gendangzou-skill) | "Follow the banker": A-share sector research skill | 306 | Apache-2.0 | Index only, not reprinted |
| [lzwme/finance-quant-skills](https://github.com/lzwme/finance-quant-skills) | A-share quant Agent Skills maintenance repo | 264 | No license | Index only, not reprinted |
| [joutaojian/arkvol-skill](https://github.com/joutaojian/arkvol-skill) | arkvol data integration agent | 169 | No license | Index only, not reprinted |
| [liusai0820/Stock-Analysis-Skill](https://github.com/liusai0820/Stock-Analysis-Skill) | Stock analyst skill (A/HK/US) | 130 | No license | Index only, not reprinted |
| [shouldnotappearcalm/hk-us-market-skill](https://github.com/shouldnotappearcalm/hk-us-market-skill) | HK/US quant research + paper trading | 3 | No license | Index only, not reprinted |
| [Patrickristal/DaA-left-side-trading-rookie](https://github.com/Patrickristal/DaA-left-side-trading-rookie) | A/HK left-side trading skill (superforecasting framework) | 2 | No license | Index only, not reprinted |
| [quantskills/skill-stock-screener](https://github.com/quantskills/skill-stock-screener) | Natural-language A-share screening | 2 | GPL-3.0 | GPL not reprinted; index only |
| [samyakjain0606/awesome-stock-skills](https://github.com/samyakjain0606/awesome-stock-skills) | Indian stock market research skills | 24 | No license | Index only, not reprinted |
| [rigneshroot/hyperbot-ai-trading-claude-skill](https://github.com/rigneshroot/hyperbot-ai-trading-claude-skill) | Explainable trading intelligence framework | 0 | NOASSERTION | Index only, not reprinted |
| [hsliuping/TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN) | Chinese multi-agent LLM trading framework | 31.4k | NOASSERTION | Index only, not reprinted |
| [24mlight/A_Share_investment_Agent](https://github.com/24mlight/A_Share_investment_Agent) | A-share investment multi-agent system | 2.5k | NOASSERTION | Index only, not reprinted |
| [HiThink-Tech/Financial-API](https://github.com/HiThink-Tech/Financial-API) | Official THS financial data MCP/API | 1.8k | MIT | Index only, not reprinted |
| [wolfjkd/tradex-hub](https://github.com/wolfjkd/tradex-hub) | A-share AI decision hub, 129 MCP tools (TDX + akshare + THS) | 32 | No license | Index only, not reprinted |
| [guangxiangdebizi/FinanceMCP-DCTHS](https://github.com/guangxiangdebizi/FinanceMCP-DCTHS) | EastMoney + THS MCP data service | 39 | Apache-2.0 | Index only, not reprinted |
| [zhuyifang/tonghuasun-codex](https://github.com/zhuyifang/tonghuasun-codex) | Local THS integration for Codex | 27 | No license | Index only, not reprinted |
| [binance/binance-skills-hub](https://github.com/binance/binance-skills-hub) | Binance official skills hub | 982 | Unspecified | Index only, not reprinted |

### B. AI Agent / LLM Trading Frameworks

| Project | Description | Stars | License | Note |
|---|---|---|---|---|
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | Multi-agent LLM financial trading framework | 100k | Apache-2.0 | Framework; index only |
| [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) | AI hedge fund multi-agent simulation | 63k | MIT | Framework; index only |
| [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | Financial reinforcement learning framework | 16.1k | MIT | Framework; index only |
| [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | LLM financial AI agent platform | 7.9k | Apache-2.0 | Framework; index only |

### C. Quant Frameworks / Backtesting

| Project | Description | Stars | License | Note |
|---|---|---|---|---|
| [vnpy/vnpy](https://github.com/vnpy/vnpy) | Best-known open-source quant trading platform in China | 44.7k | MIT | Framework; index only |
| [microsoft/qlib](https://github.com/microsoft/qlib) | Microsoft AI quant research platform | 47.9k | MIT | Framework; index only |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | Crypto trading bot | 53.6k | GPL-3.0 | GPL not reprinted; index only |
| [mementum/backtrader](https://github.com/mementum/backtrader) | Classic backtesting library (discontinued) | 23k | GPL-3.0 | GPL not reprinted; index only |
| [quantopian/zipline](https://github.com/quantopian/zipline) | Classic algorithmic trading backtester | 20.1k | Apache-2.0 | Index only |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | Algorithmic trading engine | 21.3k | Apache-2.0 | Index only |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | Vectorized backtesting | 8.8k | Apache-2.0 + Commons Clause | Index only, not reprinted |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | HFT market making / arbitrage | 19.6k | Apache-2.0 | Index only |
| [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | Crypto trading bot | 8.4k | MIT | Index only |
| [ricequant/rqalpha](https://github.com/ricequant/rqalpha) | Ricequant A-share backtesting framework | 6.7k | NOASSERTION | Index only, not reprinted |
| [zvtvz/zvt](https://github.com/zvtvz/zvt) | Modular quant framework | 4.3k | MIT | Index only |

### D. Data APIs

| Project | Description | Stars | License | Note |
|---|---|---|---|---|
| [akfamily/akshare](https://github.com/akfamily/akshare) | Go-to open-source A-share data library | 22.2k | MIT | Index only |
| [waditu/tushare](https://github.com/waditu/tushare) | Veteran A-share data (free tier discontinued; Pro requires points) | 15.2k | BSD-3-Clause | Index only |
| [Micro-sheep/efinance](https://github.com/Micro-sheep/efinance) | Fast EastMoney data access | 4k | MIT | Index only |
| [shidenggui/easyquotation](https://github.com/shidenggui/easyquotation) | Sina/Tencent real-time quotes | 5.4k | MIT | Index only |
| [rainx/pytdx](https://github.com/rainx/pytdx) | TDX quotes API | 1.6k | No license, archived | Index only, not reprinted |
| [ccxt/ccxt](https://github.com/ccxt/ccxt) | Unified API for 100+ exchanges | 43.7k | MIT | Index only |
| [OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB) | Open financial data platform | 72.3k | AGPL-3.0 | AGPL not reprinted; index only |

### E. Factors / Strategies / Indicators

| Project | Description | Stars | License | Note |
|---|---|---|---|---|
| [mpquant/MyTT](https://github.com/mpquant/MyTT) | Python port of TDX/THS indicators | 2.8k | No license | Index only, not reprinted |
| [yli188/WorldQuant_alpha101_code](https://github.com/yli188/WorldQuant_alpha101_code) | WorldQuant 101 Alpha factor implementations | 860 | No license | Index only, not reprinted |

### F. Learning Resources / Indexes

| Project | Description | Stars | License | Note |
|---|---|---|---|---|
| [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant) | Curated quant library list | 29.2k | No license | Index only, not reprinted |
| [thuquant/awesome-quant](https://github.com/thuquant/awesome-quant) | China quant resources index | 5.6k | MIT | Index only |
| [Barca0412/Introduction-to-Quantitative-Finance](https://github.com/Barca0412/Introduction-to-Quantitative-Finance) | Chinese quant finance knowledge base | 1.7k | MIT | Index only |
| [VoltAgent/awesome-claude-skills](https://github.com/VoltAgent/awesome-claude-skills) | Includes Web3/Trading section | — | — | Index only |
| [shishirui/awesome-claude-skills-zh](https://github.com/shishirui/awesome-claude-skills-zh) | Chinese skills index | 15 | CC0-1.0 | Index only |
| [yzfly/awesome-skills-zh](https://github.com/yzfly/awesome-skills-zh) | Chinese skills index | 29 | Apache-2.0 | Index only |

## License

The curation content of this collection itself (README, indexes, SOURCE.md) is licensed under the [MIT License](LICENSE). Each skill under `skills/` is governed by its original repository's license; see the LICENSE and SOURCE.md in each directory.
