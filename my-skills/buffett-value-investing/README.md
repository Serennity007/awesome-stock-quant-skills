# buffett-value-investing

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007（原创）。

A股巴菲特式价值投资分析技能：护城河评估、连续 5 年 ROE/毛利率/负债率/自由现金流筛选、安全边际估值。

## 目录

- `SKILL.md` — 技能定义与使用说明
- `scripts/screen.py` — 按巴菲特标准批量筛股并打分（CSV + 终端表格）
- `scripts/analyze.py` — 单股完整分析（护城河清单 + 财务趋势 + 估值区间）
- `references/buffett_principles.md` — 巴菲特核心原则要点总结
- `references/scoring_rules.md` — 打分规则与已知局限

## 快速开始

```bash
pip install akshare pandas

# 筛选（默认沪深300成分股作为股票池）
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 自定义股票池
python scripts/screen.py --codes 600519,000858,600036

# 单股分析
python scripts/analyze.py 600519
```

依赖：`akshare`、`pandas`（Python 3.9+）。

## 免责声明

仅供学习研究，不构成投资建议。打分只是初筛工具，最终决策必须建立在你对生意本身的理解之上（能力圈原则）。
