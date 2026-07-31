"""F19: per-PR re-trigger cooldown."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cooldown-check.sh"

# Fixed "now" for deterministic age math
NOW = 1_700_000_000  # 2023-11-14-ish epoch


def _run(
    pr: str = "42",
    comments: list[dict] | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    extra = dict(env or {})
    base = {**os.environ, **extra}
    base.pop("TORII_COOLDOWN_FORCE", None)
    if "TORII_COOLDOWN_FORCE" in (env or {}):
        base["TORII_COOLDOWN_FORCE"] = env["TORII_COOLDOWN_FORCE"]
    base["NOW_EPOCH"] = extra.get("NOW_EPOCH", str(NOW))
    if "TORII_COOLDOWN_SECONDS" not in base and "TORII_COOLDOWN_SECONDS" not in (env or {}):
        base["TORII_COOLDOWN_SECONDS"] = "900"

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(comments if comments is not None else [], f)
        fixture = f.name
    try:
        base["TORII_COOLDOWN_FIXTURE"] = fixture
        return subprocess.run(
            ["bash", str(SCRIPT), pr],
            capture_output=True,
            text=True,
            env=base,
            check=False,
        )
    finally:
        Path(fixture).unlink(missing_ok=True)


def _kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


def _iso(epoch: int) -> str:
    # UTC Z
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _success_body(pr: str = "42") -> str:
    return (
        f"<!-- torii-review pr={pr} -->\n"
        f"## Torii Review — PR #{pr}\n\n"
        "**Verdict:** APPROVE\n"
        "### Summary\nLooks good.\n"
        "---\n*Torii · Hermes Agent · OpenRouter · memory-backed review*\n"
    )


def _fail_body(pr: str = "42") -> str:
    return (
        f"<!-- torii-review pr={pr} -->\n"
        f"## Torii Review — PR #{pr}\n\n"
        "**Verdict:** COMMENT\n"
        "### Summary\nTorii failed to produce a review (hermes exit 1).\n"
        "### What I checked\n- Failure path only\n"
    )


class CooldownCheckTests(unittest.TestCase):
    def test_no_comments_allows(self):
        r = _run(comments=[])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(_kv(r.stdout)["allowed"], "true")
        self.assertEqual(_kv(r.stdout)["reason"], "no_recent_success")

    def test_recent_success_blocks(self):
        r = _run(
            comments=[
                {
                    "created_at": _iso(NOW - 60),
                    "body": _success_body(),
                }
            ],
            env={"TORII_COOLDOWN_SECONDS": "900"},
        )
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        kv = _kv(r.stdout)
        self.assertEqual(kv["allowed"], "false")
        self.assertEqual(kv["reason"], "cooldown_active")
        self.assertEqual(kv["remaining_s"], "840")

    def test_old_success_allows(self):
        r = _run(
            comments=[
                {
                    "created_at": _iso(NOW - 1800),
                    "body": _success_body(),
                }
            ],
            env={"TORII_COOLDOWN_SECONDS": "900"},
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(_kv(r.stdout)["reason"], "cooldown_expired")

    def test_recent_failure_allows_retry(self):
        r = _run(
            comments=[
                {
                    "created_at": _iso(NOW - 30),
                    "body": _fail_body(),
                }
            ],
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(_kv(r.stdout)["reason"], "no_recent_success")

    def test_force_overrides(self):
        r = _run(
            comments=[
                {
                    "created_at": _iso(NOW - 10),
                    "body": _success_body(),
                }
            ],
            env={"TORII_COOLDOWN_FORCE": "1"},
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(_kv(r.stdout)["reason"], "force")

    def test_disabled_zero(self):
        r = _run(
            comments=[
                {
                    "created_at": _iso(NOW - 10),
                    "body": _success_body(),
                }
            ],
            env={"TORII_COOLDOWN_SECONDS": "0"},
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(_kv(r.stdout)["reason"], "disabled")

    def test_wrong_pr_marker_ignored(self):
        r = _run(
            pr="99",
            comments=[
                {
                    "created_at": _iso(NOW - 10),
                    "body": _success_body("42"),
                }
            ],
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(_kv(r.stdout)["reason"], "no_recent_success")

    def test_picks_latest_success(self):
        r = _run(
            comments=[
                {
                    "created_at": _iso(NOW - 5000),
                    "body": _success_body(),
                },
                {
                    "created_at": _iso(NOW - 100),
                    "body": _success_body(),
                },
            ],
            env={"TORII_COOLDOWN_SECONDS": "900"},
        )
        self.assertEqual(r.returncode, 2)
        self.assertEqual(_kv(r.stdout)["age_s"], "100")


if __name__ == "__main__":
    unittest.main()
