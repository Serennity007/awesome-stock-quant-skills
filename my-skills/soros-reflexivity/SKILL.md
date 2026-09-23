---
name: soros-reflexivity
description: A股索罗斯反身性/宏观投机扫描器：在价格动量与基本面的裂缝中标记正反馈/负反馈阶段与潜在拐点 | A-share Soros reflexivity / macro speculation scanner: labels positive/negative feedback stages and potential inflection points from the gap between price momentum and fundamentals | A株ソロス反身性／マクロ投機スキャナー：価格モメンタムとファンダメンタルの乖離から正のフィードバック／負のフィードバック段階と転換点候補をマーク
author: Serennity007
license: MIT
---

# 🌀 索罗斯反身性扫描器：在价格与预期的裂缝里识别繁荣-萧条拐点

市场价格从不是基本面的“镜子”，而是参与者认知与现实相互塑造的“反身环”。本技能把索罗斯的反身性框架机械化落地到 A 股：**扫描价格动量与基本面之间的背离、成交拥挤度与趋势拐点信号，输出正反馈/负反馈阶段标注**，帮你把“价格正在自我强化还是自我毁灭”变成一张可排序的表。

> 重要：这是**分析框架，不是预测工具**。它只告诉你“哪里可能存在偏差”，不告诉你“明天会涨会跌”。

## 扫描逻辑

| 维度 | 含义 | 判定逻辑 |
|---|---|---|
| **价格动量** | 近 20/60 日涨幅 | 衡量趋势强度与方向 |
| **基本面背离** | 净利润同比增长 vs 价格动量 | 涨幅大 + 盈利下滑 → 脆弱泡沫候选；跌幅大 + 盈利改善 → 预期差候选 |
| **成交拥挤度** | 当日换手率 / 20 日均换手率 | >2 视为阶段性拥挤，加入警示标签 |
| **趋势拐点** | MACD 金叉/死叉、RSI 超买/超卖、均线排列 | 输出机械信号，不直接给出买卖建议 |
| **反身性阶段** | 综合上述信号 | 正反馈强化期 / 正反馈脆弱期 / 负反馈深化期 / 负反馈过度 / 均衡观察区 |

详细理论框架见 `references/soros_framework.md`。

## 使用方法

```bash
pip install akshare pandas

# 小样本实测
python scripts/reflexivity_scan.py --codes 600519,000858,600036 --out scan.csv

# 沪深300成分股扫描，取前30名
python scripts/reflexivity_scan.py --pool hs300 --top 30 --out scan.csv
```

参数说明：

- `--codes`：逗号分隔的股票代码，优先于 `--pool`。
- `--pool`：股票池，默认 `hs300`。
- `--top`：终端展示前 N 名（默认 20）。
- `--out`：CSV 输出路径，默认 `reflexivity_scan.csv`。
- `--no-proxy`：兼容参数，脚本已默认禁用系统代理。

## 输出字段

CSV 包含（但不限于）：

- `code`, `name`：股票代码与简称
- `close`, `change_pct`：最新收盘价、当日涨跌幅
- `ret_20`, `ret_60`：20/60 日涨跌幅
- `revenue_yoy`, `net_profit_yoy`：营业总收入 / 净利润同比增长率（%）
- `crowding_ratio`：成交拥挤度（换手率比值）
- `rsi14`, `macd_dif`, `macd_dea`, `trend_signals`：拐点信号
- `phase`：反身性阶段标注
- `divergence_type`：价格-盈利背离类型
- `reflexivity_score`：综合关注分值（越高越值得重点观察）

## 配合 AI 使用

1. 运行脚本得到候选表。
2. 对排名靠前的标的，人工追问：**“价格上涨/下跌是否会改变这家公司的基本面？”**（融资、并购、渠道、品牌、监管、信贷等）。
3. 结合 `references/soros_framework.md` 中的繁荣-萧条序列，判断当前处于哪个阶段。
4. 如果决定参与，**必须设置可证伪的止损与仓位上限**——反身性交易的本质是“快速认错”。

## 数据来源与降级

- 业绩数据来自 akshare `stock_yjbb_em`（东方财富）。
- 日线数据优先 `stock_zh_a_hist`（东方财富），失败自动降级到 `stock_zh_a_daily`（新浪财经）。
- 默认自动禁用系统代理，避免 `127.0.0.1:7890` 等本地代理阻断数据源。
- 所有 akshare 调用带 3 次指数退避重试，调用间隔 0.15 秒。

## 免责声明

本技能仅供学习研究，不构成投资建议。输出结果是反身性框架的机械扫描，不代表未来走势；任何标的都必须经过独立思考、风险承受度评估和止损纪律二次确认。
