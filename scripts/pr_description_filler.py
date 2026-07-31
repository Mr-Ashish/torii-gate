#!/usr/bin/env python3
"""F58: deterministic PR description filler / scaffold.

No LLM. Builds a structured description from pr.json + file stats (and optional
linked-issue refs). Safe default: only fill when body is empty/placeholder, or
refresh content between <!-- torii-description --> markers.

Usage:
  python3 scripts/pr_description_filler.py scaffold --pr-json pr.json
  python3 scripts/pr_description_filler.py scaffold --pr-json pr.json --out desc.md
  python3 scripts/pr_description_filler.py plan --pr-json pr.json
  python3 scripts/pr_description_filler.py apply --repo o/r --pr 3 --pr-json pr.json

Env:
  TORII_PR_DESCRIPTION=1 (default) | 0/off — enable scaffold/apply helpers
  TORII_PR_DESCRIPTION_APPLY=0 (default) | 1 — allow gh pr edit on apply
  TORII_PR_DESCRIPTION_MODE=fill-empty|markers|force  (default fill-empty)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


MARKER_START = "<!-- torii-description -->"
MARKER_END = "<!-- /torii-description -->"

_PLACEHOLDER_BODIES = frozenset(
    {
        "",
        "_no description_",
        "no description",
        "tbd",
        "wip",
        "...",
        ".",
        "n/a",
        "na",
        "todo",
        "coming soon",
    }
)

_DOC_EXT = frozenset({".md", ".rst", ".txt", ".adoc"})
_TEST_HINTS = ("/test", "/tests", "test_", "_test.", "spec.", ".spec.")
_BUG_TITLE = re.compile(
    r"\b(fix|bug|hotfix|regression|crash|npe|null|error)\b", re.I
)
_DOCS_TITLE = re.compile(r"\b(docs?|readme|changelog|typo|comment)\b", re.I)
_TEST_TITLE = re.compile(r"\b(tests?|coverage|spec)\b", re.I)


def _truthy(val: str | None, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "disabled")


def enabled(raw: str | None = None) -> bool:
    try:
        from feature_toggles import is_enabled  # type: ignore

        return bool(is_enabled("pr_description"))
    except Exception:
        v = raw if raw is not None else os.environ.get("TORII_PR_DESCRIPTION")
        return _truthy(v, default=True)


def apply_enabled(raw: str | None = None) -> bool:
    try:
        from feature_toggles import is_enabled  # type: ignore

        return bool(is_enabled("pr_description_apply"))
    except Exception:
        v = raw if raw is not None else os.environ.get("TORII_PR_DESCRIPTION_APPLY")
        return _truthy(v, default=False)


def mode_from_env() -> str:
    try:
        from feature_toggles import get_value  # type: ignore

        v = str(get_value("pr_description_mode") or "fill-empty").strip().lower()
        if v in ("fill-empty", "markers", "force"):
            return v
    except Exception:
        pass
    v = (os.environ.get("TORII_PR_DESCRIPTION_MODE") or "fill-empty").strip().lower()
    if v in ("fill-empty", "markers", "force"):
        return v
    return "fill-empty"


def _file_entries(pr: dict[str, Any]) -> list[dict[str, Any]]:
    files = pr.get("files") or []
    out: list[dict[str, Any]] = []
    if not isinstance(files, list):
        return out
    for f in files:
        if isinstance(f, str):
            out.append({"path": f, "additions": None, "deletions": None})
            continue
        if not isinstance(f, dict):
            continue
        path = f.get("path") or f.get("filename") or f.get("name") or ""
        if not path:
            continue
        out.append(
            {
                "path": str(path),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
            }
        )
    return out


def classify_type(title: str, files: list[dict[str, Any]]) -> str:
    paths = [f["path"] for f in files]
    if not paths and _DOCS_TITLE.search(title or ""):
        return "Documentation"
    if paths and all(
        Path(p).suffix.lower() in _DOC_EXT or p.lower().endswith("changelog")
        for p in paths
    ):
        return "Documentation"
    if _BUG_TITLE.search(title or ""):
        return "Bug fix"
    if _TEST_TITLE.search(title or "") and paths and all(
        any(h in p.replace("\\", "/").lower() for h in _TEST_HINTS) for p in paths
    ):
        return "Tests"
    if paths and all(
        any(h in p.replace("\\", "/").lower() for h in _TEST_HINTS) for p in paths
    ):
        return "Tests"
    return "Enhancement"


def _is_test_path(path: str) -> bool:
    p = path.replace("\\", "/").lower()
    return any(h in p for h in _TEST_HINTS)


def _is_doc_path(path: str) -> bool:
    return Path(path).suffix.lower() in _DOC_EXT


def extract_issue_refs(title: str, body: str) -> list[str]:
    text = f"{title or ''}\n{body or ''}"
    refs: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(
        r"(?i)\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+#(\d+)\b", text
    ):
        key = f"#{m.group(1)}"
        if key not in seen:
            seen.add(key)
            refs.append(key)
    for m in re.finditer(r"(?<![\w/])#(\d{1,6})\b", text):
        key = f"#{m.group(1)}"
        if key not in seen:
            seen.add(key)
            refs.append(key)
    return refs[:8]


def is_placeholder_body(body: str | None) -> bool:
    b = (body or "").strip()
    if b.lower() in _PLACEHOLDER_BODIES:
        return True
    # only markers / whitespace
    stripped = re.sub(
        r"<!--\s*torii-description\s*-->.*?<!--\s*/torii-description\s*-->",
        "",
        b,
        flags=re.I | re.S,
    ).strip()
    if stripped.lower() in _PLACEHOLDER_BODIES:
        return True
    return len(b) < 8


def has_markers(body: str | None) -> bool:
    b = body or ""
    return MARKER_START in b and MARKER_END in b


def build_scaffold(
    pr: dict[str, Any],
    *,
    include_mermaid_path: Path | None = None,
    architecture_md: str | None = None,
) -> dict[str, Any]:
    title = (pr.get("title") or "").strip()
    body = pr.get("body") or ""
    files = _file_entries(pr)
    additions = pr.get("additions")
    deletions = pr.get("deletions")
    if additions is None:
        additions = sum(int(f["additions"] or 0) for f in files)
    if deletions is None:
        deletions = sum(int(f["deletions"] or 0) for f in files)
    pr_type = classify_type(title, files)
    refs = extract_issue_refs(title, body)

    n_files = len(files)
    n_tests = sum(1 for f in files if _is_test_path(f["path"]))
    n_docs = sum(1 for f in files if _is_doc_path(f["path"]))
    n_prod = n_files - n_tests - n_docs

    summary_bits = [
        f"**Type:** {pr_type}",
        f"**Scope:** {n_files} file(s), +{additions}/−{deletions}",
    ]
    if n_prod:
        summary_bits.append(f"{n_prod} production path(s)")
    if n_tests:
        summary_bits.append(f"{n_tests} test path(s)")
    if n_docs:
        summary_bits.append(f"{n_docs} doc path(s)")

    lines: list[str] = [
        MARKER_START,
        "<!-- Generated by Torii F58 pr_description_filler (deterministic; edit freely) -->",
        "",
        "## Summary",
        "",
        title or "_No title_",
        "",
        " · ".join(summary_bits),
        "",
        "## Changes",
        "",
    ]
    if not files:
        lines.append("- _(no file list in pr metadata)_")
    else:
        for f in files[:60]:
            a, d = f.get("additions"), f.get("deletions")
            stats = ""
            if a is not None or d is not None:
                stats = f" (+{a if a is not None else '?'}/−{d if d is not None else '?'})"
            lines.append(f"- `{f['path']}`{stats}")
        if len(files) > 60:
            lines.append(f"- … +{len(files) - 60} more files")
    lines.append("")

    # Test plan — checklist by file shape (not LLM)
    lines.extend(["## Test plan", ""])
    checks: list[str] = []
    if n_prod and not n_tests:
        checks.append("[ ] Add or update tests for production paths touched above")
    if n_tests:
        checks.append("[ ] Run the added/updated tests locally or in CI")
    if n_docs and not n_prod:
        checks.append("[ ] Proofread docs / links render correctly")
    if any(f["path"].endswith((".yml", ".yaml")) for f in files):
        checks.append("[ ] Validate workflow/config YAML")
    if any("migration" in f["path"].lower() for f in files):
        checks.append("[ ] Verify migration upgrade + rollback path")
    if any(
        x in f["path"].lower()
        for f in files
        for x in ("security", "auth", "permission", "acl", "csrf")
    ):
        checks.append("[ ] Security-sensitive paths: negative authz case covered")
    checks.append("[ ] Diff matches intended behavior (no drive-by refactors left unexplained)")
    if not checks:
        checks.append("[ ] Smoke-check the happy path described in the summary")
    for c in checks:
        lines.append(f"- {c}")
    lines.append("")

    if refs:
        lines.extend(["## Linked issues", ""])
        for r in refs:
            lines.append(f"- {r}")
        lines.append("")

    # Optional embed mermaid from architecture.md (F57) — already trusted code output
    arch = architecture_md
    if arch is None and include_mermaid_path and include_mermaid_path.is_file():
        arch = include_mermaid_path.read_text(encoding="utf-8", errors="replace")
    if arch and "```mermaid" in arch:
        # extract mermaid fence only to keep description lean
        m = re.search(r"```mermaid\n.*?```", arch, re.S)
        if m:
            lines.extend(
                [
                    "## Architecture",
                    "",
                    "_Auto diagram from changed paths (F57); edges are adjacency, not deps._",
                    "",
                    m.group(0),
                    "",
                ]
            )

    lines.extend(
        [
            "---",
            "_Scaffold only — replace bullets with intent/risk notes before merge._",
            MARKER_END,
            "",
        ]
    )
    body_md = "\n".join(lines)
    return {
        "type": pr_type,
        "title": title,
        "files": n_files,
        "additions": additions,
        "deletions": deletions,
        "issue_refs": refs,
        "body": body_md,
        "test_checks": len(checks),
    }


def merge_body(existing: str | None, scaffold_body: str, mode: str) -> tuple[str, str]:
    """Return (new_body, action) where action is skip|fill|markers|force."""
    existing = existing or ""
    if mode == "force":
        return scaffold_body, "force"
    if mode == "markers" or has_markers(existing):
        if has_markers(existing):
            pat = re.compile(
                re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
                re.S,
            )
            if pat.search(existing):
                new = pat.sub(scaffold_body.strip(), existing, count=1)
                return new, "markers"
            return existing.rstrip() + "\n\n" + scaffold_body, "markers-append"
        # markers mode but no markers yet — append block, keep author prose
        if existing.strip():
            return existing.rstrip() + "\n\n" + scaffold_body, "markers-append"
        return scaffold_body, "fill"
    # fill-empty
    if is_placeholder_body(existing):
        return scaffold_body, "fill"
    return existing, "skip"


def gh_edit_body(repo: str, pr: int, body: str) -> None:
    subprocess.run(
        ["gh", "pr", "edit", str(pr), "--repo", repo, "--body", body],
        check=True,
        capture_output=True,
        text=True,
    )


def plan_action(pr: dict[str, Any], mode: str | None = None) -> dict[str, Any]:
    mode = mode or mode_from_env()
    sc = build_scaffold(pr)
    new_body, action = merge_body(pr.get("body"), sc["body"], mode)
    return {
        "enabled": enabled(),
        "apply_enabled": apply_enabled(),
        "mode": mode,
        "action": action,
        "type": sc["type"],
        "files": sc["files"],
        "issue_refs": sc["issue_refs"],
        "would_change": action != "skip",
        "body_chars": len(new_body),
        "body": new_body if action != "skip" else None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F58 PR description filler (deterministic)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--pr-json", type=Path, required=True)
        sp.add_argument(
            "--architecture",
            type=Path,
            default=None,
            help="optional architecture.md (F57) to embed mermaid",
        )
        sp.add_argument(
            "--mode",
            choices=["fill-empty", "markers", "force"],
            default=None,
        )

    ps = sub.add_parser("scaffold", help="print or write scaffold body")
    add_common(ps)
    ps.add_argument("--out", type=Path, default=None)
    ps.add_argument("--json", action="store_true")

    pp = sub.add_parser("plan", help="JSON plan: action skip|fill|markers|force")
    add_common(pp)

    pa = sub.add_parser("apply", help="merge + optionally gh pr edit")
    add_common(pa)
    pa.add_argument("--repo", required=True)
    pa.add_argument("--pr", type=int, required=True)
    pa.add_argument(
        "--dry-run",
        action="store_true",
        help="print plan only (no network)",
    )
    pa.add_argument(
        "--force-apply",
        action="store_true",
        help="ignore TORII_PR_DESCRIPTION_APPLY=0",
    )
    pa.add_argument("--out", type=Path, default=None, help="also write body to file")

    args = p.parse_args(argv)
    pr = json.loads(args.pr_json.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(pr, dict):
        print("error: pr-json must be object", file=sys.stderr)
        return 2

    arch_path = args.architecture
    arch_md = None
    if arch_path and arch_path.is_file():
        arch_md = arch_path.read_text(encoding="utf-8", errors="replace")

    if args.cmd == "scaffold":
        if not enabled():
            print(json.dumps({"enabled": False}))
            return 0
        sc = build_scaffold(pr, architecture_md=arch_md, include_mermaid_path=arch_path)
        if args.json:
            print(json.dumps(sc, indent=2))
        else:
            text = sc["body"]
            if args.out:
                args.out.write_text(text, encoding="utf-8")
                print(str(args.out))
            else:
                sys.stdout.write(text)
        return 0

    if args.cmd == "plan":
        # rebuild with arch
        mode = args.mode or mode_from_env()
        sc = build_scaffold(pr, architecture_md=arch_md, include_mermaid_path=arch_path)
        new_body, action = merge_body(pr.get("body"), sc["body"], mode)
        plan = {
            "enabled": enabled(),
            "apply_enabled": apply_enabled(),
            "mode": mode,
            "action": action,
            "type": sc["type"],
            "files": sc["files"],
            "issue_refs": sc["issue_refs"],
            "would_change": action != "skip",
            "body_chars": len(new_body),
        }
        print(json.dumps(plan, indent=2))
        return 0

    if args.cmd == "apply":
        if not enabled():
            print(json.dumps({"enabled": False, "action": "skip"}))
            return 0
        mode = args.mode or mode_from_env()
        sc = build_scaffold(pr, architecture_md=arch_md, include_mermaid_path=arch_path)
        new_body, action = merge_body(pr.get("body"), sc["body"], mode)
        result: dict[str, Any] = {
            "enabled": True,
            "mode": mode,
            "action": action,
            "type": sc["type"],
            "files": sc["files"],
            "posted": False,
        }
        if args.out:
            args.out.write_text(new_body if action != "skip" else (pr.get("body") or ""), encoding="utf-8")
            result["out"] = str(args.out)
        if action == "skip":
            print(json.dumps(result))
            return 0
        if args.dry_run or not (args.force_apply or apply_enabled()):
            result["posted"] = False
            result["reason"] = (
                "dry-run"
                if args.dry_run
                else "TORII_PR_DESCRIPTION_APPLY not enabled (use --force-apply)"
            )
            result["body_chars"] = len(new_body)
            print(json.dumps(result))
            return 0
        try:
            gh_edit_body(args.repo, args.pr, new_body)
            result["posted"] = True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            result["posted"] = False
            result["error"] = str(e)
            print(json.dumps(result))
            return 1
        print(json.dumps(result))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
