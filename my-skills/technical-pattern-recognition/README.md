# technical-pattern-recognition

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

A股技术形态识别 Skill（Claude Code / Agent Skills 格式）：基于 akshare 新浪日线，机械式识别均线多头/空头排列、MACD 金叉死叉、放量突破 N 日新高、缩量回踩均线，输出结构化信号表供 AI 解读。

作者：Serennity007 | License：MIT | 数据：akshare（新浪日线，前复权）

## 快速开始

```bash
pip install akshare pandas
python scripts/patterns.py 600519,601318 --days 250 --window 60 --out signals.csv
```

## 信号一览

| 信号 | 含义 |
|---|---|
| `MA_BULLISH` / `MA_BEARISH` | 均线多头 / 空头排列 |
| `MACD_GOLDEN` / `MACD_DEATH` | MACD 金叉 / 死叉（近 3 日内） |
| `VOL_BREAKOUT` | 放量突破 N 日新高（量比 ≥ 1.5） |
| `PULLBACK_MA` | 多头趋势中缩量回踩 MA20 |

判定细节见 [references/patterns.md](references/patterns.md)，真实运行输出见 [docs/demo.md](docs/demo.md)。

## 免责声明

仅供学习研究，不构成投资建议。技术形态是滞后指标，任何信号都可能失效。
