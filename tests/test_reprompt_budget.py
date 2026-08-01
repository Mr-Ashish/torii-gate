"""Tests for F108 shared re-prompt budget."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reprompt_budget.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    e = {
        **os.environ,
        "TORII_ROOT": str(ROOT),
        "TORII_REPROMPT_BUDGET": "1",
        "TORII_REPROMPT_MAX_EXTRA": "1",
    }
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
        timeout=30,
    )


class RepromptBudgetTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)

    def test_init_allow_consume(self):
        with tempfile.TemporaryDirectory() as td:
            r = _run(["init", "--out-dir", td, "--max-extra", "1"])
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            r = _run(["allow", "--out-dir", td, "--kind", "f49"])
            self.assertIn("allow=1", r.stdout)
            r = _run(["consume", "--out-dir", td, "--kind", "f49"])
            self.assertEqual(r.returncode, 0)
            r = _run(["allow", "--out-dir", td, "--kind", "f106"])
            self.assertIn("allow=0", r.stdout)
            self.assertIn("budget_exhausted", r.stdout)

    def test_max_two_allows_both(self):
        with tempfile.TemporaryDirectory() as td:
            _run(["init", "--out-dir", td, "--max-extra", "2"])
            r1 = _run(["allow", "--out-dir", td, "--kind", "f49"])
            self.assertIn("allow=1", r1.stdout)
            _run(["consume", "--out-dir", td, "--kind", "f49"])
            r2 = _run(["allow", "--out-dir", td, "--kind", "f106"])
            self.assertIn("allow=1", r2.stdout)

    def test_install_ships(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "t"
            dest.mkdir()
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((dest / "scripts" / "reprompt_budget.py").is_file())


if __name__ == "__main__":
    unittest.main()
