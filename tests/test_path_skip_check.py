#!/usr/bin/env python3
"""F38: path-glob free skip for docs-only / filtered PRs."""

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
SCRIPT = ROOT / "scripts" / "path-skip-check.py"

_spec = importlib.util.spec_from_file_location("path_skip_check", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class ParseGlobsTests(unittest.TestCase):
    def test_empty_off(self):
        for v in (None, "", "off", "0", "false", "disabled"):
            self.assertEqual(_mod.parse_globs(v), [])

    def test_docs_preset(self):
        g = _mod.parse_globs("docs")
        self.assertIn("*.md", g)
        self.assertIn("docs/**", g)

    def test_custom_list(self):
        self.assertEqual(_mod.parse_globs("*.md, docs/**"), ["*.md", "docs/**"])


class MatchTests(unittest.TestCase):
    def test_md_basename(self):
        self.assertTrue(_mod.path_matches("README.md", ["*.md"]))
        self.assertTrue(_mod.path_matches("foo/bar.md", ["*.md"]))

    def test_docs_prefix(self):
        self.assertTrue(_mod.path_matches("docs/guide.md", ["docs/**"]))
        self.assertTrue(_mod.path_matches("docs/a/b.md", ["docs/**"]))
        self.assertFalse(_mod.path_matches("src/main.py", ["docs/**"]))

    def test_decide_all_docs_skip(self):
        d = _mod.decide(["README.md", "docs/x.md"], _mod.DOCS_PRESET)
        self.assertEqual(d["allowed"], "false")
        self.assertEqual(d["reason"], "all_paths_skipped")

    def test_decide_code_allows(self):
        d = _mod.decide(["README.md", "src/a.py"], _mod.DOCS_PRESET)
        self.assertEqual(d["allowed"], "true")
        self.assertEqual(d["reason"], "code_paths_present")
        self.assertIn("src/a.py", d["sample"])

    def test_decide_disabled(self):
        d = _mod.decide(["README.md"], [])
        self.assertEqual(d["allowed"], "true")
        self.assertEqual(d["reason"], "disabled")

    def test_no_paths_allows(self):
        d = _mod.decide([], ["*.md"])
        self.assertEqual(d["allowed"], "true")
        self.assertEqual(d["reason"], "no_paths")


class CliTests(unittest.TestCase):
    def _run(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        e = {**os.environ}
        # clear force from parent unless the test sets it
        e.pop("TORII_SKIP_PATHS_FORCE", None)
        if env:
            e.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=e,
        )

    def _kv(self, out: str) -> dict[str, str]:
        d: dict[str, str] = {}
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k] = v
        return d

    def test_cli_docs_skip(self):
        with tempfile.TemporaryDirectory() as td:
            pf = Path(td) / "paths.txt"
            pf.write_text("/README.md\n/docs/a.md\n", encoding="utf-8")
            cp = self._run(
                "--paths-file",
                str(pf),
                env={"TORII_SKIP_PATH_GLOBS": "docs"},
            )
            self.assertEqual(cp.returncode, 2, cp.stdout + cp.stderr)
            kv = self._kv(cp.stdout)
            self.assertEqual(kv["allowed"], "false")

    def test_cli_code_allow(self):
        cp = self._run(
            "--path",
            "src/x.py",
            "--path",
            "README.md",
            env={"TORII_SKIP_PATH_GLOBS": "docs"},
        )
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(self._kv(cp.stdout)["allowed"], "true")

    def test_cli_disabled_default(self):
        env = {**os.environ}
        env.pop("TORII_SKIP_PATH_GLOBS", None)
        env.pop("TORII_SKIP_PATHS_FORCE", None)
        cp = subprocess.run(
            [sys.executable, str(SCRIPT), "--path", "README.md"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
        )
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(self._kv(cp.stdout)["allowed"], "true")
        self.assertEqual(self._kv(cp.stdout)["reason"], "disabled")

    def test_force(self):
        cp = self._run(
            "--path",
            "README.md",
            env={"TORII_SKIP_PATH_GLOBS": "docs", "TORII_SKIP_PATHS_FORCE": "1"},
        )
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(self._kv(cp.stdout)["reason"], "force")


class WiringTests(unittest.TestCase):
    def test_workflow_mentions_f38(self):
        text = (ROOT / ".github" / "workflows" / "torii-review-reusable.yml").read_text()
        self.assertIn("path-skip-check.py", text)
        self.assertIn("TORII_SKIP_PATH_GLOBS", text)
        self.assertIn("F38", text)

    def test_install_allowlist(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text()
        self.assertIn("path-skip-check.py", text)


if __name__ == "__main__":
    unittest.main()
