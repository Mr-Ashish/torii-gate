#!/usr/bin/env python3
"""F9: path-anchored inline review comments planner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "post-inline-comments.py"
SHOWCASE = ROOT / "docs" / "showcase" / "e2e-odoo-pr3-opus5-agentic-loop"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    e = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=e,
    )


class PostInlineCommentsTests(unittest.TestCase):
    def test_plan_showcase(self):
        self.assertTrue((SHOWCASE / "review.md").is_file())
        self.assertTrue((SHOWCASE / "pr.diff").is_file())
        r = _run(
            [
                "plan",
                "--review",
                str(SHOWCASE / "review.md"),
                "--diff",
                str(SHOWCASE / "pr.diff"),
                "--severity",
                "critical,high,blocking,medium",
                "--max",
                "6",
            ]
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data["ok"])
        self.assertGreaterEqual(data["count"], 1)
        paths = {c["path"] for c in data["comments"]}
        self.assertTrue(
            any("xml_utils.py" in p for p in paths),
            f"expected xml_utils in {paths}",
        )
        for c in data["comments"]:
            self.assertIn("line", c)
            self.assertGreater(c["line"], 0)
            if c.get("kind") == "suggestion":
                self.assertIn("torii-suggestion", c["body"])
            else:
                self.assertIn("torii-inline", c["body"])

    def test_severity_filter(self):
        r = _run(
            [
                "plan",
                "--review",
                str(SHOWCASE / "review.md"),
                "--diff",
                str(SHOWCASE / "pr.diff"),
                "--severity",
                "critical",
                "--max",
                "10",
            ],
            env={"TORII_INLINE_SUGGESTIONS": "0"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        for c in data["comments"]:
            self.assertEqual(c["severity"], "critical")


    def test_post_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = Path(td) / "payload.json"
            r = _run(
                [
                    "post",
                    "--review",
                    str(SHOWCASE / "review.md"),
                    "--diff",
                    str(SHOWCASE / "pr.diff"),
                    "--repo",
                    "Mr-Ashish/odoo",
                    "--pr",
                    "3",
                    "--commit",
                    "deadbeef",
                    "--force",
                ],
                env={"TORII_INLINE_FIXTURE": str(fixture), "TORII_INLINE_COMMENTS": "1"},
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(fixture.is_file())
            payload = json.loads(fixture.read_text())
            self.assertEqual(payload["event"], "COMMENT")
            self.assertTrue(payload["comments"])
            self.assertEqual(payload["commit_id"], "deadbeef")

    def test_disabled(self):
        r = _run(
            [
                "post",
                "--review",
                str(SHOWCASE / "review.md"),
                "--diff",
                str(SHOWCASE / "pr.diff"),
                "--repo",
                "a/b",
                "--pr",
                "1",
                "--commit",
                "abc",
            ],
            env={"TORII_INLINE_COMMENTS": "0"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("posted"), 0)
        self.assertIn("skipped", data)

    def test_install_lists_script(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text()
        self.assertIn("post-inline-comments.py", text)

    def test_f9b_exact_line_hint(self):
        """path:LINE in File cell pins to that added line when present in diff."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            review = d / "review.md"
            diff = d / "pr.diff"
            review.write_text(
                """## Torii Review — PR #1

**Verdict:** REQUEST CHANGES
**Score:** 40/100

### Blocking
- None

### Key findings

| Severity | File | Issue | Trigger scenario |
|----------|------|-------|------------------|
| critical | `src/a.py:12` | boom | x |

### Security audit
No
""",
                encoding="utf-8",
            )
            # new file lines: 10 context, 11 +, 12 +, 13 +
            diff.write_text(
                """diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -8,3 +10,4 @@
 context
+line eleven
+line twelve
+line thirteen
""",
                encoding="utf-8",
            )
            r = _run(
                [
                    "plan",
                    "--review",
                    str(review),
                    "--diff",
                    str(diff),
                    "--severity",
                    "all",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data["count"], 1)
            c = data["comments"][0]
            self.assertEqual(c["path"], "src/a.py")
            self.assertEqual(c["line"], 12)
            self.assertEqual(c["anchor"], "exact")
            self.assertEqual(c["line_hint"], 12)

    def test_f9b_nearest_when_hint_not_added(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            review = d / "review.md"
            diff = d / "pr.diff"
            review.write_text(
                """### Key findings

| Severity | File | Issue | Trigger scenario |
|----------|------|-------|------------------|
| high | `src/b.py:20` | near miss | y |
""",
                encoding="utf-8",
            )
            diff.write_text(
                """diff --git a/src/b.py b/src/b.py
--- a/src/b.py
+++ b/src/b.py
@@ -1,1 +10,3 @@
 context
+add10
+add11
""",
                encoding="utf-8",
            )
            r = _run(
                ["plan", "--review", str(review), "--diff", str(diff), "--severity", "*"]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            c = json.loads(r.stdout)["comments"][0]
            # hunk starts +10 with 1 context then 2 adds → added lines {11,12};
            # nearest to hint 20 is 12
            self.assertEqual(c["line"], 12)
            self.assertEqual(c["anchor"], "nearest")
            self.assertEqual(c["line_hint"], 20)

    def test_f9c_showcase_suggestions(self):
        r = _run(
            [
                "plan",
                "--review",
                str(SHOWCASE / "review.md"),
                "--diff",
                str(SHOWCASE / "pr.diff"),
                "--severity",
                "all",
                "--max",
                "6",
            ],
            env={"TORII_INLINE_SUGGESTIONS": "1", "TORII_SUGGESTION_MAX": "3"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertGreaterEqual(data.get("suggestions") or 0, 1)
        sugs = [c for c in data["comments"] if c.get("kind") == "suggestion"]
        self.assertTrue(sugs)
        for c in sugs:
            self.assertIn("```suggestion", c["body"])
            self.assertIn("torii-suggestion", c["body"])
            self.assertIn(c["anchor"], ("exact_minus", "exact_minus_1", "first"))
        # multi-line for xml_utils surrogatepass block
        multi = [c for c in sugs if c.get("start_line") and c["start_line"] != c["line"]]
        self.assertTrue(multi, f"expected multi-line suggestion, got {sugs}")

    def test_f9c_synthetic_multiline(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            review = d / "review.md"
            diff = d / "pr.diff"
            review.write_text(
                """### Key findings
None

### Code suggestions

#### Replace foo (`src/c.py`)
```diff
-old_one
-old_two
+new_one
+new_two
+new_three
```
""",
                encoding="utf-8",
            )
            diff.write_text(
                """diff --git a/src/c.py b/src/c.py
--- a/src/c.py
+++ b/src/c.py
@@ -1,1 +10,3 @@
 context
+old_one
+old_two
+old_three
""",
                encoding="utf-8",
            )
            r = _run(
                ["plan", "--review", str(review), "--diff", str(diff), "--severity", "*"],
                env={"TORII_INLINE_SUGGESTIONS": "1"},
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            sugs = [c for c in data["comments"] if c.get("kind") == "suggestion"]
            self.assertEqual(len(sugs), 1)
            c = sugs[0]
            self.assertEqual(c["path"], "src/c.py")
            self.assertEqual(c["start_line"], 11)
            self.assertEqual(c["line"], 12)
            self.assertIn("new_one", c["body"])
            self.assertIn("```suggestion", c["body"])

    def test_f9c_disabled(self):
        r = _run(
            [
                "plan",
                "--review",
                str(SHOWCASE / "review.md"),
                "--diff",
                str(SHOWCASE / "pr.diff"),
                "--severity",
                "all",
            ],
            env={"TORII_INLINE_SUGGESTIONS": "0"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("suggestions") or 0, 0)

    def test_f54_fixit_prompt_on_finding(self):
        """F54: each finding inline body includes a copy-pasteable fix-it agent prompt."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            review = d / "review.md"
            diff = d / "pr.diff"
            review.write_text(
                """### Key findings

| Severity | File | Issue | Trigger scenario |
|----------|------|-------|------------------|
| high | `src/f54.py:11` | missing null check before deref | caller passes None for optional user |
""",
                encoding="utf-8",
            )
            diff.write_text(
                """diff --git a/src/f54.py b/src/f54.py
--- a/src/f54.py
+++ b/src/f54.py
@@ -1,1 +10,2 @@
 context
+user.name.upper()
+return user
""",
                encoding="utf-8",
            )
            r = _run(
                ["plan", "--review", str(review), "--diff", str(diff), "--severity", "all"],
                env={"TORII_FIXIT_PROMPTS": "1", "TORII_INLINE_SUGGESTIONS": "0"},
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertGreaterEqual(data.get("fixit") or 0, 1)
            self.assertTrue(data.get("fixit_enabled"))
            findings = [c for c in data["comments"] if c.get("kind") == "finding"]
            self.assertEqual(len(findings), 1)
            c = findings[0]
            self.assertTrue(c.get("fixit"))
            body = c["body"]
            self.assertIn("torii-fixit", body)
            self.assertIn("Fix-it prompt", body)
            self.assertIn("src/f54.py", body)
            self.assertIn("Acceptance criteria", body)
            self.assertIn("How to fix", body)
            self.assertIn("Verify", body)
            self.assertIn("fix(f54):", body)
            self.assertIn("missing null check", body)
            self.assertIn("caller passes None", body)

    def test_f54_fixit_disabled(self):
        r = _run(
            [
                "plan",
                "--review",
                str(SHOWCASE / "review.md"),
                "--diff",
                str(SHOWCASE / "pr.diff"),
                "--severity",
                "critical,high,blocking",
                "--max",
                "4",
            ],
            env={"TORII_FIXIT_PROMPTS": "0", "TORII_INLINE_SUGGESTIONS": "0"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("fixit") or 0, 0)
        self.assertFalse(data.get("fixit_enabled"))
        for c in data["comments"]:
            if c.get("kind") == "finding":
                self.assertFalse(c.get("fixit"))
                self.assertNotIn("torii-fixit", c["body"])

    def test_f54_showcase_fixit_default_on(self):
        r = _run(
            [
                "plan",
                "--review",
                str(SHOWCASE / "review.md"),
                "--diff",
                str(SHOWCASE / "pr.diff"),
                "--severity",
                "critical,high,blocking,medium",
                "--max",
                "6",
            ],
            env={"TORII_INLINE_SUGGESTIONS": "0"},  # fixit default on
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertGreaterEqual(data.get("fixit") or 0, 1)
        findings = [c for c in data["comments"] if c.get("kind") == "finding"]
        self.assertTrue(any("torii-fixit" in c["body"] for c in findings))


if __name__ == "__main__":
    unittest.main()

