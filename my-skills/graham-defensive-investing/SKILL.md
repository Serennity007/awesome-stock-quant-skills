---
name: graham-defensive-investing
description: A股格雷厄姆防御型投资七准则筛股器：规模、流动比率、连续盈利、连续分红、盈利增长、低PE/PB量化筛选 | A-share Graham defensive investing screener: size, current ratio, earnings stability, dividend record, earnings growth, low PE/PB quantitative filter | A株グラハム防御型投資スクリーナー：規模、流動比率、継続的収益、継続的配当、収益成長、低PER/PBRの定量選別
author: Serennity007
license: MIT
---

# 🛡️ 格雷厄姆防御型七准则筛股器｜7道铁门守住A股本金

用本杰明·格雷厄姆（Benjamin Graham）在《聪明的投资者》中提出的防御型选股框架，对 A 股做机械化初筛。脚本把原本的 7 条定性准则量化成可计算的 7 道关卡，自动标注"通过 / 未通过 / 数据不足"，并支持数据不足 10 年时降级为 5 年窗口继续计算。

## 7 道防御关卡（A 股量化版）

| 关卡 | 标准 | 说明 |
|---|---|---|
| 1. 规模足够 | 总市值 ≥ 200 亿元（可自定义 --min-cap） | 过滤流动性差、抗风险能力弱的小盘股；默认 200 亿仅作学习参考 |
| 2. 流动比率 | 最新年度流动比率 > 2 | 流动资产 / 流动负债，衡量短期偿债能力 |
| 3. 连续盈利 | 窗口期内每年扣非每股收益 > 0 | 10 年窗口优先；不足 10 年但 ≥5 年则降级为 5 年 |
| 4. 连续分红 | 窗口期内每年都有现金分红 | 从 CNINFO 分红记录判断；某一年缺失分红记录即不通过 |
| 5. 盈利增长 | 窗口期末扣非每股收益 / 期初 > 4/3 | 近 10 年（或 5 年）每股盈利累计增长 > 1/3 |
| 6. 低 PE | 最新 PE(静) < 15 | 使用 akshare 估值数据；失败时改用年报净利润自行估算 |
| 7. 低 PB | PB < 1.5，或 PE × PB < 22.5 | 两个条件满足其一即通过 |

> 注：第 7 关是经典的 Graham "PE × PB < 22.5" 组合测试；当 PB 单独 > 1.5 但 PE 足够低时，组合值仍可能通过。

## 使用方法

```bash
pip install akshare pandas

# 沪深300成分股中筛选防御型标的
python scripts/screen.py --pool hs300 --top 20 --out graham_result.csv

# 自定义小样本测试
python scripts/screen.py --codes 600519,000858,600036 --out graham_result.csv

# 调整规模门槛
python scripts/screen.py --pool hs300 --min-cap 100 --top 30
```

参数说明：

- `--pool`: 股票池，目前仅支持 `hs300`
- `--codes`: 逗号分隔的自定义股票代码，优先于 `--pool`
- `--top`: 终端展示前 N 名（按通过关卡数 + PE × PB 综合排序，默认 20）
- `--out`: CSV 输出路径（默认 `graham_result.csv`）
- `--min-cap`: 最小总市值门槛，单位亿元（默认 200）
- `--sleep`: 每只股票间隔秒数（防限流，默认 0.5）

## 输出字段

| 字段 | 含义 |
|---|---|
| `code` | 股票代码 |
| `name` | 股票名称 |
| `window` | 数据窗口：`10Y` / `5Y` / `NA`（数据不足） |
| `market_cap` | 总市值（亿元） |
| `current_ratio` | 最新年度流动比率 |
| `eps_first` / `eps_last` | 窗口期首年 / 末年的扣非每股收益（元） |
| `eps_growth` | 每股收益累计增长率 |
| `profit_years` | 窗口期内盈利年数 |
| `div_years` | 窗口期内分红年数 |
| `pe` | 最新 PE(静) |
| `pb` | 最新 PB |
| `pe_pb` | PE × PB |
| `pass_*` | 各关卡是否通过（True/False） |
| `pass_count` | 通过关卡数（0-7） |
| `pass_all` | 是否 7 关全通过 |

## 数据来源与降级策略

- 主要使用 akshare 的东方财富接口（`stock_financial_analysis_indicator`、`stock_value_em`、`stock_dividend_cninfo`）。
- 脚本启动时自动禁用系统代理，避免本地代理（如 `127.0.0.1:7890`）阻断东财接口。
- 东财接口失败时自动降级：
  - 估值数据 → Sina 日行情 + 年报数据自行计算 PE/PB
  - 财务指标 → Sina 三大报表自行计算流动比率与盈利
  - 分红数据 → 无可靠降级，标记为数据缺失

## 配套文件

- `references/graham_principles.md` — 格雷厄姆核心原则：安全边际、市场先生、防御型 vs 进取型、烟蒂股风险

## 免责声明

本技能仅供学习研究，不构成投资建议。任何量化筛选都只能作为初筛工具，最终决策必须建立在你对企业生意、行业周期与估值的理解之上。历史数据不代表未来表现， Graham 框架本身也会错过高成长优质企业，请结合自身风险偏好使用。
