#!/usr/bin/env python3
"""F37: apply verdict-aware labels on a GitHub PR.

Completes the trust/ops signal stack (F22 reaction+status, F23 review, F37 labels)
so operators can filter boards, branch rules, and automations on Torii outcomes.

Usage:
  python3 scripts/apply-verdict-labels.py plan \\
    --verdict REQUEST_CHANGES --pipeline-ok true

  python3 scripts/apply-verdict-labels.py apply \\
    --repo owner/name --pr 3 --verdict APPROVE --pipeline-ok true

Env:
  TORII_PR_LABELS=1 (default) | 0/off to skip
  TORII_LABEL_PREFIX=torii   (labels become {prefix}:approve etc.)
  GH_TOKEN / GITHUB_TOKEN for apply
  TORII_LABELS_FIXTURE=path.json  — write planned API ops instead of calling gh

Soft-fail: apply never raises; prints JSON result on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any
from urllib.parse import quote


# Canonical label suffixes (prefix from env)
LABEL_BY_VERDICT = {
    "APPROVE": "approve",
    "REQUEST_CHANGES": "request-changes",
    "COMMENT": "comment",
    "UNKNOWN": "error",
}

# GitHub label colors (hex without #)
COLORS = {
    "approve": "0E8A16",          # green
    "request-changes": "D93F0B",  # red-orange
    "comment": "FBCA04",          # yellow
    "error": "BFDADC",            # gray-blue
}

DESCRIPTIONS = {
    "approve": "Torii verdict: APPROVE",
    "request-changes": "Torii verdict: REQUEST CHANGES",
    "comment": "Torii verdict: COMMENT",
    "error": "Torii pipeline error or unknown verdict",
}


def enabled_from_env() -> bool:
    v = (os.environ.get("TORII_PR_LABELS") or "1").strip().lower()
    return v not in ("0", "false", "off", "no")


def label_prefix() -> str:
    p = (os.environ.get("TORII_LABEL_PREFIX") or "torii").strip()
    # sanitize: allow alnum, hyphen, underscore
    p = re.sub(r"[^A-Za-z0-9_-]", "", p) or "torii"
    return p


def label_name(suffix: str, prefix: str | None = None) -> str:
    pref = prefix if prefix is not None else label_prefix()
    return f"{pref}:{suffix}"


def all_torii_labels(prefix: str | None = None) -> list[str]:
    pref = prefix if prefix is not None else label_prefix()
    return [label_name(s, pref) for s in ("approve", "request-changes", "comment", "error")]


def suffix_for_verdict(verdict: str, pipeline_ok: bool) -> str:
    """Map verdict + pipeline health → label suffix."""
    if not pipeline_ok:
        return "error"
    v = (verdict or "UNKNOWN").strip().upper().replace(" ", "_").replace("-", "_")
    # normalize REQUEST CHANGES variants already done by parse-verdict
    if v in ("REQUEST_CHANGES", "CHANGES_REQUESTED"):
        return "request-changes"
    if v in ("APPROVE", "APPROVED", "LGTM"):
        return "approve"
    if v in ("COMMENT", "COMMENTS", "NEUTRAL"):
        return "comment"
    return LABEL_BY_VERDICT.get(v, "error")


def plan_labels(
    verdict: str,
    pipeline_ok: bool,
    *,
    prefix: str | None = None,
) -> dict[str, Any]:
    pref = prefix if prefix is not None else label_prefix()
    suffix = suffix_for_verdict(verdict, pipeline_ok)
    desired = label_name(suffix, pref)
    managed = all_torii_labels(pref)
    remove = [lab for lab in managed if lab != desired]
    return {
        "enabled": True,
        "prefix": pref,
        "verdict": verdict,
        "pipeline_ok": bool(pipeline_ok),
        "suffix": suffix,
        "add": desired,
        "remove": remove,
        "managed": managed,
        "color": COLORS.get(suffix, "BFDADC"),
        "description": DESCRIPTIONS.get(suffix, "Torii verdict label"),
    }


def _gh(args: list[str], token: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GH_TOKEN": token, "GITHUB_TOKEN": token}
    return subprocess.run(
        ["gh", "api", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def ensure_label(
    repo: str,
    name: str,
    *,
    color: str,
    description: str,
    token: str,
) -> dict[str, Any]:
    """Create label if missing; ignore already_exists."""
    enc = quote(name, safe="")
    # GET first
    get = _gh(
        ["-H", "Accept: application/vnd.github+json", f"/repos/{repo}/labels/{enc}"],
        token,
    )
    if get.returncode == 0:
        return {"ok": True, "action": "exists", "name": name}
    # Create via JSON body (reliable for colons in name)
    body = json.dumps(
        {"name": name, "color": color, "description": description[:100]}
    )
    env = {**os.environ, "GH_TOKEN": token, "GITHUB_TOKEN": token}
    create = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            "-H",
            "Accept: application/vnd.github+json",
            f"/repos/{repo}/labels",
            "--input",
            "-",
        ],
        input=body,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if create.returncode == 0:
        return {"ok": True, "action": "created", "name": name}
    # Race / already exists
    if "already_exists" in (create.stderr or "") + (create.stdout or ""):
        return {"ok": True, "action": "exists", "name": name}
    return {
        "ok": False,
        "action": "create_failed",
        "name": name,
        "stderr": (create.stderr or "")[:500],
    }


def apply_labels(
    repo: str,
    pr: int,
    plan: dict[str, Any],
    *,
    token: str | None = None,
) -> dict[str, Any]:
    """Ensure desired label exists, add it, remove other managed labels."""
    fixture = (os.environ.get("TORII_LABELS_FIXTURE") or "").strip()
    result: dict[str, Any] = {
        "ok": True,
        "posted": False,
        "add": plan["add"],
        "removed": [],
        "plan": plan,
    }

    if fixture:
        from pathlib import Path

        Path(fixture).write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        result["fixture"] = fixture
        result["posted"] = True
        return result

    tok = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not tok:
        result["ok"] = False
        result["error"] = "GH_TOKEN/GITHUB_TOKEN missing"
        return result
    if not repo or not pr:
        result["ok"] = False
        result["error"] = "repo/pr required"
        return result

    # Ensure all managed labels exist (so remove/add never 404s on unknown names)
    for lab in plan["managed"]:
        suffix = lab.split(":", 1)[-1]
        ensure_label(
            repo,
            lab,
            color=COLORS.get(suffix, "BFDADC"),
            description=DESCRIPTIONS.get(suffix, "Torii verdict label"),
            token=tok,
        )

    # Remove other managed labels currently on the PR (404 = not present — fine)
    for lab in plan["remove"]:
        enc = quote(lab, safe="")
        rm = _gh(
            [
                "--method",
                "DELETE",
                "-H",
                "Accept: application/vnd.github+json",
                f"/repos/{repo}/issues/{pr}/labels/{enc}",
            ],
            tok,
        )
        if rm.returncode == 0:
            result["removed"].append(lab)

    # Add desired label via JSON body (reliable for special chars)
    body = json.dumps({"labels": [plan["add"]]})
    env = {**os.environ, "GH_TOKEN": tok, "GITHUB_TOKEN": tok}
    add = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            "-H",
            "Accept: application/vnd.github+json",
            f"/repos/{repo}/issues/{pr}/labels",
            "--input",
            "-",
        ],
        input=body,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    if add.returncode == 0:
        result["posted"] = True
    else:
        result["ok"] = False
        result["error"] = (add.stderr or add.stdout or "label add failed")[:500]
    return result


def parse_pipeline_ok(raw: str | bool | None) -> bool:
    if isinstance(raw, bool):
        return raw
    s = str(raw or "true").strip().lower()
    return s not in ("0", "false", "no", "off")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F37 verdict PR labels")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--verdict", required=True)
        sp.add_argument("--pipeline-ok", default="true")
        sp.add_argument("--prefix", default=None, help="override TORII_LABEL_PREFIX")

    sp_plan = sub.add_parser("plan", help="print planned label ops (offline)")
    add_common(sp_plan)

    sp_apply = sub.add_parser("apply", help="apply labels on a PR (soft)")
    add_common(sp_apply)
    sp_apply.add_argument("--repo", required=True)
    sp_apply.add_argument("--pr", type=int, required=True)

    args = p.parse_args(argv)

    if not enabled_from_env() and args.cmd == "apply":
        print(json.dumps({"ok": True, "skipped": "disabled", "posted": False}))
        return 0

    if args.prefix:
        os.environ["TORII_LABEL_PREFIX"] = args.prefix

    pok = parse_pipeline_ok(args.pipeline_ok)
    plan = plan_labels(args.verdict, pok, prefix=args.prefix)

    if args.cmd == "plan":
        print(json.dumps(plan, indent=2))
        return 0

    # apply
    if not enabled_from_env():
        print(json.dumps({"ok": True, "skipped": "disabled", "posted": False}))
        return 0

    result = apply_labels(args.repo, args.pr, plan)
    print(json.dumps(result, indent=2))
    # soft-fail: always exit 0 for workflow safety when called from bash with ||
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
