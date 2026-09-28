---
name: bogle-index-investing
description: A股约翰·博格指数投资法：宽基指数PE/PB近10年分位估值温度计、博格公式预期收益三项拆解（股息率+盈利增速+估值回归）、定投档位参考、月定投vs一次性买入回测，践行"低成本、广分散、买入持有" | A-share John Bogle index investing: PE/PB 10-year percentile thermometer, Bogle's three-component expected return decomposition, DCA pacing guide, monthly DCA vs lump-sum backtest | A株ジョン・ボーグル・インデックス投資法：PE/PB10年パーセンタイル温度計、ボーグル式期待リターン3分解、積立レベル目安、月積立vs一括投資のバックテスト
author: Serennity007
license: MIT
---

# 🎯 约翰·博格指数投资法｜A股指数估值温度计 + 定投回测

> **"别把大河的涨落当作自己的智慧。Don't just do something, stand there!"**

本技能把约翰·博格（John Bogle，先锋集团创始人、指数基金之父，《共同基金常识》作者）的指数投资体系机械化到 A 股：宽基指数 PE/PB 近 10 年分位估值温度计、博格公式预期收益三项拆解、定投档位参考、以及月定投 vs 一次性买入的回测对照。博格的答案永远朴素：**低成本、广分散、按纪律买入并持有到底**——温度计只是给"要不要多投一点"的节奏参考，不是择时工具。

## 温度计规则

| 输出 | 含义 |
|---|---|
| `pe_pct_10y` / `pb_pct_10y` | 当前 PE(TTM)/PB 在近 10 年月度序列中的分位（0-100） |
| `temperature` | 以 PE 10 年分位定义的温度：越低越冷、越值得投 |
| `bogle_expected_return` | 博格公式预期年化 ≈ 股息率 + 盈利增速 + 估值回归贡献 |
| `speculative_component` | 估值回归贡献：当前 PE 向 10 年中位按 5 年回归的年均值 |
| `action` | 定投档位参考（见下表） |

定投档位参考（对博格"持有不动"原则的本土化定投增强）：

| PE 10 年分位 | 档位 |
|---|---|
| < 20% | 低温：加倍定投区 |
| 20–40% | 偏低：正常偏积极定投 |
| 40–60% | 中性：正常定投 |
| 60–80% | 偏高：减半定投 |
| ≥ 80% | 高温：暂停新买入（持仓不动） |

## 使用方法

```bash
pip install akshare pandas

# 全部支持指数的估值温度计（沪深300 / 中证500 / 上证50 / 中证1000）
python scripts/index_thermometer.py --out bogle_thermometer.csv

# 单个指数 + 近 5 年月定投回测
python scripts/index_thermometer.py --index 沪深300 --dca --years 5 --out result.csv

# 校准假设参数：股息率 2.5%、长期盈利增速 5%（默认值）
python scripts/index_thermometer.py --div 3.0 --growth 6.0
```

参数说明：

- `--index`: 指数名（沪深300/中证500/上证50/中证1000），默认分析全部。
- `--div`: 假设的指数长期股息率 %（默认 2.5）。
- `--growth`: 假设的长期盈利增速 %（默认 5.0）。
- `--dca`: 附带近 N 年月定投回测。
- `--years`: 定投回测年数（默认 5）。
- `--out`: CSV 输出路径（默认 `bogle_thermometer.csv`）。

## 输出字段速览

| 字段 | 含义 |
|---|---|
| `index` / `tx_symbol` | 指数名 / 行情代码 |
| `pe_ttm` / `pe_pct_10y` / `pe_pct_all` / `pe_median_10y` / `pe_hist_years` | 当前 PE 与分位（10年/全历史）、10年中位、历史跨度 |
| `pb` / `pb_pct_10y` | 当前 PB 与 10 年分位 |
| `temperature` / `action` | 温度（0-100）与定投档位参考 |
| `bogle_expected_return` / `speculative_component` | 博格公式预期年化 / 估值回归贡献 |
| `index_close` / `dca_*` / `lumpsum_annualized` / `period_max_drawdown` | 回测输出：点位、定投投入与终值、总收益、年化、一次性年化、区间最大回撤 |

## 定投回测口径

- 按**月末收盘**等额定投（默认每月 1000 元，不含交易成本与成分股分红再投）。
- 对照组：期初一次性买入持有同期限。
- 输出两条路径的年化与指数区间最大回撤——博格用它说明"长期持有未必输给定投，定投的意义在于纪律与平滑现金流"。

## 分析流程（配合 AI 使用）

1. **跑温度计**：运行 `index_thermometer.py` 看各宽基的估值分位与档位。
2. **读原则**：对照 `references/bogle_principles.md`，用"成本、分散、纪律"三把尺子复核自己的基金选择。
3. **校准假设**：`--div` 与 `--growth` 是博格公式中两个假设项，可用指数历史股息率与盈利增速自行校准。
4. **执行纪律**：温度计改变的是"投入节奏"，不改变"是否持有"。高估暂停新买入但不清仓——这正是博格"stand there"的意思。

## 实测参考（2026-09-28）

沪深300 PE 12.59（10 年分位 60%，中性偏热）、上证50 PE 10.64（58.3%）、中证500 PE 26.51（78.3%，减半档）、中证1000 PE 29.74（70%）；近 5 年月定投沪深300 年化 1.81% vs 一次性买入 -1.79%——定投在震荡下行市中平滑成本的典型场景。实测见 `bogle_test_result.csv`。

## 数据来源与降级策略

- 估值历史来自乐咕乐股接口（2005 年至今的月度 PE/PB 序列），行情历史来自新浪指数日线、腾讯降级。
- 脚本启动时默认禁用系统代理；所有网络调用带 3 次指数退避重试。
- 乐咕接口未收录的指数（如创业板指）自动跳过并在 stderr 提示。

## 配套文件

- `references/bogle_principles.md` — 博格核心投资思想：成本、分散、纪律与"股票的长期收益来源"。

## 免责声明

本技能仅供学习研究，不构成投资建议。股息率与盈利增速为假设参数，估值分位不预示未来收益。投资决策应建立在独立研究与自身风险承受能力之上。
