"""Tests for F96 memory compound loop readiness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "memory_loop_status.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"
STATUS = ROOT / "scripts" / "torii_gate_status.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT)},
    )


class MemoryLoopStatusTests(unittest.TestCase):
    def test_fixture_l3(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertEqual(data["level"], "L3")

    def test_scorecard_shallow(self):
        r = _run(["scorecard", "--shallow"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F96")
        self.assertIn(data["level"], ("L2", "L3"))

    def test_gate_memory_loop_only(self):
        r = subprocess.run(
            [sys.executable, str(STATUS), "--memory-loop-only"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("ready"), data)

    def test_install_ships(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "t"
            dest.mkdir()
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((dest / "scripts" / "memory_loop_status.py").is_file())


if __name__ == "__main__":
    unittest.main()
