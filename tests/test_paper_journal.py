import csv
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import paper_journal as journal
from screen_report import render_report


class PaperJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.screen = self.root / "screen.csv"
        self.screen.write_text(
            "code,total,score_status,decision,valuation_date,data_issues\n"
            "000001,90,complete,review_moat,2026-07-31,\n"
            "000002,80,complete,review_moat,2026-07-31,\n"
            "000003,99,partial,needs_data,2026-07-31,cashflow_history_incomplete\n", encoding="utf-8")
        self.folder = self.root / "journal with spaces"
        self.prices = self.root / "prices.csv"

    def start(self, **kwargs):
        return journal.create_journal(self.screen, self.folder, "2026-07-31", "synthetic",
                                      **{"top": 1, "cash": 100000, **kwargs})

    def prices_to(self, last="2026-09-30", bad=None):
        rows = [("2026-07-31", "000001", 1), ("2026-07-31", "BENCHMARK", 1),
                ("2026-08-31", "000001", 110), ("2026-08-31", "BENCHMARK", 102)]
        if last == "2026-09-30":
            rows += [(last, "000001", 99), (last, "BENCHMARK", 101)]
        if bad:
            rows = bad(rows)
        with self.prices.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "code", "close"])
            writer.writerows(rows)

    def test_snapshot_excludes_high_scoring_partial_and_has_no_returns(self):
        result = self.start()
        self.assertEqual([r["code"] for r in result["candidates"]], ["000001"])
        self.assertEqual(result["partial_count"], 1)
        self.assertNotIn("net_return", result)
        self.assertEqual(result["state"], "watchlist_pending_execution")
        self.assertEqual((self.folder / "screen.csv").read_bytes(), self.screen.read_bytes())
        with self.assertRaises(FileExistsError):
            self.start()

    def test_two_reviews_charge_entry_once_and_preserve_cash_lots_and_chain(self):
        self.start()
        self.prices_to("2026-08-31")
        first = journal.append_review(self.folder, self.prices, "2026-08-31")
        self.assertEqual(first["entry_date"], "2026-08-31")
        self.assertEqual(first["entries"][0]["shares"], 900)
        self.assertEqual(first["entries"][0]["fee"], 99)
        self.assertEqual(first["cash_after_entry"], 901)
        self.assertEqual(first["equity"], 99901)
        self.prices_to()
        second = journal.append_review(self.folder, self.prices, "2026-09-30", "合成场景：只核对费用与持仓，不解释真实市场。")
        self.assertEqual(second["equity"], 90001)
        self.assertEqual(second["net_pnl"], -9999)
        self.assertAlmostEqual(second["net_return"], -0.09999)
        self.assertAlmostEqual(second["benchmark_return"], 101 / 102 - 1)
        self.assertAlmostEqual(second["max_drawdown_at_reviews"], -0.09999)
        self.assertEqual(second["note_origin"], "user_supplied")
        self.assertEqual(second["previous_review_sha256"], journal.digest(self.folder / "reviews/2026-08-31.json"))
        with self.assertRaisesRegex(ValueError, "strictly increase"):
            journal.append_review(self.folder, self.prices, "2026-09-30")

    def test_future_missing_duplicate_and_nonpositive_prices_fail_without_review(self):
        self.start()
        cases = [lambda rs: rs + [("2026-10-01", "000001", 999)],
                 lambda rs: [r for r in rs if r[:2] != ("2026-09-30", "BENCHMARK")],
                 lambda rs: rs + [rs[-1]],
                 lambda rs: [(d, c, 0 if (d, c) == ("2026-09-30", "000001") else p) for d, c, p in rs]]
        for bad in cases:
            with self.subTest(case=bad):
                self.prices_to(bad=bad)
                with self.assertRaises(ValueError):
                    journal.append_review(self.folder, self.prices, "2026-09-30")
                self.assertFalse((self.folder / "reviews").exists())

    def test_changed_frozen_snapshot_is_detected(self):
        self.start()
        self.prices_to()
        (self.folder / "screen.csv").write_text("changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            journal.append_review(self.folder, self.prices, "2026-09-30")

    def test_changed_review_is_detected(self):
        self.start()
        self.prices_to("2026-08-31")
        journal.append_review(self.folder, self.prices, "2026-08-31")
        (self.folder / "reviews/2026-08-31.json").write_text("{}")
        self.prices_to()
        with self.assertRaisesRegex(ValueError, "checksum"):
            journal.append_review(self.folder, self.prices, "2026-09-30")

    def test_revised_prior_asset_or_benchmark_price_is_rejected(self):
        self.start()
        self.prices_to("2026-08-31")
        journal.append_review(self.folder, self.prices, "2026-08-31")
        for changed_code in ("000001", "BENCHMARK"):
            self.prices_to(bad=lambda rs: [(d, c, 200 if d == "2026-08-31" and c == changed_code else p) for d, c, p in rs])
            with self.assertRaisesRegex(ValueError, "revis"):
                journal.append_review(self.folder, self.prices, "2026-09-30")

    def test_no_candidates_and_insufficient_lot_budget_do_not_invent_holdings(self):
        self.screen.write_text(self.screen.read_text().replace("review_moat", "needs_data"))
        result = self.start()
        self.assertEqual(result["state"], "no_eligible_candidates")
        self.prices_to()
        with self.assertRaisesRegex(ValueError, "no eligible"):
            journal.append_review(self.folder, self.prices, "2026-09-30")
        self.folder = self.root / "small budget"
        self.screen.write_text(self.screen.read_text().replace("needs_data", "review_moat"))
        self.start(cash=100)
        with self.assertRaisesRegex(ValueError, "one lot"):
            journal.append_review(self.folder, self.prices, "2026-09-30")

    def test_bad_screen_parameters_and_future_valuation_are_rejected(self):
        for options in ({"cash": float("nan")}, {"cost_bps": -1}, {"top": 0}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.start(**options)
        self.screen.write_text(self.screen.read_text().replace("2026-07-31", "2026-08-01"))
        with self.assertRaisesRegex(ValueError, "valuation date"):
            self.start()
        self.assertFalse(self.folder.exists())

    def test_cli_runs_outside_checkout_and_seals_provenance(self):
        run = subprocess.run([sys.executable, str(ROOT / "scripts/paper_journal.py"), "start", "--screen", str(self.screen),
                              "--output", str(self.folder), "--signal-date", "2026-07-31", "--data-kind", "synthetic", "--top", "1"],
                             cwd=self.root, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        journal.verify_seal(self.folder, "checksums.json")
        self.assertIn("synthetic", (self.folder / "INITIAL_REVIEW.md").read_text(encoding="utf-8"))

    def test_report_separates_partial_rows_and_shows_issues(self):
        report = render_report(self.screen, "2026-07-31")
        complete_section, partial_section = report.split("## 数据不完整", 1)
        self.assertNotIn("| 000003", complete_section)
        self.assertIn("cashflow_history_incomplete", partial_section)
        self.assertIn("needs_data", partial_section)
        self.assertIn("**2**", report)

    def daily_module(self):
        spec = importlib.util.spec_from_file_location("daily_journal_test", ROOT / ".github/scripts/daily_report.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ROOT = self.root
        return module

    def test_daily_success_freezes_first_snapshot_and_preserves_it_on_rerun(self):
        module = self.daily_module()
        today = journal.datetime.now(journal.MARKET_TZ).date().isoformat()
        reports = self.root / "reports"
        reports.mkdir()
        daily = reports / f"{today}.csv"
        daily.write_bytes(self.screen.read_bytes())
        with patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")):
            self.assertEqual(module.main(), 0)
            frozen = reports / "paper" / today / "snapshot.json"
            before = frozen.read_bytes()
            daily.write_text(daily.read_text().replace(",90,", ",85,"))
            self.assertEqual(module.main(), 0)
            self.assertEqual(before, frozen.read_bytes())

    def test_daily_failure_is_nonzero_and_creates_no_paper_record(self):
        module = self.daily_module()
        with patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 2, "", "network failure")):
            self.assertEqual(module.main(), 1)
        self.assertFalse((self.root / "reports/paper").exists())


if __name__ == "__main__":
    unittest.main()
