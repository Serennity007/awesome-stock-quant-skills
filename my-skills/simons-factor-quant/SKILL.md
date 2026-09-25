---
name: simons-factor-quant
description: A股西蒙斯风格多因子量化扫描：动量/反转/低波/量能/均线偏离五维复合打分，输出综合因子排名 | A-share Simons-style multi-factor quant scanner: momentum, reversal, low-vol, volume trend, and MA deviation composite scoring with ranked output | A株サイモンズ式マルチファクター定量スキャナ：モメンタム・リバーサル・低ボラ・出来高・移動平均乖離の5次元複合スコアリング
author: Serennity007
license: MIT
---

# 🧮 西蒙斯因子量化｜5 维复合信号猎取 A 股短线统计规律

> **信号重于叙事，数据驱动决策。**

本技能以詹姆斯·西蒙斯（James Simons）与大奖章基金（Medallion Fund）的公开投资哲学为灵感，构建一个面向 A 股的**风格化多因子学习框架**。核心工具是 `scripts/factor_scan.py`：它从指定股票池中抓取日线，计算动量、反转、低波、量能、均线偏离 5 个维度的百分位得分，加权合成综合因子分并输出排名。

> ⚠️ 大奖章基金的真实策略不公开。本 skill 仅为学习整理，不构成投资建议。

## 5 维因子雷达（权重 100）

| 维度 | 西蒙斯风格解释 | 代理指标 | 权重 |
|---|---|---|---|
| 1. 动量 | 极短周期趋势延续 | 20日、60日收益率百分位 | 25 |
| 2. 反转 | 短期超跌后的均值回归 | -5日收益率百分位 | 25 |
| 3. 低波动 | 低波异象 + 控制风险 | -20日年化波动率百分位 | 20 |
| 4. 量能 | 成交量验证价格行为 | 近5日均量 / 近20日均量 | 15 |
| 5. 均线偏离度 | 偏离均线的回摆潜力 | -\|收盘价/60日均线 - 1\| 百分位 | 15 |

综合得分 = 各维度百分位得分 × 对应权重之和。每只股票的每个维度得分均在 0–100 之间，因此综合得分也在 0–100 之间。

## 使用方法

```bash
pip install akshare pandas

# 默认沪深300成分股作为股票池，输出前 20 名
python scripts/factor_scan.py --pool hs300 --top 20 --out result.csv

# 自定义小股票池验证（推荐）
python scripts/factor_scan.py --codes 600519,000858,600036 --top 10 --out result.csv

# 指定截止日期与回放眼数
python scripts/factor_scan.py --codes 600519,000858,600036 --end-date 2026-09-24 --lookback 150 --out result.csv
```

参数说明：

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义股票代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `simons_factor_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，用于防接口限流）。
- `--end-date`: 截止日期，兼容 `20231231` 与 `2023-12-31`（默认今天）。
- `--lookback`: 回放眼日历天数（默认 150，约 7 个月）。

## 输出字段

- `code / name`: 股票代码与名称
- `total`: 综合因子得分（0–100）
- `momentum_score / momentum_20_score / momentum_60_score`: 动量维度得分及 20日/60日分项
- `reversal_score`: 反转维度得分
- `volatility_score`: 低波维度得分
- `volume_score`: 量能维度得分
- `ma_deviation_score`: 均线偏离度得分
- `ret_5d / ret_20d / ret_60d`: 5日 / 20日 / 60日收益率
- `vol_20d_annual`: 20日年化波动率
- `volume_ratio_5_20`: 近5日均量 / 近20日均量
- `ma60_deviation`: 收盘价相对 60 日均线的偏离
- `close / latest_date`: 最新收盘价与日期
- `data_days`: 有效日线条数
- `source`: 数据来源（东财前复权或新浪日线降级）

## 数据来源与降级策略

- 数据来自 `akshare` 公开接口（东方财富/新浪日线行情）。
- 脚本启动时默认禁用系统代理，避免 `127.0.0.1:7890` 等本地代理阻断数据源。
- 优先使用 `stock_zh_a_hist` 获取东财前复权日线；东财失败自动降级到 `stock_zh_a_daily` 新浪日线。
- 股票名称映射优先从新浪行情 `stock_zh_a_spot` 获取。
- 沪深300成分股优先使用 `index_stock_cons_csindex`，失败降级 `index_stock_cons_weight_csindex`。
- 所有 `akshare` 调用均带 `_retry_call` 指数退避 3 次，调用间 `time.sleep(0.15)` 防限流。

## 配套文件

- `references/simons_methods.md` — 詹姆斯·西蒙斯/大奖章基金思路学习整理：数据驱动、信号重于叙事、短线均值回归、严格风控、隐藏交易足迹，并注明真实策略不公开。

## 分析流程（配合 AI 使用）

1. **跑初筛**：运行 `factor_scan.py` 得到候选名单与各项因子得分。
2. **读方法论**：对照 `references/simons_methods.md`，理解西蒙斯风格的核心原则。
3. **组合验证**：把高分股票当作一个组合，观察其动量/反转/低波/量能/均线特征是否一致。
4. **风控落地**：设置止损、仓位上限、行业敞口控制；单因子高分绝不等于必然上涨。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史行情与统计规律不代表未来表现，任何筛选结果都必须经过独立研究与风险承受能力评估。大奖章基金的真实策略不公开，本 skill 仅为风格化致敬的学习框架。
