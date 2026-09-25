---
name: templeton-global-contrarian
description: A股邓普顿全球逆向投资扫描：在“极度悲观”中筛选股价近52周低位、PE/PB历史10%分位以下、缩量企稳且盈利为正的逆向买入观察清单 | A-share Templeton global contrarian scanner: screen for stocks near 52-week lows, with PE/PB below 10th percentile, volume-contracted stabilization, and still-positive earnings | A株テンプルトン式グローバル逆行投資スキャナー：52週安値圏、PE/PB過去10パーセンタイル以下、出来高縮小後の安定化、黒字維持銘柄の逆張りウォッチリスト
author: Serennity007
license: MIT
---

# 🌍 邓普顿全球逆向投资｜在 A 股“极度悲观”里捡漏

> **牛市在悲观中诞生，在怀疑中成长，在乐观中成熟，在狂热中死亡。**
> *——约翰·邓普顿（John Templeton）*

本技能把邓普顿“极度悲观时买入优质困境股”的逆向思想，转化为 A 股可量化的初筛工具：

- **不追热点**：专门找被市场冷落、股价接近 52 周低点、估值被压到历史极端分位的标的。
- **不买垃圾**：要求最新年度盈利仍为正，回避已被亏损摧毁内在价值的“伪困境股”。
- **等待企稳**：成交量极度萎缩且价格不再创新低，作为恐慌盘枯竭的代理信号。

核心工具是 `scripts/contrarian_scan.py`：它从沪深 300 或自定义股票池中扫描上述信号，输出结构化 CSV 与终端表格，供你进一步做基本面与行业周期研究。

## 4 维逆向雷达（满分 100）

| 维度 | 代理指标 | 邓普顿含义 | 权重 |
|---|---|---|---|
| 1. 52 周位置 | 股价处于近 52 周高低点区间的位置 | 市场情绪最悲观、价格最低迷 | 30 |
| 2. 估值极端性 | PE / PB 处于自身近 5 年 10% 分位以下 | 估值被压抑到历史极端低位 | 30 |
| 3. 缩量企稳 | 近 5 日均量 < 近 20 日均量 50%，且价格不再创新低 | 恐慌盘枯竭、筹码趋于稳定 | 20 |
| 4. 盈利仍为正 | 最新年度净利润 > 0 | 困境中的优质企业，未陷入亏损 | 20 |

> 注：PE/PB 优先使用东方财富每日估值历史（`akshare.stock_value_em`）；若东财接口失败，脚本自动降级为“年报 EPS/BPS + 日线收盘价”估算历史分位。

## 使用方法

```bash
pip install akshare pandas

# 默认用沪深300成分股作为股票池（质量预筛，避免全市场过慢）
python scripts/contrarian_scan.py --pool hs300 --top 20 --out result.csv

# 或用自定义股票池（推荐先小样本验证）
python scripts/contrarian_scan.py --codes 600519,000858,600036 --out result.csv
```

参数说明：

- `--pool`: 股票池，目前支持 `hs300`（沪深300）。
- `--codes`: 逗号分隔的自定义股票代码，优先级高于 `--pool`。
- `--top`: 终端展示前 N 名（默认 20）。
- `--out`: CSV 输出路径（默认 `templeton_contrarian_result.csv`）。
- `--sleep`: 每只股票间隔秒数（默认 0.3，用于防接口限流）。

## 输出字段说明

| 字段 | 含义 |
|---|---|
| `code` / `name` | 股票代码与简称 |
| `close` | 最新收盘价 |
| `wk52_low` / `wk52_high` | 近 52 周收盘价最低/最高 |
| `position_ratio` | 当前价格在 52 周区间中的位置（0=低点，1=高点） |
| `pe_ttm` / `pb` | 当前 PE(TTM) / 市净率 |
| `pe_pct` / `pb_pct` | PE / PB 自身近 5 年历史分位（0-1） |
| `vol_ratio` | 近 5 日均量 / 前 20 日均量 |
| `volume_contracted` | 是否显著萎缩（vol_ratio < 0.5） |
| `price_stabilized` | 近 5 日未创新低且波动率较低 |
| `profit_latest_亿` | 最新年度净利润（亿元） |
| `score` | 逆向信号综合得分 |
| `signals` | 触发信号标签 |
| `val_source` / `profit_source` | 数据来源 |
| `note` | 降级或异常备注 |

## 分析流程（配合 AI 使用）

1. **跑扫描**：运行 `contrarian_scan.py` 得到候选名单与各项得分。
2. **读法则**：对照 `references/templeton_rules.md`，理解“极度悲观原则”、16 条投资法则、全球视野与“牛市在悲观中诞生”。
3. **基本面过滤**：高分股只是观察清单，必须逐一确认：
   - 盈利下滑是周期性的还是结构性的？
   - 资产负债表能否熬过寒冬？
   - 行业竞争格局是否恶化？
   - 未来 3-5 年恢复正常后，内在价值是多少？
4. **仓位与节奏**：逆向买入通常需要分批、留足安全边际，不要在第一次触发时就重仓。

## 数据来源与降级策略

- 数据来自 `akshare` 公开接口（东方财富估值、新浪日线与财务数据）。
- 脚本启动时默认禁用系统代理，避免 `127.0.0.1:7890` 等本地代理阻断数据源。
- **估值接口**：优先 `stock_value_em`；失败或数据不足时，自动降级为 `stock_financial_analysis_indicator` + `stock_zh_a_daily` 估算 PE/PB 历史分位。
- **利润数据**：优先新浪利润表 `stock_financial_report_sina`。
- **日线数据**：自动尝试 `sh/sz/bj` 前缀，优先匹配交易所规则。
- 所有网络调用均带 3 次指数退避重试，调用间 `time.sleep(0.15)` 防限流；CSV 输出使用 `utf-8-sig` 编码。

## 配套文件

- `references/templeton_rules.md` — 邓普顿极度悲观原则、16 条投资法则、全球视野找便宜货、牛市在悲观中诞生。

## 免责声明

本技能仅供学习研究，不构成投资建议。历史财务指标不代表未来表现，任何筛选结果都必须经过自己对生意的理解（能力圈）二次确认。约翰·邓普顿的投资思想属于公开知识，本 skill 为个人化学习整理，可能存在理解偏差。投资决策应建立在独立研究、充分安全边际与自身风险承受能力之上。
