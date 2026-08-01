"""Tests for F97 Letta-style memory tiers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "memory_tiers.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_MEMORY_TIERS": "1"},
    )


class MemoryTiersTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["core_has_path"])
        self.assertTrue(data["noise_not_core"])
        # F147 recon-warm → core
        self.assertTrue(data.get("f147") or data.get("feature_recon_core") == "F147")
        self.assertTrue(data.get("f147_ok"), data)
        self.assertTrue(data.get("recon_warm_core"))
        self.assertIn("pickle-recon", data.get("core_ids") or [])

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        body = json.loads(r.stdout)
        self.assertEqual(body["feature"], "F97")
        self.assertEqual(body.get("feature_recon_core"), "F147")

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
            self.assertTrue((dest / "scripts" / "memory_tiers.py").is_file())

    def test_scoped_recall_applies_tiers(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from scoped_memory_recall import MemoryItem, recall  # type: ignore

        items = [
            MemoryItem(
                id="tp1",
                kind="tp",
                scope="repo",
                theme="sql_injection",
                path_globs=["app.py"],
                hits=2,
                effective_score=0.4,
                raw_id="tp1",
            ),
            MemoryItem(
                id="tp2",
                kind="tp",
                scope="global",
                theme="xss",
                hits=20,
                effective_score=0.1,
                raw_id="tp2",
            ),
        ]
        r = recall(items, ["app.py"], tp_max=8)
        self.assertTrue(r.get("tiers_enabled"), r)
        self.assertIn("tiers", r)
        core_ids = {x.get("raw_id") or x.get("id") for x in (r["tiers"].get("core") or [])}
        self.assertIn("tp1", core_ids)


if __name__ == "__main__":
    unittest.main()
