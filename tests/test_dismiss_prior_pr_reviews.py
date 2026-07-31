#!/usr/bin/env python3
"""Unit tests for F24 dismiss-prior-pr-reviews.sh (fixture mode, no network)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dismiss-prior-pr-reviews.sh"


def _run(
    pr: str = "7",
    *,
    fixture: Path | None = None,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "REPO": "owner/repo",
        "PR_NUMBER": pr,
        "GH_TOKEN": "fake",
    }
    # Drop inherited fixture unless set
    env.pop("TORII_PR_REVIEWS_FIXTURE", None)
    env.pop("TORII_REPLACE_PREVIOUS", None)
    if fixture is not None:
        env["TORII_PR_REVIEWS_FIXTURE"] = str(fixture)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), pr],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


class DismissPriorPrReviewsTests(unittest.TestCase):
    def test_replace_off_skips(self):
        r = _run(env_extra={"TORII_REPLACE_PREVIOUS": "0"})
        self.assertEqual(r.returncode, 0, r.stderr)
        kv = _kv(r.stdout)
        self.assertEqual(kv["dismissed_count"], "0")
        self.assertEqual(kv["reason"], "replace_off")

    def test_dismisses_approved_and_changes_requested(self):
        reviews = [
            {
                "id": 11,
                "state": "APPROVED",
                "body": "old\n<!-- torii-pr-review pr=7 run=1 -->",
            },
            {
                "id": 22,
                "state": "CHANGES_REQUESTED",
                "body": "## Torii\n<!-- torii-pr-review pr=7 run=2 -->",
            },
            {
                "id": 33,
                "state": "COMMENTED",
                "body": "short\n<!-- torii-pr-review pr=7 run=3 -->",
            },
            {
                "id": 44,
                "state": "APPROVED",
                "body": "someone else — no marker",
            },
            {
                "id": 55,
                "state": "DISMISSED",
                "body": "done\n<!-- torii-pr-review pr=7 run=0 -->",
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "reviews.json"
            p.write_text(json.dumps(reviews))
            r = _run(fixture=p)
        self.assertEqual(r.returncode, 0, r.stderr)
        kv = _kv(r.stdout)
        self.assertEqual(kv["dismissed_count"], "2")
        self.assertEqual(kv["skipped_commented"], "1")
        self.assertEqual(kv["reason"], "ok")

    def test_wrong_pr_marker_ignored(self):
        reviews = [
            {
                "id": 99,
                "state": "CHANGES_REQUESTED",
                "body": "<!-- torii-pr-review pr=99 run=x -->",
            }
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "reviews.json"
            p.write_text(json.dumps(reviews))
            r = _run(pr="7", fixture=p)
        kv = _kv(r.stdout)
        self.assertEqual(kv["dismissed_count"], "0")
        self.assertEqual(kv["skipped_commented"], "0")

    def test_paginated_concat_arrays(self):
        """gh --paginate can emit multiple JSON arrays back-to-back."""
        page1 = [{"id": 1, "state": "APPROVED", "body": "<!-- torii-pr-review pr=7 -->"}]
        page2 = [
            {
                "id": 2,
                "state": "CHANGES_REQUESTED",
                "body": "<!-- torii-pr-review pr=7 -->",
            }
        ]
        raw = json.dumps(page1) + "\n" + json.dumps(page2)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "reviews.json"
            p.write_text(raw)
            r = _run(fixture=p)
        kv = _kv(r.stdout)
        self.assertEqual(kv["dismissed_count"], "2")

    def test_install_pack_includes_script(self):
        text = (ROOT / "scripts" / "install-torii.sh").read_text()
        self.assertIn("dismiss-prior-pr-reviews.sh", text)


if __name__ == "__main__":
    unittest.main()
