---
name: technical-pattern-recognition
description: A股技术形态识别：均线多头/空头排列、MACD金叉死叉、放量突破N日新高、缩量回踩均线，输出信号表 | A-share technical pattern recognition: MA bullish/bearish alignment, MACD golden/death cross, volume-breakout to N-day high, low-volume pullback to MA, outputs a signal table | A株テクニカルパターン認識：移動平均線のパーフェクトオーダー/逆オーダー、MACDゴールデン/デッドクロス、出来高を伴うN日高値ブレイク、出来高減少の押し目、シグナル表を出力
author: Serennity007
license: MIT
---

# A股技术形态识别（technical-pattern-recognition）

基于 akshare 新浪日线数据，对 A 股个股做常见技术形态的**机械式识别**，输出结构化信号表，供 AI 进一步解读。本技能只做形态识别，不做收益预测。

## 识别的形态

| 信号 | 含义 | 判定逻辑（默认参数） |
|---|---|---|
| `MA_BULLISH` | 均线多头排列 | MA5 > MA10 > MA20 > MA60 |
| `MA_BEARISH` | 均线空头排列 | MA5 < MA10 < MA20 < MA60 |
| `MACD_GOLDEN` | MACD 金叉 | DIF 上穿 DEA（近 3 日内发生） |
| `MACD_DEATH` | MACD 死叉 | DIF 下穿 DEA（近 3 日内发生） |
| `VOL_BREAKOUT` | 放量突破 N 日新高 | 收盘价创 N 日（默认 60）新高，且成交量 ≥ 20 日均量 × 1.5 |
| `PULLBACK_MA` | 缩量回踩均线 | 股价回踩至 MA20 ±2% 区间，且当日成交量 ≤ 20 日均量 × 0.8，且大方向为多头排列 |

详细说明见 `references/patterns.md`。

## 使用方法

```bash
pip install akshare pandas

# 单只股票识别（默认取近 250 个交易日）
python scripts/patterns.py 600519

# 多只股票 + 自定义突破窗口与输出
python scripts/patterns.py 600519,000858 --days 250 --window 60 --out signals.csv
```

## 分析流程（配合 AI 使用）

1. 运行 `patterns.py` 得到每只股票当前命中的信号与关键指标（均线、MACD、量比、距新高幅度）。
2. AI 结合信号组合做解读（例如 `MA_BULLISH + PULLBACK_MA` 是趋势中的回调买点候选；`VOL_BREAKOUT` 后需观察是否假突破）。
3. 形态信号是**滞后指标**，必须与基本面、市场环境结合，不可单独作为交易依据。

## 免责声明

本技能仅供学习研究，不构成投资建议。技术形态基于历史价格统计，不代表未来走势；任何信号都可能失效或出现假突破。
