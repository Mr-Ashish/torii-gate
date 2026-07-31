#!/usr/bin/env python3
"""F60: reply on thread control plane."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reply_on_thread.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("reply_on_thread", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["reply_on_thread"] = _mod
_spec.loader.exec_module(_mod)


class Markers(unittest.TestCase):
    def test_is_torii_inline(self):
        self.assertTrue(_mod.is_torii_inline_body("x\n\n<!-- torii-inline -->\n"))
        self.assertFalse(_mod.is_torii_inline_body("ordinary review comment"))

    def test_index_roots(self):
        existing = [
            {
                "id": 10,
                "path": "pkg/foo.go",
                "line": 42,
                "body": "**HIGH** — bug\n\n<!-- torii-inline -->",
            },
            {
                "id": 11,
                "path": "pkg/foo.go",
                "line": 42,
                "in_reply_to_id": 10,
                "body": "human reply",
            },
            {
                "id": 12,
                "path": "other.go",
                "line": 1,
                "body": "not torii",
            },
        ]
        roots = _mod.index_torii_roots(existing)
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["id"], 10)


class Match(unittest.TestCase):
    def setUp(self):
        os.environ["TORII_REPLY_ON_THREAD"] = "1"

    def tearDown(self):
        os.environ.pop("TORII_REPLY_ON_THREAD", None)
        os.environ.pop("TORII_REPLY_MATCH", None)

    def test_path_line_exact(self):
        roots = [
            {"id": 1, "path": "a.go", "line": 10, "is_torii": True, "is_root": True, "body": ""},
            {"id": 2, "path": "a.go", "line": 20, "is_torii": True, "is_root": True, "body": ""},
        ]
        m = _mod.match_planned_to_root(
            {"path": "a.go", "line": 20, "body": "x"}, roots, mode="path_line"
        )
        self.assertEqual(m["id"], 2)

    def test_path_line_near(self):
        roots = [
            {"id": 1, "path": "a.go", "line": 10, "is_torii": True, "is_root": True, "body": ""},
        ]
        m = _mod.match_planned_to_root(
            {"path": "a.go", "line": 12, "body": "x"}, roots, mode="path_line"
        )
        self.assertEqual(m["id"], 1)

    def test_path_line_far_no_match(self):
        roots = [
            {"id": 1, "path": "a.go", "line": 10, "is_torii": True, "is_root": True, "body": ""},
        ]
        m = _mod.match_planned_to_root(
            {"path": "a.go", "line": 100, "body": "x"}, roots, mode="path_line"
        )
        self.assertIsNone(m)

    def test_plan_split(self):
        existing = [
            {
                "id": 99,
                "path": "internal/util/function/manager.go",
                "line": 55,
                "body": "**HIGH** — old\n\n<!-- torii-inline -->",
            }
        ]
        planned = [
            {
                "path": "internal/util/function/manager.go",
                "line": 55,
                "body": "**HIGH** — updated\n\n<!-- torii-inline -->",
                "severity": "high",
                "kind": "finding",
            },
            {
                "path": "newfile.go",
                "line": 1,
                "body": "**MEDIUM** — new\n\n<!-- torii-inline -->",
                "severity": "medium",
                "kind": "finding",
            },
        ]
        out = _mod.plan_replies(planned, existing)
        self.assertEqual(out["matched"], 1)
        self.assertEqual(out["replies"][0]["in_reply_to"], 99)
        self.assertEqual(len(out["new_inlines"]), 1)
        self.assertIn("torii-inline-reply", out["replies"][0]["body"])

    def test_disabled(self):
        os.environ["TORII_REPLY_ON_THREAD"] = "0"
        out = _mod.plan_replies([{"path": "a.go", "line": 1, "body": "x"}], [])
        self.assertEqual(out["reason"], "disabled")
        self.assertEqual(len(out["new_inlines"]), 1)


class PostFixture(unittest.TestCase):
    def test_fixture_post(self):
        os.environ["TORII_REPLY_ON_THREAD"] = "1"
        with tempfile.TemporaryDirectory() as td:
            fix = Path(td) / "replies.json"
            os.environ["TORII_REPLY_FIXTURE"] = str(fix)
            res = _mod.post_reply("o/r", 1, 42, "hello thread")
            self.assertTrue(res["ok"])
            data = json.loads(fix.read_text())
            self.assertEqual(data[0]["in_reply_to"], 42)
            self.assertEqual(data[0]["body"], "hello thread")
        os.environ.pop("TORII_REPLY_FIXTURE", None)
        os.environ.pop("TORII_REPLY_ON_THREAD", None)


if __name__ == "__main__":
    unittest.main()
