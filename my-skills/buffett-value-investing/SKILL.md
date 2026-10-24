---
name: buffett-value-investing
description: "A股巴菲特式价值投资分析：护城河评估、连续5年ROE/毛利率/负债率/经营现金流筛选、安全边际估值 | A-share Buffett-style value investing analysis: moat assessment, 5-year ROE/gross-margin/debt/operating-cash-flow screening, margin-of-safety valuation | A株バフェット式バリュー投資分析：堀評価、5年連続ROE/粗利率/負債比率/営業キャッシュフローのスクリーニング、安全マージン評価"
metadata:
  author: Serennity007
license: MIT
---

# 巴菲特式价值投资（A股）

用巴菲特的框架在 A 股市场做两件事：

1. **筛股**（`scripts/screen.py`）：从全市场或给定股票池中筛出符合巴菲特财务标准的候选标的，按打分排序。
2. **分析**（`scripts/analyze.py`）：对单个股票做完整分析，包括护城河清单（人工判断位）、财务质量趋势、简易估值区间与安全边际提示。

数据来自 akshare（公开行情与财务数据接口）。

## 执行与结果判断

先运行筛选，再读取输出 CSV 和同名 `.meta.json`。优先看 `score_status`、`decision`、`data_issues`，再看总分。`partial` / `needs_data` 表示证据不足，缺失维度不等于公司经营差，也不能凭一个较高总分直接进入候选。

- 年报日期统一解析、去除未来期末并排序；相同日期的冲突行报错。ROE、毛利率和现金流按相同年报期间对齐。仅一个毛利率观测不会获得“五年稳定”分。
- `financial_periods` 给出实际使用的报告期；`gross_years`、`cashflow_data_years` 给出有效覆盖。金融业毛利率不适用时仍显示数据不完整，转人工行业分析，不自动重标定满分。
- `valuation_date` 是估值交易日；`valuation_history_start` 与观测数显示窗口内实际覆盖。估值只用截止今天的近五年日期窗口内数据，PE 严格取 TTM 字段；少于 60 个正值观测不计算该分位。历史短于五年时只能称“窗口内可得历史分位”。
- 最新 PE、PB 或负债值无效时保持缺失，不用旧的有效值冒充当前值。分析脚本以估值同一行的收盘价和 PE 推算 EPS，不混入另一个日期的最新价格。

这些检查处理报表期末与行情日期，不恢复实际披露日或财报历史修订版本，不能把当前筛选用于严格历史时点研究。

## 筛选标准（巴菲特财务门槛）

| 维度 | 标准 | 说明 |
|---|---|---|
| ROE | 连续 5 年 > 15% | 巴菲特最看重的单一指标，代表资本回报能力 |
| 毛利率 | 5 年稳定（波动 < 5 个百分点）且 > 30% | 稳定高毛利是护城河的财务投影 |
| 资产负债率 | < 50%（金融股除外，需人工剔除） | 低杠杆意味着不依赖借钱赚钱 |
| 经营现金流 | 连续 5 年为正 | 利润必须是真金白银 |
| 估值 | PE / PB 处于近 5 年历史分位低位 | 安全边际：好公司也要好价格 |

> 注：金融、地产等高杠杆行业的负债率标准不适用，需另行人工分析。

打分规则详见 `references/scoring_rules.md`，投资原则详见 `references/buffett_principles.md`。

## 使用方法

```bash
pip install akshare pandas

# 筛股：默认用沪深300成分股作为股票池（质量预筛，避免全市场过慢）
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 或用自定义股票池
python scripts/screen.py --codes 600519,000858,600036 --out result.csv

# 单股完整分析
python scripts/analyze.py 600519
```

## 分析流程（配合 AI 使用）

1. 运行 `screen.py` 得到候选名单与各项得分。
2. 对排名靠前的股票运行 `analyze.py`，得到财务趋势与估值区间。
3. **护城河清单需要人工/AI 逐条判断**（品牌、成本优势、转换成本、网络效应），脚本只给出提示问题，不打假分。
4. 综合判断：好公司（护城河 + 财务质量）× 好价格（安全边际）→ 才进入买入候选。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过自己对生意的理解（能力圈）二次确认。
