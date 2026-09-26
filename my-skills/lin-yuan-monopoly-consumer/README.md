# 🍶 林园垄断+成瘾性消费投资法｜只投“嘴巴上的刚需龙头”

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富/巨潮/腾讯公开接口）

> **“我只投与嘴巴相关的、成瘾的、垄断的、毛利率唯一不骗人的公司。”**

本技能把林园公开访谈/演讲中反复提及的投资框架搬到 A 股市场：不追热点、不猜 K 线，只用 4 把财务尺子连续扫描——**嘴巴相关刚需、毛利率 >50%、ROE 持续高位、分红率高**——找出具备“垄断+成瘾”特征的候选标的，再交给定性分析（护城河、估值、能力圈）做最终判断。

## 文件清单

- `SKILL.md` — 技能定义、4 大铁律打分逻辑与使用说明
- `scripts/screen.py` — A 股林园式初筛脚本（CSV + 终端表格）
- `references/lin_yuan_rules.md` — 林园投资思想整理：垄断、嘴巴相关、毛利率、买了就不卖、纪律

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
- `--out`: CSV 输出路径（默认 `lin_yuan_screen_result.csv`）。
- `--min-gross`: 毛利率硬门槛（默认 50%）。
- `--min-roe`: ROE 硬门槛（默认 15%）。
- `--min-div`: 近 12 个月股息率硬门槛（默认 1.0%）。
- `--sleep`: 每只股票请求间隔（默认 0.3 秒，防接口限流）。

## 4 大筛选铁律

| 维度 | 代理指标 | 权重 |
|---|---|---|
| 垄断定价权 | 近 5 年毛利率均值 >50%、波动小 | 30 |
| ROE 持续高位 | 连续 5 年 ROE ≥15% 的年数与均值 | 25 |
| 股东回报 | 近 12 个月股息率 + 近 5 年分红持续性 | 20 |
| 成瘾/刚需行业 | 白酒/中药/调味品/乳品/啤酒等白名单 | 15 |
| 财务稳健 | 最新资产负债率 | 10 |

## 输出字段

- `code` / `name`：股票代码 / 简称
- `score`：综合得分（满分 100）
- `linyuan_pass`：是否通过硬门槛
- `sw_industry` / `sw_sector`：申万行业分类
- `gross_mean` / `gross_annual`：毛利率均值 / 序列
- `roe_mean` / `roe_annual`：ROE 均值 / 序列
- `dividend_yield` / `payout_recent`：股息率 / 最近一年派息
- `debt_latest`：最新资产负债率
- `addictive_tag`：成瘾/刚需行业标签
- `data_years` / `source` / `note`：数据年度、来源、降级说明

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现；任何筛选结果都必须经过你对生意的理解（能力圈）二次确认。林园本人观点以公开访谈、演讲、著作为准，本整理可能存在理解偏差。
