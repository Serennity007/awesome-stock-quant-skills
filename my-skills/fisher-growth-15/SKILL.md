---
name: fisher-growth-15
description: A股费雪《怎样选择成长股》15要点机械化：营收CAGR成长跑道、研发费用率、毛利率趋势、连续ROE、盈利含金量、财务保守六维打分，为"闲聊法"调研筛出成长股候选 | A-share Philip Fisher growth-stock scoring: revenue CAGR runway, R&D intensity, margin trend, sustained ROE, cash quality, financial conservatism — a shortlist for scuttlebutt research | A株フィリップ・フィッシャー成長株スコアリング：売上CAGR、研究開発比率、利益率トレンド、持続ROE、キャッシュの質、財務健全性の6次元
author: Serennity007
license: MIT
---

# 🌱 费雪成长股 15 要点｜六维打分为"闲聊法"调研筛出 A 股成长股

> **"The stock market is filled with individuals who know the price of everything and the value of nothing."**

本技能把费雪《Common Stocks and Uncommon Profits》（中译《怎样选择成长股》）中可量化的检查项机械化到 A 股：成长跑道、研发投入、利润率趋势、资本回报、盈利含金量、财务保守。费雪方法论的核心本来是定性的——"闲聊法"（scuttlebutt）调研用户、对手、员工——脚本只负责把候选名单从几千只缩到几十只，**15 要点中真正决定成败的部分仍需人工调研**。

## 六维成长质量雷达（满分 100）

| 维度 | 核心问题 | 代理指标 | 权重 |
|---|---|---|---|
| 1. 成长跑道 | 未来销售能否继续增长？ | 近 5 年营收 CAGR + 净利润正增长年数 | 25 |
| 2. 研发投入 | 管理层是否在为明天投入？ | 研发费用/营业收入（新浪利润表） | 20 |
| 3. 利润率趋势 | 利润率能否维持或改善？ | 毛利率水平 + 最新值相对均值趋势 | 15 |
| 4. 资本回报 | 股东回报是否优秀？ | 近 5 年 ROE 均值 | 15 |
| 5. 盈利含金量 | 利润是否为真？ | 经营现金流净额/净利润 | 15 |
| 6. 财务保守 | 财务是否稳健？（要点14） | 最新资产负债率 | 10 |

判定线：**≥75 费雪式成长股候选**，进入"闲聊法"定性调研；**55–74 有亮点也有短板**；**<55 不符合框架**。

## 使用方法

```bash
pip install akshare pandas

# 默认用沪深300成分股作为股票池
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 或用自定义股票池（推荐先小样本验证）
python scripts/screen.py --codes 600519,300760,002415 --out result.csv
```

参数说明：

- `--pool`: 股票池，目前支持 `hs300`（沪深300）。
- `--codes`: 逗号分隔的自定义股票代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `fisher_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，用于防接口限流）。

## 输出字段速览

| 字段 | 含义 |
|---|---|
| `code` / `name` / `industry` | 股票代码 / 简称 / 所处行业 |
| `total` | 成长质量综合得分（满分 100） |
| `growth_score` / `rev_cagr` / `profit_pos_years` | 成长跑道得分 / 营收CAGR / 利润正增长年数 |
| `rd_score` / `rd_ratio_avg` / `rd_annual` | 研发投入得分 / 研发费用率均值 / 逐年序列 |
| `margin_score` / `gross_mean` / `gross_annual` | 利润率得分 / 毛利率均值 / 逐年序列 |
| `roe_score` / `roe_mean` | 资本回报得分 / ROE 均值 |
| `cash_score` / `ocf_to_profit_mean` | 盈利含金量得分 / 现金流净利润比均值 |
| `debt_score` / `debt_latest` | 财务保守得分 / 最新资产负债率 |
| `data_years` / `source` / `note` | 有效年度数 / 数据来源 / 降级说明 |

## 分析流程（配合 AI 使用）

1. **跑初筛**：运行 `screen.py` 得到候选名单与各项得分。
2. **读要点**：对照 `references/fisher_15_points.md`，把 15 个要点逐条过一遍。
3. **闲聊法**：对高分股票做费雪式调研——招股书/年报的管理层讨论、客户评价、竞争对手看法、员工口碑、行业专家意见。
4. **买入与持有**：费雪式买入看"这家公司能否再成长十年"，合适的时机出现前耐心等待；符合条件则集中持有、极长期持有。

## 实测参考（2026-09-26，小样 3 只）

迈瑞医疗 78 分（研发率 9.84%、毛利率 63.6%、ROE 29.7%）、海康威视 76 分（研发率 11.71%）居前，贵州茅台 63 分（研发率 0.09% 被扣分）——费雪框架天然偏好高研发成长企业而非成熟消费股，符合直觉。小样实测见 `fisher_test_result.csv`。

## 数据来源与降级策略

- 数据来自 `akshare` 公开接口（东方财富主要财务指标、新浪三大报表、业绩报表行业映射）。
- 脚本启动时默认禁用系统代理，避免 `127.0.0.1:7890` 等本地代理阻断数据源直连。
- 研发费用率来自新浪利润表"研发费用"科目（2018 年会计准则后披露），金融/部分行业无研发数据时给中性分 5。
- 主接口失败时整体降级到新浪三大报表手工计算。
- 所有网络调用均带 3 次指数退避重试，调用间 `time.sleep(0.15)` 防限流。

## 配套文件

- `references/fisher_15_points.md` — 费雪 15 要点全清单：成长潜力、管理与文化、闲聊法、买入卖出纪律。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过"闲聊法"式的独立调研二次确认。投资决策应建立在独立研究与自身风险承受能力之上。
