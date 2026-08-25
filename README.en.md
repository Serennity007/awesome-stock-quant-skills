# awesome-stock-quant-skills

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

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

| Directory | Description | License |
|---|---|---|
| [buffett-value-investing](my-skills/buffett-value-investing) | A-share Buffett-style value investing analysis: moat assessment, 5-year ROE / gross margin / debt ratio / free cash flow screening, margin-of-safety valuation (based on akshare, with screening and single-stock analysis scripts) | MIT |

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
