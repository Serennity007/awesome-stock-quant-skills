---
name: li-lu-value-compounding
description: A股李录价值复利投资法：长期高ROE（资本回报质量）、ROE复利趋势（近2年vs前3年不失速）、利润再投资成长、盈利含金量、PE/PB历史低分位安全边际、低负债六维打分，找"持续创造价值的复利机器" | A-share Li Lu value-compounding investing: sustained high ROE, ROE trend (recent 2yr vs prior 3yr), reinvestment growth, cash quality, low PE/PB historical percentile margin of safety, low leverage | A株李録バリュー複利投資法：持続的高ROE、ROEトレンド、再投資成長、キャッシュの質、PE/PB歴史低パーセンタイルの安全マージン、低負債の6次元
author: Serennity007
license: MIT
---

# 🏔️ 李录价值复利｜找 A 股持续创造价值的"复利机器"

> **"投资是对未来预测的游戏，唯一可靠的方法是研究那些长期不变的东西。"**

本技能把李录（喜马拉雅资本创始人，芒格的关门弟子，《文明、现代化、价值投资与中国》作者）的价值投资体系机械化到 A 股：长期高 ROE、复利趋势不失速、利润再投资仍能成长、现金流为真、历史低分位的安全边际、低负债。李录的标志性持仓（比亚迪）证明了他最看重的品质——**企业是持续把留存收益变成更多价值的复利机器**。脚本输出 CSV 后，请用 `references/lilu_value_principles.md` 复核"这门生意是否在你能力圈内"。

## 六维价值复利雷达（满分 100）

| 维度 | 核心问题 | 代理指标 | 权重 |
|---|---|---|---|
| 1. 资本回报质量 | 长期回报超资本成本吗？ | 近 5 年 ROE 均值 | 25 |
| 2. 复利趋势 | 价值创造还在加速吗？ | 近 2 年 ROE 均值 − 前 3 年 ROE 均值 | 15 |
| 3. 再投资成长 | 留存收益还在生钱吗？ | 近 5 年净利润增速均值 | 20 |
| 4. 盈利含金量 | 利润是真的吗？ | 经营现金流净额/净利润 | 15 |
| 5. 安全边际 | 市场先生恐慌了吗？ | PB 自身历史分位为主锚，PE 分位辅助 | 15 |
| 6. 财务纪律 | 靠杠杆吗？ | 最新资产负债率 | 10 |

判定线：**≥75 价值复利候选**；**55–74 观察**；**<55 不符合框架**。

## 使用方法

```bash
pip install akshare pandas

# 默认用沪深300成分股作为股票池
python scripts/screen.py --pool hs300 --top 20 --out result.csv

# 或用自定义股票池（推荐先小样本验证）
python scripts/screen.py --codes 600519,000858,600036 --out result.csv
```

参数说明：

- `--pool`: 股票池，目前支持 `hs300`（沪深300）。
- `--codes`: 逗号分隔的自定义股票代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `lilu_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，用于防接口限流）。

## 输出字段速览

| 字段 | 含义 |
|---|---|
| `code` / `name` / `industry` | 股票代码 / 简称 / 所处行业 |
| `total` | 价值复利体系综合得分（满分 100） |
| `roe_quality_score` / `roe_mean` | 资本回报质量得分 / ROE 5 年均值 |
| `roe_trend_score` / `roe_trend_diff` | 复利趋势得分 / 近2年−前3年 ROE 差值（pp） |
| `reinvest_growth_score` / `profit_growth_mean` | 再投资成长得分 / 净利润增速均值 |
| `cash_score` / `ocf_mean` | 含金量得分 / OCF/净利润均值 |
| `margin_safety_score` / `pe_ttm` / `pb` / `pe_percentile` / `pb_percentile` / `val_years` | 安全边际得分 / 当前估值与历史分位 |
| `debt_score` / `debt_latest` / `data_years` / `fin_source` / `note` | 其余维度与数据说明 |

## 分析流程（配合 AI 使用）

1. **跑初筛**：运行 `screen.py` 得到候选名单与各项得分。
2. **读原则**：对照 `references/lilu_value_principles.md`，用"股票=公司所有权、市场先生、安全边际、能力圈"四把尺子复核。
3. **能力圈一票否决**：李录的纪律是"知道自己知道什么"。得分再高，看不懂的生意直接放弃——这是该框架唯一无法量化的前置条件。
4. **深度研究少数公司**：李录研究一家公司动辄数月。脚本帮你从 300 只缩到 10 只，剩下的功课要靠人做。

## 实测参考（2026-09-28，小样 3 只）

贵州茅台 88 分（ROE 32.9%、PB 分位仅 1.9%——5 年历史极低位，安全边际满分）、五粮液 62 分（PB 分位 0.3% 但成长与复利趋势失分——"便宜但变坏中"的典型结构）、招商银行 59 分。小样实测见 `lilu_test_result.csv`。

## 数据来源与降级策略

- 数据来自 `akshare` 公开接口（东财财务指标、东财个股历史估值 PE/PB、新浪三大报表）。
- 安全边际以 **PB 自身历史分位**为主锚（跨行业可比），PE 分位辅助确认；亏损股 PE 失效时只看 PB。
- 复利趋势维度在年度数据不足 4 年时（次新股）给中性 7 分。
- 主接口失败时财务数据整体降级到新浪三大报表手工计算。
- 脚本启动时默认禁用系统代理；所有网络调用带 3 次指数退避重试，调用间 `time.sleep(0.15)` 防限流。

## 配套文件

- `references/lilu_value_principles.md` — 李录核心投资思想：股票即所有权、市场先生、安全边际、能力圈、复利机器。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，能力圈与生意本质的判定必须由投资者本人完成。投资决策应建立在独立研究与自身风险承受能力之上。
