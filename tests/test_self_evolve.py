#!/usr/bin/env python3
"""Tests for F69 self_evolve."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "self_evolve.py"


class SelfEvolveTests(unittest.TestCase):
    def test_f117_fixture(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_TOOL_PROBE_MINE": "1"},
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["match_ok"])
        self.assertTrue(data["prop_product"])
        self.assertIn("skill-prefer-product-cli", data.get("observed_skills") or [])

    def test_f112_memory_recovery_signal_and_proposal(self):
        """F112: f106 recovery / utilization gap → skill-prefer-memory-cli-early."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out"
            loop = out / "agent-loop"
            loop.mkdir(parents=True)
            (loop / "agent-loop.json").write_text(
                json.dumps(
                    {
                        "tool_call_turns": 8,
                        "message_count": 12,
                        "messages": [],
                        "session_id": "sess-f112",
                        "model": "deepseek/deepseek-v4-pro",
                    }
                ),
                encoding="utf-8",
            )
            (out / "memory-tool-reprompt.env").write_text(
                "reprompt=1\nattempted=1\nrecovered=1\nreason=reprompt_recovered\n"
                "hit_count_before=0\nhit_count_after=5\nfeature=F106\n",
                encoding="utf-8",
            )
            (out / "memory-tool-audit.json").write_text(
                json.dumps(
                    {
                        "feature": "F105",
                        "hit_count": 5,
                        "tools_used": ["torii_memory"],
                        "utilization_gap": False,
                        "inject_offered": True,
                    }
                ),
                encoding="utf-8",
            )
            (out / "review-1.md").write_text(
                "**Verdict:** REQUEST CHANGES\n", encoding="utf-8"
            )
            (root / "agent" / "skills" / "active").mkdir(parents=True)
            (root / "agent" / "skills" / "proposals").mkdir(parents=True)

            env = os.environ.copy()
            env["TORII_ROOT"] = str(root)
            env["TORII_EVOLUTION_ROOT"] = str(root / "memory" / "evolution")

            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "ingest",
                    "--out-dir",
                    str(out),
                    "--pr",
                    "191813",
                    "--repo",
                    "pytorch/pytorch",
                ],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("f106_recovered", r.stdout)
            self.assertIn("memory_tools_used", r.stdout)

            r2 = subprocess.run(
                [sys.executable, str(SCRIPT), "propose", "--limit", "8"],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            prop = root / "agent" / "skills" / "proposals" / "skill-prefer-memory-cli-early.md"
            self.assertTrue(prop.is_file(), r2.stdout + str(list((root / "agent/skills/proposals").glob("*"))))
            body = prop.read_text(encoding="utf-8")
            self.assertIn("F112", body)
            self.assertIn("torii_memory", body)

    def test_ingest_propose_eval_adopt_inject(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out"
            loop = out / "agent-loop"
            loop.mkdir(parents=True)
            (loop / "agent-loop.json").write_text(
                json.dumps(
                    {
                        "tool_call_turns": 0,
                        "message_count": 3,
                        "messages": [{"role": "user"}],
                        "session_id": "sess-test",
                        "model": "test-model",
                    }
                ),
                encoding="utf-8",
            )
            (out / "review-1.md").write_text(
                "## R\n\n**Verdict:** APPROVE\n\n### Summary\nok\n",
                encoding="utf-8",
            )
            (out / "tool-turns-reprompt.env").write_text(
                "reprompt=1\nrecovered=1\n", encoding="utf-8"
            )
            (root / "agent" / "skills" / "active").mkdir(parents=True)
            (root / "agent" / "skills" / "proposals").mkdir(parents=True)

            env = os.environ.copy()
            env["TORII_ROOT"] = str(root)
            env["TORII_EVOLUTION_ROOT"] = str(root / "memory" / "evolution")

            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "ingest",
                    "--out-dir",
                    str(out),
                    "--pr",
                    "1",
                    "--repo",
                    "acme/widgets",
                ],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("trajectory=", r.stdout)
            self.assertIn("zero_tools", r.stdout)

            r2 = subprocess.run(
                [sys.executable, str(SCRIPT), "propose", "--limit", "5"],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            props = list((root / "agent" / "skills" / "proposals").glob("*.md"))
            self.assertGreaterEqual(len(props), 1)

            r3 = subprocess.run(
                [sys.executable, str(SCRIPT), "eval", "--proposal", "all"],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r3.returncode, 0, r3.stderr)

            pid = props[0].stem
            r4 = subprocess.run(
                [sys.executable, str(SCRIPT), "adopt", pid, "--force"],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r4.returncode, 0, r4.stderr + r4.stdout)
            self.assertTrue((root / "agent" / "skills" / "active" / f"{pid}.md").is_file())

            prompt = out / "prompt.md"
            prompt.write_text(
                "# Task\n\n## PR metadata\n\n- **Repo:** x\n",
                encoding="utf-8",
            )
            r5 = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "inject",
                    "--prompt",
                    str(prompt),
                ],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r5.returncode, 0, r5.stderr)
            body = prompt.read_text(encoding="utf-8")
            self.assertIn("torii-f69-skills", body)
            self.assertIn("Evolved skills", body)

            r6 = subprocess.run(
                [sys.executable, str(SCRIPT), "status"],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r6.returncode, 0)
            self.assertIn("active_skills=", r6.stdout)

    def test_f132_propose_scorecard_gaps(self):
        """F132: scorecard gap themes yield skill proposals (no home paths)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".torii").mkdir()
            (root / "agent" / "skills" / "proposals").mkdir(parents=True)
            (root / "agent" / "skills" / "active").mkdir(parents=True)
            (root / "memory" / "evolution").mkdir(parents=True)
            sc = {
                "brand_ready": False,
                "metrics": {
                    "workflow_ok": False,
                    "demote_eval_pass": False,
                    "memory_util_eval_pass": False,
                    "recovery_hub_gap_ok": True,
                    "recovery_ok": True,
                    "skill_loop_level": "L3",
                    "memory_loop_level": "L3",
                    "workflow_level": "L1",
                },
            }
            sc_path = root / ".torii" / "product-scorecard.json"
            sc_path.write_text(json.dumps(sc) + "\n", encoding="utf-8")
            env = {**os.environ, "TORII_ROOT": str(root)}
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "propose-scorecard",
                    "--scorecard",
                    str(sc_path),
                    "--limit",
                    "4",
                ],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertEqual(data.get("feature"), "F132")
            self.assertGreaterEqual(int(data.get("created_n") or 0), 2)
            self.assertIn("workflow_ok", data.get("gaps") or [])
            props = list((root / "agent" / "skills" / "proposals").glob("skill-prefer-*.md"))
            self.assertGreaterEqual(len(props), 2)
            for p in props:
                body = p.read_text(encoding="utf-8")
                self.assertNotIn("/Users/", body)
                self.assertIn("F132", body)


if __name__ == "__main__":
    unittest.main()
