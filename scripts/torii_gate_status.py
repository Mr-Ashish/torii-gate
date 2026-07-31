#!/usr/bin/env python3
"""Torii Gate — map review verdict to CI status + merge policy.

Aligns with ``parse-verdict.py`` contract (``**Verdict:**`` lines) and
optional Security audit line used by the security pack.

Exit codes:
  0  gate open (or advisory)
  1  gate closed when --strict and block=True
  2  usage / missing file
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_VERDICT_RX = re.compile(
    r"^\*\*Verdict:\*\*\s*(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_VERDICT_RX_LOOSE = re.compile(
    r"(?im)^\s*#{0,3}\s*Verdict\s*[:\-]\s*(.+?)\s*$",
)
_SECURITY_RX = re.compile(
    r"(?im)^\s*\**Security audit:\**\s*(.+?)\s*$",
)

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
    s = re.sub(r"\s*[\(\[].*$", "", s).strip().rstrip(".").strip()
    key = s.upper()
    if key in _VERDICT_ALIASES:
        return _VERDICT_ALIASES[key]
    for alias, canon in _VERDICT_ALIASES.items():
        if key.startswith(alias):
            return canon
    return "UNKNOWN"


def parse_verdict_text(text: str) -> dict:
    verdict = "UNKNOWN"
    m = _VERDICT_RX.search(text or "")
    if not m:
        m = _VERDICT_RX_LOOSE.search(text or "")
    if m:
        verdict = normalize_verdict(m.group(1))

    security = ""
    sm = _SECURITY_RX.search(text or "")
    if sm:
        security = sm.group(1).strip()

    return {"verdict": verdict, "security_audit": security, "raw_len": len(text or "")}


def _security_clean(sec: str) -> bool:
    if not sec:
        return True
    return bool(re.match(r"(?i)^(no|none|n/?a|clean|ok|pass)\b", sec.strip()))


def gate_decision(parsed: dict) -> dict:
    v = (parsed.get("verdict") or "UNKNOWN").upper().replace(" ", "_")
    sec = (parsed.get("security_audit") or "").strip()
    sec_bad = not _security_clean(sec)

    if v in {"REQUEST_CHANGES", "REQUEST-CHANGES", "CHANGES_REQUESTED"}:
        return {
            "state": "failure",
            "context": "torii/gate",
            "description": "Torii Gate closed — REQUEST CHANGES",
            "block": True,
            "verdict": v,
        }
    if sec_bad:
        return {
            "state": "failure",
            "context": "torii/gate",
            "description": f"Torii Gate closed — security: {sec[:80]}",
            "block": True,
            "verdict": v,
        }
    if v == "APPROVE":
        return {
            "state": "success",
            "context": "torii/gate",
            "description": "Torii Gate open — APPROVE",
            "block": False,
            "verdict": v,
        }
    return {
        "state": "success",
        "context": "torii/gate",
        "description": f"Torii Gate advisory — {v}",
        "block": False,
        "verdict": v,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Torii Gate status from review markdown")
    ap.add_argument("review", type=Path, help="Path to review-*.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 when block=True")
    args = ap.parse_args(argv)

    if not args.review.is_file():
        print(f"missing review file: {args.review}", file=sys.stderr)
        return 2

    text = args.review.read_text(encoding="utf-8", errors="replace")
    parsed = parse_verdict_text(text)
    decision = gate_decision(parsed)
    decision["parsed"] = parsed

    if args.json:
        print(json.dumps(decision, indent=2))
    else:
        print(f"{decision['state']}\t{decision['context']}\t{decision['description']}")

    if args.strict and decision.get("block"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
