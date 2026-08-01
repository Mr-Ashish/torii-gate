#!/usr/bin/env python3
"""Agent tool-use quality product surface (post-queue tools-as-code).

Buyers care that the gate agent **uses tools** (diff/workspace/CLI) — not pure
LLM prose. This rolls vault dogfood + fail-closed gates + catalog into one chart.

No new F-compound loop: reuses trajectory_fitness.score_tool_use signals,
tool_turns_gate defaults, and agent-loop tool_call_turns.

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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "TOOL_USE"
SCHEMA = 1
MARKER = "<!-- torii-tool-use-quality -->"
OUT_MD = Path("docs/benchmarks/tool-use-quality.md")
OUT_JSON = Path("docs/benchmarks/tool-use-quality.json")
BUYER_DOC = Path("docs/TOOL-USE.md")


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


def _find_agent_loop(d: Path) -> dict[str, Any]:
    candidates = [
        d / "agent-loop" / "agent-loop.json",
        d / "agent-loop.json",
        d / "hermes" / "agent-loop.json",
    ]
    # nested traces dirs
    for p in candidates:
        data = _safe_json(p)
        if data:
            return data
    nested = d / "traces"
    if nested.is_dir():
        for sub in nested.iterdir():
            if sub.is_dir():
                data = _find_agent_loop(sub)
                if data:
                    return data
    return {}


def _tool_names_from_loop(loop: dict[str, Any]) -> list[str]:
    names: list[str] = []
    steps = loop.get("steps") if isinstance(loop.get("steps"), list) else []
    for s in steps:
        if not isinstance(s, dict):
            continue
        if s.get("tool_name"):
            names.append(str(s["tool_name"]))
        tcs = s.get("tool_calls")
        if isinstance(tcs, list):
            for tc in tcs:
                if isinstance(tc, dict):
                    n = tc.get("name") or tc.get("tool_name") or tc.get("function", {})
                    if isinstance(n, dict):
                        n = n.get("name")
                    if n:
                        names.append(str(n))
        # terminal command snippets
        if s.get("kind") in ("tool", "tool_result", "assistant_tool_calls"):
            content = str(s.get("content") or s.get("input") or "")
            if "python3 scripts/torii" in content or "torii.py" in content:
                names.append("torii-cli")
            if re.search(r"\b(rg|grep|sed|cat|head)\b", content):
                names.append("shell-read")
    msgs = loop.get("messages") if isinstance(loop.get("messages"), list) else []
    for m in msgs:
        if not isinstance(m, dict):
            continue
        tcs = m.get("tool_calls")
        if isinstance(tcs, list):
            for tc in tcs:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
                n = tc.get("name") or fn.get("name") or tc.get("tool_name")
                if n:
                    names.append(str(n))
    return names


def _turns_from_sources(
    summary: dict[str, Any],
    loop: dict[str, Any],
    fitness: dict[str, Any] | None,
) -> int | None:
    for src in (summary, loop, fitness or {}):
        if not isinstance(src, dict):
            continue
        for k in ("tool_call_turns", "tool_turns"):
            v = src.get(k)
            if isinstance(v, (int, float)):
                return int(v)
    if loop and isinstance(loop.get("steps"), list):
        n = sum(
            1
            for s in loop["steps"]
            if isinstance(s, dict)
            and (
                s.get("kind") in ("assistant_tool_calls", "tool", "tool_call")
                or s.get("tool_calls")
                or s.get("tool_name")
            )
        )
        if n:
            return n
    return None


def collect_rows(vroot: Path) -> list[dict[str, Any]]:
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
        loop = _find_agent_loop(d)
        meta = _safe_json(d / "meta.json")
        name_l = d.name.lower()
        repo = str(summary.get("repo") or meta.get("repo") or "")
        pr = str(summary.get("pr") or summary.get("pr_number") or meta.get("pr") or "")
        if not repo and "pytorch" in name_l:
            repo = "pytorch/pytorch"
        if not pr:
            m = re.search(r"pr[#\-]?(\d{4,})", name_l)
            if m:
                pr = m.group(1)

        turns = _turns_from_sources(summary, loop, fitness if isinstance(fitness, dict) else None)
        tool_names = _tool_names_from_loop(loop) if loop else []
        has_loop = bool(loop)
        verdict = str(
            (fitness or {}).get("verdict")
            if isinstance(fitness, dict)
            else ""
            or summary.get("verdict")
            or ""
        ).upper().replace(" ", "_")

        is_dogfood = bool(
            repo
            or re.search(r"pytorch|pr\d{3,}|modal-", name_l)
            or turns is not None
            or has_loop
        )
        if not is_dogfood:
            continue
        # skip pure lab dirs without signal
        if name_l.startswith("f") and not any(
            x in name_l for x in ("pytorch", "modal", "dogfood", "live")
        ):
            if not (repo and (turns is not None or has_loop)):
                continue
        if turns is None and not has_loop and not summary:
            continue
        if turns is None and not has_loop and not any([repo, pr, verdict]):
            continue

        rows.append(
            {
                "trace_id": d.name,
                "repo": repo,
                "pr": pr,
                "tool_call_turns": turns,
                "has_agent_loop": has_loop,
                "tool_names": tool_names[:20],
                "tool_name_n": len(set(tool_names)),
                "verdict": verdict or "UNKNOWN",
                "zero_tool": turns is not None and int(turns) < 1,
                "quality_band": _band(turns),
            }
        )
    return rows


def _band(turns: int | None) -> str:
    if turns is None:
        return "unknown"
    if turns >= 5:
        return "deep"
    if turns >= 3:
        return "solid"
    if turns >= 1:
        return "minimal"
    return "zero"


def _rate(ok: int, n: int) -> float | None:
    if n <= 0:
        return None
    return round(ok / n, 4)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [r for r in rows if r.get("tool_call_turns") is not None]
    n = len(measured)
    if n == 0:
        return {
            "measured_n": 0,
            "tool_use_rate": None,
            "mean_turns": None,
            "median_turns": None,
            "zero_tool_n": 0,
            "zero_tool_rate": None,
            "deep_rate": None,
            "solid_plus_rate": None,
            "band_counts": {},
            "top_tools": [],
            "quality_score": None,
            "quality_ok": False,
        }
    turns = [int(r["tool_call_turns"]) for r in measured]
    zero_n = sum(1 for t in turns if t < 1)
    deep_n = sum(1 for t in turns if t >= 5)
    solid_plus = sum(1 for t in turns if t >= 3)
    used_n = n - zero_n
    bands = Counter(r.get("quality_band") or "unknown" for r in measured)
    name_ctr: Counter[str] = Counter()
    for r in measured:
        for nm in r.get("tool_names") or []:
            name_ctr[str(nm)] += 1
    # quality_score: 0.5 * use_rate + 0.3 * solid_plus_rate + 0.2 * deep_rate
    use_rate = used_n / n
    solid_r = solid_plus / n
    deep_r = deep_n / n
    q = round(max(0.0, min(1.0, 0.5 * use_rate + 0.3 * solid_r + 0.2 * deep_r)), 4)
    quality_ok = use_rate >= 0.5 and statistics.mean(turns) >= 1.0
    return {
        "measured_n": n,
        "tool_use_rate": _rate(used_n, n),
        "mean_turns": round(statistics.mean(turns), 2),
        "median_turns": round(statistics.median(turns), 2),
        "zero_tool_n": zero_n,
        "zero_tool_rate": _rate(zero_n, n),
        "deep_rate": _rate(deep_n, n),
        "solid_plus_rate": _rate(solid_plus, n),
        "band_counts": dict(bands),
        "top_tools": [{"name": k, "n": v} for k, v in name_ctr.most_common(12)],
        "quality_score": q,
        "quality_ok": quality_ok,
    }


def readiness(root: Path) -> dict[str, Any]:
    """Product surfaces that enforce / measure tool use."""
    checks = {
        "tool_turns_gate_script": (root / "scripts" / "tool_turns_gate.py").is_file(),
        "trajectory_fitness_script": (root / "scripts" / "trajectory_fitness.py").is_file(),
        "agent_tools_pipeline": (root / "scripts" / "agent_tools_pipeline.py").is_file(),
        "tool_use_quality_script": (root / "scripts" / "tool_use_quality.py").is_file(),
        "buyer_doc": (root / BUYER_DOC).is_file(),
        "catalog": (root / "agent" / "tools" / "catalog.json").is_file(),
        "gate_doc_mentions_tools": False,
        "tool_turns_default_on": False,
    }
    tt = root / "scripts" / "tool_turns_gate.py"
    if tt.is_file():
        text = tt.read_text(encoding="utf-8")
        # default on when unset
        checks["tool_turns_default_on"] = (
            "default" in text.lower() and "TORII_TOOL_TURNS_GATE" in text
        )
    for rel in ("docs/GATE.md", "docs/GOLDEN-PATH.md", "PRODUCT.md", str(BUYER_DOC)):
        p = root / rel
        if p.is_file() and re.search(r"\btool", p.read_text(encoding="utf-8"), re.I):
            checks["gate_doc_mentions_tools"] = True
            break

    catalog = _safe_json(root / "agent" / "tools" / "catalog.json")
    tools = catalog.get("tools") if isinstance(catalog.get("tools"), list) else []
    adopted = [
        t
        for t in tools
        if isinstance(t, dict) and str(t.get("status") or "").lower() == "adopted"
    ]
    ok_n = sum(1 for v in checks.values() if v)
    return {
        "checks": checks,
        "ok_n": ok_n,
        "total": len(checks),
        "ok": ok_n == len(checks),
        "catalog_tools": len(tools),
        "catalog_adopted": len(adopted),
        "one_liner": "tool turns gate + vault tool-use chart + adopted catalog",
    }


def build_report(root: Path) -> dict[str, Any]:
    rows = collect_rows(vault_root(root))
    agg = aggregate(rows)
    ready = readiness(root)
    tool_use_ok = bool(
        ready.get("ok")
        and (agg.get("quality_ok") or (agg.get("measured_n") or 0) == 0)
        # if no dogfood yet, readiness alone is not enough for ok=true on status
    )
    # Prefer quality_ok when measured; if measured empty, fixture uses readiness only
    if (agg.get("measured_n") or 0) >= 1:
        tool_use_ok = bool(ready.get("checks", {}).get("tool_turns_gate_script") and agg.get("quality_ok"))
        # buyer doc required for product surface
        tool_use_ok = tool_use_ok and bool(ready.get("checks", {}).get("buyer_doc"))

    return {
        "feature": FEATURE,
        "schema_version": SCHEMA,
        "at": _now(),
        "one_liner": "Agent tool-use quality: tools-as-code chart, not SOUL prose",
        "scorecard_target": "simplicity / JTBD (dims 12 + 3)",
        "dim_lift": "merge-authority agent uses tools; zero-tool APPROVE fail-closed",
        "readiness": ready,
        "aggregate": agg,
        "dogfood_n": len(rows),
        "tool_use_ok": tool_use_ok,
        "recent_rows": rows[-12:],
        "paths": {
            "md": str(OUT_MD),
            "json": str(OUT_JSON),
            "buyer_doc": str(BUYER_DOC),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    ready = report.get("readiness") or {}
    checks = ready.get("checks") or {}
    agg = report.get("aggregate") or {}
    rows = report.get("recent_rows") or []
    lines = [
        MARKER,
        "",
        "# Agent tool-use quality",
        "",
        f"_Generated: `{report.get('at')}` · feature **{FEATURE}** · "
        f"tool_use_ok=`{report.get('tool_use_ok')}`_",
        "",
        f"**One-liner:** {report.get('one_liner')}",
        "",
        "Buyer story: the merge-authority agent **reads the change with tools** — "
        "not a chat-only skim. Fail-closed `tool_turns_gate` blocks empty APPROVE.",
        "",
        f"Buyer doc: [`docs/TOOL-USE.md`](../TOOL-USE.md) · "
        f"Quieter: [`quieter-over-time.md`](quieter-over-time.md)",
        "",
        "## Readiness (tools-as-code)",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| checks ok | {ready.get('ok_n')}/{ready.get('total')} |",
        f"| catalog adopted | {ready.get('catalog_adopted')}/{ready.get('catalog_tools')} |",
        "",
        "| Check | Pass |",
        "|-------|:----:|",
    ]
    for k, v in checks.items():
        lines.append(f"| `{k}` | {'yes' if v else 'no'} |")

    bands = agg.get("band_counts") or {}
    lines += [
        "",
        "## Dogfood aggregate",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| measured runs | {agg.get('measured_n')} |",
        f"| tool_use_rate | {agg.get('tool_use_rate')} |",
        f"| mean / median turns | {agg.get('mean_turns')} / {agg.get('median_turns')} |",
        f"| zero-tool rate | {agg.get('zero_tool_rate')} (n={agg.get('zero_tool_n')}) |",
        f"| solid+ rate (≥3 turns) | {agg.get('solid_plus_rate')} |",
        f"| deep rate (≥5 turns) | {agg.get('deep_rate')} |",
        f"| quality_score | {agg.get('quality_score')} |",
        f"| quality_ok | {agg.get('quality_ok')} |",
        "",
        "### Quality bands",
        "",
        "| Band | count |",
        "|------|------:|",
    ]
    for band in ("deep", "solid", "minimal", "zero", "unknown"):
        if band in bands:
            lines.append(f"| {band} | {bands[band]} |")
    for band, c in sorted(bands.items()):
        if band not in ("deep", "solid", "minimal", "zero", "unknown"):
            lines.append(f"| {band} | {c} |")

    tops = agg.get("top_tools") or []
    if tops:
        lines += ["", "### Top tools (from agent-loop when present)", "", "| Tool | n |", "|------|--:|"]
        for t in tops:
            lines.append(f"| `{t.get('name')}` | {t.get('n')} |")

    lines += [
        "",
        "## Recent dogfood rows",
        "",
        "| trace | repo | pr | turns | band | loop |",
        "|-------|------|---:|------:|------|:----:|",
    ]
    for r in rows[-12:]:
        lines.append(
            f"| `{str(r.get('trace_id') or '')[:48]}` | {r.get('repo')} | {r.get('pr')} | "
            f"{r.get('tool_call_turns')} | {r.get('quality_band')} | "
            f"{'yes' if r.get('has_agent_loop') else ''} |"
        )

    lines += [
        "",
        "## Refresh",
        "",
        "```bash",
        "python3 scripts/tool_use_quality.py report",
        "python3 scripts/torii.py tool-use -- status",
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
        print(
            f"\n# wrote {md_path.relative_to(root)} · {js_path.relative_to(root)}",
            file=sys.stderr,
        )
    return 0 if report.get("tool_use_ok") or getattr(args, "allow_partial", False) else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    ready = readiness(root)
    script_ok = (root / "scripts" / "tool_use_quality.py").is_file()
    buyer_ok = (root / BUYER_DOC).is_file()
    gate_ok = bool(ready.get("checks", {}).get("tool_turns_gate_script"))
    fit_ok = bool(ready.get("checks", {}).get("trajectory_fitness_script"))
    fixture_pass = script_ok and buyer_ok and gate_ok and fit_ok and bool(
        ready.get("checks", {}).get("tool_turns_default_on")
    )
    out = {
        "feature": FEATURE,
        "fixture_pass": fixture_pass,
        "buyer_doc_ok": buyer_ok,
        "tool_turns_gate_ok": gate_ok,
        "trajectory_fitness_ok": fit_ok,
        "readiness_ok_n": ready.get("ok_n"),
        "readiness_total": ready.get("total"),
        "catalog_adopted": ready.get("catalog_adopted"),
        "scorecard_target": "simplicity / JTBD",
    }
    print(json.dumps(out, indent=2))
    return 0 if fixture_pass else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    agg = report.get("aggregate") or {}
    slim = {
        "feature": FEATURE,
        "tool_use_ok": report.get("tool_use_ok"),
        "readiness_ok": (report.get("readiness") or {}).get("ok"),
        "measured_n": agg.get("measured_n"),
        "tool_use_rate": agg.get("tool_use_rate"),
        "mean_turns": agg.get("mean_turns"),
        "zero_tool_rate": agg.get("zero_tool_rate"),
        "quality_score": agg.get("quality_score"),
        "quality_ok": agg.get("quality_ok"),
        "at": report.get("at"),
    }
    print(json.dumps(slim, indent=2))
    return 0 if report.get("tool_use_ok") else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Agent tool-use quality (tools-as-code)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="Write tool-use-quality.md + json from vault")
    r.add_argument("--json", action="store_true")
    r.add_argument("--allow-partial", action="store_true")
    r.set_defaults(func=cmd_report)

    f = sub.add_parser("fixture", help="Hermetic readiness of tool-use surface")
    f.set_defaults(func=cmd_fixture)

    s = sub.add_parser("status", help="Short JSON status")
    s.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
