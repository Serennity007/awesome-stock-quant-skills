"""Global peer discovery, ranking and financial normalization primitives."""
from __future__ import annotations

import math
import re
import statistics
import time
from datetime import datetime, timezone
from typing import Any

import requests

from lib.cache import TTL_QUARTERLY, cached
from lib.market_router import parse_ticker


_YAHOO_FACTS = {
    "annualTotalRevenue": "revenue",
    "annualGrossProfit": "gross_profit",
    "annualOperatingIncome": "operating_income",
    "annualNetIncome": "net_income",
    "annualStockholdersEquity": "equity",
    "annualOperatingCashFlow": "operating_cash_flow",
    "annualCapitalExpenditure": "capital_expenditure",
}

_LEGAL_SUFFIXES = re.compile(
    r"\b(incorporated|inc|corporation|corp|company|co|limited|ltd|plc|group|holdings?)\b",
    re.IGNORECASE,
)


def to_yahoo_symbol(ticker_info) -> str:
    """Map UZI canonical symbols to Yahoo's exchange suffix conventions."""
    market = getattr(ticker_info, "market", None)
    if market is None:
        return str(getattr(ticker_info, "full", None) or ticker_info.code).upper()
    if market == "A":
        suffix = ticker_info.full.rsplit(".", 1)[-1].upper()
        yahoo_suffix = "SS" if suffix == "SH" else suffix
        return f"{ticker_info.code}.{yahoo_suffix}"
    if market == "H":
        return f"{str(ticker_info.code).zfill(4)}.HK"
    return ticker_info.full.upper()


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _ratio(numerator: Any, denominator: Any) -> float | None:
    num = _number(numerator)
    den = _number(denominator)
    if num is None or den in (None, 0):
        return None
    return round(num / den * 100, 2)


def normalize_yahoo_timeseries(symbol: str, payload: dict) -> dict:
    """Translate Yahoo annual fundamentals into an auditable canonical series."""
    periods: dict[str, dict] = {}
    currency = None
    result = ((payload or {}).get("timeseries") or {}).get("result") or []
    for series in result:
        if not isinstance(series, dict):
            continue
        meta_types = (series.get("meta") or {}).get("type") or []
        yahoo_key = next((key for key in meta_types if key in _YAHOO_FACTS), None)
        if yahoo_key is None:
            yahoo_key = next((key for key in _YAHOO_FACTS if key in series), None)
        if yahoo_key is None:
            continue
        canonical_key = _YAHOO_FACTS[yahoo_key]
        for point in series.get(yahoo_key) or []:
            if not isinstance(point, dict) or point.get("periodType") not in (None, "12M"):
                continue
            period = str(point.get("asOfDate") or "")[:10]
            value = _number((point.get("reportedValue") or {}).get("raw"))
            if not period or value is None:
                continue
            currency = currency or point.get("currencyCode")
            periods.setdefault(period, {})[canonical_key] = value

    for facts in periods.values():
        facts["gross_margin"] = _ratio(facts.get("gross_profit"), facts.get("revenue"))
        facts["operating_margin"] = _ratio(facts.get("operating_income"), facts.get("revenue"))
        facts["net_margin"] = _ratio(facts.get("net_income"), facts.get("revenue"))
        facts["roe"] = _ratio(facts.get("net_income"), facts.get("equity"))
        ocf = _number(facts.get("operating_cash_flow"))
        capex = _number(facts.get("capital_expenditure"))
        if ocf is not None and capex is not None:
            facts["free_cash_flow"] = ocf + capex if capex < 0 else ocf - capex

    return {
        "symbol": symbol,
        "basis": "annual",
        "currency": currency,
        "periods": dict(sorted(periods.items())),
        "source": "yahoo_fundamentals_timeseries",
    }


def apply_yearly_fx(financials: dict, yearly_rates: dict[str, float], base_currency: str = "USD") -> dict:
    """Add comparable monetary facts while preserving original reported values."""
    result = dict(financials)
    result["base_currency"] = base_currency
    periods = {}
    for period, raw_facts in (financials.get("periods") or {}).items():
        facts = dict(raw_facts or {})
        rate = _number(yearly_rates.get(str(period)[:4]))
        if rate is not None and rate > 0:
            facts["fx_rate_to_base"] = rate
            for metric in ("revenue", "gross_profit", "operating_income", "net_income",
                           "equity", "operating_cash_flow", "capital_expenditure", "free_cash_flow"):
                value = _number(facts.get(metric))
                if value is not None:
                    facts[f"{metric}_base"] = round(value * rate, 4)
        periods[period] = facts
    result["periods"] = periods
    return result


def issuer_key(name: str) -> str:
    normalized = _LEGAL_SUFFIXES.sub(" ", str(name or ""))
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", normalized.lower())


def _candidate_score(target: dict, candidate: dict) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if target.get("industry") and target.get("industry") == candidate.get("industry"):
        score += 40
        reasons.append("细分行业一致")
    if target.get("sector") and target.get("sector") == candidate.get("sector"):
        score += 15
        reasons.append("行业板块一致")

    target_has_base = target.get("market_cap_base") is not None
    candidate_has_base = candidate.get("market_cap_base") is not None
    target_cap = _number(target.get("market_cap_base") if target_has_base else target.get("market_cap"))
    candidate_cap = _number(candidate.get("market_cap_base") if candidate_has_base else candidate.get("market_cap"))
    same_currency = bool(
        target.get("currency") and candidate.get("currency")
        and target.get("currency") == candidate.get("currency")
    )
    comparable_scale = (target_has_base and candidate_has_base) or same_currency
    if comparable_scale and target_cap and target_cap > 0 and candidate_cap and candidate_cap > 0:
        distance = abs(math.log10(candidate_cap / target_cap))
        scale_score = max(0.0, 20.0 * (1.0 - distance / 3.0))
        score += scale_score
        if distance <= 1:
            reasons.append("规模可比")

    coverage = _number(candidate.get("data_coverage"))
    if coverage is not None:
        score += max(0.0, min(1.0, coverage)) * 15
        if coverage >= 0.7:
            reasons.append("财务数据完整")

    provider_score = _number(candidate.get("provider_score"))
    if provider_score is not None:
        score += max(0.0, min(1.0, provider_score)) * 10
    if candidate.get("is_secondary"):
        score -= 25
    return round(max(score, 0.0), 2), reasons or ["候选来源关联"]


def rank_global_candidates(target: dict, candidates: list[dict], limit: int = 8) -> list[dict]:
    """Remove duplicate issuers and return the most comparable global listings."""
    target_symbol = str(target.get("symbol") or "").upper()
    target_issuer = issuer_key(target.get("name") or "")
    best_by_issuer: dict[str, dict] = {}

    for raw in candidates or []:
        if not isinstance(raw, dict):
            continue
        symbol = str(raw.get("symbol") or "").upper()
        key = issuer_key(raw.get("name") or symbol)
        if not symbol or symbol == target_symbol or (target_issuer and key == target_issuer):
            continue
        score, reasons = _candidate_score(target, raw)
        candidate = dict(raw)
        candidate["symbol"] = symbol
        candidate["relevance_score"] = score
        candidate["selection_reasons"] = reasons
        current = best_by_issuer.get(key)
        if current is None or score > current["relevance_score"]:
            best_by_issuer[key] = candidate

    ranked = sorted(
        best_by_issuer.values(),
        key=lambda item: (item["relevance_score"], item.get("data_coverage") or 0),
        reverse=True,
    )
    return ranked[:max(0, limit)]


class YahooGlobalPeerProvider:
    """No-key global discovery and annual fundamentals fallback.

    The network host is fixed and symbols are allowlisted before entering a URL,
    preventing user-controlled requests from becoming an SSRF primitive.
    """

    _BASE = "https://query2.finance.yahoo.com"
    _SYMBOL = re.compile(r"^[A-Z0-9.\-^=]{1,32}$", re.IGNORECASE)
    _FACT_TYPES = ",".join(_YAHOO_FACTS)

    def __init__(self, session=None, yf_module=None, timeout: float = 12.0):
        self.session = session or requests.Session()
        if yf_module is None:
            try:
                import yfinance as yf_module  # type: ignore
            except ImportError:
                yf_module = None
        self.yf = yf_module
        self.timeout = max(1.0, min(float(timeout), 15.0))

    @classmethod
    def _validate_symbol(cls, symbol: str) -> str:
        normalized = str(symbol or "").strip().upper()
        if not cls._SYMBOL.fullmatch(normalized):
            raise ValueError(f"unsupported Yahoo symbol: {symbol!r}")
        return normalized

    def profile(self, symbol: str) -> dict:
        symbol = self._validate_symbol(symbol)
        ticker_info = parse_ticker(symbol)
        if self.yf is None:
            return {"symbol": symbol, "market": ticker_info.market, "country": ticker_info.country,
                    "exchange": ticker_info.exchange, "currency": ticker_info.currency}
        try:
            info = self.yf.Ticker(symbol).info or {}
        except Exception:
            return {"symbol": symbol}
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "market": ticker_info.market,
            "country": ticker_info.country,
            "exchange": info.get("exchange") or ticker_info.exchange,
            "industry": info.get("industry"),
            "sector": info.get("sector"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency"),
            "financial_currency": info.get("financialCurrency"),
            "source": "yfinance_profile",
        }

    @staticmethod
    def _quote_candidate(quote: dict) -> dict:
        symbol = str(quote.get("symbol") or "").upper()
        ti = parse_ticker(symbol)
        currency = quote.get("currency")
        financial_currency = quote.get("financialCurrency")
        covered = sum(
            quote.get(field) not in (None, "")
            for field in ("marketCap", "industry", "sector", "trailingPE", "priceToBook")
        ) / 5
        return {
            "symbol": symbol,
            "name": quote.get("longName") or quote.get("shortName") or symbol,
            "market": ti.market,
            "country": ti.country,
            "exchange": quote.get("exchange") or ti.exchange,
            "currency": currency or ti.currency,
            "financial_currency": financial_currency,
            "industry": quote.get("industry"),
            "sector": quote.get("sector"),
            "market_cap": quote.get("marketCap"),
            "pe": quote.get("trailingPE"),
            "pb": quote.get("priceToBook"),
            "data_coverage": round(covered, 2),
            "is_secondary": bool(currency and financial_currency and currency != financial_currency),
            "source": "yfinance_equity_screener",
        }

    def discover(self, target_symbol: str, limit: int = 30) -> list[dict]:
        target = self.profile(target_symbol)
        industry = target.get("industry")
        if self.yf is None or not industry:
            return []
        try:
            query = self.yf.EquityQuery("EQ", ["industry", industry])
            result = self.yf.screen(
                query,
                size=max(20, min(100, limit * 5)),
                sortField="intradaymarketcap",
                sortAsc=False,
            ) or {}
        except Exception:
            return []
        quotes = [
            quote for quote in result.get("quotes") or []
            if isinstance(quote, dict) and quote.get("symbol")
        ]
        candidates = []
        quote_count = max(1, len(quotes))
        for index, quote in enumerate(quotes):
            candidate = self._quote_candidate(quote)
            candidate["industry"] = candidate.get("industry") or target.get("industry")
            candidate["sector"] = candidate.get("sector") or target.get("sector")
            candidate["provider_score"] = round(1 - index / quote_count, 4)
            candidates.append(candidate)
        return rank_global_candidates(target, candidates, limit=limit)

    def financials(self, symbol: str, years: int = 6) -> dict:
        symbol = self._validate_symbol(symbol)
        now = int(time.time())
        url = f"{self._BASE}/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}"
        response = self.session.get(
            url,
            params={
                "symbol": symbol,
                "type": self._FACT_TYPES,
                "period1": now - max(2, min(years, 10)) * 366 * 86400,
                "period2": now,
            },
            headers={"User-Agent": "UZI-Skill/3 global-peer-comparison"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return normalize_yahoo_timeseries(symbol, response.json())


class YahooFxProvider:
    """Fetch calendar-year average FX rates from a fixed Yahoo chart host."""

    _BASE = "https://query1.finance.yahoo.com"
    _CURRENCY = re.compile(r"^[A-Z]{3}$")

    def __init__(self, session=None, timeout: float = 12.0):
        self.session = session or requests.Session()
        self.timeout = max(1.0, min(float(timeout), 15.0))

    def _chart(self, symbol: str, years: int) -> dict[str, float]:
        now = int(time.time())
        response = self.session.get(
            f"{self._BASE}/v8/finance/chart/{symbol}",
            params={
                "period1": now - max(2, min(years, 10)) * 366 * 86400,
                "period2": now,
                "interval": "1d",
                "events": "history",
            },
            headers={"User-Agent": "UZI-Skill/3 global-peer-comparison"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = (((response.json() or {}).get("chart") or {}).get("result") or [])
        if not result:
            return {}
        series = result[0]
        timestamps = series.get("timestamp") or []
        closes = ((((series.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or [])
        grouped: dict[str, list[float]] = {}
        for timestamp, close in zip(timestamps, closes):
            value = _number(close)
            if value is None or value <= 0:
                continue
            year = str(datetime.fromtimestamp(timestamp, tz=timezone.utc).year)
            grouped.setdefault(year, []).append(value)
        return {year: round(sum(values) / len(values), 8) for year, values in grouped.items()}

    def rates(self, source_currency: str, base_currency: str = "USD", years: int = 6) -> dict[str, float]:
        source = str(source_currency or "").upper()
        base = str(base_currency or "").upper()
        if not self._CURRENCY.fullmatch(source) or not self._CURRENCY.fullmatch(base):
            raise ValueError("currency must be a three-letter ISO-like code")
        if source == base:
            current_year = datetime.now(tz=timezone.utc).year
            return {str(year): 1.0 for year in range(current_year - years, current_year + 1)}
        direct = self._chart(f"{source}{base}=X", years)
        if direct:
            return direct
        inverse = self._chart(f"{base}{source}=X", years)
        return {year: round(1 / value, 8) for year, value in inverse.items() if value > 0}


_COMPARABLE_METRICS = (
    "revenue_base",
    "net_income_base",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "roe",
    "free_cash_flow_base",
)


def _benchmarks(peers: list[dict]) -> dict:
    grouped: dict[str, dict[str, list[float]]] = {}
    for peer in peers:
        for period, facts in (peer.get("financials") or {}).get("periods", {}).items():
            year = str(period)[:4]
            if len(year) != 4 or not isinstance(facts, dict):
                continue
            for metric in _COMPARABLE_METRICS:
                value = _number(facts.get(metric))
                if value is not None:
                    grouped.setdefault(metric, {}).setdefault(year, []).append(value)

    result: dict[str, dict] = {}
    for metric, years in grouped.items():
        result[metric] = {}
        for year, values in sorted(years.items()):
            ordered = sorted(values)
            if len(ordered) >= 2:
                quartiles = statistics.quantiles(ordered, n=4)
                p25, p75 = quartiles[0], quartiles[2]
            else:
                p25 = p75 = ordered[0]
            result[metric][year] = {
                "min": round(ordered[0], 2),
                "p25": round(p25, 2),
                "median": round(statistics.median(ordered), 2),
                "p75": round(p75, 2),
                "max": round(ordered[-1], 2),
                "n": len(ordered),
            }
    return result


def _latest_facts(financials: dict) -> tuple[str | None, dict]:
    periods = financials.get("periods") or {}
    if not periods:
        return None, {}
    period = max(periods)
    return period, periods.get(period) or {}


def _target_percentile(target_financials: dict, peers: list[dict]) -> dict:
    if len(peers) < 3:
        return {}
    target_period, target_facts = _latest_facts(target_financials)
    if not target_period:
        return {}
    year = target_period[:4]
    result = {}
    for metric in _COMPARABLE_METRICS:
        target_value = _number(target_facts.get(metric))
        values = []
        for peer in peers:
            periods = (peer.get("financials") or {}).get("periods") or {}
            matching = [facts for period, facts in periods.items() if str(period).startswith(year)]
            if matching:
                value = _number(matching[-1].get(metric))
                if value is not None:
                    values.append(value)
        if target_value is not None and len(values) >= 3:
            result[metric] = round(sum(value < target_value for value in values) / len(values) * 100, 1)
    return result


def build_global_peer_comparison(
    target_symbol: str,
    provider: YahooGlobalPeerProvider | None = None,
    limit: int = 8,
) -> dict:
    """Discover and enrich a bounded peer set while isolating source failures."""
    provider = provider or YahooGlobalPeerProvider()
    target_symbol = provider._validate_symbol(target_symbol) if hasattr(provider, "_validate_symbol") else target_symbol
    target_profile = provider.profile(target_symbol)
    failures: dict[str, str] = {}
    try:
        target_financials = provider.financials(target_symbol)
    except Exception as exc:
        target_financials = {"symbol": target_symbol, "basis": "annual", "periods": {}}
        failures[target_symbol] = f"{type(exc).__name__}: {str(exc)[:160]}"

    peers = []
    candidate_limit = min(max(1, limit) * 2, 24)
    for candidate in provider.discover(target_symbol, limit=candidate_limit)[:candidate_limit]:
        if len(peers) >= limit:
            break
        symbol = str(candidate.get("symbol") or "")
        if not symbol:
            continue
        try:
            financials = provider.financials(symbol)
            if not financials.get("periods"):
                raise ValueError("empty annual financial series")
        except Exception as exc:
            failures[symbol] = f"{type(exc).__name__}: {str(exc)[:160]}"
            continue
        peer = dict(candidate)
        peer["financials"] = financials
        peers.append(peer)

    target_percentile = _target_percentile(target_financials, peers)
    return {
        "target": {**target_profile, "financials": target_financials},
        "peers": peers,
        "peer_count": len(peers),
        "benchmarks": _benchmarks(peers),
        "target_percentile": target_percentile,
        "conclusion_status": "ready" if len(peers) >= 3 else "insufficient_peers",
        "failed_symbols": sorted(failures),
        "failures": failures,
        "source": "global_peer_provider_registry",
    }


def apply_comparison_fx(result: dict, fx_provider: YahooFxProvider, base_currency: str = "USD") -> dict:
    """Normalize monetary facts once per currency, then rebuild comparable stats."""
    out = dict(result)
    rates_by_currency: dict[str, dict[str, float]] = {}

    def convert(financials: dict) -> dict:
        currency = str(financials.get("currency") or "").upper()
        if not currency:
            return financials
        if currency not in rates_by_currency:
            try:
                rates_by_currency[currency] = fx_provider.rates(currency, base_currency)
            except Exception:
                rates_by_currency[currency] = {}
        rates = rates_by_currency[currency]
        return apply_yearly_fx(financials, rates, base_currency) if rates else financials

    target = dict(out.get("target") or {})
    target["financials"] = convert(target.get("financials") or {})
    out["target"] = target
    peers = []
    for raw_peer in out.get("peers") or []:
        peer = dict(raw_peer)
        peer["financials"] = convert(peer.get("financials") or {})
        peers.append(peer)
    out["peers"] = peers
    out["base_currency"] = base_currency
    out["benchmarks"] = _benchmarks(peers)
    out["target_percentile"] = _target_percentile(target["financials"], peers)
    out["fx_currencies"] = sorted(currency for currency, rates in rates_by_currency.items() if rates)
    return out


def global_peers_to_comps(comparison: dict) -> list[dict]:
    """Adapt latest normalized global peer facts to `build_comps_table`."""
    result = []
    for peer in comparison.get("peers") or []:
        periods = (peer.get("financials") or {}).get("periods") or {}
        if not periods:
            continue
        ordered_periods = sorted(periods)
        latest = periods[ordered_periods[-1]] or {}
        growth = None
        if len(ordered_periods) >= 2:
            previous = _number((periods[ordered_periods[-2]] or {}).get("revenue_base"))
            current = _number(latest.get("revenue_base"))
            if previous not in (None, 0) and current is not None:
                growth = round((current / previous - 1) * 100, 2)
        result.append({
            "name": peer.get("name") or peer.get("symbol"),
            "ticker": peer.get("symbol"),
            "pe": peer.get("pe"),
            "pb": peer.get("pb"),
            "ps": peer.get("ps"),
            "roe": latest.get("roe"),
            "net_margin": latest.get("net_margin"),
            "revenue_growth": growth,
            "market_cap_yi": 0,
        })
    return result


def fetch_global_peer_comparison(
    ticker_info,
    basic: dict | None = None,
    limit: int = 8,
    provider: YahooGlobalPeerProvider | None = None,
    use_cache: bool = True,
) -> dict:
    """Cached entrypoint used by the existing 4_peers fetcher."""
    symbol = to_yahoo_symbol(ticker_info)

    def collect():
        result = build_global_peer_comparison(symbol, provider=provider, limit=limit)
        result = apply_comparison_fx(result, YahooFxProvider(), "USD")
        if basic:
            target = result.setdefault("target", {})
            target["uzi_symbol"] = ticker_info.full
            target["name"] = basic.get("name") or target.get("name")
            target["local_industry"] = basic.get("industry")
        return result

    if provider is not None or not use_cache:
        return collect()
    return cached(
        ticker_info.full,
        f"global_peer_comparison_v2__{symbol}__n{limit}",
        collect,
        ttl=TTL_QUARTERLY,
    )
