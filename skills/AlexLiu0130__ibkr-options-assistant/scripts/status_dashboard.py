"""
Status dashboard — at-a-glance snapshot of the IBKR Options Assistant.

Reuses existing scripts (portfolio_positions, wheel_tracker, optionally
options_analyzer) and renders the result in three output formats:

  ansi      — colored, aligned ASCII for terminals (the default)
  telegram  — emoji + Markdown for Telegram (no monospace alignment)
  json      — structured data for agents (Atlas) to organize freely

Quick mode (default) needs ~5s and 1 IBKR connection: covers portfolio,
positions, wheel stages, and this-week reminders derived from position DTE.
Use `--full` to also include IV environment per held symbol and recent
P&L (adds ~30s and several extra IBKR calls).

Usage:
  python status_dashboard.py
  python status_dashboard.py --output telegram
  python status_dashboard.py --output json --full --output-file /tmp/dash.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from ib_client import ib_connect, log
from portfolio_positions import fetch_positions
from wheel_tracker import summary as wheel_summary

CLIENT_ID_OFFSET = 20


# ── ANSI color helpers ────────────────────────────────────────────────────

_C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "gray": "\033[90m",
}


def _c(text: str, *styles: str) -> str:
    if not styles:
        return text
    return "".join(_C[s] for s in styles) + text + _C["reset"]


# ── Time / market session ─────────────────────────────────────────────────

def _et_session() -> dict:
    try:
        from zoneinfo import ZoneInfo
        et = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return {"et_time": None, "session": "unknown"}
    hm = (et.hour, et.minute)
    if et.weekday() >= 5:
        label = "closed (weekend)"
    elif hm < (4, 0) or hm >= (20, 0):
        label = "overnight"
    elif hm < (9, 30):
        label = "pre-market"
    elif hm < (16, 0):
        label = "RTH"
    else:
        label = "post-market"
    return {"et_time": et.strftime("%Y-%m-%d %H:%M ET"), "session": label}


# ── Data builder ──────────────────────────────────────────────────────────

def build_dashboard(ib, *, full: bool = False) -> dict:
    """Aggregate everything dashboard needs in one IBKR session."""
    out: dict = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **_et_session(),
    }

    # Portfolio + positions (one shot — gives Greeks, ITM, und_price)
    portfolio = fetch_positions(ib)
    out["portfolio_greeks"] = portfolio["portfolio_greeks"]
    out["positions"] = portfolio["positions"]
    out["data_type"] = _infer_data_type(portfolio["positions"])

    # Unrealized P&L total
    out["unrealized_pnl_total"] = round(
        sum((p.get("unrealized_pnl") or 0) for p in portfolio["positions"]), 2
    )

    # Wheel summary. NOTE: wheel_summary internally re-fetches positions to
    # join with the journal — that's a second IBKR call, accepted to keep this
    # script thin. Future optimization: refactor wheel_tracker to accept
    # pre-fetched positions.
    try:
        out["wheel"] = wheel_summary(ib)
    except Exception as e:
        log(f"  wheel summary skipped: {e}")
        out["wheel"] = {"wheels": [], "error": str(e)}

    # This-week reminders derived from position DTE
    out["this_week"] = _this_week_reminders(portfolio["positions"])

    # Full mode: IV env per symbol + recent P&L
    if full:
        out["iv_environment"] = _iv_environment_for_holdings(ib, portfolio["positions"])
        out["recent_pnl"] = _recent_pnl(ib, days=7)
    return out


def _infer_data_type(positions: list[dict]) -> str:
    """Best-effort: the OPT entries with und_price imply Greeks succeeded.
    We can't tell live vs delayed without re-querying, so report a coarse
    label."""
    has_opt_with_greeks = any(
        p.get("sec_type") == "OPT" and p.get("greeks") for p in positions
    )
    return "live (OPRA Greeks)" if has_opt_with_greeks else "limited"


def _this_week_reminders(positions: list[dict]) -> dict:
    expiring = []
    for p in positions:
        if p.get("sec_type") != "OPT":
            continue
        exp = p.get("expiration")
        try:
            exp_d = datetime.strptime(exp, "%Y%m%d").date() if len(exp) == 8 else \
                    datetime.strptime(exp, "%Y-%m-%d").date()
            dte = (exp_d - date.today()).days
        except Exception:
            continue
        if dte <= 7:
            expiring.append({
                "symbol": p.get("symbol"),
                "strike": p.get("strike"),
                "right": p.get("right"),
                "dte": dte,
                "itm": p.get("itm"),
                "position": p.get("position"),
            })
    return {
        "expiring_le_7d": sorted(expiring, key=lambda x: x["dte"]),
    }


def _iv_environment_for_holdings(ib, positions: list[dict]) -> list[dict]:
    """For each unique OPT-underlying symbol, compute IV env. Slow."""
    from options_analyzer import compute_historical_vol, assess_iv_environment
    from options_chain import fetch_chain

    syms = sorted({p["symbol"] for p in positions if p.get("sec_type") == "OPT"})
    results = []
    for sym in syms:
        try:
            chain = fetch_chain(ib, sym, num_strikes=4, dte_min=14, dte_max=60)
            hv = compute_historical_vol(ib, sym, days=20)
            env = assess_iv_environment(chain, hv)
            results.append({"symbol": sym, **env})
        except Exception as e:
            log(f"  IV env skipped for {sym}: {e}")
    return results


def _recent_pnl(ib, days: int) -> dict:
    from pnl_analytics import fetch_session_trades
    since = date.today() - timedelta(days=days)
    try:
        trades = fetch_session_trades(ib, since)
    except Exception as e:
        log(f"  recent P&L skipped: {e}")
        return {"days": days, "total_realized": 0.0, "n_trades": 0, "error": str(e)}
    realized = [t["realized_pnl"] for t in trades if t.get("realized_pnl")]
    return {
        "days": days,
        "total_realized": round(sum(realized), 2),
        "n_trades": len(trades),
        "wins": sum(1 for r in realized if r > 0),
        "losses": sum(1 for r in realized if r < 0),
    }


# ── ANSI renderer ─────────────────────────────────────────────────────────

def render_ansi(data: dict) -> str:
    lines = []
    bar = "─" * 60

    # Header
    lines.append(_c("═" * 60, "cyan"))
    lines.append(_c("  IBKR Options Assistant — Status Dashboard", "bold", "cyan"))
    sub = f"  {data.get('et_time', '?')}   "
    sess = data.get("session", "?")
    sess_color = "green" if sess == "RTH" else "yellow" if "market" in sess else "gray"
    sub += _c(f"[{sess}]", sess_color) + f"   data: {data.get('data_type', '?')}"
    lines.append(sub)
    lines.append(_c("═" * 60, "cyan"))
    lines.append("")

    # Portfolio Greeks
    g = data["portfolio_greeks"]
    lines.append(_c("PORTFOLIO ", "bold") + _c(bar[10:], "dim"))
    upl = data["unrealized_pnl_total"]
    upl_color = "green" if upl > 0 else "red" if upl < 0 else "gray"
    delta_s = f"{g['net_delta']:+.0f}"
    lines.append(
        f"  Δ {_c(delta_s, 'bold')}"
        f"   Γ {g['net_gamma']:+.2f}"
        f"   Vega {g['net_vega']:+.0f}"
        f"   Θ {g['net_theta']:+.0f}"
    )
    lines.append(f"  Unrealized P&L: {_c(f'${upl:+,.2f}', upl_color)}")
    lines.append("")

    # Positions
    positions = data["positions"]
    n_stk = sum(1 for p in positions if p["sec_type"] == "STK")
    n_opt = sum(1 for p in positions if p["sec_type"] == "OPT")
    lines.append(_c(f"POSITIONS ({n_stk} stk + {n_opt} opt) ", "bold") + _c(bar[24 + len(str(n_stk)) + len(str(n_opt)):], "dim"))

    if not positions:
        lines.append(_c("  (no positions)", "dim"))
    else:
        for p in _sorted_positions(positions):
            lines.append("  " + _render_position_ansi(p))
    lines.append("")

    # This week
    tw = data["this_week"]["expiring_le_7d"]
    lines.append(_c("THIS WEEK ", "bold") + _c(bar[10:], "dim"))
    if not tw:
        lines.append(_c("  No positions expiring within 7 days", "dim"))
    else:
        for e in tw:
            urgency = _c(f"DTE {e['dte']:>2}", "red" if e["dte"] <= 2 else "yellow")
            itm_tag = _c("ITM", "red") if e.get("itm") else _c("OTM", "green") if e.get("itm") is False else _c("?", "gray")
            sign = "-" if (e.get("position") or 0) < 0 else "+"
            lines.append(f"  {urgency}  {e['symbol']:<6} {sign}{e['right']} {e['strike']}  {itm_tag}")
    lines.append("")

    # Wheel
    wheel = data.get("wheel", {})
    wheel_syms = wheel.get("wheels", [])
    wheel_err = wheel.get("error")
    lines.append(_c("WHEEL ", "bold") + _c(bar[6:], "dim"))
    if wheel_err:
        lines.append(_c(f"  ⚠ wheel data unavailable: {wheel_err}", "yellow"))
    elif not wheel_syms:
        lines.append(_c("  No wheel cycles tracked", "dim"))
    else:
        for w in wheel_syms:
            stage = w.get("current_stage", "?")
            stage_color = {
                "short_put": "yellow",
                "assigned": "magenta",
                "covered_call": "blue",
                "closed": "gray",
            }.get(stage, "gray")
            cum = w.get("total_premium", 0)
            ann = w.get("annualized_return_pct")
            ann_s = f"  ann {ann:.1f}%" if isinstance(ann, (int, float)) else ""
            lines.append(f"  {w.get('symbol', '?'):<6}  {_c(stage, stage_color):<16}  premium ${cum:,.0f}{ann_s}")
    lines.append("")

    # IV env (full mode only)
    if "iv_environment" in data:
        lines.append(_c("IV ENVIRONMENT ", "bold") + _c(bar[15:], "dim"))
        for iv in data["iv_environment"]:
            bias = iv.get("iv_bias", "?")
            bias_color = {"high": "red", "low": "green", "neutral": "gray"}.get(bias, "gray")
            ratio = iv.get("iv_to_hv_ratio")
            ratio_s = f" ({ratio}x HV20)" if ratio is not None else ""
            lines.append(f"  {iv['symbol']:<6}  {_c(bias, bias_color):<8}{ratio_s}  {iv.get('assessment', '')}")
        lines.append("")

    # Recent P&L (full mode only)
    if "recent_pnl" in data:
        rp = data["recent_pnl"]
        lines.append(_c(f"RECENT P&L (last {rp['days']}d) ", "bold") + _c(bar[24:], "dim"))
        total = rp.get("total_realized", 0)
        total_color = "green" if total > 0 else "red" if total < 0 else "gray"
        lines.append(
            f"  Realized: {_c(f'${total:+,.2f}', total_color)}"
            f"  Trades: {rp.get('n_trades', 0)}"
            f"  W/L: {rp.get('wins', 0)}/{rp.get('losses', 0)}"
        )
        lines.append("")

    return "\n".join(lines)


def _sorted_positions(positions: list[dict]) -> list[dict]:
    """STK first, then OPT by ascending DTE."""
    def k(p):
        if p["sec_type"] == "STK":
            return (0, 0, p.get("symbol", ""))
        try:
            exp = p.get("expiration") or ""
            d = datetime.strptime(exp, "%Y%m%d").date() if len(exp) == 8 else datetime.strptime(exp, "%Y-%m-%d").date()
            dte = (d - date.today()).days
        except Exception:
            dte = 9999
        return (1, dte, p.get("symbol", ""))
    return sorted(positions, key=k)


def _render_position_ansi(p: dict) -> str:
    sym = p.get("symbol", "?")
    qty = p.get("position", 0)
    sign = "+" if qty > 0 else ""
    if p["sec_type"] == "STK":
        upl = p.get("unrealized_pnl") or 0
        upl_c = "green" if upl > 0 else "red" if upl < 0 else "gray"
        return f"{sym:<6}  {sign}{qty:>4} STK            upl {_c(f'${upl:+,.0f}', upl_c)}"
    # OPT
    right = p.get("right", "?")
    strike = p.get("strike", 0)
    exp = p.get("expiration", "")
    try:
        exp_d = datetime.strptime(exp, "%Y%m%d").date().strftime("%m/%d")
    except Exception:
        exp_d = exp
    itm = p.get("itm")
    itm_tag = _c("ITM", "red") if itm else _c("OTM", "green") if itm is False else _c(" ? ", "gray")
    delta = p.get("position_greeks", {}).get("delta")
    delta_s = f"Δ {delta:+.0f}" if isinstance(delta, (int, float)) else "Δ ?"
    und = p.get("und_price")
    und_s = f"und {und:>7.2f}" if isinstance(und, (int, float)) else ""
    upl = p.get("unrealized_pnl") or 0
    upl_c = "green" if upl > 0 else "red" if upl < 0 else "gray"
    return (
        f"{sym:<6}  {sign}{qty:>2}{right} {strike:>6} {exp_d}  {itm_tag}  "
        f"{und_s:<13} {delta_s:>8}  upl {_c(f'${upl:+,.0f}', upl_c)}"
    )


# ── Telegram renderer ─────────────────────────────────────────────────────

def render_telegram(data: dict) -> str:
    """Markdown + emoji. No monospace alignment — survives Telegram's font."""
    lines = []

    # Header
    sess = data.get("session", "?")
    sess_emoji = {"RTH": "🟢", "pre-market": "🟡", "post-market": "🟡",
                  "overnight": "🌙", "closed (weekend)": "💤"}.get(sess, "❓")
    lines.append(f"🤖 *IBKR Options Assistant*")
    lines.append(f"{sess_emoji} {data.get('et_time', '?')} _{sess}_")
    lines.append("")

    # Portfolio Greeks
    g = data["portfolio_greeks"]
    upl = data["unrealized_pnl_total"]
    upl_e = "🟢" if upl > 0 else "🔴" if upl < 0 else "⚪️"
    lines.append("*组合 Greeks*")
    lines.append(f"Δ `{g['net_delta']:+.0f}` · Γ `{g['net_gamma']:+.2f}` · Vega `{g['net_vega']:+.0f}` · Θ `{g['net_theta']:+.0f}`")
    lines.append(f"{upl_e} 未实现 `${upl:+,.2f}`")
    lines.append("")

    # Positions
    positions = data["positions"]
    n_stk = sum(1 for p in positions if p["sec_type"] == "STK")
    n_opt = sum(1 for p in positions if p["sec_type"] == "OPT")
    lines.append(f"*持仓* ({n_stk} stk + {n_opt} opt)")
    if not positions:
        lines.append("_(空)_")
    else:
        for p in _sorted_positions(positions):
            lines.append(_render_position_telegram(p))
    lines.append("")

    # This week
    tw = data["this_week"]["expiring_le_7d"]
    lines.append("*本周到期 (≤7d)*")
    if not tw:
        lines.append("_无_")
    else:
        for e in tw:
            urgency = "🚨" if e["dte"] <= 2 else "⏰"
            itm_e = "🔴" if e.get("itm") else "🟢" if e.get("itm") is False else "⚪️"
            sign = "-" if (e.get("position") or 0) < 0 else "+"
            lines.append(f"{urgency} {e['symbol']} {sign}{e['right']} `{e['strike']}` DTE `{e['dte']}` {itm_e}")
    lines.append("")

    # Wheel
    wheel = data.get("wheel", {})
    wheel_syms = wheel.get("wheels", [])
    wheel_err = wheel.get("error")
    lines.append("*Wheel 状态*")
    if wheel_err:
        lines.append(f"⚠️ 数据不可用: `{wheel_err}`")
    elif not wheel_syms:
        lines.append("_未追踪_")
    else:
        stage_emoji = {"short_put": "🟡", "assigned": "🟣", "covered_call": "🔵", "closed": "⚪️"}
        for w in wheel_syms:
            stage = w.get("current_stage", "?")
            se = stage_emoji.get(stage, "❓")
            cum = w.get("total_premium", 0)
            ann = w.get("annualized_return_pct")
            ann_s = f" · 年化 `{ann:.1f}%`" if isinstance(ann, (int, float)) else ""
            # Escape underscores in stage name for legacy Markdown
            stage_disp = stage.replace("_", "\\_")
            lines.append(f"{se} {w.get('symbol', '?')} _{stage_disp}_ · 累计 `${cum:,.0f}`{ann_s}")
    lines.append("")

    # IV env
    if "iv_environment" in data:
        lines.append("*IV 环境*")
        bias_e = {"high": "🔥", "low": "❄️", "neutral": "➖"}
        for iv in data["iv_environment"]:
            be = bias_e.get(iv.get("iv_bias"), "❓")
            ratio = iv.get("iv_to_hv_ratio")
            ratio_s = f" (`{ratio}x` HV20)" if ratio is not None else ""
            lines.append(f"{be} {iv['symbol']} _{iv.get('iv_bias', '?')}_{ratio_s}")
        lines.append("")

    # Recent P&L
    if "recent_pnl" in data:
        rp = data["recent_pnl"]
        total = rp.get("total_realized", 0)
        e = "🟢" if total > 0 else "🔴" if total < 0 else "⚪️"
        lines.append(f"*近 {rp['days']} 天已实现*")
        lines.append(f"{e} `${total:+,.2f}` · {rp.get('n_trades', 0)} 笔 · W/L `{rp.get('wins', 0)}/{rp.get('losses', 0)}`")

    return "\n".join(lines)


def _render_position_telegram(p: dict) -> str:
    sym = p.get("symbol", "?")
    qty = p.get("position", 0)
    sign = "+" if qty > 0 else ""
    if p["sec_type"] == "STK":
        upl = p.get("unrealized_pnl") or 0
        e = "🟢" if upl > 0 else "🔴" if upl < 0 else "⚪️"
        return f"📊 {sym} `{sign}{qty}` STK {e} `${upl:+,.0f}`"
    right = p.get("right", "?")
    strike = p.get("strike", 0)
    try:
        exp_d = datetime.strptime(p.get("expiration", ""), "%Y%m%d").date().strftime("%m/%d")
    except Exception:
        exp_d = p.get("expiration", "")
    itm = p.get("itm")
    itm_e = "🔴" if itm else "🟢" if itm is False else "⚪️"
    delta = p.get("position_greeks", {}).get("delta")
    delta_s = f"Δ`{delta:+.0f}`" if isinstance(delta, (int, float)) else ""
    upl = p.get("unrealized_pnl") or 0
    upl_e = "🟢" if upl > 0 else "🔴" if upl < 0 else "⚪️"
    return f"{itm_e} {sym} `{sign}{qty}{right}` `{strike}` {exp_d} {delta_s} {upl_e}`${upl:+,.0f}`"


# ── main ──────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="IBKR Options Assistant status dashboard")
    parser.add_argument("--output", choices=["ansi", "telegram", "json"], default="ansi",
                        help="render format (default: ansi)")
    parser.add_argument("--full", action="store_true",
                        help="include IV env + recent P&L (slower, more IBKR calls)")
    parser.add_argument("--output-file", help="write to file instead of stdout")
    args = parser.parse_args()

    try:
        with ib_connect(client_id_offset=CLIENT_ID_OFFSET) as ib:
            data = build_dashboard(ib, full=args.full)
    except Exception as e:
        log(f"❌ {e}")
        return 1

    if args.output == "json":
        out = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    elif args.output == "telegram":
        out = render_telegram(data)
    else:
        out = render_ansi(data)

    if args.output_file:
        tmp = args.output_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(out)
        os.rename(tmp, args.output_file)
        log(f"📁 Saved to {args.output_file}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
