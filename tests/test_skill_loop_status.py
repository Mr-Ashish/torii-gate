"""Tests for F91 skill compound loop readiness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_loop_status.py"
GATE = ROOT / "scripts" / "torii_gate_status.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"
WF = ROOT / "scripts" / "workflow_as_code.py"


def _run(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT)},
    )


class SkillLoopStatusTests(unittest.TestCase):
    def test_fixture_l3(self):
        r = _run(SCRIPT, ["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertEqual(data["level"], "L3")
        self.assertEqual(data["stages_ok"], data["stages_total"])

    def test_scorecard(self):
        r = _run(SCRIPT, ["scorecard", "--shallow"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F91")
        self.assertIn("route → hit", data.get("loop", ""))

    def test_gate_skill_loop_only(self):
        r = _run(GATE, ["--skill-loop-only"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("available"))
        self.assertTrue(data.get("ready"))

    def test_workflow_scorecard_embeds_skill_loop(self):
        r = _run(WF, ["scorecard"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertIn("skill_loop", data)
        self.assertTrue(data["skill_loop"].get("ready"))

    def test_install_ships(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "t"
            dest.mkdir()
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((dest / "scripts" / "skill_loop_status.py").is_file())


if __name__ == "__main__":
    unittest.main()
