#!/usr/bin/env python3
"""F43: hard preflight spend estimate before Hermes."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "preflight_cost.py"
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location("preflight_cost", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class ParseTests(unittest.TestCase):
    def test_parse_max_usd(self):
        self.assertIsNone(_mod.parse_max_usd(None))
        self.assertIsNone(_mod.parse_max_usd("off"))
        self.assertIsNone(_mod.parse_max_usd("0"))
        self.assertEqual(_mod.parse_max_usd("1.5"), 1.5)

    def test_parse_mode_auto(self):
        self.assertEqual(_mod.parse_preflight_mode(None, budget=None), "estimate")
        self.assertEqual(_mod.parse_preflight_mode(None, budget=1.0), "hard")
        self.assertEqual(_mod.parse_preflight_mode("auto", budget=1.0), "hard")
        self.assertEqual(_mod.parse_preflight_mode("auto", budget=None), "estimate")
        self.assertEqual(_mod.parse_preflight_mode("off", budget=1.0), "off")

    def test_parse_action(self):
        self.assertEqual(_mod.parse_action(None), "force_cheap")
        self.assertEqual(_mod.parse_action("refuse"), "refuse")
        self.assertEqual(_mod.parse_action("warn"), "warn")


class EstimateTests(unittest.TestCase):
    def test_larger_diff_costs_more(self):
        a = _mod.estimate_cost_usd(model="anthropic/claude-opus-5", diff_bytes=1_000)
        b = _mod.estimate_cost_usd(model="anthropic/claude-opus-5", diff_bytes=200_000)
        self.assertGreater(b["estimated_usd"], a["estimated_usd"])

    def test_cheap_cheaper_than_opus(self):
        full = _mod.estimate_cost_usd(
            model="anthropic/claude-opus-5", diff_bytes=100_000, file_count=10
        )
        cheap = _mod.estimate_cost_usd(
            model="openai/gpt-4.1-mini", diff_bytes=100_000, file_count=10
        )
        self.assertGreater(full["estimated_usd"], cheap["estimated_usd"])


class DecideTests(unittest.TestCase):
    def test_no_budget_allows(self):
        r = _mod.decide(model="anthropic/claude-opus-5", diff_bytes=500_000)
        self.assertEqual(r["decision"], "allow")
        self.assertEqual(r["reason"], "no_budget")
        self.assertFalse(r["refused"])

    def test_within_budget_allows(self):
        r = _mod.decide(
            model="openai/gpt-4.1-mini",
            diff_bytes=500,
            file_count=1,
            max_usd=10.0,
            mode="hard",
        )
        self.assertEqual(r["decision"], "allow")
        self.assertIn(r["reason"], ("within_budget", "ok"))

    def test_force_cheap_on_over(self):
        r = _mod.decide(
            model="anthropic/claude-opus-5",
            diff_bytes=200_000,
            file_count=20,
            max_usd=0.05,
            mode="hard",
            action="force_cheap",
        )
        self.assertEqual(r["decision"], "force_cheap")
        self.assertTrue(r["forced_cheap"])
        self.assertEqual(r["model"], _mod.DEFAULT_CHEAP_MODEL)
        self.assertFalse(r["refused"])

    def test_refuse_when_action_refuse(self):
        r = _mod.decide(
            model="anthropic/claude-opus-5",
            diff_bytes=200_000,
            file_count=20,
            max_usd=0.01,
            mode="hard",
            action="refuse",
        )
        self.assertEqual(r["decision"], "refuse")
        self.assertTrue(r["refused"])

    def test_refuse_when_already_cheap_still_over(self):
        r = _mod.decide(
            model="openai/gpt-4.1-mini",
            diff_bytes=500_000,
            file_count=50,
            max_usd=0.001,
            mode="hard",
            action="force_cheap",
        )
        self.assertEqual(r["decision"], "refuse")
        self.assertTrue(r["refused"])

    def test_warn_mode_never_refuses(self):
        r = _mod.decide(
            model="anthropic/claude-opus-5",
            diff_bytes=500_000,
            max_usd=0.001,
            mode="estimate",
            action="force_cheap",
        )
        self.assertEqual(r["decision"], "warn")
        self.assertFalse(r["refused"])

    def test_force_allow(self):
        r = _mod.decide(
            model="anthropic/claude-opus-5",
            diff_bytes=500_000,
            max_usd=0.001,
            mode="hard",
            force_allow=True,
        )
        self.assertEqual(r["decision"], "allow")
        self.assertEqual(r["reason"], "force_allow")


class CliTests(unittest.TestCase):
    def test_decide_exit_2_on_refuse(self):
        env = {**os.environ, "TORII_MAX_COST_USD": "0.001"}
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "decide",
                "--model",
                "openai/gpt-4.1-mini",
                "--diff-bytes",
                "500000",
                "--file-count",
                "40",
                "--action",
                "force_cheap",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("decision=refuse", r.stdout)

    def test_estimate_cli(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "estimate",
                "--model",
                "anthropic/claude-opus-5",
                "--diff-bytes",
                "1000",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("estimated_usd=", r.stdout)


class WiringTests(unittest.TestCase):
    def test_run_hermes_wires_preflight(self):
        text = (ROOT / "scripts" / "run-hermes-review.sh").read_text(encoding="utf-8")
        self.assertIn("preflight_cost.py", text)
        self.assertIn("preflight-cost.env", text)
        self.assertIn("F43", text)

    def test_install_includes_helper(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text(encoding="utf-8")
        self.assertIn("preflight_cost.py", text)

    def test_workflow_exports(self):
        text = (
            ROOT / ".github" / "workflows" / "torii-review-reusable.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("TORII_PREFLIGHT_COST", text)
        self.assertIn("TORII_PREFLIGHT_ACTION", text)


class PackSignalTests(unittest.TestCase):
    def test_pack_reads_preflight_env(self):
        pack = ROOT / "scripts" / "pack-run-for-ui.py"
        r = subprocess.run(
            [sys.executable, str(pack), "--help"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0)
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review-1.md").write_text(
                "## Review\nF43 preflight refuse stub\n", encoding="utf-8"
            )
            (src / "preflight-cost.env").write_text(
                "decision=refuse\nreason=over_estimate_refuse\n"
                "estimated_usd=1.5\nrefused=true\nskip=preflight_cost\n",
                encoding="utf-8",
            )
            out = Path(td) / "b.json"
            r2 = subprocess.run(
                [
                    sys.executable,
                    str(pack),
                    "--dir",
                    str(src),
                    "-o",
                    str(out),
                    "--host",
                    "gha",
                ],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            import json

            sig = json.loads(out.read_text())["signals"]
            self.assertTrue(sig.get("preflight_refuse"))
            self.assertIn("preflight-refuse", sig.get("flags") or [])


if __name__ == "__main__":
    unittest.main()
