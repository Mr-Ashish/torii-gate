"""Tests for F105 memory tool-use auditor."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "memory_tool_audit.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    e = {**os.environ, "TORII_ROOT": str(ROOT), "TORII_MEMORY_TOOL_AUDIT": "1"}
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
        timeout=90,
    )


class MemoryToolAuditTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreaterEqual(data["delta"], 0.4)
        self.assertTrue(data["weak_gap"])
        # F141 federate
        self.assertTrue(data.get("f141") or data.get("feature_federate") == "F141")
        self.assertTrue(data.get("f141_ok"), data)
        self.assertTrue(data.get("f141_privacy_ok"), data)
        self.assertGreaterEqual(int(data.get("f141_fed_good_n") or 0), 1)
        self.assertGreaterEqual(int(data.get("f141_fed_weak_n") or 0), 1)
        # F142 hub post-score
        self.assertTrue(data.get("f142") or data.get("feature_hub") == "F142")
        self.assertTrue(data.get("f142_ok"), data)
        self.assertGreaterEqual(int(data.get("f142_hub_delta") or 0), 5)
        self.assertEqual(int(data.get("f142_hub_inject") or 0), 1)

    def test_scan_detects_torii_memory(self):
        with tempfile.TemporaryDirectory() as td:
            loop = {
                "tool_call_turns": 1,
                "steps": [
                    {
                        "kind": "assistant_tool_calls",
                        "tool_calls": [
                            {
                                "name": "terminal",
                                "arguments_preview": json.dumps(
                                    {
                                        "command": "python3 scripts/torii_memory.py search -- -q pickle"
                                    }
                                ),
                            }
                        ],
                    }
                ],
                "messages": [],
            }
            lp = Path(td) / "loop.json"
            lp.write_text(json.dumps(loop))
            r = _run(["scan", "--loop", str(lp)])
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertGreaterEqual(data["hit_count"], 1)
            self.assertIn("torii_memory", data["tools_used"])

    def test_f114_scan_detects_product_cli_memory(self):
        """F114: torii.py memory (product umbrella) counts as utilization."""
        with tempfile.TemporaryDirectory() as td:
            loop = {
                "tool_call_turns": 1,
                "steps": [
                    {
                        "kind": "assistant_tool_calls",
                        "tool_calls": [
                            {
                                "name": "terminal",
                                "arguments_preview": json.dumps(
                                    {
                                        "command": (
                                            "python3 scripts/torii.py memory -- "
                                            'search -- -q "auth OR sql"'
                                        )
                                    }
                                ),
                            }
                        ],
                    }
                ],
                "messages": [],
            }
            lp = Path(td) / "loop.json"
            lp.write_text(json.dumps(loop))
            r = _run(["scan", "--loop", str(lp)])
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertGreaterEqual(data["hit_count"], 1)
            self.assertIn("torii_product_memory", data["tools_used"])

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F105")
        self.assertEqual(data["reprompt_feature"], "F106")

    def test_reprompt_decide_gap(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "agent-loop").mkdir()
            loop = {
                "tool_call_turns": 3,
                "steps": [
                    {
                        "kind": "assistant_tool_calls",
                        "tool_calls": [
                            {
                                "name": "terminal",
                                "arguments_preview": json.dumps(
                                    {"command": "cat pr.diff"}
                                ),
                            }
                        ],
                    }
                ],
                "messages": [],
            }
            (td_path / "agent-loop" / "agent-loop.json").write_text(json.dumps(loop))
            (td_path / "prompt.md").write_text(
                "<!-- torii-f103-memory-cli -->\npython3 scripts/torii_memory.py help\n"
            )
            r = _run(
                [
                    "reprompt-decide",
                    "--out-dir",
                    str(td_path),
                    "--prompt",
                    str(td_path / "prompt.md"),
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("reprompt=1", r.stdout)
            self.assertIn("reason=utilization_gap", r.stdout)

    def test_reprompt_write(self):
        with tempfile.TemporaryDirectory() as td:
            pin = Path(td) / "in.md"
            pout = Path(td) / "out.md"
            pin.write_text("# review\n")
            r = _run(
                [
                    "reprompt-write",
                    "--prompt-in",
                    str(pin),
                    "--prompt-out",
                    str(pout),
                    "--hit-count",
                    "0",
                    "--tool-turns",
                    "2",
                    "--path",
                    "app.py",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            body = pout.read_text()
            self.assertIn("F106", body)
            self.assertIn("torii_memory.py search", body)

    def test_disabled_skips(self):
        with tempfile.TemporaryDirectory() as td:
            r = _run(
                ["audit", "--out-dir", td],
                env={"TORII_MEMORY_TOOL_AUDIT": "0"},
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue(json.loads(r.stdout).get("skipped"))

    def test_f130_util_eval(self):
        """F130: paper memory util pack good>>weak for product scorecard."""
        with tempfile.TemporaryDirectory() as td:
            r = _run(["util-eval", "--out-dir", td])
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertEqual(data.get("feature"), "F130")
            self.assertTrue(data.get("eval_pass"), data)
            self.assertGreaterEqual(float(data.get("delta") or 0), 0.4)
            self.assertEqual(
                (data.get("paper") or {}).get("metric"), "memory_tool_util_delta"
            )
            art = Path(td) / "memory-util-eval.json"
            self.assertTrue(art.is_file())
            blob = art.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", blob)

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
            self.assertTrue((dest / "scripts" / "memory_tool_audit.py").is_file())


if __name__ == "__main__":
    unittest.main()
