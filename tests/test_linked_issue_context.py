#!/usr/bin/env python3
"""F53: linked issue context extraction + assemble (fixture, no network)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "linked_issue_context.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("linked_issue_context", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class ExtractRefs(unittest.TestCase):
    def test_fixes_hash(self):
        refs = _mod.extract_issue_refs(
            title="Crash on save",
            body="Fixes #42\n\nAlso see docs.",
            repo="acme/widgets",
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["number"], 42)
        self.assertEqual(refs[0]["repo"], "acme/widgets")
        self.assertTrue(refs[0]["closing"])

    def test_closes_cross_and_url(self):
        body = (
            "Closes other/lib#7\n"
            "Related: https://github.com/acme/widgets/issues/99\n"
        )
        refs = _mod.extract_issue_refs(title="", body=body, repo="acme/widgets", max_issues=5)
        keys = {r["key"] for r in refs}
        self.assertIn("other/lib#7", keys)
        self.assertIn("acme/widgets#99", keys)
        closing = [r for r in refs if r["key"] == "other/lib#7"][0]
        self.assertTrue(closing["closing"])

    def test_bare_hash_same_repo(self):
        refs = _mod.extract_issue_refs(
            title="Part of #12",
            body="Tracking #12 and #12 again",
            repo="acme/widgets",
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["key"], "acme/widgets#12")

    def test_branch_extract(self):
        refs = _mod.extract_issue_refs(
            title="wip",
            body="",
            repo="acme/widgets",
            head_ref="feature/88-fix-null",
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["number"], 88)
        self.assertEqual(refs[0]["source"], "branch")

    def test_branch_disabled(self):
        os.environ["TORII_ISSUE_FROM_BRANCH"] = "0"
        try:
            refs = _mod.extract_issue_refs(
                title="wip",
                body="",
                repo="acme/widgets",
                head_ref="feature/88-fix-null",
            )
            self.assertEqual(refs, [])
        finally:
            os.environ.pop("TORII_ISSUE_FROM_BRANCH", None)

    def test_cap_prefers_closing(self):
        body = "See #1 #2 #3\nFixes #9"
        refs = _mod.extract_issue_refs(
            title="", body=body, repo="acme/widgets", max_issues=2
        )
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0]["number"], 9)
        self.assertTrue(refs[0]["closing"])

    def test_max_zero(self):
        refs = _mod.extract_issue_refs(
            title="Fixes #1", body="", repo="acme/widgets", max_issues=0
        )
        self.assertEqual(refs, [])


class FormatAndAssemble(unittest.TestCase):
    def test_format_section_includes_body_and_comments(self):
        issues = [
            {
                "_repo": "acme/widgets",
                "number": 42,
                "title": "Null deref on save",
                "state": "OPEN",
                "url": "https://github.com/acme/widgets/issues/42",
                "author": {"login": "alice"},
                "labels": [{"name": "bug"}],
                "body": "When name is empty, save crashes.",
                "comments": [
                    {"author": {"login": "bob"}, "body": "Repro: blank name + save."},
                ],
                "_closing": True,
                "_source": "closing_hash",
            }
        ]
        md = _mod.format_issue_section(issues)
        self.assertIn("acme/widgets#42", md)
        self.assertIn("Null deref on save", md)
        self.assertIn("blank name", md)
        self.assertIn("@bob", md)
        self.assertIn("UNTRUSTED", md)

    def test_assemble_fixture_writes_env_and_md(self):
        fixture = [
            {
                "repo": "acme/widgets",
                "number": 42,
                "title": "Null deref",
                "state": "OPEN",
                "body": "Crash when empty.",
                "comments": [],
            }
        ]
        pr = {
            "title": "Guard empty name",
            "body": "Fixes #42",
            "headRefName": "fix/empty-name",
        }
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            fix = tdp / "issues.json"
            fix.write_text(json.dumps(fixture), encoding="utf-8")
            os.environ["TORII_ISSUE_CONTEXT_FIXTURE"] = str(fix)
            os.environ["TORII_ISSUE_CONTEXT"] = "1"
            try:
                fields = _mod.assemble_from_pr_json(
                    pr, repo="acme/widgets", out_dir=tdp
                )
                self.assertEqual(fields["enabled"], "1")
                self.assertEqual(fields["fetched"], "1")
                self.assertIn("acme/widgets#42", fields["refs"])
                md = (tdp / "linked-issues.md").read_text(encoding="utf-8")
                self.assertIn("Null deref", md)
                self.assertIn("Crash when empty", md)
                env = (tdp / "linked-issue-context.env").read_text(encoding="utf-8")
                self.assertIn("fetched=", env)
            finally:
                os.environ.pop("TORII_ISSUE_CONTEXT_FIXTURE", None)
                os.environ.pop("TORII_ISSUE_CONTEXT", None)

    def test_assemble_disabled(self):
        pr = {"title": "Fixes #1", "body": "x", "headRefName": "main"}
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            os.environ["TORII_ISSUE_CONTEXT"] = "0"
            try:
                fields = _mod.assemble_from_pr_json(
                    pr, repo="acme/widgets", out_dir=tdp
                )
                self.assertEqual(fields["enabled"], "0")
                self.assertEqual(fields["reason"], "disabled")
                md = (tdp / "linked-issues.md").read_text(encoding="utf-8")
                self.assertIn("None linked", md)
            finally:
                os.environ.pop("TORII_ISSUE_CONTEXT", None)

    def test_assemble_no_refs(self):
        pr = {"title": "docs only", "body": "no issues here", "headRefName": "docs"}
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            os.environ["TORII_ISSUE_CONTEXT"] = "1"
            os.environ["TORII_ISSUE_FROM_BRANCH"] = "0"
            try:
                fields = _mod.assemble_from_pr_json(
                    pr, repo="acme/widgets", out_dir=tdp
                )
                self.assertEqual(fields["count"], "0")
                self.assertEqual(fields["reason"], "no_refs")
            finally:
                os.environ.pop("TORII_ISSUE_CONTEXT", None)
                os.environ.pop("TORII_ISSUE_FROM_BRANCH", None)

    def test_cli_extract(self):
        rc = _mod.main(
            [
                "extract",
                "--repo",
                "acme/widgets",
                "--title",
                "x",
                "--body",
                "Fixes #3",
            ]
        )
        self.assertEqual(rc, 0)


class PromptWiring(unittest.TestCase):
    def test_prompt_has_linked_issues_placeholder(self):
        text = (ROOT / "agent" / "review-prompt.md").read_text(encoding="utf-8")
        self.assertIn("{{LINKED_ISSUES}}", text)
        self.assertIn("F53", text)

    def test_assemble_script_calls_linked_issue(self):
        text = (ROOT / "scripts" / "assemble-context.sh").read_text(encoding="utf-8")
        self.assertIn("linked_issue_context.py", text)
        self.assertIn("LINKED_ISSUES", text)

    def test_soul_mentions_linked_issues(self):
        text = (ROOT / "agent" / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("Linked issues (F53)", text)


if __name__ == "__main__":
    unittest.main()
