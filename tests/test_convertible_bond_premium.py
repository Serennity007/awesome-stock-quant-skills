import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "my-skills/convertible-bond-premium/scripts/convertible_bond_premium.py"
HEADER = "code,name,price,conv_price,stock_price,coupons,years_left,redemption_price"

# Independently computed reference constants (see references/method.md in the skill).
PBV_ZERO_COUPON_108_2Y_5PCT = 97.95918367346938
FLOOR_PREMIUM_95_OVER_PBV = -0.03020833333333328
PBV_COUPON_CASE = 96.715995852578
FLOOR_PREMIUM_100_OVER_PBV = 0.03395512932966871
YTM_ZERO_COUPON_95_TO_108 = 0.06622797996636631
PRICE_FOR_YTM_4PCT = 97.11538461538461


class ConvertibleBondPremiumTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def bonds(self, *rows, header=HEADER):
        return self.write("bonds.csv", header + "\n" + "".join(row + "\n" for row in rows))

    def stock(self, code, closes):
        rows = ["date,code,close"]
        for index, close in enumerate(closes):
            rows.append(f"2026-10-{index + 1:02d},{code},{close}")
        return self.write("stock.csv", "\n".join(rows) + "\n")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True)

    def run_ok(self, *args):
        out = self.root / "out.json"
        run = self.run_cli(*args, "--out", out)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(out.is_file())
        return json.loads(out.read_text(encoding="utf-8"))

    def one(self, *args):
        report = self.run_ok(*args)
        self.assertEqual(len(report["rows"]), 1)
        return report, report["rows"][0]

    # --- conversion arithmetic -------------------------------------------------

    def test_discount_case_conversion_value_and_premium(self):
        path = self.bonds("110001,深度折价转债,120,10,15,,2,105")
        report, row = self.one("--csv", path)
        self.assertAlmostEqual(row["conversion_shares"], 10.0, places=12)
        self.assertAlmostEqual(row["conversion_value"], 150.0, places=12)
        self.assertAlmostEqual(row["conversion_premium"], -0.2, places=12)

    def test_premium_case_and_double_low_score(self):
        path = self.bonds("110002,深度溢价转债,101,50,20,,2,108")
        report, row = self.one("--csv", path)
        self.assertAlmostEqual(row["conversion_value"], 40.0, places=12)
        self.assertAlmostEqual(row["conversion_premium"], 1.525, places=12)
        self.assertAlmostEqual(row["double_low"], 253.5, places=12)
        self.assertEqual(report["summary"]["double_low_best"][0]["code"], "110002")

    def test_face_override_scales_conversion_shares(self):
        path = self.bonds("110003,小面值,110,10,15,,2,105,50",
                          header=HEADER + ",face")
        report, row = self.one("--csv", path)
        self.assertAlmostEqual(row["conversion_shares"], 5.0, places=12)
        self.assertAlmostEqual(row["conversion_value"], 75.0, places=12)

    # --- pure bond value -------------------------------------------------------

    def test_zero_coupon_bond_floor(self):
        path = self.bonds("110004,零息转债,95,20,25,,2.0,108")
        report, row = self.one("--csv", path, "--discount-rate", "0.05")
        self.assertAlmostEqual(row["pure_bond_value"], PBV_ZERO_COUPON_108_2Y_5PCT, places=9)
        self.assertAlmostEqual(row["bond_floor_premium"], FLOOR_PREMIUM_95_OVER_PBV, places=9)
        self.assertEqual(row["discount_rate_source"], "default")

    def test_coupon_schedule_times_and_cashflows(self):
        path = self.bonds("110005,票息转债,100,20,25,0.002|0.004,2.0,102")
        report, row = self.one("--csv", path, "--discount-rate", "0.03")
        self.assertEqual([round(t, 12) for t in row["coupon_times"]], [1.0, 2.0])
        self.assertAlmostEqual(row["coupon_cashflows"][0], 0.2, places=12)
        self.assertAlmostEqual(row["coupon_cashflows"][1], 0.4, places=12)
        self.assertAlmostEqual(row["pure_bond_value"], PBV_COUPON_CASE, places=9)
        self.assertAlmostEqual(row["bond_floor_premium"], FLOOR_PREMIUM_100_OVER_PBV, places=9)

    def test_fractional_years_shift_coupon_times(self):
        path = self.bonds("110006,剩余一年半,98,20,25,0.01|0.02,1.5,102")
        report, row = self.one("--csv", path, "--discount-rate", "0.03")
        self.assertEqual([round(t, 12) for t in row["coupon_times"]], [0.5, 1.5])

    # --- yield to maturity -----------------------------------------------------

    def test_zero_coupon_ytm_matches_closed_form(self):
        path = self.bonds("110007,零息YTM,95,20,25,,2.0,108")
        report, row = self.one("--csv", path)
        self.assertAlmostEqual(row["ytm"], YTM_ZERO_COUPON_95_TO_108, places=9)
        self.assertIsNone(row["ytm_note"])

    def test_coupon_ytm_inverts_a_known_price(self):
        path = self.bonds("110008,票息YTM,97.11538461538461,20,25,0.01|0.02,2.0,102")
        report, row = self.one("--csv", path)
        self.assertAlmostEqual(row["ytm"], 0.04, places=9)
        self.assertAlmostEqual(PRICE_FOR_YTM_4PCT, 97.11538461538461, places=12)

    # --- redemption trigger ----------------------------------------------------

    def test_trigger_counts_last_thirty_rows_and_sorts_dates(self):
        bonds = self.bonds("110009,强赎观察,130,10,15,,2,105")
        closes = [13.5] * 16 + [12.0] * 14
        stock = self.stock("110009", closes)
        # Rows are written in reverse date order: the script must sort by date, not by file order.
        reversed_rows = stock.read_text(encoding="utf-8").splitlines()
        stock.write_text(reversed_rows[0] + "\n" + "\n".join(reversed(reversed_rows[1:])) + "\n",
                         encoding="utf-8")
        report, row = self.one("--csv", bonds, "--stock-csv", stock)
        self.assertEqual(row["trigger"]["status"], "triggered")
        self.assertEqual(row["trigger"]["count"], 16)
        self.assertEqual(row["trigger"]["observed_days"], 30)
        self.assertAlmostEqual(row["trigger"]["price_threshold"], 13.0, places=12)
        self.assertIn("110009", report["summary"]["triggered"])

    def test_trigger_boundary_counts_equal_close(self):
        bonds = self.bonds("110010,边界相等,130,10,15,,2,105")
        stock = self.stock("110010", [13.0] * 15 + [12.9] * 15)
        report, row = self.one("--csv", bonds, "--stock-csv", stock)
        self.assertEqual(row["trigger"]["count"], 15)
        self.assertEqual(row["trigger"]["status"], "triggered")

    def test_trigger_below_threshold(self):
        bonds = self.bonds("110011,未达标,120,10,15,,2,105")
        stock = self.stock("110011", [13.5] * 14 + [12.0] * 16)
        report, row = self.one("--csv", bonds, "--stock-csv", stock)
        self.assertEqual(row["trigger"]["count"], 14)
        self.assertEqual(row["trigger"]["status"], "below")
        self.assertNotIn("110011", report["summary"]["triggered"])

    def test_insufficient_history_is_not_reported_as_below(self):
        bonds = self.bonds("110012,历史不足,130,10,15,,2,105")
        stock = self.stock("110012", [13.5] * 13 + [12.0] * 12)
        report, row = self.one("--csv", bonds, "--stock-csv", stock)
        self.assertEqual(row["trigger"]["status"], "insufficient-history")
        self.assertEqual(row["trigger"]["observed_days"], 25)
        self.assertEqual(row["trigger"]["count"], 13)

    def test_missing_stock_series_is_not_zero_count(self):
        bonds = self.bonds("110013,无正股序列,120,10,15,,2,105")
        report, row = self.one("--csv", bonds)
        self.assertEqual(row["trigger"]["status"], "no-stock-series")
        self.assertIsNone(row["trigger"]["count"])
        self.assertIsNone(row["trigger"]["observed_days"])
        self.assertIn("110013", report["summary"]["no_stock_series"])

    def test_custom_clause_thresholds_are_applied(self):
        bonds = self.bonds("110014,自定义条款,130,10,15,,2,105")
        stock = self.stock("110014", [12.5] * 20 + [11.0] * 10)
        report, row = self.one("--csv", bonds, "--stock-csv", stock,
                               "--trigger-ratio", "1.2", "--trigger-window", "30",
                               "--trigger-days", "20")
        self.assertAlmostEqual(row["trigger"]["price_threshold"], 12.0, places=12)
        self.assertEqual(row["trigger"]["count"], 20)
        self.assertEqual(row["trigger"]["status"], "triggered")

    # --- discount curve --------------------------------------------------------

    def test_rating_curve_overrides_default_discount_rate(self):
        bonds = self.bonds("110015,AAA转债,100,20,25,0.01,1.0,105,AAA",
                          "110016,无评级转债,100,20,25,0.01,1.0,105,",
                          header=HEADER + ",rating")
        curve = self.write("curve.csv", "rating,rate\nAAA,0.02\n")
        report = self.run_ok("--csv", bonds, "--discount-csv", curve)
        by_code = {row["code"]: row for row in report["rows"]}
        self.assertAlmostEqual(by_code["110015"]["discount_rate"], 0.02, places=12)
        self.assertEqual(by_code["110015"]["discount_rate_source"], "rating-curve")
        self.assertAlmostEqual(by_code["110016"]["discount_rate"], 0.035, places=12)
        self.assertEqual(by_code["110016"]["discount_rate_source"], "default")

    # --- provenance, schema and aggregates -------------------------------------

    def test_output_records_input_fingerprint_and_parameters(self):
        path = self.bonds("110017,指纹校验,120,10,15,,2,105")
        stock = self.stock("110017", [13.5] * 20 + [12.0] * 10)
        report = self.run_ok("--csv", path, "--stock-csv", stock, "--discount-rate", "0.04")
        self.assertEqual(report["source_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(report["parameters"]["stock_sha256"],
                         hashlib.sha256(stock.read_bytes()).hexdigest())
        self.assertAlmostEqual(report["parameters"]["discount_rate_default"], 0.04, places=12)
        self.assertEqual(report["parameters"]["trigger_window"], 30)
        self.assertEqual(report["parameters"]["trigger_days"], 15)
        self.assertEqual(report["schema_version"], 1)
        self.assertTrue(report["scope"])
        self.assertTrue(report["limitations"])
        self.assertTrue(report["generated_at_utc"])

    def test_summary_counts_and_sorted_double_low_shortlist(self):
        bonds = self.bonds("110018,A,120,10,15,,2,105",
                           "110019,B,101,50,20,,2,108",
                           "110020,C,95,20,25,,2,108")
        report = self.run_ok("--csv", bonds)
        self.assertEqual(report["summary"]["bond_count"], 3)
        shortlist = [item["double_low"] for item in report["summary"]["double_low_best"]]
        self.assertEqual(shortlist, sorted(shortlist))
        self.assertLessEqual(len(shortlist), 5)

    # --- failure modes ---------------------------------------------------------

    def test_duplicate_code_is_rejected_without_output(self):
        path = self.bonds("110021,A,120,10,15,,2,105", "110021,B,121,10,15,,2,105")
        out = self.root / "dup.json"
        run = self.run_cli("--csv", path, "--out", out)
        self.assertEqual(run.returncode, 2)
        self.assertIn("ERROR", run.stderr)
        self.assertFalse(out.exists())

    def test_invalid_numbers_are_rejected(self):
        bad_rows = [
            "110022,A,-1,10,15,,2,105",
            "110022,A,120,0,15,,2,105",
            "110022,A,120,10,nan,,2,105",
            "110022,A,120,10,15,0.01|x,2,105",
            "110022,A,120,10,15,0.01,0,105",
            "110022,A,120,10,15,0.01,2,-5",
        ]
        for row in bad_rows:
            with self.subTest(row=row):
                path = self.bonds(row)
                out = self.root / "bad.json"
                run = self.run_cli("--csv", path, "--out", out)
                self.assertEqual(run.returncode, 2, run.stdout)
                self.assertIn("ERROR", run.stderr)
                self.assertFalse(out.exists())

    def test_coupon_schedule_longer_than_remaining_years_is_rejected(self):
        path = self.bonds("110027,A,100,10,12,0.01|0.02|0.03|0.04,1.5,105")
        out = self.root / "coupons.json"
        run = self.run_cli("--csv", path, "--out", out)
        self.assertEqual(run.returncode, 2)
        self.assertIn("ERROR", run.stderr)
        self.assertFalse(out.exists())
        # One coupon per remaining year stays on the positive-time schedule.
        ok = self.bonds("110028,B,100,10,12,0.01|0.02,2.0,105")
        report = self.run_ok("--csv", ok)
        self.assertEqual([round(time, 12) for time in report["rows"][0]["coupon_times"]], [1.0, 2.0])

    def test_missing_required_column_is_rejected(self):
        path = self.write("bonds.csv", "code,name,price,conv_price,years_left,redemption_price\n"
                                       "110023,A,120,10,2,105\n")
        out = self.root / "cols.json"
        run = self.run_cli("--csv", path, "--out", out)
        self.assertEqual(run.returncode, 2)
        self.assertIn("ERROR", run.stderr)
        self.assertFalse(out.exists())

    def test_impossible_clause_is_rejected(self):
        path = self.bonds("110024,A,120,10,15,,2,105")
        out = self.root / "clause.json"
        run = self.run_cli("--csv", path, "--out", out, "--trigger-window", "30",
                           "--trigger-days", "31")
        self.assertEqual(run.returncode, 2)
        self.assertIn("ERROR", run.stderr)

    def test_existing_output_is_never_overwritten(self):
        path = self.bonds("110025,A,120,10,15,,2,105")
        out = self.root / "keep.json"
        first = self.run_cli("--csv", path, "--out", out)
        self.assertEqual(first.returncode, 0, first.stderr)
        original = out.read_bytes()
        second = self.run_cli("--csv", path, "--out", out)
        self.assertEqual(second.returncode, 2)
        self.assertIn("ERROR", second.stderr)
        self.assertEqual(out.read_bytes(), original)

    def test_input_csv_is_never_rewritten(self):
        path = self.bonds("110026,A,120,10,15,,2,105")
        original = path.read_bytes()
        self.run_cli("--csv", path, "--out", path)
        self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
