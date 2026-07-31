#!/usr/bin/env python3
"""F36: portable review wall-clock timeout."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run-with-timeout.py"
sys.path.insert(0, str(ROOT / "scripts"))

# Import helpers without executing main
import importlib.util

_spec = importlib.util.spec_from_file_location("run_with_timeout", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class ParseSecondsTests(unittest.TestCase):
    def test_default_when_none(self):
        self.assertEqual(_mod.parse_seconds(None), 1500)

    def test_off_variants(self):
        for v in ("0", "off", "false", "no", "none", "disabled", "", "  "):
            self.assertEqual(_mod.parse_seconds(v), 0, msg=v)

    def test_positive(self):
        self.assertEqual(_mod.parse_seconds("30"), 30)
        self.assertEqual(_mod.parse_seconds("900"), 900)

    def test_invalid_is_off(self):
        self.assertEqual(_mod.parse_seconds("abc"), 0)
        self.assertEqual(_mod.parse_seconds("-5"), 0)

    def test_cap_six_hours(self):
        self.assertEqual(_mod.parse_seconds(str(99 * 3600)), 6 * 3600)

    def test_effective_env(self):
        old = os.environ.get("TORII_REVIEW_TIMEOUT_SECONDS")
        try:
            os.environ["TORII_REVIEW_TIMEOUT_SECONDS"] = "42"
            self.assertEqual(_mod.effective_seconds(None), 42)
            self.assertEqual(_mod.effective_seconds("10"), 10)
            os.environ["TORII_REVIEW_TIMEOUT_SECONDS"] = "off"
            self.assertEqual(_mod.effective_seconds(None), 0)
        finally:
            if old is None:
                os.environ.pop("TORII_REVIEW_TIMEOUT_SECONDS", None)
            else:
                os.environ["TORII_REVIEW_TIMEOUT_SECONDS"] = old


class RunTimeoutTests(unittest.TestCase):
    def test_no_timeout_runs_to_completion(self):
        rc = _mod.run_with_timeout([sys.executable, "-c", "import sys; sys.exit(7)"], 0)
        self.assertEqual(rc, 7)

    def test_fast_command_within_limit(self):
        rc = _mod.run_with_timeout(
            [sys.executable, "-c", "print('ok')"],
            5,
        )
        self.assertEqual(rc, 0)

    def test_kills_on_timeout(self):
        # sleep longer than limit → 124
        rc = _mod.run_with_timeout(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            1,
        )
        self.assertEqual(rc, 124)

    def test_cli_timeout_exit(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--seconds",
                "1",
                "--",
                sys.executable,
                "-c",
                "import time; time.sleep(30)",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 124)
        self.assertIn("TIMEOUT", proc.stderr)

    def test_cli_resolve(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "resolve", "90"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "90")

    def test_cli_resolve_default(self):
        env = {**os.environ}
        env.pop("TORII_REVIEW_TIMEOUT_SECONDS", None)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "resolve"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "1500")

    def test_empty_cmd_usage(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--seconds", "1"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 125)


class WiringTests(unittest.TestCase):
    def test_hermes_script_mentions_f36(self):
        text = (ROOT / "scripts" / "run-hermes-review.sh").read_text()
        self.assertIn("run-with-timeout.py", text)
        self.assertIn("TORII_REVIEW_TIMEOUT_SECONDS", text)
        self.assertIn("F36", text)

    def test_install_allowlist(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text()
        self.assertIn("run-with-timeout.py", text)

    def test_workflow_exports_var(self):
        text = (ROOT / ".github" / "workflows" / "torii-review-reusable.yml").read_text()
        self.assertIn("TORII_REVIEW_TIMEOUT_SECONDS", text)


if __name__ == "__main__":
    unittest.main()
