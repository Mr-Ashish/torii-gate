"""Tests for F82 safe skill auto-adopt."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_auto_adopt.py"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {
        **os.environ,
        "TORII_SKILL_AUTO_ADOPT": "1",
        "TORII_LLM_CRITIC": "0",
        "TORII_SECOND_CRITIC_DEMOTE": "0",
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


class SkillAutoAdoptTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertEqual(data["good_recommend"], "adopt")
        self.assertEqual(data["bad_recommend"], "reject")
        self.assertFalse(data["bad_active"])

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F82")

    def test_candidates_excludes_malicious_name(self):
        r = _run(["candidates"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        ids = data.get("candidates") or data.get("candidate_ids") or []
        # candidates may be list of dicts
        if ids and isinstance(ids[0], dict):
            ids = [c["id"] for c in ids]
        for i in ids:
            self.assertNotIn("malicious", i)


if __name__ == "__main__":
    unittest.main()
