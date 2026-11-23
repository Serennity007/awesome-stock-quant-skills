---
name: options-strategy-payoff
description: "个人期货期权组合到期损益工具：用多腿 CSV 计算净权利金、到期盈亏曲线、精确盈亏平衡点、有限或无限的最大盈利与最大亏损，并校验腿定义。适用于备兑、保护性看跌、领口、价差、跨式/宽跨式等组合的备课与复盘；不拉行情、不模拟盘中路径，也不把到期损益当成胜率或收益证明。"
license: MIT
metadata:
  author: Serennity007
---

# 我的期货期权组合到期损益方法

这套方法只回答一个机械问题：给定一份本地的多腿期权/期货定义，组合在到期时、不同标的到期价格下的损益是多少。它把腿定义、权利金口径、到期损益、盈亏平衡与最大盈亏分开处理，允许结论是“策略标签与腿结构可能不一致，需要人工核对”；不把任何组合叫成交易建议。

## 目标与边界

- 输入是研究者自己整理的腿表：买/卖、call/put/futures、行权价、数量、权利金（期货腿为入场价）、可选合约乘数。
- 输出是到期时点的损益算术：净权利金、给定价格表的逐点盈亏、精确盈亏平衡点、有限或无限的最大盈利与最大亏损。
- 只算**到期**：不考虑提前行权与被指派，不模拟盘中路径、波动率、Gamma 或到期前时间价值变化。
- 不建模保证金、担保品、权利金资金占用、手续费、滑点、融资成本、税费与汇率。
- 权利金、行权价、数量与乘数都是用户输入，不是行情报价，也不是交易所合约规格；策略名称由用户自报，脚本不验证它和腿结构是否匹配。
- 输出不是交易建议，也不是胜率、期望收益或历史业绩证明。

## 腿定义与符号约定

- CSV 必填列 `leg_id,instrument,side,strike,quantity,premium`，可选 `multiplier`（缺省 1）。`instrument` 取 `call/put/futures`，`side` 取 `buy/sell`，大小写不敏感。
- `leg_id` 非空且在同一文件内唯一；`quantity`、`multiplier`、call/put 的 `strike` 必须为有限正数；`premium` 必须为有限非负数。期货腿的 `premium` 是入场期货价格，必须为正。
- 期货腿的 `strike` 必须留空或写 `-`；给期货腿填数字行权价会被拒绝。
- 符号约定：`sign = +1`（buy），`-1`（sell）。期权腿入场现金流为 `-sign × quantity × premium × multiplier`，即买入支付、卖出收取权利金；期货腿入场没有权利金现金流。
- 净权利金 `net_premium` 只汇总期权腿的 `sign × quantity × premium × multiplier`：正数表示净支出权利金，负数表示净收取。期货腿的“权利金”列是入场价，不进入净权利金。
- 到期损益：期权腿为 `sign × quantity × multiplier × (内在价值 − premium)`，其中 call 内在价值 `max(S−K,0)`、put 为 `max(K−S,0)`；期货腿为 `sign × quantity × multiplier × (S − 入场价)`。
- 盈亏平衡点只在 `S>0` 上求分段线性损益的精确根，kink 位于各行权价；结果排序并保留 6 位小数。有界性只看右尾斜率 `SLOPE_HIGH`：向上无界则最大盈利为 `"unbounded"`，向下无界则最大亏损为 `"unbounded"`；其余取 `S=0` 边界与各行权价候选点上的极值。`S=0` 是定义域下界的有限极限，不是可成交价格。完整公式与退化情形见[到期损益方法](references/payoff-method.md)。

## 可复现的本地脚本

用 `scripts/options_strategy_payoff.py` 复算上述事实。脚本只用 Python 标准库，只读本地 CSV，不联网、不拉行情、不生成买卖指令。

```bash
python scripts/options_strategy_payoff.py --csv references/example-legs.csv --strategy covered-call-demo --prices 80 90 97 100 110 120 --out output/payoff.json
```

从本 Skill 目录运行。`--strategy` 是用户自报标签，只做非空校验；`--prices` 是自定义标的到期价格（有限正数），缺省时按每个期权行权价的 0.8/1.0/1.2 倍生成排序去重网格，没有期权行权价时必须显式提供；`--out` 以新文件创建，输入与已有输出都不会被覆盖。示例腿与示例输出均为明确标注的合成数据，字段约定见[输入与输出契约](references/data-contract.md)，逐项手算核对见[合成情景走查](references/example-analysis.md)。

## 输出与限制

- JSON 顶层包含 `schema_version`、`strategy`、`leg_count`、`legs`、`net_premium`、`net_premium_note`、`breakevens`、`breakeven_basis`、`max_profit`、`max_loss`、`price_grid`、`payoff_at_prices`、`scope`、`limitations`；命令行运行另加 `source_sha256`、`source_file`、`generated_at_utc`。
- `max_profit` / `max_loss` 为数字或字符串 `"unbounded"`；`breakevens` 可能为空列表，表示该损益在 `S>0` 上没有孤立零点。
- 数值保留浮点结果；盈亏平衡点四舍五入到 6 位小数，仅为展示，不改变判定。数据非法或文件读写失败时向 stderr 打印 `ERROR: ...` 并以退出码 2 结束；成功时打印一行英文摘要。
- 到期损益是价格与腿定义的机械结果，不含路径依赖、提前行权、保证金与费用，也不等于期望收益、胜率或可实现业绩。
- 具体合约乘数、行权价间距、行权方式（美式/欧式）、交割规则与保证金以交易所或经纪商规则为准；静态文档不充当当前合约规格。

## 风险与表达边界

- 不把到期损益曲线当作方向判断或进场信号；同一曲线可以来自完全不同的市场假设与持仓成本。
- 不把“最大亏损有限”解释为风险可接受：保证金、强平、流动性与跳空都可能让实际亏损超出到期损益。
- 不把 `"unbounded"` 标记当作可实现的无限收益；它是价格上升方向线性尾部的数学描述，不是风险上限。左尾不标无界，也不代表价格跌到 0 的损失是风险下限（负结算价未建模）。
- 不把本工具的输出或合成示例写成绩效记录、胜率或对某一行情的预测。
- 策略名称只是复盘标签；交付时同时给出腿结构、口径、价格网格与限制，不能只引用策略名。
