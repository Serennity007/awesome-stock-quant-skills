"""PeersRenderer · 同行对比 section · 对应 4_peers.

v2.12.1 教训：peer_table 常空（push2 反爬）· render 需要 3 态
- full: 多家同行 + PE/PB 对比
- lite: 只有公司自己 + fallback 原因
- gap: 完全空
"""
from __future__ import annotations

import html

from lib.report.global_peers import render_global_peer_comparison

from .base import SectionRenderer, RenderContext


class PeersRenderer(SectionRenderer):
    section_id = "peers"
    section_title = "🏭 同行对比"

    def render_full(self, ctx: RenderContext) -> str:
        data = ctx.data
        peer_table = data.get("peer_table") or []
        peer_comparison = data.get("peer_comparison") or []
        global_html = render_global_peer_comparison(data.get("global_peer_comparison") or {})

        if not peer_table and not peer_comparison and not global_html:
            return self.render_gap(ctx, "同行抓取失败（push2/xueqiu 反爬）")

        rows = []
        for p in (peer_comparison or peer_table)[:12]:
            if not isinstance(p, dict):
                continue
            esc = lambda value: html.escape(str(value if value not in (None, "") else "—"), quote=True)
            rows.append(f'''<tr>
  <td>{esc(p.get("name") or p.get("code"))}</td>
  <td>{esc(p.get("market_cap") or p.get("mcap"))}</td>
  <td>{esc(p.get("pe_ttm") or p.get("pe"))}</td>
  <td>{esc(p.get("pb"))}</td>
  <td>{esc(p.get("roe"))}</td>
</tr>''')

        if not rows and not global_html:
            return self.render_gap(ctx, "同行数据为空")

        # v3.9.3 · 拆出嵌套三引号 f-string · Python 3.9 不允许 f-string 表达式再含 f-string（3.12+ 才行）
        rows_html = ""
        if rows:
            rows_html = (
                '<table class="peers-table" style="width:100%;border-collapse:collapse">'
                '<thead>'
                '<tr><th>公司</th><th>市值</th><th>PE(TTM)</th><th>PB</th><th>ROE</th></tr>'
                '</thead>'
                '<tbody>' + "".join(rows) + '</tbody>'
                '</table>'
            )

        return f'''<section id="{self.section_id}">
  <h2>{self.section_title}</h2>
  {rows_html}
  {global_html}
</section>'''
