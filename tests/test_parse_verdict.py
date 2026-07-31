#!/usr/bin/env python3
"""Unit tests for F22 parse-verdict.py (stdlib only)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "parse-verdict.py"


def _contract(verdict: str = "APPROVE", score: int = 90, conf: str = "high") -> str:
    return (
        f"## 🏴‍☠️ Torii Review — PR #7\n\n"
        f"**Verdict:** {verdict}\n"
        f"**Confidence:** {conf}\n"
        f"**Score:** {score}/100\n"
        f"**Review effort:** 2/5\n\n"
        "### Summary\nok\n\n"
        "### Blocking\n- None\n\n"
        "### Security audit\nNo\n"
    )


class ParseVerdictTests(unittest.TestCase):
    def run_cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=check,
        )

    def parse_kv(self, *args: str) -> dict[str, str]:
        cp = self.run_cli(*args)
        out: dict[str, str] = {}
        for line in cp.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k] = v
        return out

    def test_approve_maps_plus_one_success(self):
        kv = self.parse_kv("--text", _contract("APPROVE"), "--pipeline-rc", "0")
        self.assertEqual(kv["verdict"], "APPROVE")
        self.assertEqual(kv["score"], "90")
        self.assertEqual(kv["confidence"], "high")
        self.assertEqual(kv["reaction"], "+1")
        self.assertEqual(kv["status_state"], "success")
        self.assertIn("APPROVE", kv["status_desc"])
        self.assertEqual(kv["review_event"], "APPROVE")
        self.assertEqual(kv["pipeline_ok"], "true")

    def test_request_changes_maps_minus_one_failure(self):
        kv = self.parse_kv(
            "--text", _contract("REQUEST CHANGES"), "--pipeline-rc", "0"
        )
        self.assertEqual(kv["verdict"], "REQUEST_CHANGES")
        self.assertEqual(kv["reaction"], "-1")
        self.assertEqual(kv["status_state"], "failure")
        self.assertIn("REQUEST CHANGES", kv["status_desc"])
        self.assertEqual(kv["review_event"], "REQUEST_CHANGES")

    def test_comment_maps_eyes_success(self):
        kv = self.parse_kv("--text", _contract("COMMENT"), "--pipeline-rc", "0")
        self.assertEqual(kv["verdict"], "COMMENT")
        self.assertEqual(kv["reaction"], "eyes")
        self.assertEqual(kv["status_state"], "success")
        self.assertEqual(kv["review_event"], "COMMENT")

    def test_pipeline_fail_overrides_to_error(self):
        kv = self.parse_kv("--text", _contract("APPROVE"), "--pipeline-rc", "1")
        self.assertEqual(kv["verdict"], "APPROVE")  # still parsed
        self.assertEqual(kv["pipeline_ok"], "false")
        self.assertEqual(kv["reaction"], "-1")
        self.assertEqual(kv["status_state"], "error")
        # F23: infra failure must not REQUEST_CHANGES
        self.assertEqual(kv["review_event"], "COMMENT")

    def test_aliases(self):
        for raw, canon in (
            ("APPROVED", "APPROVE"),
            ("LGTM", "APPROVE"),
            ("REQUEST_CHANGES", "REQUEST_CHANGES"),
            ("changes requested", "REQUEST_CHANGES"),
            ("COMMENT — minor nits", "COMMENT"),
        ):
            kv = self.parse_kv("--text", _contract(raw), "--pipeline-rc", "0")
            self.assertEqual(kv["verdict"], canon, raw)

    def test_unknown_verdict(self):
        body = "## x\n**Verdict:** SHIP IT\n**Score:** 1/100\n"
        kv = self.parse_kv("--text", body, "--pipeline-rc", "0")
        self.assertEqual(kv["verdict"], "UNKNOWN")
        self.assertEqual(kv["reaction"], "eyes")
        self.assertEqual(kv["status_state"], "success")
        self.assertEqual(kv["review_event"], "COMMENT")

    def test_file_input(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "review.md"
            p.write_text(_contract("REQUEST CHANGES", score=40, conf="medium"))
            kv = self.parse_kv(str(p), "--pipeline-rc", "0")
            self.assertEqual(kv["verdict"], "REQUEST_CHANGES")
            self.assertEqual(kv["score"], "40")
            self.assertEqual(kv["confidence"], "medium")
            self.assertEqual(kv["review_event"], "REQUEST_CHANGES")

    def test_summary_format(self):
        cp = self.run_cli(
            "--text", _contract("APPROVE"), "--pipeline-rc", "0", "--format", "summary"
        )
        self.assertIn("### Torii verdict (F22/F23)", cp.stdout)
        self.assertIn("APPROVE", cp.stdout)
        self.assertIn("success", cp.stdout)
        self.assertIn("PR review event", cp.stdout)

    def test_json_format(self):
        cp = self.run_cli(
            "--text", _contract("COMMENT"), "--pipeline-rc", "0", "--format", "json"
        )
        data = json.loads(cp.stdout)
        self.assertEqual(data["verdict"], "COMMENT")
        self.assertEqual(data["reaction"], "eyes")
        self.assertEqual(data["review_event"], "COMMENT")


if __name__ == "__main__":
    unittest.main()
