#!/usr/bin/env python3
"""cycle_gauge.py — A股市场周期温度计（霍华德·马克斯周期定位）。

用法:
    python scripts/cycle_gauge.py
    python scripts/cycle_gauge.py --codes 600519,000858,600036 --out cycle_gauge.csv
    python scripts/cycle_gauge.py --date 2023-12-31 --lookback 10 --out result.csv

输出: 0-100 的周期位置评分（0=极冷，100=极热）及对应行动建议框架，
      同时给出估值、股债收益差、成交热度、两融趋势四个维度的分项得分。
数据源: akshare（乐咕乐股/中证指数/东方财富/中国债券信息网公开接口）。
"""
import argparse
import os
import sys
import time
import warnings
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

warnings.filterwarnings("ignore")

TQDM_DISABLE = os.environ.get("TQDM_DISABLE", "1")

# 默认关闭系统代理，避免 127.0.0.1:7890 等本地代理阻断东财/同花顺/中证接口
_DISABLE_PROXIES_RAN = False


def _disable_proxies():
    """禁用系统代理变量，避免本地代理干扰数据源直连。"""
    global _DISABLE_PROXIES_RAN
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(k, None)
    _DISABLE_PROXIES_RAN = True


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
    return str(date_str).strip()


def parse_date_series(series):
    """把字符串或 date 序列统一为 Timestamp（日期）。"""
    return pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()


def find_col(df: pd.DataFrame, *keys: str) -> Optional[str]:
    """按子串查找列名，优先精确匹配，返回第一个命中的列。"""
    cols = [str(c).strip() for c in df.columns]
    # 先精确匹配
    for k in keys:
        for c in cols:
            if c == k:
                return c
    # 再子串匹配
    for k in keys:
        for c in cols:
            if k in c:
                return c
    return None


def percentile_of_last(series: pd.Series) -> Optional[float]:
    """返回序列最后一个值在序列中的历史百分位（0-100）。"""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 20:
        return None
    pct = s.rank(pct=True, method="min").iloc[-1] * 100
    return float(pct)


def ratio_score(ratio: Optional[float], neutral: float = 1.0, cold: float = 0.7, hot: float = 1.3) -> Optional[float]:
    """把当前/均线的比例映射到 0-100 分。"""
    if ratio is None or pd.isna(ratio):
        return None
    if ratio <= cold:
        return 0.0
    if ratio >= hot:
        return 100.0
    if ratio <= neutral:
        return 50.0 + (ratio - neutral) / (neutral - cold) * 50.0
    return 50.0 + (ratio - neutral) / (hot - neutral) * 50.0


# ──────────────────────────── 数据获取 ────────────────────────────

def fetch_lg_valuation(index_name: str, as_of: pd.Timestamp, lookback_years: int):
    """从乐咕乐股获取指数 PE/PB 历史，返回当前值与历史分位。"""
    start_dt = as_of - pd.DateOffset(years=lookback_years)
    note = ""
    pe_col = pb_col = None
    pe_current = pb_current = pe_pct = pb_pct = None
    pe_series = pb_series = pd.Series(dtype=float)
    try:
        pe_df = _retry_call(lambda: ak.stock_index_pe_lg(symbol=index_name))
        time.sleep(0.15)
        pb_df = _retry_call(lambda: ak.stock_index_pb_lg(symbol=index_name))
        time.sleep(0.15)
    except Exception as e:
        return {
            "pe_current": None, "pb_current": None,
            "pe_pct": None, "pb_pct": None,
            "pe_series": pe_series, "pb_series": pb_series,
            "note": f"乐咕乐股接口失败: {e}",
        }

    if pe_df is not None and not pe_df.empty:
        pe_df = pe_df.copy()
        pe_df["date"] = parse_date_series(pe_df.iloc[:, 0])
        pe_df = pe_df[(pe_df["date"] >= start_dt) & (pe_df["date"] <= as_of)].dropna(subset=["date"])
        pe_col = find_col(pe_df, "滚动市盈率")
        if pe_col:
            pe_series = pd.to_numeric(pe_df[pe_col], errors="coerce").reset_index(drop=True)
            pe_current = float(pe_series.iloc[-1]) if not pe_series.empty else None
            pe_pct = percentile_of_last(pe_series)

    if pb_df is not None and not pb_df.empty:
        pb_df = pb_df.copy()
        pb_df["date"] = parse_date_series(pb_df.iloc[:, 0])
        pb_df = pb_df[(pb_df["date"] >= start_dt) & (pb_df["date"] <= as_of)].dropna(subset=["date"])
        pb_col = find_col(pb_df, "市净率")
        # 避免误匹配 "等权市净率"，优先选精确列
        exact = [c for c in pb_df.columns if str(c).strip() == "市净率"]
        if exact:
            pb_col = exact[0]
        if pb_col:
            pb_series = pd.to_numeric(pb_df[pb_col], errors="coerce").reset_index(drop=True)
            pb_current = float(pb_series.iloc[-1]) if not pb_series.empty else None
            pb_pct = percentile_of_last(pb_series)

    if pe_current is None and pb_current is None:
        note = "乐咕乐股返回空表"
    return {
        "pe_current": pe_current, "pb_current": pb_current,
        "pe_pct": pe_pct, "pb_pct": pb_pct,
        "pe_series": pe_series, "pb_series": pb_series,
        "note": note,
    }


def fetch_csindex_history(index_code: str, as_of: pd.Timestamp, lookback_years: int):
    """从中证指数获取指数历史行情（含滚动市盈率、成交金额）。失败降级新浪日线。"""
    start_dt = as_of - pd.DateOffset(years=lookback_years)
    start_str = start_dt.strftime("%Y%m%d")
    end_str = as_of.strftime("%Y%m%d")
    note = ""
    df = pd.DataFrame()
    try:
        df = _retry_call(lambda: ak.stock_zh_index_hist_csindex(symbol=index_code, start_date=start_str, end_date=end_str))
        time.sleep(0.15)
    except Exception as e:
        note = f"中证指数历史接口失败: {e}"

    if df is not None and not df.empty:
        df = df.copy()
        df["date"] = parse_date_series(df.iloc[:, 0])
        df = df.dropna(subset=["date"]).sort_values("date")
        return df, note or "中证指数"

    # 降级：新浪日线（仅有 close/volume，无 PE/成交金额）
    try:
        sina = _retry_call(lambda: ak.stock_zh_index_daily(symbol=f"sh{index_code}" if index_code.startswith("0") else f"sz{index_code}"))
        time.sleep(0.15)
        if sina is not None and not sina.empty:
            sina = sina.copy()
            sina["date"] = parse_date_series(sina["date"])
            sina = sina[(sina["date"] >= start_dt) & (sina["date"] <= as_of)].sort_values("date")
            if not sina.empty:
                sina["成交金额"] = float("nan")
                sina["滚动市盈率"] = float("nan")
                return sina, note + "；降级到新浪日线（无 PE/成交金额）"
    except Exception as e2:
        note += f"；新浪日线降级失败: {e2}"

    return pd.DataFrame(), note


def fetch_csindex_latest_value(index_code: str):
    """中证指数最新估值（PE/股息率），用于当前值兜底。"""
    try:
        df = _retry_call(lambda: ak.stock_zh_index_value_csindex(symbol=index_code))
        time.sleep(0.15)
        if df is not None and not df.empty:
            row = df.iloc[-1]
            pe_col = find_col(df, "市盈率")
            # 优先取市盈率2（通常为代表性口径）
            pe2 = find_col(df, "市盈率2")
            return {
                "pe": float(row[pe2]) if pe2 and pd.notna(row[pe2]) else (float(row[pe_col]) if pe_col and pd.notna(row[pe_col]) else None),
                "note": "中证指数最新估值",
            }
    except Exception as e:
        return {"pe": None, "note": f"中证指数最新估值失败: {e}"}
    return {"pe": None, "note": "中证指数最新估值返回空表"}


def fetch_bond_yield_10y(as_of: pd.Timestamp):
    """获取中国10年期国债收益率（百分比）。"""
    # 主数据源：东方财富全球债券
    try:
        df = _retry_call(lambda: ak.bond_zh_us_rate())
        time.sleep(0.15)
        if df is not None and not df.empty:
            df["date"] = parse_date_series(df.iloc[:, 0])
            df = df[df["date"] <= as_of].sort_values("date")
            col = find_col(df, "中国国债收益率10年")
            if col:
                s = pd.to_numeric(df[col], errors="coerce").dropna()
                if not s.empty:
                    return float(s.iloc[-1]), "akshare.bond_zh_us_rate"
    except Exception as e:
        print(f"  10年国债（东方财富）失败: {e}", file=sys.stderr)

    # 降级：中国债券信息网收益率曲线
    try:
        df = _retry_call(lambda: ak.bond_china_yield())
        time.sleep(0.15)
        if df is not None and not df.empty:
            df["date"] = parse_date_series(df[find_col(df, "日期")])
            df = df[df["date"] <= as_of].sort_values("date")
            col = find_col(df, "10年")
            if col:
                s = pd.to_numeric(df[col], errors="coerce").dropna()
                if not s.empty:
                    return float(s.iloc[-1]), "akshare.bond_china_yield（降级）"
    except Exception as e:
        print(f"  10年国债（中债）失败: {e}", file=sys.stderr)

    return None, "10年国债收益率获取失败"


def fetch_margin_balance(as_of: pd.Timestamp):
    """获取全市场两融余额（融资余额）序列。"""
    try:
        df = _retry_call(lambda: ak.stock_margin_account_info())
        time.sleep(0.15)
    except Exception as e:
        return pd.DataFrame(), f"两融余额接口失败: {e}"
    if df is None or df.empty:
        return pd.DataFrame(), "两融余额返回空表"
    df = df.copy()
    df["date"] = parse_date_series(df.iloc[:, 0])
    df = df.dropna(subset=["date"]).sort_values("date")
    col = find_col(df, "融资余额")
    if col:
        df["margin"] = pd.to_numeric(df[col], errors="coerce")
    else:
        df["margin"] = float("nan")
    return df[df["date"] <= as_of], "akshare.stock_margin_account_info"


def fetch_sample_stocks(codes: list, as_of: pd.Timestamp):
    """获取示例股票的名称、收盘价、PE、PB。"""
    name_df = pd.DataFrame()
    try:
        name_df = _retry_call(lambda: ak.stock_info_a_code_name())
        time.sleep(0.15)
    except Exception as e:
        print(f"  股票名称表获取失败: {e}", file=sys.stderr)
    name_map = {}
    if not name_df.empty and "code" in name_df.columns and "name" in name_df.columns:
        name_map = dict(zip(name_df["code"].astype(str).str.strip(), name_df["name"].astype(str).str.strip()))

    rows = []
    for code in codes:
        code = code.strip()
        if not (code.isdigit() and len(code) == 6):
            continue
        try:
            df = _retry_call(lambda: ak.stock_value_em(symbol=code))
            time.sleep(0.15)
        except Exception as e:
            print(f"  {code} 估值获取失败: {e}", file=sys.stderr)
            continue
        if df is None or df.empty:
            continue
        df["date"] = parse_date_series(df.iloc[:, 0])
        df = df[df["date"] <= as_of].sort_values("date")
        if df.empty:
            continue
        row = df.iloc[-1]
        close_col = find_col(df, "收盘价")
        pe_col = find_col(df, "PE(TTM)")
        pb_col = find_col(df, "市净率")
        rows.append({
            "code": code,
            "name": name_map.get(code, code),
            "close": float(row[close_col]) if close_col and pd.notna(row[close_col]) else None,
            "pe_ttm": float(row[pe_col]) if pe_col and pd.notna(row[pe_col]) else None,
            "pb": float(row[pb_col]) if pb_col and pd.notna(row[pb_col]) else None,
        })
    return pd.DataFrame(rows)


# ──────────────────────────── 核心计算 ────────────────────────────

def compute_valuation_score(as_of: pd.Timestamp, lookback_years: int):
    """计算估值维度得分（PE/PB 历史分位，越高越热）。"""
    sub_scores = []
    notes = []
    details = []

    # 沪深300
    hs300 = fetch_lg_valuation("沪深300", as_of, lookback_years)
    hs_sub = []
    if hs300["pe_pct"] is not None:
        hs_sub.append(hs300["pe_pct"])
        details.append(("沪深300", "PE-TTM 历史分位", hs300["pe_current"], hs300["pe_pct"], "%"))
    if hs300["pb_pct"] is not None:
        hs_sub.append(hs300["pb_pct"])
        details.append(("沪深300", "PB 历史分位", hs300["pb_current"], hs300["pb_pct"], "%"))
    if hs_sub:
        sub_scores.append(sum(hs_sub) / len(hs_sub))
        notes.append(f"沪深300 PE={hs300['pe_current']}({hs300['pe_pct']:.1f}%) PB={hs300['pb_current']}({hs300['pb_pct']:.1f}%)")
    else:
        notes.append(f"沪深300 估值不可得: {hs300['note']}")

    # 中证全指：PE 来自中证指数历史，PB 用中证800 近似（全市场 PB 历史不可得）
    zzqz_hist, zzqz_note = fetch_csindex_history("000985", as_of, lookback_years)
    zz_sub = []
    pe_current = None
    pe_pct = None
    if not zzqz_hist.empty:
        pe_col = find_col(zzqz_hist, "滚动市盈率")
        if pe_col:
            pe_series = pd.to_numeric(zzqz_hist[pe_col], errors="coerce").dropna()
            if len(pe_series) >= 20:
                pe_current = float(pe_series.iloc[-1])
                pe_pct = percentile_of_last(pe_series)
                zz_sub.append(pe_pct)
                details.append(("中证全指", "PE-TTM 历史分位", pe_current, pe_pct, "%"))
    if pe_current is None:
        latest = fetch_csindex_latest_value("000985")
        pe_current = latest["pe"]
        notes.append(f"中证全指 PE 历史不可得，使用最新值: {latest['note']}")
    else:
        notes.append(f"中证全指 PE={pe_current:.2f}({pe_pct:.1f}%)")

    # PB 用中证800 近似
    zz800 = fetch_lg_valuation("中证800", as_of, lookback_years)
    if zz800["pb_pct"] is not None:
        zz_sub.append(zz800["pb_pct"])
        details.append(("中证800(全市场PB近似)", "PB 历史分位", zz800["pb_current"], zz800["pb_pct"], "%"))
        notes.append(f"全市场PB近似(中证800)={zz800['pb_current']}({zz800['pb_pct']:.1f}%)")
    else:
        notes.append(f"全市场PB近似不可得: {zz800['note']}")

    if zz_sub:
        sub_scores.append(sum(zz_sub) / len(zz_sub))

    score = sum(sub_scores) / len(sub_scores) if sub_scores else 50.0
    return score, details, "；".join(notes)


def compute_spread_score(zzqz_hist: pd.DataFrame, as_of: pd.Timestamp, lookback_years: int):
    """计算股债收益差得分（越高越便宜 => 周期越冷 => 低分）。"""
    if zzqz_hist.empty:
        return 50.0, None, None, "中证全指历史数据缺失，股债收益差不可用"

    pe_col = find_col(zzqz_hist, "滚动市盈率")
    if not pe_col:
        return 50.0, None, None, "中证全指历史无 PE，股债收益差不可用"

    pe_series = pd.to_numeric(zzqz_hist[pe_col], errors="coerce").dropna()
    if len(pe_series) < 20:
        return 50.0, None, None, "中证全指 PE 历史不足"

    bond_yield, bond_note = fetch_bond_yield_10y(as_of)
    if bond_yield is None:
        return 50.0, None, None, "10年国债收益率获取失败"

    # 合并 PE 日期与债券收益率日期
    pe_df = pd.DataFrame({
        "date": zzqz_hist["date"].values[-len(pe_series):],
        "pe": pe_series.values,
    })
    # 债券数据
    try:
        bond_df = _retry_call(lambda: ak.bond_zh_us_rate())
        time.sleep(0.15)
    except Exception:
        bond_df = pd.DataFrame()
    if bond_df is None or bond_df.empty:
        return 50.0, None, None, "债券收益率历史获取失败"
    bond_df["date"] = parse_date_series(bond_df.iloc[:, 0])
    bond_col = find_col(bond_df, "中国国债收益率10年")
    bond_df["yield"] = pd.to_numeric(bond_df[bond_col], errors="coerce")
    bond_df = bond_df.dropna(subset=["yield"])

    merged = pd.merge(pe_df, bond_df[["date", "yield"]], on="date", how="inner")
    if len(merged) < 20:
        return 50.0, None, None, "PE 与债券日期交集不足"

    merged["spread"] = (1.0 / merged["pe"]) * 100.0 - merged["yield"]
    merged = merged.sort_values("date")
    current_spread = float(merged["spread"].iloc[-1])
    spread_pct = percentile_of_last(merged["spread"])
    # 越高越便宜 => 越冷 => 100 - pct
    spread_score = 100.0 - spread_pct if spread_pct is not None else 50.0
    return spread_score, current_spread, bond_yield, f"股债收益差={current_spread:.2f}%({spread_pct:.1f}%分位)；{bond_note}"


def compute_turnover_score(zzqz_hist: pd.DataFrame):
    """计算成交热度得分（越高越热）。"""
    if zzqz_hist.empty:
        return 50.0, None, None, None, "中证全指历史数据缺失，成交热度不可用"
    amount_col = find_col(zzqz_hist, "成交金额")
    if not amount_col:
        return 50.0, None, None, None, "成交金额列缺失"
    amount = pd.to_numeric(zzqz_hist[amount_col], errors="coerce").dropna()
    if len(amount) < 60:
        return 50.0, None, None, None, "成交金额历史不足"

    current = float(amount.iloc[-1])
    ma20 = float(amount.tail(20).mean())
    ma60 = float(amount.tail(60).mean())
    pct = percentile_of_last(amount)
    ratio20 = current / ma20 if ma20 > 0 else None
    ratio60 = current / ma60 if ma60 > 0 else None

    score_pct = pct if pct is not None else 50.0
    score_ratio20 = ratio_score(ratio20, neutral=1.0, cold=0.7, hot=1.5)
    score = 0.6 * score_pct + 0.4 * score_ratio20 if score_ratio20 is not None else score_pct
    return score, current, ma20, ma60, f"成交额={current:.0f}亿/20日均={ma20:.0f}亿/60日均={ma60:.0f}亿"


def compute_margin_score(as_of: pd.Timestamp):
    """计算两融余额趋势得分（越高越热）。"""
    margin_df, note = fetch_margin_balance(as_of)
    if margin_df.empty or margin_df["margin"].isna().all():
        return 50.0, None, None, None, f"两融数据缺失: {note}"
    series = margin_df["margin"].dropna()
    if len(series) < 20:
        return 50.0, None, None, None, "两融余额历史不足"

    current = float(series.iloc[-1])
    ma20 = float(series.tail(20).mean())
    ma60 = float(series.tail(60).mean())
    window = series.tail(min(250, len(series)))
    min_v = float(window.min())
    max_v = float(window.max())
    range_score = (current - min_v) / (max_v - min_v) * 100.0 if max_v > min_v else 50.0
    ratio20 = current / ma20 if ma20 > 0 else None
    ratio_score20 = ratio_score(ratio20, neutral=1.0, cold=0.9, hot=1.1)
    score = 0.5 * range_score + 0.5 * ratio_score20 if ratio_score20 is not None else range_score
    return score, current, ma20, ma60, f"融资余额={current:.0f}亿/20日均={ma20:.0f}亿/60日均={ma60:.0f}亿"


def action_framework(score: float) -> str:
    """根据 0-100 周期位置给出行动建议框架。"""
    if score <= 20:
        return "极冷区间｜第二层思维：别人恐惧时贪婪。可积极布局优质资产，逆向分批买入。"
    if score <= 40:
        return "偏冷区间｜钟摆靠近低估端。逐步建仓，但保留现金等待更极端情绪。"
    if score <= 60:
        return "中性区间｜不冷不热。以持有为主，避免追涨杀跌，等待周期给出更明确信号。"
    if score <= 80:
        return "偏热区间｜谨慎追高。考虑兑现部分利润，降低仓位，警惕情绪过热。"
    return "极热区间｜风险意识优先。防御为主，控制回撤；牢记风险是永久损失，而非波动。"


def build_output_rows(report_date: str, final_score: float, scores: dict, details: list, sample_df: pd.DataFrame, action: str):
    """构造 CSV 输出用长表。"""
    rows = []
    rows.append({
        "report_date": report_date,
        "category": "GAUGE",
        "item": "cycle_position",
        "value": round(final_score, 2),
        "score": round(final_score, 2),
        "unit": "0-100",
        "note": action,
    })
    for name, sc in scores.items():
        rows.append({
            "report_date": report_date,
            "category": "COMPONENT",
            "item": name,
            "value": round(sc["value"], 2) if sc.get("value") is not None else None,
            "score": round(sc["score"], 2),
            "unit": sc.get("unit", ""),
            "note": sc.get("note", ""),
        })
    for idx_name, metric, value, pct, unit in details:
        rows.append({
            "report_date": report_date,
            "category": "INDEX",
            "item": f"{idx_name}_{metric}",
            "value": round(value, 2) if value is not None else None,
            "score": round(pct, 2) if pct is not None else None,
            "unit": unit,
            "note": "",
        })
    if not sample_df.empty:
        for _, r in sample_df.iterrows():
            rows.append({
                "report_date": report_date,
                "category": "SAMPLE",
                "item": f"{r['code']} {r['name']}",
                "value": f"close={r['close']},pe={r['pe_ttm']},pb={r['pb']}",
                "score": None,
                "unit": "",
                "note": "示例个股，仅供观察",
            })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description="A股市场周期温度计（霍华德·马克斯周期定位）")
    ap.add_argument("--date", default=pd.Timestamp.now().strftime("%Y%m%d"),
                    help="报告日期，支持 20231231 或 2023-12-31（默认今天）")
    ap.add_argument("--lookback", type=int, default=10, help="历史分位回看年数（默认 10）")
    ap.add_argument("--codes", default="", help="逗号分隔的示例股票代码，如 600519,000858,600036")
    ap.add_argument("--out", default="cycle_gauge.csv", help="CSV 输出路径（默认 cycle_gauge.csv）")
    ap.add_argument("--no-proxy", action="store_true", help="兼容旧参数，现脚本已默认禁用系统代理")
    args = ap.parse_args()

    _disable_proxies()
    if args.no_proxy:
        _disable_proxies()

    report_date = normalize_date(args.date)
    try:
        as_of = pd.Timestamp(report_date)
    except Exception:
        sys.exit(f"ERROR: 无法解析日期 {args.date}")
    if as_of > pd.Timestamp.now():
        sys.exit("ERROR: 报告日期不能是未来")

    print(f"霍华德·马克斯周期温度计 | 报告日期: {report_date} | 回看: {args.lookback}年\n")

    # 1. 估值
    print("[1/4] 计算估值分位（沪深300 PE/PB，中证全指 PE，全市场PB以中证800近似）...")
    val_score, val_details, val_note = compute_valuation_score(as_of, args.lookback)
    print(f"  估值得分: {val_score:.1f}/100  ({val_note})")

    # 中证全指历史（复用：PE、成交额）
    print("\n[2/4] 拉取中证全指历史行情（PE + 成交金额）...")
    zzqz_hist, zzqz_note = fetch_csindex_history("000985", as_of, args.lookback)
    print(f"  数据源: {zzqz_note} | 行数: {len(zzqz_hist)}")

    # 2. 股债收益差
    print("\n[3/4] 计算股债收益差（中证全指盈利收益率 - 10年国债收益率）...")
    spread_score, spread_val, bond_yield, spread_note = compute_spread_score(zzqz_hist, as_of, args.lookback)
    print(f"  股债收益差得分: {spread_score:.1f}/100  ({spread_note})")

    # 3. 成交热度
    print("\n[4/4] 计算成交热度与两融趋势...")
    turn_score, turn_cur, turn_ma20, turn_ma60, turn_note = compute_turnover_score(zzqz_hist)
    print(f"  成交热度得分: {turn_score:.1f}/100  ({turn_note})")
    margin_score, margin_cur, margin_ma20, margin_ma60, margin_note = compute_margin_score(as_of)
    print(f"  两融趋势得分: {margin_score:.1f}/100  ({margin_note})")

    # 合成周期位置评分
    weights = {"valuation": 0.30, "spread": 0.25, "turnover": 0.25, "margin": 0.20}
    final_score = (
        weights["valuation"] * val_score +
        weights["spread"] * spread_score +
        weights["turnover"] * turn_score +
        weights["margin"] * margin_score
    )
    action = action_framework(final_score)

    # 示例个股
    sample_df = pd.DataFrame()
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        print("\n[示例个股观察]")
        sample_df = fetch_sample_stocks(codes, as_of)
        if not sample_df.empty:
            print(sample_df.to_string(index=False))
        else:
            print("  未能获取示例个股数据")

    # 输出
    scores = {
        "valuation": {"score": val_score, "value": val_score, "unit": "0-100", "note": val_note},
        "spread": {"score": spread_score, "value": spread_val, "unit": "%", "note": spread_note or ""},
        "turnover": {"score": turn_score, "value": turn_cur, "unit": "亿元", "note": turn_note or ""},
        "margin": {"score": margin_score, "value": margin_cur, "unit": "亿元", "note": margin_note or ""},
    }
    out_df = build_output_rows(report_date, final_score, scores, val_details, sample_df, action)
    out_df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print(f"🌡️  周期位置评分: {final_score:.1f} / 100")
    print(f"📍 估值: {val_score:.1f} | 股债差: {spread_score:.1f} | 成交热度: {turn_score:.1f} | 两融趋势: {margin_score:.1f}")
    print(f"💡 行动建议: {action}")
    print(f"\n完整结果已写入: {args.out}")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。周期定位是艺术，不是精确科学。")


if __name__ == "__main__":
    main()
