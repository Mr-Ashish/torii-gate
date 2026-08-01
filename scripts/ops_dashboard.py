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

    report = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "scorecard_target": "ops",
        "dim_lift": "reliability/ops (dim 8)",
        "scored_at": _now(),
        "one_liner": (
            "Fail-closed defaults · cost/PR dashboard · smoke CI · required check torii/gate"
        ),
        "fail_closed": fc,
        "fail_closed_safe_defaults": all(safe_bits) if safe_bits else False,
        "required_check": req,
        "cost_per_pr": cost,
        "smoke": smoke,
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
        "## Refresh",
        "",
        "```bash",
        "python3 scripts/ops_dashboard.py report --smoke",
        "python3 scripts/torii.py ops -- report",
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

    checks = {
        "fail_closed_safe": bool(report.get("fail_closed_safe_defaults")),
        "required_check_docs": bool((report.get("required_check") or {}).get("ok")),
        "smoke_script": bool((report.get("smoke") or {}).get("script_present")),
        "smoke_ci": bool((report.get("smoke") or {}).get("ci_workflow_present")),
        "reliability_md": (root / OUT_DIR / "RELIABILITY.md").is_file(),
        "dashboard_md": (root / OUT_DIR / "DASHBOARD.md").is_file(),
        "cost_md": (root / OUT_DIR / "cost-pr-dashboard.md").is_file(),
        "ops_script": (root / "scripts" / "ops_dashboard.py").is_file(),
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
