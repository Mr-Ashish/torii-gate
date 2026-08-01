#!/usr/bin/env python3
"""Own-repo required-check · quieter-over-time path (post-queue product surface).

Buyer story: *the gate gets stricter and quieter over time — not noisier.*

Tools-as-code (no new F-compound loop):
  - own-repo required-check readiness (torii/gate docs + pack + status)
  - dogfood vault trajectory: path evidence, tool use, certificates, weak noise
  - published chart under docs/benchmarks/quieter-over-time.md

Commands:
  report | fixture | status
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "QUIETER"
SCHEMA = 1
MARKER = "<!-- torii-quieter-over-time -->"
OUT_MD = Path("docs/benchmarks/quieter-over-time.md")
OUT_JSON = Path("docs/benchmarks/quieter-over-time.json")
BUYER_DOC = Path("docs/QUIETER.md")


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def vault_root(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_TRACE_VAULT_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / "docs" / "benchmarks" / "traces"


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _norm_verdict(v: Any) -> str:
    s = str(v or "").strip().upper().replace(" ", "_")
    if s in ("REQUEST_CHANGES", "REQUESTCHANGES", "CHANGES_REQUESTED"):
        return "REQUEST_CHANGES"
    if s in ("APPROVE", "APPROVED"):
        return "APPROVE"
    if s in ("COMMENT", "COMMENTS"):
        return "COMMENT"
    return s or "UNKNOWN"


def collect_dogfood_rows(vroot: Path) -> list[dict[str, Any]]:
    """Chronological dogfood rows with quieter signals."""
    rows: list[dict[str, Any]] = []
    if not vroot.is_dir():
        return rows

    for d in sorted(vroot.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        summary = _safe_json(d / "summary.json")
        fitness = summary.get("fitness") if isinstance(summary.get("fitness"), dict) else None
        if fitness is None:
            fitness = _safe_json(d / "fitness.json") or None
        critic = _safe_json(d / "second-agent-critic.json")
        cert = _safe_json(d / "gate-certificate.json")
        usage = _safe_json(d / "hermes-usage.json")
        timings = _safe_json(d / "timings.json")
        meta = _safe_json(d / "meta.json")

        repo = str(
            summary.get("repo")
            or meta.get("repo")
            or ""
        )
        pr = str(summary.get("pr") or summary.get("pr_number") or meta.get("pr") or "")
        name_l = d.name.lower()
        if not repo and "pytorch" in name_l:
            repo = "pytorch/pytorch"
        if not pr:
            m = re.search(r"pr[#\-]?(\d{4,})", name_l)
            if m:
                pr = m.group(1)

        elapsed = timings.get("total_seconds") if timings else None
        if elapsed is None:
            elapsed = summary.get("elapsed_s") or summary.get("total_seconds")
        cost = usage.get("estimated_cost_usd") if usage else summary.get("cost_usd")

        verdict = ""
        if isinstance(fitness, dict):
            verdict = str(fitness.get("verdict") or "")
        if not verdict:
            verdict = str(summary.get("verdict") or "")
        if not verdict and cert:
            verdict = str(cert.get("verdict") or "")
        verdict_n = _norm_verdict(verdict)

        path_ev = None
        if isinstance(fitness, dict) and isinstance(fitness.get("path_evidence"), (int, float)):
            path_ev = float(fitness["path_evidence"])
        if path_ev is None and isinstance(summary.get("path_evidence_score"), (int, float)):
            path_ev = float(summary["path_evidence_score"])
        if path_ev is None and cert and isinstance(cert.get("path_evidence_score"), (int, float)):
            path_ev = float(cert["path_evidence_score"])
        if path_ev is None and critic:
            dec = critic.get("decision") if isinstance(critic.get("decision"), dict) else {}
            if isinstance(dec.get("path_evidence"), (int, float)):
                path_ev = float(dec["path_evidence"])

        tools = summary.get("tool_call_turns")
        if tools is None and isinstance(fitness, dict):
            tools = fitness.get("tool_call_turns")
        if tools is None and critic:
            tools = critic.get("tool_call_turns")

        demoted = False
        if critic:
            dec = critic.get("decision") if isinstance(critic.get("decision"), dict) else {}
            demoted = bool(dec.get("demoted"))
        weak_approve = verdict_n == "APPROVE" and (
            demoted or (path_ev is not None and path_ev < 0.5) or (isinstance(tools, int) and tools < 1)
        )

        is_dogfood = bool(
            repo
            or re.search(r"pytorch|pr\d{3,}|modal-", name_l)
            or (elapsed is not None and verdict_n != "UNKNOWN")
        )
        if not is_dogfood:
            continue
        if not any([repo, pr, elapsed, cost, verdict_n != "UNKNOWN", cert]):
            continue

        # skip pure feature-lab folders without live signal
        if name_l.startswith("f") and not any(
            x in name_l for x in ("pytorch", "modal", "dogfood", "live")
        ):
            # allow fNN* only if summary has repo/pr
            if not (repo and pr):
                continue

        rows.append(
            {
                "trace_id": d.name,
                "repo": repo,
                "pr": pr,
                "verdict": verdict_n,
                "time_to_signal_s": float(elapsed) if isinstance(elapsed, (int, float)) else None,
                "cost_usd": float(cost) if isinstance(cost, (int, float)) else None,
                "path_evidence": path_ev,
                "tool_call_turns": int(tools) if isinstance(tools, (int, float)) else None,
                "has_certificate": bool(cert and cert.get("certificate_id")),
                "certificate_id": (cert or {}).get("certificate_id"),
                "demoted": demoted,
                "weak_approve": weak_approve,
                "block": summary.get("block") if "block" in summary else (cert or {}).get("block"),
                "host": str(summary.get("host") or ("modal" if "modal" in name_l else "local")),
                "model": str(summary.get("model") or (usage or {}).get("model") or ""),
            }
        )
    return rows


def _rate(ok: int, n: int) -> float | None:
    if n <= 0:
        return None
    return round(ok / n, 4)


def window_metrics(rows: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"label": label, "n": 0}

    path_vals = [r["path_evidence"] for r in rows if isinstance(r.get("path_evidence"), (int, float))]
    tools = [r["tool_call_turns"] for r in rows if isinstance(r.get("tool_call_turns"), (int, float))]
    costs = [r["cost_usd"] for r in rows if isinstance(r.get("cost_usd"), (int, float))]
    tts = [r["time_to_signal_s"] for r in rows if isinstance(r.get("time_to_signal_s"), (int, float))]
    cert_n = sum(1 for r in rows if r.get("has_certificate"))
    tool_n = sum(1 for r in rows if isinstance(r.get("tool_call_turns"), (int, float)) and r["tool_call_turns"] >= 1)
    strong_path_n = sum(1 for r in rows if isinstance(r.get("path_evidence"), (int, float)) and r["path_evidence"] >= 0.7)
    weak_n = sum(1 for r in rows if r.get("weak_approve"))
    demote_n = sum(1 for r in rows if r.get("demoted"))
    rc_n = sum(1 for r in rows if r.get("verdict") == "REQUEST_CHANGES")
    ap_n = sum(1 for r in rows if r.get("verdict") == "APPROVE")
    cm_n = sum(1 for r in rows if r.get("verdict") == "COMMENT")
    unknown_n = sum(1 for r in rows if r.get("verdict") == "UNKNOWN")

    # quieter composite: high path evidence + tools + certs; low weak approve
    # when measured runs present
    measured = max(len(path_vals), tool_n, cert_n, n)
    quiet_score = None
    if n >= 2:
        pe = (statistics.mean(path_vals) if path_vals else 0.5)
        tu = tool_n / n
        cr = cert_n / n
        weak = weak_n / n
        quiet_score = round(max(0.0, min(1.0, 0.35 * pe + 0.30 * tu + 0.20 * cr + 0.15 * (1.0 - weak))), 4)

    return {
        "label": label,
        "n": n,
        "path_evidence_mean": round(statistics.mean(path_vals), 4) if path_vals else None,
        "path_evidence_n": len(path_vals),
        "strong_path_rate": _rate(strong_path_n, n),
        "tool_use_rate": _rate(tool_n, n),
        "tool_turns_mean": round(statistics.mean(tools), 2) if tools else None,
        "certificate_rate": _rate(cert_n, n),
        "weak_approve_n": weak_n,
        "weak_approve_rate": _rate(weak_n, n),
        "demoted_n": demote_n,
        "verdict_request_changes": rc_n,
        "verdict_approve": ap_n,
        "verdict_comment": cm_n,
        "verdict_unknown": unknown_n,
        "cost_usd_mean": round(statistics.mean(costs), 4) if costs else None,
        "cost_n": len(costs),
        "time_to_signal_mean": round(statistics.mean(tts), 1) if tts else None,
        "quiet_score": quiet_score,
        "measured_signals": measured,
    }


def split_windows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Early vs late halves of chronological dogfood (quieter-over-time)."""
    if not rows:
        return {
            "all": window_metrics([], label="all"),
            "early": window_metrics([], label="early"),
            "late": window_metrics([], label="late"),
            "delta_quiet_score": None,
            "getting_quieter": None,
        }
    mid = max(1, len(rows) // 2)
    early = rows[:mid]
    late = rows[mid:]
    # if odd, late has the more recent half+remainder
    if len(rows) >= 4:
        early = rows[: len(rows) // 2]
        late = rows[len(rows) // 2 :]
    w_all = window_metrics(rows, label="all")
    w_early = window_metrics(early, label="early")
    w_late = window_metrics(late, label="late")
    dq = None
    if w_early.get("quiet_score") is not None and w_late.get("quiet_score") is not None:
        dq = round(float(w_late["quiet_score"]) - float(w_early["quiet_score"]), 4)
    # "getting quieter" = late quiet_score >= early, or weak_approve down / path up
    getting = None
    if dq is not None:
        getting = dq >= -0.02  # allow flat; prefer non-regression
    return {
        "all": w_all,
        "early": w_early,
        "late": w_late,
        "delta_quiet_score": dq,
        "getting_quieter": getting,
        "early_n": len(early),
        "late_n": len(late),
    }


def own_repo_required_check(root: Path) -> dict[str, Any]:
    """Readiness for wiring torii/gate on a customer/own repo."""
    checks = {
        "golden_path_doc": (root / "docs" / "GOLDEN-PATH.md").is_file(),
        "gate_doc": (root / "docs" / "GATE.md").is_file(),
        "quieter_buyer_doc": (root / BUYER_DOC).is_file(),
        "install_script": (root / "scripts" / "install-torii.sh").is_file(),
        "pack_caller": (root / "pack" / "torii-pr-review-caller.yml").is_file(),
        "gate_status_script": (root / "scripts" / "torii_gate_status.py").is_file(),
        "gate_certificate_script": (root / "scripts" / "gate_certificate.py").is_file(),
        "smoke_script": (root / "scripts" / "smoke-torii-gate.sh").is_file(),
        "branch_protection_named": False,
        "required_context_torii_gate": False,
    }
    # docs must name branch protection + torii/gate
    for rel in ("docs/GOLDEN-PATH.md", "docs/GATE.md", str(BUYER_DOC)):
        p = root / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        if re.search(r"branch protection", text, re.I):
            checks["branch_protection_named"] = True
        if "torii/gate" in text:
            checks["required_context_torii_gate"] = True

    ok_n = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "checks": checks,
        "ok_n": ok_n,
        "total": total,
        "ok": ok_n == total,
        "required_check": "torii/gate",
        "one_liner": "install pack → require torii/gate → dogfood → quieter chart",
    }


def tool_use_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Agent tool-use quality from dogfood (tools-as-code, not SOUL prose)."""
    with_tools = [r for r in rows if isinstance(r.get("tool_call_turns"), (int, float))]
    n = len(with_tools)
    if n == 0:
        return {
            "n": 0,
            "tool_use_rate": None,
            "mean_turns": None,
            "zero_tool_n": 0,
            "quality_ok": False,
            "note": "no tool_call_turns in vault yet",
        }
    zero = sum(1 for r in with_tools if int(r["tool_call_turns"]) < 1)
    mean_t = statistics.mean(float(r["tool_call_turns"]) for r in with_tools)
    rate = _rate(n - zero, n)
    # quality_ok: majority of measured runs used tools
    quality_ok = (rate or 0) >= 0.5 and mean_t >= 1.0
    return {
        "n": n,
        "tool_use_rate": rate,
        "mean_turns": round(mean_t, 2),
        "zero_tool_n": zero,
        "quality_ok": quality_ok,
        "note": "measured from summary/fitness tool_call_turns on dogfood",
    }


def build_report(root: Path) -> dict[str, Any]:
    rows = collect_dogfood_rows(vault_root(root))
    windows = split_windows(rows)
    own = own_repo_required_check(root)
    tools_q = tool_use_quality(rows)
    late = windows.get("late") or {}
    all_w = windows.get("all") or {}

    quieter_ok = bool(
        own.get("ok")
        and (all_w.get("n") or 0) >= 1
        and (
            windows.get("getting_quieter") is not False
            or (all_w.get("quiet_score") or 0) >= 0.4
            or tools_q.get("quality_ok")
        )
    )

    return {
        "feature": FEATURE,
        "schema_version": SCHEMA,
        "at": _now(),
        "one_liner": "Own-repo required check torii/gate + quieter-over-time dogfood chart",
        "scorecard_target": "JTBD / simplicity (dims 3 + 12)",
        "dim_lift": "stricter-and-quieter path measured tools-as-code",
        "required_check": "torii/gate",
        "own_repo": own,
        "dogfood_n": len(rows),
        "windows": windows,
        "tool_use_quality": tools_q,
        "quieter_ok": quieter_ok,
        "recent_rows": rows[-12:],
        "paths": {
            "md": str(OUT_MD),
            "json": str(OUT_JSON),
            "buyer_doc": str(BUYER_DOC),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    own = report.get("own_repo") or {}
    checks = own.get("checks") or {}
    win = report.get("windows") or {}
    early = win.get("early") or {}
    late = win.get("late") or {}
    all_w = win.get("all") or {}
    tools_q = report.get("tool_use_quality") or {}
    rows = report.get("recent_rows") or []

    lines = [
        MARKER,
        "",
        "# Quieter-over-time (own-repo required check)",
        "",
        f"_Generated: `{report.get('at')}` · feature **{FEATURE}** · "
        f"quieter_ok=`{report.get('quieter_ok')}`_",
        "",
        f"**One-liner:** {report.get('one_liner')}",
        "",
        f"**Required check:** `{report.get('required_check')}`",
        "",
        "Buyer path:",
        "",
        "```text",
        "install pack → OPENROUTER_API_KEY → branch protection requires torii/gate",
        "    → @torii review → path-evidenced signal → next PR quieter",
        "```",
        "",
        "Buyer doc: [`docs/QUIETER.md`](../QUIETER.md) · Golden path: [`GOLDEN-PATH.md`](../GOLDEN-PATH.md)",
        "",
        "## Own-repo required-check readiness",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| checks ok | {own.get('ok_n')}/{own.get('total')} |",
        f"| own_repo_ok | {own.get('ok')} |",
        "",
        "| Check | Pass |",
        "|-------|:----:|",
    ]
    for k, v in checks.items():
        lines.append(f"| `{k}` | {'yes' if v else 'no'} |")

    lines += [
        "",
        "## Dogfood trajectory (early → late)",
        "",
        "Quieter means: more path evidence + tool use + certificates; fewer weak APPROVEs.",
        "",
        "| Window | n | path_ev mean | tool_use rate | cert rate | weak APPROVE | quiet_score |",
        "|--------|--:|-------------:|--------------:|----------:|-------------:|------------:|",
    ]
    for w in (early, late, all_w):
        lines.append(
            f"| {w.get('label')} | {w.get('n')} | {w.get('path_evidence_mean')} | "
            f"{w.get('tool_use_rate')} | {w.get('certificate_rate')} | "
            f"{w.get('weak_approve_rate')} | {w.get('quiet_score')} |"
        )

    lines += [
        "",
        f"**delta quiet_score (late − early):** `{win.get('delta_quiet_score')}` · "
        f"**getting_quieter:** `{win.get('getting_quieter')}`",
        "",
        "## Agent tool-use quality (tools-as-code)",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| measured runs | {tools_q.get('n')} |",
        f"| tool_use_rate | {tools_q.get('tool_use_rate')} |",
        f"| mean turns | {tools_q.get('mean_turns')} |",
        f"| zero-tool runs | {tools_q.get('zero_tool_n')} |",
        f"| quality_ok | {tools_q.get('quality_ok')} |",
        "",
        "## Cost / time (all dogfood)",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| cost/PR mean USD | {all_w.get('cost_usd_mean')} (n={all_w.get('cost_n')}) |",
        f"| time-to-signal mean s | {all_w.get('time_to_signal_mean')} |",
        "",
        "## Recent dogfood rows",
        "",
        "| trace | repo | pr | verdict | tools | path_ev | cert | weak_appr |",
        "|-------|------|---:|---------|------:|--------:|:----:|:---------:|",
    ]
    for r in rows[-12:]:
        lines.append(
            f"| `{r.get('trace_id', '')[:48]}` | {r.get('repo')} | {r.get('pr')} | "
            f"{r.get('verdict')} | {r.get('tool_call_turns')} | {r.get('path_evidence')} | "
            f"{'yes' if r.get('has_certificate') else ''} | "
            f"{'yes' if r.get('weak_approve') else ''} |"
        )

    lines += [
        "",
        "## Refresh",
        "",
        "```bash",
        "python3 scripts/quieter_over_time.py report",
        "python3 scripts/torii.py quieter -- status",
        "```",
        "",
    ]
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    md_path = root / OUT_MD
    js_path = root / OUT_JSON
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    js_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))
        print(f"\n# wrote {md_path.relative_to(root)} · {js_path.relative_to(root)}", file=sys.stderr)
    return 0 if report.get("quieter_ok") or getattr(args, "allow_partial", False) else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic readiness: own-repo checks + script/docs present (no live vault required)."""
    root = _root()
    own = own_repo_required_check(root)
    script_ok = (root / "scripts" / "quieter_over_time.py").is_file()
    # Buyer doc may be written by report first-time; fixture requires core path docs
    core_ok = bool(
        own.get("checks", {}).get("golden_path_doc")
        and own.get("checks", {}).get("gate_doc")
        and own.get("checks", {}).get("install_script")
        and own.get("checks", {}).get("gate_status_script")
        and own.get("checks", {}).get("branch_protection_named")
        and own.get("checks", {}).get("required_context_torii_gate")
        and script_ok
    )
    # If buyer doc missing, still pass fixture when core path is ready
    # (report creates metrics; buyer doc is part of ship)
    buyer_ok = (root / BUYER_DOC).is_file()
    fixture_pass = core_ok and buyer_ok
    out = {
        "feature": FEATURE,
        "fixture_pass": fixture_pass,
        "core_ok": core_ok,
        "buyer_doc_ok": buyer_ok,
        "own_repo_ok_n": own.get("ok_n"),
        "own_repo_total": own.get("total"),
        "required_check": "torii/gate",
        "scorecard_target": "JTBD / simplicity",
    }
    print(json.dumps(out, indent=2))
    return 0 if fixture_pass else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    win = report.get("windows") or {}
    slim = {
        "feature": FEATURE,
        "quieter_ok": report.get("quieter_ok"),
        "required_check": report.get("required_check"),
        "own_repo_ok": (report.get("own_repo") or {}).get("ok"),
        "dogfood_n": report.get("dogfood_n"),
        "quiet_score_all": (win.get("all") or {}).get("quiet_score"),
        "delta_quiet_score": win.get("delta_quiet_score"),
        "getting_quieter": win.get("getting_quieter"),
        "tool_use_quality_ok": (report.get("tool_use_quality") or {}).get("quality_ok"),
        "at": report.get("at"),
    }
    print(json.dumps(slim, indent=2))
    return 0 if report.get("quieter_ok") else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Quieter-over-time + own-repo required check")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="Write quieter-over-time.md + json from vault")
    r.add_argument("--json", action="store_true")
    r.add_argument("--allow-partial", action="store_true")
    r.set_defaults(func=cmd_report)

    f = sub.add_parser("fixture", help="Hermetic own-repo path readiness")
    f.set_defaults(func=cmd_fixture)

    s = sub.add_parser("status", help="Short JSON status")
    s.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
