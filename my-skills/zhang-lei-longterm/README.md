# 🚀 张磊高瓴长期结构性价值投资｜4 维雷达锁定 A 股“时间的朋友”

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富 / 新浪公开接口）

> **“我们是创业者，只不过恰好是投资人。”**

本技能把张磊在《价值》中提出的**长期结构性价值投资**框架搬到 A 股市场：不看 K 线、不追热点，只用 4 把财务尺子连续扫描企业成长质量——连续双增、长期投入、行业空间、ROE 趋势——找出具备“时间的朋友”特征的候选标的，再交给定性分析（人、护城河、能力圈）做最终判断。

## 文件清单

- `SKILL.md` — 技能定义、4 维打分逻辑与使用说明
- `scripts/screen.py` — A 股长期结构性价值初筛脚本（CSV + 终端表格）
- `references/zhang_lei_principles.md` — 张磊《价值》核心原则：长期主义、动态护城河、选人风控、重仓中国/科技创新、哑铃策略

## 快速开始

```bash
pip install akshare pandas

# 默认沪深300成分股作为股票池，输出前 20 名
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 自定义小股票池验证
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `zhang_lei_screen_result.csv`）。

## 4 维打分雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| 连续双增 | 近 5 年营收/净利润均正增长年数 | 4–5 年双增为最佳 |
| 长期投入 | 研发费用率 或 资本开支/营收 | 占比高且趋势向上说明企业为未来下注 |
| 行业空间 | 最新年度营收增速 vs 行业平均 | 跑赢行业说明企业在获取结构性份额 |
| ROE 趋势 | 近 5 年 ROE 走势 | 最新 ROE 高于均值且趋势向上为优 |

## 输出字段

- `code` / `name` / `industry`：代码 / 简称 / 行业
- `score_total`：综合得分（满分 100）
- `score_growth` / `score_investment` / `score_industry` / `score_roe_trend`：各维度得分
- `double_growth_years`：营收/利润双增年数
- `avg_rev_growth` / `avg_profit_growth`：近 5 年均值增速
- `rd_ratio_avg` / `capex_to_rev_avg`：研发费用率 / 资本开支占比均值
- `industry_avg_rev_growth` / `market_median_rev_growth`：行业平均 / 全市场中位增速
- `roe_latest` / `roe_5y`：最新 ROE / 5 年序列
- `data_years` / `source` / `note`：数据年数 / 来源 / 降级说明

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现；任何筛选结果都必须经过你对生意的理解（能力圈）二次确认。
