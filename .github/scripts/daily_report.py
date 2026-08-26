#!/usr/bin/env python3
"""daily_report.py — 每日巴菲特筛股自动报告（供 GitHub Action 调用）。

对固定的 20 只 A 股代表股运行 buffett-value-investing 的打分逻辑，
输出 reports/YYYY-MM-DD.csv 与 reports/latest.md。
网络/接口失败时不让 CI 变红：生成"数据获取失败"报告并以 0 退出。
"""
import subprocess
import sys
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# 固定的 20 只代表股（hs300 全池在 CI 上过慢）
CODES = "600519,000858,600036,601318,300750,000001,600900,601012,000333,600276," \
        "002415,601888,600887,603288,000651,600030,601899,002594,600585,601166"

today = datetime.date.today().isoformat()
csv_path = REPORTS / f"{today}.csv"
latest_md = REPORTS / "latest.md"

TITLE = (
    f"# 每日巴菲特筛股报告 {today} / Daily Buffett Screen {today} / 日次バフェットスクリーニング {today}\n\n"
)

result = subprocess.run(
    [sys.executable, str(ROOT / "my-skills/buffett-value-investing/scripts/screen.py"),
     "--codes", CODES, "--top", "20", "--out", str(csv_path), "--sleep", "0.5"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
)

if result.returncode == 0 and csv_path.exists():
    import pandas as pd
    df = pd.read_csv(csv_path, dtype={"code": str})
    lines = [TITLE,
             "数据源 / Data source / データ源: akshare（新浪财务 + 东财估值）。"
             "仅供学习研究，不构成投资建议 / Not investment advice / 投資助言ではありません。\n",
             "| 排名 Rank 順位 | 代码 Code コード | 总分 Score スコア | ROE 5年 | 毛利率% Gross | 负债率% Debt | PE分位 PE-pct | PB分位 PB-pct |",
             "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(df.itertuples(), 1):
        pe = f"{r.pe_pct:.2f}" if pd.notna(r.pe_pct) else "-"
        pb = f"{r.pb_pct:.2f}" if pd.notna(r.pb_pct) else "-"
        gm = f"{r.gross_mean:.1f}" if pd.notna(r.gross_mean) else "-"
        lines.append(f"| {i} | {r.code} | {r.total} | {r.roe_annual} | {gm} | {r.debt_latest} | {pe} | {pb} |")
    latest_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: {csv_path} + {latest_md}")
else:
    csv_path.write_text("# 数据获取失败 / data fetch failed / データ取得失敗\n", encoding="utf-8")
    latest_md.write_text(
        TITLE + "数据获取失败（可能是 akshare 接口限流或网络问题），本次无结果。\n\n"
        "Data fetch failed (akshare API throttling or network issue); no results this run.\n\n"
        "データ取得に失敗しました（akshare API のレート制限またはネットワーク問題）。今回の結果はありません。\n\n"
        "```\n" + (result.stderr or result.stdout or "")[-1500:] + "\n```\n",
        encoding="utf-8")
    print("FAILED but tolerated:", (result.stderr or "")[-300:])
