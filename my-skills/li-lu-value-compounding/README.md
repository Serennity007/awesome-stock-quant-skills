# 🏔️ 李录价值复利｜"复利机器"六维打分器（A股）

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | 许可证：MIT | 数据源：akshare（东财/新浪公开接口）

> **"投资是对未来预测的游戏，唯一可靠的方法是研究那些长期不变的东西。"**

本技能把李录（喜马拉雅资本创始人，芒格关门弟子）的价值投资体系机械化到 A 股：长期高 ROE、复利趋势不失速、利润再投资仍能成长、现金流为真、PE/PB 历史低分位安全边际、低负债，共六维打分。脚本只负责缩小范围，"是否在你能力圈内"必须由投资者本人裁定。

## 目录结构

- `SKILL.md` — 技能定义、六维打分逻辑与使用方法
- `scripts/screen.py` — A 股价值复利打分器（CSV + 终端表格）
- `references/lilu_value_principles.md` — 李录投资思想整理：股票即所有权、市场先生、安全边际、能力圈、复利机器
- `lilu_test_result.csv` — 小样本实测输出

## 快速开始

```bash
pip install akshare pandas

# 默认股票池：沪深300，展示前 20 名
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 自定义小池测试
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `lilu_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，防限流）。

## 六维价值复利雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| 资本回报质量 | ROE 5 年均值 | 生意本身挣钱（满分 25） |
| 复利趋势 | 近 2 年 ROE − 前 3 年 ROE | 复利未失速（满分 15） |
| 再投资成长 | 净利润增速均值 | 留存收益仍生钱（满分 20） |
| 盈利含金量 | 经营现金流/净利润 | 利润为真（满分 15） |
| 安全边际 | PB 历史分位为主锚、PE 分位辅助 | 市场先生恐慌价（满分 15） |
| 财务纪律 | 最新资产负债率 | 低杠杆（满分 10） |

判定线：**≥75 价值复利候选**；**55–74 观察**；**<55 不符合框架**。

## 输出字段

- `code` / `name` / `industry`：代码 / 简称 / 行业
- `total`：综合得分（满分 100）
- `roe_quality_score` / `roe_trend_score` / `reinvest_growth_score` / `cash_score` / `margin_safety_score` / `debt_score`：各维度得分
- `roe_mean` / `roe_trend_diff` / `profit_growth_mean` / `ocf_mean` / `debt_latest`：财务原始值
- `pe_ttm` / `pb` / `pe_percentile` / `pb_percentile` / `val_years`：估值与历史分位
- `data_years` / `fin_source` / `note`：数据年数 / 来源 / 降级说明

## 数据来源与降级

东财财务指标 + 东财历史估值（PE/PB 分位）+ 新浪三大报表降级链；复利趋势维度对数据不足 4 年的次新股给中性分；脚本默认禁用系统代理，网络调用带指数退避重试。

## 免责声明

仅供学习研究，不构成投资建议。能力圈之外的得分再高也应放弃，投资决策请建立在独立研究之上。
