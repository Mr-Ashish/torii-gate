"""Tests for F76 multi-corpus security bench (Juice Shop synthetic + insecure-demo)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bench_corpus.py"
CASES = ROOT / "docs" / "benchmarks" / "cases" / "juice-shop-synthetic.json"
GOOD = ROOT / "docs" / "benchmarks" / "fixtures" / "juice-shop-synthetic-good-review.md"
WEAK = ROOT / "docs" / "benchmarks" / "fixtures" / "juice-shop-synthetic-weak-review.md"
DEMO = ROOT / "demo" / "juice-shop-synthetic"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_BENCH_CORPUS": "1"},
    )


class BenchCorpusTests(unittest.TestCase):
    def test_artifacts_exist(self):
        self.assertTrue(CASES.is_file())
        self.assertTrue(GOOD.is_file())
        self.assertTrue(WEAK.is_file())
        self.assertTrue((DEMO / "routes.js").is_file())
        pack = json.loads(CASES.read_text(encoding="utf-8"))
        self.assertEqual(pack["id"], "juice-shop-synthetic")
        self.assertGreaterEqual(len(pack["cases"]), 5)

    def test_list_paths_ok(self):
        r = _run(["list"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F76")
        ids = {p["id"] for p in data["packs"]}
        self.assertIn("insecure-demo", ids)
        self.assertIn("juice-shop-synthetic", ids)
        self.assertTrue(all(p["paths_ok"] for p in data["packs"]))

    def test_fixture_juice_shop(self):
        r = _run(["fixture", "--pack", "juice-shop-synthetic"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertEqual(data["good_recall"], 1.0)
        self.assertEqual(data["weak_recall"], 0.0)

    def test_all_packs(self):
        r = _run(["all"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["all_pass"])
        self.assertEqual(data["packs_total"], 2)
        self.assertEqual(data["packs_passed"], 2)
        self.assertGreaterEqual(data.get("avg_delta_recall") or 0, 0.9)

    def test_taint_juice_shop(self):
        r = _run(["taint", "--pack", "juice-shop-synthetic"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["taint_ok"])
        juice = data["results"][0]
        self.assertGreaterEqual(int(juice.get("candidate_count") or 0), 2)


if __name__ == "__main__":
    unittest.main()
