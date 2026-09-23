#!/usr/bin/env python3
"""screen.py — 彼得·林奇 GARP / 十倍股 A 股初筛。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out garp_result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out garp_result.csv

逻辑:
    - 用 akshare 获取估值（PE/PEG/PB）与近 5 年年报财务指标。
    - 计算 PEG、连续盈利增长年数、负债率、ROE 稳定性。
    - 按林奇六分类（缓慢增长/稳定增长/快速增长/周期/困境反转/隐蔽资产）打标签。
    - 输出结构化 CSV，并按综合得分排序。

数据源:
    - 东方财富：akshare.stock_value_em, stock_financial_analysis_indicator, stock_yjbb_em, index_stock_cons_csindex
    - 降级：同花顺/腾讯 akshare.stock_zh_a_spot_tx 提供 PE(TTM)
"""
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Optional

import pandas as pd

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

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

# 林奇视角的周期行业关键词（粗略判断，需人工复核）
CYCLICAL_INDUSTRIES = {
    "钢铁", "煤炭", "石油", "化工", "化学", "有色", "金属", "造纸", "航运",
    "船舶", "汽车", "工程机械", "建材", "水泥", "玻璃", "航空",
    "酒店", "养殖", "种植", "农产品", "光伏设备", "电池", "风电设备",
}

# 这些行业通常不被视为强周期（避免因一次性业绩波动被误判为周期股）
NON_CYCLICAL_INDUSTRIES = {"白酒", "饮料", "食品", "医药", "医疗", "计算机", "软件", "传媒", "通信"}

# 隐蔽资产属性行业关键词
ASSET_PLAY_INDUSTRIES = {
    "房地产", "地产", "银行", "保险", "证券", "信托", "港口", "高速公路",
    "铁路", "机场", "水务", "燃气", "电力", "基础设施", "园区", "物流",
}


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理干扰东财/同花顺直连。"""
    try:
        import requests
        requests.utils.getproxies = lambda: {}
    except Exception:
        pass
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


def _get_column(df: pd.DataFrame, *keys) -> Optional[str]:
    """按关键词子串查找列名，返回第一个匹配或 None。"""
    for c in df.columns:
        cs = str(c)
        for k in keys:
            if k in cs:
                return cs
    return None


def _to_float_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


# ---------------- 数据获取 ----------------

def get_hs300_codes() -> list:
    """沪深300成分股代码列表。"""
    df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("沪深300成分股返回为空")
    code_col = _get_column(df, "成分券代码", "股票代码")
    if code_col is None:
        raise RuntimeError("沪深300返回格式变化，找不到代码列")
    return [str(x).strip().zfill(6) for x in df[code_col].tolist()]


def fetch_valuation_em(code: str) -> dict:
    """东财估值数据：PE(TTM)、PE静、PB、PEG、市值。失败返回空字典。"""
    df = _retry_call(lambda: ak.stock_value_em(symbol=code))
    time.sleep(0.15)
    if df is None or df.empty:
        return {}
    row = df.iloc[-1]
    out = {}
    for key, names in (
        ("pe_ttm", ("PE(TTM)",)),
        ("pe_static", ("PE(静)", "PE")),
        ("pb", ("市净率", "PB")),
        ("peg", ("PEG值", "PEG")),
        ("total_mv", ("总市值",)),
        ("close", ("当日收盘价",)),
    ):
        col = _get_column(df, *names)
        if col is not None:
            out[key] = pd.to_numeric(row[col], errors="coerce")
    return out


def fetch_valuation_tx_fallback(code: str) -> dict:
    """腾讯行情全市场快照降级，取 PE(TTM)。"""
    prefix = "sh" if code.startswith("6") or code.startswith("5") else "sz"
    full = f"{prefix}{code}"
    df = _retry_call(lambda: ak.stock_zh_a_spot_tx())
    time.sleep(0.15)
    if df is None or df.empty:
        return {}
    if "code" not in df.columns:
        return {}
    row = df[df["code"].astype(str).str.lower() == full]
    if row.empty:
        return {}
    r = row.iloc[-1]
    pe = pd.to_numeric(r.get("pe_ttm"), errors="coerce")
    close = pd.to_numeric(r.get("zxj"), errors="coerce")
    mv = pd.to_numeric(r.get("zsz"), errors="coerce")  # 亿元
    return {"pe_ttm": pe, "close": close, "total_mv": mv}


def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """近 YEARS+1 年主要财务指标，仅保留年报（12-31）。"""
    start = str(datetime.now().year - YEARS - 2)
    df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=start))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError(f"{code} 财务指标为空")
    date_col = _get_column(df, "日期")
    if date_col is None:
        raise RuntimeError(f"{code} 财务指标缺少日期列")
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[df[date_col].dt.month == 12].sort_values(date_col).tail(YEARS)
    if df.empty:
        raise RuntimeError(f"{code} 无年度财务数据")
    return df


def fetch_yjbb_meta() -> pd.DataFrame:
    """全市场最新业绩报表中的代码、名称、行业映射。返回 DataFrame(code, name, industry)。"""
    now = datetime.now()
    candidates = []
    for y in range(now.year, now.year - 2, -1):
        for m, d in ((12, 31), (9, 30), (6, 30), (3, 31)):
            candidates.append(f"{y}{m:02d}{d:02d}")
    for date in candidates:
        try:
            df = _retry_call(lambda d=date: ak.stock_yjbb_em(date=d))
            time.sleep(0.15)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        code_col = _get_column(df, "股票代码")
        name_col = _get_column(df, "股票简称")
        ind_col = _get_column(df, "所处行业")
        if code_col is None:
            continue
        s = df.copy()
        s["code"] = s[code_col].astype(str).str.strip().str.zfill(6)
        s = s.drop_duplicates("code")
        out = pd.DataFrame({"code": s["code"].values})
        if name_col is not None:
            out["name"] = s[name_col].astype(str).values
        if ind_col is not None:
            out["industry"] = s[ind_col].astype(str).values
        return out
    return pd.DataFrame(columns=["code", "name", "industry"])


# ---------------- 计算与分类 ----------------

def series_or_empty(df: pd.DataFrame, *keys) -> pd.Series:
    col = _get_column(df, *keys)
    if col is None:
        return pd.Series(dtype=float)
    return _to_float_series(df[col])


def lynch_classify(
    revenue_growth: pd.Series,
    profit_growth: pd.Series,
    pe_ttm: Optional[float],
    pb: Optional[float],
    debt_ratio: Optional[float],
    industry: str,
) -> dict:
    """按林奇六分类做机械化打标签。"""
    rev = revenue_growth.dropna()
    prof = profit_growth.dropna()

    avg_rev = float(rev.mean()) if len(rev) else None
    avg_prof = float(prof.mean()) if len(prof) else None
    latest_prof = float(prof.iloc[-1]) if len(prof) else None
    prof_std = float(prof.std()) if len(prof) >= 2 else None

    # 最新增长，用于 PEG 与方向判断
    growth_for_peg = latest_prof if latest_prof is not None else avg_prof
    peg_note = ""
    if pd.notna(pe_ttm) and growth_for_peg and growth_for_peg > 0:
        peg = float(pe_ttm) / growth_for_peg
    else:
        # 最新增速为负时，若历史平均增速仍为正，可给出参考性 PEG（林奇式“用均值平滑一次性亏损”）
        peg = None
        if pd.notna(pe_ttm) and avg_prof is not None and avg_prof > 0:
            peg = float(pe_ttm) / avg_prof
            peg_note = "参考PEG(基于5年均值增速，最新年为负)"
    peg = round(peg, 3) if peg is not None else None

    # 连续盈利增长年数（最近 N 年净利润同比增长 > 0）
    pos_prof_years = int((prof > 0).sum()) if len(prof) else 0
    consecutive_pos = 0
    for v in reversed(prof.tolist()):
        if v > 0:
            consecutive_pos += 1
        else:
            break

    # 困境反转：前两年中有负增长而最近一年转正或大幅反弹
    turnaround = False
    if len(prof) >= 3:
        if prof.iloc[-1] > 0 and (prof.iloc[-2] < 0 or prof.iloc[-3] < 0):
            turnaround = True
        elif prof.iloc[-1] > prof.iloc[-2] + 15 and prof.iloc[-2] < 5:
            turnaround = True

    # 隐蔽资产：PB<1 强信号；PB<1.2 + 传统行业且负债可控
    asset_play = False
    if pd.notna(pb) and pb < 1.0:
        asset_play = True
    elif pd.notna(pb) and pb < 1.2 and any(k in industry for k in ASSET_PLAY_INDUSTRIES):
        if pd.notna(debt_ratio) and debt_ratio < 70:
            asset_play = True

    # 周期：行业关键词 或 利润波动剧烈
    is_cyclical = any(k in industry for k in CYCLICAL_INDUSTRIES)
    if any(k in industry for k in NON_CYCLICAL_INDUSTRIES):
        is_cyclical = False
    if prof_std is not None and prof_std > 25 and len(prof) >= 3:
        is_cyclical = True
    if any(k in industry for k in NON_CYCLICAL_INDUSTRIES):
        is_cyclical = False

    # 确定主标签（优先级：困境反转 > 隐蔽资产 > 周期 > 快速增长 > 稳定增长 > 缓慢增长）
    tag = "未分类"
    if turnaround:
        tag = "困境反转"
    elif asset_play:
        tag = "隐蔽资产"
    elif is_cyclical:
        tag = "周期"
    elif avg_prof is not None and avg_prof > 20 and pos_prof_years >= 3:
        tag = "快速增长"
    elif avg_prof is not None and avg_prof >= 10:
        tag = "稳定增长"
    elif avg_prof is not None and avg_prof < 10:
        tag = "缓慢增长"
    else:
        tag = "未分类"

    return {
        "lynch_tag": tag,
        "avg_revenue_growth": round(avg_rev, 2) if avg_rev is not None else None,
        "avg_profit_growth": round(avg_prof, 2) if avg_prof is not None else None,
        "latest_profit_growth": round(latest_prof, 2) if latest_prof is not None else None,
        "profit_growth_std": round(prof_std, 2) if prof_std is not None else None,
        "positive_profit_years": pos_prof_years,
        "consecutive_profit_years": consecutive_pos,
        "peg": peg,
        "peg_note": peg_note,
        "industry": industry or "",
    }


def score_row(row: dict) -> int:
    """GARP 综合打分（满分 100）。"""
    s = 0
    peg = row.get("peg")
    if peg is not None:
        if peg < 0.5:
            s += 25
        elif peg < 1.0:
            s += 20
        elif peg < 1.5:
            s += 12
        elif peg < 2.0:
            s += 5

    # 连续盈利增长
    cy = row.get("consecutive_profit_years", 0)
    s += min(cy, 5) * 6

    # 平均增速
    avg = row.get("avg_profit_growth")
    if avg is not None:
        if avg > 25:
            s += 15
        elif avg > 15:
            s += 12
        elif avg > 10:
            s += 8
        elif avg > 5:
            s += 4

    # 低负债
    debt = row.get("debt_ratio")
    if debt is not None:
        if debt < 30:
            s += 15
        elif debt < 45:
            s += 10
        elif debt < 60:
            s += 4

    # ROE 水平
    roe = row.get("roe_latest")
    if roe is not None:
        if roe > 20:
            s += 15
        elif roe > 15:
            s += 10
        elif roe > 10:
            s += 5

    # 稳定性：利润增速标准差小加分
    std = row.get("profit_growth_std")
    if std is not None and std < 15:
        s += 5

    return min(s, 100)


def analyze_one(code: str, meta_map: pd.DataFrame) -> dict:
    """分析单只股票，返回结果字典。"""
    # 0. 名称/行业
    meta_row = meta_map[meta_map["code"] == code]
    name = str(meta_row["name"].iloc[0]) if not meta_row.empty else ""
    industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty else ""

    # 1. 估值（东财）
    val = {}
    try:
        val = fetch_valuation_em(code)
    except Exception as e:
        print(f"  {code} 东财估值失败，尝试腾讯降级: {e}", file=sys.stderr)
    if not val or (pd.isna(val.get("pe_ttm")) and pd.isna(val.get("pb"))):
        try:
            val = fetch_valuation_tx_fallback(code)
            if val:
                print(f"  {code} 已降级到腾讯行情获取估值")
        except Exception as e:
            print(f"  {code} 腾讯估值降级也失败: {e}", file=sys.stderr)

    # 2. 财务指标
    fin = fetch_financial_indicator(code)
    roe = series_or_empty(fin, "净资产收益率(%)")
    gross = series_or_empty(fin, "销售毛利率(%)")
    debt = series_or_empty(fin, "资产负债率(%)")
    rev_growth = series_or_empty(fin, "主营业务收入增长率(%)")
    prof_growth = series_or_empty(fin, "净利润增长率(%)")

    # 3. 林奇分类
    classify = lynch_classify(
        rev_growth, prof_growth,
        val.get("pe_ttm"), val.get("pb"),
        debt.iloc[-1] if len(debt) else None,
        industry,
    )

    latest_debt = round(float(debt.iloc[-1]), 2) if len(debt) else None
    latest_roe = round(float(roe.iloc[-1]), 2) if len(roe) else None
    latest_gross = round(float(gross.iloc[-1]), 2) if len(gross) else None

    row = {
        "code": code,
        "name": name,
        "pe_ttm": round(float(val.get("pe_ttm")), 2) if pd.notna(val.get("pe_ttm")) else None,
        "pb": round(float(val.get("pb")), 3) if pd.notna(val.get("pb")) else None,
        "peg_raw": round(float(val.get("peg")), 3) if pd.notna(val.get("peg")) else None,
        "close": round(float(val.get("close")), 2) if pd.notna(val.get("close")) else None,
        "total_mv": round(float(val.get("total_mv")), 2) if pd.notna(val.get("total_mv")) else None,
        "debt_ratio": latest_debt,
        "roe_latest": latest_roe,
        "gross_latest": latest_gross,
        "roe_5y": ",".join(f"{v:.1f}" for v in roe.tolist()) if len(roe) else "",
        "profit_growth_5y": ",".join(f"{v:.1f}" for v in prof_growth.tolist()) if len(prof_growth) else "",
        "data_years": min(len(roe), len(prof_growth), len(debt)),
    }
    row.update(classify)
    row["score"] = score_row(row)
    return row


def main():
    ap = argparse.ArgumentParser(description="彼得·林奇 GARP / 十倍股 A 股初筛")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="garp_result.csv", help="CSV 输出路径")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数(防限流)")
    ap.add_argument("--max-debt", type=float, default=60.0, help="负债率阈值（默认 60%），仅影响 PASS 标记")
    args = ap.parse_args()

    _disable_proxies()

    if args.codes:
        codes = [c.strip().zfill(6) for c in args.codes.split(",") if c.strip()]
    elif args.pool == "hs300":
        codes = get_hs300_codes()
    else:
        sys.exit(f"ERROR: 未知股票池 '{args.pool}'，目前支持: hs300，或用 --codes 自定义")

    print(f"股票池共 {len(codes)} 只，开始加载行业与名称映射...")
    meta_map = fetch_yjbb_meta()
    print(f"映射加载完成，覆盖 {len(meta_map)} 只股票。开始逐一打分...")

    rows, failed = [], []
    for i, code in enumerate(codes, 1):
        try:
            r = analyze_one(code, meta_map)
            rows.append(r)
            print(f"[{i}/{len(codes)}] {code} 得分 {r['score']} | {r['lynch_tag']} | PEG={r['peg']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)
        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows)

    # PASS 标记：GARP 友好型
    df["garp_pass"] = (
        (df["peg"] < 1.0) & (df["peg"].notna()) &
        (df["consecutive_profit_years"] >= 2) &
        (df["debt_ratio"] < args.max_debt)
    ).astype(int)

    # 排序：先 garp_pass，再 score
    df = df.sort_values(["garp_pass", "score"], ascending=[False, False]).reset_index(drop=True)
    df["data_date"] = normalize_date(datetime.now().strftime("%Y%m%d"))

    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    display_cols = [
        "code", "name", "score", "lynch_tag", "garp_pass", "peg",
        "pe_ttm", "pb", "avg_profit_growth", "consecutive_profit_years",
        "debt_ratio", "roe_latest", "industry",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    print(df.head(args.top)[display_cols].to_string(index=False))

    pass_count = int(df["garp_pass"].sum())
    print(f"\nGARP 通过数: {pass_count}/{len(df)}（PEG<1、连续盈利增长≥2年、负债率<{args.max_debt}%）")
    print(f"成功 {len(rows)} 只，失败 {len(failed)} 只。")
    if failed:
        print("失败股票:", ", ".join(f"{c}({e})" for c, e in failed[:10]))
    incomplete = df[df["data_years"] < YEARS]
    if not incomplete.empty:
        print(f"注意: {len(incomplete)} 只股票财务数据未满 {YEARS} 年，分数参考性下降。")
    print("\n免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
