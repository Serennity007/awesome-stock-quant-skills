# 本地腿表与输出契约

`scripts/options_strategy_payoff.py` 只使用 Python 标准库，读取一份本地多腿 CSV。它不联网、不拉行情、不模拟盘中路径，也不生成买卖指令或收益证明。

## 输入

```csv
leg_id,instrument,side,strike,quantity,premium,multiplier
```

- 必填列为 `leg_id,instrument,side,strike,quantity,premium`；`multiplier` 可省略，缺省为 1。文件按 UTF-8 读取，允许 BOM；空文件或只有表头都会被拒绝。
- `leg_id` 是非空文本且在同一文件内唯一，用于回指腿；程序不验证它是否对应真实持仓明细。
- `instrument` 只接受 `call`、`put`、`futures`，`side` 只接受 `buy`、`sell`，两者大小写不敏感，输出统一为小写。
- `quantity` 必须是有限正数；`multiplier` 存在时必须是有限正数。脚本不做整手或合约规格校验，乘数由调用者负责。
- `strike`：call/put 必须为正有限数；futures 必须留空、缺失或写 `-`，填任何数字行权价都会被拒绝。
- `premium`：call/put 必须为有限非负数（允许 0）；futures 的该列是入场期货价格，必须为正有限数。它不是行情报价，也不是结算价。
- `--strategy` 是用户自报标签，只校验非空并去除首尾空白；程序不会验证它和腿结构是否匹配。
- `--prices` 可选，一个或多个有限正数；提供时按给定顺序进入 `price_grid`。未提供时默认网格为每个期权行权价的 `0.8×`、`1.0×`、`1.2×` 排序去重；没有任何期权行权价时必须提供 `--prices`，否则报错。
- `--csv` 与 `--out` 解析后不能是同一路径；输出以独占模式创建，已存在的输出不会被覆盖，也不写临时文件替换。

## 输出

命令行运行写出的 JSON 顶层字段：

| 字段 | 含义 |
|---|---|
| `schema_version` | 固定为 `1` |
| `strategy` | 用户自报标签（已去首尾空白） |
| `leg_count` | 腿数 |
| `legs` | 按 CSV 顺序回显的规范化腿；含 `leg_id`、`instrument`、`side`、`strike`（期货为 `null`）、`quantity`、`premium`、`multiplier`、`signed_quantity`、`cash_flow_at_entry` |
| `net_premium` | 期权腿净权利金；正数=净支出，负数=净收取 |
| `net_premium_note` | 净权利金方向与期货腿排除规则的英文说明 |
| `breakevens` | `S>0` 上的盈亏平衡价格列表，升序、6 位小数 |
| `breakeven_basis` | 盈亏平衡点口径的英文说明 |
| `max_profit` / `max_loss` | 数字或字符串 `"unbounded"` |
| `price_grid` | 实际使用的标的到期价格列表 |
| `payoff_at_prices` | 与 `price_grid` 一一对应的 `{underlying_price, profit_loss}` 列表 |
| `scope` | 范围声明 |
| `limitations` | 限制列表（到期口径、无行权/保证金/费用、输入未核验、策略标签自报、无界标记非风险上限、非交易建议等） |
| `source_sha256` | 原始 CSV 字节的 SHA-256（命令行追加） |
| `source_file` | 输入文件名（命令行追加） |
| `generated_at_utc` | 实际生成时间，UTC ISO-8601（命令行追加） |

- 分析函数 `analyze(raw_bytes, strategy, prices=None)` 返回除 `source_sha256`、`source_file`、`generated_at_utc` 之外的全部字段，便于测试与复用；三个命令行字段由 `main()` 追加。
- `legs[].cash_flow_at_entry`：期权腿为 `-sign × quantity × premium × multiplier`；期货腿为 `0.0`，因为入场期货价格不是权利金现金流。所有腿该字段之和等于 `-net_premium`。
- `max_profit` / `max_loss` 的数字是在 `{0} ∪ 各行权价` 候选集上取得的极值（`0` 为定义域下界的极限值，不是可成交价）；`"unbounded"` 只来自 `SLOPE_HIGH` 的右尾方向判定，不是风险上限，也不表示左尾无界。判定细节见[到期损益方法](payoff-method.md)。
- 数据非法、读写出错或输出已存在时，向 stderr 打印 `ERROR: ...` 并以退出码 2 结束；成功时打印一行英文摘要并返回 0。

## 合成示例

`example-legs.csv` 是人为构造的两腿备兑看涨演示：期货腿以 100 买入，同时卖出 110 行权价、权利金 3 的 call；全部价格与数量均为便于手算的合成值，不是任何交易所的行情或真实合约规格。

示例命令（见 [SKILL.md](../SKILL.md)）把结果写到 `output/payoff.json`；仓库中的 `example-output.json` 是这次实际运行的副本，用于离线核对。输入哈希对应 `example-legs.csv` 的原始字节；`generated_at_utc` 每次运行都会不同。逐项手算见[合成情景走查](example-analysis.md)。
