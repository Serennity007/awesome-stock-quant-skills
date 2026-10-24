import importlib.util
from pathlib import Path
import tempfile
import unittest
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("upstreams", ROOT / "scripts/check_upstreams.py")
upstreams = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstreams)


class UpstreamTests(unittest.TestCase):
    def source(self, pin=None):
        return {"directory": "a__b", "repository": "a/b", "declared_license": "MIT", "mirrored_commit": pin}

    def fetch(self, url):
        if "/commits?" in url:
            return [{"sha": "a" * 40}]
        return {"license": {"spdx_id": "MIT"}, "archived": False,
                "html_url": "https://github.com/a/b", "stargazers_count": 1}

    def test_unpinned_snapshot_never_claims_current(self):
        result = upstreams.inspect_source(self.source(), {}, self.fetch)
        self.assertEqual(result["flags"], ["snapshot-unpinned"])

    def test_detects_head_change_and_snapshot_drift(self):
        previous = {"a__b": {"head_sha": "b" * 40}}
        result = upstreams.inspect_source(self.source("b" * 40), previous, self.fetch)
        self.assertIn("head-changed-since-check", result["flags"])
        self.assertIn("snapshot-behind-head", result["flags"])

    def test_license_archival_and_missing_license_are_visible(self):
        def fetch(url):
            data = self.fetch(url)
            if isinstance(data, dict):
                data.update(license=None, archived=True)
            return data
        flags = upstreams.inspect_source(self.source(), {}, fetch)["flags"]
        self.assertIn("license-needs-review", flags)
        self.assertIn("archived", flags)

    def test_fetch_failure_is_not_success_and_does_not_leak_error_body(self):
        def fail(url):
            raise URLError("secret response")
        result = upstreams.inspect_source(self.source(), {}, fail)
        self.assertEqual(result["status"], "error")
        self.assertNotIn("secret", str(result))

    def test_discovers_only_declared_mirrors(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "skills/a__b/SOURCE.md"
            path.parent.mkdir(parents=True)
            path.write_text("- 原始仓库: https://github.com/a/b\n- License: MIT\n", encoding="utf-8")
            sources = upstreams.discover_sources(Path(temp))
            self.assertEqual(sources[0]["repository"], "a/b")
            self.assertIsNone(sources[0]["mirrored_commit"])

    def test_partial_failure_preserves_baseline_until_recovery(self):
        def fail(url):
            raise URLError("offline")
        old = {"a__b": {"head_sha": "b" * 40}}
        failed = upstreams.inspect_source(self.source(), old, fail)
        self.assertEqual(failed["last_success_head_sha"], "b" * 40)
        recovered = upstreams.inspect_source(self.source(), {"a__b": failed}, self.fetch)
        self.assertIn("head-changed-since-check", recovered["flags"])


if __name__ == "__main__":
    unittest.main()
