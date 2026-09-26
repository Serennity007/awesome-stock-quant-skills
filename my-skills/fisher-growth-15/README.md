# 🌱 费雪成长股 15 要点｜六维打分为"闲聊法"调研筛出 A 股成长股

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富 / 新浪公开接口）

> **"The stock market is filled with individuals who know the price of everything and the value of nothing."**

本技能把费雪《怎样选择成长股》中可量化的检查项搬到 A 股市场：成长跑道（营收CAGR）、研发投入、利润率趋势、资本回报、盈利含金量、财务保守。脚本只负责把候选名单从几千只缩到几十只，15 要点中真正决定成败的定性部分（闲聊法调研）仍需人工完成。

## 文件清单

- `SKILL.md` — 技能定义、六维打分逻辑与使用说明
- `scripts/screen.py` — A 股成长股打分脚本（CSV + 终端表格）
- `references/fisher_15_points.md` — 费雪 15 要点全清单：成长潜力、管理与文化、闲聊法、买入卖出纪律
- `fisher_test_result.csv` — 小样实测输出（2026-09-26，迈瑞/海康/茅台）

## 快速开始

```bash
pip install akshare pandas

# 默认沪深300成分股作为股票池，输出前 20 名
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 自定义小股票池验证
python scripts/screen.py --codes 600519,300760,002415 --out result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `fisher_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，防接口限流）。

## 六维成长质量雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| 成长跑道 | 近 5 年营收 CAGR + 利润正增长年数 | 销售增长是成长股第一特征（满分 25） |
| 研发投入 | 研发费用/营业收入 | 管理层为明天投入的代理（满分 20） |
| 利润率趋势 | 毛利率水平 + 最新值趋势 | 维持或改善利润率（满分 15） |
| 资本回报 | 近 5 年 ROE 均值 | 股东回报验证（满分 15） |
| 盈利含金量 | 经营现金流净额/净利润 | 利润是否为真（满分 15） |
| 财务保守 | 最新资产负债率 | 要点 14 的代理（满分 10） |

判定线：**≥75 费雪式成长股候选**；**55–74 有亮点也有短板**；**<55 不符合框架**。金融/部分行业研发数据缺失时研发维度给中性分 5。

## 输出字段

- `code` / `name` / `industry`：代码 / 简称 / 行业
- `total`：综合得分（满分 100）
- `growth_score` / `rd_score` / `margin_score` / `roe_score` / `cash_score` / `debt_score`：各维度得分
- `rev_cagr` / `profit_pos_years`：营收CAGR / 利润正增长年数
- `rd_ratio_avg` / `rd_annual`：研发费用率均值 / 逐年序列
- `gross_mean` / `gross_annual` / `roe_mean` / `ocf_to_profit_mean` / `debt_latest`：其余财务指标
- `data_years` / `source` / `note`：数据年数 / 来源 / 降级说明

## 实测参考（2026-09-26，小样 3 只）

迈瑞医疗 78 分（研发率 9.84%、毛利率 63.6%、ROE 29.7%）、海康威视 76 分（研发率 11.71%）居前，贵州茅台 63 分（研发率 0.09% 被扣分）——费雪框架天然偏好高研发成长企业而非成熟消费股，符合直觉。

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现；任何筛选结果都必须经过"闲聊法"式的独立调研二次确认。
