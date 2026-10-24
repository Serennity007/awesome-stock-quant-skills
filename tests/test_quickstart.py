import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_demo.py"
spec = importlib.util.spec_from_file_location("quickstart_demo", SCRIPT)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class QuickStartTests(unittest.TestCase):
    def test_demo_runs_outside_checkout_and_keeps_inputs_unchanged(self):
        inputs = sorted((ROOT / "examples").rglob("*.csv"))
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "output with spaces"
            run = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), "--output-dir", str(parent)],
                                 cwd=temp, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run.returncode, 0, run.stderr)
            folder, = parent.iterdir()
            status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "passed")
            self.assertEqual(status["data_kind"], "synthetic")
            self.assertFalse(status["market_data_requested"])
            self.assertEqual([r["code"] for r in status["results"]["consensus"]], ["000003", "000001", "000002"])
            self.assertAlmostEqual(status["results"]["net_ending_wealth"], 0.98901)
            self.assertIn("SYNTHETIC DATA", (folder / "REPORT.md").read_text(encoding="utf-8"))
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})

    def test_repeated_runs_preserve_previous_output(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            sentinel = parent / "existing.txt"
            sentinel.write_text("keep me")
            first = demo.run_demo(parent)
            report = (first / "REPORT.md").read_bytes()
            second = demo.run_demo(parent)
            self.assertNotEqual(first, second)
            self.assertEqual((first / "REPORT.md").read_bytes(), report)
            self.assertEqual(sentinel.read_text(), "keep me")

    def test_child_failure_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(demo, "run_step", side_effect=RuntimeError("child failed")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(["--output-dir", temp]), 1)
            folder, = Path(temp).iterdir()
            status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "failed")
            self.assertFalse((folder / "REPORT.md").exists())

    def test_missing_dependencies_produce_install_hint_without_outputs(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(demo, "missing_dependencies", return_value=["pandas"]), contextlib.redirect_stderr(io.StringIO()) as captured:
            parent = Path(temp) / "new output"
            self.assertEqual(demo.main(["--output-dir", str(parent)]), 1)
            self.assertIn("requirements-demo.txt", captured.getvalue())
            if os.name == "nt":
                self.assertIn("Install once: & '", captured.getvalue())
            self.assertFalse(parent.exists())


if __name__ == "__main__":
    unittest.main()
