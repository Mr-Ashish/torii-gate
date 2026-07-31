"""Tests for F70 bench_security_gate (score, critic, promote, fixture)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bench_security_gate.py"
CASES = ROOT / "docs" / "benchmarks" / "cases" / "insecure-demo.json"
GOOD = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-good-review.md"
WEAK = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-weak-review.md"


class BenchSecurityGateTests(unittest.TestCase):
    def test_cases_pack_present(self):
        self.assertTrue(CASES.is_file())
        pack = json.loads(CASES.read_text(encoding="utf-8"))
        self.assertEqual(pack["id"], "insecure-demo")
        self.assertGreaterEqual(len(pack["cases"]), 4)

    def test_score_good_review_passes(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "score",
                "--review",
                str(GOOD),
                "--cases",
                str(CASES),
                "--json",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["fn"], 0)
        self.assertGreaterEqual(data["tp"], 4)
        self.assertEqual(data["verdict"], "REQUEST_CHANGES")
        self.assertAlmostEqual(data["recall"], 1.0)

    def test_score_weak_review_fails(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "score",
                "--review",
                str(WEAK),
                "--cases",
                str(CASES),
                "--soft",
                "--json",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertFalse(data["passed"])
        self.assertLess(data["recall"], 0.5)
        self.assertEqual(data["verdict"], "APPROVE")

    def test_dual_pass_critic_path_evidence(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "critic",
                "--review",
                str(GOOD),
                "--json",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertGreater(data["chunk_count"], 0)
        self.assertGreaterEqual(data["precision_proxy"], 0.0)

    def test_promote_and_inject(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            score_json = td_path / "score.json"
            # build score via CLI
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "score",
                    "--review",
                    str(GOOD),
                    "--cases",
                    str(CASES),
                    "--out",
                    str(score_json),
                    "--json",
                    "--soft",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            tp_out = td_path / "tp-signatures.json"
            r2 = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "promote",
                    "--score-json",
                    str(score_json),
                    "--cases",
                    str(CASES),
                    "--out",
                    str(tp_out),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertTrue(tp_out.is_file())
            doc = json.loads(tp_out.read_text(encoding="utf-8"))
            self.assertEqual(doc["feature"], "F70")
            self.assertGreaterEqual(doc["count"], 4)
            prompt = td_path / "prompt.md"
            prompt.write_text("# Task\n\nReview me.\n", encoding="utf-8")
            env = os.environ.copy()
            env["TORII_TP_SIGNATURES_FILE"] = str(tp_out)
            r3 = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "inject",
                    "--prompt",
                    str(prompt),
                    "--tp-signatures",
                    str(tp_out),
                ],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r3.returncode, 0, r3.stderr)
            body = prompt.read_text(encoding="utf-8")
            self.assertIn("torii-f70-tp-signatures", body)
            self.assertIn("sqli-search", body)

    def test_fixture_e2e(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bench"
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "fixture",
                    "--out-dir",
                    str(out),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("fixture_pass=1", r.stdout)
            metrics = json.loads((out / "bench-metrics.json").read_text(encoding="utf-8"))
            self.assertTrue(metrics["fixture_pass"])
            self.assertEqual(metrics["good"]["fn"], 0)
            self.assertGreater(metrics["weak"]["fn"], 0)
            self.assertGreater(metrics["delta_recall"], 0.5)
            self.assertTrue((out / "tp-signatures.json").is_file())


if __name__ == "__main__":
    unittest.main()
