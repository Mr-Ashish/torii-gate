#!/usr/bin/env python3
"""F31: pack-run-for-ui auto-bundle for the Run Console."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pack-run-for-ui.py"
SHOWCASE = ROOT / "docs" / "showcase" / "e2e-odoo-pr3-opus5-agentic-loop"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    e = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=e,
    )


class PackRunForUiTests(unittest.TestCase):
    def test_pack_showcase(self):
        self.assertTrue(SHOWCASE.is_dir(), "showcase fixture missing")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "run-bundle.json"
            r = _run(["--dir", str(SHOWCASE), "-o", str(out), "--host", "gha"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.is_file())
            bundle = json.loads(out.read_text())
            self.assertEqual(bundle["schema_version"], 1)
            self.assertEqual(bundle["host"], "gha")
            self.assertTrue(bundle["result"].get("verdict") or bundle["result"].get("review_md"))
            self.assertIn("cost", bundle)
            self.assertIn("timings", bundle)
            self.assertIn("trace", bundle)
            self.assertIn("signals", bundle)
            self.assertIn("flags", bundle["signals"])

    def test_f40_signals_timeout_and_path_skip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review.md").write_text(
                "## Torii Review — PR #1\n\n**Verdict:** COMMENT\n\n"
                "### Summary\nPath-skip (F38): free skip.\n",
                encoding="utf-8",
            )
            (src / "hermes-timeout.env").write_text(
                "timed_out=1\ntimeout_seconds=1500\nstage=hermes-z\n",
                encoding="utf-8",
            )
            (src / "ops-signals.env").write_text(
                "PATH_SKIP=1\nsample=README.md\nglobs=docs\n",
                encoding="utf-8",
            )
            (src / "meta.env").write_text("DIFF_TRUNCATED=true\n", encoding="utf-8")
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "local"])
            self.assertEqual(r.returncode, 0, r.stderr)
            sig = json.loads(out.read_text())["signals"]
            self.assertTrue(sig["timeout"])
            self.assertEqual(sig["timeout_seconds"], 1500)
            self.assertTrue(sig["path_skip"])
            self.assertTrue(sig["diff_truncated"])
            self.assertTrue(sig["any"])
            self.assertIn("timeout", sig["flags"])
            self.assertIn("path-skip", sig["flags"])
            self.assertIn("diff-truncated", sig["flags"])

    def test_f41_max_turns_and_loop_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            loop = src / "agent-loop"
            loop.mkdir()
            (src / "review.md").write_text(
                "## Torii Review — PR #2\n\n**Verdict:** COMMENT\n\n"
                "### Summary\nHit F41 max_turns iteration budget.\n",
                encoding="utf-8",
            )
            (src / "hermes-max-turns.env").write_text(
                "max_turns_enabled=1\nmax_turns=40\nmax_turns_hit=1\n",
                encoding="utf-8",
            )
            (loop / "agent-loop.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "tool_call_turns": 40,
                        "message_count": 82,
                        "steps": [{"step": i} for i in range(5)],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "gha"])
            self.assertEqual(r.returncode, 0, r.stderr)
            bundle = json.loads(out.read_text())
            sig = bundle["signals"]
            self.assertTrue(sig["max_turns_hit"])
            self.assertEqual(sig["max_turns"], 40)
            self.assertIn("max-turns", sig["flags"])
            self.assertTrue(sig["any"])
            loop_b = bundle["loop"]
            self.assertEqual(loop_b["tool_call_turns"], 40)
            self.assertEqual(loop_b["message_count"], 82)
            self.assertEqual(loop_b["step_count"], 5)
            self.assertEqual(loop_b["max_turns"], 40)
            self.assertTrue(loop_b["max_turns_hit"])

    def test_also_writes_second_path(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "a.json"
            also = Path(td) / "sub" / "b.json"
            r = _run(
                [
                    "--dir",
                    str(SHOWCASE),
                    "-o",
                    str(out),
                    "--also",
                    str(also),
                    "--host",
                    "local",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.is_file())
            self.assertTrue(also.is_file())
            self.assertEqual(json.loads(out.read_text())["host"], "local")

    def test_memory_health_inject(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review.md").write_text(
                "## Torii Review — PR #9\n\n**Verdict:** COMMENT\n**Score:** 70/100\n\n"
                "### Summary\nok\n",
                encoding="utf-8",
            )
            (src / "meta.json").write_text(
                json.dumps(
                    {
                        "trace_id": "pr9-test",
                        "repo": "acme/x",
                        "pr_number": "9",
                        "status": "success",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            mh = Path(td) / "memory-health.env"
            mh.write_text(
                "MEMORY_SOURCE=local\nLOCAL_PUBLISH=ok\nHUB_PUBLISH=skipped\n",
                encoding="utf-8",
            )
            out = Path(td) / "bundle.json"
            r = _run(
                [
                    "--dir",
                    str(src),
                    "-o",
                    str(out),
                    "--memory-health",
                    str(mh),
                    "--host",
                    "gha",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            bundle = json.loads(out.read_text())
            self.assertEqual(bundle["result"]["verdict"], "COMMENT")
            self.assertEqual(bundle["memory"]["health"].get("MEMORY_SOURCE"), "local")
            self.assertEqual(bundle["memory"]["health"].get("LOCAL_PUBLISH"), "ok")

    def test_soft_missing_dir(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "x.json"
            r = _run(
                ["--dir", str(Path(td) / "nope"), "-o", str(out), "--soft"]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(out.exists())

    def test_detect_host_env(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "b.json"
            r = _run(
                ["--dir", str(SHOWCASE), "-o", str(out)],
                env={
                    "TORII_HOST": "modal",
                    "GITHUB_ACTIONS": "",
                    "MODAL_TASK_ID": "",
                },
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(out.read_text())["host"], "modal")

    def test_review_pr_number_fallback(self):
        """OUT_DIR layout uses review-<n>.md instead of review.md."""
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "out"
            src.mkdir()
            (src / "review-42.md").write_text(
                "**Verdict:** APPROVE\n**Score:** 90/100\n\n### Summary\nship it\n",
                encoding="utf-8",
            )
            out = Path(td) / "b.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "local"])
            self.assertEqual(r.returncode, 0, r.stderr)
            b = json.loads(out.read_text())
            self.assertEqual(b["result"]["verdict"], "APPROVE")



    def test_f42_model_tier_signal(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review-1.md").write_text(
                "## Review\nLooks fine.\n", encoding="utf-8"
            )
            (src / "model-tier.env").write_text(
                "mode=auto\ntier=cheap\nreason=tiny\nmodel=openai/gpt-4.1-mini\n",
                encoding="utf-8",
            )
            (src / "torii-model.txt").write_text(
                "openai/gpt-4.1-mini\n", encoding="utf-8"
            )
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "gha"])
            self.assertEqual(r.returncode, 0, r.stderr)
            bundle = json.loads(out.read_text())
            sig = bundle["signals"]
            self.assertEqual(sig.get("model_tier_mode"), "auto")
            self.assertEqual(sig.get("model_tier"), "cheap")
            self.assertEqual(sig.get("model_tier_reason"), "tiny")
            self.assertEqual(sig.get("model"), "openai/gpt-4.1-mini")
            self.assertIn("model-cheap", sig.get("flags") or [])
            self.assertTrue(sig.get("any"))

    def test_f45_tool_turns_gate_signal(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review-2.md").write_text(
                "**Verdict:** COMMENT\n\n"
                "> ⚠️ **Incomplete agentic review (F45):** Hermes recorded "
                "**0 tool turns** on a multi-file code PR.\n",
                encoding="utf-8",
            )
            (src / "tool-turns-gate.env").write_text(
                "gate=1\nreason=zero_tools_multi_file_code\ntool_turns=0\n"
                "file_count=4\nmutated=1\n",
                encoding="utf-8",
            )
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "local"])
            self.assertEqual(r.returncode, 0, r.stderr)
            sig = json.loads(out.read_text())["signals"]
            self.assertTrue(sig.get("tool_turns_gate"))
            self.assertEqual(sig.get("tool_turns_gate_reason"), "zero_tools_multi_file_code")
            self.assertIn("tool-turns-gate", sig.get("flags") or [])
            self.assertTrue(sig.get("any"))

    def test_f46_soul_blocked_signal(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review-1.md").write_text("**Verdict:** COMMENT\n", encoding="utf-8")
            (src / "soul-context.env").write_text(
                "soul_blocked=1\nreason=prompt_injection\n",
                encoding="utf-8",
            )
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "local"])
            self.assertEqual(r.returncode, 0, r.stderr)
            sig = json.loads(out.read_text())["signals"]
            self.assertTrue(sig.get("soul_blocked"))
            self.assertEqual(sig.get("soul_blocked_reason"), "prompt_injection")
            self.assertIn("soul-blocked", sig.get("flags") or [])

    def test_f49_tool_turns_reprompt_signal(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review-2.md").write_text("**Verdict:** COMMENT\n", encoding="utf-8")
            (src / "tool-turns-reprompt.env").write_text(
                "reprompt=1\nattempted=1\nreason=reprompt_ran\n"
                "tool_turns_before=0\ntool_turns_after=0\nrecovered=0\n",
                encoding="utf-8",
            )
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "local"])
            self.assertEqual(r.returncode, 0, r.stderr)
            sig = json.loads(out.read_text())["signals"]
            self.assertTrue(sig.get("tool_turns_reprompt"))
            self.assertEqual(sig.get("tool_turns_reprompt_reason"), "reprompt_ran")
            self.assertFalse(sig.get("tool_turns_reprompt_recovered"))
            self.assertIn("tool-reprompt", sig.get("flags") or [])

    def test_f49_reprompt_recovered_chip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review-4.md").write_text("**Verdict:** REQUEST_CHANGES\n", encoding="utf-8")
            (src / "tool-turns-reprompt.env").write_text(
                "reprompt=1\nattempted=1\nreason=reprompt_recovered\n"
                "tool_turns_before=0\ntool_turns_after=3\nrecovered=1\n",
                encoding="utf-8",
            )
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "local"])
            self.assertEqual(r.returncode, 0, r.stderr)
            sig = json.loads(out.read_text())["signals"]
            self.assertTrue(sig.get("tool_turns_reprompt_recovered"))
            self.assertIn("tool-reprompt-ok", sig.get("flags") or [])

    def test_f50_severity_calibration_signal(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review-2.md").write_text(
                "**Verdict:** REQUEST CHANGES\n\n"
                "> ⚠️ **Severity calibration (F50 / H20):** test gap under APPROVE.\n",
                encoding="utf-8",
            )
            (src / "severity-calibration.env").write_text(
                "gate=1\nreason=approve_with_test_gap\nmatch=missing_tests:suggestions\n"
                "action=upgrade_request_changes\nmutated=1\n",
                encoding="utf-8",
            )
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "local"])
            self.assertEqual(r.returncode, 0, r.stderr)
            sig = json.loads(out.read_text())["signals"]
            self.assertTrue(sig.get("severity_calibration"))
            self.assertEqual(sig.get("severity_calibration_reason"), "approve_with_test_gap")
            self.assertIn("sev-cal", sig.get("flags") or [])
            self.assertTrue(sig.get("any"))

    def test_f53_issue_context_signal(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "run"
            src.mkdir()
            (src / "review-2.md").write_text("**Verdict:** COMMENT\n", encoding="utf-8")
            (src / "linked-issue-context.env").write_text(
                "enabled=1\ncount=1\nrefs=acme/widgets#42\nfetched=1\nskipped=\nreason=ok\n",
                encoding="utf-8",
            )
            out = Path(td) / "bundle.json"
            r = _run(["--dir", str(src), "-o", str(out), "--host", "local"])
            self.assertEqual(r.returncode, 0, r.stderr)
            sig = json.loads(out.read_text())["signals"]
            self.assertTrue(sig.get("issue_context"))
            self.assertEqual(sig.get("issue_context_count"), 1)
            self.assertEqual(sig.get("issue_context_refs"), "acme/widgets#42")
            self.assertIn("issue-ctx", sig.get("flags") or [])


if __name__ == "__main__":
    unittest.main()
