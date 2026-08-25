# Input Contract

## CSV

Use one aligned CSV. Dates must be unique ISO `YYYY-MM-DD` values. Return cells must be
finite simple period returns greater than -100%.

```csv
date,strategy_return,market_return,equal_weight_return,momentum_return,volatility_regime
2025-01-02,0.0060,0.0030,0.0035,0.0010,low
2025-01-03,-0.0010,-0.0020,-0.0015,0.0005,low
2025-01-06,0.0080,0.0040,0.0045,0.0020,high
```

Use decimal returns by default. Set `return_unit` to `percent` only when `0.6` means
`0.6%`.

The analyzer sorts rows by date but warns when reordering was necessary. It rejects
duplicates, missing selected columns, missing numeric values, non-finite values, and
returns at or below -100%.

## JSON specification

```json
{
  "schema_version": "1.0",
  "date_column": "date",
  "strategy_column": "strategy_return",
  "return_unit": "decimal",
  "frequency": "daily",
  "primary_model": {
    "name": "market",
    "baseline_columns": ["market_return"]
  },
  "sensitivity_models": [
    {
      "name": "equal_weight",
      "baseline_columns": ["equal_weight_return"]
    },
    {
      "name": "market_plus_momentum",
      "baseline_columns": ["market_return", "momentum_return"]
    }
  ],
  "regime_columns": ["volatility_regime"],
  "rolling_window": 63,
  "minimum_observations": 60,
  "minimum_regime_observations": 20,
  "minimum_rolling_windows": 12,
  "hac_lags": "auto",
  "include_series": true,
  "data_declarations": {
    "baseline_selection": "predeclared",
    "strategy_return_basis": "net",
    "baseline_return_basis": "net",
    "analysis_scope": "out_of_sample",
    "universe_data": "point_in_time"
  }
}
```

`include_series` must be a JSON boolean. Use `false` to omit the dated primary-model
observation series; strings such as `"false"` are rejected.

### Model rules

- `primary_model` is required.
- Each model requires a unique `name` and one or more unique `baseline_columns`.
- `sensitivity_models` is optional syntactically, but omitting it produces an evidence
  warning.
- Put multiple columns in one model to estimate simultaneous factor loadings.
- Do not reuse the date or strategy column as a baseline.

### Frequency and annualization

Defaults are 252 for daily, 52 for weekly, and 12 for monthly data. Override with a
positive integer `annualization_factor` only when the return calendar justifies it.

### Optional thresholds

```json
{
  "thresholds": {
    "baseline_explained_r2_min": 0.75,
    "weak_edge_ratio_max": 0.5,
    "residual_edge_ratio_min": 0.75,
    "alpha_t_stat_min": 2.0,
    "rolling_positive_fraction_min": 0.6
  }
}
```

Thresholds are transparent diagnostic policy, not universal laws. Keep them fixed before
inspecting the result when comparing strategies.

The evidence floor is the larger of `minimum_observations` and ten observations per
estimated parameter, including the intercept. Falling below that floor produces
`INSUFFICIENT_EVIDENCE`; it does not prevent exploratory metrics from being emitted.

### Rolling coverage floor

`minimum_rolling_windows` defaults to 12 and must be an integer of 2 or more. The
rolling check needs `rolling_window + minimum_rolling_windows - 1` observations. Below
that the rolling block reports `enabled: false` with the shortfall, and the model falls
to `RESIDUAL_FRAGILE`.

The floor exists because `positive_alpha_fraction` is only stability evidence when it is
measured across many refits. With a single window it is exactly 0.0 or 1.0 and clears
`rolling_positive_fraction_min` trivially, which would let a 60-observation series with
`rolling_window: 60` reach `RESIDUAL_EDGE` on one regression.

## Outputs

The JSON report includes:

- normalized data provenance and declarations;
- total strategy metrics;
- primary and sensitivity model coefficients;
- annualized alpha with HAC inference;
- R-squared and adjusted R-squared;
- residual volatility, edge ratio, autocorrelation, and active-return drawdown;
- VIF diagnostics;
- rolling stability;
- optional primary-model observation series;
- regime breakdowns;
- structured warnings and a non-execution verdict.

`baseline_explained_return` is the factor-loading component without the intercept.
`active_return` equals strategy return minus that component, so its mean contains alpha.
`residual` equals strategy return minus the complete fitted model and has approximately
zero sample mean.
