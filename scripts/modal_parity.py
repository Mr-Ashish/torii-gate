#!/usr/bin/env python3
"""F39: Modal host parity helpers (path-skip preflight + verdict signals).

Pure functions used by modal_app/review_pr so Modal runs the same cost/trust
gates as GHA (F38 path skip before clone, F22–F37/F9 after review).

Usage (offline):
  python3 scripts/modal_parity.py path-skip --path README.md --globs docs
  python3 scripts/modal_parity.py path-skip --paths-file pr-paths.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Import path-skip pure API (hyphenated filename)
_SCRIPTS = Path(__file__).resolve().parent
import importlib.util

_ps_spec = importlib.util.spec_from_file_location(
    "path_skip_check",
    _SCRIPTS / "path-skip-check.py",
)
assert _ps_spec and _ps_spec.loader
_ps = importlib.util.module_from_spec(_ps_spec)
_ps_spec.loader.exec_module(_ps)
decide = _ps.decide
load_paths = _ps.load_paths
parse_globs = _ps.parse_globs


def path_skip_preflight(
    paths: list[str],
    *,
    globs_raw: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Decide whether Modal should skip the paid review.

    Returns:
      {
        skip: bool,
        allowed: "true"|"false",
        reason: str,
        ...path-skip kv fields
      }
    """
    if force:
        return {
            "skip": False,
            "allowed": "true",
            "reason": "force",
            "matched_n": "0",
            "total_n": str(len(paths)),
            "globs": "",
            "sample": "",
        }
    raw = globs_raw if globs_raw is not None else os.environ.get("TORII_SKIP_PATH_GLOBS")
    globs = parse_globs(raw)
    decision = decide(paths, globs)
    skip = decision.get("allowed") == "false"
    return {
        "skip": skip,
        **decision,
    }


def parse_paths_from_gh_filenames(stdout: str) -> list[str]:
    """Normalize `gh api … -q .[].filename` / path-list lines."""
    out: list[str] = []
    seen: set[str] = set()
    for ln in (stdout or "").splitlines():
        p = ln.strip().lstrip("/")
        if not p or p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def path_skip_stub_summary(sample: str, globs: str) -> tuple[str, str]:
    """Summary + blocking lines for write-failure-review style stub."""
    summary = (
        f"Path-skip (F38/F39 Modal): every changed file matched skip globs "
        f"(`{globs or 'docs'}`) — no OpenRouter spend. Sample: {sample or 'n/a'}. "
        "Re-run with force or clear TORII_SKIP_PATH_GLOBS to review."
    )
    blocking = (
        "None — intentional free skip for docs/filtered paths on Modal host."
    )
    return summary, blocking


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F39 Modal parity helpers")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("path-skip", help="Run path-skip preflight (exit 2=skip)")
    sp.add_argument("--paths-file", type=Path, default=None)
    sp.add_argument("--path", action="append", default=[])
    sp.add_argument("--globs", default=None)
    sp.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    if args.cmd == "path-skip":
        paths = load_paths(args.paths_file, list(args.path or []))
        result = path_skip_preflight(paths, globs_raw=args.globs, force=args.force)
        print(json.dumps(result, indent=2))
        return 2 if result.get("skip") else 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
