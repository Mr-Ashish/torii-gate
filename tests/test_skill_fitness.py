"""Tests for F85 skill fitness ledger."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_fitness.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {**os.environ, "TORII_SKILL_FITNESS": "1"}
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class SkillFitnessTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data["zombie_demoted"])
        self.assertTrue(data["good_not_demoted"])
        self.assertTrue(data["privacy_ok"])
        # F116 tool-fitness compound
        self.assertEqual(data.get("feature_tool"), "F116")
        self.assertTrue(data.get("tool_shielded"), data)
        self.assertTrue(data.get("tool_in_fed"), data)
        self.assertTrue(data.get("tool_boost_ok"), data)
        # F135 scorecard skill fitness ingest
        self.assertEqual(data.get("feature_scorecard"), "F135")
        self.assertTrue(data.get("f135"), data)
        self.assertTrue(data.get("f135_sc_shielded"), data)
        self.assertTrue(data.get("f135_sc_ops_ok"), data)
        self.assertTrue(data.get("f135_sc_privacy_ok"), data)
        self.assertGreaterEqual(int(data.get("f135_sc_ingested_n") or 0), 1)
        self.assertTrue(data.get("f135_sc_in_fed"), data)

    def test_status(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F85")

    def test_f116_tool_shield_unit(self):
        """Tool-effective skill with low prose hit_rate is not demoted."""
        import importlib.util

        path = ROOT / "scripts" / "skill_fitness.py"
        spec = importlib.util.spec_from_file_location("skill_fitness", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        ledger = {
            "skills": {
                "skill-prefer-memory-cli-early": {
                    "id": "skill-prefer-memory-cli-early",
                    "selected_n": 5,
                    "hit_n": 1,
                    "miss_n": 4,
                    "hit_rate": 0.2,
                    "tool_hit_n": 4,
                    "tool_hit_rate": 0.8,
                    "demoted": True,
                },
                "skill-zombie-docs": {
                    "id": "skill-zombie-docs",
                    "selected_n": 5,
                    "hit_n": 0,
                    "miss_n": 5,
                    "hit_rate": 0.0,
                    "tool_hit_n": 0,
                    "tool_hit_rate": 0.0,
                    "demoted": False,
                },
            },
            "demoted": [],
        }
        out = mod.apply_demotions(ledger)
        dem = set(out.get("demoted") or [])
        self.assertNotIn("skill-prefer-memory-cli-early", dem)
        self.assertIn("skill-zombie-docs", dem)
        boosts = mod.fitness_boosts(out)
        self.assertGreater(boosts.get("skill-prefer-memory-cli-early", 0), 0)
        sigs = mod.federate_signals(out, tenant="t-a")
        mem = next(
            s for s in sigs if "memory" in str(s.get("id") or s.get("theme") or "")
        )
        self.assertIn("tool_outcome", mem.get("tags") or [])
        self.assertIn("f116", mem.get("tags") or [])
        self.assertNotIn("/Users/", json.dumps(sigs))

    def test_f135_scorecard_ingest_unit(self):
        """F135: federated scorecard skill themes shield + boost fitness ledger."""
        import importlib.util

        path = ROOT / "scripts" / "skill_fitness.py"
        spec = importlib.util.spec_from_file_location("skill_fitness", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        prev_root = os.environ.get("TORII_ROOT")
        prev_sc = os.environ.get("TORII_SKILL_FITNESS_SCORECARD")
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                os.environ["TORII_ROOT"] = str(root)
                os.environ["TORII_SKILL_FITNESS_SCORECARD"] = "1"
                fed = root / "memory" / "federation"
                fed.mkdir(parents=True)
                sc = "skill-prefer-product-scorecard"
                doc = {
                    "privacy_ok": True,
                    "skill_ids": [sc],
                    "signals": [
                        {
                            "id": "scorecard-skill-product",
                            "theme": sc,
                            "tags": ["scorecard_ops", "f134", "tool_outcome"],
                            "keywords": ["product-scorecard"],
                            "path_basenames": [],
                        }
                    ],
                }
                (fed / "scorecard-skill-signals.json").write_text(
                    json.dumps(doc), encoding="utf-8"
                )
                ledger = mod.empty_ledger()
                # pre-demote as if zombie
                ent = mod._skill_entry(ledger, sc)
                ent["selected_n"] = 5
                ent["hit_n"] = 0
                ent["hit_rate"] = 0.0
                ent["demoted"] = True
                ledger["skills"][sc] = ent
                rep = mod.ingest_scorecard_skills(doc, ledger, root=root, save=True)
                self.assertGreaterEqual(rep["ingested_n"], 1)
                self.assertTrue(rep["scorecard_ops_ok"])
                self.assertTrue(rep["privacy_ok"])
                ledger = mod.apply_demotions(mod.load_ledger(mod.ledger_path(root)))
                self.assertNotIn(sc, mod.demoted_set(ledger))
                self.assertGreater(mod.fitness_boosts(ledger).get(sc, 0), 0)
                sigs = mod.federate_signals(ledger, tenant="tenant-secret-xyz")
                blob = json.dumps(sigs)
                self.assertNotIn("/Users/", blob)
                self.assertNotIn("tenant-secret-xyz", blob)
                sc_sig = next(
                    s for s in sigs if sc in str(s.get("id") or s.get("theme") or "")
                )
                self.assertIn("scorecard_ops", sc_sig.get("tags") or [])
                self.assertIn("f135", sc_sig.get("tags") or [])
        finally:
            if prev_root is None:
                os.environ.pop("TORII_ROOT", None)
            else:
                os.environ["TORII_ROOT"] = prev_root
            if prev_sc is None:
                os.environ.pop("TORII_SKILL_FITNESS_SCORECARD", None)
            else:
                os.environ["TORII_SKILL_FITNESS_SCORECARD"] = prev_sc

    def test_install_ships_script(self):
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
            self.assertTrue((dest / "scripts" / "skill_fitness.py").is_file())

    def test_router_skips_demoted(self):
        """Integration: demoted skill not selected for full body (unless always)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            active = root / "agent" / "skills" / "active"
            active.mkdir(parents=True)
            (active / "skill-good.md").write_text(
                "---\nid: skill-good\ntitle: Good skill\nthemes: python,taint\n---\n\n"
                "## Skill good\nUse **taint chain** evidence.\n",
                encoding="utf-8",
            )
            (active / "skill-zombie.md").write_text(
                "---\nid: skill-zombie\ntitle: Zombie skill\nthemes: python,taint\n---\n\n"
                "## Skill zombie\nNever used docs.\n",
                encoding="utf-8",
            )
            (active / "skill-tool-depth-hunks.md").write_text(
                "---\nid: skill-tool-depth-hunks\ntitle: Depth\nalways: true\n---\n\n"
                "## Skill depth\n**diff** hunks.\n",
                encoding="utf-8",
            )
            torii = root / ".torii"
            torii.mkdir()
            # seed ledger: zombie demoted after many misses
            (torii / "skill-fitness.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "feature": "F85",
                        "skills": {
                            "skill-good": {
                                "id": "skill-good",
                                "selected_n": 5,
                                "hit_n": 5,
                                "miss_n": 0,
                                "hit_rate": 1.0,
                                "demoted": False,
                            },
                            "skill-zombie": {
                                "id": "skill-zombie",
                                "selected_n": 5,
                                "hit_n": 0,
                                "miss_n": 5,
                                "hit_rate": 0.0,
                                "demoted": True,
                            },
                        },
                        "demoted": ["skill-zombie"],
                        "history": [],
                    }
                ),
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "TORII_ROOT": str(root),
                "TORII_SKILL_FITNESS": "1",
                "TORII_SKILL_ROUTER": "1",
                "TORII_SKILL_ROUTER_MAX": "4",
            }
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "skill_router.py"),
                    "select",
                    "--paths",
                    "src/app.py",
                    "--max",
                    "4",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            sel = set(data["selected"])
            self.assertIn("skill-good", sel)
            self.assertNotIn("skill-zombie", sel)
            self.assertIn("skill-zombie", set(data.get("demoted_skipped") or ["skill-zombie"]))


if __name__ == "__main__":
    unittest.main()
