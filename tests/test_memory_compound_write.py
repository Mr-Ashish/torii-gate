"""Tests for F104 integrity-gated memory compound write."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "memory_compound_write.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"
GOOD = ROOT / "docs/benchmarks/fixtures/insecure-demo-good-review.md"
WEAK = ROOT / "docs/benchmarks/fixtures/insecure-demo-weak-review.md"


def _run(args: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    e = {**os.environ, "TORII_ROOT": str(ROOT), "TORII_MEMORY_COMPOUND": "1"}
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
        timeout=120,
    )


class MemoryCompoundWriteTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreaterEqual(data["good_promoted"], 1)
        self.assertTrue(data["poison_ok"])
        self.assertTrue(data["store_clean"])

    def test_compound_good_writes(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "tp-signatures.json"
            out = Path(td) / "out"
            r = _run(
                [
                    "compound",
                    "--review",
                    str(GOOD),
                    "--tp-out",
                    str(dest),
                    "--out-dir",
                    str(out),
                    "--source",
                    "test",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertTrue(data["applied"])
            self.assertGreaterEqual(data["promoted"], 1)
            self.assertTrue(dest.is_file())
            store = json.loads(dest.read_text())
            sigs = store.get("signatures") or []
            self.assertGreaterEqual(len(sigs), 1)
            # no absolute home or secret blobs
            raw = dest.read_text()
            self.assertNotIn("/Users/", raw)
            self.assertTrue((out / "memory-compound.json").is_file())

    def test_plan_weak_low_or_zero(self):
        r = _run(["plan", "--review", str(WEAK)])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        # weak narrative should not produce many path-evidenced candidates
        self.assertLessEqual(data["candidate_count"], 2)

    def test_disabled_skips(self):
        r = _run(
            ["compound", "--review", str(GOOD)],
            env={"TORII_MEMORY_COMPOUND": "0"},
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("skipped"))

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(json.loads(r.stdout)["feature"], "F104")

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
            self.assertTrue((dest / "scripts" / "memory_compound_write.py").is_file())


if __name__ == "__main__":
    unittest.main()
