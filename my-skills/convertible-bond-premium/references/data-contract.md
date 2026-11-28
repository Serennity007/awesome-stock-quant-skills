# 本地转债表、正股序列与输出契约

`scripts/convertible_bond_premium.py` 只用 Python 标准库，读取研究者本地整理的转债表、可选的正股收盘序列与可选的评级贴现率表。它不联网、不拉行情、不核对募集说明书，也不生成买卖指令或收益证明。本页固定三个输入 CSV 的列、类型、必填性、计算口径、错误行为与输出字段；公式细节与手算例见[测算方法](method.md)。

## 输入一：转债表（`--csv`，必填）

表头必须含 `code,name,price,conv_price,stock_price,coupons,years_left,redemption_price`，可选 `face`、`rating`；列顺序任意，列名大小写不敏感。文件按 UTF-8 读取（允许 BOM），空文件或只有表头都会被拒绝，整行全空的填充行会被跳过。

| 列 | 类型 | 必填 | 口径 |
|---|---|---|---|
| `code` | 文本 | 是 | 非空，同一文件内唯一，只允许 `[0-9A-Za-z._-]` |
| `name` | 文本 | 是 | 非空；只回显，不用于计算 |
| `price` | 有限正数 | 是 | 转债价格，元/张 |
| `conv_price` | 有限正数 | 是 | 转股价，元/股 |
| `stock_price` | 有限正数 | 是 | 正股价，元/股 |
| `coupons` | 文本 | 是（可留空） | 剩余各期票息率（小数，`0.002` 表示 0.2%），用竖线分隔；留空表示零息；每项必须是有限非负数，允许中间项为 `0`，不允许空项 |
| `years_left` | 有限正数 | 是 | 剩余年限（年），可为小数 |
| `redemption_price` | 有限正数 | 是 | 到期赎回价，元/张，按下列口径**含最后一年利息** |
| `face` | 有限正数 | 否 | 面值，缺省 `100`；列为空也按 `100` |
| `rating` | 文本 | 否 | 缺省空；只用于匹配 `--discount-csv`，不校验评级体系 |

票息时点与现金流：

- 设 `m = len(coupons)`，`t_k = years_left - (m - k)`（`k = 1..m`）；`t_m = years_left`，最后一期票息与到期赎回发生在同一时点。
- 第 `k` 期现金流为 `coupon_k × face`；到期另有 `redemption_price`。零息时只有赎回价一项。
- **到期赎回价的含息口径**：`redemption_price` 视为“到期赎回价（含最后一年利息）”。如果赎回价已经包含末期利息，应把最后一期票息写 `0`，否则脚本会把两者都折现相加、重复计息。脚本不替用户判断，口径错会直接反映在 `pure_bond_value` 上。
- 脚本按公式直接接受任意正的 `years_left`，不额外要求 `t_k > 0`。若剩余年限与票息期数不匹配（例如 `years_left < m - 1`），早期票息时点会为零或负数，现金流不再有经济意义，YTM 也可能因搜索区间内无根而为 `null`；这类输入应在整理数据时避免。

## 输入二：正股收盘序列（`--stock-csv`，可选）

列 `date,code,close`，列名大小写不敏感：

| 列 | 类型 | 必填 | 口径 |
|---|---|---|---|
| `date` | 文本 | 是 | 严格 `YYYY-MM-DD` 日历日期 |
| `code` | 文本 | 是 | 与转债表的 `code` 对应；不存在的 code 忽略，不进入输出 |
| `close` | 有限正数 | 是 | 收盘价，元/股 |

- 同一 `code` 的行在脚本内按日期升序排列后使用，**文件行序不影响计数**；同一 `code` 出现重复日期报错。重复日期与格式错误对所有 code 都校验，即使该 code 不在转债表中。
- 提供 `--stock-csv` 时至少需要一行数据；空文件、只有表头、日期不合法、收盘价非正都会报错。
- 只使用 CSV 中实际存在的交易日行，不补节假日、不换自然日、不推断交易所日历。
- 转债表中的 code 在正股 CSV 中没有序列（或完全未提供 `--stock-csv`）时，该债 `trigger.status = "no-stock-series"`，`count` 与 `observed_days` 为 `null`。

## 输入三：评级贴现率表（`--discount-csv`，可选）

列 `rating,rate`，列名大小写不敏感：

| 列 | 类型 | 必填 | 口径 |
|---|---|---|---|
| `rating` | 文本 | 是 | 非空且在同一文件内唯一；与转债表 `rating` 去首尾空白后精确匹配（区分大小写） |
| `rate` | 有限正数 | 是 | 年化贴现率，小数形式（`0.035` 表示 3.5%） |

- 命中时该债 `discount_rate_source = "rating-curve"`，用表内值；否则回退 `--discount-rate`（缺省 `0.035`），`discount_rate_source = "default"`。
- 提供该文件时至少需要一行数据；重复评级、空评级或非正 rate 报错。
- 转债表没有 `rating` 列、`rating` 为空或未命中时，一律使用默认贴现率。评级只是用户自报标签，脚本不校验评级机构与评级时点。

## 计算口径

- `conversion_shares = face / conv_price`；`conversion_value = conversion_shares × stock_price`；`conversion_premium = price / conversion_value - 1`（负数表示折价）。
- `pure_bond_value = Σ_k coupon_k × face / (1+r)^{t_k} + redemption_price / (1+r)^{years_left}`；`bond_floor_premium = price / pure_bond_value - 1`。
- `ytm` 是 `price = Σ_k coupon_k × face / (1+y)^{t_k} + redemption_price / (1+y)^{years_left}` 在 `[-0.9999, 10.0]` 内的二分法数值解，容差 `1e-12`、最多 `400` 次迭代；区间内无解时 `ytm = null`，并附英文 `ytm_note`。
- `double_low = price + 100 × conversion_premium`。
- 强赎阈值 `price_threshold = trigger_ratio × conv_price`；取该 code 按日期升序后的最后 `trigger_window` 个收盘价，统计 `close >= price_threshold` 的天数 `count`（边界含等号）。可用天数 `< trigger_window` 时 `status = "insufficient-history"` 且 `observed_days` 为实际可用天数、`count` 为这些可用天数中的达标数；否则 `count >= trigger_days` 为 `"triggered"`，否则 `"below"`。注意“最后 N 天”按 CSV 实际交易日行计，不是自然日。
- 所有价格、金额与比率保持 Python 浮点原值输出，不做展示性四舍五入；手算核对时末位可能不同。

## 输出

命令行写出的 JSON 顶层字段：

| 字段 | 含义 |
|---|---|
| `schema_version` | 固定为 `1` |
| `source_file` | 转债 CSV 的文件名（不含路径） |
| `source_sha256` | 转债 CSV 原始字节的 SHA-256 |
| `generated_at_utc` | 实际生成时间，UTC ISO-8601 |
| `parameters` | 本次参数：`discount_rate_default`、`discount_csv`（文件名或 `null`）、`trigger_ratio`、`trigger_window`、`trigger_days`、`stock_csv`（文件名或 `null`）、`stock_sha256`（原始字节哈希或 `null`） |
| `rows` | 每只债一行，按转债 CSV 行序 |
| `summary` | 横截面汇总，见下 |
| `scope` | 范围声明 |
| `limitations` | 限制列表（输入未核验、票息时点固定、赎回价含息、单利率折现、无信用/流动性/税费、YTM 假设、强赎条款简化、双低非估值、非交易建议等） |

`rows` 字段：回显 `code,name,price,conv_price,stock_price,face,rating,years_left,redemption_price,coupons`，并给出 `conversion_shares,conversion_value,conversion_premium,coupon_times,coupon_cashflows,discount_rate,discount_rate_source,pure_bond_value,bond_floor_premium,ytm,ytm_note,double_low`。`trigger` 为对象，含 `status,window,observed_days,count,trigger_days,ratio,price_threshold`。`status` 只取 `triggered / below / insufficient-history / no-stock-series` 之一。

`summary` 字段：`bond_count`、`conversion_premium_min`、`conversion_premium_max`、`conversion_premium_median`（`statistics.median`）、`pure_bond_value_min`、`double_low_best`（按 `double_low` 升序的前 5 条，不足 5 条全给，元素为 `{code,double_low}`）、`triggered`、`insufficient_history`、`no_stock_series`（三个 code 列表，按转债 CSV 行序；空集用空列表）。

## 错误行为

- 成功时向 stdout 打印一行英文摘要，退出码 `0`。
- 任何输入、校验或读写错误都向 stderr 打印 `ERROR: <message>`，退出码 `2`，且不留下输出文件；输出写入过程中失败会删除已创建的部分文件。
- `--out` 必填且目标文件必须不存在；已存在时直接报错，绝不覆盖。父目录不存在时自动创建。`--csv` 与 `--out` 指向同一路径时同样因“已存在”被拒绝，输入文件不会被改写。
- `--trigger-window`、`--trigger-days` 必须为正整数且 `trigger_days <= trigger_window`；`--trigger-ratio`、`--discount-rate` 必须为有限正数。参数校验在读取 CSV 之前执行，CSV 解析与计算错误在创建输出文件之前抛出，因此任何一项不合格都不会写出文件。
- 典型错误（全部走 `ERROR: ...` + 退出码 2）：缺列（`bond CSV requires columns: ...`）、`code` 为空/含非法字符/重复、`name` 为空、价格类字段非正或非有限、`coupons` 含空项或负值/非数值、`coupons` 期数多于剩余年限（票息时点 ≤ 0，无法折现）、正股日期格式错误或同一 code 重复日期、贴现率表重复评级、输出已存在。
- 脚本不修正、不插值、不猜条款；宁可报错退出，也不输出半成品。

## 合成示例

`references/example-bonds.csv` 是 4 行**人为构造的合成数据**，不对应任何真实存续转债或交易所行情：

| code | 情景 | 说明 |
|---|---|---|
| `CB001` | 深度折价 | 转股价值高于价格（溢价率 `-0.20`），带合成 `rating=AAA` |
| `CB002` | 深度溢价 | 转股价值远低于价格（溢价率 `1.525`），无评级 |
| `CB003` | 零息 | `coupons` 留空，到期一次还本付息，带合成 `rating=AA` |
| `CB004` | 四期票息 | 四期票息率，末期票息写 `0`，避免与含息的 `redemption_price` 重复计息（具体取值见 CSV） |

`references/example-stock.csv` 是 `CB004` 的 35 行**合成**正股收盘序列：按工作日构造（未按交易所日历剔除节假日），前 5 天低于阈值，最后 30 天中恰好 16 天 `close >= 13.0`，其中 `2024-06-26` 的收盘价恰为 `13.00`（`1.3 × 10.0`）以验证边界含等号。它只用于演示触发计数，不是真实行情。

`references/example-output.json` 由脚本对上述两份 CSV 实际运行生成，不是手写：

```bash
python scripts/convertible_bond_premium.py --csv references/example-bonds.csv \
  --stock-csv references/example-stock.csv --out references/example-output.json
```

生成后 `rows` 4 条、`summary.bond_count = 4`、`CB004` 的 `trigger.status = "triggered"` 且 `count = 16`；其余三只无正股序列，`trigger.status = "no-stock-series"`。`generated_at_utc` 每次运行都会变化；`source_sha256` 与 `parameters.stock_sha256` 分别对应两个 CSV 的原始字节。示例数值可用 `references/method.md` 的手算式逐项核对。
