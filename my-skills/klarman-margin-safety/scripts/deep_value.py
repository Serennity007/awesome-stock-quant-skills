#!/usr/bin/env python3
"""deep_value.py — 卡拉曼安全边际 A 股深度价值筛股器。

用法:
    python scripts/deep_value.py --pool hs300 --top 20 --out result.csv
    python scripts/deep_value.py --codes 600519,000858,600036 --out result.csv

筛选维度（Seth Klarman 深度价值风格）:
    1. PB 绝对值：PB<1 或处于历史极低位。
    2. PE 历史分位：越低越好。
    3. 市值/净现金比：净现金相对市值越高，安全垫越厚。
    4. 52 周高点回撤：卡拉曼偏好“跌出来”的机会，回撤越深越值得研究。
    5. 剔除 ST、亏损股。

数据源: akshare（优先东方财富估值接口，失败自动降级新浪行情/财务接口）。
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
    """兼容 20231231 与 2023-12-31 两种格式，统一返回 2023-12-31。"""
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


def _to_numeric(s):
    if isinstance(s, pd.Series):
        return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return float("nan")


# ---------------------------------------------------------------------------
# 股票代码与名称映射
# ---------------------------------------------------------------------------

def _exchange_prefix(code: str) -> str:
    """根据 A 股代码规则返回 sh/sz 前缀。"""
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return "sh"
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        return "sz"
    if code.startswith(("430", "830", "87", "88", "92")):
        return "bj"
    return "sh" if code.startswith("6") else "sz"


def _load_name_map() -> dict:
    """加载全市场代码→名称映射，用于 ST/名称识别；失败返回空字典。"""
    # 优先新浪全行情，失败降级 stock_info_a_code_name
    for func, code_col, name_col in [
        (lambda: ak.stock_zh_a_spot(), "代码", "名称"),
        (lambda: ak.stock_info_a_code_name(), "code", "name"),
    ]:
        try:
            df = _retry_call(func)
        except Exception:
            continue
        if df is None or df.empty or code_col not in df.columns or name_col not in df.columns:
            continue
        out = {}
        for _, row in df.iterrows():
            raw = str(row[code_col]).strip()
            name = str(row[name_col]).strip()
            code = raw.replace("sh", "").replace("sz", "").replace("bj", "")
            out[code] = name
        return out
    return {}


# ---------------------------------------------------------------------------
# 数据获取（东财优先，失败降级新浪）
# ---------------------------------------------------------------------------

def fetch_valuation_em(code: str) -> pd.DataFrame:
    """东方财富历史估值数据。失败抛异常。"""
    df = _retry_call(lambda: ak.stock_value_em(symbol=code))
    if df is None or df.empty:
        raise RuntimeError("东财估值数据为空")
    df.columns = [str(c).strip() for c in df.columns]
    if "数据日期" not in df.columns:
        raise RuntimeError("东财估值数据缺少日期列")
    df["数据日期"] = pd.to_datetime(df["数据日期"].astype(str).apply(normalize_date))
    today = pd.Timestamp.now()
    df = df[df["数据日期"] <= today]
    return df.sort_values("数据日期").reset_index(drop=True)


def fetch_price_daily(code: str) -> pd.DataFrame:
    """新浪日 K 线（前复权）。失败抛异常。"""
    prefix = _exchange_prefix(code)
    df = _retry_call(lambda: ak.stock_zh_a_daily(symbol=f"{prefix}{code}", adjust="qfq"))
    if df is None or df.empty or "close" not in df.columns:
        raise RuntimeError("新浪日 K 为空或缺少 close")
    df["date"] = pd.to_datetime(df["date"].astype(str))
    today = pd.Timestamp.now()
    df = df[df["date"] <= today]
    return df.sort_values("date").reset_index(drop=True)


def fetch_balance_sheet(code: str) -> pd.DataFrame:
    """新浪资产负债表（年报）。失败返回空表。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol="资产负债表"))
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["报告日"] = df["报告日"].astype(str).str.replace("-", "")
    today = pd.Timestamp.now().strftime("%Y%m%d")
    df = df[(df["报告日"].str.endswith("1231")) & (df["报告日"] <= today)]
    return df.sort_values("报告日").reset_index(drop=True)


def fetch_income_statement(code: str) -> pd.DataFrame:
    """新浪利润表（年报）。失败返回空表。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol="利润表"))
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty or "报告日" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["报告日"] = df["报告日"].astype(str).str.replace("-", "")
    today = pd.Timestamp.now().strftime("%Y%m%d")
    df = df[(df["报告日"].str.endswith("1231")) & (df["报告日"] <= today)]
    return df.sort_values("报告日").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 指标计算
# ---------------------------------------------------------------------------

def _latest_report_value(df: pd.DataFrame, *candidates) -> Optional[float]:
    """从最新年报行取第一个候选列的数值。"""
    if df.empty:
        return None
    latest = df.iloc[-1]
    for col in candidates:
        c = _find_col([col], df)
        if c is not None:
            v = _to_numeric(latest[c])
            if pd.notna(v):
                return float(v)
    return None


def calc_net_cash(balance: pd.DataFrame) -> tuple:
    """计算最新年报净现金（亿元）与现金（亿元）。

    净现金 = 货币资金 - (短期借款+长期借款+应付债券+一年内到期的非流动负债)
    若现金项取不到，返回 (None, None)。
    """
    if balance.empty:
        return None, None
    cash = _latest_report_value(balance, "货币资金", "现金及现金等价物", "货币资金(元)")
    if cash is None or cash <= 0:
        return None, None
    short = _latest_report_value(balance, "短期借款") or 0.0
    long = _latest_report_value(balance, "长期借款") or 0.0
    bond = _latest_report_value(balance, "应付债券") or 0.0
    current = _latest_report_value(balance, "一年内到期的非流动负债") or 0.0
    debt = short + long + bond + current
    net = cash - debt
    return cash / 1e8, net / 1e8


def calc_latest_profit(income: pd.DataFrame) -> Optional[float]:
    """最新年报净利润（亿元）。取不到返回 None。"""
    if income.empty:
        return None
    latest = income.iloc[-1]
    col = _find_col(["净利润"], income)
    if col is None:
        return None
    # 避免取到“归属于母公司股东的净利润”之外口径时，优先取“净利润”本身
    exact = next((c for c in income.columns if str(c).strip() == "净利润"), col)
    v = _to_numeric(latest[exact])
    return float(v) / 1e8 if pd.notna(v) else None


def calc_valuation(code: str):
    """返回当前 PB、PE(TTM)、市值(亿元) 及历史分位。

    优先东财 stock_value_em；失败则降级用新浪行情 + 财务数据手工估算。
    """
    errs = []
    try:
        df = fetch_valuation_em(code)
        if not df.empty:
            latest = df.iloc[-1]
            pb = _to_numeric(latest.get("市净率"))
            pe = _to_numeric(latest.get("PE(TTM)"))
            mc = _to_numeric(latest.get("总市值"))
            today = pd.Timestamp.now()
            cutoff = today - pd.DateOffset(years=YEARS)
            hist = df[df["数据日期"] >= cutoff]
            pb_s = pd.to_numeric(hist["市净率"], errors="coerce").dropna()
            pe_s = pd.to_numeric(hist["PE(TTM)"], errors="coerce").dropna()
            pb_s = pb_s[pb_s > 0]
            pe_s = pe_s[pe_s > 0]
            pb_pct = float((pb_s <= pb).mean()) if len(pb_s) >= 60 and pd.notna(pb) else None
            pe_pct = float((pe_s <= pe).mean()) if len(pe_s) >= 60 and pd.notna(pe) else None
            return {
                "pb": float(pb) if pd.notna(pb) else None,
                "pe": float(pe) if pd.notna(pe) else None,
                "market_cap": float(mc) / 1e8 if pd.notna(mc) else None,
                "pb_percentile": pb_pct,
                "pe_percentile": pe_pct,
                "val_source": "akshare.stock_value_em（东财）",
            }
    except Exception as e:
        errs.append(f"东财估值: {e}")
    time.sleep(0.15)

    # 降级：新浪日 K 取收盘价，新浪资产负债表取净资产，利润表取净利润
    try:
        price_df = fetch_price_daily(code)
        balance = fetch_balance_sheet(code)
        income = fetch_income_statement(code)
        if price_df.empty or balance.empty:
            raise RuntimeError("新浪行情或资产负债表为空")
        price = float(price_df["close"].iloc[-1])
        equity = _latest_report_value(balance, "所有者权益(或股东权益)合计", "归属于母公司股东权益合计", "股东权益合计")
        shares = _latest_report_value(balance, "实收资本(或股本)", "股本")
        if equity is None or shares is None or shares <= 0:
            raise RuntimeError("缺少权益或股本数据")
        market_cap = price * shares / 1e8
        pb = safe_div(market_cap * 1e8, equity, None)
        pe = None
        if not income.empty:
            profit = calc_latest_profit(income)
            if profit is not None and profit > 0:
                pe = safe_div(market_cap, profit, None)
        return {
            "pb": pb,
            "pe": pe,
            "market_cap": market_cap,
            "pb_percentile": None,
            "pe_percentile": None,
            "val_source": "akshare.stock_zh_a_daily + sina 报表（东财降级）",
        }
    except Exception as e:
        errs.append(f"新浪降级: {e}")

    raise RuntimeError("; ".join(errs))


def calc_price_metrics(code: str):
    """返回当前价、52 周最高价、回撤幅度(%)。"""
    errs = []
    try:
        df = fetch_price_daily(code)
        today = pd.Timestamp.now()
        cutoff = today - pd.Timedelta(days=252)
        recent = df[df["date"] >= cutoff]
        if recent.empty:
            recent = df.tail(252)
        high_52w = float(recent["close"].max())
        current = float(df["close"].iloc[-1])
        drawdown = safe_div(current - high_52w, high_52w, None)
        return {
            "current_price": current,
            "high_52w": high_52w,
            "drawdown_pct": drawdown * 100 if drawdown is not None else None,
            "price_source": "akshare.stock_zh_a_daily（新浪）",
        }
    except Exception as e:
        errs.append(f"新浪日 K: {e}")
    time.sleep(0.15)

    # 降级：东财日 K
    try:
        end = today.strftime("%Y%m%d")
        start = (today - pd.Timedelta(days=400)).strftime("%Y%m%d")
        df = _retry_call(lambda: ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq"))
        if df is None or df.empty:
            raise RuntimeError("东财日 K 为空")
        df["日期"] = pd.to_datetime(df["日期"].astype(str))
        df = df[df["日期"] <= today]
        recent = df[df["日期"] >= today - pd.Timedelta(days=252)]
        if recent.empty:
            recent = df.tail(252)
        high_52w = float(pd.to_numeric(recent["最高"], errors="coerce").max())
        current = float(pd.to_numeric(df["收盘"].iloc[-1], errors="coerce"))
        drawdown = safe_div(current - high_52w, high_52w, None)
        return {
            "current_price": current,
            "high_52w": high_52w,
            "drawdown_pct": drawdown * 100 if drawdown is not None else None,
            "price_source": "akshare.stock_zh_a_hist（东财降级）",
        }
    except Exception as e:
        errs.append(f"东财日 K: {e}")

    raise RuntimeError("; ".join(errs))


# ---------------------------------------------------------------------------
# 打分
# ---------------------------------------------------------------------------

def score_pb(pb: Optional[float], pb_pct: Optional[float]) -> int:
    """PB 绝对值 + 历史分位打分（满分 25）。"""
    score = 0
    if pb is not None:
        if pb < 1.0:
            score += 15
        elif pb < 1.2:
            score += 10
        elif pb < 1.5:
            score += 5
    if pb_pct is not None:
        if pb_pct < 0.1:
            score += 10
        elif pb_pct < 0.2:
            score += 7
        elif pb_pct < 0.3:
            score += 3
    return min(score, 25)


def score_pe(pe: Optional[float], pe_pct: Optional[float]) -> int:
    """PE 低分位打分（满分 15）。"""
    if pe_pct is not None:
        if pe_pct < 0.1:
            return 15
        elif pe_pct < 0.2:
            return 10
        elif pe_pct < 0.3:
            return 5
    if pe is not None and pe > 0:
        if pe < 8:
            return 12
        elif pe < 12:
            return 7
        elif pe < 15:
            return 3
    return 0


def score_netcash(market_cap: Optional[float], net_cash: Optional[float]) -> int:
    """市值/净现金比打分（满分 25）。"""
    if net_cash is None or net_cash <= 0 or market_cap is None or market_cap <= 0:
        return 0
    ratio = safe_div(market_cap, net_cash, float("nan"))
    if pd.isna(ratio):
        return 0
    if ratio < 1.0:
        return 25
    elif ratio < 2.0:
        return 18
    elif ratio < 3.0:
        return 12
    elif ratio < 5.0:
        return 6
    return 0


def score_drawdown(drawdown_pct: Optional[float]) -> int:
    """52 周高点回撤打分（满分 25），越惨越高分。"""
    if drawdown_pct is None:
        return 0
    if drawdown_pct <= -50:
        return 25
    elif drawdown_pct <= -40:
        return 20
    elif drawdown_pct <= -30:
        return 14
    elif drawdown_pct <= -20:
        return 8
    elif drawdown_pct <= -10:
        return 3
    return 0


def score_one(code: str, name_map: dict) -> dict:
    name = name_map.get(code, "—")
    is_st = "ST" in name or "*ST" in name if name != "—" else False

    val = calc_valuation(code)
    time.sleep(0.15)

    price = calc_price_metrics(code)
    time.sleep(0.15)

    balance = fetch_balance_sheet(code)
    time.sleep(0.15)
    income = fetch_income_statement(code)
    time.sleep(0.15)

    cash, net_cash = calc_net_cash(balance)
    latest_profit = calc_latest_profit(income)
    is_loss = latest_profit is not None and latest_profit <= 0

    pb_score = score_pb(val["pb"], val["pb_percentile"])
    pe_score = score_pe(val["pe"], val["pe_percentile"])
    nc_score = score_netcash(val["market_cap"], net_cash)
    dd_score = score_drawdown(price["drawdown_pct"])

    total = pb_score + pe_score + nc_score + dd_score
    if is_st or is_loss:
        total = 0

    return {
        "code": code,
        "name": name,
        "total": total,
        "pb_score": pb_score,
        "pb": round(val["pb"], 3) if val["pb"] is not None else None,
        "pb_percentile": round(val["pb_percentile"], 3) if val["pb_percentile"] is not None else None,
        "pe_score": pe_score,
        "pe": round(val["pe"], 2) if val["pe"] is not None else None,
        "pe_percentile": round(val["pe_percentile"], 3) if val["pe_percentile"] is not None else None,
        "netcash_score": nc_score,
        "market_cap": round(val["market_cap"], 2) if val["market_cap"] is not None else None,
        "net_cash": round(net_cash, 2) if net_cash is not None else None,
        "cash": round(cash, 2) if cash is not None else None,
        "market_cap_to_net_cash": round(safe_div(val["market_cap"], net_cash, None), 2) if net_cash is not None and net_cash > 0 else None,
        "drawdown_score": dd_score,
        "current_price": round(price["current_price"], 2) if price["current_price"] is not None else None,
        "high_52w": round(price["high_52w"], 2) if price["high_52w"] is not None else None,
        "drawdown_pct": round(price["drawdown_pct"], 2) if price["drawdown_pct"] is not None else None,
        "is_st": is_st,
        "is_loss": is_loss,
        "val_source": val["val_source"],
        "price_source": price["price_source"],
    }


# ---------------------------------------------------------------------------
# 股票池
# ---------------------------------------------------------------------------

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
            col = _find_col(["成分券代码"], df) or _find_col(["股票代码"], df)
            if col is not None:
                return [str(x).zfill(6) for x in df[col].tolist()]
        except Exception as e:
            errs.append(f"weight csindex: {e}")

        sys.exit(f"ERROR: 获取沪深300成分股失败: {'; '.join(errs)}")

    sys.exit(f"ERROR: 未知股票池 '{pool}'，目前支持: hs300，或用 --codes 自定义")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="卡拉曼安全边际 A 股深度价值筛股器")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="klarman_screen_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    args = ap.parse_args()

    # 默认禁用系统代理
    _disable_proxies()

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    print(f"股票池共 {len(codes)} 只，开始加载代码名称映射并逐一打分（财务接口较慢，请耐心）...")

    name_map = _load_name_map()
    print(f"已加载 {len(name_map)} 只全市场名称映射。\n")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = score_one(code, name_map)
            rows.append(r)
            flag = ""
            if r["is_st"]:
                flag += " [ST]"
            if r["is_loss"]:
                flag += " [亏损]"
            print(f"[{i}/{len(codes)}] {code} {r['name']} 得分 {r['total']}{flag} | 估值来源: {r['val_source']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows).sort_values("total", ascending=False)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    display_cols = [
        "code", "name", "total", "pb_score", "pb", "pb_percentile",
        "pe_score", "pe", "pe_percentile", "netcash_score", "market_cap",
        "net_cash", "market_cap_to_net_cash", "drawdown_score", "drawdown_pct",
        "is_st", "is_loss",
    ]
    display_df = df.head(args.top)[[c for c in display_cols if c in df.columns]].copy()
    for c in ["pb", "pb_percentile", "pe", "pe_percentile", "market_cap", "net_cash", "market_cap_to_net_cash", "drawdown_pct"]:
        if c in display_df.columns:
            display_df[c] = display_df[c].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    print(display_df.to_string(index=False))

    excluded = df[df["is_st"] | df["is_loss"]]
    if not excluded.empty:
        print(f"\n注意: 以下 {len(excluded)} 只因 ST/亏损被强制置 0 分（仍保留在 CSV 中）：")
        print(", ".join(f"{r['code']} {r['name']}" for _, r in excluded.iterrows()))

    print(f"\n成功 {len(rows)} 只，失败 {len(failed)} 只。")
    print("判定线: >=50 深度价值候选，值得人工复核; 30-49 局部价值信号; <30 当前不符合框架。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
