"""GATE_CERT soft wire: save-trace emits certificate when review exists."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAVE = ROOT / "scripts" / "save-trace.sh"
REVIEW = ROOT / "docs" / "benchmarks" / "fixtures" / "insecure-demo-good-review.md"
CRITIC = ROOT / "docs" / "benchmarks" / "fixtures" / "second-agent-critic.json"


class GateCertificateWireTests(unittest.TestCase):
    def test_save_trace_emits_certificate(self):
        self.assertTrue(SAVE.is_file())
        self.assertTrue(REVIEW.is_file())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            out.mkdir()
            # mimic orchestrator layout
            (out / "review-42.md").write_text(
                REVIEW.read_text(encoding="utf-8"), encoding="utf-8"
            )
            if CRITIC.is_file():
                (out / "second-agent-critic.json").write_text(
                    CRITIC.read_text(encoding="utf-8"), encoding="utf-8"
                )
            env = {
                **os.environ,
                "TORII_ROOT": str(ROOT),
                "OUT_DIR": str(out),
                "PR_NUMBER": "42",
                "REPO": "pytorch/pytorch",
                "TORII_GATE_CERTIFICATE": "1",
                "TORII_TRACE_VAULT": "0",  # skip paper vault side effects
                "GITHUB_RUN_ID": "wiretest",
            }
            r = subprocess.run(
                ["bash", str(SAVE)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            cert_path = out / "gate-certificate.json"
            self.assertTrue(cert_path.is_file(), r.stderr)
            cert = json.loads(cert_path.read_text(encoding="utf-8"))
            self.assertTrue(cert.get("block"))
            self.assertEqual(cert.get("verdict"), "REQUEST_CHANGES")
            self.assertTrue(cert.get("certificate_id", "").startswith("gc-"))
            # also landed in TRACE_DIR
            latest = (out / "latest-trace-dir.txt").read_text(encoding="utf-8").strip()
            self.assertTrue(Path(latest, "gate-certificate.json").is_file())

    def test_disable_env(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            out.mkdir()
            (out / "review-1.md").write_text(
                REVIEW.read_text(encoding="utf-8"), encoding="utf-8"
            )
            env = {
                **os.environ,
                "TORII_ROOT": str(ROOT),
                "OUT_DIR": str(out),
                "PR_NUMBER": "1",
                "REPO": "x/y",
                "TORII_GATE_CERTIFICATE": "0",
                "TORII_TRACE_VAULT": "0",
                "GITHUB_RUN_ID": "wireoff",
            }
            r = subprocess.run(
                ["bash", str(SAVE)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertFalse((out / "gate-certificate.json").is_file())


if __name__ == "__main__":
    unittest.main()
