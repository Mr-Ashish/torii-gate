"""Tests for F77 cross-tenant hub federated signal ingest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "federated_hub_ingest.py"
INGEST = ROOT / "scripts" / "hub-ingest-run.py"
BUILD = ROOT / "scripts" / "build-hub-payload.py"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    base = {**os.environ, "TORII_FEDERATED_HUB": "1"}
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base,
    )


class FederatedHubIngestTests(unittest.TestCase):
    def test_fixture_two_tenants(self):
        r = _run(["fixture"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"], data)
        self.assertGreaterEqual(int(data.get("sqli_tenants") or 0), 2)
        self.assertTrue(data["privacy_file_ok"])
        self.assertTrue(data["promote_ok"])

    def test_hub_ingest_with_federated_payload(self):
        with tempfile.TemporaryDirectory() as td:
            hub = Path(td)
            payload = {
                "run": {
                    "schema_version": 1,
                    "source_repo": "acme/widgets",
                    "pr_number": "11",
                    "run_id": "11",
                    "run_attempt": "1",
                    "trace_id": "pr11-run11-a1",
                    "model": "test",
                    "status": "success",
                    "verdict": "REQUEST CHANGES",
                    "tenant": "team-gamma",
                    "review_md": "## Review\n\n**Verdict:** REQUEST CHANGES\n",
                    "memory_block": "## run\n- Verdict: REQUEST CHANGES\n",
                    "timings": {},
                    "meta": {},
                    "federated_signals": {
                        "schema_version": 1,
                        "signals": [
                            {
                                "id": "sql_injection",
                                "theme": "sql_injection",
                                "cwe": ["CWE-89"],
                                "keywords": ["sql injection"],
                                "path_basenames": ["app.py"],
                                "hits": 2,
                            }
                        ],
                    },
                }
            }
            env = os.environ.copy()
            env["CLIENT_PAYLOAD"] = json.dumps(payload)
            env["HUB_ROOT"] = str(hub)
            env["TORII_FEDERATED_HUB"] = "1"
            r = subprocess.run(
                [sys.executable, str(INGEST)],
                env=env,
                cwd=str(hub),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("FEDERATED_HUB=", r.stdout)
            fed = hub / "memory" / "federation" / "federated-signals.json"
            self.assertTrue(fed.is_file(), fed)
            doc = json.loads(fed.read_text(encoding="utf-8"))
            self.assertTrue(doc.get("privacy_ok"))
            self.assertGreaterEqual(doc.get("count") or 0, 1)
            # tenant local
            t_fed = (
                hub
                / "memory"
                / "tenants"
                / "team-gamma"
                / "federation"
                / "federated-signals.json"
            )
            self.assertTrue(t_fed.is_file(), t_fed)

    def test_build_payload_includes_federated_signals(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / "review-3.md").write_text(
                "## R\n\n**Verdict:** COMMENT\n", encoding="utf-8"
            )
            (out / "federated-signals.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "signals": [
                            {
                                "id": "xss",
                                "theme": "xss",
                                "cwe": ["CWE-79"],
                                "keywords": ["xss"],
                                "hits": 1,
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["OUT_DIR"] = str(out)
            env["REPO"] = "acme/widgets"
            env["PR_NUMBER"] = "3"
            env["GITHUB_RUN_ID"] = "1"
            env["GITHUB_RUN_ATTEMPT"] = "1"
            r = subprocess.run(
                [sys.executable, str(BUILD)],
                env=env,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            payload_path = out / "hub-payload.json"
            self.assertTrue(payload_path.is_file())
            data = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertIsNotNone(data.get("federated_signals"))
            self.assertEqual(data["federated_signals"]["count"], 1)

    def test_status_enabled(self):
        r = _run(["status"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertEqual(data["feature"], "F77")
        self.assertTrue(data["enabled"])


if __name__ == "__main__":
    unittest.main()
