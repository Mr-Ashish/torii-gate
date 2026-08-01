"""Enterprise light: org isolation docs + federation privacy audit."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enterprise_surface.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(ROOT)},
        timeout=120,
    )


class EnterpriseSurfaceTests(unittest.TestCase):
    def test_docs(self):
        for name in ("README.md", "ORG-ISOLATION.md", "PRIVACY.md"):
            p = ROOT / "docs" / "enterprise" / name
            self.assertTrue(p.is_file(), name)
        org = (ROOT / "docs" / "enterprise" / "ORG-ISOLATION.md").read_text(encoding="utf-8")
        priv = (ROOT / "docs" / "enterprise" / "PRIVACY.md").read_text(encoding="utf-8")
        self.assertIn("torii/gate", org)
        self.assertIn("tenant", org.lower())
        self.assertIn("path", priv.lower())
        self.assertIn("snippet", priv.lower())
        self.assertIn("hash", priv.lower())
        fed = ROOT / "docs" / "FEDERATION.md"
        self.assertTrue(fed.is_file())
        fed_txt = fed.read_text(encoding="utf-8")
        self.assertIn("torii/gate", fed_txt)
        self.assertIn("tenant hash", fed_txt.lower())

    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertEqual(data["scorecard_target"], "enterprise")
        self.assertTrue(data["checks"]["federation_all_ok"])
        self.assertTrue(data["checks"]["hub_fixture"])
        self.assertTrue(data["checks"].get("docs_federation_buyer"), data["checks"])
        self.assertTrue(data["checks"].get("docs_federation_buyer_gate"), data["checks"])

    def test_report(self):
        r = _run(["report", "--json", "--allow-partial"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "ENTERPRISE")
        self.assertTrue((ROOT / "docs" / "enterprise" / "SURFACE.md").is_file())
        body = (ROOT / "docs" / "enterprise" / "SURFACE.md").read_text(encoding="utf-8")
        self.assertIn("Federation privacy audit", body)
        self.assertIn("Guarantees", body)

    def test_no_home_paths_in_federation(self):
        fed = ROOT / "memory" / "federation"
        for p in fed.glob("*.json"):
            text = p.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("/Users/", text, p.name)
            self.assertNotIn("/home/", text, p.name)


if __name__ == "__main__":
    unittest.main()
