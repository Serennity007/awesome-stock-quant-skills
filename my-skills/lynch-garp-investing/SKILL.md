---
name: lynch-garp-investing
description: A股彼得·林奇GARP十倍股筛选器：PEG、连续盈利增长、低负债率、林奇六分类标签 | A-share Peter Lynch GARP/ten-bagger screener: PEG, continuous profit growth, low debt, six Lynch category labels | A株ピーター・リンチGARP/テンバガー選別：PEG、連続利益成長、低負債率、リンチ6分類タグ
author: Serennity007
license: MIT
---

# 🚀 彼得·林奇 GARP / 十倍股 A 股初筛器

彼得·林奇说："十倍股往往藏在人们眼皮底下。" 本技能把林奇的 GARP（Growth at a Reasonable Price，合理价格成长）框架机械化落地到 A 股：

1. **筛股**（`scripts/screen.py`）：从沪深300或自定义股票池中筛选 PEG 合理、连续盈利增长、负债率低、ROE 稳定的标的，并按林奇六分类打标签。
2. **方法论**（`references/lynch_principles.md`）：十倍股特征、身边选股法、六类公司应对策略、避坑清单。

数据来自 akshare 公开接口（东方财富为主，失败时自动降级到同花顺/腾讯）。

## 筛选逻辑

| 维度 | 标准 | 说明 |
|---|---|---|
| PEG | < 1 为优，< 1.5 可接受 | PE(TTM) / 盈利增速；增速为负时改用 5 年均值给出参考 PEG |
| 连续盈利增长 | 最近 N 年净利润同比增长 > 0 的连续年数 | 林奇偏爱"可预测的持续增长" |
| 负债率 | < 60%（默认），越低越好 | 高杠杆企业抗风险能力弱 |
| ROE | 近 5 年稳定且 > 10% | 资本回报质量 |
| 林奇六分类 | 缓慢增长 / 稳定增长 / 快速增长 / 周期 / 困境反转 / 隐蔽资产 | 机械标签，用于决定后续研究重点 |

> 打分规则详见脚本内 `score_row()`，满分 100；`garp_pass=1` 表示同时满足 PEG<1、连续盈利增长≥2年、负债率<阈值。

## 使用方法

```bash
pip install akshare pandas

# 默认沪深300池，输出前 20 名
python scripts/screen.py --pool hs300 --top 20 --out garp_result.csv

# 自定义小样本
python scripts/screen.py --codes 600519,000858,600036 --out garp_result.csv
```

参数说明：

- `--pool`: 股票池，目前仅 `hs300`
- `--codes`: 逗号分隔代码，优先于 `--pool`
- `--top`: 终端展示数量（默认 20）
- `--out`: CSV 输出路径（默认 `garp_result.csv`）
- `--max-debt`: 负债率阈值（默认 60%），仅影响 `garp_pass` 标记
- `--sleep`: 每只股票请求间隔（默认 0.3 秒，防限流）

## 输出字段速览

| 字段 | 含义 |
|---|---|
| `code` / `name` | 股票代码 / 简称 |
| `score` | GARP 综合得分 |
| `lynch_tag` | 林奇六分类标签 |
| `garp_pass` | 是否通过 GARP 硬门槛 |
| `peg` | 计算 PEG（增速为负时可能基于 5 年均值） |
| `pe_ttm` / `pb` | 当前估值 |
| `avg_profit_growth` | 近 5 年净利润增速均值 |
| `consecutive_profit_years` | 连续盈利增长年数 |
| `debt_ratio` / `roe_latest` | 负债率 / 最新 ROE |
| `industry` | 所处行业 |
| `peg_note` | PEG 计算备注 |

## 分析流程（配合 AI 使用）

1. 运行 `screen.py` 得到候选名单与林奇标签。
2. 对 `garp_pass=1` 或 `lynch_tag='快速增长'` 的标的，人工阅读年报与业务描述，验证增长来源（订单、产能、市占率）。
3. 对 `周期` / `困境反转` / `隐蔽资产` 类股票，重点核对行业拐点、资产负债表、隐蔽资产可变现性。
4. 结合 `references/lynch_principles.md` 排除"热门股"和"多元恶化"陷阱。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过自己对生意的理解（能力圈）二次确认。林奇六分类为机械化标签，实际定性判断需人工完成。
