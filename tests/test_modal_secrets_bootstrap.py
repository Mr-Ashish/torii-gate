"""Tests for F80 Modal secrets bootstrap."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "modal_secrets_bootstrap.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ},
    )


class ModalSecretsBootstrapTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["no_leak"])
        self.assertEqual(set(data["or_keys"]), {"OPENROUTER_API_KEY", "OPENROUTER_BASE_URL"})

    def test_plan_no_secret_values(self):
        r = _run(["plan"])
        # may exit 1 if keys missing in CI — still must not leak
        body = r.stdout + r.stderr
        self.assertNotRegex(body, r"sk-or-v1-[A-Za-z0-9]{10,}")
        self.assertNotRegex(body, r"ghp_[A-Za-z0-9]{20,}")
        if r.returncode == 0:
            data = json.loads(r.stdout)
            self.assertEqual(data["feature"], "F80")
            self.assertTrue(data.get("dry_run"))

    def test_status_json(self):
        r = _run(["status"])
        # 0 if ready, 1 if not — both ok for structure
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F80")
        self.assertIn("openrouter_secret", data)
        self.assertIn("modal_present", data)


if __name__ == "__main__":
    unittest.main()
