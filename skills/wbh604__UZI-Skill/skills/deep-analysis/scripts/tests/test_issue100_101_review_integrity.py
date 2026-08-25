"""Regressions for GitHub issues #100 and #101."""
from __future__ import annotations

import json


def _complete_raw() -> dict:
    dimensions = {
        "0_basic": {
            "data": {
                "name": "Test Co",
                "price": 10,
                "industry": "通信设备",
                "market_cap": 100,
                "pe_ttm": 20,
                "pb": 2,
            }
        },
        "1_financials": {
            "data": {
                "roe_history": [10, 11, 12],
                "revenue_history": [80, 90, 100],
                "net_profit_history": [8, 9, 10],
                "financial_health": {"debt_ratio": 30},
            }
        },
        "2_kline": {"data": {"stage": "Stage 2", "ma_align": "bull", "macd": "up"}},
        "10_valuation": {"data": {"pe": 20, "pe_quantile": 30, "pb_quantile": 40}},
        "7_industry": {"data": {"growth": 8}},
        "14_moat": {"data": {"scores": {"scale": 7}}},
    }
    enrichment_dims = (
        "3_macro", "4_peers", "5_chain", "6_research", "8_materials",
        "9_futures", "11_governance", "12_capital_flow", "13_policy",
        "15_events", "16_lhb", "17_sentiment", "18_trap", "19_contests",
    )
    for dim in enrichment_dims:
        dimensions[dim] = {"data": {"evidence": "available"}}
    return {"ticker": "600487.SH", "fetched_at": "2026-08-16T12:00:00", "dimensions": dimensions}


def test_self_review_accepts_current_dcf_and_comps_field_names():
    from lib.self_review import check_valuation_sanity

    ctx = {
        "dims": {
            "20_valuation_models": {
                "data": {
                    "dcf": {"intrinsic_per_share": 30.32},
                    "comps": {"implied_price": {"via_median_pe": 28.5}},
                }
            }
        }
    }

    assert check_valuation_sanity(ctx) == []


def test_recovery_artifact_is_removed_after_raw_data_is_filled(tmp_path):
    from lib.data_integrity import refresh_recovery_artifact

    raw = _complete_raw()
    raw["dimensions"]["0_basic"]["data"]["industry"] = None
    gaps_path = tmp_path / "_data_gaps.json"

    first = refresh_recovery_artifact(raw, "600487.SH", gaps_path)
    assert first["critical_missing"] is True
    assert gaps_path.exists()
    assert any(
        task["dim"] == "0_basic" and task["field"] == "industry"
        for task in json.loads(gaps_path.read_text(encoding="utf-8"))["tasks"]
    )

    raw["dimensions"]["0_basic"]["data"]["industry"] = "通信-通信设备"
    second = refresh_recovery_artifact(raw, "600487.SH", gaps_path)

    assert second["critical_missing"] is False
    assert not gaps_path.exists()
    assert raw["_integrity"]["coverage_pct"] == 100


def test_recovery_artifact_records_raw_snapshot_timestamp(tmp_path):
    from lib.data_integrity import refresh_recovery_artifact

    raw = _complete_raw()
    raw["dimensions"]["0_basic"]["data"]["industry"] = None
    gaps_path = tmp_path / "_data_gaps.json"
    refresh_recovery_artifact(raw, "600487.SH", gaps_path)

    document = json.loads(gaps_path.read_text(encoding="utf-8"))
    assert document["raw_fetched_at"] == "2026-08-16T12:00:00"
    assert document["generated_at"]
