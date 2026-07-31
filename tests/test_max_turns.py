#!/usr/bin/env python3
"""F41: Hermes max_turns resolver + detect."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "max_turns.py"
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location("max_turns", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class ParseMaxTurnsTests(unittest.TestCase):
    def test_default_when_none(self):
        self.assertEqual(_mod.parse_max_turns(None), 40)

    def test_off_variants(self):
        for v in ("0", "off", "false", "no", "none", "disabled", "unlimited", "inf"):
            self.assertIsNone(_mod.parse_max_turns(v), msg=v)

    def test_positive(self):
        self.assertEqual(_mod.parse_max_turns("30"), 30)
        self.assertEqual(_mod.parse_max_turns("12"), 12)

    def test_cap_at_500(self):
        self.assertEqual(_mod.parse_max_turns("9999"), 500)

    def test_invalid_falls_back_default(self):
        self.assertEqual(_mod.parse_max_turns("abc"), 40)

    def test_empty_string_default(self):
        self.assertEqual(_mod.parse_max_turns(""), 40)
        self.assertEqual(_mod.parse_max_turns("  "), 40)

    def test_effective_env(self):
        old = os.environ.get("TORII_MAX_TURNS")
        try:
            os.environ["TORII_MAX_TURNS"] = "25"
            self.assertEqual(_mod.effective_max_turns(None), 25)
            self.assertEqual(_mod.effective_max_turns("10"), 10)
            os.environ["TORII_MAX_TURNS"] = "off"
            self.assertIsNone(_mod.effective_max_turns(None))
        finally:
            if old is None:
                os.environ.pop("TORII_MAX_TURNS", None)
            else:
                os.environ["TORII_MAX_TURNS"] = old


class DetectTests(unittest.TestCase):
    def test_detect_hit_patterns(self):
        self.assertTrue(
            _mod.detect_max_turns_hit(["⚠️  Iteration budget exhausted (40/40)"])
        )
        self.assertTrue(
            _mod.detect_max_turns_hit(["turn_exit_reason=max_iterations_reached(40/40)"])
        )
        self.assertTrue(
            _mod.detect_max_turns_hit(["Reached maximum iterations (40). Requesting summary"])
        )
        self.assertFalse(_mod.detect_max_turns_hit(["review completed cleanly"]))

    def test_detect_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "log.txt"
            p.write_text("all good\n", encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "detect", str(p)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            p.write_text("Iteration budget exhausted (12/12)\n", encoding="utf-8")
            r2 = subprocess.run(
                [sys.executable, str(SCRIPT), "detect", str(p)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r2.returncode, 2, r2.stdout + r2.stderr)

    def test_resolve_cli(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "resolve", "off"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "off")
        r2 = subprocess.run(
            [sys.executable, str(SCRIPT), "resolve", "33"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(r2.stdout.strip(), "33")


class ConfigYamlTests(unittest.TestCase):
    def test_agent_config_has_max_turns(self):
        cfg = (ROOT / "agent" / "config.yaml").read_text(encoding="utf-8")
        self.assertIn("max_turns:", cfg)
        self.assertIn("agent:", cfg)

    def test_run_hermes_wires_max_turns(self):
        text = (ROOT / "scripts" / "run-hermes-review.sh").read_text(encoding="utf-8")
        self.assertIn("max_turns.py", text)
        self.assertIn("hermes-max-turns.env", text)
        self.assertIn("TORII_MAX_TURNS", text)
        # F41 still uses HERMES_MAX_ITERATIONS + config rewrite (not CLI --max-turns)
        self.assertIn("HERMES_MAX_ITERATIONS", text)
        self.assertIn("agent.max_turns", text)
        # F47/H14: never pass --max-turns on the hermes binary (argparse has no flag)
        hermes_z_block = text.split("hermes -z", 1)[1].split("hermes chat", 1)[0]
        self.assertNotIn("--max-turns", hermes_z_block)
        self.assertNotIn("MAX_TURNS_ARGS", text)
        # preflight_cost.py may still take --max-turns (Torii helper, not hermes)
        self.assertIn("cli_argv_broken", text)

    def test_max_turns_helper_documents_no_cli_flag(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Do **not** pass", text)
        self.assertIn("HERMES_MAX_ITERATIONS", text)

    def test_install_includes_helper(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text(encoding="utf-8")
        self.assertIn("max_turns.py", text)

    def test_workflow_exports_var(self):
        text = (
            ROOT / ".github" / "workflows" / "torii-review-reusable.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("TORII_MAX_TURNS", text)


if __name__ == "__main__":
    unittest.main()
