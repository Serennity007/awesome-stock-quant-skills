import importlib.util
from pathlib import Path
import unittest
import tempfile
import subprocess
import sys
import json
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("framework_backtest", ROOT / "my-skills/framework-backtest/scripts/backtest.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)


class BacktestTests(unittest.TestCase):
    def run_model(self, panel, **kwargs):
        stocks = {code: {"ind": pd.DataFrame({"rank": [2 if code == "A" else 1]})} for code in panel}
        benchmark = pd.Series([100 + 10 * i for i in range(len(panel))], index=panel.index)
        with patch.object(bt, "_annual_slice", side_effect=lambda stock, t: (stock["ind"], pd.DataFrame())), \
             patch.object(bt, "score_danbin", side_effect=lambda sl, profit: float(sl["rank"].iloc[0])):
            return bt.run_framework("danbin", stocks, panel, benchmark, str(panel.index[0].date()), kwargs.pop("top_n", 1), **kwargs)

    def test_selection_cannot_use_next_month_availability(self):
        panel = pd.DataFrame({"A": [100, np.nan], "B": [100, 120]}, index=pd.to_datetime(["2024-01-31", "2024-02-29"]))
        with self.assertRaisesRegex(ValueError, "exit|holding|price"):
            self.run_model(panel)

    def test_benchmark_uses_the_same_actual_trading_dates(self):
        panel = pd.DataFrame({"A": [100, 120]}, index=pd.to_datetime(["2021-01-29", "2021-02-26"]))
        _, out, _ = self.run_model(panel)
        self.assertAlmostEqual(out["bench_ret"].iloc[0], 0.1)
        self.assertAlmostEqual(out["bench_nav"].iloc[0], 1.1)

    def test_first_month_loss_counts_as_drawdown(self):
        result = bt.metrics(pd.Series([0.8]), pd.Series([-0.2]), pd.Series([0.9]))
        self.assertEqual(result["max_dd"], -20.0)
        self.assertEqual(result["bench_max_dd"], -10.0)

    def test_cashflow_provider_values_are_ratios_despite_percent_label(self):
        low = pd.DataFrame({"净资产收益率(%)": [20] * 5, "资产负债率(%)": [30] * 5,
                            "净利润增长率(%)": [10] * 5, "主营业务收入增长率(%)": [10] * 5,
                            "经营现金净流量与净利润的比率(%)": [0.5] * 5})
        high = low.assign(**{"经营现金净流量与净利润的比率(%)": [1.0] * 5})
        self.assertGreater(bt.score_danbin(high, pd.DataFrame()), bt.score_danbin(low, pd.DataFrame()))
        self.assertGreater(bt.score_lilu(high, pd.DataFrame(), 20), bt.score_lilu(low, pd.DataFrame(), 20))

    def test_costs_and_holdings_are_auditable(self):
        panel = pd.DataFrame({"A": [100, 100, 100]}, index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-28"]))
        _, out, holdings = self.run_model(panel, cost_bps=10)
        self.assertAlmostEqual(out["ret"].iloc[0], -0.001)
        self.assertAlmostEqual(out["ret"].iloc[1], 0)
        self.assertEqual(list(out["turnover"]), [1, 0])
        self.assertEqual(len(holdings), 2)
        self.assertEqual(set(holdings["code"]), {"A"})

    def test_missing_benchmark_and_calendar_gaps_fail(self):
        panel = pd.DataFrame({"A": [100, 120]}, index=pd.to_datetime(["2024-01-31", "2024-03-28"]))
        with self.assertRaisesRegex(ValueError, "month|gap"):
            self.run_model(panel)

    def test_fetch_benchmark_preserves_trading_day_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bench_sh000300.csv"
            path.write_text("date,close\n2021-01-29,100\n2021-02-26,110\n", encoding="utf-8")
            result = bt.fetch_benchmark(temp)
        self.assertEqual(list(result.index), list(pd.to_datetime(["2021-01-29", "2021-02-26"])))

    def test_missing_benchmark_is_not_zero_return(self):
        dates = pd.to_datetime(["2024-01-31", "2024-02-29"])
        panel = pd.DataFrame({"A": [100, 110]}, index=dates)
        with patch.object(bt, "_annual_slice", return_value=(pd.DataFrame(), pd.DataFrame())), \
             patch.object(bt, "score_danbin", return_value=1), self.assertRaisesRegex(ValueError, "benchmark"):
            bt.run_framework("danbin", {"A": {}}, panel, pd.Series([100], index=dates[:1]), "2024-01-31", 1)

    def test_rebalancing_uses_drifted_weights(self):
        panel = pd.DataFrame({"A": [100, 200, 200], "B": [100, 100, 100]},
                             index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-28"]))
        _, out, _ = self.run_model(panel, top_n=2, cost_bps=10)
        self.assertAlmostEqual(out["turnover"].iloc[1], 1 / 3)
        self.assertAlmostEqual(out["cost_fraction"].iloc[1], 1 / 3000)

    def test_switching_stock_charges_buy_and_sell_legs(self):
        dates = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-28"])
        panel = pd.DataFrame({"A": [100] * 3, "B": [100] * 3}, index=dates)
        with patch.object(bt, "_annual_slice", return_value=(pd.DataFrame(), pd.DataFrame())), \
             patch.object(bt, "score_danbin", side_effect=[2, 1, 1, 2]):
            _, out, _ = bt.run_framework("danbin", {"A": {}, "B": {}}, panel,
                                         pd.Series([100] * 3, index=dates), "2024-01-31", 1, 10)
        self.assertEqual(list(out["turnover"]), [1, 2])
        self.assertAlmostEqual(out["ret"].iloc[1], -0.002)

    def test_negative_gross_margin_is_not_dropped_as_missing(self):
        gross = bt._gross_series(pd.DataFrame({"营业总收入": [100], "营业成本": [150]}))
        self.assertEqual(list(gross), [-50])

    def test_full_cli_emits_net_returns_holdings_and_input_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            run = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "my-skills/framework-backtest/scripts/backtest.py"),
                                  "--cache-dir", str(ROOT / "examples/backtest/cache"), "--results-dir", temp,
                                  "--frameworks", "danbin", "--start", "2026-07-31", "--top", "1",
                                  "--min-stocks", "2", "--cost-bps", "10"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run.returncode, 0, run.stderr)
            out = pd.read_csv(Path(temp) / "bt_result_danbin.csv")
            self.assertAlmostEqual(out["nav"].iloc[-1], 0.98901)
            self.assertAlmostEqual(out["bench_nav"].iloc[-1], 1.01)
            self.assertEqual(len(pd.read_csv(Path(temp) / "bt_holdings_danbin.csv")), 2)
            meta = json.loads((Path(temp) / "bt_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["cost_bps_per_traded_notional"], 10)
            self.assertEqual(len(meta["cache_sha256"]), 7)


if __name__ == "__main__":
    unittest.main()
