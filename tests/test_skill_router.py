"""Tests for F84 progressive skill router + hit scoring."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_router.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {**os.environ, "TORII_SKILL_ROUTER": "1"}
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class SkillRouterTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["sec_ok"])
        self.assertTrue(data["stripped_ok"])
        self.assertGreater(data["good_hit_rate"], data["weak_hit_rate"])

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F84")
        self.assertTrue(data["enabled"])

    def test_index_has_active(self):
        r = _run(["index"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertGreaterEqual(data["n"], 1)
        ids = [s["id"] for s in data["skills"]]
        self.assertTrue(any("f74" in i or "tool" in i for i in ids))

    def test_select_py_prefers_security(self):
        r = _run(
            [
                "select",
                "--paths",
                "src/auth.py",
                "lib/db.py",
                "--max",
                "4",
            ]
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        sel = set(data["selected"])
        # at least one always or f74 skill
        self.assertTrue(
            sel
            & {
                "skill-tool-depth-hunks",
                "skill-preserve-deep-tools",
                "skill-f74-prefer-chain-json",
                "skill-f74-exploit-scenario",
            },
            sel,
        )

    def test_inject_writes_marker(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = Path(td) / "prompt.md"
            prompt.write_text(
                "<!-- torii-f69-skills -->\nbulk\n<!-- /torii-f69-skills -->\n\n## PR metadata\nx\n",
                encoding="utf-8",
            )
            r = _run(
                [
                    "inject",
                    "--prompt",
                    str(prompt),
                    "--paths",
                    "app/main.py",
                    "--force",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertEqual(data.get("injected"), 1)
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("torii-f84-skill-router", text)
            self.assertIn("Skill router (F84", text)

    def test_install_ships_skill_router(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "target"
            dest.mkdir()
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((dest / "scripts" / "skill_router.py").is_file())

    def test_f114_memory_skill_always_on(self):
        """F114: skill-prefer-memory-cli-early is always routed when active."""
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data.get("f114") or data.get("tool_outcome"))
        active = ROOT / "agent" / "skills" / "active" / "skill-prefer-memory-cli-early.md"
        if active.is_file():
            self.assertIn("skill-prefer-memory-cli-early", data.get("always") or [])
            self.assertIn(
                "skill-prefer-memory-cli-early",
                data.get("tool_probe_skills") or [],
            )

    def test_f114_tool_outcome_score(self):
        """F114: memory skill hits via agent-loop torii.py memory, not prose."""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            review = td_path / "review.md"
            review.write_text("# Verdict\nLGTM no findings.\nAPPROVE\n", encoding="utf-8")
            loop = {
                "schema_version": 1,
                "tool_call_turns": 1,
                "steps": [
                    {
                        "step": 0,
                        "kind": "assistant_tool_calls",
                        "tool_calls": [
                            {
                                "name": "terminal",
                                "arguments_preview": json.dumps(
                                    {
                                        "command": (
                                            "python3 scripts/torii.py memory -- "
                                            'search -- -q "auth"'
                                        )
                                    }
                                ),
                            }
                        ],
                    }
                ],
                "messages": [],
            }
            loop_path = td_path / "agent-loop.json"
            loop_path.write_text(json.dumps(loop) + "\n", encoding="utf-8")
            r = _run(
                [
                    "score",
                    "--review",
                    str(review),
                    "--out-dir",
                    str(td_path),
                    "--selected",
                    "skill-prefer-memory-cli-early",
                    "--agent-loop",
                    str(loop_path),
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertTrue(data.get("f114"))
            hits = {h["id"]: h for h in data.get("hits") or []}
            if "skill-prefer-memory-cli-early" in hits:
                h = hits["skill-prefer-memory-cli-early"]
                self.assertTrue(h.get("tool_hit"), h)
                self.assertTrue(h.get("hit"), h)
                self.assertFalse(h.get("prose_hit"), h)


if __name__ == "__main__":
    unittest.main()
