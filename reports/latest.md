# 每日财务筛选报告 / Daily screen · 2026-10-27

数据源：AKShare（新浪财务、东财估值）。规则分用于研究和人工复核，不是收益预测或买入指令。

本次返回 **20** 条记录：数据完整 **14** 条，数据不完整 **6** 条。

## 数据完整的筛选记录

`complete` 表示筛选器需要的字段齐全，不表示数据已独立审计或投资有效。`review_moat` 仍需人工核查。

| 排名 | 代码 | 规则分 | 判定 | 年报 ROE | 毛利率 | 负债率 | PE / PB 分位 | 估值日期 |
|---|---|---:|---|---|---|---|---|---|
| 1 | 600519 | 100 | review_moat | 27.7,31.8,34.6,37.0,33.6 | 91.7 | 16.4 | 0.25 / 0.1 | 2026-10-26 |
| 2 | 002415 | 93 | review_moat | 26.5,18.8,18.5,14.8,17.0 | 44.1 | 33.9 | 0.08 / 0.43 | 2026-10-26 |
| 3 | 603288 | 91 | review_moat | 28.5,23.5,19.7,20.5,17.0 | 37.3 | 19.8 | 0.05 / 0.09 | 2026-10-26 |
| 4 | 000858 | 90 | review_moat | 23.6,23.4,23.3,23.9,7.5 | 76.2 | 35.7 | 0.45 / 0.07 | 2026-10-26 |
| 5 | 600276 | 79 | review_moat | 12.9,10.3,10.6,13.9,12.6 | 85.2 | 11.6 | 0.07 / 0.03 | 2026-10-26 |
| 6 | 300750 | 73 | review_moat | 18.9,18.7,22.3,20.6,21.4 | 23.3 | 61.9 | 0.0 / 0.0 | 2026-10-26 |
| 7 | 600887 | 73 | review_moat | 18.2,18.8,19.5,15.9,21.2 | 32.8 | 61.5 | 0.43 / 0.57 | 2026-10-26 |
| 8 | 000651 | 69 | review_weakness | 22.2,25.3,24.8,23.4,19.9 | 27.8 | 61.7 | 0.33 / 0.02 | 2026-10-26 |
| 9 | 601888 | 66 | review_weakness | 32.6,10.4,12.5,7.7,6.5 | 31.7 | 18.5 | 0.14 / 0.01 | 2026-10-26 |
| 10 | 600900 | 65 | review_weakness | 14.5,11.5,13.5,15.4,15.6 | 59.6 | 58.3 | 0.41 / 0.88 | 2026-10-26 |
| 11 | 000333 | 63 | review_weakness | 22.9,20.7,20.7,17.8,19.7 | 25.0 | 61.2 | 0.84 / 0.88 | 2026-10-26 |
| 12 | 601899 | 61 | review_weakness | 22.1,22.6,19.6,22.9,27.9 | 19.0 | 51.6 | 0.02 / 0.51 | 2026-10-26 |
| 13 | 002594 | 54 | review_weakness | 3.2,15.0,21.6,21.7,13.2 | 17.2 | 70.7 | 0.39 / 0.01 | 2026-10-26 |
| 14 | 600585 | 48 | below_threshold | 18.1,8.5,5.6,4.1,4.2 | 22.7 | 20.4 | 0.85 / 0.07 | 2026-10-26 |

## 数据不完整：先补数，不参与完整记录的总分排序

| 代码 | 数据状态 | 判定 | 数据缺口 |
|---|---|---|---|
| 601012 | partial | needs_data | valuation_incomplete |
| 601318 | partial | needs_data | roe_history_incomplete_or_nonconsecutive;gross_history_incomplete_or_not_applicable |
| 600036 | partial | needs_data | roe_history_incomplete_or_nonconsecutive;gross_history_incomplete_or_not_applicable |
| 600030 | partial | needs_data | gross_history_incomplete_or_not_applicable |
| 000001 | partial | needs_data | roe_history_incomplete_or_nonconsecutive;gross_history_incomplete_or_not_applicable |
| 601166 | partial | needs_data | roe_history_incomplete_or_nonconsecutive;gross_history_incomplete_or_not_applicable |

## 模拟与复盘

可用 `scripts/paper_journal.py start` 冻结本次输入和规则，后续导入信号日之后的价格追加模拟复盘。
筛选成功不等于模拟成交；没有后续价格时不生成收益。

[原始 CSV](2026-10-27.csv) · [数据元信息](2026-10-27.csv.meta.json) · [模拟记录说明](../docs/paper-journal.md)

[本日首次冻结的模拟观察清单](paper/2026-10-27/INITIAL_REVIEW.md)（待建仓，不含虚构收益）。
