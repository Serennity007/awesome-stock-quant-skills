"""Tests for returns-based residual edge attribution."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest


def _series(count: int, alpha: float = 0.001) -> list[dict[str, object]]:
    rows = []
    current = date(2025, 1, 1)
    noise_pattern = [-0.0006, -0.0002, 0.0002, 0.0006]
    for index in range(count):
        market = ((index % 13) - 6) * 0.001
        equal_weight = ((index * 5 % 17) - 8) * 0.0008
        momentum = 0.4 * market + ((index * 3 % 7) - 3) * 0.0005
        noise = noise_pattern[index % len(noise_pattern)]
        rows.append(
            {
                "date": current.isoformat(),
                "strategy_return": alpha + 1.2 * market + noise,
                "market_return": market,
                "equal_weight_return": equal_weight,
                "momentum_return": momentum,
                "volatility_regime": "high" if index % 3 == 0 else "low",
            }
        )
        current += timedelta(days=1)
    return rows


def _write_csv(path: Path, rows: list[dict[str, object]], percent: bool = False) -> None:
    fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            output = dict(row)
            if percent:
                for column in (
                    "strategy_return",
                    "market_return",
                    "equal_weight_return",
                    "momentum_return",
                ):
                    output[column] = float(output[column]) * 100
            writer.writerow(output)


def _config(
    *,
    return_unit: str = "decimal",
    minimum_observations: int = 60,
    baseline_selection: str = "predeclared",
    sensitivity: bool = True,
    rolling_window: int = 40,
    universe_data: str | None = "point_in_time",
    minimum_rolling_windows: int | None = None,
) -> dict[str, object]:
    declarations: dict[str, object] = {
        "baseline_selection": baseline_selection,
        "strategy_return_basis": "net",
        "baseline_return_basis": "net",
        "analysis_scope": "out_of_sample",
    }
    if universe_data is not None:
        declarations["universe_data"] = universe_data
    config: dict[str, object] = {
        "schema_version": "1.0",
        "date_column": "date",
        "strategy_column": "strategy_return",
        "return_unit": return_unit,
        "frequency": "daily",
        "primary_model": {
            "name": "market",
            "baseline_columns": ["market_return"],
        },
        "sensitivity_models": (
            [
                {
                    "name": "market_plus_momentum",
                    "baseline_columns": ["market_return", "momentum_return"],
                }
            ]
            if sensitivity
            else []
        ),
        "regime_columns": ["volatility_regime"],
        "rolling_window": rolling_window,
        "minimum_observations": minimum_observations,
        "minimum_regime_observations": 20,
        "hac_lags": "auto",
        "include_series": True,
        "data_declarations": declarations,
    }
    if minimum_rolling_windows is not None:
        config["minimum_rolling_windows"] = minimum_rolling_windows
    return config


def _write_case(
    tmp_path: Path,
    rows: list[dict[str, object]],
    config: dict[str, object],
    *,
    percent: bool = False,
) -> tuple[Path, Path]:
    csv_path = tmp_path / "returns.csv"
    config_path = tmp_path / "config.json"
    _write_csv(csv_path, rows, percent=percent)
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return csv_path, config_path


def test_fit_regression_recovers_alpha_and_loading(analyzer_module):
    market = [((index % 13) - 6) * 0.002 for index in range(120)]
    noise = [(-1 if index % 2 else 1) * 0.0002 for index in range(120)]
    strategy = [0.001 + 1.5 * factor + error for factor, error in zip(market, noise)]

    result = analyzer_module.fit_regression(strategy, [market], ["market"])

    assert result["intercept"] == pytest.approx(0.001, abs=3e-6)
    assert result["loadings"]["market"] == pytest.approx(1.5, abs=0.01)
    assert result["r_squared"] > 0.99
    assert abs(sum(result["residuals"])) < 1e-10


def test_exact_collinearity_is_rejected(analyzer_module):
    first = [index / 1000 for index in range(1, 80)]
    second = [2 * value for value in first]
    strategy = [0.001 + value for value in first]

    with pytest.raises(analyzer_module.AnalysisError, match="rank deficient"):
        analyzer_module.fit_regression(strategy, [first, second], ["first", "second"])


def test_analyze_finds_residual_edge_and_regimes(tmp_path, analyzer_module):
    csv_path, config_path = _write_case(tmp_path, _series(140), _config())

    report = analyzer_module.analyze(csv_path, config_path)

    assert report["verdict"]["status"] == "RESIDUAL_EDGE"
    assert report["verdict"]["decision_grade"] is True
    assert report["models"][0]["alpha"]["annualized_arithmetic"] > 0
    assert report["models"][0]["residual"]["residual_edge_ratio"] > 0.75
    assert len(report["primary_model_series"]) == 140
    groups = report["regime_analysis"]["volatility_regime"]
    assert {group["label"] for group in groups} == {"high", "low"}
    assert all(group["evidence_status"] == "ADEQUATE" for group in groups)


def test_baseline_explains_zero_alpha_strategy(tmp_path, analyzer_module):
    rows = _series(140, alpha=0.0)
    csv_path, config_path = _write_case(tmp_path, rows, _config(sensitivity=False))

    report = analyzer_module.analyze(csv_path, config_path)

    assert report["models"][0]["diagnostic_status"] == "BASELINE_EXPLAINED"
    assert report["verdict"]["status"] == "RESIDUAL_FRAGILE"
    assert report["verdict"]["decision_eligibility"] == "REVIEW_REQUIRED"
    assert any(
        warning["id"] == "NO_SENSITIVITY_MODELS" and warning["severity"] == "high"
        for warning in report["warnings"]
    )


def test_residual_edge_without_sensitivity_fails_closed(tmp_path, analyzer_module):
    csv_path, config_path = _write_case(tmp_path, _series(140), _config(sensitivity=False))

    report = analyzer_module.analyze(csv_path, config_path)

    assert report["models"][0]["diagnostic_status"] == "RESIDUAL_EDGE"
    assert report["verdict"]["status"] == "RESIDUAL_FRAGILE"
    assert report["verdict"]["decision_eligibility"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize("rolling_window", [0, 200])
def test_unavailable_rolling_analysis_fails_closed(tmp_path, analyzer_module, rolling_window):
    csv_path, config_path = _write_case(
        tmp_path,
        _series(140),
        _config(rolling_window=rolling_window),
    )

    report = analyzer_module.analyze(csv_path, config_path)

    assert report["models"][0]["diagnostic_status"] == "RESIDUAL_FRAGILE"
    assert report["verdict"]["status"] == "RESIDUAL_FRAGILE"
    assert report["verdict"]["decision_eligibility"] == "REVIEW_REQUIRED"
    assert any(
        warning["id"] == "ROLLING_ANALYSIS_UNAVAILABLE" and warning["severity"] == "high"
        for warning in report["warnings"]
    )


def test_single_rolling_window_fails_closed(tmp_path, analyzer_module):
    """One refit makes positive_alpha_fraction 0.0 or 1.0, which is not stability evidence."""
    csv_path, config_path = _write_case(
        tmp_path,
        _series(60),
        _config(rolling_window=60, minimum_observations=60),
    )

    report = analyzer_module.analyze(csv_path, config_path)

    for model in report["models"]:
        assert model["rolling"]["enabled"] is False
        assert "1 rolling windows" in model["rolling"]["reason"]
        assert model["diagnostic_status"] == "RESIDUAL_FRAGILE"
    assert report["verdict"]["status"] == "RESIDUAL_FRAGILE"
    assert report["verdict"]["decision_grade"] is False
    assert report["verdict"]["decision_eligibility"] == "REVIEW_REQUIRED"


def test_rolling_window_count_boundary(tmp_path, analyzer_module):
    """minimum_rolling_windows - 1 windows fails closed; exactly the minimum runs."""
    window = 40
    minimum = 5
    (tmp_path / "short").mkdir()
    (tmp_path / "exact").mkdir()

    short_path, short_config = _write_case(
        tmp_path / "short",
        _series(window + minimum - 2),
        _config(rolling_window=window, minimum_rolling_windows=minimum),
    )
    short_report = analyzer_module.analyze(short_path, short_config)
    assert short_report["models"][0]["rolling"]["enabled"] is False
    assert short_report["verdict"]["decision_eligibility"] == "REVIEW_REQUIRED"

    exact_path, exact_config = _write_case(
        tmp_path / "exact",
        _series(window + minimum - 1),
        _config(rolling_window=window, minimum_rolling_windows=minimum),
    )
    exact_report = analyzer_module.analyze(exact_path, exact_config)
    assert exact_report["models"][0]["rolling"]["enabled"] is True
    assert exact_report["models"][0]["rolling"]["window_count"] == minimum


def test_minimum_rolling_windows_must_be_at_least_two(tmp_path, analyzer_module):
    csv_path, config_path = _write_case(tmp_path, _series(140), _config(minimum_rolling_windows=1))

    with pytest.raises(analyzer_module.AnalysisError, match="minimum_rolling_windows"):
        analyzer_module.analyze(csv_path, config_path)


def test_undeclared_universe_provenance_blocks_decision_grade(tmp_path, analyzer_module):
    """`not_applicable` exists as an explicit value, so an absent declaration is undeclared."""
    csv_path, config_path = _write_case(tmp_path, _series(140), _config(universe_data=None))

    report = analyzer_module.analyze(csv_path, config_path)

    assert any(
        warning["id"] == "UNIVERSE_PROVENANCE_UNKNOWN" and warning["severity"] == "high"
        for warning in report["warnings"]
    )
    assert report["verdict"]["decision_grade"] is False
    assert report["verdict"]["decision_eligibility"] == "REVIEW_REQUIRED"


def test_not_applicable_universe_stays_decision_grade(tmp_path, analyzer_module):
    csv_path, config_path = _write_case(
        tmp_path, _series(140), _config(universe_data="not_applicable")
    )

    report = analyzer_module.analyze(csv_path, config_path)

    assert not any(warning["id"] == "UNIVERSE_PROVENANCE_UNKNOWN" for warning in report["warnings"])
    assert report["verdict"]["decision_grade"] is True
    assert report["verdict"]["decision_eligibility"] == "ELIGIBLE"


def test_post_hoc_baseline_blocks_decision_grade(tmp_path, analyzer_module):
    csv_path, config_path = _write_case(
        tmp_path, _series(100), _config(baseline_selection="post_hoc")
    )

    report = analyzer_module.analyze(csv_path, config_path)

    assert report["verdict"]["decision_grade"] is False
    assert report["verdict"]["decision_eligibility"] == "REVIEW_REQUIRED"
    assert any(
        warning["id"] == "BASELINE_SELECTION_NOT_PREDECLARED" and warning["severity"] == "high"
        for warning in report["warnings"]
    )


def test_small_sample_is_insufficient(tmp_path, analyzer_module):
    csv_path, config_path = _write_case(tmp_path, _series(30), _config(minimum_observations=60))

    report = analyzer_module.analyze(csv_path, config_path)

    assert report["verdict"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["verdict"]["decision_grade"] is False


def test_percent_and_decimal_inputs_match(tmp_path, analyzer_module):
    decimal_dir = tmp_path / "decimal"
    percent_dir = tmp_path / "percent"
    decimal_dir.mkdir()
    percent_dir.mkdir()
    rows = _series(100)
    decimal_paths = _write_case(decimal_dir, rows, _config())
    percent_paths = _write_case(
        percent_dir,
        rows,
        _config(return_unit="percent"),
        percent=True,
    )

    decimal_report = analyzer_module.analyze(*decimal_paths)
    percent_report = analyzer_module.analyze(*percent_paths)

    assert percent_report["models"][0]["r_squared"] == decimal_report["models"][0]["r_squared"]
    assert (
        percent_report["models"][0]["alpha"]["annualized_arithmetic"]
        == decimal_report["models"][0]["alpha"]["annualized_arithmetic"]
    )


def test_unsorted_input_is_sorted_and_warned(tmp_path, analyzer_module):
    rows = _series(80)
    rows[0], rows[-1] = rows[-1], rows[0]
    csv_path, config_path = _write_case(tmp_path, rows, _config())

    report = analyzer_module.analyze(csv_path, config_path)

    assert report["data"]["start_date"] < report["data"]["end_date"]
    assert report["primary_model_series"][0]["date"] == report["data"]["start_date"]
    assert any(warning["id"] == "INPUT_REORDERED" for warning in report["warnings"])


def test_duplicate_dates_are_rejected(tmp_path, analyzer_module):
    rows = _series(80)
    rows[1]["date"] = rows[0]["date"]
    csv_path, config_path = _write_case(tmp_path, rows, _config())

    with pytest.raises(analyzer_module.AnalysisError, match="duplicate dates"):
        analyzer_module.analyze(csv_path, config_path)


def test_missing_baseline_column_is_rejected(tmp_path, analyzer_module):
    rows = _series(80)
    for row in rows:
        del row["market_return"]
    csv_path, config_path = _write_case(tmp_path, rows, _config())

    with pytest.raises(analyzer_module.AnalysisError, match="missing columns"):
        analyzer_module.analyze(csv_path, config_path)


def test_return_below_minus_one_is_rejected(tmp_path, analyzer_module):
    rows = _series(80)
    rows[5]["strategy_return"] = -1.0
    csv_path, config_path = _write_case(tmp_path, rows, _config())

    with pytest.raises(analyzer_module.AnalysisError, match="Return <= -100%"):
        analyzer_module.analyze(csv_path, config_path)


def test_unknown_config_key_is_rejected(tmp_path, analyzer_module):
    config = _config()
    config["typo_key"] = True
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(analyzer_module.AnalysisError, match="Unknown config keys"):
        analyzer_module.load_config(config_path)


def test_duplicate_sensitivity_baseline_set_is_rejected(tmp_path, analyzer_module):
    config = _config()
    config["sensitivity_models"] = [
        {
            "name": "same_market_with_new_name",
            "baseline_columns": ["market_return"],
        }
    ]
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(analyzer_module.AnalysisError, match="distinct baseline set"):
        analyzer_module.load_config(config_path)


def test_include_series_requires_json_boolean(tmp_path, analyzer_module):
    config = _config()
    config["include_series"] = "false"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(analyzer_module.AnalysisError, match="JSON boolean"):
        analyzer_module.load_config(config_path)


def test_include_series_false_omits_observations(tmp_path, analyzer_module):
    config = _config()
    config["include_series"] = False
    csv_path, config_path = _write_case(tmp_path, _series(100), config)

    report = analyzer_module.analyze(csv_path, config_path)

    assert "primary_model_series" not in report


def test_missing_declarations_fail_closed(tmp_path, analyzer_module):
    config = _config()
    config["data_declarations"] = {}
    csv_path, config_path = _write_case(tmp_path, _series(100), config)

    report = analyzer_module.analyze(csv_path, config_path)

    assert report["verdict"]["decision_grade"] is False
    assert report["verdict"]["decision_eligibility"] == "REVIEW_REQUIRED"
    warning_ids = {warning["id"] for warning in report["warnings"]}
    assert {
        "BASELINE_SELECTION_NOT_PREDECLARED",
        "RETURN_BASIS_UNKNOWN",
        "NOT_OUT_OF_SAMPLE",
    } <= warning_ids


def test_markdown_contains_non_execution_guardrail(tmp_path, analyzer_module):
    csv_path, config_path = _write_case(tmp_path, _series(100), _config())
    report = analyzer_module.analyze(csv_path, config_path)

    markdown = analyzer_module.render_markdown(report)

    assert "# Residual Edge Analysis" in markdown
    assert "Model Sensitivity" in markdown
    assert "does not authorize a trade" in markdown


def test_cli_writes_json_and_markdown(tmp_path):
    rows = _series(100)
    csv_path, config_path = _write_case(tmp_path, rows, _config())
    output_json = tmp_path / "out" / "report.json"
    output_markdown = tmp_path / "out" / "report.md"
    script = Path(__file__).resolve().parents[1] / "analyze_residual_edge.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(csv_path),
            "--config",
            str(config_path),
            "--output-json",
            str(output_json),
            "--output-markdown",
            str(output_markdown),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(output_json.read_text(encoding="utf-8"))["schema_version"] == "1.0"
    assert output_markdown.read_text(encoding="utf-8").startswith("# Residual Edge Analysis")
