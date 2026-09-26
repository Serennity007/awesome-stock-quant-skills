---
name: lin-yuan-monopoly-consumer
description: A股林园垄断+成瘾性消费投资法：只投嘴巴相关的刚需龙头、毛利率>50%、ROE高位、分红高、申万行业过滤+成瘾行业白名单多维打分 | A-share Lin Yuan-style monopoly + addictive consumer investing: mouth-related necessities, gross margin >50%, high ROE, high dividends, SW industry filter + addictive-industry whitelist scoring | A株林園式独占+依存性消費投資：口元関連の必需品、粗利率50%超、高ROE、高配当、申万業種フィルタ+依存業界ホワイトリスト採点
author: Serennity007
license: MIT
---

# 🍶 林园垄断+成瘾性消费投资法｜4 大铁律锁定“嘴巴上的刚需龙头”

> **“我只投与嘴巴相关的、成瘾的、垄断的、毛利率唯一不骗人的公司。”——林园**

本技能把林园公开访谈/演讲中反复提及的投资框架，在 A 股市场做**机械化初筛**：不追热点、不猜情绪，只看“嘴巴相关刚需 + 垄断定价权 + 高且稳定毛利率 + 高分红”四大硬指标。核心工具是 `scripts/screen.py`——它从沪深300或自定义股票池中，按林园式规则打分排序，输出结构化 CSV，供你进一步做护城河与估值定性分析。

## 4 大筛选铁律（满分 100）

| 维度 | 林园原话 | 代理指标 | 权重 |
|---|---|---|---|
| 1. 垄断定价权 | “毛利率是唯一不骗人的指标” | 近 5 年毛利率均值 >50%，且波动小 | 30 |
| 2. ROE 持续高位 | “买了就不卖，企业一直赚钱” | 连续 5 年 ROE ≥15% 的年数与均值 | 25 |
| 3. 股东回报 | “分红率要高，老板舍得给” | 近 12 个月股息率 + 近 5 年分红持续性 | 20 |
| 4. 成瘾/刚需行业 | “只投嘴巴相关、吃了还想吃” | 白酒/中药/调味品/乳品/啤酒等白名单匹配 | 15 |
| 5. 财务稳健 | “不借钱也能赚钱” | 最新资产负债率 | 10 |

> 注：申万行业分类以 `akshare.stock_industry_change_cninfo` 为准；当该接口因证书/网络失败时，降级使用 `stock_yjbb_em` 的“所处行业”作为行业参考。

## 使用方法

```bash
pip install akshare pandas

# 默认用沪深300成分股作为股票池（消费医药预筛，避免全市场过慢）
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 或用自定义股票池（推荐先小样本验证）
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

参数说明：

- `--pool`: 股票池，目前支持 `hs300`（沪深300）。
- `--codes`: 逗号分隔的自定义股票代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `lin_yuan_screen_result.csv`）。
- `--min-gross`: 毛利率硬门槛（默认 50%）。
- `--min-roe`: ROE 硬门槛（默认 15%）。
- `--min-div`: 近 12 个月股息率硬门槛（默认 1.0%）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，用于防接口限流）。

## 输出字段速览

| 字段 | 含义 |
|---|---|
| `code` / `name` | 股票代码 / 简称 |
| `score` | 林园式综合得分（满分 100） |
| `linyuan_pass` | 是否通过硬门槛（毛利率、ROE、股息率、消费医药行业） |
| `sw_industry` / `sw_sector` | 申万行业三级/二级/一级分类 |
| `gross_mean` / `gross_annual` | 近 5 年毛利率均值 / 序列 |
| `roe_mean` / `roe_annual` | 近 5 年 ROE 均值 / 序列 |
| `dividend_yield` / `payout_recent` | 近 12 个月股息率 / 最近一年派息额 |
| `debt_latest` | 最新资产负债率 |
| `addictive_tag` | 成瘾/刚需行业标签 |
| `data_years` | 有效年度数 |
| `source` / `note` | 数据来源与降级说明 |

## 分析流程（配合 AI 使用）

1. **跑初筛**：运行 `screen.py` 得到候选名单与各项得分。
2. **读清单**：对照 `references/lin_yuan_rules.md`，用“只投垄断、只投嘴巴、毛利率不骗人、买了就不卖”做自我检查。
3. **护城河定性**：对高分股票逐一判断——品牌成瘾性、渠道控制力、提价能力、产能稀缺性、管理层对股东回报的态度。
4. **估值与仓位**：只在能力圈内、估值合理或低估时买入；真正看懂的机会敢于重注、长期持有。

## 数据来源与降级策略

- 数据来自 `akshare` 公开接口（东方财富/巨潮/腾讯行情）。
- 脚本启动时默认禁用系统代理，避免 `127.0.0.1:7890` 等本地代理阻断数据源。
- 财务主接口：`akshare.stock_financial_analysis_indicator`；失败时整体降级到新浪三大报表手工计算。
- 估值主接口：`akshare.stock_value_em`；失败时降级到 `stock_zh_a_spot_tx`。
- 行业主接口：`akshare.stock_industry_change_cninfo`（申万）；失败时降级到 `stock_yjbb_em` 的“所处行业”。
- 分红主接口：`akshare.stock_dividend_cninfo`；失败时股息率标记为缺失，不影响其他维度打分。
- 所有网络调用均带 3 次指数退避重试，调用间 `time.sleep(0.15)` 防限流。

## 配套文件

- `references/lin_yuan_rules.md` — 林园投资思想整理：垄断、嘴巴相关、毛利率、买了就不卖、能力圈与纪律。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过自己对生意的理解（能力圈）二次确认。林园本人观点以公开访谈、演讲、著作为准，本整理可能存在理解偏差。投资决策应建立在独立研究、充分安全边际与自身风险承受能力之上。
