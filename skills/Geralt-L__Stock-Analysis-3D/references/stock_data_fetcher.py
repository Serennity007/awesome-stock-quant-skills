#!/usr/bin/env python3
"""
Stock Data Fetcher + Technical Indicator Calculator
Outputs structured JSON for Claude Code analysis.
No AI/LLM calls -- pure data + math.

Data source priority (graceful degradation):
  A-share: Tushare Pro (if TUSHARE_TOKEN set) > efinance > akshare > yfinance
  HK:      efinance > akshare > yfinance
  US:      yfinance (primary)

News search priority (via --news flag):
  Tavily (if TAVILY_API_KEY set) > SerpAPI (if SERPAPI_KEY set) > skip (use WebSearch in Claude)

Usage:
    python3 stock_data_fetcher.py --stocks "600519,TSLA,HK00700" [--days 120] [--news]

Environment variables (optional, for enhanced data):
    TUSHARE_TOKEN    - Tushare Pro token (free signup at tushare.pro)
    TAVILY_API_KEY   - Tavily API key (1000 free calls/month)
    SERPAPI_KEY       - SerpAPI key (100 free calls/month)
"""

import os
import sys
import json
import argparse
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# Data source availability detection
_AVAILABLE_SOURCES = {}

def _check_source(name):
    """Lazy-check if a data source library is importable."""
    if name not in _AVAILABLE_SOURCES:
        try:
            __import__(name)
            _AVAILABLE_SOURCES[name] = True
        except ImportError:
            _AVAILABLE_SOURCES[name] = False
    return _AVAILABLE_SOURCES[name]

def _log(msg):
    """Log to stderr so it doesn't pollute JSON stdout."""
    print(f"[INFO] {msg}", file=sys.stderr)


# ============================================================
# SECTION 1: Stock Code Parser
# ============================================================

def classify_stock(code: str) -> tuple:
    """
    Returns (market, normalized_code, display_code)
    market: 'cn_a', 'cn_hk', 'us'
    """
    code = code.strip()
    upper = code.upper()

    # 港股: HK00700 -> ('cn_hk', '00700', 'HK00700')
    if upper.startswith("HK") and upper[2:].isdigit():
        return ("cn_hk", upper[2:], upper)

    # A股: 600519 -> ('cn_a', '600519', '600519')
    if upper.isdigit() and len(upper) == 6:
        return ("cn_a", upper, upper)

    # 美股: TSLA -> ('us', 'TSLA', 'TSLA')
    if upper.isalpha() and 1 <= len(upper) <= 5:
        return ("us", upper, upper)

    # 带后缀的A股: 600519.SH -> strip
    if "." in upper:
        base, suffix = upper.rsplit(".", 1)
        if suffix in ("SH", "SZ", "SS") and base.isdigit():
            return ("cn_a", base, base)

    # 带前缀的A股: SH600519 -> strip
    if upper[:2] in ("SH", "SZ") and upper[2:].isdigit():
        return ("cn_a", upper[2:], upper[2:])

    return ("unknown", code, code)


def to_yfinance_code(code: str, market: str) -> str:
    """Convert to Yahoo Finance ticker format."""
    if market == "cn_hk":
        num = code.lstrip("0") or "0"
        return f"{num.zfill(4)}.HK"
    if market == "us":
        return code
    # A股
    if code.startswith(("600", "601", "603", "688")):
        return f"{code}.SS"
    if code.startswith(("51", "52", "56", "58")):
        return f"{code}.SS"
    return f"{code}.SZ"


# ============================================================
# SECTION 2: Data Fetchers (with graceful degradation)
# ============================================================

def _df_to_ohlcv(df, days):
    """Convert a normalized DataFrame to OHLCV list."""
    import pandas as pd
    for c in ["open", "close", "high", "low", "volume", "amount", "pct_chg"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values("date").tail(days).reset_index(drop=True)
    ohlcv = []
    for _, row in df.iterrows():
        ohlcv.append({
            "date": str(row.get("date", "")),
            "open": _safe_float(row.get("open")),
            "high": _safe_float(row.get("high")),
            "low": _safe_float(row.get("low")),
            "close": _safe_float(row.get("close")),
            "volume": _safe_float(row.get("volume")),
            "amount": _safe_float(row.get("amount")),
            "pct_chg": _safe_float(row.get("pct_chg")),
        })
    return ohlcv


# --- Tushare Pro (Priority 0, needs TUSHARE_TOKEN) ---

def _fetch_tushare_a(code: str, days: int):
    """Fetch A-share via Tushare Pro. Returns (ohlcv, source) or raises."""
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise EnvironmentError("TUSHARE_TOKEN not set")
    import tushare as ts
    pro = ts.pro_api(token)
    ts_code = f"{code}.SH" if code.startswith(("600", "601", "603", "688")) else f"{code}.SZ"
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df is None or df.empty:
        raise ValueError(f"Tushare returned no data for {code}")
    col_map = {
        "trade_date": "date", "open": "open", "close": "close",
        "high": "high", "low": "low", "vol": "volume",
        "amount": "amount", "pct_chg": "pct_chg",
    }
    df = df.rename(columns=col_map)
    df["date"] = df["date"].apply(lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}" if len(str(x)) == 8 else x)
    _log(f"[{code}] Using Tushare Pro (premium)")
    return _df_to_ohlcv(df, days), "tushare"


# --- efinance (Priority 1, free) ---

def _fetch_efinance_a(code: str, days: int):
    """Fetch A-share via efinance (EastMoney). Returns (ohlcv, source) or raises."""
    import efinance as ef
    df = ef.stock.get_quote_history(code)
    if df is None or df.empty:
        raise ValueError(f"efinance returned no data for {code}")
    col_map = {
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
        "成交额": "amount", "涨跌幅": "pct_chg",
    }
    df = df.rename(columns=col_map)
    _log(f"[{code}] Using efinance (free)")
    return _df_to_ohlcv(df, days), "efinance"


def _fetch_efinance_hk(code: str, days: int):
    """Fetch HK stock via efinance."""
    import efinance as ef
    df = ef.stock.get_quote_history(code, stock_type="hk")
    if df is None or df.empty:
        raise ValueError(f"efinance returned no data for HK{code}")
    col_map = {
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
        "成交额": "amount", "涨跌幅": "pct_chg",
    }
    df = df.rename(columns=col_map)
    _log(f"[HK{code}] Using efinance (free)")
    return _df_to_ohlcv(df, days), "efinance"


# --- akshare (Priority 2, free) ---

def _fetch_akshare_a(code: str, days: int):
    """Fetch A-share via akshare."""
    import akshare as ak
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")
    except Exception:
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=start_date, end_date=end_date, adjust="")
    if df is None or df.empty:
        raise ValueError(f"akshare returned no data for {code}")
    col_map = {
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
        "成交额": "amount", "涨跌幅": "pct_chg",
    }
    df = df.rename(columns=col_map)
    _log(f"[{code}] Using akshare (free)")
    return _df_to_ohlcv(df, days), "akshare"


def _fetch_akshare_hk(code: str, days: int):
    """Fetch HK stock via akshare."""
    import akshare as ak
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
    try:
        df = ak.stock_hk_hist(symbol=code, period="daily",
                              start_date=start_date, end_date=end_date, adjust="qfq")
    except Exception:
        df = ak.stock_hk_hist(symbol=code, period="daily",
                              start_date=start_date, end_date=end_date, adjust="")
    if df is None or df.empty:
        raise ValueError(f"akshare returned no data for HK{code}")
    col_map = {
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
        "成交额": "amount", "涨跌幅": "pct_chg",
    }
    df = df.rename(columns=col_map)
    _log(f"[HK{code}] Using akshare (free)")
    return _df_to_ohlcv(df, days), "akshare"


# --- yfinance (Priority 3, free, fallback for all markets) ---

def _fetch_yfinance(code: str, market: str, days: int):
    """Fetch any stock via yfinance (universal fallback)."""
    import yfinance as yf
    yf_code = to_yfinance_code(code, market)
    ticker = yf.Ticker(yf_code)
    hist = ticker.history(period=f"{days}d")
    if hist is None or hist.empty:
        raise ValueError(f"yfinance returned no data for {yf_code}")
    ohlcv = []
    for idx, row in hist.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        ohlcv.append({
            "date": date_str,
            "open": _safe_float(row.get("Open")),
            "high": _safe_float(row.get("High")),
            "low": _safe_float(row.get("Low")),
            "close": _safe_float(row.get("Close")),
            "volume": _safe_float(row.get("Volume")),
            "amount": None, "pct_chg": None,
        })
    for i in range(1, len(ohlcv)):
        prev = ohlcv[i - 1]["close"]
        if prev and prev > 0:
            ohlcv[i]["pct_chg"] = round((ohlcv[i]["close"] - prev) / prev * 100, 2)
    _log(f"[{code}] Using yfinance (free, fallback)")
    return ohlcv, "yfinance"


# --- Realtime quote fetchers ---

def _fetch_realtime_a(code: str) -> dict:
    """Fetch A-share realtime quote with fallback."""
    # Try akshare spot (most reliable for realtime)
    if _check_source("akshare"):
        try:
            import akshare as ak
            spot_df = ak.stock_zh_a_spot_em()
            row = spot_df[spot_df["代码"] == code]
            if not row.empty:
                r = row.iloc[0]
                return {
                    "name": str(r.get("名称", code)),
                    "price": _safe_float(r.get("最新价")),
                    "change_pct": _safe_float(r.get("涨跌幅")),
                    "change_amount": _safe_float(r.get("涨跌额")),
                    "volume": _safe_float(r.get("成交量")),
                    "amount": _safe_float(r.get("成交额")),
                    "amplitude": _safe_float(r.get("振幅")),
                    "turnover_rate": _safe_float(r.get("换手率")),
                    "pe_ratio": _safe_float(r.get("市盈率-动态")),
                    "pb_ratio": _safe_float(r.get("市净率")),
                    "total_mv": _safe_float(r.get("总市值")),
                    "circ_mv": _safe_float(r.get("流通市值")),
                    "high": _safe_float(r.get("最高")),
                    "low": _safe_float(r.get("最低")),
                    "open": _safe_float(r.get("今开")),
                    "pre_close": _safe_float(r.get("昨收")),
                    "volume_ratio": _safe_float(r.get("量比")),
                }
        except Exception:
            pass
    # Try efinance
    if _check_source("efinance"):
        try:
            import efinance as ef
            qt = ef.stock.get_realtime_quotes([code])
            if qt is not None and not qt.empty:
                r = qt.iloc[0]
                return {
                    "name": str(r.get("股票名称", code)),
                    "price": _safe_float(r.get("最新价")),
                    "change_pct": _safe_float(r.get("涨跌幅")),
                }
        except Exception:
            pass
    return {}


def _fetch_realtime_hk(code: str) -> dict:
    """Fetch HK realtime quote."""
    if _check_source("akshare"):
        try:
            import akshare as ak
            spot_df = ak.stock_hk_spot_em()
            matched = spot_df[spot_df["代码"] == code]
            if not matched.empty:
                r = matched.iloc[0]
                return {
                    "name": str(r.get("名称", f"HK{code}")),
                    "price": _safe_float(r.get("最新价")),
                    "change_pct": _safe_float(r.get("涨跌幅")),
                    "volume": _safe_float(r.get("成交量")),
                    "pe_ratio": _safe_float(r.get("市盈率")),
                    "pb_ratio": _safe_float(r.get("市净率")),
                    "total_mv": _safe_float(r.get("总市值")),
                }
        except Exception:
            pass
    return {}


def _fetch_realtime_us(code: str) -> dict:
    """Fetch US realtime quote via yfinance."""
    try:
        import yfinance as yf
        info = yf.Ticker(code).info
        return {
            "name": info.get("shortName") or info.get("longName") or code,
            "price": _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
            "change_pct": _safe_float(info.get("regularMarketChangePercent")),
            "volume": _safe_float(info.get("regularMarketVolume")),
            "pe_ratio": _safe_float(info.get("trailingPE")),
            "pb_ratio": _safe_float(info.get("priceToBook")),
            "total_mv": _safe_float(info.get("marketCap")),
            "high": _safe_float(info.get("dayHigh")),
            "low": _safe_float(info.get("dayLow")),
            "open": _safe_float(info.get("regularMarketOpen")),
            "pre_close": _safe_float(info.get("regularMarketPreviousClose")),
            "week_52_high": _safe_float(info.get("fiftyTwoWeekHigh")),
            "week_52_low": _safe_float(info.get("fiftyTwoWeekLow")),
            "avg_volume": _safe_float(info.get("averageVolume")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
        }
    except Exception:
        return {}


# ============================================================
# SECTION 2.4: Fundamental Data Fetchers (NEW)
# ============================================================

def _safe_pct(val) -> float:
    """Parse value that may be percent string (e.g. '15.5%') or float."""
    if val is None:
        return None
    if isinstance(val, str):
        s = val.replace("%", "").replace(",", "").strip()
        if s in ("", "--", "NA", "nan", "None"):
            return None
        try:
            return round(float(s), 2)
        except ValueError:
            return None
    return _safe_float(val)


def _empty_fundamentals(source="unknown"):
    return {
        "pe_ttm": None, "pb": None, "roe": None,
        "revenue_yoy": None, "gross_margin": None, "debt_to_asset": None,
        "source": source,
    }


def fetch_fundamentals_a(code: str, realtime: dict) -> dict:
    """Fetch A-share fundamentals. Try multiple sources for robustness."""
    fund = _empty_fundamentals("akshare_spot_only")
    fund["pe_ttm"] = realtime.get("pe_ratio")
    fund["pb"] = realtime.get("pb_ratio")

    # --- Fill PE/PB: try akshare individual info, then efinance ---
    if fund["pe_ttm"] is None or fund["pb"] is None:
        # Try 1: akshare individual info
        if _check_source("akshare"):
            try:
                import akshare as ak
                info_df = ak.stock_individual_info_em(symbol=code)
                if info_df is not None and not info_df.empty:
                    # Returns DataFrame with item-value pairs
                    info_dict = dict(zip(info_df["item"].astype(str), info_df["value"]))
                    if fund["pe_ttm"] is None:
                        fund["pe_ttm"] = _safe_pct(info_dict.get("市盈率(动)") or info_dict.get("市盈率") or info_dict.get("市盈率(TTM)"))
                    if fund["pb"] is None:
                        fund["pb"] = _safe_pct(info_dict.get("市净率"))
            except Exception as e:
                _log(f"[{code}] akshare individual_info failed: {e}")

        # Try 2: efinance base info
        if (fund["pe_ttm"] is None or fund["pb"] is None) and _check_source("efinance"):
            try:
                import efinance as ef
                base = ef.stock.get_base_info(code)
                if base is not None:
                    if hasattr(base, "to_dict"):
                        bd = base.to_dict()
                    else:
                        bd = dict(base)
                    if fund["pe_ttm"] is None:
                        fund["pe_ttm"] = _safe_pct(bd.get("市盈率(动)") or bd.get("市盈率"))
                    if fund["pb"] is None:
                        fund["pb"] = _safe_pct(bd.get("市净率"))
            except Exception as e:
                _log(f"[{code}] efinance base_info failed: {e}")

        # Try 3: yfinance fallback (most reliable but slowest)
        if (fund["pe_ttm"] is None or fund["pb"] is None) and _check_source("yfinance"):
            try:
                import yfinance as yf
                yf_code = to_yfinance_code(code, "cn_a")
                info = yf.Ticker(yf_code).info
                if fund["pe_ttm"] is None:
                    fund["pe_ttm"] = _safe_float(info.get("trailingPE"))
                if fund["pb"] is None:
                    fund["pb"] = _safe_float(info.get("priceToBook"))
            except Exception as e:
                _log(f"[{code}] yfinance fundamentals fallback failed: {e}")

    if not _check_source("akshare"):
        return fund

    import akshare as ak

    # Try strategy 1: 同花顺财务摘要 (按报告期)
    try:
        df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
        if df is not None and not df.empty:
            latest = df.iloc[0]
            cols = list(df.columns)
            # ROE
            for k in ("净资产收益率", "加权净资产收益率", "净资产收益率(摊薄)", "净资产收益率(%)"):
                if k in cols:
                    fund["roe"] = _safe_pct(latest.get(k))
                    if fund["roe"] is not None:
                        break
            # 毛利率
            for k in ("销售毛利率", "毛利率", "销售毛利率(%)"):
                if k in cols:
                    fund["gross_margin"] = _safe_pct(latest.get(k))
                    if fund["gross_margin"] is not None:
                        break
            # 营收增速
            for k in ("营业总收入同比增长率", "营业收入同比增长率", "营业总收入同比", "营业收入同比"):
                if k in cols:
                    fund["revenue_yoy"] = _safe_pct(latest.get(k))
                    if fund["revenue_yoy"] is not None:
                        break
            # 资产负债率
            for k in ("资产负债率", "资产负债率(%)"):
                if k in cols:
                    fund["debt_to_asset"] = _safe_pct(latest.get(k))
                    if fund["debt_to_asset"] is not None:
                        break
            fund["source"] = "akshare_ths"
            _log(f"[{code}] Fundamentals via akshare_ths (cols={len(cols)})")
    except Exception as e:
        _log(f"[{code}] akshare_ths failed: {e}")

    # Strategy 2: compute revenue_yoy from two periods if still missing
    if fund["revenue_yoy"] is None:
        try:
            df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
            if df is not None and len(df) >= 5:
                cols = list(df.columns)
                for rev_key in ("营业总收入", "营业收入"):
                    if rev_key in cols:
                        cur = _safe_pct(df.iloc[0].get(rev_key))
                        prev = _safe_pct(df.iloc[4].get(rev_key))  # 同期 (4 quarters ago)
                        if cur and prev and prev > 0:
                            fund["revenue_yoy"] = round((cur - prev) / prev * 100, 2)
                            break
        except Exception:
            pass

    return fund


def fetch_fundamentals_hk(code: str, realtime: dict) -> dict:
    """Fetch HK stock fundamentals."""
    fund = _empty_fundamentals("akshare_spot_only")
    fund["pe_ttm"] = realtime.get("pe_ratio")
    fund["pb"] = realtime.get("pb_ratio")

    # Try akshare HK financial indicator
    if _check_source("akshare"):
        try:
            import akshare as ak
            df = ak.stock_financial_hk_analysis_indicator_em(symbol=code, indicator="年度")
            if df is not None and not df.empty:
                latest = df.iloc[0]
                cols = list(df.columns)
                for k in ("净资产收益率(摊薄)", "净资产收益率", "ROE", "净资产收益率(%)"):
                    if k in cols:
                        v = _safe_pct(latest.get(k))
                        if v is not None:
                            fund["roe"] = v
                            break
                for k in ("销售毛利率", "毛利率", "毛利率%", "毛利率(%)"):
                    if k in cols:
                        v = _safe_pct(latest.get(k))
                        if v is not None:
                            fund["gross_margin"] = v
                            break
                for k in ("资产负债率", "资产负债率%", "资产负债率(%)"):
                    if k in cols:
                        v = _safe_pct(latest.get(k))
                        if v is not None:
                            fund["debt_to_asset"] = v
                            break
                for k in ("营业总收入同比增长率", "营业收入同比增长率", "营收同比"):
                    if k in cols:
                        v = _safe_pct(latest.get(k))
                        if v is not None:
                            fund["revenue_yoy"] = v
                            break
                fund["source"] = "akshare_hk"
                _log(f"[HK{code}] Fundamentals via akshare_hk (cols={len(cols)})")
        except Exception as e:
            _log(f"[HK{code}] akshare_hk fundamentals failed: {e}")

    # yfinance fallback for any missing fields
    missing = [k for k in ("pe_ttm", "pb", "roe", "revenue_yoy", "gross_margin", "debt_to_asset") if fund[k] is None]
    if missing and _check_source("yfinance"):
        try:
            import yfinance as yf
            yf_code = to_yfinance_code(code, "cn_hk")
            info = yf.Ticker(yf_code).info
            if fund["pe_ttm"] is None:
                fund["pe_ttm"] = _safe_float(info.get("trailingPE"))
            if fund["pb"] is None:
                fund["pb"] = _safe_float(info.get("priceToBook"))
            if fund["roe"] is None:
                roe = info.get("returnOnEquity")
                if roe is not None:
                    fund["roe"] = round(float(roe) * 100, 2)
            if fund["revenue_yoy"] is None:
                rg = info.get("revenueGrowth")
                if rg is not None:
                    fund["revenue_yoy"] = round(float(rg) * 100, 2)
            if fund["gross_margin"] is None:
                gm = info.get("grossMargins")
                if gm is not None:
                    fund["gross_margin"] = round(float(gm) * 100, 2)
            if fund["debt_to_asset"] is None:
                de = info.get("debtToEquity")
                if de is not None:
                    ratio = float(de) / 100.0 if float(de) > 5 else float(de)
                    if ratio > 0:
                        fund["debt_to_asset"] = round(ratio / (1 + ratio) * 100, 2)
            fund["source"] = fund["source"] + "+yfinance" if fund["source"] != "akshare_spot_only" else "yfinance"
            _log(f"[HK{code}] Fundamentals filled via yfinance fallback")
        except Exception as e:
            _log(f"[HK{code}] yfinance HK fallback failed: {e}")

    return fund


def fetch_fundamentals_us(code: str) -> dict:
    """Fetch US stock fundamentals via yfinance."""
    fund = _empty_fundamentals("yfinance")
    try:
        import yfinance as yf
        info = yf.Ticker(code).info
        fund["pe_ttm"] = _safe_float(info.get("trailingPE"))
        fund["pb"] = _safe_float(info.get("priceToBook"))
        roe = info.get("returnOnEquity")
        if roe is not None:
            fund["roe"] = round(float(roe) * 100, 2)
        rev_growth = info.get("revenueGrowth")
        if rev_growth is not None:
            fund["revenue_yoy"] = round(float(rev_growth) * 100, 2)
        gm = info.get("grossMargins")
        if gm is not None:
            fund["gross_margin"] = round(float(gm) * 100, 2)
        de = info.get("debtToEquity")
        # yfinance debtToEquity is D/E ratio (often as percent e.g. 150 meaning 1.5)
        # Convert to debt/asset: D/A = D/(D+E)
        if de is not None:
            ratio = float(de) / 100.0 if float(de) > 5 else float(de)
            if ratio > 0:
                fund["debt_to_asset"] = round(ratio / (1 + ratio) * 100, 2)
        _log(f"[{code}] Fundamentals via yfinance")
    except Exception as e:
        _log(f"[{code}] yfinance fundamentals failed: {e}")
    return fund


# ============================================================
# SECTION 2.5: Priority router (now also fetches fundamentals)
# ============================================================

def fetch_cn_a(code: str, days: int) -> dict:
    """Fetch A-share with priority: Tushare > efinance > akshare > yfinance."""
    ohlcv = None
    source = "unknown"
    errors = []

    # Priority 0: Tushare Pro (if token configured)
    if os.environ.get("TUSHARE_TOKEN") and _check_source("tushare"):
        try:
            ohlcv, source = _fetch_tushare_a(code, days)
        except Exception as e:
            errors.append(f"tushare: {e}")

    # Priority 1: efinance
    if ohlcv is None and _check_source("efinance"):
        try:
            ohlcv, source = _fetch_efinance_a(code, days)
        except Exception as e:
            errors.append(f"efinance: {e}")

    # Priority 2: akshare
    if ohlcv is None and _check_source("akshare"):
        try:
            ohlcv, source = _fetch_akshare_a(code, days)
        except Exception as e:
            errors.append(f"akshare: {e}")

    # Priority 3: yfinance (universal fallback)
    if ohlcv is None and _check_source("yfinance"):
        try:
            ohlcv, source = _fetch_yfinance(code, "cn_a", days)
        except Exception as e:
            errors.append(f"yfinance: {e}")

    if ohlcv is None:
        raise ValueError(f"All data sources failed for A-share {code}: {'; '.join(errors)}")

    realtime = _fetch_realtime_a(code)
    name = realtime.get("name", code)
    fundamentals = fetch_fundamentals_a(code, realtime)
    return {"ohlcv": ohlcv, "realtime": realtime, "fundamentals": fundamentals, "name": name, "source": source}


def fetch_hk(code: str, days: int) -> dict:
    """Fetch HK stock with priority: efinance > akshare > yfinance."""
    ohlcv = None
    source = "unknown"
    errors = []

    if _check_source("efinance"):
        try:
            ohlcv, source = _fetch_efinance_hk(code, days)
        except Exception as e:
            errors.append(f"efinance: {e}")

    if ohlcv is None and _check_source("akshare"):
        try:
            ohlcv, source = _fetch_akshare_hk(code, days)
        except Exception as e:
            errors.append(f"akshare: {e}")

    if ohlcv is None and _check_source("yfinance"):
        try:
            ohlcv, source = _fetch_yfinance(code, "cn_hk", days)
        except Exception as e:
            errors.append(f"yfinance: {e}")

    if ohlcv is None:
        raise ValueError(f"All data sources failed for HK{code}: {'; '.join(errors)}")

    realtime = _fetch_realtime_hk(code)
    name = realtime.get("name", f"HK{code}")
    fundamentals = fetch_fundamentals_hk(code, realtime)
    return {"ohlcv": ohlcv, "realtime": realtime, "fundamentals": fundamentals, "name": name, "source": source}


def fetch_us(code: str, days: int) -> dict:
    """Fetch US stock via yfinance (primary source for US)."""
    ohlcv, source = _fetch_yfinance(code, "us", days)
    realtime = _fetch_realtime_us(code)
    if not realtime and ohlcv:
        last = ohlcv[-1]
        realtime = {"name": code, "price": last["close"], "change_pct": last.get("pct_chg")}
    name = realtime.get("name", code)
    fundamentals = fetch_fundamentals_us(code)
    return {"ohlcv": ohlcv, "realtime": realtime, "fundamentals": fundamentals, "name": name, "source": source}


# ============================================================
# SECTION 2.6: News Search (optional, with graceful degradation)
# ============================================================

def search_news(stock_name: str, code: str, max_results: int = 5) -> list:
    """
    Search news with priority: Tavily > SerpAPI > empty (let Claude WebSearch).
    Returns list of {"title": ..., "content": ..., "url": ..., "date": ...}
    """
    # Priority 0: Tavily
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            query = f"{stock_name} {code} stock news"
            resp = client.search(query=query, max_results=max_results, search_depth="basic")
            results = []
            for r in resp.get("results", [])[:max_results]:
                results.append({
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:200],
                    "url": r.get("url", ""),
                    "source": "tavily",
                })
            if results:
                _log(f"[{code}] News via Tavily ({len(results)} results)")
                return results
        except Exception as e:
            _log(f"[{code}] Tavily failed: {e}")

    # Priority 1: SerpAPI
    serpapi_key = os.environ.get("SERPAPI_KEY")
    if serpapi_key:
        try:
            from serpapi import GoogleSearch
            params = {
                "q": f"{stock_name} stock news",
                "api_key": serpapi_key,
                "num": max_results,
            }
            search = GoogleSearch(params)
            data = search.get_dict()
            results = []
            for r in data.get("organic_results", [])[:max_results]:
                results.append({
                    "title": r.get("title", ""),
                    "content": r.get("snippet", "")[:200],
                    "url": r.get("link", ""),
                    "source": "serpapi",
                })
            if results:
                _log(f"[{code}] News via SerpAPI ({len(results)} results)")
                return results
        except Exception as e:
            _log(f"[{code}] SerpAPI failed: {e}")

    # No API keys configured — return empty, let Claude use WebSearch
    _log(f"[{code}] No news API configured, skipping (Claude will use WebSearch)")
    return []


# ============================================================
# SECTION 3: Technical Indicator Calculations
# ============================================================

def _safe_float(val) -> float:
    """Safely convert to float."""
    if val is None:
        return None
    try:
        import math
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except (ValueError, TypeError):
        return None


def calc_ema(data: list, period: int) -> list:
    """Calculate Exponential Moving Average."""
    if not data or len(data) < period:
        return [None] * len(data)
    result = [None] * (period - 1)
    multiplier = 2.0 / (period + 1)
    # First EMA = SMA of first 'period' values
    sma = sum(data[:period]) / period
    result.append(sma)
    for i in range(period, len(data)):
        ema = (data[i] - result[-1]) * multiplier + result[-1]
        result.append(ema)
    return result


def calc_ma(closes: list, periods: list) -> dict:
    """Calculate Simple Moving Averages."""
    result = {}
    for p in periods:
        key = f"MA{p}"
        if len(closes) >= p:
            ma_val = sum(closes[-p:]) / p
            result[key] = round(ma_val, 4)
        else:
            result[key] = None

    # MA alignment status
    ma5 = result.get("MA5")
    ma10 = result.get("MA10")
    ma20 = result.get("MA20")

    if all(v is not None for v in [ma5, ma10, ma20]):
        if ma5 > ma10 > ma20:
            result["alignment"] = "bullish"
            spread = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0
            result["alignment_detail"] = "strong_bullish" if spread > 5 else "bullish"
        elif ma5 < ma10 < ma20:
            result["alignment"] = "bearish"
            spread = (ma20 - ma5) / ma20 * 100 if ma20 > 0 else 0
            result["alignment_detail"] = "strong_bearish" if spread > 5 else "bearish"
        elif ma5 > ma10 and ma10 <= ma20:
            result["alignment"] = "weak_bullish"
            result["alignment_detail"] = "weak_bullish"
        elif ma5 < ma10 and ma10 >= ma20:
            result["alignment"] = "weak_bearish"
            result["alignment_detail"] = "weak_bearish"
        else:
            result["alignment"] = "consolidation"
            result["alignment_detail"] = "consolidation"
    else:
        result["alignment"] = "insufficient_data"
        result["alignment_detail"] = "insufficient_data"

    return result


def calc_macd(closes: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calculate MACD: DIF, DEA, Histogram, and cross signals."""
    if len(closes) < slow + signal:
        return {"DIF": None, "DEA": None, "hist": None, "signal": "insufficient_data"}

    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)

    dif_list = []
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif_list.append(ema_fast[i] - ema_slow[i])
        else:
            dif_list.append(None)

    # DEA = EMA of DIF
    valid_dif = [d for d in dif_list if d is not None]
    if len(valid_dif) < signal:
        return {"DIF": None, "DEA": None, "hist": None, "signal": "insufficient_data"}

    dea_list = calc_ema(valid_dif, signal)

    # Current values
    curr_dif = valid_dif[-1] if valid_dif else None
    curr_dea = dea_list[-1] if dea_list else None
    prev_dif = valid_dif[-2] if len(valid_dif) >= 2 else None
    prev_dea = dea_list[-2] if len(dea_list) >= 2 else None

    hist = round((curr_dif - curr_dea) * 2, 4) if curr_dif is not None and curr_dea is not None else None

    # Cross signal detection
    macd_signal = "neutral"
    if all(v is not None for v in [curr_dif, curr_dea, prev_dif, prev_dea]):
        curr_diff = curr_dif - curr_dea
        prev_diff = prev_dif - prev_dea

        if prev_diff <= 0 and curr_diff > 0:
            macd_signal = "golden_cross_above_zero" if curr_dif > 0 else "golden_cross"
        elif prev_diff >= 0 and curr_diff < 0:
            macd_signal = "death_cross"
        elif curr_dif > 0 and curr_dea > 0:
            macd_signal = "bullish"
        elif curr_dif < 0 and curr_dea < 0:
            macd_signal = "bearish"

        # Zero axis cross
        if prev_dif is not None and curr_dif is not None:
            if prev_dif < 0 and curr_dif >= 0:
                macd_signal = "crossing_above_zero"
            elif prev_dif > 0 and curr_dif <= 0:
                macd_signal = "crossing_below_zero"

    return {
        "DIF": round(curr_dif, 4) if curr_dif is not None else None,
        "DEA": round(curr_dea, 4) if curr_dea is not None else None,
        "hist": hist,
        "signal": macd_signal,
    }


def calc_rsi(closes: list, periods: list) -> dict:
    """Calculate RSI using Wilder's method."""
    result = {}
    for period in periods:
        key = f"RSI{period}"
        if len(closes) < period + 1:
            result[key] = None
            continue

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(0, d) for d in deltas]
        losses = [max(0, -d) for d in deltas]

        # First average
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Smoothed averages (Wilder's method)
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        result[key] = round(rsi, 2)

    # RSI zone
    rsi12 = result.get("RSI12")
    if rsi12 is not None:
        if rsi12 >= 80:
            result["zone"] = "overbought"
        elif rsi12 >= 60:
            result["zone"] = "strong"
        elif rsi12 >= 40:
            result["zone"] = "neutral"
        elif rsi12 >= 20:
            result["zone"] = "weak"
        else:
            result["zone"] = "oversold"
    else:
        result["zone"] = "unknown"

    return result


def calc_volume_analysis(volumes: list, closes: list) -> dict:
    """Analyze volume patterns."""
    if len(volumes) < 6 or len(closes) < 2:
        return {"vol_ratio": None, "trend": "insufficient_data"}

    # 5-day average volume (excluding today)
    avg_vol_5 = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else volumes[-1]
    curr_vol = volumes[-1]

    vol_ratio = round(curr_vol / avg_vol_5, 2) if avg_vol_5 > 0 else None

    # Price change direction
    price_up = closes[-1] >= closes[-2]

    # Volume trend classification
    if vol_ratio is None:
        trend = "unknown"
    elif vol_ratio >= 1.5 and price_up:
        trend = "heavy_volume_up"
    elif vol_ratio >= 1.5 and not price_up:
        trend = "heavy_volume_down"
    elif vol_ratio <= 0.7 and not price_up:
        trend = "shrink_pullback"
    elif vol_ratio <= 0.7 and price_up:
        trend = "shrink_up"
    else:
        trend = "normal"

    return {"vol_ratio": vol_ratio, "trend": trend}


def calc_bias(closes: list, ma_data: dict) -> dict:
    """Calculate bias ratio (乖离率)."""
    if not closes:
        return {}
    curr = closes[-1]
    result = {}
    for key in ["MA5", "MA10", "MA20"]:
        ma_val = ma_data.get(key)
        if ma_val and ma_val > 0:
            bias = round((curr - ma_val) / ma_val * 100, 2)
            result[f"bias_{key.lower()}"] = bias
    return result


def calc_support(closes: list, ma_data: dict) -> dict:
    """Check if price is supported by MA lines."""
    if not closes:
        return {"support_ma5": False, "support_ma10": False}
    curr = closes[-1]
    ma5 = ma_data.get("MA5")
    ma10 = ma_data.get("MA10")

    support_ma5 = False
    support_ma10 = False

    if ma5 and curr > 0:
        # Price within 1% of MA5
        support_ma5 = abs(curr - ma5) / curr * 100 <= 1.0
    if ma10 and curr > 0:
        support_ma10 = abs(curr - ma10) / curr * 100 <= 1.5

    return {"support_ma5": support_ma5, "support_ma10": support_ma10}


# ============================================================
# SECTION 4: Composite Trend Scoring (100 points)
# ============================================================

def calc_trend_score(ma_data: dict, macd_data: dict, rsi_data: dict,
                     vol_data: dict, bias_data: dict, support_data: dict) -> dict:
    """
    Composite scoring system (100 points total):
    - Trend/MA alignment: 30 pts
    - Bias (乖离率): 20 pts
    - Volume: 15 pts
    - MACD: 15 pts
    - RSI: 10 pts
    - Support: 10 pts
    """
    breakdown = {}

    # 1. Trend score (30 pts)
    alignment = ma_data.get("alignment_detail", "consolidation")
    trend_scores = {
        "strong_bullish": 30, "bullish": 26, "weak_bullish": 18,
        "consolidation": 12, "weak_bearish": 8, "bearish": 4,
        "strong_bearish": 0, "insufficient_data": 12,
    }
    breakdown["trend"] = trend_scores.get(alignment, 12)

    # 2. Bias score (20 pts) - prefer slightly below MA5
    bias_ma5 = bias_data.get("bias_ma5", 0)
    if bias_ma5 is None:
        breakdown["bias"] = 10
    elif -3 <= bias_ma5 < 0:
        breakdown["bias"] = 20  # Slightly below MA5 = ideal dip
    elif 0 <= bias_ma5 < 2:
        breakdown["bias"] = 18  # Close to MA5
    elif 2 <= bias_ma5 < 5:
        breakdown["bias"] = 14  # Slightly above
    elif bias_ma5 >= 5:
        breakdown["bias"] = 4   # Too far above, don't chase
    elif -5 <= bias_ma5 < -3:
        breakdown["bias"] = 14  # Pulling back more
    else:
        breakdown["bias"] = 6   # Far below

    # 3. Volume score (15 pts)
    vol_trend = vol_data.get("trend", "normal")
    vol_scores = {
        "shrink_pullback": 15, "heavy_volume_up": 12, "normal": 10,
        "shrink_up": 6, "heavy_volume_down": 0, "insufficient_data": 8,
        "unknown": 8,
    }
    breakdown["volume"] = vol_scores.get(vol_trend, 8)

    # 4. MACD score (15 pts)
    macd_signal = macd_data.get("signal", "neutral")
    macd_scores = {
        "golden_cross_above_zero": 15, "crossing_above_zero": 13,
        "golden_cross": 12, "bullish": 10, "neutral": 7,
        "bearish": 3, "death_cross": 0, "crossing_below_zero": 1,
        "insufficient_data": 7,
    }
    breakdown["macd"] = macd_scores.get(macd_signal, 7)

    # 5. RSI score (10 pts)
    rsi_zone = rsi_data.get("zone", "neutral")
    rsi_scores = {
        "oversold": 10, "strong": 8, "neutral": 5,
        "weak": 3, "overbought": 0, "unknown": 5,
    }
    breakdown["rsi"] = rsi_scores.get(rsi_zone, 5)

    # 6. Support score (10 pts)
    sup_score = 0
    if support_data.get("support_ma5"):
        sup_score += 5
    if support_data.get("support_ma10"):
        sup_score += 5
    breakdown["support"] = sup_score

    total = sum(breakdown.values())

    # Signal generation
    alignment_val = ma_data.get("alignment", "consolidation")
    bullish_alignments = ["bullish", "strong_bullish", "weak_bullish"]

    if total >= 75 and alignment_val in ["bullish", "strong_bullish"]:
        signal = "strong_buy"
    elif total >= 60 and alignment_val in bullish_alignments:
        signal = "buy"
    elif total >= 45:
        signal = "hold"
    elif total >= 30:
        signal = "wait"
    elif alignment_val in ["bearish", "strong_bearish"]:
        signal = "strong_sell"
    else:
        signal = "sell"

    signal_cn = {
        "strong_buy": "强烈买入", "buy": "买入", "hold": "持有",
        "wait": "观望", "sell": "卖出", "strong_sell": "强烈卖出",
    }

    return {
        "total": total,
        "breakdown": breakdown,
        "signal": signal,
        "signal_cn": signal_cn.get(signal, signal),
    }


# ============================================================
# SECTION 4.5: Fundamental Score (30 pts) - NEW
# ============================================================

def _score_pe(pe):
    """PE 估值 (5 pts). Lower is cheaper; negative means loss."""
    if pe is None:
        return 2, "数据缺失"
    if pe <= 0:
        return 0, f"PE={pe:.1f} 亏损或负值"
    if pe < 15:
        return 5, f"PE={pe:.1f} 便宜"
    if pe < 25:
        return 4, f"PE={pe:.1f} 合理"
    if pe < 40:
        return 3, f"PE={pe:.1f} 偏贵"
    if pe < 60:
        return 1, f"PE={pe:.1f} 高估"
    return 0, f"PE={pe:.1f} 极度高估"


def _score_pb(pb):
    """PB 估值 (5 pts)."""
    if pb is None:
        return 2, "数据缺失"
    if pb <= 0:
        return 0, f"PB={pb:.2f} 异常"
    if pb < 1:
        return 5, f"PB={pb:.2f} 破净"
    if pb < 2:
        return 5, f"PB={pb:.2f} 便宜"
    if pb < 4:
        return 4, f"PB={pb:.2f} 合理"
    if pb < 6:
        return 2, f"PB={pb:.2f} 偏贵"
    return 0, f"PB={pb:.2f} 昂贵"


def _score_roe(roe):
    """ROE (5 pts). %"""
    if roe is None:
        return 2, "数据缺失"
    if roe >= 20:
        return 5, f"ROE={roe:.1f}% 高质量"
    if roe >= 15:
        return 4, f"ROE={roe:.1f}% 优秀"
    if roe >= 10:
        return 3, f"ROE={roe:.1f}% 一般"
    if roe >= 5:
        return 2, f"ROE={roe:.1f}% 偏弱"
    if roe >= 0:
        return 1, f"ROE={roe:.1f}% 很弱"
    return 0, f"ROE={roe:.1f}% 亏损"


def _score_revenue_yoy(yoy):
    """营收增速 (5 pts). %"""
    if yoy is None:
        return 2, "数据缺失"
    if yoy >= 50:
        return 5, f"营收YoY={yoy:.1f}% 高速增长"
    if yoy >= 20:
        return 4, f"营收YoY={yoy:.1f}% 强劲"
    if yoy >= 10:
        return 3, f"营收YoY={yoy:.1f}% 稳健"
    if yoy >= 0:
        return 2, f"营收YoY={yoy:.1f}% 缓慢"
    if yoy >= -10:
        return 1, f"营收YoY={yoy:.1f}% 下滑"
    return 0, f"营收YoY={yoy:.1f}% 大幅下滑"


def _score_gross_margin(gm):
    """毛利率 (5 pts). %"""
    if gm is None:
        return 2, "数据缺失"
    if gm >= 50:
        return 5, f"毛利率={gm:.1f}% 高毛利"
    if gm >= 30:
        return 4, f"毛利率={gm:.1f}% 健康"
    if gm >= 20:
        return 3, f"毛利率={gm:.1f}% 一般"
    if gm >= 10:
        return 2, f"毛利率={gm:.1f}% 偏低"
    if gm > 0:
        return 1, f"毛利率={gm:.1f}% 低毛利"
    return 0, f"毛利率={gm:.1f}% 负毛利"


def _score_debt(da):
    """资产负债率 (5 pts). %"""
    if da is None:
        return 2, "数据缺失"
    if da < 30:
        return 5, f"负债率={da:.1f}% 非常健康"
    if da < 50:
        return 4, f"负债率={da:.1f}% 健康"
    if da < 65:
        return 3, f"负债率={da:.1f}% 一般"
    if da < 80:
        return 1, f"负债率={da:.1f}% 高杠杆"
    return 0, f"负债率={da:.1f}% 高风险"


def calc_fundamental_score(fundamentals: dict) -> dict:
    """
    Composite fundamental scoring (30 points total):
    PE 5 + PB 5 + ROE 5 + Revenue YoY 5 + Gross Margin 5 + Debt/Asset 5
    """
    if not fundamentals:
        fundamentals = _empty_fundamentals()

    pe_score, pe_note = _score_pe(fundamentals.get("pe_ttm"))
    pb_score, pb_note = _score_pb(fundamentals.get("pb"))
    roe_score, roe_note = _score_roe(fundamentals.get("roe"))
    rev_score, rev_note = _score_revenue_yoy(fundamentals.get("revenue_yoy"))
    gm_score, gm_note = _score_gross_margin(fundamentals.get("gross_margin"))
    debt_score, debt_note = _score_debt(fundamentals.get("debt_to_asset"))

    breakdown = {
        "pe": pe_score, "pb": pb_score, "roe": roe_score,
        "revenue_yoy": rev_score, "gross_margin": gm_score, "debt_to_asset": debt_score,
    }
    notes = {
        "pe": pe_note, "pb": pb_note, "roe": roe_note,
        "revenue_yoy": rev_note, "gross_margin": gm_note, "debt_to_asset": debt_note,
    }
    total = sum(breakdown.values())

    if total >= 24:
        rating = "优秀"
    elif total >= 18:
        rating = "良好"
    elif total >= 12:
        rating = "中等"
    elif total >= 6:
        rating = "偏弱"
    else:
        rating = "差"

    return {
        "total": total,
        "max": 30,
        "breakdown": breakdown,
        "notes": notes,
        "rating": rating,
    }


# ============================================================
# SECTION 5: Main Orchestrator
# ============================================================

def analyze_stock(code: str, days: int = 120, fetch_news: bool = False) -> dict:
    """Full analysis pipeline for a single stock."""
    market, normalized, display = classify_stock(code)

    if market == "unknown":
        raise ValueError(f"Cannot classify stock code: {code}")

    # Fetch data with graceful degradation
    if market == "cn_a":
        raw = fetch_cn_a(normalized, days)
    elif market == "cn_hk":
        raw = fetch_hk(normalized, days)
    else:
        raw = fetch_us(normalized, days)

    ohlcv = raw["ohlcv"]
    if not ohlcv or len(ohlcv) < 10:
        raise ValueError(f"Insufficient data for {code}: only {len(ohlcv)} bars")

    closes = [bar["close"] for bar in ohlcv if bar["close"] is not None]
    volumes = [bar["volume"] for bar in ohlcv if bar["volume"] is not None]

    if len(closes) < 10:
        raise ValueError(f"Insufficient valid close prices for {code}")

    # Calculate technical indicators
    ma = calc_ma(closes, [5, 10, 20, 60])
    macd = calc_macd(closes)
    rsi = calc_rsi(closes, [6, 12, 24])
    vol = calc_volume_analysis(volumes, closes)
    bias = calc_bias(closes, ma)
    support = calc_support(closes, ma)
    technical_raw = calc_trend_score(ma, macd, rsi, vol, bias, support)

    # Calculate fundamental score (NEW)
    fundamentals = raw.get("fundamentals", _empty_fundamentals())
    fundamental = calc_fundamental_score(fundamentals)

    # 3D composite score: technical 50 + fundamental 30 + news 20 (Claude fills)
    tech_50 = round(technical_raw["total"] / 2, 1)
    fund_30 = fundamental["total"]
    subtotal_80 = round(tech_50 + fund_30, 1)

    composite = {
        "technical_50": tech_50,
        "fundamental_30": fund_30,
        "news_20": None,
        "subtotal_80": subtotal_80,
        "max_total": 100,
        "weight_scheme": "technical 50% + fundamental 30% + news 20%",
        "note": "news_20 待 Claude 根据消息面分析填入 0-20 分；最终总分 = technical_50 + fundamental_30 + news_20",
    }

    # News search (optional)
    news = []
    if fetch_news:
        stock_name = raw.get("name", display)
        news = search_news(stock_name, display)

    result = {
        "code": display,
        "market": market,
        "name": raw.get("name", display),
        "data_source": raw.get("source", "unknown"),
        "realtime": raw.get("realtime", {}),
        "fundamentals": fundamentals,
        "indicators": {
            "ma": ma,
            "macd": macd,
            "rsi": rsi,
            "volume": vol,
            "bias": bias,
            "support": support,
        },
        "technical_score": {
            "total_100": technical_raw["total"],
            "total_50": tech_50,
            "breakdown": technical_raw["breakdown"],
            "signal_native": technical_raw["signal"],
            "signal_cn_native": technical_raw["signal_cn"],
        },
        "fundamental_score": fundamental,
        "composite_score": composite,
        "trend_score": technical_raw,  # backward-compat
        "recent_bars": ohlcv[-10:],
        "total_bars": len(ohlcv),
        "fetch_time": datetime.now().isoformat(),
    }
    if news:
        result["news"] = news
    return result


def main():
    parser = argparse.ArgumentParser(description="Stock Data Fetcher")
    parser.add_argument("--stocks", required=True, help="Comma-separated stock codes")
    parser.add_argument("--days", type=int, default=120, help="History trading days")
    parser.add_argument("--news", action="store_true", help="Also search news (requires TAVILY_API_KEY or SERPAPI_KEY)")
    args = parser.parse_args()

    codes = [c.strip() for c in args.stocks.split(",") if c.strip()]
    results = []
    errors = []

    # Report available data sources
    sources_status = {}
    for lib in ["tushare", "efinance", "akshare", "yfinance"]:
        sources_status[lib] = "available" if _check_source(lib) else "not installed"
    sources_status["tushare_token"] = "configured" if os.environ.get("TUSHARE_TOKEN") else "not set"
    sources_status["tavily_api"] = "configured" if os.environ.get("TAVILY_API_KEY") else "not set"
    sources_status["serpapi"] = "configured" if os.environ.get("SERPAPI_KEY") else "not set"
    _log(f"Data sources: {json.dumps(sources_status)}")

    for code in codes:
        try:
            result = analyze_stock(code, args.days, fetch_news=args.news)
            results.append(result)
        except Exception as e:
            errors.append({"code": code, "error": str(e), "type": type(e).__name__})

    output = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "analysis_time": datetime.now().strftime("%H:%M:%S"),
        "data_sources": sources_status,
        "stocks": results,
        "errors": errors,
        "total_requested": len(codes),
        "total_success": len(results),
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
