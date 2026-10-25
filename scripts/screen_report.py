#!/usr/bin/env python3
"""Render screening results with complete and partial records visibly separated."""
import argparse
from datetime import date
from pathlib import Path

from paper_journal import read_screen


def cell(value):
    return str(value or "—").replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_report(screen, report_date):
    date.fromisoformat(report_date)
    rows = read_screen(screen)
    complete = sorted((r for r in rows if r["score_status"] == "complete"), key=lambda r: (-r["total"], r["code"]))
    partial = [r for r in rows if r["score_status"] == "partial"]
    lines = [f"# 每日财务筛选报告 / Daily screen · {report_date}", "",
             "数据源：AKShare（新浪财务、东财估值）。规则分用于研究和人工复核，不是收益预测或买入指令。", "",
             f"本次返回 **{len(rows)}** 条记录：数据完整 **{len(complete)}** 条，数据不完整 **{len(partial)}** 条。", "",
             "## 数据完整的筛选记录", "", "`complete` 表示筛选器需要的字段齐全，不表示数据已独立审计或投资有效。`review_moat` 仍需人工核查。", "",
             "| 排名 | 代码 | 规则分 | 判定 | 年报 ROE | 毛利率 | 负债率 | PE / PB 分位 | 估值日期 |",
             "|---|---|---:|---|---|---|---|---|---|"]
    for index, row in enumerate(complete, 1):
        values = [index, row["code"], f"{row['total']:g}", row["decision"], row.get("roe_annual"),
                  row.get("gross_mean"), row.get("debt_latest"),
                  f"{row.get('pe_pct') or '—'} / {row.get('pb_pct') or '—'}", row.get("valuation_date")]
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    if not complete:
        lines += ["", "本次没有数据完整的记录。"]
    lines += ["", "## 数据不完整：先补数，不参与完整记录的总分排序", "",
              "| 代码 | 数据状态 | 判定 | 数据缺口 |", "|---|---|---|---|"]
    lines += ["| " + " | ".join(cell(r.get(key)) for key in ("code", "score_status", "decision", "data_issues")) + " |" for r in partial]
    if not partial:
        lines += ["", "本次没有不完整记录。"]
    lines += ["", "## 模拟与复盘", "",
              "可用 `scripts/paper_journal.py start` 冻结本次输入和规则，后续导入信号日之后的价格追加模拟复盘。",
              "筛选成功不等于模拟成交；没有后续价格时不生成收益。", "",
              f"[原始 CSV]({Path(screen).name}) · [数据元信息]({Path(screen).name}.meta.json) · [模拟记录说明](../docs/paper-journal.md)", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = render_report(args.screen, args.date)
        if args.out.resolve() == args.screen.resolve():
            raise ValueError("report must not overwrite input")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
