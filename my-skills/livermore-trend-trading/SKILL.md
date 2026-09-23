---
name: livermore-trend-trading
description: A股杰西·利弗莫尔趋势投机：识别N日新高关键点突破、放量确认、缩量回踩二次入场与单日反转/放量滞涨危险信号，输出信号表与金字塔仓位试探框架 | A-share Jesse Livermore trend speculation: identifies N-day new-high pivotal-point breakout, volume confirmation, low-volume pullback secondary entry, and one-day reversal/volume-stagnation danger signals, outputs a signal table and pyramid position-probe framework | A株ジェシー・リバモア流トレンド投機：N日高値の軸となるポイントブレイクアウト、出来高確認、縮量押し目の2次エントリー、一日反転/出来高伴う行き詰まり危険シグナルを識別し、シグナル表とピラミッド建玉試行フレームワークを出力
author: Serennity007
license: MIT
---

# 🎯 A股利弗莫尔趋势投机：5条纪律抓关键突破点

利弗莫尔说“大钱靠坐得住”。本技能用akshare日线数据做**机械化趋势投机信号识别**：N日新高关键点突破、放量确认、缩量回踩的二次入场点，以及单日反转/放量滞涨两类危险信号；并输出一套**金字塔加仓仓位试探框架**，帮助把“试探仓→确认加仓”的纪律落到可执行的数字。

## 识别的信号

| 信号 | 含义 | 默认判定 |
|---|---|---|
| `KEY_BREAKOUT` | 关键点放量突破 | 收盘价创近N日新高，且成交量 ≥ 20日均量 × 1.5 |
| `WEAK_BREAKOUT` | 突破但无量 | 收盘价创近N日新高，但成交量未达放量阈值 |
| `PULLBACK_ENTRY` | 缩量回踩二次入场 | 均线多头排列，收盘价回踩MA20 ±2%，成交量 ≤ 20日均量 × 0.8 |
| `ONE_DAY_REVERSAL` | 单日反转 | 创出近期高点后收盘接近当日低点，上影线显著，且放量 |
| `VOLUME_STAGNATION` | 放量滞涨 | 成交量显著放大（≥20日均量×1.8），但涨幅很小或收跌，伴随上影线 |
| `NO_SIGNAL` | 无明确信号 | 未命中上述任何信号 |

详细规则与仓位框架见 `references/livermore_rules.md`。

## 使用方法

```bash
pip install akshare pandas

# 默认：3只股票，近250个交易日，60日突破窗口，输出CSV
python scripts/pivotal_points.py --codes 600519,000858,600036 --out signals.csv

# 自定义窗口与交易日数
python scripts/pivotal_points.py --codes 600519,000858 --days 120 --window 30 --out signals.csv
```

参数说明：

- `--codes`：逗号分隔的6位A股代码（必填）
- `--days`：取近N个交易日（默认250）
- `--window`：N日新高突破窗口（默认60）
- `--out`：CSV输出路径（默认 `livermore_signals.csv`）
- `--no-proxy`：禁用系统代理（脚本默认已自动绕过系统代理，保留兼容参数）

## 仓位试探框架（金字塔）

脚本根据当前信号给出建议仓位动作：

| 信号 | 建议动作 |
|---|---|
| `KEY_BREAKOUT` | 最小阻力向上突破：试探仓 20%，回踩不破 + 放量确认后加仓至 40%；止损设于关键点下方 3–5% |
| `PULLBACK_ENTRY` | 趋势中缩量回踩：加仓/建仓 20–30%，止损设于 MA20 / 前低下方 |
| `WEAK_BREAKOUT` | 无量突破需警惕：暂不追，等待放量确认或回踩后再决定 |
| `ONE_DAY_REVERSAL` / `VOLUME_STAGNATION` | 危险信号：减仓或观望，暂停新开仓 |
| `NO_SIGNAL` | 无明确信号：空仓或轻仓观察 |

> 以上比例为示意框架，需根据个人资金规模、风险承受能力与市场环境调整。本工具只输出机械信号，不代替交易决策。

## 数据来源

- 优先使用东方财富日线接口（akshare `stock_zh_a_hist`）。
- 东财接口失败时自动降级到新浪财经日线接口（`stock_zh_a_daily`）。
- 脚本启动时自动清除 `HTTP_PROXY` / `HTTPS_PROXY` 等环境变量，避免本地代理（如 `127.0.0.1:7890`）阻断数据源。

## 配套文件

- `references/livermore_rules.md` — 利弗莫尔趋势投机核心原则与学习整理

## 免责声明

本技能仅供学习研究，不构成投资建议。历史价格行为不代表未来走势；机械信号必须结合市场环境、基本面与风险管理综合判断。任何交易决策均由使用者自行承担风险。
