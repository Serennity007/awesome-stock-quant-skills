#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen.py — 费雪《怎样选择成长股》A股成长质量打分器。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out fisher_result.csv
    python scripts/screen.py --codes 600519,300760,002415 --out fisher_result.csv

筛选逻辑（费雪 15 要点的机械化近似）:
    1. 成长跑道：近 5 年营收 CAGR（费雪:销售额增长是成长股第一特征）。
    2. 研发投入：研发费用率（闲聊法之外最可量化的"管理层判断"指标）。
    3. 利润率趋势：毛利率水平高且稳定或改善（利润率维持/改善）。
    4. 资本回报：连续 ROE（利润率+周转的综合验证）。
    5. 盈利含金量：经营现金流/净利润（利润是否为真）。
    6. 财务健康：低资产负债率（要点14:财务保守）。
    打分排序输出 CSV，供进一步"闲聊法"定性调研（15要点中的管理层、销售组织、客户评价）。

数据源: akshare（东财财务指标表优先，新浪利润表补充研发费用，失败自动降级）。
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
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理阻断东财/新浪直连。"""
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
    df = df.sort_values("报告日").tail(YEARS + 1)
    return df.reset_index(drop=True)


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
# 指标集合
# ---------------------------------------------------------------------------

class FisherMetrics:
    """一只股票近 YEARS 年的费雪风格指标集合。"""

    def __init__(self):
        self.roe: pd.Series = pd.Series(dtype=float)
        self.gross_margin: pd.Series = pd.Series(dtype=float)
        self.debt_ratio: pd.Series = pd.Series(dtype=float)
        self.ocf_to_profit: pd.Series = pd.Series(dtype=float)
        self.profit_growth: pd.Series = pd.Series(dtype=float)
        self.revenue: pd.Series = pd.Series(dtype=float)
        self.rd_ratio: pd.Series = pd.Series(dtype=float)
        self.source = ""
        self.note = ""


def _from_indicator(code: str) -> FisherMetrics:
    df = fetch_financial_indicator(code)
    m = FisherMetrics()
    m.source = "akshare.stock_financial_analysis_indicator"

    roe_col = _find_col(["净资产收益率(%)"], df)
    gm_col = _find_col(["销售毛利率(%)"], df)
    debt_col = _find_col(["资产负债率(%)"], df)
    ocf_profit_col = _find_col(["经营现金净流量与净利润的比率(%)"], df)
    profit_growth_col = _find_col(["净利润增长率(%)"], df)

    if roe_col is None or gm_col is None:
        raise RuntimeError("主要财务指标缺少必要列")

    m.roe = _to_numeric_series(df[roe_col]).dropna()
    m.gross_margin = _to_numeric_series(df[gm_col]).dropna()
    if debt_col is not None:
        m.debt_ratio = _to_numeric_series(df[debt_col]).dropna()
    if ocf_profit_col is not None:
        m.ocf_to_profit = _to_numeric_series(df[ocf_profit_col]).dropna()
    if profit_growth_col is not None:
        m.profit_growth = _to_numeric_series(df[profit_growth_col]).dropna()
    m.note = ""
    return m


def _enrich_from_sina_income(m: FisherMetrics, code: str):
    """新浪利润表补充：研发费用率、营收序列（CAGR 用）。"""
    inc = fetch_sina_report(code, "利润表")
    if inc.empty:
        return
    rev_col = _find_col(["营业收入"], inc)
    if rev_col is not None:
        m.revenue = _to_numeric_series(inc[rev_col]).dropna()
        # 毛利率缺失时补充
        if m.gross_margin.dropna().empty:
            cost_col = _find_col(["营业成本"], inc)
            if cost_col is not None:
                rev = _to_numeric_series(inc[rev_col])
                cost = _to_numeric_series(inc[cost_col])
                m.gross_margin = ((rev - cost) / rev.replace(0, float("nan")) * 100).dropna()
    rd_col = _find_col(["研发费用"], inc)
    if rd_col is not None and rev_col is not None:
        rd = _to_numeric_series(inc[rd_col])
        rev = _to_numeric_series(inc[rev_col])
        rd_ratio = (rd / rev.replace(0, float("nan")) * 100).dropna()
        m.rd_ratio = rd_ratio
        if m.note:
            m.note += "；"
        m.note += "研发费用率来自新浪利润表"


def get_metrics(code: str) -> FisherMetrics:
    errs = []
    try:
        m = _from_indicator(code)
        _enrich_from_sina_income(m, code)
        return m
    except Exception as e:
        errs.append(f"财务指标表: {e}")
    time.sleep(0.15)

    # 整体降级：仅用新浪利润表拼出可用指标
    try:
        inc = fetch_sina_report(code, "利润表")
        bs = fetch_sina_report(code, "资产负债表")
        cf = fetch_sina_report(code, "现金流量表")
        if inc.empty or bs.empty:
            raise RuntimeError("新浪三大报表不足以计算指标")
        m = FisherMetrics()
        m.source = "akshare.stock_financial_report_sina（降级）"
        rev_col = _find_col(["营业收入"], inc)
        profit_col = _find_col(["净利润"], inc)
        equity_col = _find_col(["所有者权益(或股东权益)合计"], bs)
        cost_col = _find_col(["营业成本"], inc)
        if rev_col is not None:
            m.revenue = _to_numeric_series(inc[rev_col]).dropna()
            if cost_col is not None:
                rev = _to_numeric_series(inc[rev_col])
                cost = _to_numeric_series(inc[cost_col])
                m.gross_margin = ((rev - cost) / rev.replace(0, float("nan")) * 100).dropna()
        if profit_col is not None:
            profit = _to_numeric_series(inc[profit_col]).dropna()
            if len(profit) >= 2:
                m.profit_growth = (profit.pct_change().dropna() * 100).dropna()
            if equity_col is not None:
                equity = _to_numeric_series(bs[equity_col])
                m.roe = (profit / equity.replace(0, float("nan")) * 100).dropna()
        liab_col = _find_col(["负债合计"], bs)
        asset_col = _find_col(["资产总计"], bs)
        if liab_col is not None and asset_col is not None:
            m.debt_ratio = (_to_numeric_series(bs[liab_col]) / _to_numeric_series(bs[asset_col]).replace(0, float("nan")) * 100).dropna()
        if not cf.empty and profit_col is not None:
            ocf_col = _find_col(["经营活动产生的现金流量净额"], cf)
            if ocf_col is not None:
                cf["_rd"] = cf["报告日"].astype(str)
                inc["_rd"] = inc["报告日"].astype(str)
                merged = pd.merge(cf[["_rd", ocf_col]], inc[["_rd", profit_col]], on="_rd", how="inner")
                if not merged.empty:
                    m.ocf_to_profit = (_to_numeric_series(merged[ocf_col]) / _to_numeric_series(merged[profit_col]).replace(0, float("nan"))).dropna()
        rd_col = _find_col(["研发费用"], inc)
        if rd_col is not None and rev_col is not None:
            m.rd_ratio = (_to_numeric_series(inc[rd_col]) / _to_numeric_series(inc[rev_col]).replace(0, float("nan")) * 100).dropna()
        m.note = "新浪三大报表降级计算"
        return m
    except Exception as e:
        errs.append(f"新浪三大报表: {e}")

    raise RuntimeError("; ".join(errs))


# ---------------------------------------------------------------------------
# 打分
# ---------------------------------------------------------------------------

def _cagr(series: pd.Series, years: int = 5) -> float:
    """由最早与最新值计算 CAGR（%）。数据不足返回 nan。"""
    s = series.dropna()
    if len(s) < 2 or float(s.iloc[0]) <= 0:
        return float("nan")
    n = len(s) - 1
    try:
        return (float(s.iloc[-1]) / float(s.iloc[0])) ** (1.0 / n) * 100 - 100
    except Exception:
        return float("nan")


def score_growth(m: FisherMetrics) -> tuple[int, dict]:
    """成长跑道：营收 CAGR 为主，净利润增速为辅（满分 25）。"""
    rev_cagr = _cagr(m.revenue, YEARS)
    s = m.profit_growth.dropna()
    pos_years = int((s > 0).sum()) if not s.empty else 0

    score = 0
    if pd.notna(rev_cagr):
        if rev_cagr >= 25:
            score += 18
        elif rev_cagr >= 15:
            score += 14
        elif rev_cagr >= 10:
            score += 10
        elif rev_cagr >= 5:
            score += 6
        elif rev_cagr > 0:
            score += 3
    elif not s.empty:
        mean_g = s.mean()
        if mean_g >= 25:
            score += 18
        elif mean_g >= 15:
            score += 14
        elif mean_g >= 10:
            score += 10
        elif mean_g >= 5:
            score += 6
        elif mean_g > 0:
            score += 3

    # 利润同步增长加分（费雪:利润率应伴随销售增长）
    if not s.empty and pos_years >= 4:
        score += 7
    elif not s.empty and pos_years >= 3:
        score += 4
    return min(score, 25), {"rev_cagr": rev_cagr, "profit_pos_years": pos_years}


def score_rd(rd_ratio: pd.Series) -> tuple[int, str]:
    """研发投入（满分 20）。数据完全缺失（金融等）给中性分 5。"""
    rd = rd_ratio.dropna()
    if rd.empty:
        return 5, "研发费用数据缺失（金融/部分行业常见），给中性分"
    avg_rd = float(rd.mean())
    if avg_rd >= 8:
        return 20, ""
    elif avg_rd >= 5:
        return 16, ""
    elif avg_rd >= 3:
        return 11, ""
    elif avg_rd >= 1.5:
        return 7, ""
    elif avg_rd >= 0.5:
        return 3, ""
    return 1, ""


def score_margin(gross_margin: pd.Series) -> int:
    """利润率水平与趋势（满分 15）：高毛利加分，最新值高于均值为改善。"""
    s = gross_margin.dropna()
    if s.empty:
        return 0
    mean_v = float(s.mean())
    score = 0
    if mean_v >= 40:
        score += 8
    elif mean_v >= 30:
        score += 6
    elif mean_v >= 20:
        score += 4
    elif mean_v >= 10:
        score += 2
    if len(s) >= 2:
        latest = float(s.iloc[-1])
        if latest > mean_v + 1:
            score += 7
        elif abs(latest - mean_v) <= 2:
            score += 4
    return min(score, 15)


def score_roe(roe: pd.Series) -> int:
    """资本回报（满分 15）。"""
    s = roe.dropna()
    if s.empty:
        return 0
    mean_v = s.mean()
    if mean_v >= 20:
        return 15
    elif mean_v >= 15:
        return 12
    elif mean_v >= 12:
        return 9
    elif mean_v >= 8:
        return 5
    elif mean_v >= 5:
        return 2
    return 0


def score_cash(ocf_to_profit: pd.Series) -> int:
    """盈利含金量（满分 15）。"""
    s = ocf_to_profit.dropna()
    if s.empty:
        return 0
    mean_v = s.mean()
    if mean_v >= 1.2:
        return 15
    elif mean_v >= 1.0:
        return 12
    elif mean_v >= 0.8:
        return 8
    elif mean_v >= 0.6:
        return 5
    elif mean_v >= 0.4:
        return 2
    return 0


def score_debt(debt_ratio: pd.Series) -> int:
    """财务保守（满分 10）。"""
    s = debt_ratio.dropna()
    if s.empty:
        return 0
    latest = s.iloc[-1]
    if latest < 30:
        return 10
    elif latest < 45:
        return 7
    elif latest < 60:
        return 4
    return 0


def score_one(code: str, meta: pd.DataFrame) -> dict:
    m = get_metrics(code)
    time.sleep(0.15)

    meta_row = meta[meta["code"] == code]
    name = str(meta_row["name"].iloc[0]) if not meta_row.empty and "name" in meta.columns else ""
    industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty and "industry" in meta.columns else ""

    growth_score, growth_info = score_growth(m)
    rd_score, rd_note = score_rd(m.rd_ratio)
    margin_score = score_margin(m.gross_margin)
    roe_score = score_roe(m.roe)
    cash_score = score_cash(m.ocf_to_profit)
    debt_score = score_debt(m.debt_ratio)
    total = growth_score + rd_score + margin_score + roe_score + cash_score + debt_score

    profit_growth_annual = ",".join(f"{v:.1f}" for v in m.profit_growth.tolist()) if len(m.profit_growth) else "—"
    gm_annual = ",".join(f"{v:.1f}" for v in m.gross_margin.tolist()) if len(m.gross_margin) else "—"
    rd_annual = ",".join(f"{v:.2f}" for v in m.rd_ratio.tolist()) if len(m.rd_ratio) else "—"

    data_years = max(
        len(m.roe), len(m.gross_margin.dropna()), len(m.revenue.dropna()),
        len(m.profit_growth), len(m.rd_ratio.dropna()),
    )

    return {
        "code": code,
        "name": name,
        "industry": industry,
        "total": total,
        "growth_score": growth_score,
        "rd_score": rd_score,
        "margin_score": margin_score,
        "roe_score": roe_score,
        "cash_score": cash_score,
        "debt_score": debt_score,
        "rev_cagr": round(growth_info["rev_cagr"], 1) if pd.notna(growth_info["rev_cagr"]) else None,
        "profit_pos_years": growth_info["profit_pos_years"],
        "profit_growth_annual": profit_growth_annual,
        "rd_ratio_avg": round(float(m.rd_ratio.mean()), 2) if len(m.rd_ratio.dropna()) else None,
        "rd_annual": rd_annual,
        "gross_mean": round(float(m.gross_margin.mean()), 1) if len(m.gross_margin) else None,
        "gross_annual": gm_annual,
        "roe_mean": round(float(m.roe.mean()), 1) if len(m.roe) else None,
        "ocf_to_profit_mean": round(float(m.ocf_to_profit.mean()), 2) if len(m.ocf_to_profit) else None,
        "debt_latest": round(float(m.debt_ratio.iloc[-1]), 1) if len(m.debt_ratio) else None,
        "data_years": data_years,
        "source": m.source,
        "note": (rd_note + ("；" + m.note if m.note else "")).strip("；"),
        "data_date": normalize_date(datetime.now().strftime("%Y%m%d")),
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
    ap = argparse.ArgumentParser(description="费雪成长股 A 股打分器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="fisher_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    codes = [c.zfill(6) for c in codes]

    print(f"股票池共 {len(codes)} 只，加载名称/行业映射...")
    meta = fetch_industry_map()

    print("开始逐一打分（新浪利润表补充研发费用率，财务接口较慢，请耐心）...")
    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, meta)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} {r['name']} 得分 {r['total']} | 研发率 {r['rd_ratio_avg']} | 来源: {r['source']}")
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
        "code", "name", "total", "growth_score", "rd_score", "margin_score",
        "roe_score", "cash_score", "debt_score", "rev_cagr", "rd_ratio_avg",
        "gross_mean", "roe_mean", "data_years",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    print(df.head(args.top)[display_cols].to_string(index=False))

    incomplete = df[df["data_years"] < YEARS]
    if not incomplete.empty:
        print(f"\n注意: {len(incomplete)} 只股票财务数据未满 {YEARS} 年，分数基于部分年份。")

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=75 费雪式成长股候选，进入闲聊法定性调研; 55-74 有亮点也有短板; <55 不符合框架。")
    print("提醒: 研发费用率给金融/部分行业中性分 5，纵向对比请在同行业内进行。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
