---
name: master-ensemble
description: 大师共识筛选器：把多个大师 skill（buffett/danbin/lilu/canslim/neff 等任意 screen.py）的打分结果 CSV 按框架内百分位归一化后合成共识分，输出"多条独立思路同时指向"的跨框架交集标的 | Master-consensus screener: merges scoring CSVs from any master skills, percentile-normalizes within each framework, outputs cross-framework consensus stocks that multiple independent methodologies point to | マスター合意スクリーナー：複数のマスタースキルのスコアCSVをパーセンタイル正規化し、複数の独立した手法が同時に指す銘柄を出力
author: Serennity007
license: MIT
---

# 🤝 大师共识筛选器｜多条独立思路同时指向的标的

> **"如果你把几个互相独立的判断框架指向同一方向的时刻找出来，你就在给概率加权。"**

本技能是系列联动器：单一大师框架只回答"在他的体系里谁好"，而**共识筛选回答"谁被多条互相独立的思路同时看好"**。输入任意多个大师 skill 的打分结果 CSV（各 `screen.py` 的输出，要求含 `code`/`total` 列），脚本在每个框架内部做百分位归一，合成共识分与"顶级命中数"，输出跨框架交集名单。

## 为什么用框架内百分位而不是原始分

巴菲特、但斌、欧奈尔、聂夫的分数都是 0-100，但给分哲学完全不同（有的框架慷慨、有的严苛；价值框架与动量框架甚至互斥）。**直接平均原始分会被给分宽松的框架绑架**；框架内百分位把每个框架变成"相对排名的公平货币"，再合成才有意义。

## 输出指标

| 字段 | 含义 |
|---|---|
| `consensus_score` | 共识分 = 该股票在所有覆盖它的框架中百分位的均值（0-100） |
| `top_hits` | 顶级命中数 = 处于该框架前 top-pct 分位（默认前 10%）的框架个数 |
| `frameworks` | 覆盖该股票的框架个数（打分失败的框架不算"不看好"，只是缺席） |
| `<框架>_pct` / `<框架>_raw` | 该框架内的百分位 / 原始分 |

## 使用方法

```bash
# 推荐：先分别跑全量沪深300，再合成
python ../dan-bin-rose-of-time/scripts/screen.py --pool hs300 --out danbin_hs300_result.csv
python ../li-lu-value-compounding/scripts/screen.py --pool hs300 --out lilu_hs300_result.csv
python ../oneil-canslim/scripts/screen.py --pool hs300 --out canslim_hs300_result.csv

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
- `--out`: 共识结果 CSV 输出路径。

## 分析流程（配合 AI 使用）

1. **选框架组合**：同类型框架（如 danbin + lin-yuan 都是价值消费）共识≈冗余验证；跨类型框架（如 lilu 价值 + canslim 动量）共识≈多空双方都认可，信号更稀少更珍贵。
2. **跑共识**：运行 `ensemble.py`。
3. **读原则**：对照 `references/ensemble_methodology.md` 理解"框架冲突是特性"——茅台与海康不会同时高分，两种共识各有含义。
4. **人工定性**：共识分只是"多条思路指向"，不回答"思路是否都错"。仍需回到各大师的 references 文件做定性复核。

## 实测参考（2026-09-28）

4 框架小样 smoke test：贵州茅台共识 83.4（danbin 100 分位 / lilu 100 分位 / neff 66.7 / canslim 66.7，顶级命中 2）居首——3 个价值框架加 1 个动量框架中仅动量框架缺席顶级。全量沪深300 三框架共识 demo 见 `consensus_hs300_demo.csv`。

## 注意事项

- 各输入 CSV 必须来自**同一股票池**（都用 `--pool hs300`），否则"缺席"会污染共识。
- `frameworks` 计数是"覆盖数"不是"通过数"：某框架数据缺失导致的缺席会拉低共识分（均值只算覆盖的框架），但 `--min-frameworks` 过滤会把它挡在门外。
- 本脚本不做任何网络调用，纯本地 CSV 合成，秒级完成。

## 配套文件

- `references/ensemble_methodology.md` — 共识筛选方法论：百分位归一的理由、框架冲突的解读、共识的局限。

## 免责声明

本技能仅供学习研究，不构成投资建议。共识分不构成任何买入依据，历史一致不代表未来一致。
