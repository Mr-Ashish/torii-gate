"""Offline smoke-torii-gate.sh must stay green for product MVP."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts" / "smoke-torii-gate.sh"


class SmokeToriiGateTests(unittest.TestCase):
    def test_smoke_script_passes(self):
        self.assertTrue(SMOKE.is_file(), f"missing {SMOKE}")
        r = subprocess.run(
            ["bash", str(SMOKE)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            r.returncode,
            0,
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}",
        )
        self.assertIn("SMOKE PASSED", r.stderr + r.stdout)
