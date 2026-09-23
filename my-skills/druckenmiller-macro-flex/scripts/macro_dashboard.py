#!/usr/bin/env python3
"""macro_dashboard.py — 德鲁肯米勒式宏观灵活策略仪表盘。

用法:
    python scripts/macro_dashboard.py
    python scripts/macro_dashboard.py --days 20 --out macro_dashboard.csv
    python scripts/macro_dashboard.py --days 20 --codes 600519,000858,600036 --out result.csv

输出: 美元/人民币汇率、中美10年国债收益率、黄金、原油、铜、A股主要指数
      及可选个股的 N 日趋势与动量快照（趋势跟随视角）。
数据源: akshare 公开接口；默认禁用系统代理，东财接口失败时自动降级到新浪/中行/同花顺。
"""
import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta

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


TQDM_DISABLE = os.environ.get("TQDM_DISABLE", "1")

A_INDEX_CONFIG = [
    {"name": "上证指数", "code": "sh000001", "em_symbol": "000001"},
    {"name": "沪深300", "code": "sh000300", "em_symbol": "000300"},
    {"name": "深证成指", "code": "sz399001", "em_symbol": "399001"},
    {"name": "创业板指", "code": "sz399006", "em_symbol": "399006"},
    {"name": "科创50", "code": "sh000688", "em_symbol": "000688"},
]


# -----------------------------------------------------------------------------
# 基础设施
# -----------------------------------------------------------------------------

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


def _sleep():
    """调用间短暂休眠，降低被数据源限流的概率。"""
    time.sleep(0.15)


def normalize_date(date_str: str) -> str:
    """兼容 20231231 与 2023-12-31 两种格式，统一返回 2023-12-31。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return date_str


def safe_pct(numerator, denominator):
    """除零防护的百分比变化计算。"""
    try:
        if denominator is None or numerator is None:
            return float("nan")
        d = float(denominator)
        if d == 0 or pd.isna(d):
            return float("nan")
        return (float(numerator) - d) / d * 100
    except Exception:
        return float("nan")


def safe_div(a, b):
    """除零防护的除法。"""
    try:
        if b == 0 or pd.isna(b):
            return float("nan")
        return float(a) / float(b)
    except Exception:
        return float("nan")


def parse_date_series(series) -> pd.Series:
    """把可能是字符串或 datetime.date 的序列统一转成 datetime。"""
    s = pd.to_datetime(series, errors="coerce")
    if s.isna().all():
        s = series.astype(str).apply(lambda x: normalize_date(x))
        s = pd.to_datetime(s, errors="coerce")
    return s


# -----------------------------------------------------------------------------
# 数据获取（每个函数内部先尝试东财/首选接口，失败自动降级）
# -----------------------------------------------------------------------------

def fetch_usdcny(days: int) -> tuple[pd.DataFrame, str]:
    """获取 USD/CNY 历史日线。优先中行外汇牌价，失败时降级为即期快照。"""
    end = datetime.now()
    start = end - timedelta(days=max(days + 30, 90))
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    try:
        df = _retry_call(lambda: ak.currency_boc_sina(symbol="美元", start_date=start_str, end_date=end_str))
        _sleep()
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            df = df.rename(columns={df.columns[0]: "date", df.columns[1]: "open", df.columns[2]: "close"})
            df["date"] = parse_date_series(df["date"])
            df["close"] = pd.to_numeric(df["close"], errors="coerce") / 100.0
            df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
            if not df.empty:
                return df[["date", "close"]], "currency_boc_sina"
    except Exception as e:
        print(f"  中行 USD/CNY 历史接口失败: {e}", file=sys.stderr)

    try:
        df = _retry_call(lambda: ak.fx_spot_quote())
        _sleep()
        if df is not None and not df.empty:
            row = df[df.iloc[:, 0].astype(str).str.contains("USD/CNY", na=False)]
            if not row.empty:
                val = pd.to_numeric(row.iloc[0, 1], errors="coerce")
                today = pd.Timestamp.now().normalize()
                return pd.DataFrame({"date": [today], "close": [val]}), "fx_spot_quote(快照)"
    except Exception as e:
        print(f"  外汇即期报价接口失败: {e}", file=sys.stderr)

    raise RuntimeError("USD/CNY 数据获取失败")


def fetch_bond_yields() -> tuple[pd.DataFrame, str]:
    """获取中美 10 年期国债收益率。优先 bond_zh_us_rate，失败降级 bond_china_yield。"""
    try:
        df = _retry_call(lambda: ak.bond_zh_us_rate())
        _sleep()
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            cutoff = date.today()
            df["date"] = parse_date_series(df.iloc[:, 0])
            df = df[df["date"] <= pd.Timestamp(cutoff)].copy()
            # 列顺序：日期, 中国2Y, 中国5Y, 中国10Y, 中国30Y, ... 美国2Y, 美国5Y, 美国10Y, ...
            cols = df.columns.tolist()
            rename = {}
            if len(cols) >= 4:
                rename[cols[3]] = "china_10y"
            if len(cols) >= 10:
                rename[cols[9]] = "us_10y"
            df = df.rename(columns=rename)
            df["china_10y"] = pd.to_numeric(df["china_10y"], errors="coerce")
            df["us_10y"] = pd.to_numeric(df["us_10y"], errors="coerce")
            df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
            if not df.empty and not df[["china_10y", "us_10y"]].isna().all().all():
                return df[["date", "china_10y", "us_10y"]], "bond_zh_us_rate"
    except Exception as e:
        print(f"  bond_zh_us_rate 接口失败: {e}", file=sys.stderr)

    try:
        end = datetime.now()
        start = end - timedelta(days=365)
        df = _retry_call(lambda: ak.bond_china_yield(start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d")))
        _sleep()
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            # 筛选国债收益率曲线行
            type_col = df.columns[0]
            treasury = df[df[type_col].astype(str).str.contains("国债", na=False)].copy()
            if not treasury.empty:
                date_col = df.columns[1]
                ten_y_col = df.columns[-2]  # 10年列通常在倒数第二
                treasury = treasury.rename(columns={date_col: "date", ten_y_col: "china_10y"})
                treasury["date"] = parse_date_series(treasury["date"])
                treasury["china_10y"] = pd.to_numeric(treasury["china_10y"], errors="coerce")
                treasury["us_10y"] = float("nan")
                return treasury[["date", "china_10y", "us_10y"]].sort_values("date").reset_index(drop=True), "bond_china_yield(仅中债)"
    except Exception as e:
        print(f"  bond_china_yield 接口失败: {e}", file=sys.stderr)

    raise RuntimeError("国债收益率数据获取失败")


def fetch_commodity_hist(symbol: str, name: str) -> tuple[pd.DataFrame, str]:
    """通过 Sina 获取国际期货历史日线（GC 黄金 / CL 原油 / HG 铜）。"""
    df = _retry_call(lambda: ak.futures_foreign_hist(symbol=symbol))
    _sleep()
    if df is None or df.empty:
        raise RuntimeError(f"{name} 历史数据为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "date" not in df.columns or "close" not in df.columns:
        raise RuntimeError(f"{name} 数据列异常")
    df["date"] = parse_date_series(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
    return df[["date", "close"]], f"futures_foreign_hist({symbol})"


def fetch_gold() -> tuple[pd.DataFrame, str]:
    """黄金历史日线；优先 COMEX 黄金，失败降级上海金。"""
    try:
        return fetch_commodity_hist("GC", "黄金")
    except Exception as e:
        print(f"  COMEX 黄金接口失败，降级上海金: {e}", file=sys.stderr)
    try:
        df = _retry_call(lambda: ak.spot_golden_benchmark_sge())
        _sleep()
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            df = df.rename(columns={df.columns[0]: "date", df.columns[2]: "close"})
            df["date"] = parse_date_series(df["date"])
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
            if not df.empty:
                return df[["date", "close"]], "spot_golden_benchmark_sge"
    except Exception as e:
        print(f"  上海金接口失败: {e}", file=sys.stderr)
    raise RuntimeError("黄金数据获取失败")


def fetch_oil() -> tuple[pd.DataFrame, str]:
    return fetch_commodity_hist("CL", "原油")


def fetch_copper() -> tuple[pd.DataFrame, str]:
    return fetch_commodity_hist("HG", "铜")


def fetch_a_index(config: dict, days: int) -> tuple[pd.DataFrame, str]:
    """A股指数日线；优先新浪，失败降级东财。"""
    try:
        df = _retry_call(lambda: ak.stock_zh_index_daily(symbol=config["code"]))
        _sleep()
        if df is not None and not df.empty:
            df = df.copy()
            df.columns = [str(c).strip() for c in df.columns]
            df["date"] = parse_date_series(df["date"])
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
            if not df.empty:
                return df[["date", "close"]], "stock_zh_index_daily(Sina)"
    except Exception as e:
        print(f"  {config['name']} 新浪接口失败，降级东财: {e}", file=sys.stderr)

    try:
        end = datetime.now()
        start = end - timedelta(days=max(days + 60, 365))
        df = _retry_call(
            lambda: ak.index_zh_a_hist(
                symbol=config["em_symbol"],
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
            )
        )
        _sleep()
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            df = df.rename(columns={df.columns[0]: "date", df.columns[2]: "close"})
            df["date"] = parse_date_series(df["date"])
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
            if not df.empty:
                return df[["date", "close"]], "index_zh_a_hist(EM)"
    except Exception as e:
        print(f"  {config['name']} 东财接口失败: {e}", file=sys.stderr)

    raise RuntimeError(f"{config['name']} 数据获取失败")


def fetch_stock(code: str, days: int) -> tuple[pd.DataFrame, str]:
    """个股日线；使用新浪前复权数据。"""
    symbol = ("sh" if code.startswith("6") else "sz") + code
    df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=symbol, adjust="qfq"))
    _sleep()
    if df is None or df.empty:
        raise RuntimeError(f"{code} 数据为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = parse_date_series(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
    return df[["date", "close"]], "stock_zh_a_daily(Sina)"


# -----------------------------------------------------------------------------
# 趋势与动量计算
# -----------------------------------------------------------------------------

def calc_trend(df: pd.DataFrame, days: int) -> dict:
    """计算某资产近 N 日的趋势与动量指标。"""
    if df is None or df.empty or len(df) < 5:
        return {
            "current": None,
            "ma": None,
            "roc": None,
            "roc_5": None,
            "trend": "数据不足",
            "signal": "NEUTRAL",
            "bias": "中性",
        }

    df = df.copy().sort_values("date").reset_index(drop=True)
    if len(df) < days:
        days = len(df) - 1
    if days < 2:
        days = min(5, len(df) - 1)

    current = float(df["close"].iloc[-1])
    prev_n = float(df["close"].iloc[-(days + 1)])
    prev_5 = float(df["close"].iloc[-min(6, len(df))])

    window = df["close"].tail(days)
    ma = float(window.mean())
    roc = safe_pct(current, prev_n)
    roc_5 = safe_pct(current, prev_5)

    if current > ma and roc > 0:
        trend = "上升"
        signal = "BULLISH"
    elif current < ma and roc < 0:
        trend = "下降"
        signal = "BEARISH"
    else:
        trend = "震荡/拐点"
        signal = "NEUTRAL"

    return {
        "current": round(current, 4),
        "ma": round(ma, 4),
        "roc": round(roc, 2),
        "roc_5": round(roc_5, 2),
        "trend": trend,
        "signal": signal,
    }


def fmt_signal_for_commodity(signal: str, name: str) -> str:
    """把趋势信号转译为多空倾向描述。"""
    if signal == "BULLISH":
        return f"{name}偏多"
    if signal == "BEARISH":
        return f"{name}偏空"
    return f"{name}中性"


def build_asset_row(name: str, category: str, df: pd.DataFrame, days: int, source: str) -> dict:
    """为某类资产构造一行宏观快照。"""
    calc = calc_trend(df, days)
    if category == "fx":
        bias = fmt_signal_for_commodity(calc["signal"], "美元") if calc["signal"] != "NEUTRAL" else "USD/CNY 中性"
    elif category == "bond_cn":
        # 收益率上行 = 债券价格下跌 = 中债偏空
        if calc["signal"] == "BULLISH":
            bias = "中债偏空（收益率上行）"
        elif calc["signal"] == "BEARISH":
            bias = "中债偏多（收益率下行）"
        else:
            bias = "中债中性"
    elif category == "bond_us":
        if calc["signal"] == "BULLISH":
            bias = "美债偏空（收益率上行）"
        elif calc["signal"] == "BEARISH":
            bias = "美债偏多（收益率下行）"
        else:
            bias = "美债中性"
    elif category == "equity":
        bias = fmt_signal_for_commodity(calc["signal"], "A股") if calc["signal"] != "NEUTRAL" else "A股中性"
    else:
        bias = fmt_signal_for_commodity(calc["signal"], name) if calc["signal"] != "NEUTRAL" else f"{name}中性"

    return {
        "asset": name,
        "category": category,
        "current": calc["current"],
        "ma_n": calc["ma"],
        "roc_n": calc["roc"],
        "roc_5": calc["roc_5"],
        "trend": calc["trend"],
        "signal": calc["signal"],
        "bias": bias,
        "source": source,
    }


# -----------------------------------------------------------------------------
# 主流程
# -----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="德鲁肯米勒式宏观灵活策略仪表盘")
    ap.add_argument("--days", type=int, default=20, help="趋势与动量计算窗口（默认 20 日）")
    ap.add_argument("--codes", default=None, help="可选：逗号分隔的 A 股个股代码，如 600519,000858,600036")
    ap.add_argument("--out", default="macro_dashboard.csv", help="CSV 输出路径（默认 macro_dashboard.csv）")
    ap.add_argument("--no-proxy", action="store_true", help="禁用系统代理（脚本已默认禁用，保留兼容参数）")
    args = ap.parse_args()

    _disable_proxies()
    if args.no_proxy:
        _disable_proxies()

    days = max(2, args.days)
    data_date = datetime.now().strftime("%Y-%m-%d")
    rows = []
    failed = []

    print(f"=== 德鲁肯米勒宏观仪表盘 | 数据日期 {data_date} | 窗口 {days} 日 ===\n")

    # 1. USD/CNY
    print("[1/7] 获取 USD/CNY ...")
    try:
        df, src = fetch_usdcny(days)
        rows.append(build_asset_row("USD/CNY", "fx", df, days, src))
        print(f"  当前: {rows[-1]['current']} | 来源: {src}")
    except Exception as e:
        failed.append(("USD/CNY", str(e)))
        print(f"  失败: {e}", file=sys.stderr)

    # 2. 中美 10Y 国债
    print("[2/7] 获取中美 10 年国债收益率 ...")
    try:
        df, src = fetch_bond_yields()
        if "china_10y" in df.columns and not df["china_10y"].isna().all():
            rows.append(build_asset_row("中国10Y国债", "bond_cn", df.assign(close=df["china_10y"]), days, src))
            print(f"  中国10Y: {rows[-1]['current']}% | 来源: {src}")
        if "us_10y" in df.columns and not df["us_10y"].isna().all():
            rows.append(build_asset_row("美国10Y国债", "bond_us", df.assign(close=df["us_10y"]), days, src))
            print(f"  美国10Y: {rows[-1]['current']}% | 来源: {src}")
    except Exception as e:
        failed.append(("中美10Y国债", str(e)))
        print(f"  失败: {e}", file=sys.stderr)

    # 3. 黄金
    print("[3/7] 获取黄金价格 ...")
    try:
        df, src = fetch_gold()
        rows.append(build_asset_row("黄金", "commodity", df, days, src))
        print(f"  当前: {rows[-1]['current']} | 来源: {src}")
    except Exception as e:
        failed.append(("黄金", str(e)))
        print(f"  失败: {e}", file=sys.stderr)

    # 4. 原油
    print("[4/7] 获取原油价格 ...")
    try:
        df, src = fetch_oil()
        rows.append(build_asset_row("原油", "commodity", df, days, src))
        print(f"  当前: {rows[-1]['current']} | 来源: {src}")
    except Exception as e:
        failed.append(("原油", str(e)))
        print(f"  失败: {e}", file=sys.stderr)

    # 5. 铜
    print("[5/7] 获取铜价格 ...")
    try:
        df, src = fetch_copper()
        rows.append(build_asset_row("铜", "commodity", df, days, src))
        print(f"  当前: {rows[-1]['current']} | 来源: {src}")
    except Exception as e:
        failed.append(("铜", str(e)))
        print(f"  失败: {e}", file=sys.stderr)

    # 6. A 股指数
    print("[6/7] 获取 A 股主要指数 ...")
    for cfg in A_INDEX_CONFIG:
        try:
            df, src = fetch_a_index(cfg, days)
            rows.append(build_asset_row(cfg["name"], "equity", df, days, src))
            print(f"  {cfg['name']}: {rows[-1]['current']} | {rows[-1]['bias']} | 来源: {src}")
        except Exception as e:
            failed.append((cfg["name"], str(e)))
            print(f"  {cfg['name']} 失败: {e}", file=sys.stderr)

    # 7. 可选个股
    stock_rows = []
    if args.codes:
        print("[7/7] 获取个股趋势 ...")
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        for code in codes:
            try:
                df, src = fetch_stock(code, days)
                calc = calc_trend(df, days)
                stock_rows.append({
                    "asset": code,
                    "category": "stock",
                    "current": calc["current"],
                    "ma_n": calc["ma"],
                    "roc_n": calc["roc"],
                    "roc_5": calc["roc_5"],
                    "trend": calc["trend"],
                    "signal": calc["signal"],
                    "bias": fmt_signal_for_commodity(calc["signal"], code) if calc["signal"] != "NEUTRAL" else f"{code}中性",
                    "source": src,
                })
                print(f"  {code}: {stock_rows[-1]['current']} | {stock_rows[-1]['bias']}")
            except Exception as e:
                failed.append((code, str(e)))
                print(f"  {code} 失败: {e}", file=sys.stderr)

    if not rows and not stock_rows:
        sys.exit("ERROR: 所有资产均获取失败，请检查网络、akshare 版本或数据源状态")

    # 汇总输出
    all_rows = rows + stock_rows
    out_df = pd.DataFrame(all_rows)
    out_df["data_date"] = data_date
    out_df["window_days"] = days

    # 计算综合宏观得分（偏多 +1，偏空 -1，中性 0）
    score_map = {"BULLISH": 1, "BEARISH": -1, "NEUTRAL": 0}
    macro_score = sum(score_map.get(r["signal"], 0) for r in rows)
    total = len(rows)
    if total > 0:
        bullish = sum(1 for r in rows if r["signal"] == "BULLISH")
        bearish = sum(1 for r in rows if r["signal"] == "BEARISH")
        neutral = total - bullish - bearish
    else:
        bullish = bearish = neutral = 0

    print("\n=== 宏观快照表 ===")
    display_cols = ["asset", "current", "roc_n", "roc_5", "trend", "signal", "bias", "source"]
    print(out_df[display_cols].to_string(index=False))

    print(f"\n=== 综合趋势跟随打分 ===")
    print(f"偏多资产: {bullish} / {total} | 偏空资产: {bearish} / {total} | 中性: {neutral} / {total}")
    print(f"宏观得分: {macro_score}（区间 -{total} ~ +{total}）")
    if macro_score >= total * 0.4:
        stance = "整体偏多：趋势环境有利，可维持或增加风险敞口，但仍需资本保护纪律。"
    elif macro_score <= -total * 0.4:
        stance = "整体偏空：趋势环境不利，优先减仓/防守，等待流动性或价格企稳。"
    else:
        stance = "整体中性：方向不明，保持灵活，等待更清晰的信号再下重注。"
    print(f"趋势立场: {stance}")

    if failed:
        print(f"\n=== 失败项目 ===")
        for name, err in failed:
            print(f"  {name}: {err}")

    # 输出 CSV
    out_cols = [
        "data_date", "window_days", "asset", "category", "current", "ma_n",
        "roc_n", "roc_5", "trend", "signal", "bias", "source",
    ]
    out_df = out_df[[c for c in out_cols if c in out_df.columns]]
    out_df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"\n完整结果已写入: {args.out}")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。宏观趋势为滞后统计，任何结果都必须结合基本面与自身风险偏好二次确认。")


if __name__ == "__main__":
    main()
