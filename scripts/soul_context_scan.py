#!/usr/bin/env python3
"""F46 / H13: keep agent/SOUL.md loadable under Hermes context-file scanner.

Hermes (`agent/prompt_builder._scan_context_content`) runs threat_patterns with
scope=context on SOUL.md and **blocks** the whole file when any match fires
(replaces content with a [BLOCKED: …] placeholder). Torii's F44 e2e log:

  Context file SOUL.md blocked: prompt_injection

Root cause: the trust-model section quoted the attack phrase
"ignore previous instructions", which is a classic pattern.

This script:
  - Scans SOUL (or any path) with the same classic/context patterns we care about
  - Exits 2 when content would be blocked (CI / pre-flight)
  - Detects blocked lines in Hermes logs (post-run ops signal)

Usage:
  python3 scripts/soul_context_scan.py check [PATH]     # default agent/SOUL.md
  python3 scripts/soul_context_scan.py detect LOG…      # exit 2 if SOUL blocked in logs
  python3 scripts/soul_context_scan.py patterns         # list pattern ids

Env:
  TORII_SOUL_SCAN=1 (default) | 0/off to skip in shell wrappers
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Mirror Hermes tools/threat_patterns.py classic + context scope (subset).
# Keep in sync when hermes pin moves if SOUL starts blocking again.
_FILLER = r"(?:\w+\s+){0,8}"

# (regex, pattern_id) — all treated as blocking for SOUL (Hermes blocks on any).
_BLOCKING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            rf"ignore\s+{_FILLER}(previous|all|above|prior)\s+{_FILLER}instructions",
            re.I,
        ),
        "prompt_injection",
    ),
    (re.compile(r"system\s+prompt\s+override", re.I), "sys_prompt_override"),
    (
        re.compile(
            rf"disregard\s+{_FILLER}(your|all|any)\s+{_FILLER}(instructions|rules|guidelines)",
            re.I,
        ),
        "disregard_rules",
    ),
    (
        re.compile(
            rf"act\s+as\s+(if|though)\s+{_FILLER}you\s+{_FILLER}(have\s+no|don't\s+have)\s+{_FILLER}(restrictions|limits|rules)",
            re.I,
        ),
        "bypass_restrictions",
    ),
    (
        re.compile(
            rf"you\s+are\s+{_FILLER}now\s+(?:a|an|the)\s+",
            re.I,
        ),
        "role_hijack",
    ),
    (
        re.compile(rf"pretend\s+{_FILLER}(you\s+are|to\s+be)\s+", re.I),
        "role_pretend",
    ),
    (
        re.compile(rf"output\s+{_FILLER}(system|initial)\s+prompt", re.I),
        "leak_system_prompt",
    ),
    (
        re.compile(
            rf"(respond|answer|reply)\s+without\s+{_FILLER}(restrictions|limitations|filters|safety)",
            re.I,
        ),
        "remove_filters",
    ),
]

_LOG_BLOCKED_RX = re.compile(
    r"Context file\s+SOUL\.md\s+blocked\s*:\s*([^\n]+)",
    re.I,
)


def enabled() -> bool:
    v = (os.environ.get("TORII_SOUL_SCAN") or "1").strip().lower()
    return v not in ("0", "false", "off", "no", "none", "disabled")


def scan_text(text: str) -> list[str]:
    """Return list of pattern_ids that match (empty = clean)."""
    if text.startswith("\ufeff"):
        text = text[1:]
    # Cap like Hermes MAX_SCAN_CHARS
    blob = text[:65_536]
    hits: list[str] = []
    seen: set[str] = set()
    for rx, pid in _BLOCKING_PATTERNS:
        if rx.search(blob) and pid not in seen:
            hits.append(pid)
            seen.add(pid)
    return hits


def scan_path(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return scan_text(path.read_text(encoding="utf-8", errors="replace"))


def detect_blocked_in_texts(texts: list[str]) -> tuple[bool, list[str]]:
    """True if any log blob shows SOUL.md blocked; return reason tokens."""
    reasons: list[str] = []
    hit = False
    for t in texts:
        if not t:
            continue
        for m in _LOG_BLOCKED_RX.finditer(t[:500_000]):
            hit = True
            reasons.append(m.group(1).strip())
    return hit, reasons


def detect_paths(paths: list[Path]) -> tuple[bool, list[str]]:
    blobs: list[str] = []
    for p in paths:
        if p.is_file():
            try:
                blobs.append(p.read_text(encoding="utf-8", errors="replace")[:500_000])
            except OSError:
                continue
    return detect_blocked_in_texts(blobs)


def default_soul_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "agent" / "SOUL.md"


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else default_soul_path()
    if not enabled() and not args.force:
        print("skipped=1")
        print("reason=scan_off")
        return 0
    try:
        hits = scan_path(path)
    except FileNotFoundError:
        print(f"error: SOUL not found: {path}", file=sys.stderr)
        return 1
    print(f"path={path}")
    print(f"clean={'1' if not hits else '0'}")
    print(f"findings={','.join(hits) if hits else ''}")
    if hits:
        print(
            f"error: {path.name} would be blocked by Hermes context scanner "
            f"({', '.join(hits)}). Rephrase without classic injection quotes "
            f"(H13/F46).",
            file=sys.stderr,
        )
        return 2
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    hit, reasons = detect_paths([Path(p) for p in args.paths])
    if hit:
        print("soul_blocked=1")
        print(f"reason={';'.join(reasons) if reasons else 'prompt_injection'}")
        return 2
    print("soul_blocked=0")
    return 0


def cmd_patterns(_args: argparse.Namespace) -> int:
    for _, pid in _BLOCKING_PATTERNS:
        print(pid)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Scan SOUL.md; exit 2 if would block")
    c.add_argument("path", nargs="?", default=None, help="Path (default agent/SOUL.md)")
    c.add_argument(
        "--force",
        action="store_true",
        help="Scan even when TORII_SOUL_SCAN=off",
    )
    c.set_defaults(func=cmd_check)

    d = sub.add_parser("detect", help="Detect SOUL blocked lines in hermes logs")
    d.add_argument("paths", nargs="+", help="Log / stderr paths")
    d.set_defaults(func=cmd_detect)

    s = sub.add_parser("patterns", help="List pattern ids")
    s.set_defaults(func=cmd_patterns)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
