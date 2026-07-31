#!/usr/bin/env python3
"""F60: reply on existing Torii inline review threads.

When re-reviewing a PR, findings that land on the same path (+ optional line)
as a prior Torii inline comment are posted as **thread replies**
(`in_reply_to`) instead of new top-level review comments. Deterministic
control-plane — no LLM judgment.

Usage:
  python3 scripts/reply_on_thread.py plan \\
    --planned planned.json --existing existing-comments.json

  python3 scripts/reply_on_thread.py post \\
    --planned planned.json --repo o/r --pr 3 \\
    [--existing existing.json | fetch via gh]

Env:
  TORII_REPLY_ON_THREAD=1 (default on) | 0/off to skip
  TORII_REPLY_MATCH=path_line (default) | path  — match strictness
  TORII_REPLY_MAX=6
  TORII_REPLY_FIXTURE=path.json — write reply payload(s) offline (tests)
  GH_TOKEN for live post / fetch
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

try:
    from feature_toggles import is_enabled as _toggle_enabled  # type: ignore
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from feature_toggles import is_enabled as _toggle_enabled  # type: ignore
    except ImportError:
        _toggle_enabled = None  # type: ignore


_TORII_INLINE_MARKERS = (
    "<!-- torii-inline -->",
    "<!-- torii-inline-review",
    "torii inline findings",
    "🏴‍☠️ torii inline",
)

# GitHub review comment body often has path in metadata; we also keep path/line fields
_PATH_LINE_IN_BODY = re.compile(
    r"`(?P<path>[^`\n]+?)(?::(?P<line>\d{1,7}))?`",
)


def _truthy(val: str | None, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "disabled", "n")


def enabled(raw: str | None = None) -> bool:
    if _toggle_enabled is not None:
        try:
            return bool(_toggle_enabled("reply_on_thread"))
        except Exception:
            pass
    v = raw if raw is not None else os.environ.get("TORII_REPLY_ON_THREAD")
    return _truthy(v, default=True)


def match_mode() -> str:
    m = (os.environ.get("TORII_REPLY_MATCH") or "path_line").strip().lower()
    return m if m in ("path_line", "path") else "path_line"


def max_replies() -> int:
    try:
        return max(1, min(20, int(os.environ.get("TORII_REPLY_MAX") or "6")))
    except ValueError:
        return 6


def is_torii_inline_body(body: str) -> bool:
    if not body:
        return False
    low = body.lower()
    return any(m in low for m in _TORII_INLINE_MARKERS)


def normalize_path(raw: str) -> str:
    s = (raw or "").strip().strip("`").strip()
    if s.startswith(("a/", "b/")):
        s = s[2:]
    # drop line suffix if present
    if re.search(r":\d+$", s):
        s = re.sub(r":\d+$", "", s)
    return s


def is_torii_thread(comment: dict[str, Any]) -> bool:
    """True if this PR review comment is a Torii-owned root or reply."""
    if comment.get("in_reply_to_id") or comment.get("in_reply_to"):
        # still count replies for lineage, but match roots only for targets
        pass
    body = str(comment.get("body") or "")
    if is_torii_inline_body(body):
        return True
    user = comment.get("user") or {}
    login = str(user.get("login") or comment.get("user_login") or "").lower()
    if "torii" in login or login.endswith("[bot]"):
        # only if body looks like ours
        if "torii" in body.lower() or "severity" in body.lower():
            return True
    return is_torii_inline_body(body)


def is_root_thread(comment: dict[str, Any]) -> bool:
    return not (comment.get("in_reply_to_id") or comment.get("in_reply_to"))


def extract_thread_key(comment: dict[str, Any]) -> dict[str, Any]:
    path = normalize_path(str(comment.get("path") or ""))
    line = comment.get("line") or comment.get("original_line")
    try:
        line_i = int(line) if line is not None else None
    except (TypeError, ValueError):
        line_i = None
    if not path:
        body = str(comment.get("body") or "")
        m = _PATH_LINE_IN_BODY.search(body)
        if m:
            path = normalize_path(m.group("path"))
            if m.group("line"):
                try:
                    line_i = int(m.group("line"))
                except ValueError:
                    pass
    return {
        "id": comment.get("id"),
        "path": path,
        "line": line_i,
        "body": comment.get("body") or "",
        "is_torii": is_torii_thread(comment),
        "is_root": is_root_thread(comment),
    }


def index_torii_roots(existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    for c in existing:
        key = extract_thread_key(c)
        if key["is_torii"] and key["is_root"] and key["id"] is not None and key["path"]:
            roots.append(key)
    return roots


def match_planned_to_root(
    planned: dict[str, Any],
    roots: list[dict[str, Any]],
    *,
    mode: str | None = None,
) -> dict[str, Any] | None:
    """Return best matching root thread for a planned inline comment."""
    mode = mode or match_mode()
    p_path = normalize_path(str(planned.get("path") or ""))
    if not p_path:
        return None
    try:
        p_line = int(planned["line"]) if planned.get("line") is not None else None
    except (TypeError, ValueError):
        p_line = None

    candidates = [r for r in roots if r["path"] == p_path]
    if not candidates:
        # basename fallback
        base = p_path.split("/")[-1]
        candidates = [r for r in roots if r["path"].split("/")[-1] == base]
    if not candidates:
        return None

    if mode == "path_line" and p_line is not None:
        exact = [r for r in candidates if r.get("line") == p_line]
        if exact:
            return exact[0]
        # nearest line within 5
        near = sorted(
            (r for r in candidates if r.get("line") is not None),
            key=lambda r: abs(int(r["line"]) - p_line),
        )
        if near and abs(int(near[0]["line"]) - p_line) <= 5:
            return near[0]
        return None  # path_line strict: no match if line far

    # path mode: single candidate or newest
    return candidates[-1]


def format_reply_body(planned: dict[str, Any], *, run: str | None = None) -> str:
    sev = str(planned.get("severity") or "").upper()
    kind = planned.get("kind") or "finding"
    body = planned.get("body") or ""
    # Prefer planned body (already formatted) with reply header
    header = "## 🏴‍☠️ Torii follow-up"
    if sev:
        header += f" ({sev})"
    if kind == "suggestion":
        header += " · suggestion"
    run_bit = f" run={run}" if run else ""
    marker = f"\n\n<!-- torii-inline-reply{run_bit} -->"
    # Avoid double markers bloating
    core = body
    if "<!-- torii-inline -->" in core:
        core = core.replace("<!-- torii-inline -->", "").rstrip()
    return f"{header}\n\n{core}{marker}"[:65000]


def plan_replies(
    planned: list[dict[str, Any]],
    existing: list[dict[str, Any]],
    *,
    max_n: int | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Split planned inlines into thread replies vs new top-level comments."""
    if not enabled():
        return {
            "ok": True,
            "enabled": False,
            "replies": [],
            "new_inlines": list(planned),
            "matched": 0,
            "reason": "disabled",
        }

    roots = index_torii_roots(existing)
    max_n = max_n if max_n is not None else max_replies()
    replies: list[dict[str, Any]] = []
    new_inlines: list[dict[str, Any]] = []
    used_root_ids: set[Any] = set()

    for p in planned:
        root = match_planned_to_root(p, roots, mode=mode)
        if root and root["id"] not in used_root_ids and len(replies) < max_n:
            used_root_ids.add(root["id"])
            replies.append(
                {
                    "in_reply_to": root["id"],
                    "path": root["path"],
                    "line": root.get("line"),
                    "planned_path": p.get("path"),
                    "planned_line": p.get("line"),
                    "body": format_reply_body(p),
                    "severity": p.get("severity"),
                    "kind": p.get("kind"),
                }
            )
        else:
            new_inlines.append(p)

    return {
        "ok": True,
        "enabled": True,
        "replies": replies,
        "new_inlines": new_inlines,
        "matched": len(replies),
        "roots_indexed": len(roots),
        "mode": mode or match_mode(),
    }


def fetch_review_comments(repo: str, pr: int) -> list[dict[str, Any]]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    proc = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"/repos/{repo}/pulls/{pr}/comments",
            "-H",
            "Accept: application/vnd.github+json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GH_TOKEN": token, "GITHUB_TOKEN": token} if token else os.environ,
    )
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def post_reply(
    repo: str,
    pr: int,
    in_reply_to: int,
    body: str,
) -> dict[str, Any]:
    """POST a pull request review comment as a reply."""
    payload = {
        "body": body,
        "in_reply_to": int(in_reply_to),
    }
    fixture = (os.environ.get("TORII_REPLY_FIXTURE") or "").strip()
    if fixture:
        path = Path(fixture)
        existing: list[Any] = []
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = [existing]
            except json.JSONDecodeError:
                existing = []
        existing.append(payload)
        path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "fixture": fixture, "in_reply_to": in_reply_to}

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        return {"ok": False, "error": "GH_TOKEN/GITHUB_TOKEN missing"}

    # GitHub: POST /repos/{owner}/{repo}/pulls/{pull_number}/comments
    # with in_reply_to — path/commit/line not required for replies
    proc = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            "-H",
            "Accept: application/vnd.github+json",
            f"/repos/{repo}/pulls/{pr}/comments",
            "--input",
            "-",
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GH_TOKEN": token, "GITHUB_TOKEN": token},
    )
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": (proc.stderr or proc.stdout or "gh api failed")[-800:],
            "in_reply_to": in_reply_to,
        }
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        data = {}
    return {
        "ok": True,
        "id": data.get("id"),
        "html_url": data.get("html_url"),
        "in_reply_to": in_reply_to,
    }


def post_replies(
    repo: str,
    pr: int,
    replies: list[dict[str, Any]],
) -> dict[str, Any]:
    results = []
    ok_n = 0
    for r in replies:
        res = post_reply(repo, pr, int(r["in_reply_to"]), str(r["body"]))
        results.append(res)
        if res.get("ok"):
            ok_n += 1
    return {
        "ok": ok_n == len(replies) or (ok_n > 0 and ok_n == len([x for x in results if x.get("ok")])),
        "posted": ok_n,
        "attempted": len(replies),
        "results": results,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Split planned inlines into replies vs new")
    p_plan.add_argument("--planned", type=Path, required=True, help="JSON list of planned inlines")
    p_plan.add_argument("--existing", type=Path, required=True, help="JSON list of PR review comments")
    p_plan.add_argument("--max", type=int, default=None)
    p_plan.add_argument("--mode", choices=("path_line", "path"), default=None)

    p_post = sub.add_parser("post", help="Plan + post replies (new inlines left to F9)")
    p_post.add_argument("--planned", type=Path, required=True)
    p_post.add_argument("--existing", type=Path, default=None, help="Fixture; else fetch via gh")
    p_post.add_argument("--repo", required=True)
    p_post.add_argument("--pr", type=int, required=True)
    p_post.add_argument("--max", type=int, default=None)
    p_post.add_argument("--mode", choices=("path_line", "path"), default=None)
    p_post.add_argument("--force", action="store_true", help="Ignore disabled toggle")

    p_match = sub.add_parser("match-one", help="Debug single match (JSON stdin planned+roots)")
    p_match.add_argument("--mode", default=None)

    args = ap.parse_args(argv)

    if args.cmd == "plan":
        planned = _load_json(args.planned)
        existing = _load_json(args.existing)
        if not isinstance(planned, list):
            planned = planned.get("comments") or planned.get("planned") or []
        out = plan_replies(planned, existing, max_n=args.max, mode=args.mode)
        print(json.dumps(out, indent=2))
        return 0

    if args.cmd == "post":
        if not args.force and not enabled():
            print(json.dumps({"ok": True, "posted": 0, "reason": "disabled"}))
            return 0
        planned = _load_json(args.planned)
        if not isinstance(planned, list):
            planned = planned.get("comments") or planned.get("planned") or []
        if args.existing:
            existing = _load_json(args.existing)
        else:
            existing = fetch_review_comments(args.repo, args.pr)
        plan = plan_replies(planned, existing, max_n=args.max, mode=args.mode)
        post_res = post_replies(args.repo, args.pr, plan["replies"])
        out = {
            **plan,
            "post": post_res,
            "posted": post_res.get("posted", 0),
        }
        print(json.dumps(out, indent=2))
        return 0 if post_res.get("posted", 0) == len(plan["replies"]) or not plan["replies"] else 0

    if args.cmd == "match-one":
        data = json.load(sys.stdin)
        root = match_planned_to_root(data["planned"], data["roots"], mode=args.mode)
        print(json.dumps(root, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
