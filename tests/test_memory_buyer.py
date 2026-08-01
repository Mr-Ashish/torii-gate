"""Buyer MEMORY.md surface + memory CLI doctor."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MemoryBuyerTests(unittest.TestCase):
    def test_buyer_doc(self):
        p = ROOT / "docs" / "MEMORY.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("die twice", text.lower())
        self.assertIn("torii/gate", text)
        self.assertIn("path-evidenced", text.lower())
        install = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("MEMORY.md", install)

    def test_memory_doctor_via_torii(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "torii.py"), "memory", "--", "doctor"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_ROOT": str(ROOT)},
            timeout=120,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("doctor_pass"), data)

    def test_memory_loop_fixture(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "memory_loop_status.py"), "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_ROOT": str(ROOT)},
            timeout=120,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("fixture_pass"), data)


if __name__ == "__main__":
    unittest.main()
