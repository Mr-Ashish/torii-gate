#!/usr/bin/env python3
"""F22/F23: Parse Torii Gate review Markdown for verdict signals.

Reads a normalized review body and emits key=value lines suitable for
GitHub Actions $GITHUB_OUTPUT / shell eval:

  verdict=APPROVE|REQUEST_CHANGES|COMMENT|UNKNOWN
  score=<int or empty>
  confidence=low|medium|high|empty
  reaction=+1|-1|eyes
  status_state=success|failure|error
  status_desc=<short description>
  review_event=APPROVE|REQUEST_CHANGES|COMMENT
  pipeline_ok=true|false

Mapping (when pipeline_rc is 0 / pipeline_ok=true):
  APPROVE          → reaction +1,  status success, review_event APPROVE
  REQUEST CHANGES  → reaction -1,  status failure, review_event REQUEST_CHANGES
  COMMENT          → reaction eyes, status success, review_event COMMENT
  UNKNOWN          → reaction eyes, status success, review_event COMMENT

When pipeline_ok=false (Hermes/config/crash):
  reaction -1, status error, review_event COMMENT (do not REQUEST_CHANGES on infra fail),
  verdict kept from body if present else UNKNOWN.

F23: review_event drives a formal GitHub Pull Request Review (Reviews panel),
separate from the full issue comment + commit status.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_VERDICT_RX = re.compile(
    r"^\*\*Verdict:\*\*\s*(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_SCORE_RX = re.compile(
    r"^\*\*Score:\*\*\s*(\d+)\s*(?:/100)?",
    re.MULTILINE | re.IGNORECASE,
)
_CONF_RX = re.compile(
    r"^\*\*Confidence:\*\*\s*(low|medium|high)\b",
    re.MULTILINE | re.IGNORECASE,
)

# Normalize free-form model text → canonical token
_VERDICT_ALIASES: dict[str, str] = {
    "APPROVE": "APPROVE",
    "APPROVED": "APPROVE",
    "LGTM": "APPROVE",
    "REQUEST CHANGES": "REQUEST_CHANGES",
    "REQUEST_CHANGES": "REQUEST_CHANGES",
    "REQUEST-CHANGES": "REQUEST_CHANGES",
    "CHANGES REQUESTED": "REQUEST_CHANGES",
    "COMMENT": "COMMENT",
    "COMMENTS": "COMMENT",
    "NEUTRAL": "COMMENT",
}


def normalize_verdict(raw: str) -> str:
    s = re.sub(r"\s+", " ", (raw or "").strip())
    # Strip trailing punctuation / parenthetical notes
    s = re.sub(r"\s*[\(\[].*$", "", s).strip()
    s = s.rstrip(".").strip()
    key = s.upper()
    if key in _VERDICT_ALIASES:
        return _VERDICT_ALIASES[key]
    # Prefix match (e.g. "REQUEST CHANGES — see blocking")
    for alias, canon in _VERDICT_ALIASES.items():
        if key.startswith(alias):
            return canon
    return "UNKNOWN"


def parse_review(text: str) -> dict[str, str]:
    verdict = "UNKNOWN"
    m = _VERDICT_RX.search(text or "")
    if m:
        verdict = normalize_verdict(m.group(1))

    score = ""
    sm = _SCORE_RX.search(text or "")
    if sm:
        score = sm.group(1)

    confidence = ""
    cm = _CONF_RX.search(text or "")
    if cm:
        confidence = cm.group(1).lower()

    return {"verdict": verdict, "score": score, "confidence": confidence}


def signal_for(verdict: str, *, pipeline_ok: bool) -> dict[str, str]:
    """Map verdict + pipeline health → reaction, commit-status, PR review event."""
    if not pipeline_ok:
        return {
            "reaction": "-1",
            "status_state": "error",
            "status_desc": f"Torii pipeline failed (verdict={verdict})",
            # Infra failure must not look like product REQUEST CHANGES
            "review_event": "COMMENT",
        }

    if verdict == "APPROVE":
        return {
            "reaction": "+1",
            "status_state": "success",
            "status_desc": "Torii: APPROVE",
            "review_event": "APPROVE",
        }
    if verdict == "REQUEST_CHANGES":
        return {
            "reaction": "-1",
            "status_state": "failure",
            "status_desc": "Torii: REQUEST CHANGES",
            "review_event": "REQUEST_CHANGES",
        }
    if verdict == "COMMENT":
        return {
            "reaction": "eyes",
            "status_state": "success",
            "status_desc": "Torii: COMMENT",
            "review_event": "COMMENT",
        }
    return {
        "reaction": "eyes",
        "status_state": "success",
        "status_desc": f"Torii: review complete ({verdict})",
        "review_event": "COMMENT",
    }


def step_summary_md(fields: dict[str, str]) -> str:
    lines = [
        "### Torii verdict (F22/F23)",
        f"- **Verdict:** `{fields['verdict']}`",
    ]
    if fields.get("score"):
        lines.append(f"- **Score:** {fields['score']}/100")
    if fields.get("confidence"):
        lines.append(f"- **Confidence:** {fields['confidence']}")
    lines.append(f"- **Pipeline ok:** {fields.get('pipeline_ok', '')}")
    lines.append(f"- **Reaction:** `{fields.get('reaction', '')}`")
    lines.append(
        f"- **Commit status:** `{fields.get('status_state', '')}` — {fields.get('status_desc', '')}"
    )
    if fields.get("review_event"):
        lines.append(f"- **PR review event (F23):** `{fields['review_event']}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "review",
        nargs="?",
        type=Path,
        help="Path to review.md (normalized). Omit with --text.",
    )
    p.add_argument("--text", default=None, help="Review body inline (tests).")
    p.add_argument(
        "--pipeline-rc",
        type=int,
        default=0,
        help="Orchestrator exit code (0 = ok). Default 0.",
    )
    p.add_argument(
        "--format",
        choices=("kv", "summary", "json"),
        default="kv",
        help="kv = GITHUB_OUTPUT lines; summary = job-summary Markdown; json = one object",
    )
    args = p.parse_args(argv)

    if args.text is not None:
        body = args.text
    elif args.review is not None:
        if not args.review.is_file():
            print(f"error: review not found: {args.review}", file=sys.stderr)
            return 1
        body = args.review.read_text(errors="replace")
    else:
        print("error: pass a review path or --text", file=sys.stderr)
        return 1

    parsed = parse_review(body)
    pipeline_ok = args.pipeline_rc == 0
    sig = signal_for(parsed["verdict"], pipeline_ok=pipeline_ok)
    fields = {
        **parsed,
        "pipeline_ok": "true" if pipeline_ok else "false",
        **sig,
    }

    if args.format == "summary":
        sys.stdout.write(step_summary_md(fields))
        return 0
    if args.format == "json":
        import json

        sys.stdout.write(json.dumps(fields, indent=2) + "\n")
        return 0

    # kv (default)
    for k in (
        "verdict",
        "score",
        "confidence",
        "reaction",
        "status_state",
        "status_desc",
        "review_event",
        "pipeline_ok",
    ):
        v = fields.get(k, "")
        # Single-line values only for GITHUB_OUTPUT
        v = str(v).replace("\n", " ").replace("\r", "")
        print(f"{k}={v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
