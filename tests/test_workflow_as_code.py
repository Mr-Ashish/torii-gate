"""Tests for F79 workflows-as-code."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workflow_as_code.py"
WF = ROOT / "docs" / "workflows" / "torii-gate.workflow.yaml"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ},
    )


class WorkflowAsCodeTests(unittest.TestCase):
    def test_workflow_file_exists(self):
        self.assertTrue(WF.is_file())

    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertEqual(data["level"], "L3")
        self.assertGreaterEqual(data["stages"], 10)
        self.assertGreaterEqual(data["capabilities"], 8)

    def test_validate(self):
        r = _run(["validate"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["valid"])
        self.assertEqual(data["pct"], 100.0)

    def test_plan_phases(self):
        r = _run(["plan"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        phases = data.get("by_phase") or {}
        self.assertIn("maker", phases)
        self.assertIn("checker", phases)
        self.assertIn("pre", phases)

    def test_pack_check(self):
        r = _run(["pack-check"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["install_lists_all"])
        self.assertEqual(data["disk_missing"], [])

    def test_install_guide_contains_gate(self):
        r = _run(["install-guide"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("torii/gate", r.stdout)
        self.assertIn("Maker", r.stdout)
        self.assertIn("F78", r.stdout)


if __name__ == "__main__":
    unittest.main()
