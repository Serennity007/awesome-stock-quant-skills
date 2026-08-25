"""Self-contained global peer performance visualization."""
from __future__ import annotations

import html
import math


def _esc(value) -> str:
    return html.escape(str(value if value not in (None, "") else "—"), quote=True)


def _num(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _fmt(value, suffix="") -> str:
    number = _num(value)
    if number is None:
        return "—"
    return f"{number:,.1f}{suffix}"


def _fmt_amount(value) -> str:
    number = _num(value)
    if number is None:
        return "—"
    absolute = abs(number)
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if absolute >= divisor:
            return f"{number / divisor:,.1f}{suffix}"
    return f"{number:,.1f}"


def _latest(financials: dict) -> tuple[str, dict]:
    periods = financials.get("periods") or {}
    if not periods:
        return "—", {}
    period = max(periods)
    return period, periods.get(period) or {}


def _scatter(target: dict, peers: list[dict], base_currency: str) -> str:
    entities = [(target, True)] + [(peer, False) for peer in peers]
    points = []
    for entity, is_target in entities:
        period, facts = _latest(entity.get("financials") or {})
        revenue = _num(facts.get("revenue_base"))
        margin = _num(facts.get("gross_margin"))
        if revenue is None or revenue <= 0 or margin is None:
            continue
        points.append((entity, is_target, period, revenue, margin))
    if len(points) < 2:
        return '<div style="color:#94a3b8;font-size:11px">规模/盈利散点数据不足</div>'

    width, height = 760, 310
    left, right, top, bottom = 62, 22, 22, 48
    plot_w, plot_h = width - left - right, height - top - bottom
    xs = [math.log10(point[3]) for point in points]
    ys = [point[4] for point in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if x_min == x_max:
        x_min, x_max = x_min - 0.5, x_max + 0.5
    if y_min == y_max:
        y_min, y_max = y_min - 5, y_max + 5
    y_pad = max(2, (y_max - y_min) * 0.12)
    y_min, y_max = y_min - y_pad, y_max + y_pad

    def px(value):
        return left + (math.log10(value) - x_min) / (x_max - x_min) * plot_w

    def py(value):
        return top + (y_max - value) / (y_max - y_min) * plot_h

    grid = []
    for idx in range(5):
        y = top + idx * plot_h / 4
        value = y_max - idx * (y_max - y_min) / 4
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e2e8f0"/>'
            f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-size="10" fill="#64748b">{value:.1f}%</text>'
        )
    dots = []
    placed_labels: list[tuple[float, float]] = []
    for entity, is_target, period, revenue, margin in points:
        x, y = px(revenue), py(margin)
        color = "#f59e0b" if is_target else "#6478d3"
        radius = 7 if is_target else 5
        name = str(entity.get("name") or entity.get("symbol") or "—")
        label = _esc(name[:18])
        title = _esc(f"{name} | {period} | {base_currency} {revenue:,.1f} | 毛利率 {margin:.1f}%")
        near_right = x > width - right - 145
        label_x = x - 8 if near_right else x + 8
        anchor = "end" if near_right else "start"
        label_y = y - 7
        while any(abs(label_x - old_x) < 165 and abs(label_y - old_y) < 14 for old_x, old_y in placed_labels):
            label_y += 14
        label_y = max(top + 10, min(height - bottom - 5, label_y))
        placed_labels.append((label_x, label_y))
        dots.append(
            f'<g><title>{title}</title><circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{color}" opacity=".9"/>'
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" font-size="10" fill="#334155">{label}</text></g>'
        )
    return f'''<div style="margin-top:12px">
  <div style="font-size:11px;color:#64748b;margin-bottom:6px">规模与盈利质量 · 横轴为 {base_currency} 营收（对数）</div>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label="全球同行营收与毛利率散点图" style="width:100%;height:auto;display:block">
    {''.join(grid)}
    <line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#94a3b8"/>
    <line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#94a3b8"/>
    {''.join(dots)}
    <text x="{width/2:.1f}" y="{height-10}" text-anchor="middle" font-size="10" fill="#64748b">营收规模（对数轴）</text>
  </svg>
</div>'''


def render_global_peer_comparison(comparison: dict) -> str:
    if not comparison:
        return ""
    status = comparison.get("conclusion_status") or "unavailable"
    if status in {"disabled", "insufficient_target_profile"}:
        return ""
    if status == "unavailable":
        return '<div style="margin-top:12px;color:#94a3b8;font-size:11px">全球同行数据暂不可用</div>'

    target = comparison.get("target") or {}
    peers = comparison.get("peers") or []
    base_currency = _esc(comparison.get("base_currency") or "USD")
    market_count = len({peer.get("market") or peer.get("country") for peer in peers if peer.get("market") or peer.get("country")})
    percentile = comparison.get("target_percentile") or {}
    gross_pct = percentile.get("gross_margin")
    latest_benchmark = (comparison.get("benchmarks") or {}).get("gross_margin") or {}
    benchmark_year = max(latest_benchmark) if latest_benchmark else None
    benchmark = latest_benchmark.get(benchmark_year, {}) if benchmark_year else {}

    rows = []
    for entity, is_target in [(target, True)] + [(peer, False) for peer in peers]:
        period, facts = _latest(entity.get("financials") or {})
        style = ' style="background:#fffbeb;font-weight:700"' if is_target else ""
        rows.append(f'''<tr{style}>
  <td>{_esc(entity.get("name") or entity.get("symbol"))}</td>
  <td>{_esc(entity.get("symbol") or entity.get("uzi_symbol"))}</td>
  <td>{_esc(entity.get("market") or entity.get("country"))}</td>
  <td>{_esc(period)}</td>
  <td>{_fmt_amount(facts.get("revenue_base"))}</td>
  <td>{_fmt(facts.get("gross_margin"), "%")}</td>
  <td>{_fmt(facts.get("net_margin"), "%")}</td>
  <td>{_fmt(facts.get("roe"), "%")}</td>
</tr>''')

    return f'''<style>
  .global-peer-comparison{{box-sizing:border-box;max-width:100%;min-width:0;overflow:hidden}}
  .global-peer-head>div{{min-width:0}}
  .global-peer-meta{{overflow-wrap:anywhere}}
  .global-peer-table{{max-width:100%;overflow-x:auto}}
  @media(max-width:640px){{
    .global-peer-head{{align-items:flex-start!important}}
    .global-peer-meta{{width:100%}}
    .global-peer-summary{{grid-template-columns:1fr!important}}
  }}
</style>
<div class="global-peer-comparison" style="margin-top:16px;padding-top:14px;border-top:1px solid #e2e8f0">
  <div class="global-peer-head" style="display:flex;justify-content:space-between;gap:12px;align-items:flex-end;flex-wrap:wrap">
    <div><div style="font-size:13px;font-weight:700;color:#0f172a">全球同行业绩对比</div>
    <div style="font-size:10px;color:#64748b;margin-top:2px">跨市场、跨币种标准化 · 原币数据保留</div></div>
    <div class="global-peer-meta" style="font-size:10px;color:#475569">有效同行 <strong>{len(peers)}</strong> · 市场 <strong>{market_count}</strong> · 基准币 {base_currency}</div>
  </div>
  <div class="global-peer-summary" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px">
    <div style="padding:8px;background:#f8fafc;border:1px solid #e2e8f0"><div style="font-size:9px;color:#64748b">目标公司</div><div style="font-size:12px;font-weight:700">{_esc(target.get("name") or target.get("symbol"))}</div></div>
    <div style="padding:8px;background:#f8fafc;border:1px solid #e2e8f0"><div style="font-size:9px;color:#64748b">同行中位数 · 毛利率</div><div style="font-size:12px;font-weight:700">{_fmt(benchmark.get("median"), "%")}</div></div>
    <div style="padding:8px;background:#f8fafc;border:1px solid #e2e8f0"><div style="font-size:9px;color:#64748b">目标毛利率分位</div><div style="font-size:12px;font-weight:700">{_fmt(gross_pct, "%")}</div></div>
  </div>
  {_scatter(target, peers, str(comparison.get("base_currency") or "USD"))}
  <div class="global-peer-table" style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:10px;white-space:nowrap">
    <thead><tr><th>公司</th><th>代码</th><th>市场</th><th>报告期</th><th>营收({base_currency})</th><th>毛利率</th><th>净利率</th><th>ROE</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
</div>'''
