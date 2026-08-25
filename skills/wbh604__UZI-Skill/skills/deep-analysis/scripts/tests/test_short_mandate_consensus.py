"""Short-seller mandates must not be reported as long-book buy votes."""
from __future__ import annotations


def _result(signal: str, score: int, headline: str = "x") -> dict:
    return {"signal": signal, "score": score, "confidence": 70, "headline": headline}


def test_short_sellers_are_explicitly_tagged():
    from lib.investor_db import by_id

    assert by_id("burry")["mandate"] == "short"
    assert by_id("chanos")["mandate"] == "short"


def test_panel_summary_separates_short_book_from_long_book():
    from lib.investor_evaluator import panel_summary

    summary = panel_summary({
        "buffett": _result("bullish", 80),
        "graham": _result("bearish", 20),
        "burry": _result("bullish", 85, "no short thesis"),
        "chanos": _result("bearish", 10, "short candidate"),
    })

    assert summary["active"] == 2
    assert summary["bullish"] == 1
    assert summary["bearish"] == 1
    assert summary["short_consensus"]["short_candidates"] == 1
    assert summary["short_consensus"]["no_short_thesis"] == 1


def test_generate_panel_uses_short_specific_verdicts(monkeypatch):
    import lib.pipeline.score_fns as score_fns

    investors = [
        {"id": "long", "name": "Long", "group": "A"},
        {"id": "burry", "name": "Burry", "group": "C", "mandate": "short"},
        {"id": "chanos", "name": "Chanos", "group": "C", "mandate": "short"},
    ]
    verdicts = {
        "long": _result("bullish", 80),
        "burry": _result("bullish", 85, "no short thesis"),
        "chanos": _result("bearish", 10, "short candidate"),
    }
    for verdict in verdicts.values():
        verdict.update({
            "confidence": 70,
            "rationale": verdict["headline"],
            "pass_rules": [],
            "fail_rules": [],
            "weight_pass": 0,
            "weight_total": 0,
        })

    monkeypatch.setattr(score_fns, "INVESTORS", investors)
    monkeypatch.setattr(score_fns, "extract_features", lambda raw, dims: {})
    monkeypatch.setattr(score_fns, "_evaluate_investor", lambda investor_id, features: verdicts[investor_id])
    monkeypatch.setattr(score_fns, "_persona_comment", lambda *args: "persona")

    panel = score_fns.generate_panel({}, {"ticker": "TEST", "dimensions": {}})
    by_id = {item["investor_id"]: item for item in panel["investors"]}

    assert panel["signal_distribution"] == {"bullish": 1, "neutral": 0, "bearish": 0, "skip": 0}
    assert panel["long_active"] == 1
    assert panel["short_consensus"]["short_candidates"] == 1
    assert panel["school_scores"]["C"]["n_members"] == 0
    assert panel["school_scores"]["C"]["short_excluded"] == 2
    assert by_id["burry"]["verdict"] == "无明确做空逻辑"
    assert by_id["chanos"]["verdict"] == "做空候选"


def test_top_long_lists_exclude_short_mandate():
    from lib.report.panel_cards import render_top3_bulls, render_top3_bears

    investors = [
        {"investor_id": "long", "name": "Long", "signal": "bullish", "score": 70},
        {"investor_id": "burry", "name": "Burry", "signal": "bullish", "score": 95, "mandate": "short"},
        {"investor_id": "chanos", "name": "Chanos", "signal": "bearish", "score": 5, "mandate": "short"},
    ]

    bulls = render_top3_bulls(investors)
    bears = render_top3_bears(investors)
    assert "Long" in bulls and "Burry" not in bulls
    assert "Chanos" not in bears
