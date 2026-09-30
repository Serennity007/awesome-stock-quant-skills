#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_history.py — 回测数据缓存器：逐股拉取历史估值/财务指标/利润表并落盘。

用法:
    python scripts/fetch_history.py --pool hs300            # 全池（可断点续传）
    python scripts/fetch_history.py --offset 0 --limit 100  # 分块

每只股票缓存 3 个 CSV（存 cache/ 目录，已被 .gitignore 排除）:
    value_{code}.csv    东财历史估值: 数据日期/收盘价/PE(TTM)/市净率（约2018年至今日线）
    ind_{code}.csv      东财年度财务指标: ROE/负债率/现金流比/净利润增速/营收增速（2015年起年报）
    profit_{code}.csv   东财年度利润表: 营业总收入/营业成本（算毛利率，年报）

已存在的股票自动跳过——中断后重跑即续传。
"""
import os
import sys
import time
import argparse
from datetime import datetime

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

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")

VALUE_COLS = ["数据日期", "当日收盘价", "PE(TTM)", "市净率"]
IND_COLS = ["日期", "净资产收益率(%)", "资产负债率(%)", "经营现金净流量与净利润的比率(%)",
            "净利润增长率(%)", "主营业务收入增长率(%)"]
PROFIT_COLS = ["REPORT_DATE", "OPERATE_INCOME", "OPERATE_COST"]


def _disable_proxies():
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(k, None)
    # akshare 内部 requests 不带 timeout，个别挂起连接会无限阻塞
    _orig_request = requests.Session.request

    def _with_timeout(self, *args, **kwargs):
        kwargs.setdefault("timeout", 20)
        return _orig_request(self, *args, **kwargs)

    requests.Session.request = _with_timeout


def _retry(func, n=3):
    last = None
    for i in range(n):
        try:
            return func()
        except Exception as e:
            last = e
            if i < n - 1:
                time.sleep(1.5 * (2 ** i))
    raise last


def _find_col(cands, df):
    for c in df.columns:
        for cand in cands:
            if cand in str(c):
                return c
    return None


def fetch_one(code: str) -> tuple:
    """拉一只股票的三类数据，返回 (value_rows, ind_rows, profit_rows)。"""
    # 1. 历史估值（全量日线）
    v = _retry(lambda: ak.stock_value_em(symbol=code))
    time.sleep(0.15)
    v = v[[c for c in VALUE_COLS if c in v.columns]].copy()
    v = v[v["数据日期"].astype(str).str.replace("-", "").str[:8].le(datetime.now().strftime("%Y%m%d"))]

    # 2. 年度财务指标（2015 起年报）
    d = _retry(lambda: ak.stock_financial_analysis_indicator(symbol=code, start_year="2015"))
    time.sleep(0.15)
    d.columns = [str(c).strip() for c in d.columns]
    date_col = _find_col(["日期"], d) or d.columns[0]
    d = d.copy()
    d[date_col] = pd.to_datetime(d[date_col].astype(str).str.replace("-", "", regex=False),
                                 format="%Y%m%d", errors="coerce")
    d = d[(d[date_col].dt.month == 12) & (d[date_col] <= pd.Timestamp.now())]
    keep = [c for c in IND_COLS if c in d.columns and c != date_col]
    d = d[[date_col] + keep].rename(columns={date_col: "日期"})

    # 3. 年度利润表（算毛利率）：EM 优先，失败降级新浪（东财类型探测子接口会挂）
    try:
        p = _retry(lambda: ak.stock_profit_sheet_by_report_em(symbol=code))
        time.sleep(0.15)
        p.columns = [str(c).strip() for c in p.columns]
        pdate = _find_col(["REPORT_DATE"], p)
        p = p.copy()
        p[pdate] = pd.to_datetime(p[pdate], errors="coerce")
        p = p[(p[pdate].dt.month == 12) & (p[pdate] <= pd.Timestamp.now())].tail(12)
        pkeep = [c for c in PROFIT_COLS if c in p.columns and c != pdate]
        p = p[[pdate] + pkeep].rename(columns={pdate: "REPORT_DATE"})
        p = p.rename(columns={"OPERATE_INCOME": "营业总收入", "OPERATE_COST": "营业成本"})
    except Exception:
        inc = _retry(lambda: ak.stock_financial_report_sina(stock=code, symbol="利润表"))
        time.sleep(0.15)
        if inc is None or inc.empty:
            raise RuntimeError("利润表 EM 与新浪均失败")
        inc = inc.copy()
        inc["报告日"] = inc["报告日"].astype(str).str.replace("-", "")
        inc = inc[inc["报告日"].str.endswith("1231")].tail(12)
        # 银行/保险等利润表无"营业成本"列（利息支出模式，毛利率无意义）——
        # 存 REPORT_DATE 单列空壳，回测引擎检测后按中性分处理（与 screen.py 一致）
        if "营业成本" not in inc.columns:
            p = pd.DataFrame({"REPORT_DATE": pd.to_datetime(inc["报告日"], format="%Y%m%d", errors="coerce")})
            p = p.dropna(subset=["REPORT_DATE"])
        else:
            p = inc[["报告日", "营业总收入", "营业成本"]].rename(columns={"报告日": "REPORT_DATE"})
            p["REPORT_DATE"] = pd.to_datetime(p["REPORT_DATE"], format="%Y%m%d", errors="coerce")
            p = p.dropna(subset=["REPORT_DATE"])
    p.columns = [str(c).strip() for c in p.columns]

    return v, d, p


def get_pool(pool: str) -> list:
    if pool != "hs300":
        sys.exit(f"ERROR: 未知股票池 '{pool}'")
    df = _retry(lambda: ak.index_stock_cons_csindex(symbol="000300"))
    time.sleep(0.2)
    col = _find_col(["成分券代码"], df)
    if col is None:
        df = _retry(lambda: ak.index_stock_cons_weight_csindex(symbol="000300"))
        time.sleep(0.2)
        col = _find_col(["成分券代码", "股票代码"], df)
    return [str(x).zfill(6) for x in df[col].tolist()]


def main():
    ap = argparse.ArgumentParser(description="回测数据缓存器")
    ap.add_argument("--pool", default="hs300")
    ap.add_argument("--codes", default=None, help="逗号分隔，优先于 --pool")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    _disable_proxies()
    os.makedirs(CACHE_DIR, exist_ok=True)

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else get_pool(args.pool)
    codes = [c.zfill(6) for c in codes]
    if args.offset or args.limit:
        codes = codes[args.offset: args.offset + args.limit if args.limit else None]

    todo = []
    for c in codes:
        have = all(os.path.exists(os.path.join(CACHE_DIR, f"{p}_{c}.csv"))
                   for p in ("value", "ind", "profit"))
        if not have:
            todo.append(c)
    print(f"共 {len(codes)} 只，其中 {len(codes) - len(todo)} 只已有缓存，待拉取 {len(todo)} 只")

    failed = []
    for i, code in enumerate(todo, 1):
        try:
            v, d, p = fetch_one(code)
            v.to_csv(os.path.join(CACHE_DIR, f"value_{code}.csv"), index=False, encoding="utf-8-sig")
            d.to_csv(os.path.join(CACHE_DIR, f"ind_{code}.csv"), index=False, encoding="utf-8-sig")
            p.to_csv(os.path.join(CACHE_DIR, f"profit_{code}.csv"), index=False, encoding="utf-8-sig")
            print(f"[{i}/{len(todo)}] {code} OK (value {len(v)} 行 / ind {len(d)} 行 / profit {len(p)} 行)")
        except Exception as e:
            failed.append(code)
            print(f"[{i}/{len(todo)}] {code} FAIL: {str(e)[:80]}", file=sys.stderr)
        time.sleep(args.sleep)

    print(f"\n完成。本次成功 {len(todo) - len(failed)} 只，失败 {len(failed)} 只: {failed[:10]}")
    print(f"缓存目录: {CACHE_DIR}")
    # 全部就绪时写完成 flag（供外层重启循环检测）
    remaining = 0
    for c in get_pool("hs300"):
        have = all(os.path.exists(os.path.join(CACHE_DIR, f"{p}_{c}.csv"))
                   for p in ("value", "ind", "profit"))
        if not have:
            remaining += 1
    if remaining == 0:
        with open(os.path.join(os.path.dirname(CACHE_DIR), "fetch_done.flag"), "w") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("全部缓存就绪，已写 fetch_done.flag")


if __name__ == "__main__":
    main()
