#!/usr/bin/env python3
"""hot_themes.py — A股热点题材扫描器。

用法:
    python scripts/hot_themes.py --days 5 --top 20 --out hot_themes.csv
    python scripts/hot_themes.py --days 1 --top 15

输出: 结构化热度表（题材、匹配板块、涨幅、主力净流入、领涨股、连续上榜天数）。
数据源: akshare（东方财富/同花顺公开接口）。
代理: 默认自动绕过系统代理，避免 127.0.0.1:7890 等本地代理阻断数据源；
      先尝试东方财富接口，失败自动降级同花顺。
"""
import os
import time

os.environ.setdefault("TQDM_DISABLE", "1")

import argparse
import re
import sys
from pathlib import Path
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

# 可用时间窗口：akshare stock_fund_flow_concept 支持的 symbol 与对应近似天数
TIME_FRAMES = [
    ("即时", 1),
    ("3日排行", 3),
    ("5日排行", 5),
    ("10日排行", 10),
]


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


def _disable_system_proxy():
    """禁用系统代理，避免本地代理（常见如 127.0.0.1:7890）阻断东方财富/同花顺接口。"""
    requests.utils.getproxies = lambda: {}
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ.pop(k, None)


def parse_glossary(path: Path) -> list:
    """解析 references/theme_glossary.md 中的题材表。

    返回: [{"name": ..., "aliases": [...], "logic": ..., "catalyst": ..., "stocks": ...}, ...]
    """
    if not path.exists():
        sys.exit(f"ERROR: 找不到题材词典: {path}")
    text = path.read_text(encoding="utf-8")
    rows = []
    in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("|") and "题材名" in line:
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")][1:-1]
        if len(parts) < 5 or parts[0] == "题材名":
            continue
        name, aliases, logic, catalyst, stocks = parts[0], parts[1], parts[2], parts[3], parts[4]
        alias_list = [a.strip() for a in aliases.replace("、", ",").split(",") if a.strip()]
        rows.append({
            "name": name,
            "aliases": alias_list,
            "logic": logic,
            "catalyst": catalyst,
            "stocks": stocks,
        })
    if not rows:
        print("WARN: 未从词典中解析到题材，将使用内置默认热点题材", file=sys.stderr)
        rows = _default_themes()
    return rows


def _default_themes() -> list:
    """当 glossary 解析失败时的兜底热点题材。"""
    return [
        {"name": "光模块/CPO", "aliases": ["共封装光学", "CPO", "光通信"], "logic": "", "catalyst": "", "stocks": ""},
        {"name": "PCB", "aliases": ["PCB概念", "印制电路板", "HDI"], "logic": "", "catalyst": "", "stocks": ""},
        {"name": "MLCC", "aliases": ["MLCC概念", "片式多层陶瓷电容"], "logic": "", "catalyst": "", "stocks": ""},
        {"name": "存储", "aliases": ["存储芯片", "存储器", "HBM"], "logic": "", "catalyst": "", "stocks": ""},
        {"name": "商业航天", "aliases": ["商业航天概念", "卫星互联网", "低轨卫星"], "logic": "", "catalyst": "", "stocks": ""},
        {"name": "可控核聚变", "aliases": ["核聚变", "人造太阳"], "logic": "", "catalyst": "", "stocks": ""},
        {"name": "固态电池", "aliases": ["固态电池概念", "全固态电池"], "logic": "", "catalyst": "", "stocks": ""},
        {"name": "创新药", "aliases": ["创新药概念", "CRO", "减肥药"], "logic": "", "catalyst": "", "stocks": ""},
        {"name": "军工重组", "aliases": ["军工", "军工重组", "国防军工"], "logic": "", "catalyst": "", "stocks": ""},
    ]


def _match_score(theme: dict, board_name: str) -> int:
    """返回题材与板块名的匹配得分；0 表示不匹配。得分越高代表关联越直接。"""
    if not board_name:
        return 0
    bn = board_name.strip().lower()
    name = theme["name"].strip().lower()

    # 题材名本身
    if name == bn:
        return 100
    if name in bn:
        return 80
    if bn in name:
        return 60

    # 别名
    for alias in theme.get("aliases", []):
        a = alias.strip().lower()
        if not a:
            continue
        if a == bn:
            return 50
        if len(a) >= 4:
            if a in bn or bn in a:
                return 40
        else:
            if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", bn):
                return 40
    return 0


def _theme_matches(theme: dict, board_name: str) -> bool:
    """判断题材是否匹配板块名。"""
    return _match_score(theme, board_name) > 0


def fetch_fund_flow_frames() -> dict:
    """拉取 1/3/5/10 日概念资金流向排行。返回 {days: DataFrame}。"""
    frames = {}
    for symbol, days in TIME_FRAMES:
        try:
            df = _retry_call(lambda s=symbol: ak.stock_fund_flow_concept(symbol=s))
            time.sleep(0.15)
        except Exception as e:
            print(f"WARN: 获取概念资金流向 '{symbol}' 失败: {e}", file=sys.stderr)
            continue
        if df is None or df.empty:
            continue
        df.columns = [str(c).strip() for c in df.columns]
        df = df.copy()
        # 统一列名：3/5/10日排行的涨跌幅列名为'阶段涨跌幅'，即时为'行业-涨跌幅'
        if "阶段涨跌幅" in df.columns and "行业-涨跌幅" not in df.columns:
            df["行业-涨跌幅"] = df["阶段涨跌幅"]
        # 数值化涨跌幅（可能带 % 号）
        chg_col = "行业-涨跌幅"
        if chg_col in df.columns:
            df[chg_col] = pd.to_numeric(df[chg_col].astype(str).str.replace("%", ""), errors="coerce")
        # 数值化净流入
        if "净额" in df.columns:
            df["净额"] = pd.to_numeric(df["净额"], errors="coerce")
        # 领涨股涨跌幅
        if "领涨股-涨跌幅" in df.columns:
            df["领涨股-涨跌幅"] = pd.to_numeric(
                df["领涨股-涨跌幅"].astype(str).str.replace("%", ""), errors="coerce"
            )
        frames[days] = df
    return frames


def fetch_em_concept_boards() -> Optional[pd.DataFrame]:
    """尝试东方财富概念板块接口；失败返回 None。"""
    try:
        df = _retry_call(lambda: ak.stock_board_concept_name_em())
        time.sleep(0.15)
        return df
    except Exception as e:
        print(f"INFO: 东方财富概念板块接口不可用，降级处理: {e}", file=sys.stderr)
        return None


def fetch_hot_rank() -> Optional[pd.DataFrame]:
    """拉取同花顺热股榜，用于辅助热度验证。"""
    try:
        df = _retry_call(lambda: ak.stock_hot_rank_em())
        time.sleep(0.15)
        return df
    except Exception as e:
        print(f"INFO: 同花顺热股榜获取失败: {e}", file=sys.stderr)
        return None


def select_window_frame(frames: dict, days: int) -> tuple[int, pd.DataFrame]:
    """根据 --days 选择最接近的可用时间窗口。"""
    available = sorted(frames.keys())
    if not available:
        raise RuntimeError("没有可用的概念资金流向数据")
    chosen = max((d for d in available if d <= days), default=available[0])
    return chosen, frames[chosen]


def _leader_for_board(board_name: str, frames: dict) -> tuple[str, Optional[float]]:
    """从即时窗口中查找指定板块的领涨股；若无时返回 ('', None)。"""
    if 1 not in frames:
        return "", None
    df = frames[1]
    row = df[df["行业"] == board_name]
    if row.empty:
        return "", None
    leader = str(row.iloc[0].get("领涨股", ""))
    leader_chg = row.iloc[0].get("领涨股-涨跌幅")
    leader_chg = float(leader_chg) if pd.notna(leader_chg) else None
    return leader, leader_chg


def build_heat_table(themes: list, frames: dict, days: int, top_n: int) -> pd.DataFrame:
    """构建结构化热度表。"""
    chosen_window, primary_df = select_window_frame(frames, days)
    rows = []
    for theme in themes:
        # 在主要窗口中匹配板块
        matched = primary_df[primary_df["行业"].apply(lambda x: _theme_matches(theme, str(x)))]
        if matched.empty:
            continue
        # 若命中多个板块，按匹配得分优先，同分取涨幅最高者
        matched = matched.copy()
        matched["_score"] = matched["行业"].apply(lambda x: _match_score(theme, str(x)))
        best = matched.sort_values(["_score", "行业-涨跌幅"], ascending=[False, False]).iloc[0]
        board_name = str(best["行业"])
        chg = float(best["行业-涨跌幅"]) if pd.notna(best["行业-涨跌幅"]) else None
        net = float(best["净额"]) if pd.notna(best.get("净额")) else None

        # 领涨股优先从即时窗口取，若即时无则尝试主窗口
        leader = str(best.get("领涨股", "")) if pd.notna(best.get("领涨股")) else ""
        leader_chg = float(best["领涨股-涨跌幅"]) if pd.notna(best.get("领涨股-涨跌幅")) else None
        if not leader:
            leader, leader_chg = _leader_for_board(board_name, frames)

        # 计算连续上榜天数：在 1/3/5/10 日排行中连续进入前 top_n 的最长窗口
        consecutive_days = 0
        for d in sorted(frames.keys()):
            df = frames[d]
            top_df = df.head(top_n)
            hit = top_df["行业"].apply(lambda x: _theme_matches(theme, str(x))).any()
            if hit:
                consecutive_days = d
            else:
                break

        rows.append({
            "题材": theme["name"],
            "匹配板块": board_name,
            "统计窗口": f"近{chosen_window}日",
            "阶段涨幅%": round(chg, 2) if chg is not None else None,
            "主力净流入（亿元）": round(net, 2) if net is not None else None,
            "领涨股": leader,
            "领涨股涨幅%": round(leader_chg, 2) if leader_chg is not None else None,
            "连续上榜天数": consecutive_days,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # 排序：连续上榜天数降序，然后阶段涨幅降序
    df = df.sort_values(["连续上榜天数", "阶段涨幅%"], ascending=[False, False]).reset_index(drop=True)
    return df


def main():
    ap = argparse.ArgumentParser(description="A股热点题材扫描器")
    ap.add_argument("--days", type=int, default=5, help="统计窗口天数，支持 1/3/5/10（默认5）")
    ap.add_argument("--top", type=int, default=20, help="进入排行前 N 名视为热门（默认20）")
    ap.add_argument("--out", default="hot_themes.csv", help="CSV 输出路径（默认 hot_themes.csv）")
    ap.add_argument("--no-proxy", action="store_true", help="禁用系统代理（默认已自动禁用，保留兼容参数）")
    args = ap.parse_args()

    # 默认绕过系统代理；--no-proxy 保持兼容（与默认行为一致）
    _disable_system_proxy()

    script_dir = Path(__file__).resolve().parent
    glossary_path = script_dir.parent / "references" / "theme_glossary.md"
    themes = parse_glossary(glossary_path)
    print(f"已加载 {len(themes)} 个热点题材，统计窗口请求={args.days}日，热门阈值=前{args.top}名\n")

    # 1. 尝试东方财富概念板块（按要求优先），失败则仅记录信息
    em_boards = fetch_em_concept_boards()
    if em_boards is not None:
        print(f"东方财富概念板块接口可用，获取 {len(em_boards)} 个板块（当前环境可能无法进一步获取成分股，将用资金流向补充）")

    # 2. 拉取同花顺概念资金流向（主要数据来源）
    print("正在拉取概念板块资金流向排行（1/3/5/10日）...")
    frames = fetch_fund_flow_frames()
    if not frames:
        sys.exit("ERROR: 所有概念资金流向接口均不可用，请检查网络或升级 akshare（pip install -U akshare）")

    # 3. 拉取热股榜辅助验证
    hot_rank = fetch_hot_rank()
    if hot_rank is not None:
        print(f"同花顺热股榜可用，共 {len(hot_rank)} 条\n")

    # 4. 构建热度表
    df = build_heat_table(themes, frames, args.days, args.top)
    if df.empty:
        print("WARN: 未匹配到任何热门题材，可能当前窗口无热点或词典别名需更新", file=sys.stderr)
        # 仍输出空表
        df.to_csv(args.out, index=False, encoding="utf-8-sig")
        print(f"空表已写入 {args.out}")
        return

    # 5. 输出
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    display_cols = ["题材", "匹配板块", "统计窗口", "阶段涨幅%", "主力净流入（亿元）", "领涨股", "领涨股涨幅%", "连续上榜天数"]
    print("=== 热点题材扫描结果 ===")
    print(df[display_cols].to_string(index=False))
    print(f"\n共匹配 {len(df)} 个热点题材，完整结果已写入 {args.out}")
    print("免责声明：仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
