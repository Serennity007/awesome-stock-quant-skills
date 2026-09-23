#!/usr/bin/env python3
"""concept_mapper.py — A股题材关键词 → 概念股映射器。

用法:
    python scripts/concept_mapper.py --keywords 商业航天
    python scripts/concept_mapper.py --keywords 商业航天,核聚变,固态电池 --top 15 --sort main_force --out result.csv

数据源: akshare 公开接口 + 同花顺行情中心页面（当 akshare 东方财富接口不可达时的降级来源）。
"""
import argparse
import os
import re
import sys
import time
from difflib import get_close_matches
from io import StringIO

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


def normalize_date(date_str: str) -> str:
    """兼容 20231231 与 2023-12-31 两种格式，统一返回 2023-12-31。"""
    s = str(date_str).strip().replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return date_str


def parse_percent(value) -> float:
    """把 '10.52%' 或 '10.52' 解析为 float；失败返回 nan。"""
    try:
        s = str(value).strip().replace(",", "").replace("%", "")
        return float(s) if s else float("nan")
    except Exception:
        return float("nan")


def parse_amount(value) -> float:
    """把 '7.06亿' / '1234万' / '1.2千' 解析为亿元。"""
    try:
        s = str(value).strip().replace(",", "")
        if not s:
            return float("nan")
        m = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([万亿千]?)", s)
        if not m:
            return float("nan")
        num, unit = float(m.group(1)), m.group(2)
        multipliers = {"": 1e-8, "万": 1e-4, "千": 1e-7, "亿": 1.0, "万亿": 10000.0}
        return num * multipliers.get(unit, 1e-8)
    except Exception:
        return float("nan")


def parse_up_down(text: str):
    """解析 '138/359' 为 (上涨家数, 下跌家数, 总家数)。"""
    try:
        parts = str(text).strip().split("/")
        if len(parts) == 2:
            up, total = int(parts[0]), int(parts[1])
            down = max(total - up, 0)
            return up, down, total
    except Exception:
        pass
    return None, None, None


def _ths_v_code() -> str:
    """计算同花顺反爬所需的 v_code。"""
    try:
        from akshare.datasets import get_ths_js
        from py_mini_racer import MiniRacer

        js_path = get_ths_js("ths.js")
        with open(js_path, encoding="utf-8") as f:
            js = f.read()
        ctx = MiniRacer()
        ctx.eval(js)
        return ctx.call("v")
    except Exception as e:
        raise RuntimeError(f"计算同花顺 v_code 失败: {e}")


def concept_name_map() -> pd.DataFrame:
    """同花顺概念板块名称与代码映射表。"""
    df = _retry_call(lambda: ak.stock_board_concept_name_ths())
    if df is None or df.empty or "name" not in df.columns or "code" not in df.columns:
        raise RuntimeError("获取同花顺概念板块列表为空或格式异常")
    df["name"] = df["name"].astype(str).str.strip()
    df["code"] = df["code"].astype(str).str.strip()
    return df


def fuzzy_match_concept(keyword: str, concepts: pd.DataFrame) -> str:
    """对关键词做模糊匹配，返回最相关的概念名称。"""
    kw = keyword.strip()
    if not kw:
        return None
    names = concepts["name"].tolist()
    # 1. 直接包含关键词，优先选名称最短的
    contains = [n for n in names if kw in n]
    if contains:
        return min(contains, key=len)
    # 2. 关键词包含于概念名（反向）
    reverse = [n for n in names if n in kw]
    if reverse:
        return min(reverse, key=len)
    # 3. 编辑距离最近
    close = get_close_matches(kw, names, n=1, cutoff=0.3)
    return close[0] if close else None


def board_info_ths(concept_name: str) -> dict:
    """同花顺概念板块简介，返回题材强度指标。"""
    df = _retry_call(lambda: ak.stock_board_concept_info_ths(symbol=concept_name))
    time.sleep(0.15)
    if df is None or df.empty:
        return {}
    df.columns = [str(c).strip() for c in df.columns]
    item_col, val_col = df.columns[0], df.columns[1]
    data = dict(zip(df[item_col].astype(str), df[val_col].astype(str)))

    def get(key):
        return data.get(key, "").strip()

    up, down, total = parse_up_down(get("涨跌家数"))
    return {
        "concept_name": concept_name,
        "board_change_pct": parse_percent(get("板块涨幅")),
        "board_main_force": float(get("资金净流入(亿)") or "nan"),
        "board_amount": float(get("成交额(亿)") or "nan"),
        "up_count": up,
        "down_count": down,
        "total_count": total,
    }


def _parse_em_cons(df: pd.DataFrame) -> pd.DataFrame:
    """统一东方财富成分股表的列名与类型。"""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename = {
        "代码": "code",
        "名称": "name",
        "最新价": "close",
        "涨跌幅": "change_pct",
        "换手率": "turnover",
        "成交额": "amount",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for col in ["close", "change_pct", "turnover"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce") * 1e-8  # 元 -> 亿元
    df["main_force"] = float("nan")
    return df[[c for c in ["code", "name", "close", "change_pct", "turnover", "amount", "main_force"] if c in df.columns]]


def fetch_cons_em(concept_name: str) -> pd.DataFrame:
    """优先尝试 akshare 东方财富成分股接口。"""
    df = _retry_call(lambda: ak.stock_board_concept_cons_em(symbol=concept_name))
    time.sleep(0.15)
    return _parse_em_cons(df)


def fetch_cons_ths_page(concept_code: str, pages: int = 5) -> pd.DataFrame:
    """降级：从同花顺概念详情页抓取成分股（每页 10 条）。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }
    rows = []
    for page in range(1, pages + 1):
        url = f"http://q.10jqka.com.cn/gn/detail/code/{concept_code}/page/{page}/"
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.encoding = "gbk"
            dfs = pd.read_html(StringIO(r.text))
            if not dfs:
                break
            df = dfs[0]
            if df.empty:
                break
            df.columns = [str(c).strip() for c in df.columns]
            # 同花顺表头可能因版本不同而变化，按常见列名匹配
            rename = {}
            for c in df.columns:
                if c == "代码":
                    rename[c] = "code"
                elif c == "名称":
                    rename[c] = "name"
                elif "现价" in c:
                    rename[c] = "close"
                elif "涨跌幅" in c:
                    rename[c] = "change_pct"
                elif "换手" in c:
                    rename[c] = "turnover"
                elif "成交额" in c:
                    rename[c] = "amount"
            df = df.rename(columns=rename)
            df["code"] = df["code"].astype(str).str.strip().str.zfill(6)
            df["name"] = df["name"].astype(str).str.strip()
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["change_pct"] = df["change_pct"].apply(parse_percent)
            df["turnover"] = df["turnover"].apply(parse_percent)
            df["amount"] = df["amount"].apply(parse_amount)
            df["main_force"] = float("nan")
            rows.append(df[[c for c in ["code", "name", "close", "change_pct", "turnover", "amount", "main_force"] if c in df.columns]])
            # 如果一页不足 10 行，说明已到末尾
            if len(df) < 10:
                break
        except Exception as e:
            print(f"  同花顺成分股第 {page} 页抓取失败: {e}", file=sys.stderr)
            break
        time.sleep(0.15)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).drop_duplicates(subset=["code"])


def fetch_main_force_map() -> pd.Series:
    """从同花顺个股资金流页面抓取全市场主力净流入映射（代码 -> 亿元）。"""
    try:
        v_code = _ths_v_code()
    except Exception as e:
        print(f"  主力资金映射获取失败（v_code）: {e}", file=sys.stderr)
        return pd.Series(dtype=float)

    headers = {
        "Accept": "text/html, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "hexin-v": v_code,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "http://data.10jqka.com.cn/funds/ggzjl/",
        "Host": "data.10jqka.com.cn",
    }
    # 先请求第一页拿总页数
    first_url = "http://data.10jqka.com.cn/funds/ggzjl/field/zdf/order/desc/page/1/ajax/1/free/1/"
    r = requests.get(first_url, headers=headers, timeout=20)
    r.encoding = "gbk"
    dfs = pd.read_html(StringIO(r.text))
    if not dfs:
        return pd.Series(dtype=float)
    first_df = dfs[0]
    page_info = re.search(r'<span class="page_info">(\d+)/(\d+)</span>', r.text)
    page_num = int(page_info.group(2)) if page_info else 1

    rows = []
    for page in range(1, min(page_num, 120) + 1):  # 全市场约 100 页，抓全
        url = f"http://data.10jqka.com.cn/funds/ggzjl/field/zdf/order/desc/page/{page}/ajax/1/free/1/"
        try:
            rr = requests.get(url, headers=headers, timeout=20)
            rr.encoding = "gbk"
            dfs = pd.read_html(StringIO(rr.text))
            if dfs:
                df = dfs[0]
                df.columns = [str(c).strip() for c in df.columns]
                # 列位置固定：第2列代码，第3列简称，第9列净流入（按常见表头）
                cols = df.columns.tolist()
                if len(cols) >= 10:
                    code_col, net_col = cols[1], cols[8]
                    for _, row in df.iterrows():
                        code = str(row[code_col]).strip().zfill(6)
                        net = parse_amount(row[net_col])
                        if code and len(code) == 6 and pd.notna(net):
                            rows.append((code, net))
        except Exception as e:
            print(f"  主力资金第 {page} 页抓取失败: {e}", file=sys.stderr)
            break
        time.sleep(0.15)
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series({c: v for c, v in rows})
    return s[~s.index.duplicated(keep="first")]


def build_cons_df(concept_name: str, concept_code: str, top: int, sort_by: str, mf_map: pd.Series, full_fetch: bool = False) -> tuple:
    """获取某个概念的成分股并按指定维度排序取 top；返回 (df, source, note)。"""
    df = pd.DataFrame()
    source = ""
    note = ""
    try:
        df = fetch_cons_em(concept_name)
        if not df.empty:
            source = "akshare.stock_board_concept_cons_em"
    except Exception as e:
        print(f"  东方财富成分股接口失败，降级到同花顺页面: {e}", file=sys.stderr)
    if df.empty:
        pages = 100 if full_fetch else max(1, (top // 10) + 2)
        df = fetch_cons_ths_page(concept_code, pages=pages)
        source = "同花顺概念详情页(降级)"
    if df.empty:
        return pd.DataFrame(), source, note

    # 尝试补全主力净流入
    if not mf_map.empty:
        df["main_force"] = df["code"].map(mf_map)

    # 若主力资金整列为空，重试一次资金流页面；仍失败则以成交额代理并在备注列标注
    if "main_force" in df.columns and df["main_force"].isna().all():
        try:
            mf_map_retry = _retry_call(fetch_main_force_map, max_retries=2)
        except Exception as e:
            print(f"  主力资金重试失败: {e}", file=sys.stderr)
            mf_map_retry = pd.Series(dtype=float)
        if not mf_map_retry.empty:
            df["main_force"] = df["code"].map(mf_map_retry)

    if "main_force" in df.columns and df["main_force"].isna().all() and "amount" in df.columns:
        df["main_force"] = df["amount"].copy()
        note = "main_force 以成交额 amount 代理（资金流页面未获取）"

    sort_col = {"change_pct": "change_pct", "turnover": "turnover", "main_force": "main_force"}.get(sort_by, "change_pct")
    if sort_col not in df.columns or df[sort_col].isna().all():
        sort_col = "change_pct"
    df = df.sort_values(sort_col, ascending=False, na_position="last").head(top).reset_index(drop=True)
    df["theme_rank"] = df.index + 1
    return df, source, note


def main():
    ap = argparse.ArgumentParser(description="A股题材关键词 → 概念股映射器")
    ap.add_argument("--keywords", required=True, help="逗号分隔的题材关键词，如 商业航天,核聚变")
    ap.add_argument("--top", type=int, default=15, help="每个题材取前 N 只成分股（默认 15）")
    ap.add_argument("--sort", default="change_pct", choices=["change_pct", "turnover", "main_force"], help="排序维度（默认 change_pct）")
    ap.add_argument("--out", default="concept_stocks.csv", help="CSV 输出路径")
    ap.add_argument("--no-proxy", action="store_true", help="兼容旧参数，现脚本已默认禁用系统代理")
    args = ap.parse_args()

    # 默认禁用系统代理，避免本地代理（如 127.0.0.1:7890）导致同花顺/东财接口失败
    _disable_proxies()
    # --no-proxy 保留兼容：传与不传效果相同
    if args.no_proxy:
        _disable_proxies()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        sys.exit("ERROR: --keywords 不能为空")

    print(f"正在加载概念板块列表（akshare {ak.__version__}）...")
    concepts = concept_name_map()
    time.sleep(0.15)

    # 提前准备全市场主力净流入映射，避免每个题材重复抓取
    print("正在准备主力资金映射（同花顺个股资金流），可能需要几秒...")
    try:
        mf_map = fetch_main_force_map()
    except Exception as e:
        print(f"  主力资金映射初始化失败: {e}", file=sys.stderr)
        mf_map = pd.Series(dtype=float)

    theme_summary_rows = []
    all_cons = []
    failed = []

    for kw in keywords:
        print(f"\n关键词: {kw}")
        concept_name = fuzzy_match_concept(kw, concepts)
        if concept_name is None:
            print(f"  未找到匹配的概念板块", file=sys.stderr)
            failed.append((kw, "未找到匹配的概念板块"))
            continue
        print(f"  命中板块: {concept_name}")

        concept_code_row = concepts[concepts["name"] == concept_name]
        concept_code = str(concept_code_row["code"].iloc[0]) if not concept_code_row.empty else None

        # 题材强度
        try:
            info = board_info_ths(concept_name)
        except Exception as e:
            print(f"  题材强度获取失败: {e}", file=sys.stderr)
            info = {"concept_name": concept_name}

        # 成分股
        try:
            # 非默认排序时需要尽可能抓全成分股，否则本地排序会受页面默认涨幅排序影响
            full_fetch = args.sort in ("turnover", "main_force")
            cons_df, source, note = build_cons_df(concept_name, concept_code, args.top, args.sort, mf_map, full_fetch=full_fetch)
        except Exception as e:
            print(f"  成分股获取失败: {e}", file=sys.stderr)
            failed.append((kw, f"成分股获取失败: {e}"))
            continue

        if cons_df.empty:
            failed.append((kw, "成分股为空"))
            continue

        # 用成分股数量补齐 info 中的 total_count
        if info.get("total_count") is None:
            info["total_count"] = len(cons_df)

        print(f"  数据来源: {source} | 成分股数量: {info.get('total_count')} | 本题材输出: {len(cons_df)}")
        print(f"  板块涨幅: {info.get('board_change_pct')} | 资金净流入(亿): {info.get('board_main_force')} | 成交额(亿): {info.get('board_amount')}")

        theme_summary_rows.append({
            "keyword": kw,
            "concept_name": concept_name,
            "board_change_pct": info.get("board_change_pct"),
            "board_main_force": info.get("board_main_force"),
            "board_amount": info.get("board_amount"),
            "up_count": info.get("up_count"),
            "down_count": info.get("down_count"),
            "total_count": info.get("total_count"),
        })

        cons_df["keyword"] = kw
        cons_df["concept_name"] = concept_name
        for k2 in ["board_change_pct", "board_main_force", "board_amount", "up_count", "down_count", "total_count"]:
            cons_df[k2] = info.get(k2)
        cons_df["sort_by"] = args.sort
        cons_df["note"] = note
        all_cons.append(cons_df)
        print(cons_df.head(min(5, len(cons_df)))[["theme_rank", "code", "name", "close", "change_pct", "turnover", "amount", "main_force"]].to_string(index=False))

    if not all_cons:
        sys.exit("ERROR: 所有关键词均未获取到成分股，请检查网络、关键词或升级 akshare")

    summary_df = pd.DataFrame(theme_summary_rows)
    out_df = pd.concat(all_cons, ignore_index=True)
    out_df["data_date"] = normalize_date(pd.Timestamp.now().strftime("%Y%m%d"))
    out_cols = [
        "keyword", "concept_name", "board_change_pct", "board_main_force", "board_amount",
        "up_count", "down_count", "total_count", "theme_rank", "sort_by", "data_date",
        "code", "name", "close", "change_pct", "turnover", "amount", "main_force", "note",
    ]
    out_df = out_df[[c for c in out_cols if c in out_df.columns]]
    out_df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print("\n=== 题材强度对比 ===")
    print(summary_df.to_string(index=False))
    print(f"\n完整结果已写入: {args.out}")
    print("说明: 当 note 列标注 'main_force 以成交额 amount 代理' 时，表示主力资金页面抓取失败并已用成交额作为活跃度代理。")
    print("免责声明: 本工具仅供学习研究，不构成投资建议。")


if __name__ == "__main__":
    main()
