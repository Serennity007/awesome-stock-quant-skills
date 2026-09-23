#!/usr/bin/env python3
"""screen.py — 查理·芒格优质企业投资法 A 股初筛。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out result.csv

筛选维度（芒格质量风格）:
    1. 连续 5 年高 ROIC 风格指标：优先使用“投入资本回报率”口径；akshare 公开接口未直接提供
       该字段时，以 ROE（净资产收益率）代理，并在输出中明确标注。
    2. 低负债：资产负债率。
    3. 高且稳定毛利率。
    4. 盈利质量：经营现金流 / 净利润比。
    5. 少股本稀释：近 5 年“实收资本(或股本)”增长幅度。

数据源: akshare（优先东方财富/新浪财务接口，东财失败自动降级新浪三大报表）。
"""
import os

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import argparse
import re
import sys
import time
from typing import Optional

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
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理干扰同花顺/东财直连。"""
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
        for cand in candidates:
            if cand in str(c):
                return c
    return None


def _find_shares_col(df: pd.DataFrame) -> Optional[str]:
    """查找总股本列（银行/金融企业列名常为“股本”，一般企业为“实收资本(或股本)”）。"""
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
    """获取主要财务指标（年报），失败抛异常。过滤掉未来日期。"""
    start_year = pd.Timestamp.now().year - YEARS - 2
    df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=str(start_year)))
    if df is None or df.empty:
        raise RuntimeError("财务指标为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df) or df.columns[0]
    df[date_col] = df[date_col].astype(str).apply(normalize_date)
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    df = df[(df[date_col].str.endswith("12-31")) & (df[date_col] <= today)]
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
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["报告日"] = df["报告日"].astype(str).str.replace("-", "")
    today = pd.Timestamp.now().strftime("%Y%m%d")
    df = df[(df["报告日"].str.endswith("1231")) & (df["报告日"] <= today)]
    df = df.sort_values("报告日").tail(YEARS)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 指标抽取（优先财务指标表，失败降级新浪报表）
# ---------------------------------------------------------------------------

class Metrics:
    """一只股票近 YEARS 年的质量指标集合。"""

    def __init__(self):
        self.roic_like: pd.Series = pd.Series(dtype=float)   # ROIC 风格指标（ROE 代理时已在 note 说明）
        self.gross_margin: pd.Series = pd.Series(dtype=float)
        self.debt_ratio: pd.Series = pd.Series(dtype=float)
        self.ocf_to_profit: pd.Series = pd.Series(dtype=float)
        self.shares: pd.Series = pd.Series(dtype=float)
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

    if roe_col is None or gm_col is None or debt_col is None:
        raise RuntimeError("主要财务指标缺少必要列")

    m.roic_like = _to_numeric_series(df[roe_col]).dropna()
    m.gross_margin = _to_numeric_series(df[gm_col]).dropna()
    m.debt_ratio = _to_numeric_series(df[debt_col]).dropna()
    if ocf_profit_col is not None:
        m.ocf_to_profit = _to_numeric_series(df[ocf_profit_col]).dropna()

    # 股本稀释：从财务指标表尝试“每股净资产_调整后(元)” + “净资产(?)” 反推，
    # 但该表没有总股本。这里仅做占位，具体股本从 balance sheet 补充。
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

    # 股本
    shares_col = _find_shares_col(bs)
    if shares_col is not None:
        m.shares = _to_numeric_series(bs[shares_col]).dropna()

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
        m.roic_like = (profit / equity.replace(0, float("nan")) * 100).dropna()

    # 盈利质量 = 经营现金流净额 / 净利润
    if not cf.empty:
        ocf_col = _find_col(["经营活动产生的现金流量净额"], cf)
        if ocf_col is not None and profit_col is not None:
            # 对齐三张表的报告期
            ocf = _to_numeric_series(cf[ocf_col])
            cf["_rd"] = cf["报告日"].astype(str)
            inc["_rd"] = inc["报告日"].astype(str)
            merged = pd.merge(cf[["_rd", ocf_col]], inc[["_rd", profit_col]], on="_rd", how="inner")
            if not merged.empty:
                ocf_vals = _to_numeric_series(merged[ocf_col])
                profit_vals = _to_numeric_series(merged[profit_col])
                m.ocf_to_profit = (ocf_vals / profit_vals.replace(0, float("nan"))).dropna()

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
    """获取一只股票的质量指标，优先财务指标表，失败降级新浪报表。"""
    errs = []
    try:
        m = _from_indicator(code)
        # 毛利率在财务指标表中经常缺失，用利润表补充
        _fill_gross_margin_from_income(m, code)
        # 股本稀释必须依赖资产负债表，补充抓取
        bs = fetch_sina_report(code, "资产负债表")
        shares_col = _find_shares_col(bs) if not bs.empty else None
        if shares_col is not None:
            m.shares = _to_numeric_series(bs[shares_col]).dropna()
        return m
    except Exception as e:
        errs.append(f"财务指标表: {e}")
    time.sleep(0.15)

    try:
        m = _from_sina(code)
        return m
    except Exception as e:
        errs.append(f"新浪三大报表: {e}")

    raise RuntimeError("; ".join(errs))


# ---------------------------------------------------------------------------
# 打分
# ---------------------------------------------------------------------------

def score_roic(s: pd.Series) -> int:
    if s.empty:
        return 0
    total = 0
    for v in s:
        if pd.isna(v):
            continue
        if v > 20:
            total += 5
        elif v > 15:
            total += 3
        elif v > 10:
            total += 1
    return min(total, 25)


def score_gross_margin(s: pd.Series) -> int:
    if s.empty:
        return 0
    mean_v = s.mean()
    score = 0
    if mean_v > 40:
        score += 15
    elif mean_v > 30:
        score += 10
    elif mean_v > 20:
        score += 5

    spread = s.max() - s.min()
    if spread < 3:
        score += 10
    elif spread < 5:
        score += 7
    elif spread < 10:
        score += 3
    return min(score, 25)


def score_debt(s: pd.Series) -> int:
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


def score_quality(s: pd.Series) -> int:
    if s.empty:
        return 0
    mean_v = s.mean()
    if mean_v > 1.0:
        return 20
    elif mean_v > 0.8:
        return 15
    elif mean_v > 0.6:
        return 10
    elif mean_v > 0.4:
        return 5
    return 0


def score_dilution(s: pd.Series) -> int:
    """近 5 年股本增长越小得分越高。"""
    if s.empty or len(s) < 2:
        return 0
    first, last = s.iloc[0], s.iloc[-1]
    if pd.isna(first) or pd.isna(last) or first <= 0:
        return 0
    growth = (last - first) / first
    if growth < 0.05:
        return 15
    elif growth < 0.20:
        return 10
    elif growth < 0.50:
        return 5
    return 0


def score_one(code: str) -> dict:
    m = get_metrics(code)
    time.sleep(0.15)

    roic_score = score_roic(m.roic_like)
    gm_score = score_gross_margin(m.gross_margin)
    debt_score = score_debt(m.debt_ratio)
    quality_score = score_quality(m.ocf_to_profit)
    dilution_score = score_dilution(m.shares)

    total = roic_score + gm_score + debt_score + quality_score + dilution_score

    roic_annual = ",".join(f"{v:.1f}" for v in m.roic_like.tolist()) if len(m.roic_like) else "—"
    gm_annual = ",".join(f"{v:.1f}" for v in m.gross_margin.tolist()) if len(m.gross_margin) else "—"
    debt_latest = round(float(m.debt_ratio.iloc[-1]), 1) if len(m.debt_ratio) else None
    gm_mean = round(float(m.gross_margin.mean()), 1) if len(m.gross_margin) else None
    quality_mean = round(float(m.ocf_to_profit.mean()), 2) if len(m.ocf_to_profit) else None

    shares_growth = None
    if len(m.shares) >= 2:
        shares_growth = round(float((m.shares.iloc[-1] - m.shares.iloc[0]) / m.shares.iloc[0] * 100), 1)

    data_years = max(
        len(m.roic_like),
        len(m.gross_margin.dropna()),
        len(m.debt_ratio),
        len(m.ocf_to_profit),
        len(m.shares),
    )

    return {
        "code": code,
        "total": total,
        "roic_score": roic_score,
        "roic_annual": roic_annual,
        "gross_score": gm_score,
        "gross_mean": gm_mean,
        "gross_annual": gm_annual,
        "debt_score": debt_score,
        "debt_latest": debt_latest,
        "quality_score": quality_score,
        "quality_mean": quality_mean,
        "dilution_score": dilution_score,
        "shares_growth_pct": shares_growth,
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
            col = _find_col(["成分券代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"csindex: {e}")

        time.sleep(0.15)
        try:
            df = _retry_call(lambda: ak.index_stock_cons_weight_csindex(symbol="000300"))
            col = _find_col(["成分券代码"], df) or _find_col(["股票代码"], df)
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
    ap = argparse.ArgumentParser(description="查理·芒格优质企业投资法 A 股初筛")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="munger_screen_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    # 默认禁用系统代理
    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    print(f"股票池共 {len(codes)} 只，开始逐一打分（财务接口较慢，请耐心）...")
    print("注：ROIC 风格指标以 ROE 代理，因为 akshare 公开接口未直接提供 ROIC。")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} 得分 {r['total']} | 来源: {r['source']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("total", ascending=False)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = ["code", "total", "roic_score", "gross_score", "debt_score",
                    "quality_score", "dilution_score", "gross_mean", "debt_latest",
                    "quality_mean", "shares_growth_pct", "data_years"]
    display_df = df.head(args.top)[display_cols].copy()
    for c in ["gross_mean", "debt_latest", "quality_mean", "shares_growth_pct"]:
        display_df[c] = display_df[c].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    print(display_df.to_string(index=False))

    incomplete = df[df["data_years"] < YEARS]
    if not incomplete.empty:
        print(f"\n注意: 以下 {len(incomplete)} 只股票财务数据未满 {YEARS} 年，分数基于部分年份，参考性下降：")
        print(", ".join(incomplete["code"].tolist()))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=75 进入人工护城河与管理层核查; 55-74 有短板; <55 不符合框架。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
