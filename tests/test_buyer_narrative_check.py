"""Buyer narrative surface checks (one diagram, F-IDs behind Advanced)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "buyer_narrative_check.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT)},
        timeout=60,
    )


class BuyerNarrativeTests(unittest.TestCase):
    def test_diagram_exists(self):
        p = ROOT / "docs" / "brand" / "BUYER-DIAGRAM.md"
        self.assertTrue(p.is_file())
        t = p.read_text(encoding="utf-8")
        self.assertIn("stricter and quieter", t.lower())
        self.assertIn("torii/gate", t)

    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertEqual(data["scorecard_target"], "8.0")
        self.assertLessEqual(data["counts"]["landing_primary_f"], 3)
        self.assertLessEqual(data["counts"]["product_primary_f"], 8)

    def test_cli_umbrella(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "torii.py"), "buyer", "--", "status"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_ROOT": str(ROOT)},
            timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("fixture_pass"))


if __name__ == "__main__":
    unittest.main()
