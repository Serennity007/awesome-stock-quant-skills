---
name: framework-backtest
description: 大师框架回测验证器：月度调仓回测各大师 skill 的打分框架在 A 股的历史真实表现（等权持有前N名 vs 沪深300），时点正确（point-in-time）无未来函数，输出年化/超额/最大回撤/夏普与逐年对照表，附幸存者偏差等局限说明 | Master-framework backtest validator: monthly-rebalanced backtest of each master framework on A-shares (equal-weight top-N vs CSI 300), point-in-time scoring, CAGR/excess/maxDD/Sharpe with yearly table, documented survivorship-bias caveats | マスター框架バックテスト検証器：月次リバランスで各框架のA株実績を検証（等上位N銘柄 vs 沪深300）、時点正確、年率/超過/最大DD/シャープ
author: Serennity007
license: MIT
---

# 📊 大师框架回测验证器｜用历史数据检验大师框架在 A 股是否真的有效

> **"回测是策略的照妖镜——所有讲不出来的收益都是故事。"**

本技能把仓库里的大师框架变成**可证伪的策略**：每月末用某框架对全池打分 → 等权买入前 N 名 → 持有到下月末 → 累计净值对照沪深300。打分严格 point-in-time：只用调仓日已发布 ≥120 天的年报数据和调仓时点的估值，无未来函数。

v1 支持三个框架：**danbin**（但斌六维，分红维度剔除后 85 分重标定）、**lilu**（李录六维）、**mom12_1**（12-1 月价格动量，作为价值框架的对照基准）。

## 已知局限（读结果前必读）

| 局限 | 影响 | 方向 |
|---|---|---|
| **幸存者偏差** | 股票池固定为当前沪深300名单，"活到今天的好公司"被系统性高估，绝对收益偏乐观 | 引入历史成分股回溯可消除 |
| 无交易成本 | 月度换手 10 只，成本侵蚀约 1-2pp/年 | 可加双边 0.1% 修正 |
| PE/PB 历史 | 东财接口约自 2018 年起，早期分位窗口短 | 换乐咕/其他源 |
| 年报滞后近似 | 按 120 天假设发布（实际 1-4 月底） | 保守方向，影响小 |

**结论的正确用法：框架之间的相对比较（谁的超额高、谁的回撤小）比绝对数字可信。**

## 使用方法

```bash
pip install akshare pandas numpy

# 第一步：拉取全池历史数据缓存（约 25 分钟，可断点续传，支持 --offset/--limit 分块）
python scripts/fetch_history.py --pool hs300

# 第二步：回测（默认三框架、每月等权前 10、2021-09 起）
python scripts/backtest.py

# 自定义：只跑一个框架、前 5 名、从 2023 年开始
python scripts/backtest.py --frameworks danbin --top 5 --start 2023-01-31 --out-prefix v2
```

参数说明：

- `--frameworks`: 逗号分隔，danbin / lilu / mom12_1。
- `--start`: 首个调仓月（默认 2021-09-30）。
- `--top`: 每月等权持有前 N 名（默认 10）。
- `--min-stocks`: 缓存少于该数量报错（默认 50；子集测试时调低）。
- `--out-prefix`: 输出文件名前缀。

## 输出文件

- `results/bt_summary.csv` — 各框架年化/基准年化/超额/最大回撤/夏普汇总
- `results/bt_result_<框架>.csv` — 月度收益与净值曲线（策略 vs 基准）
- `results/bt_yearly_<框架>.csv` — 逐年收益对照表
- `cache/` — 个股历史数据缓存（估值/年度指标/利润表，.gitignore 排除，可随时删除重建）

## 打分口径

与各大师 skill 的 `screen.py` 完全同一套档位函数，仅两处 v1 简化：

1. danbin 的"时间的玫瑰"（分红）维度剔除——历史逐股分红数据获取成本高；其余六维 85 分制重标定到 100。
2. 金融业等无毛利率行业，厚雪维度给中性 8 分（与 screen.py 一致）。

## 实测结果

见 `results/bt_summary.csv` 与根 README Demo 区（2026-09-28 首次全量回测数字在回测完成后回填）。

## 配套文件

- `references/backtest_methodology.md` — 方法论：point-in-time 原则、幸存者偏差的量化影响、为什么相对比较更可信。

## 免责声明

本技能仅供学习研究，不构成投资建议。回测收益不代表未来，历史规律可能失效。
