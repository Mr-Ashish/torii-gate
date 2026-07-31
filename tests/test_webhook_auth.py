#!/usr/bin/env python3
"""F33/F34: webhook HMAC + bearer authorization (fail-closed default)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "webhook_auth.py"
sys.path.insert(0, str(ROOT / "scripts"))

from webhook_auth import (  # noqa: E402
    authorize_webhook,
    github_hmac_hex,
    github_signature_valid,
)


class WebhookAuthTests(unittest.TestCase):
    def test_fail_closed_when_no_secrets(self):
        r = authorize_webhook(b"{}", {}, secret="", token="", allow_open=False)
        self.assertFalse(r["ok"])
        self.assertEqual(r["auth"], "denied")
        self.assertIn("fail-closed", r.get("error", ""))

    def test_open_when_allow_open(self):
        r = authorize_webhook(b"{}", {}, secret="", token="", allow_open=True)
        self.assertTrue(r["ok"])
        self.assertEqual(r["auth"], "open")
        self.assertIn("warning", r)

    def test_open_via_env(self):
        old = os.environ.get("TORII_WEBHOOK_ALLOW_OPEN")
        try:
            os.environ["TORII_WEBHOOK_ALLOW_OPEN"] = "1"
            r = authorize_webhook(b"{}", {}, secret="", token="")
            self.assertTrue(r["ok"])
            self.assertEqual(r["auth"], "open")
        finally:
            if old is None:
                os.environ.pop("TORII_WEBHOOK_ALLOW_OPEN", None)
            else:
                os.environ["TORII_WEBHOOK_ALLOW_OPEN"] = old

    def test_hmac_good_and_bad(self):
        body = b'{"repo":"a/b","pr":1}'
        secret = "whsec_test"
        sig = f"sha256={github_hmac_hex(body, secret)}"
        self.assertTrue(github_signature_valid(body, sig, secret))
        good = authorize_webhook(
            body, {"X-Hub-Signature-256": sig}, secret=secret, token=""
        )
        self.assertTrue(good["ok"])
        self.assertEqual(good["auth"], "github_hmac")
        bad = authorize_webhook(
            body, {"x-hub-signature-256": "sha256=00"}, secret=secret, token=""
        )
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["auth"], "denied")

    def test_bearer(self):
        body = b"{}"
        r = authorize_webhook(
            body,
            {"Authorization": "Bearer abc"},
            secret="",
            token="abc",
        )
        self.assertTrue(r["ok"])
        self.assertEqual(r["auth"], "bearer")
        r2 = authorize_webhook(
            body, {"X-Torii-Token": "abc"}, secret="", token="abc"
        )
        self.assertTrue(r2["ok"])
        r3 = authorize_webhook(
            body, {"Authorization": "Bearer wrong"}, secret="", token="abc"
        )
        self.assertFalse(r3["ok"])

    def test_secret_without_signature_denied(self):
        r = authorize_webhook(b"{}", {}, secret="s", token="")
        self.assertFalse(r["ok"])
        self.assertEqual(r["auth"], "denied")

    def test_cli_sign_and_authorize(self):
        body = b'{"hello":1}'
        sign = subprocess.run(
            [sys.executable, str(SCRIPT), "sign", "--secret", "s", "--body", "-"],
            input=body,
            capture_output=True,
            check=False,
        )
        self.assertEqual(sign.returncode, 0, sign.stderr.decode())
        sig = sign.stdout.decode().strip()
        self.assertTrue(sig.startswith("sha256="))
        auth = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "authorize",
                "--secret",
                "s",
                "--body",
                "-",
                "--header",
                f"X-Hub-Signature-256: {sig}",
            ],
            input=body,
            capture_output=True,
            check=False,
        )
        self.assertEqual(auth.returncode, 0, auth.stderr.decode())
        data = json.loads(auth.stdout.decode())
        self.assertTrue(data["ok"])
        self.assertEqual(data["auth"], "github_hmac")

    def test_cli_fail_closed_no_creds(self):
        body = b"{}"
        env = {**os.environ}
        env.pop("TORII_WEBHOOK_ALLOW_OPEN", None)
        env.pop("TORII_WEBHOOK_SECRET", None)
        env.pop("TORII_WEBHOOK_TOKEN", None)
        auth = subprocess.run(
            [sys.executable, str(SCRIPT), "authorize", "--body", "-"],
            input=body,
            capture_output=True,
            check=False,
            env=env,
        )
        self.assertNotEqual(auth.returncode, 0)
        data = json.loads(auth.stdout.decode())
        self.assertFalse(data["ok"])


if __name__ == "__main__":
    unittest.main()
