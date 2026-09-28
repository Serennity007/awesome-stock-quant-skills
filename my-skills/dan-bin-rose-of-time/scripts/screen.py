#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen.py — 但斌"时间的玫瑰"伟大企业 A 股打分器。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out result.csv

筛选逻辑（但斌东方港湾"与伟大企业共成长"的机械化近似）:
    1. 长坡：行业与公司的成长跑道（营收 5 年 CAGR）。
    2. 厚雪：高毛利率=生意本身的利润禀赋（品牌的定价权体现）。
    3. 复利引擎：长期高 ROE 是复利的发动机。
    4. 时间的玫瑰：持续分红让股东分享复利，检验现金流真实性。
    5. 盈利含金量 / 财务健康 / 成长质量：伟大企业的基本面底线。
    打分排序输出 CSV，供进一步定性复核（是否"可以传给下一代的生意"）。

数据源: akshare（东财财务指标/估值 + 巨潮分红 + 腾讯快照，失败自动降级）。
"""
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Optional

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import pandas as pd
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import akshare as ak
except ImportError:
    sys.exit("ERROR: 未安装 akshare，请先执行: pip install akshare pandas")

YEARS = 5


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理阻断数据源直连。"""
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(k, None)
    _install_request_timeout()


def _install_request_timeout(seconds: int = 20):
    """给所有 requests 请求注入默认超时——akshare 内部调用不带 timeout，
    个别挂起连接会让整个跑测无限阻塞（实测发生过），必须全局兜底。"""
    _orig_request = requests.Session.request

    def _with_timeout(self, *args, **kwargs):
        kwargs.setdefault("timeout", seconds)
        return _orig_request(self, *args, **kwargs)

    requests.Session.request = _with_timeout


def _retry_call(func, max_retries: int = 3, sleep_base: float = 1.0):
    """带指数退避的简单重试，最后一次失败抛出原异常。"""
    last_err = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(sleep_base * (2 ** attempt))
    raise last_err


def normalize_date(date_str: str) -> str:
    """兼容 20231231 与 2023-12-31，统一返回 2023-12-31。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return date_str


def safe_div(a, b, default=float("nan")):
    """除零防护：b 为 0 或 nan 时返回 default。"""
    try:
        if pd.isna(a) or pd.isna(b):
            return default
        b = float(b)
        if b == 0:
            return default
        return float(a) / b
    except Exception:
        return default


def _find_col(candidates: list, df: pd.DataFrame) -> Optional[str]:
    """按候选子串在 df 列名中查找第一个匹配列。"""
    for c in df.columns:
        cs = str(c)
        for cand in candidates:
            if cand in cs:
                return c
    return None


def _to_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


# ---------------------------------------------------------------------------
# 股票池与元信息
# ---------------------------------------------------------------------------

def get_pool(pool: str) -> list:
    if pool == "hs300":
        errs = []
        try:
            df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
            time.sleep(0.15)
            col = _find_col(["成分券代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"csindex: {e}")
        try:
            df = _retry_call(lambda: ak.index_stock_cons_weight_csindex(symbol="000300"))
            time.sleep(0.15)
            col = _find_col(["成分券代码", "股票代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"weight csindex: {e}")
        sys.exit(f"ERROR: 获取沪深300成分股失败: {'; '.join(errs)}")
    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


def fetch_industry_map() -> pd.DataFrame:
    """从最新业绩报表获取代码->名称/行业映射。失败返回空 DataFrame。"""
    now = datetime.now()
    candidates = []
    for y in range(now.year, now.year - 3, -1):
        for m, d in ((12, 31), (9, 30), (6, 30), (3, 31)):
            candidates.append(f"{y}{m:02d}{d:02d}")
    for date in candidates:
        try:
            df = _retry_call(lambda d=date: ak.stock_yjbb_em(date=d))
            time.sleep(0.15)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        code_col = _find_col(["股票代码"], df)
        name_col = _find_col(["股票简称"], df)
        ind_col = _find_col(["所处行业"], df)
        if code_col is None:
            continue
        s = df.copy()
        s["code"] = s[code_col].astype(str).str.strip().str.zfill(6)
        s = s.drop_duplicates("code")
        out = pd.DataFrame({"code": s["code"].values})
        if name_col is not None:
            out["name"] = s[name_col].astype(str).values
        if ind_col is not None:
            out["industry"] = s[ind_col].astype(str).values
        if "industry" in out.columns and out["industry"].notna().sum() > 0:
            return out.dropna(subset=["industry"]).reset_index(drop=True)
    return pd.DataFrame(columns=["code", "name", "industry"])


# ---------------------------------------------------------------------------
# 个股数据
# ---------------------------------------------------------------------------

def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """近 YEARS 年主要财务指标（年报）。失败抛异常。"""
    start_year = datetime.now().year - YEARS - 2
    df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=str(start_year)))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("财务指标为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df) or df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col].astype(str).apply(normalize_date), errors="coerce")
    today = pd.Timestamp.now()
    df = df[(df[date_col].dt.month == 12) & (df[date_col] <= today)]
    df = df.sort_values(date_col).tail(YEARS)
    if df.empty:
        raise RuntimeError("无年度财务数据")
    return df.reset_index(drop=True)


def fetch_sina_report(code: str, report_type: str) -> pd.DataFrame:
    """新浪三大报表（年报）。失败返回空 DataFrame。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol=report_type))
    except Exception:
        return pd.DataFrame()
    time.sleep(0.15)
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["报告日"] = df["报告日"].astype(str).str.replace("-", "")
    today = pd.Timestamp.now().strftime("%Y%m%d")
    df = df[(df["报告日"].str.endswith("1231")) & (df["报告日"] <= today)]
    df = df.sort_values("报告日").tail(YEARS)
    return df.reset_index(drop=True)


def fetch_dividend_cninfo(code: str) -> pd.DataFrame:
    """巨潮资讯分红数据，失败返回空 DataFrame；过滤未来日期。"""
    try:
        df = _retry_call(lambda: ak.stock_dividend_cninfo(symbol=code))
    except Exception:
        return pd.DataFrame()
    time.sleep(0.15)
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["实施方案公告日期"], df)
    if date_col is None:
        return pd.DataFrame()
    df[date_col] = df[date_col].astype(str).apply(normalize_date)
    df = df[df[date_col] <= datetime.now().strftime("%Y-%m-%d")]
    return df.reset_index(drop=True)


def _annual_dividend_per_share(div_df: pd.DataFrame) -> tuple:
    """年化每股分红（元），返回 (年化DPS, 次数, 参考跨度年)。

    按"报告时间"列的财年归属精确年化：一个财年 = 同一报告年份的
    三季报分红（中期）+ 年报分红。取最近一个**完整财年**（含"年报"
    分红已实施）的每股合计——分红频率变化（如 2024 年后普及的中期
    分红）、特别分红都不会虚高；若最新财年年报分红尚未实施，退回
    上一财年。报告时间缺失时降级为"最近 5 次按跨度年化"。
    """
    if div_df.empty:
        return float("nan"), 0, float("nan")
    ratio_col = _find_col(["派息比例"], div_df)
    date_col = _find_col(["实施方案公告日期"], div_df)
    report_col = _find_col(["报告时间"], div_df)
    if ratio_col is None or date_col is None:
        return float("nan"), 0, float("nan")
    sub = div_df[[ratio_col, date_col] + ([report_col] if report_col else [])].copy()
    sub[ratio_col] = _to_numeric_series(sub[ratio_col])
    sub[date_col] = pd.to_datetime(sub[date_col], errors="coerce")
    sub = sub.dropna(subset=[ratio_col, date_col]).sort_values(date_col)
    if sub.empty:
        return float("nan"), 0, float("nan")

    # 主口径：财年归属
    if report_col:
        sub["fy"] = sub[report_col].astype(str).str.extract(r"(\d{4})")
        sub = sub.dropna(subset=["fy"])
        if not sub.empty:
            for fy in sorted(sub["fy"].unique(), reverse=True):
                grp = sub[sub["fy"] == fy]
                is_annual = grp[report_col].astype(str).str.contains("年报").any()
                if is_annual:
                    annual_dps = float(grp[ratio_col].sum()) / 10.0
                    span_years = (sub[date_col].iloc[-1] - sub[date_col].iloc[0]).days / 365.25
                    return annual_dps, len(grp), max(span_years, 0.8)

    # 降级：最近 5 次按实际跨度年化（稳定派息者仍较准）
    last5 = sub.tail(5)
    total_per_share = float(last5[ratio_col].sum()) / 10.0
    span_years = max((last5[date_col].iloc[-1] - last5[date_col].iloc[0]).days / 365.25, 0.8)
    return total_per_share / span_years, len(last5), span_years


def fetch_gross_from_income(code: str) -> pd.Series:
    """从利润表现算毛利率 (营收-营业成本)/营收：东财季报优先，新浪降级。"""
    today = pd.Timestamp.now().strftime("%Y%m%d")

    # 东财利润表（报告期），列名为英文大写
    try:
        df = _retry_call(lambda: ak.stock_profit_sheet_by_report_em(symbol=code))
        time.sleep(0.15)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            date_col = _find_col(["REPORT_DATE", "报告日期", "报告日"], df)
            inc_col = _find_col(["OPERATE_INCOME", "营业总收入", "营业收入"], df)
            cost_col = _find_col(["OPERATE_COST", "营业成本"], df)
            if date_col and inc_col and cost_col:
                d = pd.to_datetime(df[date_col].astype(str).apply(normalize_date), errors="coerce")
                inc = _to_numeric_series(df[inc_col])
                cost = _to_numeric_series(df[cost_col])
                mask = d.dt.month == 12
                annual = pd.DataFrame({"d": d, "inc": inc, "cost": cost})[mask.fillna(False)]
                annual = annual[(annual["inc"] > 0) & annual["cost"].notna()].sort_values("d").tail(YEARS)
                if not annual.empty:
                    return ((annual["inc"] - annual["cost"]) / annual["inc"] * 100).reset_index(drop=True)
    except Exception:
        pass

    # 新浪利润表降级
    inc_df = fetch_sina_report(code, "利润表")
    if inc_df.empty:
        return pd.Series(dtype=float)
    inc_col = _find_col(["营业总收入", "营业收入"], inc_df)
    cost_col = _find_col(["营业成本"], inc_df)
    if inc_col is None or cost_col is None:
        return pd.Series(dtype=float)
    rev = _to_numeric_series(inc_df[inc_col]).dropna()
    cost = _to_numeric_series(inc_df[cost_col]).dropna()
    n = min(len(rev), len(cost))
    if n == 0:
        return pd.Series(dtype=float)
    gross = ((rev.iloc[-n:].values - cost.iloc[-n:].values) / rev.iloc[-n:].replace(0, float("nan")).values * 100)
    return pd.Series(gross).dropna()


def get_financials(code: str) -> dict:
    """毛利率 / ROE / 营收与净利润增速 / 负债率 / 现金流含金量，东财优先，新浪降级。"""
    errs = []
    try:
        df = fetch_financial_indicator(code)
        roe_col = _find_col(["净资产收益率(%)"], df)
        gross_col = _find_col(["销售毛利率(%)"], df)
        debt_col = _find_col(["资产负债率(%)"], df)
        ocf_col = _find_col(["经营现金净流量与净利润的比率(%)"], df)
        growth_col = _find_col(["净利润增长率(%)"], df)
        rev_growth_col = _find_col(["主营业务收入增长率(%)"], df)
        if roe_col is None:
            raise RuntimeError("财务指标表缺少 ROE 列")
        out = {
            "roe": _to_numeric_series(df[roe_col]).dropna(),
            "gross": _to_numeric_series(df[gross_col]).dropna() if gross_col is not None else pd.Series(dtype=float),
            "debt": _to_numeric_series(df[debt_col]).dropna() if debt_col is not None else pd.Series(dtype=float),
            "ocf": _to_numeric_series(df[ocf_col]).dropna() if ocf_col is not None else pd.Series(dtype=float),
            "profit_growth": _to_numeric_series(df[growth_col]).dropna() if growth_col is not None else pd.Series(dtype=float),
            "rev_growth": _to_numeric_series(df[rev_growth_col]).dropna() if rev_growth_col is not None else pd.Series(dtype=float),
            "source": "akshare.stock_financial_analysis_indicator",
            "note": "",
        }
        if out["gross"].empty:
            # 东财财务指标表的毛利率列已停供，改从利润表现算
            out["gross"] = fetch_gross_from_income(code)
            if not out["gross"].empty and not out["note"]:
                out["note"] = "毛利率由利润表现算"
        if out["profit_growth"].empty or out["rev_growth"].empty:
            time.sleep(0.15)
            inc = fetch_sina_report(code, "利润表")
            if not inc.empty:
                rev_col = _find_col(["营业总收入"], inc) or _find_col(["营业收入"], inc)
                profit_col = _find_col(["净利润"], inc)
                if rev_col is not None and len(inc) >= 2:
                    rev = _to_numeric_series(inc[rev_col]).dropna().sort_index()
                    n = len(rev)
                    if n >= 2 and rev.iloc[0] > 0:
                        cagr = ((rev.iloc[-1] / rev.iloc[0]) ** (1 / (n - 1)) - 1) * 100
                        if out["rev_growth"].empty:
                            out["rev_growth"] = pd.Series([cagr])
                            out["note"] = "营收CAGR由新浪利润表补充"
                if profit_col is not None and out["profit_growth"].empty:
                    profit = _to_numeric_series(inc[profit_col]).dropna()
                    if len(profit) >= 2:
                        out["profit_growth"] = (profit.pct_change().dropna() * 100).dropna()
        return out
    except Exception as e:
        errs.append(f"财务指标表: {e}")

    time.sleep(0.15)
    try:
        inc = fetch_sina_report(code, "利润表")
        bs = fetch_sina_report(code, "资产负债表")
        if inc.empty or bs.empty:
            raise RuntimeError("新浪三大报表不足以计算指标")
        rev_col = _find_col(["营业总收入"], inc) or _find_col(["营业收入"], inc)
        profit_col = _find_col(["净利润"], inc)
        cost_col = _find_col(["营业成本"], inc)
        equity_col = _find_col(["所有者权益(或股东权益)合计"], bs)
        out = {"roe": pd.Series(dtype=float), "gross": pd.Series(dtype=float),
               "debt": pd.Series(dtype=float), "ocf": pd.Series(dtype=float),
               "profit_growth": pd.Series(dtype=float), "rev_growth": pd.Series(dtype=float),
               "source": "akshare.stock_financial_report_sina（降级）", "note": ""}
        if profit_col is not None and equity_col is not None:
            profit = _to_numeric_series(inc[profit_col]).dropna()
            equity = _to_numeric_series(bs[equity_col]).dropna()
            n = min(len(profit), len(equity))
            if n > 0:
                out["roe"] = (profit.iloc[-n:].values / equity.iloc[-n:].replace(0, float("nan")).values * 100)
                out["roe"] = pd.Series(out["roe"]).dropna()
        if rev_col is not None:
            rev = _to_numeric_series(inc[rev_col]).dropna()
            if len(rev) >= 2 and rev.iloc[0] > 0:
                out["rev_growth"] = pd.Series([((rev.iloc[-1] / rev.iloc[0]) ** (1 / (len(rev) - 1)) - 1) * 100])
            if cost_col is not None:
                cost = _to_numeric_series(inc[cost_col]).dropna()
                n = min(len(rev), len(cost))
                if n > 0:
                    out["gross"] = ((rev.iloc[-n:].values - cost.iloc[-n:].values) / rev.iloc[-n:].replace(0, float("nan")).values * 100)
                    out["gross"] = pd.Series(out["gross"]).dropna()
        if profit_col is not None:
            profit = _to_numeric_series(inc[profit_col]).dropna()
            if len(profit) >= 2:
                out["profit_growth"] = (profit.pct_change().dropna() * 100).dropna()
        liab_col = _find_col(["负债合计"], bs)
        asset_col = _find_col(["资产总计"], bs)
        if liab_col is not None and asset_col is not None:
            out["debt"] = (_to_numeric_series(bs[liab_col]) / _to_numeric_series(bs[asset_col]).replace(0, float("nan")) * 100).dropna()
        out["note"] = "新浪三大报表降级计算"
        return out
    except Exception as e:
        errs.append(f"新浪三大报表: {e}")

    raise RuntimeError("; ".join(errs))


_TX_SPOT_CACHE: Optional[pd.DataFrame] = None


def _get_tx_spot() -> Optional[pd.DataFrame]:
    """全市场快照每次跑测只拉一次（300 只股票逐只拉会拖慢 10 倍且易被限流）。"""
    global _TX_SPOT_CACHE
    if _TX_SPOT_CACHE is not None:
        return _TX_SPOT_CACHE
    try:
        _TX_SPOT_CACHE = _retry_call(lambda: ak.stock_zh_a_spot_tx())
    except Exception:
        _TX_SPOT_CACHE = pd.DataFrame()
    time.sleep(0.2)
    return _TX_SPOT_CACHE


def get_close_price(code: str) -> float:
    """从缓存的全市场快照取最新收盘价，失败返回 nan。"""
    try:
        prefix = "sh" if code.startswith("6") or code.startswith("5") else "sz"
        df = _get_tx_spot()
        if df is None or df.empty or "code" not in df.columns:
            return float("nan")
        row = df[df["code"].astype(str).str.lower() == f"{prefix}{code}"]
        if row.empty:
            return float("nan")
        return float(pd.to_numeric(row.iloc[-1].get("zxj"), errors="coerce"))
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# 打分（七维，满分 100）
# ---------------------------------------------------------------------------

def score_runway(rev_growth: pd.Series) -> tuple[int, float]:
    """长坡·成长跑道（满分 15）：营收 5 年 CAGR 越高，坡越长。"""
    s = rev_growth.dropna()
    if s.empty:
        return 0, float("nan")
    v = float(s.mean())
    if v >= 25:
        return 15, v
    elif v >= 15:
        return 12, v
    elif v >= 10:
        return 9, v
    elif v >= 5:
        return 6, v
    elif v > 0:
        return 3, v
    return 0, v


def score_thick_snow(gross: pd.Series) -> tuple[int, float]:
    """厚雪·利润禀赋（满分 20）：高毛利率=生意的定价权与品牌力。"""
    s = gross.dropna()
    if s.empty:
        return 0, float("nan")
    v = float(s.mean())
    if v >= 60:
        return 20, v
    elif v >= 45:
        return 16, v
    elif v >= 30:
        return 12, v
    elif v >= 20:
        return 8, v
    elif v >= 10:
        return 4, v
    return 0, v


def score_roe_engine(roe: pd.Series) -> tuple[int, float]:
    """复利引擎（满分 20）：长期高 ROE 是复利的发动机。"""
    s = roe.dropna()
    if s.empty:
        return 0, float("nan")
    v = float(s.mean())
    if v >= 25:
        return 20, v
    elif v >= 20:
        return 17, v
    elif v >= 15:
        return 13, v
    elif v >= 10:
        return 8, v
    elif v >= 5:
        return 4, v
    return 0, v


def score_rose(div_yield: float, div_count: int) -> int:
    """时间的玫瑰（满分 15）：持续分红是复利之花，也检验现金流真实。"""
    if pd.isna(div_yield) or div_count == 0:
        return 0
    if div_yield >= 5:
        return 15
    elif div_yield >= 3:
        return 12
    elif div_yield >= 2:
        return 9
    elif div_yield >= 1:
        return 5
    elif div_yield > 0:
        return 2
    return 0


def score_cash(ocf: pd.Series) -> int:
    """盈利含金量（满分 10）。"""
    s = ocf.dropna()
    if s.empty:
        return 0
    v = float(s.mean())
    if v >= 1.0:
        return 10
    elif v >= 0.8:
        return 7
    elif v >= 0.5:
        return 4
    elif v > 0:
        return 2
    return 0


def score_debt(debt: pd.Series) -> int:
    """财务健康（满分 10）。"""
    s = debt.dropna()
    if s.empty:
        return 0
    latest = float(s.iloc[-1])
    if latest < 35:
        return 10
    elif latest < 50:
        return 7
    elif latest < 65:
        return 4
    elif latest < 75:
        return 2
    return 0


def score_growth_quality(profit_growth: pd.Series) -> int:
    """成长质量（满分 10）：净利润正增长年数，伟大企业 rarely 变坏。"""
    s = profit_growth.dropna()
    if s.empty:
        return 0
    n = int((s > 0).sum())
    if n >= 4:
        return 10
    elif n >= 3:
        return 7
    elif n >= 2:
        return 4
    elif n >= 1:
        return 2
    return 0


def score_one(code: str, meta: pd.DataFrame) -> dict:
    fin = get_financials(code)
    time.sleep(0.15)
    div_df = fetch_dividend_cninfo(code)
    close = get_close_price(code)

    div_per_share, div_count, div_span_years = _annual_dividend_per_share(div_df)
    div_yield = safe_div(div_per_share, close, default=float("nan")) * 100 if div_count else float("nan")

    meta_row = meta[meta["code"] == code]
    name = str(meta_row["name"].iloc[0]) if not meta_row.empty and "name" in meta.columns else ""
    industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty and "industry" in meta.columns else ""

    runway_score, rev_cagr = score_runway(fin["rev_growth"])
    snow_score, gross_mean = score_thick_snow(fin["gross"])
    snow_note = ""
    if pd.isna(gross_mean):
        # 银行/保险等金融业没有毛利率概念，给中性分而不是 0 分
        snow_score, snow_note = 8, "金融业等无毛利率，厚雪给中性分(8/20)"
    roe_score, roe_mean = score_roe_engine(fin["roe"])
    rose_score = score_rose(div_yield, div_count)
    cash_score = score_cash(fin["ocf"])
    debt_score = score_debt(fin["debt"])
    gq_score = score_growth_quality(fin["profit_growth"])
    total = runway_score + snow_score + roe_score + rose_score + cash_score + debt_score + gq_score

    return {
        "code": code,
        "name": name,
        "industry": industry,
        "total": total,
        "runway_score": runway_score,
        "snow_score": snow_score,
        "roe_engine_score": roe_score,
        "rose_score": rose_score,
        "cash_score": cash_score,
        "debt_score": debt_score,
        "growth_quality_score": gq_score,
        "rev_cagr": round(float(rev_cagr), 1) if pd.notna(rev_cagr) else None,
        "gross_mean": round(float(gross_mean), 1) if pd.notna(gross_mean) else None,
        "roe_mean": round(float(roe_mean), 1) if pd.notna(roe_mean) else None,
        "dividend_yield": round(div_yield, 2) if pd.notna(div_yield) else None,
        "dividend_events": div_count,
        "dividend_span_years": round(div_span_years, 1) if pd.notna(div_span_years) else None,
        "ocf_mean": round(float(fin["ocf"].mean()), 2) if len(fin["ocf"]) else None,
        "debt_latest": round(float(fin["debt"].iloc[-1]), 1) if len(fin["debt"]) else None,
        "profit_pos_years": int((fin["profit_growth"] > 0).sum()) if len(fin["profit_growth"]) else None,
        "close": round(close, 2) if pd.notna(close) else None,
        "data_years": max(len(fin["roe"]), len(fin["rev_growth"]), len(fin["gross"])),
        "fin_source": fin["source"],
        "note": "; ".join(x for x in [fin.get("note", ""), snow_note] if x),
        "data_date": normalize_date(datetime.now().strftime("%Y%m%d")),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description='但斌"时间的玫瑰"伟大企业 A 股打分器')
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="danbin_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    ap.add_argument("--offset", type=int, default=0, help="跳过池内前 N 只（分块跑测用）")
    ap.add_argument("--limit", type=int, default=0, help="最多处理 N 只（分块跑测用，0=不限制）")
    args = ap.parse_args()

    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    codes = [c.zfill(6) for c in codes]
    if args.offset or args.limit:
        codes = codes[args.offset: args.offset + args.limit if args.limit else None]

    print(f"股票池共 {len(codes)} 只，加载名称/行业映射...")
    meta = fetch_industry_map()

    print("开始逐一打分（财务指标+分红+行情三个接口，请耐心）...")
    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, meta)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} {r['name']} 得分 {r['total']} | 营收CAGR {r['rev_cagr']}% | 毛利率 {r['gross_mean']}% | ROE {r['roe_mean']}% | 股息率 {r['dividend_yield']}%")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("total", ascending=False)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "code", "name", "total", "runway_score", "snow_score", "roe_engine_score", "rose_score",
        "rev_cagr", "gross_mean", "roe_mean", "dividend_yield", "debt_latest", "data_years",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    print(df.head(args.top)[display_cols].to_string(index=False))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=75 '与伟大企业共成长'候选; 55-74 观察; <55 不符合框架。")
    print("提醒: 得分只回答'长坡厚雪'的量化部分，'能否传给下一代'的生意定性必须人工复核。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
