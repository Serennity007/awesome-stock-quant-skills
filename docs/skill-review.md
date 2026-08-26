# 收录技能实测对比表（skill-review）

**[中文](skill-review.md) | [English](skill-review.en.md) | [日本語](skill-review.ja.md)**

检查日期：2026-08-26。检查方式：本机（Windows + Python 3.11）结构化检查 + 能装的依赖真装、能跑的真跑。需要付费 API key、券商终端（QMT/IBKR）等外部环境的，如实标注「需外部环境，未实测」，不编造测试结果。

## 检查表

| 技能 | 标准 SKILL.md | 脚本/依赖 | 需要的 API key | 本次实测 | 一句话简评 |
|---|---|---|---|---|---|
| simonlin1212__a-stock-data | ✅（1 个） | Python 脚本 + baostock/akshare/requests | 无（baostock/akshare 免费） | ❌ 未实测 | A股数据全栈型，结构规范，双数据源互为兜底。 |
| wbh604__UZI-Skill | ✅（4 个技能目录） | run.py 一键入口，依赖 akshare/yfinance/baostock/ddgs/playwright 等 | 无硬性要求（Web 搜索维度用 ddgs） | ⚠️ 部分实测：依赖装齐、`run.py 600519.SH` 成功启动并通过网络自检、进入数据采集（21/22 维缓存有效），但全流程在本机代理环境下 15 分钟超时未完成 | 功能最全面的 A 股深度分析 skill，工程化程度高，但依赖重、全流程耗时长。 |
| BitSoulTech__BitSoulStockSkill | ✅（位于 bitsoulstockskill/ 子目录） | Python 选股/因子/回测脚本 | 无（公开数据源） | ❌ 未实测 | 选股+因子+回测一体，核心目录已收录，assets 未含。 |
| fadewalk__serenity-stock-choke | ✅ | scripts/a_stock_query.py | 需 OpenAI 兼容 key | ❌ 需付费 key，未实测 | "卡脖子"主题选股，思路有特色，但依赖 LLM key。 |
| shouldnotappearcalm__a-share-skill | ✅（5 个子技能） | Python 脚本 + akshare/baostock | 无 | ❌ 未实测 | 数据/分析/模拟交易分目录清晰，覆盖链路完整。 |
| StanleyChanH__Tushare-Finance-Skill | ✅ | Python + tushare | 需 Tushare Pro token（积分制） | ❌ 需付费 token，未实测 | Tushare 接口封装+接口文档齐全，token 是硬门槛。 |
| Geralt-L__Stock-Analysis-3D | ✅ | references/stock_data_fetcher.py，多数据源（akshare/yfinance/efinance/tushare） | 无硬性要求（tushare 维度可选） | ❌ 未实测 | 三维评分框架思路清晰，数据源冗余设计合理。 |
| atorber__qmt-trading-skill | ✅（22 个子技能） | Python + xtquant | 需券商 QMT 终端 | ❌ 需外部环境（QMT），未实测 | 21+ 个 QMT 实盘/数据桥接技能，接实盘者首选，但必须本地装 QMT。 |
| staruhub__a-share-analyst | ✅（位于 Geek-skills 子目录） | 提示词为主，附 references/scripts | 无 | ❌ 未实测 | 分析师角色型提示词技能，轻量易上手。 |
| tradermonty__claude-trading-skills | ✅（72 个 SKILL.md） | 大量 Python 脚本（yfinance/requests），多数带 tests | 无硬性要求（美股免费数据） | ❌ 未实测 | 美股/CANSLIM/事件驱动覆盖面最大，且自带测试，工程规范好。 |
| agiprolabs__claude-trading-skills | ✅（67 个 SKILL.md） | Python 脚本 | 部分需 Birdeye/Helius 等链上 API key | ❌ 需付费 key（部分技能），未实测 | 偏加密/Solana 生态，数量多但主题与 A 股差异大。 |
| zubair-trabzada__ai-trading-claude | ✅（15 个） | 纯提示词（无 Python 脚本）+ 5 个 agents | 无 | ➖ 无需实测（无脚本可跑），已检查结构 | 提示词型交易技能集，结构规范，零依赖。 |
| yennanliu__InvestSkill | ✅（27 个） | 提示词为主（DCF/财报/竞品等） | 部分需 OpenAI/Anthropic key | ❌ 需付费 key，未实测 | 美股基本面分析技能集，主题划分细。 |
| tellmefrankie__ai-investment-skills | ✅（5 个） | 提示词 + 部分脚本 | 需 OpenAI/Anthropic key | ❌ 需付费 key，未实测 | 期权流/新闻情绪/价格提醒等实用小技能。 |
| cruisekkk__trading-ledger | ✅ | 纯提示词/日志模板（demo 为 Remotion 前端，非运行依赖） | 无 | ➖ 无需实测（无可执行脚本），已检查结构 | 交易日志记录技能，简单实用，零依赖。 |
| AlexLiu0130__ibkr-options-assistant | ✅ | Python + ib_insync（requirements.txt 齐全） | 需 IBKR TWS/Gateway | ❌ 需外部环境（IBKR），未实测 | 期权持仓/集中度/成本分析脚本完整，接 IBKR 者可用。 |

## 汇总

- **本次实测跑通**：仅本仓库原创的 `buffett-value-investing` 与 `technical-pattern-recognition`（见各自 docs/demo）。
- **部分实测**：`wbh604__UZI-Skill`（入口可启动、数据采集部分完成，全流程超时）。
- **零依赖可直接用**（提示词型，已做结构检查）：`zubair-trabzada__ai-trading-claude`、`cruisekkk__trading-ledger`。
- **需付费 key 或外部环境，未实测**：Tushare token（StanleyChanH）、OpenAI/Anthropic key（fadewalk、tellmefrankie、yennanliu 部分）、QMT（atorber）、IBKR（AlexLiu0130）、链上 API key（agiprolabs 部分）。
- **其余**：结构检查通过（SKILL.md 规范、依赖明确），本次未逐一运行。

> 说明：「未实测」不代表技能有质量问题，仅表示本次在本机环境下未完成端到端运行；欢迎原作者或使用者补充实测结果（提 PR 更新本表）。
