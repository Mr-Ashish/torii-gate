#!/usr/bin/env python3
"""Gate certificate — deterministic merge-authority evidence (tools-as-code).

Every open/close of ``torii/gate`` becomes an auditable certificate:
reason codes + path evidence + optional critic demote — not LLM prose.

Buyer JTBD: "Why did the gate close?" answered by machine-readable
``gate-certificate.json`` / short markdown, not a chat transcript.

Commands:
  emit     — build certificate from a review markdown
  fixture  — hermetic good/weak certificate checks
  status   — summary of last written certificate (if any)
  report   — write docs/benchmarks/gate-certificate.md scorecard stub

Env:
  TORII_ROOT
  TORII_GATE_CERTIFICATE  1 to prefer writing cert next to review (emit --write)
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "GATE_CERT"
SCHEMA = 1
OUT_MD = Path("docs/benchmarks/gate-certificate.md")
OUT_JSON = Path("docs/benchmarks/gate-certificate.json")
MARKER = "<!-- torii-gate-certificate -->"

_PATH_LINE_RX = re.compile(
    r"(?P<path>(?:[\w.-]+/)+[\w.-]+\.[a-zA-Z0-9]{1,12})(?::(?P<line>\d+))?",
)
_BLOCKING_RX = re.compile(r"(?im)^###?\s*Blocking\b")


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_mod(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _gate_mod(root: Path) -> Any:
    return _load_mod("torii_gate_status", root / "scripts" / "torii_gate_status.py")


def _fitness_mod(root: Path) -> Any:
    return _load_mod("trajectory_fitness", root / "scripts" / "trajectory_fitness.py")


def extract_path_cites(text: str) -> list[dict[str, Any]]:
    cites: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in _PATH_LINE_RX.finditer(text or ""):
        p = m.group("path")
        line = m.group("line")
        key = f"{p}:{line or ''}"
        if key in seen:
            continue
        seen.add(key)
        cites.append({"path": p, "line": int(line) if line else None})
    return cites


def load_critic(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def reason_codes(
    decision: dict[str, Any],
    *,
    path_score: float,
    path_hits: list[str],
    has_blocking_section: bool,
    critic: dict[str, Any] | None,
) -> list[str]:
    codes: list[str] = []
    v = (decision.get("verdict") or "UNKNOWN").upper()
    block = bool(decision.get("block"))

    if block and v in {"REQUEST_CHANGES", "REQUEST-CHANGES", "CHANGES_REQUESTED"}:
        codes.append("verdict_request_changes")
    if block and "security:" in (decision.get("description") or "").lower():
        codes.append("security_audit_concern")
    if not block and v == "APPROVE":
        codes.append("verdict_approve_open")
    if not block and v not in {"APPROVE", "REQUEST_CHANGES"}:
        codes.append("advisory_non_blocking")

    if path_score < 0.4:
        codes.append("low_path_evidence")
    elif path_score >= 0.75:
        codes.append("strong_path_evidence")
    else:
        codes.append("partial_path_evidence")

    if has_blocking_section and path_hits:
        codes.append("blocking_with_paths")
    if has_blocking_section and not path_hits:
        codes.append("blocking_without_paths")

    if critic:
        dec = critic.get("decision") if isinstance(critic.get("decision"), dict) else {}
        if dec.get("demoted"):
            codes.append("critic_demoted_maker")
        for r in (dec.get("reasons") or [])[:6]:
            # compress free-text demote reasons into stable-ish codes
            s = re.sub(r"[^a-z0-9_]+", "_", str(r).lower())[:64].strip("_")
            if s:
                codes.append(f"critic:{s[:48]}")

    # de-dupe preserve order
    out: list[str] = []
    seen: set[str] = set()
    for c in codes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def build_certificate(
    root: Path,
    review_path: Path,
    *,
    critic_path: Path | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = review_path.read_text(encoding="utf-8", errors="replace")
    gmod = _gate_mod(root)
    parsed = gmod.parse_verdict_text(text)
    decision = gmod.gate_decision(parsed)

    path_score = 0.1
    path_hits: list[str] = []
    path_fb: list[str] = []
    try:
        fmod = _fitness_mod(root)
        path_score, path_hits, path_fb = fmod.score_path_evidence(text)
    except Exception as exc:  # pragma: no cover — soft fallback
        path_fb = [f"path_score_error:{str(exc)[:80]}"]
        cites = extract_path_cites(text)
        path_hits = [c["path"] for c in cites]
        path_score = 0.75 if len({c["path"] for c in cites if "/" in c["path"]}) >= 1 else 0.1

    cites = extract_path_cites(text)
    has_blocking = bool(_BLOCKING_RX.search(text))
    critic = load_critic(critic_path)
    codes = reason_codes(
        decision,
        path_score=float(path_score),
        path_hits=path_hits,
        has_blocking_section=has_blocking,
        critic=critic,
    )

    body = {
        "verdict": decision.get("verdict"),
        "block": bool(decision.get("block")),
        "state": decision.get("state"),
        "context": decision.get("context") or "torii/gate",
        "description": decision.get("description"),
        "reason_codes": codes,
        "path_evidence": {
            "score": round(float(path_score), 4),
            "hits": path_hits[:24],
            "hit_n": len(path_hits),
            "cites": cites[:24],
            "feedback": path_fb[:8],
        },
        "structure": {
            "has_blocking_section": has_blocking,
            "security_audit": (parsed.get("security_audit") or "")[:200],
            "raw_len": parsed.get("raw_len"),
        },
    }
    if critic:
        dec = critic.get("decision") if isinstance(critic.get("decision"), dict) else {}
        body["critic"] = {
            "maker_verdict": critic.get("maker_verdict") or dec.get("maker_verdict"),
            "recommended_verdict": dec.get("recommended_verdict"),
            "demoted": bool(dec.get("demoted")),
            "reasons": (dec.get("reasons") or [])[:8],
            "path_evidence": dec.get("path_evidence"),
            "composite": dec.get("composite") or (critic.get("panel") or {}).get("composite"),
        }

    raw_for_hash = json.dumps(body, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw_for_hash.encode("utf-8")).hexdigest()[:16]

    cert: dict[str, Any] = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "one_liner": "Deterministic merge-authority certificate: reason codes + path evidence, not chat.",
        "scorecard_target": "evidence / simplicity (dim 12)",
        "dim_lift": "merge-authority evidence + tools-as-code vs LLM prose",
        "at": _now(),
        "review": str(review_path),
        "review_name": review_path.name,
        "certificate_id": f"gc-{digest}",
        "content_sha256_16": digest,
        **body,
        "merge_authority": {
            "context": "torii/gate",
            "open": not bool(decision.get("block")),
            "closed": bool(decision.get("block")),
            "human_summary": _human_summary(decision, codes, path_score),
        },
    }
    if meta:
        cert["meta"] = meta
    return cert


def _human_summary(decision: dict[str, Any], codes: list[str], path_score: float) -> str:
    if decision.get("block"):
        why = ", ".join(codes[:4]) or "policy"
        return f"CLOSED — {decision.get('verdict')} ({why}); path_evidence={path_score:.2f}"
    return f"OPEN — {decision.get('verdict')} ({', '.join(codes[:3])}); path_evidence={path_score:.2f}"


def render_md(cert: dict[str, Any]) -> str:
    pe = cert.get("path_evidence") or {}
    ma = cert.get("merge_authority") or {}
    codes = cert.get("reason_codes") or []
    lines = [
        MARKER,
        "",
        "# Torii gate certificate",
        "",
        f"_id `{cert.get('certificate_id')}` · `{cert.get('at')}`_",
        "",
        f"**{ma.get('human_summary')}**",
        "",
        "| Field | Value |",
        "|-------|------:|",
        f"| context | `{cert.get('context')}` |",
        f"| state | {cert.get('state')} |",
        f"| block | {cert.get('block')} |",
        f"| verdict | {cert.get('verdict')} |",
        f"| path_evidence | {pe.get('score')} (n={pe.get('hit_n')}) |",
        f"| content_sha | `{cert.get('content_sha256_16')}` |",
        "",
        "## Reason codes (deterministic)",
        "",
    ]
    if codes:
        for c in codes:
            lines.append(f"- `{c}`")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Path cites", ""])
    hits = pe.get("hits") or []
    if hits:
        for h in hits[:20]:
            lines.append(f"- `{h}`")
    else:
        lines.append("- _(none)_")
    critic = cert.get("critic")
    if isinstance(critic, dict) and critic.get("demoted"):
        lines.extend(["", "## Critic demote", ""])
        lines.append(f"- maker → recommended: **{critic.get('maker_verdict')}** → **{critic.get('recommended_verdict')}**")
        for r in critic.get("reasons") or []:
            lines.append(f"- {r}")
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            f"python3 scripts/gate_certificate.py emit --review {cert.get('review_name') or 'review.md'}",
            "python3 scripts/torii.py certificate -- fixture",
            "```",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_certificate(cert: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jp = out_dir / "gate-certificate.json"
    mp = out_dir / "gate-certificate.md"
    jp.write_text(json.dumps(cert, indent=2) + "\n", encoding="utf-8")
    mp.write_text(render_md(cert), encoding="utf-8")
    return {"json": jp, "md": mp}


def run_fixture(root: Path) -> dict[str, Any]:
    fixtures = root / "docs" / "benchmarks" / "fixtures"
    good = fixtures / "insecure-demo-good-review.md"
    weak = fixtures / "insecure-demo-weak-review.md"
    critic_p = fixtures / "second-agent-critic.json"

    checks: dict[str, bool] = {}
    detail: dict[str, Any] = {}

    if not good.is_file() or not weak.is_file():
        return {
            "feature": FEATURE,
            "schema": SCHEMA,
            "fixture_pass": False,
            "error": "missing_fixtures",
            "at": _now(),
        }

    good_c = build_certificate(root, good)
    weak_c = build_certificate(root, weak, critic_path=critic_p if critic_p.is_file() else None)

    checks["good_blocks"] = bool(good_c.get("block")) is True
    checks["good_request_changes"] = good_c.get("verdict") == "REQUEST_CHANGES"
    checks["good_strong_or_partial_path"] = float(
        (good_c.get("path_evidence") or {}).get("score") or 0
    ) >= 0.45
    checks["good_has_reason_codes"] = bool(good_c.get("reason_codes"))
    checks["good_has_cert_id"] = bool(good_c.get("certificate_id"))
    checks["weak_opens"] = bool(weak_c.get("block")) is False
    checks["weak_low_path"] = "low_path_evidence" in (weak_c.get("reason_codes") or [])
    if critic_p.is_file():
        checks["weak_critic_attached"] = isinstance(weak_c.get("critic"), dict)
        checks["weak_critic_demoted_code"] = "critic_demoted_maker" in (
            weak_c.get("reason_codes") or []
        )
    else:
        checks["weak_critic_attached"] = True  # optional
        checks["weak_critic_demoted_code"] = True

    # write hermetic sample under benchmarks
    sample_dir = root / "docs" / "benchmarks" / "fixtures"
    write_certificate(good_c, sample_dir / "gate-certificate-good")
    write_certificate(weak_c, sample_dir / "gate-certificate-weak")
    checks["wrote_sample_certs"] = (
        sample_dir / "gate-certificate-good" / "gate-certificate.json"
    ).is_file() and (sample_dir / "gate-certificate-weak" / "gate-certificate.json").is_file()

    # docs exist for buyer path
    gate_md = root / "docs" / "GATE.md"
    checks["gate_md_mentions_certificate"] = "certificate" in gate_md.read_text(
        encoding="utf-8", errors="replace"
    ).lower() if gate_md.is_file() else False

    detail["good"] = {
        "block": good_c.get("block"),
        "verdict": good_c.get("verdict"),
        "path_score": (good_c.get("path_evidence") or {}).get("score"),
        "reason_codes": good_c.get("reason_codes"),
        "certificate_id": good_c.get("certificate_id"),
    }
    detail["weak"] = {
        "block": weak_c.get("block"),
        "verdict": weak_c.get("verdict"),
        "path_score": (weak_c.get("path_evidence") or {}).get("score"),
        "reason_codes": weak_c.get("reason_codes"),
        "certificate_id": weak_c.get("certificate_id"),
    }

    ok_n = sum(1 for v in checks.values() if v)
    total = len(checks)
    fixture_pass = ok_n == total and total > 0
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "fixture_pass": fixture_pass,
        "ok_n": ok_n,
        "total": total,
        "checks": checks,
        "detail": detail,
        "scorecard_target": "evidence / simplicity (dim 12)",
        "dim_lift": "merge-authority certificate tools-as-code",
        "one_liner": "Every gate open/close ships a deterministic reason-code certificate.",
        "at": _now(),
    }


def write_report(root: Path, fixture: dict[str, Any] | None = None) -> dict[str, Any]:
    fx = fixture or run_fixture(root)
    payload = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "scored_at": _now(),
        "fixture_pass": fx.get("fixture_pass"),
        "ok_n": fx.get("ok_n"),
        "total": fx.get("total"),
        "checks": fx.get("checks"),
        "detail": fx.get("detail"),
        "scorecard_target": "evidence / simplicity (dim 12)",
        "dim_lift": "merge-authority evidence + tools-as-code vs LLM prose",
        "one_liner": "Deterministic merge-authority certificate: reason codes + path evidence, not chat.",
    }
    out_json = root / OUT_JSON
    out_md = root / OUT_MD
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    checks = fx.get("checks") or {}
    rows = "\n".join(
        f"| `{k}` | {'yes' if v else 'no'} |" for k, v in checks.items()
    )
    detail = fx.get("detail") or {}
    good = detail.get("good") or {}
    weak = detail.get("weak") or {}
    md = f"""{MARKER}

# Gate certificate surface

_Generated: `{payload['scored_at']}` · **fixture_pass={payload['fixture_pass']}** · target **evidence / dim 12**_

{payload['one_liner']}

## Hermetic checks

| Check | Pass |
|-------|:----:|
{rows}

## Sample certificates

| Review | block | verdict | path_score | cert id |
|--------|:-----:|---------|----------:|---------|
| insecure-demo good | {good.get('block')} | {good.get('verdict')} | {good.get('path_score')} | `{good.get('certificate_id')}` |
| insecure-demo weak | {weak.get('block')} | {weak.get('verdict')} | {weak.get('path_score')} | `{weak.get('certificate_id')}` |

Fixtures: `docs/benchmarks/fixtures/gate-certificate-{{good,weak}}/`.

## Buyer use

```bash
python3 scripts/gate_certificate.py emit --review .torii-out/review-1.md --write .torii-out
python3 scripts/torii.py certificate -- fixture
python3 scripts/torii.py certificate -- report
```

Branch protection still requires **`torii/gate`**. The certificate explains *why* without opening the chat log.

Related: [GATE.md](../GATE.md) · [GOLDEN-PATH.md](../GOLDEN-PATH.md)
"""
    out_md.write_text(md, encoding="utf-8")
    payload["paths"] = {"md": str(OUT_MD), "json": str(OUT_JSON)}
    return payload


def cmd_emit(args: argparse.Namespace) -> int:
    root = _root()
    review = Path(args.review)
    if not review.is_file():
        # allow relative to root
        alt = root / review
        if alt.is_file():
            review = alt
        else:
            print(json.dumps({"error": "missing_review", "path": str(args.review)}), file=sys.stderr)
            return 2
    critic = Path(args.critic) if args.critic else None
    if critic and not critic.is_file():
        c2 = root / critic
        critic = c2 if c2.is_file() else critic
    meta = {}
    if args.repo:
        meta["repo"] = args.repo
    if args.pr:
        meta["pr"] = args.pr
    cert = build_certificate(root, review, critic_path=critic, meta=meta or None)
    if args.write:
        out = Path(args.write)
        if not out.is_absolute():
            out = root / out
        paths = write_certificate(cert, out)
        cert["written"] = {k: str(v) for k, v in paths.items()}
    if args.json or not args.write:
        print(json.dumps(cert, indent=2))
    else:
        print(cert.get("merge_authority", {}).get("human_summary"))
        print(cert.get("written"))
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    # ensure GATE.md mentions certificate before final check; report path soft
    rep = run_fixture(root)
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("fixture_pass") else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    # prefer report json, else fixture sample
    candidates = [
        root / OUT_JSON,
        root / "docs/benchmarks/fixtures/gate-certificate-good/gate-certificate.json",
    ]
    for p in candidates:
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            print(json.dumps({"feature": FEATURE, "source": str(p.relative_to(root)), **{k: data.get(k) for k in ("fixture_pass", "certificate_id", "block", "verdict", "reason_codes", "merge_authority", "one_liner", "at", "scored_at") if k in data or True}}, indent=2, default=str))
            return 0
    # fall back to fixture
    rep = run_fixture(root)
    print(json.dumps({"feature": FEATURE, "source": "fixture", "fixture_pass": rep.get("fixture_pass"), "ok_n": rep.get("ok_n"), "total": rep.get("total")}, indent=2))
    return 0 if rep.get("fixture_pass") else 1


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    payload = write_report(root)
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("fixture_pass") else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Torii gate certificate (merge-authority evidence)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    em = sub.add_parser("emit", help="Emit certificate from review markdown")
    em.add_argument("--review", required=True, help="Path to review-*.md")
    em.add_argument("--critic", default=None, help="Optional second-agent critic JSON")
    em.add_argument("--write", default=None, help="Directory to write gate-certificate.{json,md}")
    em.add_argument("--repo", default=None)
    em.add_argument("--pr", default=None)
    em.add_argument("--json", action="store_true")
    em.set_defaults(func=cmd_emit)

    fx = sub.add_parser("fixture", help="Hermetic good/weak certificate checks")
    fx.set_defaults(func=cmd_fixture)

    st = sub.add_parser("status", help="Show last certificate / fixture summary")
    st.set_defaults(func=cmd_status)

    rp = sub.add_parser("report", help="Write docs/benchmarks/gate-certificate.{md,json}")
    rp.set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
