#!/usr/bin/env python3
"""F105: Audit mid-review memory tool use (measure the F103/F104 front door).

Research drivers:
  - IFCMemoryBench / WorldMemArena: decompose memory into ingestion · retrieval ·
    utilization — Torii had write+inject but not measured retrieval utilization.
  - Loop-eng: score the loop, do not assume SOUL prose was followed.
  - MemGPT/Letta: memory tools only help if the agent actually calls them.

Product thesis:
  F103 shipped a discoverable CLI; F104 compounds post-review writes. Highest ROI
  now is a **deterministic auditor** on agent-loop/tool args that scores whether
  Hermes invoked memory tools (search/graph/tiers/compound/…) mid-review, so
  fitness + traces can prove utilization — not just inject presence.

Commands:
  scan            — extract memory tool invocations from agent-loop / log
  score           — scan + 0–1 utilization score + readiness flags
  inject          — write memory-tool-audit section into a prompt (soft rubric)
  audit           — score a run dir (agent-loop under out_dir)
  reprompt-decide — F106: whether to soft re-prompt on utilization gap
  reprompt-write  — F106: append memory-tool nudge to prompt
  fixture         — hermetic good (memory cmds) vs weak (no memory cmds) + re-prompt
  util-eval       — F130 paper pack: memory util good/weak scores for product scorecard
  status          — feature + toggle

Env:
  TORII_ROOT
  TORII_MEMORY_TOOL_AUDIT     1 (default) | 0
  TORII_MEMORY_TOOL_FITNESS   1 (default) | 0  — soft blend into trajectory fitness
  TORII_MEMORY_TOOL_REPROMPT  1 (default) | 0  — F106 soft re-prompt once on gap
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F105"
FEATURE_REPROMPT = "F106"
FEATURE_UTIL_EVAL = "F130"
SCHEMA = 1
MARKER = "<!-- torii-f105-memory-tool-audit -->"
REPROMPT_MARKER = "## Soft re-prompt (Torii F106 / memory tools)"
REPORT_NAME = "memory-tool-audit.json"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

# Patterns that prove memory-tool utilization (terminal / args / log)
_MEMORY_CMD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("torii_memory", re.compile(r"torii_memory\.py\b", re.I)),
    # F114: product umbrella CLI (F110) — skill-prefer-memory-cli-early teaches this
    ("torii_product_memory", re.compile(r"torii\.py\s+memory\b", re.I)),
    ("archival_search", re.compile(r"archival_memory_search\.py\b", re.I)),
    ("memory_graph", re.compile(r"memory_temporal_graph\.py\b", re.I)),
    ("memory_tiers", re.compile(r"memory_tiers\.py\b", re.I)),
    ("memory_compound", re.compile(r"memory_compound_write\.py\b", re.I)),
    ("scoped_recall", re.compile(r"scoped_memory_recall\.py\b", re.I)),
    ("memory_events", re.compile(r"memory_event_policy\.py\b", re.I)),
    ("memory_consolidate", re.compile(r"memory_consolidate\.py\b", re.I)),
    ("memory_loop", re.compile(r"memory_loop_status\.py\b", re.I)),
]

# Subcommand hints when using unified CLI (F103) or product front door (F110/F114)
_CLI_SUBCMDS = re.compile(
    r"(?:torii_memory\.py|torii\.py\s+memory(?:\s+--)?)\s+"
    r"(?:help|status|doctor|search|search-auto|promote|"
    r"graph|tiers|consolidate|events|recall|loop|federate|compound|inject-hint)\b",
    re.I,
)

# Inject markers that mean memory tools were offered this run
_INJECT_MARKERS = (
    "<!-- torii-f103-memory-cli -->",
    "<!-- torii-f98-archival",
    "<!-- torii-f100-memory-graph -->",
    "<!-- torii-f70-tp-signatures -->",
    "Memory tools (F103",
    "torii_memory.py help",
    "torii.py memory",
)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_TOOL_AUDIT") or "1").strip().lower()
    return raw not in _FALSEY


def fitness_blend_enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_TOOL_FITNESS") or "1").strip().lower()
    return raw not in _FALSEY


def reprompt_enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_TOOL_REPROMPT") or "1").strip().lower()
    return raw not in _FALSEY


def _collect_text_blobs(loop: dict[str, Any], log_text: str = "") -> list[str]:
    blobs: list[str] = []
    for s in loop.get("steps") or []:
        if not isinstance(s, dict):
            continue
        for c in s.get("tool_calls") or []:
            if isinstance(c, dict):
                blobs.append(str(c.get("arguments_preview") or c.get("arguments") or ""))
                blobs.append(str(c.get("name") or ""))
            else:
                blobs.append(str(c))
        blobs.append(str(s.get("content_preview") or ""))
        if s.get("tool_name"):
            blobs.append(str(s.get("tool_name")))
    for m in loop.get("messages") or []:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if isinstance(content, str):
            blobs.append(content[:4000])
        tc = m.get("tool_calls")
        if isinstance(tc, list):
            for c in tc:
                if isinstance(c, dict):
                    fn = c.get("function") or c
                    if isinstance(fn, dict):
                        blobs.append(str(fn.get("arguments") or "")[:2000])
                        blobs.append(str(fn.get("name") or ""))
    if log_text:
        blobs.append(log_text[:120_000])
    return blobs


def scan_blobs(blobs: list[str]) -> dict[str, Any]:
    """Scan text blobs for memory tool invocations."""
    hits: list[dict[str, Any]] = []
    by_tool: dict[str, int] = {}
    subcmds: dict[str, int] = {}
    seen_snip: set[str] = set()

    for blob in blobs:
        if not blob:
            continue
        low = blob
        for tool_id, rx in _MEMORY_CMD_PATTERNS:
            for m in rx.finditer(low):
                # context snip
                start = max(0, m.start() - 40)
                end = min(len(low), m.end() + 80)
                snip = re.sub(r"\s+", " ", low[start:end]).strip()[:160]
                key = f"{tool_id}:{snip[:80]}"
                if key in seen_snip:
                    continue
                seen_snip.add(key)
                hits.append({"tool": tool_id, "snip": snip})
                by_tool[tool_id] = by_tool.get(tool_id, 0) + 1
        for m in _CLI_SUBCMDS.finditer(low):
            cmd = m.group(0).split()[-1].lower()
            subcmds[cmd] = subcmds.get(cmd, 0) + 1

    return {
        "hit_count": len(hits),
        "hits": hits[:40],
        "by_tool": by_tool,
        "cli_subcmds": subcmds,
        "tools_used": sorted(by_tool.keys()),
    }


def detect_inject_offered(prompt_text: str = "", context_text: str = "") -> bool:
    blob = (prompt_text or "") + "\n" + (context_text or "")
    return any(m in blob for m in _INJECT_MARKERS)


def score_utilization(
    scan: dict[str, Any],
    *,
    inject_offered: bool = False,
    tool_call_turns: int = 0,
) -> dict[str, Any]:
    """0–1 memory utilization score + flags."""
    hits = int(scan.get("hit_count") or 0)
    tools_n = len(scan.get("tools_used") or [])
    sub_n = len(scan.get("cli_subcmds") or {})

    # Base score from hits
    if hits >= 3 and tools_n >= 2:
        base = 1.0
    elif hits >= 2 or (hits >= 1 and sub_n >= 1):
        base = 0.85
    elif hits >= 1:
        base = 0.7
    elif inject_offered and tool_call_turns >= 1:
        # tools used but memory ignored despite inject
        base = 0.15
    elif inject_offered and tool_call_turns == 0:
        base = 0.1
    else:
        # no inject offered — memory tools optional; neutral-low
        base = 0.45 if tool_call_turns >= 1 else 0.35

    # Bonus for unified CLI front door (F103) or product umbrella (F110/F114)
    used = set(scan.get("tools_used") or [])
    if "torii_memory" in used or "torii_product_memory" in used:
        base = min(1.0, base + 0.1)
    if scan.get("cli_subcmds"):
        base = min(1.0, base + 0.05)

    gap = bool(inject_offered and hits == 0 and tool_call_turns >= 1)
    feedback: list[str] = []
    if hits:
        feedback.append(
            f"memory_tools_used={tools_n} hits={hits} tools={scan.get('tools_used')}"
        )
    elif inject_offered:
        feedback.append(
            "memory_inject_offered_but_unused — prefer "
            "`python3 scripts/torii.py memory -- search` or "
            "`python3 scripts/torii_memory.py search|graph` before re-raising themes"
        )
    else:
        feedback.append("no_memory_tool_hits (inject not detected or optional)")

    level = "L3" if base >= 0.85 else "L2" if base >= 0.55 else "L1" if base >= 0.3 else "L0"

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "score": round(base, 4),
        "level": level,
        "hit_count": hits,
        "tools_used": scan.get("tools_used") or [],
        "by_tool": scan.get("by_tool") or {},
        "cli_subcmds": scan.get("cli_subcmds") or {},
        "inject_offered": inject_offered,
        "utilization_gap": gap,
        "tool_call_turns": tool_call_turns,
        "feedback": feedback,
        "scored_at": _now(),
    }


def load_loop(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def audit_run(
    out_dir: Path,
    *,
    loop_path: Path | None = None,
    prompt_path: Path | None = None,
    log_path: Path | None = None,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    loop_p = loop_path or (out_dir / "agent-loop" / "agent-loop.json")
    loop = load_loop(loop_p)

    log_text = ""
    for cand in (
        log_path,
        out_dir / "agent-loop" / "agent.log",
        out_dir / "hermes-run.log",
    ):
        if cand and Path(cand).is_file():
            try:
                log_text = Path(cand).read_text(encoding="utf-8", errors="replace")[
                    :120_000
                ]
            except OSError:
                pass
            break

    prompt_text = ""
    for cand in (
        prompt_path,
        out_dir / "prompt.md",
        out_dir / "prompt-final.md",
        out_dir / "context.md",
    ):
        if cand and Path(cand).is_file():
            try:
                prompt_text += Path(cand).read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

    blobs = _collect_text_blobs(loop, log_text)
    scan = scan_blobs(blobs)
    turns = int(loop.get("tool_call_turns") or 0)
    if not turns:
        turns = sum(
            1
            for s in (loop.get("steps") or [])
            if isinstance(s, dict)
            and (
                s.get("kind") == "assistant_tool_calls"
                or s.get("tool_calls")
            )
        )
    inject = detect_inject_offered(prompt_text)
    report = score_utilization(
        scan, inject_offered=inject, tool_call_turns=turns
    )
    report["hits_detail"] = scan.get("hits") or []
    report["out_dir"] = str(out_dir)
    report["loop_path"] = str(loop_p) if loop_p.is_file() else None
    report["enabled"] = enabled()

    dest = out_dir / REPORT_NAME
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        report["report_path"] = str(dest)
    except OSError:
        report["report_path"] = None
    return report


def render_inject_section() -> str:
    return (
        f"{MARKER}\n"
        "## Memory tool utilization (F105)\n\n"
        "When memory sections are injected (F103 CLI / F98 archival / F100 graph / F70 TP),\n"
        "prefer **calling** them mid-review via terminal before re-raising old themes:\n\n"
        "```bash\n"
        "python3 scripts/torii.py memory -- help\n"
        "python3 scripts/torii.py memory -- search -- -q \"theme keywords\"\n"
        "python3 scripts/torii_memory.py search -- -q \"theme keywords\"\n"
        "python3 scripts/torii_memory.py graph -- query --path <file> --hops 2\n"
        "```\n\n"
        "Post-run auditor scores whether these tools were used (not only offered).\n"
        "Still require path:line evidence to block.\n"
        "<!-- /torii-f105-memory-tool-audit -->\n"
    )


def inject_prompt(prompt_path: Path) -> bool:
    if not enabled():
        return False
    section = render_inject_section()
    text = (
        prompt_path.read_text(encoding="utf-8", errors="replace")
        if prompt_path.is_file()
        else ""
    )
    if MARKER in text:
        text = re.sub(
            rf"{re.escape(MARKER)}[\s\S]*?(?=\n<!--|\Z)",
            section.rstrip() + "\n",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + "\n\n" + section
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return True


def should_reprompt(
    audit: dict[str, Any],
    *,
    already_reprompted: bool = False,
    reprompt_on: bool | None = None,
) -> dict[str, Any]:
    """F106: soft re-prompt once when memory inject offered but unused after tools.

    Mirrors F49 tool-turns re-prompt, but targets **utilization gap**:
    inject_offered ∧ hit_count==0 ∧ tool_call_turns≥1.
    Zero-tool cases remain F49's job (F106 does not stack when tools never ran).
    """
    on = reprompt_enabled() if reprompt_on is None else bool(reprompt_on)
    hits = int(audit.get("hit_count") or 0)
    turns = int(audit.get("tool_call_turns") or 0)
    inject = bool(audit.get("inject_offered"))
    gap = bool(audit.get("utilization_gap")) or (inject and hits == 0 and turns >= 1)
    out: dict[str, Any] = {
        "feature": FEATURE_REPROMPT,
        "reprompt": 0,
        "enabled": on,
        "reason": "ok",
        "hit_count": hits,
        "tool_call_turns": turns,
        "inject_offered": inject,
        "utilization_gap": gap,
        "already_reprompted": bool(already_reprompted),
        "score": audit.get("score"),
    }
    if not on:
        out["reason"] = "reprompt_off"
        return out
    if already_reprompted:
        out["reason"] = "already_reprompted"
        return out
    if not inject:
        out["reason"] = "inject_not_offered"
        return out
    if hits > 0:
        out["reason"] = "memory_tools_used"
        return out
    if turns < 1:
        # F49 owns zero-tool recovery; avoid double re-prompt storm
        out["reason"] = "zero_tools_defer_f49"
        return out
    out["reprompt"] = 1
    out["reason"] = "utilization_gap"
    return out


def build_memory_reprompt_suffix(
    *,
    hit_count: int = 0,
    tool_call_turns: int = 0,
    paths: list[str] | None = None,
) -> str:
    """Soft nudge: call torii_memory before finalizing review."""
    paths = [p for p in (paths or []) if p][:12]
    files_block = ""
    if paths:
        bullets = "\n".join(f"  - `{p}`" for p in paths)
        files_block = f"\nChanged paths (memory search seeds):\n{bullets}\n"
    seed = paths[0] if paths else "changed/file.py"
    return (
        "\n\n---\n\n"
        f"{REPROMPT_MARKER}\n\n"
        f"Your previous reply used **{tool_call_turns} tool turns** but "
        f"**{hit_count} memory-tool calls** despite injected memory CLI / "
        "archival / graph sections (F103–F105).\n\n"
        "Before finalizing, **once** use the Torii memory front door via terminal:\n\n"
        "```bash\n"
        "python3 scripts/torii_memory.py help\n"
        f'python3 scripts/torii_memory.py search -- -q "auth OR sql OR pickle OR secret"\n'
        f"python3 scripts/torii_memory.py graph -- query --path {seed} --hops 2\n"
        "```\n\n"
        "Treat hits as **hints only** — still require path:line evidence to block. "
        "If search returns nothing relevant, say so and continue the review.\n"
        f"{files_block}"
    )


def write_memory_reprompt_prompt(
    *,
    prompt_in: Path,
    prompt_out: Path,
    hit_count: int = 0,
    tool_call_turns: int = 0,
    paths: list[str] | None = None,
) -> str:
    base = prompt_in.read_text(encoding="utf-8", errors="replace")
    if REPROMPT_MARKER in base:
        text = base
    else:
        text = base.rstrip() + build_memory_reprompt_suffix(
            hit_count=hit_count,
            tool_call_turns=tool_call_turns,
            paths=paths,
        )
        if not text.endswith("\n"):
            text += "\n"
    prompt_out.parent.mkdir(parents=True, exist_ok=True)
    prompt_out.write_text(text, encoding="utf-8")
    return text


def blend_into_fitness(
    fitness: dict[str, Any], audit: dict[str, Any], *, weight: float = 0.08
) -> dict[str, Any]:
    """Soft-blend memory utilization into trajectory fitness composite.

    Small weight (default 0.08) so path evidence remains dominant; only when
    TORII_MEMORY_TOOL_FITNESS enabled.
    """
    if not fitness_blend_enabled():
        out = dict(fitness)
        out["memory_tool_audit"] = {
            "blended": False,
            "score": audit.get("score"),
            "reason": "fitness_blend_disabled",
        }
        return out
    mem_s = float(audit.get("score") or 0.0)
    comp = float(fitness.get("composite") or 0.0)
    # soft blend: composite' = (1-w)*comp + w*mem
    blended = (1.0 - weight) * comp + weight * mem_s
    blended = max(0.0, min(1.0, blended))
    out = dict(fitness)
    out["composite_before_memory_tool"] = comp
    out["composite"] = round(blended, 4)
    # recompute level
    if blended >= 0.85:
        out["level"] = "L3"
    elif blended >= 0.65:
        out["level"] = "L2"
    elif blended >= 0.4:
        out["level"] = "L1"
    else:
        out["level"] = "L0"
    fb = list(out.get("feedback") or [])
    for f in audit.get("feedback") or []:
        if f not in fb:
            fb.append(f)
    out["feedback"] = fb
    out["memory_tool_audit"] = {
        "blended": True,
        "weight": weight,
        "score": mem_s,
        "hit_count": audit.get("hit_count"),
        "utilization_gap": audit.get("utilization_gap"),
        "tools_used": audit.get("tools_used"),
        "feature": FEATURE,
    }
    sig = dict(out.get("signals") or {})
    sig["memory_tool_score"] = mem_s
    sig["memory_tool_weight"] = weight
    out["signals"] = sig
    return out


def _synthetic_loop(commands: list[str], *, turns: int | None = None) -> dict[str, Any]:
    steps = []
    for i, cmd in enumerate(commands):
        steps.append(
            {
                "step": i,
                "kind": "assistant_tool_calls",
                "tool_calls": [
                    {
                        "name": "terminal",
                        "arguments_preview": json.dumps({"command": cmd}),
                    }
                ],
            }
        )
        steps.append(
            {
                "step": i + 0.5,
                "kind": "tool_result",
                "tool_name": "terminal",
                "content_preview": f"ok: {cmd[:40]}",
            }
        )
    return {
        "schema_version": 1,
        "tool_call_turns": turns if turns is not None else len(commands),
        "steps": steps,
        "messages": [],
    }


def cmd_scan(args: argparse.Namespace) -> int:
    loop = load_loop(Path(args.loop)) if args.loop else {}
    log = ""
    if args.log:
        log = Path(args.log).read_text(encoding="utf-8", errors="replace")[:120_000]
    blobs = _collect_text_blobs(loop, log)
    if args.text:
        blobs.append(args.text)
    scan = scan_blobs(blobs)
    print(json.dumps({"feature": FEATURE, **scan}, indent=2))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    loop = load_loop(Path(args.loop)) if args.loop else {}
    log = ""
    if args.log:
        log = Path(args.log).read_text(encoding="utf-8", errors="replace")[:120_000]
    blobs = _collect_text_blobs(loop, log)
    scan = scan_blobs(blobs)
    inject = False
    if args.prompt:
        inject = detect_inject_offered(
            Path(args.prompt).read_text(encoding="utf-8", errors="replace")
        )
    turns = int(loop.get("tool_call_turns") or 0)
    report = score_utilization(scan, inject_offered=inject, tool_call_turns=turns)
    report["hits_detail"] = scan.get("hits") or []
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0
    report = audit_run(
        Path(args.out_dir),
        loop_path=Path(args.loop) if args.loop else None,
        prompt_path=Path(args.prompt) if args.prompt else None,
        log_path=Path(args.log) if args.log else None,
    )
    # optional fitness blend
    if args.fitness and Path(args.fitness).is_file():
        try:
            fit = json.loads(Path(args.fitness).read_text(encoding="utf-8"))
            blended = blend_into_fitness(fit, report)
            out_fit = Path(args.fitness)
            if args.fitness_out:
                out_fit = Path(args.fitness_out)
            out_fit.write_text(json.dumps(blended, indent=2) + "\n", encoding="utf-8")
            report["fitness_blended"] = True
            report["fitness_composite"] = blended.get("composite")
            report["fitness_path"] = str(out_fit)
        except Exception as exc:
            report["fitness_error"] = str(exc)[:160]
    print(json.dumps(report, indent=2))
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    ok = inject_prompt(Path(args.prompt))
    print(json.dumps({"feature": FEATURE, "injected": ok, "prompt": args.prompt}))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "reprompt_feature": FEATURE_REPROMPT,
                "enabled": enabled(),
                "fitness_blend": fitness_blend_enabled(),
                "reprompt_enabled": reprompt_enabled(),
                "patterns": [t for t, _ in _MEMORY_CMD_PATTERNS],
            },
            indent=2,
        )
    )
    return 0


def cmd_reprompt_decide(args: argparse.Namespace) -> int:
    """Stdout key=value for shell (F49-style) plus optional JSON."""
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        audit = audit_run(
            out_dir,
            loop_path=Path(args.loop) if args.loop else None,
            prompt_path=Path(args.prompt) if args.prompt else None,
        )
    else:
        loop = load_loop(Path(args.loop)) if args.loop else {}
        log = ""
        blobs = _collect_text_blobs(loop, log)
        scan = scan_blobs(blobs)
        inject = False
        if args.prompt and Path(args.prompt).is_file():
            inject = detect_inject_offered(
                Path(args.prompt).read_text(encoding="utf-8", errors="replace")
            )
        turns = int(loop.get("tool_call_turns") or 0)
        audit = score_utilization(scan, inject_offered=inject, tool_call_turns=turns)

    already = bool(args.already_reprompted)
    if args.already_env and Path(args.already_env).is_file():
        try:
            for line in Path(args.already_env).read_text().splitlines():
                if line.startswith("attempted=1") or line.startswith("reprompt=1"):
                    already = True
        except OSError:
            pass

    dec = should_reprompt(audit, already_reprompted=already)
    # shell-friendly
    print(f"reprompt={dec['reprompt']}")
    print(f"enabled={int(bool(dec['enabled']))}")
    print(f"reason={dec['reason']}")
    print(f"hit_count={dec['hit_count']}")
    print(f"tool_call_turns={dec['tool_call_turns']}")
    print(f"inject_offered={int(bool(dec['inject_offered']))}")
    print(f"utilization_gap={int(bool(dec['utilization_gap']))}")
    print(f"score={dec.get('score')}")
    if args.json:
        print(json.dumps(dec, indent=2), file=sys.stderr)
    return 0


def cmd_reprompt_write(args: argparse.Namespace) -> int:
    paths: list[str] = []
    if args.paths_file and Path(args.paths_file).is_file():
        paths = [
            ln.strip()
            for ln in Path(args.paths_file).read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
    for p in args.path or []:
        if p:
            paths.append(p)
    write_memory_reprompt_prompt(
        prompt_in=Path(args.prompt_in),
        prompt_out=Path(args.prompt_out),
        hit_count=int(args.hit_count or 0),
        tool_call_turns=int(args.tool_turns or 0),
        paths=paths,
    )
    print(
        json.dumps(
            {
                "feature": FEATURE_REPROMPT,
                "prompt_out": args.prompt_out,
                "written": True,
            }
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: good loop with memory cmds scores high; weak gap when inject offered."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        good_dir = td_path / "good"
        weak_dir = td_path / "weak"
        good_dir.mkdir()
        weak_dir.mkdir()
        (good_dir / "agent-loop").mkdir()
        (weak_dir / "agent-loop").mkdir()

        good_loop = _synthetic_loop(
            [
                "cat pr.diff",
                # F114: product CLI + legacy memory CLI both count as utilization
                'python3 scripts/torii.py memory -- search -- -q "sql injection"',
                "python3 scripts/torii_memory.py graph -- query --path app.py --hops 2",
                "rg -n execute app.py",
            ]
        )
        weak_loop = _synthetic_loop(
            [
                "cat pr.diff",
                "rg -n foo bar.py",
                "head -40 app.py",
            ]
        )
        (good_dir / "agent-loop" / "agent-loop.json").write_text(
            json.dumps(good_loop) + "\n"
        )
        (weak_dir / "agent-loop" / "agent-loop.json").write_text(
            json.dumps(weak_loop) + "\n"
        )
        # inject offered on both
        prompt = (
            "<!-- torii-f103-memory-cli -->\n"
            "## Memory tools (F103)\n"
            "python3 scripts/torii_memory.py help\n"
        )
        (good_dir / "prompt.md").write_text(prompt)
        (weak_dir / "prompt.md").write_text(prompt)

        good = audit_run(good_dir)
        weak = audit_run(weak_dir)

        # blend fitness
        base_fit = {
            "composite": 0.8,
            "level": "L2",
            "feedback": [],
            "signals": {},
        }
        good_fit = blend_into_fitness(base_fit, good)
        weak_fit = blend_into_fitness(dict(base_fit), weak)

        good_ok = (
            good["hit_count"] >= 2
            and good["score"] >= 0.7
            and "torii_memory" in good["tools_used"]
            and not good["utilization_gap"]
        )
        weak_ok = (
            weak["hit_count"] == 0
            and weak["utilization_gap"] is True
            and weak["score"] <= 0.3
        )
        delta = round(float(good["score"]) - float(weak["score"]), 4)
        delta_ok = delta >= 0.4
        blend_ok = float(good_fit["composite"]) > float(weak_fit["composite"])

        # inject round-trip
        inj_p = td_path / "p.md"
        inj_p.write_text("# p\n")
        inject_prompt(inj_p)
        inject_ok = MARKER in inj_p.read_text()

        # F106 re-prompt decide
        dec_weak = should_reprompt(weak, already_reprompted=False)
        dec_good = should_reprompt(good, already_reprompted=False)
        dec_already = should_reprompt(weak, already_reprompted=True)
        dec_zero = should_reprompt(
            {
                "hit_count": 0,
                "tool_call_turns": 0,
                "inject_offered": True,
                "utilization_gap": False,
                "score": 0.1,
            }
        )
        reprompt_ok = (
            dec_weak.get("reprompt") == 1
            and dec_weak.get("reason") == "utilization_gap"
            and dec_good.get("reprompt") == 0
            and dec_already.get("reprompt") == 0
            and dec_zero.get("reason") == "zero_tools_defer_f49"
        )

        # write nudge
        pin = td_path / "prompt-in.md"
        pout = td_path / "prompt-out.md"
        pin.write_text(prompt + "\n# review task\n")
        write_memory_reprompt_prompt(
            prompt_in=pin,
            prompt_out=pout,
            hit_count=0,
            tool_call_turns=3,
            paths=["app.py", "db.py"],
        )
        write_ok = REPROMPT_MARKER in pout.read_text() and "torii_memory.py search" in pout.read_text()

        fixture_pass = all(
            [good_ok, weak_ok, delta_ok, blend_ok, inject_ok, reprompt_ok, write_ok]
        )
        out = {
            "feature": FEATURE,
            "reprompt_feature": FEATURE_REPROMPT,
            "fixture_pass": fixture_pass,
            "good_score": good["score"],
            "weak_score": weak["score"],
            "delta": delta,
            "good_ok": good_ok,
            "weak_ok": weak_ok,
            "delta_ok": delta_ok,
            "blend_ok": blend_ok,
            "inject_ok": inject_ok,
            "reprompt_ok": reprompt_ok,
            "write_ok": write_ok,
            "dec_weak": dec_weak,
            "dec_good_reason": dec_good.get("reason"),
            "dec_zero_reason": dec_zero.get("reason"),
            "good_tools": good["tools_used"],
            "weak_gap": weak["utilization_gap"],
            "good_fit_composite": good_fit["composite"],
            "weak_fit_composite": weak_fit["composite"],
            "scored_at": _now(),
        }
        print(json.dumps(out, indent=2))
        return 0 if fixture_pass else 1


def util_eval(*, out_dir: Path | None = None) -> dict[str, Any]:
    """F130: paper-ready memory utilization pack (Mem0/Letta: tools must be called).

    Offline good (memory CLI hits) vs weak (inject offered, unused) → delta + rate.
    Same discipline as F128 critic demote-eval for product scorecard.
    """
    # reuse fixture hermetic cases via in-process logic
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        good_dir = td_path / "good"
        weak_dir = td_path / "weak"
        good_dir.mkdir()
        weak_dir.mkdir()
        (good_dir / "agent-loop").mkdir()
        (weak_dir / "agent-loop").mkdir()
        good_loop = _synthetic_loop(
            [
                "cat pr.diff",
                'python3 scripts/torii.py memory -- search -- -q "sql injection"',
                "python3 scripts/torii_memory.py graph -- query --path app.py --hops 2",
            ]
        )
        weak_loop = _synthetic_loop(
            ["cat pr.diff", "rg -n foo bar.py", "head -40 app.py"]
        )
        (good_dir / "agent-loop" / "agent-loop.json").write_text(
            json.dumps(good_loop) + "\n", encoding="utf-8"
        )
        (weak_dir / "agent-loop" / "agent-loop.json").write_text(
            json.dumps(weak_loop) + "\n", encoding="utf-8"
        )
        prompt = (
            "<!-- torii-f103-memory-cli -->\n"
            "## Memory tools\n"
            "python3 scripts/torii.py memory -- search\n"
        )
        (good_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        (weak_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        good = audit_run(good_dir)
        weak = audit_run(weak_dir)
        good_score = float(good.get("score") or 0)
        weak_score = float(weak.get("score") or 0)
        delta = round(good_score - weak_score, 4)
        good_ok = good_score >= 0.7 and int(good.get("hit_count") or 0) >= 1
        weak_gap_ok = bool(weak.get("utilization_gap")) and weak_score <= 0.35
        eval_pass = good_ok and weak_gap_ok and delta >= 0.4
        report: dict[str, Any] = {
            "feature": FEATURE_UTIL_EVAL,
            "feature_audit": FEATURE,
            "scored_at": _now(),
            "good_score": good_score,
            "weak_score": weak_score,
            "delta": delta,
            "good_hit_count": good.get("hit_count"),
            "weak_utilization_gap": weak.get("utilization_gap"),
            "good_ok": good_ok,
            "weak_gap_ok": weak_gap_ok,
            "eval_pass": eval_pass,
            "paper": {
                "metric": "memory_tool_util_delta",
                "value": delta,
                "good_score": good_score,
                "weak_score": weak_score,
                "notes": (
                    "Mem0/Letta pattern: memory only helps if tools are called; "
                    "offline good vs inject-offered-unused weak pack"
                ),
            },
        }
        if out_dir:
            try:
                od = Path(out_dir)
                od.mkdir(parents=True, exist_ok=True)
                dest = od / "memory-util-eval.json"
                dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                report["artifact"] = dest.name
            except OSError:
                pass
        return report


def cmd_util_eval(args: argparse.Namespace) -> int:
    """F130: paper memory utilization eval for product scorecard."""
    od = Path(args.out_dir) if getattr(args, "out_dir", None) and args.out_dir else None
    if od is None and (os.environ.get("OUT_DIR") or "").strip():
        od = Path(os.environ["OUT_DIR"])
    report = util_eval(out_dir=od)
    print(json.dumps(report, indent=2))
    return 0 if report.get("eval_pass") else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F105/F106 memory tool-use auditor + re-prompt")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("scan", help="extract memory tool hits from loop/log")
    ps.add_argument("--loop", default="")
    ps.add_argument("--log", default="")
    ps.add_argument("--text", default="")
    ps.set_defaults(func=cmd_scan)

    psc = sub.add_parser("score", help="scan + utilization score")
    psc.add_argument("--loop", default="")
    psc.add_argument("--log", default="")
    psc.add_argument("--prompt", default="")
    psc.add_argument("--out", default="")
    psc.set_defaults(func=cmd_score)

    pa = sub.add_parser("audit", help="audit a run out_dir")
    pa.add_argument("--out-dir", required=True)
    pa.add_argument("--loop", default="")
    pa.add_argument("--prompt", default="")
    pa.add_argument("--log", default="")
    pa.add_argument("--fitness", default="", help="trajectory fitness.json to blend")
    pa.add_argument("--fitness-out", default="")
    pa.add_argument("--force", action="store_true")
    pa.set_defaults(func=cmd_audit)

    pi = sub.add_parser("inject", help="inject utilization rubric into prompt")
    pi.add_argument("--prompt", required=True)
    pi.set_defaults(func=cmd_inject)

    prd = sub.add_parser("reprompt-decide", help="F106: decide soft memory re-prompt")
    prd.add_argument("--out-dir", default="")
    prd.add_argument("--loop", default="")
    prd.add_argument("--prompt", default="")
    prd.add_argument("--already-reprompted", action="store_true")
    prd.add_argument("--already-env", default="", help="prior memory-tool-reprompt.env")
    prd.add_argument("--json", action="store_true")
    prd.set_defaults(func=cmd_reprompt_decide)

    prw = sub.add_parser("reprompt-write", help="F106: write memory-nudged prompt")
    prw.add_argument("--prompt-in", required=True)
    prw.add_argument("--prompt-out", required=True)
    prw.add_argument("--hit-count", type=int, default=0)
    prw.add_argument("--tool-turns", type=int, default=0)
    prw.add_argument("--paths-file", default="")
    prw.add_argument("--path", action="append", default=[])
    prw.set_defaults(func=cmd_reprompt_write)

    pue = sub.add_parser(
        "util-eval",
        help="F130 paper memory util good/weak pack for product scorecard",
    )
    pue.add_argument("--out-dir", default="")
    pue.set_defaults(func=cmd_util_eval)

    pst = sub.add_parser("status")
    pst.set_defaults(func=cmd_status)

    pf = sub.add_parser("fixture", help="hermetic good vs weak utilization + re-prompt")
    pf.set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
