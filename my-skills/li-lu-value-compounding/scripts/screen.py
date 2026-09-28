#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen.py — 李录价值复利 A 股打分器。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out result.csv

筛选逻辑（李录/喜马拉雅资本价值投资框架的机械化近似）:
    1. 资本回报质量：长期高 ROE，企业必须持续挣出远超资本成本回报。
    2. 复利趋势：近 2 年 ROE 相对前 3 年不下降，价值创造在加速或稳态。
    3. 再投资成长：利润再投入仍能推动两位数增长（李录重仓比亚迪式复利）。
    4. 盈利含金量：经营现金流/净利润，利润必须是真金白银。
    5. 安全边际：PE/PB 处于自身历史低分位，市场先生报出恐慌价。
    6. 财务纪律：低负债。
    打分排序输出 CSV，供进一步定性复核（能力圈与生意本质）。

数据源: akshare（东财财务指标/历史估值/利润表，失败自动降级）。
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


def get_financials(code: str) -> dict:
    """ROE / 净利润增速 / 负债率 / 现金流含金量，东财优先，新浪降级。"""
    errs = []
    try:
        df = fetch_financial_indicator(code)
        roe_col = _find_col(["净资产收益率(%)"], df)
        debt_col = _find_col(["资产负债率(%)"], df)
        ocf_col = _find_col(["经营现金净流量与净利润的比率(%)"], df)
        growth_col = _find_col(["净利润增长率(%)"], df)
        if roe_col is None:
            raise RuntimeError("财务指标表缺少 ROE 列")
        out = {
            "roe": _to_numeric_series(df[roe_col]).dropna(),
            "debt": _to_numeric_series(df[debt_col]).dropna() if debt_col is not None else pd.Series(dtype=float),
            "ocf": _to_numeric_series(df[ocf_col]).dropna() if ocf_col is not None else pd.Series(dtype=float),
            "profit_growth": _to_numeric_series(df[growth_col]).dropna() if growth_col is not None else pd.Series(dtype=float),
            "source": "akshare.stock_financial_analysis_indicator",
            "note": "",
        }
        if out["profit_growth"].empty:
            time.sleep(0.15)
            inc = fetch_sina_report(code, "利润表")
            if not inc.empty:
                profit_col = _find_col(["净利润"], inc)
                if profit_col is not None:
                    profit = _to_numeric_series(inc[profit_col]).dropna()
                    if len(profit) >= 2:
                        out["profit_growth"] = (profit.pct_change().dropna() * 100).dropna()
                        out["note"] = "净利润增速由新浪利润表补充"
        return out
    except Exception as e:
        errs.append(f"财务指标表: {e}")

    time.sleep(0.15)
    try:
        inc = fetch_sina_report(code, "利润表")
        bs = fetch_sina_report(code, "资产负债表")
        if inc.empty or bs.empty:
            raise RuntimeError("新浪三大报表不足以计算指标")
        profit_col = _find_col(["净利润"], inc)
        equity_col = _find_col(["所有者权益(或股东权益)合计"], bs)
        out = {"roe": pd.Series(dtype=float), "debt": pd.Series(dtype=float),
               "ocf": pd.Series(dtype=float), "profit_growth": pd.Series(dtype=float),
               "source": "akshare.stock_financial_report_sina（降级）", "note": ""}
        if profit_col is not None:
            profit = _to_numeric_series(inc[profit_col]).dropna()
            if len(profit) >= 2:
                out["profit_growth"] = (profit.pct_change().dropna() * 100).dropna()
            if equity_col is not None:
                equity = _to_numeric_series(bs[equity_col])
                out["roe"] = (profit / equity.replace(0, float("nan")) * 100).dropna()
        liab_col = _find_col(["负债合计"], bs)
        asset_col = _find_col(["资产总计"], bs)
        if liab_col is not None and asset_col is not None:
            out["debt"] = (_to_numeric_series(bs[liab_col]) / _to_numeric_series(bs[asset_col]).replace(0, float("nan")) * 100).dropna()
        out["note"] = "新浪三大报表降级计算"
        return out
    except Exception as e:
        errs.append(f"新浪三大报表: {e}")

    raise RuntimeError("; ".join(errs))


def get_valuation_percentile(code: str) -> dict:
    """东财个股历史估值表算 PE(TTM) 与 PB 的历史分位与当前值。失败抛异常。"""
    df = _retry_call(lambda: ak.stock_value_em(symbol=code))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("估值数据为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["数据日期"], df) or df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[df[date_col] <= pd.Timestamp.now()]
    pe_col = _find_col(["PE(TTM)"], df)
    pb_col = _find_col(["市净率", "PB"], df)
    pe = _to_numeric_series(df[pe_col]).dropna() if pe_col else pd.Series(dtype=float)
    pb = _to_numeric_series(df[pb_col]).dropna() if pb_col else pd.Series(dtype=float)
    cur_pe = float(pe.iloc[-1]) if not pe.empty else float("nan")
    cur_pb = float(pb.iloc[-1]) if not pb.empty else float("nan")
    pe_pct = (pe < cur_pe).mean() * 100 if not pe.empty and pd.notna(cur_pe) else float("nan")
    pb_pct = (pb < cur_pb).mean() * 100 if not pb.empty and pd.notna(cur_pb) else float("nan")
    return {"pe_ttm": cur_pe, "pb": cur_pb, "pe_percentile": pe_pct, "pb_percentile": pb_pct,
            "val_years": int(len(pb)) if not pb.empty else int(len(pe))}


# ---------------------------------------------------------------------------
# 打分（六维，满分 100）
# ---------------------------------------------------------------------------

def score_roe_quality(roe: pd.Series) -> tuple[int, float]:
    """资本回报质量（满分 25）：长期高 ROE 是价值创造的根基。"""
    s = roe.dropna()
    if s.empty:
        return 0, float("nan")
    v = float(s.mean())
    if v >= 20:
        return 25, v
    elif v >= 15:
        return 20, v
    elif v >= 12:
        return 15, v
    elif v >= 8:
        return 10, v
    elif v >= 5:
        return 5, v
    return 0, v


def score_roe_trend(roe: pd.Series) -> tuple[int, float]:
    """复利趋势（满分 15）：近 2 年均值 vs 前 3 年均值，价值创造不能失速。

    数据不足 4 年时给中性 7 分（次新上市）。
    """
    s = roe.dropna()
    if len(s) < 4:
        return 7, float("nan")
    recent = float(s.iloc[-2:].mean())
    prior = float(s.iloc[:-2].mean())
    diff = recent - prior
    if diff >= 2:
        return 15, diff
    elif diff >= 0:
        return 10, diff
    elif diff >= -3:
        return 6, diff
    return 0, diff


def score_reinvest_growth(profit_growth: pd.Series) -> tuple[int, float]:
    """再投资成长（满分 20）：利润再投入推动的持续增长。"""
    s = profit_growth.dropna()
    if s.empty:
        return 0, float("nan")
    v = float(s.mean())
    if v >= 25:
        return 20, v
    elif v >= 15:
        return 16, v
    elif v >= 10:
        return 12, v
    elif v >= 5:
        return 8, v
    elif v > 0:
        return 4, v
    return 0, v


def score_cash(ocf: pd.Series) -> int:
    """盈利含金量（满分 15）。"""
    s = ocf.dropna()
    if s.empty:
        return 0
    v = float(s.mean())
    if v >= 1.0:
        return 15
    elif v >= 0.8:
        return 11
    elif v >= 0.5:
        return 7
    elif v > 0:
        return 3
    return 0


def score_margin_of_safety(pe_pct: float, pb_pct: float, cur_pe: float, cur_pb: float) -> tuple[int, float]:
    """安全边际（满分 15）：PE/PB 处于自身历史低分位（市场先生恐慌时）。

    以 PB 分位为主锚（跨行业可比），PE 分位辅助；亏损股只看 PB。
    """
    if pd.isna(pb_pct):
        if pd.notna(cur_pe) and cur_pe > 0 and pd.notna(pe_pct) and pe_pct <= 20:
            return 8, float("nan")
        return 0, float("nan")
    if pb_pct <= 30 and (pd.isna(pe_pct) or pe_pct <= 60 or pd.isna(cur_pe) or cur_pe <= 0):
        return 15, pb_pct
    elif pb_pct <= 40:
        return 11, pb_pct
    elif pb_pct <= 60:
        return 7, pb_pct
    elif pb_pct <= 80:
        return 4, pb_pct
    return 0, pb_pct


def score_debt(debt: pd.Series) -> int:
    """财务纪律（满分 10）。"""
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


def score_one(code: str, meta: pd.DataFrame) -> dict:
    fin = get_financials(code)
    val = get_valuation_percentile(code)

    meta_row = meta[meta["code"] == code]
    name = str(meta_row["name"].iloc[0]) if not meta_row.empty and "name" in meta.columns else ""
    industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty and "industry" in meta.columns else ""

    roe_score, roe_mean = score_roe_quality(fin["roe"])
    trend_score, roe_diff = score_roe_trend(fin["roe"])
    growth_score, growth_mean = score_reinvest_growth(fin["profit_growth"])
    cash_score = score_cash(fin["ocf"])
    mos_score, pb_pct = score_margin_of_safety(val["pe_percentile"], val["pb_percentile"],
                                               val["pe_ttm"], val["pb"])
    debt_score = score_debt(fin["debt"])
    total = roe_score + trend_score + growth_score + cash_score + mos_score + debt_score

    return {
        "code": code,
        "name": name,
        "industry": industry,
        "total": total,
        "roe_quality_score": roe_score,
        "roe_trend_score": trend_score,
        "reinvest_growth_score": growth_score,
        "cash_score": cash_score,
        "margin_safety_score": mos_score,
        "debt_score": debt_score,
        "roe_mean": round(float(roe_mean), 1) if pd.notna(roe_mean) else None,
        "roe_trend_diff": round(float(roe_diff), 1) if pd.notna(roe_diff) else None,
        "profit_growth_mean": round(float(growth_mean), 1) if pd.notna(growth_mean) else None,
        "ocf_mean": round(float(fin["ocf"].mean()), 2) if len(fin["ocf"]) else None,
        "debt_latest": round(float(fin["debt"].iloc[-1]), 1) if len(fin["debt"]) else None,
        "pe_ttm": round(val["pe_ttm"], 2) if pd.notna(val["pe_ttm"]) else None,
        "pb": round(val["pb"], 2) if pd.notna(val["pb"]) else None,
        "pe_percentile": round(val["pe_percentile"], 1) if pd.notna(val["pe_percentile"]) else None,
        "pb_percentile": round(val["pb_percentile"], 1) if pd.notna(val["pb_percentile"]) else None,
        "val_years": val["val_years"],
        "data_years": max(len(fin["roe"]), len(fin["profit_growth"])),
        "fin_source": fin["source"],
        "note": fin.get("note", ""),
        "data_date": normalize_date(datetime.now().strftime("%Y%m%d")),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="李录价值复利 A 股打分器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="lilu_result.csv", help="CSV 输出路径")
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

    print("开始逐一打分（财务指标+历史估值两个接口，请耐心）...")
    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, meta)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} {r['name']} 得分 {r['total']} | ROE {r['roe_mean']}% | 增速 {r['profit_growth_mean']}% | PB分位 {r['pb_percentile']} | PE {r['pe_ttm']}")
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
        "code", "name", "total", "roe_quality_score", "roe_trend_score", "reinvest_growth_score",
        "margin_safety_score", "roe_mean", "profit_growth_mean", "pe_ttm", "pb_percentile", "data_years",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    print(df.head(args.top)[display_cols].to_string(index=False))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=75 价值复利候选; 55-74 观察; <55 不符合框架。")
    print("提醒: 高分不等于买入——能力圈之外的公司得分再高也应放弃。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
