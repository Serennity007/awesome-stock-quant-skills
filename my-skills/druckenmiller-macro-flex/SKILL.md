---
name: druckenmiller-macro-flex
description: 德鲁肯米勒式宏观灵活仪表盘：用akshare跟踪美元/人民币汇率、中美10Y国债收益率、黄金、原油、铜、A股指数及个股的近N日趋势与动量，输出多空倾向快照 | Druckenmiller-style macro-flex dashboard: tracks USD/CNY, China/US 10Y yields, gold, crude oil, copper, A-share indices and individual stocks' N-day trend/momentum, outputs a long/short bias snapshot | ドラッケンミラー式マクロ・フレックス・ダッシュボード：USD/CNY、中米10年国債利回り、金、原油、銅、A株指数と個別銘柄のN日トレンド/モメンタムを追跡し、多空バイアス・スナップショットを出力
author: Serennity007
license: MIT
---

# 🦎 宏观变色龙：德鲁肯米勒式灵活仪表盘

每天开盘前先看一眼全球资金的"风向"。本技能以斯坦利·德鲁肯米勒（Stanley Druckenmiller）的宏观交易哲学为框架，用 akshare 把 **7 大类资产** 的近期趋势与动量压缩成一张表：美元/人民币汇率、中美 10 年期国债收益率、黄金、原油、铜、A 股主要指数，以及可选个股。输出不是交易信号，而是一张**趋势跟随视角的多空倾向快照**，帮助你判断当下是该"押重注"还是"买鸡蛋防守"。

## 核心能力（6 个维度）

| 维度 | 资产 | 趋势跟随含义 |
|---|---|---|
| 1. 汇率 | USD/CNY | 美元走强 → 美元偏多；人民币走强 → 美元偏空 |
| 2. 中债 | 中国 10Y 国债收益率 | 收益率上行 → 中债偏空；下行 → 中债偏多 |
| 3. 美债 | 美国 10Y 国债收益率 | 收益率上行 → 美债偏空；下行 → 美债偏多 |
| 4. 贵金属 | 黄金 | 价格上涨 → 黄金偏多；下跌 → 黄金偏空 |
| 5. 能源 | 原油 | 价格上涨 → 原油偏多；下跌 → 原油偏空 |
| 6. 工业金属 | 铜 | 价格上涨 → 铜偏多；下跌 → 铜偏空 |
| + A股 | 上证/沪深300/深证成指/创业板/科创50 + 自选个股 | 价格与动量方向决定偏多/偏空/中性 |

## 判定逻辑（趋势跟随视角）

```
BULLISH  = 收盘价 > N 日均线 且 N 日涨跌幅 > 0
BEARISH  = 收盘价 < N 日均线 且 N 日涨跌幅 < 0
NEUTRAL  = 其他情况（震荡或潜在拐点）
```

- 国债收益率的趋势方向与债券价格**相反**：收益率上行 = 债券偏空。
- 同时输出 `roc_n`（N 日涨跌幅%）与 `roc_5`（近 5 日涨跌幅%），帮助区分短期波动与中期趋势。
- 最后汇总综合宏观得分：偏多 +1、偏空 -1、中性 0，给出一个整体立场提示。

## 使用方法

```bash
pip install akshare pandas

# 默认 20 日窗口，输出 macro_dashboard.csv
python scripts/macro_dashboard.py

# 自定义窗口与输出路径
python scripts/macro_dashboard.py --days 20 --out macro_dashboard.csv

# 加入自选个股做同步扫描
python scripts/macro_dashboard.py --days 20 --codes 600519,000858,600036 --out my_dashboard.csv
```

参数说明：

- `--days`: 趋势/动量计算窗口（默认 20）
- `--codes`: 逗号分隔的 A 股个股代码（可选）
- `--out`: CSV 输出路径（默认 `macro_dashboard.csv`）
- `--no-proxy`: 禁用系统代理（脚本已默认禁用，保留兼容参数）

## 数据来源与降级策略

| 资产 | 首选接口 | 降级接口 |
|---|---|---|
| USD/CNY | `currency_boc_sina`（中行外汇牌价历史） | `fx_spot_quote`（外汇即期快照） |
| 中美 10Y 国债 | `bond_zh_us_rate` | `bond_china_yield`（仅中债） |
| 黄金 | `futures_foreign_hist(GC)`（COMEX 黄金） | `spot_golden_benchmark_sge`（上海金） |
| 原油 | `futures_foreign_hist(CL)`（NYMEX 原油） | — |
| 铜 | `futures_foreign_hist(HG)`（COMEX 铜） | — |
| A股指数 | `stock_zh_index_daily`（新浪） | `index_zh_a_hist`（东财） |
| 个股 | `stock_zh_a_daily`（新浪前复权） | — |

> 脚本启动时自动清除 `HTTP_PROXY` / `HTTPS_PROXY` 等环境变量并覆盖 `requests.utils.getproxies`，避免本地代理（如 `127.0.0.1:7890`）阻断数据源。所有 akshare 调用均包 `_retry_call` 指数退避 3 次，调用间 `time.sleep(0.15)`。

## 配套文件

- `references/druckenmiller_style.md` — 德鲁肯米勒投资思想要点整理（集中押注+快速认错、流动性驱动市场、资本保护第一、趋势比估值重要、"熊市买鸡蛋"式灵活）。

## 免责声明

本技能仅供学习研究，不构成投资建议。宏观趋势与动量均由历史价格统计而来，不代表未来走势；任何输出都必须结合基本面、流动性环境、政策变化与自身风险偏好二次确认。
