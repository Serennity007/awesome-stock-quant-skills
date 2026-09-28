#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ensemble.py — 大师共识筛选器：把多个大师 skill 的打分结果合成为跨框架共识。

用法:
    python scripts/ensemble.py \
        --csvs ../dan-bin-rose-of-time/danbin_hs300_result.csv \
               ../li-lu-value-compounding/lilu_hs300_result.csv \
               ../oneil-canslim/canslim_hs300_result.csv \
        --min-frameworks 2 --out consensus.csv

逻辑:
    1. 读取多个打分 CSV（要求含 code/total 列，即各大师 screen.py 的输出）。
    2. 每个框架内部做百分位归一（0-100）：不同大师的分数量纲不同，
       直接平均会被"给分宽松的框架"绑架，百分位才是公平货币。
    3. 共识分 = 该股票在所有覆盖它的框架中百分位的均值；
       顶级命中数 = 处于该框架前 top-pct 分位（默认前 10%）的框架数。
    4. 按 --min-frameworks 过滤后按共识分排序输出。

输入 CSV 的文件名（去掉 _result/_test_result/_hs300_result 等后缀）
作为框架名，如 danbin_hs300_result.csv -> danbin。

提醒: 价值框架与动量框架天然对立（茅台与海康不会同时高分），
共识分高说明"多条互相独立的思路都指向它"，这是罕见的信号而非唯一真理。
"""
import os
import sys
import argparse
from datetime import datetime

os.environ.setdefault("TQDM_DISABLE", "1")
os.environ["TQDM_DISABLE"] = "1"

import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SUFFIXES = ["_hs300_result", "_test_result", "_result", "_demo", "_hs300"]


def framework_name(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0]
    for suf in SUFFIXES:
        if stem.endswith(suf):
            stem = stem[: -len(suf)]
            break
    return stem


def load_one(path: str) -> tuple:
    """读取一个框架的结果 CSV，返回 (框架名, DataFrame[code, total])。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到 {path}")
    df = pd.read_csv(path, dtype={"code": str})
    df["code"] = df["code"].astype(str).str.strip().str.zfill(6)
    for col in ("code", "total"):
        if col not in df.columns:
            raise ValueError(f"{path} 缺少 '{col}' 列——需要大师 screen.py 的原始输出")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df = df.dropna(subset=["total"]).drop_duplicates("code")
    if df.empty:
        raise ValueError(f"{path} 无有效行")
    return framework_name(path), df[["code", "total"]]


def main():
    ap = argparse.ArgumentParser(description="大师共识筛选器：多框架打分结果合成")
    ap.add_argument("--csvs", nargs="+", required=True,
                    help="多个大师 screen.py 的结果 CSV 路径（至少 2 个）")
    ap.add_argument("--top-pct", type=float, default=10.0,
                    help="单框架'顶级命中'的分位线%%（默认前 10%%）")
    ap.add_argument("--min-frameworks", type=int, default=2,
                    help="至少被几个框架覆盖才进入输出（默认 2）")
    ap.add_argument("--out", default="consensus.csv", help="CSV 输出路径")
    args = ap.parse_args()

    if len(args.csvs) < 2:
        sys.exit("ERROR: 至少需要 2 个框架的 CSV 才有共识可言")

    frames, names, meta = [], [], []
    for path in args.csvs:
        try:
            name, df = load_one(path)
        except Exception as e:
            print(f"跳过 {path}: {e}", file=sys.stderr)
            continue
        df = df.rename(columns={"total": f"{name}_raw"})
        # 框架内百分位（0-100）
        df[f"{name}_pct"] = (df[f"{name}_raw"].rank(pct=True) * 100).round(1)
        frames.append(df.set_index("code"))
        names.append(name)
        print(f"载入 {name}: {len(df)} 只（{os.path.basename(path)}）")

    if len(names) < 2:
        sys.exit("ERROR: 有效框架不足 2 个")

    merged = pd.concat(frames, axis=1)
    pct_cols = [f"{n}_pct" for n in names]
    merged["frameworks"] = merged[pct_cols].notna().sum(axis=1).astype(int)
    merged["consensus_score"] = merged[pct_cols].mean(axis=1).round(1)
    top_line = 100.0 - args.top_pct
    merged["top_hits"] = (merged[pct_cols] >= top_line).sum(axis=1).astype(int)

    out = merged[merged["frameworks"] >= args.min_frameworks].copy()
    out = out.sort_values(["consensus_score", "top_hits"], ascending=False)

    # 附加元信息（name/industry 取自第一个含该列的框架）
    for path in args.csvs:
        try:
            m = pd.read_csv(path, dtype={"code": str})
        except Exception:
            continue
        m["code"] = m["code"].astype(str).str.strip().str.zfill(6)
        for col in ("name", "industry"):
            if col in m.columns and col not in out.columns:
                out = out.join(m.drop_duplicates("code").set_index("code")[[col]], how="left")

    cols = (["name", "industry"] if "name" in out.columns else []) + \
           ["consensus_score", "top_hits", "frameworks"] + \
           [c for n in names for c in (f"{n}_pct", f"{n}_raw")]
    cols = [c for c in cols if c in out.columns]
    out = out[cols].reset_index()

    out.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"\n=== 共识前 20（共 {len(out)} 只被 ≥{args.min_frameworks} 个框架覆盖，完整见 {args.out}）===")
    print(out.head(20).to_string(index=False))

    hit_line = f"前 {args.top_pct:.0f}% 分位"
    print(f"\n口径说明: 每个框架内部按百分位归一（0-100）；consensus_score=各框架百分位均值；")
    print(f"top_hits=处于该框架 {hit_line} 的框架数（默认线 {top_line:.0f} 分）。")
    print("提醒: 价值框架与动量框架天然对立，共识分高=多条独立思路同时指向，属罕见信号，仍需人工定性复核。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
