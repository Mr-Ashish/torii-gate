"""Tests for F88 per-skill contribution attribution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_attribution.py"
ADOPT = ROOT / "scripts" / "skill_auto_adopt.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(script: Path, args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {**os.environ, "TORII_SKILL_ATTRIBUTION": "1", "TORII_SKILL_AUTO_ADOPT_ATTR": "1"}
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class SkillAttributionTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(SCRIPT, ["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreaterEqual(data["n_contributing"], 1)
        self.assertTrue(data["proposal_free_rider"]["free_rider"])
        self.assertGreater(data["proposal_good"]["contribution"], 0)

    def test_status(self):
        r = _run(SCRIPT, ["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(json.loads(r.stdout)["feature"], "F88")

    def test_gate_includes_f88(self):
        r = _run(ADOPT, ["gate"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        names = [g["name"] for g in data.get("gates") or []]
        self.assertIn("f88_skill_attribution", names)
        self.assertTrue(data.get("passed"))

    def test_cycle_writes_ledger(self):
        r = _run(SCRIPT, ["cycle", "--review", str(ROOT / "docs/benchmarks/fixtures/insecure-demo-good-review.md")])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "F89")
        self.assertTrue(Path(data["ledger"]).is_file() or "skill-attribution" in data["ledger"])

    def test_router_skips_free_rider_from_ledger(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            lp = Path(td) / "skill-attribution.json"
            lp.write_text(json.dumps({
                "schema_version": 1,
                "feature": "F89",
                "skills": {
                    "skill-soft-tool-nudge": {
                        "id": "skill-soft-tool-nudge",
                        "n": 3, "contribution_sum": 0.0, "solo_hits": 0,
                        "free_rider_n": 3, "avg_contribution": 0.0, "free_rider": True,
                    },
                    "skill-f74-prefer-chain-json": {
                        "id": "skill-f74-prefer-chain-json",
                        "n": 3, "contribution_sum": 6.0, "solo_hits": 3,
                        "free_rider_n": 0, "avg_contribution": 2.0, "free_rider": False,
                    },
                },
                "free_riders": ["skill-soft-tool-nudge"],
                "history": [],
            }))
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "skill_router.py"),
                 "select", "--paths", "demo/insecure/app.py", "--max", "4"],
                cwd=str(ROOT), capture_output=True, text=True,
                env={**os.environ, "TORII_ROOT": str(ROOT),
                     "TORII_SKILL_ATTR_FILE": str(lp),
                     "TORII_SKILL_ATTRIBUTION": "1",
                     "TORII_SKILL_ATTR_ROUTER": "1",
                     "TORII_SKILL_FITNESS": "0"},
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertIn("skill-soft-tool-nudge", data.get("free_rider_skipped") or [])
            self.assertNotIn("skill-soft-tool-nudge", data.get("selected") or [])

    def test_install_ships(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "t"
            dest.mkdir()
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((dest / "scripts" / "skill_attribution.py").is_file())


if __name__ == "__main__":
    unittest.main()
