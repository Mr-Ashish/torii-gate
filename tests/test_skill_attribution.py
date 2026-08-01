"""Tests for F88 per-skill contribution attribution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "skill_attribution.py"
ADOPT = ROOT / "scripts" / "skill_auto_adopt.py"
INSTALL = ROOT / "scripts" / "install-torii.sh"


def _run(script: Path, args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {**os.environ, "TORII_SKILL_ATTRIBUTION": "1", "TORII_SKILL_AUTO_ADOPT_ATTR": "1"}
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class SkillAttributionTests(unittest.TestCase):
    def test_fixture(self):
        r = _run(SCRIPT, ["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreaterEqual(data["n_contributing"], 1)
        self.assertTrue(data["proposal_free_rider"]["free_rider"])
        self.assertGreater(data["proposal_good"]["contribution"], 0)
        # F140 scorecard hub LOO floor
        self.assertTrue(data.get("f140") or data.get("feature_scorecard") == "F140")
        self.assertTrue(data.get("f140_ok"), data)
        sc = data.get("f140_sc_row") or {}
        self.assertTrue(sc.get("scorecard_floor"), sc)
        self.assertFalse(sc.get("free_rider"), sc)
        self.assertGreaterEqual(float(sc.get("contribution") or 0), 0.85)

    def test_status(self):
        r = _run(SCRIPT, ["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(json.loads(r.stdout)["feature"], "F88")

    def test_f127_hub_ingested_floor(self):
        """F127: fitness hub_ingested skills get contribution floor, not free-rider."""
        prev = {
            k: os.environ.get(k)
            for k in ("TORII_ROOT", "TORII_SKILL_ATTR_HUB", "TORII_SKILL_ATTR_TOOL")
        }
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / ".torii").mkdir()
                (root / ".torii" / "skill-fitness.json").write_text(
                    json.dumps(
                        {
                            "skills": {
                                "skill-prefer-product-cli": {
                                    "hub_ingested_n": 2,
                                    "tool_hit_n": 2,
                                    "hub_priority_delta": 24,
                                    "last_hub_at": "2026-08-01T00:00:00Z",
                                }
                            }
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                active = root / "agent" / "skills" / "active"
                active.mkdir(parents=True)
                (active / "skill-prefer-product-cli.md").write_text(
                    "---\nid: skill-prefer-product-cli\nalways: true\n---\n\nproduct cli\n",
                    encoding="utf-8",
                )
                (active / "skill-zombie-free.md").write_text(
                    "---\nid: skill-zombie-free\n---\n\nzombie free rider\n",
                    encoding="utf-8",
                )
                os.environ["TORII_ROOT"] = str(root)
                os.environ["TORII_SKILL_ATTR_HUB"] = "1"
                os.environ["TORII_SKILL_ATTR_TOOL"] = "0"
                sys.path.insert(0, str(ROOT / "scripts"))
                import skill_attribution as sa  # type: ignore

                rep = sa.attribute(
                    "LGTM no findings APPROVE",
                    root=root,
                    paths=["x.py"],
                    selected=["skill-prefer-product-cli", "skill-zombie-free"],
                    tool_blob="",
                )
                self.assertEqual(rep.get("feature_hub"), "F127")
                self.assertIn(
                    "skill-prefer-product-cli", rep.get("hub_contributors") or []
                )
                row = next(
                    r for r in rep["skills"] if r["id"] == "skill-prefer-product-cli"
                )
                self.assertGreaterEqual(float(row["contribution"]), 0.75)
                self.assertFalse(row["free_rider"])
                z = next(r for r in rep["skills"] if r["id"] == "skill-zombie-free")
                self.assertTrue(z["free_rider"])
        finally:
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_f140_scorecard_hub_floor(self):
        """F140: scorecard_ops fitness skills get LOO floor, not free-rider."""
        prev = {
            k: os.environ.get(k)
            for k in (
                "TORII_ROOT",
                "TORII_SKILL_ATTR_SCORECARD",
                "TORII_SKILL_ATTR_TOOL",
            )
        }
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / ".torii").mkdir()
                sc_id = "skill-prefer-product-scorecard"
                (root / ".torii" / "skill-fitness.json").write_text(
                    json.dumps(
                        {
                            "skills": {
                                sc_id: {
                                    "scorecard_ops": True,
                                    "scorecard_ingested_n": 2,
                                    "tool_hit_n": 2,
                                    "hub_priority_delta": 20,
                                }
                            }
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                active = root / "agent" / "skills" / "active"
                active.mkdir(parents=True)
                (active / f"{sc_id}.md").write_text(
                    f"---\nid: {sc_id}\n---\n\nscorecard ops\n",
                    encoding="utf-8",
                )
                (active / "skill-zombie-sc.md").write_text(
                    "---\nid: skill-zombie-sc\n---\n\nzombie\n",
                    encoding="utf-8",
                )
                os.environ["TORII_ROOT"] = str(root)
                os.environ["TORII_SKILL_ATTR_SCORECARD"] = "1"
                os.environ["TORII_SKILL_ATTR_TOOL"] = "0"
                sys.path.insert(0, str(ROOT / "scripts"))
                import skill_attribution as sa  # type: ignore

                rep = sa.attribute(
                    "LGTM no findings APPROVE silent",
                    root=root,
                    paths=["x.py"],
                    selected=[sc_id, "skill-zombie-sc"],
                    tool_blob="",
                )
                self.assertEqual(rep.get("feature_scorecard"), "F140")
                self.assertIn(sc_id, rep.get("scorecard_floored") or [])
                self.assertIn(sc_id, rep.get("scorecard_contributors") or [])
                row = next(r for r in rep["skills"] if r["id"] == sc_id)
                self.assertTrue(row.get("scorecard_floor"))
                self.assertFalse(row["free_rider"])
                self.assertGreaterEqual(float(row["contribution"]), 0.85)
                z = next(r for r in rep["skills"] if r["id"] == "skill-zombie-sc")
                self.assertTrue(z["free_rider"])
        finally:
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_gate_includes_f88(self):
        r = _run(ADOPT, ["gate"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        names = [g["name"] for g in data.get("gates") or []]
        self.assertIn("f88_skill_attribution", names)
        self.assertTrue(data.get("passed"))

    def test_cycle_writes_ledger(self):
        r = _run(SCRIPT, ["cycle", "--review", str(ROOT / "docs/benchmarks/fixtures/insecure-demo-good-review.md")])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data.get("feature"), "F89")
        self.assertTrue(Path(data["ledger"]).is_file() or "skill-attribution" in data["ledger"])

    def test_router_skips_free_rider_from_ledger(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            lp = Path(td) / "skill-attribution.json"
            lp.write_text(json.dumps({
                "schema_version": 1,
                "feature": "F89",
                "skills": {
                    "skill-soft-tool-nudge": {
                        "id": "skill-soft-tool-nudge",
                        "n": 3, "contribution_sum": 0.0, "solo_hits": 0,
                        "free_rider_n": 3, "avg_contribution": 0.0, "free_rider": True,
                    },
                    "skill-f74-prefer-chain-json": {
                        "id": "skill-f74-prefer-chain-json",
                        "n": 3, "contribution_sum": 6.0, "solo_hits": 3,
                        "free_rider_n": 0, "avg_contribution": 2.0, "free_rider": False,
                    },
                },
                "free_riders": ["skill-soft-tool-nudge"],
                "history": [],
            }))
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "skill_router.py"),
                 "select", "--paths", "demo/insecure/app.py", "--max", "4"],
                cwd=str(ROOT), capture_output=True, text=True,
                env={**os.environ, "TORII_ROOT": str(ROOT),
                     "TORII_SKILL_ATTR_FILE": str(lp),
                     "TORII_SKILL_ATTRIBUTION": "1",
                     "TORII_SKILL_ATTR_ROUTER": "1",
                     "TORII_SKILL_FITNESS": "0"},
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertIn("skill-soft-tool-nudge", data.get("free_rider_skipped") or [])
            self.assertNotIn("skill-soft-tool-nudge", data.get("selected") or [])

    def test_install_ships(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "t"
            dest.mkdir()
            r = subprocess.run(
                ["bash", str(INSTALL), "--dest", str(dest), "--force"],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((dest / "scripts" / "skill_attribution.py").is_file())

    def test_f115_tool_only_attribution(self):
        """F115: silent prose + agent-loop tools → memory skill contributes."""
        import importlib.util

        path = ROOT / "scripts" / "skill_attribution.py"
        spec = importlib.util.spec_from_file_location("skill_attribution", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        silent = "## Review\n\nGeneric note only.\nVerdict: COMMENT\n"
        blob = mod.SYNTH_TOOL_BLOB_GOOD
        mem = "skill-prefer-memory-cli-early"
        with_t = mod.attribute(
            silent,
            root=ROOT,
            selected=[mem],
            tool_blob=blob,
        )
        row = next(r for r in with_t["skills"] if r["id"] == mem)
        self.assertTrue(row["tool_hit"])
        self.assertFalse(row["prose_hit"])
        self.assertGreaterEqual(row["contribution"], 1.5)
        self.assertFalse(row["free_rider"])
        self.assertIn(mem, with_t.get("tool_contributors") or [])

        without = mod.attribute(
            silent,
            root=ROOT,
            selected=[mem],
            tool_blob="",
        )
        row0 = next(r for r in without["skills"] if r["id"] == mem)
        self.assertFalse(row0["tool_hit"])
        self.assertLess(row0["contribution"], 1.5)


if __name__ == "__main__":
    unittest.main()
