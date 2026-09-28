# 🚀 威廉·欧奈尔 CANSLIM｜七要素逐项体检（A股）

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | 许可证：MIT | 数据源：akshare（新浪/东财公开接口）

> **"历史上的大牛股，在暴涨之前都有可以识别的共同特征。"**

本技能把威廉·欧奈尔（《笑傲股市》作者）的 CANSLIM 七要素机械化到 A 股：C（当季收益 ≥25%）、A（年度增长）、N（距 250 日新高）、S（量能）、L（相对强度超额）、I（机构持股）、M（大盘 50 日线趋势），逐字母输出通过表与得分（满分 100），池模式下附带 RPS 百分位。与价值类 skill 互补——茅台在本框架下低分是特性不是 bug。

## 目录结构

- `SKILL.md` — 技能定义、七要素打分逻辑与使用方法
- `scripts/screen.py` — A 股 CANSLIM 打分器（CSV + 终端表格）
- `references/oneil_canslim_rules.md` — 欧奈尔投资思想整理：七要素详解、带柄杯形态、买卖纪律与 7% 止损铁律
- `canslim_test_result.csv` — 小样本实测输出

## 快速开始

```bash
pip install akshare pandas

# 默认股票池：沪深300，展示前 20 名（附带 RPS 百分位）
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 自定义小池测试
python scripts/screen.py --codes 600519,300760,002415 --out result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `canslim_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，防限流）。

## 七要素打分表

| 字母 | 量化标准 | 权重 |
|---|---|---|
| C | 最新报告期净利润同比 ≥25% 满分 | 20 |
| A | 近 3 年净利润增速均值 ≥25% 满分 | 15 |
| N | 收盘价距 250 日新高 ≤15% 满分 | 15 |
| S | 近 5 日均量/60 日均量 ≥1.5 满分 | 10 |
| L | 120 日涨幅相对沪深300超额 ≥30pp 满分 | 20 |
| I | 机构持股占流通股比例 ≥10% 满分；无数据给中性 5 分 | 10 |
| M | 沪深300 收盘 > 50 日均线（失败全池扣分） | 10 |

判定线：**≥70 且 C/A/N/L 四项成立 → CANSLIM 候选**；**50–69 观察**；**<50 不符合**。

## 输出字段

- `code` / `name` / `industry` / `total` / `passed_letters`：基本信息与逐字母通过表
- `C_score` / `A_score` / `N_score` / `S_score` / `L_score` / `I_score` / `M_score`：各字母得分
- `quarter_yoy` / `annual_growth_3y` / `dist_from_250d_high` / `vol_ratio_5_60` / `excess_ret_120d` / `inst_hold_ratio`：原始指标
- `rps_percentile`：池内 RPS 百分位（仅池模式）
- `close` / `a_source` / `note` / `data_date`：辅助信息

## 数据来源与降级

新浪个股日线（前复权）+ 东财业绩报表（季同比，池级一次调用）+ 东财机构持股（无数据给中性分）+ 新浪指数日线（M 维度）；年度增长维度失败时降级新浪利润表现算；脚本默认禁用系统代理，网络调用带指数退避重试。

## 免责声明

仅供学习研究，不构成投资建议。CANSLIM 是高换手成长动量体系，历史形态不代表未来。
