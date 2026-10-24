#!/usr/bin/env python3
"""analyze.py — 单只 A 股巴菲特式完整分析。

用法:
    python scripts/analyze.py 600519

输出: 护城河人工评分清单、财务质量趋势（近 5 年年报）、简易估值区间与安全边际提示。
数据源: akshare（新浪财经/东方财富公开接口）。
"""
import os
import time

os.environ.setdefault("TQDM_DISABLE", "1")

import sys

import pandas as pd
from research_data import annual_rows, numeric, valuation_snapshot

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import akshare as ak
except ImportError:
    ak = None

YEARS = 5


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


MOAT_CHECKLIST = [
    ("品牌/无形资产", "消费者是否愿意为它多付钱？提价后销量是否稳住？"),
    ("成本优势", "单位成本是否低于主要对手？规模扩大是否继续摊薄成本？"),
    ("转换成本", "客户更换供应商的金钱/时间/风险成本高不高？"),
    ("网络效应", "新增用户是否提升老用户的价值？"),
]


def get_name(code: str) -> str:
    try:
        df = _retry_call(lambda: ak.stock_info_a_code_name())
        if "code" not in df.columns or "name" not in df.columns:
            return code
        row = df[df["code"] == code]
        return str(row["name"].iloc[0]) if len(row) else code
    except Exception:
        return code


def financial_trend(code: str) -> pd.DataFrame:
    """近 YEARS 年年报：ROE / 毛利率(利润表计算) / 资产负债率。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_analysis_indicator(
            symbol=code, start_year=str(pd.Timestamp.now().year - YEARS - 1)))
    except Exception as e:
        print(f"ERROR: 获取 {code} 财务指标失败: {e}", file=sys.stderr)
        return pd.DataFrame()
    if df is None or df.empty:
        print(f"ERROR: {code} 财务指标为空，请检查代码或稍后重试（可能限流）", file=sys.stderr)
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = next((c for c in df.columns if "日期" in c), df.columns[0])
    df = annual_rows(df, date_col, YEARS)
    if df.empty:
        print(f"ERROR: {code} 无年度财务数据", file=sys.stderr)
        return pd.DataFrame()

    def col(*keys):
        for k in keys:
            c = next((x for x in df.columns if k in x), None)
            if c is not None:
                return numeric(df[c])
        return pd.Series([float("nan")] * len(df), index=df.index)

    # 毛利率：新浪指标接口该字段常为空，改从利润表计算
    gross = pd.Series([float("nan")] * len(df), index=df.index)
    try:
        time.sleep(0.15)
        inc = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol="利润表"))
        if inc is not None and not inc.empty and "报告日" in inc.columns:
            revenue_col = next((c for c in ("营业收入", "营业总收入") if c in inc), None)
            if revenue_col is None or "营业成本" not in inc.columns:
                pass  # 部分行业（如银行）利润表口径不同，毛利率不适用
            else:
                inc = annual_rows(inc, "报告日", YEARS).set_index("报告日")
                rev = numeric(inc[revenue_col])
                cost = numeric(inc["营业成本"])
                gm = ((rev - cost) / rev.where(rev > 0, float("nan")) * 100)
                dates = df[date_col]
                gross = dates.map(gm).astype(float)
    except Exception as e:
        print(f"WARN: 利润表获取失败，毛利率将缺失: {e}", file=sys.stderr)

    return pd.DataFrame({
        "年报": df[date_col].dt.strftime("%Y-%m-%d").values,
        "ROE%": col("净资产收益率").round(1).values,
        "毛利率%": gross.round(1).values,
        "资产负债率%": col("资产负债率").round(1).values,
    })


def _a_symbol(code: str) -> str:
    """根据 A 股代码规则生成带交易所前缀的 symbol。"""
    if code.startswith(("6", "688", "689")):
        return f"sh{code}"
    if code.startswith(("0", "2", "3", "30", "301")):
        return f"sz{code}"
    return f"bj{code}"


def latest_price(code: str):
    """新浪日线最新收盘价（带 SH/SZ/BJ 前缀自动判断）。"""
    primary = _a_symbol(code)
    fallbacks = [s for s in (f"sh{code}", f"sz{code}", f"bj{code}") if s != primary]
    for sym in [primary] + fallbacks:
        try:
            d = _retry_call(lambda: ak.stock_zh_a_daily(symbol=sym, adjust=""))
            if d is not None and not d.empty:
                return float(d["close"].iloc[-1])
        except Exception:
            continue
        finally:
            time.sleep(0.1)
    return None


def pe_band_and_eps(code: str):
    """返回 (最新PE, PE25分位, PE50分位, 最新收盘价)。失败返回 None 元组。"""
    snapshot = valuation_for_analysis(code)
    if not snapshot or snapshot["pe_q25"] is None:
        return None, None, None, None
    return snapshot["pe"], snapshot["pe_q25"], snapshot["pe_q50"], snapshot["close"]


def valuation_for_analysis(code):
    try:
        return valuation_snapshot(_retry_call(lambda: ak.stock_value_em(symbol=code)))
    except Exception as exc:
        print(f"WARN: 估值数据不可用: {exc}", file=sys.stderr)
        return None


def main():
    if len(sys.argv) != 2:
        sys.exit("用法: python scripts/analyze.py <6位股票代码>，如 600519")
    code = sys.argv[1].strip()
    if not (code.isascii() and code.isdigit() and len(code) == 6):
        sys.exit("ERROR: 请输入 6 位数字股票代码，如 600519")
    if ak is None:
        sys.exit("ERROR: 未安装 akshare，请执行 python -m pip install akshare pandas")

    name = get_name(code)
    time.sleep(0.15)
    print(f"===== {name} ({code}) 巴菲特式分析 =====\n")

    # 1. 护城河人工清单
    print("【1】护城河清单（人工/AI 逐项打 0-2 分，脚本不打假分）")
    for moat, q in MOAT_CHECKLIST:
        print(f"  [ ] {moat}: {q}  -> 得分 _/2")
    print("  合计 >=5/8 视为有较强护城河。\n")

    # 2. 财务趋势
    print(f"【2】财务质量趋势（近 {YEARS} 年年报）")
    trend = financial_trend(code)
    if trend.empty:
        print("  财务趋势数据获取失败，跳过财务分析。")
        return
    print(trend.to_string(index=False))
    roe_ok = (trend["ROE%"] > 15).sum()
    missing_years = YEARS - len(trend)
    if missing_years > 0:
        print(f"  注意: 仅获取到 {len(trend)}/{YEARS} 年年报数据，以下判断可能不完整。")
    print(f"  ROE>15% 年数: {roe_ok}/{len(trend)}（巴菲特偏好全达标）\n")

    # 3. 估值与安全边际
    print("【3】估值区间与安全边际")
    snapshot = valuation_for_analysis(code)
    if not snapshot or snapshot["pe_q25"] is None or snapshot["close"] is None:
        print("  估值数据不完整，无法计算区间。请人工查询 PE 历史分位与最新 EPS。")
        return
    pe_now, pe25, pe50 = snapshot["pe"], snapshot["pe_q25"], snapshot["pe_q50"]
    # Price and PE must describe the same observation. A newer price would distort EPS.
    price = snapshot["close"]
    eps = price / pe_now if pe_now > 0 else None
    if not eps:
        print("  最新 PE 无效（可能亏损），不适用 PE 估值法。")
        return
    conservative = pe25 * eps
    neutral = pe50 * eps
    print(f"  估值交易日: {snapshot['date']} | 同日收盘价: {price:.2f} 元 | 同日 PE(TTM): {pe_now:.1f} | EPS(估算): {eps:.2f} 元")
    print(f"  近5年 PE 25/50 分位: {pe25:.1f} / {pe50:.1f}")
    print(f"  保守估值(PE25×EPS): {conservative:.2f} 元 | 中性估值(PE50×EPS): {neutral:.2f} 元")
    margin_price = conservative * 0.7
    print(f"  安全边际买入参考价(保守×0.7): {margin_price:.2f} 元")
    if price <= margin_price:
        print("  => 现价具备安全边际（仍需确认护城河与生意理解！）")
    elif price <= conservative:
        print("  => 同日价格低于保守估值，但未达到本模型 30% 的安全边际条件。")
    else:
        print("  => 现价高于保守估值，好公司也要等好价格，建议放入观察列表。")


if __name__ == "__main__":
    main()
