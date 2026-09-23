# 🧠 芒格优质企业投资法｜5 维雷达锁定 A 股“伟大公司”

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富/新浪公开接口）

> **以公允价格买伟大公司，胜过以便宜价格买普通公司。**

本技能把查理·芒格的质量投资框架搬到 A 股市场：不追热点、不猜K线，只用 5 把财务尺子连续扫描企业质量，找出具备“伟大公司”特征的候选标的，再交给定性分析（护城河、管理层、能力圈）做最终判断。

## 文件清单

- `SKILL.md` — 技能定义、5 维打分逻辑与使用说明
- `scripts/screen.py` — A 股质量初筛脚本（CSV + 终端表格）
- `references/munger_checklist.md` — 芒格多元思维模型、反向思考、能力圈、人类误判心理学 25 倾向、投资检查清单

## 快速开始

```bash
pip install akshare pandas

# 默认沪深300成分股作为股票池，输出前 20 名
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 自定义小股票池验证
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

## 参数说明

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `munger_screen_result.csv`）。

## 5 维打分雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| 资本回报 | 连续 5 年 ROIC 风格指标 | 以 ROE 代理（akshare 公开接口未直接提供 ROIC） |
| 毛利率 | 5 年均值与稳定性 | 均值 >40%、波动 <3pp 为最佳 |
| 低负债 | 最新资产负债率 | <30% 得满分；金融企业需单独判断 |
| 盈利质量 | 经营现金流 / 净利润比 | 均值 >1.0 说明利润有现金支撑 |
| 少股本稀释 | 近 5 年总股本增长 | <5% 得满分；警惕频繁定增摊薄 |

## 输出字段

- `code`：股票代码
- `total`：综合得分（满分 100）
- `roic_score / roic_annual`：资本回报得分 / 近 5 年 ROE 序列
- `gross_score / gross_mean / gross_annual`：毛利率得分 / 均值 / 序列
- `debt_score / debt_latest`：负债得分 / 最新负债率
- `quality_score / quality_mean`：盈利质量得分 / 现金流净利比均值
- `dilution_score / shares_growth_pct`：股本稀释得分 / 股本增长率
- `data_years`：有效年度数
- `source / note`：数据来源与降级说明

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现；任何筛选结果都必须经过你对生意的理解（能力圈）二次确认。
