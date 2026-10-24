---
name: master-ensemble
description: "合成多个 A 股框架的打分 CSV，校验股票代码、分数、框架名称和股票池，以框架内百分位生成共识排名，并输出输入哈希与参数记录。用于跨框架比较与筛选，不把共识分解释为胜率。"
metadata:
  author: Serennity007
license: MIT
---

# 🤝 大师共识筛选器｜多个研究框架同时指向的标的

> **"如果你把几个不同判断框架指向同一方向的时刻找出来，可以更清楚地比较框架共性与分歧。"**

本技能是系列联动器：单一大师框架只回答"在他的体系里谁好"，而**共识筛选回答"谁被多个研究框架同时给出较高排名"**。输入任意多个大师 skill 的打分结果 CSV（各 `screen.py` 的输出，要求含 `code`/`total` 列），脚本在每个框架内部做百分位归一，合成共识分与"顶级命中数"，输出跨框架交集名单。

## 为什么用框架内百分位而不是原始分

巴菲特、但斌、欧奈尔、聂夫的分数都是 0-100，但给分哲学完全不同（有的框架慷慨、有的严苛；价值框架与动量框架甚至互斥）。**直接平均原始分会被给分宽松的框架绑架**；框架内百分位把每个框架变成"相对排名的公平货币"，再合成才有意义。

## 输出指标

| 字段 | 含义 |
|---|---|
| `consensus_score` | 共识分 = 该股票在所有覆盖它的框架中百分位的均值（0-100） |
| `top_hits` | 顶级命中数 = 处于该框架前 top-pct 分位（默认前 10%）的框架个数 |
| `frameworks` | 覆盖该股票的框架个数（默认要求同池；显式允许部分池时仅计算实际覆盖） |
| `<框架>_pct` / `<框架>_raw` | 该框架内的百分位 / 原始分 |

## 使用方法

```bash
# 推荐：先分别跑全量沪深300，再合成
python ../dan-bin-rose-of-time/scripts/screen.py --pool hs300 --out ../dan-bin-rose-of-time/danbin_hs300_result.csv
python ../li-lu-value-compounding/scripts/screen.py --pool hs300 --out ../li-lu-value-compounding/lilu_hs300_result.csv
python ../oneil-canslim/scripts/screen.py --pool hs300 --out ../oneil-canslim/canslim_hs300_result.csv

python scripts/ensemble.py \
    --csvs ../dan-bin-rose-of-time/danbin_hs300_result.csv \
           ../li-lu-value-compounding/lilu_hs300_result.csv \
           ../oneil-canslim/canslim_hs300_result.csv \
    --min-frameworks 2 --out consensus.csv
```

参数说明：

- `--csvs`: 至少 2 个大师结果 CSV；文件名（去 `_result`/`_test_result`/`_hs300_result` 等后缀）作为框架名。
- `--top-pct`: 单框架"顶级命中"分位线（默认前 10%）。
- `--min-frameworks`: 至少被几个框架覆盖才输出（默认 2）。
- `--out`: 共识结果 CSV 输出路径；同时写入 `<输出>.meta.json`，记录输入 SHA-256、运行时间、参数与 pandas 版本。
- `--as-of YYYY-MM-DD`: 用户声明的数据日期，不自动验证；未提供时记录为 null。
- `--allow-partial-pools`: 显式允许股票池不同，输出警告并记录 `pools_match=false`；需自行判断不同总体的排名能否比较。

## 分析流程（配合 AI 使用）

1. **选框架组合**：同类型框架（如 danbin + lin-yuan 都是价值消费）共识≈冗余验证；跨类型框架（如 lilu 价值 + canslim 动量）共识表示两类规则在本次截面上交集，信息增量需要另行检验。
2. **跑共识**：运行 `ensemble.py`。
3. **读原则**：对照 `references/ensemble_methodology.md` 理解"框架冲突是特性"——茅台与海康不会同时高分，两种共识各有含义。
4. **人工定性**：共识分只是"多条思路指向"，不回答"思路是否都错"。仍需回到各大师的 references 文件做定性复核。

## 实测参考（2026-09-28）

4 框架小样 smoke test：贵州茅台共识 83.4（danbin 100 分位 / lilu 100 分位 / neff 66.7 / canslim 66.7，顶级命中 2）居首——3 个价值框架加 1 个动量框架中仅动量框架缺席顶级。全量沪深300 三框架共识 demo 见 `consensus_hs300_demo.csv`。

## 注意事项

- 默认要求各输入 CSV 的代码集合相同；不能通过文件名证明同池同日。请另核对数据日期；仅在确实需要比较部分池时开启 `--allow-partial-pools`。
- `frameworks` 是覆盖数，不是通过数；均值只算覆盖框架，缺席不会自动降低均值。
- 缺列、空表、重复代码、无效代码、非有限分数、框架重名及不合法参数直接报错，不静默跳过。
- 输入包含 `score_status` 时，只接受全部为 `complete` 的结果；`partial` 财务评分不能作为完整共识票。先解决数据问题；若人工选择子集，需明确股票池变化并重新对齐所有框架。
- 百分位使用平均秩 `rank(method="average", pct=True)`。默认顶级命中判定为百分位 ≥90；小样本与并列分数下不保证恰好 10% 命中，阈值判定在显示四舍五入之前完成。
- 不同框架可能共享 ROE、毛利率和数据源，不能把高共识解读为统计独立或收益概率。
- 本脚本不做任何网络调用，纯本地 CSV 合成，秒级完成。

## 配套文件

- `references/ensemble_methodology.md` — 共识筛选方法论：百分位归一的理由、框架冲突的解读、共识的局限。

## 免责声明

本技能仅供学习研究，不构成投资建议。共识分不构成任何买入依据，历史一致不代表未来一致。
