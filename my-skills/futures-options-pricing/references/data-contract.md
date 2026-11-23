# 本地期权定价批次契约

`scripts/futures_options_pricing.py` 只使用 Python 标准库，读取一个本地的、单一期货合约单一到期日的欧式期权 CSV 批次。它不联网、不拉行情、不读盘口、不产生交易指令。

## 输入 CSV

必需列：`option_id,option_type,strike`。可选列：`market_price,volatility`。

```csv
option_id,option_type,strike,market_price,volatility
C100,call,100,8.46,
P100,put,100,7.86,
C95,call,95,,0.20
```

- `option_id`：非空且批次内唯一；用于报错时定位行，也用于平价检查配对。
- `option_type`：`call` 或 `put`，大小写不敏感，输出统一归一化为小写。
- `strike`：有限正数。
- `market_price`：可选；存在时必须有限且大于 0。给定时脚本检查无套利边界并反推隐含波动率。
- `volatility`：可选；存在时必须有限且大于 0，作为该行的定价波动率。
- 每行至少要提供 `market_price` 与 `volatility` 之一，否则整份输入报错；只有必需列、所有可选列缺失的文件也会报错。
- 空单元格表示“未提供”；`NaN/Inf`、负数、0 等非空非法值会报错，不会被当成缺失值。
- 行按 CSV 顺序输出。允许同一行权价出现多行看涨/看跌，平价检查按同价位的看涨×看跌组合逐对生成。
- 空文件、只有表头、缺少必需列、重复 `option_id` 均报错。输入文件只读；脚本不会写回或修改它。

## 命令行参数

| 参数 | 说明 |
|---|---|
| `--csv` | 输入 CSV 路径，必需 |
| `--futures-price` | 同一合约的期货价格，必需，有限正数 |
| `--expiry` | 到期日，`YYYY-MM-DD`，必需 |
| `--as-of` | 定价日，`YYYY-MM-DD` 或带时区的 ISO-8601 时间；必需。带时间时先换算到 UTC 再取日历日期 |
| `--rate` | 连续复利年化无风险利率（小数），可选，默认 `0`，绝对值不得超过 1.0 |
| `--out` | 输出 JSON 路径，必需；不能等于 `--csv`，父目录会自动创建 |

`T = (expiry - as_of 的日历日期) / 365`，必须严格大于 0，否则报错。`--as-of` 允许日期等于或早于当前系统时间，不代表数据已经核验为当日行情。

## 输出 JSON

顶层字段：

- `schema_version`：固定 `1`。
- `futures_price`、`as_of_date`、`expiry`、`days_to_expiry`、`time_to_expiry_years`、`rate`、`day_count_basis`（固定 `"calendar_365"`）。
- `source_sha256`：输入 CSV 原始字节的 SHA-256，用于核对本次输入。
- `options`：逐行结果，见下。
- `parity_checks`：同一行权价的看涨/看跌平价残差列表；没有同价位配对时为空列表。
- `scope`、`limitations`：研究边界与限制说明。
- `source_file`、`generated_at_utc`：由 CLI 追加，`analyze()` 本身不包含。

每个 option 行含：`option_id`、`option_type`、`strike`、`moneyness_ln_F_over_K`（`ln(F/K)`）、`days_to_expiry`、`time_to_expiry_years`、`market_price`（缺失为 `null`）、`pricing_volatility`、`model_price`、`price_difference_vs_market`（无市场价为 `null`）、`implied_volatility`（未反推为 `null`）、`implied_volatility_status`（`solved` 或 `not_requested`）、`greeks`。

`greeks` 固定包含 `delta`、`gamma`、`vega_per_unit_vol`、`vega_per_vol_point`、`theta_per_year`、`theta_per_day`、`rho_per_1_rate`；公式、符号和单位见 [定价方法与约定](pricing-method.md)。

`parity_checks` 的每项含 `strike`、`call_option_id`、`put_option_id`、`call_minus_put`、`discounted_forward_intrinsic`（`e^{-rT}(F-K)`）、`residual`（前两项之差）。

## 运行与错误行为

从本 Skill 目录运行示例：

```bash
python scripts/futures_options_pricing.py --csv references/example-options.csv --futures-price 100 --expiry 2027-06-30 --as-of 2026-11-24 --rate 0.03 --out output/pricing.json
```

成功时以 0 退出并打印一行 ASCII 摘要；输入错误、越界价格、不可解、输出已存在（`open("x")` 模式）或输出等于输入时，以 2 退出并向 stderr 打印 `ERROR: ...`。已有输出不会被覆盖，重复运行同一个 `--out` 会失败并保留原文件。

## 合成示例

`example-options.csv` 是 6 行人为构造的期权报价，`F=100`、定价日 `2026-11-24`、到期 `2027-06-30`、`r=0.03`，不是任何市场的真实报价。其中 `C100/P100` 只给市场价格用于反推隐波且人为偏离平价 0.60；`C95/P95` 只给 0.20 的波动率；`C110` 只给市场价用于反推深虚值隐波；`P105` 只给 0.22 的波动率。

`example-output.json` 由下面这条命令实际运行一次生成（运行前删除旧文件）：

```bash
python scripts/futures_options_pricing.py --csv references/example-options.csv --futures-price 100 --expiry 2027-06-30 --as-of 2026-11-24 --rate 0.03 --out references/example-output.json
```

输出的 `source_sha256` 可与 CSV 文件字节核对；`generated_at_utc` 只是运行时刻，不是数据时间戳，也不能证明输入数据真实。手算核对见 [合成数据走查](example-analysis.md)。
