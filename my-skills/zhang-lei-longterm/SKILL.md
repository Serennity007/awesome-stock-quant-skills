---
name: zhang-lei-longterm
description: 张磊高瓴长期结构性价值投资：A股4维成长质量雷达，锁定连续双增、长期投入、行业空间、ROE向上的“时间的朋友” | Zhang Lei Hillhouse long-term structural value investing: 4-dimensional growth-quality radar for A-shares targeting sustained double growth, R&D/capex investment, industry headroom, and rising ROE | 張磊・高瓴の長期構造価値投資：A株4次元成長質スクリーナー、連続増収増益・長期投資・業界成長余地・ROE上昇を捕捉
author: Serennity007
license: MIT
---

# 🚀 张磊高瓴长期结构性价值投资｜4 维成长质量雷达锁定 A 股“时间的朋友”

> **“我们是创业者，只不过恰好是投资人。”**

本技能把张磊在《价值》中提出的**长期结构性价值投资**框架机械化落地到 A 股：不追热点、不猜情绪，只看企业是否具备“长期主义 + 动态护城河 + 长期投入 + 行业空间”的成长质量。核心工具是 `scripts/screen.py`——它从全市场或指定股票池中，按 4 个维度打分排序，输出结构化 CSV，供你进一步用 `references/zhang_lei_principles.md` 做定性复核。

## 4 维成长质量雷达（满分 100）

| 维度 | 核心问题 | 代理指标 | 权重 |
|---|---|---|---|
| 1. 连续双增 | 企业是否在持续增长？ | 近 5 年营收增速 >0 且净利润增速 >0 的年数 | 40 |
| 2. 长期投入 | 企业是否在为未来下注？ | 研发费用率 或 资本开支/营收 高且趋势向上 | 25 |
| 3. 行业空间 | 企业增速是否跑赢行业？ | 最新年度营收增速 vs 同花顺/东财行业平均（近似） | 20 |
| 4. ROE 趋势 | 资本回报是否在改善？ | 近 5 年 ROE 趋势向上 | 15 |

> 注：`akshare` 公开接口未直接提供一致口径的研发/资本开支指标，脚本从新浪三大报表手工计算，并在输出中标注来源。

## 使用方法

```bash
pip install akshare pandas

# 默认用沪深300成分股作为股票池
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 或用自定义股票池（推荐先小样本验证）
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

参数说明：

- `--pool`: 股票池，目前支持 `hs300`（沪深300）。
- `--codes`: 逗号分隔的自定义股票代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `zhang_lei_screen_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，用于防接口限流）。

## 输出字段速览

| 字段 | 含义 |
|---|---|
| `code` / `name` / `industry` | 股票代码 / 简称 / 所处行业 |
| `score_total` | 成长质量综合得分（满分 100） |
| `score_growth` | 连续营收/利润双增得分 |
| `score_investment` | 长期投入得分（研发或资本开支） |
| `score_industry` | 行业空间得分（相对行业/市场中位增速） |
| `score_roe_trend` | ROE 趋势向上得分 |
| `double_growth_years` | 近 5 年营收/利润双增年数 |
| `avg_rev_growth` / `avg_profit_growth` | 近 5 年营收/利润增速均值 |
| `rd_ratio_avg` / `capex_to_rev_avg` | 研发费用率均值 / 资本开支占营收比均值 |
| `industry_avg_rev_growth` / `market_median_rev_growth` | 行业平均增速 / 全市场中位增速 |
| `roe_latest` / `roe_5y` | 最新 ROE / 近 5 年 ROE 序列 |
| `data_years` / `source` / `note` | 有效年度数 / 数据来源 / 降级说明 |

## 分析流程（配合 AI 使用）

1. **跑初筛**：运行 `screen.py` 得到候选名单与各项得分。
2. **读原则**：对照 `references/zhang_lei_principles.md`，用“长期主义、动态护城河、选人是最大风控、重仓中国/科技创新、哑铃策略”五把尺子做定性复核。
3. **看人**：对高分股票重点研究管理层历史资本配置、是否跨界追热点、股东回报意识。
4. **估值与仓位**：只在能力圈内、价格留有安全边际时买入；真正看懂的机会敢于重注、长期持有。

## 数据来源与降级策略

- 数据来自 `akshare` 公开接口（东方财富财务指标表、新浪三大报表、业绩快报行业映射）。
- 脚本启动时默认禁用系统代理，避免 `127.0.0.1:7890` 等本地代理阻断数据源。
- 优先使用 `stock_financial_analysis_indicator` 获取主要财务指标；若金融/周期股字段缺失，自动用新浪三大报表补充。
- 若主接口失败，整体降级到新浪三大报表手工计算。
- 行业映射与行业平均增速来自 `stock_yjbb_em`；全部失败时以市场中位增速作为近似基准。
- 所有网络调用均带 3 次指数退避重试，调用间 `time.sleep(0.15)` 防限流。

## 配套文件

- `references/zhang_lei_principles.md` — 张磊《价值》核心：长期主义、动态护城河、选人是最大的风控、重仓中国/科技创新、哑铃策略。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过自己对生意的理解（能力圈）二次确认。投资决策应建立在独立研究、充分安全边际与自身风险承受能力之上。
