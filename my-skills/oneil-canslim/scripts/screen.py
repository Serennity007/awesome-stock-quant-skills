#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""screen.py — 威廉·欧奈尔 CANSLIM 七要素 A 股打分器。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,300760,002415 --out result.csv

筛选逻辑（欧奈尔《笑傲股市》CANSLIM 的 A 股机械化近似）:
    C  最新季度净利润同比 >= 25%（当季收益加速）
    A  近 3 年年度净利润增速 >= 25%（年度增长）
    N  收盘价距 250 日新高 <= 15%（新产品/新高的价格形态）
    S  近 5 日均量 / 60 日均量 >= 1.2（供需：放量）
    L  120 日涨幅相对沪深300超额 >= 15pp（领导者；池内附带 RPS 百分位）
    I  机构持股比例（无数据时给中性分，注明）
    M  沪深300 收盘价在 50 日均线上（市场方向，全池一致）
    权重 C20/A15/N15/S10/L20/I10/M10，满分 100。

数据源: akshare（新浪个股日线 qfq + 东财业绩报表 + 东财机构持股 +
新浪指数日线，东财日线不通时全链路可走新浪降级）。
"""
import os
import sys
import time
import argparse
from datetime import datetime

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

YEARS = 3


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理阻断数据源直连。"""
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(k, None)


def _retry_call(func, max_retries: int = 3, sleep_base: float = 1.5):
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


def _find_col(candidates: list, df: pd.DataFrame):
    for c in df.columns:
        cs = str(c)
        for cand in candidates:
            if cand in cs:
                return c
    return None


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


# ---------------------------------------------------------------------------
# 池级数据：业绩报表（C 维度+元信息）、机构持股（I 维度）、大盘（M 维度）
# ---------------------------------------------------------------------------

def _quarter_ends(max_n: int = 8) -> list:
    """从最近的季度末往前生成候选报告期，如 20260930 > 20260630 > ..."""
    today = datetime.now()
    out = []
    y = today.year
    while len(out) < max_n:
        for qm in (12, 9, 6, 3):
            d = f"{y}{qm:02d}{ {12:31, 9:30, 6:30, 3:31}[qm] }"
            if f"{y}{qm:02d}" <= today.strftime("%Y%m"):
                out.append(d)
        y -= 1
    return out


def fetch_latest_yjbb() -> tuple:
    """最新已发布的业绩报表，返回 (DataFrame, 报告期字符串)。"""
    errs = []
    for date in _quarter_ends(8):
        try:
            df = _retry_call(lambda d=date: ak.stock_yjbb_em(date=d))
            time.sleep(0.2)
        except Exception as e:
            errs.append(f"{date}: {e}")
            continue
        if df is None or df.empty:
            continue
        code_col = _find_col(["股票代码"], df)
        yoy_col = _find_col(["净利润-同比增长"], df) or _find_col(["净利润同比增长"], df)
        if code_col and yoy_col:
            df = df.copy()
            df["code"] = df[code_col].astype(str).str.strip().str.zfill(6)
            df[yoy_col] = _to_num(df[yoy_col])
            keep = {"code": df["code"].values,
                    "quarter_yoy": df[yoy_col].values}
            for cand, alias in [("股票简称", "name"), ("所处行业", "industry")]:
                c = _find_col([cand], df)
                if c:
                    keep[alias] = df[c].astype(str).values
            return pd.DataFrame(keep), date
    raise RuntimeError(f"业绩报表获取失败: {'; '.join(errs[:3])}")


def fetch_inst_hold() -> tuple:
    """最新可用的机构持股表，返回 (DataFrame, 报告期字符串)；无数据返回 (None, '')。"""
    now = datetime.now()
    for y in range(now.year, now.year - 3, -1):
        for q in (4, 3, 2, 1):
            sym = f"{y}{q}"
            try:
                df = _retry_call(lambda s=sym: ak.stock_institute_hold(symbol=s))
                time.sleep(0.2)
            except Exception:
                continue
            if df is None or df.empty:
                continue
            code_col = _find_col(["证券代码"], df)
            ratio_col = _find_col(["持股比例"], df)
            if not code_col or not ratio_col:
                continue
            # 优先"占流通股比例"，缺失则用"持股比例"
            free_col = _find_col(["占流通股比例"], df)
            use_col = free_col if free_col else ratio_col
            df = df.copy()
            df["code"] = df[code_col].astype(str).str.strip().str.zfill(6)
            df["inst_ratio"] = _to_num(df[use_col])
            out = df[["code", "inst_ratio"]].dropna().drop_duplicates("code")
            if not out.empty:
                return out, sym
    return None, ""


def fetch_market_trend() -> dict:
    """沪深300 收盘价与 50 日均线的相对位置（M 维度）。"""
    df = _retry_call(lambda: ak.stock_zh_index_daily(symbol="sh000300"))
    time.sleep(0.2)
    if df is None or df.empty:
        raise RuntimeError("沪深300行情为空")
    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    ma50 = df["close"].rolling(50).mean().iloc[-1]
    close = float(df["close"].iloc[-1])
    return {"close": close, "ma50": float(ma50), "above": close > ma50}


# ---------------------------------------------------------------------------
# 个股数据
# ---------------------------------------------------------------------------

def fetch_daily_sina(code: str, days: int = 420) -> pd.DataFrame:
    """新浪个股日线（前复权，供新高/量能/动量计算），失败抛异常。"""
    start = (datetime.now() - pd.Timedelta(days=days)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    prefix = "sh" if code.startswith("6") else ("bj" if code.startswith(("4", "8")) else "sz")
    try:
        df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=f"{prefix}{code}",
                                                     start_date=start, end_date=end,
                                                     adjust="qfq"))
        time.sleep(0.15)
    except Exception:
        # 未复权降级
        df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=f"{prefix}{code}",
                                                     start_date=start, end_date=end))
        time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("日线数据为空")
    df = df.copy()
    for col in ("close", "high", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)


def fetch_annual_growth(code: str) -> tuple:
    """近 YEARS 年年度净利润增速列表（东财财务指标，降级新浪利润表）。返回 (Series, source)"""
    start_year = datetime.now().year - YEARS - 2
    try:
        df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=str(start_year)))
        time.sleep(0.15)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            date_col = _find_col(["日期"], df) or df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col].astype(str).str.replace("-", "", regex=False),
                                          format="%Y%m%d", errors="coerce")
            df = df[(df[date_col].dt.month == 12) & (df[date_col] <= pd.Timestamp.now())]
            df = df.sort_values(date_col).tail(YEARS)
            g_col = _find_col(["净利润增长率(%)"], df)
            if g_col is not None and not df.empty:
                s = _to_num(df[g_col]).dropna()
                if not s.empty:
                    return s, "akshare.stock_financial_analysis_indicator"
    except Exception:
        pass
    # 新浪利润表降级
    try:
        inc = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol="利润表"))
        time.sleep(0.15)
    except Exception:
        return pd.Series(dtype=float), ""
    if inc is None or inc.empty or "报告日" not in inc.columns:
        return pd.Series(dtype=float), ""
    inc = inc.copy()
    inc["报告日"] = inc["报告日"].astype(str).str.replace("-", "")
    inc = inc[(inc["报告日"].str.endswith("1231")) & (inc["报告日"] <= datetime.now().strftime("%Y%m%d"))]
    inc = inc.sort_values("报告日").tail(YEARS + 1)
    p_col = _find_col(["净利润"], inc)
    if p_col is None:
        return pd.Series(dtype=float), ""
    profit = _to_num(inc[p_col]).dropna()
    if len(profit) < 2:
        return pd.Series(dtype=float), ""
    return (profit.pct_change().dropna() * 100).dropna(), "akshare.stock_financial_report_sina（降级）"


# ---------------------------------------------------------------------------
# 打分（七要素，满分 100）
# ---------------------------------------------------------------------------

def score_c(quarter_yoy) -> tuple[int, float]:
    """C 当季收益（满分 20）：最新季度净利润同比。"""
    if quarter_yoy is None or pd.isna(quarter_yoy):
        return 0, float("nan")
    v = float(quarter_yoy)
    if v >= 25:
        return 20, v
    elif v >= 10:
        return 12, v
    elif v > 0:
        return 6, v
    return 0, v


def score_a(annual_growth: pd.Series) -> tuple[int, float]:
    """A 年度增长（满分 15）：近 3 年净利润增速均值。"""
    s = annual_growth.dropna()
    if s.empty:
        return 0, float("nan")
    v = float(s.mean())
    if v >= 25:
        return 15, v
    elif v >= 10:
        return 10, v
    elif v > 0:
        return 5, v
    return 0, v


def score_n(daily: pd.DataFrame, near_pct: float = 15) -> tuple[int, float]:
    """N 新高（满分 15）：收盘价距 250 日最高收盘的回撤幅度。"""
    close = float(daily["close"].iloc[-1])
    high_250 = float(daily["close"].tail(250).max())
    dist = (close / high_250 - 1) * 100
    if dist >= -near_pct:
        return 15, dist
    elif dist >= -30:
        return 8, dist
    return 0, dist


def score_s(daily: pd.DataFrame) -> tuple[int, float]:
    """S 供需（满分 10）：近 5 日均量 / 60 日均量。"""
    if "volume" not in daily.columns or daily["volume"].dropna().empty:
        return 0, float("nan")
    v5 = float(daily["volume"].tail(5).mean())
    v60 = float(daily["volume"].tail(60).mean())
    ratio = v5 / v60 if v60 and v60 > 0 else float("nan")
    if pd.isna(ratio):
        return 0, float("nan")
    if ratio >= 1.5:
        return 10, ratio
    elif ratio >= 1.2:
        return 7, ratio
    elif ratio >= 1.0:
        return 4, ratio
    return 0, ratio


def score_l(daily: pd.DataFrame, bench_ret: float) -> tuple[int, float]:
    """L 领导者（满分 20）：120 日涨幅相对沪深300的超额收益（pp）。"""
    if len(daily) < 120:
        return 0, float("nan")
    ret = (float(daily["close"].iloc[-1]) / float(daily["close"].iloc[-120]) - 1) * 100
    excess = ret - bench_ret if pd.notna(bench_ret) else float("nan")
    if pd.isna(excess):
        return 0, float("nan")
    if excess >= 30:
        return 20, excess
    elif excess >= 15:
        return 15, excess
    elif excess >= 5:
        return 10, excess
    elif excess >= 0:
        return 5, excess
    return 0, excess


def score_i(inst_ratio) -> tuple[int, float, str]:
    """I 机构认可（满分 10）：机构（基金）持股占流通股比例；无数据给中性 5 分。"""
    if inst_ratio is None or pd.isna(inst_ratio):
        return 5, float("nan"), "机构持股无数据，给中性分(5/10)"
    v = float(inst_ratio)
    if v >= 10:
        return 10, v, ""
    elif v >= 5:
        return 7, v, ""
    elif v >= 2:
        return 4, v, ""
    elif v > 0:
        return 2, v, ""
    return 0, v, ""


def score_m(market: dict) -> int:
    """M 市场方向（满分 10）：沪深300 在 50 日均线上方。"""
    return 10 if market.get("above") else 0


def score_one(code: str, yjbb: pd.DataFrame, inst: pd.DataFrame,
              bench_ret: float, market: dict) -> dict:
    daily = fetch_daily_sina(code)
    annual_growth, a_source = fetch_annual_growth(code)

    yoy = float("nan")
    if not yjbb.empty:
        row = yjbb[yjbb["code"] == code]
        if not row.empty:
            yoy = float(row["quarter_yoy"].iloc[0])
    c_score, c_yoy = score_c(yoy)
    a_score, a_mean = score_a(annual_growth)
    n_score, n_dist = score_n(daily)
    s_score, s_ratio = score_s(daily)
    l_score, l_excess = score_l(daily, bench_ret)
    inst_ratio = float("nan")
    if inst is not None and not inst.empty:
        row = inst[inst["code"] == code]
        if not row.empty:
            inst_ratio = float(row["inst_ratio"].iloc[0])
    i_score, i_val, i_note = score_i(inst_ratio)
    m_score = score_m(market)
    total = c_score + a_score + n_score + s_score + l_score + i_score + m_score

    passed = [ltr for ltr, sc in [("C", c_score), ("A", a_score), ("N", n_score),
                                  ("S", s_score), ("L", l_score), ("I", i_score), ("M", m_score)]
              if sc >= 6]

    return {
        "code": code,
        "total": total,
        "C_score": c_score, "A_score": a_score, "N_score": n_score, "S_score": s_score,
        "L_score": l_score, "I_score": i_score, "M_score": m_score,
        "passed_letters": ",".join(passed),
        "quarter_yoy": round(c_yoy, 1) if pd.notna(c_yoy) else None,
        "annual_growth_3y": round(a_mean, 1) if pd.notna(a_mean) else None,
        "dist_from_250d_high": round(n_dist, 1) if pd.notna(n_dist) else None,
        "vol_ratio_5_60": round(s_ratio, 2) if pd.notna(s_ratio) else None,
        "excess_ret_120d": round(l_excess, 1) if pd.notna(l_excess) else None,
        "inst_hold_ratio": round(i_val, 2) if pd.notna(i_val) else None,
        "close": round(float(daily["close"].iloc[-1]), 2),
        "a_source": a_source,
        "note": i_note,
        "data_date": datetime.now().strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_pool(pool: str) -> list:
    if pool == "hs300":
        df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
        time.sleep(0.2)
        col = _find_col(["成分券代码"], df)
        if col is None:
            df = _retry_call(lambda: ak.index_stock_cons_weight_csindex(symbol="000300"))
            time.sleep(0.2)
            col = _find_col(["成分券代码", "股票代码"], df)
        if col is None:
            sys.exit("ERROR: 沪深300成分股获取失败")
        return [str(x).zfill(6) for x in df[col].tolist()]
    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


def main():
    ap = argparse.ArgumentParser(description="威廉·欧奈尔 CANSLIM 七要素 A 股打分器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="canslim_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    codes = [c.zfill(6) for c in codes]

    print(f"股票池共 {len(codes)} 只。加载池级数据：业绩报表 / 机构持股 / 沪深300趋势...")
    yjbb, report_date = fetch_latest_yjbb()
    print(f"  最新业绩报表期: {report_date}（{len(yjbb)} 只）")
    inst, inst_date = fetch_inst_hold()
    if inst is not None:
        print(f"  机构持股报告期: {inst_date}（{len(inst)} 只）")
    else:
        print("  机构持股无数据，I 维度全部给中性分", file=sys.stderr)
    market = fetch_market_trend()
    bench_ret = float("nan")
    idx = _retry_call(lambda: ak.stock_zh_index_daily(symbol="sh000300"))
    idx["close"] = pd.to_numeric(idx["close"], errors="coerce")
    bench_ret = (float(idx["close"].iloc[-1]) / float(idx["close"].iloc[-120]) - 1) * 100
    print(f"  大盘 M: 沪深300 {market['close']:.0f} vs MA50 {market['ma50']:.0f} → {'上方' if market['above'] else '下方'}（120日涨幅 {bench_ret:.1f}%）")

    print("开始逐一打分（新浪日线+财务指标，请耐心）...")
    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, yjbb, inst, bench_ret, market)
            name = ""
            if not yjbb.empty and "name" in yjbb.columns:
                row = yjbb[yjbb["code"] == code]
                if not row.empty:
                    name = str(row["name"].iloc[0])
            industry = ""
            if not yjbb.empty and "industry" in yjbb.columns:
                row = yjbb[yjbb["code"] == code]
                if not row.empty:
                    industry = str(row["industry"].iloc[0])
            r["name"], r["industry"] = name, industry
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} {name} 得分 {r['total']} [{r['passed_letters']}] | 季同比 {r['quarter_yoy']}% | 距新高 {r['dist_from_250d_high']}% | 超额 {r['excess_ret_120d']}pp")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("total", ascending=False)

    # 池内 RPS 百分位（欧奈尔原版按 12 个月相对强度排名，这里补充 120 日口径）
    if len(df) >= 20 and df["excess_ret_120d"].notna().sum() >= 20:
        df["rps_percentile"] = (df["excess_ret_120d"].rank(pct=True) * 100).round(1)
    else:
        df["rps_percentile"] = None

    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = ["code", "name", "total", "passed_letters", "C_score", "A_score", "N_score",
                    "L_score", "quarter_yoy", "annual_growth_3y", "dist_from_250d_high",
                    "excess_ret_120d", "rps_percentile"]
    display_cols = [c for c in display_cols if c in df.columns]
    print(df.head(args.top)[display_cols].to_string(index=False))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=70 CANSLIM 候选(欧奈尔要求至少 C,A,N,L 四项同时成立); 50-69 观察; <50 不符合。")
    print("提醒: M 项失败时全池减 10 分——欧奈尔纪律：熊市/跌势中不做新买入。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
