#!/usr/bin/env python3
"""F58: deterministic PR description filler."""

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
SCRIPT = ROOT / "scripts" / "pr_description_filler.py"
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location("pr_description_filler", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["pr_description_filler"] = _mod
_spec.loader.exec_module(_mod)


def sample_pr(**over):
    base = {
        "title": "Fix null crash in parser",
        "body": "",
        "additions": 12,
        "deletions": 3,
        "files": [
            {"path": "pkg/parser.py", "additions": 10, "deletions": 3},
            {"path": "tests/test_parser.py", "additions": 2, "deletions": 0},
        ],
    }
    base.update(over)
    return base


class Classify(unittest.TestCase):
    def test_bug_from_title(self):
        self.assertEqual(
            _mod.classify_type("Fix crash on empty input", sample_pr()["files"]),
            "Bug fix",
        )

    def test_docs_only(self):
        files = [{"path": "README.md", "additions": 2, "deletions": 0}]
        self.assertEqual(_mod.classify_type("Update readme", files), "Documentation")

    def test_enhancement_default(self):
        files = [{"path": "src/feature.py", "additions": 5, "deletions": 0}]
        self.assertEqual(_mod.classify_type("Add export API", files), "Enhancement")


class Scaffold(unittest.TestCase):
    def test_body_markers_and_sections(self):
        sc = _mod.build_scaffold(sample_pr(body="Fixes #99"))
        body = sc["body"]
        self.assertIn(_mod.MARKER_START, body)
        self.assertIn(_mod.MARKER_END, body)
        self.assertIn("## Summary", body)
        self.assertIn("## Changes", body)
        self.assertIn("## Test plan", body)
        self.assertIn("`pkg/parser.py`", body)
        self.assertIn("#99", body)
        self.assertEqual(sc["type"], "Bug fix")
        self.assertIn("[ ]", body)

    def test_embed_mermaid(self):
        arch = "### Architecture\n\n```mermaid\nflowchart LR\n  a-->b\n```\n"
        sc = _mod.build_scaffold(sample_pr(), architecture_md=arch)
        self.assertIn("```mermaid", sc["body"])
        self.assertIn("## Architecture", sc["body"])


class Merge(unittest.TestCase):
    def test_fill_empty(self):
        sc_body = _mod.build_scaffold(sample_pr())["body"]
        new, action = _mod.merge_body("", sc_body, "fill-empty")
        self.assertEqual(action, "fill")
        self.assertIn(_mod.MARKER_START, new)

    def test_skip_rich_body(self):
        sc_body = _mod.build_scaffold(sample_pr())["body"]
        rich = "## Why\n\nThis PR carefully rewrites the parser for correctness.\n"
        new, action = _mod.merge_body(rich, sc_body, "fill-empty")
        self.assertEqual(action, "skip")
        self.assertEqual(new, rich)

    def test_markers_refresh(self):
        old = (
            "Author note stays.\n\n"
            f"{_mod.MARKER_START}\nold scaffold\n{_mod.MARKER_END}\n"
        )
        sc_body = _mod.build_scaffold(sample_pr())["body"]
        new, action = _mod.merge_body(old, sc_body, "markers")
        self.assertEqual(action, "markers")
        self.assertIn("Author note stays", new)
        self.assertIn("## Test plan", new)
        self.assertNotIn("old scaffold", new)

    def test_force(self):
        sc_body = _mod.build_scaffold(sample_pr())["body"]
        new, action = _mod.merge_body("keep me", sc_body, "force")
        self.assertEqual(action, "force")
        self.assertNotIn("keep me", new)


class CLI(unittest.TestCase):
    def _run(self, *args, env=None):
        e = os.environ.copy()
        e.pop("TORII_TOGGLES_FILE", None)
        if env:
            e.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=e,
        )

    def test_plan_fill(self):
        with tempfile.TemporaryDirectory() as td:
            prp = Path(td) / "pr.json"
            prp.write_text(json.dumps(sample_pr(body="")))
            cp = self._run("plan", "--pr-json", str(prp), "--mode", "fill-empty")
            self.assertEqual(cp.returncode, 0, cp.stderr)
            data = json.loads(cp.stdout)
            self.assertEqual(data["action"], "fill")
            self.assertTrue(data["would_change"])

    def test_apply_dry_run_no_post(self):
        with tempfile.TemporaryDirectory() as td:
            prp = Path(td) / "pr.json"
            prp.write_text(json.dumps(sample_pr(body="")))
            cp = self._run(
                "apply",
                "--pr-json",
                str(prp),
                "--repo",
                "acme/x",
                "--pr",
                "1",
                "--dry-run",
                "--mode",
                "fill-empty",
            )
            self.assertEqual(cp.returncode, 0, cp.stderr)
            data = json.loads(cp.stdout)
            self.assertFalse(data["posted"])
            self.assertEqual(data["action"], "fill")


if __name__ == "__main__":
    unittest.main()
