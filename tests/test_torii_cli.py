"""Tests for F110 unified product CLI front door."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "torii.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT), "TORII_CLI": "1"},
        timeout=timeout,
    )


class ToriiProductCliTests(unittest.TestCase):
    def test_help(self):
        r = _run(["help"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("torii.py", r.stdout)
        self.assertIn("memory", r.stdout)

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F110")
        self.assertTrue(data.get("all_present"), data)

    def test_fixture(self):
        r = _run(["fixture"], timeout=240)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)

    def test_dispatch_memory_help(self):
        r = _run(["memory", "--", "help"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("torii_memory", r.stdout.lower() + r.stderr.lower() or r.stdout)

    def test_budget_status(self):
        r = _run(["budget", "--", "status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("F108", r.stdout)

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
            self.assertTrue((dest / "scripts" / "torii.py").is_file())


    def test_doctor_recovery_ok(self):
        """F124/F128: doctor requires recovery_ok + recovery_hub_gap_ok."""
        r = _run(["doctor"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("doctor_pass"), data)
        self.assertTrue(data.get("recovery_ok"), data)
        self.assertTrue(data.get("recovery_hub_gap_ok"), data)
        self.assertEqual(data.get("feature_recovery"), "F128")
        self.assertIn("skill-prefer-product-cli", data.get("recovery_active") or [])

    def test_f129_product_scorecard(self):
        """F129–F131: scorecard packages doctor + demote + util + workflow dual compound."""
        with tempfile.TemporaryDirectory() as td:
            r = _run(["scorecard", "--out-dir", td], timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertEqual(data.get("feature"), "F131")
            self.assertTrue(data.get("brand_ready"), data)
            m = data.get("metrics") or {}
            self.assertTrue(m.get("doctor_pass"), m)
            self.assertTrue(m.get("recovery_hub_gap_ok"), m)
            self.assertIsNotNone(m.get("critic_approve_demote_rate"), m)
            self.assertTrue(m.get("demote_eval_pass"), m)
            self.assertTrue(m.get("memory_util_eval_pass"), m)
            self.assertGreaterEqual(float(m.get("memory_tool_util_delta") or 0), 0.4)
            self.assertTrue(m.get("workflow_ok"), m)
            self.assertEqual(m.get("workflow_level"), "L3")
            dc = data.get("dual_compound") or {}
            self.assertTrue(dc.get("triple_ready"), dc)
            art = Path(td) / "product-scorecard.json"
            self.assertTrue(art.is_file())
            mu = Path(td) / "memory-util-eval.json"
            self.assertTrue(mu.is_file())
            brand = ROOT / "docs" / "brand" / "scorecard-metrics.md"
            self.assertTrue(brand.is_file())
            body = brand.read_text(encoding="utf-8")
            self.assertIn("critic_approve_demote_rate", body)
            self.assertIn("memory_tool_util_delta", body)
            self.assertIn("workflow_level", body)
            self.assertNotIn("/Users/", body)

    def test_workflow_group(self):
        """F131: torii.py workflow -- scorecard reachable."""
        r = _run(["workflow", "--", "scorecard"], timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "F79")
        self.assertEqual(data.get("feature_dual"), "F131")
        self.assertTrue(data.get("valid"), data)
        self.assertTrue((data.get("dual_compound") or {}).get("triple_ready"), data)


if __name__ == "__main__":
    unittest.main()
