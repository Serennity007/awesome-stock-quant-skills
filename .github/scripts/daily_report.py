#!/usr/bin/env python3
"""Run the daily screen, expose data quality, and freeze a pending paper watchlist."""
import datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from paper_journal import create_journal, verify_seal
from screen_report import render_report

CODES = "600519,000858,600036,601318,300750,000001,600900,601012,000333,600276," \
        "002415,601888,600887,603288,000651,600030,601899,002594,600585,601166"


def main():
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()
    csv_path = reports / f"{today}.csv"
    latest = reports / "latest.md"
    result = subprocess.run(
        [sys.executable, str(ROOT / "my-skills/buffett-value-investing/scripts/screen.py"),
         "--codes", CODES, "--top", "20", "--out", str(csv_path), "--sleep", "0.5"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        if result.returncode != 0 or not csv_path.is_file():
            raise ValueError("screening failed: " + (result.stderr or result.stdout or "no output")[-1000:])
        report = render_report(csv_path, today)
        journal = reports / "paper" / today
        if journal.exists():
            verify_seal(journal, "checksums.json")
            print("Existing first snapshot preserved; a rerun does not replace its frozen inputs.")
        else:
            create_journal(csv_path, journal, today, "market_snapshot")
        report += f"\n[本日首次冻结的模拟观察清单](paper/{today}/INITIAL_REVIEW.md)（待建仓，不含虚构收益）。\n"
        latest.write_text(report, encoding="utf-8")
        print(f"OK: {csv_path}; quality report and pending paper snapshot saved.")
        return 0
    except (ValueError, OSError, KeyError) as exc:
        latest.write_text(f"# 每日筛选失败 · {today}\n\n本次没有新模拟记录；不得将失败当成正常筛选。\n\n```text\n{str(exc).replace('```', '')}\n```\n", encoding="utf-8")
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
