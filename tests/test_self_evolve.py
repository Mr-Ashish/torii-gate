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


if __name__ == "__main__":
    unittest.main()
