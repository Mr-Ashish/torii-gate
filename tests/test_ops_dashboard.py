"""Ops dashboard: fail-closed defaults, cost/PR stub, smoke CI surface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops_dashboard.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT)},
        timeout=120,
    )


class OpsDashboardTests(unittest.TestCase):
    def test_ci_workflow_exists(self):
        wf = ROOT / ".github" / "workflows" / "smoke-offline.yml"
        self.assertTrue(wf.is_file())
        text = wf.read_text(encoding="utf-8")
        self.assertIn("smoke-torii-gate.sh", text)
        self.assertIn("ops_dashboard.py", text)

    def test_reliability_doc(self):
        p = ROOT / "docs" / "ops" / "RELIABILITY.md"
        self.assertTrue(p.is_file())
        t = p.read_text(encoding="utf-8")
        self.assertIn("torii/gate", t)
        self.assertIn("fail-closed", t.lower())

    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertEqual(data["required_context"], "torii/gate")
        self.assertTrue(data["checks"]["smoke_ci"])
        self.assertTrue(data["checks"]["fail_closed_safe"])

    def test_report(self):
        r = _run(["report", "--json", "--allow-partial"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "OPS")
        self.assertIn("fail_closed", data)
        self.assertIn("cost_per_pr", data)
        dash = ROOT / "docs" / "ops" / "DASHBOARD.md"
        cost = ROOT / "docs" / "ops" / "cost-pr-dashboard.md"
        self.assertTrue(dash.is_file())
        self.assertTrue(cost.is_file())
        body = dash.read_text(encoding="utf-8")
        self.assertIn("Fail-closed", body)
        self.assertIn("Cost / PR", body)
        self.assertIn("torii/gate", body)

    def test_tool_turns_default_on(self):
        # Ensure product default remains fail-closed for tool turns
        tt = (ROOT / "scripts" / "tool_turns_gate.py").read_text(encoding="utf-8")
        self.assertIn("TORII_TOOL_TURNS_GATE", tt)
        self.assertRegex(tt, r"1 \(default\)|default\) \| 0")


if __name__ == "__main__":
    unittest.main()
