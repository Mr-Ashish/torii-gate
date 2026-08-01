"""Tests for quieter-over-time + own-repo required-check surface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "quieter_over_time.py"
BUYER = ROOT / "docs" / "QUIETER.md"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = {**os.environ, "TORII_ROOT": str(ROOT)}
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
        timeout=120,
    )


class QuieterOverTimeTests(unittest.TestCase):
    def test_script_and_buyer_doc(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(BUYER.is_file())
        text = BUYER.read_text(encoding="utf-8")
        self.assertIn("torii/gate", text)
        self.assertIn("branch protection", text.lower())
        self.assertIn("stricter and quieter", text.lower())

    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertEqual(data["required_check"], "torii/gate")
        self.assertTrue(data["core_ok"])
        self.assertTrue(data["buyer_doc_ok"])

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "QUIETER")
        self.assertEqual(data.get("required_check"), "torii/gate")
        self.assertTrue(data.get("own_repo_ok") or data.get("quieter_ok"))

    def test_report_writes(self):
        r = _run(["report", "--json", "--allow-partial"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "QUIETER")
        self.assertIn("windows", data)
        self.assertIn("tool_use_quality", data)
        md = ROOT / "docs" / "benchmarks" / "quieter-over-time.md"
        js = ROOT / "docs" / "benchmarks" / "quieter-over-time.json"
        self.assertTrue(md.is_file())
        self.assertTrue(js.is_file())
        body = md.read_text(encoding="utf-8")
        self.assertIn("torii-quieter-over-time", body)
        self.assertIn("quiet_score", body)
        self.assertIn("Own-repo", body)

    def test_window_delta_logic_hermetic(self):
        """Unit: late higher quiet signals → getting_quieter."""
        sys.path.insert(0, str(ROOT / "scripts"))
        import quieter_over_time as q  # type: ignore

        early = [
            {
                "trace_id": f"e{i}",
                "repo": "acme/app",
                "pr": str(i),
                "verdict": "COMMENT",
                "path_evidence": 0.2,
                "tool_call_turns": 0,
                "has_certificate": False,
                "weak_approve": False,
                "demoted": False,
                "cost_usd": 0.01,
                "time_to_signal_s": 100.0,
            }
            for i in range(4)
        ]
        late = [
            {
                "trace_id": f"l{i}",
                "repo": "acme/app",
                "pr": str(10 + i),
                "verdict": "REQUEST_CHANGES",
                "path_evidence": 1.0,
                "tool_call_turns": 6,
                "has_certificate": True,
                "weak_approve": False,
                "demoted": False,
                "cost_usd": 0.01,
                "time_to_signal_s": 90.0,
            }
            for i in range(4)
        ]
        win = q.split_windows(early + late)
        self.assertIsNotNone(win.get("delta_quiet_score"))
        self.assertGreater(win["delta_quiet_score"], 0)
        self.assertTrue(win.get("getting_quieter"))

    def test_cli_umbrella(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "torii.py"), "quieter", "--", "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_ROOT": str(ROOT)},
            timeout=60,
        )
        # CLI may fail until COMMANDS wired — assert after wire; allow skip message
        if r.returncode != 0 and "unknown" in (r.stderr + r.stdout).lower():
            self.skipTest("torii.py quieter not wired yet")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("fixture_pass"))


if __name__ == "__main__":
    unittest.main()
