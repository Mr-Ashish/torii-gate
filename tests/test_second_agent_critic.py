"""Tests for F78 multi-checker second-agent critic."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "second_agent_critic.py"
GOOD = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-good-review.md"
WEAK = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-weak-review.md"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {
        **os.environ,
        "TORII_SECOND_CRITIC": "1",
        "TORII_SECOND_CRITIC_DEMOTE": "0",  # never rewrite fixtures
        "TORII_LLM_CRITIC": "0",  # F81 off in unit tests unless mock
        "TORII_LLM_CRITIC_MOCK": "1",
    }
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class SecondAgentCriticTests(unittest.TestCase):
    def test_fixture_offline(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreater(data["delta"], 0.1)
        self.assertTrue(data["inject_ok"])

    def test_good_higher_than_weak(self):
        rg = _run(["run", "--review", str(GOOD), "--force"])
        rw = _run(["run", "--review", str(WEAK), "--force"])
        self.assertEqual(rg.returncode, 0, rg.stderr + rg.stdout)
        self.assertEqual(rw.returncode, 0, rw.stderr + rw.stdout)
        g = json.loads(rg.stdout)
        w = json.loads(rw.stdout)
        self.assertGreater(
            float(g["panel"]["composite"]),
            float(w["panel"]["composite"]),
        )
        # weak APPROVE should recommend demote
        self.assertEqual(w["maker_verdict"], "APPROVE")
        self.assertTrue(w["decision"]["demoted"] or w["decision"]["recommended_verdict"] != "APPROVE")

    def test_inject_marker(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = Path(td) / "prompt.md"
            prompt.write_text("# p\n", encoding="utf-8")
            r = _run(["inject", "--prompt", str(prompt)])
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            body = prompt.read_text(encoding="utf-8")
            self.assertIn("<!-- torii-f78-second-agent-critic -->", body)
            self.assertIn("maker", body.lower())

    def test_demote_rewrites_copy_not_source(self):
        with tempfile.TemporaryDirectory() as td:
            review = Path(td) / "review.md"
            review.write_text(WEAK.read_text(encoding="utf-8"), encoding="utf-8")
            r = _run(
                ["run", "--review", str(review), "--demote", "--force"],
                env={"TORII_SECOND_CRITIC_DEMOTE": "1"},
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            if data["decision"]["demoted"]:
                body = review.read_text(encoding="utf-8")
                self.assertIn("torii-f78-demote", body)
                self.assertNotIn("**Verdict:** APPROVE", body)
            # source fixture unchanged
            self.assertIn("APPROVE", WEAK.read_text(encoding="utf-8"))

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F78")
        self.assertTrue(data["enabled"])


if __name__ == "__main__":
    unittest.main()
