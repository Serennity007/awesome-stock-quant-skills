---
name: feng-liu-weak-side
description: A股冯柳弱者体系/逆向投资扫描器：大跌后的高赔率标的，基本面未崩+估值历史低位+低关注度，输出赔率/概率逆向观察清单 | A-share Feng Liu "weak-side" contrarian screener: high-odds candidates after deep drawdowns, intact fundamentals, low valuation percentile, and low attention | A株馮柳「弱者体系」逆張りスクリーナー：大幅下落後の高利ざや候補、崩れぬファンダメンタルズ、低バリュエーション、低関心度
author: Serennity007
license: MIT
---

# 🥊 冯柳弱者体系｜跌出来的赔率：4 个指标逆向打捞 A 股“没人要”的标的

> **假设自己是市场上最弱的信息接收者，赔率优先、逆向买入、集中但认错快。**

本技能把高毅资产冯柳的“弱者体系”机械化落地到 A 股：不追热点、不拼消息，只看“跌透了但还没死”的标的。核心工具是 `scripts/screen.py`——它从全市场或指定股票池中，按“跌幅、估值、基本面、关注度”四维打分，输出带“赔率 / 概率”标签的逆向观察清单，供你进一步验证是否属于可纠错的错杀。

## 弱者视角 4 维雷达（满分 100）

| 维度 | 核心问题 | 代理指标 | 权重 |
|---|---|---|---|
| 1. 赔率（跌幅） | 股价是否已经跌出足够空间？ | 距 52 周高点回撤幅度 | 30 |
| 2. 赔率（估值） | 估值是否打到自身历史低位？ | PE/PB 近 3 年百分位 | 25 |
| 3. 概率（基本面） | 公司是否还活着、还能赚钱？ | 净利润为正、营收/利润未大幅下滑、ROE/负债可控 | 25 |
| 4. 低关注度 | 市场是否已经把它遗忘？ | 换手率（%） | 20 |

> 注：`akshare` 公开接口下，52 周高点优先用新浪日线 `high` 计算；估值百分位用东方财富历史估值序列；东财不可达时自动降级到同花顺/新浪快照。

## 使用方法

```bash
pip install akshare pandas

# 默认用沪深300成分股作为股票池（弱者预筛，避免全市场过慢）
python scripts/screen.py --pool hs300 --top 20 --out weak_side_result.csv

# 或用自定义股票池（推荐先小样本验证）
python scripts/screen.py --codes 600519,000858,600036 --out weak_side_result.csv
```

参数说明：

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义股票代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `weak_side_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，用于防接口限流）。

## 输出字段速览

- `code` / `name` / `industry`：代码 / 简称 / 行业
- `close` / `high_52w` / `drawdown_pct`：现价 / 52 周高点 / 回撤幅度
- `pe_ttm` / `pb`：当前估值
- `pe_percentile_3y` / `pb_percentile_3y`：近 3 年估值百分位（越小越便宜）
- `turnover_pct`：最新换手率（%）
- `latest_revenue` / `latest_profit` / `revenue_yoy` / `profit_yoy`：最新报告期营收/利润（亿元）及同比增速
- `avg_rev_growth_5y` / `avg_profit_growth_5y` / `avg_roe_5y` / `latest_debt`：5 年平均增速/ROE、最新负债率
- `weak_score`：弱者体系综合得分
- `odds_label` / `probability_label`：赔率标签 / 概率标签
- `framework_note`：赔率与概率来源说明
- `weak_pass`：是否通过硬门槛（回撤 > 40% + 盈利为正 + 营收未大幅下滑）

## 分析流程（配合 AI 使用）

1. **跑初筛**：运行 `screen.py` 得到候选名单与“赔率 / 概率”标签。
2. **读清单**：对照 `references/feng_liu_framework.md`，判断每个候选是否属于“可纠错的错杀”，而非“基本面永久恶化”的价值陷阱。
3. **验证拐点**：对 `weak_pass=1` 或 `weak_score>=70` 的标的，跟踪行业数据、公司订单/库存/价格/政策等可验证信号。
4. **集中+快认错**：在能力圈内、赔率清晰时下注；若核心假设被证伪，立即离场，不补仓幻想。

## 数据来源与降级策略

- 数据来自 `akshare` 公开接口（东方财富估值/财务、同花顺/新浪行情）。
- 脚本启动时默认禁用系统代理，避免 `127.0.0.1:7890` 等本地代理阻断数据源。
- 52 周高点回撤优先用新浪日线计算；估值百分位优先用东财 `stock_value_em`；若东财失败，自动使用同花顺快照当前 PE/PB，并在 `val_source` 标注。
- 所有网络调用均带 3 次指数退避重试，调用间 `time.sleep(0.15)` 防限流。

## 配套文件

- `references/feng_liu_framework.md` — 弱者体系核心思想：弱者假设、赔率优先、逆向买入、集中持仓、认错要快、价值陷阱辨析。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过自己对生意的理解（能力圈）二次确认。逆向投资面临价值陷阱、流动性、行业长期衰退等风险，投资决策应建立在独立研究、充分安全边际与自身风险承受能力之上。
