#!/usr/bin/env python3
"""F38: skip paid OpenRouter review when every changed path matches skip globs.

Cost control for monorepos: docs/changelog-only PRs should not burn Hermes.
Default is **off** (empty globs) — operators opt in via env/repo var.

Usage:
  python3 scripts/path-skip-check.py --paths-file pr-paths.txt
  python3 scripts/path-skip-check.py --path a.md --path docs/x.md

Env:
  TORII_SKIP_PATH_GLOBS   comma list, or preset name `docs` / `off`
  TORII_SKIP_PATHS_FORCE=1  always allow (paid run)
  TORII_SKIP_PATHS_FIXTURE  unused (paths come from CLI)

Exit:
  0  allow paid run
  2  skip paid run (all paths matched)
  1  hard error (caller should fail-open → allow)

Stdout key=value:
  allowed=true|false
  reason=...
  matched_n=N
  total_n=N
  globs=...
  sample=path1,path2
"""

from __future__ import annotations

import argparse
import os
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable


# Convenience preset for docs/docs-adjacent PRs (no code).
DOCS_PRESET: list[str] = [
    "*.md",
    "*.mdx",
    "*.markdown",
    "*.rst",
    "*.txt",
    "*.adoc",
    "docs/**",
    "**/docs/**",
    "doc/**",
    "**/doc/**",
    "LICENSE*",
    "COPYING*",
    "CHANGELOG*",
    "CHANGES*",
    "HISTORY*",
    "AUTHORS*",
    "CONTRIBUTING*",
    "CODE_OF_CONDUCT*",
    "*.mdc",
]


def parse_globs(raw: str | None) -> list[str]:
    """Parse TORII_SKIP_PATH_GLOBS. Empty/off → []. Preset `docs` → DOCS_PRESET."""
    if raw is None:
        return []
    s = str(raw).strip()
    if not s or s.lower() in ("0", "off", "false", "no", "none", "disabled"):
        return []
    if s.lower() in ("docs", "docs-only", "doc", "documentation"):
        return list(DOCS_PRESET)
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts


def normalize_path(p: str) -> str:
    s = (p or "").strip().lstrip("/")
    if s.startswith("./"):
        s = s[2:]
    return s


def load_paths(paths_file: Path | None, extra: list[str]) -> list[str]:
    out: list[str] = []
    if paths_file is not None and paths_file.is_file():
        for line in paths_file.read_text(encoding="utf-8", errors="replace").splitlines():
            n = normalize_path(line)
            if n:
                out.append(n)
    for p in extra:
        n = normalize_path(p)
        if n:
            out.append(n)
    # unique preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def path_matches(path: str, globs: Iterable[str]) -> bool:
    """True if path matches any glob (fnmatch; also try basename-only patterns)."""
    for g in globs:
        g = g.strip().lstrip("/")
        if not g:
            continue
        if fnmatch(path, g):
            return True
        # basename match for patterns like *.md
        base = path.rsplit("/", 1)[-1]
        if fnmatch(base, g):
            return True
        # prefix/** style already covered by fnmatch if ** used — Python fnmatch
        # does not treat ** specially, so expand: docs/** → docs/* and docs/*/*
        if g.endswith("/**"):
            prefix = g[:-3]
            if path == prefix or path.startswith(prefix + "/"):
                return True
        if g.endswith("/**/*"):
            prefix = g[:-5]
            if path.startswith(prefix + "/"):
                return True
    return False


def decide(paths: list[str], globs: list[str]) -> dict[str, str]:
    """Return decision dict for stdout kv."""
    if not globs:
        return {
            "allowed": "true",
            "reason": "disabled",
            "matched_n": "0",
            "total_n": str(len(paths)),
            "globs": "",
            "sample": "",
        }
    if not paths:
        # No paths → do not skip (unknown set; fail-open paid)
        return {
            "allowed": "true",
            "reason": "no_paths",
            "matched_n": "0",
            "total_n": "0",
            "globs": ",".join(globs),
            "sample": "",
        }

    matched = [p for p in paths if path_matches(p, globs)]
    unmatched = [p for p in paths if p not in matched]
    if unmatched:
        return {
            "allowed": "true",
            "reason": "code_paths_present",
            "matched_n": str(len(matched)),
            "total_n": str(len(paths)),
            "globs": ",".join(globs),
            "sample": ",".join(unmatched[:5]),
        }
    # all matched → skip paid
    return {
        "allowed": "false",
        "reason": "all_paths_skipped",
        "matched_n": str(len(matched)),
        "total_n": str(len(paths)),
        "globs": ",".join(globs),
        "sample": ",".join(matched[:8]),
    }


def emit(d: dict[str, str]) -> None:
    for k, v in d.items():
        print(f"{k}={v}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F38 path-glob free skip")
    p.add_argument("--paths-file", type=Path, default=None)
    p.add_argument("--path", action="append", default=[], dest="paths")
    p.add_argument(
        "--globs",
        default=None,
        help="Override TORII_SKIP_PATH_GLOBS (comma list or 'docs')",
    )
    args = p.parse_args(argv)

    if (os.environ.get("TORII_SKIP_PATHS_FORCE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        emit(
            {
                "allowed": "true",
                "reason": "force",
                "matched_n": "0",
                "total_n": "0",
                "globs": "",
                "sample": "",
            }
        )
        return 0

    raw = args.globs if args.globs is not None else os.environ.get("TORII_SKIP_PATH_GLOBS")
    globs = parse_globs(raw)
    paths = load_paths(args.paths_file, list(args.paths or []))
    decision = decide(paths, globs)
    emit(decision)
    if decision["allowed"] == "false":
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:  # pragma: no cover
        print(f"allowed=true\nreason=error\nerror={e}", file=sys.stderr)
        print("allowed=true")
        print("reason=error")
        raise SystemExit(1)
