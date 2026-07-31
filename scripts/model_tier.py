#!/usr/bin/env python3
"""F42: auto model tier by PR size (Hermes-inspired cost control).

Tiny / docs-only PRs do not need Claude Opus — use a cheap OpenRouter model
first. Operators opt in with TORII_MODEL_TIER=auto (default off keeps F26
single-model behaviour).

Usage:
  python3 scripts/model_tier.py select
  python3 scripts/model_tier.py select --diff-bytes 800 --file-count 2
  python3 scripts/model_tier.py select --path README.md --path docs/x.md
  python3 scripts/model_tier.py select --pr-json pr.json --meta meta.env

Env:
  TORII_MODEL_TIER          off|auto|cheap|full  (default off)
  TORII_MODEL               when tier=off: single model; when auto: full model
  TORII_MODEL_FULL          full-tier model (default anthropic/claude-opus-5)
  TORII_MODEL_CHEAP         cheap-tier model (default openai/gpt-4.1-mini)
  TORII_TIER_MAX_BYTES      tiny-diff threshold (default 12000)
  TORII_TIER_MAX_FILES      tiny file-count threshold (default 3)
  OPENROUTER_MODEL          fallback when TORII_MODEL unset (tier=off)

Stdout key=value:
  model=...
  tier=cheap|full|explicit|default
  reason=...
  mode=off|auto|cheap|full
  full_model=...
  cheap_model=...
  diff_bytes=N
  file_count=N
  docs_only=true|false
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

# Match F26 SoT in run-hermes-review.sh
DEFAULT_FULL_MODEL = "anthropic/claude-opus-5"
# Match trigger-review.sh --cheap
DEFAULT_CHEAP_MODEL = "openai/gpt-4.1-mini"
DEFAULT_MAX_BYTES = 12_000
DEFAULT_MAX_FILES = 3

# Docs-adjacent paths safe for cheap model (aligned with F38 DOCS_PRESET).
DOCS_GLOBS: list[str] = [
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


def normalize_path(p: str) -> str:
    s = (p or "").strip().lstrip("/")
    if s.startswith("./"):
        s = s[2:]
    return s


def path_matches_docs(path: str) -> bool:
    path = normalize_path(path)
    if not path:
        return False
    base = path.rsplit("/", 1)[-1]
    for g in DOCS_GLOBS:
        g = g.strip().lstrip("/")
        if not g:
            continue
        if fnmatch(path, g) or fnmatch(base, g):
            return True
        if g.endswith("/**"):
            prefix = g[:-3]
            if path == prefix or path.startswith(prefix + "/"):
                return True
    return False


def is_docs_only(paths: list[str]) -> bool:
    if not paths:
        return False
    return all(path_matches_docs(p) for p in paths)


def parse_mode(raw: str | None) -> str:
    if raw is None:
        return "off"
    s = str(raw).strip().lower()
    if not s or s in ("0", "off", "false", "no", "none", "disabled"):
        return "off"
    if s in ("1", "on", "true", "yes", "auto", "tier", "size"):
        return "auto"
    if s in ("cheap", "mini", "small", "fast"):
        return "cheap"
    if s in ("full", "opus", "quality", "large"):
        return "full"
    # unknown → off (safe)
    return "off"


def _positive_int(raw: str | None, default: int) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        n = int(str(raw).strip(), 10)
    except ValueError:
        return default
    return max(0, n)


def resolve_models(
    *,
    torii_model: str | None,
    openrouter_model: str | None,
    full_env: str | None,
    cheap_env: str | None,
) -> tuple[str, str]:
    """Return (full_model, cheap_model)."""
    cheap = (cheap_env or "").strip() or DEFAULT_CHEAP_MODEL
    full = (full_env or "").strip()
    if not full:
        full = (torii_model or "").strip() or (openrouter_model or "").strip() or DEFAULT_FULL_MODEL
    return full, cheap


def select_model(
    *,
    mode: str = "off",
    torii_model: str | None = None,
    openrouter_model: str | None = None,
    full_model: str | None = None,
    cheap_model: str | None = None,
    diff_bytes: int = 0,
    file_count: int = 0,
    paths: list[str] | None = None,
    diff_truncated: bool = False,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
) -> dict[str, Any]:
    """Pick model + reason for the given PR size signals."""
    mode = parse_mode(mode)
    full, cheap = resolve_models(
        torii_model=torii_model,
        openrouter_model=openrouter_model,
        full_env=full_model,
        cheap_env=cheap_model,
    )
    paths = [normalize_path(p) for p in (paths or []) if normalize_path(p)]
    docs = is_docs_only(paths) if paths else False
    try:
        diff_bytes = max(0, int(diff_bytes))
    except (TypeError, ValueError):
        diff_bytes = 0
    try:
        file_count = max(0, int(file_count))
    except (TypeError, ValueError):
        file_count = 0
    if file_count == 0 and paths:
        file_count = len(paths)

    base: dict[str, Any] = {
        "mode": mode,
        "full_model": full,
        "cheap_model": cheap,
        "diff_bytes": diff_bytes,
        "file_count": file_count,
        "docs_only": docs,
        "diff_truncated": bool(diff_truncated),
        "max_bytes": max_bytes,
        "max_files": max_files,
    }

    if mode == "off":
        # Classic F26: single explicit/default model
        explicit = (torii_model or "").strip() or (openrouter_model or "").strip()
        if explicit:
            return {
                **base,
                "model": explicit,
                "tier": "explicit",
                "reason": "explicit_model",
            }
        return {
            **base,
            "model": DEFAULT_FULL_MODEL,
            "tier": "default",
            "reason": "default_full",
        }

    if mode == "cheap":
        return {**base, "model": cheap, "tier": "cheap", "reason": "forced_cheap"}

    if mode == "full":
        return {**base, "model": full, "tier": "full", "reason": "forced_full"}

    # mode == auto
    if diff_truncated:
        return {
            **base,
            "model": full,
            "tier": "full",
            "reason": "diff_truncated",
        }
    if docs:
        return {
            **base,
            "model": cheap,
            "tier": "cheap",
            "reason": "docs_only",
        }
    tiny = file_count > 0 and file_count <= max_files and diff_bytes <= max_bytes
    # If we lack file signals but bytes are tiny, still prefer cheap
    if not paths and file_count == 0 and 0 < diff_bytes <= max_bytes:
        tiny = True
    if tiny:
        return {
            **base,
            "model": cheap,
            "tier": "cheap",
            "reason": "tiny",
        }
    return {
        **base,
        "model": full,
        "tier": "full",
        "reason": "large",
    }


def _parse_meta_env(path: Path | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if path is None or not path.is_file():
        return out
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        # strip simple shell quotes from assemble-context shlex.quote
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        out[k] = v
    return out


def _paths_from_pr_json(path: Path | None) -> tuple[list[str], int, int, int]:
    """Return (paths, file_count, additions, deletions)."""
    if path is None or not path.is_file():
        return [], 0, 0, 0
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return [], 0, 0, 0
    if not isinstance(data, dict):
        return [], 0, 0, 0
    files = data.get("files") or []
    paths: list[str] = []
    if isinstance(files, list):
        for f in files:
            if isinstance(f, dict):
                p = f.get("path") or f.get("filename") or ""
            else:
                p = str(f)
            n = normalize_path(str(p))
            if n:
                paths.append(n)
    adds = int(data.get("additions") or 0)
    dels = int(data.get("deletions") or 0)
    return paths, len(paths), adds, dels


def _load_paths_file(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    out: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            # files.txt format from assemble: "- `path` (+a/-d)" or plain paths
            m = re.search(r"`([^`]+)`", line)
            if m:
                n = normalize_path(m.group(1))
            else:
                n = normalize_path(line)
            if n and not n.lower().startswith("total:"):
                out.append(n)
    except OSError:
        return []
    return out


def cmd_select(args: argparse.Namespace) -> int:
    meta = _parse_meta_env(Path(args.meta) if args.meta else None)
    pr_paths, pr_fc, _adds, _dels = _paths_from_pr_json(
        Path(args.pr_json) if args.pr_json else None
    )
    file_paths = _load_paths_file(Path(args.paths_file) if args.paths_file else None)
    cli_paths = [normalize_path(p) for p in (args.path or []) if normalize_path(p)]

    paths = cli_paths or file_paths or pr_paths

    diff_bytes = args.diff_bytes
    if diff_bytes is None:
        raw = meta.get("DIFF_SIZE") or os.environ.get("DIFF_SIZE") or "0"
        try:
            diff_bytes = int(raw)
        except ValueError:
            diff_bytes = 0

    file_count = args.file_count
    if file_count is None:
        raw = meta.get("FILE_COUNT") or os.environ.get("FILE_COUNT") or ""
        if raw:
            try:
                file_count = int(raw)
            except ValueError:
                file_count = len(paths)
        else:
            file_count = len(paths)

    trunc_raw = (
        args.diff_truncated
        if args.diff_truncated is not None
        else meta.get("DIFF_TRUNCATED") or os.environ.get("DIFF_TRUNCATED") or "false"
    )
    if isinstance(trunc_raw, bool):
        diff_truncated = trunc_raw
    else:
        diff_truncated = str(trunc_raw).strip().lower() in ("1", "true", "yes")

    mode = args.mode if args.mode is not None else os.environ.get("TORII_MODEL_TIER")

    result = select_model(
        mode=parse_mode(mode),
        torii_model=os.environ.get("TORII_MODEL"),
        openrouter_model=os.environ.get("OPENROUTER_MODEL"),
        full_model=os.environ.get("TORII_MODEL_FULL"),
        cheap_model=os.environ.get("TORII_MODEL_CHEAP"),
        diff_bytes=int(diff_bytes or 0),
        file_count=int(file_count or 0),
        paths=paths,
        diff_truncated=diff_truncated,
        max_bytes=_positive_int(os.environ.get("TORII_TIER_MAX_BYTES"), DEFAULT_MAX_BYTES),
        max_files=_positive_int(os.environ.get("TORII_TIER_MAX_FILES"), DEFAULT_MAX_FILES),
    )

    # Stable key=value for shell
    order = [
        "model",
        "tier",
        "reason",
        "mode",
        "full_model",
        "cheap_model",
        "diff_bytes",
        "file_count",
        "docs_only",
        "diff_truncated",
        "max_bytes",
        "max_files",
    ]
    for k in order:
        v = result.get(k)
        if isinstance(v, bool):
            v = "true" if v else "false"
        print(f"{k}={v}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F42 auto model tier by PR size")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("select", help="Print model= tier= reason= key=value lines")
    s.add_argument("--mode", default=None, help="off|auto|cheap|full (else env)")
    s.add_argument("--diff-bytes", type=int, default=None)
    s.add_argument("--file-count", type=int, default=None)
    s.add_argument("--diff-truncated", default=None, help="true|false")
    s.add_argument("--path", action="append", default=[], help="Changed path (repeatable)")
    s.add_argument("--paths-file", default=None, help="paths file or assemble files.txt")
    s.add_argument("--pr-json", default=None, help="gh pr view --json … file")
    s.add_argument("--meta", default=None, help="meta.env from assemble-context")
    s.set_defaults(func=cmd_select)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
