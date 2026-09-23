# 🚀 彼得·林奇 GARP / 十倍股 A 股初筛器｜用林奇的眼光逛超市选股

**[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)**

作者：Serennity007 | License：MIT | 数据：akshare（东方财富/同花顺/腾讯公开接口）

彼得·林奇在《彼得·林奇的成功投资》里把选股变成逛超市：从身边熟悉的产品、服务和品牌出发，找到"合理价格成长"（GARP）的好公司。本技能把这套思路做成 A 股机械化初筛器：自动计算 PEG、连续盈利增长、负债率、ROE 稳定性，并按林奇六分类（缓慢增长/稳定增长/快速增长/周期/困境反转/隐蔽资产）打标签，输出一张可直接交给 AI 深度分析的结构化表格。

## 快速开始

```bash
pip install akshare pandas

# 默认沪深300成分股池，取前 20 名
python scripts/screen.py --pool hs300 --top 20 --out garp_result.csv

# 自定义股票池（适合快速验证）
python scripts/screen.py --codes 600519,000858,600036 --out garp_result.csv
```

## 筛选标准

| 维度 | 优秀 | 可接受 | 说明 |
|---|---|---|---|
| PEG | < 1.0 | < 1.5 | PE(TTM) / 盈利增速；增速为负时改用 5 年均值给出参考 PEG |
| 连续盈利增长 | ≥ 3 年 | ≥ 2 年 | 最近 N 年净利润同比增长连续为正 |
| 负债率 | < 40% | < 60% | 默认 `--max-debt 60`；银行股等杠杆行业需单独判断 |
| ROE | > 15% | > 10% | 近 5 年相对稳定 |
| 林奇标签 | 快速增长 / 稳定增长 | 隐蔽资产 / 困境反转 | 周期股和缓慢增长股谨慎对待 |

## 输出字段

| 字段 | 说明 |
|---|---|
| `code` / `name` | 股票代码 / 简称 |
| `score` | GARP 综合得分（满分 100） |
| `lynch_tag` | 林奇六分类标签 |
| `garp_pass` | 是否满足 PEG<1、连续盈利增长≥2年、负债率<阈值 |
| `peg` / `peg_note` | 计算 PEG 与备注 |
| `pe_ttm` / `pb` | 当前 PE(TTM)、市净率 |
| `avg_profit_growth` | 近 5 年净利润增速均值 |
| `consecutive_profit_years` | 连续盈利增长年数 |
| `debt_ratio` / `roe_latest` | 负债率 / 最新 ROE |
| `industry` | 所处行业 |

## 配套文件

- `SKILL.md` — 技能定义与使用说明
- `scripts/screen.py` — GARP 筛选脚本
- `references/lynch_principles.md` — 林奇十倍股方法论整理

## 免责声明

仅供学习研究，不构成投资建议。历史财务指标不代表未来表现；林奇六分类为机械化标签，实际决策必须结合业务理解、行业周期与风险偏好二次确认。
