#!/usr/bin/env python3
"""F37: verdict → PR labels."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply-verdict-labels.py"

import importlib.util

_spec = importlib.util.spec_from_file_location("apply_verdict_labels", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
all_torii_labels = _mod.all_torii_labels
enabled_from_env = _mod.enabled_from_env
label_name = _mod.label_name
plan_labels = _mod.plan_labels
suffix_for_verdict = _mod.suffix_for_verdict


class PlanTests(unittest.TestCase):
    def test_approve(self):
        p = plan_labels("APPROVE", True, prefix="torii")
        self.assertEqual(p["add"], "torii:approve")
        self.assertIn("torii:request-changes", p["remove"])
        self.assertIn("torii:comment", p["remove"])
        self.assertIn("torii:error", p["remove"])
        self.assertEqual(p["suffix"], "approve")

    def test_request_changes(self):
        p = plan_labels("REQUEST_CHANGES", True, prefix="torii")
        self.assertEqual(p["add"], "torii:request-changes")
        self.assertEqual(p["color"], "D93F0B")

    def test_comment(self):
        p = plan_labels("COMMENT", True)
        self.assertEqual(p["add"], "torii:comment")

    def test_pipeline_fail_forces_error(self):
        p = plan_labels("APPROVE", False, prefix="torii")
        self.assertEqual(p["add"], "torii:error")
        self.assertEqual(p["suffix"], "error")

    def test_unknown_is_error(self):
        self.assertEqual(suffix_for_verdict("UNKNOWN", True), "error")
        self.assertEqual(suffix_for_verdict("WEIRD", True), "error")

    def test_custom_prefix(self):
        p = plan_labels("APPROVE", True, prefix="bot")
        self.assertEqual(p["add"], "bot:approve")
        self.assertEqual(all_torii_labels("bot"), [
            "bot:approve",
            "bot:request-changes",
            "bot:comment",
            "bot:error",
        ])

    def test_label_name(self):
        self.assertEqual(label_name("approve", "torii"), "torii:approve")


class EnvTests(unittest.TestCase):
    def test_enabled_default(self):
        old = os.environ.get("TORII_PR_LABELS")
        try:
            os.environ.pop("TORII_PR_LABELS", None)
            self.assertTrue(enabled_from_env())
            os.environ["TORII_PR_LABELS"] = "0"
            self.assertFalse(enabled_from_env())
            os.environ["TORII_PR_LABELS"] = "off"
            self.assertFalse(enabled_from_env())
        finally:
            if old is None:
                os.environ.pop("TORII_PR_LABELS", None)
            else:
                os.environ["TORII_PR_LABELS"] = old


class CliTests(unittest.TestCase):
    def _run(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        e = {**os.environ, **(env or {})}
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=e,
        )

    def test_plan_json(self):
        cp = self._run("plan", "--verdict", "REQUEST_CHANGES", "--pipeline-ok", "true")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["add"], "torii:request-changes")

    def test_apply_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            fix = Path(td) / "labels.json"
            cp = self._run(
                "apply",
                "--repo",
                "o/r",
                "--pr",
                "3",
                "--verdict",
                "COMMENT",
                "--pipeline-ok",
                "true",
                env={"TORII_LABELS_FIXTURE": str(fix)},
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            data = json.loads(cp.stdout)
            self.assertTrue(data.get("posted"))
            self.assertTrue(fix.is_file())
            plan = json.loads(fix.read_text())
            self.assertEqual(plan["add"], "torii:comment")

    def test_apply_disabled(self):
        cp = self._run(
            "apply",
            "--repo",
            "o/r",
            "--pr",
            "1",
            "--verdict",
            "APPROVE",
            env={"TORII_PR_LABELS": "0"},
        )
        self.assertEqual(cp.returncode, 0)
        data = json.loads(cp.stdout)
        self.assertEqual(data.get("skipped"), "disabled")


class WiringTests(unittest.TestCase):
    def test_report_verdict_wires_f37(self):
        text = (ROOT / "scripts" / "report-verdict.sh").read_text()
        self.assertIn("apply-verdict-labels.py", text)
        self.assertIn("F37", text)
        self.assertIn("TORII_PR_LABELS", text)

    def test_install_allowlist(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text()
        self.assertIn("apply-verdict-labels.py", text)

    def test_workflow_exports_var(self):
        text = (ROOT / ".github" / "workflows" / "torii-review-reusable.yml").read_text()
        self.assertIn("TORII_PR_LABELS", text)


if __name__ == "__main__":
    unittest.main()
