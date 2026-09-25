#!/usr/bin/env python3
"""factor_scan.py — A股西蒙斯风格多因子打分器。

用法:
    python scripts/factor_scan.py --pool hs300 --top 20 --out result.csv
    python scripts/factor_scan.py --codes 600519,000858,600036 --top 10 --out result.csv

因子说明（西蒙斯/大奖章风格化学习框架）:
    1. 动量：20日、60日收益率，强势延续得分。
    2. 反转：5日超跌得分，短线均值回归候选。
    3. 波动率：20日收益率标准差，低波加分。
    4. 量能：近5日成交量 / 近20日成交量，放量趋势加分。
    5. 均线偏离度：收盘价偏离60日均线的绝对幅度，偏离越小得分越高。

数据源: akshare（优先东方财富日线，失败降级新浪日线）。
"""
import os

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import argparse
import sys
import time
import warnings
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

# 运行参数常量
MIN_DAYS = 65          # 至少保留 60 日用于计算 60 日收益与均线
DEFAULT_LOOKBACK = 150 # 默认抓取交易日数（约 7 个月）
FACTOR_WEIGHTS = {
    "momentum": 0.25,
    "reversal": 0.25,
    "volatility": 0.20,
    "volume": 0.15,
    "ma_deviation": 0.15,
}


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


def normalize_date_ak(date_str: str) -> str:
    """兼容 20231231 与 2023-12-31，统一返回 20231231（akshare 接口常用格式）。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return s
    # 尝试解析其它格式
    try:
        return pd.Timestamp(date_str).strftime("%Y%m%d")
    except Exception:
        return s


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


def add_exchange_prefix(code: str) -> str:
    """给 6 位代码加 sh/sz 前缀，供新浪日线接口使用。"""
    c = str(code).strip().zfill(6)
    if c.startswith(("6", "9")):
        return f"sh{c}"
    return f"sz{c}"


def _find_col(candidates: list, df: pd.DataFrame) -> Optional[str]:
    """按候选子串在 df 列名中查找第一个匹配列。"""
    for c in df.columns:
        for cand in candidates:
            if cand in str(c):
                return c
    return None


def fetch_hist_em(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """东方财富日线（前复权）。"""
    df = _retry_call(
        lambda: ak.stock_zh_a_hist(
            symbol=str(code).strip().zfill(6),
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
    )
    if df is None or df.empty:
        raise RuntimeError("东财日线返回为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df["date"] = pd.to_datetime(df[_find_col(["日期"], df) or df.columns[0]], errors="coerce")
    df["close"] = pd.to_numeric(df[_find_col(["收盘", "close"], df) or "收盘"], errors="coerce")
    df["volume"] = pd.to_numeric(df[_find_col(["成交量", "volume"], df) or "成交量"], errors="coerce")
    return df[["date", "close", "volume"]].dropna()


def fetch_hist_sina(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """新浪日线（未明确复权，作为降级来源）。"""
    df = _retry_call(
        lambda: ak.stock_zh_a_daily(
            symbol=add_exchange_prefix(code),
            start_date=start_date,
            end_date=end_date,
        )
    )
    if df is None or df.empty:
        raise RuntimeError("新浪日线返回为空")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df["date"] = pd.to_datetime(df[_find_col(["date", "日期"], df) or "date"], errors="coerce")
    df["close"] = pd.to_numeric(df[_find_col(["close", "收盘"], df) or "close"], errors="coerce")
    df["volume"] = pd.to_numeric(df[_find_col(["volume", "成交量"], df) or "volume"], errors="coerce")
    return df[["date", "close", "volume"]].dropna()


def fetch_hist(code: str, start_date: str, end_date: str) -> tuple:
    """获取日线，优先东财，失败降级新浪。返回 (df, source)。"""
    errs = []
    try:
        df = fetch_hist_em(code, start_date, end_date)
        time.sleep(0.15)
        return df, "akshare.stock_zh_a_hist（东财前复权）"
    except Exception as e:
        errs.append(f"东财: {e}")
        time.sleep(0.15)

    try:
        df = fetch_hist_sina(code, start_date, end_date)
        time.sleep(0.15)
        return df, "akshare.stock_zh_a_daily（新浪，降级）"
    except Exception as e:
        errs.append(f"新浪: {e}")

    raise RuntimeError("; ".join(errs))


def fetch_name_map() -> dict:
    """获取全市场代码 -> 名称映射（新浪行情接口）。"""
    try:
        df = _retry_call(lambda: ak.stock_zh_a_spot())
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    df.columns = [str(c).strip() for c in df.columns]
    code_col = _find_col(["代码", "code"], df) or df.columns[0]
    name_col = _find_col(["名称", "name"], df) or df.columns[1]
    df[code_col] = (
        df[code_col]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"^(sh|sz|bj)", "", regex=True)
        .str.zfill(6)
    )
    return dict(zip(df[code_col].tolist(), df[name_col].astype(str).tolist()))


def compute_factors(df: pd.DataFrame) -> dict:
    """由日线 DataFrame 计算原始因子值。"""
    df = df.sort_values("date").reset_index(drop=True)
    if len(df) < MIN_DAYS:
        raise RuntimeError(f"日线数据仅 {len(df)} 条，不足 {MIN_DAYS} 条")

    close = df["close"].astype(float)
    volume = df["volume"].astype(float)

    # 收益率
    ret_5d = safe_div(close.iloc[-1], close.iloc[-6]) - 1.0 if len(close) >= 6 else float("nan")
    ret_20d = safe_div(close.iloc[-1], close.iloc[-21]) - 1.0 if len(close) >= 21 else float("nan")
    ret_60d = safe_div(close.iloc[-1], close.iloc[-61]) - 1.0 if len(close) >= 61 else float("nan")

    # 波动率（年化）
    daily_ret = close.pct_change().dropna()
    vol_20d = daily_ret.tail(20).std() * (252 ** 0.5) if len(daily_ret) >= 20 else float("nan")

    # 量比趋势：近5日均量 / 近20日均量
    volume_ratio = safe_div(volume.tail(5).mean(), volume.tail(20).mean()) if len(volume) >= 20 else float("nan")

    # 均线偏离度（60日均线）
    ma60 = close.tail(60).mean() if len(close) >= 60 else float("nan")
    ma60_deviation = safe_div(close.iloc[-1], ma60) - 1.0 if pd.notna(ma60) else float("nan")

    # 最新收盘价与日期
    latest_close = float(close.iloc[-1])
    latest_date = df["date"].iloc[-1].strftime("%Y-%m-%d")

    return {
        "ret_5d": ret_5d,
        "ret_20d": ret_20d,
        "ret_60d": ret_60d,
        "vol_20d_annual": vol_20d,
        "volume_ratio_5_20": volume_ratio,
        "ma60": ma60,
        "ma60_deviation": ma60_deviation,
        "close": latest_close,
        "latest_date": latest_date,
        "data_days": len(df),
    }


def percentile_score(s: pd.Series, ascending: bool = True) -> pd.Series:
    """把序列转为 0-100 的百分位得分。ascending=True 表示原值越大越好。"""
    valid = s.dropna()
    if len(valid) < 2:
        return pd.Series(index=s.index, dtype=float)
    if ascending:
        ranked = valid.rank(method="min", pct=True)
    else:
        ranked = (-valid).rank(method="min", pct=True)
    # 从 0 起点的百分位转为更直观的 0-100
    return (ranked * 100).reindex(s.index)


def build_scores(rows: list) -> pd.DataFrame:
    """把原始因子行合并为 DataFrame，并计算各维度百分位得分与综合得分。"""
    df = pd.DataFrame(rows).copy()
    if df.empty:
        return df

    # 各维度百分位得分（越大越好）
    df["momentum_20_score"] = percentile_score(df["ret_20d"], ascending=True)
    df["momentum_60_score"] = percentile_score(df["ret_60d"], ascending=True)
    df["momentum_score"] = df[["momentum_20_score", "momentum_60_score"]].mean(axis=1)

    df["reversal_score"] = percentile_score(df["ret_5d"], ascending=False)
    df["volatility_score"] = percentile_score(df["vol_20d_annual"], ascending=False)
    df["volume_score"] = percentile_score(df["volume_ratio_5_20"], ascending=True)
    df["ma_deviation_score"] = percentile_score(df["ma60_deviation"].abs(), ascending=False)

    # 综合得分
    df["total"] = (
        df["momentum_score"] * FACTOR_WEIGHTS["momentum"]
        + df["reversal_score"] * FACTOR_WEIGHTS["reversal"]
        + df["volatility_score"] * FACTOR_WEIGHTS["volatility"]
        + df["volume_score"] * FACTOR_WEIGHTS["volume"]
        + df["ma_deviation_score"] * FACTOR_WEIGHTS["ma_deviation"]
    )

    # 保留两位小数便于展示
    round_cols = [
        "total",
        "momentum_score", "momentum_20_score", "momentum_60_score",
        "reversal_score", "volatility_score", "volume_score", "ma_deviation_score",
        "ret_5d", "ret_20d", "ret_60d",
        "vol_20d_annual", "volume_ratio_5_20", "ma60_deviation", "close",
    ]
    for c in round_cols:
        if c in df.columns:
            df[c] = df[c].apply(lambda x: round(x, 4) if pd.notna(x) else x)

    return df.sort_values("total", ascending=False).reset_index(drop=True)


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
            col = _find_col(["成分券代码", "股票代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"weight csindex: {e}")

        sys.exit(f"ERROR: 获取沪深300成分股失败: {'; '.join(errs)}")

    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


def score_one(code: str, end_date: Optional[str] = None, lookback: int = DEFAULT_LOOKBACK) -> dict:
    end = pd.Timestamp.now() if end_date is None else pd.Timestamp(normalize_date(end_date))
    start = end - pd.Timedelta(days=lookback)
    start_str = normalize_date_ak(start.strftime("%Y%m%d"))
    end_str = normalize_date_ak(end.strftime("%Y%m%d"))

    df, source = fetch_hist(code, start_str, end_str)
    factors = compute_factors(df)
    return {
        "code": str(code).strip().zfill(6),
        **factors,
        "source": source,
    }


def main():
    ap = argparse.ArgumentParser(description="A股西蒙斯风格多因子打分器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="simons_factor_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    ap.add_argument("--end-date", default=None, help="截止日期，兼容 20231231 或 2023-12-31（默认今天）")
    ap.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK, help=f"回放眼日历天数（默认 {DEFAULT_LOOKBACK}）")
    args = ap.parse_args()

    # 默认禁用系统代理
    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    print(f"股票池共 {len(codes)} 只，开始多因子打分（行情接口较慢，请耐心）...")
    print("注：本 skill 为詹姆斯·西蒙斯/大奖章基金的风格化学习框架，真实策略不公开。")

    # 一次性获取名称映射
    print("正在加载股票名称映射...")
    name_map = fetch_name_map()
    time.sleep(0.15)

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, end_date=args.end_date, lookback=args.lookback)
            r["name"] = name_map.get(r["code"], "—")
            rows.append(r)
            print(f"[{i}/{len(codes)}] {r['code']} {r['name']} 数据条数={r.get('data_days', '—')}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    df = build_scores(rows)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "rank", "code", "name", "total", "close", "latest_date",
        "ret_5d", "ret_20d", "ret_60d", "vol_20d_annual",
        "volume_ratio_5_20", "ma60_deviation",
        "momentum_score", "reversal_score", "volatility_score",
        "volume_score", "ma_deviation_score",
    ]
    df["rank"] = df.index + 1
    display_df = df.head(args.top).copy()

    def fmt_num(x):
        if pd.isna(x):
            return "—"
        if isinstance(x, (int, float)):
            return f"{x:.2f}"
        return str(x)

    for c in display_cols:
        if c in display_df.columns and c not in ("rank", "code", "name", "latest_date"):
            display_df[c] = display_df[c].apply(fmt_num)
    print(display_df[[c for c in display_cols if c in display_df.columns]].to_string(index=False))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    if failed:
        print(f"失败代码: {', '.join(code for code, _ in failed[:10])}{' ...' if len(failed) > 10 else ''}")
    print("判定线: 综合分越高，越符合本框架下的‘动量+反转+低波+放量+均线回归’复合特征；高分仅作初筛。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
