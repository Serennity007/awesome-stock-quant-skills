# 🏦 约翰·聂夫低市盈率投资法｜总回报率 ≥2 找 A 股"遭人嫌弃的好公司"

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富 / 巨潮 / 腾讯公开接口）

> **"在无人喜爱的行业里布局位置稳固的公司。"**

本技能把约翰·聂夫（温莎基金 31 年年化跑赢市场 3.1 个百分点）的低市盈率体系搬到 A 股市场：个股 PE 相对全市场中位数的折价、(增速+股息率)/PE≥2 的总回报率黄金标准、持续分红、基本面底线。脚本输出 CSV，再用"便宜是因为没人喜欢，还是真的坏掉了"做人工复核。

## 文件清单

- `SKILL.md` — 技能定义、七维打分逻辑与使用说明
- `scripts/screen.py` — A 股低市盈率打分脚本（CSV + 终端表格）
- `references/neff_principles.md` — 聂夫核心思想：低市盈率哲学、总回报率公式、逆人潮而行、卖出纪律
- `neff_test_result.csv` — 小样实测输出（2026-09-26，招行/茅台/五粮液）

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
- `--out`: CSV 输出路径（默认 `neff_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，防接口限流）。

## 七维低市盈率雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| 低市盈率 | 个股 PE(TTM) / 全市场 PE 中位数 | 温莎组合 PE 长期为市场 4–6 折（满分 25） |
| 总回报率 | (净利润增速均值 + 股息率) / PE | 聂夫黄金标准 ≥2（满分 25） |
| 股息率 | 最近 5 次派息按时间跨度年化 / 现价 | 等待市场转变看法期间的工资（满分 15） |
| 盈利增长底线 | 增速均值 >0 且正增长年数≥3 | 区分"被嫌弃"与"坏掉"（满分 10） |
| 资本回报 | 近 5 年 ROE 均值 | 生意质量（满分 10） |
| 低负债 | 最新资产负债率 | 财务稳健（满分 10） |
| 盈利含金量 | 经营现金流净额/净利润 | 利润为真（满分 5） |

判定线：**≥75 聂夫式候选**；**55–74 观察**；**<55 不符合框架**。全市场中位数获取失败时低PE维度降级为绝对 PE 分档。

## 输出字段

- `code` / `name` / `industry`：代码 / 简称 / 行业
- `total`：综合得分（满分 100）
- `low_pe_score` / `trr_score` / `dividend_score` / `growth_score` / `roe_score` / `debt_score` / `cash_score`：各维度得分
- `pe_ttm` / `pe_market_ratio` / `pe_percentile`：PE(TTM) / 相对市场中位数比 / 历史分位
- `total_return_ratio` / `dividend_yield` / `dividend_events` / `dividend_span_years`：总回报率 / 年化股息率 / 派息次数 / 统计跨度
- `profit_growth_mean` / `roe_mean` / `debt_latest` / `ocf_mean`：其余财务指标
- `data_years` / `val_source` / `fin_source` / `note`：数据年数 / 来源 / 降级说明

## 实测参考（2026-09-26，小样 3 只）

招商银行 88 分（PE 6.76，仅为全市场中位数的 0.18 倍；股息率 6.34%；总回报率 2.33 过黄金线）、贵州茅台 76 分、五粮液 65 分——银行等被冷落的低估值高分红行业天然契合聂夫框架，符合直觉。

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现；任何筛选结果都必须经过"便宜的原因"定性复核。
