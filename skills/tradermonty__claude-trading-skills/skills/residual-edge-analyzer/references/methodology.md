# Methodology

## Model

For strategy return \(r_t\) and declared baseline returns \(f_t\), estimate:

\[
r_t = \alpha + \beta^\top f_t + \epsilon_t
\]

Report:

- `alpha`: periodic intercept and arithmetic annualization;
- `loadings`: baseline coefficients;
- `R-squared`: share of strategy-return variance explained by the complete fitted model;
- `residual volatility`: sample volatility of \(\epsilon_t\);
- `residual edge ratio`: \(\alpha A / (\sigma_\epsilon \sqrt{A})\), where \(A\) is
  the annualization factor.

With an intercept, OLS residuals sum to approximately zero. Therefore, a raw residual-mean
Sharpe is not an alpha measure. The residual edge ratio used here is an appraisal or
information-ratio-style statistic.

## Inference

Use heteroskedasticity and autocorrelation consistent Newey-West covariance. `hac_lags:
"auto"` uses the common \(floor(4(n/100)^{2/9})\) lag rule. Treat the t-statistic as
asymptotic evidence, not proof, especially in short, non-stationary samples.

Review lag-one residual autocorrelation and Durbin-Watson diagnostics. HAC inference does
not make a misspecified model correct.

## Multiple baselines

The primary model expresses the predeclared hypothesis. Sensitivity models answer whether
the conclusion survives plausible alternate explanations.

For multi-factor models, inspect variance inflation factors:

- around 1: little linear redundancy;
- above 5: investigate;
- above 10 or undefined: treat coefficients as unstable.

Do not interpret individual loadings when baselines are strongly collinear.

## Rolling stability

Refit the same declared model over a fixed trailing window. Compare rolling R-squared,
annualized alpha, residual edge ratio, and the fraction of windows with positive alpha.
Choose the window before looking at the output.

Rolling estimates overlap and are not independent tests. Use them to locate instability,
not to multiply significance claims.

Locating instability requires many refits. The analyzer therefore refuses to report
rolling stability unless at least `minimum_rolling_windows` windows fit in the series,
defaulting to 12. With one window the positive-alpha fraction is exactly 0.0 or 1.0 and
carries no information about stability, so the model falls to `RESIDUAL_FRAGILE`
instead.

## Regime breakdown

Apply categorical regime labels supplied in the CSV to the primary model's active return,
which is strategy return minus the baseline-loading component. Mark groups below
`minimum_regime_observations` as `THIN`.

Prefer two or three economically motivated regimes. Regime mining after observing losses
creates multiple-testing and overfitting risk.

## Interpretation limits

- Return regression describes covariance with supplied baselines; it does not prove a
  causal mechanism.
- A missing baseline can make alpha look independent.
- A post-hoc baseline can make alpha disappear or appear.
- Same-universe baselines require point-in-time constituents and historical construction
  rules.
- Strategy and baseline returns must use comparable gross/net costs, cash treatment,
  leverage, calendar, and rebalance timing.
- In-sample results require untouched out-of-sample or live confirmation.
- High R-squared does not measure capacity, tail protection, tax value, or operational
  usefulness.
- This method is not Brinson holdings attribution and is not feature-level Shapley risk
  attribution.
