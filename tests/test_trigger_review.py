#!/usr/bin/env python3
"""F32: trigger-review.sh print/local validation + Modal enqueue payload parse."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "trigger-review.sh"


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        **kw,
    )


class TriggerReviewShTests(unittest.TestCase):
    def test_help(self):
        r = _run(["help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("print", r.stdout)
        self.assertIn("modal", r.stdout)

    def test_print_commands(self):
        r = _run(["print", "Mr-Ashish/odoo", "3"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("review-local.sh Mr-Ashish/odoo 3", r.stdout)
        self.assertIn("modal run modal_app/app.py --bit 3", r.stdout)
        self.assertIn("--repo Mr-Ashish/odoo", r.stdout)
        self.assertIn("--pr 3", r.stdout)
        self.assertIn("--bit 4", r.stdout)

    def test_print_with_model_and_post(self):
        r = _run(
            [
                "print",
                "acme/x",
                "9",
                "--model",
                "openai/gpt-4.1-mini",
                "--post",
            ]
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("TORII_MODEL=openai/gpt-4.1-mini", r.stdout)
        self.assertIn("POST_COMMENT=1", r.stdout)
        self.assertIn("--model openai/gpt-4.1-mini", r.stdout)

    def test_bad_repo(self):
        r = _run(["print", "noneslash", "1"])
        self.assertNotEqual(r.returncode, 0)

    def test_bad_pr(self):
        r = _run(["print", "a/b", "x"])
        self.assertNotEqual(r.returncode, 0)

    def test_install_includes_trigger(self):
        install = ROOT / "scripts" / "install-torii.sh"
        text = install.read_text()
        self.assertIn("trigger-review.sh", text)


class ModalEnqueueParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            # Import may require `modal` package
            sys.path.insert(0, str(ROOT))
            from modal_app.app import parse_enqueue_payload, plan_enqueue  # noqa: WPS433

            cls.parse = staticmethod(parse_enqueue_payload)
            cls.plan = staticmethod(plan_enqueue)
            cls.ok = True
        except Exception as e:  # noqa: BLE001
            cls.ok = False
            cls.err = e

    def test_simple_api(self):
        if not self.ok:
            self.skipTest(f"modal_app import failed: {self.err}")
        p = self.parse(
            {"repo": "Mr-Ashish/odoo", "pr": 3, "model": "openai/gpt-4.1-mini"}
        )
        self.assertTrue(p["ok"])
        self.assertEqual(p["repo"], "Mr-Ashish/odoo")
        self.assertEqual(p["pr_number"], 3)
        self.assertEqual(p["source"], "api")

    def test_github_trigger(self):
        if not self.ok:
            self.skipTest(f"modal_app import failed: {self.err}")
        p = self.parse(
            {
                "action": "created",
                "issue": {"number": 7, "pull_request": {"url": "https://x"}},
                "comment": {"id": 99, "body": "hey @torii please review this"},
                "repository": {"full_name": "acme/r"},
            }
        )
        self.assertTrue(p["ok"])
        self.assertEqual(p["pr_number"], 7)
        self.assertEqual(p["source"], "github")

    def test_github_skip_non_trigger(self):
        if not self.ok:
            self.skipTest(f"modal_app import failed: {self.err}")
        p = self.parse(
            {
                "action": "created",
                "issue": {"number": 7, "pull_request": {"url": "https://x"}},
                "comment": {"body": "lgtm"},
                "repository": {"full_name": "acme/r"},
            }
        )
        self.assertFalse(p["ok"])
        self.assertTrue(p.get("skipped"))

    def test_plan_enqueue_dry(self):
        if not self.ok:
            self.skipTest(f"modal_app import failed: {self.err}")
        p = self.plan("a/b", 1, model="openai/gpt-4.1-mini", post_comment=False)
        self.assertTrue(p["ok"])
        self.assertTrue(p["dry_run"])
        self.assertFalse(p["spawned"])
        self.assertEqual(p["bit"], 4)


if __name__ == "__main__":
    unittest.main()
