"""Tests for F103 unified torii_memory CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "torii_memory.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT), "TORII_MEMORY_CLI": "1"},
        timeout=timeout,
    )


class ToriiMemoryCliTests(unittest.TestCase):
    def test_help(self):
        r = _run(["help"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("torii_memory.py", r.stdout)
        self.assertIn("search", r.stdout)

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F103")
        self.assertTrue(data.get("all_present"), data)

    def test_fixture(self):
        r = _run(["fixture"], timeout=360)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["doctor_ok"], data)

    def test_dispatch_graph_fixture(self):
        r = _run(["graph", "--", "status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

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
            self.assertTrue((dest / "scripts" / "torii_memory.py").is_file())


if __name__ == "__main__":
    unittest.main()
