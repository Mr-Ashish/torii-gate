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


def skill_loop_snapshot(root: Path | None = None) -> dict:
    """F91: optional skill compound loop readiness (does not affect merge exit)."""
    try:
        import importlib.util
        import os

        r = root
        if r is None:
            env = (os.environ.get("TORII_ROOT") or "").strip()
            r = Path(env).resolve() if env else Path(__file__).resolve().parents[1]
        slp = r / "scripts" / "skill_loop_status.py"
        if not slp.is_file():
            return {"available": False}
        spec = importlib.util.spec_from_file_location("skill_loop_status", slp)
        if spec is None or spec.loader is None:
            return {"available": False}
        mod = importlib.util.module_from_spec(spec)
        sys.modules["skill_loop_status"] = mod
        spec.loader.exec_module(mod)
        rep = mod.assess(r, deep=False)
        return {
            "available": True,
            "feature": "F91",
            "level": rep.get("level"),
            "pct": rep.get("pct"),
            "ready": rep.get("ready"),
            "stages_ok": f"{rep.get('stages_ok')}/{rep.get('stages_total')}",
            "skills_n": rep.get("active_skills_n"),
            "loop": rep.get("loop"),
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)[:120]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Torii Gate status from review markdown")
    ap.add_argument("review", type=Path, nargs="?", default=None, help="Path to review-*.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 when block=True")
    ap.add_argument(
        "--skill-loop",
        action="store_true",
        help="F91: include skill compound loop readiness (shallow; never blocks merge alone)",
    )
    ap.add_argument(
        "--skill-loop-only",
        action="store_true",
        help="F91: print skill loop readiness only (no review required)",
    )
    args = ap.parse_args(argv)

    if args.skill_loop_only:
        snap = skill_loop_snapshot()
        print(json.dumps(snap, indent=2) if args.json or True else snap)
        # exit 0 if ready else 1 for ops, but not used in CI gate path
        return 0 if snap.get("ready") else 1

    if args.review is None or not args.review.is_file():
        print(f"missing review file: {args.review}", file=sys.stderr)
        return 2

    text = args.review.read_text(encoding="utf-8", errors="replace")
    parsed = parse_verdict_text(text)
    decision = gate_decision(parsed)
    decision["parsed"] = parsed
    if args.skill_loop:
        decision["skill_loop"] = skill_loop_snapshot()

    if args.json:
        print(json.dumps(decision, indent=2))
    else:
        print(f"{decision['state']}\t{decision['context']}\t{decision['description']}")
        if args.skill_loop and isinstance(decision.get("skill_loop"), dict):
            sl = decision["skill_loop"]
            print(
                f"skill_loop\t{sl.get('level')}\t"
                f"stages={sl.get('stages_ok')} skills={sl.get('skills_n')} ready={sl.get('ready')}"
            )

    if args.strict and decision.get("block"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
