#!/usr/bin/env python3
"""F59: incremental review control plane."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "incremental_review.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("incremental_review", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["incremental_review"] = _mod
_spec.loader.exec_module(_mod)


class Marker(unittest.TestCase):
    def test_parse_full(self):
        p = _mod.parse_marker("<!-- torii-review pr=12 run=99 head=abcdef1234567890 -->")
        self.assertEqual(p["pr"], "12")
        self.assertEqual(p["run"], "99")
        self.assertEqual(p["head"], "abcdef1234567890")

    def test_format_roundtrip(self):
        m = _mod.format_marker(3, run="local", head="deadbeefcafebabe")
        p = _mod.parse_marker(m)
        self.assertEqual(p["pr"], "3")
        self.assertTrue(p["head"].startswith("deadbeef"))

    def test_extract_last_head(self):
        comments = [
            {
                "id": 1,
                "created_at": "2026-01-01T00:00:00Z",
                "body": "<!-- torii-review pr=5 head=aaa111bbb222 -->\n**Verdict:** APPROVE",
            },
            {
                "id": 2,
                "created_at": "2026-01-02T00:00:00Z",
                "body": "<!-- torii-review pr=5 head=ccc333ddd444 -->\n**Verdict:** COMMENT",
            },
        ]
        info = _mod.extract_last_head_from_comments(comments, 5)
        self.assertEqual(info["head"], "ccc333ddd444")


class Plan(unittest.TestCase):
    def setUp(self):
        os.environ["TORII_INCREMENTAL"] = "1"

    def tearDown(self):
        os.environ.pop("TORII_INCREMENTAL", None)

    def test_disabled(self):
        os.environ["TORII_INCREMENTAL"] = "0"
        d = _mod.plan(pr=1, head_sha="abc", last_head="def")
        self.assertEqual(d["mode"], "full")
        self.assertEqual(d["reason"], "disabled")

    def test_no_prior(self):
        d = _mod.plan(pr=1, head_sha="abc", comments=[])
        self.assertEqual(d["mode"], "full")
        self.assertEqual(d["reason"], "no_prior_head")

    def test_incremental(self):
        d = _mod.plan(pr=1, head_sha="bbb222", last_head="aaa111")
        self.assertEqual(d["mode"], "incremental")
        self.assertEqual(d["base_sha"], "aaa111")

    def test_unchanged(self):
        d = _mod.plan(pr=1, head_sha="aaa111bbb", last_head="aaa111")
        self.assertEqual(d["mode"], "unchanged")


class AssembleFixture(unittest.TestCase):
    def test_rewrite_diff(self):
        os.environ["TORII_INCREMENTAL"] = "1"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            fix = {
                "head_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "last_head": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "compare_diff": "diff --git a/x.py b/x.py\n+hello\n",
                "compare_files": [
                    {"path": "x.py", "additions": 1, "deletions": 0}
                ],
            }
            fp = out / "fixture.json"
            fp.write_text(json.dumps(fix))
            os.environ["TORII_INCREMENTAL_FIXTURE"] = str(fp)
            try:
                d = _mod.assemble(
                    repo="acme/x",
                    pr=9,
                    out_dir=out,
                    pr_json_path=None,
                )
            finally:
                os.environ.pop("TORII_INCREMENTAL_FIXTURE", None)
                os.environ.pop("TORII_INCREMENTAL", None)
            self.assertEqual(d["mode"], "incremental")
            self.assertTrue((out / "pr.diff").is_file())
            self.assertIn("+hello", (out / "pr.diff").read_text())
            self.assertIn("x.py", (out / "files.txt").read_text())
            self.assertIn("incremental", (out / "incremental.md").read_text().lower())


class CLI(unittest.TestCase):
    def test_plan_cli(self):
        env = os.environ.copy()
        env["TORII_INCREMENTAL"] = "1"
        cp = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "plan",
                "--pr",
                "1",
                "--head-sha",
                "bbb",
                "--last-head",
                "aaa",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["mode"], "incremental")


if __name__ == "__main__":
    unittest.main()
