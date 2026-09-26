# 🌙 数月亮不数星星｜邱国鹭「三好」A 股龙头打分器

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富/同花顺/腾讯/新浪公开接口）

> **行业格局大于个股 α，便宜是硬道理，胜而后求战。**

本技能把邱国鹭《投资中最简单的事》里的“好行业、好公司、好价格”三好标准，做成 A 股机械化初筛器：直接从沪深300或自定义股票池中，按行业市值龙头、ROE 稳定性、营收增速、PE/PB 历史低分位打分，只输出各行业“月亮”（龙头），不追逐二三线“星星”。

## 文件清单

- `SKILL.md` — 技能定义、3 维打分逻辑与使用说明
- `scripts/screen.py` — A 股三好龙头打分脚本（CSV + 终端表格）
- `references/qiu_principles.md` — 邱国鹭核心投资原则整理

## 快速开始

```bash
pip install akshare pandas

# 默认沪深300成分股作为股票池，输出前 20 名
python scripts/screen.py --pool hs300 --top 20 --out qiu_result.csv

# 自定义小股票池验证
python scripts/screen.py --codes 600519,000858,600036 --out qiu_result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `qiu_result.csv`）。
- `--sleep`: 每只股票请求间隔（默认 0.3 秒，防限流）。

## 3 维打分雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| 好行业 | 行业内市值排名 | 前 3 名得 25/20/15 分；非龙头 0 分，落实“数月亮不数星星” |
| 好公司 | 近 5 年 ROE + 营收增速 | ROE 均值 ≥15% 且稳定得分高；营收增速为正且稳定近似市占率/竞争优势 |
| 好价格 | PE/PB 历史估值分位 | 分位越低得分越高；无历史分位时按绝对 PE/PB 降级评分 |

## 输出字段

- `code` / `name` / `industry`：股票代码 / 简称 / 行业
- `total_score`：综合得分（满分 100）
- `industry_rank` / `industry_score`：行业内市值排名 / 行业得分
- `roe_score` / `growth_score`：ROE 维度得分 / 营收增速维度得分
- `price_score` / `pe_score` / `pb_score`：价格维度总分 / PE 分位得分 / PB 分位得分
- `pe_ttm` / `pb` / `pe_percentile` / `pb_percentile`：当前估值与历史分位
- `roe_avg` / `roe_std` / `revenue_growth_avg`：ROE 均值 / 标准差 / 营收增速均值
- `total_mv_yi`：总市值（亿元）
- `data_years`：有效年度数
- `val_source` / `fin_source` / `note`：数据来源与降级说明

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标与估值分位不代表未来表现；任何筛选结果都必须经过你对行业格局与生意模式的独立研究二次确认。
