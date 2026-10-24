#!/usr/bin/env python3
"""Run the bundled synthetic consensus and backtest examples, then inspect a report."""
import argparse
import csv
import importlib.util
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def missing_dependencies():
    return [name for name in ("numpy", "pandas") if importlib.util.find_spec(name) is None]


def run_step(command, log):
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    log.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{log.stem} exited with {result.returncode}; see {log}")


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def inspect_results(run_dir):
    consensus = rows(run_dir / "consensus.csv")
    if [row["code"] for row in consensus] != ["000003", "000001", "000002"]:
        raise ValueError("synthetic consensus order differs from the documented fixture")
    for row, expected in zip(consensus, (83.3, 66.7, 50.0)):
        if not math.isclose(float(row["consensus_score"]), expected, abs_tol=0.01):
            raise ValueError("synthetic consensus scores differ from the documented fixture")
    history = rows(run_dir / "backtest/bt_result_danbin.csv")
    holdings = rows(run_dir / "backtest/bt_holdings_danbin.csv")
    if len(history) != 2 or len(holdings) != 2:
        raise ValueError("synthetic backtest must contain two holding periods")
    nav, benchmark = float(history[-1]["nav"]), float(history[-1]["bench_nav"])
    # Independent fixture arithmetic: 0.999 entry factor, followed by +10% and -10%.
    if not math.isclose(nav, 0.999 * 1.1 * 0.9, abs_tol=1e-9):
        raise ValueError("net ending wealth differs from the documented cost calculation")
    if not math.isclose(benchmark, 1.01, abs_tol=1e-9):
        raise ValueError("benchmark ending wealth differs from the documented fixture")
    consensus_meta = json.loads((run_dir / "consensus.csv.meta.json").read_text(encoding="utf-8"))
    backtest_meta = json.loads((run_dir / "backtest/bt_manifest.json").read_text(encoding="utf-8"))
    if len(consensus_meta["inputs"]) != 2 or len(backtest_meta["cache_sha256"]) != 7:
        raise ValueError("input provenance is incomplete")
    return {"consensus": consensus, "net_ending_wealth": nav, "benchmark_ending_wealth": benchmark,
            "holding_periods": len(history), "consensus_provenance": "consensus.csv.meta.json",
            "backtest_provenance": "backtest/bt_manifest.json"}


def run_demo(output_parent):
    output_parent.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=output_parent)).resolve()
    status = {"status": "running", "data_kind": "synthetic", "market_data_requested": False,
              "generated_at_utc": datetime.now(timezone.utc).isoformat()}
    status_path = run_dir / "status.json"
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    commands = [
        [sys.executable, "-X", "utf8", str(ROOT / "my-skills/master-ensemble/scripts/ensemble.py"),
         "--csvs", str(ROOT / "examples/ensemble/quality.csv"), str(ROOT / "examples/ensemble/momentum.csv"),
         "--out", str(run_dir / "consensus.csv")],
        [sys.executable, "-X", "utf8", str(ROOT / "my-skills/framework-backtest/scripts/backtest.py"),
         "--cache-dir", str(ROOT / "examples/backtest/cache"), "--results-dir", str(run_dir / "backtest"),
         "--frameworks", "danbin", "--start", "2026-07-31", "--top", "1", "--min-stocks", "2", "--cost-bps", "10"],
    ]
    try:
        for name, command in zip(("consensus", "backtest"), commands):
            run_step(command, run_dir / f"{name}.log")
        result = inspect_results(run_dir)
        lines = ["# 离线演示报告 / Offline demo report", "",
                 "**合成数据 / SYNTHETIC DATA。用于核对计算，不是真实证券行情、实盘收益或选股建议。**", "",
                 "## 共识排序 / Consensus ranking", "",
                 "| 示例代码 | 共识分 | 覆盖框架数 |", "|---|---:|---:|"]
        lines += [f"| {r['code']} | {r['consensus_score']} | {r['frameworks']} |" for r in result["consensus"]]
        lines += ["", "## 回测计算 / Backtest calculation", "",
                  "输入价格人为设定为 100 → 110 → 99。首期建仓成本为 10 bps；后一期持仓不变，期末不强制清仓。", "",
                  f"- 净期末资产：**{result['net_ending_wealth']:.5f}**，计算为 `0.999 × 1.1 × 0.9`。",
                  f"- 基准期末资产：**{result['benchmark_ending_wealth']:.2f}**。",
                  "- 两期持仓明细、调仓成本与输入哈希已保存。", "",
                  "## 文件 / Files", "",
                  "- [共识 CSV](consensus.csv) · [输入记录](consensus.csv.meta.json)",
                  "- [月度回测 CSV](backtest/bt_result_danbin.csv) · [持仓明细](backtest/bt_holdings_danbin.csv)",
                  "- [回测输入记录](backtest/bt_manifest.json)",
                  "- [共识运行日志](consensus.log) · [回测运行日志](backtest.log)",
                  "- [验证状态](status.json)", ""]
        (run_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
        status.update(status="passed", results=result)
    except (OSError, RuntimeError, ValueError, KeyError, IndexError) as exc:
        status.update(status="failed", error=str(exc))
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/demo",
                        help="Parent for a fresh run directory; existing output is never overwritten")
    args = parser.parse_args(argv)
    missing = missing_dependencies()
    if missing:
        print("Missing dependencies: " + ", ".join(missing), file=sys.stderr)
        install = [sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements-demo.txt")]
        if os.name == "nt":
            # PowerShell needs its call operator before a quoted executable path.
            command = "& " + " ".join("'" + part.replace("'", "''") + "'" for part in install)
        else:
            command = shlex.join(install)
        print("Install once: " + command, file=sys.stderr)
        return 1
    try:
        run_dir = run_demo(args.output_dir.resolve())
    except (OSError, RuntimeError, ValueError, KeyError, IndexError) as exc:
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        return 1
    print("PASS: synthetic consensus, transaction costs, holdings and input provenance checked.")
    print(f"Open report: {run_dir / 'REPORT.md'}")
    print("Synthetic fixture only; no market data or investment performance is claimed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
