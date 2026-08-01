#!/usr/bin/env python3
"""Commercial product scorecard rollup (post priority-queue 1–6).

Tools-as-code that serve golden path / eval / install / ops / enterprise:
runs hermetic fixtures for each commercial surface and publishes a single
score trajectory from baseline 6.6 toward 7.5+.

Commands:
  report | fixture | status
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "COMMERCIAL"
SCHEMA = 1
BASELINE_OVERALL = 6.6
OUT_REL = Path("docs/benchmarks/commercial-scorecard.md")
OUT_JSON = Path("docs/benchmarks/commercial-scorecard.json")

# Priority queue surfaces: script, target label, weight toward overall lift
SURFACES: list[dict[str, Any]] = [
    {
        "id": "golden_path",
        "script": "golden_path_metrics.py",
        "target": "7.5",
        "dim": "commercial / simplicity path",
        "weight": 0.22,
        "pass_key": "fixture_pass",
    },
    {
        "id": "buyer_narrative",
        "script": "buyer_narrative_check.py",
        "target": "8.0",
        "dim": "simplicity (narrative)",
        "weight": 0.18,
        "pass_key": "fixture_pass",
    },
    {
        "id": "public_eval",
        "script": "public_eval.py",
        "target": "8.5",
        "dim": "technical trust",
        "weight": 0.20,
        "pass_key": "fixture_pass",
    },
    {
        "id": "install_ux",
        "script": "install_ux_check.py",
        "target": "install",
        "dim": "install UX (dim 7)",
        "weight": 0.14,
        "pass_key": "fixture_pass",
    },
    {
        "id": "ops",
        "script": "ops_dashboard.py",
        "target": "ops",
        "dim": "reliability/ops (dim 8)",
        "weight": 0.14,
        "pass_key": "fixture_pass",
    },
    {
        "id": "enterprise",
        "script": "enterprise_surface.py",
        "target": "enterprise",
        "dim": "enterprise light (dim 9)",
        "weight": 0.12,
        "pass_key": "fixture_pass",
    },
]


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_fixture(root: Path, script: str) -> dict[str, Any]:
    path = root / "scripts" / script
    if not path.is_file():
        return {"ok": False, "error": "missing_script", "script": script}
    try:
        r = subprocess.run(
            [sys.executable, str(path), "fixture"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "script": script}
    data: dict[str, Any] = {}
    try:
        data = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    except json.JSONDecodeError:
        data = {}
    ok = r.returncode == 0 and bool(
        data.get("fixture_pass") if "fixture_pass" in data else r.returncode == 0
    )
    return {
        "ok": ok,
        "rc": r.returncode,
        "fixture_pass": data.get("fixture_pass"),
        "scorecard_target": data.get("scorecard_target"),
        "script": script,
        "payload_keys": list(data.keys())[:12],
    }


def estimate_overall(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Heuristic commercial score: baseline + weighted lifts when fixtures pass.

    Caps at 8.5 for this rollup (does not claim market validation).
    """
    # Max lift budget to go from 6.6 → ~8.3 if all pass
    max_lift = 1.9
    earned = 0.0
    for r in results:
        w = float(r.get("weight") or 0)
        if r.get("ok"):
            earned += w
    # normalize weights sum ~1.0
    wsum = sum(float(r.get("weight") or 0) for r in results) or 1.0
    frac = earned / wsum
    overall = round(min(8.5, BASELINE_OVERALL + max_lift * frac), 2)
    return {
        "baseline": BASELINE_OVERALL,
        "overall_est": overall,
        "lift": round(overall - BASELINE_OVERALL, 2),
        "surfaces_pass": sum(1 for r in results if r.get("ok")),
        "surfaces_total": len(results),
        "pass_fraction": round(frac, 3),
        "note": (
            "Heuristic commercial score from hermetic surface fixtures — "
            "not a customer interview score. Cap 8.5 until live revenue proof."
        ),
    }


def build_report(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    results: list[dict[str, Any]] = []
    for s in SURFACES:
        fr = run_fixture(root, s["script"])
        results.append(
            {
                "id": s["id"],
                "target": s["target"],
                "dim": s["dim"],
                "weight": s["weight"],
                "ok": fr.get("ok"),
                "fixture": fr,
            }
        )
    est = estimate_overall(results)
    # docs presence quick check for golden path metrics artifact
    artifacts = {
        "golden_path_md": (root / "docs" / "benchmarks" / "golden-path-metrics.md").is_file(),
        "public_eval_md": (root / "docs" / "benchmarks" / "public-eval" / "SCORECARD.md").is_file(),
        "buyer_diagram": (root / "docs" / "brand" / "BUYER-DIAGRAM.md").is_file(),
        "install_md": (root / "docs" / "INSTALL.md").is_file(),
        "ops_dashboard": (root / "docs" / "ops" / "DASHBOARD.md").is_file(),
        "enterprise_privacy": (root / "docs" / "enterprise" / "PRIVACY.md").is_file(),
    }
    report = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "scored_at": _now(),
        "scorecard_target": "7.5+",
        "dim_lift": "commercial rollup of priority queue 1–6",
        "one_liner": (
            "Single commercial scorecard: golden path · buyer · public eval · "
            "install · ops · enterprise"
        ),
        "surfaces": results,
        "estimate": est,
        "artifacts": artifacts,
        "all_surfaces_pass": all(r.get("ok") for r in results),
        "artifacts_ok": all(artifacts.values()),
    }
    report["commercial_ok"] = bool(
        report["all_surfaces_pass"] and report["artifacts_ok"] and est["overall_est"] >= 7.5
    )
    return report


def render_md(report: dict[str, Any]) -> str:
    est = report.get("estimate") or {}
    lines = [
        "<!-- torii-commercial-scorecard -->",
        "",
        "# Commercial product scorecard",
        "",
        f"_Generated: `{report.get('scored_at')}` · "
        f"**overall_est={est.get('overall_est')}/10** "
        f"(baseline {est.get('baseline')}) · "
        f"commercial_ok=`{report.get('commercial_ok')}`_",
        "",
        f"{report.get('one_liner')}",
        "",
        est.get("note") or "",
        "",
        "## Trajectory",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| baseline overall | {est.get('baseline')} |",
        f"| overall_est | **{est.get('overall_est')}** |",
        f"| lift | +{est.get('lift')} |",
        f"| surfaces pass | {est.get('surfaces_pass')}/{est.get('surfaces_total')} |",
        "",
        "## Priority queue surfaces",
        "",
        "| Surface | Target | Dim | Pass |",
        "|---------|--------|-----|:----:|",
    ]
    for r in report.get("surfaces") or []:
        mark = "yes" if r.get("ok") else "**no**"
        lines.append(
            f"| `{r.get('id')}` | {r.get('target')} | {r.get('dim')} | {mark} |"
        )
    lines += [
        "",
        "## Buyer artifacts",
        "",
        "| Artifact | Present |",
        "|----------|:-------:|",
    ]
    for k, v in sorted((report.get("artifacts") or {}).items()):
        lines.append(f"| `{k}` | {v} |")
    lines += [
        "",
        "## Refresh",
        "",
        "```bash",
        "python3 scripts/commercial_scorecard.py report",
        "python3 scripts/commercial_scorecard.py fixture",
        "python3 scripts/torii.py commercial -- status",
        "```",
        "",
        "Related: [GOLDEN-PATH](../GOLDEN-PATH.md) · "
        "[public-eval](public-eval/SCORECARD.md) · "
        "[ops](../ops/DASHBOARD.md) · "
        "[enterprise](../enterprise/)",
        "",
    ]
    return "\n".join(lines)


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    if not getattr(args, "dry_run", False):
        out = root / OUT_REL
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_md(report), encoding="utf-8")
        jpath = root / OUT_JSON
        jpath.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        report["wrote"] = {"md": str(out), "json": str(jpath)}
    if getattr(args, "json", False) or not sys.stdout.isatty():
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_md(report))
    return 0 if report.get("commercial_ok") or getattr(args, "allow_partial", False) else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    # always write on fixture for CI artifact
    (root / OUT_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / OUT_REL).write_text(render_md(report), encoding="utf-8")
    (root / OUT_JSON).write_text(
        json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
    )
    payload = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "fixture_pass": bool(report.get("commercial_ok")),
        "all_surfaces_pass": report.get("all_surfaces_pass"),
        "artifacts_ok": report.get("artifacts_ok"),
        "overall_est": (report.get("estimate") or {}).get("overall_est"),
        "surfaces_pass": (report.get("estimate") or {}).get("surfaces_pass"),
        "surfaces_total": (report.get("estimate") or {}).get("surfaces_total"),
        "scorecard_target": "7.5+",
        "at": _now(),
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["fixture_pass"] else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    path = root / OUT_JSON
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            print(
                json.dumps(
                    {
                        "feature": FEATURE,
                        "commercial_ok": data.get("commercial_ok"),
                        "overall_est": (data.get("estimate") or {}).get("overall_est"),
                        "surfaces_pass": (data.get("estimate") or {}).get("surfaces_pass"),
                        "at": data.get("scored_at"),
                    },
                    indent=2,
                )
            )
            return 0 if data.get("commercial_ok") else 1
        except json.JSONDecodeError:
            pass
    return cmd_fixture(args)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Torii commercial scorecard rollup")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("report", help="Run all commercial fixtures + write scorecard")
    pr.add_argument("--json", action="store_true")
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--allow-partial", action="store_true")
    pr.set_defaults(func=cmd_report)

    pf = sub.add_parser("fixture", help="Hermetic commercial rollup")
    pf.set_defaults(func=cmd_fixture)

    ps = sub.add_parser("status", help="Short status from last scorecard")
    ps.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
