#!/usr/bin/env python3
"""Tests for F68 agent_tools_pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_tools_pipeline.py"


class AgentToolsPipelineTests(unittest.TestCase):
    def test_research_eval_adopt_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # minimal tree
            (root / "agent" / "tools").mkdir(parents=True)
            (root / "docs" / "experiments").mkdir(parents=True)
            catalog = {
                "schema_version": 1,
                "feature": "F68",
                "tools": [
                    {
                        "id": "terminal",
                        "status": "adopted",
                        "toolset": "terminal",
                    }
                ],
                "candidates": [],
            }
            (root / "agent" / "tools" / "catalog.json").write_text(
                json.dumps(catalog), encoding="utf-8"
            )
            # fake agent-loop with zero tools
            loop_dir = root / "runs" / "x" / "agent-loop"
            loop_dir.mkdir(parents=True)
            (loop_dir / "agent-loop.json").write_text(
                json.dumps(
                    {
                        "tool_call_turns": 0,
                        "message_count": 2,
                        "messages": [],
                        "steps": [],
                    }
                ),
                encoding="utf-8",
            )
            # ROI backlog line
            (root / "docs" / "experiments" / "hermes-inspired-roi.md").write_text(
                "| H3 | Skill-file evolution | L | quality | backlog |\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["TORII_ROOT"] = str(root)

            r = subprocess.run(
                [sys.executable, str(SCRIPT), "research", "--runs", str(root)],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("new_candidates=", r.stdout)

            cat = json.loads(
                (root / "agent" / "tools" / "catalog.json").read_text(encoding="utf-8")
            )
            self.assertGreaterEqual(len(cat["candidates"]), 1)
            cid = cat["candidates"][0]["id"]

            r2 = subprocess.run(
                [sys.executable, str(SCRIPT), "eval", "--candidate", cid, "--runs", str(root)],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)

            # force adopt workflow tool
            r3 = subprocess.run(
                [sys.executable, str(SCRIPT), "adopt", cid, "--force"],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r3.returncode, 0, r3.stderr + r3.stdout)
            self.assertTrue((root / "agent" / "tools" / "adopted" / f"{cid}.json").is_file())
            self.assertTrue((root / "agent" / "tools" / "active-toolsets.txt").is_file())

            r4 = subprocess.run(
                [sys.executable, str(SCRIPT), "status"],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r4.returncode, 0)
            self.assertIn("adopted=", r4.stdout)

    def test_toolsets_default_terminal(self):
        env = os.environ.copy()
        env["TORII_ROOT"] = str(ROOT)
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "toolsets"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("terminal", r.stdout)


if __name__ == "__main__":
    unittest.main()
