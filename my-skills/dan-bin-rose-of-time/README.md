# 🌹 但斌"时间的玫瑰"｜伟大企业七维打分器（A股）

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | 许可证：MIT | 数据源：akshare（东财/巨潮/腾讯公开接口）

> **"时间是最有价值的资产，我们应当与伟大企业共成长。"**

本技能把但斌（东方港湾创始人，《时间的玫瑰》作者）的伟大企业体系机械化到 A 股：长坡（营收 CAGR 成长跑道）、厚雪（高毛利率=定价权）、复利引擎（连续 5 年 ROE）、时间的玫瑰（持续分红）、盈利含金量、财务健康、成长质量，共七维打分。脚本只负责缩小范围，"这是否是一门能传给下一代的生意"必须人工定性复核。

## 目录结构

- `SKILL.md` — 技能定义、七维打分逻辑与使用方法
- `scripts/screen.py` — A 股伟大企业打分器（CSV + 终端表格）
- `references/danbin_rose_principles.md` — 但斌投资思想整理：时间的玫瑰、伟大企业标准、两条路线、买卖纪律
- `danbin_test_result.csv` — 小样本实测输出

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
- `--out`: CSV 输出路径（默认 `danbin_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，防限流）。

## 七维伟大企业雷达

| 维度 | 指标 | 说明 |
|---|---|---|
| 长坡 | 近 5 年营收 CAGR | 成长跑道（满分 15） |
| 厚雪 | 毛利率均值 | 品牌定价权（满分 20） |
| 复利引擎 | ROE 5 年均值 | 复利发动机（满分 20） |
| 时间的玫瑰 | 年化股息率（近 5 次派息跨度年化） | 分享复利（满分 15） |
| 盈利含金量 | 经营现金流/净利润 | 利润为真（满分 10） |
| 财务健康 | 最新资产负债率 | 低杠杆（满分 10） |
| 成长质量 | 净利润正增长年数 | 稳定性（满分 10） |

判定线：**≥75 伟大企业候选**；**55–74 观察**；**<55 不符合框架**。

## 输出字段

- `code` / `name` / `industry`：代码 / 简称 / 行业
- `total`：综合得分（满分 100）
- `runway_score` / `snow_score` / `roe_engine_score` / `rose_score` / `cash_score` / `debt_score` / `growth_quality_score`：各维度得分
- `rev_cagr` / `gross_mean` / `roe_mean` / `dividend_yield` / `ocf_mean` / `debt_latest` / `profit_pos_years` / `close`：原始指标
- `data_years` / `fin_source` / `note`：数据年数 / 来源 / 降级说明

## 数据来源与降级

东财财务指标 + 巨潮分红 + 腾讯快照；主接口失败自动降级新浪三大报表手工计算；股息率按近 5 次派息实际时间跨度年化，不会因特别分红虚高；脚本默认禁用系统代理，网络调用带指数退避重试。

## 免责声明

仅供学习研究，不构成投资建议。"伟大"的判定远超量化范围，筛选结果必须经过生意本质的定性复核。
