import csv
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "my-skills/gold-cross-asset-research"
SCRIPT = SKILL / "scripts/analyze_structure.py"
spec = importlib.util.spec_from_file_location("gold_structure", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def csv_bytes(closes, start=None):
    start = start or datetime(2024, 1, 1, tzinfo=timezone.utc)
    text = io.StringIO()
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(["close_time", "open", "high", "low", "close"])
    previous = closes[0]
    for index, close in enumerate(closes, 1):
        writer.writerow([(start + timedelta(hours=4 * index)).isoformat(), previous,
                         max(previous, close) + .5, min(previous, close) - .5, close])
        previous = close
    return text.getvalue().encode()


class GoldStructureTests(unittest.TestCase):
    def analyze(self, raw, **kwargs):
        return module.analyze(raw, "GOLD_DEMO", "H4", "2024-02-01T00:00:00+00:00", "synthetic", **kwargs)

    def test_flat_series_has_exact_averages_and_zero_macd_without_trade_claims(self):
        result = self.analyze(csv_bytes([100] * 40))
        self.assertEqual(result["moving_averages"], {"ma5": 100, "ma10": 100, "ma20": 100})
        self.assertEqual(result["macd"]["histogram"], 0)
        self.assertEqual(result["macd"]["dif"], 0)
        self.assertEqual(result["macd"]["dea"], 0)
        self.assertEqual(result["ma_ordering"], "mixed_or_flat")
        self.assertNotIn("trade", result)
        self.assertNotIn("win_rate", result)

    def test_short_history_is_explicit_and_ema_matches_hand_arithmetic(self):
        self.assertEqual(module.ema([1, 2, 3], 3), [1, 1.5, 2.25])
        result = self.analyze(csv_bytes([100] * 4))
        self.assertEqual(result["moving_averages"], {"ma5": None, "ma10": None, "ma20": None})
        self.assertFalse(result["macd"]["ready"])
        self.assertFalse(self.analyze(csv_bytes([100] * 34))["macd"]["ready"])
        self.assertTrue(self.analyze(csv_bytes([100] * 35))["macd"]["ready"])

    def test_future_prices_cannot_change_cutoff_indicators(self):
        base = [100 + i / 10 for i in range(40)]
        cutoff = (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=160)).isoformat()
        results = [module.analyze(csv_bytes(base + [future]), "GOLD_DEMO", "H4", cutoff, "synthetic") for future in (1, 9999)]
        for result in results:
            self.assertEqual(result["completed_bar_count"], 40)
            self.assertEqual(result["excluded_after_cutoff"], 1)
        for field in ("moving_averages", "macd", "ma_ordering", "latest_completed_bar", "boundary_observations"):
            self.assertEqual(results[0][field], results[1][field])
        self.assertNotEqual(results[0]["source_sha256"], results[1]["source_sha256"])

    def test_timestamps_ohlc_and_nonfinite_values_are_checked(self):
        raw = csv_bytes([100, 101]).decode()
        cases = [raw.replace("+00:00", ""),
                 raw.replace("2024-01-01T08:00:00+00:00", "2024-01-01T12:00:00+08:00"),
                 raw.replace("2024-01-01T08:00:00+00:00", "2024-01-01T00:00:00+00:00"),
                 raw.replace("101.5", "90"), raw.replace("101.5", "NaN"), raw.replace("101.5", "-1")]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.analyze(text.encode())

    def test_reclaim_and_rejection_have_symmetric_observation_rules(self):
        reclaimed = self.analyze(csv_bytes([98, 102]), support=100)
        rejected = self.analyze(csv_bytes([102, 98]), resistance=100)
        self.assertEqual(reclaimed["boundary_observations"]["support"]["observation"], "reclaimed_after_closed_break")
        self.assertEqual(rejected["boundary_observations"]["resistance"]["observation"], "rejected_after_closed_break")
        self.assertFalse(reclaimed["macd"]["ready"])
        self.assertNotIn("confirmed_reversal", reclaimed)

    def test_reference_count_and_expiry_use_completed_bars_excluding_anchor(self):
        raw = csv_bytes([100] * 48)
        result = self.analyze(raw, reference_time="2024-01-06T00:00:00+00:00", window_bars=12)
        self.assertEqual(result["reference_window"]["completed_bars_after_reference"], 18)
        self.assertEqual(result["reference_window"]["window_state"], "expired")
        self.assertFalse(result["reference_window"]["includes_reference_bar"])
        due = self.analyze(raw, reference_time="2024-01-06T00:00:00+00:00", window_bars=18)
        self.assertEqual(due["reference_window"]["window_state"], "due_now")

    def test_invalid_boundaries_and_unobserved_reference_are_rejected(self):
        for options in ({"support": 102, "resistance": 100}, {"support": float("nan")},
                        {"window_bars": 5}, {"reference_time": "2024-03-01T00:00:00+00:00"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.analyze(csv_bytes([100] * 40), **options)

    def test_cli_is_offline_runs_outside_skill_and_preserves_inputs_and_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source, output = directory / "bars.csv", directory / "report with spaces.json"
            raw = csv_bytes([100] * 40)
            source.write_bytes(raw)
            args = [sys.executable, str(SCRIPT), "--csv", str(source), "--instrument", "GOLD_DEMO", "--timeframe", "H4",
                    "--as-of", "2024-02-01T00:00:00+00:00", "--data-kind", "synthetic", "--out", str(output)]
            run = subprocess.run(args, cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["data_kind"], "synthetic")
            before = output.read_bytes()
            self.assertNotEqual(subprocess.run(args, cwd=directory, capture_output=True).returncode, 0)
            self.assertEqual(before, output.read_bytes())
            args[-1] = str(source)
            self.assertNotEqual(subprocess.run(args, cwd=directory, capture_output=True).returncode, 0)
            self.assertEqual(raw, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
