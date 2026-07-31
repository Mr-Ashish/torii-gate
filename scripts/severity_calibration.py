#!/usr/bin/env python3
"""F50 / H20: severity calibration for missing-test self-reports.

Evidence (odoo e2e #2): GHA REQUEST CHANGES on missing `format` alias tests;
F49 mini APPROVE 95 while Suggestions asked for the same float/integer tests.

When the model *itself* reports a test gap for production behavior under
APPROVE, Torii upgrades to REQUEST CHANGES (score cap aligned with the
40–69 scoring band for missing tests on risky paths).

Usage:
  python3 scripts/severity_calibration.py decide --review review.md
  python3 scripts/severity_calibration.py apply \\
    --review review.md --out review.md --env-out severity-calibration.env

Env:
  TORII_SEVERITY_CALIBRATION  1 (default) | 0/off
  TORII_SEVERITY_SCORE_CAP    default 69

Stdout decide/apply key=value:
  gate=0|1 reason=... match=... verdict_before=... verdict_after=... mutated=...
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_SCORE_CAP = 69

_VERDICT_RX = re.compile(
    r"^(\*\*Verdict:\*\*\s*)(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_SCORE_RX = re.compile(
    r"^(\*\*Score:\*\*\s*)(\d+)(\s*(?:/100)?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_CONF_RX = re.compile(
    r"^(\*\*Confidence:\*\*\s*)(low|medium|high)\b(.*)$",
    re.MULTILINE | re.IGNORECASE,
)
_BANNER_RX = re.compile(
    r"Severity calibration \(F50",
    re.IGNORECASE,
)

# Explicit Tests & risk line: "Relevant tests added/updated: no"
_TESTS_NO_RX = re.compile(
    r"Relevant tests added/updated:\s*no\b",
    re.IGNORECASE,
)

# Self-reported test gaps (Suggestions / Key findings / Tests & risk / Blocking).
# Intentionally require a test-gap signal, not generic "could improve".
_GAP_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tests_no_line", _TESTS_NO_RX),
    (
        "missing_tests",
        re.compile(
            r"\b(?:missing|no|without|lack(?:s|ing)?)\s+"
            r"(?:unit\s+|integration\s+|e2e\s+)?tests?\b"
            r"|\btests?\s+(?:are\s+)?missing\b"
            r"|\bnot\s+(?:covered|asserted|tested)\b"
            r"|\b(?:add|needs?|require[sd]?)\s+(?:unit\s+|a\s+)?"
            r"tests?\s+(?:that|for|covering|to)\b"
            r"|\benhance\s+test\s+coverage\b"
            r"|\btest\s+coverage\b.{0,40}\b(?:missing|gap|incomplete|slight)\b"
            r"|\b(?:missing|gap|incomplete|slight)\b.{0,40}\btest\s+coverage\b"
            r"|\bexplicitly\s+test(?:ing)?\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "coverage_gap",
        re.compile(
            r"\bCoverage:\s*.{0,120}\b(?:missing|none|not\s+covered|gap|no tests)\b",
            re.IGNORECASE,
        ),
    ),
]

# Negations that cancel a match when they dominate the same sentence-ish window.
_NEGATE_RX = re.compile(
    r"\b(?:no\s+missing\s+tests?|tests?\s+(?:are\s+)?(?:present|complete|adequate)"
    r"|fully\s+covered|coverage\s+(?:is\s+)?(?:complete|adequate|good)"
    r"|not\s+(?:missing|needed)\s+tests?)\b",
    re.IGNORECASE,
)

# Sections where a buried test ask under APPROVE is a calibration signal.
_SECTION_RX = re.compile(
    r"^###\s+(Blocking|Key findings|Suggestions|Tests\s*&\s*risk|Nits)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def enabled(raw: str | None = None) -> bool:
    v = (
        raw
        if raw is not None
        else (os.environ.get("TORII_SEVERITY_CALIBRATION") or "1")
    )
    s = str(v).strip().lower()
    return s not in ("0", "false", "off", "no", "none", "disabled")


def score_cap(raw: str | None = None) -> int:
    v = (
        raw
        if raw is not None
        else (os.environ.get("TORII_SEVERITY_SCORE_CAP") or str(DEFAULT_SCORE_CAP))
    )
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return DEFAULT_SCORE_CAP
    return max(0, min(100, n))


def parse_verdict_token(text: str) -> str:
    m = _VERDICT_RX.search(text or "")
    if not m:
        return ""
    raw = m.group(2).strip()
    # Strip trailing notes
    raw = re.sub(r"\s*[(\[].*$", "", raw).strip().rstrip(".")
    up = re.sub(r"\s+", " ", raw).upper()
    aliases = {
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
    if up in aliases:
        return aliases[up]
    for prefix, canon in (
        ("REQUEST", "REQUEST_CHANGES"),
        ("APPROV", "APPROVE"),
        ("COMMENT", "COMMENT"),
        ("LGTM", "APPROVE"),
    ):
        if up.startswith(prefix):
            return canon
    return up.replace(" ", "_")


def _section_bodies(text: str) -> dict[str, str]:
    """Map section name → body until next ### heading."""
    parts = list(_SECTION_RX.finditer(text or ""))
    out: dict[str, str] = {}
    for i, m in enumerate(parts):
        name = re.sub(r"\s+", " ", m.group(1).strip().lower())
        start = m.end()
        end = parts[i + 1].start() if i + 1 < len(parts) else len(text)
        out[name] = text[start:end]
    return out


def detect_test_gap(text: str) -> dict[str, Any]:
    """Return match metadata if review self-reports a production test gap."""
    body = text or ""
    # Global explicit "tests: no" is always a hit.
    if _TESTS_NO_RX.search(body):
        return {
            "hit": True,
            "match": "tests_no_line",
            "snippet": "Relevant tests added/updated: no",
        }

    sections = _section_bodies(body)
    # Prefer signal sections; ignore pure Nits unless nothing else matched later.
    preferred = []
    for key in ("blocking", "key findings", "suggestions", "tests & risk"):
        if key in sections:
            preferred.append((key, sections[key]))
    if not preferred:
        preferred = [("body", body)]

    for sec_name, sec_body in preferred:
        if _NEGATE_RX.search(sec_body) and not _TESTS_NO_RX.search(sec_body):
            # Strong "coverage complete" language — skip this section
            # unless a clear missing-test imperative remains.
            if not re.search(
                r"\b(?:add|missing|needs?)\s+tests?\b",
                sec_body,
                re.IGNORECASE,
            ):
                continue
        for match_id, rx in _GAP_PATTERNS:
            if match_id == "tests_no_line":
                continue  # already handled globally
            m = rx.search(sec_body)
            if not m:
                continue
            snippet = m.group(0)
            snippet = re.sub(r"\s+", " ", snippet).strip()[:120]
            return {
                "hit": True,
                "match": f"{match_id}:{sec_name}",
                "snippet": snippet,
            }

    return {"hit": False, "match": "", "snippet": ""}


def decide(
    text: str,
    *,
    gate_on: bool | None = None,
    verdict: str | None = None,
) -> dict[str, Any]:
    on = enabled() if gate_on is None else bool(gate_on)
    v = (verdict or parse_verdict_token(text) or "").upper().replace(" ", "_")
    if v == "REQUESTCHANGES":
        v = "REQUEST_CHANGES"
    gap = detect_test_gap(text)
    out: dict[str, Any] = {
        "gate": 0,
        "enabled": on,
        "reason": "ok",
        "match": gap.get("match") or "",
        "snippet": gap.get("snippet") or "",
        "verdict": v,
        "action": "none",
        "score_cap": score_cap(),
    }
    if not on:
        out["reason"] = "gate_off"
        return out
    if not gap.get("hit"):
        out["reason"] = "no_test_gap_signal"
        return out
    if v != "APPROVE":
        # Already non-green or COMMENT — annotate only when REQUEST_CHANGES;
        # for COMMENT leave alone (F45 may have already fail-closed).
        out["gate"] = 1
        out["reason"] = "test_gap_non_approve"
        out["action"] = "annotate_only" if v == "REQUEST_CHANGES" else "skip_non_approve"
        if out["action"] == "skip_non_approve":
            out["gate"] = 0
            out["reason"] = f"test_gap_under_{v or 'unknown'}"
        return out

    out["gate"] = 1
    out["reason"] = "approve_with_test_gap"
    out["action"] = "upgrade_request_changes"
    return out


def banner_md(*, reason: str, match: str, snippet: str) -> str:
    snip = (snippet or "").replace("\n", " ").strip()
    if len(snip) > 100:
        snip = snip[:97] + "..."
    snip_disp = snip or "(self-reported test gap)"
    return (
        f"> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a "
        f"**test gap** while verdict was APPROVE (`{reason}` · match=`{match}`). "
        f"Torii upgrades to **REQUEST CHANGES** — missing tests for new "
        f"production behavior are blocking, not Suggestions. "
        f"Signal: _{snip_disp}_\n"
    )


def apply_to_review(
    text: str,
    *,
    decision: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    meta: dict[str, Any] = {
        "mutated": False,
        "verdict_before": parse_verdict_token(text),
        "verdict_after": parse_verdict_token(text),
        "score_capped": False,
        "banner_added": False,
    }
    if not decision.get("gate"):
        return text, meta

    body = text or ""
    action = decision.get("action") or "none"
    reason = str(decision.get("reason") or "approve_with_test_gap")
    match = str(decision.get("match") or "")
    snippet = str(decision.get("snippet") or "")
    cap = int(decision.get("score_cap") or score_cap())

    if action == "upgrade_request_changes" and meta["verdict_before"] == "APPROVE":

        def _repl_v(m: re.Match[str]) -> str:
            return f"{m.group(1)}REQUEST CHANGES"

        new_body, n = _VERDICT_RX.subn(_repl_v, body, count=1)
        if n:
            body = new_body
            meta["mutated"] = True
            meta["verdict_after"] = "REQUEST_CHANGES"

        def _repl_c(m: re.Match[str]) -> str:
            # Keep medium if already medium/high; force at least medium trust in gap
            cur = (m.group(2) or "").lower()
            conf = "medium" if cur == "high" else cur or "medium"
            return f"{m.group(1)}{conf}{m.group(3)}"

        body2, nc = _CONF_RX.subn(_repl_c, body, count=1)
        if nc:
            body = body2
            meta["mutated"] = True

        def _repl_s(m: re.Match[str]) -> str:
            try:
                sc = int(m.group(2))
            except ValueError:
                return m.group(0)
            if sc > cap:
                meta["score_capped"] = True
                meta["mutated"] = True
                return f"{m.group(1)}{cap}{m.group(3)}"
            return m.group(0)

        body = _SCORE_RX.sub(_repl_s, body, count=1)
    else:
        meta["verdict_after"] = meta["verdict_before"]

    if action in ("upgrade_request_changes", "annotate_only") and not _BANNER_RX.search(
        body
    ):
        ban = banner_md(reason=reason, match=match, snippet=snippet)
        m = re.search(
            r"(^\*\*(?:Verdict|Confidence|Score|Review effort):\*\*.*\n)+",
            body,
            re.MULTILINE,
        )
        if m:
            insert_at = m.end()
            body = body[:insert_at] + "\n" + ban + body[insert_at:]
        else:
            body = ban + "\n" + body
        meta["banner_added"] = True
        meta["mutated"] = True

    meta["verdict_after"] = parse_verdict_token(body)
    return body, meta


def write_env(path: Path, decision: dict[str, Any], mut: dict[str, Any] | None = None) -> None:
    lines = [
        f"gate={'1' if decision.get('gate') else '0'}",
        f"enabled={'1' if decision.get('enabled') else '0'}",
        f"reason={decision.get('reason', '')}",
        f"match={decision.get('match', '')}",
        f"action={decision.get('action', 'none')}",
        f"score_cap={decision.get('score_cap', score_cap())}",
        f"verdict_before={(mut or {}).get('verdict_before', decision.get('verdict', ''))}",
        f"verdict_after={(mut or {}).get('verdict_after', '')}",
        f"mutated={'1' if (mut or {}).get('mutated') else '0'}",
        f"score_capped={'1' if (mut or {}).get('score_capped') else '0'}",
        f"banner_added={'1' if (mut or {}).get('banner_added') else '0'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _emit_kv(d: dict[str, Any]) -> None:
    for k, v in d.items():
        if isinstance(v, bool):
            vv = "true" if v else "false"
        else:
            vv = str(v).replace("\n", " ").replace("\r", "")
        print(f"{k}={vv}")


def cmd_decide(args: argparse.Namespace) -> int:
    review_path = Path(args.review)
    if not review_path.is_file():
        print(f"error: review not found: {review_path}", file=sys.stderr)
        return 1
    body = review_path.read_text(encoding="utf-8", errors="replace")
    d = decide(
        body,
        gate_on=enabled(args.enabled) if args.enabled is not None else None,
        verdict=args.verdict,
    )
    _emit_kv(d)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    review_path = Path(args.review)
    if not review_path.is_file():
        print(f"error: review not found: {review_path}", file=sys.stderr)
        return 1
    body = review_path.read_text(encoding="utf-8", errors="replace")
    d = decide(
        body,
        gate_on=enabled(args.enabled) if args.enabled is not None else None,
        verdict=args.verdict,
    )
    new_body, mut = apply_to_review(body, decision=d)
    out = Path(args.out) if args.out else review_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(new_body, encoding="utf-8")
    if args.env_out:
        write_env(Path(args.env_out), d, mut)
    _emit_kv(
        {
            "gate": d.get("gate"),
            "enabled": d.get("enabled"),
            "reason": d.get("reason"),
            "match": d.get("match"),
            "action": d.get("action"),
            "verdict_before": mut.get("verdict_before"),
            "verdict_after": mut.get("verdict_after"),
            "mutated": mut.get("mutated"),
            "score_capped": mut.get("score_capped"),
            "banner_added": mut.get("banner_added"),
        }
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F50/H20 severity calibration gate")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("decide", help="Print severity calibration decision key=value")
    d.add_argument("--review", required=True, help="Path to review Markdown")
    d.add_argument("--verdict", default=None, help="Override parsed verdict")
    d.add_argument(
        "--enabled",
        default=None,
        help="Override TORII_SEVERITY_CALIBRATION (1/0)",
    )
    d.set_defaults(func=cmd_decide)

    a = sub.add_parser("apply", help="Apply calibration rewrite to review")
    a.add_argument("--review", required=True)
    a.add_argument("--out", default=None)
    a.add_argument("--env-out", default=None)
    a.add_argument("--verdict", default=None)
    a.add_argument("--enabled", default=None)
    a.set_defaults(func=cmd_apply)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
