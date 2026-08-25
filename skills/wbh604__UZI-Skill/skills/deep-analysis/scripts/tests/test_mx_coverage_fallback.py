"""Regression tests for PR #92's MX coverage fallbacks.

All MX responses are mocked: these tests must remain deterministic and offline.
"""
from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))


def _mx_table(name_map: dict, heads: list, series: dict) -> dict:
    table = {"headName": heads, **series}
    return {
        "success": True,
        "data": {
            "data": {
                "searchDataResultDTO": {
                    "dataTableDTOList": [{
                        "table": table,
                        "rawTable": table,
                        "nameMap": name_map,
                    }],
                },
            },
        },
    }


def test_parse_mx_roe_series_prefers_annual_and_keeps_zero():
    from fetch_financials import _parse_mx_roe_series

    payload = _mx_table(
        {"roe": "净资产收益率ROE(加权)"},
        ["2026一季报", "2025年报", "2024年报", "2023年报"],
        {"roe": ["10.57", "0", "36.02", "34.19"]},
    )

    parsed = _parse_mx_roe_series(payload)

    assert parsed["roe_history"] == [34.19, 36.02, 0.0]
    assert parsed["financial_years"] == ["2023", "2024", "2025"]
    assert parsed["roe"] == "0.0%"


def test_financial_health_via_mx_keeps_zero(monkeypatch):
    from fetch_financials import _fetch_financial_health_via_mx
    import lib.mx_api as mx_mod

    class _Client:
        available = True

        def query(self, _query):
            return _mx_table(
                {
                    "a": "流动比率",
                    "b": "资产负债率",
                    "c": "总资产净利率ROA",
                    "d": "销售净利率",
                },
                ["2025年报"],
                {"a": ["0"], "b": ["--"], "c": ["0"], "d": ["12.5"]},
            )

    monkeypatch.setattr(mx_mod, "MXClient", _Client)

    health = _fetch_financial_health_via_mx("600519", "贵州茅台")

    assert health == {"current_ratio": 0.0, "roic": 0.0, "net_margin_pct": 12.5}


def test_mx_latest_pct_reads_window_from_label():
    from fetch_valuation import _mx_latest_pct

    payload = _mx_table(
        {"p": "3年市盈率历史百分位"},
        ["2026-07-30"],
        {"p": ["32.78%"]},
    )

    assert _mx_latest_pct(payload, "市盈率") == (32.78, "3 年")


def test_fetch_valuation_via_mx_tracks_basic_only_source(monkeypatch):
    from fetch_valuation import _fetch_valuation_via_mx
    import lib.mx_api as mx_mod

    class _Client:
        available = False

    monkeypatch.setattr(mx_mod, "MXClient", _Client)

    out = _fetch_valuation_via_mx(
        "600519", "贵州茅台", {"pe_ttm": 20.58, "pb": 6.3}
    )

    assert out == {"_valuation_source": "basic", "pe": "20.58", "pb": "6.3"}


def test_fetch_valuation_via_mx_survives_individual_query_errors(monkeypatch):
    from fetch_valuation import _fetch_valuation_via_mx
    import lib.mx_api as mx_mod

    class _Client:
        available = True

        def fetch_snapshot(self, _label):
            return {}

        def query(self, query):
            if "市盈率" in query:
                raise TimeoutError("PE endpoint timed out")
            return _mx_table(
                {"p": "5年市净率历史百分位"},
                ["2026-07-30"],
                {"p": ["8%"]},
            )

    monkeypatch.setattr(mx_mod, "MXClient", _Client)

    out = _fetch_valuation_via_mx("600519", "贵州茅台", {"pe_ttm": 20.58})

    assert out["_valuation_source"] == "basic+mx_api"
    assert out["pe"] == "20.58"
    assert out["pb_quantile"] == "8%"


def test_main_safe_fills_coverage_fields(monkeypatch):
    import fetch_valuation as fv
    import lib.data_sources as data_sources

    monkeypatch.setattr(
        data_sources,
        "fetch_basic",
        lambda _ticker: {"pe_ttm": 20.58, "pb": 6.3, "name": "贵州茅台"},
    )
    monkeypatch.setattr(
        fv,
        "_fetch_valuation_via_mx",
        lambda *_args, **_kwargs: {
            "_valuation_source": "basic+mx_api",
            "pe": "20.58",
            "pb": "6.3",
            "pe_quantile": "3 年 33 分位",
            "pb_quantile": "8%",
        },
    )

    out = fv.main_safe("600519")

    assert out["fallback"] is False
    assert out["data"]["pe_quantile"] == "3 年 33 分位"
    assert out["source"] == "basic+mx_api (mini_racer-safe)"


def test_legacy_runner_uses_safe_valuation_when_miniracer_disabled(monkeypatch):
    import fetch_valuation
    import run_real_test as rrt

    monkeypatch.setattr(rrt, "_mini_racer_disabled", lambda: True)
    monkeypatch.setattr(
        fetch_valuation,
        "main_safe",
        lambda ticker: {
            "ticker": ticker,
            "data": {"pe": "20.58"},
            "source": "basic (mini_racer-safe)",
            "fallback": False,
        },
    )

    out = rrt.run_fetcher("fetch_valuation", ("600519",))

    assert out["data"]["pe"] == "20.58"
    assert out["fallback"] is False


def test_pipeline_worker_uses_safe_valuation_when_miniracer_disabled(monkeypatch):
    import importlib

    import fetch_valuation

    collect = importlib.import_module("lib.pipeline.collect")

    monkeypatch.setattr(collect, "_mini_racer_disabled", lambda: True)
    monkeypatch.setattr(
        fetch_valuation,
        "main_safe",
        lambda ticker: {
            "ticker": ticker,
            "data": {"pe": "20.58", "pb": "6.3"},
            "source": "basic (mini_racer-safe)",
            "fallback": False,
        },
    )

    dim_key, result, _top_level = collect._run_fetcher_job("10_valuation", "600519")

    assert dim_key == "10_valuation"
    assert result["data"]["pe"] == "20.58"
    assert result["fallback"] is False
