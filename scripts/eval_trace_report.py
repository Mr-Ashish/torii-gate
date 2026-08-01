#!/usr/bin/env python3
"""F83: Paper-ready eval report from the redacted trace vault.

Aggregates docs/benchmarks/traces/*/summary.json (+ fitness when present)
into a single metrics table for research papers / dashboards.

Commands:
  report   — write Markdown + JSON report
  fixture  — offline: vault non-empty, report has rows, no home paths
  status   — count vault entries

Env:
  TORII_ROOT
  TORII_TRACE_VAULT_ROOT  override docs/benchmarks/traces
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F83"
SCHEMA = 1


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


def load_entries(vroot: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not vroot.is_dir():
        return rows
    for d in sorted(vroot.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        summary_p = d / "summary.json"
        fitness_p = d / "fitness.json"
        meta_p = d / "meta.json"
        summary: dict[str, Any] = {}
        if summary_p.is_file():
            try:
                summary = json.loads(summary_p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                summary = {}
        fitness = summary.get("fitness") if isinstance(summary.get("fitness"), dict) else None
        if fitness is None and fitness_p.is_file():
            try:
                fitness = json.loads(fitness_p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                fitness = None
        meta = {}
        if meta_p.is_file():
            try:
                meta = json.loads(meta_p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}
        modal = summary.get("modal") if isinstance(summary.get("modal"), dict) else {}
        composite = None
        level = None
        if isinstance(fitness, dict):
            composite = fitness.get("composite")
            level = fitness.get("level")
        # modal-only entries may lack fitness
        host = summary.get("host") or meta.get("host") or (
            "modal" if modal or "modal" in d.name else "local"
        )
        row = {
            "dir": d.name,
            "run_id": summary.get("run_id") or d.name,
            "archived_at": summary.get("archived_at") or "",
            "repo": summary.get("repo") or "",
            "pr": str(summary.get("pr_number") or summary.get("pr") or ""),
            "model": summary.get("model") or "",
            "label": summary.get("label") or "",
            "feature": summary.get("feature") or meta.get("feature") or "",
            "host": host,
            "composite": composite,
            "level": level or (summary.get("label") if isinstance(summary.get("label"), str) else ""),
            "log_streaming": modal.get("log_streaming"),
            "elapsed_s": modal.get("elapsed_s"),
            "tool_call_turns": (modal.get("tool_call_turns") or (fitness or {}).get("tool_call_turns")),
            "git_safe": summary.get("git_safe", True),
        }
        rows.append(row)
    return rows


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    composites = [
        float(r["composite"])
        for r in rows
        if isinstance(r.get("composite"), (int, float))
    ]
    modal_n = sum(1 for r in rows if str(r.get("host")) == "modal")
    local_n = len(rows) - modal_n
    streaming_n = sum(1 for r in rows if r.get("log_streaming") is True)
    by_level: dict[str, int] = {}
    for r in rows:
        lv = str(r.get("level") or "—")
        by_level[lv] = by_level.get(lv, 0) + 1
    models = sorted({str(r.get("model") or "") for r in rows if r.get("model")})
    return {
        "n_runs": len(rows),
        "n_modal": modal_n,
        "n_local": local_n,
        "n_log_streaming": streaming_n,
        "n_with_composite": len(composites),
        "composite_mean": round(statistics.mean(composites), 4) if composites else None,
        "composite_median": round(statistics.median(composites), 4) if composites else None,
        "composite_min": round(min(composites), 4) if composites else None,
        "composite_max": round(max(composites), 4) if composites else None,
        "by_level": by_level,
        "models": models,
    }


def render_markdown(rows: list[dict[str, Any]], agg: dict[str, Any]) -> str:
    lines = [
        f"# Torii eval-trace report (F83)",
        "",
        f"Generated: `{_now()}`",
        "",
        "## Aggregate",
        "",
        f"- runs: **{agg['n_runs']}** (modal={agg['n_modal']}, local={agg['n_local']})",
        f"- log_streaming true: **{agg['n_log_streaming']}**",
        f"- fitness composite n={agg['n_with_composite']}",
    ]
    if agg.get("composite_mean") is not None:
        lines.append(
            f"- composite mean/median/min/max: "
            f"**{agg['composite_mean']}** / {agg['composite_median']} / "
            f"{agg['composite_min']} / {agg['composite_max']}"
        )
    lines += [
        f"- levels: `{json.dumps(agg.get('by_level') or {})}`",
        f"- models: {', '.join(f'`{m}`' for m in (agg.get('models') or []) if m) or '—'}",
        "",
        "## Runs",
        "",
        "| Archived | Host | Repo | PR | Model | Composite | Level | Feature | Dir |",
        "|----------|------|------|----|-------|-----------|-------|---------|-----|",
    ]
    for r in rows:
        comp = r.get("composite")
        comp_s = f"{comp:.4f}" if isinstance(comp, (int, float)) else "—"
        lines.append(
            f"| {r.get('archived_at') or '—'} | {r.get('host')} | {r.get('repo') or '—'} | "
            f"{r.get('pr') or '—'} | `{r.get('model') or '—'}` | {comp_s} | "
            f"{r.get('level') or '—'} | {r.get('feature') or '—'} | `{r.get('dir')}` |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Vault entries are redacted for paper/eval use; large agent.log may be gitignored.",
        "- Modal rows may omit composite when fitness was scored only in-container.",
        "- Source of truth paths: `docs/benchmarks/traces/*/summary.json`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_report(
    root: Path,
    *,
    out_md: Path | None = None,
    out_json: Path | None = None,
) -> dict[str, Any]:
    vroot = vault_root(root)
    rows = load_entries(vroot)
    agg = aggregate(rows)
    payload = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "generated_at": _now(),
        "vault": str(vroot),
        "aggregate": agg,
        "runs": rows,
    }
    md = render_markdown(rows, agg)
    out_md = out_md or (root / "docs" / "benchmarks" / "traces" / "EVAL-REPORT.md")
    out_json = out_json or (root / "docs" / "benchmarks" / "traces" / "eval-report.json")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # privacy: no home paths in report
    privacy_ok = "/Users/" not in md and "sk-or-v1-" not in md
    return {
        "feature": FEATURE,
        "n_runs": agg["n_runs"],
        "aggregate": agg,
        "out_md": str(out_md),
        "out_json": str(out_json),
        "privacy_ok": privacy_ok,
    }


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    result = write_report(
        root,
        out_md=Path(args.out_md) if args.out_md else None,
        out_json=Path(args.out_json) if args.out_json else None,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("n_runs", 0) >= 0 and result.get("privacy_ok") else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    rows = load_entries(vault_root(root))
    agg = aggregate(rows)
    print(json.dumps({"feature": FEATURE, "aggregate": agg}, indent=2))
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    result = write_report(root)
    fixture_pass = (
        result.get("n_runs", 0) >= 1
        and result.get("privacy_ok")
        and Path(result["out_md"]).is_file()
        and Path(result["out_json"]).is_file()
        and "Aggregate" in Path(result["out_md"]).read_text(encoding="utf-8")
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                **{k: result[k] for k in ("n_runs", "privacy_ok", "out_md", "out_json") if k in result},
                "aggregate": result.get("aggregate"),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F83 paper eval report from trace vault")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("report")
    pr.add_argument("--out-md", default="")
    pr.add_argument("--out-json", default="")
    pr.set_defaults(func=cmd_report)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("fixture").set_defaults(func=cmd_fixture)
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
