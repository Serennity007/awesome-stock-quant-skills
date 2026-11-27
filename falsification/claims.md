# 主张登记表 / Claim registry

状态定义见 [README.md](README.md)。一行一条主张；每轮最多推进一条。证据列指向 `rounds/` 里的记录或仓库文档。

| ID | 主张 | 来源 | 状态 | 测试方式 | 证据 |
|---|---|---|---|---|---|
| F-001 | 卖出深度虚值期权，因为胜率高，所以长期稳定盈利 | 常见交易经验（"高胜率卖方策略"） | **REFUTED** | 公平 Black-76 定价下，任一虚值行权价的卖出看涨期权到期期望损益（贴现）为 0，与胜率无关；计入成本后为负。胜率 21.6%–98.5% 的六档行权价给出相同期望 | [2026-11-27](rounds/2026-11-27.md) |
| F-002 | 当实际波动率低于隐含波动率时，卖出期权存在正期望（波动率风险溢价） | 波动率交易常见说法 | `BLOCKED` | 需要真实隐含波动率与已实现波动率序列；仓库当前无该数据源。解除条件：接入期权 IV 与 RV 历史数据后，用固定窗口比较 `RV < IV` 子样本内卖方组合的到期损益（含成本、报告样本量） | 待数据；数据就绪后重试 |
| F-003 | 期货曲线年化斜率（按 365 自然日线性换算）等于持有该价差可实现的年化展期收益 | 本仓库 `futures-curve-structure` 的常见误读 | `OPEN` | 合成/离线曲线：比较年化斜率与含换手成本、按实际展期日移仓的收益；证明年化斜率忽略了换手与价格路径，不能直接当可实现收益 | 待做（Round 3 候选） |
| F-004 | 多框架共识分 = 多个相互独立框架的投票 | 本仓库 `master-ensemble` 的反对说法 | **REFUTED** | 仓库文档已说明框架共享因子与数据源，不具备统计独立性；"独立投票"的解读不成立 | [docs/validation.md "尚未证明的能力"](../docs/validation.md)、[README.md](../README.md) |
| F-005 | 用"当前股票池 + 120 天财报滞后"的回测可视为 point-in-time 历史业绩 | 本仓库 `framework-backtest` 的已知限制 | **REFUTED** | 当前成分股与固定滞后不含真实披露日、历史修订与退市；存在幸存者/前视偏差。仓库文档已明确该限制 | [framework-backtest README](../my-skills/framework-backtest/README.md)、[docs/validation.md](../docs/validation.md) |
| F-006 | 备兑看涨组合的最大亏损一定是有限的 | 期权教材式结论（标的不可为负时成立） | **REFUTED** | 以期货为标的且允许负结算价时（如 2020 年 WTI），备兑看涨左尾亏损无界；本仓库组合损益工具把定义域限定 `S>0` 并在文档中声明该限制 | [options-strategy-payoff](../my-skills/options-strategy-payoff/SKILL.md)、[payoff-method.md](../my-skills/options-strategy-payoff/references/payoff-method.md) |
| F-007 | Black-76 平价残差接近 0，说明市场价格无套利机会 | 对 `futures-options-pricing` 平价校验的误读 | **REFUTED** | 残差 ≈0 只表示同期限同行使价的看涨/看跌报价口径一致；未建模借券、资金成本、手续费与买卖价差，不能据此判断可套利性 | [futures-options-pricing SKILL.md](../my-skills/futures-options-pricing/SKILL.md) |
| F-008 | RSI < 30 的"超卖"状态之后，短期（如 5 个交易日）正收益概率显著高于 50% | 常见技术分析经验 | `OPEN` | 需要一段可复现的日线数据（AKShare 或本地缓存）；固定股票池、固定阈值、固定持有期，含多重比较控制与成本；报告样本量与置信区间 | 待做（数据就绪后 Round 候选） |

> 说明：`REFUTED` 里 F-004–F-007 是"主张本身在仓库文档/模型边界里已被推翻或明确不成立"，属于文档级证据；F-001 是模型级反例（本轮计算）。`OPEN` 是尚未验证的主张，不代表正确。
