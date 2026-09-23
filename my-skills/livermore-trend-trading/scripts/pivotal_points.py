#!/usr/bin/env python3
"""pivotal_points.py — A股利弗莫尔趋势投机关键点识别。

用法:
    python scripts/pivotal_points.py --codes 600519,000858,600036 --out signals.csv
    python scripts/pivotal_points.py --codes 600519,000858 --days 120 --window 30 --out signals.csv

输出: 信号表 + 金字塔仓位试探框架。
数据源: 优先 akshare 东方财富日线 (stock_zh_a_hist)，失败自动降级新浪日线 (stock_zh_a_daily)。
代理: 默认自动绕过系统代理，避免 127.0.0.1:7890 等本地代理阻断数据源。
"""
import os
import time

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import argparse
import sys
from typing import Optional

import pandas as pd
import requests

# 必须在 akshare 之前禁用系统代理，避免其缓存本地代理导致东财/新浪接口被阻断
for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
requests.utils.getproxies = lambda: {}

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


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理干扰东财/新浪直连。"""
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
    """兼容 20231231 与 2023-12-31 两种格式，统一返回 2023-12-31。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return date_str


def _safe_div(a, b, default=float("nan")):
    """除零保护。"""
    try:
        if b and b != 0:
            return a / b
    except Exception:
        pass
    return default


# ---------------------------------------------------------------------------
# 数据获取
# ---------------------------------------------------------------------------


def _rename_em_cols(df: pd.DataFrame) -> pd.DataFrame:
    """统一日线列名。优先识别中文（东方财富）或英文（新浪）表头，否则按位置兜底。"""
    rename_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "换手率": "turnover",
        "振幅": "amplitude",
        "股票代码": "code",
    }
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # 新浪接口已返回英文列名，直接保留
    english_core = {"date", "open", "high", "low", "close", "volume"}
    if english_core.issubset(set(df.columns)):
        return df

    # 东方财富中文列名映射
    if any(c in df.columns for c in rename_map):
        df = df.rename(columns=rename_map)
        return df

    # 兜底：按东方财富常见返回顺序
    default_cols = ["date", "code", "open", "close", "high", "low", "volume", "amount", "amplitude", "pct_change", "change", "turnover"]
    for i, c in enumerate(default_cols):
        if i < len(df.columns):
            df.rename(columns={df.columns[i]: c}, inplace=True)
    return df


def _clean_daily(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """清洗日线表：统一列名、类型、排序，取近 days 根K线。"""
    if df is None or df.empty:
        raise ValueError("日线数据为空")
    df = _rename_em_cols(df)

    if "date" not in df.columns:
        raise ValueError(f"日线数据缺少 date 列，现有列: {df.columns.tolist()}")

    df["date"] = df["date"].astype(str).apply(normalize_date)
    df = df.sort_values("date").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close", "volume"])
    if df.empty:
        raise ValueError("清洗后日线数据为空")

    return df.tail(days).reset_index(drop=True)


def fetch_daily_em(code: str, days: int) -> pd.DataFrame:
    """东方财富日线接口。"""
    end = pd.Timestamp.now()
    start = end - pd.Timedelta(days=int(days * 1.5) + 60)
    df = _retry_call(
        lambda: ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
    )
    return _clean_daily(df, days)


def fetch_daily_sina(code: str, days: int) -> pd.DataFrame:
    """新浪财经日线接口（降级）。"""
    symbol = ("sh" if code.startswith("6") else "sz") + code
    df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=symbol, adjust="qfq"))
    return _clean_daily(df, days)


def fetch_daily(code: str, days: int) -> pd.DataFrame:
    """优先东财，失败降级新浪。"""
    try:
        df = fetch_daily_em(code, days)
        return df
    except Exception as e:
        print(f"  {code} 东方财富日线失败，降级新浪: {e}", file=sys.stderr)
        time.sleep(0.15)
    try:
        df = fetch_daily_sina(code, days)
        return df
    except Exception as e:
        raise RuntimeError(f"获取 {code} 日线失败（东财/新浪均不可用）: {e}")


def load_name_map() -> dict:
    """加载全市场代码-名称映射。"""
    try:
        df = _retry_call(lambda: ak.stock_info_a_code_name())
        time.sleep(0.15)
        if df is None or df.empty or "code" not in df.columns or "name" not in df.columns:
            return {}
        df["code"] = df["code"].astype(str).str.strip().str.zfill(6)
        df["name"] = df["name"].astype(str).str.strip()
        return dict(zip(df["code"], df["name"]))
    except Exception as e:
        print(f"WARN: 股票名称映射获取失败: {e}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# 指标与信号
# ---------------------------------------------------------------------------


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """加入均线、均量、前收等辅助列。"""
    for n in (5, 10, 20, 60):
        df[f"ma{n}"] = df["close"].rolling(n).mean()
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["prev_close"] = df["close"].shift(1)
    df["range"] = df["high"] - df["low"]
    df["upper_shadow"] = df["high"] - df[["close", "open"]].max(axis=1)
    df["lower_shadow"] = df[["close", "open"]].min(axis=1) - df["low"]
    df["close_chg_pct"] = (df["close"] - df["prev_close"]) / df["prev_close"].where(df["prev_close"] > 0, float("nan")) * 100
    return df


def detect_signals(df: pd.DataFrame, window: int) -> tuple:
    """对最后一根K线做利弗莫尔式信号判定。

    返回: (signals_list, window_high, position_plan)
    """
    min_len = max(65, window + 2)
    if len(df) < min_len:
        return ["INSUFFICIENT_DATA"], float("nan"), "数据不足：空仓观察，等待信号"

    row = df.iloc[-1]
    prev = df.iloc[-2]

    # 关键价位
    prev_closes = df["close"].iloc[: -1]
    window_high = prev_closes.tail(window).max() if len(prev_closes) >= window else prev_closes.max()
    prev_highs = df["high"].iloc[: -1]
    window_high_bar = prev_highs.tail(window).max() if len(prev_highs) >= window else prev_highs.max()

    vol_ratio = _safe_div(row["volume"], row["vol_ma20"])

    # 均线状态
    ma_bull = (
        row["ma5"] > row["ma10"] > row["ma20"] > row["ma60"]
        if pd.notna(row["ma60"])
        else False
    )
    near_ma20 = abs(row["close"] / row["ma20"] - 1) <= 0.02 if pd.notna(row["ma20"]) else False
    above_ma20 = row["close"] > row["ma20"] if pd.notna(row["ma20"]) else False

    signals = []

    # 1) N日新高突破
    new_high_close = row["close"] > window_high
    if new_high_close:
        if vol_ratio >= 1.5:
            signals.append("KEY_BREAKOUT")
        else:
            signals.append("WEAK_BREAKOUT")

    # 2) 缩量回踩二次入场（前提：趋势多头排列）
    if ma_bull and near_ma20 and above_ma20 and (vol_ratio <= 0.8) and "KEY_BREAKOUT" not in signals:
        signals.append("PULLBACK_ENTRY")

    # 3) 危险信号：单日反转
    new_intraday_high = row["high"] > window_high_bar
    upper_ratio = _safe_div(row["upper_shadow"], row["range"])
    lower_ratio = _safe_div(row["lower_shadow"], row["range"])
    bearish_close = row["close"] < row["open"]
    if new_intraday_high and bearish_close and upper_ratio >= 0.65 and vol_ratio >= 1.0:
        signals.append("ONE_DAY_REVERSAL")

    # 4) 危险信号：放量滞涨
    small_change = abs(row["close_chg_pct"]) <= 1.0
    if vol_ratio >= 1.8 and small_change and upper_ratio >= 0.35 and "KEY_BREAKOUT" not in signals:
        signals.append("VOLUME_STAGNATION")

    if not signals:
        signals.append("NO_SIGNAL")

    # 仓位计划：按优先级给出一条主建议
    priority = ["ONE_DAY_REVERSAL", "VOLUME_STAGNATION", "KEY_BREAKOUT", "WEAK_BREAKOUT", "PULLBACK_ENTRY", "NO_SIGNAL"]
    dominant = next((s for s in priority if s in signals), "NO_SIGNAL")
    plan = {
        "KEY_BREAKOUT": (
            "最小阻力向上突破：试探仓 20%，突破回踩不破+放量确认后加仓至 40%；"
            "止损设于关键点下方 3-5%"
        ),
        "PULLBACK_ENTRY": (
            "趋势中缩量回踩：加仓/建仓 20-30%，止损设于 MA20/前低下方"
        ),
        "WEAK_BREAKOUT": (
            "无量突破需警惕：暂不追，等待放量确认或回踩后再决定"
        ),
        "ONE_DAY_REVERSAL": (
            "单日反转危险信号：减仓或观望，暂停新开仓"
        ),
        "VOLUME_STAGNATION": (
            "放量滞涨危险信号：减仓或观望，暂停新开仓"
        ),
        "NO_SIGNAL": (
            "无明确信号：空仓或轻仓观察"
        ),
        "INSUFFICIENT_DATA": (
            "数据不足：空仓观察，等待信号"
        ),
    }[dominant]

    return signals, window_high, plan


def analyze_one(code: str, name_map: dict, days: int, window: int) -> dict:
    df = fetch_daily(code, days)
    df = add_indicators(df)
    signals, window_high, plan = detect_signals(df, window)
    row = df.iloc[-1]

    dist_to_high = _safe_div(row["close"], window_high, float("nan"))
    dist_to_high_pct = (dist_to_high - 1) * 100 if dist_to_high and dist_to_high != float("nan") else float("nan")

    return {
        "code": code,
        "name": name_map.get(code, ""),
        "date": str(row["date"])[:10],
        "close": round(float(row["close"]), 2),
        "close_chg_pct": round(float(row["close_chg_pct"]), 2) if pd.notna(row["close_chg_pct"]) else None,
        "volume_ratio": round(float(_safe_div(row["volume"], row["vol_ma20"])), 2),
        "ma20": round(float(row["ma20"]), 2) if pd.notna(row["ma20"]) else None,
        "ma60": round(float(row["ma60"]), 2) if pd.notna(row["ma60"]) else None,
        "window_high": round(float(window_high), 2) if pd.notna(window_high) else None,
        "dist_to_high_pct": round(float(dist_to_high_pct), 2) if pd.notna(dist_to_high_pct) else None,
        "signals": ",".join(signals),
        "position_plan": plan,
    }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="A股利弗莫尔趋势投机关键点识别")
    ap.add_argument("--codes", required=True, help="逗号分隔的股票代码，如 600519,000858,600036")
    ap.add_argument("--days", type=int, default=250, help="取近 N 个交易日(默认250)")
    ap.add_argument("--window", type=int, default=60, help="N日新高突破窗口(默认60)")
    ap.add_argument("--out", default="livermore_signals.csv", help="CSV 输出路径")
    ap.add_argument("--no-proxy", action="store_true", help="禁用系统代理（默认已自动禁用，保留兼容参数）")
    args = ap.parse_args()

    # 默认绕过系统代理
    _disable_proxies()
    if args.no_proxy:
        _disable_proxies()

    codes = [c.strip().zfill(6) for c in args.codes.split(",") if c.strip()]
    if not codes:
        sys.exit("ERROR: --codes 不能为空")

    print(f"正在加载股票名称映射（akshare {ak.__version__}）...")
    name_map = load_name_map()

    rows, failed = [], []
    for code in codes:
        print(f"分析 {code} ...")
        try:
            r = analyze_one(code, name_map, args.days, args.window)
            rows.append(r)
            print(f"  {r['date']} 收盘 {r['close']} 量比 {r['volume_ratio']} 信号: {r['signals']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"  {code} 失败: {e}", file=sys.stderr)
        time.sleep(0.15)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代码或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print("\n=== 利弗莫尔趋势投机信号表 ===")
    display_cols = ["code", "name", "date", "close", "volume_ratio", "signals", "position_plan"]
    print(df[display_cols].to_string(index=False))
    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。完整结果已写入 {args.out}")
    if failed:
        print("失败明细:", failed, file=sys.stderr)
    print("免责声明：仅供学习研究，不构成投资建议。机械信号必须结合市场环境与风险管理综合判断。")


if __name__ == "__main__":
    main()
