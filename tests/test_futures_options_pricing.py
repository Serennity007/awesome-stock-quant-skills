import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "my-skills/futures-options-pricing"
SCRIPT = SKILL / "scripts/futures_options_pricing.py"
EXAMPLE_CSV = SKILL / "references/example-options.csv"
EXAMPLE_OUTPUT = SKILL / "references/example-output.json"
spec = importlib.util.spec_from_file_location("futures_options_pricing", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

AS_OF = "2026-11-24"
EXPIRY = "2027-06-30"
FUTURES = 100.0
RATE = 0.03
DAYS = 218
YEARS = 218 / 365
GREEK_KEYS = {"delta", "gamma", "vega_per_unit_vol", "vega_per_vol_point", "theta_per_year",
              "theta_per_day", "rho_per_1_rate"}
HEADER = ("option_id", "option_type", "strike", "market_price", "volatility")
BASE_ROWS = [
    ("C100", "call", 100, 8.46, ""),
    ("P100", "put", 100, 7.86, ""),
    ("C95", "call", 95, "", 0.20),
    ("P95", "put", 95, "", 0.20),
    ("C110", "call", 110, 2.61, ""),
]


def option_bytes(rows, header=HEADER):
    text = io.StringIO()
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return text.getvalue().encode("utf-8")


def batch_bytes(rows=None):
    return option_bytes(BASE_ROWS if rows is None else rows)


class FuturesOptionsPricingTests(unittest.TestCase):
    def analyze(self, raw, futures_price=FUTURES, expiry=EXPIRY, as_of=AS_OF, rate=RATE):
        return module.analyze(raw, futures_price, expiry, as_of, rate)

    def test_atm_reference_price_matches_documented_value(self):
        call = module.black76_price(100, 100, 1, 0, 0.2, "call")
        put = module.black76_price(100, 100, 1, 0, 0.2, "put")
        self.assertAlmostEqual(call, 7.9656, places=4)
        self.assertAlmostEqual(put, 7.9656, places=4)
        self.assertAlmostEqual(call, put, places=12)

    def test_put_call_parity_holds_with_non_zero_rate(self):
        for futures, strike in ((105, 100), (95, 100), (100, 100)):
            call = module.black76_price(futures, strike, 0.75, 0.03, 0.22, "call")
            put = module.black76_price(futures, strike, 0.75, 0.03, 0.22, "put")
            expected = math.exp(-0.03 * 0.75) * (futures - strike)
            self.assertAlmostEqual(call - put, expected, places=12)
            self.assertAlmostEqual(put - call, -expected, places=12)

    def test_finite_difference_delta_and_gamma_match_greeks(self):
        futures, strike, years, sigma = 100.0, 100.0, 0.5, 0.25
        step = 1e-4
        for option_type in ("call", "put"):
            with self.subTest(option_type=option_type):
                values = module.greeks(futures, strike, years, RATE, sigma, option_type)
                prices = [module.black76_price(futures + offset, strike, years, RATE, sigma, option_type)
                          for offset in (step, -step)]

                def price(offset):
                    return module.black76_price(futures + offset, strike, years, RATE, sigma, option_type)

                self.assertAlmostEqual(values["delta"], (prices[0] - prices[1]) / (2 * step), delta=1e-5)
                self.assertAlmostEqual(values["gamma"], (prices[0] - 2 * price(0.0) + prices[1]) / (step * step),
                                       delta=1e-5)

    def test_finite_difference_vega_and_theta_match_greeks(self):
        futures, strike, years, sigma = 100.0, 100.0, 0.5, 0.25
        step = 1e-5
        for option_type in ("call", "put"):
            with self.subTest(option_type=option_type):
                values = module.greeks(futures, strike, years, RATE, sigma, option_type)
                vega_up = module.black76_price(futures, strike, years, RATE, sigma + step, option_type)
                vega_down = module.black76_price(futures, strike, years, RATE, sigma - step, option_type)
                theta_up = module.black76_price(futures, strike, years + step, RATE, sigma, option_type)
                theta_down = module.black76_price(futures, strike, years - step, RATE, sigma, option_type)
                self.assertAlmostEqual(values["vega_per_unit_vol"], (vega_up - vega_down) / (2 * step), delta=1e-5)
                self.assertAlmostEqual(values["vega_per_vol_point"], values["vega_per_unit_vol"] / 100.0, places=14)
                self.assertAlmostEqual(values["theta_per_year"], -(theta_up - theta_down) / (2 * step), delta=1e-5)
                self.assertEqual(values["theta_per_day"], values["theta_per_year"] / 365)

    def test_theta_and_rho_sign_conventions(self):
        futures, strike, years, sigma = 100.0, 100.0, 0.5, 0.25
        for option_type in ("call", "put"):
            with self.subTest(option_type=option_type):
                values = module.greeks(futures, strike, years, RATE, sigma, option_type)
                price = module.black76_price(futures, strike, years, RATE, sigma, option_type)
                self.assertAlmostEqual(values["rho_per_1_rate"], -years * price, places=12)
                self.assertAlmostEqual(values["theta_per_day"], values["theta_per_year"] / 365, places=15)

    def test_implied_volatility_round_trip_both_types(self):
        for option_type in ("call", "put"):
            with self.subTest(option_type=option_type):
                price = module.black76_price(90, 100, 0.5, 0.02, 0.35, option_type)
                solved = module.implied_vol(price, 90, 100, 0.5, 0.02, option_type)
                self.assertAlmostEqual(solved, 0.35, delta=1e-7)

    def test_implied_volatility_rejects_prices_outside_the_band(self):
        cases = [
            ("call", 100.0, 90.0, 1.0, 0.0, 9.99),
            ("call", 100.0, 90.0, 1.0, 0.0, 10.0),
            ("call", 100.0, 90.0, 1.0, 0.0, 100.0),
            ("put", 100.0, 110.0, 1.0, 0.0, 9.99),
            ("put", 100.0, 110.0, 1.0, 0.0, 10.0),
            ("put", 100.0, 110.0, 1.0, 0.0, 110.0),
            ("call", 100.0, 80.0, 1.0, 0.03, 19.3),
            ("call", 100.0, 100.0, 1.0, 0.03, 98.52),
            ("put", 100.0, 100.0, 1.0, 0.03, 98.52),
        ]
        for option_type, futures, strike, years, rate, price in cases:
            with self.subTest(option_type=option_type, strike=strike, price=price):
                with self.assertRaises(ValueError):
                    module.implied_vol(price, futures, strike, years, rate, option_type)

    def test_invalid_pricing_inputs_are_rejected(self):
        for arguments in [
            (100, 100, 0, 0, 0.2, "call"),
            (100, 100, -1, 0, 0.2, "call"),
            (100, 100, 1, 0, 0.0, "call"),
            (100, 100, 1, 0, -0.1, "call"),
            (float("nan"), 100, 1, 0, 0.2, "call"),
            (100, float("inf"), 1, 0, 0.2, "call"),
            (100, 100, 1, float("nan"), 0.2, "call"),
            (100, 100, 1, 0, 0.2, "straddle"),
        ]:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                module.black76_price(*arguments)
        with self.assertRaises(ValueError):
            module.implied_vol(float("nan"), 100, 100, 1, 0, "call")

    def test_csv_validation_rejects_bad_rows(self):
        header = "option_id,option_type,strike,market_price,volatility\n"
        cases = {
            "missing column": "option_id,option_type\nX,call\n",
            "empty file": "",
            "duplicate option_id": header + "X,call,100,8.5,\nX,put,100,8.0,\n",
            "blank option_id": header + ",call,100,8.5,\n",
            "unknown option_type": header + "X,straddle,100,8.5,\n",
            "zero strike": header + "X,call,0,8.5,\n",
            "negative strike": header + "X,call,-100,8.5,\n",
            "NaN strike": header + "X,call,NaN,8.5,\n",
            "negative market_price": header + "X,call,100,-1,\n",
            "NaN volatility": header + "X,call,100,,NaN\n",
            "no pricing input": header + "X,call,100,,\n",
            "required columns only": "option_id,option_type,strike\nX,call,100\n",
        }
        for label, raw in cases.items():
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.analyze(raw.encode("utf-8"))

    def test_option_types_are_case_insensitive_and_normalized(self):
        raw = option_bytes([("C1", "CALL", 100, "", 0.20), ("P1", "Put", 100, 7.80, "")])
        result = self.analyze(raw)
        first, second = result["options"]
        self.assertEqual(first["option_type"], "call")
        self.assertEqual(second["option_type"], "put")
        self.assertEqual(first["pricing_volatility"], 0.20)
        self.assertIsNotNone(second["implied_volatility"])
        self.assertEqual(second["implied_volatility_status"], "solved")

    def test_batch_analysis_fields_greeks_and_parity_checks(self):
        raw = batch_bytes()
        result = self.analyze(raw)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["futures_price"], 100.0)
        self.assertEqual(result["as_of_date"], AS_OF)
        self.assertEqual(result["expiry"], EXPIRY)
        self.assertEqual(result["days_to_expiry"], DAYS)
        self.assertEqual(result["time_to_expiry_years"], YEARS)
        self.assertEqual(result["rate"], RATE)
        self.assertEqual(result["day_count_basis"], "calendar_365")
        self.assertEqual(result["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual([option["option_id"] for option in result["options"]],
                         ["C100", "P100", "C95", "P95", "C110"])
        options = {option["option_id"]: option for option in result["options"]}
        for option in result["options"]:
            self.assertEqual(option["days_to_expiry"], DAYS)
            self.assertEqual(option["time_to_expiry_years"], YEARS)
            self.assertEqual(set(option["greeks"]), GREEK_KEYS)
        self.assertAlmostEqual(options["C95"]["moneyness_ln_F_over_K"], math.log(100 / 95), places=14)
        self.assertEqual(options["C100"]["moneyness_ln_F_over_K"], 0.0)
        self.assertAlmostEqual(options["C95"]["model_price"], 8.676242099805636, places=9)
        self.assertIsNone(options["C95"]["market_price"])
        self.assertIsNone(options["C95"]["implied_volatility"])
        self.assertEqual(options["C95"]["implied_volatility_status"], "not_requested")
        self.assertEqual(options["C95"]["pricing_volatility"], 0.20)
        self.assertIsNone(options["C95"]["price_difference_vs_market"])
        self.assertEqual(options["C100"]["implied_volatility_status"], "solved")
        self.assertAlmostEqual(options["C100"]["implied_volatility"], options["C100"]["pricing_volatility"], places=12)
        self.assertAlmostEqual(options["C100"]["implied_volatility"], 0.2799021057, places=6)
        self.assertLess(abs(options["C100"]["price_difference_vs_market"]), 1e-9)
        checks = {check["strike"]: check for check in result["parity_checks"]}
        self.assertEqual(set(checks), {95.0, 100.0})
        self.assertEqual((checks[100.0]["call_option_id"], checks[100.0]["put_option_id"]), ("C100", "P100"))
        self.assertEqual(checks[100.0]["discounted_forward_intrinsic"], 0.0)
        self.assertAlmostEqual(checks[100.0]["call_minus_put"], 0.60, delta=1e-9)
        self.assertAlmostEqual(checks[100.0]["residual"], 0.60, delta=1e-9)
        self.assertAlmostEqual(checks[95.0]["residual"], 0.0, delta=1e-12)
        self.assertAlmostEqual(checks[95.0]["discounted_forward_intrinsic"], math.exp(-RATE * YEARS) * 5.0, places=12)
        self.assertGreaterEqual(len(result["limitations"]), 4)
        self.assertIsInstance(result["scope"], str)
        self.assertNotIn("trade", result)
        self.assertNotIn("win_rate", result)

    def test_as_of_datetime_is_normalized_to_utc_calendar_date(self):
        raw = batch_bytes()
        self.assertEqual(self.analyze(raw, as_of="2026-11-24T20:00:00+08:00")["days_to_expiry"], 218)
        self.assertEqual(self.analyze(raw, as_of="2026-11-25T03:00:00+08:00")["days_to_expiry"], 218)
        self.assertEqual(self.analyze(raw, as_of="2026-11-24T23:30:00-05:00")["days_to_expiry"], 217)
        with self.assertRaises(ValueError):
            self.analyze(raw, as_of="2026-11-24T10:00:00")
        with self.assertRaises(ValueError):
            self.analyze(raw, as_of=EXPIRY)
        with self.assertRaises(ValueError):
            self.analyze(raw, expiry="2027-06-30T00:00:00")

    def test_no_arbitrage_failures_name_the_offending_row(self):
        with self.assertRaises(ValueError) as caught:
            self.analyze(option_bytes([("BAD_CALL", "call", 80, 5.0, "")]))
        self.assertIn("BAD_CALL", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            self.analyze(option_bytes([("BAD_PUT", "put", 110, 1.0, "")]))
        self.assertIn("BAD_PUT", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            self.analyze(option_bytes([("HIGH_CALL", "call", 100, 99.5, "")]))
        self.assertIn("HIGH_CALL", str(caught.exception))

    def test_deep_itm_and_otm_prices_stay_inside_no_arbitrage_band(self):
        futures, rate = 100.0, 0.02
        discount = math.exp(-rate * 0.5)
        for strike, option_type, lower in (
            (60.0, "call", discount * (futures - 60.0)),
            (140.0, "call", 0.0),
            (140.0, "put", discount * (140.0 - futures)),
            (60.0, "put", 0.0),
        ):
            with self.subTest(strike=strike, option_type=option_type):
                upper = discount * (futures if option_type == "call" else strike)
                price = module.black76_price(futures, strike, 0.5, rate, 0.2, option_type)
                self.assertLessEqual(lower, price)
                self.assertLessEqual(price, upper)
        deep_itm = module.black76_price(futures, 60.0, 0.5, rate, 0.2, "call")
        self.assertGreater(deep_itm, discount * (futures - 60.0))

    def test_prices_are_monotone_in_strike_and_volatility(self):
        strikes = [80.0, 90.0, 100.0, 110.0, 120.0]
        call_prices = [module.black76_price(100, strike, 0.5, 0.03, 0.25, "call") for strike in strikes]
        put_prices = [module.black76_price(100, strike, 0.5, 0.03, 0.25, "put") for strike in strikes]
        self.assertEqual(call_prices, sorted(call_prices, reverse=True))
        self.assertEqual(put_prices, sorted(put_prices))
        volatilities = [0.05, 0.10, 0.20, 0.30, 0.50]
        call_by_vol = [module.black76_price(100, 100, 0.5, 0.03, sigma, "call") for sigma in volatilities]
        self.assertEqual(call_by_vol, sorted(call_by_vol))

    def test_cli_end_to_end_outside_skill_and_guard_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "options input.csv"
            output = directory / "nested output" / "pricing report.json"
            raw = batch_bytes()
            source.write_bytes(raw)
            base = [sys.executable, str(SCRIPT), "--csv", str(source), "--futures-price", "100",
                    "--expiry", EXPIRY, "--as-of", AS_OF, "--out", str(output)]
            run = subprocess.run(base + ["--rate", "0.03"], cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stderr, "")
            self.assertTrue(run.stdout.isascii())
            self.assertEqual(run.stdout.count("\n"), 1)
            self.assertIn("Priced 5 option rows", run.stdout)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["source_file"], source.name)
            self.assertEqual(report["source_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertTrue(report["generated_at_utc"])
            self.assertAlmostEqual(report["rate"], 0.03)
            self.assertEqual(raw, source.read_bytes())
            before = output.read_bytes()
            self.assertNotEqual(subprocess.run(base + ["--rate", "0.03"], cwd=directory, capture_output=True).returncode, 0)
            self.assertEqual(before, output.read_bytes())
            overwrite_args = base[:]
            overwrite_args[overwrite_args.index("--out") + 1] = str(source)
            self.assertNotEqual(subprocess.run(overwrite_args, cwd=directory, capture_output=True).returncode, 0)
            self.assertEqual(raw, source.read_bytes())
            default_rate_out = directory / "default rate.json"
            default_run = subprocess.run(base[:1] + base[1:-1] + [str(default_rate_out)], cwd=directory,
                                         capture_output=True, text=True)
            self.assertEqual(default_run.returncode, 0, default_run.stderr)
            self.assertEqual(json.loads(default_rate_out.read_text(encoding="utf-8"))["rate"], 0.0)

    def test_shipped_example_fixture_is_reproducible(self):
        raw = EXAMPLE_CSV.read_bytes()
        document = json.loads(EXAMPLE_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(document["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(document["source_file"], "example-options.csv")
        self.assertTrue(document["generated_at_utc"])
        regenerated = self.analyze(raw, document["futures_price"], document["expiry"],
                                   document["as_of_date"], document["rate"])
        for key in ("source_file", "generated_at_utc"):
            document.pop(key)
        self.assertEqual(document, regenerated)


if __name__ == "__main__":
    unittest.main()
