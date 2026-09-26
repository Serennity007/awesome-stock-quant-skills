#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen.py — 段永平"商业模式第一"A股初筛器。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out result.csv

筛选逻辑（段永平投资思想机械化）:
    1. 生意模式优先：高毛利率 + 高ROE + 低资本开支（经营现金流/净利润比近似）。
    2. 低负债、盈利长期稳定。
    3. "敢为天下后"的行业龙头指标：在申万行业内按市值排名前列。
    打分排序输出 CSV，供进一步定性分析（企业文化、价格、能力圈）。

数据源: akshare（优先东方财富/同花顺/新浪公开接口，失败自动降级）。
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
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理阻断东财/同花顺/新浪直连。"""
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(k, None)


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


def _find_shares_col(df: pd.DataFrame) -> Optional[str]:
    """查找总股本列（银行/金融企业列名常为"股本"，一般企业为"实收资本(或股本)"）。"""
    for exact in ["实收资本(或股本)", "股本"]:
        for c in df.columns:
            if str(c).strip() == exact:
                return c
    return None


def _to_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


# ---------------------------------------------------------------------------
# 数据获取
# ---------------------------------------------------------------------------

def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """获取主要财务指标（年报），失败抛异常；过滤掉未来日期。"""
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
        raise RuntimeError("无年度财务指标数据")
    return df.reset_index(drop=True)


def fetch_sina_report(code: str, report_type: str) -> pd.DataFrame:
    """获取新浪三大报表（年报）。失败返回空 DataFrame；过滤掉未来日期。"""
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


def fetch_value_em(code: str) -> dict:
    """东财估值数据：总市值、PE、PB、PEG。失败返回空字典。"""
    try:
        df = _retry_call(lambda: ak.stock_value_em(symbol=code))
    except Exception:
        return {}
    time.sleep(0.15)
    if df is None or df.empty:
        return {}
    row = df.iloc[-1]
    out = {}
    for key, names in (
        ("total_mv", ("总市值",)),
        ("pe_ttm", ("PE(TTM)",)),
        ("pb", ("市净率", "PB")),
        ("peg", ("PEG值", "PEG")),
    ):
        col = _find_col(list(names), df)
        if col is not None:
            out[key] = pd.to_numeric(row[col], errors="coerce")
    return out


def fetch_value_tx_fallback(code: str) -> dict:
    """腾讯行情全市场快照降级，取总市值、PE(TTM)。"""
    prefix = "sh" if code.startswith("6") or code.startswith("5") else "sz"
    full = f"{prefix}{code}"
    try:
        df = _retry_call(lambda: ak.stock_zh_a_spot_tx())
    except Exception:
        return {}
    time.sleep(0.15)
    if df is None or df.empty or "code" not in df.columns:
        return {}
    row = df[df["code"].astype(str).str.lower() == full]
    if row.empty:
        return {}
    r = row.iloc[-1]
    return {
        "total_mv": pd.to_numeric(r.get("zsz"), errors="coerce"),  # 亿元
        "pe_ttm": pd.to_numeric(r.get("pe_ttm"), errors="coerce"),
    }


def fetch_yjbb_meta() -> pd.DataFrame:
    """全市场最新业绩报表中的代码、名称、行业映射。返回 DataFrame(code, name, industry)。"""
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
        return out
    return pd.DataFrame(columns=["code", "name", "industry"])


def fetch_market_snapshot_tx() -> pd.DataFrame:
    """腾讯全市场快照，返回 code(6位), total_mv(亿元), pe_ttm。"""
    df = _retry_call(lambda: ak.stock_zh_a_spot_tx())
    time.sleep(0.15)
    if df is None or df.empty or "code" not in df.columns:
        raise RuntimeError("腾讯全市场快照为空")
    out = pd.DataFrame()
    out["code"] = df["code"].astype(str).str.strip().str[-6:].str.zfill(6)
    out["total_mv"] = pd.to_numeric(df.get("zsz"), errors="coerce")
    out["pe_ttm"] = pd.to_numeric(df.get("pe_ttm"), errors="coerce")
    return out.dropna(subset=["code"]).drop_duplicates("code").reset_index(drop=True)


def build_industry_rank_map(yjbb: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    """合并业绩报表（行业）与市场快照（市值），计算行业内市值排名。"""
    if yjbb.empty or market.empty:
        return pd.DataFrame(columns=["code", "industry", "total_mv", "ind_rank", "ind_total", "ind_top_mv"])
    merged = pd.merge(yjbb[["code", "industry", "name"]], market[["code", "total_mv"]], on="code", how="inner")
    merged = merged.dropna(subset=["industry", "total_mv"])
    if merged.empty:
        return pd.DataFrame(columns=["code", "industry", "total_mv", "ind_rank", "ind_total", "ind_top_mv"])

    # 按行业内市值降序排名（method='min' 处理并列）
    merged["ind_rank"] = merged.groupby("industry")["total_mv"].rank(method="min", ascending=False).astype(int)
    merged["ind_total"] = merged.groupby("industry")["code"].transform("size").astype(int)
    merged["ind_top_mv"] = merged.groupby("industry")["total_mv"].transform("max")
    return merged[["code", "industry", "total_mv", "ind_rank", "ind_total", "ind_top_mv"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# 指标抽取（优先财务指标表，失败降级新浪报表）
# ---------------------------------------------------------------------------

class Metrics:
    """一只股票近 YEARS 年的段永平风格指标集合。"""

    def __init__(self):
        self.roe: pd.Series = pd.Series(dtype=float)
        self.gross_margin: pd.Series = pd.Series(dtype=float)
        self.debt_ratio: pd.Series = pd.Series(dtype=float)
        self.ocf_to_profit: pd.Series = pd.Series(dtype=float)
        self.profit_growth: pd.Series = pd.Series(dtype=float)
        self.revenue_growth: pd.Series = pd.Series(dtype=float)
        self.source = ""
        self.note = ""


def _from_indicator(code: str) -> Metrics:
    df = fetch_financial_indicator(code)
    m = Metrics()
    m.source = "akshare.stock_financial_analysis_indicator"

    roe_col = _find_col(["净资产收益率(%)"], df)
    gm_col = _find_col(["销售毛利率(%)"], df)
    debt_col = _find_col(["资产负债率(%)"], df)
    ocf_profit_col = _find_col(["经营现金净流量与净利润的比率(%)"], df)
    profit_growth_col = _find_col(["净利润增长率(%)"], df)
    rev_growth_col = _find_col(["主营业务收入增长率(%)"], df)

    if roe_col is None or gm_col is None or debt_col is None:
        raise RuntimeError("主要财务指标缺少必要列")

    m.roe = _to_numeric_series(df[roe_col]).dropna()
    m.gross_margin = _to_numeric_series(df[gm_col]).dropna()
    m.debt_ratio = _to_numeric_series(df[debt_col]).dropna()
    if ocf_profit_col is not None:
        # 该列名义为比率(%)，实际数值为 OCF/净利润 的倍数形式
        m.ocf_to_profit = _to_numeric_series(df[ocf_profit_col]).dropna()
    if profit_growth_col is not None:
        m.profit_growth = _to_numeric_series(df[profit_growth_col]).dropna()
    if rev_growth_col is not None:
        m.revenue_growth = _to_numeric_series(df[rev_growth_col]).dropna()

    m.note = "ROIC 风格指标以 ROE 代理（akshare 公开接口未直接提供 ROIC）"
    return m


def _from_sina(code: str) -> Metrics:
    """新浪三大报表降级：手工计算所需指标。"""
    bs = fetch_sina_report(code, "资产负债表")
    inc = fetch_sina_report(code, "利润表")
    cf = fetch_sina_report(code, "现金流量表")

    if bs.empty or inc.empty:
        raise RuntimeError("新浪三大报表不足以计算指标")

    m = Metrics()
    m.source = "akshare.stock_financial_report_sina（降级）"

    # 负债率 = 负债合计 / 资产总计
    liability_col = _find_col(["负债合计"], bs)
    asset_col = _find_col(["资产总计"], bs)
    if liability_col is not None and asset_col is not None:
        liabilities = _to_numeric_series(bs[liability_col])
        assets = _to_numeric_series(bs[asset_col])
        m.debt_ratio = (liabilities / assets.replace(0, float("nan")) * 100).dropna()

    # 毛利率 = (营业收入 - 营业成本) / 营业收入
    rev_col = _find_col(["营业收入"], inc)
    cost_col = _find_col(["营业成本"], inc)
    if rev_col is not None and cost_col is not None:
        rev = _to_numeric_series(inc[rev_col])
        cost = _to_numeric_series(inc[cost_col])
        m.gross_margin = ((rev - cost) / rev.replace(0, float("nan")) * 100).dropna()

    # ROE = 净利润 / 所有者权益合计
    profit_col = _find_col(["净利润"], inc)
    equity_col = _find_col(["所有者权益(或股东权益)合计"], bs)
    if profit_col is not None and equity_col is not None:
        profit = _to_numeric_series(inc[profit_col])
        equity = _to_numeric_series(bs[equity_col])
        m.roe = (profit / equity.replace(0, float("nan")) * 100).dropna()

    # 盈利质量 = 经营现金流净额 / 净利润
    if not cf.empty and profit_col is not None:
        ocf_col = _find_col(["经营活动产生的现金流量净额"], cf)
        if ocf_col is not None:
            cf["_rd"] = cf["报告日"].astype(str)
            inc["_rd"] = inc["报告日"].astype(str)
            merged = pd.merge(cf[["_rd", ocf_col]], inc[["_rd", profit_col]], on="_rd", how="inner")
            if not merged.empty:
                ocf_vals = _to_numeric_series(merged[ocf_col])
                profit_vals = _to_numeric_series(merged[profit_col])
                m.ocf_to_profit = (ocf_vals / profit_vals.replace(0, float("nan"))).dropna()

    # 利润增速：新浪利润表没有同比增长，用相邻年度净利润增速近似
    if profit_col is not None:
        profit = _to_numeric_series(inc[profit_col]).dropna()
        if len(profit) >= 2:
            m.profit_growth = (profit.pct_change().dropna() * 100).dropna()

    m.note = "ROIC 风格指标以 ROE 代理；主要数据源降级为新浪三大报表"
    return m


def _fill_gross_margin_from_income(m: Metrics, code: str):
    """当财务指标表中毛利率缺失时，用新浪利润表手工计算补充。"""
    if not m.gross_margin.empty and not m.gross_margin.dropna().empty:
        return
    inc = fetch_sina_report(code, "利润表")
    if inc.empty:
        return
    rev_col = _find_col(["营业收入"], inc)
    cost_col = _find_col(["营业成本"], inc)
    if rev_col is not None and cost_col is not None:
        rev = _to_numeric_series(inc[rev_col])
        cost = _to_numeric_series(inc[cost_col])
        m.gross_margin = ((rev - cost) / rev.replace(0, float("nan")) * 100).dropna()


def get_metrics(code: str) -> Metrics:
    """获取一只股票的段永平风格指标，优先财务指标表，失败降级新浪报表。"""
    errs = []
    try:
        m = _from_indicator(code)
        # 财务指标表近期经常出现毛利率缺失，用新浪利润表补充
        _fill_gross_margin_from_income(m, code)
        return m
    except Exception as e:
        errs.append(f"财务指标表: {e}")
    time.sleep(0.15)

    try:
        return _from_sina(code)
    except Exception as e:
        errs.append(f"新浪三大报表: {e}")

    raise RuntimeError("; ".join(errs))


# ---------------------------------------------------------------------------
# 打分
# ---------------------------------------------------------------------------

def score_business(s: pd.Series) -> int:
    """生意模式：高毛利率 + 稳定性（满分 25）。"""
    if s.empty:
        return 0
    mean_v = s.mean()
    score = 0
    if mean_v > 50:
        score += 15
    elif mean_v > 40:
        score += 12
    elif mean_v > 30:
        score += 8
    elif mean_v > 20:
        score += 4

    spread = s.max() - s.min()
    if spread < 3:
        score += 10
    elif spread < 5:
        score += 7
    elif spread < 10:
        score += 4
    return min(score, 25)


def score_roe(s: pd.Series) -> int:
    """资本回报：连续高 ROE（满分 20）。"""
    if s.empty:
        return 0
    total = 0
    for v in s:
        if pd.isna(v):
            continue
        if v > 20:
            total += 4
        elif v > 15:
            total += 3
        elif v > 10:
            total += 1
    return min(total, 20)


def score_cash_quality(s: pd.Series) -> int:
    """盈利含金量 / 资本开支友好度：经营现金流/净利润比（满分 20）。"""
    if s.empty:
        return 0
    mean_v = s.mean()
    if mean_v > 1.2:
        return 20
    elif mean_v > 1.0:
        return 16
    elif mean_v > 0.8:
        return 12
    elif mean_v > 0.6:
        return 8
    elif mean_v > 0.4:
        return 4
    return 0


def score_debt(s: pd.Series) -> int:
    """低负债（满分 15）。"""
    if s.empty:
        return 0
    latest = s.iloc[-1]
    if latest < 30:
        return 15
    elif latest < 45:
        return 10
    elif latest < 60:
        return 5
    return 0


def score_stability(profit_g: pd.Series, revenue_g: pd.Series) -> int:
    """盈利长期稳定：用利润增速变异系数，无利润增速则用营收增速（满分 10）。"""
    s = profit_g.dropna() if not profit_g.empty else revenue_g.dropna()
    if len(s) < 2:
        return 0
    mean_v = s.mean()
    std_v = s.std()
    if pd.isna(mean_v) or pd.isna(std_v):
        return 0
    cv = safe_div(std_v, abs(mean_v), default=float("nan"))
    if pd.isna(cv):
        return 0
    if cv < 0.15:
        return 10
    elif cv < 0.30:
        return 7
    elif cv < 0.50:
        return 4
    return 0


def score_leader(ind_rank: Optional[int], ind_total: Optional[int]) -> int:
    """行业龙头地位：市值排名越靠前越好（满分 10）。"""
    if ind_rank is None or ind_total is None or ind_total <= 0:
        return 0
    ratio = ind_rank / ind_total
    if ind_rank <= 3 or ratio <= 0.05:
        return 10
    elif ind_rank <= 5 or ratio <= 0.10:
        return 7
    elif ind_rank <= 10 or ratio <= 0.20:
        return 4
    return 0


def score_one(code: str, rank_map: pd.DataFrame) -> dict:
    m = get_metrics(code)
    time.sleep(0.15)

    # 行业排名信息
    rank_row = rank_map[rank_map["code"] == code]
    if not rank_row.empty:
        industry = str(rank_row["industry"].iloc[0])
        ind_rank = int(rank_row["ind_rank"].iloc[0])
        ind_total = int(rank_row["ind_total"].iloc[0])
        total_mv = float(rank_row["total_mv"].iloc[0])
        ind_top_mv = float(rank_row["ind_top_mv"].iloc[0])
    else:
        industry = ""
        ind_rank = None
        ind_total = None
        total_mv = None
        ind_top_mv = None

    business_score = score_business(m.gross_margin)
    roe_score = score_roe(m.roe)
    cash_score = score_cash_quality(m.ocf_to_profit)
    debt_score = score_debt(m.debt_ratio)
    stability_score = score_stability(m.profit_growth, m.revenue_growth)
    leader_score = score_leader(ind_rank, ind_total)

    total = business_score + roe_score + cash_score + debt_score + stability_score + leader_score

    roe_annual = ",".join(f"{v:.1f}" for v in m.roe.tolist()) if len(m.roe) else "—"
    gm_annual = ",".join(f"{v:.1f}" for v in m.gross_margin.tolist()) if len(m.gross_margin) else "—"
    profit_growth_annual = ",".join(f"{v:.1f}" for v in m.profit_growth.tolist()) if len(m.profit_growth) else "—"
    rev_growth_annual = ",".join(f"{v:.1f}" for v in m.revenue_growth.tolist()) if len(m.revenue_growth) else "—"

    gm_mean = round(float(m.gross_margin.mean()), 1) if len(m.gross_margin) else None
    roe_mean = round(float(m.roe.mean()), 1) if len(m.roe) else None
    ocf_mean = round(float(m.ocf_to_profit.mean()), 2) if len(m.ocf_to_profit) else None
    debt_latest = round(float(m.debt_ratio.iloc[-1]), 1) if len(m.debt_ratio) else None

    leader_ratio = safe_div(total_mv, ind_top_mv, default=None) if total_mv is not None else None

    data_years = max(
        len(m.roe),
        len(m.gross_margin.dropna()),
        len(m.debt_ratio),
        len(m.ocf_to_profit),
        len(m.profit_growth),
        len(m.revenue_growth),
    )

    return {
        "code": code,
        "name": "",
        "industry": industry,
        "total": total,
        "business_score": business_score,
        "roe_score": roe_score,
        "cash_score": cash_score,
        "debt_score": debt_score,
        "stability_score": stability_score,
        "leader_score": leader_score,
        "roe_mean": roe_mean,
        "roe_annual": roe_annual,
        "gross_mean": gm_mean,
        "gross_annual": gm_annual,
        "ocf_to_profit_mean": ocf_mean,
        "debt_latest": debt_latest,
        "profit_growth_annual": profit_growth_annual,
        "revenue_growth_annual": rev_growth_annual,
        "total_mv_yi": round(total_mv, 2) if total_mv is not None else None,
        "ind_rank": ind_rank,
        "ind_total": ind_total,
        "leader_ratio": round(leader_ratio, 4) if leader_ratio is not None else None,
        "data_years": data_years,
        "source": m.source,
        "note": m.note,
    }


# ---------------------------------------------------------------------------
# 股票池
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="段永平商业模式第一 A 股初筛器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="duan_screen_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    # 默认禁用系统代理
    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    codes = [c.zfill(6) for c in codes]

    print(f"股票池共 {len(codes)} 只，开始加载行业/市值映射与名称...")
    yjbb_meta = fetch_yjbb_meta()
    market_snapshot = pd.DataFrame()
    try:
        market_snapshot = fetch_market_snapshot_tx()
    except Exception as e:
        print(f"  腾讯全市场快照失败，行业排名将不可用: {e}", file=sys.stderr)

    rank_map = build_industry_rank_map(yjbb_meta, market_snapshot)
    name_map = dict(zip(yjbb_meta["code"].astype(str), yjbb_meta["name"].astype(str))) if not yjbb_meta.empty else {}

    print(f"映射加载完成（行业覆盖 {len(rank_map)} 只）。开始逐一打分（财务接口较慢，请耐心）...")
    print("注：ROIC 风格指标以 ROE 代理，低资本开支以经营现金流/净利润比代理。")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, rank_map)
            r["name"] = name_map.get(code, "")
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} 得分 {r['total']} | 行业: {r['industry'] or '—'} | 来源: {r['source']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("total", ascending=False)
    df["data_date"] = normalize_date(datetime.now().strftime("%Y%m%d"))
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "code", "name", "total", "business_score", "roe_score", "cash_score",
        "debt_score", "stability_score", "leader_score",
        "gross_mean", "roe_mean", "ocf_to_profit_mean", "debt_latest",
        "ind_rank", "ind_total", "data_years",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    display_df = df.head(args.top)[display_cols].copy()
    for c in ["gross_mean", "roe_mean", "ocf_to_profit_mean", "debt_latest"]:
        if c in display_df.columns:
            display_df[c] = display_df[c].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    for c in ["ind_rank", "ind_total"]:
        if c in display_df.columns:
            display_df[c] = display_df[c].apply(lambda x: f"{int(x)}" if pd.notna(x) else "—")
    print(display_df.to_string(index=False))

    incomplete = df[df["data_years"] < YEARS]
    if not incomplete.empty:
        print(f"\n注意: 以下 {len(incomplete)} 只股票财务数据未满 {YEARS} 年，分数基于部分年份，参考性下降：")
        print(", ".join(incomplete["code"].tolist()))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=75 商业模式优秀，进入企业文化与价格研究; 55-74 有亮点也有短板; <55 不符合框架。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
