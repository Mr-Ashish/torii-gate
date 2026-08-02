#!/usr/bin/env python3
"""Own-repo required-check · quieter-over-time path (post-queue product surface).

Buyer story: *the gate gets stricter and quieter over time — not noisier.*

Tools-as-code (no new F-compound loop):
  - own-repo required-check readiness (torii/gate docs + pack + status)
  - **customer vault**: `.torii/runs/{trace_id}/` after pack install (not hub-only)
  - hub dogfood vault: docs/benchmarks/traces (optional on customer repos)
  - chart: docs/benchmarks/quieter-over-time.md (hub) and/or .torii/quieter-over-time.md

Commands:
  report | fixture | status | bootstrap [--demo] | land-dogfood
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
SCHEMA = 2
MARKER = "<!-- torii-quieter-over-time -->"
OUT_MD = Path("docs/benchmarks/quieter-over-time.md")
OUT_JSON = Path("docs/benchmarks/quieter-over-time.json")
CUSTOMER_OUT_MD = Path(".torii/quieter-over-time.md")
CUSTOMER_OUT_JSON = Path(".torii/quieter-over-time.json")
BUYER_DOC = Path("docs/QUIETER.md")
LOCAL_RUNS = Path(".torii/runs")
# Install path-to-value: two labeled demo packs so quieter chart works before first PR
DEMO_EARLY_ID = "demo-early-001"
DEMO_LATE_ID = "demo-late-001"

def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def vault_root(root: Path | None = None) -> Path:
    """Primary vault (env override or hub dogfood traces). Prefer vault_dirs()."""
    env = (os.environ.get("TORII_TRACE_VAULT_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    r = root or _root()
    local = r / LOCAL_RUNS
    hub = r / "docs" / "benchmarks" / "traces"
    # Customer pack: prefer local runs when present
    if local.is_dir() and any(local.iterdir()):
        return local.resolve()
    return hub


def vault_dirs(root: Path | None = None) -> list[tuple[str, Path]]:
    """Ordered vaults: env override · local .torii/runs · hub traces.

    OWN_REPO_QUIETER: customer install measures quieter without hub dogfood archaeology.
    """
    r = root or _root()
    out: list[tuple[str, Path]] = []
    seen: set[Path] = set()

    def _add(kind: str, p: Path) -> None:
        try:
            rp = p.resolve()
        except OSError:
            return
        if rp in seen or not rp.is_dir():
            return
        seen.add(rp)
        out.append((kind, rp))

    env = (os.environ.get("TORII_TRACE_VAULT_ROOT") or "").strip()
    if env:
        _add("env", Path(env))
    _add("local_runs", r / LOCAL_RUNS)
    _add("hub_traces", r / "docs" / "benchmarks" / "traces")
    return out


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


def _parse_summary_md(path: Path) -> dict[str, Any]:
    """Slim pack summary.md → dict (customer .torii/runs)."""
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    out: dict[str, Any] = {}
    m = re.search(r"(?im)^\**Verdict:\**\s*([A-Za-z_ ]+)", text)
    if m:
        out["verdict"] = m.group(1).strip()
    m = re.search(r"(?im)^\**Score:\**\s*(\d+)", text)
    if m:
        out["score"] = int(m.group(1))
    m = re.search(r"(?i)tool[_\s-]?call[_\s-]?turns[:\s]+(\d+)", text)
    if m:
        out["tool_call_turns"] = int(m.group(1))
    m = re.search(r"(?i)path[_\s-]?evidence[:\s]+([0-9.]+)", text)
    if m:
        try:
            out["path_evidence_score"] = float(m.group(1))
        except ValueError:
            pass
    m = re.search(r"(?i)(?:repo|repository)[:\s]+([\w.-]+/[\w.-]+)", text)
    if m:
        out["repo"] = m.group(1)
    m = re.search(r"(?i)\bPR[#\s:-]*(\d{1,7})\b", text)
    if m:
        out["pr"] = m.group(1)
    return out


def collect_dogfood_rows(vroot: Path, *, vault_kind: str = "hub_traces") -> list[dict[str, Any]]:
    """Chronological dogfood / local-run rows with quieter signals."""
    rows: list[dict[str, Any]] = []
    if not vroot.is_dir():
        return rows
    local_pack = vault_kind in ("local_runs", "env") or vroot.name == "runs"

    for d in sorted(vroot.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        summary = _safe_json(d / "summary.json")
        if not summary:
            # slim customer pack may only have summary.md
            summary = _parse_summary_md(d / "summary.md")
        fitness = summary.get("fitness") if isinstance(summary.get("fitness"), dict) else None
        if fitness is None:
            fitness = _safe_json(d / "fitness.json") or None
        critic = _safe_json(d / "second-agent-critic.json")
        cert = _safe_json(d / "gate-certificate.json")
        usage = _safe_json(d / "hermes-usage.json")
        timings = _safe_json(d / "timings.json")
        meta = _safe_json(d / "meta.json")
        is_demo = bool(
            (meta or {}).get("demo")
            or (summary or {}).get("demo")
            or str((meta or {}).get("source") or "").startswith("install-demo")
            or d.name.startswith("demo-")
        )

        repo = str(
            summary.get("repo")
            or meta.get("repo")
            or meta.get("repository")
            or ""
        )
        pr = str(
            summary.get("pr")
            or summary.get("pr_number")
            or meta.get("pr")
            or meta.get("pr_number")
            or ""
        )
        name_l = d.name.lower()
        if not repo and "pytorch" in name_l:
            repo = "pytorch/pytorch"
        if not pr:
            m = re.search(r"pr[#\-]?(\d{4,})", name_l)
            if m:
                pr = m.group(1)

        elapsed = timings.get("total_seconds") if timings else None
        if elapsed is None:
            elapsed = summary.get("elapsed_s") or summary.get("total_seconds") or meta.get("elapsed_s")
        cost = None
        if usage:
            cost = usage.get("estimated_cost_usd")
        if cost is None:
            cost = summary.get("cost_usd") or meta.get("cost_usd")

        verdict = ""
        if isinstance(fitness, dict):
            verdict = str(fitness.get("verdict") or "")
        if not verdict:
            verdict = str(summary.get("verdict") or meta.get("verdict") or "")
        if not verdict and cert:
            verdict = str(cert.get("verdict") or "")
        # parse review.md if still empty (slim pack)
        if not verdict:
            for rev_name in ("review.md", "summary.md"):
                rp = d / rev_name
                if rp.is_file():
                    try:
                        rt = rp.read_text(encoding="utf-8", errors="replace")[:4000]
                    except OSError:
                        rt = ""
                    m = re.search(r"(?im)^\**Verdict:\**\s*([A-Za-z_ ]+)", rt)
                    if m:
                        verdict = m.group(1).strip()
                        break
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
            local_pack
            or repo
            or re.search(r"pytorch|pr\d{3,}|modal-", name_l)
            or (elapsed is not None and verdict_n != "UNKNOWN")
        )
        if not is_dogfood:
            continue
        if not any([repo, pr, elapsed, cost, verdict_n != "UNKNOWN", cert, local_pack]):
            continue
        # local pack: need at least a verdict or meta signal
        if local_pack and verdict_n == "UNKNOWN" and not any([repo, pr, cert, tools is not None]):
            continue

        # skip pure feature-lab folders without live signal (hub vault only)
        if not local_pack and name_l.startswith("f") and not any(
            x in name_l for x in ("pytorch", "modal", "dogfood", "live")
        ):
            # allow fNN* only if summary has repo/pr
            if not (repo and pr):
                continue

        rows.append(
            {
                "trace_id": d.name,
                "repo": repo or ("local" if local_pack else ""),
                "pr": pr,
                "verdict": verdict_n,
                "time_to_signal_s": float(elapsed) if isinstance(elapsed, (int, float)) else None,
                "cost_usd": float(cost) if isinstance(cost, (int, float)) else None,
                "path_evidence": path_ev,
                "tool_call_turns": int(tools) if isinstance(tools, (int, float)) else None,
                "has_certificate": bool(cert and (cert.get("certificate_id") or cert.get("verdict"))),
                "certificate_id": (cert or {}).get("certificate_id"),
                "demoted": demoted,
                "weak_approve": weak_approve,
                "demo": is_demo,
                "block": summary.get("block") if "block" in summary else (cert or {}).get("block"),
                "host": str(
                    summary.get("host")
                    or meta.get("host")
                    or (
                        "demo"
                        if is_demo
                        else ("local_pack" if local_pack else ("modal" if "modal" in name_l else "local"))
                    )
                ),
                "model": str(summary.get("model") or meta.get("model") or (usage or {}).get("model") or ""),
                "vault": vault_kind,
            }
        )
    return rows


def collect_all_rows(root: Path | None = None) -> list[dict[str, Any]]:
    """Merge local .torii/runs + hub traces (dedupe by trace_id, prefer local)."""
    root = root or _root()
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for kind, vdir in vault_dirs(root):
        for row in collect_dogfood_rows(vdir, vault_kind=kind):
            tid = str(row.get("trace_id") or "")
            if not tid:
                continue
            if tid in by_id:
                # prefer local_runs over hub when same id
                prev = by_id[tid]
                if prev.get("vault") == "local_runs" and kind != "local_runs":
                    continue
            else:
                order.append(tid)
            by_id[tid] = row
    return [by_id[t] for t in order]


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
        "pack_caller": (root / "pack" / "torii-pr-review-caller.yml").is_file()
        or (root / ".github" / "workflows" / "torii-pr-review.yml").is_file(),
        "gate_status_script": (root / "scripts" / "torii_gate_status.py").is_file(),
        "gate_certificate_script": (root / "scripts" / "gate_certificate.py").is_file(),
        "quieter_script": (root / "scripts" / "quieter_over_time.py").is_file(),
        "torii_cli": (root / "scripts" / "torii.py").is_file(),
        "smoke_script": (root / "scripts" / "smoke-torii-gate.sh").is_file(),
        "local_runs_parent": True,  # .torii/runs created on first report/publish
        "branch_protection_named": False,
        "required_context_torii_gate": False,
        "customer_path_documented": False,
    }
    # docs must name branch protection + torii/gate
    for rel in ("docs/GOLDEN-PATH.md", "docs/GATE.md", str(BUYER_DOC), "docs/INSTALL.md"):
        p = root / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        if re.search(r"branch protection", text, re.I):
            checks["branch_protection_named"] = True
        if "torii/gate" in text:
            checks["required_context_torii_gate"] = True
        if re.search(r"\.torii/runs|local.?runs|customer vault", text, re.I):
            checks["customer_path_documented"] = True

    ok_n = sum(1 for v in checks.values() if v)
    total = len(checks)
    # pack_ok: customer target after install may lack hub docs — scripts + workflow enough
    pack_ok = bool(
        checks["gate_status_script"]
        and checks["quieter_script"]
        and checks["torii_cli"]
        and checks["pack_caller"]
    )
    hub_ok = ok_n == total
    return {
        "checks": checks,
        "ok_n": ok_n,
        "total": total,
        "ok": hub_ok or pack_ok,
        "hub_docs_ok": hub_ok,
        "pack_surface_ok": pack_ok,
        "required_check": "torii/gate",
        "one_liner": (
            "install pack → require torii/gate → reviews land in .torii/runs → quieter chart"
        ),
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


def window_source_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Prefer organic/hub for quiet trajectory; fall back to labeled demo only.

    Honesty: install-demo packs prove the vault path works; they do not claim
    customer PR quieter-over-time when real dogfood/hub rows exist.
    """
    organic = [r for r in rows if not r.get("demo")]
    if len(organic) >= 1:
        return organic, "measured"
    demos = [r for r in rows if r.get("demo")]
    if demos:
        return demos, "demo"
    return rows, "measured"


def build_report(root: Path) -> dict[str, Any]:
    rows = collect_all_rows(root)
    traj_rows, traj_source = window_source_rows(rows)
    windows = split_windows(traj_rows)
    windows["trajectory_source"] = traj_source
    own = own_repo_required_check(root)
    tools_q = tool_use_quality(traj_rows if traj_rows else rows)
    late = windows.get("late") or {}
    all_w = windows.get("all") or {}
    vaults = [{"kind": k, "path": str(p)} for k, p in vault_dirs(root)]
    local_n = sum(1 for r in rows if r.get("vault") == "local_runs")
    local_demo_n = sum(1 for r in rows if r.get("vault") == "local_runs" and r.get("demo"))
    local_organic_n = local_n - local_demo_n
    hub_n = sum(1 for r in rows if r.get("vault") == "hub_traces")

    n_rows = int(all_w.get("n") or 0)
    # quieter_ok: own-repo surface ready AND (measured trajectory OR hub legacy OR demo vault)
    quieter_ok = bool(
        own.get("ok")
        and n_rows >= 1
        and (
            windows.get("getting_quieter") is not False
            or (all_w.get("quiet_score") or 0) >= 0.35
            or tools_q.get("quality_ok")
            or local_n >= 1
        )
    )

    return {
        "feature": FEATURE,
        "schema_version": SCHEMA,
        "at": _now(),
        "one_liner": (
            "Own-repo required check torii/gate + quieter chart from .torii/runs "
            "(customer) and/or hub dogfood vault"
        ),
        "scorecard_target": "JTBD / simplicity (dims 3 + 12)",
        "dim_lift": "stricter-and-quieter path measured tools-as-code on own repo",
        "required_check": "torii/gate",
        "own_repo": own,
        "dogfood_n": len(traj_rows),
        "local_runs_n": local_n,
        "local_demo_n": local_demo_n,
        "local_organic_n": local_organic_n,
        "hub_traces_n": hub_n,
        "trajectory_source": traj_source,
        "vaults": vaults,
        "windows": windows,
        "tool_use_quality": tools_q,
        "quieter_ok": quieter_ok,
        "recent_rows": rows[-12:],
        "paths": {
            "md": str(OUT_MD),
            "json": str(OUT_JSON),
            "customer_md": str(CUSTOMER_OUT_MD),
            "customer_json": str(CUSTOMER_OUT_JSON),
            "local_runs": str(LOCAL_RUNS),
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
        "    → @torii review → runs land in .torii/runs/ → quieter chart (this file)",
        "```",
        "",
        "Buyer doc: [`docs/QUIETER.md`](../QUIETER.md) · Golden path: [`GOLDEN-PATH.md`](../GOLDEN-PATH.md)",
        "",
        "## Vaults (customer + hub)",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| local `.torii/runs` rows | {report.get('local_runs_n')} |",
        f"| hub dogfood rows | {report.get('hub_traces_n')} |",
        f"| total rows | {report.get('dogfood_n')} |",
        "",
        "Customer repos measure quieter from **`.torii/runs/`** after pack install — no hub clone required.",
        "",
        "## Own-repo required-check readiness",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| checks ok | {own.get('ok_n')}/{own.get('total')} |",
        f"| own_repo_ok | {own.get('ok')} |",
        f"| pack_surface_ok | {own.get('pack_surface_ok')} |",
        f"| hub_docs_ok | {own.get('hub_docs_ok')} |",
        "",
        "| Check | Pass |",
        "|-------|:----:|",
    ]
    for k, v in checks.items():
        lines.append(f"| `{k}` | {'yes' if v else 'no'} |")

    lines += [
        "",
        "## Trajectory (early → late)",
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
        "## Cost / time (all rows)",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| cost/PR mean USD | {all_w.get('cost_usd_mean')} (n={all_w.get('cost_n')}) |",
        f"| time-to-signal mean s | {all_w.get('time_to_signal_mean')} |",
        "",
        "## Recent rows",
        "",
        "| trace | vault | repo | pr | verdict | tools | path_ev | cert | weak_appr |",
        "|-------|-------|------|---:|---------|------:|--------:|:----:|:---------:|",
    ]
    for r in rows[-12:]:
        lines.append(
            f"| `{r.get('trace_id', '')[:40]}` | {r.get('vault')} | {r.get('repo')} | {r.get('pr')} | "
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
        "# customer pack also writes .torii/quieter-over-time.md",
        "```",
        "",
    ]
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    md_body = render_markdown(report)
    js_body = json.dumps(report, indent=2) + "\n"
    wrote: list[str] = []

    # Hub chart path when docs/benchmarks exists (or always try)
    md_path = root / OUT_MD
    js_path = root / OUT_JSON
    try:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_body, encoding="utf-8")
        js_path.write_text(js_body, encoding="utf-8")
        wrote.append(str(OUT_MD))
        wrote.append(str(OUT_JSON))
    except OSError:
        pass

    # Customer pack path — always when .torii exists or we can create it
    cust_md = root / CUSTOMER_OUT_MD
    cust_js = root / CUSTOMER_OUT_JSON
    try:
        cust_md.parent.mkdir(parents=True, exist_ok=True)
        (root / LOCAL_RUNS).mkdir(parents=True, exist_ok=True)
        cust_md.write_text(md_body, encoding="utf-8")
        cust_js.write_text(js_body, encoding="utf-8")
        wrote.append(str(CUSTOMER_OUT_MD))
        wrote.append(str(CUSTOMER_OUT_JSON))
    except OSError:
        pass

    report["wrote"] = wrote
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
    else:
        print(md_body)
        print(f"\n# wrote {', '.join(wrote)}", file=sys.stderr)
    return 0 if report.get("quieter_ok") or getattr(args, "allow_partial", False) else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic readiness: own-repo checks + local .torii/runs collection (no live hub required)."""
    import tempfile

    root = _root()
    own = own_repo_required_check(root)
    script_ok = (root / "scripts" / "quieter_over_time.py").is_file()
    core_ok = bool(
        own.get("checks", {}).get("golden_path_doc")
        and own.get("checks", {}).get("gate_doc")
        and own.get("checks", {}).get("install_script")
        and own.get("checks", {}).get("gate_status_script")
        and own.get("checks", {}).get("quieter_script")
        and own.get("checks", {}).get("branch_protection_named")
        and own.get("checks", {}).get("required_context_torii_gate")
        and own.get("checks", {}).get("customer_path_documented")
        and script_ok
    )
    buyer_ok = (root / BUYER_DOC).is_file()

    # Hermetic customer vault: temp .torii/runs with two synthetic slim packs
    local_collect_ok = False
    local_n = 0
    try:
        with tempfile.TemporaryDirectory(prefix="torii-quieter-") as td:
            fake = Path(td)
            runs = fake / ".torii" / "runs"
            for i, (verdict, tools, pe) in enumerate(
                (
                    ("APPROVE", 0, 0.2),
                    ("REQUEST_CHANGES", 3, 0.9),
                ),
                start=1,
            ):
                d = runs / f"run-local-{i:03d}"
                d.mkdir(parents=True)
                (d / "meta.json").write_text(
                    json.dumps(
                        {
                            "repo": "acme/app",
                            "pr": str(100 + i),
                            "verdict": verdict,
                            "elapsed_s": 60 + i * 10,
                            "host": "gha",
                        }
                    ),
                    encoding="utf-8",
                )
                (d / "summary.md").write_text(
                    f"**Verdict:** {verdict}\n"
                    f"tool_call_turns: {tools}\n"
                    f"path_evidence: {pe}\n"
                    f"repo: acme/app\nPR: {100 + i}\n",
                    encoding="utf-8",
                )
            rows = collect_all_rows(fake)
            local_n = len(rows)
            local_collect_ok = local_n >= 2 and all(
                r.get("vault") == "local_runs" for r in rows
            )
            # late should prefer higher path evidence run
            win = split_windows(rows)
            _ = win.get("getting_quieter")
    except OSError:
        local_collect_ok = False

    install_ships_quieter = False
    inst = root / "scripts" / "install-torii.sh"
    if inst.is_file():
        it = inst.read_text(encoding="utf-8")
        install_ships_quieter = "quieter_over_time.py" in it

    fixture_pass = bool(
        core_ok and buyer_ok and local_collect_ok and install_ships_quieter
    )
    out = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "fixture_pass": fixture_pass,
        "core_ok": core_ok,
        "buyer_doc_ok": buyer_ok,
        "local_collect_ok": local_collect_ok,
        "local_fixture_n": local_n,
        "install_ships_quieter": install_ships_quieter,
        "own_repo_ok_n": own.get("ok_n"),
        "own_repo_total": own.get("total"),
        "pack_surface_ok": own.get("pack_surface_ok"),
        "required_check": "torii/gate",
        "scorecard_target": "JTBD / simplicity",
        "dim_lift": "own-repo quieter from .torii/runs after pack install",
    }
    print(json.dumps(out, indent=2))
    return 0 if fixture_pass else 1


def seed_demo_local_runs(root: Path, *, force: bool = False) -> dict[str, Any]:
    """Write two labeled install-demo slim packs (early weak → late strong).

    Path-to-value: after install, quieter -- status shows local_runs_n≥1 and an
    offline chart works without waiting for the first real PR. Packs carry
    demo=true so organic quieter claims stay honest.
    """
    runs = root / LOCAL_RUNS
    runs.mkdir(parents=True, exist_ok=True)
    # Skip if organic (non-demo) local packs already present unless force
    organic = []
    for d in runs.iterdir() if runs.is_dir() else []:
        if not d.is_dir() or d.name.startswith("."):
            continue
        meta = _safe_json(d / "meta.json")
        if meta.get("demo") or d.name.startswith("demo-"):
            continue
        organic.append(d.name)
    if organic and not force:
        return {
            "seeded": False,
            "reason": "organic_local_runs_present",
            "organic_n": len(organic),
            "wrote": [],
        }

    packs = [
        (
            DEMO_EARLY_ID,
            {
                "repo": "acme/app",
                "pr": "101",
                "verdict": "APPROVE",
                "elapsed_s": 120,
                "host": "demo",
                "demo": True,
                "source": "install-demo",
                "path_evidence_score": 0.2,
                "tool_call_turns": 0,
                "cost_usd": 0.01,
            },
            (
                "**Verdict:** APPROVE\n"
                "tool_call_turns: 0\n"
                "path_evidence: 0.2\n"
                "repo: acme/app\n"
                "PR: 101\n"
                "demo: true\n"
                "source: install-demo (early / noisy)\n"
            ),
            (
                "# Demo review (early)\n\n"
                "**Verdict:** APPROVE\n\n"
                "_Install demo only — weak path evidence, zero tools. "
                "Not a customer PR._\n"
            ),
        ),
        (
            DEMO_LATE_ID,
            {
                "repo": "acme/app",
                "pr": "102",
                "verdict": "REQUEST_CHANGES",
                "elapsed_s": 95,
                "host": "demo",
                "demo": True,
                "source": "install-demo",
                "path_evidence_score": 0.9,
                "tool_call_turns": 4,
                "cost_usd": 0.012,
            },
            (
                "**Verdict:** REQUEST_CHANGES\n"
                "tool_call_turns: 4\n"
                "path_evidence: 0.9\n"
                "repo: acme/app\n"
                "PR: 102\n"
                "demo: true\n"
                "source: install-demo (late / quieter)\n"
            ),
            (
                "# Demo review (late)\n\n"
                "**Verdict:** REQUEST_CHANGES\n\n"
                "_Install demo only — path-evidenced finding, tools used. "
                "Not a customer PR._\n"
            ),
        ),
    ]
    wrote: list[str] = []
    for tid, meta, summary_md, review_md in packs:
        d = runs / tid
        if d.is_dir() and not force:
            # already seeded
            continue
        d.mkdir(parents=True, exist_ok=True)
        (d / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        (d / "summary.md").write_text(summary_md, encoding="utf-8")
        (d / "review.md").write_text(review_md, encoding="utf-8")
        wrote.append(tid)
    return {
        "seeded": bool(wrote) or all((runs / t).is_dir() for t in (DEMO_EARLY_ID, DEMO_LATE_ID)),
        "reason": "ok" if wrote else "already_present",
        "wrote": wrote,
        "demo_ids": [DEMO_EARLY_ID, DEMO_LATE_ID],
    }


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    win = report.get("windows") or {}
    own = report.get("own_repo") or {}
    local_n = int(report.get("local_runs_n") or 0)
    local_demo_n = int(report.get("local_demo_n") or 0)
    local_organic_n = int(report.get("local_organic_n") or 0)
    runs_readme = (root / LOCAL_RUNS / "README.md").is_file()
    # Vault empty only when neither demo nor organic packs exist
    bootstrap_needed = local_n < 1
    organic_needed = local_organic_n < 1
    if bootstrap_needed:
        hint = (
            "quieter -- bootstrap --demo  →  require torii/gate  →  "
            "@torii review  →  .torii/runs fills"
        )
    elif organic_needed:
        hint = (
            f"demo vault only (local_demo_n={local_demo_n}) · "
            "require torii/gate → @torii review  OR  quieter -- land-dogfood"
        )
    else:
        hint = "local vault has organic runs · quieter chart ready"
    slim = {
        "feature": FEATURE,
        "quieter_ok": report.get("quieter_ok"),
        "required_check": report.get("required_check"),
        "own_repo_ok": own.get("ok"),
        "pack_surface_ok": own.get("pack_surface_ok"),
        "dogfood_n": report.get("dogfood_n"),
        "local_runs_n": local_n,
        "local_demo_n": local_demo_n,
        "local_organic_n": local_organic_n,
        "hub_traces_n": report.get("hub_traces_n"),
        "trajectory_source": report.get("trajectory_source"),
        "quiet_score_all": (win.get("all") or {}).get("quiet_score"),
        "delta_quiet_score": win.get("delta_quiet_score"),
        "getting_quieter": win.get("getting_quieter"),
        "tool_use_quality_ok": (report.get("tool_use_quality") or {}).get("quality_ok"),
        "customer_vault_readme": runs_readme,
        "bootstrap_needed": bootstrap_needed,
        "organic_needed": organic_needed,
        "bootstrap_hint": hint,
        "at": report.get("at"),
    }
    print(json.dumps(slim, indent=2))
    return 0 if report.get("quieter_ok") else 1


def _parse_summary_md_file(path: Path) -> dict[str, Any]:
    """Best-effort parse of SUMMARY.md fire notes (Modal e2e tags)."""
    out: dict[str, Any] = {}
    if not path.is_file():
        return out
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:8000]
    except OSError:
        return out
    m = re.search(r"pytorch#(\d+)", text, re.I)
    if m:
        out["pr"] = m.group(1)
        out["repo"] = "pytorch/pytorch"
    m = re.search(r"tool_call_turns\s*=\s*(\d+)", text, re.I)
    if m:
        out["tool_call_turns"] = int(m.group(1))
    m = re.search(r"elapsed_s[≈~=]*\s*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        out["elapsed_s"] = float(m.group(1))
    m = re.search(r"\b(APPROVE|REQUEST_CHANGES|COMMENT)\b", text)
    if m:
        out["verdict"] = m.group(1)
    m = re.search(r"https://modal\.com/apps/[^\s)]+", text)
    if m:
        out["modal_app"] = m.group(0).rstrip(".,;")
    return out


def _pick_hub_trace(root: Path, explicit: str | None = None) -> Path | None:
    """Pick a hub dogfood trace dir with enough signal to land as organic local pack."""
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = (root / p).resolve()
        return p if p.is_dir() else None
    hub = root / "docs" / "benchmarks" / "traces"
    if not hub.is_dir():
        return None
    candidates: list[tuple[float, Path]] = []
    for d in hub.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        name_l = d.name.lower()
        # Prefer live modal pytorch dogfood over pure feature labs
        score = 0.0
        if "modal" in name_l:
            score += 2
        if "pytorch" in name_l:
            score += 2
        if (d / "summary.json").is_file():
            score += 3
        if (d / "review.md").is_file() or list(d.glob("review-*.md")):
            score += 2
        if (d / "SUMMARY.md").is_file():
            score += 1
        if (d / "meta.json").is_file():
            score += 0.5
        if (d / "gate-certificate.json").is_file():
            score += 1
        if score < 3:
            continue
        try:
            mtime = d.stat().st_mtime
        except OSError:
            mtime = 0.0
        candidates.append((score * 1e12 + mtime, d))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def land_dogfood_pack(
    root: Path,
    *,
    trace_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Land one hub dogfood / Modal trace as an **organic** local slim pack.

    Honesty: demo=false · source=land-dogfood · host/modal preserved.
    Closes organic_needed for hub maintainers and proves the customer vault path
    after FS publish without inventing partner PRs.
    """
    src = trace_dir or _pick_hub_trace(root)
    if src is None or not src.is_dir():
        return {
            "landed": False,
            "reason": "no_hub_trace",
            "hint": "pass --trace docs/benchmarks/traces/<fire-tag>",
        }

    summary = _safe_json(src / "summary.json")
    meta_src = _safe_json(src / "meta.json")
    usage = _safe_json(src / "hermes-usage.json")
    cert = _safe_json(src / "gate-certificate.json")
    timings = _safe_json(src / "timings.json")
    fire = _parse_summary_md_file(src / "SUMMARY.md")

    # review body
    review_text = ""
    for rp in [src / "review.md", *sorted(src.glob("review-*.md"))]:
        if rp.is_file():
            try:
                review_text = rp.read_text(encoding="utf-8", errors="replace")[:12000]
            except OSError:
                review_text = ""
            if review_text.strip():
                break
    if not review_text and (src / "SUMMARY.md").is_file():
        try:
            review_text = (src / "SUMMARY.md").read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            review_text = ""

    repo = str(
        summary.get("repo")
        or meta_src.get("repo")
        or fire.get("repo")
        or ""
    )
    pr = str(
        summary.get("pr")
        or summary.get("pr_number")
        or meta_src.get("pr")
        or fire.get("pr")
        or ""
    )
    if not repo and "pytorch" in src.name.lower():
        repo = "pytorch/pytorch"
    if not pr:
        m = re.search(r"pr[#\-]?(\d{4,})", src.name.lower())
        if m:
            pr = m.group(1)

    verdict = str(
        summary.get("verdict")
        or meta_src.get("verdict")
        or (cert or {}).get("verdict")
        or fire.get("verdict")
        or ""
    )
    if not verdict and review_text:
        m = re.search(r"(?im)^\**Verdict:\**\s*([A-Za-z_ ]+)", review_text)
        if m:
            verdict = m.group(1).strip()
    verdict_n = _norm_verdict(verdict) if verdict else "UNKNOWN"

    tools = summary.get("tool_call_turns")
    if tools is None:
        tools = meta_src.get("tool_call_turns") or fire.get("tool_call_turns")
    elapsed = summary.get("elapsed_s") or meta_src.get("elapsed_s") or fire.get("elapsed_s")
    if elapsed is None and timings:
        elapsed = timings.get("total_seconds")
    cost = summary.get("cost_usd")
    if cost is None and usage:
        cost = usage.get("estimated_cost_usd")
    if cost is None:
        cost = meta_src.get("cost_usd")
    path_ev = summary.get("path_evidence_score")
    if path_ev is None and cert:
        path_ev = cert.get("path_evidence_score")
    if path_ev is None and isinstance(summary.get("path_evidence"), (int, float)):
        path_ev = summary.get("path_evidence")

    # Need a usable signal — refuse empty landings
    if verdict_n == "UNKNOWN" and tools is None and not review_text.strip():
        return {
            "landed": False,
            "reason": "trace_too_thin",
            "trace": str(src),
            "hint": "need summary.json or review.md with verdict/tools",
        }

    tid = f"landed-{src.name}"[:120]
    # shorten very long names
    if len(tid) > 90:
        tid = f"landed-{src.name[-80:]}"

    runs = root / LOCAL_RUNS
    runs.mkdir(parents=True, exist_ok=True)
    dest = runs / tid
    if dest.is_dir() and not force:
        return {
            "landed": False,
            "reason": "already_present",
            "trace_id": tid,
            "dest": str(dest.relative_to(root)) if dest.is_relative_to(root) else str(dest),
        }

    dest.mkdir(parents=True, exist_ok=True)
    meta = {
        "repo": repo or "unknown/repo",
        "pr": pr,
        "verdict": verdict_n,
        "elapsed_s": float(elapsed) if isinstance(elapsed, (int, float)) else None,
        "tool_call_turns": int(tools) if isinstance(tools, (int, float)) else None,
        "cost_usd": float(cost) if isinstance(cost, (int, float)) else None,
        "path_evidence_score": float(path_ev) if isinstance(path_ev, (int, float)) else None,
        "host": str(summary.get("host") or meta_src.get("host") or "modal"),
        "model": str(summary.get("model") or meta_src.get("model") or ""),
        "demo": False,
        "source": "land-dogfood",
        "hub_trace": src.name,
        "certificate_id": (cert or {}).get("certificate_id") or summary.get("certificate_id"),
        "modal_app": fire.get("modal_app") or summary.get("modal_run") or meta_src.get("modal_app"),
        "landed_at": _now(),
    }
    # drop nulls for cleaner packs
    meta = {k: v for k, v in meta.items() if v is not None and v != ""}

    summary_md = (
        f"**Verdict:** {verdict_n}\n"
        f"tool_call_turns: {meta.get('tool_call_turns', '—')}\n"
        f"path_evidence: {meta.get('path_evidence_score', '—')}\n"
        f"repo: {meta.get('repo')}\n"
        f"PR: {meta.get('pr')}\n"
        f"elapsed_s: {meta.get('elapsed_s', '—')}\n"
        f"cost_usd: {meta.get('cost_usd', '—')}\n"
        f"demo: false\n"
        f"source: land-dogfood\n"
        f"hub_trace: {src.name}\n"
    )
    if not review_text.strip():
        review_text = (
            f"# Landed dogfood pack\n\n"
            f"**Verdict:** {verdict_n}\n\n"
            f"_Organic local pack from hub dogfood `{src.name}` "
            f"(source=land-dogfood). Not install-demo._\n"
        )

    (dest / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (dest / "summary.md").write_text(summary_md, encoding="utf-8")
    (dest / "review.md").write_text(review_text, encoding="utf-8")
    # optional: copy certificate if present (path evidence)
    if cert and (src / "gate-certificate.json").is_file():
        try:
            (dest / "gate-certificate.json").write_text(
                json.dumps(cert, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass

    try:
        dest_rel = str(dest.relative_to(root))
        src_rel = str(src.relative_to(root)) if src.is_relative_to(root) else str(src)
    except ValueError:
        dest_rel = str(dest)
        src_rel = str(src)

    return {
        "landed": True,
        "reason": "ok",
        "trace_id": tid,
        "dest": dest_rel,
        "hub_trace": src_rel,
        "verdict": verdict_n,
        "tool_call_turns": meta.get("tool_call_turns"),
        "repo": meta.get("repo"),
        "pr": meta.get("pr"),
        "demo": False,
        "source": "land-dogfood",
        "one_liner": (
            f"Landed organic local pack from hub dogfood · "
            f"{meta.get('repo')}#{meta.get('pr')} · {verdict_n}"
        ),
    }


def cmd_land_dogfood(args: argparse.Namespace) -> int:
    """CLI: land hub dogfood into .torii/runs as organic (closes organic_needed)."""
    root = _root()
    explicit = getattr(args, "trace", None) or None
    src = _pick_hub_trace(root, explicit)
    result = land_dogfood_pack(
        root,
        trace_dir=src,
        force=bool(getattr(args, "force", False)),
    )
    # refresh organic counts for operator
    report = build_report(root) if result.get("landed") or result.get("reason") == "already_present" else {}
    out = {
        "feature": FEATURE,
        **result,
        "local_runs_n": report.get("local_runs_n"),
        "local_demo_n": report.get("local_demo_n"),
        "local_organic_n": report.get("local_organic_n"),
        "organic_needed": (
            int(report.get("local_organic_n") or 0) < 1 if report else None
        ),
        "at": _now(),
    }
    print(json.dumps(out, indent=2))
    return 0 if result.get("landed") or result.get("reason") == "already_present" else 1


def cmd_bootstrap(args: argparse.Namespace) -> int:
    """Ensure customer .torii/runs vault + README (+ optional demo packs)."""
    root = _root()
    runs = root / LOCAL_RUNS
    runs.mkdir(parents=True, exist_ok=True)
    gitkeep = runs / ".gitkeep"
    if not gitkeep.is_file():
        gitkeep.write_text("", encoding="utf-8")
    readme = runs / "README.md"
    wrote = False
    if not readme.is_file() or getattr(args, "force", False):
        readme.write_text(
            "# Torii run vault (customer quieter path)\n\n"
            "Slim packs land here after each gate review: "
            "`{trace_id}/meta.json` · `summary.md` · `review.md`.\n\n"
            "Install seeds **labeled demo** packs (`demo-*-001`, `demo: true`) so "
            "`quieter -- status` works offline; organic packs after "
            "`torii/gate` reviews or hub `quieter -- land-dogfood`.\n\n"
            "```bash\n"
            "python3 scripts/torii.py quieter -- status\n"
            "python3 scripts/torii.py quieter -- report\n"
            "python3 scripts/torii.py quieter -- bootstrap --demo\n"
            "python3 scripts/torii.py quieter -- land-dogfood\n"
            "```\n\n"
            "First organic fill: require **torii/gate** · `@torii review this pr` · "
            "re-check status (`local_organic_n`). Hub maintainers: `land-dogfood`.\n"
            "Docs: docs/QUIETER.md\n",
            encoding="utf-8",
        )
        wrote = True
    # Default: seed demo packs on bootstrap (path-to-value). --no-demo skips.
    seed: dict[str, Any] = {"seeded": False, "wrote": [], "reason": "skipped"}
    want_demo = not getattr(args, "no_demo", False)
    if want_demo or getattr(args, "demo", False):
        seed = seed_demo_local_runs(root, force=bool(getattr(args, "force", False)))
    try:
        runs_rel = str(runs.relative_to(root))
        readme_rel = str(readme.relative_to(root))
    except ValueError:
        runs_rel = str(runs)
        readme_rel = str(readme)
    demo_n = sum(
        1
        for d in runs.iterdir()
        if d.is_dir() and (d.name.startswith("demo-") or (_safe_json(d / "meta.json") or {}).get("demo"))
    )
    out = {
        "feature": FEATURE,
        "bootstrap_ok": True,
        "runs_dir": runs_rel,
        "readme": readme_rel,
        "wrote_readme": wrote,
        "demo_seed": seed,
        "local_demo_n": demo_n,
        "one_liner": (
            "Customer quieter vault ready — demo packs prove path; "
            "require torii/gate for organic quieter"
            if demo_n
            else "Customer quieter vault ready — require torii/gate and run a review"
        ),
        "at": _now(),
    }
    print(json.dumps(out, indent=2))
    return 0


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

    b = sub.add_parser(
        "bootstrap",
        help="Seed .torii/runs README + labeled demo packs (path-to-value)",
    )
    b.add_argument("--force", action="store_true", help="Overwrite README / re-seed demo")
    b.add_argument(
        "--demo",
        action="store_true",
        default=True,
        help="Seed labeled demo packs (default on)",
    )
    b.add_argument(
        "--no-demo",
        action="store_true",
        help="README only — skip install-demo packs",
    )
    b.set_defaults(func=cmd_bootstrap)

    ld = sub.add_parser(
        "land-dogfood",
        help="Land hub Modal dogfood into .torii/runs as organic (closes organic_needed)",
    )
    ld.add_argument(
        "--trace",
        default=None,
        help="Hub trace dir (default: best recent docs/benchmarks/traces/*)",
    )
    ld.add_argument("--force", action="store_true", help="Overwrite existing landed pack")
    ld.set_defaults(func=cmd_land_dogfood)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
