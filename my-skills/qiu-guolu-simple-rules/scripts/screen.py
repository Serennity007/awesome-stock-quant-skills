#!/usr/bin/env python3
"""screen.py — 邱国鹭《投资中最简单的事》A 股“三好”龙头打分器。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out qiu_result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out qiu_result.csv

筛选逻辑（机械近似）:
    1. 好行业：以同花顺/东方财富行业分类为锚，按市值前 3 近似“行业集中度/龙头溢价”。
    2. 好公司：ROE>15% 且稳定；营收增速为正且稳定，近似“市占率/竞争优势”。
    3. 好价格：当前 PE/PB 处于自身历史估值低分位。
    “数月亮不数星星”——直接输出各行业龙头打分，不追逐二三线标的。

数据源: akshare（东方财富优先，失败自动降级同花顺/腾讯/新浪）。
"""
import os

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import argparse
import sys
import time
from datetime import datetime
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
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理干扰东财/同花顺直连。"""
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


def _to_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


# ---------------------------------------------------------------------------
# 股票池
# ---------------------------------------------------------------------------

def get_pool(pool: str) -> list:
    """获取股票池代码列表。"""
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
# 行业映射
# ---------------------------------------------------------------------------

def fetch_industry_map() -> pd.DataFrame:
    """从最新业绩报表获取代码->行业映射。失败返回空 DataFrame。"""
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

        # 如果该期有有效行业数据，则采用
        if "industry" in out.columns and out["industry"].notna().sum() > 0:
            return out.dropna(subset=["industry"]).reset_index(drop=True)

    return pd.DataFrame(columns=["code", "name", "industry"])


# ---------------------------------------------------------------------------
# 估值与市值（东财为主，腾讯/同花顺降级）
# ---------------------------------------------------------------------------

def fetch_value_em(code: str) -> pd.DataFrame:
    """获取个股历史估值/市值表，过滤未来日期。"""
    df = _retry_call(lambda: ak.stock_value_em(symbol=code))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("估值数据为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["数据日期"], df) or df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    today = pd.Timestamp.now()
    df = df[df[date_col] <= today]
    if df.empty:
        raise RuntimeError("无有效历史估值数据")
    return df.sort_values(date_col).reset_index(drop=True)


def fetch_spot_tx_fallback(code: str) -> dict:
    """腾讯行情全市场快照降级，取最新 PE/PB/市值。"""
    prefix = "sh" if code.startswith("6") or code.startswith("5") else "sz"
    full = f"{prefix}{code}"
    df = _retry_call(lambda: ak.stock_zh_a_spot_tx())
    time.sleep(0.15)
    if df is None or df.empty or "code" not in df.columns:
        return {}
    row = df[df["code"].astype(str).str.lower() == full]
    if row.empty:
        return {}
    r = row.iloc[-1]
    return {
        "pe_ttm": pd.to_numeric(r.get("pe_ttm"), errors="coerce"),
        "pb": pd.to_numeric(r.get("pn"), errors="coerce"),
        "total_mv_yi": pd.to_numeric(r.get("zsz"), errors="coerce"),  # 亿元
        "close": pd.to_numeric(r.get("zxj"), errors="coerce"),
        "name": str(r.get("name", "")).strip() if pd.notna(r.get("name")) else "",
    }


# ---------------------------------------------------------------------------
# 财务指标（东财财务指标表为主，新浪三大报表降级）
# ---------------------------------------------------------------------------

def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """近 YEARS+1 年主要财务指标，仅保留年报（12-31）。"""
    start = str(datetime.now().year - YEARS - 2)
    df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=start))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError(f"{code} 财务指标为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df) or df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[df[date_col].dt.month == 12].sort_values(date_col).tail(YEARS)
    if df.empty:
        raise RuntimeError(f"{code} 无年度财务数据")
    return df.reset_index(drop=True)


def fetch_sina_report(code: str, report_type: str) -> pd.DataFrame:
    """获取新浪三大报表（年报）。失败返回空 DataFrame；过滤掉未来日期。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol=report_type))
        time.sleep(0.15)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["报告日"] = df["报告日"].astype(str).str.replace("-", "")
    today = datetime.now().strftime("%Y%m%d")
    df = df[(df["报告日"].str.endswith("1231")) & (df["报告日"] <= today)]
    df = df.sort_values("报告日").tail(YEARS)
    return df.reset_index(drop=True)


def _financials_from_sina(code: str) -> dict:
    """新浪三大报表降级，提取 ROE 与营收增速。"""
    bs = fetch_sina_report(code, "资产负债表")
    inc = fetch_sina_report(code, "利润表")
    if bs.empty or inc.empty:
        raise RuntimeError("新浪三大报表不足以计算指标")

    # ROE = 净利润 / 所有者权益合计
    profit_col = _find_col(["净利润"], inc)
    equity_col = _find_col(["所有者权益(或股东权益)合计"], bs)
    roe = pd.Series(dtype=float)
    if profit_col is not None and equity_col is not None:
        profit = _to_numeric_series(inc[profit_col])
        equity = _to_numeric_series(bs[equity_col])
        roe = (profit / equity.replace(0, float("nan")) * 100).dropna()

    # 营收增速：需要两年的营业收入
    rev_col = _find_col(["营业收入"], inc)
    rev_growth = pd.Series(dtype=float)
    if rev_col is not None:
        rev = _to_numeric_series(inc[rev_col]).dropna()
        if len(rev) >= 2:
            rev_growth = ((rev - rev.shift(1)) / rev.shift(1).replace(0, float("nan")) * 100).dropna()

    return {"roe": roe, "revenue_growth": rev_growth, "source": "akshare.stock_financial_report_sina（降级）"}


def get_financials(code: str) -> dict:
    """获取财务指标，优先东财财务指标表；若营收增速缺失则用新浪利润表补充；整体失败降级新浪三大报表。"""
    errs = []
    try:
        df = fetch_financial_indicator(code)
        roe_col = _find_col(["净资产收益率(%)"], df)
        rev_col = _find_col(["主营业务收入增长率(%)", "营业收入增长率(%)", "营业总收入增长率(%)"], df)
        if roe_col is None:
            raise RuntimeError("财务指标表缺少 ROE 列")

        roe = _to_numeric_series(df[roe_col]).dropna()
        rev_growth = _to_numeric_series(df[rev_col]).dropna() if rev_col else pd.Series(dtype=float)

        # 银行/保险等金融企业的年度营收增速列可能为空，用新浪利润表补充
        if rev_growth.empty:
            time.sleep(0.15)
            try:
                inc = fetch_sina_report(code, "利润表")
                if not inc.empty:
                    sina_rev_col = _find_col(["营业收入"], inc)
                    if sina_rev_col is not None:
                        rev = _to_numeric_series(inc[sina_rev_col]).dropna()
                        if len(rev) >= 2:
                            rev_growth = ((rev - rev.shift(1)) / rev.shift(1).replace(0, float("nan")) * 100).dropna()
            except Exception as e:
                errs.append(f"新浪利润表补充营收增速: {e}")

        return {
            "roe": roe,
            "revenue_growth": rev_growth,
            "source": "akshare.stock_financial_analysis_indicator",
            "note": "营收增速由新浪利润表补充" if not rev_growth.empty and rev_col is None else "",
        }
    except Exception as e:
        errs.append(f"财务指标表: {e}")

    time.sleep(0.15)
    try:
        out = _financials_from_sina(code)
        out["note"] = "ROE/营收增速由新浪三大报表手工计算"
        return out
    except Exception as e:
        errs.append(f"新浪三大报表: {e}")

    raise RuntimeError("; ".join(errs))


# ---------------------------------------------------------------------------
# 综合数据获取
# ---------------------------------------------------------------------------

def get_valuation(code: str) -> dict:
    """获取估值/市值，优先东财历史估值，失败降级腾讯快照。"""
    # 东财：有历史 PE/PB 与市值
    try:
        df = fetch_value_em(code)
        pe_col = _find_col(["PE(TTM)"], df)
        pb_col = _find_col(["市净率"], df)
        mv_col = _find_col(["总市值"], df)
        close_col = _find_col(["当日收盘价"], df)

        pe_series = _to_numeric_series(df[pe_col]).dropna() if pe_col else pd.Series(dtype=float)
        pb_series = _to_numeric_series(df[pb_col]).dropna() if pb_col else pd.Series(dtype=float)
        mv_series = _to_numeric_series(df[mv_col]).dropna() if mv_col else pd.Series(dtype=float)
        close_series = _to_numeric_series(df[close_col]).dropna() if close_col else pd.Series(dtype=float)

        cur_pe = pe_series.iloc[-1] if not pe_series.empty else float("nan")
        cur_pb = pb_series.iloc[-1] if not pb_series.empty else float("nan")
        cur_mv = mv_series.iloc[-1] if not mv_series.empty else float("nan")  # 元
        cur_close = close_series.iloc[-1] if not close_series.empty else float("nan")

        pe_pct = (pe_series < cur_pe).mean() * 100 if not pe_series.empty and pd.notna(cur_pe) else float("nan")
        pb_pct = (pb_series < cur_pb).mean() * 100 if not pb_series.empty and pd.notna(cur_pb) else float("nan")

        return {
            "pe_ttm": cur_pe,
            "pb": cur_pb,
            "total_mv_yi": cur_mv / 1e8 if pd.notna(cur_mv) else float("nan"),  # 亿元
            "close": cur_close,
            "pe_percentile": pe_pct,
            "pb_percentile": pb_pct,
            "pe_history_len": len(pe_series),
            "pb_history_len": len(pb_series),
            "source": "akshare.stock_value_em",
            "note": "",
        }
    except Exception as e:
        pass

    # 降级：腾讯快照只有当前值，无法计算历史分位
    time.sleep(0.15)
    try:
        data = fetch_spot_tx_fallback(code)
        if data:
            data["pe_percentile"] = float("nan")
            data["pb_percentile"] = float("nan")
            data["pe_history_len"] = 0
            data["pb_history_len"] = 0
            data["source"] = "akshare.stock_zh_a_spot_tx（降级）"
            data["note"] = "当前估值来自腾讯快照，无历史分位"
            return data
    except Exception as e:
        pass

    raise RuntimeError("无法获取估值数据")


# ---------------------------------------------------------------------------
# 打分
# ---------------------------------------------------------------------------

def score_industry(rank: int) -> int:
    """行业龙头排名打分：第 1 名 25 分，前 3 名有分。"""
    if rank == 1:
        return 25
    elif rank == 2:
        return 20
    elif rank == 3:
        return 15
    return 0


def score_company(roe: pd.Series, rev_growth: pd.Series) -> dict:
    """好公司打分：ROE 稳定性与水平 25 分，营收增速 15 分。"""
    roe = roe.dropna()
    rev_growth = rev_growth.dropna()

    roe_score = 0
    if not roe.empty:
        avg = float(roe.mean())
        std = float(roe.std()) if len(roe) >= 2 else 0.0
        if avg >= 20:
            roe_score += 20
        elif avg >= 15:
            roe_score += 16
        elif avg >= 12:
            roe_score += 12
        elif avg >= 10:
            roe_score += 8
        elif avg >= 5:
            roe_score += 4

        # 稳定性奖励：标准差小
        if std < 3:
            roe_score += 5
        elif std < 5:
            roe_score += 3
        elif std < 8:
            roe_score += 1
        roe_score = min(roe_score, 25)

    growth_score = 0
    if not rev_growth.empty:
        avg_g = float(rev_growth.mean())
        if avg_g >= 20:
            growth_score = 15
        elif avg_g >= 15:
            growth_score = 13
        elif avg_g >= 10:
            growth_score = 10
        elif avg_g >= 5:
            growth_score = 7
        elif avg_g >= 0:
            growth_score = 4

    return {
        "roe_score": roe_score,
        "growth_score": growth_score,
        "roe_avg": round(float(roe.mean()), 2) if not roe.empty else None,
        "roe_std": round(float(roe.std()), 2) if len(roe) >= 2 else None,
        "revenue_growth_avg": round(float(rev_growth.mean()), 2) if not rev_growth.empty else None,
    }


def score_price(pe: float, pb: float, pe_pct: float, pb_pct: float) -> dict:
    """好价格打分：优先历史低分位；无分位时按绝对估值降级。"""
    pe_score = 0
    pb_score = 0
    note = ""

    has_pct = pd.notna(pe_pct) and pd.notna(pb_pct)
    if has_pct:
        # PE 分位：20 分
        if pe_pct < 10:
            pe_score = 20
        elif pe_pct < 25:
            pe_score = 15
        elif pe_pct < 50:
            pe_score = 10
        elif pe_pct < 75:
            pe_score = 5

        # PB 分位：15 分
        if pb_pct < 10:
            pb_score = 15
        elif pb_pct < 25:
            pb_score = 12
        elif pb_pct < 50:
            pb_score = 8
        elif pb_pct < 75:
            pb_score = 4
    else:
        note = "无历史估值分位，按绝对 PE/PB 降级评分"
        # 绝对 PE：20 分
        if pd.notna(pe):
            if pe < 15:
                pe_score = 20
            elif pe < 25:
                pe_score = 14
            elif pe < 40:
                pe_score = 8
            elif pe < 60:
                pe_score = 4
        # 绝对 PB：15 分
        if pd.notna(pb):
            if pb < 1.5:
                pb_score = 15
            elif pb < 3:
                pb_score = 10
            elif pb < 5:
                pb_score = 6
            elif pb < 8:
                pb_score = 3

    return {
        "pe_score": pe_score,
        "pb_score": pb_score,
        "price_score": pe_score + pb_score,
        "price_note": note,
    }


def analyze_one(code: str, industry_map: pd.DataFrame) -> dict:
    """分析单只股票，返回完整结果字典。"""
    meta = industry_map[industry_map["code"] == code]
    name = str(meta["name"].iloc[0]) if not meta.empty else ""
    industry = str(meta["industry"].iloc[0]) if not meta.empty else ""

    # 1. 估值
    val = get_valuation(code)
    if not name and val.get("name"):
        name = val["name"]

    # 2. 财务
    fin = get_financials(code)

    data_years = max(
        len(fin["roe"].dropna()),
        len(fin["revenue_growth"].dropna()),
    )

    return {
        "code": code,
        "name": name,
        "industry": industry,
        "pe_ttm": round(float(val["pe_ttm"]), 2) if pd.notna(val.get("pe_ttm")) else None,
        "pb": round(float(val["pb"]), 3) if pd.notna(val.get("pb")) else None,
        "total_mv_yi": round(float(val["total_mv_yi"]), 2) if pd.notna(val.get("total_mv_yi")) else None,
        "close": round(float(val["close"]), 2) if pd.notna(val.get("close")) else None,
        "pe_percentile": round(float(val["pe_percentile"]), 1) if pd.notna(val.get("pe_percentile")) else None,
        "pb_percentile": round(float(val["pb_percentile"]), 1) if pd.notna(val.get("pb_percentile")) else None,
        "roe_avg": None,
        "roe_std": None,
        "revenue_growth_avg": None,
        "data_years": data_years,
        "val_source": val.get("source", ""),
        "fin_source": fin.get("source", ""),
        "note": " ".join(filter(None, [val.get("note", ""), fin.get("note", "")])).strip(),
        "_total_mv_yi": val.get("total_mv_yi"),
        "_industry": industry,
        "_roe": fin["roe"],
        "_revenue_growth": fin["revenue_growth"],
        "_pe": val["pe_ttm"],
        "_pb": val["pb"],
        "_pe_pct": val["pe_percentile"],
        "_pb_pct": val["pb_percentile"],
    }


def add_scores_and_ranks(rows: list) -> list:
    """在收集完全部市值后，计算行业排名与各项得分。"""
    if not rows:
        return rows

    # 按行业分组，按市值排名
    df = pd.DataFrame(rows)
    df["industry_rank"] = df.groupby("_industry")["_total_mv_yi"].rank(
        method="min", ascending=False, na_option="bottom"
    ).fillna(999).astype(int)

    out = []
    for _, row in df.iterrows():
        d = dict(row)
        d["industry_rank"] = int(row["industry_rank"])

        # 好行业
        d["industry_score"] = score_industry(d["industry_rank"])

        # 好公司
        company = score_company(row["_roe"], row["_revenue_growth"])
        d.update(company)

        # 好价格
        price = score_price(row["_pe"], row["_pb"], row["_pe_pct"], row["_pb_pct"])
        d.update(price)

        d["total_score"] = d["industry_score"] + d["roe_score"] + d["growth_score"] + d["price_score"]

        # 清理内部字段
        for k in ["_total_mv_yi", "_industry", "_roe", "_revenue_growth", "_pe", "_pb", "_pe_pct", "_pb_pct"]:
            d.pop(k, None)

        out.append(d)

    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="邱国鹭《投资中最简单的事》A 股三好龙头打分器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="qiu_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    # 默认禁用系统代理
    _disable_proxies()

    codes = [c.strip().zfill(6) for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    print(f"股票池共 {len(codes)} 只，开始加载行业映射...")

    industry_map = fetch_industry_map()
    print(f"行业映射加载完成，覆盖 {len(industry_map)} 只股票。开始逐一采集估值与财务...")
    print("注：ROE/营收增速为机械近似；历史估值分位基于东财日度估值序列。")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = analyze_one(code, industry_map)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} {r['name']} 市值={r['total_mv_yi']}亿 | 来源: {r['val_source']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    rows = add_scores_and_ranks(rows)
    df = pd.DataFrame(rows).sort_values("total_score", ascending=False).reset_index(drop=True)
    df["data_date"] = normalize_date(datetime.now().strftime("%Y%m%d"))
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    display_cols = [
        "code", "name", "industry", "industry_rank", "total_score",
        "industry_score", "roe_score", "growth_score", "price_score",
        "pe_ttm", "pb", "pe_percentile", "pb_percentile",
        "roe_avg", "roe_std", "revenue_growth_avg", "total_mv_yi",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    print(df.head(args.top)[display_cols].to_string(index=False))

    leader_count = int((df["industry_rank"] <= 3).sum())
    print(f"\n行业龙头（行业市值前3）: {leader_count}/{len(df)} 只")
    print(f"成功 {len(rows)} 只，失败 {len(failed)} 只。")
    if failed:
        print("失败股票:", ", ".join(f"{c}({e})" for c, e in failed[:10]))
    incomplete = df[df["data_years"] < YEARS]
    if not incomplete.empty:
        print(f"注意: {len(incomplete)} 只股票财务数据未满 {YEARS} 年，分数参考性下降。")
    print("\n免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
