"""Public labeled eval: Juice Shop + 2 OSS-theme packs, seed, scorecard."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "public_eval.py"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = {**os.environ, "TORII_ROOT": str(ROOT), "TORII_PUBLIC_EVAL_SEED": "42"}
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
        timeout=180,
    )


class PublicEvalTests(unittest.TestCase):
    def test_packs_exist(self):
        for pid in (
            "juice-shop-synthetic",
            "nodegoat-synthetic",
            "django-vuln-synthetic",
        ):
            self.assertTrue((ROOT / "docs" / "benchmarks" / "cases" / f"{pid}.json").is_file())
            self.assertTrue(
                (ROOT / "docs" / "benchmarks" / "fixtures" / f"{pid}-good-review.md").is_file()
            )
            self.assertTrue(
                (ROOT / "docs" / "benchmarks" / "fixtures" / f"{pid}-weak-review.md").is_file()
            )

    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertEqual(data["seed"], 42)
        self.assertEqual(data["scorecard_target"], "8.5")
        for pid in data["required_packs"]:
            self.assertIn(pid, data["catalog_ids"])

    def test_report(self):
        r = _run(["report", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("public_eval_ok"), data)
        self.assertEqual(data.get("seed"), 42)
        self.assertIn("model_id", data)
        self.assertGreaterEqual((data.get("fp_tp") or {}).get("labeled_tp_cases") or 0, 13)
        md = ROOT / "docs" / "benchmarks" / "public-eval" / "SCORECARD.md"
        js = ROOT / "docs" / "benchmarks" / "public-eval" / "scorecard.json"
        self.assertTrue(md.is_file())
        self.assertTrue(js.is_file())
        body = md.read_text(encoding="utf-8")
        self.assertIn("seed", body.lower())
        self.assertIn("nodegoat-synthetic", body)
        self.assertIn("django-vuln-synthetic", body)
        self.assertIn("Cost / PR", body)

    def test_corpus_four_packs(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "bench_corpus.py"), "list"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_ROOT": str(ROOT)},
            timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        ids = {p["id"] for p in data.get("packs") or []}
        self.assertIn("nodegoat-synthetic", ids)
        self.assertIn("django-vuln-synthetic", ids)
        self.assertTrue(all(p.get("paths_ok") for p in data["packs"]))


if __name__ == "__main__":
    unittest.main()
