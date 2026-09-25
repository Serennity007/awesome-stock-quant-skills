#!/usr/bin/env python3
"""contrarian_scan.py — 约翰·邓普顿全球逆向投资法 A 股初筛。

用法:
    python scripts/contrarian_scan.py --pool hs300 --top 20 --out result.csv
    python scripts/contrarian_scan.py --codes 600519,000858,600036 --out result.csv

筛选逻辑（极度悲观信号）:
    1. 股价处于 52 周低位区间（距离低点不远）。
    2. PE(TTM) / PB 处于自身近 5 年历史 10% 分位以下。
    3. 成交量极度萎缩后企稳（近 5 日均量 < 近 20 日均量 50%，且未再创新低）。
    4. 最新年度盈利仍为正（困境中的优质企业）。

数据源: akshare（优先东方财富估值接口，失败降级为新浪财报 + 日线）。
"""
import os

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import argparse
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
TRADING_DAYS_YEAR = 250


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


def _to_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


def _a_symbol(code: str) -> str:
    """根据 A 股代码规则生成带交易所前缀的 symbol。"""
    if code.startswith(("6", "688", "689")):
        return f"sh{code}"
    if code.startswith(("0", "2", "3", "30", "301")):
        return f"sz{code}"
    return f"bj{code}"


def get_pool(pool: str) -> list:
    """获取预定义股票池代码列表。"""
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


def build_name_map() -> dict:
    """构建全部 A 股代码 -> 名称映射，失败返回空字典。"""
    try:
        df = _retry_call(lambda: ak.stock_info_a_code_name())
        time.sleep(0.15)
        if "code" not in df.columns or "name" not in df.columns:
            return {}
        df["code"] = df["code"].astype(str).str.zfill(6)
        names = df["name"].astype(str).str.strip().str.replace(" ", "")
        return dict(zip(df["code"].tolist(), names.tolist()))
    except Exception:
        return {}


def fetch_daily(code: str) -> pd.DataFrame:
    """获取个股日线（近 2 年），返回含 date/close/volume 的标准化 DataFrame。"""
    primary = _a_symbol(code)
    fallbacks = [s for s in (f"sh{code}", f"sz{code}", f"bj{code}") if s != primary]

    for sym in [primary] + fallbacks:
        try:
            df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=sym, adjust=""))
            time.sleep(0.15)
            if df is None or df.empty:
                continue
            df = df.copy()
            df.columns = [str(c).strip() for c in df.columns]
            date_col = _find_col(["date", "日期"], df) or df.columns[0]
            df["date"] = pd.to_datetime(df[date_col], errors="coerce")
            today = pd.Timestamp.now().normalize()
            df = df[df["date"] <= today].sort_values("date").reset_index(drop=True)
            if len(df) < 60:
                continue
            close_col = _find_col(["close", "收盘"], df)
            vol_col = _find_col(["volume", "成交量"], df)
            if close_col is None or vol_col is None:
                continue
            df["close"] = pd.to_numeric(df[close_col], errors="coerce")
            df["volume"] = pd.to_numeric(df[vol_col], errors="coerce")
            return df[["date", "close", "volume"]].dropna()
        except Exception:
            continue
    return pd.DataFrame()


def fetch_valuation_em(code: str) -> pd.DataFrame:
    """东方财富每日估值历史（PE/PB）。"""
    df = _retry_call(lambda: ak.stock_value_em(symbol=code))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("估值数据为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["数据日期", "日期"], df) or df.columns[0]
    df["date"] = pd.to_datetime(df[date_col].astype(str).apply(normalize_date), errors="coerce")
    today = pd.Timestamp.now().normalize()
    df = df[df["date"] <= today].sort_values("date").reset_index(drop=True)
    return df


def _valuation_percentile(series: pd.Series, current: float):
    """计算当前值在序列中的历史分位（0-1），序列需为正且样本足够。"""
    s = series.dropna()
    s = s[s > 0]
    if len(s) < 60 or pd.isna(current) or current <= 0:
        return None
    return float((s <= current).mean())


def compute_valuation_em(code: str):
    """优先使用东财估值接口计算 PE/PB 及历史分位。"""
    df = fetch_valuation_em(code)
    pe_col = _find_col(["PE(TTM)", "PE"], df)
    pb_col = _find_col(["市净率", "PB"], df)
    if pe_col is None or pb_col is None:
        raise RuntimeError("估值表缺少 PE/PB 列")

    pe = _to_numeric_series(df[pe_col])
    pb = _to_numeric_series(df[pb_col])
    current_pe = float(pe.iloc[-1]) if not pe.empty else float("nan")
    current_pb = float(pb.iloc[-1]) if not pb.empty else float("nan")

    pe_pct = _valuation_percentile(pe, current_pe)
    pb_pct = _valuation_percentile(pb, current_pb)
    return current_pe, pe_pct, current_pb, pb_pct, "东财估值(akshare.stock_value_em)", ""


def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """主要财务指标（年报 + 季报）。"""
    start_year = pd.Timestamp.now().year - YEARS - 2
    df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=str(start_year)))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("财务指标为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df) or df.columns[0]
    df["date"] = pd.to_datetime(df[date_col].astype(str).apply(normalize_date), errors="coerce")
    today = pd.Timestamp.now().normalize()
    df = df[df["date"] <= today].sort_values("date").reset_index(drop=True)
    return df


def compute_valuation_fallback(code: str, daily_df: pd.DataFrame):
    """东财估值失败时，用新浪财报 + 日线估算 PE/PB 及历史分位。"""
    fin = fetch_financial_indicator(code)
    eps_col = _find_col(["摊薄每股收益"], fin)
    bps_col = _find_col(["每股净资产_调整后", "每股净资产_调整前", "每股净资产"], fin)
    if eps_col is None or bps_col is None:
        raise RuntimeError("财务指标缺少每股收益/每股净资产列")

    fin["eps"] = _to_numeric_series(fin[eps_col])
    fin["bps"] = _to_numeric_series(fin[bps_col])
    fin_annual = fin[fin["date"].astype(str).str.endswith("12-31")].copy()
    if fin_annual.empty:
        raise RuntimeError("无年度财务数据")

    pe_records, pb_records = [], []
    for _, row in fin_annual.iterrows():
        eps, bps, rpt_date = row["eps"], row["bps"], row["date"]
        if pd.isna(eps) or eps <= 0 or pd.isna(bps) or bps <= 0:
            continue
        # 取年报日期之后的第一个交易日收盘价
        future = daily_df[daily_df["date"] >= rpt_date]
        if future.empty:
            continue
        close = float(future["close"].iloc[0])
        pe_records.append((rpt_date, safe_div(close, eps)))
        pb_records.append((rpt_date, safe_div(close, bps)))

    if len(pe_records) < 4:
        raise RuntimeError("年报+日线计算的估值样本不足")

    pe_series = pd.Series([v for _, v in pe_records])
    pb_series = pd.Series([v for _, v in pb_records])

    # 当前：用最新一期财务数据 + 最新收盘价
    latest_eps = float(fin["eps"].dropna().iloc[-1])
    latest_bps = float(fin["bps"].dropna().iloc[-1])
    latest_close = float(daily_df["close"].iloc[-1])
    current_pe = safe_div(latest_close, latest_eps)
    current_pb = safe_div(latest_close, latest_bps)

    pe_pct = _valuation_percentile(pe_series, current_pe)
    pb_pct = _valuation_percentile(pb_series, current_pb)
    note = "东财估值接口不可用，改用年报 EPS/BPS + 日线收盘价估算"
    return current_pe, pe_pct, current_pb, pb_pct, "新浪财报+日线(降级)", note


def compute_valuation(code: str, daily_df: pd.DataFrame):
    """计算估值与历史分位，优先东财，失败降级。"""
    try:
        return compute_valuation_em(code)
    except Exception as e:
        try:
            return compute_valuation_fallback(code, daily_df)
        except Exception as e2:
            raise RuntimeError(f"估值计算失败: 东财 {e}; 降级 {e2}")


def compute_price_metrics(daily_df: pd.DataFrame) -> dict:
    """基于日线计算 52 周位置、成交量萎缩、企稳信号。"""
    if daily_df.empty or len(daily_df) < TRADING_DAYS_YEAR:
        return {}

    last_year = daily_df.tail(TRADING_DAYS_YEAR)
    close = float(daily_df["close"].iloc[-1])
    low_52w = float(last_year["close"].min())
    high_52w = float(last_year["close"].max())

    position_ratio = safe_div(close - low_52w, high_52w - low_52w, default=float("nan"))
    dist_low_pct = safe_div(close, low_52w, default=float("nan"))
    dist_low_pct = (dist_low_pct - 1) * 100 if not pd.isna(dist_low_pct) else float("nan")
    dist_high_pct = safe_div(high_52w, close, default=float("nan"))
    dist_high_pct = (dist_high_pct - 1) * 100 if not pd.isna(dist_high_pct) else float("nan")

    # 成交量：近 5 日 vs 前 20 日（不含近 5 日）
    recent5 = daily_df.tail(5)["volume"]
    prior20 = daily_df.iloc[-25:-5]["volume"]
    vol_ratio = safe_div(recent5.mean(), prior20.mean(), default=float("nan"))
    volume_contracted = bool(not pd.isna(vol_ratio) and vol_ratio < 0.5)

    # 企稳：近 5 日最低价未跌破前 20 日最低价，且收盘价波动率较低
    recent5_close = daily_df.tail(5)["close"]
    prior20_low = float(daily_df.iloc[-25:-5]["close"].min()) if len(daily_df) >= 25 else float("nan")
    no_new_low = bool(not pd.isna(prior20_low) and float(recent5_close.min()) >= prior20_low * 0.98)
    low_volatility = bool(recent5_close.std() / close < 0.03) if close > 0 else False
    price_stabilized = no_new_low and low_volatility

    return {
        "close": round(close, 2),
        "wk52_low": round(low_52w, 2),
        "wk52_high": round(high_52w, 2),
        "position_ratio": round(position_ratio, 3) if not pd.isna(position_ratio) else None,
        "dist_low_pct": round(dist_low_pct, 2) if not pd.isna(dist_low_pct) else None,
        "dist_high_pct": round(dist_high_pct, 2) if not pd.isna(dist_high_pct) else None,
        "vol_ratio": round(vol_ratio, 3) if not pd.isna(vol_ratio) else None,
        "volume_contracted": volume_contracted,
        "price_stabilized": price_stabilized,
    }


def fetch_sina_income(code: str) -> pd.DataFrame:
    """新浪利润表（年报）。"""
    df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol="利润表"))
    time.sleep(0.15)
    if df is None or df.empty or "报告日" not in df.columns:
        raise RuntimeError("新浪利润表为空或格式异常")
    df = df.copy()
    df["报告日"] = df["报告日"].astype(str).apply(normalize_date)
    df["date"] = pd.to_datetime(df["报告日"], errors="coerce")
    today = pd.Timestamp.now().normalize()
    df = df[(df["date"].astype(str).str.endswith("12-31")) & (df["date"] <= today)]
    df = df.sort_values("date").reset_index(drop=True)
    return df


def compute_profit(code: str) -> tuple:
    """返回最新年度净利润（亿元）与来源说明。"""
    try:
        inc = fetch_sina_income(code)
        profit_col = _find_col(["净利润"], inc)
        if profit_col is None:
            raise RuntimeError("利润表缺少净利润列")
        latest_profit = _to_numeric_series(inc[profit_col]).dropna().iloc[-1]
        return float(latest_profit) / 1e8, "新浪利润表"
    except Exception as e:
        raise RuntimeError(f"净利润获取失败: {e}")


def score_one(code: str, name_map: dict) -> dict:
    note_parts = []

    daily_df = fetch_daily(code)
    if daily_df.empty:
        raise RuntimeError("日线数据获取失败")

    price_metrics = compute_price_metrics(daily_df)
    if not price_metrics:
        raise RuntimeError("日线数据不足一年，无法计算 52 周指标")

    time.sleep(0.15)
    pe_ttm, pe_pct, pb, pb_pct, val_source, val_note = compute_valuation(code, daily_df)
    if val_note:
        note_parts.append(val_note)

    time.sleep(0.15)
    profit_latest, profit_source = compute_profit(code)

    # 打分
    score = 0
    signals = []

    pos = price_metrics.get("position_ratio")
    dist_low = price_metrics.get("dist_low_pct")
    if pos is not None and pos <= 0.15:
        score += 30
        signals.append("52周底部区")
    elif pos is not None and pos <= 0.25:
        score += 25
        signals.append("52周低位")
    elif pos is not None and pos <= 0.40:
        score += 15
        signals.append("52周偏低")
    elif dist_low is not None and dist_low <= 10:
        score += 15
        signals.append("距52周低点<10%")

    pe_low = pe_pct is not None and pe_pct < 0.10
    pb_low = pb_pct is not None and pb_pct < 0.10
    if pe_low and pb_low:
        score += 30
        signals.append("PE/PB双历史低位")
    elif pe_low or pb_low:
        score += 20
        signals.append("PE或PB历史低位")

    if price_metrics.get("volume_contracted") and price_metrics.get("price_stabilized"):
        score += 20
        signals.append("缩量企稳")
    elif price_metrics.get("volume_contracted"):
        score += 10
        signals.append("成交萎缩")

    if profit_latest is not None and profit_latest > 0:
        score += 20
        signals.append("盈利为正")
    else:
        note_parts.append("最新年度净利润非正，请注意是否为真困境股")

    return {
        "code": code,
        "name": name_map.get(code, code),
        "close": price_metrics["close"],
        "wk52_low": price_metrics["wk52_low"],
        "wk52_high": price_metrics["wk52_high"],
        "position_ratio": price_metrics["position_ratio"],
        "dist_low_pct": price_metrics["dist_low_pct"],
        "dist_high_pct": price_metrics["dist_high_pct"],
        "pe_ttm": round(pe_ttm, 2) if not pd.isna(pe_ttm) else None,
        "pe_pct": round(pe_pct, 3) if pe_pct is not None else None,
        "pb": round(pb, 2) if not pd.isna(pb) else None,
        "pb_pct": round(pb_pct, 3) if pb_pct is not None else None,
        "vol_ratio": price_metrics["vol_ratio"],
        "volume_contracted": price_metrics["volume_contracted"],
        "price_stabilized": price_metrics["price_stabilized"],
        "profit_latest_亿": round(profit_latest, 2) if profit_latest is not None else None,
        "score": score,
        "signals": "、".join(signals) if signals else "—",
        "val_source": val_source,
        "profit_source": profit_source,
        "note": "；".join(note_parts) if note_parts else "",
    }


def main():
    ap = argparse.ArgumentParser(description="约翰·邓普顿全球逆向投资法 A 股初筛")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="templeton_contrarian_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    print(f"股票池共 {len(codes)} 只，开始扫描邓普顿式极度悲观信号...")

    name_map = build_name_map()

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, name_map)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} 得分 {r['score']} | 信号: {r['signals']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "code", "name", "close", "wk52_low", "wk52_high", "position_ratio",
        "pe_ttm", "pe_pct", "pb", "pb_pct", "vol_ratio", "profit_latest_亿", "score", "signals",
    ]
    display_df = df.head(args.top)[display_cols].copy()
    for c in ["pe_ttm", "pe_pct", "pb", "pb_pct", "vol_ratio", "profit_latest_亿", "position_ratio"]:
        display_df[c] = display_df[c].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
    print(display_df.to_string(index=False))

    high_score = df[df["score"] >= 60]
    if not high_score.empty:
        print(f"\n强逆向信号（>=60 分）: {len(high_score)} 只，建议结合基本面深入研究后再纳入观察清单。")
    else:
        print("\n本池暂无明显强逆向信号股（>=60 分），建议扩大股票池或等待更悲观的市场情绪。")

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    if failed:
        print("失败代码: " + ", ".join(f"{c}({e})" for c, e in failed[:5]))
    print("判定线: >=60 分进入观察清单；40-59 分可跟踪；<40 分暂不符合邓普顿极端悲观框架。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
