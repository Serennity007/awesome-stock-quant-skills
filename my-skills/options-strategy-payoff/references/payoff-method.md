# 到期损益与盈亏平衡方法

本页固定 `scripts/options_strategy_payoff.py` 的记账口径。所有公式都以“一份策略单位”为基准；`quantity` 与 `multiplier` 是用户输入，脚本只做算术，不核对合约面值。

## 符号与记账

- `sign = +1` 表示 `buy`，`sign = -1` 表示 `sell`。
- `unit = sign × quantity × multiplier`，即每腿每份策略单位在价格变动中的方向系数。
- 期权腿的入场现金流为 `-sign × quantity × premium × multiplier`：买入为负（支付权利金），卖出为正（收取权利金）。
- 期货腿没有权利金现金流：其 `premium` 列是入场期货价格，`cash_flow_at_entry` 记为 `0.0`。因此各腿 `cash_flow_at_entry` 之和等于 `-net_premium`。
- 净权利金 `net_premium = Σ 期权腿 sign × quantity × premium × multiplier`。正数表示净支出权利金（debit），负数表示净收取（credit）。期货腿不进入该求和；只含期货腿的组合 `net_premium = 0.0`。

## 到期损益

设到期标的价格为 `S`：

- call 腿：`sign × quantity × multiplier × (max(S − K, 0) − premium)`
- put 腿：`sign × quantity × multiplier × (max(K − S, 0) − premium)`
- futures 腿：`sign × quantity × multiplier × (S − 入场价)`

把各腿相加即得 `S` 处的到期损益（`payoff_at_prices[].profit_loss`）。`premium` 已包含在期权腿公式内，所以净权利金与逐腿损益是同一套符号，不能重复加减。

## 斜率与有界性

分段线性函数在三个区域的斜率只与腿的方向系数有关：

- `SLOPE_HIGH = 各腿 unit × (call: 1, put: 0, futures: 1) 之和`：`S` 趋于正无穷时的斜率。
- `SLOPE_LOW = 各腿 unit × (call: 0, put: -1, futures: 1) 之和`：`S` 从右侧趋于 0 时的斜率，仅用于描述左尾方向。

判定规则（定义域为 `S>0`）：

- `max_profit = "unbounded"` 当 `SLOPE_HIGH > 0`（价格上升时损益没有上界）。
- `max_loss = "unbounded"` 当 `SLOPE_HIGH < 0`（价格上升时损失没有下界）。
- 其余情况在 `{0} ∪ 各行权价` 的候选集上取最大/最小值作为 `max_profit` / `max_loss`：分段线性函数的极值只能出现在 kink 或定义域端点。

`S=0` 是价格定义域的下边界，损益在此处收敛到有限极限，因此左尾不会被标为 `"unbounded"`：例如纯空头期货的损益为 `入场价 − S`，价格降到 0 时盈利最多为入场价，`max_profit` 是有限数而不是无界。把 `S=0` 作为候选点得到的是**上确界/下确界**，不是可成交价格。负的期货结算价（如 2020 年 WTI）会突破这一约定，本工具未建模该情形；需要覆盖时应另建扩展定义域的工具，不修改本口径。

## 盈亏平衡点

定义域为 `S>0`，kink 只出现在期权行权价（期货腿是线性的，不产生 kink）：

1. 取 `bounds = [0] + 排序去重的期权行权价`。
2. 对每个相邻区间 `(low, high)` 用解析斜率求线性根 `root = low − payoff(low) / slope`；仅当 `low < root < high` 时采纳。
3. 最后一段区间（最后行权价以上直到正无穷）用 `SLOPE_HIGH` 求根，仅当根大于最后行权价时采纳。
4. 每个 `S>0` 的 kink 若损益为 0，且它不是恒为零区间内部点，则采纳；恒为零区间的有限边界也采纳，因为它是“离开零损益区间”的价格。
5. 结果排序、去重，并四舍五入到 6 位小数；`S=0` 上的根不报告。

盈亏平衡点是损益函数的精确零点，不代表价格会在这里停留，也不代表策略“安全”或“划算”。

## 退化与边界情形

- 文件为空、只有表头、没有腿，或字段非法时直接报错，不猜测行权价或权利金。
- 如果损益在**所有** `S>0` 上都恒为 0（例如同一行权价、同一权利金的买入与卖出完全对冲），盈亏平衡集合是无限集，`analyze()` 抛出 `ValueError`，不输出伪造的有限列表。
- 如果损益只在部分区间恒为 0（例如零成本价差），该区间的有限边界会作为盈亏平衡点列出，区间内部不重复报告。
- 数量可以是小数；脚本不做整手、合约乘数或交易单位取整。
- 浮点运算顺序固定为逐腿求和，输出保留完整浮点；只有盈亏平衡点按上述规则取 6 位小数。
