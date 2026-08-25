"""Dimension 4 · 同行对比 — 产出 peer_table + peer_comparison."""
from __future__ import annotations

import json
import os
import sys
import time

import akshare as ak  # type: ignore
from lib import data_sources as ds
from lib.global_peers import fetch_global_peer_comparison
from lib.market_router import parse_ticker


def _float(v, default=0.0):
    try:
        s = str(v).replace(",", "").replace("%", "")
        if s in ("", "nan", "-", "--", "None"):
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def _build_self_only_table(ti, basic: dict) -> tuple[list, list]:
    """v2.12.1 · Tier 4 兜底：只返回公司自己一行，agent 可识别需外部补同行数据."""
    self_row = {
        "name": basic.get("name") or ti.full,
        "code": ti.full,
        "pe": f"{_float(basic.get('pe_ttm')):.1f}" if _float(basic.get("pe_ttm")) > 0 else "—",
        "pb": f"{_float(basic.get('pb')):.2f}" if _float(basic.get("pb")) > 0 else "—",
        "roe": "—",
        "revenue_growth": "—",
        "is_self": True,
    }
    return [self_row], []


def _attach_global_peers(data: dict, ti, basic: dict) -> dict:
    """Attach global peers without allowing the optional source to fail dim 4."""
    out = dict(data)
    if os.getenv("UZI_DISABLE_GLOBAL_PEERS", "").strip().lower() in {"1", "true", "yes"}:
        out["global_peer_comparison"] = {"conclusion_status": "disabled", "peer_count": 0}
        return out
    if not (basic.get("name") and basic.get("industry")):
        out["global_peer_comparison"] = {
            "conclusion_status": "insufficient_target_profile",
            "peer_count": 0,
        }
        return out
    try:
        limit = max(3, min(int(os.getenv("UZI_GLOBAL_PEER_LIMIT", "8")), 12))
        out["global_peer_comparison"] = fetch_global_peer_comparison(
            ti,
            basic=basic,
            limit=limit,
        )
    except Exception as exc:
        out["global_peer_comparison"] = {
            "conclusion_status": "unavailable",
            "peer_count": 0,
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
        }
    return out


def main(ticker: str) -> dict:
    ti = parse_ticker(ticker)
    basic = ds.fetch_basic(ti)
    industry = basic.get("industry") or ""
    peers_raw: list = []
    peer_table: list = []
    peer_comparison: list = []

    # v2.5 · HK 分支：用 akshare HK valuation/scale comparison 给出 rank-in-HK-universe，
    # 没有具体同行名单（akshare 港股没有按行业列表函数；agent 可走 AASTOCKS Playwright 兜底）
    if ti.market == "H":
        # v2.12.1 · HK 分支独立 try/except 隔离（HK 数据路径与 A 股独立，失败不应污染）
        try:
            ranks = (basic.get("_ranks") or {})
            val = ranks.get("valuation") or {}
            scale = ranks.get("scale") or {}
            growth = ranks.get("growth") or {}
        except Exception:
            ranks, val, scale, growth = {}, {}, {}, {}
        # 用 PE/PB/Mcap 排名构造一行 self
        self_row = {
            "name": basic.get("name") or ti.full,
            "code": ti.full,
            "pe": f"{val.get('pe_ttm', 0):.1f}" if val.get("pe_ttm") else "—",
            "pb": f"{val.get('pb_mrq', 0):.2f}" if val.get("pb_mrq") else "—",
            "roe": "—",
            "revenue_growth": f"{growth.get('revenue_yoy', 0):.1f}%" if growth.get("revenue_yoy") else "—",
            "is_self": True,
        }
        peer_table = [self_row]
        peer_comparison = [
            {"name": "PE-TTM 排名 (HK 全市场)", "self": val.get("pe_ttm_rank"), "peer": "—"},
            {"name": "PB-MRQ 排名 (HK 全市场)", "self": val.get("pb_mrq_rank"), "peer": "—"},
            {"name": "总市值排名 (HK 全市场)", "self": scale.get("market_cap_rank"), "peer": "—"},
            {"name": "营收 YoY 排名", "self": growth.get("revenue_yoy_rank"), "peer": "—"},
        ]
        # rank string for the report
        mcap_rank = scale.get("market_cap_rank")
        rank_str = f"HK 第 {mcap_rank} 位（按总市值）" if mcap_rank else "—"
        hk_data = _attach_global_peers({
                "industry": industry or "未分类（akshare HK 无行业聚合）",
                "self": basic,
                "peer_table": peer_table,
                "peer_comparison": peer_comparison,
                "rank": rank_str,
                "peers_top20_raw": [],
                "_note": "HK peer LIST 需走 AASTOCKS Playwright 或问财；本字段提供 rank-in-universe 作替代",
            }, ti, basic)
        return {
            "ticker": ti.full,
            "data": hk_data,
            "source": "akshare:hk_valuation_comparison_em + scale_comparison_em + growth_comparison_em",
            "fallback": False,
        }

    # v2.12.1 · A 股分支 · 三层 fallback 链防止 push2 挂了报告空板块
    fallback_used = False
    fallback_reason = ""
    source_used = "akshare:stock_board_industry_cons_em"

    def _parse_peer_df(df, self_ticker_code: str):
        """共用解析逻辑：df → (peers_raw, peer_table, peer_comparison)."""
        df = df.copy()
        df["_mcap"] = df["总市值"].apply(_float) if "总市值" in df.columns else 0
        df = df.sort_values("_mcap", ascending=False)
        raw = df.head(20).to_dict("records")

        self_row = None
        peers_top5 = []
        for r in raw:
            code = str(r.get("代码", ""))
            name = r.get("名称", "")
            entry = {
                "name": name, "code": code,
                "pe": f"{_float(r.get('市盈率-动态')):.1f}" if _float(r.get("市盈率-动态")) > 0 else "—",
                "pb": f"{_float(r.get('市净率')):.2f}" if _float(r.get("市净率")) > 0 else "—",
                "roe": "—", "revenue_growth": "—",
            }
            if code == self_ticker_code:
                entry["is_self"] = True
                self_row = entry
            elif len(peers_top5) < 5:
                peers_top5.append(entry)

        tbl = ([self_row] if self_row else []) + peers_top5

        # v3.9.4 · 同行 ROE 补充（参考 stock_web._fetch_peer · 不走 push2 更稳）
        # 只给 top 同行补 ROE · 单只失败静默跳过 · 不阻塞主流程
        try:
            _roe_cache = {}
            for _p in tbl:
                _c = str(_p.get("code", ""))
                if not _c or _c in _roe_cache:
                    _p["roe"] = _roe_cache.get(_c, "—")
                    continue
                try:
                    _ind = ak.stock_financial_analysis_indicator_em(symbol=f"{_c}.{('SH' if _c.startswith(('6','9')) else 'SZ')}")
                    if _ind is not None and not _ind.empty and "ROEJQ" in _ind.columns:
                        _annual = _ind[_ind.get("REPORT_DATE_NAME", _ind.iloc[:, 0]).astype(str).str.contains("年报", na=False)]
                        _src = _annual if not _annual.empty else _ind
                        _v = _float(_src.iloc[-1].get("ROEJQ"))
                        _p["roe"] = f"{_v:.1f}" if _v else "—"
                        _roe_cache[_c] = _p["roe"]
                except Exception:
                    _roe_cache[_c] = "—"
        except Exception:
            pass

        def _avg(col):
            if col not in df.columns: return 0.0
            vals = [_float(v) for v in df[col] if _float(v) > 0]
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        # v3.9.4 · ROE 同行均值（用上面补的逐行 ROE · 非 self）
        _peer_roes = [_float(p.get("roe")) for p in tbl if not p.get("is_self") and _float(p.get("roe")) > 0]
        _peer_roe_avg = round(sum(_peer_roes) / len(_peer_roes), 1) if _peer_roes else 0.0
        _self_roe = _float(basic.get("roe")) if _float(basic.get("roe")) else None

        cmp = [
            {"name": "PE (越低越好)", "self": _float(basic.get("pe_ttm")), "peer": _avg("市盈率-动态")},
            {"name": "PB (越低越好)", "self": _float(basic.get("pb")),     "peer": _avg("市净率")},
            {"name": "ROE (越高越好)", "self": _self_roe, "peer": _peer_roe_avg},
        ]
        return raw, tbl, cmp

    if ti.market == "A" and not industry:
        peer_table, peer_comparison = _build_self_only_table(ti, basic)
        fallback_used = True
        fallback_reason = "basic.industry 缺失 · 仅返回公司自身"
        source_used += " (missing-industry self-only fallback)"

    elif ti.market == "A" and industry:
        # ─── Tier 1: 主链（push2） ───
        try:
            df = ak.stock_board_industry_cons_em(symbol=industry)
            if df is not None and not df.empty:
                peers_raw, peer_table, peer_comparison = _parse_peer_df(df, ti.code)
        except Exception as e:
            peers_raw = [{"tier": 1, "error": f"{type(e).__name__}: {str(e)[:200]}"}]

        # ─── Tier 2: 重试一次（网络抖动） ───
        if not peer_table:
            try:
                time.sleep(2.5)
                df = ak.stock_board_industry_cons_em(symbol=industry)
                if df is not None and not df.empty:
                    peers_raw, peer_table, peer_comparison = _parse_peer_df(df, ti.code)
                    fallback_used = True
                    fallback_reason = "Tier 1 网络失败 · Tier 2 retry 成功"
                    source_used += " (retry)"
            except Exception as e:
                peers_raw.append({"tier": 2, "error": f"{type(e).__name__}: {str(e)[:200]}"})

        # ─── Tier 3: 雪球 Playwright 登录兜底（用户 opt-in） ───
        if not peer_table:
            try:
                from lib.xueqiu_browser import is_login_enabled, fetch_peers_via_browser
                if is_login_enabled():
                    xq_peers = fetch_peers_via_browser(ti.code)  # 返 list[dict]
                    if xq_peers:
                        # 构造兼容的 df-like 结构
                        import pandas as pd
                        xq_df = pd.DataFrame([
                            {"代码": p.get("code", ""), "名称": p.get("name", ""),
                             "总市值": p.get("mcap_yi", 0),
                             "市盈率-动态": p.get("pe", 0), "市净率": p.get("pb", 0)}
                            for p in xq_peers
                        ])
                        if not xq_df.empty:
                            peers_raw, peer_table, peer_comparison = _parse_peer_df(xq_df, ti.code)
                            fallback_used = True
                            fallback_reason = "Tier 1/2 akshare 失败 · Tier 3 雪球浏览器兜底"
                            source_used = "xueqiu.com/S/{code} (playwright)"
            except Exception as e:
                peers_raw.append({"tier": 3, "error": f"{type(e).__name__}: {str(e)[:200]}"})

        # ─── Tier 3.5 · v3.9.4 · push2 全挂时用 INDUSTRY_PEERS 硬编码同行兜底 ───
        # 白酒/半导体等行业在 fetch_similar_stocks.INDUSTRY_PEERS 有真实同行列表，
        # 用 stock_financial_analysis_indicator_em（不走 push2）拉它们的估值。
        if not peer_table:
            try:
                from fetch_similar_stocks import INDUSTRY_PEERS, INDUSTRY_ALIASES
                # v3.9.4 · 别名匹配（Codex P2-1）：集成电路→半导体 / 工业金属→有色金属 / 乘用车→汽车
                _peers = INDUSTRY_PEERS.get(industry, [])
                if not _peers:
                    _alias = INDUSTRY_ALIASES.get(industry)
                    if _alias:
                        _peers = INDUSTRY_PEERS.get(_alias, [])
                if _peers:
                    import pandas as _pd
                    # v3.9.4 · 若被分析股票不在同行列表里，先补 self 行（Codex P2-2）
                    _self_code = ti.code
                    _in_list = any(str(c) == _self_code for c, _ in _peers)
                    if not _in_list:
                        _peers = [(_self_code, basic.get("name") or ti.full)] + list(_peers)
                    _rows = []
                    for _pc, _pn in _peers[:6]:
                        _code = _pc + (".SH" if _pc.startswith("6") else ".SZ")
                        try:
                            _df = ak.stock_financial_analysis_indicator_em(symbol=_code)
                            _roe = "—"
                            _rev = 0.0
                            if _df is not None and not _df.empty:
                                # 取最新一期非空 ROEJQ（末尾行可能是 NaN）
                                _last = _df.iloc[-1]
                                if "ROEJQ" in _df.columns:
                                    _ser = _df["ROEJQ"].dropna()
                                    _v = float(_ser.iloc[-1]) if len(_ser) else None
                                    _roe = f"{_v:.1f}" if _v else "—"
                                if "TOTALOPERATEREVE" in _df.columns:
                                    _rev = _float(_last.get("TOTALOPERATEREVE"))
                            # 同行名单至少要有名称/代码（即使无 PE/PB 也比"暂无可比股"强）
                            _rows.append({
                                "代码": _pc, "名称": _pn,
                                "总市值": _rev,
                                "市盈率-动态": 0,
                                "市净率": 0,
                                "_roe": _roe,
                            })
                        except Exception:
                            continue
                    if _rows:
                        _xdf = _pd.DataFrame(_rows)
                        peers_raw, peer_table, peer_comparison = _parse_peer_df(_xdf, ti.code)
                        # 把 _roe 填回 peer_table（_parse_peer_df 内 ROE 补充逻辑拿不到这里的字段名）
                        _by_code = {str(r["代码"]): r["_roe"] for r in _rows}
                        for _p in peer_table:
                            _pc = str(_p.get("code", "")).split(".")[0]
                            if _pc in _by_code:
                                _p["roe"] = _by_code[_pc]
                        # self 行的 PE/PB 从 basic 补回（_rows 里 PE/PB 是 0，会覆盖真实值）
                        for _p in peer_table:
                            if _p.get("is_self"):
                                _p["pe"] = f"{_float(basic.get('pe_ttm')):.1f}" if _float(basic.get("pe_ttm")) > 0 else "—"
                                _p["pb"] = f"{_float(basic.get('pb')):.2f}" if _float(basic.get("pb")) > 0 else "—"
                        fallback_used = True
                        fallback_reason = "push2 失败 · INDUSTRY_PEERS 硬编码同行兜底"
                        source_used = "akshare:stock_financial_analysis_indicator_em (INDUSTRY_PEERS)"
            except Exception as e:
                peers_raw.append({"tier": 3.5, "error": f"{type(e).__name__}: {str(e)[:200]}"})

        # ─── Tier 4 保底：仅公司自己一行 + fallback 标记 ───
        if not peer_table:
            peer_table, peer_comparison = _build_self_only_table(ti, basic)
            fallback_used = True
            if not fallback_reason:
                fallback_reason = "所有同行数据源失败 · 仅返回公司自身"
            source_used += " (self-only fallback)"

    local_data = _attach_global_peers({
            "industry": industry,
            "self": basic,
            "peer_table": peer_table,
            "peer_comparison": peer_comparison,
            "rank": "—",  # 真实排名需要 聚合查询
            "peers_top20_raw": peers_raw[:20],
            "fallback_reason": fallback_reason,  # v2.12.1
        }, ti, basic)
    return {
        "ticker": ti.full,
        "data": local_data,
        "source": source_used,
        "fallback": fallback_used,
    }


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1] if len(sys.argv) > 1 else "002273.SZ"), ensure_ascii=False, indent=2, default=str))
