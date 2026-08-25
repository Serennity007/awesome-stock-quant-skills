#!/usr/bin/env python3
"""Separate declared baseline exposure from residual strategy edge.

The script consumes one aligned CSV and one JSON analysis specification. It
fits OLS models with an intercept, reports HAC (Newey-West) inference, and
defines the residual edge ratio as annualized alpha divided by annualized
residual volatility. This is equivalent to an appraisal/information ratio;
the raw OLS residual mean is zero when an intercept is present.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
EPSILON = 1e-12
ANNUALIZATION_FACTORS = {"daily": 252, "weekly": 52, "monthly": 12}
DEFAULT_THRESHOLDS = {
    "baseline_explained_r2_min": 0.75,
    "weak_edge_ratio_max": 0.50,
    "residual_edge_ratio_min": 0.75,
    "alpha_t_stat_min": 2.0,
    "rolling_positive_fraction_min": 0.60,
}
# `positive_alpha_fraction` is only evidence of stability when it is measured
# across many refits. With a handful of windows it is a coarse ratio that
# clears any threshold trivially — one window makes it exactly 0.0 or 1.0 —
# so the rolling check fails closed below this count.
DEFAULT_MINIMUM_ROLLING_WINDOWS = 12
ALLOWED_CONFIG_KEYS = {
    "schema_version",
    "date_column",
    "strategy_column",
    "return_unit",
    "frequency",
    "annualization_factor",
    "primary_model",
    "sensitivity_models",
    "regime_columns",
    "rolling_window",
    "minimum_observations",
    "minimum_regime_observations",
    "minimum_rolling_windows",
    "hac_lags",
    "include_series",
    "thresholds",
    "data_declarations",
}
DECLARATION_VALUES = {
    "baseline_selection": {"predeclared", "post_hoc", "unknown"},
    "strategy_return_basis": {"gross", "net", "unknown"},
    "baseline_return_basis": {"gross", "net", "unknown"},
    "analysis_scope": {"in_sample", "out_of_sample", "live", "unknown"},
    "universe_data": {
        "point_in_time",
        "current_constituents",
        "not_applicable",
        "unknown",
    },
}


class AnalysisError(ValueError):
    """Raised when the input contract cannot support a valid analysis."""


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    center = _mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1))


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if abs(denominator) <= EPSILON:
        return None
    return numerator / denominator


def _round_value(value: Any, digits: int = 10) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return round(value, digits)
    if isinstance(value, list):
        return [_round_value(item, digits) for item in value]
    if isinstance(value, dict):
        return {key: _round_value(item, digits) for key, item in value.items()}
    return value


def _matmul(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    if not left or not right:
        return []
    return [
        [
            sum(left[row][k] * right[k][col] for k in range(len(right)))
            for col in range(len(right[0]))
        ]
        for row in range(len(left))
    ]


def _transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix)]


def _solve_and_inverse(
    matrix: list[list[float]], vector: list[float]
) -> tuple[list[float], list[list[float]], float]:
    """Solve Ax=b and invert A with partial-pivot Gauss-Jordan elimination."""
    size = len(matrix)
    augmented = [
        list(matrix[row]) + [1.0 if row == col else 0.0 for col in range(size)] + [vector[row]]
        for row in range(size)
    ]
    pivots: list[float] = []

    for col in range(size):
        pivot_row = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        pivot = augmented[pivot_row][col]
        if abs(pivot) <= EPSILON:
            raise AnalysisError("Baseline matrix is rank deficient; remove duplicate factors.")
        augmented[col], augmented[pivot_row] = augmented[pivot_row], augmented[col]
        pivots.append(abs(pivot))

        divisor = augmented[col][col]
        augmented[col] = [value / divisor for value in augmented[col]]
        for row in range(size):
            if row == col:
                continue
            multiplier = augmented[row][col]
            if abs(multiplier) <= EPSILON:
                continue
            augmented[row] = [
                current - multiplier * pivot_value
                for current, pivot_value in zip(augmented[row], augmented[col])
            ]

    inverse = [row[size : 2 * size] for row in augmented]
    solution = [row[-1] for row in augmented]
    pivot_ratio = min(pivots) / max(pivots)
    return solution, inverse, pivot_ratio


def _cross_product(design: list[list[float]]) -> list[list[float]]:
    width = len(design[0])
    return [
        [sum(row[left] * row[right] for row in design) for right in range(width)]
        for left in range(width)
    ]


def _cross_vector(design: list[list[float]], values: list[float]) -> list[float]:
    width = len(design[0])
    return [sum(row[col] * value for row, value in zip(design, values)) for col in range(width)]


def _quadratic_form(vector: list[float], matrix: list[list[float]]) -> float:
    return sum(
        vector[row] * matrix[row][col] * vector[col]
        for row in range(len(vector))
        for col in range(len(vector))
    )


def _automatic_hac_lags(observation_count: int) -> int:
    return max(0, int(math.floor(4 * (observation_count / 100) ** (2 / 9))))


def _newey_west_covariance(
    design: list[list[float]],
    residuals: list[float],
    inverse_xtx: list[list[float]],
    lags: int,
) -> list[list[float]]:
    width = len(design[0])
    meat = [[0.0 for _ in range(width)] for _ in range(width)]

    for row, residual in zip(design, residuals):
        for left in range(width):
            for right in range(width):
                meat[left][right] += residual * residual * row[left] * row[right]

    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1.0)
        for current in range(lag, len(design)):
            previous = current - lag
            product = residuals[current] * residuals[previous]
            for left in range(width):
                for right in range(width):
                    meat[left][right] += (
                        weight
                        * product
                        * (
                            design[current][left] * design[previous][right]
                            + design[previous][left] * design[current][right]
                        )
                    )

    correction = len(design) / max(1, len(design) - width)
    meat = [[value * correction for value in row] for row in meat]
    return _matmul(_matmul(inverse_xtx, meat), inverse_xtx)


def _coefficient_transform(means: list[float], scales: list[float]) -> list[list[float]]:
    width = len(means) + 1
    transform = [[0.0 for _ in range(width)] for _ in range(width)]
    transform[0][0] = 1.0
    for index, (center, scale) in enumerate(zip(means, scales), start=1):
        transform[0][index] = -center / scale
        transform[index][index] = 1.0 / scale
    return transform


def _lag_one_autocorrelation(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    center = _mean(values)
    denominator = sum((value - center) ** 2 for value in values)
    if denominator <= EPSILON:
        return None
    numerator = sum(
        (values[index] - center) * (values[index - 1] - center) for index in range(1, len(values))
    )
    return numerator / denominator


def _durbin_watson(values: list[float]) -> float | None:
    denominator = sum(value * value for value in values)
    if denominator <= EPSILON:
        return None
    numerator = sum((values[index] - values[index - 1]) ** 2 for index in range(1, len(values)))
    return numerator / denominator


def _max_drawdown(returns: list[float]) -> float | None:
    wealth = 1.0
    peak = 1.0
    worst = 0.0
    for period_return in returns:
        if period_return <= -1.0:
            return None
        wealth *= 1.0 + period_return
        peak = max(peak, wealth)
        worst = min(worst, wealth / peak - 1.0)
    return worst


def _performance_metrics(returns: list[float], annualization_factor: int) -> dict[str, Any]:
    periodic_mean = _mean(returns)
    periodic_volatility = _sample_std(returns)
    annualized_return = periodic_mean * annualization_factor
    annualized_volatility = periodic_volatility * math.sqrt(annualization_factor)
    return {
        "periodic_mean": periodic_mean,
        "periodic_volatility": periodic_volatility,
        "annualized_arithmetic_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_zero_rate": _safe_ratio(annualized_return, annualized_volatility),
        "max_drawdown": _max_drawdown(returns),
    }


def _r_squared(target: list[float], fitted: list[float]) -> float:
    center = _mean(target)
    total = sum((value - center) ** 2 for value in target)
    if total <= EPSILON:
        raise AnalysisError("Strategy returns have zero variance.")
    residual = sum((actual - predicted) ** 2 for actual, predicted in zip(target, fitted))
    return 1.0 - residual / total


def _regression_r_squared(target: list[float], factors: list[list[float]]) -> float:
    if not factors:
        return 0.0
    result = fit_regression(
        target,
        factors,
        [f"factor_{index}" for index in range(len(factors))],
        calculate_vif=False,
    )
    return result["r_squared"]


def _variance_inflation_factors(
    factor_columns: list[list[float]], factor_names: list[str]
) -> dict[str, float | None]:
    if len(factor_columns) == 1:
        return {factor_names[0]: 1.0}

    result: dict[str, float | None] = {}
    for index, name in enumerate(factor_names):
        others = [
            column for other_index, column in enumerate(factor_columns) if other_index != index
        ]
        try:
            r_squared = _regression_r_squared(factor_columns[index], others)
        except AnalysisError:
            result[name] = None
            continue
        result[name] = None if r_squared >= 1.0 - 1e-10 else 1.0 / (1.0 - r_squared)
    return result


def fit_regression(
    strategy_returns: list[float],
    factor_columns: list[list[float]],
    factor_names: list[str],
    hac_lags: int | None = None,
    calculate_vif: bool = True,
) -> dict[str, Any]:
    """Fit an intercept OLS model and return residual-edge diagnostics."""
    observation_count = len(strategy_returns)
    if not factor_columns:
        raise AnalysisError("At least one baseline column is required.")
    if any(len(column) != observation_count for column in factor_columns):
        raise AnalysisError("All return series must have the same number of observations.")
    if observation_count <= len(factor_columns) + 1:
        raise AnalysisError("Too few observations for the requested baseline model.")
    if len(factor_columns) != len(factor_names):
        raise AnalysisError("Factor names do not match factor columns.")

    means = [_mean(column) for column in factor_columns]
    scales = [
        math.sqrt(sum((value - center) ** 2 for value in column) / observation_count)
        for column, center in zip(factor_columns, means)
    ]
    zero_variance = [name for name, scale in zip(factor_names, scales) if abs(scale) <= EPSILON]
    if zero_variance:
        raise AnalysisError(
            "Baseline columns have zero variance: " + ", ".join(sorted(zero_variance))
        )

    standardized = [
        [(value - center) / scale for value in column]
        for column, center, scale in zip(factor_columns, means, scales)
    ]
    design = [[1.0] + [column[row] for column in standardized] for row in range(observation_count)]
    xtx = _cross_product(design)
    xty = _cross_vector(design, strategy_returns)
    standardized_coefficients, inverse_xtx, pivot_ratio = _solve_and_inverse(xtx, xty)

    transform = _coefficient_transform(means, scales)
    original_coefficients = [
        sum(transform[row][col] * standardized_coefficients[col] for col in range(len(transform)))
        for row in range(len(transform))
    ]
    intercept = original_coefficients[0]
    loadings = original_coefficients[1:]
    baseline_explained = [
        sum(loading * column[row] for loading, column in zip(loadings, factor_columns))
        for row in range(observation_count)
    ]
    fitted = [intercept + explained for explained in baseline_explained]
    residuals = [actual - predicted for actual, predicted in zip(strategy_returns, fitted)]
    active_returns = [
        actual - explained for actual, explained in zip(strategy_returns, baseline_explained)
    ]

    model_r_squared = _r_squared(strategy_returns, fitted)
    parameter_count = len(original_coefficients)
    adjusted_r_squared = 1.0 - (1.0 - model_r_squared) * (
        (observation_count - 1) / (observation_count - parameter_count)
    )

    lags = _automatic_hac_lags(observation_count) if hac_lags is None else hac_lags
    lags = min(max(0, lags), observation_count - 1)
    standardized_covariance = _newey_west_covariance(design, residuals, inverse_xtx, lags)
    original_covariance = _matmul(
        _matmul(transform, standardized_covariance), _transpose(transform)
    )
    standard_errors = [
        math.sqrt(max(0.0, original_covariance[index][index])) for index in range(parameter_count)
    ]

    coefficients = []
    names = ["intercept", *factor_names]
    for name, estimate, standard_error in zip(names, original_coefficients, standard_errors):
        coefficients.append(
            {
                "name": name,
                "estimate": estimate,
                "hac_standard_error": standard_error,
                "t_stat": _safe_ratio(estimate, standard_error),
            }
        )

    return {
        "observation_count": observation_count,
        "coefficients": coefficients,
        "intercept": intercept,
        "loadings": dict(zip(factor_names, loadings)),
        "r_squared": model_r_squared,
        "adjusted_r_squared": adjusted_r_squared,
        "hac_lags": lags,
        "pivot_ratio": pivot_ratio,
        "residuals": residuals,
        "active_returns": active_returns,
        "baseline_explained_returns": baseline_explained,
        "fitted_returns": fitted,
        "residual_volatility_periodic": _sample_std(residuals),
        "lag_one_residual_autocorrelation": _lag_one_autocorrelation(residuals),
        "durbin_watson": _durbin_watson(residuals),
        "vif": (_variance_inflation_factors(factor_columns, factor_names) if calculate_vif else {}),
    }


def _validate_model(model: Any, label: str) -> dict[str, Any]:
    if not isinstance(model, dict):
        raise AnalysisError(f"{label} must be an object.")
    name = model.get("name")
    columns = model.get("baseline_columns")
    if not isinstance(name, str) or not name.strip():
        raise AnalysisError(f"{label}.name must be a non-empty string.")
    if (
        not isinstance(columns, list)
        or not columns
        or any(not isinstance(column, str) or not column.strip() for column in columns)
    ):
        raise AnalysisError(f"{label}.baseline_columns must be a non-empty string list.")
    if len(set(columns)) != len(columns):
        raise AnalysisError(f"{label}.baseline_columns contains duplicates.")
    return {"name": name.strip(), "baseline_columns": columns}


def load_config(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"Cannot read config: {exc}") from exc
    if not isinstance(raw, dict):
        raise AnalysisError("Config root must be an object.")

    unknown = sorted(set(raw) - ALLOWED_CONFIG_KEYS)
    if unknown:
        raise AnalysisError("Unknown config keys: " + ", ".join(unknown))
    if raw.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise AnalysisError(f"schema_version must be {SCHEMA_VERSION}.")

    date_column = raw.get("date_column", "date")
    strategy_column = raw.get("strategy_column", "strategy_return")
    if not isinstance(date_column, str) or not date_column:
        raise AnalysisError("date_column must be a non-empty string.")
    if not isinstance(strategy_column, str) or not strategy_column:
        raise AnalysisError("strategy_column must be a non-empty string.")

    return_unit = raw.get("return_unit", "decimal")
    if return_unit not in {"decimal", "percent"}:
        raise AnalysisError("return_unit must be decimal or percent.")
    frequency = raw.get("frequency", "daily")
    if frequency not in ANNUALIZATION_FACTORS:
        raise AnalysisError("frequency must be daily, weekly, or monthly.")
    annualization_factor = raw.get("annualization_factor", ANNUALIZATION_FACTORS[frequency])
    if (
        not isinstance(annualization_factor, int)
        or isinstance(annualization_factor, bool)
        or annualization_factor <= 0
    ):
        raise AnalysisError("annualization_factor must be a positive integer.")

    primary_model = _validate_model(raw.get("primary_model"), "primary_model")
    sensitivity_raw = raw.get("sensitivity_models", [])
    if not isinstance(sensitivity_raw, list):
        raise AnalysisError("sensitivity_models must be a list.")
    sensitivity_models = [
        _validate_model(model, f"sensitivity_models[{index}]")
        for index, model in enumerate(sensitivity_raw)
    ]
    model_names = [primary_model["name"], *[model["name"] for model in sensitivity_models]]
    if len(set(model_names)) != len(model_names):
        raise AnalysisError("Model names must be unique.")

    models = [primary_model, *sensitivity_models]
    signatures = [tuple(sorted(model["baseline_columns"])) for model in models]
    if len(set(signatures)) != len(signatures):
        raise AnalysisError("Each sensitivity model must use a distinct baseline set.")

    all_baselines = {column for model in models for column in model["baseline_columns"]}
    protected_columns = {date_column, strategy_column}
    conflict = sorted(all_baselines & protected_columns)
    if conflict:
        raise AnalysisError(
            "Baseline columns conflict with date/strategy columns: " + ", ".join(conflict)
        )

    regime_columns = raw.get("regime_columns", [])
    if (
        not isinstance(regime_columns, list)
        or any(not isinstance(column, str) or not column for column in regime_columns)
        or len(set(regime_columns)) != len(regime_columns)
    ):
        raise AnalysisError("regime_columns must be a unique string list.")
    regime_conflict = sorted(set(regime_columns) & (protected_columns | all_baselines))
    if regime_conflict:
        raise AnalysisError(
            "Regime columns conflict with date/return columns: " + ", ".join(regime_conflict)
        )

    minimum_observations = raw.get("minimum_observations", 60)
    minimum_regime_observations = raw.get("minimum_regime_observations", 20)
    minimum_rolling_windows = raw.get("minimum_rolling_windows", DEFAULT_MINIMUM_ROLLING_WINDOWS)
    rolling_window = raw.get(
        "rolling_window", {"daily": 63, "weekly": 52, "monthly": 24}[frequency]
    )
    for name, value, minimum in (
        ("minimum_observations", minimum_observations, 10),
        ("minimum_regime_observations", minimum_regime_observations, 2),
        ("minimum_rolling_windows", minimum_rolling_windows, 2),
        ("rolling_window", rolling_window, 0),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise AnalysisError(f"{name} must be an integer >= {minimum}.")

    hac_lags = raw.get("hac_lags", "auto")
    if hac_lags != "auto" and (
        not isinstance(hac_lags, int) or isinstance(hac_lags, bool) or hac_lags < 0
    ):
        raise AnalysisError("hac_lags must be auto or a non-negative integer.")

    include_series = raw.get("include_series", True)
    if not isinstance(include_series, bool):
        raise AnalysisError("include_series must be a JSON boolean.")

    thresholds = dict(DEFAULT_THRESHOLDS)
    supplied_thresholds = raw.get("thresholds", {})
    if not isinstance(supplied_thresholds, dict):
        raise AnalysisError("thresholds must be an object.")
    unknown_thresholds = sorted(set(supplied_thresholds) - set(DEFAULT_THRESHOLDS))
    if unknown_thresholds:
        raise AnalysisError("Unknown thresholds: " + ", ".join(unknown_thresholds))
    for name, value in supplied_thresholds.items():
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            raise AnalysisError(f"thresholds.{name} must be finite numeric.")
        thresholds[name] = float(value)
    for fractional in (
        "baseline_explained_r2_min",
        "rolling_positive_fraction_min",
    ):
        if not 0 <= thresholds[fractional] <= 1:
            raise AnalysisError(f"thresholds.{fractional} must be between 0 and 1.")
    for nonnegative in (
        "weak_edge_ratio_max",
        "residual_edge_ratio_min",
        "alpha_t_stat_min",
    ):
        if thresholds[nonnegative] < 0:
            raise AnalysisError(f"thresholds.{nonnegative} must be non-negative.")

    declarations = raw.get("data_declarations", {})
    if not isinstance(declarations, dict):
        raise AnalysisError("data_declarations must be an object.")
    unknown_declarations = sorted(set(declarations) - set(DECLARATION_VALUES))
    if unknown_declarations:
        raise AnalysisError("Unknown data_declarations keys: " + ", ".join(unknown_declarations))
    for name, allowed in DECLARATION_VALUES.items():
        value = declarations.get(name, "unknown")
        if value not in allowed:
            raise AnalysisError(
                f"data_declarations.{name} must be one of: {', '.join(sorted(allowed))}."
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "date_column": date_column,
        "strategy_column": strategy_column,
        "return_unit": return_unit,
        "frequency": frequency,
        "annualization_factor": annualization_factor,
        "primary_model": primary_model,
        "sensitivity_models": sensitivity_models,
        "regime_columns": regime_columns,
        "minimum_observations": minimum_observations,
        "minimum_regime_observations": minimum_regime_observations,
        "minimum_rolling_windows": minimum_rolling_windows,
        "rolling_window": rolling_window,
        "hac_lags": hac_lags,
        "include_series": include_series,
        "thresholds": thresholds,
        "data_declarations": declarations,
    }


def load_dataset(csv_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    model_list = [config["primary_model"], *config["sensitivity_models"]]
    baseline_columns = sorted(
        {column for model in model_list for column in model["baseline_columns"]}
    )
    required_columns = {
        config["date_column"],
        config["strategy_column"],
        *baseline_columns,
        *config["regime_columns"],
    }
    rows: list[dict[str, Any]] = []

    try:
        handle = csv_path.open(encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise AnalysisError(f"Cannot read CSV: {exc}") from exc

    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AnalysisError("CSV has no header.")
        missing = sorted(required_columns - set(reader.fieldnames))
        if missing:
            raise AnalysisError("CSV is missing columns: " + ", ".join(missing))

        for line_number, raw in enumerate(reader, start=2):
            raw_date = (raw.get(config["date_column"]) or "").strip()
            try:
                parsed_date = date.fromisoformat(raw_date)
            except ValueError as exc:
                raise AnalysisError(
                    f"Invalid ISO date at CSV line {line_number}: {raw_date!r}"
                ) from exc

            numeric: dict[str, float] = {}
            for column in [config["strategy_column"], *baseline_columns]:
                value = (raw.get(column) or "").strip()
                try:
                    parsed = float(value)
                except ValueError as exc:
                    raise AnalysisError(
                        f"Invalid numeric value at CSV line {line_number}, column {column}: {value!r}"
                    ) from exc
                if not math.isfinite(parsed):
                    raise AnalysisError(
                        f"Non-finite value at CSV line {line_number}, column {column}."
                    )
                if config["return_unit"] == "percent":
                    parsed /= 100.0
                if parsed <= -1.0:
                    raise AnalysisError(
                        f"Return <= -100% at CSV line {line_number}, column {column}."
                    )
                numeric[column] = parsed

            regimes = {
                column: ((raw.get(column) or "").strip() or "__MISSING__")
                for column in config["regime_columns"]
            }
            rows.append({"date": parsed_date, "numeric": numeric, "regimes": regimes})

    if not rows:
        raise AnalysisError("CSV contains no data rows.")
    input_order = [row["date"] for row in rows]
    duplicate_dates = sorted(value for value, count in Counter(input_order).items() if count > 1)
    if duplicate_dates:
        display = ", ".join(value.isoformat() for value in duplicate_dates[:5])
        raise AnalysisError(f"CSV contains duplicate dates: {display}")
    was_sorted = input_order == sorted(input_order)
    rows.sort(key=lambda row: row["date"])

    return {
        "rows": rows,
        "baseline_columns": baseline_columns,
        "was_sorted": was_sorted,
    }


def _declaration_warnings(config: dict[str, Any]) -> list[dict[str, str]]:
    declarations = config["data_declarations"]
    warnings: list[dict[str, str]] = []

    baseline_selection = declarations.get("baseline_selection", "unknown")
    if baseline_selection != "predeclared":
        warnings.append(
            {
                "id": "BASELINE_SELECTION_NOT_PREDECLARED",
                "severity": "high",
                "message": "Declare baselines before inspecting results; post-hoc selection can manufacture residual edge.",
            }
        )

    universe_data = declarations.get("universe_data", "unknown")
    if universe_data == "current_constituents":
        warnings.append(
            {
                "id": "SURVIVORSHIP_BIAS_RISK",
                "severity": "high",
                "message": "A current-constituent baseline is not point-in-time and can introduce survivorship bias.",
            }
        )
    elif universe_data == "unknown":
        warnings.append(
            {
                "id": "UNIVERSE_PROVENANCE_UNKNOWN",
                "severity": "high",
                "message": (
                    "Declare universe_data as point_in_time, current_constituents, or "
                    "not_applicable; undeclared provenance cannot rule out survivorship bias."
                ),
            }
        )

    strategy_basis = declarations.get("strategy_return_basis", "unknown")
    baseline_basis = declarations.get("baseline_return_basis", "unknown")
    if (
        strategy_basis != "unknown"
        and baseline_basis != "unknown"
        and strategy_basis != baseline_basis
    ):
        warnings.append(
            {
                "id": "RETURN_BASIS_MISMATCH",
                "severity": "high",
                "message": "Strategy and baseline returns use different gross/net cost bases.",
            }
        )
    elif "unknown" in {strategy_basis, baseline_basis}:
        warnings.append(
            {
                "id": "RETURN_BASIS_UNKNOWN",
                "severity": "high",
                "message": "Declare gross or net return basis for both strategy and baselines.",
            }
        )

    analysis_scope = declarations.get("analysis_scope", "unknown")
    if analysis_scope not in {"out_of_sample", "live"}:
        warnings.append(
            {
                "id": "NOT_OUT_OF_SAMPLE",
                "severity": "high",
                "message": "Treat in-sample residual edge as exploratory until confirmed out of sample.",
            }
        )
    return warnings


def _rolling_analysis(
    strategy_returns: list[float],
    factor_columns: list[list[float]],
    factor_names: list[str],
    rolling_window: int,
    annualization_factor: int,
    hac_lags: int | None,
    minimum_rolling_windows: int,
) -> dict[str, Any]:
    if rolling_window == 0:
        return {"enabled": False, "reason": "disabled"}
    minimum_window = max(20, 5 * (len(factor_columns) + 1))
    if rolling_window < minimum_window:
        return {
            "enabled": False,
            "reason": f"rolling_window must be at least {minimum_window} for this model",
        }
    if len(strategy_returns) < rolling_window:
        return {"enabled": False, "reason": "fewer observations than rolling_window"}
    # Enough history to refit the window `minimum_rolling_windows` times, so the
    # positive-alpha fraction is measured over a real span rather than one fit.
    required_observations = rolling_window + minimum_rolling_windows - 1
    if len(strategy_returns) < required_observations:
        available = len(strategy_returns) - rolling_window + 1
        return {
            "enabled": False,
            "reason": (
                f"only {available} rolling windows fit in {len(strategy_returns)} observations; "
                f"{minimum_rolling_windows} required "
                f"(need at least {required_observations} observations for window {rolling_window})"
            ),
        }

    windows = []
    failed_windows = 0
    for end in range(rolling_window, len(strategy_returns) + 1):
        start = end - rolling_window
        try:
            fit = fit_regression(
                strategy_returns[start:end],
                [column[start:end] for column in factor_columns],
                factor_names,
                hac_lags=hac_lags,
                calculate_vif=False,
            )
        except AnalysisError:
            failed_windows += 1
            continue
        residual_volatility = fit["residual_volatility_periodic"]
        edge_ratio = _safe_ratio(
            fit["intercept"] * annualization_factor,
            residual_volatility * math.sqrt(annualization_factor),
        )
        windows.append(
            {
                "end_index": end - 1,
                "r_squared": fit["r_squared"],
                "annualized_alpha": fit["intercept"] * annualization_factor,
                "residual_edge_ratio": edge_ratio,
            }
        )

    if not windows:
        return {"enabled": False, "reason": "all rolling models were rank deficient"}

    edge_ratios = [
        window["residual_edge_ratio"]
        for window in windows
        if window["residual_edge_ratio"] is not None
    ]
    return {
        "enabled": True,
        "window": rolling_window,
        "window_count": len(windows),
        "failed_window_count": failed_windows,
        "latest": windows[-1],
        "r_squared": {
            "min": min(window["r_squared"] for window in windows),
            "median": statistics.median(window["r_squared"] for window in windows),
            "max": max(window["r_squared"] for window in windows),
        },
        "residual_edge_ratio": (
            {
                "min": min(edge_ratios),
                "median": statistics.median(edge_ratios),
                "max": max(edge_ratios),
            }
            if edge_ratios
            else None
        ),
        "positive_alpha_fraction": sum(window["annualized_alpha"] > 0 for window in windows)
        / len(windows),
    }


def _classify_model(model: dict[str, Any], thresholds: dict[str, float]) -> tuple[str, list[str]]:
    alpha_t_stat = model["alpha"]["t_stat"]
    edge_ratio = model["residual"]["residual_edge_ratio"]
    rolling = model["rolling"]
    if not rolling["enabled"]:
        return "RESIDUAL_FRAGILE", [f"Rolling stability is unavailable: {rolling['reason']}."]
    if rolling["failed_window_count"] > 0:
        return "RESIDUAL_FRAGILE", [
            f"{rolling['failed_window_count']} rolling windows could not be estimated."
        ]

    rolling_pass = rolling["positive_alpha_fraction"] >= thresholds["rolling_positive_fraction_min"]

    if (
        edge_ratio is not None
        and alpha_t_stat is not None
        and edge_ratio >= thresholds["residual_edge_ratio_min"]
        and alpha_t_stat >= thresholds["alpha_t_stat_min"]
        and rolling_pass
    ):
        return "RESIDUAL_EDGE", [
            "Alpha, residual edge ratio, and rolling stability clear the configured thresholds."
        ]

    if (
        model["r_squared"] >= thresholds["baseline_explained_r2_min"]
        and (edge_ratio is None or abs(edge_ratio) <= thresholds["weak_edge_ratio_max"])
        and (alpha_t_stat is None or abs(alpha_t_stat) < thresholds["alpha_t_stat_min"])
    ):
        return "BASELINE_EXPLAINED", [
            "Declared baselines explain most variation and residual edge is weak."
        ]

    reasons = ["Residual evidence does not clear all robustness thresholds."]
    if not rolling_pass:
        reasons.append("Rolling alpha is positive in too few windows.")
    return "RESIDUAL_FRAGILE", reasons


def _analyze_model(
    model_spec: dict[str, Any],
    model_role: str,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    strategy = [row["numeric"][config["strategy_column"]] for row in rows]
    factor_names = model_spec["baseline_columns"]
    factors = [[row["numeric"][name] for row in rows] for name in factor_names]
    requested_lags = None if config["hac_lags"] == "auto" else config["hac_lags"]
    fit = fit_regression(strategy, factors, factor_names, hac_lags=requested_lags)
    annualization = config["annualization_factor"]
    residual_volatility_annualized = fit["residual_volatility_periodic"] * math.sqrt(annualization)
    annualized_alpha = fit["intercept"] * annualization
    alpha_coefficient = fit["coefficients"][0]
    rolling = _rolling_analysis(
        strategy,
        factors,
        factor_names,
        config["rolling_window"],
        annualization,
        requested_lags,
        config["minimum_rolling_windows"],
    )

    result = {
        "name": model_spec["name"],
        "role": model_role,
        "baseline_columns": factor_names,
        "observation_count": fit["observation_count"],
        "coefficients": fit["coefficients"],
        "alpha": {
            "periodic": fit["intercept"],
            "annualized_arithmetic": annualized_alpha,
            "hac_standard_error_periodic": alpha_coefficient["hac_standard_error"],
            "t_stat": alpha_coefficient["t_stat"],
        },
        "r_squared": fit["r_squared"],
        "adjusted_r_squared": fit["adjusted_r_squared"],
        "residual": {
            "periodic_volatility": fit["residual_volatility_periodic"],
            "annualized_volatility": residual_volatility_annualized,
            "residual_edge_ratio": _safe_ratio(annualized_alpha, residual_volatility_annualized),
            "active_return_max_drawdown": _max_drawdown(fit["active_returns"]),
            "lag_one_autocorrelation": fit["lag_one_residual_autocorrelation"],
            "durbin_watson": fit["durbin_watson"],
        },
        "hac_lags": fit["hac_lags"],
        "vif": fit["vif"],
        "rolling": rolling,
    }
    status, reasons = _classify_model(result, config["thresholds"])
    result["diagnostic_status"] = status
    result["status_reasons"] = reasons
    series = {
        "strategy": strategy,
        "residual": fit["residuals"],
        "active": fit["active_returns"],
        "baseline_explained": fit["baseline_explained_returns"],
        "fitted": fit["fitted_returns"],
    }
    return result, series


def _regime_analysis(
    rows: list[dict[str, Any]],
    active_returns: list[float],
    config: dict[str, Any],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    annualization = config["annualization_factor"]
    minimum = config["minimum_regime_observations"]
    for column in config["regime_columns"]:
        groups: dict[str, list[float]] = {}
        for row, active_return in zip(rows, active_returns):
            groups.setdefault(row["regimes"][column], []).append(active_return)
        output[column] = []
        for label in sorted(groups):
            values = groups[label]
            metrics = _performance_metrics(values, annualization) if len(values) >= 2 else None
            output[column].append(
                {
                    "label": label,
                    "observation_count": len(values),
                    "evidence_status": "ADEQUATE" if len(values) >= minimum else "THIN",
                    "active_return_metrics": metrics,
                    "positive_fraction": sum(value > 0 for value in values) / len(values),
                }
            )
    return output


def analyze(csv_path: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    dataset = load_dataset(csv_path, config)
    rows = dataset["rows"]
    warnings = _declaration_warnings(config)
    if not dataset["was_sorted"]:
        warnings.append(
            {
                "id": "INPUT_REORDERED",
                "severity": "low",
                "message": "CSV rows were sorted by date before analysis.",
            }
        )
    largest_parameter_count = max(
        len(model["baseline_columns"]) + 1
        for model in [config["primary_model"], *config["sensitivity_models"]]
    )
    effective_minimum_observations = max(
        config["minimum_observations"], 10 * largest_parameter_count
    )
    if len(rows) < effective_minimum_observations:
        warnings.append(
            {
                "id": "SMALL_SAMPLE",
                "severity": "high",
                "message": (
                    f"{len(rows)} observations are below the effective minimum "
                    f"of {effective_minimum_observations}."
                ),
            }
        )
    if not config["sensitivity_models"]:
        warnings.append(
            {
                "id": "NO_SENSITIVITY_MODELS",
                "severity": "high",
                "message": "No alternate baseline model was supplied; baseline-choice sensitivity is unknown.",
            }
        )

    strategy = [row["numeric"][config["strategy_column"]] for row in rows]
    if any(abs(value) > 0.50 for value in strategy):
        warnings.append(
            {
                "id": "EXTREME_STRATEGY_RETURN",
                "severity": "medium",
                "message": "At least one absolute strategy return exceeds 50%; verify return units and leverage.",
            }
        )

    models = []
    primary_series: dict[str, list[float]] | None = None
    for index, model_spec in enumerate([config["primary_model"], *config["sensitivity_models"]]):
        result, series = _analyze_model(
            model_spec, "primary" if index == 0 else "sensitivity", rows, config
        )
        models.append(result)
        if index == 0:
            primary_series = series
        rolling = result["rolling"]
        if not rolling["enabled"]:
            warnings.append(
                {
                    "id": "ROLLING_ANALYSIS_UNAVAILABLE",
                    "severity": "high",
                    "message": (
                        f"Model {result['name']} has no rolling stability evidence: "
                        f"{rolling['reason']}."
                    ),
                }
            )
        elif rolling["failed_window_count"] > 0:
            warnings.append(
                {
                    "id": "ROLLING_ANALYSIS_INCOMPLETE",
                    "severity": "high",
                    "message": (
                        f"Model {result['name']} could not estimate "
                        f"{rolling['failed_window_count']} rolling windows."
                    ),
                }
            )
        for name, value in result["vif"].items():
            if value is None or value > 10:
                warnings.append(
                    {
                        "id": "MULTICOLLINEARITY",
                        "severity": "high",
                        "message": f"Model {result['name']} baseline {name} has VIF > 10 or is singular.",
                    }
                )
        autocorrelation = result["residual"]["lag_one_autocorrelation"]
        if autocorrelation is not None and abs(autocorrelation) >= 0.30:
            warnings.append(
                {
                    "id": "RESIDUAL_AUTOCORRELATION",
                    "severity": "medium",
                    "message": f"Model {result['name']} has absolute lag-1 residual autocorrelation >= 0.30.",
                }
            )

    assert primary_series is not None
    primary_status = models[0]["diagnostic_status"]
    status_reasons = list(models[0]["status_reasons"])
    sensitivity_statuses = [model["diagnostic_status"] for model in models[1:]]
    if not sensitivity_statuses:
        primary_status = "RESIDUAL_FRAGILE"
        status_reasons.append("No alternate baseline model was supplied.")
    elif any(status != primary_status for status in sensitivity_statuses):
        primary_status = "RESIDUAL_FRAGILE"
        status_reasons.append("Diagnostic status changes under alternate declared baselines.")

    high_warnings = [warning for warning in warnings if warning["severity"] == "high"]
    if any(warning["id"] == "SMALL_SAMPLE" for warning in high_warnings):
        overall_status = "INSUFFICIENT_EVIDENCE"
        status_reasons.insert(0, "Observation count is below the configured minimum.")
    else:
        overall_status = primary_status

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analysis_type": "returns_based_residual_edge",
        "source": {
            "csv_name": csv_path.name,
            "config_name": config_path.name,
        },
        "data": {
            "start_date": rows[0]["date"].isoformat(),
            "end_date": rows[-1]["date"].isoformat(),
            "observation_count": len(rows),
            "frequency": config["frequency"],
            "annualization_factor": config["annualization_factor"],
            "configured_minimum_observations": config["minimum_observations"],
            "effective_minimum_observations": effective_minimum_observations,
            "return_unit_normalized": "decimal",
            "strategy_column": config["strategy_column"],
            "baseline_columns": dataset["baseline_columns"],
            "regime_columns": config["regime_columns"],
            "declarations": config["data_declarations"],
        },
        "strategy_metrics": _performance_metrics(strategy, config["annualization_factor"]),
        "models": models,
        "primary_model": models[0]["name"],
        "regime_analysis": _regime_analysis(rows, primary_series["active"], config),
        "warnings": warnings,
        "verdict": {
            "status": overall_status,
            "reasons": status_reasons,
            "decision_grade": not high_warnings,
            "decision_eligibility": "ELIGIBLE" if not high_warnings else "REVIEW_REQUIRED",
            "thresholds": config["thresholds"],
            "trade_authorization": "NOT_AUTHORIZED",
        },
        "method_notes": [
            "OLS includes an intercept.",
            "Residual edge ratio is annualized alpha divided by annualized residual volatility.",
            "HAC standard errors address heteroskedasticity and serial correlation asymptotically.",
            "Results describe declared return-series exposure, not holdings-based Brinson attribution.",
        ],
    }

    if config["include_series"]:
        result["primary_model_series"] = [
            {
                "date": row["date"].isoformat(),
                "strategy_return": primary_series["strategy"][index],
                "baseline_explained_return": primary_series["baseline_explained"][index],
                "active_return": primary_series["active"][index],
                "residual": primary_series["residual"][index],
                "fitted_total_return": primary_series["fitted"][index],
            }
            for index, row in enumerate(rows)
        ]
    return _round_value(result)


def render_markdown(report: dict[str, Any]) -> str:
    primary = next(model for model in report["models"] if model["name"] == report["primary_model"])
    verdict = report["verdict"]
    data = report["data"]
    lines = [
        "# Residual Edge Analysis",
        "",
        f"**Status:** {verdict['status']}",
        f"**Decision eligibility:** {verdict['decision_eligibility']}",
        f"**Period:** {data['start_date']} to {data['end_date']} ({data['observation_count']} observations)",
        f"**Primary model:** {primary['name']}",
        "",
        "## Primary Model",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| R² | {primary['r_squared']:.4f} |",
        f"| Adjusted R² | {primary['adjusted_r_squared']:.4f} |",
        f"| Annualized alpha | {primary['alpha']['annualized_arithmetic']:.4%} |",
        f"| Alpha HAC t-stat | {_format_number(primary['alpha']['t_stat'])} |",
        f"| Annualized residual volatility | {primary['residual']['annualized_volatility']:.4%} |",
        f"| Residual edge ratio | {_format_number(primary['residual']['residual_edge_ratio'])} |",
        "",
        "## Baseline Loadings",
        "",
        "| Baseline | Loading | HAC t-stat | VIF |",
        "|---|---:|---:|---:|",
    ]
    coefficients = {item["name"]: item for item in primary["coefficients"]}
    for baseline in primary["baseline_columns"]:
        coefficient = coefficients[baseline]
        lines.append(
            f"| {baseline} | {coefficient['estimate']:.4f} | "
            f"{_format_number(coefficient['t_stat'])} | {_format_number(primary['vif'][baseline])} |"
        )

    lines.extend(
        [
            "",
            "## Model Sensitivity",
            "",
            "| Model | Role | R² | Annualized alpha | Residual edge ratio | Status |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for model in report["models"]:
        lines.append(
            f"| {model['name']} | {model['role']} | {model['r_squared']:.4f} | "
            f"{model['alpha']['annualized_arithmetic']:.4%} | "
            f"{_format_number(model['residual']['residual_edge_ratio'])} | "
            f"{model['diagnostic_status']} |"
        )

    lines.extend(["", "## Evidence Warnings", ""])
    if report["warnings"]:
        for warning in report["warnings"]:
            lines.append(
                f"- **{warning['severity'].upper()} — {warning['id']}:** {warning['message']}"
            )
    else:
        lines.append("- None.")

    if report["regime_analysis"]:
        lines.extend(["", "## Regime Breakdown", ""])
        for column, groups in report["regime_analysis"].items():
            lines.extend(
                [
                    f"### {column}",
                    "",
                    "| Regime | N | Evidence | Annualized active return | Active Sharpe |",
                    "|---|---:|---|---:|---:|",
                ]
            )
            for group in groups:
                metrics = group["active_return_metrics"]
                annualized_return = (
                    f"{metrics['annualized_arithmetic_return']:.4%}" if metrics else "n/a"
                )
                sharpe = _format_number(metrics["sharpe_zero_rate"]) if metrics else "n/a"
                lines.append(
                    f"| {group['label']} | {group['observation_count']} | "
                    f"{group['evidence_status']} | {annualized_return} | {sharpe} |"
                )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            *[f"- {reason}" for reason in verdict["reasons"]],
            "- This report does not authorize a trade or an automatic exposure change.",
            "- Confirm exploratory findings on untouched out-of-sample or live data.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Aligned return-series CSV.")
    parser.add_argument("--config", required=True, type=Path, help="JSON analysis specification.")
    parser.add_argument("--output-json", required=True, type=Path, help="JSON report path.")
    parser.add_argument("--output-markdown", type=Path, help="Optional Markdown summary path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = analyze(args.input, args.config)
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if args.output_markdown:
            args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.output_markdown.write_text(render_markdown(report), encoding="utf-8")
    except AnalysisError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote {args.output_json}")
    if args.output_markdown:
        print(f"Wrote {args.output_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
