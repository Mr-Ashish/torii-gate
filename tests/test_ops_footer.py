#!/usr/bin/env python3
"""F35: ops deep-link footer for PR comments."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops_footer.py"
sys.path.insert(0, str(ROOT / "scripts"))

from ops_footer import (  # noqa: E402
    append_ops_to_review,
    format_ops_line,
    format_step_summary,
    run_url,
)


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    e = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=e,
    )


class OpsFooterTests(unittest.TestCase):
    def test_run_url(self):
        u = run_url(
            server="https://github.com",
            repo="Mr-Ashish/torii-gate",
            run_id="12345",
        )
        self.assertEqual(
            u,
            "https://github.com/Mr-Ashish/torii-gate/actions/runs/12345",
        )
        self.assertIsNone(run_url(repo="a/b", run_id="local"))

    def test_format_line_with_run_and_console(self):
        line = format_ops_line(
            server="https://github.com",
            repo="o/r",
            run_id="9",
            console_url="https://console.example/",
        )
        self.assertIn("Ops (F35):", line)
        self.assertIn("actions/runs/9", line)
        self.assertIn("Run Console", line)
        self.assertIn("run-bundle.json", line)

    def test_disabled(self):
        old = os.environ.get("TORII_OPS_FOOTER")
        try:
            os.environ["TORII_OPS_FOOTER"] = "0"
            self.assertEqual(format_ops_line(repo="a/b", run_id="1"), "")
        finally:
            if old is None:
                os.environ.pop("TORII_OPS_FOOTER", None)
            else:
                os.environ["TORII_OPS_FOOTER"] = old

    def test_append_after_cost(self):
        with tempfile.TemporaryDirectory() as td:
            review = Path(td) / "review.md"
            review.write_text(
                "## Review\n\n"
                "**Verdict:** APPROVE\n\n"
                "*Torii · Hermes Agent · OpenRouter · memory-backed review*\n"
                "*Cost / usage: model=`x` · ~$0.01 · 1k tokens · 1 API calls*\n",
                encoding="utf-8",
            )
            env = {
                "TORII_OPS_FOOTER": "1",
                "GITHUB_SERVER_URL": "https://github.com",
                "GITHUB_REPOSITORY": "acme/app",
                "GITHUB_RUN_ID": "42",
                "TORII_CONSOLE_URL": "",
            }
            # clear console from parent env
            e = {**os.environ, **env}
            e.pop("TORII_CONSOLE_URL", None)
            r = _run(["append", "--review", str(review)], env=e)
            self.assertEqual(r.returncode, 0, r.stderr)
            body = review.read_text()
            self.assertIn("*Ops (F35):", body)
            self.assertIn("actions/runs/42", body)
            # after cost
            self.assertLess(body.index("Cost / usage:"), body.index("Ops (F35):"))

    def test_step_summary(self):
        md = format_step_summary(
            server="https://github.com", repo="a/b", run_id="7"
        )
        self.assertIn("Torii ops links (F35)", md)
        self.assertIn("actions/runs/7", md)

    def test_install_lists(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text()
        self.assertIn("ops_footer.py", text)


if __name__ == "__main__":
    unittest.main()
