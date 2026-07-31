#!/usr/bin/env python3
"""Pack a Torii .torii-out / showcase run directory into a single JSON for the UI.

Usage:
  python3 scripts/pack-run-for-ui.py \\
    --dir docs/showcase/e2e-odoo-pr3-opus5-agentic-loop \\
    -o ui/review-console/public/fixtures/run-bundle.json

  # F31 pipeline (soft): pack TRACE_DIR after each review
  python3 scripts/pack-run-for-ui.py --dir \"$TRACE_DIR\" -o \"$OUT_DIR/run-bundle.json\"

Optional overrides:
  --comment-url URL  --host modal|gha|local
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path


def read_text(p: Path, limit: int = 400_000) -> str | None:
    if not p.is_file():
        return None
    t = p.read_text(encoding="utf-8", errors="replace")
    if len(t) > limit:
        return t[:limit] + f"\n\n… [truncated at {limit} chars] …\n"
    return t


def read_json(p: Path):
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


def parse_review(md: str) -> dict:
    def field(name: str) -> str:
        m = re.search(rf"^\*\*{re.escape(name)}:\*\*\s*(.+)$", md, re.M)
        return m.group(1).strip() if m else ""

    def section(heading: str) -> str:
        m = re.search(
            rf"^### {re.escape(heading)}\s*\n(.*?)(?=^### |\Z)",
            md,
            re.M | re.S,
        )
        return (m.group(1).strip() if m else "") or ""

    findings = []
    body = section("Key findings")
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|\s*-+", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() in {"severity", "sev"}:
            continue
        findings.append(
            {
                "severity": cells[0],
                "file": cells[1] if len(cells) > 1 else "",
                "issue": cells[2] if len(cells) > 2 else "",
                "trigger": cells[3] if len(cells) > 3 else "",
            }
        )

    blocking = []
    for line in section("Blocking").splitlines():
        s = line.strip()
        if s.startswith(("- ", "* ")):
            blocking.append(re.sub(r"^[-*]\s+", "", s)[:500])

    return {
        "verdict": field("Verdict"),
        "score": field("Score"),
        "effort": field("Review effort"),
        "confidence": field("Confidence"),
        "summary": section("Summary"),
        "walkthrough": section("Walkthrough"),
        "architecture": section("Architecture diagram"),
        "multi_lens": section("Multi-lens checklist"),
        "blocking": blocking,
        "findings": findings,
        "security": section("Security audit") or field("Security audit"),
        "suggestions": section("Suggestions"),
    }


def detect_host(explicit: str | None = None) -> str:
    """Resolve host label for the Run Console (gha | modal | local)."""
    if explicit in ("gha", "modal", "local"):
        return explicit
    env_host = (os.environ.get("TORII_HOST") or "").strip().lower()
    if env_host in ("gha", "modal", "local"):
        return env_host
    if os.environ.get("MODAL_TASK_ID") or os.environ.get("MODAL_ENVIRONMENT"):
        return "modal"
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "gha"
    return "local"


def _parse_env_file(p: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def collect_signals(
    dir_path: Path,
    *,
    review_md: str = "",
    meta_env: str | None = None,
    usage: dict | None = None,
) -> dict:
    """F40/F41/F42: ops signals for Run Console overview.

    Sources (files preferred, review text as soft fallback):
      hermes-timeout.env / hermes-timeout-seconds.txt  → timeout (F36)
      path-skip / ops-signals.env PATH_SKIP=1          → path_skip (F38)
      meta.env DIFF_TRUNCATED / review banner (F27)    → diff_truncated
      review OVER BUDGET / usage + env max (F29)       → over_budget
      hermes-max-turns.env / iteration budget logs     → max_turns_hit (F41)
      model-tier.env (F42)                              → model_tier / selected_tier
      preflight-cost.env (F43)                          → preflight_refuse / forced_cheap
      tool-turns-gate.env (F45)                         → tool_turns_gate (H12)
      tool-turns-reprompt.env (F49)                     → tool_turns_reprompt (H15)
      soul-context.env (F46)                            → soul_blocked (H13)
      severity-calibration.env (F50)                    → severity_calibration (H20)
      linked-issue-context.env (F53)                    → issue_context
    """
    signals: dict = {
        "timeout": False,
        "timeout_seconds": None,
        "path_skip": False,
        "diff_truncated": False,
        "over_budget": False,
        "max_turns_hit": False,
        "max_turns": None,
        "model_tier_mode": None,
        "model_tier": None,
        "model_tier_reason": None,
        "model": None,
        "preflight_refuse": False,
        "preflight_forced_cheap": False,
        "preflight_estimated_usd": None,
        "tool_turns_gate": False,
        "tool_turns_gate_reason": None,
        "tool_turns_reprompt": False,
        "tool_turns_reprompt_reason": None,
        "tool_turns_reprompt_recovered": False,
        "soul_blocked": False,
        "soul_blocked_reason": None,
        "severity_calibration": False,
        "severity_calibration_reason": None,
        "issue_context": False,
        "issue_context_count": None,
        "issue_context_refs": None,
        "flags": [],  # short chip labels for UI
    }
    te = _parse_env_file(dir_path / "hermes-timeout.env")
    if te.get("timed_out") in ("1", "true", "yes") or te.get("timeout_seconds"):
        signals["timeout"] = True
        try:
            signals["timeout_seconds"] = int(te.get("timeout_seconds") or 0) or None
        except ValueError:
            pass
        if te.get("stage"):
            signals["timeout_stage"] = te["stage"]
    ts_file = dir_path / "hermes-timeout-seconds.txt"
    if ts_file.is_file() and signals["timeout_seconds"] is None:
        try:
            signals["timeout_seconds"] = int(ts_file.read_text().strip())
        except ValueError:
            pass
    # Soft: review body mentions F36 timeout
    low = (review_md or "").lower()
    if not signals["timeout"] and (
        "timed out" in low and ("f36" in low or "wall-clock" in low or "timeout" in low)
    ):
        signals["timeout"] = True

    ops = _parse_env_file(dir_path / "ops-signals.env")
    if ops.get("PATH_SKIP") in ("1", "true", "yes") or ops.get("path_skip") in (
        "1",
        "true",
        "yes",
    ):
        signals["path_skip"] = True
        if ops.get("sample"):
            signals["path_skip_sample"] = ops["sample"]
        if ops.get("globs"):
            signals["path_skip_globs"] = ops["globs"]
    if not signals["path_skip"] and (
        "path-skip (f38" in low or "path-skip (f38/f39" in low or "intentional free skip" in low
    ):
        signals["path_skip"] = True

    # F27 truncation
    env_map = _parse_env_file(dir_path / "meta.env") if meta_env is None else {}
    if meta_env:
        for line in meta_env.splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env_map[k.strip()] = v.strip()
    # also merge from file always
    env_map.update(_parse_env_file(dir_path / "meta.env"))
    if env_map.get("DIFF_TRUNCATED", "").lower() in ("true", "1", "yes"):
        signals["diff_truncated"] = True
    if not signals["diff_truncated"] and (
        "diff was truncated" in low or "max_diff_bytes" in low or "incomplete context" in low
    ):
        signals["diff_truncated"] = True

    # F29 over budget
    if "over budget" in low:
        signals["over_budget"] = True
    usage = usage or {}
    cost = usage.get("estimated_cost_usd")
    max_raw = (os.environ.get("TORII_MAX_COST_USD") or "").strip()
    if (
        not signals["over_budget"]
        and cost is not None
        and max_raw
        and max_raw.lower() not in ("0", "off", "false", "no")
    ):
        try:
            if float(cost) > float(max_raw):
                signals["over_budget"] = True
                signals["budget_max_usd"] = float(max_raw)
        except (TypeError, ValueError):
            pass

    # F41 max_turns / iteration budget
    mt = _parse_env_file(dir_path / "hermes-max-turns.env")
    if mt.get("max_turns") and mt.get("max_turns") not in ("off", "0", ""):
        try:
            signals["max_turns"] = int(mt["max_turns"])
        except ValueError:
            signals["max_turns"] = mt["max_turns"]
    if mt.get("max_turns_hit") in ("1", "true", "yes"):
        signals["max_turns_hit"] = True
    # Soft: review / logs mention iteration budget
    if not signals["max_turns_hit"] and (
        "iteration budget" in low
        or ("max_turns" in low and "f41" in low)
        or "max iterations" in low
        or "max_iterations_reached" in low
    ):
        signals["max_turns_hit"] = True
    # Also scan agent-loop md if present
    if not signals["max_turns_hit"]:
        al = dir_path / "agent-loop" / "agent-loop.md"
        if al.is_file():
            try:
                chunk = al.read_text(encoding="utf-8", errors="replace")[:80_000].lower()
            except OSError:
                chunk = ""
            if (
                "iteration budget exhausted" in chunk
                or "max_iterations_reached" in chunk
                or "reached maximum iterations" in chunk
            ):
                signals["max_turns_hit"] = True

    # F42 model tier (cheap/full selection)
    mte = _parse_env_file(dir_path / "model-tier.env")
    if mte.get("mode"):
        signals["model_tier_mode"] = mte["mode"]
    if mte.get("tier"):
        signals["model_tier"] = mte["tier"]
    if mte.get("reason"):
        signals["model_tier_reason"] = mte["reason"]
    if mte.get("model"):
        signals["model"] = mte["model"]
    # Soft: torii-model.txt when env missing
    if not signals.get("model"):
        lm = dir_path / "torii-model.txt"
        if lm.is_file():
            try:
                signals["model"] = lm.read_text(encoding="utf-8", errors="replace").strip() or None
            except OSError:
                pass

    # F43 preflight cost
    pfc = _parse_env_file(dir_path / "preflight-cost.env")
    if pfc.get("decision"):
        signals["preflight_decision"] = pfc["decision"]
    if pfc.get("reason"):
        signals["preflight_reason"] = pfc["reason"]
    if pfc.get("estimated_usd"):
        try:
            signals["preflight_estimated_usd"] = float(pfc["estimated_usd"])
        except ValueError:
            signals["preflight_estimated_usd"] = pfc["estimated_usd"]
    if pfc.get("refused") in ("1", "true", "yes") or pfc.get("decision") == "refuse" or pfc.get("skip") == "preflight_cost":
        signals["preflight_refuse"] = True
    if pfc.get("forced_cheap") in ("1", "true", "yes") or pfc.get("decision") == "force_cheap":
        signals["preflight_forced_cheap"] = True
    # Soft: review text
    if not signals["preflight_refuse"] and (
        "preflight cost gate (f43)" in low or "f43 preflight refuse" in low
    ):
        signals["preflight_refuse"] = True

    # F45 tool-turns gate (H12 zero tools on multi-file code)
    ttg = _parse_env_file(dir_path / "tool-turns-gate.env")
    if ttg.get("gate") in ("1", "true", "yes") or ttg.get("mutated") in (
        "1",
        "true",
        "yes",
    ):
        signals["tool_turns_gate"] = True
        if ttg.get("reason"):
            signals["tool_turns_gate_reason"] = ttg["reason"]
        if ttg.get("tool_turns") not in (None, ""):
            try:
                signals["tool_turns"] = int(ttg["tool_turns"])
            except ValueError:
                signals["tool_turns"] = ttg["tool_turns"]
    if not signals["tool_turns_gate"] and (
        "incomplete agentic review (f45)" in low
        or "tool-turns gate (f45)" in low
        or ("zero tool turns" in low and "f45" in low)
    ):
        signals["tool_turns_gate"] = True
        signals["tool_turns_gate_reason"] = signals.get("tool_turns_gate_reason") or "review_banner"

    # F49 soft re-prompt (H15)
    ttr = _parse_env_file(dir_path / "tool-turns-reprompt.env")
    if ttr.get("attempted") in ("1", "true", "yes") or ttr.get("reprompt") in (
        "1",
        "true",
        "yes",
    ):
        signals["tool_turns_reprompt"] = True
        if ttr.get("reason"):
            signals["tool_turns_reprompt_reason"] = ttr["reason"]
        if ttr.get("recovered") in ("1", "true", "yes"):
            signals["tool_turns_reprompt_recovered"] = True
        if ttr.get("tool_turns_before") not in (None, ""):
            try:
                signals["tool_turns_before"] = int(ttr["tool_turns_before"])
            except ValueError:
                signals["tool_turns_before"] = ttr["tool_turns_before"]
        if ttr.get("tool_turns_after") not in (None, ""):
            try:
                signals["tool_turns_after"] = int(ttr["tool_turns_after"])
            except ValueError:
                signals["tool_turns_after"] = ttr["tool_turns_after"]
    if not signals["tool_turns_reprompt"] and (
        "soft re-prompt (f49" in low or "soft re-prompt (torii h15" in low
    ):
        signals["tool_turns_reprompt"] = True
        signals["tool_turns_reprompt_reason"] = (
            signals.get("tool_turns_reprompt_reason") or "review_banner"
        )

    # F46 SOUL.md blocked by Hermes context scanner
    sce = _parse_env_file(dir_path / "soul-context.env")
    scp = _parse_env_file(dir_path / "soul-context-preflight.env")
    if sce.get("soul_blocked") in ("1", "true", "yes"):
        signals["soul_blocked"] = True
        if sce.get("reason"):
            signals["soul_blocked_reason"] = sce["reason"]
    if scp.get("soul_blocked_risk") in ("1", "true", "yes") or scp.get(
        "preflight_failed"
    ) in ("1", "true", "yes"):
        # Preflight risk without runtime block still worth a softer flag
        if not signals["soul_blocked"]:
            signals["soul_blocked_reason"] = signals.get("soul_blocked_reason") or scp.get(
                "findings"
            ) or "preflight_risk"
    if not signals["soul_blocked"] and (
        "context file soul.md blocked" in low
        or ("soul.md blocked" in low and "prompt_injection" in low)
        or "soul blocked (f46)" in low
    ):
        signals["soul_blocked"] = True
        signals["soul_blocked_reason"] = signals.get("soul_blocked_reason") or "prompt_injection"

    # F50 severity calibration (H20 missing-test → REQUEST CHANGES)
    sc = _parse_env_file(dir_path / "severity-calibration.env")
    if sc.get("gate") in ("1", "true", "yes") or sc.get("mutated") in (
        "1",
        "true",
        "yes",
    ):
        signals["severity_calibration"] = True
        if sc.get("reason"):
            signals["severity_calibration_reason"] = sc["reason"]
        if sc.get("match"):
            signals["severity_calibration_match"] = sc["match"]
    if not signals["severity_calibration"] and (
        "severity calibration (f50" in low
        or "severity calibration (f50 / h20)" in low
    ):
        signals["severity_calibration"] = True
        signals["severity_calibration_reason"] = (
            signals.get("severity_calibration_reason") or "review_banner"
        )

    flags: list[str] = []
    if signals["path_skip"]:
        flags.append("path-skip")
    if signals["timeout"]:
        flags.append("timeout")
    if signals["over_budget"]:
        flags.append("over-budget")
    if signals["diff_truncated"]:
        flags.append("diff-truncated")
    if signals["max_turns_hit"]:
        flags.append("max-turns")
    if signals.get("preflight_refuse"):
        flags.append("preflight-refuse")
    elif signals.get("preflight_forced_cheap"):
        flags.append("preflight-cheap")
    if signals.get("tool_turns_gate"):
        flags.append("tool-turns-gate")
    if signals.get("tool_turns_reprompt"):
        if signals.get("tool_turns_reprompt_recovered"):
            flags.append("tool-reprompt-ok")
        else:
            flags.append("tool-reprompt")
    if signals.get("soul_blocked"):
        flags.append("soul-blocked")
    if signals.get("severity_calibration"):
        flags.append("sev-cal")

    # F53 linked issue context (product: claim-to-fix from Fixes/#N)
    lic = _parse_env_file(dir_path / "linked-issue-context.env")
    try:
        fetched_n = int(lic.get("fetched") or "0")
    except ValueError:
        fetched_n = 0
    if lic.get("enabled") in ("1", "true", "yes") and fetched_n > 0:
        signals["issue_context"] = True
        signals["issue_context_count"] = fetched_n
        if lic.get("refs"):
            signals["issue_context_refs"] = lic["refs"]
    if signals.get("issue_context"):
        flags.append("issue-ctx")

    # Surface auto/cheap/full when tier mode is active (not plain off/default)
    mode = (signals.get("model_tier_mode") or "").lower()
    tier = (signals.get("model_tier") or "").lower()
    if mode in ("auto", "cheap", "full") or tier in ("cheap", "full") and mode not in ("", "off"):
        if tier == "cheap" or mode == "cheap":
            flags.append("model-cheap")
        elif tier == "full" and mode in ("auto", "full"):
            flags.append("model-full")
        elif mode == "auto":
            flags.append("model-tier")
    signals["flags"] = flags
    signals["any"] = bool(flags)
    return signals


def collect_loop(dir_path: Path) -> dict:
    """F41: structured agent-loop metrics for Run Console (Hermes iteration observability)."""
    loop_json = read_json(dir_path / "agent-loop" / "agent-loop.json") or {}
    mt = _parse_env_file(dir_path / "hermes-max-turns.env")
    steps = loop_json.get("steps") if isinstance(loop_json, dict) else None
    step_count = len(steps) if isinstance(steps, list) else None
    max_turns_val: int | str | None = None
    if mt.get("max_turns") and mt.get("max_turns") not in ("off", ""):
        try:
            max_turns_val = int(mt["max_turns"])
        except ValueError:
            max_turns_val = mt["max_turns"]
    return {
        "tool_call_turns": loop_json.get("tool_call_turns")
        if isinstance(loop_json, dict)
        else None,
        "message_count": loop_json.get("message_count")
        if isinstance(loop_json, dict)
        else None,
        "step_count": step_count,
        "max_turns": max_turns_val,
        "max_turns_enabled": mt.get("max_turns_enabled") in ("1", "true", "yes"),
        "max_turns_hit": mt.get("max_turns_hit") in ("1", "true", "yes"),
    }


def _resolve_review_md(dir_path: Path) -> str:
    """Prefer review.md; fall back to review-<pr>.md under OUT_DIR layouts."""
    direct = read_text(dir_path / "review.md")
    if direct:
        return direct
    candidates = sorted(
        p
        for p in dir_path.glob("review-*.md")
        if ".raw." not in p.name and p.is_file()
    )
    if candidates:
        return read_text(candidates[0]) or ""
    return ""


def prepare_pack_dir(dir_path: Path, *, extra_env_file: Path | None = None) -> Path:
    """Return a directory ready for pack() — copy memory-health if needed.

    If memory-health.env is only under OUT_DIR (not TRACE_DIR), soft-copy into a
    temp overlay so the bundle includes F30 health without mutating the trace.
    When the source already has everything, return dir_path unchanged.
    """
    mh_src = None
    if extra_env_file and extra_env_file.is_file():
        mh_src = extra_env_file
    elif (dir_path / "memory-health.env").is_file():
        return dir_path
    # Look next to common OUT_DIR layouts: parent of traces/<id>
    sibling = dir_path.parent.parent / "memory-health.env"
    if mh_src is None and sibling.is_file() and dir_path.parent.name == "traces":
        mh_src = sibling
    parent_mh = dir_path.parent / "memory-health.env"
    if mh_src is None and parent_mh.is_file():
        mh_src = parent_mh
    if mh_src is None or (dir_path / "memory-health.env").is_file():
        return dir_path
    # Overlay: temp dir with symlink/copy of files is heavy; just copy mh into
    # source when writable, else temp overlay with key files.
    try:
        shutil.copy2(mh_src, dir_path / "memory-health.env")
        return dir_path
    except OSError:
        pass
    tmp = Path(tempfile.mkdtemp(prefix="torii-pack-"))
    for p in dir_path.iterdir():
        dest = tmp / p.name
        if p.is_dir():
            shutil.copytree(p, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(p, dest)
    shutil.copy2(mh_src, tmp / "memory-health.env")
    return tmp


def pack(dir_path: Path, *, comment_url: str = "", host: str = "gha") -> dict:
    meta = read_json(dir_path / "meta.json") or {}
    timings = read_json(dir_path / "timings.json") or {}
    usage = read_json(dir_path / "hermes-usage.json") or read_json(
        dir_path / "agent-loop" / "usage.json"
    ) or {}
    pr = read_json(dir_path / "pr.json") or {}
    trace = read_json(dir_path / "trace.json") or {}
    review_md = _resolve_review_md(dir_path)
    review_raw = read_text(dir_path / "review.raw.md", 80_000)
    if not review_raw:
        raws = sorted(dir_path.glob("review-*.raw.md"))
        if raws:
            review_raw = read_text(raws[0], 80_000)
    prompt = read_text(dir_path / "prompt.md", 40_000)
    context = read_text(dir_path / "context.md", 40_000)
    diff = read_text(dir_path / "pr.diff", 120_000)
    memory = read_text(dir_path / "memory-after.md", 40_000)
    agent_loop_md = read_text(dir_path / "agent-loop" / "agent-loop.md", 80_000)
    agent_log = read_text(dir_path / "agent-loop" / "agent.log", 40_000) or read_text(
        dir_path / "hermes-run.log", 40_000
    )
    hermes_stderr = read_text(dir_path / "hermes.stderr", 20_000)
    files_txt = read_text(dir_path / "files.txt", 10_000)
    meta_env = read_text(dir_path / "meta.env", 5_000)
    memory_health = {}
    mh = dir_path / "memory-health.env"
    if mh.is_file():
        for line in mh.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                memory_health[k.strip()] = v.strip()

    signals = collect_signals(
        dir_path,
        review_md=review_md or "",
        meta_env=meta_env,
        usage=usage if isinstance(usage, dict) else {},
    )
    loop = collect_loop(dir_path)
    # Prefer loop metrics for max_turns display even when not hit
    if loop.get("max_turns") is not None and signals.get("max_turns") is None:
        signals["max_turns"] = loop["max_turns"]
    if loop.get("max_turns_hit"):
        signals["max_turns_hit"] = True
        if "max-turns" not in signals.get("flags", []):
            signals.setdefault("flags", []).append("max-turns")
            signals["any"] = True

    # Artifact inventory from meta or directory listing
    artifacts = []
    if isinstance(meta.get("files"), dict):
        for path, info in meta["files"].items():
            artifacts.append(
                {
                    "path": path,
                    "bytes": info.get("bytes") if isinstance(info, dict) else None,
                }
            )
    else:
        for p in sorted(dir_path.rglob("*")):
            if p.is_file() and p.name != "run-bundle.json":
                rel = str(p.relative_to(dir_path))
                artifacts.append({"path": rel, "bytes": p.stat().st_size})

    repo = meta.get("repo") or pr.get("url", "").replace("https://github.com/", "").rsplit(
        "/pull/", 1
    )[0]
    pr_number = str(meta.get("pr_number") or pr.get("number") or "")
    pr_url = pr.get("url") or (
        f"https://github.com/{repo}/pull/{pr_number}" if repo and pr_number else ""
    )

    return {
        "schema_version": 1,
        "host": host,
        "packed_from": str(dir_path),
        "run": {
            "trace_id": meta.get("trace_id") or f"pr{pr_number}-unknown",
            "run_id": str(meta.get("run_id") or ""),
            "run_attempt": str(meta.get("run_attempt") or "1"),
            "status": meta.get("status") or "unknown",
            "model": meta.get("model") or usage.get("model") or "unknown",
            "started_at": meta.get("started_at") or timings.get("started_at"),
            "ended_at": meta.get("ended_at") or timings.get("ended_at"),
            "total_seconds": timings.get("total_seconds"),
            "github_sha": meta.get("github_sha") or pr.get("commits", [{}])[-1].get("oid")
            if pr.get("commits")
            else meta.get("github_sha"),
            "github_ref": meta.get("github_ref"),
            "github_event_name": meta.get("github_event_name"),
            "trigger_comment": meta.get("trigger_comment") or "",
            "comment_url": comment_url,
            "hermes_rc": meta.get("hermes_rc"),
        },
        "pr": {
            "repo": repo,
            "number": pr_number,
            "title": pr.get("title") or "",
            "url": pr_url,
            "base": pr.get("baseRefName") or "",
            "head": pr.get("headRefName") or "",
            "author": (pr.get("author") or {}).get("login")
            if isinstance(pr.get("author"), dict)
            else pr.get("author") or "",
            "additions": pr.get("additions"),
            "deletions": pr.get("deletions"),
            "files": [
                {
                    "path": f.get("path"),
                    "additions": f.get("additions"),
                    "deletions": f.get("deletions"),
                }
                for f in (pr.get("files") or [])
                if isinstance(f, dict)
            ],
            "body": (pr.get("body") or "")[:4000],
        },
        "result": {
            **parse_review(review_md),
            "review_md": review_md,
            "review_raw_md": review_raw,
        },
        "cost": {
            "estimated_cost_usd": usage.get("estimated_cost_usd"),
            "cost_status": usage.get("cost_status"),
            "model": usage.get("model"),
            "total_tokens": usage.get("total_tokens"),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cache_read_tokens": usage.get("cache_read_tokens"),
            "cache_write_tokens": usage.get("cache_write_tokens"),
            "api_calls": usage.get("api_calls"),
            "provider": usage.get("provider"),
        },
        "timings": {
            "total_seconds": timings.get("total_seconds"),
            "stages": timings.get("stages") or [],
        },
        "memory": {
            "health": memory_health,
            "after_md": memory,
        },
        "signals": signals,  # F40/F41: timeout / path-skip / budget / truncation / max-turns
        "loop": loop,  # F41: agent-loop metrics (tool turns, max_turns cap)
        "trace": {
            "meta": meta,
            "trace_json": trace if isinstance(trace, dict) else {},
            "agent_loop_md": agent_loop_md,
            "agent_log": agent_log,
            "hermes_stderr": hermes_stderr,
            "prompt_md": prompt,
            "context_md": context,
            "files_txt": files_txt,
            "meta_env": meta_env,
            "artifacts": artifacts,
        },
        "diff": {
            "pr_diff": diff,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, required=True, help="Run / TRACE_DIR directory")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--comment-url", default="")
    ap.add_argument(
        "--host",
        default=None,
        choices=("gha", "modal", "local"),
        help="Host label (default: auto-detect from env)",
    )
    ap.add_argument(
        "--memory-health",
        type=Path,
        default=None,
        help="Optional path to memory-health.env (F30) if not inside --dir",
    )
    ap.add_argument(
        "--also",
        type=Path,
        action="append",
        default=[],
        help="Extra output path(s) to write the same bundle (e.g. TRACE_DIR/run-bundle.json)",
    )
    ap.add_argument(
        "--soft",
        action="store_true",
        help="Exit 0 even when pack fails (pipeline must not fail reviews)",
    )
    args = ap.parse_args()
    try:
        if not args.dir.is_dir():
            raise FileNotFoundError(f"not a directory: {args.dir}")
        host = detect_host(args.host)
        pack_dir = prepare_pack_dir(args.dir, extra_env_file=args.memory_health)
        bundle = pack(pack_dir, comment_url=args.comment_url, host=host)
        if not bundle["result"].get("review_md") and not bundle["result"].get("verdict"):
            print("pack: no review.md found — writing minimal bundle", file=sys.stderr)
        outs = [args.out, *args.also]
        written = []
        for out in outs:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
            written.append(out)
        for w in written:
            print(w)
        print(
            f"host={host} trace={bundle['run']['trace_id']} "
            f"verdict={bundle['result'].get('verdict') or '—'} "
            f"files={len(bundle['trace']['artifacts'])}",
            file=sys.stderr,
        )
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"pack-run-for-ui failed: {e}", file=sys.stderr)
        if args.soft:
            return 0
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
