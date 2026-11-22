# 每日财务筛选报告 / Daily screen · 2026-11-22

数据源：AKShare（新浪财务、东财估值）。规则分用于研究和人工复核，不是收益预测或买入指令。

本次返回 **20** 条记录：数据完整 **0** 条，数据不完整 **20** 条。

## 数据完整的筛选记录

`complete` 表示筛选器需要的字段齐全，不表示数据已独立审计或投资有效。`review_moat` 仍需人工核查。

| 排名 | 代码 | 规则分 | 判定 | 年报 ROE | 毛利率 | 负债率 | PE / PB 分位 | 估值日期 |
|---|---|---:|---|---|---|---|---|---|

本次没有数据完整的记录。

## 数据不完整：先补数，不参与完整记录的总分排序

| 代码 | 数据状态 | 判定 | 数据缺口 |
|---|---|---|---|
| 603288 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 600519 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 002415 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 601899 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 300750 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 000858 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 000651 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 600276 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 601888 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 600887 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 002594 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 000333 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 601012 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete;valuation_incomplete |
| 600585 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 600900 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 600030 | partial | needs_data | gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 600036 | partial | needs_data | roe_history_incomplete_or_nonconsecutive;gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 601318 | partial | needs_data | roe_history_incomplete_or_nonconsecutive;gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 601166 | partial | needs_data | roe_history_incomplete_or_nonconsecutive;gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |
| 000001 | partial | needs_data | roe_history_incomplete_or_nonconsecutive;gross_history_incomplete_or_not_applicable;cashflow_history_incomplete |

## 模拟与复盘

可用 `scripts/paper_journal.py start` 冻结本次输入和规则，后续导入信号日之后的价格追加模拟复盘。
筛选成功不等于模拟成交；没有后续价格时不生成收益。

[原始 CSV](2026-11-22.csv) · [数据元信息](2026-11-22.csv.meta.json) · [模拟记录说明](../docs/paper-journal.md)

[本日首次冻结的模拟观察清单](paper/2026-11-22/INITIAL_REVIEW.md)（待建仓，不含虚构收益）。
