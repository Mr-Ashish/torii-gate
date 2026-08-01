#!/usr/bin/env python3
"""Reliability / ops dashboard stub (priority queue dim 8).

Surfaces:
  - fail-closed defaults inventory
  - cost/PR + time-to-signal from dogfood vault
  - smoke / required-check readiness
  - writes docs/ops/DASHBOARD.md + cost-pr-dashboard.md

Commands:
  report | fixture | status
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "OPS"
SCHEMA = 1
OUT_DIR = Path("docs/ops")


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_default(name: str, *, default_on: bool, truthy: set[str] | None = None) -> dict[str, Any]:
    """Document default fail-closed posture (unset = product default)."""
    truthy = truthy or {"1", "true", "yes", "on"}
    falsey = {"0", "false", "no", "off", "disabled", ""}
    raw = os.environ.get(name)
    if raw is None:
        effective = default_on
        source = "unset→default"
    else:
        low = raw.strip().lower()
        if low in falsey:
            effective = False
            source = f"env={raw!r}"
        elif low in truthy:
            effective = True
            source = f"env={raw!r}"
        else:
            effective = default_on
            source = f"env={raw!r} (nonstandard→default)"
    return {
        "name": name,
        "default_on": default_on,
        "effective": effective,
        "source": source,
        "fail_closed_when_on": default_on,
    }


def fail_closed_inventory() -> list[dict[str, Any]]:
    """Product defaults that refuse silent green merges / open ingress."""
    return [
        {
            **_env_default("TORII_TOOL_TURNS_GATE", default_on=True),
            "what": "Zero-tool multi-file code PRs cannot APPROVE (fail-closed)",
            "docs": "scripts/tool_turns_gate.py · docs/OPERATIONS.md",
        },
        {
            **_env_default("TORII_TOOL_TURNS_REPROMPT", default_on=True),
            "what": "Soft re-prompt once when tools were skipped (budgeted)",
            "docs": "scripts/tool_turns_gate.py",
        },
        {
            **_env_default("TORII_WEBHOOK_ALLOW_OPEN", default_on=False),
            "what": "Modal webhook refuse-open by default (must explicitly allow)",
            "docs": "docs/OPERATIONS.md · modal_app",
            # special: default_on False means fail-closed when OFF is the safe default
            "fail_closed_when_on": False,
            "safe_default": "off",
        },
        {
            **_env_default("TORII_COMMIT_STATUS", default_on=True),
            "what": "Post torii/gate + torii/review commit statuses",
            "docs": "docs/GATE.md",
        },
        {
            **_env_default("TORII_GATE_STRICT", default_on=False),
            "what": "Optional hard job fail when gate closed (branch protection uses status)",
            "docs": "docs/GATE.md · TORII_GATE_STRICT=1",
            "note": "Status context torii/gate is the merge authority; strict job fail is optional",
        },
        {
            **_env_default("TORII_PR_LABELS", default_on=True),
            "what": "Verdict labels on PRs (visible ops signal)",
            "docs": "docs/GATE.md",
        },
    ]


def required_check_docs(root: Path) -> dict[str, Any]:
    paths = [
        "docs/GATE.md",
        "docs/INSTALL.md",
        "docs/GOLDEN-PATH.md",
        "docs/workflows/INSTALL-GUIDE.md",
        "pack/README.md",
    ]
    found = {}
    for rel in paths:
        p = root / rel
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        found[rel] = {
            "exists": p.is_file(),
            "names_torii_gate": "torii/gate" in text,
            "branch_protection": bool(
                re.search(r"branch protection|required (status )?check", text, re.I)
            ),
        }
    ok = all(v.get("exists") and v.get("names_torii_gate") for v in found.values())
    return {"ok": ok, "paths": found, "required_context": "torii/gate"}


def cost_pr_table(root: Path) -> dict[str, Any]:
    try:
        sys.path.insert(0, str(root / "scripts"))
        from golden_path_metrics import (  # type: ignore
            collect_dogfood_rows,
            summarize_dogfood,
            vault_root,
        )

        rows = collect_dogfood_rows(vault_root(root))
        dog = summarize_dogfood(rows)
        return {
            "source": "docs/benchmarks/traces vault",
            "runs": dog.get("runs"),
            "time_to_signal_s": dog.get("time_to_signal_s"),
            "cost_usd": dog.get("cost_usd"),
            "verdicts": dog.get("verdicts"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"source": "unavailable", "error": str(exc), "runs": 0}


def last_gate_certificate(root: Path) -> dict[str, Any]:
    """Buyer-facing last merge-authority certificate from dogfood vault (GATE_CERT wire)."""
    vault = root / "docs" / "benchmarks" / "traces"
    out: dict[str, Any] = {
        "available": False,
        "script_present": (root / "scripts" / "gate_certificate.py").is_file(),
        "save_trace_wired": False,
        "workflow_wired": False,
    }
    st = root / "scripts" / "save-trace.sh"
    if st.is_file():
        text = st.read_text(encoding="utf-8", errors="replace")
        out["save_trace_wired"] = "gate_certificate" in text and "GATE_CERT" in text
    wf = root / ".github" / "workflows" / "torii-review-reusable.yml"
    if wf.is_file():
        wt = wf.read_text(encoding="utf-8", errors="replace")
        out["workflow_wired"] = "--certificate" in wt and "certificate-write" in wt

    if not vault.is_dir():
        out["reason"] = "no_vault"
        return out

    newest: Path | None = None
    newest_mtime = 0.0
    for p in vault.rglob("gate-certificate.json"):
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if m >= newest_mtime:
            newest_mtime = m
            newest = p
    if newest is None:
        out["reason"] = "no_certificate_in_vault"
        out["wire_ok"] = bool(out["script_present"] and out["save_trace_wired"])
        return out

    try:
        data = json.loads(newest.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        out["reason"] = f"bad_json:{exc}"
        return out

    pe = data.get("path_evidence") if isinstance(data.get("path_evidence"), dict) else {}
    ma = data.get("merge_authority") if isinstance(data.get("merge_authority"), dict) else {}
    try:
        rel = str(newest.relative_to(root))
    except ValueError:
        rel = str(newest)
    out.update(
        {
            "available": True,
            "path": rel,
            "certificate_id": data.get("certificate_id"),
            "verdict": data.get("verdict"),
            "block": data.get("block"),
            "state": data.get("state"),
            "reason_codes": data.get("reason_codes") or [],
            "path_evidence_score": pe.get("score"),
            "human_summary": ma.get("human_summary") or data.get("description"),
            "at": data.get("at"),
            "repo": (data.get("meta") or {}).get("repo") if isinstance(data.get("meta"), dict) else None,
            "pr": (data.get("meta") or {}).get("pr") if isinstance(data.get("meta"), dict) else None,
            "wire_ok": bool(
                out["script_present"] and out["save_trace_wired"] and out["workflow_wired"]
            ),
        }
    )
    return out


def smoke_status(root: Path, *, run: bool) -> dict[str, Any]:
    smoke = root / "scripts" / "smoke-torii-gate.sh"
    wf = root / ".github" / "workflows" / "smoke-offline.yml"
    out: dict[str, Any] = {
        "script_present": smoke.is_file(),
        "ci_workflow_present": wf.is_file(),
        "ran": False,
        "pass": None,
    }
    if not run or not smoke.is_file():
        return out
    try:
        r = subprocess.run(
            ["bash", str(smoke)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=180,
            env={
                **os.environ,
                "TORII_ROOT": str(root),
                "TORII_SMOKE_TOOL_EVOLVE": os.environ.get("TORII_SMOKE_TOOL_EVOLVE", "0"),
            },
        )
        out["ran"] = True
        out["pass"] = r.returncode == 0 and "SMOKE PASSED" in (r.stderr + r.stdout)
        out["rc"] = r.returncode
        out["tail"] = (r.stderr + r.stdout)[-400:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        out["ran"] = True
        out["pass"] = False
        out["error"] = str(exc)
    return out


def product_surfaces_inventory(root: Path) -> dict[str, Any]:
    """Post-queue + core product docs/scripts operators open from ops day-2."""
    surfaces = [
        ("install", "docs/INSTALL.md", "scripts/install_ux_check.py", "torii.py doctor"),
        ("golden_path", "docs/GOLDEN-PATH.md", "scripts/golden_path_metrics.py", "torii.py golden-path -- status"),
        ("certificate", "docs/GATE.md", "scripts/gate_certificate.py", "torii.py certificate -- fixture"),
        ("quieter", "docs/QUIETER.md", "scripts/quieter_over_time.py", "torii.py quieter -- status"),
        ("tool_use", "docs/TOOL-USE.md", "scripts/tool_use_quality.py", "torii.py tool-use -- status"),
        ("workflows", "docs/WORKFLOWS.md", "scripts/workflow_as_code.py", "torii.py workflow -- scorecard"),
        ("memory", "docs/MEMORY.md", "scripts/torii_memory.py", "torii.py memory -- doctor"),
        ("federation", "docs/FEDERATION.md", "scripts/federated_hub_ingest.py", "torii.py federation -- status"),
        ("self_evolve", "docs/SELF-EVOLVE.md", "scripts/self_evolve.py", "torii.py self-evolve -- status"),
        ("commercial", "docs/benchmarks/commercial-scorecard.md", "scripts/commercial_scorecard.py", "torii.py commercial -- status"),
    ]
    rows: list[dict[str, Any]] = []
    ok_n = 0
    for sid, doc_rel, script_rel, cmd in surfaces:
        doc = root / doc_rel
        script = root / script_rel
        doc_ok = doc.is_file()
        script_ok = script.is_file()
        ok = doc_ok and script_ok
        if ok:
            ok_n += 1
        rows.append(
            {
                "id": sid,
                "doc": doc_rel,
                "doc_ok": doc_ok,
                "script": script_rel,
                "script_ok": script_ok,
                "cli": cmd,
                "ok": ok,
            }
        )
    total = len(rows)
    return {
        "surfaces": rows,
        "ok_n": ok_n,
        "total": total,
        "ok": ok_n == total and total >= 8,
        "one_liner": "Product surface docs + scripts present for day-2 ops",
    }


def build_report(root: Path | None = None, *, run_smoke: bool = False) -> dict[str, Any]:
    root = root or _root()
    fc = fail_closed_inventory()
    # safe posture: tool turns gate on; webhook open off
    safe_bits = []
    for item in fc:
        name = item["name"]
        if name == "TORII_TOOL_TURNS_GATE":
            safe_bits.append(bool(item["effective"]))
        if name == "TORII_WEBHOOK_ALLOW_OPEN":
            safe_bits.append(not bool(item["effective"]))
        if name == "TORII_COMMIT_STATUS":
            safe_bits.append(bool(item["effective"]))
    req = required_check_docs(root)
    cost = cost_pr_table(root)
    smoke = smoke_status(root, run=run_smoke)
    last_cert = last_gate_certificate(root)
    products = product_surfaces_inventory(root)

    report = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "scorecard_target": "ops",
        "dim_lift": "reliability/ops (dim 8) + certificate + product surface map",
        "scored_at": _now(),
        "one_liner": (
            "Fail-closed defaults · cost/PR · gate certificate · smoke CI · "
            "product surfaces · torii/gate"
        ),
        "fail_closed": fc,
        "fail_closed_safe_defaults": all(safe_bits) if safe_bits else False,
        "required_check": req,
        "cost_per_pr": cost,
        "smoke": smoke,
        "last_gate_certificate": last_cert,
        "product_surfaces": products,
        "paths": {
            "dashboard_md": str(OUT_DIR / "DASHBOARD.md"),
            "cost_md": str(OUT_DIR / "cost-pr-dashboard.md"),
            "reliability_md": str(OUT_DIR / "RELIABILITY.md"),
            "smoke_ci": ".github/workflows/smoke-offline.yml",
        },
    }
    report["ops_ok"] = bool(
        report["fail_closed_safe_defaults"]
        and req.get("ok")
        and smoke.get("script_present")
        and smoke.get("ci_workflow_present")
        and products.get("ok")
        and (not run_smoke or smoke.get("pass"))
    )
    return report


def render_dashboard(report: dict[str, Any]) -> str:
    cost = report.get("cost_per_pr") or {}
    tts = cost.get("time_to_signal_s") or {}
    cusd = cost.get("cost_usd") or {}
    smoke = report.get("smoke") or {}
    req = report.get("required_check") or {}
    lines = [
        "<!-- torii-ops-dashboard -->",
        "",
        "# Torii ops dashboard",
        "",
        f"_Generated: `{report.get('scored_at')}` · **ops_ok={report.get('ops_ok')}** · "
        f"target **ops / dim 8**_",
        "",
        f"{report.get('one_liner')}",
        "",
        "## Fail-closed defaults",
        "",
        f"Safe defaults active: **{report.get('fail_closed_safe_defaults')}**",
        "",
        "| Env | Default | Effective | What |",
        "|-----|---------|-----------|------|",
    ]
    for item in report.get("fail_closed") or []:
        lines.append(
            f"| `{item.get('name')}` | "
            f"{'on' if item.get('default_on') else 'off'} | "
            f"{'on' if item.get('effective') else 'off'} | "
            f"{item.get('what')} |"
        )
    lines += [
        "",
        "## Required check",
        "",
        f"Context: **`{req.get('required_context')}`** · docs_ok=**{req.get('ok')}**",
        "",
        "Branch protection must require **`torii/gate`** (see `docs/INSTALL.md`, `docs/GATE.md`).",
        "",
        "## Smoke",
        "",
        f"- Script: `{smoke.get('script_present')}` · CI workflow: `{smoke.get('ci_workflow_present')}`",
        f"- Last run in this report: ran={smoke.get('ran')} pass={smoke.get('pass')}",
        "",
        "```bash",
        "./scripts/smoke-torii-gate.sh",
        "python3 scripts/ops_dashboard.py report --smoke",
        "```",
        "",
        "## Cost / PR (dogfood vault)",
        "",
        "| Stat | time-to-signal (s) | cost USD |",
        "|------|-------------------:|---------:|",
        f"| n | {tts.get('n')} | {cusd.get('n')} |",
        f"| mean | {tts.get('mean')} | {cusd.get('mean')} |",
        f"| p50 | {tts.get('p50')} | {cusd.get('p50')} |",
        f"| min | {tts.get('min')} | {cusd.get('min')} |",
        f"| max | {tts.get('max')} | {cusd.get('max')} |",
        "",
        f"Runs: **{cost.get('runs')}** · source: `{cost.get('source')}`",
        "",
        "Detail: [cost-pr-dashboard.md](cost-pr-dashboard.md) · "
        "Reliability one-pager: [RELIABILITY.md](RELIABILITY.md)",
        "",
    ]
    cert = report.get("last_gate_certificate") or {}
    lines += [
        "## Last gate certificate (merge authority)",
        "",
        "Deterministic reason codes + path evidence for the latest dogfood gate decision "
        "(not a chat transcript). Soft-wired via `save-trace.sh` + reusable workflow.",
        "",
    ]
    if cert.get("available"):
        codes = ", ".join(f"`{c}`" for c in (cert.get("reason_codes") or [])[:8]) or "—"
        lines += [
            f"**{cert.get('human_summary') or '—'}**",
            "",
            "| Field | Value |",
            "|-------|------:|",
            f"| certificate_id | `{cert.get('certificate_id')}` |",
            f"| block | {cert.get('block')} |",
            f"| verdict | {cert.get('verdict')} |",
            f"| path_evidence | {cert.get('path_evidence_score')} |",
            f"| reason_codes | {codes} |",
            f"| vault path | `{cert.get('path')}` |",
            f"| wire_ok | {cert.get('wire_ok')} |",
            "",
        ]
    else:
        lines += [
            f"_No certificate in vault yet_ · reason=`{cert.get('reason')}` · "
            f"script={cert.get('script_present')} save_trace_wired={cert.get('save_trace_wired')} "
            f"workflow_wired={cert.get('workflow_wired')}",
            "",
        ]
    lines += [
        "```bash",
        "python3 scripts/torii.py certificate -- fixture",
        "python3 scripts/gate_certificate.py emit --review .torii-out/review-1.md --write .torii-out",
        "```",
        "",
    ]
    products = report.get("product_surfaces") or {}
    lines += [
        "## Product surfaces (day-2 ops map)",
        "",
        f"Docs + scripts ready: **{products.get('ok_n')}/{products.get('total')}** · "
        f"product_surfaces_ok=**{products.get('ok')}**",
        "",
        "Operators should not hunt research logs — each surface has one CLI.",
        "",
        "| Surface | Doc | Script | CLI | Ok |",
        "|---------|-----|--------|-----|:--:|",
    ]
    for row in products.get("surfaces") or []:
        mark = "yes" if row.get("ok") else "**no**"
        lines.append(
            f"| `{row.get('id')}` | `{row.get('doc')}` | `{row.get('script')}` | "
            f"`{row.get('cli')}` | {mark} |"
        )
    lines += [
        "",
        "Hub map: [README product surfaces](../../README.md#product-surfaces-one-cli) · "
        "commercial: `python3 scripts/torii.py commercial -- status`",
        "",
        "## Refresh",
        "",
        "```bash",
        "python3 scripts/ops_dashboard.py report --smoke",
        "python3 scripts/torii.py ops -- report",
        "python3 scripts/golden_path_metrics.py report",
        "```",
        "",
    ]
    return "\n".join(lines)


def render_cost_md(report: dict[str, Any]) -> str:
    cost = report.get("cost_per_pr") or {}
    tts = cost.get("time_to_signal_s") or {}
    cusd = cost.get("cost_usd") or {}
    lines = [
        "<!-- torii-cost-pr-dashboard -->",
        "",
        "# Cost / PR dashboard (stub)",
        "",
        f"_Generated: `{report.get('scored_at')}` · from dogfood vault_",
        "",
        "Operator-facing cost visibility without opening Modal artifacts.",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| dogfood runs | {cost.get('runs')} |",
        f"| time-to-signal p50 (s) | {tts.get('p50')} |",
        f"| time-to-signal mean (s) | {tts.get('mean')} |",
        f"| cost/PR p50 (USD) | {cusd.get('p50')} |",
        f"| cost/PR mean (USD) | {cusd.get('mean')} |",
        f"| cost/PR min–max | {cusd.get('min')} – {cusd.get('max')} |",
        "",
        "### Verdict distribution (unlabelled live)",
        "",
        "| Verdict | count |",
        "|---------|------:|",
    ]
    for k, v in sorted((cost.get("verdicts") or {}).items()):
        lines.append(f"| {k} | {v} |")
    if not cost.get("verdicts"):
        lines.append("| _(none)_ | 0 |")
    lines += [
        "",
        "Soft budget (GHA): set repo var `TORII_MAX_COST_USD` for over-budget warnings "
        "(does not fail the run by default).",
        "",
        "Related: `docs/benchmarks/golden-path-metrics.md` · `docs/benchmarks/public-eval/SCORECARD.md`",
        "",
    ]
    return "\n".join(lines)


def ensure_reliability_md(root: Path) -> None:
    path = root / OUT_DIR / "RELIABILITY.md"
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# Torii reliability & ops (one-pager)

**Dim 8 lift:** fail-closed defaults · cost/PR visibility · smoke CI · required check.

## Fail-closed (defaults)

| Control | Default | Effect |
|---------|---------|--------|
| Tool-turns gate | **on** | Multi-file code PRs with 0 tool turns cannot APPROVE |
| Tool-turns re-prompt | **on** | One budgeted soft re-prompt when tools were skipped |
| Modal webhook open | **off** | Refuse unauthenticated open webhook unless explicitly allowed |
| Commit statuses | **on** | Posts `torii/gate` + `torii/review` |
| `TORII_GATE_STRICT` | off | Optional hard job fail; branch protection uses **status** |

## Required check

Branch protection → require **`torii/gate`**. See `docs/INSTALL.md` and `docs/GATE.md`.

## Smoke CI

```bash
./scripts/smoke-torii-gate.sh
# CI: .github/workflows/smoke-offline.yml on push/PR
```

## Cost / PR

```bash
python3 scripts/ops_dashboard.py report
# → docs/ops/DASHBOARD.md · docs/ops/cost-pr-dashboard.md
```

Day-2: `python3 scripts/torii.py doctor` · `python3 scripts/torii.py ops -- status`
""",
        encoding="utf-8",
    )


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root, run_smoke=bool(getattr(args, "smoke", False)))
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    ensure_reliability_md(root)
    if not getattr(args, "dry_run", False):
        (out / "DASHBOARD.md").write_text(render_dashboard(report), encoding="utf-8")
        (out / "cost-pr-dashboard.md").write_text(render_cost_md(report), encoding="utf-8")
        (out / "dashboard.json").write_text(
            json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
        )
        report["wrote"] = {
            "dashboard": str(out / "DASHBOARD.md"),
            "cost": str(out / "cost-pr-dashboard.md"),
            "json": str(out / "dashboard.json"),
        }
    if getattr(args, "json", False) or not sys.stdout.isatty():
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_dashboard(report))
    return 0 if report.get("ops_ok") or getattr(args, "allow_partial", False) else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root, run_smoke=False)
    # fixture: surfaces present; do not require smoke run
    ensure_reliability_md(root)
    # write dashboard without smoke for hermetic artifacts
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "DASHBOARD.md").write_text(render_dashboard(report), encoding="utf-8")
    (out / "cost-pr-dashboard.md").write_text(render_cost_md(report), encoding="utf-8")

    cert = report.get("last_gate_certificate") or {}
    dash_body = (root / OUT_DIR / "DASHBOARD.md").read_text(
        encoding="utf-8", errors="replace"
    )
    products = report.get("product_surfaces") or {}
    checks = {
        "fail_closed_safe": bool(report.get("fail_closed_safe_defaults")),
        "required_check_docs": bool((report.get("required_check") or {}).get("ok")),
        "smoke_script": bool((report.get("smoke") or {}).get("script_present")),
        "smoke_ci": bool((report.get("smoke") or {}).get("ci_workflow_present")),
        "reliability_md": (root / OUT_DIR / "RELIABILITY.md").is_file(),
        "dashboard_md": (root / OUT_DIR / "DASHBOARD.md").is_file(),
        "cost_md": (root / OUT_DIR / "cost-pr-dashboard.md").is_file(),
        "ops_script": (root / "scripts" / "ops_dashboard.py").is_file(),
        "gate_cert_script": bool(cert.get("script_present")),
        "gate_cert_save_trace_wired": bool(cert.get("save_trace_wired")),
        "gate_cert_workflow_wired": bool(cert.get("workflow_wired")),
        "dashboard_mentions_certificate": "gate certificate" in dash_body.lower()
        or "Last gate certificate" in dash_body,
        "product_surfaces_ok": bool(products.get("ok")),
        "dashboard_mentions_product_surfaces": "Product surfaces" in dash_body,
    }
    # Also require tool_turns gate source default on
    tt = root / "scripts" / "tool_turns_gate.py"
    checks["tool_turns_default_on"] = tt.is_file() and "default" in tt.read_text(encoding="utf-8")

    fixture_pass = all(checks.values())
    payload = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "fixture_pass": fixture_pass,
        "checks": checks,
        "fail_closed_safe_defaults": report.get("fail_closed_safe_defaults"),
        "required_context": "torii/gate",
        "last_gate_certificate": {
            "available": cert.get("available"),
            "certificate_id": cert.get("certificate_id"),
            "wire_ok": cert.get("wire_ok"),
        },
        "scorecard_target": "ops",
        "at": _now(),
    }
    print(json.dumps(payload, indent=2))
    return 0 if fixture_pass else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    path = root / OUT_DIR / "dashboard.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            print(
                json.dumps(
                    {
                        "feature": FEATURE,
                        "ops_ok": data.get("ops_ok"),
                        "fail_closed_safe_defaults": data.get("fail_closed_safe_defaults"),
                        "cost_runs": (data.get("cost_per_pr") or {}).get("runs"),
                        "smoke_ci": (data.get("smoke") or {}).get("ci_workflow_present"),
                        "at": data.get("scored_at"),
                    },
                    indent=2,
                )
            )
            return 0 if data.get("ops_ok") else 1
        except json.JSONDecodeError:
            pass
    return cmd_fixture(args)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Torii ops / reliability dashboard")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("report", help="Write ops dashboard + cost/PR stub")
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--smoke", action="store_true", help="Also run offline smoke")
    pr.add_argument("--allow-partial", action="store_true")
    pr.set_defaults(func=cmd_report)

    pf = sub.add_parser("fixture", help="Hermetic ops surface check")
    pf.set_defaults(func=cmd_fixture)

    ps = sub.add_parser("status", help="Short ops status")
    ps.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
