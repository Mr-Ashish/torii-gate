"""Commercial scorecard rollup of priority queue surfaces 1–6."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "commercial_scorecard.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT)},
        timeout=300,
    )


class CommercialScorecardTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["all_surfaces_pass"])
        self.assertTrue(data.get("post_queue_complete"), data)
        self.assertGreaterEqual(float(data["overall_est"]), 7.5)
        self.assertEqual(data["surfaces_pass"], data["surfaces_total"])
        self.assertGreaterEqual(int(data["surfaces_total"]), 9)

    def test_report_writes(self):
        r = _run(["report", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("commercial_ok"), data)
        self.assertTrue(data.get("post_queue_complete"), data)
        ids = {s.get("id") for s in (data.get("surfaces") or [])}
        for need in ("golden_path", "enterprise", "gate_certificate", "quieter", "tool_use"):
            self.assertIn(need, ids)
        md = ROOT / "docs" / "benchmarks" / "commercial-scorecard.md"
        js = ROOT / "docs" / "benchmarks" / "commercial-scorecard.json"
        self.assertTrue(md.is_file())
        self.assertTrue(js.is_file())
        body = md.read_text(encoding="utf-8")
        self.assertIn("overall_est", body)
        self.assertIn("golden_path", body)
        self.assertIn("public_eval", body)
        self.assertIn("enterprise", body)
        self.assertIn("gate_certificate", body)
        self.assertIn("Post-queue", body)
        self.assertIn("tool_use", body)


if __name__ == "__main__":
    unittest.main()
