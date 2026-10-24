import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io

import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1] / "my-skills/buffett-value-investing/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("buffett_screen", SCRIPTS / "screen.py")
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)
from research_data import annual_rows, valuation_snapshot
spec = importlib.util.spec_from_file_location("buffett_analyze", SCRIPTS / "analyze.py")
analyze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze)


class BuffettDataTests(unittest.TestCase):
    def valuation(self, frame):
        with patch.object(screen, "_retry_call", return_value=frame):
            return screen.valuation_percentile("600519")

    def frame(self):
        dates = pd.bdate_range(end=pd.Timestamp.now().normalize() - pd.Timedelta(days=1), periods=80)
        return pd.DataFrame({"数据日期": dates, "PE(TTM)": range(1, 81), "市净率": [2.0] * 80, "当日收盘价": [100.0] * 80})

    def test_invalid_latest_pe_cannot_reuse_an_old_positive_pe(self):
        frame = self.frame()
        frame.loc[79, "PE(TTM)"] = -1
        pe, _ = self.valuation(frame)
        self.assertIsNone(pe)

    def test_valuation_sorts_by_date_instead_of_input_order(self):
        self.assertEqual(self.valuation(self.frame()), self.valuation(self.frame().iloc[::-1]))

    def test_ttm_is_chosen_even_when_static_pe_is_first(self):
        frame = self.frame()
        frame.insert(1, "PE(静)", list(range(80, 0, -1)))
        pe, _ = self.valuation(frame)
        self.assertEqual(pe, 1.0)

    def test_old_history_outside_five_years_is_excluded(self):
        frame = self.frame()
        old = frame.copy()
        old["数据日期"] -= pd.DateOffset(years=8)
        old["PE(TTM)"] = 1000
        self.assertEqual(self.valuation(frame), self.valuation(pd.concat([old, frame])))

    def test_one_gross_margin_observation_is_not_five_year_stability(self):
        ind = pd.DataFrame({"日期": pd.date_range("2020-12-31", periods=5, freq="YE"),
                            "净资产收益率(%)": [20] * 5, "资产负债率(%)": [30] * 5})
        with patch.object(screen, "annual_fin_indicator", return_value=ind), \
             patch.object(screen, "gross_margins", return_value=pd.Series([50.0])), \
             patch.object(screen, "cashflow_values", return_value=pd.Series([1] * 5)), \
             patch.object(screen, "valuation_data", return_value={"pe_pct": 0.1, "pb_pct": 0.1, "date": "2026-10-23"}), \
             patch.object(screen.time, "sleep"):
            row = screen.score_one("600519")
        self.assertLessEqual(row["gross_score"], 10)
        self.assertEqual(row["decision"], "needs_data")

    def test_mixed_report_dates_and_future_rows(self):
        frame = pd.DataFrame({"日期": [20241231, "2023-12-31 00:00:00", "2099-12-31", "2024-06-30"]})
        result = annual_rows(frame, "日期", as_of="2026-10-24")
        self.assertEqual(list(result["日期"].dt.year), [2023, 2024])

    def test_conflicting_duplicate_dates_are_rejected(self):
        frame = self.frame()
        duplicate = frame.iloc[-1:].assign(**{"PE(TTM)": 999})
        with self.assertRaisesRegex(ValueError, "conflicting"):
            valuation_snapshot(pd.concat([frame, duplicate]))

    def test_missing_cashflow_and_latest_debt_cannot_pass_as_complete(self):
        ind = pd.DataFrame({"日期": pd.date_range("2020-12-31", periods=5, freq="YE"),
                            "净资产收益率(%)": [20] * 5, "资产负债率(%)": [30, 30, 30, 30, None]})
        with patch.object(screen, "annual_fin_indicator", return_value=ind), \
             patch.object(screen, "gross_margins", return_value=pd.Series([50.0] * 5)), \
             patch.object(screen, "cashflow_values", return_value=pd.Series(dtype=float)), \
             patch.object(screen, "valuation_data", return_value={"pe_pct": 0.1, "pb_pct": 0.1, "date": "2026-10-23"}), \
             patch.object(screen.time, "sleep"):
            row = screen.score_one("600519")
        self.assertEqual(row["decision"], "needs_data")
        self.assertEqual(row["debt_score"], 0)
        self.assertIn("cashflow_history_incomplete", row["data_issues"])
        self.assertIn("latest_debt_missing", row["data_issues"])

    def test_analysis_does_not_mix_new_price_with_older_pe(self):
        snapshot = {"date": "2026-10-23", "pe": 10, "pe_q25": 8, "pe_q50": 12, "close": 100}
        trend = pd.DataFrame({"ROE%": [20] * 5})
        text = io.StringIO()
        with patch.object(sys, "argv", ["analyze.py", "600519"]), \
             patch.object(analyze, "ak", object()), patch.object(analyze, "get_name", return_value="Example"), \
             patch.object(analyze, "financial_trend", return_value=trend), \
             patch.object(analyze, "valuation_for_analysis", return_value=snapshot), \
             patch.object(analyze, "latest_price", side_effect=AssertionError("must not mix price dates")), \
             patch.object(analyze.time, "sleep"), redirect_stdout(text):
            analyze.main()
        self.assertIn("2026-10-23", text.getvalue())
        self.assertIn("EPS(估算): 10.00", text.getvalue())


if __name__ == "__main__":
    unittest.main()
