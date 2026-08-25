"""Regression tests for issue #90 US financials TTM freshness."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))


def _fake_yfinance(monkeypatch, ticker_obj):
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=lambda _code: ticker_obj),
    )


def test_us_financials_appends_newer_quarterly_ttm(monkeypatch):
    import fetch_financials

    annual = pd.DataFrame(
        {
            "2025-08-31": [37.4e9, 8.54e9],
            "2024-08-31": [25.1e9, 1.1e9],
        },
        index=["Total Revenue", "Net Income"],
    )
    quarterly = pd.DataFrame(
        {
            "2026-05-31": [41.5e9, 28.2e9],
            "2026-02-28": [36.0e9, 10.0e9],
            "2025-11-30": [32.0e9, 8.0e9],
            "2025-08-31": [29.0e9, 4.3e9],
        },
        index=["Total Revenue", "Net Income"],
    )
    fake = SimpleNamespace(
        financials=annual,
        quarterly_financials=quarterly,
        balance_sheet=pd.DataFrame(),
        cashflow=pd.DataFrame(),
        info={"returnOnEquity": 0.24, "profitMargins": 0.18},
    )
    _fake_yfinance(monkeypatch, fake)

    out = fetch_financials._fetch_us(SimpleNamespace(code="MU"))

    assert out["financial_basis"] == "TTM"
    assert out["financial_period"] == "2026-05-31"
    assert out["financial_years"] == ["2024", "2025", "TTM 2026-05-31"]
    assert out["revenue_history"][-1] == 1385.0
    assert out["net_profit_history"][-1] == 505.0
    assert out["revenue_ttm"] == 1385.0
    assert out["net_profit_ttm"] == 505.0
    assert "financial_staleness_warning" not in out


def test_us_financials_warns_when_latest_period_is_stale(monkeypatch):
    import fetch_financials

    annual = pd.DataFrame(
        {"2025-08-31": [37.4e9, 8.54e9]},
        index=["Total Revenue", "Net Income"],
    )
    fake = SimpleNamespace(
        financials=annual,
        quarterly_financials=pd.DataFrame(),
        balance_sheet=pd.DataFrame(),
        cashflow=pd.DataFrame(),
        info={},
    )
    _fake_yfinance(monkeypatch, fake)

    out = fetch_financials._fetch_us(SimpleNamespace(code="MU"))

    assert out["financial_basis"] == "annual"
    assert out["financial_period"] == "2025-08-31"
    assert out["financial_staleness_days"] > 180
    assert "stale" in out["financial_staleness_warning"]


def test_data_sources_us_financials_exposes_quarterly_income(monkeypatch):
    from lib import data_sources as ds

    annual = pd.DataFrame(
        {"2025-08-31": [37.4e9]},
        index=["Total Revenue"],
    )
    quarterly = pd.DataFrame(
        {"2026-05-31": [41.5e9]},
        index=["Total Revenue"],
    )
    fake = SimpleNamespace(
        financials=annual,
        quarterly_financials=quarterly,
        balance_sheet=pd.DataFrame(),
        cashflow=pd.DataFrame(),
    )
    monkeypatch.setattr(ds, "yf", SimpleNamespace(Ticker=lambda _code: fake))

    out = ds._fetch_financials_impl(SimpleNamespace(market="U", code="MU"))

    assert "income" in out
    assert "quarterly_income" in out
    assert out["quarterly_income"] != {}
