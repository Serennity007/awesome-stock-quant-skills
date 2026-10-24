import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "my-skills/master-ensemble/scripts/ensemble.py"
spec = importlib.util.spec_from_file_location("ensemble", SCRIPT)
ensemble = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ensemble)


class EnsembleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def csv(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def pair(self):
        return [self.csv("quality.csv", "code,total\n1,10\n2,20\n3,30\n"),
                self.csv("momentum.csv", "code,total\n1,30\n2,10\n3,20\n")]

    def test_known_ranks_and_leading_zero_codes(self):
        out, matches = ensemble.combine(self.pair())
        self.assertTrue(matches)
        self.assertEqual(list(out.code), ["000003", "000001", "000002"])
        self.assertEqual(list(out.consensus_score), [83.3, 66.7, 50.0])
        self.assertEqual(list(out.top_hits), [1, 1, 0])

    def test_rejects_bad_schema_codes_scores_and_duplicates(self):
        for content in ("total\n1\n", "code,total\n,10\n", "code,total\nABC,10\n",
                        "code,total\n1,inf\n", "code,total\n1,\n",
                        "code,total\n1,10\n000001,20\n", "code,total\n"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                ensemble.load_one(self.csv("bad.csv", content))

    def test_rejects_framework_name_collision(self):
        paths = [self.csv(n, "code,total\n1,20\n") for n in ("same_result.csv", "same_demo.csv")]
        with self.assertRaisesRegex(ValueError, "collide"):
            ensemble.combine(paths)

    def test_partial_financial_scores_are_not_consensus_votes(self):
        path = self.csv("partial.csv", "code,total,score_status\n1,80,partial\n")
        with self.assertRaisesRegex(ValueError, "partial financial scores"):
            ensemble.load_one(path)

    def test_partial_pools_require_explicit_opt_in(self):
        paths = self.pair()
        paths[1] = self.csv("momentum.csv", "code,total\n2,10\n3,20\n")
        with self.assertRaisesRegex(ValueError, "pools differ"):
            ensemble.combine(paths)
        out, matches = ensemble.combine(paths, allow_partial_pools=True)
        self.assertFalse(matches)
        self.assertEqual(set(out.code), {"000002", "000003"})

    def test_parameters_and_finite_sample_ties(self):
        paths = self.pair()
        for top in (0, -1, 101, float("nan")):
            with self.assertRaises(ValueError):
                ensemble.combine(paths, top_pct=top)
        for minimum in (1, 3):
            with self.assertRaises(ValueError):
                ensemble.combine(paths, min_frameworks=minimum)
        paths = [self.csv(n, "code,total\n1,10\n2,10\n") for n in ("a.csv", "b.csv")]
        out, _ = ensemble.combine(paths)
        self.assertEqual(list(out.consensus_score), [75.0, 75.0])
        self.assertEqual(list(out.top_hits), [0, 0])

    def test_cli_manifest_and_invalid_input_exit(self):
        paths = self.pair()
        output = self.root / "result.csv"
        command = [sys.executable, str(SCRIPT), "--csvs", *map(str, paths), "--out", str(output)]
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        meta = json.loads(output.with_suffix(".csv.meta.json").read_text())
        self.assertIsNone(meta["as_of"])
        self.assertFalse(meta["as_of_verified"])
        self.assertEqual(meta["inputs"][0]["sha256"], hashlib.sha256(paths[0].read_bytes()).hexdigest())
        self.assertNotEqual(subprocess.run(command + ["--top-pct", "0"], capture_output=True).returncode, 0)

    def test_cli_cannot_overwrite_input(self):
        paths = self.pair()
        original = paths[0].read_bytes()
        run = subprocess.run([sys.executable, str(SCRIPT), "--csvs", *map(str, paths),
                              "--out", str(paths[0])], capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(paths[0].read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
