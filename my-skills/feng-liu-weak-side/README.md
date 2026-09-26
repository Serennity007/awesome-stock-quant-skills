# 🥊 冯柳弱者体系｜跌出来的赔率：4 个指标逆向打捞 A 股“没人要”的标的

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富/同花顺/新浪公开接口）

> **假设自己是市场上最弱的信息接收者，赔率优先、逆向买入、集中但认错快。**

本技能把高毅资产冯柳的“弱者体系”搬到 A 股市场：不追热点、不拼消息，只看“跌透了但还没死”的标的。核心脚本 `scripts/screen.py` 按“跌幅、估值、基本面、关注度”四维打分，输出带“赔率 / 概率”标签的逆向观察清单。

## 文件清单

- `SKILL.md` — 技能定义、4 维打分逻辑与使用说明
- `scripts/screen.py` — A 股弱者体系初筛脚本（CSV + 终端表格）
- `references/feng_liu_framework.md` — 弱者体系核心思想：弱者假设、赔率优先、逆向买入、集中持仓、认错要快、价值陷阱辨析

## 快速开始

```bash
pip install akshare pandas

# 默认沪深300成分股作为股票池，输出前 20 名
python scripts/screen.py --pool hs300 --top 20 --out weak_side_result.csv

# 自定义小股票池验证
python scripts/screen.py --codes 600519,000858,600036 --out weak_side_result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `weak_side_result.csv`）。

## 4 维逆向雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| 赔率（跌幅） | 距 52 周高点回撤 | 回撤 > 40% 视为高赔率起点 |
| 赔率（估值） | PE/PB 近 3 年百分位 | 百分位 < 20% 视为历史低位 |
| 概率（基本面） | 盈利为正、营收/利润未崩、ROE/负债可控 | 排除基本面永久恶化的价值陷阱 |
| 低关注度 | 换手率 | 越低越说明市场已遗忘或厌恶 |

## 输出字段

- `code` / `name` / `industry`：代码 / 简称 / 行业
- `close` / `high_52w` / `drawdown_pct`：现价 / 52 周高点 / 回撤幅度
- `pe_ttm` / `pb` / `pe_percentile_3y` / `pb_percentile_3y`：估值与近 3 年百分位
- `turnover_pct`：换手率（%）
- `latest_revenue` / `latest_profit` / `revenue_yoy` / `profit_yoy`：最新报告期营收/利润（亿元）及同比增速
- `weak_score` / `odds_label` / `probability_label`：综合得分 / 赔率标签 / 概率标签
- `framework_note`：赔率/概率来源说明
- `weak_pass`：是否通过硬门槛

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现；任何筛选结果都必须经过你对生意的理解（能力圈）二次确认。逆向投资面临价值陷阱、流动性、行业长期衰退等风险，请独立判断。
