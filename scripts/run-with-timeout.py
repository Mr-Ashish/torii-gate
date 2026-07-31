#!/usr/bin/env python3
"""F36: portable wall-clock timeout for a child process group.

Kills runaway Hermes/OpenRouter sessions so a hung review cannot burn the
full job timeout (GHA 90m / Modal 25m) on a stuck agent loop.

Usage:
  python3 scripts/run-with-timeout.py --seconds 1500 -- cmd [args...]
  python3 scripts/run-with-timeout.py 1500 -- cmd [args...]
  python3 scripts/run-with-timeout.py resolve   # print effective seconds

Exit codes:
  child return code on normal completion
  124 on wall-clock timeout (GNU `timeout` convention)
  125 invalid usage / empty command

Env:
  TORII_REVIEW_TIMEOUT_SECONDS  default seconds when --seconds omitted
                                (default 1500; 0/off/false/no disables)

Soft policy: this helper never swallows the child exit code except timeout→124.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from typing import Sequence


# Align with Modal review_pr hard cap (~25m). 0 = disabled.
DEFAULT_SECONDS = 1500
TIMEOUT_EXIT = 124
USAGE_EXIT = 125


def parse_seconds(raw: str | None) -> int:
    """Parse timeout seconds. Empty/0/off/false/no/invalid → 0 (disabled)."""
    if raw is None:
        return DEFAULT_SECONDS
    s = str(raw).strip().lower()
    if s in ("", "0", "off", "false", "no", "none", "disabled"):
        return 0
    try:
        n = int(s)
    except ValueError:
        return 0
    if n < 0:
        return 0
    # Cap at 6h — never exceed a sane CI bound via typo
    return min(n, 6 * 3600)


def effective_seconds(cli: str | None = None) -> int:
    if cli is not None and str(cli).strip() != "":
        return parse_seconds(cli)
    return parse_seconds(os.environ.get("TORII_REVIEW_TIMEOUT_SECONDS"))


def run_with_timeout(cmd: Sequence[str], seconds: int) -> int:
    """Run cmd; on timeout SIGTERM the process group, then SIGKILL after 30s."""
    if not cmd:
        return USAGE_EXIT
    if seconds <= 0:
        proc = subprocess.run(list(cmd), check=False)
        return int(proc.returncode or 0)

    # New session → process group id == pid; kill descendants (hermes children)
    proc = subprocess.Popen(list(cmd), start_new_session=True)
    try:
        return int(proc.wait(timeout=seconds) or 0)
    except subprocess.TimeoutExpired:
        _kill_group(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            _kill_group(proc.pid, signal.SIGKILL)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        return TIMEOUT_EXIT


def _kill_group(pid: int, sig: int) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return
    except PermissionError:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "resolve":
        # Optional: resolve SECONDS [from env or next arg]
        raw = argv[1] if len(argv) > 1 else None
        print(effective_seconds(raw))
        return 0

    p = argparse.ArgumentParser(description="F36 portable run-with-timeout")
    p.add_argument(
        "--seconds",
        "-s",
        default=None,
        help="Wall seconds (default: env TORII_REVIEW_TIMEOUT_SECONDS or 1500; 0=off)",
    )
    p.add_argument(
        "rest",
        nargs=argparse.REMAINDER,
        help="Command after -- ",
    )
    # Also allow: run-with-timeout.py 1500 -- cmd
    if argv and not argv[0].startswith("-") and argv[0].isdigit():
        argv = ["--seconds", argv[0], *argv[1:]]

    args = p.parse_args(argv)
    cmd = list(args.rest or [])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("usage: run-with-timeout.py [--seconds N] -- cmd [args...]", file=sys.stderr)
        return USAGE_EXIT

    seconds = effective_seconds(args.seconds)
    if seconds > 0:
        print(f"F36 timeout: {seconds}s · {' '.join(cmd[:3])}…", file=sys.stderr)
    t0 = time.monotonic()
    rc = run_with_timeout(cmd, seconds)
    elapsed = time.monotonic() - t0
    if rc == TIMEOUT_EXIT:
        print(
            f"F36 TIMEOUT after {elapsed:.1f}s (limit {seconds}s) — killed process group",
            file=sys.stderr,
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
