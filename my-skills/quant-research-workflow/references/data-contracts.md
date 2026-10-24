# 读取产物时的决策

## 财务筛选 → 共识

巴菲特筛选保留 `code,total` 供共识合成，同时输出：

| 字段 | 使用方式 |
|---|---|
| `score_status` / `decision` | 仅 `complete` 才能按分数解释；`partial` 必须优先处理 `needs_data` |
| `data_issues` | 区分缺年、毛利率不适用、现金流缺失、最新负债缺失与估值不足 |
| `financial_periods` | 实际报告期，不是披露日 |
| `gross_years` / `cashflow_data_years` | 有效年度覆盖，不是通过门槛的年数 |
| `valuation_date` / `valuation_history_start` | 当前估值日期与实际历史起点；不能用运行日期替代 |

共识输入如有 `score_status` 列，会拒绝非 `complete` 行；不自动删除失败标的或补分。完整财务状态也不代表数据源已审计、金融行业规则适用或估值有收益预测力。

## 回测

- `ret/nav` 为应用所选成本假设后的净收益/净值，`gross_ret/gross_nav` 为毛收益/毛净值。
- `turnover` 为调仓前资产权重相对等权目标的买卖成交额绝对和，初始买入为 1，整仓换股通常为 2。旧权重先按上期价格变化漂移，不把同一股票未换仓一概当作零换手。
- `cost_fraction = turnover × cost_bps / 10000`，`net_ret = (1-cost_fraction) × (1+gross_ret)-1`。这是按调仓前净资产测算的简化成本模型，不是成交回报或实际费率。
- 策略与基准使用同一实际交易日期区间。缺失基准、已选持仓退出价格或投资期间缺月时终止，不填零、不跳月、不利用下个月价格是否存在来提前换掉股票。
- 读取 `bt_holdings_*.csv` 核对每期代码、分数、等权权重及进出价格；用 `bt_manifest.json` 核对参数、输入哈希与未实现假设。

CLI 默认每单位买卖成交额 10 bps，可改为 0 或做多组敏感性比较。首期建仓计成本；末期不强制清仓，不含末期清仓费。仍采用当前池、120 天财报滞后近似和未复权价格；不将其称为严格时点回测、总回报或可实盘收益。

## 本地运行验证

在仓库根目录运行：

```bash
python my-skills/framework-backtest/scripts/backtest.py --cache-dir examples/backtest/cache --results-dir output/backtest-demo --frameworks danbin --start 2026-07-31 --top 1 --min-stocks 2 --cost-bps 10
```

输入为合成数据，两期净期末资产应为 `0.98901`，基准为 `1.01`。这只验证引擎机制。安装单个 skill 时不会附带仓库顶层的合成场景；需要示例时从仓库读取，不能声称示例已经装在 skill 中。
