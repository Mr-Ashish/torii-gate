"""Tests for F83 eval trace report + pack skills ship."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_trace_report.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ},
    )


class EvalTraceReportTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertGreaterEqual(data["n_runs"], 1)
        self.assertTrue(data["privacy_ok"])
        self.assertTrue(Path(data["out_md"]).is_file())

    def test_report_aggregate_fields(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        agg = data["aggregate"]
        self.assertIn("n_runs", agg)
        self.assertIn("n_modal", agg)

    def test_install_ships_skills(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "target"
            dest.mkdir()
            # init fake git? install may not need
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            active = dest / "agent" / "skills" / "active"
            self.assertTrue(active.is_dir(), "skills/active missing from pack")
            f74 = list(active.glob("skill-f74-*.md"))
            self.assertGreaterEqual(len(f74), 1, "F74 skills not shipped")
            tools = dest / "agent" / "tools"
            self.assertTrue(tools.is_dir() or (tools / "catalog.json").is_file() or (dest / "agent" / "tools" / "catalog.json").exists())


if __name__ == "__main__":
    unittest.main()
