# 🔻 卡拉曼安全边际｜4 把尺子丈量 A 股“跌出来的机会”

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富/新浪公开接口）

> **风险优先于收益，现金是期权，便宜只是起点，催化剂才是回归的门票。**

本技能把塞斯·卡拉曼（Seth Klarman）在《安全边际》中的风险厌恶型深度价值投资框架搬到 A 股市场：不追热点、不猜 K 线，只找价格显著低于保守价值、且具备回归路径的候选标的。

## 文件清单

- `SKILL.md` — 技能定义、4 维打分逻辑与使用说明
- `scripts/deep_value.py` — A 股深度价值筛股脚本（CSV + 终端表格）
- `references/klarman_principles.md` — 《安全边际》核心思想：绝对收益、风险优先、催化剂驱动、现金是期权、不追市场

## 快速开始

```bash
pip install akshare pandas

# 默认沪深300成分股作为股票池，输出前 20 名
python scripts/deep_value.py --pool hs300 --top 20 --out result.csv

# 自定义小股票池验证（推荐）
python scripts/deep_value.py --codes 600519,000858,600036 --out result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `klarman_screen_result.csv`）。

## 4 维深度价值雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| PB 绝对值与历史分位 | 当前 PB、近 5 年 PB 分位 | PB<1 或历史极低位得分最高 |
| PE 低分位 | 近 5 年 PE(TTM) 分位 | 分位越低得分越高 |
| 市值/净现金比 | 市值 ÷（货币资金 - 有息负债）| <1 说明市值低于净现金，安全垫极厚 |
| 52 周高点回撤 | 当前价较 52 周高点跌幅 | 卡拉曼偏爱“跌出来”的机会 |
| 风险剔除 | ST / 最新年报亏损 | 强制 0 分 |

> 金融、地产等高杠杆行业的净现金口径不适用，脚本会标记缺失，但 PB/PE/回撤仍可打分。

## 输出字段

- `code / name`: 股票代码与名称
- `total`: 综合安全边际得分（满分 100）
- `pb_score / pb / pb_percentile`: PB 得分 / 当前 PB / 近 5 年分位
- `pe_score / pe / pe_percentile`: PE 得分 / 当前 PE / 近 5 年分位
- `netcash_score / market_cap / net_cash / market_cap_to_net_cash`: 净现金维度
- `drawdown_score / current_price / high_52w / drawdown_pct`: 回撤维度
- `is_st / is_loss`: 风险标记
- `val_source / price_source`: 数据来源与降级说明

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现；任何筛选结果都必须经过你对生意的理解（能力圈）与内在价值估算二次确认。
