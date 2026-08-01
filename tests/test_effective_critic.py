"""Tests for F95 effective-aware dual-pass critic + federated effective export."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class EffectiveDualPassTests(unittest.TestCase):
    def test_high_effective_confirms(self):
        from bench_security_gate import dual_pass_critic  # type: ignore

        review = """
## Finding: SQL injection
**Path:** `app.py`
User input is concatenated into SQL: `sql injection` via f-string execute.
"""
        tp = [
            {
                "id": "sqli-hot",
                "theme": "sql_injection",
                "keywords": ["sql injection", "f-string"],
                "effective_score": 0.9,
            }
        ]
        r = dual_pass_critic(review, tp_signatures=tp)
        self.assertTrue(r.get("effective_aware"))
        self.assertGreaterEqual(r.get("confirmed_tp", 0), 1)
        self.assertEqual(r.get("stale_tp_match", 0), 0)

    def test_low_effective_stale_not_confirm(self):
        from bench_security_gate import dual_pass_critic  # type: ignore

        review = """
## Finding: SQL injection
**Path:** `app.py`
User input is concatenated into SQL: `sql injection` via f-string execute.
"""
        tp = [
            {
                "id": "sqli-stale",
                "theme": "sql_injection",
                "keywords": ["sql injection"],
                "effective_score": 0.05,
            }
        ]
        r = dual_pass_critic(review, tp_signatures=tp)
        self.assertEqual(r.get("confirmed_tp", 0), 0)
        self.assertGreaterEqual(r.get("stale_tp_match", 0), 1)
        findings = r.get("findings") or []
        self.assertTrue(any(f.get("status") == "stale_tp_match" for f in findings))

    def test_legacy_without_score_still_confirms(self):
        from bench_security_gate import dual_pass_critic  # type: ignore

        review = """
## Finding: command injection
**Path:** `runner.py`
Uses shell=True with user input — command injection risk.
"""
        tp = [
            {
                "id": "cmdi",
                "theme": "command_injection",
                "keywords": ["command injection", "shell=true"],
            }
        ]
        r = dual_pass_critic(review, tp_signatures=tp)
        # default effective 0.55 >= 0.25 floor
        self.assertGreaterEqual(r.get("confirmed_tp", 0), 1)


class FederatedEffectiveTests(unittest.TestCase):
    def test_federated_fixture_f95(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "federated_hub_ingest.py"), "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertTrue(data.get("effective_max_ok"))
        self.assertTrue(data.get("eff_promote_ok"))

    def test_consolidate_federate_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "tp-signatures.json"
            store.write_text(
                json.dumps(
                    {
                        "signatures": [
                            {
                                "id": "sqli",
                                "theme": "sql_injection",
                                "keywords": ["sqli"],
                                "path_globs": ["app.py"],
                                "hits": 3,
                                "last_seen": "2026-08-01T00:00:00Z",
                                "effective_score": 0.8,
                                "importance_score": 0.7,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "memory_consolidate.py"),
                    "federate",
                    "--store",
                    str(store),
                    "--dry-run",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env={**os.environ, "TORII_MEMORY_CONSOLIDATE": "1"},
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            data = json.loads(r.stdout)
            self.assertGreaterEqual(data.get("signal_count", 0), 1)
            self.assertEqual(data.get("feature"), "F95")


if __name__ == "__main__":
    unittest.main()
