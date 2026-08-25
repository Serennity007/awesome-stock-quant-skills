"""Global peer comparison routing and normalization tests."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

from lib.market_router import parse_ticker


def test_parse_ticker_routes_major_global_exchange_suffixes():
    cases = {
        "7203.T": ("JP", "TSE", "JPY"),
        "005930.KS": ("KR", "KRX", "KRW"),
        "2330.TW": ("TW", "TWSE", "TWD"),
        "D05.SI": ("SG", "SGX", "SGD"),
        "SHOP.TO": ("CA", "TSX", "CAD"),
        "BHP.AX": ("AU", "ASX", "AUD"),
        "ASML.AS": ("NL", "EURONEXT_AMSTERDAM", "EUR"),
        "SHEL.L": ("GB", "LSE", "GBP"),
        "SIE.DE": ("DE", "XETRA", "EUR"),
        "AIR.PA": ("FR", "EURONEXT_PARIS", "EUR"),
    }

    for symbol, expected in cases.items():
        info = parse_ticker(symbol)
        assert (info.market, info.exchange, info.currency) == expected
        assert info.full == symbol


def test_parse_ticker_routes_additional_global_venues():
    cases = {
        "NESN.SW": ("CH", "SIX", "CHF"),
        "SAN.MC": ("ES", "BME", "EUR"),
        "ENI.MI": ("IT", "BORSA_ITALIANA", "EUR"),
        "ERIC-B.ST": ("SE", "OMX_STOCKHOLM", "SEK"),
        "PETR4.SA": ("BR", "B3", "BRL"),
        "AMXL.MX": ("MX", "BMV", "MXN"),
        "BBCA.JK": ("ID", "IDX", "IDR"),
        "NPN.JO": ("ZA", "JSE", "ZAR"),
        "RELIANCE.NS": ("IN", "NSE", "INR"),
    }

    for symbol, expected in cases.items():
        info = parse_ticker(symbol)
        assert (info.market, info.exchange, info.currency) == expected


def test_unknown_exchange_suffix_is_global_not_a_share():
    info = parse_ticker("EXAMPLE.XX")

    assert info.market == "G"
    assert info.exchange == "XX"


def test_parse_ticker_keeps_existing_market_contract():
    assert parse_ticker("600519.SH").market == "A"
    assert parse_ticker("00700.HK").market == "H"
    assert parse_ticker("AAPL").market == "U"


def test_to_yahoo_symbol_normalizes_existing_markets():
    from lib.global_peers import to_yahoo_symbol

    assert to_yahoo_symbol(parse_ticker("600519.SH")) == "600519.SS"
    assert to_yahoo_symbol(parse_ticker("000001.SZ")) == "000001.SZ"
    assert to_yahoo_symbol(parse_ticker("00700.HK")) == "0700.HK"
    assert to_yahoo_symbol(parse_ticker("AAPL")) == "AAPL"
    assert to_yahoo_symbol(parse_ticker("7203.T")) == "7203.T"


def test_normalize_yahoo_timeseries_builds_comparable_annual_metrics():
    from lib.global_peers import normalize_yahoo_timeseries

    payload = {
        "timeseries": {
            "result": [
                {
                    "meta": {"type": ["annualTotalRevenue"]},
                    "annualTotalRevenue": [
                        {"asOfDate": "2023-12-31", "currencyCode": "JPY", "reportedValue": {"raw": 1000}},
                        {"asOfDate": "2024-12-31", "currencyCode": "JPY", "reportedValue": {"raw": 1200}},
                    ],
                },
                {
                    "meta": {"type": ["annualGrossProfit"]},
                    "annualGrossProfit": [
                        {"asOfDate": "2023-12-31", "currencyCode": "JPY", "reportedValue": {"raw": 300}},
                        {"asOfDate": "2024-12-31", "currencyCode": "JPY", "reportedValue": {"raw": 420}},
                    ],
                },
                {
                    "meta": {"type": ["annualNetIncome"]},
                    "annualNetIncome": [
                        {"asOfDate": "2023-12-31", "currencyCode": "JPY", "reportedValue": {"raw": 100}},
                        {"asOfDate": "2024-12-31", "currencyCode": "JPY", "reportedValue": {"raw": 180}},
                    ],
                },
                {
                    "meta": {"type": ["annualStockholdersEquity"]},
                    "annualStockholdersEquity": [
                        {"asOfDate": "2023-12-31", "currencyCode": "JPY", "reportedValue": {"raw": 500}},
                        {"asOfDate": "2024-12-31", "currencyCode": "JPY", "reportedValue": {"raw": 600}},
                    ],
                },
            ]
        }
    }

    result = normalize_yahoo_timeseries("7203.T", payload)

    assert result["currency"] == "JPY"
    assert result["basis"] == "annual"
    assert result["periods"]["2024-12-31"]["revenue"] == 1200
    assert result["periods"]["2024-12-31"]["gross_margin"] == 35.0
    assert result["periods"]["2024-12-31"]["net_margin"] == 15.0
    assert result["periods"]["2024-12-31"]["roe"] == 30.0


def test_rank_global_candidates_removes_target_and_secondary_listings():
    from lib.global_peers import rank_global_candidates

    target = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "industry": "Consumer Electronics",
        "sector": "Technology",
        "market_cap": 3_000,
    }
    candidates = [
        {"symbol": "AAPL.BA", "name": "Apple Inc.", "industry": "Consumer Electronics", "sector": "Technology"},
        {"symbol": "005930.KS", "name": "Samsung Electronics Co., Ltd.", "industry": "Consumer Electronics", "sector": "Technology", "market_cap": 2_000, "data_coverage": 0.9},
        {"symbol": "005935.KS", "name": "Samsung Electronics Co., Ltd.", "industry": "Consumer Electronics", "sector": "Technology", "market_cap": 100, "data_coverage": 0.4, "is_secondary": True},
        {"symbol": "6758.T", "name": "Sony Group Corporation", "industry": "Consumer Electronics", "sector": "Technology", "market_cap": 1_000, "data_coverage": 0.8},
    ]

    ranked = rank_global_candidates(target, candidates, limit=8)

    assert [p["symbol"] for p in ranked] == ["005930.KS", "6758.T"]
    assert all(p["relevance_score"] > 0 for p in ranked)
    assert all(p["selection_reasons"] for p in ranked)


def test_candidate_scale_score_is_not_computed_from_mixed_raw_currencies():
    from lib.global_peers import rank_global_candidates

    target = {"symbol": "A", "name": "A", "industry": "Software", "market_cap": 1000, "currency": "USD"}
    candidates = [
        {"symbol": "B.KS", "name": "B", "industry": "Software", "market_cap": 1000, "currency": "KRW"},
        {"symbol": "C", "name": "C", "industry": "Software", "market_cap": 1000, "currency": "USD"},
    ]

    ranked = rank_global_candidates(target, candidates, limit=2)

    assert [candidate["symbol"] for candidate in ranked] == ["C", "B.KS"]
    assert "规模可比" not in ranked[1]["selection_reasons"]


def test_yahoo_provider_discovers_and_enriches_global_candidates():
    from types import SimpleNamespace

    from lib.global_peers import YahooGlobalPeerProvider

    financial_payload = {
        "timeseries": {
            "result": [{
                "meta": {"type": ["annualTotalRevenue"]},
                "annualTotalRevenue": [{
                    "asOfDate": "2024-12-31",
                    "periodType": "12M",
                    "currencyCode": "KRW",
                    "reportedValue": {"raw": 3000},
                }],
            }]
        }
    }

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeSession:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return FakeResponse(financial_payload)

    class FakeTicker:
        info = {
            "longName": "Apple Inc.",
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "marketCap": 3000,
        }

    fake_yf = SimpleNamespace(
        Ticker=lambda _symbol: FakeTicker(),
        EquityQuery=lambda op, operands: (op, operands),
        screen=lambda *_args, **_kwargs: {
            "quotes": [
                {"symbol": "005930.KS", "longName": "Samsung Electronics Co., Ltd.", "industry": "Consumer Electronics", "sector": "Technology", "marketCap": 2000, "currency": "KRW", "financialCurrency": "KRW"},
                {"symbol": "6758.T", "longName": "Sony Group Corporation", "industry": "Consumer Electronics", "sector": "Technology", "marketCap": 1000, "currency": "JPY", "financialCurrency": "JPY"},
            ]
        },
    )
    session = FakeSession()
    provider = YahooGlobalPeerProvider(session=session, yf_module=fake_yf)

    discovered = provider.discover("AAPL", limit=8)
    enriched = provider.financials("005930.KS")

    assert [p["symbol"] for p in discovered] == ["005930.KS", "6758.T"]
    assert discovered[0]["market"] == "KR"
    assert enriched["periods"]["2024-12-31"]["revenue"] == 3000
    assert session.calls[0][0].startswith("https://query2.finance.yahoo.com/")
    assert session.calls[0][1]["timeout"] <= 15


def test_build_global_comparison_isolates_failures_and_builds_benchmarks():
    from lib.global_peers import build_global_peer_comparison

    def annual(symbol, gross_margin, net_margin):
        return {
            "symbol": symbol,
            "currency": "USD",
            "basis": "annual",
            "source": "fixture",
            "periods": {
                "2024-12-31": {
                    "revenue": 100,
                    "gross_margin": gross_margin,
                    "net_margin": net_margin,
                    "roe": 10,
                }
            },
        }

    class FakeProvider:
        def profile(self, symbol):
            return {"symbol": symbol, "name": "Apple Inc.", "industry": "Consumer Electronics"}

        def discover(self, _symbol, limit=30):
            return [
                {"symbol": "005930.KS", "name": "Samsung Electronics", "relevance_score": 90},
                {"symbol": "6758.T", "name": "Sony Group", "relevance_score": 80},
                {"symbol": "BAD.L", "name": "Unavailable PLC", "relevance_score": 70},
            ][:limit]

        def financials(self, symbol):
            if symbol == "BAD.L":
                raise TimeoutError("source timed out")
            return {
                "AAPL": annual(symbol, 45, 20),
                "005930.KS": annual(symbol, 35, 12),
                "6758.T": annual(symbol, 25, -2),
            }[symbol]

    result = build_global_peer_comparison("AAPL", provider=FakeProvider(), limit=8)

    assert result["peer_count"] == 2
    assert result["failed_symbols"] == ["BAD.L"]
    assert result["benchmarks"]["gross_margin"]["2024"]["median"] == 30.0
    assert result["benchmarks"]["net_margin"]["2024"]["min"] == -2.0
    assert result["target_percentile"] == {}
    assert result["conclusion_status"] == "insufficient_peers"


def test_build_global_comparison_backfills_after_candidate_failure():
    from lib.global_peers import build_global_peer_comparison

    class FakeProvider:
        def profile(self, symbol):
            return {"symbol": symbol, "name": "Target", "industry": "Hardware"}

        def discover(self, _symbol, limit=30):
            candidates = [
                {"symbol": "P1", "name": "Peer One"},
                {"symbol": "BAD", "name": "Broken Peer"},
                {"symbol": "P2", "name": "Peer Two"},
                {"symbol": "P3", "name": "Peer Three"},
            ]
            return candidates[:limit]

        def financials(self, symbol):
            if symbol == "BAD":
                raise TimeoutError("source timed out")
            return {
                "symbol": symbol,
                "currency": "USD",
                "basis": "annual",
                "periods": {"2024-12-31": {"revenue": 100, "gross_margin": 30}},
            }

    result = build_global_peer_comparison("TARGET", provider=FakeProvider(), limit=3)

    assert [peer["symbol"] for peer in result["peers"]] == ["P1", "P2", "P3"]
    assert result["failed_symbols"] == ["BAD"]


def test_fetch_peers_attaches_global_comparison_without_breaking_local_data(monkeypatch):
    import fetch_peers

    expected = {"peer_count": 4, "peers": [{"symbol": "6758.T"}]}
    monkeypatch.setattr(
        fetch_peers,
        "fetch_global_peer_comparison",
        lambda *_args, **_kwargs: expected,
        raising=False,
    )
    local = {"industry": "消费电子", "peer_table": [{"name": "目标公司", "is_self": True}]}

    result = fetch_peers._attach_global_peers(
        local,
        parse_ticker("600519.SH"),
        {"name": "贵州茅台", "industry": "消费电子"},
    )

    assert result["peer_table"] == local["peer_table"]
    assert result["global_peer_comparison"] == expected


def test_fetch_peers_global_failure_is_a_visible_nonfatal_gap(monkeypatch):
    import fetch_peers

    def fail(*_args, **_kwargs):
        raise TimeoutError("global source timeout")

    monkeypatch.setattr(fetch_peers, "fetch_global_peer_comparison", fail, raising=False)

    result = fetch_peers._attach_global_peers(
        {"industry": "半导体"},
        parse_ticker("600519.SH"),
        {"name": "目标公司", "industry": "半导体"},
    )

    assert result["global_peer_comparison"]["conclusion_status"] == "unavailable"
    assert "TimeoutError" in result["global_peer_comparison"]["error"]


def test_global_target_uses_full_yahoo_symbol_for_basic_and_kline(monkeypatch):
    from types import SimpleNamespace

    from lib import data_sources

    seen = []

    class FakeTicker:
        info = {"longName": "Toyota Motor Corporation", "industry": "Auto Manufacturers"}

    monkeypatch.setattr(
        data_sources,
        "yf",
        SimpleNamespace(Ticker=lambda symbol: seen.append(symbol) or FakeTicker()),
    )
    monkeypatch.setattr(data_sources, "_retry", lambda fn, **_kwargs: fn())
    monkeypatch.setattr(
        data_sources,
        "_kline_us_chain",
        lambda ti: seen.append(ti.full) or [{"Close": 1}],
    )

    ti = parse_ticker("7203.T")
    basic = data_sources._fetch_basic_us(ti)
    kline = data_sources._fetch_kline_impl(ti, "daily", "20240101", "qfq")

    assert basic["name"] == "Toyota Motor Corporation"
    assert kline == [{"Close": 1}]
    assert seen == ["7203.T", "7203.T"]


def test_global_target_dispatches_to_yahoo_financials(monkeypatch):
    import fetch_financials

    seen = []
    monkeypatch.setattr(
        fetch_financials,
        "_fetch_us",
        lambda ti: seen.append(ti.full) or {"currency": ti.currency},
    )

    result = fetch_financials.main("005930.KS")

    assert seen == ["005930.KS"]
    assert result["data"]["currency"] == "KRW"


def test_apply_yearly_fx_preserves_raw_values_and_adds_base_currency_values():
    from lib.global_peers import apply_yearly_fx

    financials = {
        "currency": "JPY",
        "periods": {
            "2023-03-31": {"revenue": 1000, "net_income": -50, "gross_margin": 20},
            "2024-03-31": {"revenue": 1200, "net_income": 100, "gross_margin": 25},
        },
    }

    normalized = apply_yearly_fx(financials, {"2023": 0.007, "2024": 0.0068}, "USD")

    assert normalized["currency"] == "JPY"
    assert normalized["base_currency"] == "USD"
    assert normalized["periods"]["2023-03-31"]["revenue"] == 1000
    assert normalized["periods"]["2023-03-31"]["revenue_base"] == 7.0
    assert normalized["periods"]["2023-03-31"]["net_income_base"] == -0.35
    assert normalized["periods"]["2024-03-31"]["gross_margin"] == 25


def test_yahoo_fx_provider_returns_yearly_average_rates():
    from lib.global_peers import YahooFxProvider

    payload = {
        "chart": {
            "result": [{
                "timestamp": [1672531200, 1688169600, 1704067200],
                "indicators": {"quote": [{"close": [0.007, 0.0068, 0.0066]}]},
            }],
            "error": None,
        }
    }

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    class FakeSession:
        def get(self, url, **kwargs):
            assert url.startswith("https://query1.finance.yahoo.com/")
            assert kwargs["timeout"] <= 15
            return FakeResponse()

    rates = YahooFxProvider(session=FakeSession()).rates("JPY", "USD", years=3)

    assert rates["2023"] == 0.0069
    assert rates["2024"] == 0.0066


def test_global_peer_renderer_outputs_scatter_table_and_escapes_external_text():
    from lib.report.global_peers import render_global_peer_comparison

    comparison = {
        "peer_count": 3,
        "conclusion_status": "ready",
        "base_currency": "USD",
        "target": {
            "name": "Target <script>alert(1)</script>",
            "symbol": "TARGET",
            "market": "A",
            "financials": {
                "periods": {"2024-12-31": {"revenue_base": 90, "gross_margin": 40, "net_margin": 20, "roe": 18}}
            },
        },
        "peers": [
            {"name": "Samsung Electronics", "symbol": "005930.KS", "market": "KR", "financials": {"periods": {"2024-12-31": {"revenue_base": 220, "gross_margin": 36, "net_margin": 14, "roe": 12}}}},
            {"name": "Sony Group", "symbol": "6758.T", "market": "JP", "financials": {"periods": {"2024-03-31": {"revenue_base": 85, "gross_margin": 28, "net_margin": 8, "roe": 10}}}},
            {"name": "Peer Three", "symbol": "PEER", "market": "U", "financials": {"periods": {"2024-12-31": {"revenue_base": 40, "gross_margin": 32, "net_margin": -2, "roe": -1}}}},
        ],
        "benchmarks": {"gross_margin": {"2024": {"median": 32, "p25": 28, "p75": 36, "n": 3}}},
        "target_percentile": {"gross_margin": 100},
    }

    html = render_global_peer_comparison(comparison)

    assert "全球同行业绩对比" in html
    assert "005930.KS" in html and "6758.T" in html
    assert "同行中位数" in html
    assert "<svg" in html
    assert "<script>alert(1)</script>" not in html
    assert "Target &lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "@media(max-width:640px)" in html
    assert "global-peer-summary" in html
    assert "global-peer-meta" in html


def test_existing_peer_visualization_includes_global_section():
    from lib.report.dim_viz import _viz_peers

    html = _viz_peers({
        "peer_table": [],
        "peer_comparison": [],
        "global_peer_comparison": {
            "peer_count": 0,
            "conclusion_status": "insufficient_peers",
            "target": {"name": "Target", "symbol": "TARGET", "financials": {"periods": {}}},
            "peers": [],
            "benchmarks": {},
            "target_percentile": {},
        },
    })

    assert "全球同行业绩对比" in html


def test_pipeline_peer_renderer_accepts_global_only_data():
    from lib.pipeline.renderer.base import RenderContext
    from lib.pipeline.renderer.peers import PeersRenderer

    context = RenderContext(
        ticker="TARGET",
        name="Target",
        data={
            "peer_table": [],
            "peer_comparison": [],
            "global_peer_comparison": {
                "peer_count": 0,
                "conclusion_status": "insufficient_peers",
                "target": {"name": "Target", "symbol": "TARGET", "financials": {"periods": {}}},
                "peers": [],
                "benchmarks": {},
                "target_percentile": {},
            },
        },
    )

    html = PeersRenderer().render_full(context)

    assert "全球同行业绩对比" in html


def test_global_peers_feed_comparable_company_analysis():
    from lib.global_peers import global_peers_to_comps

    comparison = {
        "peers": [{
            "name": "Samsung Electronics",
            "symbol": "005930.KS",
            "pe": 18.5,
            "pb": 1.7,
            "financials": {
                "periods": {
                    "2023-12-31": {"revenue_base": 190, "net_margin": 6, "roe": 5},
                    "2024-12-31": {"revenue_base": 220, "net_margin": 14, "roe": 12},
                }
            },
        }]
    }

    peers = global_peers_to_comps(comparison)

    assert peers == [{
        "name": "Samsung Electronics",
        "ticker": "005930.KS",
        "pe": 18.5,
        "pb": 1.7,
        "ps": None,
        "roe": 12,
        "net_margin": 14,
        "revenue_growth": 15.79,
        "market_cap_yi": 0,
    }]


def test_dimension_scoring_recognizes_global_peers_when_local_pool_is_empty():
    from lib.pipeline.score_fns import score_dimensions

    raw = {
        "ticker": "TARGET",
        "dimensions": {
            "4_peers": {
                "data": {
                    "peer_table": [],
                    "global_peer_comparison": {"peer_count": 5, "conclusion_status": "ready"},
                }
            }
        }
    }

    score = score_dimensions(raw)["dimensions"]["4_peers"]

    assert score["score"] == 7
    assert score["label"] == "全球同行 5 家对比"
