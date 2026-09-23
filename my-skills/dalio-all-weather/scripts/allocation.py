#!/usr/bin/env python3
"""allocation.py — A股全天候/债务周期参考配置器。

用法:
    python scripts/allocation.py --lookback 252 --out allocation.csv
    python scripts/allocation.py --codes 600519,000858,600036 --lookback 60 --out test_alloc.csv

说明:
    用 A 股宽基指数、国债/黄金 ETF、商品指数的日线数据计算相关性、波动率与
    风险平价风格权重，并输出组合回测摘要（年化收益、最大回撤、夏普）。
    东财接口失败时自动降级到新浪/同花顺同类接口。
"""
import argparse
import os
import sys
import time
import warnings
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import akshare as ak
except ImportError:
    sys.exit("ERROR: 未安装 akshare，请先执行: pip install akshare==1.18.96 pandas")

TQDM_DISABLE = os.environ.get("TQDM_DISABLE", "1")
TRADING_DAYS_YEAR = 252

# 默认全天候资产池（A 股代理）
DEFAULT_ASSETS = [
    {"code": "sh000300", "name": "沪深300", "category": "股票", "fetch_type": "index"},
    {"code": "sh000905", "name": "中证500", "category": "股票", "fetch_type": "index"},
    {"code": "sh511010", "name": "国债ETF", "category": "债券", "fetch_type": "etf"},
    {"code": "sh518880", "name": "黄金ETF", "category": "黄金", "fetch_type": "etf"},
    {"code": "中证商品期货指数", "name": "中证商品期货指数", "category": "商品", "fetch_type": "commodity"},
]


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理阻断东财/同花顺直连。"""
    import requests

    requests.utils.getproxies = lambda: {}
    for k in [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "http_proxy",
        "https_proxy",
        "ALL_PROXY",
        "all_proxy",
    ]:
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


def to_date_str(dt) -> str:
    """把 datetime/date/Timestamp 转为 YYYY-MM-DD。"""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return normalize_date(dt)
    return pd.Timestamp(dt).strftime("%Y-%m-%d")


def to_em_date_str(dt) -> str:
    """东财接口需要 YYYYMMDD。"""
    return to_date_str(dt).replace("-", "")


def guess_prefix(code: str) -> str:
    """根据 A 股代码猜测交易所前缀：6 开头为 sh，其余为 sz。"""
    c = str(code).strip()
    if c.startswith("6"):
        return "sh"
    return "sz"


def _sleep():
    """调用间短暂等待，降低对公开接口的压力。"""
    time.sleep(0.15)


def _extract_close_df(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """从 akshare 返回的 DataFrame 中统一提取 date + close。"""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # 找日期列
    date_col = None
    for c in df.columns:
        if c.lower() in ("date", "日期"):
            date_col = c
            break
    if date_col is None:
        # 兜底：第一列
        date_col = df.columns[0]

    # 找收盘价列
    close_col = None
    for c in df.columns:
        if c in ("close", "收盘", "收盘价"):
            close_col = c
            break
    if close_col is None:
        # 兜底：包含 "收盘" 或 "close" 的列
        for c in df.columns:
            if "收盘" in c or "close" in c.lower():
                close_col = c
                break
    if close_col is None:
        # 兜底：常见位置
        close_col = df.columns[df.columns.get_loc("close")] if "close" in df.columns else df.columns[2]

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce")
    out["close"] = pd.to_numeric(df[close_col], errors="coerce")
    out = out.dropna().sort_values("date").reset_index(drop=True)
    out["source"] = source
    return out


def _filter_date_range(df: pd.DataFrame, start: Optional[str], end: Optional[str], last_n: Optional[int] = None) -> pd.DataFrame:
    """按日期范围过滤，并可取最后 N 个交易日。"""
    if df is None or df.empty:
        return df
    df = df.copy()
    if start:
        sd = pd.to_datetime(start)
        df = df[df["date"] >= sd]
    if end:
        ed = pd.to_datetime(end)
        df = df[df["date"] <= ed]
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    if last_n and len(df) > last_n:
        df = df.tail(last_n)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 各类资产抓取函数：优先东财，失败降级新浪/同花顺
# ---------------------------------------------------------------------------


def fetch_index_em(code: str, start: str, end: str) -> pd.DataFrame:
    """东财指数日线。code 形如 sh000300。"""
    symbol = code[2:] if len(code) > 6 else code
    # 优先 index_zh_a_hist
    try:
        df = _retry_call(
            lambda: ak.index_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=to_em_date_str(start),
                end_date=to_em_date_str(end),
            )
        )
        _sleep()
        return _extract_close_df(df, "akshare.index_zh_a_hist")
    except Exception:
        pass
    # 备选 stock_zh_index_daily_em
    try:
        df = _retry_call(
            lambda: ak.stock_zh_index_daily_em(
                symbol=code,
                start_date=to_em_date_str(start),
                end_date=to_em_date_str(end),
            )
        )
        _sleep()
        return _extract_close_df(df, "akshare.stock_zh_index_daily_em")
    except Exception:
        raise


def fetch_index_sina(code: str, start: str, end: str) -> pd.DataFrame:
    """新浪指数日线。"""
    df = _retry_call(lambda: ak.stock_zh_index_daily(symbol=code))
    _sleep()
    return _extract_close_df(df, "akshare.stock_zh_index_daily (Sina)")


def fetch_etf_em(code: str, start: str, end: str) -> pd.DataFrame:
    """东财 ETF 日线。code 形如 sh511010。"""
    symbol = code[2:] if len(code) > 6 else code
    df = _retry_call(
        lambda: ak.fund_etf_hist_em(
            symbol=symbol,
            period="daily",
            start_date=to_em_date_str(start),
            end_date=to_em_date_str(end),
        )
    )
    _sleep()
    return _extract_close_df(df, "akshare.fund_etf_hist_em")


def fetch_etf_sina(code: str, start: str, end: str) -> pd.DataFrame:
    """新浪 ETF 日线，需要带 sh/sz 前缀。"""
    df = _retry_call(lambda: ak.fund_etf_hist_sina(symbol=code))
    _sleep()
    return _extract_close_df(df, "akshare.fund_etf_hist_sina")


def fetch_stock_em(code: str, start: str, end: str) -> pd.DataFrame:
    """东财个股日线。code 为 6 位数字。"""
    df = _retry_call(
        lambda: ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=to_em_date_str(start),
            end_date=to_em_date_str(end),
            adjust="qfq",
        )
    )
    _sleep()
    return _extract_close_df(df, "akshare.stock_zh_a_hist")


def fetch_stock_sina(code: str, start: str, end: str) -> pd.DataFrame:
    """新浪个股日线。code 为 6 位数字。"""
    full_code = f"{guess_prefix(code)}{code}"
    df = _retry_call(
        lambda: ak.stock_zh_a_daily(
            symbol=full_code,
            start_date=to_em_date_str(start),
            end_date=to_em_date_str(end),
            adjust="qfq",
        )
    )
    _sleep()
    return _extract_close_df(df, "akshare.stock_zh_a_daily")


def fetch_commodity_ccidx(symbol: str, start: str, end: str) -> pd.DataFrame:
    """中证商品期货指数日线。列名可能为乱码，按位置取值。"""
    df = _retry_call(lambda: ak.futures_index_ccidx(symbol=symbol))
    _sleep()
    if df is None or df.empty or df.shape[1] < 5:
        raise RuntimeError("中证商品期货指数返回为空或列数异常")
    # 实测：第 4 列为 date，第 3 列为 settlement/close
    sub = df.iloc[:, [4, 3]].copy()
    sub.columns = ["date", "close"]
    sub["date"] = pd.to_datetime(sub["date"], errors="coerce")
    sub["close"] = pd.to_numeric(sub["close"], errors="coerce")
    sub = sub.dropna().sort_values("date").reset_index(drop=True)
    sub["source"] = "akshare.futures_index_ccidx"
    return sub


def fetch_asset(asset: dict, start: str, end: str, last_n: Optional[int]) -> Optional[pd.DataFrame]:
    """抓取单个资产，失败时自动降级。返回 date/close/source。"""
    code = asset["code"]
    ftype = asset.get("fetch_type", "stock")
    errors = []

    try:
        if ftype == "index":
            try:
                df = fetch_index_em(code, start, end)
            except Exception as e:
                errors.append(f"东财指数失败: {e}")
                df = fetch_index_sina(code, start, end)
        elif ftype == "etf":
            try:
                df = fetch_etf_em(code, start, end)
            except Exception as e:
                errors.append(f"东财ETF失败: {e}")
                df = fetch_etf_sina(code, start, end)
        elif ftype == "commodity":
            df = fetch_commodity_ccidx(code, start, end)
        else:  # stock
            try:
                df = fetch_stock_em(code, start, end)
            except Exception as e:
                errors.append(f"东财个股失败: {e}")
                df = fetch_stock_sina(code, start, end)

        df = _filter_date_range(df, start, end, last_n=last_n)
        if not df.empty:
            return df
    except Exception as e:
        errors.append(str(e))

    print(f"  [{code}] 数据获取失败: {'; '.join(errors)}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# 计算逻辑
# ---------------------------------------------------------------------------


def resolve_lookback(lookback: Optional[str]) -> Tuple[str, str, Optional[int]]:
    """解析 --lookback，返回 (start, end, last_n)。"""
    today = datetime.now().date()
    end_str = today.strftime("%Y-%m-%d")

    if lookback is None:
        n = TRADING_DAYS_YEAR
        start = today - timedelta(days=int(n * 1.8))
        return start.strftime("%Y-%m-%d"), end_str, n

    s = str(lookback).strip().replace("-", "")
    if s.isdigit() and len(s) == 8:
        # 视为起始日期
        start = datetime.strptime(s, "%Y%m%d").date()
        return start.strftime("%Y-%m-%d"), end_str, None

    if s.isdigit():
        n = int(s)
        start = today - timedelta(days=int(n * 1.8))
        return start.strftime("%Y-%m-%d"), end_str, n

    # 尝试用 pandas 解析日期
    try:
        start = pd.to_datetime(lookback).date()
        return start.strftime("%Y-%m-%d"), end_str, None
    except Exception as exc:
        raise ValueError(f"无法解析 --lookback: {lookback}（{exc}）")


def build_returns_table(asset_dfs: dict) -> pd.DataFrame:
    """把各资产 close 表合并成日收益率矩阵。"""
    merged = None
    for code, df in asset_dfs.items():
        tmp = df[["date", "close"]].copy().rename(columns={"close": code})
        if merged is None:
            merged = tmp
        else:
            merged = pd.merge(merged, tmp, on="date", how="inner")

    merged = merged.sort_values("date").set_index("date")
    returns = merged.pct_change().dropna()
    return returns, merged


def annual_metrics(returns: pd.Series, periods: int = TRADING_DAYS_YEAR) -> dict:
    """计算单个资产/组合的年化收益、年化波动、夏普。"""
    r = returns.dropna()
    if len(r) == 0:
        return {"ann_return": np.nan, "ann_vol": np.nan, "sharpe": np.nan}
    ann_vol = r.std() * np.sqrt(periods)
    # 几何年化收益
    n = len(r)
    total = (1 + r).prod() - 1
    ann_return = (1 + total) ** (periods / n) - 1 if n > 0 else np.nan
    sharpe = ann_return / ann_vol if ann_vol and ann_vol > 0 else np.nan
    return {"ann_return": ann_return, "ann_vol": ann_vol, "sharpe": sharpe}


def max_drawdown(cumulative: pd.Series) -> float:
    """从累计净值序列计算最大回撤。"""
    if cumulative.empty:
        return np.nan
    running_max = cumulative.cummax()
    dd = (cumulative - running_max) / running_max
    return dd.min()


def risk_parity_weights(vol_series: pd.Series) -> pd.Series:
    """按逆波动率分配权重，波动为 0 或 nan 时权重为 0。"""
    vol = vol_series.replace(0, np.nan).fillna(np.nan)
    inv = (1.0 / vol).replace([np.inf, -np.inf], np.nan)
    inv = inv.fillna(0.0)
    total = inv.sum()
    if total <= 0:
        # 全部不可算则等权
        return pd.Series(1.0 / len(vol_series), index=vol_series.index)
    return inv / total


def format_pct(x) -> str:
    """把小数格式化为百分比字符串，除零/空值防护。"""
    if pd.isna(x):
        return "N/A"
    return f"{x * 100:.2f}%"


def format_float(x) -> str:
    if pd.isna(x):
        return "N/A"
    return f"{x:.4f}"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="A股全天候/债务周期参考配置器")
    ap.add_argument("--codes", default=None, help="逗号分隔的 A 股代码（可选，默认使用内置全天候资产池）")
    ap.add_argument("--lookback", default=None, help="回看交易日数（默认 252），或起始日期如 2023-01-01 / 20230101")
    ap.add_argument("--out", default="allocation.csv", help="输出 CSV 路径（默认 allocation.csv）")
    args = ap.parse_args()

    # 默认禁用系统代理
    _disable_proxies()

    start, end, last_n = resolve_lookback(args.lookback)
    print(f"数据区间: {start} ~ {end}，取最近 {last_n if last_n else '全部'} 个交易日\n")

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        assets = [
            {"code": c, "name": c, "category": "股票", "fetch_type": "stock"}
            for c in codes
        ]
    else:
        assets = DEFAULT_ASSETS

    print(f"正在加载资产数据（akshare {ak.__version__}）...")
    asset_dfs = {}
    for asset in assets:
        code = asset["code"]
        name = asset["name"]
        print(f"  获取 {name}({code}) ...")
        df = fetch_asset(asset, start, end, last_n)
        if df is not None and not df.empty:
            asset_dfs[code] = df
            print(f"    ✓ 来源: {df['source'].iloc[0]} | 条数: {len(df)} | 最新: {df['date'].iloc[-1].date()} 收盘 {df['close'].iloc[-1]:.4f}")
        else:
            print(f"    ✗ 跳过 {name}({code})", file=sys.stderr)

    if len(asset_dfs) < 2:
        sys.exit("ERROR: 成功获取数据的资产不足 2 个，无法计算相关性与配置权重")

    returns, close_df = build_returns_table(asset_dfs)
    if returns.empty or len(returns) < 30:
        sys.exit(f"ERROR: 对齐后有效交易日仅 {len(returns)} 天，样本过少")

    # 各资产表现
    per_asset = []
    for code in returns.columns:
        metrics = annual_metrics(returns[code])
        per_asset.append(
            {
                "code": code,
                "name": next((a["name"] for a in assets if a["code"] == code), code),
                "category": next((a["category"] for a in assets if a["code"] == code), ""),
                "ann_return": metrics["ann_return"],
                "ann_vol": metrics["ann_vol"],
                "sharpe": metrics["sharpe"],
            }
        )
    asset_perf = pd.DataFrame(per_asset).set_index("code")

    # 相关性矩阵
    corr = returns.corr()

    # 风险平价权重（基于年化波动率）
    vol_series = asset_perf["ann_vol"]
    weights = risk_parity_weights(vol_series)
    asset_perf["weight"] = weights

    # 大类权重
    class_weight = {}
    for _, row in asset_perf.iterrows():
        cat = row["category"]
        class_weight[cat] = class_weight.get(cat, 0.0) + row["weight"]
    class_weight_series = pd.Series(class_weight).sort_values(ascending=False)

    # 组合回测
    port_returns = returns.dot(weights)
    port_metrics = annual_metrics(port_returns)
    cum = (1 + port_returns).cumprod()
    mdd = max_drawdown(cum)

    # 输出到终端
    print("\n" + "=" * 60)
    print("📊 资产表现（最近窗口）")
    print("=" * 60)
    display = asset_perf.copy()
    display["ann_return"] = display["ann_return"].apply(format_pct)
    display["ann_vol"] = display["ann_vol"].apply(format_pct)
    display["sharpe"] = display["sharpe"].apply(format_float)
    display["weight"] = display["weight"].apply(format_pct)
    print(display[["name", "category", "ann_return", "ann_vol", "sharpe", "weight"]].to_string())

    print("\n" + "=" * 60)
    print("🔗 相关性矩阵")
    print("=" * 60)
    print(corr.round(3).to_string())

    print("\n" + "=" * 60)
    print("🌧️ 风险平价风格权重（股票 / 债券 / 黄金 / 商品）")
    print("=" * 60)
    for cat, w in class_weight_series.items():
        print(f"  {cat}: {w * 100:.2f}%")

    print("\n" + "=" * 60)
    print("📈 组合回测摘要")
    print("=" * 60)
    print(f"  年化收益: {format_pct(port_metrics['ann_return'])}")
    print(f"  年化波动: {format_pct(port_metrics['ann_vol'])}")
    print(f"  最大回撤: {format_pct(mdd)}")
    print(f"  夏普比率: {format_float(port_metrics['sharpe'])}")
    print(f"  回测天数: {len(port_returns)}")

    # 写 CSV
    out_path = args.out
    # 主表：每个资产的权重与表现，外加组合行
    main_rows = []
    for code, row in asset_perf.iterrows():
        main_rows.append(
            {
                "code": code,
                "name": row["name"],
                "category": row["category"],
                "ann_return": row["ann_return"],
                "ann_vol": row["ann_vol"],
                "sharpe": row["sharpe"],
                "weight": row["weight"],
                "class_weight": class_weight_series.get(row["category"], np.nan),
                "max_drawdown": np.nan,
            }
        )
    main_rows.append(
        {
            "code": "PORTFOLIO",
            "name": "组合回测",
            "category": "组合",
            "ann_return": port_metrics["ann_return"],
            "ann_vol": port_metrics["ann_vol"],
            "sharpe": port_metrics["sharpe"],
            "weight": 1.0,
            "class_weight": np.nan,
            "max_drawdown": mdd,
        }
    )
    main_df = pd.DataFrame(main_rows)
    main_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    # 相关性矩阵单独输出
    base, ext = os.path.splitext(out_path)
    corr_path = f"{base}_correlation{ext}"
    corr.to_csv(corr_path, encoding="utf-8-sig")

    print(f"\n✅ 结果已写入:")
    print(f"   主表: {out_path}")
    print(f"   相关性矩阵: {corr_path}")
    print("\n免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
