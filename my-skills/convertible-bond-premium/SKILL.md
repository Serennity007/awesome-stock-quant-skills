---
name: convertible-bond-premium
description: "个人可转债转股溢价与债底测算方法：用本地转债表与可选的正股收盘序列，机械计算转股价值、转股溢价率、纯债价值与债底溢价率、到期收益率、双低值，并按条款参数统计强赎触发天数。适用于转债备课、条款情景核对与数据口径检查；不拉行情、不联网、不预测价格，不把溢价率或双低值当估值判断或买卖信号，不把纯债价值当保本承诺，也不把强赎计数当必然触发。"
license: MIT
metadata:
  author: Serennity007
---

# 我的可转债转股溢价与债底测算方法

这套方法只回答一个机械问题：给定一份本地整理的转债表（价格、转股价、正股价、票息、剩余年限、到期赎回价）与可选的正股收盘序列，每只债的转股价值、转股溢价率、纯债价值、债底溢价率、到期收益率、双低值分别是多少，强赎条款在给定窗口内记到几天。它把价格口径、票息时点、折现口径与条款计数分开处理，允许结论是“数据不足”“区间内无解”或“未触发”；不把任何读数叫成估值结论、买卖信号或收益证明。

## 目标与边界

- 输入是研究者自己整理的转债表与正股收盘序列；脚本只读本地 CSV，不联网、不拉行情、不取公告，也不校验这些数据是否对应真实存续债。
- 输出是算术结果：转股价值、转股溢价率、纯债价值、债底溢价率、YTM、双低值，以及强赎条款的触发天数计数。
- 只算静态口径：不模拟正股路径、不预测价格、不判断发行人是否会下修或赎回、不评估信用资质。
- 不建模信用风险、违约与评级迁移，不建模利率路径与再投资，不建模流动性、税费、手续费、融资成本与汇率。
- 票息、转股价、赎回价与评级都是用户输入，不是募集说明书或交易所数据；脚本不核对条款原文，也不判断输入是否过期。
- 示例转债表、正股序列与示例输出均为合成数据，只用于验证计算行为，不是真实行情、真实条款或历史业绩。

## 输入定义与符号约定

- 转债 CSV 必填列 `code,name,price,conv_price,stock_price,coupons,years_left,redemption_price`，可选 `face`（缺省 100）与 `rating`（缺省空）。列顺序任意、大小写不敏感。
- `code` 非空且在同一文件内唯一，允许 `[0-9A-Za-z._-]`；`name` 非空。`price`（元/张）、`conv_price`（元/股）、`stock_price`（元/股）、`face`、`years_left`、`redemption_price` 必须是有限正数。
- `coupons` 是**剩余各期票息率**（小数，`0.002` 表示 0.2%），用竖线 `|` 分隔；整格留空表示零息，不允许空项（如 `0.002||0.004`）；每项必须是有限非负数。
- 票息时点：设 `m = len(coupons)`，`t_k = years_left - (m - k)`（k = 1..m）。因此 `t_m = years_left`，最后一期票息与到期赎回发生在同一时点；`t_k` 是距估值日的年数，不是自然年序号。任何 `t_k <= 0`（票息期数多于剩余年限）都会被拒绝，而不是按负数指数折现出一个更大的现值。
- **到期赎回价口径**：`redemption_price` 视为“到期赎回价（含最后一年利息）”。如果用户的赎回价已经包含末期利息，应把最后一期票息写 0；脚本不替用户判断，而是把票息与赎回价都按公式相加，口径错会直接反映在纯债价值上。
- 正股 CSV（可选）列 `date,code,close`：`date` 为 `YYYY-MM-DD`，`close` 为有限正数；同一 `code` 按日期升序排列后使用，重复日期报错。CSV 中出现 bonds 里没有的 code 不进入输出，但这些行的日期格式、重复日期与数值仍会被校验；bonds 里的 code 在正股 CSV 中缺失时，该债的 `trigger.status` 记为 `no-stock-series`。
- 符号：`face` 面值（元/张），`conv_price` 转股价（元/股），`stock_price` 正股价（元/股），`price` 转债价格（元/张），`r` 贴现率，`y` 到期收益率。
- 主要公式：
  - `conversion_shares = face / conv_price`，`conversion_value = conversion_shares × stock_price`，`conversion_premium = price / conversion_value - 1`（负数表示折价）。
  - `pure_bond_value = Σ_k coupon_k × face / (1+r)^{t_k} + redemption_price / (1+r)^{years_left}`；零息时只剩赎回价一项。
  - `bond_floor_premium = price / pure_bond_value - 1`；`double_low = price + 100 × conversion_premium`。
  - 强赎阈值 `price_threshold = trigger_ratio × conv_price`，边界含等号。
- 转股数按面值直接除以转股价得到理论股数；整股取整、不足一股的现金替代与实际转股规则未建模。
- 贴现率：默认 `--discount-rate 0.035` 作用于所有债；`--discount-csv` 为可选表，列 `rating,rate`，债的 `rating` 命中时用表内值，否则回退默认值；每行输出 `discount_rate` 与 `discount_rate_source`（`rating-curve` 或 `default`）。完整公式、YTM 二分法与逐项手算见[测算方法](references/method.md)。

## 可复现的本地脚本

用 `scripts/convertible_bond_premium.py` 复算上述事实。脚本只用 Python 标准库，只读本地 CSV，不联网、不拉行情、不生成买卖指令。

```bash
python scripts/convertible_bond_premium.py --csv references/example-bonds.csv \
  --stock-csv references/example-stock.csv --discount-rate 0.035 \
  --trigger-ratio 1.3 --trigger-window 30 --trigger-days 15 --out output/premium.json
```

从本 Skill 目录运行，结果写入 `output/premium.json`。`--csv` 与 `--out` 必填；`--stock-csv`、`--discount-csv` 可选；`--discount-rate` 缺省 0.035；`--trigger-ratio` 缺省 1.3；`--trigger-window` 与 `--trigger-days` 缺省 30 与 15，必须为正整数且 `trigger_days <= trigger_window`。`--out` 以新文件创建，目标已存在则报错退出、不覆盖；父目录不存在时自动创建。成功时向 stdout 打印一行英文摘要并以 0 退出；任何输入、校验或读写错误向 stderr 打印 `ERROR: <message>`、以 2 退出，且不留下输出文件。字段约定见[输入与输出契约](references/data-contract.md)，示例数据为明确标注的合成数据。

## 输出与限制

- JSON 顶层包含 `schema_version`（固定 `1`）、`source_file`、`source_sha256`、`generated_at_utc`、`parameters`、`rows`、`summary`、`scope`、`limitations`。
- `parameters` 含 `discount_rate_default`、`discount_csv`、`trigger_ratio`、`trigger_window`、`trigger_days`、`stock_csv`、`stock_sha256`。
- `rows` 每项回显输入并给出 `conversion_shares`、`conversion_value`、`conversion_premium`、`coupon_times`、`coupon_cashflows`、`discount_rate`、`discount_rate_source`、`pure_bond_value`、`bond_floor_premium`、`ytm`、`ytm_note`、`double_low`、`trigger`；`trigger` 含 `status`、`window`、`observed_days`、`count`、`trigger_days`、`ratio`、`price_threshold`。
- `trigger.status` 取 `triggered`、`below`、`insufficient-history`、`no-stock-series`：可用交易日少于 `trigger_window` 时为 `insufficient-history`，此时 `observed_days` 为可用天数、`count` 为这些天中的达标数；无正股 CSV 或该 code 无序列时为 `no-stock-series`，此时 `count` 与 `observed_days` 为 `null`。达标判定含等号，`close == trigger_ratio × conv_price` 计入。
- `ytm` 是二分法数值解；在 `[-0.9999, 10.0]` 内无解时 `ytm` 为 `null` 并附 `ytm_note`。浮点保持原值，输出不做展示性四舍五入；手算末几位可能与输出不同。
- `summary` 含 `bond_count`、`conversion_premium_min`、`conversion_premium_max`、`conversion_premium_median`、`pure_bond_value_min`、`double_low_best`（按 `double_low` 升序前 5 条）、`triggered`、`insufficient_history`、`no_stock_series`；空集用空列表。
- 纯债价值是给定 `r` 下的折现结果，不是保本价格；YTM 是“持有到期、足额兑付、不扣税费”的内部收益率，不是可实现收益。
- 强赎计数只统计给定窗口内的收盘价，不补交易日、不换自然日，也不判断公告或赎回程序。
- 数据错误时脚本不修正、不插值、不猜条款；宁可报错退出，也不输出半成品。

## 风险与表达边界

- 不把转股溢价率当估值判断或买卖信号；同一溢价率可以对应完全不同的正股波动、条款、信用与流动性。
- 不把纯债价值（债底）当保本承诺：信用风险、违约、评级迁移、利率路径、流动性、税费与交易成本均未建模；债底只是给定贴现率下的算术参考，不是兑付保证。
- 不把强赎计数当必然触发：正股波动、下修、回售、公告口径、各家条款差异与计数起点均未建模；`triggered` 只说明给定窗口与参数下达标天数足够，不说明发行人将行使赎回权。
- 不把双低值当筛选结论或排名依据；它是价格与溢价率的固定线性组合，系数 100 是本方法的定义，不是市场共识或最优参数。
- 不把 YTM 当可实现收益：它是按当前价格与合同现金流反解的贴现率，假设持有到期、足额兑付、不扣税费；再投资路径、嵌入期权与违约均未建模。
- 不把示例数据、示例输出或合成情景当作真实行情、真实条款或业绩记录。
- 交付时同时给出输入口径、参数（`r`、`trigger_ratio`、`trigger_window`、`trigger_days`）、缺失数据与限制，不能只给一个溢价率、一个 YTM 或一份排名。
