# Black-76 定价与希腊字母口径

本文件固定 `scripts/futures_options_pricing.py` 的数学定义。所有价格都是**单一期货价格 F** 下的欧式期权理论值；不声称与交易所结算规则、做市商报价或可成交价格一致。

## 符号与假设

- `F`：标的期货价格，有限正数；同一批次所有行共用 `--futures-price` 一个值。
- `K`：行权价，有限正数。
- `T`：到期时间（年），按 `T = 日历天数 / 365` 计算；日历天数由 `--expiry` 日期减 `--as-of` 日期得到，必须为正。带时区的 `--as-of` 先换算成 UTC 再取日历日期。
- `r`：连续复利、按年化的无风险利率，小数形式（`0.03` 表示 3%）。允许负值，但绝对值不得超过 1.0。
- `sigma`：每行的定价波动率，年化小数；同一行内视为常数，不随行权价、期限或时间变化。
- 假设：无分红、无租赁利率（lease rate）、无仓储/持有成本、无交易费用与买卖价差；欧式行权，到期前不可行权。

## 分布函数

- `N(x) = 0.5 * (1 + erf(x / sqrt(2)))`，标准正态分布函数，用 `math.erf` 实现。
- `n(x) = exp(-x*x/2) / sqrt(2*pi)`，标准正态密度函数。

## 定价公式

```text
d1 = (ln(F/K) + 0.5*sigma^2*T) / (sigma*sqrt(T))
d2 = d1 - sigma*sqrt(T)

Call = e^{-rT} * (F*N(d1) - K*N(d2))
Put  = e^{-rT} * (K*N(-d2) - F*N(-d1))
```

`T = 0`、`F <= 0`、`K <= 0`、`sigma <= 0`、任何非有限输入都直接抛 `ValueError`，不返回 `NaN` 或默认值。

## 希腊字母

```text
delta_call = e^{-rT} * N(d1)
delta_put  = -e^{-rT} * N(-d1)
gamma      = e^{-rT} * n(d1) / (F * sigma * sqrt(T))
vega_per_unit_vol  = e^{-rT} * F * n(d1) * sqrt(T)   # sigma 变化 1.00 的价格变化
vega_per_vol_point = vega_per_unit_vol / 100         # sigma 变化 1 个波动率点（0.01）的价格变化
theta_per_year = -e^{-rT} * F * n(d1) * sigma / (2*sqrt(T)) + r*Price   # theta = -dPrice/dT
theta_per_day  = theta_per_year / 365
rho_per_1_rate = -T * Price                          # 利率变化 1.00 的价格变化
```

其中 `Price` 是该行同一 `option_type` 的 Black-76 价格（看涨用 Call、看跌用 Put），所以 `+r*Price` 项对看涨、看跌分别使用各自的折现价。theta 的符号约定是**每单位日历时间的价格变化**，即 `theta = -dPrice/dT`：在其他条件不变时 `T` 增加一年，价格变化的相反数。`theta_per_day` 只是该值除以 365，不区分交易日与自然日。

## 看跌看涨平价残差

同一行权价 K 同时存在看涨行与看跌行时，输出：

```text
discounted_forward_intrinsic = e^{-rT} * (F - K)
call_minus_put = call_model_price - put_model_price
residual = call_minus_put - discounted_forward_intrinsic
```

Black-76 在完全一致的输入下应得到 `call_minus_put = e^{-rT}(F - K)`，所以残差只反映两行的模型价格口径差异，例如两行使用不同的定价波动率、或市场报价本身不满足平价。残差接近 0 **不**证明市场无套利，也不构成套利机会判断；未计入借券、资金、保证金和手续费。

## 隐含波动率的反推

当某行提供 `market_price` 时，脚本按有界二分求解隐波：

1. 先检查价格严格落在无套利带内（小容差 `1e-12`）：
   - 看涨：`max(0, e^{-rT}(F-K)) < p < e^{-rT}F`
   - 看跌：`max(0, e^{-rT}(K-F)) < p < e^{-rT}K`
   否则抛出指出行 `option_id` 的 `ValueError`。
2. 再检查价格是否落在搜索区间 `[1e-6, 5.0]` 可达到的价格范围内；超出则同样报错。
3. 最多 200 次二分迭代，价格差容差 `1e-12`，区间宽度低于 `1e-15` 时提前结束；循环次数固定，不会无限循环。

求解失败会直接报错，不会静默返回 `None`。成功时 `implied_volatility_status` 为 `solved`；只给 `volatility`、没给 `market_price` 的行不反推，状态为 `not_requested`。

## 定价波动率的选择

- 行内提供 `volatility` 时，`pricing_volatility` 使用该值，`model_price` 与希腊字母都按它计算；若同时提供 `market_price`，还额外反推 `implied_volatility`，`price_difference_vs_market` 才是“给定波动率理论价减市场价”。
- 行内只有 `market_price` 时，`pricing_volatility` 取反推的隐含波动率，因此 `model_price` 是用该波动率重算的报价，`price_difference_vs_market` 接近 0；这是复算，不是独立理论价。

## 限制清单

- 欧式行权近似；交易所若按美式行权，提前行权价值与理论价可能不同。
- 每行一个常数波动率；没有波动率微笑、期限结构、随机波动率、跳跃或波动率风险溢价建模。
- 自然日/365 年计数；没有交易日、假期、交易时段或结算日调整。
- 不建模分红、租赁利率、仓储/持有成本、交易费用、保证金与买卖价差。
- 理论价不是可成交报价、结算价或市场公允价值；不能直接用于下单价。
- 定价公式与希腊字母依赖输入假设；输入未经独立核验时，输出只说明在这组假设下的复算结果。
- 有界搜索内的单一隐含波动率根不证明唯一性、正确性或市场可成交性。
- `parity_checks` 只做同一行权价的代数残差，不是套利检验或交易策略。
