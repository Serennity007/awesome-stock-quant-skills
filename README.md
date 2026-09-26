# awesome-stock-quant-skills

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

![GitHub stars](https://img.shields.io/github/stars/Serennity007/awesome-stock-quant-skills?style=flat-square) ![License](https://img.shields.io/github/license/Serennity007/awesome-stock-quant-skills?style=flat-square) ![收录技能](https://img.shields.io/badge/收录技能-16-blue?style=flat-square) ![原创技能](https://img.shields.io/badge/原创技能-21-green?style=flat-square) ![语言](https://img.shields.io/badge/语言-中文%20%7C%20EN%20%7C%20JA-orange?style=flat-square)

炒股 / 量化交易 / 选股 AI Skill 合集：收录国内外 GitHub 上的股票分析、量化交易、选股策略 Agent Skills（Claude Code / Agent Skills 格式），附索引与合规转载。

- **合规原则**：`skills/` 目录仅收录 License 为 MIT / Apache-2.0 / BSD / CC0 的项目，并保留原 LICENSE 文件与 SOURCE.md 来源说明；无 License、GPL、AGPL、NOASSERTION 的项目一律只进索引、不复制文件。
- 收录日期：2026-08-25。

## 免责声明

本仓库内容仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。所有技能版权归原作者及原仓库所有，如有侵权请联系删除。

## 使用说明

将 `skills/` 下需要的技能目录复制到你的技能目录即可使用：

```bash
# Claude Code
cp -r skills/<作者>__<技能名> ~/.claude/skills/

# 或通用 agents skills 目录
cp -r skills/<作者>__<技能名> ~/.agents/skills/
```

多技能合集（如 `agiprolabs__claude-trading-skills/skills/...`）请将其内部的具体技能子目录复制到技能目录下。每个收录目录中的 `SOURCE.md` 记录了原始仓库 URL、作者与 License。

## 已收录技能

| 目录 | 简介 | 来源 | License |
|---|---|---|---|
| [simonlin1212__a-stock-data](skills/simonlin1212__a-stock-data) | A股全栈数据 SKILL | [simonlin1212/a-stock-data](https://github.com/simonlin1212/a-stock-data) | Apache-2.0 |
| [wbh604__UZI-Skill](skills/wbh604__UZI-Skill) | 游资UZI炒股 Skill（深度分析/龙虎榜/陷阱识别等） | [wbh604/UZI-Skill](https://github.com/wbh604/UZI-Skill) | MIT |
| [BitSoulTech__BitSoulStockSkill](skills/BitSoulTech__BitSoulStockSkill) | A股选股+因子+回测（核心目录，assets 未收录） | [BitSoulTech/BitSoulStockSkill](https://github.com/BitSoulTech/BitSoulStockSkill) | Apache-2.0 |
| [fadewalk__serenity-stock-choke](skills/fadewalk__serenity-stock-choke) | A股"卡脖子"选股 | [fadewalk/serenity-stock-choke](https://github.com/fadewalk/serenity-stock-choke) | MIT |
| [shouldnotappearcalm__a-share-skill](skills/shouldnotappearcalm__a-share-skill) | A股分析+选股+模拟交易（多个技能子目录） | [shouldnotappearcalm/a-share-skill](https://github.com/shouldnotappearcalm/a-share-skill) | MIT |
| [StanleyChanH__Tushare-Finance-Skill](skills/StanleyChanH__Tushare-Finance-Skill) | Tushare 数据技能包 | [StanleyChanH/Tushare-Finance-Skill-for-Claude-Code](https://github.com/StanleyChanH/Tushare-Finance-Skill-for-Claude-Code) | MIT |
| [Geralt-L__Stock-Analysis-3D](skills/Geralt-L__Stock-Analysis-3D) | 3D 评分股票分析 | [Geralt-L/Stock-Analysis-3D](https://github.com/Geralt-L/Stock-Analysis-3D) | MIT |
| [atorber__qmt-trading-skill](skills/atorber__qmt-trading-skill) | QMT 交易 21 个 skills | [atorber/qmt-trading-skill](https://github.com/atorber/qmt-trading-skill) | MIT |
| [staruhub__a-share-analyst](skills/staruhub__a-share-analyst) | A股分析师技能（取自 ClaudeSkills） | [staruhub/ClaudeSkills](https://github.com/staruhub/ClaudeSkills) | MIT |
| [tradermonty__claude-trading-skills](skills/tradermonty__claude-trading-skills) | 美股分析 / CANSLIM 选股等 | [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) | MIT |
| [agiprolabs__claude-trading-skills](skills/agiprolabs__claude-trading-skills) | 67 个交易 skills（含加密/期权/风控） | [agiprolabs/claude-trading-skills](https://github.com/agiprolabs/claude-trading-skills) | MIT |
| [zubair-trabzada__ai-trading-claude](skills/zubair-trabzada__ai-trading-claude) | 16 个 trade-* skills + 5 agents | [zubair-trabzada/ai-trading-claude](https://github.com/zubair-trabzada/ai-trading-claude) | MIT |
| [yennanliu__InvestSkill](skills/yennanliu__InvestSkill) | 美股分析 + stock-screener 等 | [yennanliu/InvestSkill](https://github.com/yennanliu/InvestSkill) | MIT |
| [tellmefrankie__ai-investment-skills](skills/tellmefrankie__ai-investment-skills) | 期权流/新闻情绪/价格提醒等 5 个投资 skills | [tellmefrankie/ai-investment-skills](https://github.com/tellmefrankie/ai-investment-skills) | MIT |
| [cruisekkk__trading-ledger](skills/cruisekkk__trading-ledger) | 交易日志 skill | [cruisekkk/trading-ledger](https://github.com/cruisekkk/trading-ledger) | MIT |
| [AlexLiu0130__ibkr-options-assistant](skills/AlexLiu0130__ibkr-options-assistant) | IBKR 期权助手 | [AlexLiu0130/ibkr-options-assistant](https://github.com/AlexLiu0130/ibkr-options-assistant) | MIT |

## 原创技能

本仓库作者（Serennity007）原创的技能，放在 `my-skills/` 目录，与 `skills/` 收录区区分：

### 投资大师方法论系列

| 目录 | 简介 | License |
|---|---|---|
| [buffett-value-investing](my-skills/buffett-value-investing) | A股巴菲特式价值投资分析：护城河评估、连续5年ROE/毛利率/负债率/经营现金流筛选、安全边际估值（基于 akshare，含筛股与单股分析脚本） | MIT |
| [munger-quality-investing](my-skills/munger-quality-investing) | A股芒格优质企业投资法：连续5年ROIC/ROE、低负债、高稳定毛利率、盈利质量、少股本稀释五维质量打分 | MIT |
| [lynch-garp-investing](my-skills/lynch-garp-investing) | A股彼得·林奇GARP十倍股筛选器：PEG、连续盈利增长、低负债率、林奇六分类标签 | MIT |
| [graham-defensive-investing](my-skills/graham-defensive-investing) | A股格雷厄姆防御型投资七准则筛股器：规模、流动比率、连续盈利、连续分红、盈利增长、低PE/PB量化筛选 | MIT |
| [dalio-all-weather](my-skills/dalio-all-weather) | A股达利欧全天候/债务周期参考配置：用宽基指数、国债ETF、黄金ETF与商品指数计算相关性、波动率与风险平价权重，并回测年化/最大回撤/夏普 | MIT |
| [howard-marks-cycle](my-skills/howard-marks-cycle) | A股霍华德·马克斯周期温度计：沪深300/中证全指估值分位、股债收益差、成交热度、两融趋势，合成0-100周期位置评分并输出行动框架 | MIT |
| [soros-reflexivity](my-skills/soros-reflexivity) | A股索罗斯反身性/宏观投机扫描器：在价格动量与基本面的裂缝中标记正反馈/负反馈阶段与潜在拐点 | MIT |
| [druckenmiller-macro-flex](my-skills/druckenmiller-macro-flex) | 德鲁肯米勒式宏观灵活仪表盘：用akshare跟踪美元/人民币汇率、中美10Y国债收益率、黄金、原油、铜、A股指数及个股的近N日趋势与动量，输出多空倾向快照 | MIT |
| [livermore-trend-trading](my-skills/livermore-trend-trading) | A股杰西·利弗莫尔趋势投机：识别N日新高关键点突破、放量确认、缩量回踩二次入场与单日反转/放量滞涨危险信号，输出信号表与金字塔仓位试探框架 | MIT |
| [simons-factor-quant](my-skills/simons-factor-quant) | A股西蒙斯式多因子打分器：动量/反转/波动率/量能/均线偏离五维合成综合因子分并输出排名 | MIT |
| [klarman-margin-safety](my-skills/klarman-margin-safety) | A股卡拉曼安全边际深度价值筛选：PB/PE历史分位、市值/净现金比、52周高点回撤四把尺子，剔除ST与亏损股 | MIT |
| [templeton-global-contrarian](my-skills/templeton-global-contrarian) | A股邓普顿极度悲观逆向扫描器：52周位置、PE/PB自身历史低分位、缩量企稳、盈利为正，输出逆向买入观察清单 | MIT |

### 国内投资大佬系列

| 目录 | 简介 | License |
|---|---|---|
| [duan-yongping-business-first](my-skills/duan-yongping-business-first) | A股段永平"商业模式第一"六维打分：毛利率稳定性、连续ROE、经营现金流/净利润、低负债、盈利稳定、行业内龙头排名，"敢为天下后"筛选好生意 | MIT |
| [zhang-lei-longterm](my-skills/zhang-lei-longterm) | A股张磊高瓴长期结构性价值投资：连续双增、长期投入（研发/资本开支）、行业空间、ROE趋势四维成长质量雷达，"时间的朋友"筛选器 | MIT |
| [qiu-guolu-simple-rules](my-skills/qiu-guolu-simple-rules) | A股邱国鹭"投资中最简单的事"三好打分器：好行业（数月亮不数星星）、好公司（龙头+高ROE）、好价格（PE/PB历史分位） | MIT |
| [feng-liu-weak-side](my-skills/feng-liu-weak-side) | A股冯柳弱者体系逆向扫描：52周回撤、PE/PB三年历史分位、基本面未崩（盈利为正+营收未失速）、低关注度，输出赔率/概率逆向观察清单 | MIT |
| [lin-yuan-monopoly-consumer](my-skills/lin-yuan-monopoly-consumer) | A股林园垄断+成瘾性消费投资法：嘴巴相关刚需龙头、毛利率≥50%、ROE≥15%、高分红、申万消费/医药行业过滤多维打分 | MIT |

### 热点题材系列

| 目录 | 简介 | License |
|---|---|---|
| [hot-theme-scanner](my-skills/hot-theme-scanner) | A股热点题材扫描器：基于akshare概念板块与资金流向接口，识别近N日最热题材、列出领涨股并输出结构化热度表 | MIT |
| [us-hot-stocks-tracker](my-skills/us-hot-stocks-tracker) | 美股热门AI股追踪器：内置AI算力/存储/AI应用/robotaxi主题清单，输出现价、涨跌幅、20/60日动量、52周高低位距离、成交量异动快照表 | MIT |
| [concept-stock-mapper](my-skills/concept-stock-mapper) | A股题材关键词→概念股映射器：用akshare概念板块接口模糊匹配板块，取成分股并按涨幅/换手/主力资金排序，支持多关键词题材强度对比 | MIT |

### 原有

| 目录 | 简介 | License |
|---|---|---|
| [technical-pattern-recognition](my-skills/technical-pattern-recognition) | A股技术形态识别：均线多头/空头排列、MACD 金叉死叉、放量突破 N 日新高、缩量回踩均线，输出信号表（基于 akshare 新浪日线） | MIT |

## 演示 / Demo

原创技能均为真实可运行代码，附实跑输出（2026-08-26 实测，akshare 1.18.94，数据为当日真实行情与财务数据）：

- **巴菲特筛股实测**：`screen.py --codes 600519,000858,600036` → 贵州茅台 100 分（5 年 ROE 27.7%–37.0%、毛利率 91.7%、PE/PB 分位 0.07/0.03）、五粮液 94 分、招商银行 47 分（金融业高杠杆被正确扣分）。完整输出：[my-skills/buffett-value-investing/docs/demo.md](my-skills/buffett-value-investing/docs/demo.md)
- **单股分析实测**：`analyze.py 600519` → 护城河清单 + 5 年财务趋势 + 估值区间（保守估值 1547.89 元 / 安全边际参考价 1083.52 元）。
- **技术形态识别实测**：`patterns.py` 6 只实测 → 601318/000001 命中 `MACD_GOLDEN`，其余 `NO_SIGNAL`。完整输出：[my-skills/technical-pattern-recognition/docs/demo.md](my-skills/technical-pattern-recognition/docs/demo.md)
- **每日自动报告**：GitHub Action 每天 UTC 01:00 对 20 只 A 股代表股自动运行巴菲特筛股，结果提交到 [`reports/`](reports/)（最新报告：[reports/latest.md](reports/latest.md)）。
- **段永平全池实测**（2026-09-26）：`screen.py --pool hs300`（300 只）→ 山西汾酒 86 分、迈瑞医疗 83 分、贵州茅台 82 分、五粮液 81 分、中国海油 81 分居前——高毛利现金牛行业整体领先。
- **收录技能实测对比**：16 个收录技能的结构化检查表（SKILL.md 规范性、依赖、API key、是否实测跑通）见 [docs/skill-review.md](docs/skill-review.md)。

## 索引目录

以下项目仅提供链接索引，未转载文件（License 不允许转载、体量过大或为完整应用/框架）。Stars 数据为 2026-08-25 查询。

### A. 中文 Skill / Agent 项目

| 项目 | 简介 | Stars | License | 备注 |
|---|---|---|---|---|
| [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) | LLM驱动多市场智能分析系统 | 63.8k | MIT | 完整应用，建议直接用原仓库，仅索引未转载 |
| [jwangkun/claude-for-financial-services-cn](https://github.com/jwangkun/claude-for-financial-services-cn) | 63个A股金融 Claude Skills | 720 | Apache-2.0 | 体量大，仅索引未转载 |
| [liangdabiao/Claude-Code-Stock-Deep-Research-Agent](https://github.com/liangdabiao/Claude-Code-Stock-Deep-Research-Agent) | 8阶段股票尽调+28并行研究智能体 | 367 | 无License | 仅索引，未转载 |
| [MobiusQuant/Gendangzou-skill](https://github.com/MobiusQuant/Gendangzou-skill) | 跟庄走：A股板块研究 Skill | 306 | Apache-2.0 | 仅索引未转载 |
| [lzwme/finance-quant-skills](https://github.com/lzwme/finance-quant-skills) | A股量化 Agent Skills 维护仓库 | 264 | 无License | 仅索引，未转载 |
| [joutaojian/arkvol-skill](https://github.com/joutaojian/arkvol-skill) | arkvol 数据接入 Agent | 169 | 无License | 仅索引，未转载 |
| [liusai0820/Stock-Analysis-Skill](https://github.com/liusai0820/Stock-Analysis-Skill) | 股票分析师 skill（A/港/美） | 130 | 无License | 仅索引，未转载 |
| [shouldnotappearcalm/hk-us-market-skill](https://github.com/shouldnotappearcalm/hk-us-market-skill) | 港美股量化研究+模拟交易 | 3 | 无License | 仅索引，未转载 |
| [Patrickristal/DaA-left-side-trading-rookie](https://github.com/Patrickristal/DaA-left-side-trading-rookie) | A股港股左侧交易 skill（超预测框架） | 2 | 无License | 仅索引，未转载 |
| [quantskills/skill-stock-screener](https://github.com/quantskills/skill-stock-screener) | 自然语言A股选股 | 2 | GPL-3.0 | GPL 不转载，仅索引 |
| [samyakjain0606/awesome-stock-skills](https://github.com/samyakjain0606/awesome-stock-skills) | 印度股市研究 skills | 24 | 无License | 仅索引，未转载 |
| [rigneshroot/hyperbot-ai-trading-claude-skill](https://github.com/rigneshroot/hyperbot-ai-trading-claude-skill) | 可解释交易情报框架 | 0 | NOASSERTION | 仅索引，未转载 |
| [hsliuping/TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN) | 中文多智能体LLM交易框架 | 31.4k | NOASSERTION | 仅索引，未转载 |
| [24mlight/A_Share_investment_Agent](https://github.com/24mlight/A_Share_investment_Agent) | A股投资多智能体系统 | 2.5k | NOASSERTION | 仅索引，未转载 |
| [HiThink-Tech/Financial-API](https://github.com/HiThink-Tech/Financial-API) | 同花顺官方金融数据 MCP/API | 1.8k | MIT | 仅索引未转载 |
| [wolfjkd/tradex-hub](https://github.com/wolfjkd/tradex-hub) | A股AI决策中台，129个MCP工具（通达信+akshare+同花顺） | 32 | 无License | 仅索引，未转载 |
| [guangxiangdebizi/FinanceMCP-DCTHS](https://github.com/guangxiangdebizi/FinanceMCP-DCTHS) | 东财+同花顺 MCP 数据服务 | 39 | Apache-2.0 | 仅索引未转载 |
| [zhuyifang/tonghuasun-codex](https://github.com/zhuyifang/tonghuasun-codex) | 本机同花顺接入 Codex | 27 | 无License | 仅索引，未转载 |
| [binance/binance-skills-hub](https://github.com/binance/binance-skills-hub) | 币安官方 skills 市场 | 982 | 未标注 | 仅索引，未转载 |

### B. AI Agent / LLM 交易框架

| 项目 | 简介 | Stars | License | 备注 |
|---|---|---|---|---|
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | 多智能体LLM金融交易框架 | 100k | Apache-2.0 | 框架类，仅索引 |
| [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) | AI对冲基金多agent模拟 | 63k | MIT | 框架类，仅索引 |
| [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | 金融强化学习框架 | 16.1k | MIT | 框架类，仅索引 |
| [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | LLM金融AI Agent平台 | 7.9k | Apache-2.0 | 框架类，仅索引 |

### C. 量化框架 / 回测

| 项目 | 简介 | Stars | License | 备注 |
|---|---|---|---|---|
| [vnpy/vnpy](https://github.com/vnpy/vnpy) | 国内最知名开源量化交易平台 | 44.7k | MIT | 框架类，仅索引 |
| [microsoft/qlib](https://github.com/microsoft/qlib) | 微软AI量化投研平台 | 47.9k | MIT | 框架类，仅索引 |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | 加密货币交易机器人 | 53.6k | GPL-3.0 | GPL 不转载，仅索引 |
| [mementum/backtrader](https://github.com/mementum/backtrader) | 经典回测库（已停更） | 23k | GPL-3.0 | GPL 不转载，仅索引 |
| [quantopian/zipline](https://github.com/quantopian/zipline) | 经典算法交易回测库 | 20.1k | Apache-2.0 | 仅索引 |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | 算法交易引擎 | 21.3k | Apache-2.0 | 仅索引 |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | 向量化回测 | 8.8k | Apache-2.0 + Commons Clause | 仅索引，未转载 |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | 高频做市/套利 | 19.6k | Apache-2.0 | 仅索引 |
| [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | 加密货币交易机器人 | 8.4k | MIT | 仅索引 |
| [ricequant/rqalpha](https://github.com/ricequant/rqalpha) | 米筐A股回测框架 | 6.7k | NOASSERTION | 仅索引，未转载 |
| [zvtvz/zvt](https://github.com/zvtvz/zvt) | 模块化量化框架 | 4.3k | MIT | 仅索引 |

### D. 数据接口

| 项目 | 简介 | Stars | License | 备注 |
|---|---|---|---|---|
| [akfamily/akshare](https://github.com/akfamily/akshare) | A股数据首选开源库 | 22.2k | MIT | 仅索引 |
| [waditu/tushare](https://github.com/waditu/tushare) | 老牌A股数据（免费版停更，Pro需积分） | 15.2k | BSD-3-Clause | 仅索引 |
| [Micro-sheep/efinance](https://github.com/Micro-sheep/efinance) | 东财数据快速获取 | 4k | MIT | 仅索引 |
| [shidenggui/easyquotation](https://github.com/shidenggui/easyquotation) | 新浪/腾讯实时行情 | 5.4k | MIT | 仅索引 |
| [rainx/pytdx](https://github.com/rainx/pytdx) | 通达信行情接口 | 1.6k | 无License已归档 | 仅索引，未转载 |
| [ccxt/ccxt](https://github.com/ccxt/ccxt) | 统一100+交易所API | 43.7k | MIT | 仅索引 |
| [OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB) | 开放金融数据平台 | 72.3k | AGPL-3.0 | AGPL 不转载，仅索引 |

### E. 因子 / 策略 / 指标

| 项目 | 简介 | Stars | License | 备注 |
|---|---|---|---|---|
| [mpquant/MyTT](https://github.com/mpquant/MyTT) | 通达信/同花顺指标 Python 移植 | 2.8k | 无License | 仅索引，未转载 |
| [yli188/WorldQuant_alpha101_code](https://github.com/yli188/WorldQuant_alpha101_code) | WorldQuant 101 Alpha 因子实现 | 860 | 无License | 仅索引，未转载 |

### F. 学习资源 / 索引

| 项目 | 简介 | Stars | License | 备注 |
|---|---|---|---|---|
| [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant) | 量化库精选列表 | 29.2k | 无License | 仅索引，未转载 |
| [thuquant/awesome-quant](https://github.com/thuquant/awesome-quant) | 中国Quant资源索引 | 5.6k | MIT | 仅索引 |
| [Barca0412/Introduction-to-Quantitative-Finance](https://github.com/Barca0412/Introduction-to-Quantitative-Finance) | 中文量化金融入门知识库 | 1.7k | MIT | 仅索引 |
| [VoltAgent/awesome-claude-skills](https://github.com/VoltAgent/awesome-claude-skills) | 含 Web3/Trading 分区 | — | — | 仅索引 |
| [shishirui/awesome-claude-skills-zh](https://github.com/shishirui/awesome-claude-skills-zh) | 中文 skills 索引 | 15 | CC0-1.0 | 仅索引 |
| [yzfly/awesome-skills-zh](https://github.com/yzfly/awesome-skills-zh) | 中文 skills 索引 | 29 | Apache-2.0 | 仅索引 |

## License

本合集自身的整理内容（README、索引、SOURCE.md）采用 [MIT License](LICENSE)。`skills/` 下各技能以各自原仓库 License 为准，详见各目录内的 LICENSE 与 SOURCE.md。
