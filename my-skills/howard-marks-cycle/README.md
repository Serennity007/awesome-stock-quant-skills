# 🌡️ A股周期温度计｜霍华德·马克斯钟摆定位器

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（乐咕乐股 / 中证指数 / 东方财富公开接口）

别人贪婪时恐惧，别人恐惧时贪婪——但前提是，你得先能量出“贪婪”和“恐惧”到了哪一步。这个脚本把霍华德·马克斯的周期思想落地成一张数字化的 A 股体温表：沪深300/中证全指估值分位、股债收益差、成交热度、两融余额趋势，四合一合成 **0-100 的周期位置评分**，并给出对应行动框架。

## 快速开始

```bash
pip install akshare pandas

# 默认今天，回看 10 年
python scripts/cycle_gauge.py

# 带示例个股
python scripts/cycle_gauge.py --codes 600519,000858,600036 --out cycle_gauge.csv

# 回测历史日期
python scripts/cycle_gauge.py --date 2023-12-31 --lookback 5 --out 2023_gauge.csv
```

已验证环境：Python 3.11 + akshare 1.18.96 + pandas。

## 参数说明

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--date` | 今天 | 报告日期，支持 `20231231` 或 `2023-12-31` |
| `--lookback` | 10 | 历史分位回看年数 |
| `--codes` | — | 逗号分隔的示例个股代码，仅观察用 |
| `--out` | `cycle_gauge.csv` | CSV 输出路径 |
| `--no-proxy` | — | 兼容旧参数，脚本已默认禁用系统代理 |

> 代理说明：启动时自动清除 `HTTP_PROXY` / `HTTPS_PROXY` 等环境变量，避免本地代理（如 `127.0.0.1:7890`）阻断数据源。

## 输出字段

CSV 为长表格式，便于 AI 解析：

| category | item | value | score | note |
|---|---|---|---|---|
| GAUGE | cycle_position | 综合评分 | 0-100 | 行动建议 |
| COMPONENT | valuation / spread / turnover / margin | 当前值 | 分项得分 | 计算说明 |
| INDEX | 沪深300_PE-TTM、沪深300_PB、中证全指_PE-TTM 等 | 当前估值 | 历史分位 | — |
| SAMPLE | 个股代码+名称 | 收盘价/PE/PB | — | 示例观察 |

## 评分逻辑简述

- **估值（30%）**：沪深300 PE/PB、中证全指 PE 历史分位越高，评分越热；全市场 PB 以中证800 近似。
- **股债收益差（25%）**：中证全指盈利收益率 − 10年国债收益率，越高代表股市相对债券越便宜，评分越冷。
- **成交热度（25%）**：中证全指成交金额相对 20日/60日均线位置，放量偏热。
- **两融趋势（20%）**：全市场融资余额相对近期趋势，上行偏热。

## 配套文件

- `SKILL.md` — 技能定义与使用说明
- `scripts/cycle_gauge.py` — 周期温度计主脚本
- `references/marks_memos.md` — 霍华德·马克斯核心思想整理

## 免责声明

仅供学习研究，不构成投资建议。周期定位基于历史统计，不代表未来走势；任何评分与行动框架都必须经过自己的风险偏好与独立判断二次确认。
