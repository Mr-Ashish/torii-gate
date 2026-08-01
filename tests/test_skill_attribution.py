"""Tests for F88 per-skill contribution attribution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_attribution.py"
ADOPT = ROOT / "scripts" / "skill_auto_adopt.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(script: Path, args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {**os.environ, "TORII_SKILL_ATTRIBUTION": "1", "TORII_SKILL_AUTO_ADOPT_ATTR": "1"}
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class SkillAttributionTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(SCRIPT, ["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreaterEqual(data["n_contributing"], 1)
        self.assertTrue(data["proposal_free_rider"]["free_rider"])
        self.assertGreater(data["proposal_good"]["contribution"], 0)

    def test_status(self):
        r = _run(SCRIPT, ["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(json.loads(r.stdout)["feature"], "F88")

    def test_gate_includes_f88(self):
        r = _run(ADOPT, ["gate"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        names = [g["name"] for g in data.get("gates") or []]
        self.assertIn("f88_skill_attribution", names)
        self.assertTrue(data.get("passed"))

    def test_install_ships(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "t"
            dest.mkdir()
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((dest / "scripts" / "skill_attribution.py").is_file())


if __name__ == "__main__":
    unittest.main()
