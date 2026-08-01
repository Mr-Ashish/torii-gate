"""Tests for F72 full-chain revalidation (maker/checker)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chain_revalidate.py"
CASES = ROOT / "docs" / "benchmarks" / "cases" / "insecure-demo.json"
GOOD = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-good-review.md"
WEAK = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-weak-review.md"
DEMO = ROOT / "demo" / "insecure"


class ChainRevalidateTests(unittest.TestCase):
    def test_fixture_offline_e2e(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertGreaterEqual(data["good"]["full_chain_rate"], 0.5)
        self.assertGreater(data["delta_precision_proxy"], 0.0)
        self.assertEqual(data["good"]["verdict_checker"], "REQUEST_CHANGES")
        self.assertTrue(data["good"]["case_score"]["passed"])
        self.assertTrue(data["inject_ok"])

    def test_revalidate_good_full_chain(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "revalidate",
                str(GOOD),
                "--auto-scan",
                "--json",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["role"], "checker")
        self.assertGreaterEqual(data["counts"]["full_chain"], 1)
        self.assertEqual(data["verdict_checker"], "REQUEST_CHANGES")

    def test_revalidate_weak_low_validation(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "revalidate",
                str(WEAK),
                "--auto-scan",
                "--json",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertLess(data["precision_proxy"], 0.5)
        self.assertNotEqual(data["verdict_checker"], "REQUEST_CHANGES")

    def test_score_good_recall(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "score",
                str(GOOD),
                "--cases",
                str(CASES),
                "--auto-scan",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["passed"])
        self.assertAlmostEqual(data["recall"], 1.0)

    def test_inject_marker(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = Path(td) / "prompt.md"
            prompt.write_text("# prompt\n", encoding="utf-8")
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "inject",
                    "--prompt",
                    str(prompt),
                    "--auto-scan",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("<!-- torii-f72-chain-revalidate -->", text)
            self.assertIn("Maker/Checker", text)

    def test_scorecard_level(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "rep.json"
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "revalidate",
                    str(GOOD),
                    "--auto-scan",
                    "--out",
                    str(out),
                    "--json",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            r2 = subprocess.run(
                [sys.executable, str(SCRIPT), "scorecard", str(out)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            sc = json.loads(r2.stdout)
            self.assertGreaterEqual(sc["pct"], 70)
            self.assertIn(sc["level"], ("L2", "L3"))

    def test_module_import_revalidate(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from chain_revalidate import revalidate, match_hypotheses  # type: ignore

        hyps = match_hypotheses("SQL injection in app.py via f-string execute CWE-89")
        self.assertTrue(any(h["theme"] == "sql_injection" for h in hyps))
        good = GOOD.read_text(encoding="utf-8")
        # without scan still theme_path
        rep = revalidate(good, scan={"candidates": []})
        self.assertGreaterEqual(rep["counts"]["theme_path"] + rep["counts"]["full_chain"], 1)


if __name__ == "__main__":
    unittest.main()
