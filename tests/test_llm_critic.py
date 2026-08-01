"""Tests for F81 optional LLM critic."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "llm_critic.py"
WEAK = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-weak-review.md"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {**os.environ, "TORII_LLM_CRITIC": "1", "TORII_LLM_CRITIC_MOCK": "1"}
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class LlmCriticTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["privacy_ok"])

    def test_mock_run_weak_endorses_demote(self):
        r = _run(["run", "--review", str(WEAK), "--mock", "--force"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("ok"))
        res = data.get("result") or {}
        self.assertTrue(res.get("endorse_demote") or res.get("recommended_verdict") != "APPROVE")

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F81")

    def test_redact_in_messages(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from llm_critic import build_messages

        msgs = build_messages(
            "key sk-or-v1-deadbeefcafebabe /Users/ashish/secret app",
            None,
        )
        blob = json.dumps(msgs)
        self.assertNotIn("deadbeef", blob)
        self.assertNotIn("/Users/ashish", blob)


if __name__ == "__main__":
    unittest.main()
