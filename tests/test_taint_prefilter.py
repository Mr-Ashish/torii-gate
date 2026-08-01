"""Tests for F71 taint prefilter + federated sanitized signals."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "taint_prefilter.py"
CASES = ROOT / "docs" / "benchmarks" / "cases" / "insecure-demo.json"
DEMO = ROOT / "demo" / "insecure"


class TaintPrefilterTests(unittest.TestCase):
    def test_scan_demo_finds_sinks(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "scan", str(DEMO), "--json"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertGreaterEqual(data["candidate_count"], 3)
        themes = {c["theme"] for c in data["candidates"]}
        self.assertIn("sql_injection", themes)
        self.assertIn("insecure_deserialization", themes)
        self.assertIn("command_injection", themes)

    def test_score_demo_full_recall(self):
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "score",
                str(DEMO),
                "--cases",
                str(CASES),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["passed"])
        self.assertEqual(data["fn"], 0)
        self.assertAlmostEqual(data["recall"], 1.0)

    def test_fixture_offline_e2e(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "fixture"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        self.assertTrue(data["fixture_pass"])
        self.assertTrue(data["privacy_ok"])
        self.assertTrue(data["inject_prefilter"])
        self.assertTrue(data["inject_federated"])

    def test_federate_strips_private_paths(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            tp = td_path / "tp.json"
            tp.write_text(
                json.dumps(
                    {
                        "signatures": [
                            {
                                "id": "x",
                                "theme": "sql_injection",
                                "cwe": ["CWE-89"],
                                "keywords": ["sql injection", "cwe-89"],
                                "path_globs": [
                                    "/Users/alice/secret-org/repo/models/db.py",
                                    "Acme--private-repo/app.py",
                                ],
                                "hits": 3,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            out = td_path / "fed.json"
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "federate",
                    "--tp-signatures",
                    str(tp),
                    "--out",
                    str(out),
                    "--tenant",
                    "Acme-Corp",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["privacy_ok"])
            self.assertGreaterEqual(payload["count"], 1)
            blob = json.dumps(payload)
            self.assertNotIn("/Users/", blob)
            self.assertNotIn("secret-org", blob)
            self.assertNotIn("Acme-Corp", blob)  # tenant hashed, not raw
            for s in payload["signals"]:
                for b in s.get("path_basenames") or []:
                    self.assertNotIn("/", b)
                    self.assertNotIn("--", b)

    def test_inject_writes_marker(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = Path(td) / "p.md"
            prompt.write_text("# hello\n", encoding="utf-8")
            r = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "inject",
                    "--prompt",
                    str(prompt),
                    str(DEMO),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            body = prompt.read_text(encoding="utf-8")
            self.assertIn("torii-f71-taint-prefilter", body)
            self.assertIn("sql_injection", body)

    def test_module_scan_text_flow(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import taint_prefilter as tp  # type: ignore

        src = (DEMO / "app.py").read_text(encoding="utf-8")
        hits, flows = tp.scan_text(src, path="demo/insecure/app.py", lang="py")
        self.assertGreater(len(hits), 0)
        self.assertGreaterEqual(len(flows), 3)
        themes = {f.theme for f in flows}
        self.assertIn("sql_injection", themes)


if __name__ == "__main__":
    unittest.main()
