# 🚀 美股最热AI股追踪器｜8只核心标的动量一屏扫完

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007（原创）| License：MIT | 数据：akshare（新浪财经美股日线）

一屏追踪美股AI行情最前线。覆盖 NVDA/AVGO/ORCL/GOOGL/SNDK/WDC/PLTR/TSLA 共8只核心标的，基于 akshare 新浪财经美股日线，机械式输出最新价、日涨跌幅、20/60日动量、52周位置、量能异动，并按20日动量排序，快速判断谁强谁弱。

## 快速开始

```bash
pip install akshare pandas

# 默认清单（AI 算力 / 存储 / AI 应用 / robotaxi）
python scripts/us_hot.py

# 自定义标的
python scripts/us_hot.py --tickers NVDA,AAPL,MSFT,AMD

# 输出 CSV
python scripts/us_hot.py --out us_hot.csv
```

## 默认追踪清单

| 标签 | 标的 | 关键人物 |
|---|---|---|
| AI 算力 | NVDA、AVGO、ORCL、GOOGL | 黄仁勋（NVDA） |
| 存储 | SNDK、WDC | — |
| AI 应用 | PLTR | Alex Karp |
| robotaxi / 人物概念 | TSLA | 马斯克 |

详细看点与风险提示见 `references/watchlist.md`。

## 输出字段

| 字段 | 说明 |
|---|---|
| `ticker` | 股票代码 |
| `theme` | 题材标签 |
| `price` | 最新收盘价（未复权日线最新收盘价） |
| `change_pct` | 较前一日涨跌幅（%，基于未复权收盘价） |
| `mom_20` | 近 20 日动量（%，基于前复权收盘价） |
| `mom_60` | 近 60 日动量（%，基于前复权收盘价） |
| `dist_52w_high` | 距离近 252 日高点（%，基于前复权高低点） |
| `dist_52w_low` | 距离近 252 日低点（%，基于前复权高低点） |
| `vol_ratio` | 成交量 / 20 日均量（基于未复权成交量） |

## 配套文件

- `SKILL.md` — 技能定义与使用说明
- `scripts/us_hot.py` — 主脚本（支持 `--tickers`、`--out`、`--sort`）
- `references/watchlist.md` — 标的题材标签、关键人物与近期看点

## 数据说明

- 日线数据来自 akshare `stock_us_daily`（新浪财经美股日线）。
- 现价、涨跌幅、成交量使用**未复权**日线（`adjust=""`），避免复权因子异常导致的价格失真。
- 20/60 日动量、52 周高低位距离使用**前复权**日线（`adjust="qfq"`），保证长期可比性。

## 免责声明

仅供学习研究，不构成投资建议。历史价格与动量不代表未来表现，任何交易决策必须结合基本面、市场环境与个人风险承受能力独立判断。
