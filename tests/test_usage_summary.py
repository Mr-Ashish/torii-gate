#!/usr/bin/env python3
"""Unit tests for F21 usage-summary.py (stdlib only)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "usage-summary.py"

SAMPLE = {
    "estimated_cost_usd": 0.5930795,
    "cost_status": "estimated",
    "cost_source": "provider_models_api",
    "input_tokens": 20,
    "output_tokens": 14601,
    "cache_read_tokens": 156634,
    "cache_write_tokens": 23942,
    "total_tokens": 195197,
    "api_calls": 10,
    "model": "anthropic/claude-opus-5",
    "provider": "openrouter",
    "session_id": "20260730_191954_63f003",
    "completed": True,
}


class UsageSummaryTests(unittest.TestCase):
    def run_cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=check,
        )

    def test_footer_from_sample(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "hermes-usage.json"
            usage.write_text(json.dumps(SAMPLE))
            cp = self.run_cli("footer", "--usage", str(usage))
            out = cp.stdout.strip()
            self.assertIn("Cost / usage:", out)
            self.assertIn("anthropic/claude-opus-5", out)
            self.assertIn("$0.59", out)
            self.assertIn("195k tokens", out)
            self.assertIn("10 API calls", out)
            self.assertIn("(estimated)", out)

    def test_footer_missing_usage_is_noop(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "nope.json"
            cp = self.run_cli("footer", "--usage", str(missing))
            self.assertEqual(cp.returncode, 0)
            self.assertEqual(cp.stdout, "")

    def test_append_after_brand_footer(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "hermes-usage.json"
            review = Path(td) / "review.md"
            usage.write_text(json.dumps(SAMPLE))
            review.write_text(
                "## 🏴‍☠️ Torii Review — PR #1\n\n"
                "**Verdict:** APPROVE\n"
                "**Score:** 90/100\n\n"
                "### Summary\nok\n\n"
                "---\n"
                "*Torii · Hermes Agent · OpenRouter · memory-backed review*\n"
            )
            self.run_cli("append", "--usage", str(usage), "--review", str(review))
            body = review.read_text()
            self.assertIn("*Torii · Hermes Agent · OpenRouter · memory-backed review*", body)
            self.assertIn("*Cost / usage:", body)
            self.assertIn("$0.59", body)
            # Cost line should come after brand footer
            brand_i = body.index("Torii · Hermes Agent")
            cost_i = body.index("Cost / usage:")
            self.assertGreater(cost_i, brand_i)

    def test_append_idempotent_replace(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "hermes-usage.json"
            review = Path(td) / "review.md"
            usage.write_text(json.dumps(SAMPLE))
            review.write_text(
                "body\n\n*Torii · Hermes Agent · OpenRouter · memory-backed review*\n"
                "*Cost / usage: model=`old` · ~$0.01 · 1k tokens · 1 API calls*\n"
            )
            self.run_cli("append", "--usage", str(usage), "--review", str(review))
            body = review.read_text()
            self.assertEqual(body.count("*Cost / usage:"), 1)
            self.assertIn("anthropic/claude-opus-5", body)
            self.assertNotIn("model=`old`", body)

    def test_step_summary_includes_timings(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "u.json"
            timings = Path(td) / "t.json"
            usage.write_text(json.dumps(SAMPLE))
            timings.write_text(
                json.dumps(
                    {
                        "total_seconds": 253,
                        "stages": [
                            {"name": "hermes", "seconds": 251, "exit_code": 0},
                            {"name": "assemble", "seconds": 2, "exit_code": 0},
                        ],
                    }
                )
            )
            cp = self.run_cli(
                "step-summary",
                "--usage",
                str(usage),
                "--timings",
                str(timings),
            )
            out = cp.stdout
            self.assertIn("### Torii cost / usage (F21)", out)
            self.assertIn("Estimated cost:", out)
            self.assertIn("$0.59", out)
            self.assertIn("253s", out)
            self.assertIn("hermes=251s", out)

    def test_step_summary_without_usage(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing.json"
            cp = self.run_cli("step-summary", "--usage", str(missing))
            self.assertIn("No `hermes-usage.json`", cp.stdout)

    def test_small_cost_precision(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "u.json"
            usage.write_text(
                json.dumps(
                    {
                        "estimated_cost_usd": 0.0042,
                        "total_tokens": 500,
                        "api_calls": 2,
                        "model": "openai/gpt-4.1-mini",
                        "cost_status": "estimated",
                    }
                )
            )
            cp = self.run_cli("footer", "--usage", str(usage))
            self.assertIn("$0.0042", cp.stdout)

    def test_f29_budget_over(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "u.json"
            usage.write_text(json.dumps(SAMPLE))  # ~$0.59
            cp = self.run_cli("budget", "--usage", str(usage), "--max-usd", "0.10")
            self.assertEqual(cp.returncode, 0)
            kv = dict(
                line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line
            )
            self.assertEqual(kv["budget_enabled"], "true")
            self.assertEqual(kv["over_budget"], "true")
            self.assertIn("over soft budget", cp.stderr.lower())

    def test_f29_budget_within(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "u.json"
            usage.write_text(json.dumps(SAMPLE))
            cp = self.run_cli("budget", "--usage", str(usage), "--max-usd", "5.00")
            kv = dict(
                line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line
            )
            self.assertEqual(kv["over_budget"], "false")
            self.assertNotIn("OVER BUDGET", cp.stderr)

    def test_f29_budget_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "u.json"
            usage.write_text(json.dumps(SAMPLE))
            for raw in ("", "0", "off", "disabled"):
                cp = self.run_cli("budget", "--usage", str(usage), "--max-usd", raw)
                kv = dict(
                    line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line
                )
                self.assertEqual(kv["budget_enabled"], "false", msg=raw)
                self.assertEqual(kv["over_budget"], "false", msg=raw)

    def test_f29_footer_over_budget_note(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "u.json"
            usage.write_text(json.dumps(SAMPLE))
            cp = self.run_cli("footer", "--usage", str(usage), "--max-usd", "0.10")
            self.assertIn("OVER BUDGET", cp.stdout)
            self.assertIn("max $0.10", cp.stdout)

    def test_f29_step_summary_budget_section(self):
        with tempfile.TemporaryDirectory() as td:
            usage = Path(td) / "u.json"
            usage.write_text(json.dumps(SAMPLE))
            cp = self.run_cli(
                "step-summary", "--usage", str(usage), "--max-usd", "0.10"
            )
            self.assertIn("### Torii cost budget (F29)", cp.stdout)
            self.assertIn("OVER BUDGET", cp.stdout)


if __name__ == "__main__":
    unittest.main()
