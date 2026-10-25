# 模拟记录与复盘

这里记录的是 **paper research**：冻结筛选输入与规则，再用明确导入的价格观察计算模拟持仓。它不连接券商，不证明真实成交、个人资金或策略盈利。

## 已经写入的两套记录

| 记录 | 数据与当前状态 | 阅读入口 |
|---|---|---|
| 2026-10-25 真实筛选快照 | 来自当天已保存的 20 只股票筛选结果；14 只完整、6 只不完整；固定规则取前三只，等待后续价格，无持仓、无收益 | [起始记录](../reports/paper/2026-10-25/INITIAL_REVIEW.md)、[冻结参数](../reports/paper/2026-10-25/snapshot.json) |
| 合成演示账户 | 人为构造价格与评分，演示两个观察日的建仓费用、剩余现金、持仓损益和复盘；历史日期只作场景标签 | [初始记录](../examples/paper/journal/INITIAL_REVIEW.md)、[首次复盘](../examples/paper/journal/reviews/2026-08-31.md)、[第二次复盘](../examples/paper/journal/reviews/2026-09-30.md) |

这两套记录都在 2026-10-25 创建。合成演示的 7—9 月日期不代表当时已经运行或发布，更不能描述成几个月的真实操盘经历。JSON 的 `created_at_utc` 保留实际生成时间。

## 1. 冻结观察清单

该功能只用 Python 标准库。仓库已有的起始记录不可覆盖；自己试用请写入 `output/`。

```bash
python scripts/paper_journal.py start --screen reports/2026-10-25.csv --signal-date 2026-10-25 --data-kind market_snapshot --top 3 --cash 1000000 --cost-bps 10 --lot-size 100 --output output/my-paper-journal
```

固定规则：`score_status=complete`、`decision=review_moat`、总分至少 70；按总分降序、代码升序取前 N 只。分数高但财务不完整的股票会被排除。这里的“候选”仍需人工核查，不等于完成护城河研究或发出买入指令。

`snapshot.json` 保存规则、参数、观察清单、排除原因、数据口径与引擎哈希；原始筛选 CSV 和可用的元信息一并复制。初始记录不产生持仓、净值或“0% 收益”，状态为 `watchlist_pending_execution`。无合格候选时如实记录 `no_eligible_candidates`。

模拟资金 100 万和 10 bps 是核算参数，不代表个人资金或真实市场费率。每个候选使用等额预算，整手向下取整，保留剩余现金；预算不足一手时拒绝生成成交记录。

## 2. 导入后续观察价格

CSV 格式为 `date,code,close`，每个复盘日必须同时提供所有候选和 `BENCHMARK` 的价格。`BENCHMARK` 是用户导入的基准序列标识，脚本不会自动补造沪深300行情。

```csv
date,code,close
```

请在表头下面填写从可靠来源取得的真实观察值。真实账户示例没有预填任何未来价格。自行保存数据源、抓取时间和复权口径，只有标签并不能保证输入真实。

```bash
python scripts/paper_journal.py review --journal output/my-paper-journal --prices path/to/observed-prices.csv --review-date YYYY-MM-DD --notes-file path/to/your-review.md
```

`--notes-file` 可省略。复盘日期必须晚于信号日、晚于已有复盘，且不能在未来。输入中出现复盘日期之后的价格会报错，不会静默使用未来信息。

首次模拟买入使用信号日之后 **第一个所有候选与基准都有观察值的日期**，按该日收盘价假设成交。它不是交易所日历推算的“下一交易日”，也不保证当时能以该价格成交。信号日价格不会被拿来建仓。

后续记录保持首次买入股数、费用与剩余现金，计算当前总资产、累计净损益、基准价格收益、差值及复盘观察点最大回撤。不自动卖出、止损或再平衡，不强制期末清仓。基准是同起点价格比较，不扣策略建仓费用，也不是完整含分红指数总回报。

## 3. 重跑合成演示

```bash
python scripts/paper_journal.py start --screen examples/paper/screen.csv --signal-date 2026-07-31 --data-kind synthetic --top 1 --cash 100000 --output output/paper-demo
python scripts/paper_journal.py review --journal output/paper-demo --prices examples/paper/prices-first.csv --review-date 2026-08-31 --notes-file examples/paper/notes-first.md
python scripts/paper_journal.py review --journal output/paper-demo --prices examples/paper/prices-through-second.csv --review-date 2026-09-30 --notes-file examples/paper/notes-second.md
```

这是独立的模拟账户示例，不沿用 `run_demo.py` 的资金与成本计算结果。价格取自同一套[合成回测缓存](../examples/backtest/SCENARIO.md)，但账户在信号日之后的首个共同观察日才模拟建仓：

- 合成代码 `000003` 虽有 99 分，但为 `partial`，不能入选；选中 `000001`。
- 2026-08-31 观察价 110，模拟买入 900 股，费用 99，剩余现金 901；当期总资产 99,901。
- 2026-09-30 观察价 99，持仓市值 89,100，加现金后总资产 90,001，累计净损失 9,999。
- 基准从 102 变为 101。所有价格与日期都是合成测试标签，亏损也只是公式演示，不是真实证券表现。

## 4. 复盘文件与校验

每次复盘新增 `reviews/YYYY-MM-DD.json`、Markdown、当次价格 CSV 和 SHA256 清单。记录链接上一条 JSON 的哈希；追加前检查起始输入与已有复盘的校验记录。同日重跑、修改冻结输入、回写已记录的建仓价/复盘价都会报错。

这些措施防止意外覆盖并方便复核，**不是可信时间戳、数字签名或不可篡改账本**。人为修改文件及其哈希仍可伪造本地记录。真实前向验证应及时公开冻结快照，并保留独立来源的数据和发布证据。

仓库通过 `.gitattributes` 保留已发布快照与复盘文件的原始字节，避免 Windows/Linux 自动转换换行导致校验失效。

自动复盘只写可核对的计算事实，人工补充单独标记为 `user_supplied`。不自动编造行情原因、新闻解读或个人交易心得。只有离散复盘点的回撤，不等于期间真实最大回撤；停牌、涨跌停、滑点、冲击、分红及复权尚未完整建模。

## 5. 每日报告接入

现有 daily-report 工作流下一次运行时，新脚本会把完整与不完整记录分开展示，并在 `reports/paper/日期/` 保存该日首次筛选的待建仓快照。同日重新取数可更新日报，但保留第一次冻结的输入，不把后来的结果改写成更早的判断。

这不会自动产生后续价格、收益或跨日调仓；各日快照是独立观察批次，不能把每天重新选择的候选拼成一个连续账户。连续持仓复盘必须始终对同一个 journal 追加。

取数或输入验证失败时，日报脚本现在返回非零状态，不再以成功任务掩盖失败。失败说明写入本地 `latest.md`；现有 Actions 的后续自动提交步骤可能因此不执行，应到运行日志查看失败，不能假定失败说明已发布。

未新增定时工作流，也未为生成这些记录重拉市场数据；首次真实快照引用仓库已保存的 2026-10-25 CSV。模拟账户、报告展示与故障路径已做本地测试，线上下一次定时运行的结果应另行核对。
