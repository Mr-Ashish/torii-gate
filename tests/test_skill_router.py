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


if __name__ == "__main__":
    unittest.main()
