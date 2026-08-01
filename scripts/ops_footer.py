#!/usr/bin/env python3
"""F35: ops deep-link footer on posted PR comments (Actions run + run-bundle tip).

OpenUI phase 4b minimal: no hosted console required. Surfaces:
  - Workflow run URL (when GITHUB_* env present)
  - Optional TORII_CONSOLE_URL base (operator-hosted Run Console)
  - Always: download run-bundle.json from torii-out artifact → ui/review-console

Usage:
  python3 scripts/ops_footer.py line
  python3 scripts/ops_footer.py append --review review.md
  python3 scripts/ops_footer.py step-summary

Env:
  TORII_OPS_FOOTER=1 (default) | 0/off to skip
  GITHUB_SERVER_URL, GITHUB_REPOSITORY, GITHUB_RUN_ID
  TORII_CONSOLE_URL — optional https://… base for interactive console
  REPO / GITHUB_REPOSITORY

Soft-fail: never raises for missing env; empty line when nothing useful.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_OPS_LINE_RX = re.compile(r"^\*Ops \(F35\):.*\*\s*$", re.M)
_BRAND_RX = re.compile(
    r"^\*Torii · Hermes Agent · OpenRouter · memory-backed review[^*]*\*\s*$",
    re.M,
)
_COST_RX = re.compile(r"^\*Cost / usage:.*\*\s*$", re.M)


def enabled() -> bool:
    v = (os.environ.get("TORII_OPS_FOOTER") or "1").strip().lower()
    return v not in ("0", "false", "off", "no")


def run_url(
    *,
    server: str | None = None,
    repo: str | None = None,
    run_id: str | None = None,
) -> str | None:
    server = (server or os.environ.get("GITHUB_SERVER_URL") or "https://github.com").rstrip(
        "/"
    )
    repo = (repo or os.environ.get("GITHUB_REPOSITORY") or os.environ.get("REPO") or "").strip()
    run_id = (run_id or os.environ.get("GITHUB_RUN_ID") or "").strip()
    if not repo or not run_id or run_id in {"local", "0"}:
        return None
    # Actions path works for github.com and GHES with same shape
    return f"{server}/{repo}/actions/runs/{run_id}"


def format_ops_line(
    *,
    server: str | None = None,
    repo: str | None = None,
    run_id: str | None = None,
    console_url: str | None = None,
) -> str:
    """Italic Markdown ops line (no trailing newline). Empty if disabled/useless."""
    if not enabled():
        return ""
    bits: list[str] = []
    url = run_url(server=server, repo=repo, run_id=run_id)
    if url:
        bits.append(f"[workflow run]({url})")
    console = (
        console_url
        if console_url is not None
        else (os.environ.get("TORII_CONSOLE_URL") or "").strip()
    )
    if console:
        bits.append(f"[Run Console]({console.rstrip('/')})")
    bits.append("artifact `run-bundle.json` → `ui/review-console` Load bundle")
    return f"*Ops (F35): {' · '.join(bits)}*"


def format_gate_onboarding() -> str:
    """First-run required-check checklist for GITHUB_STEP_SUMMARY (GATE_ONBOARDING).

    Buyer JTBD: after install, the first Actions run must tell the operator how
    to make **torii/gate** the merge authority — not bury it in docs only.
    """
    lines = [
        "### Required check — make the gate merge authority",
        "",
        "After this run posts context **`torii/gate`**, require it on the default branch:",
        "",
        "1. GitHub → **Settings → Branches → Branch protection** (default branch)",
        "2. Enable **Require status checks to pass before merging**",
        "3. Add required context: **`torii/gate`** (prefer over `torii/review` alone)",
        "4. If the check name is missing from the picker, re-run this workflow once "
        "so GitHub lists it",
        "",
        "| Context | Role |",
        "|---------|------|",
        "| **`torii/gate`** | Security-aware open/closed — **use for branch protection** |",
        "| `torii/review` | Optional companion verdict signal |",
        "",
        "Then: `@torii review this pr` on real PRs → "
        "`python3 scripts/torii.py quieter -- status` (own-repo quieter chart).",
        "",
        "Docs: `docs/INSTALL.md` · `docs/GATE.md` · `docs/GOLDEN-PATH.md` · `docs/QUIETER.md`",
        "",
    ]
    return "\n".join(lines)


def format_step_summary(
    *,
    server: str | None = None,
    repo: str | None = None,
    run_id: str | None = None,
    console_url: str | None = None,
    include_gate_onboarding: bool = True,
) -> str:
    if not enabled():
        # still allow gate onboarding even if ops links disabled
        if include_gate_onboarding:
            return format_gate_onboarding()
        return ""
    lines = ["### Torii ops links (F35)", ""]
    url = run_url(server=server, repo=repo, run_id=run_id)
    if url:
        lines.append(f"- **Workflow run:** {url}")
    else:
        lines.append("- **Workflow run:** _(local / missing GITHUB_RUN_ID)_")
    console = (
        console_url
        if console_url is not None
        else (os.environ.get("TORII_CONSOLE_URL") or "").strip()
    )
    if console:
        lines.append(f"- **Run Console:** {console.rstrip('/')}")
    lines.append(
        "- **Interactive review:** download `torii-out-*` artifact → "
        "`run-bundle.json` → `cd ui/review-console && npm run dev` → **Load bundle**"
    )
    lines.append("")
    body = "\n".join(lines)
    if include_gate_onboarding:
        # Onboarding first — operators see required check before ops deep-links
        body = format_gate_onboarding() + body
    return body


def append_ops_to_review(review_path: Path, line: str | None = None) -> bool:
    """Inject/update ops line near brand/cost footer. Returns True if changed."""
    if not enabled():
        return False
    line = line if line is not None else format_ops_line()
    if not line:
        return False
    text = review_path.read_text(encoding="utf-8", errors="replace")
    if _OPS_LINE_RX.search(text):
        new = _OPS_LINE_RX.sub(line, text)
        if new == text:
            return False
        review_path.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
        return True

    # Prefer after cost line, else after brand footer, else EOF
    m_cost = _COST_RX.search(text)
    if m_cost:
        insert_at = m_cost.end()
        new = text[:insert_at] + "\n" + line + text[insert_at:]
    else:
        m_brand = _BRAND_RX.search(text)
        if m_brand:
            insert_at = m_brand.end()
            new = text[:insert_at] + "\n" + line + text[insert_at:]
        else:
            new = text.rstrip() + "\n\n" + line + "\n"
    if not new.endswith("\n"):
        new += "\n"
    review_path.write_text(new, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("line", help="Print ops footer line (or empty)")
    p_app = sub.add_parser("append", help="Inject into review.md")
    p_app.add_argument("--review", type=Path, required=True)
    p_ss = sub.add_parser("step-summary", help="Markdown for GITHUB_STEP_SUMMARY")
    p_ss.add_argument(
        "--no-gate-onboarding",
        action="store_true",
        help="Omit required-check torii/gate onboarding checklist",
    )
    sub.add_parser(
        "gate-onboarding",
        help="Required-check torii/gate onboarding checklist only (job summary)",
    )
    p_fix = sub.add_parser("fixture", help="Hermetic gate-onboarding surface check")
    p_fix.set_defaults(cmd="fixture")

    args = ap.parse_args(argv)

    if args.cmd == "line":
        line = format_ops_line()
        if line:
            sys.stdout.write(line + "\n")
        return 0

    if args.cmd == "append":
        if not args.review.is_file():
            print(f"ops-footer: missing review {args.review}", file=sys.stderr)
            return 0  # soft
        changed = append_ops_to_review(args.review)
        print(
            f"ops-footer: {'updated' if changed else 'unchanged'} {args.review}",
            file=sys.stderr,
        )
        return 0

    if args.cmd == "gate-onboarding":
        sys.stdout.write(format_gate_onboarding())
        return 0

    if args.cmd == "fixture":
        import json
        from datetime import datetime, timezone

        root = Path(__file__).resolve().parents[1]
        md = format_gate_onboarding()
        ss = format_step_summary(include_gate_onboarding=True)
        checks = {
            "has_heading": "Required check" in md and "torii/gate" in md,
            "has_branch_protection": "Branch protection" in md,
            "has_settings_path": "Settings" in md and "Branches" in md,
            "prefers_gate_over_review": "prefer over" in md.lower() or "prefer" in md,
            "links_install_or_gate_doc": "INSTALL.md" in md or "GATE.md" in md,
            "step_summary_includes_onboarding": "Required check" in ss
            and "torii/gate" in ss,
            "report_verdict_wires": False,
            "workflow_wires": False,
        }
        rv = root / "scripts" / "report-verdict.sh"
        if rv.is_file():
            rvt = rv.read_text(encoding="utf-8", errors="replace")
            checks["report_verdict_wires"] = bool(
                "gate-onboarding" in rvt or "format_gate_onboarding" in rvt
                or ("ops_footer" in rvt and "gate" in rvt and "STEP_SUMMARY" in rvt)
            )
        wf = root / ".github" / "workflows" / "torii-review-reusable.yml"
        if wf.is_file():
            wft = wf.read_text(encoding="utf-8", errors="replace")
            checks["workflow_wires"] = bool(
                "gate-onboarding" in wft
                or ("Required check" in wft and "torii/gate" in wft)
                or ("ops_footer.py" in wft and "gate-onboarding" in wft)
            )
        # also accept report-verdict calling gate-onboarding via python
        if rv.is_file() and not checks["report_verdict_wires"]:
            rvt = rv.read_text(encoding="utf-8", errors="replace")
            checks["report_verdict_wires"] = "gate-onboarding" in rvt
        fixture_pass = all(checks.values())
        print(
            json.dumps(
                {
                    "feature": "GATE_ONBOARDING",
                    "fixture_pass": fixture_pass,
                    "checks": checks,
                    "scorecard_target": "JTBD / install (dims 3 + 7)",
                    "dim_lift": "first-run Actions summary teaches require torii/gate",
                    "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                indent=2,
            )
        )
        return 0 if fixture_pass else 1

    if args.cmd == "step-summary":
        md = format_step_summary(
            include_gate_onboarding=not getattr(args, "no_gate_onboarding", False)
        )
        if md:
            sys.stdout.write(md)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
