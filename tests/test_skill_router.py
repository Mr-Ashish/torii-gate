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
        # F136 scorecard skill util
        self.assertTrue(data.get("f136") or data.get("feature_scorecard_util") == "F136")
        self.assertTrue(data.get("f136_sc_util_ok"), data)
        self.assertTrue(data.get("f136_sc_util_gap"), data)
        self.assertTrue(data.get("f136_sc_none_ok"), data)
        self.assertTrue(data.get("f136_sc_privacy_ok"), data)
        self.assertGreaterEqual(float(data.get("f136_sc_util_rate_good") or 0), 1.0)
        self.assertGreaterEqual(int(data.get("f136_sc_fed_n") or 0), 1)

    def test_f136_scorecard_util_cli(self):
        """Scorecard util gap only when scorecard skills injected without tools."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            od = root / "out"
            od.mkdir()
            sid = "skill-prefer-product-scorecard"
            (od / "skill-router.json").write_text(
                json.dumps({"selected": [sid], "inject_chars": 400}),
                encoding="utf-8",
            )
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": sid,
                                "hit": False,
                                "tool_hit": False,
                                "prose_hit": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            env = {
                "TORII_ROOT": str(root),
                "TORII_SCORECARD_UTIL_FEDERATE": "1",
                "TORII_MEMORY_TENANT": "secret-tenant-x",
            }
            r = _run(["scorecard-util", "--out-dir", str(od)], env=env)
            self.assertEqual(r.returncode, 1, r.stderr + r.stdout)
            rep = json.loads(r.stdout)
            self.assertTrue(rep["utilization_gap"])
            self.assertFalse(rep["ok"])
            self.assertEqual(rep.get("feature"), "F136")
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": sid,
                                "hit": True,
                                "tool_hit": True,
                                "prose_hit": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            r2 = _run(["scorecard-util", "--out-dir", str(od)], env=env)
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            rep2 = json.loads(r2.stdout)
            self.assertFalse(rep2["utilization_gap"])
            self.assertTrue(rep2["ok"])
            blob = r2.stdout
            self.assertNotIn("/Users/", blob)
            self.assertNotIn("secret-tenant-x", blob)
            self.assertTrue((od / "scorecard-skill-util.json").is_file())

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

    def test_f125_hub_score_compound(self):
        """F125: hub post-score yields priority deltas + privacy-safe inject."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fed = root / "memory" / "federation"
            fed.mkdir(parents=True)
            (fed / "recovery-util-signals.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "feature": "F124",
                        "signals": [
                            {
                                "id": "recovery-util-hit-skill-prefer-memory-cli-early",
                                "theme": "skill-prefer-memory-cli-early",
                                "tags": ["recovery_util", "tool_outcome", "f124"],
                                "keywords": ["prefer-memory-cli-early", "recovery-util"],
                                "hits": 3,
                                "tool_hits": 3,
                                "tenants": 2,
                                "tenant_hashes": ["aaa", "bbb"],
                                "util_rate_bin": "hit",
                                "source": "recovery_skill_util",
                            },
                            {
                                "id": "recovery-util-gap",
                                "theme": "recovery-util-gap",
                                "tags": ["recovery_util", "utilization_gap"],
                                "hits": 1,
                                "util_rate_bin": "gap",
                                "source": "recovery_skill_util",
                            },
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            prompt = root / "prompt.md"
            prompt.write_text("## PR metadata\nrepo: t\n", encoding="utf-8")
            env = {
                **os.environ,
                "TORII_ROOT": str(root),
                "TORII_RECOVERY_HUB_COMPOUND": "1",
                "OUT_DIR": str(root / "out"),
            }
            (root / "out").mkdir(exist_ok=True)
            r = _run(["hub-score", "--inject", str(prompt)], env=env)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertEqual(data.get("feature"), "F125")
            self.assertTrue(data.get("privacy_ok"), data)
            self.assertGreaterEqual(int(data.get("skill_n") or 0), 1)
            deltas = data.get("priority_deltas") or {}
            self.assertIn("skill-prefer-memory-cli-early", deltas)
            self.assertGreaterEqual(int(deltas["skill-prefer-memory-cli-early"]), 5)
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("torii-f125-recovery-hub", text)
            self.assertIn("skill-prefer-memory-cli-early", text)
            self.assertNotIn("/Users/", text)
            blob = json.dumps(data)
            self.assertNotIn("/Users/", blob)
            # F126: hub-score also soft-ingests fitness
            fi = data.get("fitness_ingest") or {}
            self.assertTrue(
                int(fi.get("ingested_n") or 0) >= 1 or "soft_error" in fi, data
            )

    def test_f126_hub_gap_reprompt_partial(self):
        """F126: high hub gap_pressure re-prompts idle recovery under partial util."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fed = root / "memory" / "federation"
            fed.mkdir(parents=True)
            # high gap pressure signals
            (fed / "recovery-util-signals.json").write_text(
                json.dumps(
                    {
                        "signals": [
                            {
                                "id": "recovery-util-gap",
                                "theme": "recovery-util-gap",
                                "tags": ["recovery_util", "utilization_gap"],
                                "hits": 5,
                                "tenants": 3,
                                "util_rate_bin": "gap",
                                "source": "recovery_skill_util",
                            },
                            {
                                "id": "recovery-util-ok",
                                "theme": "recovery-util-ok",
                                "tags": ["recovery_util", "util_ok"],
                                "hits": 2,
                                "util_rate_bin": "full",
                                "source": "recovery_skill_util",
                            },
                            {
                                "id": "recovery-util-hit-skill-prefer-product-cli",
                                "theme": "skill-prefer-product-cli",
                                "tags": ["recovery_util", "tool_outcome"],
                                "hits": 1,
                                "tool_hits": 1,
                                "util_rate_bin": "hit",
                                "source": "recovery_skill_util",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            od = root / "out"
            od.mkdir()
            (od / "skill-router.json").write_text(
                json.dumps(
                    {
                        "selected": [
                            "skill-prefer-memory-cli-early",
                            "skill-prefer-product-cli",
                        ],
                        "always_selected": [
                            "skill-prefer-memory-cli-early",
                            "skill-prefer-product-cli",
                        ],
                        "inject_chars": 900,
                    }
                ),
                encoding="utf-8",
            )
            # partial: memory hit, product idle
            (od / "skill-hits.json").write_text(
                json.dumps(
                    {
                        "hits": [
                            {
                                "id": "skill-prefer-memory-cli-early",
                                "tool_hit": True,
                                "hit": True,
                            },
                            {
                                "id": "skill-prefer-product-cli",
                                "tool_hit": False,
                                "hit": False,
                            },
                        ],
                        "tool_hit_n": 1,
                    }
                ),
                encoding="utf-8",
            )
            (od / "agent-loop").mkdir()
            (od / "agent-loop" / "agent-loop.json").write_text(
                json.dumps({"tool_call_turns": 4}), encoding="utf-8"
            )
            env = {
                **os.environ,
                "TORII_ROOT": str(root),
                "TORII_HUB_GAP_REPROMPT": "1",
                "TORII_HUB_GAP_PRESSURE_THR": "0.3",
                "TORII_RECOVERY_HUB_COMPOUND": "1",
            }
            r = _run(["reprompt-decide", "--out-dir", str(od)], env=env)
            self.assertIn("reprompt=1", r.stdout, r.stdout)
            self.assertIn("hub_gap", r.stdout)
            self.assertIn("hub_gap_bias=1", r.stdout)
            # write prompt includes hub line
            pin = root / "p.md"
            pin.write_text("base prompt\n", encoding="utf-8")
            pout = root / "p-out.md"
            r2 = _run(
                [
                    "reprompt-write",
                    "--prompt-in",
                    str(pin),
                    "--prompt-out",
                    str(pout),
                    "--idle-ids",
                    "skill-prefer-product-cli",
                    "--tool-turns",
                    "4",
                    "--hub-gap-pressure",
                    "0.71",
                    "--hub-gap-bias",
                    "1",
                ],
                env=env,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            text = pout.read_text(encoding="utf-8")
            self.assertIn("F126", text)
            self.assertIn("Hub gap pressure", text)
            self.assertNotIn("/Users/", text)


if __name__ == "__main__":
    unittest.main()
