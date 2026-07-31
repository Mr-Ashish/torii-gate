#!/usr/bin/env python3
"""F39: Modal host parity helpers."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "modal_parity.py"

_spec = importlib.util.spec_from_file_location("modal_parity", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class PathSkipPreflightTests(unittest.TestCase):
    def test_docs_skip(self):
        r = _mod.path_skip_preflight(["README.md", "docs/a.md"], globs_raw="docs")
        self.assertTrue(r["skip"])
        self.assertEqual(r["allowed"], "false")

    def test_code_allows(self):
        r = _mod.path_skip_preflight(["src/x.py", "README.md"], globs_raw="docs")
        self.assertFalse(r["skip"])
        self.assertEqual(r["allowed"], "true")

    def test_disabled(self):
        r = _mod.path_skip_preflight(["README.md"], globs_raw="")
        self.assertFalse(r["skip"])
        self.assertEqual(r["reason"], "disabled")

    def test_force(self):
        r = _mod.path_skip_preflight(["README.md"], globs_raw="docs", force=True)
        self.assertFalse(r["skip"])
        self.assertEqual(r["reason"], "force")

    def test_parse_gh_paths(self):
        raw = "/README.md\nsrc/a.py\n/README.md\n"
        self.assertEqual(
            _mod.parse_paths_from_gh_filenames(raw),
            ["README.md", "src/a.py"],
        )

    def test_stub_summary(self):
        s, b = _mod.path_skip_stub_summary("README.md", "docs")
        self.assertIn("F38/F39", s)
        self.assertIn("None", b)


class CliTests(unittest.TestCase):
    def test_cli_skip_exit_2(self):
        cp = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "path-skip",
                "--path",
                "README.md",
                "--globs",
                "docs",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(cp.returncode, 2, cp.stdout + cp.stderr)
        data = json.loads(cp.stdout)
        self.assertTrue(data["skip"])


class WiringTests(unittest.TestCase):
    def test_modal_app_imports_parity(self):
        text = (ROOT / "modal_app" / "app.py").read_text()
        self.assertIn("modal_parity", text)
        self.assertIn("F39", text)
        self.assertIn("report-verdict.sh", text)
        self.assertIn("path_skip_preflight", text)

    def test_install_allowlist(self):
        # optional on target packs — Modal image uses add_local_dir scripts/
        text = (ROOT / "scripts" / "install-torii.sh").read_text()
        # not required on target GHA packs; present in scripts/ is enough
        self.assertTrue((ROOT / "scripts" / "modal_parity.py").is_file())


if __name__ == "__main__":
    unittest.main()
