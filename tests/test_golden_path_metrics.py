"""Tests for commercial golden path metrics (install → torii/gate → dogfood)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "golden_path_metrics.py"
GOLDEN_DOC = ROOT / "docs" / "GOLDEN-PATH.md"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = {**os.environ, "TORII_ROOT": str(ROOT)}
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
        timeout=180,
    )


class GoldenPathMetricsTests(unittest.TestCase):
    def test_script_and_doc_exist(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(GOLDEN_DOC.is_file())
        text = GOLDEN_DOC.read_text(encoding="utf-8")
        self.assertIn("torii/gate", text)
        self.assertIn("install-torii.sh", text)

    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertEqual(data["required_check"], "torii/gate")
        self.assertGreaterEqual(data["readiness"]["ok_n"], 10)
        self.assertGreaterEqual(int(data["labeled_eval"].get("labeled_tp_cases") or 0), 4)

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("ready"))
        self.assertEqual(data.get("required_check"), "torii/gate")

    def test_report_writes_metrics(self):
        out = ROOT / "docs" / "benchmarks" / "golden-path-metrics.md"
        r = _run(["report", "--json", "--allow-partial"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "GOLDEN")
        self.assertEqual(data.get("scorecard_target"), "7.5")
        self.assertIn("fp_tp_chart", data)
        self.assertTrue(out.is_file(), "report should write golden-path-metrics.md")
        body = out.read_text(encoding="utf-8")
        self.assertIn("torii-golden-path-metrics", body)
        self.assertIn("Time-to-signal", body)
        self.assertIn("FP / TP", body)

    def test_cli_umbrella(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "torii.py"), "golden-path", "--", "status"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_ROOT": str(ROOT)},
            timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("required_check"), "torii/gate")


if __name__ == "__main__":
    unittest.main()
