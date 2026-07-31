#!/usr/bin/env python3
"""F45: tool_turns_gate (H12 fail closed on zero tools)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tool_turns_gate.py"
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location("tool_turns_gate", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class DecideTests(unittest.TestCase):
    def test_tools_used_no_gate(self):
        d = _mod.decide(tool_turns=3, file_count=4, paths=["a.py", "b.py"])
        self.assertEqual(d["gate"], 0)
        self.assertEqual(d["reason"], "tools_used")

    def test_zero_tools_multi_file_gates(self):
        d = _mod.decide(tool_turns=0, file_count=4, paths=["a.js", "b.js", "c.js"])
        self.assertEqual(d["gate"], 1)
        self.assertEqual(d["reason"], "zero_tools_multi_file_code")
        self.assertEqual(d["action"], "downgrade_approve")

    def test_docs_only_skips(self):
        d = _mod.decide(
            tool_turns=0,
            file_count=3,
            paths=["README.md", "docs/x.md", "CHANGELOG.md"],
        )
        self.assertEqual(d["gate"], 0)
        self.assertEqual(d["reason"], "docs_only")
        self.assertTrue(d["docs_only"])

    def test_single_file_below_min(self):
        d = _mod.decide(tool_turns=0, file_count=1, paths=["only.py"], min_files_n=2)
        self.assertEqual(d["gate"], 0)
        self.assertEqual(d["reason"], "below_min_files")

    def test_gate_off(self):
        d = _mod.decide(tool_turns=0, file_count=5, paths=["a.py", "b.py"], gate_on=False)
        self.assertEqual(d["gate"], 0)
        self.assertEqual(d["reason"], "gate_off")

    def test_nontarget_verdict_annotate_only(self):
        d = _mod.decide(
            tool_turns=0,
            file_count=3,
            paths=["a.py", "b.py"],
            verdict="REQUEST_CHANGES",
        )
        self.assertEqual(d["gate"], 1)
        self.assertEqual(d["action"], "annotate_only")


class ApplyTests(unittest.TestCase):
    SAMPLE = """## 🏴‍☠️ Torii Review — PR #2

**Verdict:** APPROVE
**Confidence:** medium
**Score:** 90/100
**Review effort:** 2/5

### Summary
Looks good enough.

### Blocking
- None
"""

    def test_downgrade_approve(self):
        d = _mod.decide(tool_turns=0, file_count=4, paths=["a.js", "b.js"])
        new, mut = _mod.apply_to_review(self.SAMPLE, decision=d)
        self.assertTrue(mut["mutated"])
        self.assertEqual(mut["verdict_before"], "APPROVE")
        self.assertEqual(mut["verdict_after"], "COMMENT")
        self.assertIn("**Verdict:** COMMENT", new)
        self.assertIn("**Confidence:** low", new)
        self.assertIn("**Score:** 55/100", new)
        self.assertIn("Incomplete agentic review (F45)", new)
        self.assertTrue(mut["banner_added"])

    def test_idempotent_banner(self):
        d = _mod.decide(tool_turns=0, file_count=4, paths=["a.js", "b.js"])
        once, _ = _mod.apply_to_review(self.SAMPLE, decision=d)
        twice, mut2 = _mod.apply_to_review(once, decision=d)
        self.assertEqual(once.count("Incomplete agentic review (F45)"), 1)
        # second apply still COMMENT; banner not duplicated
        self.assertEqual(twice.count("Incomplete agentic review (F45)"), 1)
        self.assertEqual(mut2["verdict_after"], "COMMENT")

    def test_no_mutate_when_tools(self):
        d = _mod.decide(tool_turns=2, file_count=4, paths=["a.js", "b.js"])
        new, mut = _mod.apply_to_review(self.SAMPLE, decision=d)
        self.assertFalse(mut["mutated"])
        self.assertEqual(new, self.SAMPLE)


class RepromptTests(unittest.TestCase):
    """F49 / H15 soft re-prompt helpers."""

    def test_should_reprompt_zero_tools(self):
        d = _mod.should_reprompt(
            tool_turns=0, file_count=4, paths=["a.py", "b.py", "c.py"]
        )
        self.assertEqual(d["reprompt"], 1)
        self.assertEqual(d["reason"], "zero_tools_multi_file_code")

    def test_should_not_reprompt_when_tools(self):
        d = _mod.should_reprompt(tool_turns=2, file_count=4, paths=["a.py", "b.py"])
        self.assertEqual(d["reprompt"], 0)
        self.assertEqual(d["reason"], "tools_used")

    def test_should_not_reprompt_docs_only(self):
        d = _mod.should_reprompt(
            tool_turns=0,
            file_count=3,
            paths=["README.md", "docs/a.md", "CHANGELOG.md"],
        )
        self.assertEqual(d["reprompt"], 0)
        self.assertEqual(d["reason"], "docs_only")

    def test_should_not_reprompt_already(self):
        d = _mod.should_reprompt(
            tool_turns=0,
            file_count=3,
            paths=["a.py", "b.py"],
            already_reprompted=True,
        )
        self.assertEqual(d["reprompt"], 0)
        self.assertEqual(d["reason"], "already_reprompted")

    def test_reprompt_off_env(self):
        d = _mod.should_reprompt(
            tool_turns=0,
            file_count=3,
            paths=["a.py", "b.py"],
            reprompt_on=False,
        )
        self.assertEqual(d["reprompt"], 0)
        self.assertEqual(d["reason"], "reprompt_off")

    def test_build_suffix_contains_nudge(self):
        s = _mod.build_reprompt_suffix(
            tool_turns=0, file_count=3, paths=["a.py", "b.py", "c.py"]
        )
        self.assertIn("Soft re-prompt (Torii H15 / F49", s)
        self.assertIn("0 tool turns", s)
        self.assertIn("`a.py`", s)

    def test_build_suffix_tool_depth_h26(self):
        """F51/H26: re-prompt must forbid head-only large-file reads."""
        s = _mod.build_reprompt_suffix(
            tool_turns=0,
            file_count=14,
            paths=["odoo/tools/misc.py", "addons/base_address_extended/tests/test_street_fields.py"],
        )
        self.assertIn("Tool depth (H26 / F51)", s)
        self.assertIn("head", s.lower())
        self.assertIn("changed region", s.lower())
        self.assertIn("rg", s.lower())
        self.assertIn("`odoo/tools/misc.py`", s)

    def test_write_reprompt_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            pin = td_p / "prompt.md"
            pin.write_text("hello review prompt\n", encoding="utf-8")
            pout = td_p / "out.md"
            _mod.write_reprompt_prompt(
                prompt_in=pin,
                prompt_out=pout,
                tool_turns=0,
                file_count=2,
                paths=["x.js", "y.js"],
            )
            once = pout.read_text(encoding="utf-8")
            # second write from already-nudged prompt must not stack
            _mod.write_reprompt_prompt(
                prompt_in=pout,
                prompt_out=pout,
                tool_turns=0,
                file_count=2,
                paths=["x.js", "y.js"],
            )
            twice = pout.read_text(encoding="utf-8")
            self.assertEqual(once.count("Soft re-prompt (Torii H15 / F49"), 1)
            self.assertEqual(twice.count("Soft re-prompt (Torii H15 / F49"), 1)
            self.assertIn("Tool depth (H26 / F51)", once)
            self.assertIn("hello review prompt", twice)


class CliTests(unittest.TestCase):
    def test_decide_cli(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "decide",
                "--tool-turns",
                "0",
                "--file-count",
                "4",
                "--path",
                "a.js",
                "--path",
                "b.js",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("gate=1", r.stdout)
        self.assertIn("reason=zero_tools_multi_file_code", r.stdout)

    def test_reprompt_decide_cli(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "reprompt-decide",
                "--tool-turns",
                "0",
                "--file-count",
                "4",
                "--path",
                "a.js",
                "--path",
                "b.js",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("reprompt=1", r.stdout)
        self.assertIn("reason=zero_tools_multi_file_code", r.stdout)

    def test_apply_cli_and_env(self):
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            rev = td_p / "review.md"
            rev.write_text(
                "**Verdict:** APPROVE\n**Confidence:** high\n**Score:** 88/100\n\n### Summary\nok\n",
                encoding="utf-8",
            )
            loop = td_p / "agent-loop.json"
            loop.write_text(json.dumps({"tool_call_turns": 0}), encoding="utf-8")
            env_out = td_p / "tool-turns-gate.env"
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "apply",
                    "--review",
                    str(rev),
                    "--loop-json",
                    str(loop),
                    "--file-count",
                    "3",
                    "--path",
                    "x.py",
                    "--path",
                    "y.py",
                    "--env-out",
                    str(env_out),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            body = rev.read_text(encoding="utf-8")
            self.assertIn("**Verdict:** COMMENT", body)
            self.assertTrue(env_out.is_file())
            env_txt = env_out.read_text(encoding="utf-8")
            self.assertIn("gate=1", env_txt)
            self.assertIn("mutated=1", env_txt)

    def test_enabled_env_off(self):
        env = os.environ.copy()
        env["TORII_TOOL_TURNS_GATE"] = "off"
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "decide",
                "--tool-turns",
                "0",
                "--file-count",
                "5",
                "--path",
                "a.py",
                "--path",
                "b.py",
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("gate=0", r.stdout)
        self.assertIn("reason=gate_off", r.stdout)


class WireTests(unittest.TestCase):
    def test_run_hermes_mentions_f45(self):
        text = (ROOT / "scripts" / "run-hermes-review.sh").read_text(encoding="utf-8")
        self.assertIn("tool_turns_gate.py", text)
        self.assertIn("F45", text)
        self.assertIn("tool-turns-gate.env", text)

    def test_run_hermes_mentions_f49(self):
        text = (ROOT / "scripts" / "run-hermes-review.sh").read_text(encoding="utf-8")
        self.assertIn("F49", text)
        self.assertIn("reprompt-decide", text)
        self.assertIn("tool-turns-reprompt.env", text)
        self.assertIn("TORII_TOOL_TURNS_REPROMPT", text)

    def test_install_pack_lists_script(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text(encoding="utf-8")
        self.assertIn("tool_turns_gate.py", text)


if __name__ == "__main__":
    unittest.main()
