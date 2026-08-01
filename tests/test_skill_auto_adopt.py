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
        # F118 tool-aware product-cli adopt
        self.assertEqual(data.get("feature_tool"), "F118")
        self.assertTrue(data.get("f118_tool_attr_ok"), data)
        self.assertTrue(data.get("f118_free_without_tools"), data)
        self.assertTrue(data.get("f118_prod_active"), data)

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

    def test_gate_includes_f86_dual_contribution(self):
        """F87: auto-adopt regression gates require dual contribution_pp > 0."""
        r = _run(["gate"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("passed"), data)
        names = [g.get("name") for g in data.get("gates") or []]
        self.assertIn("f86_dual_contribution", names)
        dual = next(g for g in data["gates"] if g["name"] == "f86_dual_contribution")
        self.assertTrue(dual.get("dual_pass"))
        self.assertGreater(float(dual.get("skill_contribution_pp") or 0), 0)
        self.assertGreater(float(data.get("dual_contribution_pp") or 0), 0)

    def test_status_f87_flags(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("f87"))
        self.assertTrue(data.get("dual_gate"))

    def test_f113_memory_cli_skill_active(self):
        """F113: dual-gate adopted prefer-memory-cli-early into active/."""
        active = ROOT / "agent" / "skills" / "active" / "skill-prefer-memory-cli-early.md"
        self.assertTrue(active.is_file(), "expected dual-gate adopt of memory-cli skill")
        body = active.read_text(encoding="utf-8")
        self.assertIn("status: adopted", body)
        self.assertIn("torii_memory", body)
        self.assertIn("F113", body)
        # not listed as candidate once active
        r = _run(["candidates"])
        data = json.loads(r.stdout)
        ids = [c["id"] for c in (data.get("candidates") or []) if isinstance(c, dict)]
        self.assertNotIn("skill-prefer-memory-cli-early", ids)

    def test_f118_product_cli_skill_active(self):
        """F118: tool-attr dual-gate adopted prefer-product-cli into active/."""
        active = ROOT / "agent" / "skills" / "active" / "skill-prefer-product-cli.md"
        self.assertTrue(active.is_file(), "expected F118 dual-gate adopt of product-cli skill")
        body = active.read_text(encoding="utf-8")
        self.assertIn("status: adopted", body)
        self.assertIn("torii.py doctor", body)
        self.assertTrue("F118" in body or "F117" in body)
        critic = ROOT / "agent" / "skills" / "active" / "skill-prefer-critic-early.md"
        self.assertTrue(critic.is_file(), "expected F118 adopt of critic-early skill")
        r = _run(["candidates"])
        data = json.loads(r.stdout)
        ids = [c["id"] for c in (data.get("candidates") or []) if isinstance(c, dict)]
        self.assertNotIn("skill-prefer-product-cli", ids)


if __name__ == "__main__":
    unittest.main()
