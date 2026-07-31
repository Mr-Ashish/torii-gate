#!/usr/bin/env python3
"""F62: FP resolve + memory update (fixture, no network)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "fp_resolve_memory.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("fp_resolve_memory", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["fp_resolve_memory"] = _mod
_spec.loader.exec_module(_mod)


class Classify(unittest.TestCase):
    def test_false_positive_phrases(self):
        for body in (
            "This is a false positive — mutex already covers it.",
            "not a bug, by design",
            "won't fix — out of scope",
            "Working as intended for legacy clients.",
        ):
            self.assertEqual(_mod.classify_body(body), "false_positive", body)

    def test_resolved_phrases(self):
        for body in (
            "Fixed in latest commit",
            "addressed in the latest push",
            "this is fixed now",
        ):
            self.assertEqual(_mod.classify_body(body), "resolved", body)

    def test_weak_resolved(self):
        self.assertEqual(_mod.classify_body("fixed"), "resolved")
        self.assertEqual(_mod.classify_body("done"), "resolved")

    def test_none(self):
        self.assertIsNone(_mod.classify_body("thanks for the review"))
        self.assertIsNone(_mod.classify_body(""))


class FromThreads(unittest.TestCase):
    def test_reply_under_torii_root(self):
        comments = [
            {
                "id": 10,
                "path": "pkg/foo.go",
                "line": 42,
                "body": "**HIGH** — race\n\n<!-- torii-inline -->",
                "user": {"login": "torii-bot[bot]"},
            },
            {
                "id": 11,
                "in_reply_to_id": 10,
                "body": "false positive — protected by singleflight",
                "user": {"login": "alice"},
            },
        ]
        pats = _mod.patterns_from_review_comments(comments, pr="3")
        self.assertEqual(len(pats), 1)
        self.assertEqual(pats[0].kind, "false_positive")
        self.assertEqual(pats[0].path, "pkg/foo.go")
        self.assertEqual(pats[0].line, 42)
        self.assertEqual(pats[0].source, "thread_reply")
        self.assertEqual(pats[0].author, "alice")

    def test_skips_bot_replies(self):
        comments = [
            {
                "id": 10,
                "path": "a.go",
                "line": 1,
                "body": "x\n<!-- torii-inline -->",
                "user": {"login": "torii[bot]"},
            },
            {
                "id": 11,
                "in_reply_to_id": 10,
                "body": "false positive",
                "user": {"login": "torii[bot]"},
            },
        ]
        self.assertEqual(_mod.patterns_from_review_comments(comments), [])

    def test_issue_comment_requires_path(self):
        ok = _mod.patterns_from_issue_comments(
            [
                {
                    "id": 1,
                    "body": "false positive on `internal/proxy/server.go:88`",
                    "user": {"login": "bob"},
                }
            ],
            pr="2",
        )
        self.assertEqual(len(ok), 1)
        self.assertEqual(ok[0].path, "internal/proxy/server.go")
        self.assertEqual(ok[0].line, 88)

        bare = _mod.patterns_from_issue_comments(
            [{"id": 2, "body": "false positive", "user": {"login": "bob"}}]
        )
        self.assertEqual(bare, [])


class MemorySection(unittest.TestCase):
    def test_parse_and_merge(self):
        mem = """# Torii Gate review memory

## Review craft
- focus new code

## FP patterns

- `pkg/a.go:10` kind=false_positive pr=#1 reason="by design"
- `pkg/b.go` kind=resolved pr=#2 reason="fixed"

## Review 2026
- Verdict: APPROVE
"""
        parsed = _mod.parse_memory_fp_section(mem)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].path, "pkg/a.go")
        self.assertEqual(parsed[0].line, 10)

        extra = [
            _mod.FpPattern(
                kind="false_positive",
                path="pkg/c.go",
                line=3,
                reason="won't fix",
                pr="9",
                source="thread_reply",
            )
        ]
        new = _mod.merge_into_memory(mem, extra)
        self.assertIn("pkg/c.go:3", new)
        self.assertIn("pkg/a.go:10", new)
        # still only one FP patterns section
        self.assertEqual(new.lower().count("## fp patterns"), 1)

    def test_merge_creates_section(self):
        mem = "# Torii Gate review memory\n\n## Review craft\n- x\n"
        pats = [
            _mod.FpPattern(
                kind="resolved",
                path="x.py",
                line=None,
                reason="fixed",
                source="thread_reply",
            )
        ]
        new = _mod.merge_into_memory(mem, pats)
        self.assertIn("## FP patterns", new)
        self.assertIn("`x.py`", new)


class PlanMerge(unittest.TestCase):
    def test_dedupe_prefers_thread(self):
        thr = [
            _mod.FpPattern(
                kind="false_positive",
                path="a.go",
                line=1,
                reason="by design from alice",
                source="thread_reply",
            )
        ]
        mem = [
            _mod.FpPattern(
                kind="false_positive",
                path="a.go",
                line=1,
                reason="by design old",
                source="memory",
            )
        ]
        m = _mod.merge_patterns(thr, mem)
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0].source, "thread_reply")
        self.assertIn("alice", m[0].reason)


class PromptInject(unittest.TestCase):
    def test_apply_before_changed_files(self):
        prompt = "# Review\n\n## Changed files summary\n\n- a\n"
        sec = _mod.render_section(
            [
                _mod.FpPattern(
                    kind="false_positive",
                    path="a.go",
                    line=2,
                    reason="by design",
                    source="memory",
                )
            ]
        )
        out = _mod.apply_to_prompt(prompt, sec)
        self.assertIn("Known false positives", out)
        self.assertLess(out.find("Known false positives"), out.find("Changed files"))

    def test_placeholder(self):
        prompt = "pre\n{{FP_RESOLVE}}\npost"
        out = _mod.apply_to_prompt(prompt, "## Known\n\nok\n")
        self.assertNotIn("{{FP_RESOLVE}}", out)
        self.assertIn("## Known", out)


class AssembleFixture(unittest.TestCase):
    def test_assemble_fixture(self):
        comments = [
            {
                "id": 100,
                "path": "client/bloom.go",
                "line": 50,
                "body": "nit\n\n<!-- torii-inline -->",
                "user": {"login": "torii[bot]"},
            },
            {
                "id": 101,
                "in_reply_to_id": 100,
                "body": "won't fix — intentional tradeoff",
                "user": {"login": "dev"},
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            fixture = td_path / "comments.json"
            fixture.write_text(json.dumps(comments), encoding="utf-8")
            prompt = td_path / "prompt.md"
            prompt.write_text(
                "# P\n\n## Changed files summary\n\n- x\n\n## Required Markdown template\n",
                encoding="utf-8",
            )
            mem = td_path / "MEMORY.md"
            mem.write_text("# Torii Gate review memory\n\n", encoding="utf-8")
            out = td_path / "out"
            out.mkdir()
            env = os.environ.copy()
            env["TORII_FP_RESOLVE"] = "1"
            env["TORII_FP_RESOLVE_FIXTURE"] = str(fixture)
            env["TORII_FP_RESOLVE_ISSUE_FIXTURE"] = str(td_path / "empty.json")
            (td_path / "empty.json").write_text("[]", encoding="utf-8")
            # isolate toggle registry
            old = os.environ.get("TORII_FP_RESOLVE")
            os.environ["TORII_FP_RESOLVE"] = "1"
            os.environ["TORII_FP_RESOLVE_FIXTURE"] = str(fixture)
            os.environ["TORII_FP_RESOLVE_ISSUE_FIXTURE"] = str(td_path / "empty.json")
            try:
                r = _mod.assemble(
                    repo="Mr-Ashish/milvus",
                    pr="2",
                    out_dir=out,
                    memory_path=mem,
                    prompt_path=prompt,
                )
            finally:
                if old is None:
                    os.environ.pop("TORII_FP_RESOLVE", None)
                else:
                    os.environ["TORII_FP_RESOLVE"] = old
                os.environ.pop("TORII_FP_RESOLVE_FIXTURE", None)
                os.environ.pop("TORII_FP_RESOLVE_ISSUE_FIXTURE", None)
            self.assertEqual(r["enabled"], "1")
            self.assertEqual(r["count"], "1")
            self.assertTrue((out / "fp-resolve.json").is_file())
            body = prompt.read_text(encoding="utf-8")
            self.assertIn("client/bloom.go", body)
            self.assertIn("false_positive", body)

    def test_update_writes_memory(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            out = td_path / "out"
            out.mkdir()
            patterns = [
                {
                    "kind": "false_positive",
                    "path": "z.go",
                    "line": 9,
                    "reason": "by design",
                    "pr": "1",
                    "source": "thread_reply",
                    "author": "alice",
                }
            ]
            (out / "fp-resolve.json").write_text(
                json.dumps(patterns), encoding="utf-8"
            )
            mem = td_path / "MEMORY.md"
            mem.write_text("# Torii Gate review memory\n\n## Review craft\n- x\n", encoding="utf-8")
            os.environ["TORII_FP_RESOLVE"] = "1"
            try:
                r = _mod.update_memory(out_dir=out, memory_path=mem)
            finally:
                os.environ.pop("TORII_FP_RESOLVE", None)
            self.assertEqual(r["updated"], "1")
            text = mem.read_text(encoding="utf-8")
            self.assertIn("## FP patterns", text)
            self.assertIn("z.go:9", text)


class FindingMatch(unittest.TestCase):
    def test_match(self):
        pats = [
            _mod.FpPattern(
                kind="false_positive",
                path="a.go",
                line=3,
                reason="x",
                source="memory",
            )
        ]
        hit = _mod.finding_matches_fp("- bug in `a.go:3` still races", pats)
        self.assertIsNotNone(hit)
        miss = _mod.finding_matches_fp("- bug in `b.go:1`", pats)
        self.assertIsNone(miss)


class RulesFile(unittest.TestCase):
    def test_save_load_merge(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            rules = td_path / "fp-rules.json"
            pats = [
                _mod.FpPattern(
                    kind="false_positive",
                    path="a.go",
                    line=1,
                    reason="by design",
                    source="thread_reply",
                    author="alice",
                    pr="3",
                )
            ]
            _mod.save_rules_file(rules, pats)
            loaded, src = _mod.load_rules_file(explicit=rules)
            self.assertEqual(src, str(rules))
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].path, "a.go")
            # second write merges
            more = [
                _mod.FpPattern(
                    kind="resolved",
                    path="b.go",
                    line=2,
                    reason="fixed",
                    source="thread_reply",
                )
            ]
            _mod.save_rules_file(rules, more)
            loaded2 = _mod.patterns_from_rules_file(rules)
            self.assertEqual(len(loaded2), 2)

    def test_update_writes_rules(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            out = td_path / "out"
            out.mkdir()
            patterns = [
                {
                    "kind": "false_positive",
                    "path": "z.go",
                    "line": 9,
                    "reason": "by design",
                    "pr": "1",
                    "source": "thread_reply",
                    "author": "alice",
                }
            ]
            (out / "fp-resolve.json").write_text(
                json.dumps(patterns), encoding="utf-8"
            )
            mem = td_path / "MEMORY.md"
            mem.write_text("# Torii Gate review memory\n\n", encoding="utf-8")
            os.environ["TORII_FP_RESOLVE"] = "1"
            try:
                r = _mod.update_memory(out_dir=out, memory_path=mem)
            finally:
                os.environ.pop("TORII_FP_RESOLVE", None)
            self.assertEqual(r["updated"], "1")
            self.assertTrue((out / "fp-rules.json").is_file())
            self.assertTrue((mem.parent / "fp-rules.json").is_file())
            doc = json.loads((out / "fp-rules.json").read_text(encoding="utf-8"))
            self.assertEqual(doc["schema_version"], 1)
            self.assertEqual(doc["count"], 1)
            self.assertEqual(doc["rules"][0]["path"], "z.go")

    def test_build_plan_includes_rules(self):
        rules = [
            _mod.FpPattern(
                kind="false_positive",
                path="c.go",
                line=3,
                reason="x",
                source="rules",
            )
        ]
        plan = _mod.build_plan(rules=rules, memory_md="")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].source, "rules")


if __name__ == "__main__":
    unittest.main()
