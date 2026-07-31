#!/usr/bin/env python3
"""F68: Agent tools pipeline — research → eval → adopt.

Torii control-plane (not Hermes fork). Turns run evidence + ROI backlog into
structured tool candidates, scores them offline, and promotes winners into
``agent/tools/catalog.json`` + ``agent/tools/adopted/``.

Usage:
  python3 scripts/agent_tools_pipeline.py research [--runs DIR] [--out OUT]
  python3 scripts/agent_tools_pipeline.py eval [--candidate ID|all]
  python3 scripts/agent_tools_pipeline.py adopt CANDIDATE_ID [--force]
  python3 scripts/agent_tools_pipeline.py status
  python3 scripts/agent_tools_pipeline.py toolsets   # print active TORII_TOOLSETS

Env:
  TORII_ROOT                 repo root (default: parent of scripts/)
  TORII_AGENT_TOOLS_AUTO_ADOPT=0|1  (default 0 — human gate for adopt)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _catalog_path(root: Path) -> Path:
    return root / "agent" / "tools" / "catalog.json"


def _load_catalog(root: Path) -> dict[str, Any]:
    path = _catalog_path(root)
    if not path.is_file():
        return {
            "schema_version": 1,
            "feature": "F68",
            "tools": [],
            "candidates": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("tools", [])
    data.setdefault("candidates", [])
    return data


def _save_catalog(root: Path, data: dict[str, Any]) -> Path:
    path = _catalog_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    data["schema_version"] = 1
    data["feature"] = "F68"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", s.strip().lower())
    return s.strip("-")[:64] or "tool"


def _iter_agent_loops(runs_dir: Path) -> list[Path]:
    if not runs_dir.is_dir():
        return []
    out: list[Path] = []
    for p in runs_dir.rglob("agent-loop.json"):
        if "node_modules" in p.parts:
            continue
        out.append(p)
    return sorted(out)


def _scan_loop(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {"path": str(path), "error": "invalid_json"}
    turns = data.get("tool_call_turns")
    if turns is None:
        turns = data.get("tool_turns")
    try:
        turns_i = int(turns) if turns is not None else 0
    except (TypeError, ValueError):
        turns_i = 0
    tools: list[str] = []
    for step in data.get("steps") or []:
        if not isinstance(step, dict):
            continue
        name = step.get("tool") or step.get("name") or step.get("tool_name")
        if name:
            tools.append(str(name))
        for tc in step.get("tool_calls") or []:
            if isinstance(tc, dict):
                n = tc.get("name") or tc.get("tool")
                if n:
                    tools.append(str(n))
    for msg in data.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        for tc in msg.get("tool_calls") or []:
            if isinstance(tc, dict):
                fn = tc.get("function") or tc
                if isinstance(fn, dict):
                    n = fn.get("name")
                    if n:
                        tools.append(str(n))
    # unique preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for t in tools:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return {
        "path": str(path),
        "tool_call_turns": turns_i,
        "message_count": data.get("message_count") or len(data.get("messages") or []),
        "tools": uniq,
        "model": data.get("model"),
        "session_id": data.get("session_id"),
    }


def _scan_roi_backlog(root: Path) -> list[dict[str, Any]]:
    """Mine unfinished hermes-inspired ROI rows as tool/research ideas."""
    roi = root / "docs" / "experiments" / "hermes-inspired-roi.md"
    if not roi.is_file():
        return []
    ideas: list[dict[str, Any]] = []
    for line in roi.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("| H"):
            continue
        if "backlog" not in line.lower() and "P2" not in line:
            continue
        # | H3 | Skill-file evolution ... | L | ... | backlog |
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4:
            continue
        hid, title = parts[0], parts[1]
        if "shipped" in line.lower() or "**Shipped" in line:
            continue
        ideas.append(
            {
                "id": _slug(f"roi-{hid}"),
                "name": f"{hid}: {title[:80]}",
                "source": "hermes_roi_backlog",
                "evidence": [f"docs/experiments/hermes-inspired-roi.md:{hid}"],
                "rationale": title,
                "kind": "research_pattern",
            }
        )
    return ideas


# Built-in research hypotheses mapped from evidence patterns → tool candidates
_PATTERN_CANDIDATES = [
    {
        "id": "diff-hunk-reader",
        "name": "Diff hunk reader (prefer pr.diff over head)",
        "match": lambda scans: any(s.get("tool_call_turns", 0) == 0 for s in scans)
        or any(s.get("tool_call_turns", 0) == 1 for s in scans),
        "toolset_hint": "terminal",
        "rationale": "Zero/one-tool first passes need forced diff-hunk inspection (H26/F51)",
        "kind": "workflow_tool",
    },
    {
        "id": "test-gap-scanner",
        "name": "Test-gap scanner for claim-to-fix PRs",
        "match": lambda scans: len(scans) >= 1,
        "toolset_hint": "terminal",
        "rationale": "F50 severity calibration needs evidence of missing tests near changed paths",
        "kind": "workflow_tool",
    },
    {
        "id": "symbol-range-reader",
        "name": "Symbol + line-range reader (rg + sed)",
        "match": lambda scans: any(
            t in (s.get("tools") or [])
            for s in scans
            for t in ("terminal", "bash", "shell")
        )
        or any(s.get("tool_call_turns", 0) >= 5 for s in scans),
        "toolset_hint": "terminal",
        "rationale": "Successful deep runs use rg/sed ranges — codify as preferred tool pattern",
        "kind": "workflow_tool",
    },
]


def cmd_research(args: argparse.Namespace) -> int:
    root = _root()
    runs = Path(args.runs) if args.runs else root
    scans = [_scan_loop(p) for p in _iter_agent_loops(runs)]
    scans = [s for s in scans if "error" not in s]

    catalog = _load_catalog(root)
    adopted_ids = {t.get("id") for t in catalog.get("tools") or [] if t.get("status") == "adopted"}
    cand_ids = {c.get("id") for c in catalog.get("candidates") or []}

    new_cands: list[dict[str, Any]] = []

    # Pattern-based candidates
    zero = sum(1 for s in scans if s.get("tool_call_turns", 0) == 0)
    deep = sum(1 for s in scans if s.get("tool_call_turns", 0) >= 10)
    for spec in _PATTERN_CANDIDATES:
        if not spec["match"](scans):
            continue
        cid = spec["id"]
        if cid in adopted_ids or cid in cand_ids:
            continue
        new_cands.append(
            {
                "id": cid,
                "name": spec["name"],
                "status": "candidate",
                "source": "run_evidence",
                "kind": spec["kind"],
                "toolset_hint": spec["toolset_hint"],
                "rationale": spec["rationale"],
                "evidence": {
                    "agent_loops_scanned": len(scans),
                    "zero_tool_runs": zero,
                    "deep_tool_runs": deep,
                    "sample_paths": [s["path"] for s in scans[:5]],
                },
                "eval": None,
                "researched_at": _now(),
            }
        )

    # ROI backlog ideas
    for idea in _scan_roi_backlog(root):
        if idea["id"] in adopted_ids or idea["id"] in cand_ids:
            continue
        if any(c["id"] == idea["id"] for c in new_cands):
            continue
        new_cands.append(
            {
                **idea,
                "status": "candidate",
                "toolset_hint": "terminal",
                "eval": None,
                "researched_at": _now(),
            }
        )

    # Aggregate observed tool names as micro-candidates
    tool_freq: dict[str, int] = {}
    for s in scans:
        for t in s.get("tools") or []:
            tool_freq[t] = tool_freq.get(t, 0) + 1
    for tname, freq in sorted(tool_freq.items(), key=lambda x: -x[1])[:8]:
        cid = _slug(f"observed-{tname}")
        if cid in adopted_ids or cid in cand_ids:
            continue
        if any(c["id"] == cid for c in new_cands):
            continue
        if tname in ("terminal", "bash", "shell"):
            continue  # already adopted base
        new_cands.append(
            {
                "id": cid,
                "name": f"Observed tool: {tname}",
                "status": "candidate",
                "source": "agent_loop_observation",
                "kind": "observed_tool",
                "toolset_hint": tname,
                "rationale": f"Seen in {freq} agent-loop scan(s)",
                "evidence": {"frequency": freq},
                "eval": None,
                "researched_at": _now(),
            }
        )

    catalog["candidates"] = list(catalog.get("candidates") or []) + new_cands
    path = _save_catalog(root, catalog)

    # Persist research report
    report_dir = root / "agent" / "tools" / "candidates"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "feature": "F68",
        "researched_at": _now(),
        "loops_scanned": len(scans),
        "new_candidates": [c["id"] for c in new_cands],
        "zero_tool_runs": zero,
        "deep_tool_runs": deep,
        "tool_frequency": tool_freq,
    }
    rpath = report_dir / f"research-{_now().replace(':', '')}.json"
    rpath.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"catalog={path}")
    print(f"new_candidates={len(new_cands)}")
    print(f"loops_scanned={len(scans)}")
    print(f"report={rpath}")
    for c in new_cands:
        print(f"  + {c['id']}: {c['name']}")
    if not new_cands:
        print("  (no new candidates — catalog already has research hits)")
    return 0


def _score_candidate(c: dict[str, Any], scans: list[dict[str, Any]]) -> dict[str, Any]:
    """Offline heuristic eval (1–5 dims). Judgment for production still human."""
    evidence = c.get("evidence") or {}
    if isinstance(evidence, list):
        ev_n = len(evidence)
        zero = 0
        deep = 0
    else:
        ev_n = int(evidence.get("agent_loops_scanned") or evidence.get("frequency") or 1)
        zero = int(evidence.get("zero_tool_runs") or 0)
        deep = int(evidence.get("deep_tool_runs") or 0)

    # dims
    signal = min(5, 2 + (1 if zero else 0) + (1 if deep else 0) + (1 if ev_n >= 3 else 0))
    safety = 5 if c.get("kind") in ("workflow_tool", "research_pattern") else 3
    if c.get("kind") == "observed_tool":
        safety = 2  # unknown tool names need review
    effort = 4 if c.get("kind") == "workflow_tool" else 2
    if str(c.get("source") or "").startswith("hermes") or c.get("source") == "hermes_roi_backlog":
        effort = 2  # large research items
    fit = 5 if c.get("toolset_hint") == "terminal" else 3
    cost = 4 if c.get("kind") == "workflow_tool" else 3

    total = signal + safety + effort + fit + cost  # /25
    recommend = "adopt" if total >= 18 and safety >= 3 and c.get("kind") != "observed_tool" else "hold"
    if c.get("kind") == "research_pattern":
        recommend = "design"  # not a wireable toolset yet
    if c.get("kind") == "observed_tool":
        recommend = "hold"

    return {
        "scored_at": _now(),
        "dims": {
            "signal": signal,
            "safety": safety,
            "effort": effort,
            "torii_fit": fit,
            "cost": cost,
        },
        "total": total,
        "max": 25,
        "recommend": recommend,
        "notes": (
            f"zero_tool_runs={zero} deep_tool_runs={deep} evidence_n={ev_n} "
            f"kind={c.get('kind')}"
        ),
    }


def cmd_eval(args: argparse.Namespace) -> int:
    root = _root()
    catalog = _load_catalog(root)
    runs = Path(args.runs) if args.runs else root
    scans = [_scan_loop(p) for p in _iter_agent_loops(runs)]
    scans = [s for s in scans if "error" not in s]

    target = (args.candidate or "all").strip()
    updated = 0
    for c in catalog.get("candidates") or []:
        if target not in ("all", c.get("id")):
            continue
        c["eval"] = _score_candidate(c, scans)
        c["status"] = "evaluated"
        updated += 1
        e = c["eval"]
        print(
            f"{c['id']}: total={e['total']}/25 recommend={e['recommend']} "
            f"dims={e['dims']}"
        )

    _save_catalog(root, catalog)
    print(f"evaluated={updated}")
    return 0 if updated else 1


def cmd_adopt(args: argparse.Namespace) -> int:
    root = _root()
    auto = (os.environ.get("TORII_AGENT_TOOLS_AUTO_ADOPT") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if not args.force and not auto:
        # Explicit CLI adopt is allowed (operator action); env auto is for CI
        pass

    catalog = _load_catalog(root)
    cid = args.candidate_id.strip()
    cand = None
    for c in list(catalog.get("candidates") or []):
        if c.get("id") == cid:
            cand = c
            break
    if not cand:
        print(f"error: candidate not found: {cid}", file=sys.stderr)
        return 1

    ev = cand.get("eval") or {}
    rec = (ev.get("recommend") or "").lower()
    if rec in ("hold", "design") and not args.force:
        print(
            f"error: candidate recommend={rec}; re-eval or pass --force",
            file=sys.stderr,
        )
        return 2

    adopted = {
        "id": cand["id"],
        "name": cand.get("name") or cand["id"],
        "status": "adopted",
        "source": cand.get("source") or "research",
        "kind": cand.get("kind"),
        "toolset": cand.get("toolset_hint") or "terminal",
        "rationale": cand.get("rationale"),
        "eval": ev,
        "adopted_at": _now(),
        "feature": "F68",
    }
    tools = [t for t in (catalog.get("tools") or []) if t.get("id") != cid]
    tools.append(adopted)
    catalog["tools"] = tools
    catalog["candidates"] = [c for c in (catalog.get("candidates") or []) if c.get("id") != cid]

    adopted_dir = root / "agent" / "tools" / "adopted"
    adopted_dir.mkdir(parents=True, exist_ok=True)
    apath = adopted_dir / f"{cid}.json"
    apath.write_text(json.dumps(adopted, indent=2) + "\n", encoding="utf-8")

    # Active toolsets file for hermes / env wiring
    _write_active_toolsets(root, catalog)

    _save_catalog(root, catalog)
    print(f"adopted={cid}")
    print(f"file={apath}")
    print(f"toolset={adopted['toolset']}")
    return 0


def _write_active_toolsets(root: Path, catalog: dict[str, Any]) -> Path:
    """Comma-separated toolsets for TORII_TOOLSETS consumers."""
    sets: list[str] = []
    for t in catalog.get("tools") or []:
        if t.get("status") != "adopted":
            continue
        ts = str(t.get("toolset") or t.get("toolset_hint") or "").strip()
        if ts and ts not in sets:
            sets.append(ts)
    if "terminal" not in sets:
        sets.insert(0, "terminal")
    path = root / "agent" / "tools" / "active-toolsets.txt"
    path.write_text(",".join(sets) + "\n", encoding="utf-8")
    # also env snippet
    envp = root / "agent" / "tools" / "active-toolsets.env"
    envp.write_text(f"TORII_TOOLSETS={','.join(sets)}\n", encoding="utf-8")
    return path


def cmd_toolsets(args: argparse.Namespace) -> int:
    root = _root()
    catalog = _load_catalog(root)
    path = root / "agent" / "tools" / "active-toolsets.txt"
    if path.is_file():
        print(path.read_text(encoding="utf-8").strip())
        return 0
    _write_active_toolsets(root, catalog)
    print(path.read_text(encoding="utf-8").strip())
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    catalog = _load_catalog(root)
    tools = catalog.get("tools") or []
    cands = catalog.get("candidates") or []
    print(f"catalog={_catalog_path(root)}")
    print(f"adopted={sum(1 for t in tools if t.get('status')=='adopted')}")
    print(f"candidates={len(cands)}")
    print(f"evaluated={sum(1 for c in cands if c.get('eval'))}")
    for t in tools:
        print(f"  [tool] {t.get('id')} status={t.get('status')} toolset={t.get('toolset')}")
    for c in cands:
        rec = (c.get("eval") or {}).get("recommend", "-")
        tot = (c.get("eval") or {}).get("total", "-")
        print(f"  [cand] {c.get('id')} status={c.get('status')} score={tot} recommend={rec}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F68 agent tools research→eval→adopt")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("research", help="Scan runs + ROI backlog → candidates")
    pr.add_argument("--runs", default="", help="Root to scan for agent-loop.json")
    pr.set_defaults(func=cmd_research)

    pe = sub.add_parser("eval", help="Offline-score candidates")
    pe.add_argument("--candidate", default="all")
    pe.add_argument("--runs", default="")
    pe.set_defaults(func=cmd_eval)

    pa = sub.add_parser("adopt", help="Promote a candidate into catalog tools")
    pa.add_argument("candidate_id")
    pa.add_argument("--force", action="store_true")
    pa.set_defaults(func=cmd_adopt)

    sub.add_parser("status", help="Print catalog summary").set_defaults(func=cmd_status)
    sub.add_parser("toolsets", help="Print active TORII_TOOLSETS value").set_defaults(
        func=cmd_toolsets
    )

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
