#!/usr/bin/env python3
"""Theme match quality scoring for Theme Detector.

This module scores how specifically a detected theme is supported by its
industry matches, explicit stock basket, proxy ETFs, and optional narrative
input. It is intentionally deterministic and offline.
"""

import json
from pathlib import Path
from typing import Optional

THEME_MATCH_WEIGHTS = {
    "industry_match_score": 0.40,
    "static_stock_hit_score": 0.30,
    "proxy_etf_momentum_score": 0.20,
    "narrative_keyword_score": 0.10,
}


def load_narrative_scores(path: str) -> dict[str, float]:
    """Load optional caller-supplied narrative scores keyed by theme name.

    Supported shapes:
    - {"AI & Semiconductors": 82}
    - {"AI & Semiconductors": {"narrative_keyword_score": 82}}
    - {"themes": {"AI & Semiconductors": 82}}
    """
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and isinstance(data.get("themes"), dict):
        data = data["themes"]
    if not isinstance(data, dict):
        return {}

    scores: dict[str, float] = {}
    for name, value in data.items():
        if isinstance(value, dict):
            value = value.get("narrative_keyword_score", value.get("narrative_score"))
        score = _float(value)
        if score is not None:
            scores[str(name)] = _clamp(score)
    return scores


def calculate_theme_match(
    theme: dict,
    scan_hits: list,
    etf_volume_map: dict[str, dict],
    scan_hits_available: bool,
    narrative_scores: Optional[dict[str, float]] = None,
) -> dict:
    """Calculate a 0-100 theme match quality score with components."""
    industry_score = _industry_match_score(theme)
    static_stock_score, static_stock_detail = _static_stock_hit_score(
        theme, scan_hits, scan_hits_available
    )
    etf_score, etf_confirmation = _proxy_etf_momentum_score(theme, etf_volume_map)
    narrative_score = _narrative_score(theme, narrative_scores)

    components = {
        "industry_match_score": industry_score,
        "static_stock_hit_score": static_stock_score,
        "proxy_etf_momentum_score": etf_score,
        "narrative_keyword_score": narrative_score,
    }
    score, coverage, missing = _weighted_available_score(components, THEME_MATCH_WEIGHTS)

    return {
        "theme_match_score": round(score, 2) if score is not None else None,
        "theme_match_components": {
            key: round(value, 2) if value is not None else None for key, value in components.items()
        },
        "theme_match_coverage": round(coverage, 4),
        "theme_match_missing_components": missing,
        "static_stock_confirmation": static_stock_detail,
        "proxy_etf_confirmation": etf_confirmation,
    }


def _industry_match_score(theme: dict) -> float:
    industries = theme.get("matching_industries", [])
    if not industries:
        return 0.0

    target_count = theme.get("matching_keyword_count") or max(len(industries), 5)
    count_score = min(len(industries) / max(float(target_count), 1.0), 1.0) * 100.0

    strengths = []
    for industry in industries:
        weighted_return = _float(industry.get("weighted_return"))
        if weighted_return is not None:
            strengths.append(min(abs(weighted_return) / 30.0, 1.0) * 100.0)
    strength_score = sum(strengths) / len(strengths) if strengths else count_score

    return _clamp(0.55 * count_score + 0.45 * strength_score)


def _static_stock_hit_score(
    theme: dict, scan_hits: list, scan_hits_available: bool
) -> tuple[Optional[float], dict]:
    basket = _theme_stock_basket(theme)
    if not scan_hits_available:
        return None, {
            "available": False,
            "basket_size": len(basket),
            "hit_symbols": [],
            "hit_count": 0,
        }

    if not basket:
        return 0.0, {
            "available": True,
            "basket_size": 0,
            "hit_symbols": [],
            "hit_count": 0,
        }

    hits_by_symbol: dict[str, set[str]] = {}
    for hit in scan_hits:
        symbol = getattr(hit, "symbol", None)
        if symbol in basket:
            hits_by_symbol.setdefault(symbol, set()).add(getattr(hit, "scan_type", "unknown"))

    hit_symbols = sorted(hits_by_symbol)
    hit_count = len(hit_symbols)
    score = min(100.0, hit_count * 40.0)
    return score, {
        "available": True,
        "basket_size": len(basket),
        "hit_symbols": hit_symbols,
        "hit_count": hit_count,
        "hit_scan_types": {
            symbol: sorted(scan_types) for symbol, scan_types in hits_by_symbol.items()
        },
    }


def _proxy_etf_momentum_score(
    theme: dict, etf_volume_map: dict[str, dict]
) -> tuple[Optional[float], dict]:
    proxy_etfs = [str(etf).upper() for etf in theme.get("proxy_etfs", [])]
    ratios = []
    matched = []
    missing = []

    for etf in proxy_etfs:
        data = etf_volume_map.get(etf, {})
        ratio = _float(data.get("vol_ratio"))
        if ratio is None:
            missing.append(etf)
            continue
        ratios.append(ratio)
        matched.append({"symbol": etf, "vol_ratio": ratio})

    if not ratios:
        return None, {
            "confirmed": False,
            "average_vol_ratio": None,
            "matched_etfs": matched,
            "missing_etfs": missing or proxy_etfs,
        }

    avg_ratio = sum(ratios) / len(ratios)
    score = _clamp(50.0 + (avg_ratio - 1.0) * 50.0)
    return score, {
        "confirmed": avg_ratio >= 1.2,
        "average_vol_ratio": round(avg_ratio, 4),
        "matched_etfs": matched,
        "missing_etfs": missing,
    }


def _narrative_score(theme: dict, narrative_scores: Optional[dict[str, float]]) -> Optional[float]:
    if not narrative_scores:
        return None
    name = theme.get("theme_name") or theme.get("name")
    value = narrative_scores.get(name)
    return _clamp(value) if value is not None else None


def _theme_stock_basket(theme: dict) -> set[str]:
    stocks = theme.get("static_stocks") or theme.get("representative_stocks") or []
    return {str(stock).upper() for stock in stocks if stock}


def _weighted_available_score(
    components: dict[str, Optional[float]], weights: dict[str, float]
) -> tuple[Optional[float], float, list[str]]:
    available = {key: value for key, value in components.items() if value is not None}
    total_possible = sum(weights.values())
    total_available = sum(weights[key] for key in available)
    if total_available <= 0:
        return None, 0.0, list(components)
    score = sum(available[key] * weights[key] for key in available) / total_available
    missing = [key for key, value in components.items() if value is None]
    return score, total_available / total_possible if total_possible else 0.0, missing


def _float(value) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, float(value)))
