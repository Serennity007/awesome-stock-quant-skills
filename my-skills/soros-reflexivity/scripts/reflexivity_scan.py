#!/usr/bin/env python3
"""reflexivity_scan.py — A股索罗斯反身性扫描器。

用法:
    python scripts/reflexivity_scan.py --codes 600519,000858,600036 --out scan.csv
    python scripts/reflexivity_scan.py --pool hs300 --top 30 --out scan.csv

输出: 价格动量、基本面背离度、成交拥挤度、趋势拐点信号及反身性阶段标注。
数据源: akshare（东方财富为主，失败自动降级到新浪财经）。
"""
import argparse
import os
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


TQDM_DISABLE = os.environ.get("TQDM_DISABLE", "1")


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
    """兼容 20231231 与 2023-12-31 两种格式，统一返回 2023-12-31。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return str(date_str).strip()


def to_yyyymmdd(date_str) -> str:
    """把 2023-12-31 或 20231231 转成 20231231。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return s
    return str(date_str).strip()


def safe_div(a, b, default=float("nan")):
    """除零防护的除法。"""
    try:
        if pd.notna(b) and b != 0:
            return a / b
    except Exception:
        pass
    return default


def parse_float(value) -> float:
    """把任意值解析为 float，失败返回 nan。"""
    try:
        return float(value)
    except Exception:
        return float("nan")


def parse_pct(value) -> float:
    """把 '15.38' 或 '15.38%' 解析为 float。"""
    try:
        s = str(value).strip().replace(",", "").replace("%", "")
        return float(s) if s else float("nan")
    except Exception:
        return float("nan")


def _exchange_prefix(code: str) -> str:
    """为新浪财经日线接口构造前缀。"""
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return "sh"
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        return "sz"
    return "bj"


def recent_report_dates(today=None, n: int = 6) -> list:
    """生成最近 n 个季度末报告日（yyyy-mm-dd），默认从当前日期往前推。"""
    today = pd.Timestamp.now() if today is None else pd.Timestamp(today)
    qm = ((today.month - 1) // 3 + 1) * 3
    cur = pd.Timestamp(today.year, qm, 1) + pd.offsets.MonthEnd(0)
    if cur >= today:
        cur = cur - pd.offsets.DateOffset(months=3)
    dates = [cur]
    for _ in range(n - 1):
        cur = cur - pd.offsets.DateOffset(months=3)
        dates.append(cur)
    return [d.strftime("%Y-%m-%d") for d in dates]


def fetch_latest_yjbb(today=None) -> pd.DataFrame:
    """获取最近可用季度业绩报表（全部 A 股），失败返回空表。"""
    for d in recent_report_dates(today, n=6):
        dt = to_yyyymmdd(d)
        try:
            df = _retry_call(lambda dt=dt: ak.stock_yjbb_em(date=dt))
            time.sleep(0.15)
            if df is not None and not df.empty and len(df) > 1000:
                df.columns = [str(c).strip() for c in df.columns]
                df["report_date"] = normalize_date(d)
                return df
        except Exception as e:
            print(f"WARN: 业绩报表 {d} 获取失败: {e}", file=sys.stderr)
    return pd.DataFrame()


def lookup_fundamental(code: str, yjbb_df: pd.DataFrame) -> dict:
    """在业绩报表中查找单票基本面数据。"""
    if yjbb_df.empty:
        return {}
    row = yjbb_df[yjbb_df["股票代码"].astype(str).str.zfill(6) == code]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {
        "name": str(r.get("股票简称", "")).strip(),
        "report_date": r.get("report_date"),
        "revenue_yoy": parse_pct(r.get("营业总收入-同比增长")),
        "net_profit_yoy": parse_pct(r.get("净利润-同比增长")),
        "roe": parse_float(r.get("净资产收益率")),
        "gross_margin": parse_float(r.get("销售毛利率")),
        "fund_source": "业绩报表(yjbb)",
    }


def fetch_fundamental_sina(code: str) -> dict:
    """新浪财经财务指标降级：计算年度净利润同比增速与最新 ROE。"""
    try:
        start_year = str(pd.Timestamp.now().year - 5)
        df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=start_year))
        time.sleep(0.15)
        if df is None or df.empty:
            return {}
        df.columns = [str(c).strip() for c in df.columns]
        date_col = next((c for c in df.columns if "日期" in c), df.columns[0])
        np_col = next((c for c in df.columns if "净利润" in c and "同比" not in c and "率" not in c), None)
        roe_col = next((c for c in df.columns if "净资产收益率" in c), None)
        if np_col is None:
            return {}
        df[date_col] = df[date_col].astype(str)
        df["_np"] = pd.to_numeric(df[np_col], errors="coerce")
        annual = df[df[date_col].str.endswith("12-31")].sort_values(date_col).tail(2)
        if len(annual) >= 2:
            prev, cur = annual["_np"].iloc[-2], annual["_np"].iloc[-1]
            np_yoy = (cur / prev - 1) * 100 if pd.notna(prev) and prev != 0 else float("nan")
        else:
            np_yoy = float("nan")
        roe = float("nan")
        if roe_col:
            s = pd.to_numeric(df[roe_col], errors="coerce").dropna()
            if not s.empty:
                roe = float(s.iloc[-1])
        return {
            "net_profit_yoy": np_yoy,
            "roe": roe,
            "fund_source": "新浪财经财务指标(降级)",
        }
    except Exception as e:
        print(f"WARN: {code} 新浪财经财务指标获取失败: {e}", file=sys.stderr)
        return {}


def fetch_daily_em(code: str) -> pd.DataFrame:
    """东方财富日线数据。"""
    end = (pd.Timestamp.now() + pd.DateOffset(days=30)).strftime("%Y%m%d")
    start = (pd.Timestamp.now() - pd.DateOffset(days=360)).strftime("%Y%m%d")
    df = _retry_call(lambda: ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq"))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("empty")
    df.columns = [str(c).strip() for c in df.columns]
    rename = {
        "日期": "date",
        "收盘": "close",
        "涨跌幅": "change_pct",
        "换手率": "turnover",
        "成交量": "volume",
        "成交额": "amount",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    for col in ["close", "change_pct", "turnover", "volume", "amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["_source"] = "eastmoney"
    return df[[c for c in ["date", "close", "change_pct", "turnover", "volume", "amount", "_source"] if c in df.columns]]


def fetch_daily_sina(code: str) -> pd.DataFrame:
    """新浪财经日线数据（东方财富失败时降级）。"""
    symbol = f"{_exchange_prefix(code)}{code}"
    start = (pd.Timestamp.now() - pd.DateOffset(days=360)).strftime("%Y%m%d")
    end = (pd.Timestamp.now() + pd.DateOffset(days=30)).strftime("%Y%m%d")
    df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust="qfq"))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("empty")
    df.columns = [str(c).strip() for c in df.columns]
    rename = {
        "date": "date",
        "close": "close",
        "turnover": "turnover",
        "volume": "volume",
        "amount": "amount",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    for col in ["close", "turnover", "volume", "amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["change_pct"] = df["close"].pct_change() * 100
    # 新浪财经的换手率是小数（0.002 = 0.2%），统一为百分比以便与东方财富输出对齐
    if "turnover" in df.columns:
        df["turnover"] = df["turnover"] * 100
    df["_source"] = "sina"
    return df[[c for c in ["date", "close", "change_pct", "turnover", "volume", "amount", "_source"] if c in df.columns]]


def fetch_daily(code: str) -> pd.DataFrame:
    """优先东方财富日线，失败降级新浪财经。"""
    try:
        return fetch_daily_em(code)
    except Exception as e:
        print(f"  {code} 东方财富日线失败，降级到新浪财经: {e}", file=sys.stderr)
        return fetch_daily_sina(code)


def compute_technicals(df: pd.DataFrame) -> dict:
    """基于日线计算动量、拥挤度、均线与拐点信号。"""
    if df is None or len(df) < 60:
        return {}
    close = df["close"].astype(float)
    latest = df.iloc[-1]

    ret_20 = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else float("nan")
    ret_60 = (close.iloc[-1] / close.iloc[-61] - 1) * 100 if len(close) >= 61 else float("nan")

    ma5 = close.tail(5).mean()
    ma20 = close.tail(20).mean()
    ma60 = close.tail(60).mean()

    turnover_current = float(latest["turnover"]) if "turnover" in df.columns and pd.notna(latest["turnover"]) else float("nan")
    turnover_avg20 = df["turnover"].tail(20).mean() if "turnover" in df.columns else float("nan")
    crowding = safe_div(turnover_current, turnover_avg20)

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_signal = ""
    if len(dif) >= 2:
        if dif.iloc[-2] <= dea.iloc[-2] and dif.iloc[-1] > dea.iloc[-1]:
            macd_signal = "MACD金叉"
        elif dif.iloc[-2] >= dea.iloc[-2] and dif.iloc[-1] < dea.iloc[-1]:
            macd_signal = "MACD死叉"

    # RSI14
    delta = close.diff()
    gain = delta.where(delta > 0, 0).tail(14)
    loss = -delta.where(delta < 0, 0).tail(14)
    avg_gain = gain.mean() if not gain.empty else 0
    avg_loss = loss.mean() if not loss.empty else 0
    if avg_loss == 0:
        rsi = 100.0 if avg_gain > 0 else 50.0
    else:
        rsi = 100 - 100 / (1 + avg_gain / avg_loss)
    rsi_signal = ""
    if rsi > 80:
        rsi_signal = "RSI超买"
    elif rsi < 20:
        rsi_signal = "RSI超卖"

    # 趋势排列
    if close.iloc[-1] > ma20 > ma60:
        trend = "多头排列"
    elif close.iloc[-1] < ma20 < ma60:
        trend = "空头排列"
    else:
        trend = "趋势混沌"

    signals = [s for s in [macd_signal, rsi_signal, trend] if s]
    return {
        "close": float(close.iloc[-1]),
        "change_pct": float(latest.get("change_pct", float("nan"))),
        "ret_20": float(ret_20),
        "ret_60": float(ret_60),
        "ma5": float(ma5),
        "ma20": float(ma20),
        "ma60": float(ma60),
        "turnover_current": float(turnover_current),
        "turnover_avg20": float(turnover_avg20),
        "crowding_ratio": float(crowding),
        "macd_dif": float(dif.iloc[-1]),
        "macd_dea": float(dea.iloc[-1]),
        "rsi14": float(rsi),
        "trend_signals": " | ".join(signals),
        "data_source": str(latest.get("_source", "")),
    }


def reflexivity_phase(ret_20, ret_60, net_profit_yoy, revenue_yoy, crowding, signals: str) -> tuple:
    """返回 (反身性阶段, 背离类型)。"""
    mom = ret_20 if pd.notna(ret_20) else 0.0
    mom60 = ret_60 if pd.notna(ret_60) else 0.0
    earn = net_profit_yoy if pd.notna(net_profit_yoy) else (revenue_yoy if pd.notna(revenue_yoy) else None)

    labels = []
    divergence_type = "方向一致"

    if mom > 15 or mom60 > 30:
        if earn is not None and earn < 10:
            labels.append("正反馈脆弱期（泡沫候选）")
            divergence_type = "价格↑ 盈利↓（脆弱泡沫）"
        else:
            labels.append("正反馈强化期")
    elif mom < -10 or mom60 < -20:
        if earn is not None and earn > 15:
            labels.append("负反馈过度（预期差候选）")
            divergence_type = "价格↓ 盈利↑（预期差）"
        else:
            labels.append("负反馈深化期")
    else:
        labels.append("均衡/观察区")

    if pd.notna(crowding) and crowding > 2.0:
        labels.append("拥挤度警示")

    if "死叉" in signals or "超买" in signals:
        labels.append("拐点观察（下行风险）")
    if "金叉" in signals or "超卖" in signals:
        labels.append("拐点观察（反弹可能）")

    if divergence_type == "方向一致" and earn is not None and mom * earn < 0:
        divergence_type = "价格-盈利背离"

    return "；".join(labels), divergence_type


def reflexivity_score(row: dict) -> float:
    """分值越高，越值得作为反身性案例重点关注。"""
    mom = abs(row.get("ret_20", 0) or 0)
    earn = abs(row.get("net_profit_yoy", 0) or 0)
    if row.get("divergence_type") in ("价格↑ 盈利↓（脆弱泡沫）", "价格↓ 盈利↑（预期差）"):
        return mom * (1 + min(earn, 100) / 10)
    return mom + earn * 0.1


def get_pool(pool: str) -> list:
    """获取股票池，目前支持 hs300。"""
    if pool == "hs300":
        try:
            df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
            time.sleep(0.15)
        except Exception as e:
            sys.exit(f"ERROR: 获取沪深300成分股失败: {e}")
        col = next((c for c in df.columns if "成分券代码" in str(c)), None)
        if col is None:
            sys.exit("ERROR: 沪深300成分股返回格式变化，找不到代码列")
        return [str(x).zfill(6) for x in df[col].tolist()]
    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


def main():
    ap = argparse.ArgumentParser(description="A股索罗斯反身性扫描器")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，如 600519,000858,600036")
    ap.add_argument("--pool", default="hs300", help="股票池，默认 hs300（当未指定 --codes 时使用）")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="reflexivity_scan.csv", help="CSV 输出路径")
    ap.add_argument("--no-proxy", action="store_true", help="兼容旧参数，脚本已默认禁用系统代理")
    args = ap.parse_args()

    _disable_proxies()
    if args.no_proxy:
        _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    if not codes:
        sys.exit("ERROR: 股票代码为空")

    print(f"加载最新业绩报表（akshare {ak.__version__}）...")
    yjbb = fetch_latest_yjbb()
    if yjbb.empty:
        print("WARN: 业绩报表未获取到，将尝试单票财务指标降级", file=sys.stderr)
    else:
        print(f"业绩报表日期: {yjbb['report_date'].iloc[0]}，共 {len(yjbb)} 条")

    rows = []
    failed = []
    print(f"开始扫描 {len(codes)} 只股票...")
    for i, code in enumerate(codes, 1):
        try:
            tech = compute_technicals(fetch_daily(code))
            if not tech:
                raise RuntimeError("日线数据不足")
            fun = lookup_fundamental(code, yjbb)
            if not fun:
                fun = fetch_fundamental_sina(code)
            if not fun:
                fun = {"name": ""}
            phase, div_type = reflexivity_phase(
                tech.get("ret_20"),
                tech.get("ret_60"),
                fun.get("net_profit_yoy"),
                fun.get("revenue_yoy"),
                tech.get("crowding_ratio"),
                tech.get("trend_signals", ""),
            )
            row = {
                "code": code,
                "name": fun.get("name", ""),
                "report_date": fun.get("report_date", ""),
                "close": tech["close"],
                "change_pct": tech["change_pct"],
                "ret_20": tech["ret_20"],
                "ret_60": tech["ret_60"],
                "revenue_yoy": fun.get("revenue_yoy"),
                "net_profit_yoy": fun.get("net_profit_yoy"),
                "roe": fun.get("roe"),
                "gross_margin": fun.get("gross_margin"),
                "turnover_current": tech["turnover_current"],
                "turnover_avg20": tech["turnover_avg20"],
                "crowding_ratio": tech["crowding_ratio"],
                "rsi14": tech["rsi14"],
                "macd_dif": tech["macd_dif"],
                "macd_dea": tech["macd_dea"],
                "trend_signals": tech["trend_signals"],
                "phase": phase,
                "divergence_type": div_type,
                "data_source": tech.get("data_source", "") + "+" + fun.get("fund_source", ""),
                "data_date": normalize_date(pd.Timestamp.now().strftime("%Y%m%d")),
            }
            row["reflexivity_score"] = reflexivity_score(row)
            rows.append(row)
            print(f"[{i}/{len(codes)}] {code} {fun.get('name', '')} 完成")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(0.15)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows)
    df = df.sort_values("reflexivity_score", ascending=False).reset_index(drop=True)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    display_cols = [
        "code", "name", "close", "change_pct", "ret_20", "ret_60",
        "net_profit_yoy", "revenue_yoy", "crowding_ratio", "phase", "divergence_type",
    ]
    print("\n=== 反身性扫描结果（按关注分值排序）===")
    print(df[display_cols].head(args.top).to_string(index=False))
    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。完整结果写入: {args.out}")
    print("免责声明：本工具仅供学习研究，不构成投资建议。输出为反身性分析框架的机械扫描，不是预测工具。")


if __name__ == "__main__":
    main()
