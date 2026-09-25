# 🧮 西蒙斯因子量化｜5 维复合信号猎取 A 股短线统计规律

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富/新浪公开接口）

> **信号重于叙事，数据驱动决策。**

本技能以詹姆斯·西蒙斯与大奖章基金的公开投资哲学为灵感，把 A 股行情转化为 5 个可量化的统计信号：动量、反转、低波、量能、均线偏离度。`scripts/factor_scan.py` 会对股票池逐只打分，输出综合因子排名，供你进一步做组合验证与风控设计。

> ⚠️ 大奖章基金的真实策略不公开。本 skill 仅为学习整理，不构成投资建议。

## 文件清单

- `SKILL.md` — 技能定义、5 维因子逻辑与使用说明
- `scripts/factor_scan.py` — A 股多因子打分脚本（CSV + 终端表格）
- `references/simons_methods.md` — 詹姆斯·西蒙斯/大奖章基金思路学习整理

## 快速开始

```bash
pip install akshare pandas

# 默认沪深300成分股作为股票池，输出前 20 名
python scripts/factor_scan.py --pool hs300 --top 20 --out result.csv

# 自定义小股票池验证（推荐）
python scripts/factor_scan.py --codes 600519,000858,600036 --top 10 --out result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `simons_factor_result.csv`）。
- `--end-date`: 截止日期，兼容 `20231231` 与 `2023-12-31`（默认今天）。
- `--lookback`: 回放眼日历天数（默认 150）。

## 5 维因子雷达

| 维度 | 代理指标 | 说明 |
|---|---|---|
| 动量 | 20日、60日收益率 | 强势延续得分 |
| 反转 | -5日收益率 | 短期超跌，均值回归候选 |
| 低波动 | -20日年化波动率 | 低波异象，控制风险 |
| 量能 | 近5日均量 / 近20日均量 | 成交量验证价格行为 |
| 均线偏离度 | -\|收盘价/60日均线 - 1\| | 偏离越小，回摆潜力越受青睐 |

## 输出字段

- `code / name`：股票代码与名称
- `total`：综合因子得分（0–100）
- `momentum_score / reversal_score / volatility_score / volume_score / ma_deviation_score`：五维得分
- `ret_5d / ret_20d / ret_60d / vol_20d_annual / volume_ratio_5_20 / ma60_deviation`：原始因子值
- `close / latest_date`：最新收盘价与日期
- `data_days / source`：有效数据条数与数据来源

## 免责声明

仅供学习研究，不构成投资建议。历史行情与统计规律不代表未来表现；任何筛选结果都必须经过独立研究与风险承受能力评估。大奖章基金的真实策略不公开，本 skill 仅为风格化致敬的学习框架。
