"""Regression tests for issue #87 em-direct fallback and comps integrity."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))


def test_em_direct_payload_does_not_treat_volume_as_change_pct():
    from lib.data_sources import _parse_em_direct_payload

    out = _parse_em_direct_payload({
        "f43": 6237,          # price = 62.37
        "f47": 1281448,       # volume, not change pct
        "f60": 6318,          # prev close = 63.18
        "f116": 457223467965.5,
        "f162": 3120,
        "f167": 238,
    })

    assert out["change_pct"] == -1.28
    assert out["market_cap"] == "4572.2亿"
    assert out["market_cap_raw"] == 457223467965.5
    assert out["pe_ttm"] == 31.2
    assert out["pb"] == 2.38


def test_stock_features_converts_raw_yuan_market_cap_to_yi():
    from lib.stock_features import extract_features

    raw = {
        "ticker": "002475.SZ",
        "market": "A",
        "dimensions": {
            "0_basic": {"data": {
                "name": "立讯精密",
                "price": 62.37,
                "market_cap": 457223467965.5,
            }},
            "7_industry": {"data": {
                "cninfo_metrics": {"total_mcap_yi": 23150.0},
            }},
        },
    }

    features = extract_features(raw, raw["dimensions"])

    assert features["market_cap_yi"] == 4572.234679655
    assert features["market_share"] == 19.75


def test_comps_table_requires_real_peer_universe():
    from lib.fin_models import build_comps_table

    target = {"name": "立讯精密", "ticker": "002475.SZ", "pe": 31.2, "price": 62.37}
    peers = [{"name": "立讯精密", "ticker": "002475.SZ", "pe": 31.2, "is_self": True}]

    comps = build_comps_table(target, peers)

    assert comps["peer_count"] == 0
    assert comps["valuation_verdict"] == "⚪ 同行样本不足 · 无法对标"
    assert comps["target_percentile"] == {}
