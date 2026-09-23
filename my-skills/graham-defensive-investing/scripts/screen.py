#!/usr/bin/env python3
"""screen.py — 格雷厄姆防御型七准则 A 股筛股器。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out graham_result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out graham_result.csv

数据源: akshare（东方财富为主，失败时降级新浪财经/同花顺）。
"""
import argparse
import os
import re
import sys
import time
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

MAX_YEARS = 10
MIN_YEARS = 5
DEFAULT_MIN_CAP = 200  # 亿元


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


def normalize_date(date_str) -> str:
    """兼容 20231231 与 2023-12-31，统一返回 2023-12-31。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return str(date_str).strip()


def get_year(date_str) -> Optional[int]:
    """从日期字符串中提取 4 位年份。"""
    s = normalize_date(date_str)
    m = re.search(r"(\d{4})", s)
    return int(m.group(1)) if m else None


def safe_numeric(series: pd.Series) -> pd.Series:
    """把可能是字符串的列转为数值，非数字转为 nan。"""
    return pd.to_numeric(series.astype(str).str.replace(",", ""), errors="coerce")


def get_pool(pool: str) -> list:
    if pool == "hs300":
        try:
            df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
        except Exception as e:
            sys.exit(f"ERROR: 获取沪深300成分股失败: {e}")
        col = next((c for c in df.columns if "成分券代码" in str(c)), None)
        if col is None:
            sys.exit("ERROR: 沪深300成分股返回格式变化，找不到代码列")
        return [str(x).zfill(6) for x in df[col].tolist()]
    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


def fetch_name_map() -> dict:
    """从新浪财经全市场快照获取代码→名称映射。"""
    try:
        df = _retry_call(lambda: ak.stock_zh_a_spot())
        time.sleep(0.15)
    except Exception:
        return {}
    if df is None or df.empty or "代码" not in df.columns or "名称" not in df.columns:
        return {}
    df["代码"] = df["代码"].astype(str).str.strip()
    df["名称"] = df["名称"].astype(str).str.strip()
    # 代码可能带 sh/sz/bj 前缀，统一为 6 位数字
    df["code6"] = df["代码"].str.replace(r"^(sh|sz|bj)", "", regex=True)
    return dict(zip(df["code6"], df["名称"]))


def _annual_rows(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """从包含季报/年报的 DataFrame 中过滤出年度（12-31）行，按年份升序。"""
    if df is None or df.empty or date_col not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df[date_col] = df[date_col].astype(str).apply(normalize_date)
    # 年度报告：12-31 或 1231
    mask = df[date_col].str.endswith("12-31")
    df = df[mask].copy()
    df["_year"] = df[date_col].apply(get_year)
    df = df[df["_year"].notna()].sort_values("_year").drop_duplicates("_year", keep="last")
    return df


def _first_numeric(df: pd.DataFrame, *candidates) -> Optional[pd.Series]:
    """按候选列名顺序返回第一个存在的数值列。"""
    for col in candidates:
        c = next((c for c in df.columns if col in str(c)), None)
        if c is not None:
            return safe_numeric(df[c])
    return None


def fetch_financial_indicator(code: str) -> Optional[pd.DataFrame]:
    """东方财富主要财务指标，返回年度行。失败返回 None。"""
    try:
        start_year = pd.Timestamp.now().year - 15
        df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=str(start_year)))
        time.sleep(0.15)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    annual = _annual_rows(df, "日期")
    if annual.empty:
        return None

    # 提取关键列
    current_ratio = _first_numeric(annual, "流动比率")
    eps = _first_numeric(annual, "扣除非经常性损益后的每股收益", "摊薄每股收益", "加权每股收益", "每股收益_调整后")
    net_profit = _first_numeric(annual, "扣除非经常性损益后的净利润")
    total_assets = _first_numeric(annual, "总资产")

    out = pd.DataFrame({"year": annual["_year"].astype(int)})
    if current_ratio is not None:
        out["current_ratio"] = current_ratio.values
    if eps is not None:
        out["eps"] = eps.values
    if net_profit is not None:
        out["net_profit"] = net_profit.values
    if total_assets is not None:
        out["total_assets"] = total_assets.values
    out["source"] = "em"
    return out.dropna(how="all", subset=[c for c in out.columns if c not in ("year", "source")])


def fetch_sina_balance(code: str) -> Optional[pd.DataFrame]:
    """新浪资产负债表年度数据。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol="资产负债表"))
        time.sleep(0.15)
    except Exception:
        return None
    if df is None or df.empty or "报告日" not in df.columns:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    annual = _annual_rows(df, "报告日")
    if annual.empty:
        return None
    current_assets = _first_numeric(annual, "流动资产合计")
    current_liabilities = _first_numeric(annual, "流动负债合计")
    equity = _first_numeric(annual, "归属于母公司股东权益合计")
    out = pd.DataFrame({"year": annual["_year"].astype(int)})
    if current_assets is not None:
        out["current_assets"] = current_assets.values
    if current_liabilities is not None:
        out["current_liabilities"] = current_liabilities.values
    if equity is not None:
        out["equity"] = equity.values
    return out.dropna(how="all", subset=[c for c in out.columns if c != "year"])


def fetch_sina_income(code: str) -> Optional[pd.DataFrame]:
    """新浪利润表年度数据。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol="利润表"))
        time.sleep(0.15)
    except Exception:
        return None
    if df is None or df.empty or "报告日" not in df.columns:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    annual = _annual_rows(df, "报告日")
    if annual.empty:
        return None
    net_profit = _first_numeric(annual, "归属于母公司所有者的净利润")
    eps = _first_numeric(annual, "基本每股收益", "稀释每股收益")
    out = pd.DataFrame({"year": annual["_year"].astype(int)})
    if net_profit is not None:
        out["net_profit"] = net_profit.values
    if eps is not None:
        out["eps"] = eps.values
    return out.dropna(how="all", subset=[c for c in out.columns if c != "year"])


def fetch_financial_sina(code: str) -> Optional[pd.DataFrame]:
    """新浪财报 fallback，合并资产负债表与利润表。"""
    bs = fetch_sina_balance(code)
    inc = fetch_sina_income(code)
    if bs is None and inc is None:
        return None
    if bs is not None and inc is not None:
        df = pd.merge(bs, inc, on="year", how="outer")
    else:
        df = bs if bs is not None else inc
    df = df.sort_values("year")
    # 流动比率 = 流动资产 / 流动负债
    if "current_assets" in df.columns and "current_liabilities" in df.columns:
        denom = df["current_liabilities"].where(df["current_liabilities"] > 0, float("nan"))
        df["current_ratio"] = df["current_assets"] / denom
    df["source"] = "sina"
    return df.dropna(how="all", subset=[c for c in df.columns if c not in ("year", "source")])


def fetch_financial_data(code: str) -> pd.DataFrame:
    """获取年度财务数据，优先东财，失败降级新浪。"""
    df = fetch_financial_indicator(code)
    if df is not None and not df.empty and "current_ratio" in df.columns and "eps" in df.columns:
        return df
    # 尝试新浪补充（可能补上 equity 等东财指标里缺失的项）
    sina_df = fetch_financial_sina(code)
    if sina_df is not None and not sina_df.empty:
        # 若东财已拿到部分列，以外层合并方式补全新浪列
        if df is not None and not df.empty:
            merged = pd.merge(df, sina_df, on="year", how="outer", suffixes=("", "_sina"))
            # 优先保留东财列，新浪列用于填补缺失
            for col in ["current_ratio", "eps", "net_profit", "equity"]:
                sina_col = f"{col}_sina"
                if sina_col in merged.columns:
                    if col in merged.columns:
                        merged[col] = merged[col].fillna(merged[sina_col])
                    else:
                        merged[col] = merged[sina_col]
                    merged.drop(columns=[sina_col], inplace=True)
            merged["source"] = merged.get("source", pd.Series(["em"] * len(merged), index=merged.index))
            return merged
        return sina_df
    if df is not None and not df.empty:
        return df
    raise RuntimeError(f"{code} 财务数据获取失败（东财与新浪均不可用）")


def fetch_value_em(code: str) -> Optional[dict]:
    """东方财富估值数据：总市值、PE、PB。失败返回 None。"""
    try:
        df = _retry_call(lambda: ak.stock_value_em(symbol=code))
        time.sleep(0.15)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    df = df.sort_values(df.columns[0]).tail(1)
    row = df.iloc[0]

    def get(*names):
        for n in names:
            c = next((col for col in df.columns if n in str(col)), None)
            if c is not None:
                v = row[c]
                try:
                    return float(v)
                except Exception:
                    return None
        return None

    market_cap = get("总市值")
    pe = get("PE(静)", "PE")
    pb = get("市净率", "PB")
    return {
        "market_cap": market_cap,
        "pe": pe,
        "pb": pb,
        "source": "em",
    }


def _sina_daily_symbol(code: str) -> str:
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def fetch_value_fallback(code: str, fin_df: pd.DataFrame) -> Optional[dict]:
    """东财估值失败时，用新浪财经日行情 + 最新年报数据估算 PE/PB。"""
    latest = fin_df.sort_values("year").dropna(subset=["net_profit"]).tail(1)
    if latest.empty or pd.isna(latest["net_profit"].iloc[0]):
        return None
    year = int(latest["year"].iloc[0])
    net_profit = float(latest["net_profit"].iloc[0])

    equity = None
    if "equity" in fin_df.columns:
        eq_row = fin_df[fin_df["year"] == year]["equity"]
        if not eq_row.empty and pd.notna(eq_row.iloc[0]):
            equity = float(eq_row.iloc[0])
    # 若财务数据来自东财指标（不含股东权益），降级到新浪资产负债表补全
    if equity is None:
        bs = fetch_sina_balance(code)
        if bs is not None and not bs.empty and "equity" in bs.columns:
            eq_row = bs[bs["year"] == year]["equity"]
            if not eq_row.empty and pd.notna(eq_row.iloc[0]):
                equity = float(eq_row.iloc[0])

    try:
        df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=_sina_daily_symbol(code), adjust="qfq"))
        time.sleep(0.15)
    except Exception:
        return None
    if df is None or df.empty or "close" not in df.columns or "outstanding_share" not in df.columns:
        return None
    df = df.sort_values("date").tail(1)
    close = float(df["close"].iloc[0])
    shares = float(df["outstanding_share"].iloc[0])
    if shares <= 0:
        return None
    market_cap = close * shares
    # 统一为亿元
    market_cap_yi = market_cap / 1e8
    pe = market_cap / net_profit if net_profit > 0 else float("inf")
    pb = market_cap / equity if equity and equity > 0 else float("nan")
    return {
        "market_cap": market_cap_yi,
        "pe": pe,
        "pb": pb,
        "source": "sina",
    }


def fetch_value(code: str, fin_df: pd.DataFrame) -> dict:
    """获取估值数据，优先东财，失败降级新浪估算。"""
    val = fetch_value_em(code)
    if val is not None and val.get("pe") is not None and val.get("pb") is not None:
        return val
    fb = fetch_value_fallback(code, fin_df)
    if fb is not None:
        return fb
    if val is not None:
        return val
    raise RuntimeError(f"{code} 估值数据获取失败（东财与新浪均不可用）")


def fetch_dividends(code: str) -> pd.DataFrame:
    """获取分红记录。失败返回空表。"""
    try:
        df = _retry_call(lambda: ak.stock_dividend_cninfo(symbol=code))
        time.sleep(0.15)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    # 派息比例：每 10 股派息金额；>0 表示现金分红
    if "派息比例" in df.columns:
        df["派息比例"] = safe_numeric(df["派息比例"])
    else:
        df["派息比例"] = float("nan")

    # 确定分红归属年份：优先 报告时间，其次 股权登记日，再次 实施方案公告日期
    years = []
    for _, row in df.iterrows():
        y = None
        for field in ["报告时间", "股权登记日", "实施方案公告日期"]:
            if field in row.index and pd.notna(row[field]):
                y = get_year(row[field])
                if y is not None:
                    break
        years.append(y)
    df["year"] = years
    return df


def screen_one(code: str, min_cap: float = DEFAULT_MIN_CAP, name_map: dict = None) -> dict:
    fin_df = fetch_financial_data(code)
    if fin_df is None or fin_df.empty:
        raise RuntimeError(f"{code} 无财务数据")

    val = fetch_value(code, fin_df)
    div_df = fetch_dividends(code)
    name = ""
    if name_map and code in name_map:
        name = name_map[code]

    # 确定窗口
    annual = fin_df.sort_values("year").dropna(subset=["eps"])
    n = len(annual)
    if n >= MAX_YEARS:
        window_years = MAX_YEARS
        window_label = "10Y"
    elif n >= MIN_YEARS:
        window_years = MIN_YEARS
        window_label = "5Y"
    else:
        window_years = n
        window_label = "NA"

    window = annual.tail(window_years) if window_years > 0 else annual

    # 1. 规模
    market_cap = val.get("market_cap")
    pass_size = market_cap is not None and market_cap >= min_cap

    # 2. 流动比率
    cr_row = fin_df.sort_values("year").tail(1)
    current_ratio = float(cr_row["current_ratio"].iloc[0]) if "current_ratio" in cr_row.columns and pd.notna(cr_row["current_ratio"].iloc[0]) else None
    pass_current = current_ratio is not None and current_ratio > 2

    # 3. 连续盈利
    if not window.empty and "eps" in window.columns:
        profit_years = int((window["eps"] > 0).sum())
        pass_profit = profit_years >= window_years and window_years > 0
    else:
        profit_years = 0
        pass_profit = False

    # 4. 连续分红
    div_years = 0
    pass_dividend = False
    if not window.empty and not div_df.empty and "year" in div_df.columns and "派息比例" in div_df.columns:
        div_years_set = set()
        for year in window["year"].astype(int):
            year_divs = div_df[div_df["year"] == year]["派息比例"]
            if not year_divs.empty and (year_divs > 0).any():
                div_years_set.add(year)
        div_years = len(div_years_set)
        pass_dividend = div_years >= window_years and window_years > 0

    # 5. 盈利增长
    eps_first = float(window["eps"].iloc[0]) if not window.empty and "eps" in window.columns and pd.notna(window["eps"].iloc[0]) else None
    eps_last = float(window["eps"].iloc[-1]) if not window.empty and "eps" in window.columns and pd.notna(window["eps"].iloc[-1]) else None
    eps_growth = None
    pass_growth = False
    if eps_first is not None and eps_last is not None and eps_first > 0:
        eps_growth = eps_last / eps_first - 1
        pass_growth = eps_growth > 1 / 3

    # 6/7. 估值
    pe = val.get("pe")
    pb = val.get("pb")
    pe_pb = None
    pass_pe = pe is not None and pe > 0 and pe < 15
    pass_pb = pb is not None and pb > 0 and (pb < 1.5)
    if pe is not None and pb is not None and pe > 0 and pb > 0:
        pe_pb = pe * pb
        pass_pe_pb = pe_pb < 22.5
    else:
        pass_pe_pb = False
    pass_valuation = pass_pe and (pass_pb or pass_pe_pb)

    passes = {
        "pass_size": bool(pass_size),
        "pass_current_ratio": bool(pass_current),
        "pass_profit": bool(pass_profit),
        "pass_dividend": bool(pass_dividend),
        "pass_growth": bool(pass_growth),
        "pass_pe": bool(pass_pe),
        "pass_pb_or_pepb": bool(pass_valuation),
    }
    pass_count = sum(passes.values())
    pass_all = pass_count == 7

    return {
        "code": code,
        "name": name,
        "window": window_label,
        "market_cap": round(market_cap, 2) if market_cap is not None else None,
        "current_ratio": round(current_ratio, 2) if current_ratio is not None else None,
        "eps_first": round(eps_first, 4) if eps_first is not None else None,
        "eps_last": round(eps_last, 4) if eps_last is not None else None,
        "eps_growth": round(eps_growth, 4) if eps_growth is not None else None,
        "profit_years": profit_years,
        "div_years": div_years,
        "pe": round(pe, 2) if pe is not None else None,
        "pb": round(pb, 2) if pb is not None else None,
        "pe_pb": round(pe_pb, 2) if pe_pb is not None else None,
        **passes,
        "pass_count": pass_count,
        "pass_all": pass_all,
        "data_years": n,
        "val_source": val.get("source", ""),
        "fin_source": fin_df.get("source", pd.Series([""] * len(fin_df))).iloc[-1] if not fin_df.empty else "",
    }


def main():
    ap = argparse.ArgumentParser(description="格雷厄姆防御型七准则 A 股筛股器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名（默认 20）")
    ap.add_argument("--out", default="graham_result.csv", help="CSV 输出路径（默认 graham_result.csv）")
    ap.add_argument("--min-cap", type=float, default=DEFAULT_MIN_CAP, help="最小总市值门槛，单位亿元（默认 200）")
    ap.add_argument("--sleep", type=float, default=0.5, help="每只股票间隔秒数（默认 0.5）")
    args = ap.parse_args()

    # 默认禁用系统代理
    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    print(f"股票池共 {len(codes)} 只，正在加载股票名称映射...")
    name_map = fetch_name_map()
    print(f"名称映射加载完成，开始按格雷厄姆防御型七准则逐一筛选（财务接口较慢，请耐心）...")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = screen_one(code, min_cap=args.min_cap, name_map=name_map)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} 通过 {r['pass_count']}/7 关")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    # 排序：通过关卡数降序，然后 PE×PB 升序
    df = pd.DataFrame(rows)
    df["_sort_pepb"] = df["pe_pb"].fillna(9999)
    df = df.sort_values(["pass_count", "_sort_pepb"], ascending=[False, True]).drop(columns=["_sort_pepb"]).reset_index(drop=True)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "code", "name", "window", "pass_count", "pass_all",
        "market_cap", "current_ratio", "eps_growth",
        "profit_years", "div_years", "pe", "pb", "pe_pb",
    ]
    display_df = df.head(args.top)[[c for c in display_cols if c in df.columns]].copy()
    print(display_df.to_string(index=False))

    all_pass = df[df["pass_all"] == True]
    if not all_pass.empty:
        print(f"\n✅ 7 关全通过：{len(all_pass)} 只")
        print(", ".join(all_pass["code"].tolist()))
    else:
        print("\n⚠️ 本次样本中无 7 关全通过的股票。")

    partial = df[(df["pass_count"] >= 5) & (df["pass_all"] == False)]
    if not partial.empty:
        print(f"\n📌 通过 5-6 关：{len(partial)} 只")
        print(", ".join(partial["code"].tolist()))

    na_rows = df[df["window"] == "NA"]
    if not na_rows.empty:
        print(f"\n注意：以下 {len(na_rows)} 只股票财务数据不足 5 年，结果参考性下降：")
        print(", ".join(na_rows["code"].tolist()))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    if failed:
        print("失败股票：")
        for code, err in failed[:10]:
            print(f"  {code}: {err}")
    print("\n免责声明：本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
