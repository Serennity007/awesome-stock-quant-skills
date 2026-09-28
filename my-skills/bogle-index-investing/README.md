# 🎯 约翰·博格指数投资法｜A股指数估值温度计 + 定投回测

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | 许可证：MIT | 数据源：akshare（乐咕乐股/新浪/腾讯公开接口）

> **"别把大河的涨落当作自己的智慧。Don't just do something, stand there!"**

本技能把指数基金之父约翰·博格的体系机械化到 A 股：宽基指数 PE/PB 近 10 年分位估值温度计、博格公式预期收益三项拆解（股息率+盈利增速+估值回归）、定投档位参考、月定投 vs 一次性买入回测。支持沪深300 / 中证500 / 上证50 / 中证1000。

## 目录结构

- `SKILL.md` — 技能定义、温度计规则与使用方法
- `scripts/index_thermometer.py` — 指数估值温度计 + 定投回测（CSV + 终端表格）
- `references/bogle_principles.md` — 博格投资思想整理：成本、分散、纪律、博格公式、均值回归
- `bogle_test_result.csv` — 全指数实测输出（含定投回测）

## 快速开始

```bash
pip install akshare pandas

# 全部指数估值温度计
python scripts/index_thermometer.py --out bogle_thermometer.csv

# 单指数 + 近5年月定投回测
python scripts/index_thermometer.py --index 沪深300 --dca --years 5 --out result.csv

# 校准博格公式假设参数（股息率/盈利增速）
python scripts/index_thermometer.py --div 3.0 --growth 6.0
```

## 参数说明

- `--index`: 指数名，默认全部。
- `--div` / `--growth`: 博格公式中的股息率与盈利增速假设（默认 2.5% / 5.0%）。
- `--dca`: 附带定投回测；`--years`: 回测年数（默认 5）。
- `--out`: CSV 输出路径。

## 定投档位参考

| PE 10 年分位 | 档位 |
|---|---|
| < 20% | 低温：加倍定投区 |
| 20–40% | 偏低：正常偏积极 |
| 40–60% | 中性：正常定投 |
| 60–80% | 偏高：减半定投 |
| ≥ 80% | 高温：暂停新买入（持仓不动） |

## 输出字段

- `pe_ttm` / `pe_pct_10y` / `pe_pct_all` / `pe_median_10y`：当前 PE 与历史分位
- `pb` / `pb_pct_10y`：PB 与分位
- `temperature` / `action`：温度与档位
- `bogle_expected_return` / `speculative_component`：预期年化拆解
- `dca_annualized` / `lumpsum_annualized` / `period_max_drawdown`：定投与一次性回测

## 免责声明

仅供学习研究，不构成投资建议。股息率与盈利增速为假设参数，估值分位不预示未来收益。
