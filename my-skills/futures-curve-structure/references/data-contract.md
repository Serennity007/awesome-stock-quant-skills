# 本地期货曲线契约

`scripts/futures_curve.py` 只使用 Python 标准库，读取单个品种的合约价格 CSV。它不拉取行情、不构造连续合约、不预测价格，也不生成交易指令或收益证明。

## 输入

```csv
contract,expiry,last,volume,open_interest
```

- 必填列为 `contract,expiry,last`；`volume,open_interest` 可省略。文件按 UTF-8 读取，允许 BOM。
- `contract` 是调用者声明的合约标识，非空且在同一文件内唯一；程序不验证它是否为真实挂牌合约，也不推断品种。
- `expiry` 必须是 `YYYY-MM-DD` 形式的到期日，不接受日期时间或斜杠格式；非法日历日期（如 2 月 30 日）会被拒绝。“到期日”不等于交易所的最后交易日，CSV 没有字段声明后者。
- `last` 必须是有限正数。它可能是结算价、收盘价或最后一笔成交价，文件不声明来源，脚本不校验口径；同一文件里混用不同口径会让价差失去可比性。
- `volume` 与 `open_interest` 存在时必须为有限非负数，空字符串记为 `null`（不是 0）。字段缺失时输出同样为 `null`。单位、聚合范围与供应商定义都没有被验证。
- `--product` 是自由文本身份，会被去除首尾空白且必须非空；程序不会把它验证为真实品种或交易所。
- `--as-of` 是 `YYYY-MM-DD` 日期或带显式时区的 ISO-8601 时间。带时间时先归一到 UTC，再取 UTC 日期作为 `as_of_date`；只有日期时直接使用该日期。无时区的时间会被拒绝。到期日不晚于该日期的合约行仍逐字段校验，但不进入曲线，计入 `excluded_expired`。
- `--spot` 可选，必须是有限正数；只用于计算基差，不会替换或校准期货价格。
- `--csv` 与 `--out` 解析后不能是同一路径；输出以独占模式创建，已存在的输出不会被覆盖，也不写临时文件替换。

## 输出

顶层字段：`schema_version`(1)、`product`、`as_of_date`、`source_sha256`（原始输入字节的 SHA-256，包含已到期行）、`excluded_expired`、`curve`、`adjacent_spreads`、`structure`、`basis`（未给 `--spot` 时为 `null`）、`scope`、`limitations`。命令行运行还会追加 `source_file`（文件名）与 `generated_at_utc`（UTC ISO-8601 生成时间）；分析函数 `analyze()` 不包含这两项。

- `curve` 按到期日升序，每项含 `contract`、`expiry`、`days_to_expiry`（自然日）、`last`、`volume`、`open_interest`。
- `adjacent_spreads` 对每对到期相邻合约给出 `near_contract`、`far_contract`、`spread`、`spread_pct_of_near`、`days_between`、`annualized_slope_pct`；顺序与 `curve` 一致。
- `structure` 含 `classification`（`contango` / `backwardation` / `flat` / `mixed`）、`total_annualized_change_pct`（只用首末合约）与说明性 `note`。
- `basis` 只在提供 `--spot` 时出现，含 `spot`、`nearest_contract`、`nearest_expiry`、`nearest_days_to_expiry`、`basis`、`basis_pct_of_futures`、`annualized_basis_pct`。
- 数值保留完整浮点，不做四舍五入；所有年化都使用固定 365 自然日分母，公式见[曲线计算方法](curve-method.md)。
- 未能得到至少两个未到期合约、未到期合约到期日重复、字段非法或文件读写失败时，向 stderr 打印 `ERROR: ...` 并以退出码 2 结束；成功时打印一行英文摘要并返回 0。
- `limitations` 固定列出五类未建模项：价格口径未验证、自然日年化忽略交易日历、未建模乘数/货币/单位/保证金/换月成本、数量字段口径未验证、形态不是预测或交易信号。

## 合成示例

`example-curve.csv` 是人为构造的 5 个铜合约曲线：产品标签 `CU_DEMO`，到期日 2026-11-16 至 2027-06-15，价格是便于手算的合成点位，不是任何交易所的真实行情。`CU2706` 的 `volume` 留空用于展示 `null` 处理。

截至日 `2026-10-15`、现货 `70950` 也都是合成参数；`example-output.json` 由这组输入实际运行生成，不能当作行情快照、收益记录或对未来的判断。走查过程见[合成曲线走查](example-analysis.md)。
