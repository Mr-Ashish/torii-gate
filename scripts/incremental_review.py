#!/usr/bin/env python3
"""F59: incremental PR review — scope diff to commits since last Torii Gate review.

Deterministic control-plane. Finds last reviewed head SHA from prior Torii
comment markers (`head=`), then replaces the assembled full PR diff with a
compare-patch base...head when TORII_INCREMENTAL=1.

Usage:
  python3 scripts/incremental_review.py parse-marker '<!-- torii-review pr=3 head=abc -->'
  python3 scripts/incremental_review.py plan --pr-json pr.json --comments-json c.json
  python3 scripts/incremental_review.py assemble --repo o/r --pr 3 --out-dir .torii-out

Env:
  TORII_INCREMENTAL=0 (default off) | 1 — enable incremental scoping
  TORII_INCREMENTAL_FIXTURE=path.json — hermetic plan/assemble (no network)
  TORII_INCREMENTAL_MIN_COMMITS=1 — min new commits to stay incremental
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


# <!-- torii-review pr=12 run=99 head=deadbeef -->
_MARKER_RE = re.compile(
    r"<!--\s*torii-review\s+pr=(?P<pr>\d+)"
    r"(?:\s+run=(?P<run>[^\s>]+))?"
    r"(?:\s+head=(?P<head>[0-9a-fA-F]{7,40}))?"
    r"\s*-->",
    re.I,
)


def _truthy(val: str | None, default: bool = False) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "disabled")


def enabled(raw: str | None = None) -> bool:
    try:
        from feature_toggles import is_enabled  # type: ignore

        return bool(is_enabled("incremental"))
    except Exception:
        v = raw if raw is not None else os.environ.get("TORII_INCREMENTAL")
        return _truthy(v, default=False)


def parse_marker(body: str) -> dict[str, str | None] | None:
    if not body:
        return None
    m = _MARKER_RE.search(body)
    if not m:
        # prefix-only legacy
        if "<!-- torii-review pr=" in body:
            m2 = re.search(r"<!--\s*torii-review\s+pr=(\d+)", body, re.I)
            if m2:
                return {"pr": m2.group(1), "run": None, "head": None}
        return None
    return {
        "pr": m.group("pr"),
        "run": m.group("run"),
        "head": (m.group("head") or "").lower() or None,
    }


def format_marker(pr: str | int, *, run: str | None = None, head: str | None = None) -> str:
    parts = [f"pr={pr}"]
    if run:
        parts.append(f"run={run}")
    if head:
        parts.append(f"head={head[:40]}")
    return f"<!-- torii-review {' '.join(parts)} -->"


def extract_last_head_from_comments(
    comments: list[dict[str, Any]],
    pr: str | int,
) -> dict[str, Any] | None:
    """Newest success Torii Gate review with a head= SHA."""
    pr_s = str(pr)
    best: tuple[str, dict[str, Any]] | None = None  # (created_at, info)
    for c in comments:
        body = c.get("body") or ""
        parsed = parse_marker(body)
        if not parsed or parsed.get("pr") != pr_s:
            continue
        if not parsed.get("head"):
            continue
        # skip failure stubs
        low = body.lower()
        if any(
            s in low
            for s in (
                "torii failed to produce a review",
                "missing required secret",
                "openrouter_api_key",
                "contract repair",
            )
        ):
            continue
        created = c.get("created_at") or c.get("updated_at") or ""
        info = {
            "head": parsed["head"],
            "run": parsed.get("run"),
            "comment_id": c.get("id"),
            "created_at": created,
        }
        if best is None or str(created) >= str(best[0]):
            best = (str(created), info)
    return best[1] if best else None


def short_sha(sha: str | None) -> str:
    if not sha:
        return ""
    return sha[:12]


def plan(
    *,
    pr: str | int,
    head_sha: str | None,
    comments: list[dict[str, Any]] | None = None,
    last_head: str | None = None,
    force_full: bool = False,
) -> dict[str, Any]:
    """Decide full vs incremental vs unchanged."""
    base: dict[str, Any] = {
        "enabled": enabled(),
        "mode": "full",
        "reason": "disabled",
        "pr": str(pr),
        "head_sha": head_sha or "",
        "base_sha": "",
        "last_reviewed_head": "",
    }
    if force_full or not enabled():
        base["reason"] = "force_full" if force_full else "disabled"
        return base

    prior = last_head
    if not prior and comments is not None:
        info = extract_last_head_from_comments(comments, pr)
        if info:
            prior = info.get("head")
            base["prior"] = info
    if not prior:
        base["reason"] = "no_prior_head"
        return base

    prior = prior.lower().strip()
    head = (head_sha or "").lower().strip()
    base["last_reviewed_head"] = prior
    base["base_sha"] = prior

    if not head:
        base["reason"] = "no_head_sha"
        return base
    if head == prior or head.startswith(prior) or prior.startswith(head):
        base["mode"] = "unchanged"
        base["reason"] = "head_matches_last_review"
        return base

    base["mode"] = "incremental"
    base["reason"] = "new_commits_since_last_review"
    base["head_sha"] = head
    return base


def _gh_api(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", "api", *args],
        capture_output=True,
        text=True,
    )


def fetch_comments(repo: str, pr: int | str) -> list[dict[str, Any]]:
    cp = _gh_api(
        [
            "--paginate",
            f"repos/{repo}/issues/{pr}/comments",
        ]
    )
    if cp.returncode != 0:
        return []
    try:
        data = json.loads(cp.stdout or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def fetch_compare(
    repo: str, base: str, head: str
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Return (unified_diff, files, meta)."""
    # JSON first for file list
    meta: dict[str, Any] = {}
    files: list[dict[str, Any]] = []
    cp = _gh_api([f"repos/{repo}/compare/{base}...{head}"])
    if cp.returncode == 0:
        try:
            data = json.loads(cp.stdout)
            meta = {
                "status": data.get("status"),
                "ahead_by": data.get("ahead_by"),
                "behind_by": data.get("behind_by"),
                "total_commits": data.get("total_commits"),
            }
            for f in data.get("files") or []:
                files.append(
                    {
                        "path": f.get("filename"),
                        "additions": f.get("additions"),
                        "deletions": f.get("deletions"),
                        "status": f.get("status"),
                    }
                )
        except json.JSONDecodeError:
            pass

    # raw diff
    cp2 = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/compare/{base}...{head}",
            "-H",
            "Accept: application/vnd.github.diff",
        ],
        capture_output=True,
        text=True,
    )
    diff = cp2.stdout if cp2.returncode == 0 else ""
    return diff, files, meta


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_note(plan_d: dict[str, Any]) -> str:
    mode = plan_d.get("mode") or "full"
    if mode == "full":
        return (
            "## Incremental review (F59)\n\n"
            f"_Mode: **full** ({plan_d.get('reason', 'n/a')}). "
            "Review the complete PR diff._\n"
        )
    if mode == "unchanged":
        return (
            "## Incremental review (F59)\n\n"
            f"_Mode: **unchanged** — head `{short_sha(plan_d.get('head_sha'))}` "
            "matches last Torii Gate review. Prefer a short COMMENT confirming no new diff, "
            "or re-state residual risks without re-litigating unchanged code._\n"
        )
    return (
        "## Incremental review (F59)\n\n"
        f"- **Mode:** incremental\n"
        f"- **Last reviewed head:** `{short_sha(plan_d.get('base_sha'))}`\n"
        f"- **Current head:** `{short_sha(plan_d.get('head_sha'))}`\n"
        "- Focus findings on **new commits only** (diff below is compare patch).\n"
        "- Do not re-raise issues only present outside this incremental diff "
        "unless still visible here.\n"
    )


def write_files_summary(files: list[dict[str, Any]], additions: int, deletions: int) -> str:
    lines = [
        f"Total: +{additions} / -{deletions} across {len(files)} files",
        "",
    ]
    for f in files:
        path = f.get("path") or "?"
        a = f.get("additions", "?")
        d = f.get("deletions", "?")
        lines.append(f"- `{path}` (+{a}/-{d})")
    return "\n".join(lines) + "\n"


def assemble(
    *,
    repo: str,
    pr: str | int,
    out_dir: Path,
    pr_json_path: Path | None = None,
    force_full: bool = False,
) -> dict[str, Any]:
    """Plan + optionally rewrite pr.diff / files.txt / incremental.md in out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fixture_path = (os.environ.get("TORII_INCREMENTAL_FIXTURE") or "").strip()
    fixture = load_fixture(Path(fixture_path)) if fixture_path else None

    head_sha = ""
    if pr_json_path and pr_json_path.is_file():
        prj = json.loads(pr_json_path.read_text(encoding="utf-8"))
        # commits list may have oid
        commits = prj.get("commits") or []
        if commits and isinstance(commits, list):
            last = commits[-1]
            if isinstance(last, dict):
                head_sha = (
                    last.get("oid")
                    or last.get("sha")
                    or (last.get("commit") or {}).get("oid")
                    or ""
                )
        head_sha = head_sha or (prj.get("headRefOid") or "")
    if fixture and fixture.get("head_sha"):
        head_sha = fixture["head_sha"]

    comments: list[dict[str, Any]]
    if fixture and "comments" in fixture:
        comments = fixture["comments"]
    elif enabled() and not force_full:
        comments = fetch_comments(repo, pr)
    else:
        comments = []

    if fixture and fixture.get("last_head"):
        plan_d = plan(
            pr=pr,
            head_sha=head_sha,
            last_head=fixture["last_head"],
            force_full=force_full,
        )
    else:
        plan_d = plan(
            pr=pr,
            head_sha=head_sha,
            comments=comments,
            force_full=force_full,
        )

    note = render_note(plan_d)
    (out_dir / "incremental.md").write_text(note, encoding="utf-8")
    (out_dir / "incremental.json").write_text(
        json.dumps(plan_d, indent=2) + "\n", encoding="utf-8"
    )

    if plan_d["mode"] != "incremental":
        return plan_d

    base = plan_d["base_sha"]
    head = plan_d["head_sha"]
    if fixture and "compare_diff" in fixture:
        diff = fixture["compare_diff"]
        files = fixture.get("compare_files") or []
        meta = fixture.get("compare_meta") or {}
    else:
        diff, files, meta = fetch_compare(repo, base, head)

    plan_d["compare"] = meta
    plan_d["file_count"] = len(files)
    if not diff.strip():
        # fall back to full — empty compare is useless
        plan_d["mode"] = "full"
        plan_d["reason"] = "empty_compare_patch"
        (out_dir / "incremental.json").write_text(
            json.dumps(plan_d, indent=2) + "\n", encoding="utf-8"
        )
        (out_dir / "incremental.md").write_text(render_note(plan_d), encoding="utf-8")
        return plan_d

    banner = (
        f"# F59 incremental diff: {short_sha(base)}...{short_sha(head)}\n"
        f"# full PR diff replaced for this review scope\n\n"
    )
    diff_path = out_dir / "pr.diff"
    diff_path.write_text(banner + diff, encoding="utf-8", errors="replace")

    additions = sum(int(f.get("additions") or 0) for f in files)
    deletions = sum(int(f.get("deletions") or 0) for f in files)
    files_txt = write_files_summary(files, additions, deletions)
    (out_dir / "files.txt").write_text(files_txt, encoding="utf-8")
    plan_d["additions"] = additions
    plan_d["deletions"] = deletions
    plan_d["diff_bytes"] = diff_path.stat().st_size
    (out_dir / "incremental.json").write_text(
        json.dumps(plan_d, indent=2) + "\n", encoding="utf-8"
    )
    return plan_d


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F59 incremental review control plane")
    sub = p.add_subparsers(dest="cmd", required=True)

    pm = sub.add_parser("parse-marker", help="parse a marker string")
    pm.add_argument("text")

    pf = sub.add_parser("format-marker", help="format marker HTML")
    pf.add_argument("--pr", required=True)
    pf.add_argument("--run", default=None)
    pf.add_argument("--head", default=None)

    pp = sub.add_parser("plan", help="JSON plan full|incremental|unchanged")
    pp.add_argument("--pr", required=True)
    pp.add_argument("--head-sha", default="")
    pp.add_argument("--comments-json", type=Path, default=None)
    pp.add_argument("--last-head", default=None)
    pp.add_argument("--force-full", action="store_true")

    pa = sub.add_parser("assemble", help="plan + rewrite out_dir diff when incremental")
    pa.add_argument("--repo", required=True)
    pa.add_argument("--pr", required=True)
    pa.add_argument("--out-dir", type=Path, required=True)
    pa.add_argument("--pr-json", type=Path, default=None)
    pa.add_argument("--force-full", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "parse-marker":
        print(json.dumps(parse_marker(args.text), indent=2))
        return 0
    if args.cmd == "format-marker":
        print(format_marker(args.pr, run=args.run, head=args.head))
        return 0
    if args.cmd == "plan":
        comments = None
        if args.comments_json:
            comments = json.loads(args.comments_json.read_text(encoding="utf-8"))
        d = plan(
            pr=args.pr,
            head_sha=args.head_sha,
            comments=comments,
            last_head=args.last_head,
            force_full=args.force_full,
        )
        print(json.dumps(d, indent=2))
        return 0
    if args.cmd == "assemble":
        d = assemble(
            repo=args.repo,
            pr=args.pr,
            out_dir=args.out_dir,
            pr_json_path=args.pr_json,
            force_full=args.force_full,
        )
        print(json.dumps(d, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
