"""Tests for F86 dual-rollout skill contribution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_dual_rollout.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_SKILL_DUAL_ROLLOUT": "1"},
    )


class SkillDualRolloutTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreater(data["skill_contribution_pp"], 0)
        self.assertTrue(data["multi_ok"])
        self.assertTrue(data["single_blocked"])

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F86")

    def test_dual_insecure_demo(self):
        r = _run(["dual"])
        # dual may return 0 on pass; accept 0
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["dual_pass"], data)
        self.assertGreater(data["with_skills"]["hit_rate"], data["ablated"]["hit_rate"])

    def test_f115_tool_contribution(self):
        """F115: with-skills tool blob beats ablated tools on tool_hit_n."""
        r = _run(["dual"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature_tool"), "F115")
        self.assertTrue(data.get("tool_dual_ok"), data)
        self.assertGreaterEqual(int(data["with_skills"].get("tool_hit_n") or 0), 1)
        self.assertGreaterEqual(float(data.get("tool_contribution_pp") or 0), 0)
        self.assertGreater(
            int(data["with_skills"].get("tool_hit_n") or 0),
            int(data["ablated"].get("tool_hit_n") or 0),
        )

    def test_install_ships(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "target"
            dest.mkdir()
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((dest / "scripts" / "skill_dual_rollout.py").is_file())


if __name__ == "__main__":
    unittest.main()
