#!/usr/bin/env python3
"""F42: auto model tier by PR size."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "model_tier.py"
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location("model_tier", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class ParseModeTests(unittest.TestCase):
    def test_off_variants(self):
        for v in (None, "", "off", "0", "false", "no", "none", "disabled"):
            self.assertEqual(_mod.parse_mode(v), "off", msg=v)

    def test_auto_variants(self):
        for v in ("auto", "on", "1", "true", "yes", "size"):
            self.assertEqual(_mod.parse_mode(v), "auto", msg=v)

    def test_cheap_full(self):
        self.assertEqual(_mod.parse_mode("cheap"), "cheap")
        self.assertEqual(_mod.parse_mode("full"), "full")
        self.assertEqual(_mod.parse_mode("mini"), "cheap")


class SelectModelTests(unittest.TestCase):
    def test_off_default_full(self):
        r = _mod.select_model(mode="off")
        self.assertEqual(r["model"], _mod.DEFAULT_FULL_MODEL)
        self.assertEqual(r["tier"], "default")
        self.assertEqual(r["reason"], "default_full")

    def test_off_explicit(self):
        r = _mod.select_model(mode="off", torii_model="openai/gpt-5-mini")
        self.assertEqual(r["model"], "openai/gpt-5-mini")
        self.assertEqual(r["tier"], "explicit")

    def test_auto_docs_only_cheap(self):
        r = _mod.select_model(
            mode="auto",
            paths=["README.md", "docs/guide.md"],
            diff_bytes=50_000,
            file_count=2,
        )
        self.assertEqual(r["tier"], "cheap")
        self.assertEqual(r["reason"], "docs_only")
        self.assertEqual(r["model"], _mod.DEFAULT_CHEAP_MODEL)

    def test_auto_tiny_cheap(self):
        r = _mod.select_model(
            mode="auto",
            paths=["src/x.py"],
            diff_bytes=800,
            file_count=1,
        )
        self.assertEqual(r["tier"], "cheap")
        self.assertEqual(r["reason"], "tiny")

    def test_auto_large_full(self):
        r = _mod.select_model(
            mode="auto",
            paths=["a.py", "b.py", "c.py", "d.py"],
            diff_bytes=80_000,
            file_count=4,
        )
        self.assertEqual(r["tier"], "full")
        self.assertEqual(r["reason"], "large")
        self.assertEqual(r["model"], _mod.DEFAULT_FULL_MODEL)

    def test_auto_truncated_forces_full(self):
        r = _mod.select_model(
            mode="auto",
            paths=["README.md"],
            diff_bytes=100,
            file_count=1,
            diff_truncated=True,
        )
        self.assertEqual(r["tier"], "full")
        self.assertEqual(r["reason"], "diff_truncated")

    def test_auto_uses_torii_model_as_full(self):
        r = _mod.select_model(
            mode="auto",
            torii_model="anthropic/claude-sonnet-4",
            paths=["a.py", "b.py", "c.py", "d.py", "e.py"],
            diff_bytes=100_000,
            file_count=5,
        )
        self.assertEqual(r["model"], "anthropic/claude-sonnet-4")
        self.assertEqual(r["tier"], "full")

    def test_forced_cheap_full(self):
        self.assertEqual(
            _mod.select_model(mode="cheap", paths=["a.py"], diff_bytes=1e9)["tier"],
            "cheap",
        )
        self.assertEqual(
            _mod.select_model(mode="full", paths=["README.md"], diff_bytes=10)["tier"],
            "full",
        )

    def test_custom_cheap_env_via_arg(self):
        r = _mod.select_model(
            mode="auto",
            cheap_model="openai/gpt-5-mini",
            paths=["README.md"],
            diff_bytes=100,
            file_count=1,
        )
        self.assertEqual(r["model"], "openai/gpt-5-mini")


class CliTests(unittest.TestCase):
    def test_select_cli_auto_tiny(self):
        env = {**os.environ, "TORII_MODEL_TIER": "auto"}
        env.pop("TORII_MODEL", None)
        env.pop("OPENROUTER_MODEL", None)
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "select",
                "--diff-bytes",
                "500",
                "--file-count",
                "1",
                "--path",
                "src/x.py",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("tier=cheap", r.stdout)
        self.assertIn("reason=tiny", r.stdout)
        self.assertIn(f"model={_mod.DEFAULT_CHEAP_MODEL}", r.stdout)

    def test_select_cli_off_default(self):
        env = {**os.environ}
        env.pop("TORII_MODEL_TIER", None)
        env.pop("TORII_MODEL", None)
        env.pop("OPENROUTER_MODEL", None)
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "select", "--mode", "off"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"model={_mod.DEFAULT_FULL_MODEL}", r.stdout)
        self.assertIn("tier=default", r.stdout)

    def test_select_from_pr_json(self):
        with tempfile.TemporaryDirectory() as td:
            pr = Path(td) / "pr.json"
            pr.write_text(
                json.dumps(
                    {
                        "files": [
                            {"path": "README.md", "additions": 2, "deletions": 0},
                            {"path": "docs/a.md", "additions": 1, "deletions": 0},
                        ],
                        "additions": 3,
                        "deletions": 0,
                    }
                ),
                encoding="utf-8",
            )
            env = {**os.environ, "TORII_MODEL_TIER": "auto"}
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "select",
                    "--pr-json",
                    str(pr),
                    "--diff-bytes",
                    "99999",
                ],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(ROOT),
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("reason=docs_only", r.stdout)
            self.assertIn("tier=cheap", r.stdout)


class WiringTests(unittest.TestCase):
    def test_run_hermes_wires_model_tier(self):
        text = (ROOT / "scripts" / "run-hermes-review.sh").read_text(encoding="utf-8")
        self.assertIn("model_tier.py", text)
        self.assertIn("model-tier.env", text)
        self.assertIn("TORII_MODEL_TIER", text)

    def test_install_includes_helper(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text(encoding="utf-8")
        self.assertIn("model_tier.py", text)

    def test_workflow_exports_vars(self):
        text = (
            ROOT / ".github" / "workflows" / "torii-review-reusable.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("TORII_MODEL_TIER", text)
        self.assertIn("TORII_MODEL_CHEAP", text)

    def test_assemble_writes_file_count(self):
        text = (ROOT / "scripts" / "assemble-context.sh").read_text(encoding="utf-8")
        self.assertIn("FILE_COUNT", text)


if __name__ == "__main__":
    unittest.main()
