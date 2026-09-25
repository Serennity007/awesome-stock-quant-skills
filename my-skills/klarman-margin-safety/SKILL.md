---
name: klarman-margin-safety
description: A股卡拉曼安全边际深度价值筛股：PB<1或历史极低位、PE低分位、市值/净现金比、52周高点回撤，剔除ST/亏损股 | A-share Seth Klarman-style deep value screener: PB<1 or historical low, low PE percentile, market-cap-to-net-cash ratio, 52-week drawdown, exclude ST/loss makers | A株セス・クラーマン式ディープバリュー選別：PB<1または歴史的低位、PE低パーセンタイル、時価総額/純キャッシュ比、52週高値からの下落、ST/赤字銘柄を除外
author: Serennity007
license: MIT
---

# 🔻 卡拉曼安全边际｜4 把尺子丈量 A 股“跌出来的机会”

> **风险优先于收益，现金是期权，便宜只是起点，催化剂才是回归的门票。**

本技能用塞斯·卡拉曼（Seth Klarman）在《安全边际》中倡导的**风险厌恶型深度价值投资**框架，在 A 股市场做机械化初筛：不追热点、不猜涨跌，只找价格显著低于保守估算价值、且具备回归路径的候选标的。核心工具是 `scripts/deep_value.py`。

## 4 维深度价值雷达（满分 100）

| 维度 | 核心问题 | 代理指标 | 权重 |
|---|---|---|---|
| 1. PB 绝对值与历史分位 | 股价相对净资产是否足够便宜？ | 当前 PB、近 5 年 PB 分位 | 25 |
| 2. PE 低分位 | 估值是否处于历史底部？ | 近 5 年 PE(TTM) 分位 | 15 |
| 3. 市值/净现金比 | 资产负债表是否提供安全垫？ | 货币资金 - 有息负债；市值/净现金 | 25 |
| 4. 52 周高点回撤 | 市场是否已经把价格打到恐慌区间？ | 当前价较 52 周高点回撤 | 25 |
| 5. 风险剔除 | 是否踩了绝对红线？ | ST、最新年报亏损 → 强制 0 分 | — |

> 注：金融、地产等重负债/高杠杆行业的“净现金”口径不适用，脚本会标记为缺失；银行股的 PB、PE、回撤仍可参与打分。

## 使用方法

```bash
pip install akshare pandas

# 默认用沪深300成分股作为股票池，输出前 20 名
python scripts/deep_value.py --pool hs300 --top 20 --out result.csv

# 自定义小股票池验证（推荐）
python scripts/deep_value.py --codes 600519,000858,600036 --out result.csv
```

参数说明：

- `--pool`: 股票池，目前支持 `hs300`。
- `--codes`: 逗号分隔的自定义代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `klarman_screen_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，用于防接口限流）。

## 数据来源与降级策略

- 数据来自 `akshare` 公开接口（东方财富估值、新浪行情与财务数据）。
- 脚本启动时默认禁用系统代理，避免 `127.0.0.1:7890` 等本地代理阻断数据源。
- 优先使用 `stock_value_em` 获取 PB/PE/市值及历史分位；若东财接口失败，自动降级到新浪日 K + 新浪三大报表手工估算。
- 优先使用 `stock_zh_a_daily`（新浪）获取 52 周价格与回撤；若失败，自动降级到 `stock_zh_a_hist`（东财）。
- 所有网络调用均带 3 次指数退避重试，调用间 `time.sleep(0.15)` 防限流。

## 输出字段

- `code / name`: 股票代码与名称
- `total`: 综合安全边际得分（满分 100，ST/亏损强制 0）
- `pb_score / pb / pb_percentile`: PB 得分 / 当前 PB / 近 5 年分位
- `pe_score / pe / pe_percentile`: PE 得分 / 当前 PE(TTM) / 近 5 年分位
- `netcash_score / market_cap / net_cash / market_cap_to_net_cash`: 净现金维度得分 / 市值(亿元) / 净现金(亿元) / 市值/净现金比
- `drawdown_score / current_price / high_52w / drawdown_pct`: 回撤维度得分 / 当前价 / 52 周高点 / 回撤(%)
- `is_st / is_loss`: ST、亏损标记
- `val_source / price_source`: 数据来源与降级说明

## 分析流程（配合 AI 使用）

1. **跑初筛**：运行 `deep_value.py` 得到候选名单与各项得分。
2. **读清单**：对照 `references/klarman_principles.md`，检查绝对收益、风险优先、催化剂、现金期权、逆向思维。
3. **内在价值估算**：对高分股票做保守估值——清算价值、自由现金流折现、同业重置成本，留出安全边际。
4. **催化剂识别**：价值何时、以何种方式回归？回购、分红、资产剥离、行业周期、治理改善都是可选项。
5. **仓位与耐心**：只在能力圈内、价格显著低估时下注；没有好机会就持有现金，等待“别人恐惧”的时刻。

## 配套文件

- `references/klarman_principles.md` — 《安全边际》核心思想：绝对收益、风险优先、催化剂驱动、现金是期权、不追市场。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过自己对生意的理解（能力圈）与内在价值估算二次确认。投资决策应建立在独立研究、充分安全边际与自身风险承受能力之上。
