import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "my-skills/futures-curve-structure"
SCRIPT = SKILL / "scripts/futures_curve.py"
spec = importlib.util.spec_from_file_location("futures_curve", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

AS_OF = "2026-01-01"
HEADER = ["contract", "expiry", "last", "volume", "open_interest"]
BASE_ROWS = [
    ["CI2601", "2026-01-31", "100", "1000", "5000"],
    ["CI2602", "2026-03-02", "102", "900", "4800"],
    ["CI2603", "2026-04-01", "104", "800", "4600"],
]


def curve_bytes(rows, header=HEADER):
    text = io.StringIO()
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return text.getvalue().encode("utf-8")


def contracts(*entries):
    rows = []
    for entry in entries:
        contract, expiry, last = entry[:3]
        volume = entry[3] if len(entry) > 3 else ""
        open_interest = entry[4] if len(entry) > 4 else ""
        rows.append([contract, expiry, last, volume, open_interest])
    return rows


class FuturesCurveTests(unittest.TestCase):
    def analyze(self, raw, **kwargs):
        return module.analyze(raw, "DEMO", AS_OF, **kwargs)

    def test_contango_spreads_and_total_change_match_hand_arithmetic(self):
        result = self.analyze(curve_bytes(BASE_ROWS))
        self.assertEqual([entry["days_to_expiry"] for entry in result["curve"]], [30, 60, 90])
        first, second = result["adjacent_spreads"]
        self.assertEqual((first["near_contract"], first["far_contract"]), ("CI2601", "CI2602"))
        self.assertAlmostEqual(first["spread"], 2.0)
        self.assertAlmostEqual(first["spread_pct_of_near"], 2.0)
        self.assertEqual(first["days_between"], 30)
        self.assertAlmostEqual(first["annualized_slope_pct"], 2 / 100 * 365 / 30 * 100)
        self.assertAlmostEqual(second["spread"], 2.0)
        self.assertAlmostEqual(second["spread_pct_of_near"], 2 / 102 * 100)
        self.assertAlmostEqual(second["annualized_slope_pct"], 2 / 102 * 365 / 30 * 100)
        self.assertEqual(result["structure"]["classification"], "contango")
        self.assertAlmostEqual(result["structure"]["total_annualized_change_pct"], 4 / 100 * 365 / 60 * 100)
        self.assertEqual(result["as_of_date"], "2026-01-01")
        self.assertIsNone(result["basis"])

    def test_backwardation_flat_and_mixed_classifications(self):
        descending = contracts(("A", "2026-01-31", "104", "", ""), ("B", "2026-03-02", "102", "", ""),
                               ("C", "2026-04-01", "100", "", ""))
        backward = self.analyze(curve_bytes(descending))
        self.assertEqual(backward["structure"]["classification"], "backwardation")
        self.assertTrue(all(entry["spread"] < 0 for entry in backward["adjacent_spreads"]))
        self.assertLess(backward["structure"]["total_annualized_change_pct"], 0)

        level = contracts(("A", "2026-01-31", "100", "", ""), ("B", "2026-03-02", "100", "", ""),
                          ("C", "2026-04-01", "100", "", ""))
        flat = self.analyze(curve_bytes(level))
        self.assertEqual(flat["structure"]["classification"], "flat")
        self.assertEqual([entry["spread"] for entry in flat["adjacent_spreads"]], [0.0, 0.0])
        self.assertEqual(flat["structure"]["total_annualized_change_pct"], 0.0)

        mixed_rows = contracts(("A", "2026-01-31", "100", "", ""), ("B", "2026-03-02", "102", "", ""),
                               ("C", "2026-04-01", "101", "", ""))
        mixed = self.analyze(curve_bytes(mixed_rows))
        self.assertEqual(mixed["structure"]["classification"], "mixed")
        self.assertEqual([entry["spread"] for entry in mixed["adjacent_spreads"]], [2.0, -1.0])

    def test_output_has_no_trade_win_rate_or_signal_keys(self):
        result = self.analyze(curve_bytes(BASE_ROWS), spot=99.5)
        for key in ("trade", "win_rate", "signal"):
            self.assertNotIn(key, result)
        self.assertGreaterEqual(len(result["limitations"]), 4)
        self.assertTrue(any("365" in item for item in result["limitations"]))
        self.assertTrue(any("multiplier" in item for item in result["limitations"]))
        self.assertIn("no live quotes", result["scope"])
        self.assertIn("not a forecast", result["structure"]["note"])

    def test_curve_sorts_by_expiry_and_uses_calendar_days(self):
        rows = contracts(("LATE", "2026-04-01", "104", "", ""), ("EARLY", "2026-01-31", "100", "", ""),
                         ("MID", "2026-03-02", "102", "", ""))
        result = self.analyze(curve_bytes(rows))
        self.assertEqual([entry["contract"] for entry in result["curve"]], ["EARLY", "MID", "LATE"])
        self.assertEqual([entry["expiry"] for entry in result["curve"]], ["2026-01-31", "2026-03-02", "2026-04-01"])
        self.assertEqual([entry["days_to_expiry"] for entry in result["curve"]], [30, 60, 90])
        self.assertEqual([entry["near_contract"] for entry in result["adjacent_spreads"]], ["EARLY", "MID"])

    def test_duplicate_contract_and_duplicate_expiry_are_rejected(self):
        duplicate_contract = contracts(("A", "2026-01-31", "100", "", ""), ("A", "2026-03-02", "101", "", ""))
        with self.assertRaises(ValueError):
            self.analyze(curve_bytes(duplicate_contract))
        duplicate_expiry = contracts(("A", "2026-01-31", "100", "", ""), ("B", "2026-01-31", "101", "", ""),
                                     ("C", "2026-04-01", "102", "", ""))
        with self.assertRaises(ValueError):
            self.analyze(curve_bytes(duplicate_expiry))

    def test_expired_rows_are_counted_but_do_not_change_curve_facts(self):
        expired = ["OLD", "2025-12-01", "9999", "1", "1"]
        base = curve_bytes(BASE_ROWS)
        with_expired = self.analyze(curve_bytes([expired] + BASE_ROWS))
        without = self.analyze(base)
        self.assertEqual(with_expired["excluded_expired"], 1)
        self.assertEqual(without["excluded_expired"], 0)
        for field in ("curve", "adjacent_spreads", "structure", "basis"):
            self.assertEqual(with_expired[field], without[field])
        self.assertNotEqual(with_expired["source_sha256"], without["source_sha256"])
        boundary = self.analyze(curve_bytes([["TODAY", "2026-01-01", "50", "", ""]] + BASE_ROWS))
        self.assertEqual(boundary["excluded_expired"], 1)
        self.assertEqual([entry["contract"] for entry in boundary["curve"]], [row[0] for row in BASE_ROWS])
        with self.assertRaises(ValueError):
            self.analyze(curve_bytes([["OLD", "2025-12-01", "-1", "", ""]] + BASE_ROWS))

    def test_all_expired_and_insufficient_curves_are_rejected(self):
        cases = [
            contracts(("A", "2025-01-31", "100", "", ""), ("B", "2025-03-02", "101", "", "")),
            contracts(("A", "2026-01-31", "100", "", "")),
            [],
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.analyze(curve_bytes(rows))

    def test_invalid_prices_expiries_headers_and_counts_are_rejected(self):
        cases = [
            contracts(("A", "2026-01-31", "0", "", ""), ("B", "2026-03-02", "101", "", "")),
            contracts(("A", "2026-01-31", "-1", "", ""), ("B", "2026-03-02", "101", "", "")),
            contracts(("A", "2026-01-31", "NaN", "", ""), ("B", "2026-03-02", "101", "", "")),
            contracts(("A", "2026-01-31", "", "", ""), ("B", "2026-03-02", "101", "", "")),
            contracts(("A", "2026-02-30", "100", "", ""), ("B", "2026-03-02", "101", "", "")),
            contracts(("A", "2026/01/31", "100", "", ""), ("B", "2026-03-02", "101", "", "")),
            contracts(("A", "2026-01-31", "100", "-1", ""), ("B", "2026-03-02", "101", "", "")),
            contracts(("A", "2026-01-31", "100", "nan", ""), ("B", "2026-03-02", "101", "", "")),
            contracts(("A", "2026-01-31", "100", "", "-5"), ("B", "2026-03-02", "101", "", "")),
            contracts(("", "2026-01-31", "100", "", ""), ("B", "2026-03-02", "101", "", "")),
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.analyze(curve_bytes(rows))
        missing_header = curve_bytes(contracts(("A", "2026-01-31", "100", "", "")),
                                     header=["contract", "expiry", "close"])
        with self.assertRaises(ValueError):
            self.analyze(missing_header)
        with self.assertRaises(ValueError):
            self.analyze(b"\xff\xfe not utf-8")

    def test_basis_math_with_and_without_spot(self):
        without_spot = self.analyze(curve_bytes(BASE_ROWS))
        self.assertIsNone(without_spot["basis"])
        result = self.analyze(curve_bytes(BASE_ROWS), spot=99.5)
        basis = result["basis"]
        self.assertEqual(basis["spot"], 99.5)
        self.assertEqual(basis["nearest_contract"], "CI2601")
        self.assertEqual(basis["nearest_expiry"], "2026-01-31")
        self.assertEqual(basis["nearest_days_to_expiry"], 30)
        self.assertAlmostEqual(basis["basis"], -0.5)
        self.assertAlmostEqual(basis["basis_pct_of_futures"], -0.5)
        self.assertAlmostEqual(basis["annualized_basis_pct"], -0.5 / 100 * 365 / 30 * 100)
        self.assertAlmostEqual(basis["annualized_basis_pct"], -6.083333333333334)
        for invalid in (0, -1.0, float("nan"), float("inf")):
            with self.subTest(spot=invalid), self.assertRaises(ValueError):
                self.analyze(curve_bytes(BASE_ROWS), spot=invalid)

    def test_volume_and_open_interest_blank_values_become_null(self):
        rows = contracts(("A", "2026-01-31", "100", "", ""), ("B", "2026-03-02", "101", "250.5", ""))
        result = self.analyze(curve_bytes(rows))
        self.assertIsNone(result["curve"][0]["volume"])
        self.assertIsNone(result["curve"][0]["open_interest"])
        self.assertEqual(result["curve"][1]["volume"], 250.5)
        self.assertIsNone(result["curve"][1]["open_interest"])
        minimal = curve_bytes(contracts(("A", "2026-01-31", "100"), ("B", "2026-03-02", "101")),
                              header=["contract", "expiry", "last"])
        bare = self.analyze(minimal)
        self.assertEqual((bare["curve"][0]["volume"], bare["curve"][0]["open_interest"]), (None, None))

    def test_as_of_accepts_date_or_aware_datetime_and_rejects_naive(self):
        by_date = module.analyze(curve_bytes(BASE_ROWS), "DEMO", "2026-01-01")
        self.assertEqual(by_date["as_of_date"], "2026-01-01")
        self.assertEqual([entry["days_to_expiry"] for entry in by_date["curve"]], [30, 60, 90])
        by_utc = module.analyze(curve_bytes(BASE_ROWS), "DEMO", "2026-01-01T00:00:00Z")
        self.assertEqual(by_utc["as_of_date"], "2026-01-01")
        by_offset = module.analyze(curve_bytes(BASE_ROWS), "DEMO", "2026-01-01T23:30:00-05:00")
        self.assertEqual(by_offset["as_of_date"], "2026-01-02")
        self.assertEqual([entry["days_to_expiry"] for entry in by_offset["curve"]], [29, 59, 89])
        for value in ("2026-01-01T00:00:00", "01/01/2026", "", "2026-13-01", "2026-1-1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.analyze(curve_bytes(BASE_ROWS), "DEMO", value)

    def test_source_hash_matches_raw_bytes_and_keeps_unicode_product(self):
        raw = curve_bytes(BASE_ROWS)
        result = self.analyze(raw)
        self.assertEqual(result["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("source_file", result)
        self.assertNotIn("generated_at_utc", result)
        unicode_product = module.analyze(raw, "沪铜_DEMO", AS_OF)
        body = json.dumps(unicode_product, ensure_ascii=False, allow_nan=False)
        self.assertIn("沪铜_DEMO", body)

    def test_cli_is_offline_runs_outside_skill_and_preserves_inputs_and_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "curve input.csv"
            output = directory / "curve report with spaces.json"
            raw = curve_bytes(BASE_ROWS)
            source.write_bytes(raw)
            args = [sys.executable, str(SCRIPT), "--csv", str(source), "--product", "DEMO",
                    "--as-of", AS_OF, "--spot", "99.5", "--out", str(output)]
            run = subprocess.run(args, cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(len(run.stdout.strip().splitlines()), 1)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["product"], "DEMO")
            self.assertEqual(report["source_file"], source.name)
            self.assertIn("generated_at_utc", report)
            self.assertEqual(report["structure"]["classification"], "contango")
            for key in ("trade", "win_rate", "signal"):
                self.assertNotIn(key, report)
            self.assertEqual(raw, source.read_bytes())
            before = output.read_bytes()
            repeat = subprocess.run(args, cwd=directory, capture_output=True, text=True)
            self.assertEqual(repeat.returncode, 2, repeat.stderr)
            self.assertIn("ERROR:", repeat.stderr)
            self.assertEqual(before, output.read_bytes())
            same_path = [sys.executable, str(SCRIPT), "--csv", str(source), "--product", "DEMO",
                         "--as-of", AS_OF, "--out", str(source)]
            rejected = subprocess.run(same_path, cwd=directory, capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 2, rejected.stderr)
            self.assertEqual(raw, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
