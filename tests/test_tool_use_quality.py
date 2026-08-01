"""Tests for agent tool-use quality product surface."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tool_use_quality.py"
BUYER = ROOT / "docs" / "TOOL-USE.md"


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


class ToolUseQualityTests(unittest.TestCase):
    def test_script_and_buyer_doc(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(BUYER.is_file())
        text = BUYER.read_text(encoding="utf-8")
        self.assertIn("tool_turns_gate", text)
        self.assertIn("tools-as-code", text.lower())

    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["buyer_doc_ok"])
        self.assertTrue(data["tool_turns_gate_ok"])

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "TOOL_USE")
        self.assertIsNotNone(data.get("measured_n"))

    def test_report_writes(self):
        r = _run(["report", "--json", "--allow-partial"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "TOOL_USE")
        self.assertIn("aggregate", data)
        md = ROOT / "docs" / "benchmarks" / "tool-use-quality.md"
        js = ROOT / "docs" / "benchmarks" / "tool-use-quality.json"
        self.assertTrue(md.is_file())
        self.assertTrue(js.is_file())
        body = md.read_text(encoding="utf-8")
        self.assertIn("torii-tool-use-quality", body)
        self.assertIn("tool_use_rate", body)

    def test_aggregate_hermetic(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import tool_use_quality as t  # type: ignore

        rows = [
            {
                "trace_id": "a",
                "tool_call_turns": 0,
                "tool_names": [],
                "quality_band": "zero",
            },
            {
                "trace_id": "b",
                "tool_call_turns": 4,
                "tool_names": ["terminal", "terminal"],
                "quality_band": "solid",
            },
            {
                "trace_id": "c",
                "tool_call_turns": 6,
                "tool_names": ["terminal"],
                "quality_band": "deep",
            },
        ]
        agg = t.aggregate(rows)
        self.assertEqual(agg["measured_n"], 3)
        self.assertAlmostEqual(agg["tool_use_rate"], 2 / 3, places=3)
        self.assertTrue(agg["quality_ok"])
        self.assertGreater(agg["quality_score"], 0.3)

    def test_cli_umbrella(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "torii.py"), "tool-use", "--", "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_ROOT": str(ROOT)},
            timeout=60,
        )
        if r.returncode != 0 and "unknown" in (r.stderr + r.stdout).lower():
            self.skipTest("torii.py tool-use not wired yet")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("fixture_pass"))


if __name__ == "__main__":
    unittest.main()
