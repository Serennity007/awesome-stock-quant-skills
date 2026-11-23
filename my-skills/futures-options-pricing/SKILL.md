---
name: futures-options-pricing
description: "个人期货期权定价工具：用 Black-76 对同一期货合约的欧式看涨/看跌期权计算理论价、隐含波动率与 Delta/Gamma/Vega/Theta/Rho，并做看跌看涨平价残差校验。适用于期权报价合理性检查、波动率反推和组合敏感度备课；不拉行情、不保证单一波动率解，也不把理论价当成可成交价或收益证明。"
license: MIT
metadata:
  author: Serennity007
---

# 我的期货期权定价工具

这套个人工具在本地对一个期货合约、一个到期日的欧式期权报价批次做 Black-76 复算：给定期货价格、到期日、定价日与无风险利率，计算理论价、由市场价反推的隐含波动率，以及 Delta/Gamma/Vega/Theta/Rho，并对同一行权价的看涨/看跌做平价残差校验。价格与希腊字母都是模型输出，不是可成交报价。

## 目标与边界

- 只回答“在给定 Black-76 假设下，这批报价对应的理论价、隐含波动率和局部敏感度是多少”，不预测方向。
- 采用欧式行权近似，**不处理美式/提前行权**；交易所实际挂牌合约若可按美式行权，理论价可能偏低或偏高。
- 不建模分红、租赁利率（lease rate）、仓储/持有成本、手续费与买卖价差；不建模波动率微笑、期限结构、随机波动率或跳跃。
- 一次只处理一个期货价格、一个到期日；不合成期货曲线，也不处理合约乘数、保证金或资金占用。
- 输出只用于备课与研究记录；不生成组合层面的风险限额、保证金计算或交易计划。
- 本工具不构成交易建议，也不证明任何收益或胜率。

## 输入与定价口径

- 本地 CSV：必需 `option_id,option_type,strike`，可选 `market_price,volatility`；`option_type` 大小写不敏感并归一化为 `call/put`。每行至少要有一个价格或波动率输入。
- 时间口径固定为自然日/365：`T = (expiry - as_of) / 365`，`T` 必须为正；带时区的 `--as-of` 先换算到 UTC 再取日历日期。
- 定价公式、每单位/每波动率点/每年的约定见 [定价方法与约定](references/pricing-method.md)。
- 市场价格必须严格落在无套利上下界内才反推隐含波动率，否则对该行报错；字段含义与输入校验见 [输入与输出契约](references/data-contract.md)。

## 可复现的本地脚本

从本 Skill 目录运行，只读本地 CSV，不联网、不拉行情：

```bash
python scripts/futures_options_pricing.py --csv references/example-options.csv --futures-price 100 --expiry 2027-06-30 --as-of 2026-11-24 --rate 0.03 --out output/pricing.json
```

隐含波动率用有界二分求解：区间 `[1e-6, 5.0]`、最多 200 次迭代，不会无限循环；价格超出可达到范围或落在无套利带外时，脚本以非零退出并指出行。已有输出不会被覆盖，`--out` 不能等于 `--csv`。

## 输出与限制

JSON 顶层含 `schema_version`、`futures_price`、`as_of_date`、`expiry`、`days_to_expiry`、`time_to_expiry_years`、`rate`、`day_count_basis`、`source_sha256`、`options`、`parity_checks`、`scope`、`limitations`，并由 CLI 追加 `source_file` 与 `generated_at_utc`。逐行输出 `pricing_volatility`、`model_price`、`implied_volatility` 及其状态、`price_difference_vs_market` 与 `greeks`。

看跌看涨平价残差按 `C - P - e^{-rT}(F - K)` 计算，只在同一行权价同时存在看涨与看跌行时生成；`residual` 接近 0 只说明两行价格口径一致，不说明市场报价无套利。只给 `market_price` 的行会用反推的隐含波动率重新定价，因此 `price_difference_vs_market` 接近 0，这是复算而非独立理论价。`limitations` 至少列出欧式近似、单一波动率、自然日/365、无分红/租赁/仓储/费用/价差、理论价不是可成交价、单一隐含波动率根不证明唯一性六项。

合成示例的字段与手算核对见 [合成数据走查](references/example-analysis.md)；全部示例价格都是人为构造，不是市场报价。

## 风险与表达边界

- 理论价与希腊字母依赖输入假设，输入未经独立核验；不能当作市场公允价值、结算价或成交价。
- 隐含波动率在盘口噪声、行权价稀疏和流动性不足时不可靠；本工具只回报有界搜索内的一个根，不保证唯一或正确。
- 不把平价残差解释成套利机会：未计借券、资金成本、保证金、手续费与价差，也不判断可执行性。
- 不把模型输出改写成买卖指令、目标价、收益承诺或“稳赚”表述；组合敏感度只用于备课和风险讨论。
- 需要实际交易决策时，另行确认合约规则、行权方式、保证金、费用与数据来源。
