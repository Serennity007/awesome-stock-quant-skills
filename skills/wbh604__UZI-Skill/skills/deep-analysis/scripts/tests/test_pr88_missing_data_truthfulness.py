"""Truthfulness regressions distilled from PR #88 without its FCF blocker."""
from __future__ import annotations

import pandas as pd


def _minimal_dims(financials: dict | None = None) -> dict:
    return {
        "0_basic": {"data": {"name": "测试公司", "price": 10, "market_cap": 100}},
        "1_financials": {"data": financials or {}},
        "14_moat": {"data": {}},
    }


def test_a_share_financial_ratios_use_annual_period(monkeypatch):
    import fetch_financials as ff
    from lib.market_router import parse_ticker

    indicator = pd.DataFrame({
        "日期": ["2025-12-31", "2026-03-31"],
        "加权净资产收益率(%)": [26.61, 9.06],
        "流动比率": [1.2, 1.5],
        "资产负债率(%)": [50.0, 55.0],
        "总资产净利率(%)": [12.0, 3.0],
        "销售净利率(%)": [20.0, 21.0],
        "总资产周转率(次)": [0.8, 0.2],
    })
    empty = pd.DataFrame()
    monkeypatch.setattr(ff.ak, "stock_financial_abstract", lambda **_kwargs: empty)
    monkeypatch.setattr(ff.ak, "stock_financial_analysis_indicator", lambda **_kwargs: indicator)
    monkeypatch.setattr(ff.ak, "stock_balance_sheet_by_report_em", lambda **_kwargs: empty)
    monkeypatch.setattr(ff.ak, "stock_cash_flow_sheet_by_report_em", lambda **_kwargs: empty)
    monkeypatch.setattr(ff.ak, "stock_history_dividend_detail", lambda **_kwargs: empty)

    out = ff._fetch_a_share(parse_ticker("603993.SH"))

    assert out["roe"] == "26.6%"
    assert out["roe_mrq"] == "9.1%"
    assert out["net_margin"] == "20.0%"
    assert out["financial_period"] == "2025-12-31"
    assert out["financial_health"]["current_ratio"] == 1.5
    assert out["financial_health"]["debt_ratio"] == 55.0
    assert out["financial_health"]["roic"] == 12.0
    assert out["dupont"]["net_margin_pct"] == 20.0


def test_all_zero_financial_histories_are_dropped():
    from fetch_financials import _drop_all_zero_histories

    out = {
        "revenue_history": [0.0, 0.0, 0.0],
        "net_profit_history": [0.0, 1.0, 2.0],
    }

    _drop_all_zero_histories(out)

    assert "revenue_history" not in out
    assert out["net_profit_history"] == [0.0, 1.0, 2.0]
    assert out["_zero_history_dropped"] == ["revenue_history"]


def test_missing_cash_flow_is_unknown_and_investor_rule_skips():
    from lib.investor_criteria import BUFFETT_RULES
    from lib.investor_evaluator import _safe_check
    from lib.stock_features import extract_features

    dims = _minimal_dims({"net_profit_history": [10.0]})
    features = extract_features({"ticker": "TEST", "dimensions": dims}, dims)
    fcf_rule = next(rule for rule in BUFFETT_RULES if rule.rule_id == "fcf_positive")

    assert features["fcf_known"] is False
    assert features["fcf_positive"] is None
    assert features["fcf_is_proxy"] is True
    assert _safe_check(fcf_rule, features) is None


def test_no_sentiment_evidence_is_not_bearish(monkeypatch):
    import fetch_sentiment as sentiment
    import lib.hottrend as hottrend
    import lib.news_providers as news

    monkeypatch.setattr(sentiment.ds, "fetch_basic", lambda _ticker: {"name": "测试公司"})
    monkeypatch.setattr(sentiment, "search", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(hottrend, "get_hot_mentions", lambda _name: {"total_hits": 0})
    monkeypatch.setattr(news, "get_news_multi_source", lambda **_kwargs: {"total_hits": 0, "sources": {}})

    data = sentiment.main("600000.SH")["data"]

    assert data["sentiment_data_available"] is False
    assert data["positive_pct"] == "—"
    assert "数据缺失" in data["sentiment_label"]
    assert "悲观" not in data["sentiment_label"]


def test_no_moat_evidence_does_not_create_neutral_scores(monkeypatch):
    import fetch_moat as moat

    monkeypatch.setattr(moat.ds, "fetch_basic", lambda _ticker: {"name": "测试公司"})
    monkeypatch.setattr(moat, "search", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(moat, "search_trusted", lambda *_args, **_kwargs: [])

    data = moat.main("600000.SH")["data"]

    assert data["scores"] == {}
    assert data["scores_available"] is False
    assert "未评估" in data["scores_note"]


def test_hollow_long_verdicts_invalidate_consensus(monkeypatch):
    import lib.pipeline.score_fns as score_fns

    investors = [{"id": f"i{i}", "name": f"I{i}", "group": "A"} for i in range(5)]

    def verdict(investor_id, _features):
        hollow = investor_id == "i0"
        return {
            "signal": "bearish" if hollow else "neutral",
            "score": 0 if hollow else 50,
            "confidence": 50,
            "headline": "no evidence" if hollow else "evaluated",
            "rationale": "",
            "pass_rules": [] if hollow else [{"name": "x", "msg": "x", "weight": 1}],
            "fail_rules": [],
            "weight_pass": 0 if hollow else 1,
            "weight_total": 0 if hollow else 1,
        }

    monkeypatch.setattr(score_fns, "INVESTORS", investors)
    monkeypatch.setattr(score_fns, "extract_features", lambda *_args: {})
    monkeypatch.setattr(score_fns, "_evaluate_investor", verdict)
    monkeypatch.setattr(score_fns, "_persona_comment", lambda *_args: "persona")

    panel = score_fns.generate_panel({}, {"ticker": "TEST", "dimensions": {}})

    assert panel["consensus_valid"] is False
    assert panel["hollow_pct"] == 20
    assert panel["hollow_ids"] == ["i0"]


def test_self_review_rejects_hollow_consensus():
    from lib.self_review import check_panel_hollow_verdicts

    issues = check_panel_hollow_verdicts({
        "panel": {
            "consensus_valid": False,
            "hollow_verdicts": 2,
            "hollow_pct": 25,
            "hollow_ids": ["a", "b"],
            "panel_consensus": 30,
        }
    })

    assert len(issues) == 1
    assert issues[0].severity == "critical"
