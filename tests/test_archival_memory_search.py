"""Tests for F98 archival memory search."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "archival_memory_search.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ARCHIVAL_SEARCH": "1"},
    )


class ArchivalMemorySearchTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["hit_tp"])
        self.assertTrue(data["privacy_ok"])
        # F144 multi-hop → archival promote compound
        self.assertTrue(data.get("f144") or data.get("feature_graph") == "F144")
        self.assertTrue(data.get("f144_ok"), data)
        themes = data.get("f144_graph_themes") or []
        self.assertTrue(
            any("pickle" in str(t) or "deserial" in str(t) for t in themes),
            themes,
        )
        # F145 supersede-aware promote (temporal faithfulness)
        self.assertTrue(data.get("f145") or data.get("feature_supersede") == "F145")
        self.assertTrue(data.get("f145_ok"), data)

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(json.loads(r.stdout)["feature"], "F98")

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
            self.assertTrue((dest / "scripts" / "archival_memory_search.py").is_file())


if __name__ == "__main__":
    unittest.main()
