"""Tests for F94 memory consolidation (importance/merge/decay/evict)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "memory_consolidate.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = {**os.environ, "TORII_MEMORY_CONSOLIDATE": "1"}
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
    )


class MemoryConsolidateTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["merge_ok"])
        self.assertTrue(data["evict_ok"])
        self.assertTrue(data["decay_rank_ok"])

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(json.loads(r.stdout)["feature"], "F94")

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
            self.assertTrue((dest / "scripts" / "memory_consolidate.py").is_file())

    def test_consolidate_items_api(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import memory_consolidate as mc  # type: ignore

        items = [
            {
                "id": "a",
                "theme": "sql_injection",
                "keywords": ["sqli", "sql"],
                "path_globs": ["a.py"],
                "hits": 2,
                "last_seen": "2026-07-31T00:00:00Z",
            },
            {
                "id": "b",
                "theme": "sql_injection",
                "keywords": ["sqli", "execute"],
                "path_globs": ["a.py"],
                "hits": 1,
                "last_seen": "2026-07-30T00:00:00Z",
            },
        ]
        out = mc.consolidate_items(items)
        self.assertLessEqual(len(out), 2)
        # at least one active with scores
        self.assertTrue(any(i.get("importance_score") is not None for i in out))


if __name__ == "__main__":
    unittest.main()
