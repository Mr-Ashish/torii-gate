#!/usr/bin/env python3
"""F41/F47: Hermes agent.max_turns resolver for Torii cost control.

Hermes defaults to 500 tool-calling iterations per turn — far too high for a
CI PR review (a solid Odoo monorepo review finishes in ~9 tool turns). Cap the
loop so a runaway agent cannot burn unbounded OpenRouter spend even when the
F36 wall-clock timeout has not yet fired.

**F47 (H14):** Do **not** pass ``--max-turns`` on the ``hermes`` CLI. Current
Hermes argparse has no such flag; the bare integer is treated as a subcommand
(``invalid choice: '25'``), ``hermes -z`` exits 2, and Torii falls back to
``hermes chat -q`` (zero tool turns). Apply the cap via:

  - env ``HERMES_MAX_ITERATIONS=<n>`` (Hermes-native), and
  - ``agent.max_turns: <n>`` in ``$HERMES_HOME/config.yaml``

Usage:
  python3 scripts/max_turns.py resolve [RAW]   # print integer or "off"
  python3 scripts/max_turns.py detect PATH…    # exit 2 if max-turns hit in logs

Env / var:
  TORII_MAX_TURNS  default 40; 0/off/false/no/none/disabled → unlimited (Hermes default)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Product default — well above normal PR tool loops (~5–15), well below Hermes 500.
DEFAULT_MAX_TURNS = 40
# Cap absurd values so a typo cannot request millions of iterations.
MAX_ALLOWED = 500

_HIT_PATTERNS = [
    re.compile(r"Iteration budget exhausted", re.I),
    re.compile(r"max_iterations_reached", re.I),
    re.compile(r"Reached maximum iterations", re.I),
    re.compile(r"Reached max iterations", re.I),
]


def parse_max_turns(raw: str | None, *, default: int = DEFAULT_MAX_TURNS) -> int | None:
    """Return positive int cap, or None when disabled (Hermes unlimited default)."""
    if raw is None:
        return default
    s = str(raw).strip().lower()
    if not s:
        return default
    if s in {"0", "off", "false", "no", "none", "disabled", "unlimited", "inf"}:
        return None
    try:
        n = int(s, 10)
    except ValueError:
        return default
    if n <= 0:
        return None
    return min(n, MAX_ALLOWED)


def effective_max_turns(cli_raw: str | None = None) -> int | None:
    """CLI/env precedence: explicit raw wins; else TORII_MAX_TURNS; else default 40."""
    if cli_raw is not None and str(cli_raw).strip() != "":
        return parse_max_turns(cli_raw)
    env = os.environ.get("TORII_MAX_TURNS")
    if env is not None and str(env).strip() != "":
        return parse_max_turns(env)
    return DEFAULT_MAX_TURNS


def detect_max_turns_hit(texts: list[str]) -> bool:
    """True if any text blob looks like Hermes hit the iteration budget."""
    for t in texts:
        if not t:
            continue
        for rx in _HIT_PATTERNS:
            if rx.search(t):
                return True
    return False


def detect_paths(paths: list[Path]) -> bool:
    blobs: list[str] = []
    for p in paths:
        if p.is_file():
            try:
                blobs.append(p.read_text(encoding="utf-8", errors="replace")[:500_000])
            except OSError:
                continue
    return detect_max_turns_hit(blobs)


def cmd_resolve(args: argparse.Namespace) -> int:
    n = effective_max_turns(args.raw)
    if n is None:
        print("off")
    else:
        print(n)
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    hit = detect_paths([Path(p) for p in args.paths])
    if hit:
        print("hit=1")
        return 2
    print("hit=0")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F41 Hermes max_turns helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("resolve", help="Print max turns integer or 'off'")
    r.add_argument("raw", nargs="?", default=None, help="Override raw (else env/default)")
    r.set_defaults(func=cmd_resolve)

    d = sub.add_parser("detect", help="Exit 2 if logs show iteration budget exhausted")
    d.add_argument("paths", nargs="+", help="Log / stderr / agent-loop files to scan")
    d.set_defaults(func=cmd_detect)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
