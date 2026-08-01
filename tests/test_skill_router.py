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
        # F119 always budget
        self.assertTrue(data.get("f119") or data.get("feature_always_budget") == "F119")
        self.assertTrue(data.get("product_in_py"), data)
        self.assertIn("skill-prefer-product-cli", data.get("always_selected") or [])
        # F120 SkillReducer compact
        self.assertTrue(data.get("f120") or data.get("feature_compact") == "F120")
        self.assertTrue(data.get("compact_ok"), data)
        self.assertTrue(data.get("smaller_ok"), data)
        self.assertGreaterEqual(int(data.get("f120_chars_saved") or 0), 1)
        # F121 recovery util
        self.assertTrue(data.get("f121") or data.get("feature_util") == "F121")
        self.assertTrue(data.get("util_ok"), data)
        self.assertTrue(data.get("util_gap"), data)
        self.assertGreaterEqual(float(data.get("util_rate_good") or 0), 1.0)

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
        # F119: recovery always (memory/product/critic) or f74/tool always
        self.assertTrue(
            sel
            & {
                "skill-prefer-memory-cli-early",
                "skill-prefer-product-cli",
                "skill-prefer-critic-early",
                "skill-tool-depth-hunks",
                "skill-preserve-deep-tools",
                "skill-f74-prefer-chain-json",
                "skill-f74-exploit-scenario",
            },
            sel,
        )
        # recovery skills win always budget over soft tool-depth
        always_sel = set(data.get("always_selected") or [])
        if always_sel:
            self.assertIn("skill-prefer-memory-cli-early", always_sel)

    def test_f119_always_budget_priority(self):
        """F119: ALWAYS_MAX keeps product-cli over soft always tool-depth."""
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "select",
                "--paths",
                "demo/insecure/app.py",
                "--max",
                "4",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "TORII_SKILL_ROUTER_ALWAYS_MAX": "3"},
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        always_sel = data.get("always_selected") or []
        always_def = data.get("always_deferred") or []
        self.assertIn("skill-prefer-memory-cli-early", always_sel)
        self.assertIn("skill-prefer-product-cli", always_sel)
        self.assertIn("skill-prefer-critic-early", always_sel)
        # soft always deferred under budget=3 with 5 always candidates
        self.assertTrue(
            "skill-tool-depth-hunks" in always_def
            or "skill-preserve-deep-tools" in always_def,
            data,
        )
        sel = set(data.get("selected") or [])
        self.assertIn("skill-prefer-product-cli", sel)

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
            # F120: pack ships dual-gate recovery skills
            for name in (
                "skill-prefer-memory-cli-early.md",
                "skill-prefer-product-cli.md",
                "skill-prefer-critic-early.md",
            ):
                self.assertTrue(
                    (dest / "agent" / "skills" / "active" / name).is_file(),
                    f"pack missing {name}",
                )

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


    def test_f121_recovery_util_command(self):
        """F121: util scores tool hits vs idle recovery skills."""
        with tempfile.TemporaryDirectory() as td:
            od = Path(td)
            (od / "skill-router.json").write_text(
                json.dumps(
                    {
                        "selected": ["skill-prefer-product-cli"],
                        "always_selected": ["skill-prefer-product-cli"],
                        "inject_chars": 420,
                        "f120_chars_saved": 100,
                    }
                ),
                encoding="utf-8",
            )
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": "skill-prefer-product-cli",
                                "hit": False,
                                "tool_hit": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            r = _run(["util", "--out-dir", str(od)])
            self.assertEqual(r.returncode, 1, r.stderr + r.stdout)  # gap → rc 1
            data = json.loads(r.stdout)
            self.assertEqual(data.get("feature"), "F121")
            self.assertTrue(data.get("utilization_gap"))
            self.assertEqual(int(data.get("inject_chars") or 0), 420)
            self.assertTrue((od / "recovery-skill-util.json").is_file())


    def test_f122_recovery_reprompt_decide(self):
        """F122: reprompt-decide fires on util gap with tools; defers zero tools."""
        with tempfile.TemporaryDirectory() as td:
            od = Path(td)
            (od / "skill-router.json").write_text(
                json.dumps(
                    {
                        "selected": ["skill-prefer-product-cli"],
                        "always_selected": ["skill-prefer-product-cli"],
                        "inject_chars": 400,
                    }
                ),
                encoding="utf-8",
            )
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": "skill-prefer-product-cli",
                                "hit": False,
                                "tool_hit": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (od / "agent-loop").mkdir()
            (od / "agent-loop" / "agent-loop.json").write_text(
                json.dumps({"tool_call_turns": 3}), encoding="utf-8"
            )
            r = _run(["reprompt-decide", "--out-dir", str(od)])
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("reprompt=1", r.stdout)
            self.assertIn("feature=F122", r.stdout)
            # zero tools defers
            (od / "agent-loop" / "agent-loop.json").write_text(
                json.dumps({"tool_call_turns": 0}), encoding="utf-8"
            )
            r2 = _run(["reprompt-decide", "--out-dir", str(od), "--tool-turns", "0"])
            self.assertIn("reprompt=0", r2.stdout)
            self.assertIn("zero_tools_defer_f49", r2.stdout)


    def test_f124_federate_util(self):
        """F124: util federate emits privacy-safe recovery themes."""
        with tempfile.TemporaryDirectory() as td:
            od = Path(td)
            (od / "skill-router.json").write_text(
                json.dumps(
                    {
                        "selected": ["skill-prefer-memory-cli-early"],
                        "always_selected": ["skill-prefer-memory-cli-early"],
                        "inject_chars": 1200,
                        "f120_chars_saved": 400,
                    }
                ),
                encoding="utf-8",
            )
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": "skill-prefer-memory-cli-early",
                                "tool_hit": True,
                                "hit": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            env = {**os.environ, "TORII_ROOT": str(ROOT), "TORII_MEMORY_TENANT": "tenant-z"}
            r = _run(["util", "--out-dir", str(od)], env=env)
            # util may return 0 when ok
            data = json.loads(r.stdout)
            self.assertIn("federate", data)
            self.assertTrue(data["federate"].get("privacy_ok"), data)
            self.assertGreaterEqual(int(data["federate"].get("fed_n") or 0), 1)
            fed_path = Path(data["federate"]["fed_path"])
            self.assertTrue(fed_path.is_file())
            fed = json.loads(fed_path.read_text(encoding="utf-8"))
            blob = json.dumps(fed)
            self.assertNotIn("/Users/", blob)
            self.assertNotIn("tenant-z", blob)


if __name__ == "__main__":
    unittest.main()
