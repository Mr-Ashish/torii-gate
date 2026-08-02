"""Tests for design-partner / pilot surface + proof packet."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pilot_surface.py"
PROOF = ROOT / "docs" / "PILOT-PROOF.md"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT)},
        timeout=180,
    )


class PilotSurfaceTests(unittest.TestCase):
    def test_fixture_and_packet(self):
        self.assertTrue(SCRIPT.is_file())
        r = _run(["packet"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("packet_ok"))
        self.assertTrue(PROOF.is_file())
        body = PROOF.read_text(encoding="utf-8")
        self.assertIn("0 paid", body.lower())
        self.assertIn("torii/gate", body)
        self.assertIn("time-to-signal", body.lower())

        f = _run(["fixture"])
        self.assertEqual(f.returncode, 0, f.stderr + f.stdout)
        fd = json.loads(f.stdout)
        self.assertTrue(fd.get("fixture_pass"), fd)
        self.assertTrue(fd.get("checks", {}).get("proof_packet_md"))
        self.assertTrue(fd.get("checks", {}).get("gtm_links_proof"))

    def test_status_proof_flag(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("proof_packet_ok"))
        self.assertEqual(data.get("feature"), "PILOT")


if __name__ == "__main__":
    unittest.main()
