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
SKILL = ROOT / "my-skills/options-strategy-payoff"
SCRIPT = SKILL / "scripts/options_strategy_payoff.py"
EXAMPLE_LEGS = SKILL / "references/example-legs.csv"
EXAMPLE_OUTPUT = SKILL / "references/example-output.json"
spec = importlib.util.spec_from_file_location("options_strategy_payoff", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

HEADER = ["leg_id", "instrument", "side", "strike", "quantity", "premium", "multiplier"]
COVERED_CALL = [
    ["futures_long_100", "futures", "buy", "", 1, 100, 1],
    ["call_short_110", "call", "sell", 110, 1, 3, 1],
]
STRADDLE = [
    ["call_long_100", "call", "buy", 100, 1, 5, 1],
    ["put_long_100", "put", "buy", 100, 1, 4, 1],
]
BULL_SPREAD = [
    ["call_long_100", "call", "buy", 100, 1, 6, 1],
    ["call_short_110", "call", "sell", 110, 1, 2, 1],
]
SHORT_FUTURES = [
    ["futures_short_100", "futures", "sell", "", 1, 100, 1],
]
COLLAR = [
    ["put_long_95", "put", "buy", 95, 1, 2, 1],
    ["call_short_110", "call", "sell", 110, 1, 1.5, 1],
    ["futures_long_100", "futures", "buy", "", 1, 100, 1],
]
BUTTERFLY = [
    ["call_long_90", "call", "buy", 90, 1, 12, 1],
    ["call_short_100", "call", "sell", 100, 2, 6, 1],
    ["call_long_110", "call", "buy", 110, 1, 2, 1],
]


def legs_csv(rows, header=HEADER):
    text = io.StringIO()
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return text.getvalue().encode("utf-8")


def analyze(rows, strategy="DEMO", prices=None):
    return module.analyze(legs_csv(rows), strategy, prices)


def payoff_table(result):
    return {item["underlying_price"]: item["profit_loss"] for item in result["payoff_at_prices"]}


class OptionsStrategyPayoffTests(unittest.TestCase):
    def test_covered_call_matches_hand_arithmetic(self):
        result = analyze(COVERED_CALL, "covered-call-demo", [80, 90, 97, 100, 110, 120])
        self.assertEqual(result["net_premium"], -3.0)
        self.assertEqual(result["breakevens"], [97.0])
        table = payoff_table(result)
        self.assertEqual(table[80.0], -17.0)
        self.assertEqual(table[90.0], -7.0)
        self.assertEqual(table[97.0], 0.0)
        self.assertEqual(table[100.0], 3.0)
        self.assertEqual(table[110.0], 13.0)
        self.assertEqual(table[120.0], 13.0)
        self.assertEqual(result["max_profit"], 13.0)
        self.assertEqual(result["max_loss"], -97.0)
        self.assertEqual(result["price_grid"], [80.0, 90.0, 97.0, 100.0, 110.0, 120.0])

    def test_long_straddle_has_two_breakevens_and_unbounded_profit(self):
        result = analyze(STRADDLE, "long-straddle", [91, 100, 109])
        self.assertEqual(result["net_premium"], 9.0)
        self.assertEqual(result["breakevens"], [91.0, 109.0])
        self.assertEqual(result["max_profit"], "unbounded")
        self.assertEqual(result["max_loss"], -9.0)
        self.assertEqual(payoff_table(result)[100.0], -9.0)
        legs = module.parse_legs(legs_csv(STRADDLE))
        self.assertEqual(module.slope_high(legs), 1.0)
        self.assertEqual(module.slope_low(legs), -1.0)
        self.assertGreater(module.payoff(legs, 1000.0), 0.0)

    def test_bull_call_spread_is_finite_and_breaks_even_at_104(self):
        result = analyze(BULL_SPREAD, "bull-call-spread", [100, 104, 110])
        self.assertEqual(result["net_premium"], 4.0)
        self.assertEqual(result["breakevens"], [104.0])
        self.assertEqual(result["max_profit"], 6.0)
        self.assertEqual(result["max_loss"], -4.0)
        table = payoff_table(result)
        self.assertEqual(table[100.0], -4.0)
        self.assertEqual(table[104.0], 0.0)
        self.assertEqual(table[110.0], 6.0)
        legs = module.parse_legs(legs_csv(BULL_SPREAD))
        self.assertEqual(module.payoff(legs, 0.0), -4.0)

    def test_short_futures_profit_is_bounded_at_zero_price_and_loss_is_unbounded(self):
        result = analyze(SHORT_FUTURES, "short-futures", [50, 100, 150])
        self.assertEqual(result["net_premium"], 0.0)
        self.assertEqual(result["breakevens"], [100.0])
        # Domain is S>0: profit tops out at the 100 entry price as S approaches 0,
        # while a rising underlying price makes the loss unbounded.
        self.assertEqual(result["max_profit"], 100.0)
        self.assertEqual(result["max_loss"], "unbounded")
        legs = module.parse_legs(legs_csv(SHORT_FUTURES))
        self.assertEqual(module.slope_high(legs), -1.0)
        self.assertEqual(module.slope_low(legs), -1.0)
        self.assertEqual(module.payoff(legs, 0.0), 100.0)
        # A long put has the same bounded left tail: max profit is K - premium at S=0.
        long_put = analyze([["put_long", "put", "buy", 100, 1, 5, 1]], "long-put", [50, 100])
        self.assertEqual(long_put["max_profit"], 95.0)
        self.assertEqual(long_put["max_loss"], -5.0)

    def test_collar_matches_hand_arithmetic_and_correct_breakeven(self):
        result = analyze(COLLAR, "collar", [0.5, 95, 100, 110, 120])
        self.assertEqual(result["net_premium"], 0.5)
        self.assertEqual(result["breakevens"], [100.5])
        self.assertEqual(result["max_profit"], 9.5)
        self.assertEqual(result["max_loss"], -5.5)
        legs = module.parse_legs(legs_csv(COLLAR))
        self.assertEqual(module.payoff(legs, 0.0), -5.5)
        self.assertEqual(module.payoff(legs, 95.0), -5.5)
        self.assertEqual(module.payoff(legs, 100.0), -0.5)
        self.assertEqual(module.payoff(legs, 100.5), 0.0)
        self.assertEqual(module.payoff(legs, 110.0), 9.5)
        self.assertEqual(module.payoff(legs, 120.0), 9.5)
        # 95.5 is the "strike + net debit" shortcut; the futures entry at 100 adds a
        # further 5-point in-the-money cushion, so the actual zero level is 100.5.
        self.assertEqual(module.payoff(legs, 95.5), -5.0)

    def test_butterfly_breakevens_are_exact_across_multiple_kinks(self):
        result = analyze(BUTTERFLY, "butterfly", [92, 100, 108])
        self.assertEqual(result["net_premium"], 2.0)
        self.assertEqual(result["breakevens"], [92.0, 108.0])
        self.assertEqual(result["max_profit"], 8.0)
        self.assertEqual(result["max_loss"], -2.0)
        legs = module.parse_legs(legs_csv(BUTTERFLY))
        self.assertEqual(module.payoff(legs, 92.0), 0.0)
        self.assertEqual(module.payoff(legs, 100.0), 8.0)
        self.assertEqual(module.payoff(legs, 108.0), 0.0)
        self.assertEqual(module.payoff(legs, 120.0), -2.0)

    def test_net_premium_sign_and_futures_exclusion(self):
        cases = [(COVERED_CALL, -3.0), (STRADDLE, 9.0), (BULL_SPREAD, 4.0),
                 (SHORT_FUTURES, 0.0), (COLLAR, 0.5)]
        for rows, expected in cases:
            with self.subTest(expected=expected):
                result = analyze(rows, "premium", [100])
                self.assertEqual(result["net_premium"], expected)
                legs = module.parse_legs(legs_csv(rows))
                cash_total = sum(leg["cash_flow_at_entry"] for leg in legs)
                self.assertAlmostEqual(cash_total, -expected, places=12)
                for leg in result["legs"]:
                    if leg["instrument"] == "futures":
                        self.assertEqual(leg["cash_flow_at_entry"], 0.0)
                    else:
                        self.assertEqual(leg["cash_flow_at_entry"],
                                         -leg["signed_quantity"] * leg["premium"] * leg["multiplier"])
    def test_futures_legs_are_echoed_without_strike_and_leave_net_premium_zero(self):
        result = analyze(COVERED_CALL, "echo", [100])
        futures_leg, call_leg = result["legs"]
        self.assertEqual(futures_leg["instrument"], "futures")
        self.assertEqual(futures_leg["side"], "buy")
        self.assertIsNone(futures_leg["strike"])
        self.assertEqual(futures_leg["signed_quantity"], 1.0)
        self.assertEqual(futures_leg["cash_flow_at_entry"], 0.0)
        self.assertEqual(call_leg["signed_quantity"], -1.0)
        self.assertEqual(call_leg["cash_flow_at_entry"], 3.0)
        self.assertEqual(result["leg_count"], 2)
        self.assertEqual(analyze(SHORT_FUTURES, "futures-only", [100])["net_premium"], 0.0)

    def test_validation_rejects_invalid_leg_definitions(self):
        cases = [
            [["a", "call", "hold", 100, 1, 5, 1]],
            [["a", "swaption", "buy", 100, 1, 5, 1]],
            [["a", "call", "buy", 100, 0, 5, 1]],
            [["a", "call", "buy", 100, -1, 5, 1]],
            [["a", "call", "buy", 100, "nan", 5, 1]],
            [["a", "call", "buy", 100, "inf", 5, 1]],
            [["a", "call", "buy", 100, 1, -1, 1]],
            [["a", "call", "buy", 100, 1, "nan", 1]],
            [["a", "call", "buy", 100, 1, 5, 0]],
            [["a", "call", "buy", 100, 1, 5, -2]],
            [["a", "futures", "buy", "", 1, 0, 1]],
            [["a", "futures", "buy", "", 1, "nan", 1]],
            [["a", "futures", "buy", 100, 1, 100, 1]],
            [["a", "futures", "buy", "-5", 1, 100, 1]],
            [["a", "futures", "buy", "abc", 1, 100, 1]],
            [["a", "call", "buy", "", 1, 5, 1]],
            [["a", "call", "buy", "-", 1, 5, 1]],
            [["a", "call", "buy", "nan", 1, 5, 1]],
            [["dup", "call", "buy", 100, 1, 5, 1], ["dup", "put", "sell", 100, 1, 5, 1]],
            [["", "call", "buy", 100, 1, 5, 1]],
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                analyze(rows, "bad", [100])
        for prices in ([0.0], [-1.0], [float("nan")], [float("inf")], []):
            with self.subTest(prices=prices), self.assertRaises(ValueError):
                module.analyze(legs_csv(COVERED_CALL), "bad", prices)
        for strategy in ("", "   ", None):
            with self.subTest(strategy=strategy), self.assertRaises(ValueError):
                module.analyze(legs_csv(COVERED_CALL), strategy, [100])

    def test_empty_files_missing_columns_and_bad_encoding_are_rejected(self):
        cases = [b"", b"  \n\n", legs_csv([]), b"leg_id,instrument\nx,call\n",
                 b"\xff\xfe not utf-8"]
        for raw in cases:
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                module.analyze(raw, "bad", [100])

    def test_default_price_grid_is_sorted_unique_and_deterministic(self):
        covered = analyze(COVERED_CALL, "grid")
        self.assertEqual(covered["price_grid"], [88.0, 110.0, 132.0])
        straddle = analyze(STRADDLE, "grid")
        self.assertEqual(straddle["price_grid"], [80.0, 100.0, 120.0])
        butterfly = analyze(BUTTERFLY, "grid")
        self.assertEqual(butterfly["price_grid"],
                         [72.0, 80.0, 88.0, 90.0, 100.0, 108.0, 110.0, 120.0, 132.0])
        self.assertEqual(butterfly["price_grid"], sorted(set(butterfly["price_grid"])))
        repeat = analyze(BUTTERFLY, "grid")
        self.assertEqual(repeat["price_grid"], butterfly["price_grid"])
        self.assertEqual(repeat["payoff_at_prices"], butterfly["payoff_at_prices"])
        self.assertEqual(len(butterfly["payoff_at_prices"]), len(butterfly["price_grid"]))

    def test_default_price_grid_requires_an_option_strike(self):
        with self.assertRaises(ValueError):
            analyze(SHORT_FUTURES, "futures-only")
        result = analyze(SHORT_FUTURES, "futures-only", [100])
        self.assertEqual(result["price_grid"], [100.0])

    def test_breakevens_are_restricted_to_positive_underlying_prices(self):
        rows = [["put_long_100", "put", "buy", 100, 1, 100, 1]]
        legs = module.parse_legs(legs_csv(rows))
        self.assertEqual(module.payoff(legs, 0.0), 0.0)
        result = analyze(rows, "zero-boundary", [0.5, 1])
        self.assertEqual(result["breakevens"], [])
        self.assertEqual(result["max_loss"], -100.0)

    def test_identically_zero_payoff_is_rejected_as_undefined(self):
        rows = [["call_buy", "call", "buy", 100, 1, 5, 1],
                ["call_sell", "call", "sell", 100, 1, 5, 1]]
        legs = module.parse_legs(legs_csv(rows))
        self.assertEqual(module.payoff(legs, 80.0), 0.0)
        self.assertEqual(module.payoff(legs, 120.0), 0.0)
        with self.assertRaises(ValueError):
            analyze(rows, "flat-zero", [100])

    def test_extrema_are_consistent_with_candidate_points_and_price_table(self):
        for rows in (COVERED_CALL, STRADDLE, BULL_SPREAD, SHORT_FUTURES, COLLAR, BUTTERFLY):
            with self.subTest(rows=rows):
                raw = legs_csv(rows)
                result = module.analyze(raw, "consistency", [10, 50, 100, 200])
                legs = module.parse_legs(raw)
                candidates = [0.0] + module.option_strikes(legs)
                candidate_values = [module.payoff(legs, point) for point in candidates]
                table = payoff_table(result)
                for price, value in table.items():
                    self.assertAlmostEqual(module.payoff(legs, price), value, places=12)
                if result["max_profit"] != "unbounded":
                    self.assertAlmostEqual(result["max_profit"], max(candidate_values), places=12)
                    for value in table.values():
                        self.assertLessEqual(value, result["max_profit"] + 1e-9)
                if result["max_loss"] != "unbounded":
                    self.assertAlmostEqual(result["max_loss"], min(candidate_values), places=12)
                    for value in table.values():
                        self.assertGreaterEqual(value, result["max_loss"] - 1e-9)

    def test_parsing_is_case_insensitive_and_defaults_multiplier(self):
        rows = [["a", "CALL", "SELL", 110, 1, 3],
                ["b", "FUTURES", "BUY", "-", 1, 100]]
        raw = legs_csv(rows, header=["leg_id", "instrument", "side", "strike", "quantity", "premium"])
        result = module.analyze(raw, "  demo label  ", [100])
        self.assertEqual(result["strategy"], "demo label")
        self.assertEqual([leg["instrument"] for leg in result["legs"]], ["call", "futures"])
        self.assertEqual([leg["side"] for leg in result["legs"]], ["sell", "buy"])
        self.assertEqual([leg["multiplier"] for leg in result["legs"]], [1.0, 1.0])
        self.assertEqual(result["legs"][0]["strike"], 110.0)
        self.assertIsNone(result["legs"][1]["strike"])
        blank_multiplier = module.analyze(legs_csv([["a", "call", "buy", 100, 1, 5, ""]]), "blank", [100])
        self.assertEqual(blank_multiplier["legs"][0]["multiplier"], 1.0)
        fractional = module.analyze(legs_csv([["a", "call", "buy", 100, 2.5, 5, 2]]), "fractional", [110])
        self.assertEqual(fractional["net_premium"], 25.0)
        self.assertEqual(payoff_table(fractional)[110.0], 25.0)

    def test_output_declares_scope_limitations_and_no_trade_claims(self):
        result = analyze(COVERED_CALL, "scope", [100])
        for key in ("trade", "win_rate", "signal", "recommendation"):
            self.assertNotIn(key, result)
        for key in ("source_sha256", "source_file", "generated_at_utc"):
            self.assertNotIn(key, result)
        self.assertIsInstance(result["scope"], str)
        self.assertIn("expiry-only", result["scope"].lower())
        self.assertIn("trade recommendation", result["scope"].lower())
        self.assertGreaterEqual(len(result["limitations"]), 4)
        text = " ".join(result["limitations"]).lower()
        for fragment in ("early exercise", "margin", "slippage", "user inputs",
                         "strategy label", "unbounded", "not a trade recommendation"):
            self.assertIn(fragment, text)

    def test_cli_runs_outside_skill_dir_with_spaces_and_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "legs input.csv"
            output = directory / "payoff report.json"
            raw = legs_csv(COVERED_CALL)
            source.write_bytes(raw)
            args = [sys.executable, str(SCRIPT), "--csv", str(source), "--strategy", "covered-call-demo",
                    "--prices", "80", "90", "97", "100", "110", "120", "--out", str(output)]
            run = subprocess.run(args, cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(len(run.stdout.strip().splitlines()), 1)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["net_premium"], -3.0)
            self.assertEqual(report["breakevens"], [97.0])
            self.assertEqual(report["price_grid"], [80.0, 90.0, 97.0, 100.0, 110.0, 120.0])
            self.assertEqual(report["source_file"], source.name)
            self.assertEqual(report["source_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertIn("generated_at_utc", report)
            self.assertEqual(raw, source.read_bytes())
            before = output.read_bytes()
            repeat = subprocess.run(args, cwd=directory, capture_output=True, text=True)
            self.assertEqual(repeat.returncode, 2, repeat.stderr)
            self.assertIn("ERROR:", repeat.stderr)
            self.assertEqual(before, output.read_bytes())
            same_path = args.copy()
            same_path[-1] = str(source)
            rejected = subprocess.run(same_path, cwd=directory, capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 2, rejected.stderr)
            self.assertEqual(raw, source.read_bytes())

    def test_cli_reports_invalid_input_as_error_exit_2(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "bad.csv"
            output = directory / "out.json"
            source.write_text("leg_id,instrument,side,strike,quantity,premium,multiplier\n"
                              "a,call,buy,100,0,5,1\n", encoding="utf-8")
            args = [sys.executable, str(SCRIPT), "--csv", str(source), "--strategy", "bad",
                    "--out", str(output)]
            run = subprocess.run(args, cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertIn("ERROR:", run.stderr)
            self.assertFalse(output.exists())

    def test_breakevens_are_rounded_to_six_decimals(self):
        rows = [["call_long_100", "call", "buy", 100, 1, 6.123456789, 1],
                ["call_short_110", "call", "sell", 110, 1, 2, 1]]
        result = analyze(rows, "rounding", [104])
        self.assertEqual(len(result["breakevens"]), 1)
        self.assertAlmostEqual(result["breakevens"][0], 104.123457, places=6)
        self.assertAlmostEqual(result["breakevens"][0], round(104.123456789, 6), places=6)

    def test_covered_call_leg_echo_and_net_premium_note(self):
        result = analyze(COVERED_CALL, "echo-note", [100])
        self.assertEqual(result["leg_count"], 2)
        self.assertIn("Positive net_premium", result["net_premium_note"])
        self.assertIn("futures", result["net_premium_note"].lower())
        self.assertIsInstance(result["breakeven_basis"], str)
        self.assertEqual(result["strategy"], "echo-note")

    def test_reference_example_files_match_actual_analysis(self):
        self.assertTrue(EXAMPLE_LEGS.is_file())
        self.assertTrue(EXAMPLE_OUTPUT.is_file())
        raw = EXAMPLE_LEGS.read_bytes()
        stored = json.loads(EXAMPLE_OUTPUT.read_text(encoding="utf-8"))
        expected = module.analyze(raw, "covered-call-demo", [80, 90, 97, 100, 110, 120])
        for key in ("schema_version", "strategy", "leg_count", "legs", "net_premium",
                    "net_premium_note", "breakevens", "breakeven_basis", "max_profit",
                    "max_loss", "price_grid", "payoff_at_prices", "scope", "limitations"):
            self.assertEqual(stored[key], expected[key], key)
        self.assertEqual(stored["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(stored["source_file"], "example-legs.csv")
        self.assertIn("generated_at_utc", stored)
        self.assertEqual(stored["leg_count"], 2)
        self.assertEqual(stored["net_premium"], -3.0)
        self.assertEqual(stored["breakevens"], [97.0])
        self.assertEqual(stored["max_profit"], 13.0)
        self.assertEqual(stored["max_loss"], -97.0)
        csv_rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        self.assertEqual(len(csv_rows), 2)
        self.assertEqual(csv_rows[0]["instrument"], "futures")
        self.assertEqual(csv_rows[0]["strike"], "")
        self.assertEqual(csv_rows[1]["premium"], "3")


if __name__ == "__main__":
    unittest.main()
