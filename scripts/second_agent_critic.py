#!/usr/bin/env python3
"""F78: Deterministic multi-checker second-agent critic (maker/checker panel).

Research drivers (2026):
  - QASecClaw (arXiv 2605.01885): multi-agent SAST + validation agents cut FPs
  - VulAgent / Argus: decouple discovery (maker) from confirmation (checker)
  - Loop Engineering loop-verifier: independent checker, default REJECT
  - Prior Torii: F70 dual_pass_critic, F72 chain_revalidate, F73 fitness,
    F75 scoped memory — never **orchestrated as one post-run critic panel**

Product thesis:
  Hermes agent is the **maker**. F78 is a second "agent" implemented as
  tools-as-code (no extra LLM spend by default) that re-scores the review
  and can **demote** weak APPROVE → COMMENT/REQUEST_CHANGES when evidence fails.

Commands:
  run       — full multi-checker panel on a review (+ optional out_dir)
  inject    — pre-review policy brief into prompt
  fixture   — good vs weak offline panel
  scorecard — Loop-Ready L0–L3 from a critic JSON
  status    — feature toggles / last report summary

Env:
  TORII_ROOT
  TORII_SECOND_CRITIC          1 (default) | 0
  TORII_SECOND_CRITIC_DEMOTE   1 (default) | 0 — rewrite verdict file on demote
  TORII_SECOND_CRITIC_MIN_PATH  default 0.4 path-evidence floor for APPROVE
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F78"
SCHEMA = 1
MARKER = "<!-- torii-f78-second-agent-critic -->"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

_VERDICT_RX = re.compile(
    r"\*\*Verdict:\*\*\s*(APPROVE|REQUEST\s*CHANGES|COMMENT|LGTM|CHANGES\s*REQUESTED)\b",
    re.I,
)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SECOND_CRITIC") or "1").strip().lower()
    return raw not in _FALSEY


def demote_enabled() -> bool:
    raw = (os.environ.get("TORII_SECOND_CRITIC_DEMOTE") or "1").strip().lower()
    return raw not in _FALSEY


def _scripts() -> Path:
    return Path(__file__).resolve().parent


def _ensure_path() -> None:
    sp = str(_scripts())
    if sp not in sys.path:
        sys.path.insert(0, sp)


def normalize_verdict(raw: str) -> str:
    s = re.sub(r"\s+", " ", (raw or "").strip().upper())
    if s in ("LGTM", "APPROVED"):
        return "APPROVE"
    if s in ("CHANGES REQUESTED", "REQUEST-CHANGES", "REQUEST_CHANGES"):
        return "REQUEST_CHANGES"
    if "REQUEST" in s and "CHANGE" in s:
        return "REQUEST_CHANGES"
    if s in ("APPROVE", "COMMENT", "REQUEST_CHANGES"):
        return s
    return "UNKNOWN"


def parse_verdict(text: str) -> str:
    m = _VERDICT_RX.search(text or "")
    if not m:
        return "UNKNOWN"
    return normalize_verdict(m.group(1))


@dataclass
class CheckerResult:
    id: str
    name: str
    ok: bool
    score: float  # 0-1
    level: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def run_f70_critic(review: str, root: Path, out_dir: Path | None) -> CheckerResult:
    _ensure_path()
    try:
        from bench_security_gate import (  # type: ignore
            dual_pass_critic,
            load_tp_signatures,
            default_tp_path,
            load_fp_rules_dicts,
        )

        tp = load_tp_signatures(default_tp_path(root))
        fp_path = root / ".torii" / "fp-rules.json"
        if out_dir and (out_dir / "fp-rules.json").is_file():
            fp_path = out_dir / "fp-rules.json"
        fp = load_fp_rules_dicts(fp_path) if fp_path.is_file() else []
        result = dual_pass_critic(review, fp_rules=fp, tp_signatures=tp)
        precision = float(result.get("precision_proxy") or 0)
        weak = int(result.get("weak_evidence") or 0)
        chunks = int(result.get("chunk_count") or 0)
        # ok if not mostly weak when there are findings
        ok = precision >= 0.35 or chunks == 0 or weak == 0
        return CheckerResult(
            id="f70_dual_critic",
            name="Dual-pass path/FP/TP critic (F70)",
            ok=ok,
            score=precision,
            detail={
                "precision_proxy": precision,
                "weak_evidence": weak,
                "confirmed_tp": result.get("confirmed_tp"),
                "likely_fp": result.get("likely_fp"),
                "chunk_count": chunks,
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f70_dual_critic",
            name="Dual-pass path/FP/TP critic (F70)",
            ok=False,
            score=0.0,
            error=str(e)[:200],
        )


def run_f72_chain(review_path: Path, out_dir: Path | None) -> CheckerResult:
    _ensure_path()
    try:
        from chain_revalidate import revalidate, load_scan, scan_demo_or_paths  # type: ignore

        text = review_path.read_text(encoding="utf-8", errors="replace")
        scan = {}
        if out_dir and (out_dir / "taint-candidates.json").is_file():
            scan = load_scan(out_dir / "taint-candidates.json")
        if not scan:
            try:
                scan = scan_demo_or_paths(None)
            except Exception:
                scan = {}
        report = revalidate(text, scan=scan or None)
        full_chain = float(report.get("full_chain_rate") or 0)
        # chain quality relative; if no security findings, pass soft
        findings = int(report.get("finding_count") or report.get("n_findings") or 0)
        # read from report structure
        if "findings" in report and isinstance(report["findings"], list):
            findings = len(report["findings"])
        unvalidated = int(report.get("unvalidated") or report.get("unvalidated_count") or 0)
        scorecard = float(report.get("scorecard_pct") or 0) / 100.0
        score = max(full_chain, scorecard * 0.5)
        ok = findings == 0 or full_chain >= 0.25 or scorecard >= 40
        return CheckerResult(
            id="f72_chain",
            name="Full-chain revalidation (F72)",
            ok=ok,
            score=round(min(1.0, score), 4),
            detail={
                "full_chain_rate": full_chain,
                "scorecard_pct": report.get("scorecard_pct"),
                "verdict_checker": report.get("verdict_checker"),
                "finding_count": findings,
                "unvalidated": unvalidated,
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f72_chain",
            name="Full-chain revalidation (F72)",
            ok=False,
            score=0.0,
            error=str(e)[:200],
        )


def run_f73_fitness(review_path: Path, out_dir: Path | None) -> CheckerResult:
    _ensure_path()
    try:
        from trajectory_fitness import compute_fitness, load_json  # type: ignore

        text = review_path.read_text(encoding="utf-8", errors="replace")
        loop: dict[str, Any] = {}
        chain: dict[str, Any] = {}
        if out_dir and (out_dir / "agent-loop" / "agent-loop.json").is_file():
            loop = load_json(out_dir / "agent-loop" / "agent-loop.json") or {}
        if out_dir and (out_dir / "chain-revalidate.json").is_file():
            chain = load_json(out_dir / "chain-revalidate.json") or {}
        fit = compute_fitness(text, loop=loop or None, chain=chain or None)
        composite = float(getattr(fit, "composite", 0) or 0)
        path_ev = float(getattr(fit, "path_evidence", 0) or 0)
        level = str(getattr(fit, "level", "") or "")
        ok = composite >= 0.4 and path_ev >= 0.25
        return CheckerResult(
            id="f73_fitness",
            name="Trajectory fitness (F73)",
            ok=ok,
            score=round(composite, 4),
            level=level,
            detail={
                "composite": composite,
                "path_evidence": path_ev,
                "procedure": getattr(fit, "procedure", None),
                "tool_use": getattr(fit, "tool_use", None),
                "chain_quality": getattr(fit, "chain_quality", None),
                "verdict": getattr(fit, "verdict", None),
            },
        )
    except Exception as e:
        try:
            import subprocess

            cmd = [
                sys.executable,
                str(_scripts() / "trajectory_fitness.py"),
                "score",
                str(review_path),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_root()))
            data = json.loads(r.stdout) if r.returncode == 0 else {}
            composite = float(data.get("composite") or 0)
            path_ev = float(data.get("path_evidence") or 0)
            ok = composite >= 0.4
            return CheckerResult(
                id="f73_fitness",
                name="Trajectory fitness (F73)",
                ok=ok,
                score=round(composite, 4),
                level=str(data.get("level") or ""),
                detail={
                    "composite": composite,
                    "path_evidence": path_ev,
                    "procedure": data.get("procedure"),
                    "tool_use": data.get("tool_use"),
                    "chain_quality": data.get("chain_quality"),
                    "verdict": data.get("verdict"),
                }
                if data
                else {"error": (r.stderr or "")[:200]},
            )
        except Exception as e2:
            return CheckerResult(
                id="f73_fitness",
                name="Trajectory fitness (F73)",
                ok=False,
                score=0.0,
                error=f"{e}; {e2}"[:200],
            )


def run_f75_memory(out_dir: Path | None, root: Path) -> CheckerResult:
    _ensure_path()
    try:
        from scoped_memory_recall import (  # type: ignore
            load_store,
            default_store_path,
            ingest,
            detect_conflicts,
            parse_changed_paths,
        )

        store = default_store_path(root)
        if not store.is_file():
            ingest(root, out_dir=out_dir)
        items = load_store(store, root)
        paths: list[str] = []
        if out_dir and (out_dir / "files.txt").is_file():
            paths = parse_changed_paths(str(out_dir / "files.txt"), root)
        conflicts, suppress = detect_conflicts(items, paths)
        # ok if no hard suppress storm
        ok = len(suppress) <= max(3, len(items) // 2)
        score = 1.0 if not conflicts else max(0.3, 1.0 - 0.1 * len(conflicts))
        return CheckerResult(
            id="f75_memory",
            name="Scoped memory conflicts (F75)",
            ok=ok,
            score=round(score, 4),
            detail={
                "conflict_count": len(conflicts),
                "suppress_count": len(suppress),
                "item_count": len(items),
            },
        )
    except Exception as e:
        return CheckerResult(
            id="f75_memory",
            name="Scoped memory conflicts (F75)",
            ok=True,  # soft — memory optional
            score=0.5,
            error=str(e)[:200],
        )


def run_verdict_structure(review: str) -> CheckerResult:
    v = parse_verdict(review)
    has_summary = bool(re.search(r"(?m)^###?\s+Summary\b", review, re.I))
    has_blocking = bool(re.search(r"(?m)^###?\s+Blocking\b", review, re.I))
    has_checked = bool(re.search(r"(?m)^###?\s+What I checked\b", review, re.I))
    path_n = len(
        re.findall(
            r"`?[\w./-]+\.(?:py|js|ts|tsx|go|java|rb)(?::\d+)?`?",
            review,
        )
    )
    parts = [v != "UNKNOWN", has_summary, has_blocking, has_checked, path_n >= 1]
    score = sum(1 for p in parts if p) / len(parts)
    ok = v != "UNKNOWN" and (path_n >= 1 or v == "APPROVE")
    return CheckerResult(
        id="structure",
        name="Verdict structure",
        ok=ok,
        score=round(score, 4),
        detail={
            "verdict": v,
            "has_summary": has_summary,
            "has_blocking": has_blocking,
            "has_checked": has_checked,
            "path_mentions": path_n,
        },
    )


def composite_panel(checkers: list[CheckerResult]) -> dict[str, Any]:
    """Weighted composite; default REJECT stance on weak APPROVE."""
    weights = {
        "structure": 0.15,
        "f70_dual_critic": 0.25,
        "f72_chain": 0.20,
        "f73_fitness": 0.25,
        "f75_memory": 0.15,
    }
    total_w = 0.0
    acc = 0.0
    for c in checkers:
        w = weights.get(c.id, 0.1)
        # failed checkers with errors still contribute low score
        s = c.score if not c.error else min(c.score, 0.2)
        acc += w * s
        total_w += w
    composite = acc / total_w if total_w else 0.0
    ok_n = sum(1 for c in checkers if c.ok)
    n = len(checkers) or 1
    # Loop-Ready levels
    if composite >= 0.75 and ok_n == n:
        level = "L3"
    elif composite >= 0.55 and ok_n >= n - 1:
        level = "L2"
    elif composite >= 0.35:
        level = "L1"
    else:
        level = "L0"
    return {
        "composite": round(composite, 4),
        "level": level,
        "checkers_ok": ok_n,
        "checkers_total": n,
        "pass_rate": round(ok_n / n, 4),
    }


def decide_verdict(
    maker_verdict: str,
    panel: dict[str, Any],
    checkers: list[CheckerResult],
) -> dict[str, Any]:
    """Default REJECT-until-evidence for APPROVE demotions."""
    maker = normalize_verdict(maker_verdict)
    composite = float(panel.get("composite") or 0)
    path_ev = 0.0
    for c in checkers:
        if c.id == "f73_fitness":
            path_ev = float((c.detail or {}).get("path_evidence") or 0)
        if c.id == "structure":
            path_n = int((c.detail or {}).get("path_mentions") or 0)
            if path_ev == 0 and path_n:
                path_ev = min(1.0, path_n * 0.2)

    min_path = float(os.environ.get("TORII_SECOND_CRITIC_MIN_PATH") or "0.4")
    recommended = maker
    reasons: list[str] = []
    demoted = False

    if maker == "APPROVE":
        if composite < 0.5:
            recommended = "COMMENT"
            demoted = True
            reasons.append(f"composite_below_0.5 ({composite})")
        if path_ev < min_path:
            recommended = "REQUEST_CHANGES" if path_ev < 0.2 else "COMMENT"
            demoted = True
            reasons.append(f"path_evidence_below_{min_path} ({path_ev})")
        weak = next((c for c in checkers if c.id == "f70_dual_critic"), None)
        if weak and float((weak.detail or {}).get("weak_evidence") or 0) >= 3:
            if float((weak.detail or {}).get("precision_proxy") or 0) < 0.3:
                recommended = "COMMENT"
                demoted = True
                reasons.append("high_weak_evidence_low_precision")
    elif maker == "UNKNOWN":
        recommended = "COMMENT"
        demoted = True
        reasons.append("unknown_maker_verdict")

    return {
        "maker_verdict": maker,
        "recommended_verdict": recommended,
        "demoted": demoted,
        "reasons": reasons,
        "path_evidence": path_ev,
        "composite": composite,
    }


def run_panel(
    review_path: Path,
    *,
    out_dir: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    root = root or _root()
    review_path = Path(review_path)
    text = review_path.read_text(encoding="utf-8", errors="replace")
    maker = parse_verdict(text)
    checkers = [
        run_verdict_structure(text),
        run_f70_critic(text, root, out_dir),
        run_f72_chain(review_path, out_dir),
        run_f73_fitness(review_path, out_dir),
        run_f75_memory(out_dir, root),
    ]
    panel = composite_panel(checkers)
    decision = decide_verdict(maker, panel, checkers)
    report = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "at": _now(),
        "review": str(review_path),
        "out_dir": str(out_dir) if out_dir else None,
        "maker_verdict": maker,
        "panel": panel,
        "decision": decision,
        "checkers": [
            {
                "id": c.id,
                "name": c.name,
                "ok": c.ok,
                "score": c.score,
                "level": c.level,
                "detail": c.detail,
                "error": c.error,
            }
            for c in checkers
        ],
    }
    return report


def apply_demote(review_path: Path, decision: dict[str, Any]) -> bool:
    """Rewrite **Verdict:** line when demoted (optional)."""
    if not decision.get("demoted") or not demote_enabled():
        return False
    rec = decision.get("recommended_verdict")
    maker = decision.get("maker_verdict")
    if not rec or rec == maker:
        return False
    text = review_path.read_text(encoding="utf-8", errors="replace")
    label = rec.replace("_", " ")
    new, n = re.subn(
        r"(\*\*Verdict:\*\*\s*)(APPROVE|REQUEST\s*CHANGES|COMMENT|LGTM|CHANGES\s*REQUESTED)\b",
        rf"\1{label}",
        text,
        count=1,
        flags=re.I,
    )
    if n == 0:
        return False
    # annotate
    note = (
        f"\n\n<!-- torii-f78-demote -->\n"
        f"_Second-agent critic (F78) demoted `{maker}` → `{rec}`: "
        f"{', '.join(decision.get('reasons') or [])}_\n"
        f"<!-- /torii-f78-demote -->\n"
    )
    if "torii-f78-demote" not in new:
        new = new.rstrip() + note
    review_path.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    return True


def render_inject() -> str:
    return "\n".join(
        [
            MARKER,
            "## Second-agent critic panel (F78 — maker/checker)",
            "",
            "You are the **maker**. An independent deterministic **checker panel** will re-score this review:",
            "1. **Structure** — verdict + Summary + Blocking + What I checked + path cites",
            "2. **F70 dual critic** — path evidence / FP demote / TP boost",
            "3. **F72 chain** — full-chain source→sink revalidation",
            "4. **F73 fitness** — procedure / tool_use / path_evidence composite",
            "5. **F75 memory** — scoped TP/FP conflicts",
            "",
            "**Default stance:** weak APPROVE without path evidence will be **demoted**.",
            "Prefer REQUEST CHANGES with path:line over narrative-only APPROVE.",
            "",
            "<!-- /torii-f78-second-agent-critic -->",
            "",
        ]
    )


def inject_into_prompt(prompt_path: Path) -> bool:
    if not enabled():
        return False
    path = Path(prompt_path)
    if not path.is_file() and not path.parent.exists():
        return False
    chunk = render_inject()
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if MARKER in text:
        text = re.sub(
            r"<!-- torii-f78-second-agent-critic -->.*?<!-- /torii-f78-second-agent-critic -->\n?",
            chunk,
            text,
            count=1,
            flags=re.S,
        )
    else:
        text = text.rstrip() + "\n\n" + chunk
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return True


def write_report(report: dict[str, Any], out_dir: Path | None, review_path: Path) -> Path:
    if out_dir:
        dest = Path(out_dir) / "second-agent-critic.json"
    else:
        dest = review_path.parent / "second-agent-critic.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # markdown summary
    md = dest.with_suffix(".md")
    panel = report.get("panel") or {}
    dec = report.get("decision") or {}
    lines = [
        f"# Second-agent critic (F78)",
        "",
        f"- at: `{report.get('at')}`",
        f"- maker: **{report.get('maker_verdict')}**",
        f"- recommended: **{dec.get('recommended_verdict')}**"
        + (" (demoted)" if dec.get("demoted") else ""),
        f"- composite: **{panel.get('composite')}** level **{panel.get('level')}** "
        f"({panel.get('checkers_ok')}/{panel.get('checkers_total')} checkers ok)",
        "",
        "| Checker | OK | Score | Notes |",
        "|---------|:--:|------:|-------|",
    ]
    for c in report.get("checkers") or []:
        note = c.get("error") or json.dumps(c.get("detail") or {})[:80]
        lines.append(
            f"| {c.get('id')} | {'yes' if c.get('ok') else 'no'} | {c.get('score')} | {note} |"
        )
    if dec.get("reasons"):
        lines += ["", "### Demote reasons", ""]
        for r in dec["reasons"]:
            lines.append(f"- {r}")
    lines.append("")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def cmd_run(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "skipped": True, "reason": "disabled"}))
        return 0
    root = _root()
    review = Path(args.review)
    out_dir = Path(args.out_dir) if args.out_dir else None
    report = run_panel(review, out_dir=out_dir, root=root)
    demoted = False
    if args.demote or demote_enabled():
        demoted = apply_demote(review, report["decision"])
    report["decision"]["applied_demote"] = demoted
    dest = write_report(report, out_dir, review)
    report["report_path"] = str(dest)
    print(json.dumps(report, indent=2))
    # exit 0 always for soft stage; use --strict to fail on L0
    if args.strict and (report.get("panel") or {}).get("level") == "L0":
        return 1
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    ok = inject_into_prompt(Path(args.prompt))
    print(json.dumps({"feature": FEATURE, "injected": ok, "prompt": args.prompt}))
    return 0 if ok else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    good = root / "docs/benchmarks/fixtures/insecure-demo-good-review.md"
    weak = root / "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
    g = run_panel(good, root=root)
    w = run_panel(weak, root=root)
    g_comp = float((g.get("panel") or {}).get("composite") or 0)
    w_comp = float((w.get("panel") or {}).get("composite") or 0)
    # good should beat weak; weak APPROVE-like should demote or low composite
    delta = g_comp - w_comp
    w_dec = w.get("decision") or {}
    # weak fixture is APPROVE with no path → expect demote or low score
    weak_ok = w_comp < 0.55 or w_dec.get("demoted") or w_dec.get("recommended_verdict") != "APPROVE"
    good_ok = g_comp >= 0.45 and (g.get("maker_verdict") in ("REQUEST_CHANGES", "COMMENT", "APPROVE"))
    # inject
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        prompt = Path(td) / "prompt.md"
        prompt.write_text("# p\n", encoding="utf-8")
        inj = inject_into_prompt(prompt)
        inject_ok = inj and MARKER in prompt.read_text(encoding="utf-8")

    fixture_pass = good_ok and weak_ok and delta >= 0.1 and inject_ok
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                "good_composite": g_comp,
                "weak_composite": w_comp,
                "delta": round(delta, 4),
                "good_level": (g.get("panel") or {}).get("level"),
                "weak_level": (w.get("panel") or {}).get("level"),
                "weak_decision": w_dec,
                "inject_ok": inject_ok,
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def cmd_scorecard(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    panel = data.get("panel") or {}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "level": panel.get("level"),
                "composite": panel.get("composite"),
                "pass_rate": panel.get("pass_rate"),
                "decision": data.get("decision"),
            },
            indent=2,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "demote": demote_enabled(),
                "min_path": os.environ.get("TORII_SECOND_CRITIC_MIN_PATH") or "0.4",
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F78 multi-checker second-agent critic")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Run critic panel on a review")
    pr.add_argument("--review", required=True)
    pr.add_argument("--out-dir", default="")
    pr.add_argument("--demote", action="store_true")
    pr.add_argument("--force", action="store_true")
    pr.add_argument("--strict", action="store_true")
    pr.set_defaults(func=cmd_run)

    pi = sub.add_parser("inject", help="Inject maker/checker policy into prompt")
    pi.add_argument("--prompt", required=True)
    pi.set_defaults(func=cmd_inject)

    sub.add_parser("fixture", help="Offline good vs weak panel").set_defaults(
        func=cmd_fixture
    )

    ps = sub.add_parser("scorecard", help="Summarize critic JSON")
    ps.add_argument("--report", required=True)
    ps.set_defaults(func=cmd_scorecard)

    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
