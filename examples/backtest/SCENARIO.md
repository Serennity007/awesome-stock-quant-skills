# 合成回测场景：验证计算，不代表历史业绩

`cache/` 内七份 CSV 全部为人为构造，代码只用于索引，不是真实证券行情或真实财报。

两个股票序列分别为 `100 → 110 → 99` 与 `100 → 100 → 105`；财务打分使第一只始终排在前面。基准为 `100 → 102 → 101`。报告期和月份只是测试标签。

在仓库根目录执行：

```bash
python my-skills/framework-backtest/scripts/backtest.py --cache-dir examples/backtest/cache --results-dir output/backtest-demo --frameworks danbin --start 2026-07-31 --top 1 --min-stocks 2 --cost-bps 10
```

预期：首期买入一单位成交额、收取 10 bps 成本，此后持仓不变、不再次收费、不在期末强制清仓。两期毛收益为 `+10%` 和 `-10%`，净期末资产 `1 × 0.999 × 1.1 × 0.9 = 0.98901`，基准期末资产 `1.01`。

输出月度毛净收益、换手、成本、持仓明细、指标汇总和输入 CSV 哈希。该场景只检验机制，不验证真实交易可执行性、财务披露或投资收益。
