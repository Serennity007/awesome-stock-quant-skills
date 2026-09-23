---
name: us-hot-stocks-tracker
description: 美股热门AI股追踪器：内置AI算力/存储/AI应用/robotaxi主题清单，输出现价、涨跌幅、20/60日动量、52周高低位距离、成交量异动快照表 | US hot AI stocks tracker: built-in AI compute/storage/AI application/robotaxi watchlist, outputs current price, change%, 20/60-day momentum, 52-week high/low distance, volume anomaly snapshot | 米国人気AI株トラッカー：AIコンピュート/ストレージ/AIアプリ/robotaxiテーマのウォッチリストを内蔵し、現在値、騰落率、20/60日モメンタム、52週高安値距離、出来高異常を出力
author: Serennity007
license: MIT
---

# 🚀 美股最热 AI 股追踪器（us-hot-stocks-tracker）

一屏追踪美股AI行情最前线。基于 akshare 新浪财经美股日线，对内置主题清单做机械式快照，覆盖 AI 算力、存储、AI 应用、robotaxi 等方向的8只核心标的，输出现价、涨跌幅、20/60日动量、52周位置、成交量异动，并按20日动量排序，供 AI 快速把握市场情绪与强度。

## 追踪清单

| 标签 | 默认标的 |
|---|---|
| AI 算力 | NVDA、AVGO、ORCL、GOOGL |
| 存储 | SNDK、WDC |
| AI 应用 | PLTR |
| robotaxi / 人物概念 | TSLA（马斯克） |

题材标签、关键人物与近期看点见 `references/watchlist.md`。

## 输出字段

| 字段 | 说明 |
|---|---|
| `ticker` | 股票代码 |
| `theme` | 题材标签 |
| `price` | 最新收盘价（未复权日线最新收盘价） |
| `change_pct` | 较前一日涨跌幅（%，基于未复权收盘价） |
| `mom_20` | 近 20 个交易日动量（%，基于前复权收盘价） |
| `mom_60` | 近 60 个交易日动量（%，基于前复权收盘价） |
| `dist_52w_high` | 距离近 252 个交易日高点（%，基于前复权高低点） |
| `dist_52w_low` | 距离近 252 个交易日低点（%，基于前复权高低点） |
| `vol_ratio` | 成交量 / 20 日均量（基于未复权成交量） |

默认按 `mom_20` 降序排列。

## 使用方法

```bash
pip install akshare pandas

# 默认追踪清单
python scripts/us_hot.py

# 自定义标的
python scripts/us_hot.py --tickers NVDA,AAPL,MSFT

# 输出 CSV
python scripts/us_hot.py --out us_hot.csv

# 按 60 日动量排序
python scripts/us_hot.py --sort mom_60
```

参数说明：

- `--tickers`: 逗号分隔的美股代码（默认 `NVDA,AVGO,ORCL,GOOGL,SNDK,WDC,PLTR,TSLA`）
- `--out`: CSV 输出路径（可选）
- `--sort`: 排序字段，可选 `mom_20`、`mom_60`、`change_pct`、`vol_ratio`（默认 `mom_20`）

## 数据来源与局限

- 日线数据来自 akshare `stock_us_daily`（新浪财经美股日线）。
- 现价、涨跌幅、成交量基于**未复权**日线（`adjust=""`），避免复权因子异常导致的价格失真。
- 20/60 日动量、52 周高低位距离基于**前复权**日线（`adjust="qfq"`），保证长期可比性。
- 由于 akshare 实时行情接口（如 `stock_us_spot_em`）在本脚本测试环境中无法稳定访问，脚本采用**日线最新收盘价**作为现价、**日线最新成交量**作为成交量，涨跌幅由最近两根未复权 K 线计算。若需实时盘中数据，可替换为可用的实时接口。
- 美股受财报、宏观、地缘影响波动大，快照表仅为机械统计，不构成投资建议。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史价格与动量不代表未来表现，任何交易决策必须结合基本面、市场环境与个人风险承受能力独立判断。
