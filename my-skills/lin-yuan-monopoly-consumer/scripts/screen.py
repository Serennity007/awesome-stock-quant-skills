#!/usr/bin/env python3
"""screen.py — 林园垄断 + 成瘾性消费投资法 A 股初筛。

用法:
    python scripts/screen.py --pool hs300 --top 20 --out result.csv
    python scripts/screen.py --codes 600519,000858,600036 --out result.csv

筛选逻辑（林园式）:
    1. 申万消费/医药行业过滤，并叠加“成瘾/刚需”白名单。
    2. 毛利率 > 50%（垄断定价权）。
    3. ROE 连续高位（>=15%）。
    4. 分红率高、持续分红。
    5. 低负债、盈利质量佳。

数据源: akshare（东方财富、巨潮资讯、腾讯行情），东财失败自动降级同花顺/新浪/腾讯。
"""
import os

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import argparse
import re
import sys
import time
from datetime import datetime
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

# 申万消费/医药大类（ broad filter ）
CONSUMER_MEDICAL_SECTORS = {
    "食品饮料", "医药生物", "家用电器", "美容护理", "纺织服饰",
    "轻工制造", "农林牧渔", "商贸零售", "社会服务",
}

# 林园式“成瘾 / 刚需 / 嘴巴相关”白名单（申万二级/三级或 yjbb 所处行业关键词）
ADDICTIVE_WHITELIST = {
    # 酒类
    "白酒", "啤酒", "黄酒", "葡萄酒", "非白酒", "其他酒类", "软饮料",
    # 食品/饮料/调味品
    "饮料乳品", "调味发酵品", "食品加工", "休闲食品", "肉制品", "食品综合",
    "乳品", "乳制品", "调味品", "酱油", "醋", "酵母", "速冻食品",
    # 医药刚需
    "中药", "化学制药", "生物制品", "医疗器械", "医疗服务", "医药商业",
    "制药", "原料药", "医疗", "医药",
    # 日用刚需
    "化妆品", "个护用品", "家居用品",
    # 家电（部分）
    "白色家电", "小家电", "厨卫电器",
}

# 林园明确不看或高周期性行业（用于提示）
NON_PREFERRED_SECTORS = {
    "钢铁", "煤炭", "石油", "化工", "化学", "有色", "金属", "造纸", "航运",
    "船舶", "汽车", "工程机械", "建材", "水泥", "玻璃", "航空", "酒店",
    "养殖", "种植", "农产品", "光伏设备", "电池", "风电设备", "房地产",
    "银行", "保险", "证券", "信托",
}


def _disable_proxies():
    """禁用系统代理变量，避免 127.0.0.1:7890 等本地代理干扰东财/同花顺/腾讯直连。"""
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
        cs = str(c)
        for cand in candidates:
            if cand in cs:
                return cs
    return None


def _to_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


# ---------------------------------------------------------------------------
# 数据获取
# ---------------------------------------------------------------------------

def get_latest_yjbb_date() -> str:
    """从最近年份/季度倒推，找到可用的 stock_yjbb_em 报告期。"""
    now = datetime.now()
    candidates = []
    for y in range(now.year, now.year - 3, -1):
        for m, d in ((12, 31), (9, 30), (6, 30), (3, 31)):
            candidates.append(f"{y}{m:02d}{d:02d}")
    for date in candidates:
        try:
            df = _retry_call(lambda d=date: ak.stock_yjbb_em(date=d), max_retries=2)
            if df is not None and not df.empty:
                return date
        except Exception:
            continue
    return "20231231"


def load_meta_map(date: Optional[str] = None) -> pd.DataFrame:
    """用 stock_yjbb_em 一次性加载全市场代码-名称-行业-毛利率映射。

    返回 DataFrame: code, name, industry, gross_margin
    """
    if date is None:
        date = get_latest_yjbb_date()
    df = _retry_call(lambda: ak.stock_yjbb_em(date=date))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("stock_yjbb_em 返回为空")

    df.columns = [str(c).strip() for c in df.columns]
    code_col = _find_col(["股票代码"], df)
    name_col = _find_col(["股票简称"], df)
    ind_col = _find_col(["所处行业"], df)
    gross_col = _find_col(["销售毛利率"], df)

    if code_col is None:
        raise RuntimeError("stock_yjbb_em 缺少股票代码列")

    out = pd.DataFrame()
    out["code"] = df[code_col].astype(str).str.strip().str.zfill(6)
    out["name"] = df[name_col].astype(str).str.strip() if name_col else ""
    out["industry"] = df[ind_col].astype(str).str.strip() if ind_col else ""
    if gross_col is not None:
        out["gross_margin"] = _to_numeric_series(df[gross_col])
    else:
        out["gross_margin"] = float("nan")

    out = out.drop_duplicates("code").reset_index(drop=True)
    return out


def get_hs300_codes() -> list:
    """沪深300成分股代码列表。"""
    errs = []
    try:
        df = _retry_call(lambda: ak.index_stock_cons_csindex(symbol="000300"))
        time.sleep(0.15)
        col = _find_col(["成分券代码", "股票代码"], df)
        if col is not None:
            return [str(x).strip().zfill(6) for x in df[col].tolist()]
    except Exception as e:
        errs.append(f"csindex: {e}")

    try:
        df = _retry_call(lambda: ak.index_stock_cons_weight_csindex(symbol="000300"))
        time.sleep(0.15)
        col = _find_col(["成分券代码", "股票代码"], df)
        if col is not None:
            return [str(x).strip().zfill(6) for x in df[col].tolist()]
    except Exception as e:
        errs.append(f"weight csindex: {e}")

    sys.exit(f"ERROR: 获取沪深300成分股失败: {'; '.join(errs)}")


def fetch_all_spot_tx() -> pd.DataFrame:
    """腾讯行情全市场快照（一次调用覆盖全市场），用于估值与当前价。"""
    df = _retry_call(lambda: ak.stock_zh_a_spot_tx())
    time.sleep(0.15)
    if df is None or df.empty or "code" not in df.columns:
        raise RuntimeError("腾讯行情快照返回为空或格式异常")
    df = df.copy()
    df["code"] = df["code"].astype(str).str.lower().str.replace(r"^sh|sz", "", regex=True).str.zfill(6)
    # 关键列映射
    if "zxj" in df.columns:
        df["close"] = pd.to_numeric(df["zxj"], errors="coerce")
    if "pe_ttm" in df.columns:
        df["pe_ttm"] = pd.to_numeric(df["pe_ttm"], errors="coerce")
    if "pb" in df.columns:
        df["pb"] = pd.to_numeric(df["pb"], errors="coerce")
    if "zsz" in df.columns:
        df["total_mv"] = pd.to_numeric(df["zsz"], errors="coerce")  # 亿元
    return df[[c for c in ["code", "name", "close", "pe_ttm", "pb", "total_mv"] if c in df.columns]]


def fetch_financial_indicator(code: str) -> pd.DataFrame:
    """获取主要财务指标（年报），失败抛异常。过滤掉未来日期。"""
    start_year = datetime.now().year - YEARS - 2
    df = _retry_call(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year=str(start_year)))
    time.sleep(0.15)
    if df is None or df.empty:
        raise RuntimeError("财务指标为空")
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["日期"], df) or df.columns[0]
    df[date_col] = df[date_col].astype(str).apply(normalize_date)
    today = datetime.now().strftime("%Y-%m-%d")
    df = df[(df[date_col].str.endswith("12-31")) & (df[date_col] <= today)]
    df = df.sort_values(date_col).tail(YEARS)
    if df.empty:
        raise RuntimeError("无年度财务指标数据")
    return df.reset_index(drop=True)


def fetch_sina_income_gross_margin(code: str) -> pd.Series:
    """新浪三大报表之利润表，手工计算近 YEARS 年年报毛利率（%）。失败返回空 Series。"""
    try:
        df = _retry_call(lambda: ak.stock_financial_report_sina(stock=code, symbol="利润表"))
    except Exception:
        return pd.Series(dtype=float)
    time.sleep(0.15)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    df.columns = [str(c).strip() for c in df.columns]
    if "报告日" not in df.columns:
        return pd.Series(dtype=float)

    df["报告日"] = df["报告日"].astype(str).str.replace("-", "")
    today = datetime.now().strftime("%Y%m%d")
    df = df[(df["报告日"].str.endswith("1231")) & (df["报告日"] <= today)]
    df = df.sort_values("报告日").tail(YEARS)
    if df.empty:
        return pd.Series(dtype=float)

    rev_col = _find_col(["营业收入"], df)
    cost_col = _find_col(["营业成本"], df)
    if rev_col is None or cost_col is None:
        return pd.Series(dtype=float)

    rev = _to_numeric_series(df[rev_col])
    cost = _to_numeric_series(df[cost_col])
    gm = ((rev - cost) / rev.replace(0, float("nan")) * 100).dropna()
    return gm.reset_index(drop=True)


def fetch_dividend_cninfo(code: str) -> pd.DataFrame:
    """巨潮资讯分红数据，失败返回空 DataFrame；过滤掉未来日期。"""
    try:
        df = _retry_call(lambda: ak.stock_dividend_cninfo(symbol=code))
    except Exception:
        return pd.DataFrame()
    time.sleep(0.15)
    if df is None or df.empty:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    date_col = _find_col(["实施方案公告日期"], df)
    if date_col is None:
        return pd.DataFrame()
    df[date_col] = df[date_col].astype(str).apply(normalize_date)
    today = datetime.now().strftime("%Y-%m-%d")
    df = df[df[date_col] <= today]
    return df.reset_index(drop=True)


def fetch_sw_industry(code: str) -> dict:
    """巨潮申万行业分类，返回 {一级, 二级, 三级}。失败返回空 dict。"""
    try:
        df = _retry_call(lambda: ak.stock_industry_change_cninfo(symbol=code))
    except Exception:
        return {}
    time.sleep(0.15)
    if df is None or df.empty:
        return {}
    df.columns = [str(c).strip() for c in df.columns]
    std_col = _find_col(["分类标准"], df)
    if std_col is None:
        return {}
    row = df[df[std_col].astype(str).str.contains("申银万国", na=False)]
    if row.empty:
        row = df.iloc[[-1]]
    r = row.iloc[-1]
    return {
        "sw_sector": str(r.get(_find_col(["行业门类"], df) or _find_col(["行业大类"], df) or "", "")).strip(),
        "sw_industry": str(r.get(_find_col(["行业中类"], df) or _find_col(["行业次类"], df) or "", "")).strip(),
        "sw_detail": str(r.get(_find_col(["行业大类"], df) or "", "")).strip(),
    }


# ---------------------------------------------------------------------------
# 指标计算
# ---------------------------------------------------------------------------

def _annual_dividend_per_share(div_df: pd.DataFrame) -> tuple:
    """基于巨潮分红数据计算最近一个报告年度的每股派息（元）与股息次数。"""
    if div_df.empty:
        return float("nan"), 0

    ratio_col = _find_col(["派息比例"], div_df)
    if ratio_col is None:
        return float("nan"), 0

    ratios = _to_numeric_series(div_df[ratio_col]).dropna()
    if ratios.empty:
        return float("nan"), 0

    # 派息比例通常为“每 10 股派息 X 元”，转换为每股
    total = ratios.iloc[-5:].sum() / 10.0  # 取最近 5 条记录作为近 1–2 年分红合计
    count = len(ratios.iloc[-5:])
    return total, count


def classify_industry_tag(industry: str) -> tuple:
    """返回 (industry_tag, addictive_tag, is_consumer_medical, is_non_preferred)。"""
    if not industry or industry.lower() == "nan":
        return "", "", False, False

    ind = str(industry)
    # 精确匹配白名单
    for kw in sorted(ADDICTIVE_WHITELIST, key=len, reverse=True):
        if kw in ind:
            return kw, kw, True, False

    # broad 消费/医药大类
    for sector in CONSUMER_MEDICAL_SECTORS:
        if sector in ind:
            return sector, "", True, False

    # 非偏好行业
    for kw in NON_PREFERRED_SECTORS:
        if kw in ind:
            return kw, "", False, True

    return ind, "", False, False


def score_gross_margin(s: pd.Series) -> int:
    if s.empty:
        return 0
    mean_v = float(s.mean()) if not pd.isna(s.mean()) else 0
    std_v = float(s.std()) if len(s) >= 2 and not pd.isna(s.std()) else 0

    score = 0
    if mean_v >= 55:
        score += 25
    elif mean_v >= 50:
        score += 22
    elif mean_v >= 45:
        score += 18
    elif mean_v >= 40:
        score += 12
    elif mean_v >= 35:
        score += 6

    if std_v < 3:
        score += 5
    elif std_v < 5:
        score += 3
    elif std_v < 10:
        score += 1
    return min(score, 30)


def score_roe(s: pd.Series) -> int:
    if s.empty:
        return 0
    high_years = int((s.dropna() >= 15).sum())
    mean_v = float(s.mean()) if not pd.isna(s.mean()) else 0

    score = min(high_years * 4, 20)
    if mean_v >= 20:
        score += 5
    elif mean_v >= 15:
        score += 3
    elif mean_v >= 10:
        score += 1
    return min(score, 25)


def score_dividend(div_per_share: float, close: float, count: int) -> int:
    if pd.isna(div_per_share) or pd.isna(close) or close <= 0:
        return 0
    yld = div_per_share / close * 100

    score = 0
    if yld >= 3.0:
        score += 15
    elif yld >= 2.0:
        score += 12
    elif yld >= 1.5:
        score += 8
    elif yld >= 1.0:
        score += 5
    elif yld >= 0.5:
        score += 2

    if count >= 4:
        score += 5
    elif count >= 3:
        score += 3
    elif count >= 2:
        score += 1
    return min(score, 20)


def score_debt(debt: Optional[float]) -> int:
    if debt is None or pd.isna(debt):
        return 0
    if debt < 30:
        return 10
    elif debt < 45:
        return 7
    elif debt < 60:
        return 4
    elif debt < 80:
        return 1
    return 0


def score_industry(addictive_tag: str, is_consumer_medical: bool) -> int:
    if addictive_tag and addictive_tag in ADDICTIVE_WHITELIST:
        return 15
    if is_consumer_medical:
        return 8
    return 0


# ---------------------------------------------------------------------------
# 单只股票分析
# ---------------------------------------------------------------------------

def analyze_one(
    code: str,
    meta_map: pd.DataFrame,
    spot_map: pd.DataFrame,
    fetch_detail: bool,
    min_gross: float,
    min_roe: float,
    min_div: float,
) -> dict:
    """分析单只股票，返回结果字典。"""
    meta_row = meta_map[meta_map["code"] == code]
    name = str(meta_row["name"].iloc[0]) if not meta_row.empty else ""
    yjbb_industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty else ""
    yjbb_gross = float(meta_row["gross_margin"].iloc[0]) if not meta_row.empty else float("nan")

    # 行业标签（优先 yjbb 行业）
    industry_tag, addictive_tag, is_consumer_medical, is_non_preferred = classify_industry_tag(yjbb_industry)

    # 估值（来自腾讯快照）
    spot_row = spot_map[spot_map["code"] == code]
    close = float(spot_row["close"].iloc[0]) if not spot_row.empty and "close" in spot_row else float("nan")
    pe_ttm = float(spot_row["pe_ttm"].iloc[0]) if not spot_row.empty and "pe_ttm" in spot_row else float("nan")
    pb = float(spot_row["pb"].iloc[0]) if not spot_row.empty and "pb" in spot_row else float("nan")
    total_mv = float(spot_row["total_mv"].iloc[0]) if not spot_row.empty and "total_mv" in spot_row else float("nan")

    # 若 meta 已显示明显不符合且不要求详细计算，返回极简结果
    if not fetch_detail:
        return {
            "code": code,
            "name": name,
            "score": 0,
            "linyuan_pass": 0,
            "sw_industry": yjbb_industry,
            "sw_sector": "",
            "gross_mean": yjbb_gross if pd.notna(yjbb_gross) else None,
            "gross_annual": "",
            "roe_mean": None,
            "roe_annual": "",
            "dividend_yield": None,
            "payout_recent": None,
            "debt_latest": None,
            "pe_ttm": pe_ttm if pd.notna(pe_ttm) else None,
            "pb": pb if pd.notna(pb) else None,
            "total_mv": total_mv if pd.notna(total_mv) else None,
            "industry_tag": industry_tag,
            "addictive_tag": addictive_tag,
            "is_consumer_medical": int(is_consumer_medical),
            "data_years": 0,
            "source": "yjbb 初筛跳过",
            "note": "行业/毛利率未通过初筛，未拉取详细财务",
        }

    # 详细财务指标
    fin = fetch_financial_indicator(code)
    gross_col = _find_col(["销售毛利率(%)"], fin)
    roe_col = _find_col(["净资产收益率(%)"], fin)
    debt_col = _find_col(["资产负债率(%)"], fin)
    profit_growth_col = _find_col(["净利润增长率(%)"], fin)
    rev_growth_col = _find_col(["主营业务收入增长率(%)"], fin)

    gross_orig = _to_numeric_series(fin[gross_col]).dropna() if gross_col else pd.Series(dtype=float)
    gross_fallback_used = False
    gross = gross_orig.copy()
    # 东财财务指标表偶发毛利率整列为空，降级用新浪利润表手工计算
    if gross.empty or gross.dropna().empty:
        gross = fetch_sina_income_gross_margin(code)
        gross_fallback_used = True
    # 若 yjbb 有最新毛利率，作为补充/校验
    if pd.notna(yjbb_gross):
        if gross.empty:
            gross = pd.Series([yjbb_gross])
        else:
            # 保持近 YEARS 个值，最新值用 yjbb 替换（通常更及时）
            gross = gross.tail(YEARS - 1)
            gross = pd.concat([gross, pd.Series([yjbb_gross])], ignore_index=True)

    roe = _to_numeric_series(fin[roe_col]).dropna() if roe_col else pd.Series(dtype=float)
    debt = _to_numeric_series(fin[debt_col]).dropna() if debt_col else pd.Series(dtype=float)
    profit_growth = _to_numeric_series(fin[profit_growth_col]).dropna() if profit_growth_col else pd.Series(dtype=float)
    rev_growth = _to_numeric_series(fin[rev_growth_col]).dropna() if rev_growth_col else pd.Series(dtype=float)

    # 分红
    div_df = fetch_dividend_cninfo(code)
    div_per_share, div_count = _annual_dividend_per_share(div_df)

    # 申万行业明细（如可用）
    sw = fetch_sw_industry(code)
    sw_industry = sw.get("sw_industry") or yjbb_industry
    sw_sector = sw.get("sw_sector") or ""

    # 指标汇总
    gross_mean = round(float(gross.mean()), 2) if not gross.empty else None
    roe_mean = round(float(roe.mean()), 2) if not roe.empty else None
    debt_latest = round(float(debt.iloc[-1]), 2) if not debt.empty else None
    div_yield = round(div_per_share / close * 100, 2) if pd.notna(div_per_share) and pd.notna(close) and close > 0 else None

    # 打分
    gm_score = score_gross_margin(gross)
    roe_score = score_roe(roe)
    div_score = score_dividend(div_per_share, close, div_count)
    ind_score = score_industry(addictive_tag, is_consumer_medical)
    debt_score = score_debt(debt_latest)

    total_score = gm_score + roe_score + div_score + ind_score + debt_score

    # 硬门槛
    pass_gross = gross_mean is not None and gross_mean >= min_gross
    pass_roe = roe_mean is not None and roe_mean >= min_roe
    pass_div = div_yield is not None and div_yield >= min_div
    pass_industry = is_consumer_medical or bool(addictive_tag)
    linyuan_pass = int(pass_gross and pass_roe and pass_div and pass_industry)

    return {
        "code": code,
        "name": name,
        "score": total_score,
        "linyuan_pass": linyuan_pass,
        "sw_industry": sw_industry,
        "sw_sector": sw_sector,
        "gross_mean": gross_mean,
        "gross_annual": ",".join(f"{v:.1f}" for v in gross.tolist()) if len(gross) else "",
        "roe_mean": roe_mean,
        "roe_annual": ",".join(f"{v:.1f}" for v in roe.tolist()) if len(roe) else "",
        "dividend_yield": div_yield,
        "payout_recent": round(div_per_share, 3) if pd.notna(div_per_share) else None,
        "debt_latest": debt_latest,
        "pe_ttm": round(pe_ttm, 2) if pd.notna(pe_ttm) else None,
        "pb": round(pb, 3) if pd.notna(pb) else None,
        "total_mv": round(total_mv, 2) if pd.notna(total_mv) else None,
        "profit_growth_annual": ",".join(f"{v:.1f}" for v in profit_growth.tolist()) if len(profit_growth) else "",
        "rev_growth_annual": ",".join(f"{v:.1f}" for v in rev_growth.tolist()) if len(rev_growth) else "",
        "industry_tag": industry_tag,
        "addictive_tag": addictive_tag,
        "is_consumer_medical": int(is_consumer_medical),
        "data_years": min(len(gross), len(roe), len(debt)),
        "source": "akshare.stock_financial_analysis_indicator + stock_dividend_cninfo + stock_zh_a_spot_tx",
        "note": "毛利率经新浪利润表/yjbb 补充" if gross_fallback_used else "",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="林园垄断+成瘾性消费投资法 A 股初筛")
    ap.add_argument("--pool", default="hs300", help="股票池: hs300(默认)")
    ap.add_argument("--codes", default=None, help="逗号分隔的股票代码，优先于 --pool")
    ap.add_argument("--top", type=int, default=20, help="终端展示前 N 名")
    ap.add_argument("--out", default="lin_yuan_screen_result.csv", help="CSV 输出路径")
    ap.add_argument("--min-gross", type=float, default=50.0, help="毛利率硬门槛（默认 50%）")
    ap.add_argument("--min-roe", type=float, default=15.0, help="ROE 硬门槛（默认 15%）")
    ap.add_argument("--min-div", type=float, default=1.0, help="股息率硬门槛（默认 1.0%）")
    ap.add_argument("--sleep", type=float, default=0.3, help="每只股票间隔秒数（防接口限流）")
    ap.add_argument("--detail-all", action="store_true", help="对所有股票拉取详细财务（默认仅对初筛通过候选）")
    args = ap.parse_args()

    # 默认禁用系统代理
    _disable_proxies()

    # 股票池
    if args.codes:
        codes = [c.strip().zfill(6) for c in args.codes.split(",") if c.strip()]
    elif args.pool == "hs300":
        codes = get_hs300_codes()
    else:
        sys.exit(f"ERROR: 未知股票池 '{args.pool}'，目前支持: hs300，或用 --codes 自定义")

    print(f"股票池共 {len(codes)} 只，正在加载行业与估值映射...")

    # 加载全市场 yjbb 映射（一次性）
    try:
        meta_map = load_meta_map()
        print(f"行业映射加载完成，覆盖 {len(meta_map)} 只股票。")
    except Exception as e:
        print(f"批量行业映射失败，降级为逐只获取: {e}", file=sys.stderr)
        meta_map = pd.DataFrame({"code": codes, "name": "", "industry": "", "gross_margin": float("nan")})

    # 加载全市场估值快照（一次性）
    try:
        spot_map = fetch_all_spot_tx()
        print(f"估值快照加载完成，覆盖 {len(spot_map)} 只股票。")
    except Exception as e:
        print(f"腾讯估值快照失败: {e}", file=sys.stderr)
        spot_map = pd.DataFrame(columns=["code", "name", "close", "pe_ttm", "pb", "total_mv"])

    print("开始逐一打分（财务接口较慢，请耐心）...")

    rows, failed = [], []
    skipped = 0
    for i, code in enumerate(codes, 1):
        meta_row = meta_map[meta_map["code"] == code]
        yjbb_industry = str(meta_row["industry"].iloc[0]) if not meta_row.empty else ""
        yjbb_gross = float(meta_row["gross_margin"].iloc[0]) if not meta_row.empty else float("nan")
        _, _, is_consumer_medical, _ = classify_industry_tag(yjbb_industry)

        # 默认仅对“消费/医药 或 毛利率已达标”的股票拉详细财务，节省调用
        fetch_detail = bool(
            args.detail_all
            or is_consumer_medical
            or (pd.notna(yjbb_gross) and yjbb_gross >= args.min_gross - 10)  # 留 10pp 缓冲
        )

        try:
            r = analyze_one(code, meta_map, spot_map, fetch_detail, args.min_gross, args.min_roe, args.min_div)
            rows.append(r)
            if not fetch_detail:
                skipped += 1
            print(f"[{i}/{len(codes)}] {code} {r['name']} 得分 {r['score']} | 通过={r['linyuan_pass']}")
        except Exception as e:
            failed.append((code, str(e)))
            print(f"[{i}/{len(codes)}] {code} 失败: {e}", file=sys.stderr)

        time.sleep(args.sleep)

    if not rows:
        sys.exit("ERROR: 全部股票获取失败，请检查网络、代理设置或升级 akshare（pip install -U akshare）")

    df = pd.DataFrame(rows)
    df = df.sort_values(["linyuan_pass", "score"], ascending=[False, False]).reset_index(drop=True)
    df["data_date"] = normalize_date(datetime.now().strftime("%Y%m%d"))
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    display_cols = [
        "code", "name", "score", "linyuan_pass", "sw_industry", "gross_mean",
        "roe_mean", "dividend_yield", "debt_latest", "pe_ttm", "addictive_tag",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    print(f"\n=== 前 {min(args.top, len(df))} 名（完整结果见 {args.out}）===")
    print(df.head(args.top)[display_cols].to_string(index=False))

    pass_count = int(df["linyuan_pass"].sum())
    print(f"\n林园硬门槛通过数: {pass_count}/{len(df)}（毛利率≥{args.min_gross}%、ROE≥{args.min_roe}%、股息率≥{args.min_div}%、消费/医药行业）")
    print(f"成功 {len(rows)} 只，失败 {len(failed)} 只，初筛跳过 {skipped} 只。")
    if failed:
        print("失败股票:", ", ".join(f"{c}({e})" for c, e in failed[:10]))

    incomplete = df[(df["data_years"] > 0) & (df["data_years"] < YEARS)]
    if not incomplete.empty:
        print(f"注意: {len(incomplete)} 只股票财务数据未满 {YEARS} 年，分数参考性下降。")

    print("\n判定线: >=75 进入人工护城河核查; 55-74 有亮点有短板; <55 不符合框架。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
