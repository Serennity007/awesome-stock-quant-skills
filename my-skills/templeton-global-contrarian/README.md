# templeton-global-contrarian

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007（原创）。

A股邓普顿全球逆向投资扫描技能：在“极度悲观”中筛选股价近 52 周低位、PE/PB 历史 10% 分位以下、成交极度萎缩后企稳、盈利仍为正的逆向买入观察清单。

## 目录

- `SKILL.md` — 技能定义与使用说明
- `scripts/contrarian_scan.py` — 批量扫描邓普顿式逆向买入信号（CSV + 终端表格）
- `references/templeton_rules.md` — 邓普顿极度悲观原则、16 条投资法则、全球视野与周期观

## 快速开始

```bash
pip install akshare pandas

# 筛选（默认沪深300成分股作为股票池）
python scripts/contrarian_scan.py --pool hs300 --top 20 --out result.csv

# 自定义股票池
python scripts/contrarian_scan.py --codes 600519,000858,600036 --out result.csv
```

依赖：`akshare` 1.18.96、`pandas`（Python 3.11+）。

## 免责声明

仅供学习研究，不构成投资建议。筛选结果只是观察清单，最终决策必须建立在你对生意、行业周期与资产负债表的独立研究之上（能力圈原则）。
