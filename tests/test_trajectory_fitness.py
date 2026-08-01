"""Tests for F73 trajectory fitness + eval-trace vault."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "trajectory_fitness.py"
GOOD = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-good-review.md"
WEAK = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-weak-review.md"


class TrajectoryFitnessTests(unittest.TestCase):
    def test_fixture_offline_e2e(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**dict(**__import__("os").environ), "TORII_TRAJECTORY_FITNESS": "1"},
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertGreaterEqual(data["good"]["composite"], 0.55)
        self.assertGreater(data["delta_composite"], 0.15)
        self.assertGreaterEqual(data["good"]["path_evidence"], 0.6)
        self.assertLessEqual(data["weak"]["path_evidence"], 0.45)
        self.assertTrue(data["inject_ok"])

    def test_score_good_has_path_and_procedure(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "score", str(GOOD)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F73")
        self.assertEqual(data["verdict"], "REQUEST_CHANGES")
        self.assertGreaterEqual(data["path_evidence"], 0.6)
        self.assertGreaterEqual(data["procedure"], 0.5)
        self.assertIn(data["level"], ("L1", "L2", "L3"))

    def test_score_weak_low_path(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "score", str(WEAK)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertLess(data["composite"], 0.55)
        self.assertLessEqual(data["path_evidence"], 0.5)

    def test_inject_marker(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = Path(td) / "prompt.md"
            prompt.write_text("# prompt\n", encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "inject", str(prompt)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env={**dict(**__import__("os").environ), "TORII_TRAJECTORY_FITNESS": "1"},
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("<!-- torii-f73-trajectory-fitness -->", text)
            self.assertIn("path_evidence", text)

    def test_archive_updates_index(self):
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "traces"
            out = Path(td) / "out"
            out.mkdir()
            review = out / "review.md"
            review.write_text(GOOD.read_text(encoding="utf-8"), encoding="utf-8")
            env = {
                **dict(**__import__("os").environ),
                "TORII_TRACE_VAULT": "1",
                "TORII_TRACE_VAULT_ROOT": str(vault),
                "TORII_ROOT": str(ROOT),
            }
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "archive",
                    "--out-dir",
                    str(out),
                    "--review",
                    str(review),
                    "--label",
                    "test",
                    "--repo",
                    "torii/test",
                    "--pr",
                    "1",
                    "--model",
                    "test-model",
                    "--force",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertTrue(data["ok"])
            dest = Path(data["path"])
            self.assertTrue((dest / "summary.json").is_file())
            self.assertTrue((dest / "fitness.json").is_file())
            self.assertTrue((dest / "review.md").is_file())
            self.assertTrue((vault / "INDEX.md").is_file())
            idx = (vault / "INDEX.md").read_text(encoding="utf-8")
            self.assertIn("torii/test", idx)
            self.assertIn("Fitness", idx)

    def test_score_with_loop_boosts_tool_use(self):
        loop = {
            "tool_call_turns": 6,
            "model": "test",
            "steps": [{"kind": "assistant_tool_calls"} for _ in range(6)],
        }
        with tempfile.TemporaryDirectory() as td:
            lp = Path(td) / "agent-loop.json"
            lp.write_text(json.dumps(loop), encoding="utf-8")
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "score",
                    str(GOOD),
                    "--loop",
                    str(lp),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertEqual(data["tool_call_turns"], 6)
            self.assertGreaterEqual(data["tool_use"], 0.9)


if __name__ == "__main__":
    unittest.main()
