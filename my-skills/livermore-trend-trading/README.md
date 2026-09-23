# 🎯 A股利弗莫尔趋势投机｜用5条纪律守住关键突破与止损

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富/新浪财经公开接口）

“大钱靠坐得住，不是靠乱动。”本技能把杰西·利弗莫尔的趋势投机纪律机械化：识别**N日新高关键点突破、放量确认、缩量回踩二次入场**，并提醒**单日反转/放量滞涨**两类危险信号；同时输出一套**金字塔加仓仓位试探框架**，让“试探仓→确认加仓→止损”有数字可依。

## 快速开始

```bash
pip install akshare pandas

# 默认：3只示例股，近250个交易日，60日突破窗口
python scripts/pivotal_points.py --codes 600519,000858,600036 --out signals.csv

# 缩短窗口，看更近期的关键突破
python scripts/pivotal_points.py --codes 600519,000858 --days 120 --window 30 --out signals.csv
```

## 参数说明

- `--codes`：逗号分隔的6位A股代码（必填）
- `--days`：取近N个交易日（默认250）
- `--window`：N日新高突破窗口（默认60）
- `--out`：CSV输出路径（默认 `livermore_signals.csv`）
- `--no-proxy`：禁用系统代理（脚本默认已自动绕过系统代理，保留兼容参数）

> 代理说明：脚本启动时自动清除 `HTTP_PROXY` / `HTTPS_PROXY` 等环境变量，避免本地代理（如 `127.0.0.1:7890`）阻断东方财富/新浪接口。优先尝试东方财富日线接口，失败自动降级新浪日线接口。

## 输出字段

| 字段 | 说明 |
|---|---|
| `code` | 6位股票代码 |
| `name` | 股票简称 |
| `date` | 信号日期 |
| `close` | 最新收盘价 |
| `close_chg_pct` | 当日涨跌幅（%） |
| `volume_ratio` | 当日成交量 / 20日均量 |
| `ma20` | 20日均线 |
| `ma60` | 60日均线 |
| `window_high` | 突破窗口内最高收盘价 |
| `dist_to_high_pct` | 现价距窗口高点幅度（%） |
| `signals` | 命中的信号，逗号分隔 |
| `position_plan` | 基于信号的金字塔仓位建议 |

## 信号含义

| 信号 | 含义 |
|---|---|
| `KEY_BREAKOUT` | 放量突破N日新高，最小阻力方向向上 |
| `WEAK_BREAKOUT` | 突破N日新高但成交量未达标，需警惕假突破 |
| `PULLBACK_ENTRY` | 多头趋势中缩量回踩MA20，二次入场候选 |
| `ONE_DAY_REVERSAL` | 单日反转：冲高回落，收盘接近低点 |
| `VOLUME_STAGNATION` | 放量滞涨：成交量放大但价格几乎没涨 |
| `NO_SIGNAL` | 未命中明确信号 |

## 配套文件

- `SKILL.md` — 技能定义与使用说明
- `scripts/pivotal_points.py` — 趋势投机信号识别脚本
- `references/livermore_rules.md` — 利弗莫尔投机原则学习整理

## 免责声明

仅供学习研究，不构成投资建议。历史价格行为不代表未来走势；机械信号必须结合市场环境、基本面与风险管理综合判断。任何交易决策均由使用者自行承担风险。
