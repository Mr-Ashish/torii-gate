#!/usr/bin/env python3
"""F69/F112/F117: Torii-native self-evolution (Hermes best practices, not a fork).

Patterns adopted from Hermes self-evolution / skill evolution (H3, H9, H10):
  - trajectory packaging from agent-loop runs
  - skill proposals from failure/recovery signals
  - offline eval of proposals
  - adopt → agent/skills/active/ injected into review prompts
  - soft skill nudge when prior runs show zero-tool thrash

F112: memory utilization recovery signals (F105/F106) → skill proposal to call
product CLI / torii_memory early (proactive use, not only soft re-prompt).

F117: mine allowlisted tool-outcome probes from live skill-hits + agent-loop
into durable `.torii/tool-outcome-probes.json` (merged by skill_router F114),
and propose skills for novel tool families (product doctor/status, critic, …).

F132: product scorecard gap themes (F129–F131 brand_ready metrics) → skill
proposals so self-evolution closes install/ops readiness gaps, not only
trajectory thrash.

F165: GEPA-lite skill body refine from util traces (Hermes self-evolution /
ICLR 2026 GEPA pattern) — read recovery/hub-archival util + fitness ledger,
diagnose idle inject≠tool, mutate skill bodies with tool-first nudges under
constraint gates (size ≤15KB, id preserved, required tool probes present).
No LLM required for the deterministic path; dual-gate adopt remains separate.

Usage:
  python3 scripts/self_evolve.py ingest --out-dir DIR [--pr N] [--repo R]
  python3 scripts/self_evolve.py propose [--limit N]
  python3 scripts/self_evolve.py propose-scorecard [--scorecard PATH] [--limit N]
  python3 scripts/self_evolve.py mine-probes --out-dir DIR [--propose]
  python3 scripts/self_evolve.py refine-from-util --out-dir DIR [--apply|--dry-run]
  python3 scripts/self_evolve.py eval [--proposal ID|all]
  python3 scripts/self_evolve.py adopt PROPOSAL_ID [--force]
  python3 scripts/self_evolve.py inject --prompt PATH [--out PATH]
  python3 scripts/self_evolve.py status
  python3 scripts/self_evolve.py fixture   # F117 hermetic mine+score
  python3 scripts/self_evolve.py fixture-refine  # F165 hermetic refine-from-util
  python3 scripts/self_evolve.py nudge-text   # print soft nudge if warranted

Env:
  TORII_ROOT
  TORII_SELF_EVOLVE=0|1          (default 0 for auto-propose in CI; CLI always works)
  TORII_SELF_EVOLVE_AUTO_ADOPT=0|1  (default 0)
  TORII_EVOLUTION_ROOT           (default: <root>/memory/evolution)
  TORII_TOOL_PROBE_MINE=1        (default 1) — F117 mine-probes soft post-run
  TORII_TOOL_OUTCOME_PROBES_FILE override path for durable probe ledger
  TORII_SKILL_REFINE=1           (default 1) — F165 GEPA-lite refine-from-util
  TORII_SKILL_REFINE_MIN_GAP     default 0.33 chronic hub_archival/tool gap rate
  TORII_SKILL_REFINE_MAX_BYTES   default 15360 (Hermes ≤15KB skill gate)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
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


def _evo_root(root: Path) -> Path:
    env = (os.environ.get("TORII_EVOLUTION_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return root / "memory" / "evolution"


def _ledger_path(root: Path) -> Path:
    return _evo_root(root) / "ledger.json"


def _load_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.is_file():
        return {
            "schema_version": 1,
            "feature": "F69",
            "trajectories": [],
            "proposals": [],
            "adopted": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    for k in ("trajectories", "proposals", "adopted"):
        data.setdefault(k, [])
    return data


def _save_ledger(root: Path, data: dict[str, Any]) -> Path:
    path = _ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["schema_version"] = 1
    data["feature"] = "F69"
    data["updated_at"] = _now()
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", s.strip().lower())
    return s.strip("-")[:72] or "skill"


# ---------------------------------------------------------------------------
# F165: GEPA-lite skill body refine from util traces
# ---------------------------------------------------------------------------

FEATURE_REFINE = "F165"
REFINE_MARKER = "<!-- torii-f165-gepa-refine -->"
REFINE_MARKER_CLOSE = "<!-- /torii-f165-gepa-refine -->"
# Hermes self-evolution skill size gate (≤15KB)
DEFAULT_REFINE_MAX_BYTES = 15 * 1024

# Deterministic tool-first nudges when util traces show inject≠tool (GEPA reflection → mutation)
REFINE_NUDGES: dict[str, dict[str, Any]] = {
    "skill-prefer-hub-archival-early": {
        "required_substrings": [
            "archival_memory_search.py",
            "hub_boost",
            "TORII_RECON_WARM_HUB_QUERY",
        ],
        "nudge_lines": [
            "**F165 GEPA-lite (util trace):** hub-archival inject without hub_boost is a measured gap.",
            "1. **First tool call** this turn: `python3 scripts/archival_memory_search.py auto --files changed.py`",
            "   Keep `TORII_RECON_WARM_HUB_QUERY=1` so multi-tenant warm themes expand the query.",
            "2. Prefer hits that carry **hub_boost** / recon-warm hub heat; require path:line evidence.",
            "3. Do not finish APPROVE while hub-archival is idle — one archival tool fire closes F155 util.",
        ],
    },
    "skill-prefer-memory-cli-early": {
        "required_substrings": [
            "torii.py memory",
            "archival_memory_search",
        ],
        "nudge_lines": [
            "**F165 GEPA-lite (util trace):** memory inject without memory tools is a measured gap.",
            "1. **First tool call:** `python3 scripts/torii.py memory -- search -- -q \"<path theme>\"`",
            "2. Page cold TPs: `python3 scripts/archival_memory_search.py auto --files changed.py`",
            "3. Prefer path-matched memory hits before writing findings.",
        ],
    },
    "skill-prefer-product-cli": {
        "required_substrings": [
            "torii.py doctor",
            "torii.py status",
        ],
        "nudge_lines": [
            "**F165 GEPA-lite (util trace):** product-cli skill must fire doctor/status CLIs.",
            "1. Run `python3 scripts/torii.py doctor` once when pack health is uncertain.",
            "2. Surface `python3 scripts/torii.py status` for loop readiness before verdict.",
        ],
    },
    "skill-prefer-critic-early": {
        "required_substrings": [
            "second_agent_critic.py",
        ],
        "nudge_lines": [
            "**F165 GEPA-lite (util trace):** critic skill must invoke the checker panel.",
            "1. Prefer path evidence; optionally `python3 scripts/second_agent_critic.py score --review REVIEW.md`.",
            "2. Do not APPROVE without path:line on security findings.",
        ],
    },
}


def skill_refine_enabled() -> bool:
    """F165: GEPA-lite refine-from-util (default on for CLI; hermes soft)."""
    raw = (os.environ.get("TORII_SKILL_REFINE") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def skill_refine_min_gap_rate() -> float:
    try:
        return float(os.environ.get("TORII_SKILL_REFINE_MIN_GAP") or "0.33")
    except (TypeError, ValueError):
        return 0.33


def skill_refine_max_bytes() -> int:
    try:
        n = int(os.environ.get("TORII_SKILL_REFINE_MAX_BYTES") or str(DEFAULT_REFINE_MAX_BYTES))
        return max(2048, min(n, 32 * 1024))
    except (TypeError, ValueError):
        return DEFAULT_REFINE_MAX_BYTES


def constraint_validate_skill(
    text: str,
    skill_id: str,
    *,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    """Hermes self-evolution / GEPA constraint gate for skill bodies.

    Gates: size ≤ max_bytes, skill id preserved, required tool probe substrings present.
    """
    max_b = max_bytes if max_bytes is not None else skill_refine_max_bytes()
    raw = text if isinstance(text, str) else ""
    size = len(raw.encode("utf-8"))
    errors: list[str] = []
    if size > max_b:
        errors.append(f"size_{size}_gt_{max_b}")
    if size < 40:
        errors.append("size_too_small")
    # id preserved in frontmatter or body
    id_ok = bool(
        re.search(rf"(?m)^id:\s*{re.escape(skill_id)}\s*$", raw)
        or skill_id in raw
    )
    if not id_ok:
        errors.append("id_missing")
    req = list((REFINE_NUDGES.get(skill_id) or {}).get("required_substrings") or [])
    missing = [s for s in req if s.lower() not in raw.lower()]
    if missing:
        errors.append("missing_probes:" + ",".join(missing))
    return {
        "ok": not errors,
        "skill_id": skill_id,
        "size": size,
        "max_bytes": max_b,
        "id_ok": id_ok,
        "missing_probes": missing,
        "errors": errors,
        "feature": FEATURE_REFINE,
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}


def diagnose_util_gaps(
    out_dir: Path,
    root: Path | None = None,
    *,
    min_gap_rate: float | None = None,
) -> list[dict[str, Any]]:
    """Reflect on util + fitness traces (GEPA: read trajectories, diagnose).

    Returns skill targets with reason tags (this-run idle and/or chronic gap).
    """
    root = root or _root()
    thr = min_gap_rate if min_gap_rate is not None else skill_refine_min_gap_rate()
    util = _load_json(out_dir / "recovery-skill-util.json")
    fitness = _load_json(root / ".torii" / "skill-fitness.json")
    skills_fit = fitness.get("skills") if isinstance(fitness.get("skills"), dict) else {}

    targets: dict[str, dict[str, Any]] = {}

    def _add(sid: str, reason: str, **extra: Any) -> None:
        if sid not in REFINE_NUDGES:
            return
        ent = targets.setdefault(
            sid,
            {"skill_id": sid, "reasons": [], "feature": FEATURE_REFINE},
        )
        if reason not in ent["reasons"]:
            ent["reasons"].append(reason)
        ent.update({k: v for k, v in extra.items() if v is not None})

    idle = list(util.get("idle_ids") or util.get("prose_only_ids") or [])
    for sid in idle:
        _add(str(sid), "run_idle", util_rate=util.get("util_rate"))

    if util.get("hub_archival_util_gap") or util.get("hub_archival_idle"):
        _add(
            "skill-prefer-hub-archival-early",
            "hub_archival_util_gap",
            hub_archival_util_gap=True,
        )
    if util.get("utilization_gap") and not idle:
        # full recovery gap but idle list empty — still refine injected recovery skills
        for sid in util.get("recovery_injected") or []:
            if sid not in (util.get("tool_hit_ids") or []):
                _add(str(sid), "utilization_gap")

    # chronic fitness (F158 hub_archival_gap_rate / tool miss)
    for sid, ent in skills_fit.items():
        if not isinstance(ent, dict):
            continue
        sid_s = str(sid)
        ha_gap = float(ent.get("hub_archival_gap_rate") or 0.0)
        if ha_gap >= thr:
            _add(sid_s, "chronic_hub_archival_gap", chronic_gap_rate=ha_gap)
        tool_rate = ent.get("tool_hit_rate")
        try:
            tr = float(tool_rate) if tool_rate is not None else None
        except (TypeError, ValueError):
            tr = None
        sel_n = int(ent.get("selected_n") or ent.get("hub_archival_selected_n") or 0)
        if tr is not None and sel_n >= 2 and tr <= (1.0 - thr):
            _add(sid_s, "chronic_tool_miss", tool_hit_rate=tr, selected_n=sel_n)
        if ent.get("demoted"):
            _add(sid_s, "fitness_demoted")

    return list(targets.values())


def refine_skill_body(text: str, skill_id: str, reasons: list[str]) -> tuple[str, bool]:
    """Mutate skill body with tool-first GEPA-lite nudge block if probes missing or marker absent."""
    spec = REFINE_NUDGES.get(skill_id) or {}
    req = list(spec.get("required_substrings") or [])
    lines = list(spec.get("nudge_lines") or [])
    raw = text if text.endswith("\n") else text + "\n"
    missing = [s for s in req if s.lower() not in raw.lower()]
    already = REFINE_MARKER in raw
    # re-refine only if still missing required probes
    if already and not missing:
        return raw, False
    if not lines and not missing:
        return raw, False

    reason_blob = ", ".join(reasons) if reasons else "util_trace"
    block_lines = [
        "",
        REFINE_MARKER,
        f"## F165 GEPA-lite refine ({reason_blob})",
        "",
        *lines,
        REFINE_MARKER_CLOSE,
        "",
    ]
    block = "\n".join(block_lines)
    if already:
        # replace prior refine block
        raw2 = re.sub(
            rf"{re.escape(REFINE_MARKER)}.*?{re.escape(REFINE_MARKER_CLOSE)}\n?",
            block.lstrip("\n"),
            raw,
            count=1,
            flags=re.S,
        )
        if raw2 == raw:
            raw2 = raw.rstrip() + "\n" + block.lstrip("\n")
        return raw2 if raw2.endswith("\n") else raw2 + "\n", True

    # append after body
    return raw.rstrip() + "\n" + block.lstrip("\n"), True


def refine_from_util(
    out_dir: Path,
    root: Path | None = None,
    *,
    apply: bool = True,
    force_skills: list[str] | None = None,
    min_gap_rate: float | None = None,
) -> dict[str, Any]:
    """F165: diagnose util/fitness gaps → constraint-gated skill body refine.

    Writes refined bodies into agent/skills/active/ (apply=True) when constraints pass.
    Always writes out_dir/skill-refine.json report.
    """
    root = root or _root()
    out_dir = Path(out_dir)
    report: dict[str, Any] = {
        "feature": FEATURE_REFINE,
        "scored_at": _now(),
        "enabled": skill_refine_enabled(),
        "apply": bool(apply),
        "targets": [],
        "refined": [],
        "skipped": [],
        "constraint_failures": [],
        "ok": True,
    }
    if not skill_refine_enabled():
        report["ok"] = True
        report["reason"] = "refine_off"
        _write_refine_report(out_dir, report)
        return report

    targets = diagnose_util_gaps(out_dir, root, min_gap_rate=min_gap_rate)
    if force_skills:
        have = {t["skill_id"] for t in targets}
        for sid in force_skills:
            if sid not in have and sid in REFINE_NUDGES:
                targets.append(
                    {
                        "skill_id": sid,
                        "reasons": ["force"],
                        "feature": FEATURE_REFINE,
                    }
                )
    report["targets"] = targets

    active_dir = root / "agent" / "skills" / "active"
    for t in targets:
        sid = str(t["skill_id"])
        path = active_dir / f"{sid}.md"
        if not path.is_file():
            # try proposal as source of truth
            prop = root / "agent" / "skills" / "proposals" / f"{sid}.md"
            if prop.is_file() and apply:
                active_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(prop, path)
            else:
                report["skipped"].append({"skill_id": sid, "reason": "no_active_skill"})
                continue
        before = path.read_text(encoding="utf-8", errors="replace")
        after, changed = refine_skill_body(before, sid, list(t.get("reasons") or []))
        gate = constraint_validate_skill(after, sid)
        entry = {
            "skill_id": sid,
            "reasons": t.get("reasons"),
            "changed": changed,
            "constraint": gate,
            "path": (
                str(path.relative_to(root))
                if str(path).startswith(str(root))
                else str(path)
            ),
        }
        if not gate["ok"]:
            report["constraint_failures"].append(entry)
            report["ok"] = False
            continue
        if not changed:
            report["skipped"].append({**entry, "reason": "already_refined"})
            continue
        if apply:
            stamped = stamp_dual_gate_refine(after, sid, reasons=list(t.get("reasons") or []))
            path.write_text(
                stamped if stamped.endswith("\n") else stamped + "\n", encoding="utf-8"
            )
            entry["applied"] = True
            entry["dual_gate"] = "constraint_ok"
            entry["dual_gate_feature"] = "F166"
        else:
            entry["applied"] = False
            entry["dry_run_bytes"] = len(after.encode("utf-8"))
        report["refined"].append(entry)

    report["refined_n"] = len(report["refined"])
    report["target_n"] = len(targets)
    # ledger event
    try:
        ledger = _load_ledger(root)
        ledger.setdefault("refines", [])
        ledger["refines"].append(
            {
                "at": _now(),
                "feature": FEATURE_REFINE,
                "dual_gate_feature": "F166",
                "out_dir": str(out_dir),
                "refined_n": report["refined_n"],
                "target_n": report["target_n"],
                "skill_ids": [r["skill_id"] for r in report["refined"]],
            }
        )
        ledger["refines"] = ledger["refines"][-50:]
        ledger["last_refine"] = ledger["refines"][-1]
        _save_ledger(root, ledger)
    except OSError:
        pass

    # F166: privacy-safe federate of refined skill themes
    if apply and report["refined"]:
        try:
            federate_refine_skills(
                root,
                [r["skill_id"] for r in report["refined"]],
                reasons_by_id={
                    r["skill_id"]: list(r.get("reasons") or []) for r in report["refined"]
                },
            )
            report["federated"] = True
        except OSError:
            report["federated"] = False

    _write_refine_report(out_dir, report)
    return report


def stamp_dual_gate_refine(
    text: str,
    skill_id: str,
    *,
    reasons: list[str] | None = None,
) -> str:
    """F166: stamp dual-gate constraint_ok on refined skill frontmatter.

    Hermes self-evolution / dual-gate: constraint-passed refine is an adopt event,
    not a silent body edit — frontmatter records F165 refine + F166 dual_gate.
    """
    raw = text if text.endswith("\n") else text + "\n"
    # inject/update keys in first frontmatter block
    def _ensure_keys(fm: str) -> str:
        lines = fm.splitlines()
        keys = {
            "dual_gate": "constraint_ok",
            "dual_gate_feature": "F166",
            "refined_feature": "F165",
            "refined_at": _now(),
        }
        if reasons:
            keys["refine_reasons"] = "|".join(reasons)[:120]
        present = set()
        out_lines: list[str] = []
        for line in lines:
            m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
            if m and m.group(1) in keys:
                out_lines.append(f"{m.group(1)}: {keys[m.group(1)]}")
                present.add(m.group(1))
            else:
                out_lines.append(line)
        for k, v in keys.items():
            if k not in present:
                out_lines.append(f"{k}: {v}")
        return "\n".join(out_lines)

    if raw.lstrip().startswith("---"):
        parts = raw.split("---", 2)
        # parts[0] may be empty or leading whitespace; parts[1]=fm; parts[2]=body
        if len(parts) >= 3:
            fm = _ensure_keys(parts[1].strip("\n"))
            body = parts[2]
            return f"---\n{fm}\n---{body}" if body.startswith("\n") else f"---\n{fm}\n---\n{body}"
    # no frontmatter — prepend
    header = (
        f"---\nid: {skill_id}\ndual_gate: constraint_ok\n"
        f"dual_gate_feature: F166\nrefined_feature: F165\nrefined_at: {_now()}\n---\n"
    )
    return header + raw


def federate_refine_skills(
    root: Path,
    skill_ids: list[str],
    *,
    reasons_by_id: dict[str, list[str]] | None = None,
) -> Path:
    """F166: privacy-safe multi-tenant refine themes (skill id + bins only)."""
    reasons_by_id = reasons_by_id or {}
    dest = root / "memory" / "federation" / "skill-refine-signals.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {"schema_version": 1, "feature": "F166", "signals": []}
    if dest.is_file():
        try:
            data = json.loads(dest.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = data
                existing.setdefault("signals", [])
        except (OSError, json.JSONDecodeError):
            pass
    sigs = list(existing.get("signals") or [])
    by_theme = {
        str(s.get("theme") or s.get("id") or ""): s
        for s in sigs
        if isinstance(s, dict)
    }
    for sid in skill_ids:
        if not sid.startswith("skill-"):
            continue
        prev = by_theme.get(sid) if isinstance(by_theme.get(sid), dict) else {}
        hits = int(prev.get("hits") or 0) + 1
        entry = {
            "id": f"refine-{sid}"[:64],
            "theme": sid,
            "skill_id": sid,
            "tags": ["refine", "f165", "f166", "gepa", "constraint_ok"],
            "hits": hits,
            "util_rate_bin": "refined",
            "reasons": list(reasons_by_id.get(sid) or prev.get("reasons") or [])[:6],
            "tenants": int(prev.get("tenants") or 1),
            "updated_at": _now(),
            "feature": "F166",
        }
        by_theme[sid] = entry
    existing["signals"] = list(by_theme.values())[-100:]
    existing["feature"] = "F166"
    existing["updated_at"] = _now()
    dest.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return dest


def _write_refine_report(out_dir: Path, report: dict[str, Any]) -> Path | None:
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "skill-refine.json"
        dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return dest
    except OSError:
        return None


def cmd_refine_from_util(args: argparse.Namespace) -> int:
    """F165: GEPA-lite refine skill bodies from recovery/hub-archival util traces."""
    out_dir = Path(args.out_dir)
    if not out_dir.is_dir():
        print(json.dumps({"feature": FEATURE_REFINE, "error": "no_out_dir", "ok": False}))
        return 1
    apply = not bool(getattr(args, "dry_run", False))
    if getattr(args, "apply", False):
        apply = True
    force = []
    raw_force = (getattr(args, "force_skills", "") or "").strip()
    if raw_force:
        force = [s.strip() for s in raw_force.split(",") if s.strip()]
    report = refine_from_util(
        out_dir,
        root=_root(),
        apply=apply,
        force_skills=force or None,
        min_gap_rate=float(args.min_gap) if getattr(args, "min_gap", None) is not None else None,
    )
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


def cmd_fixture_refine(args: argparse.Namespace) -> int:
    """F165 hermetic: weak hub-archival body + util gap → refine + constraint pass."""
    import tempfile

    root_real = _root()
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        os.environ["TORII_ROOT"] = str(td_path)
        os.environ["TORII_EVOLUTION_ROOT"] = str(td_path / "memory" / "evolution")
        os.environ["TORII_SKILL_REFINE"] = "1"
        out = td_path / "out"
        out.mkdir(parents=True)
        active = td_path / "agent" / "skills" / "active"
        active.mkdir(parents=True)
        sid = "skill-prefer-hub-archival-early"
        # Weak body: missing hub_boost / archival CLI (inject-only slogans)
        weak = (
            f"---\nid: {sid}\nfeature: F154\nstatus: adopted\nalways: true\n"
            f"always_priority: 95\n---\n\n"
            f"## Skill: prefer-hub-archival-early (weak)\n\n"
            f"Remember multi-tenant warm themes when reviewing PRs.\n"
            f"Prefer archival memory if available.\n"
        )
        (active / f"{sid}.md").write_text(weak, encoding="utf-8")
        # this-run util gap
        (out / "recovery-skill-util.json").write_text(
            json.dumps(
                {
                    "feature": "F121",
                    "feature_hub_archival_util": "F155",
                    "recovery_injected": [sid, "skill-prefer-memory-cli-early"],
                    "recovery_injected_n": 2,
                    "tool_hit_ids": ["skill-prefer-memory-cli-early"],
                    "idle_ids": [sid],
                    "prose_only_ids": [sid],
                    "util_rate": 0.5,
                    "utilization_gap": True,
                    "hub_archival_injected": True,
                    "hub_archival_tool_hit": False,
                    "hub_archival_idle": True,
                    "hub_archival_util_gap": True,
                }
            ),
            encoding="utf-8",
        )
        # chronic fitness gap
        fit_dir = td_path / ".torii"
        fit_dir.mkdir(parents=True)
        (fit_dir / "skill-fitness.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "feature": "F158",
                    "skills": {
                        sid: {
                            "id": sid,
                            "hub_archival_selected_n": 3,
                            "hub_archival_hit_n": 0,
                            "hub_archival_gap_n": 3,
                            "hub_archival_util_rate": 0.0,
                            "hub_archival_gap_rate": 1.0,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        before_gate = constraint_validate_skill(weak, sid)
        report = refine_from_util(out, root=td_path, apply=True)
        after_text = (active / f"{sid}.md").read_text(encoding="utf-8")
        after_gate = constraint_validate_skill(after_text, sid)
        has_marker = REFINE_MARKER in after_text
        refined_n = int(report.get("refined_n") or 0)
        # diagnose found target
        targets = diagnose_util_gaps(out, td_path)
        has_target = any(t.get("skill_id") == sid for t in targets)
        f165_ok = (
            has_target
            and refined_n >= 1
            and has_marker
            and after_gate.get("ok") is True
            and not before_gate.get("ok")  # weak failed probes; refined passes
            and "hub_boost" in after_text
            and "archival_memory_search.py" in after_text
        )
        # paper artifact under real repo fixtures (optional write)
        result = {
            "feature": FEATURE_REFINE,
            "fixture_pass": f165_ok,
            "f165_ok": f165_ok,
            "has_target": has_target,
            "refined_n": refined_n,
            "has_marker": has_marker,
            "before_constraint_ok": before_gate.get("ok"),
            "after_constraint_ok": after_gate.get("ok"),
            "before_errors": before_gate.get("errors"),
            "after_missing": after_gate.get("missing_probes"),
            "reasons": next(
                (t.get("reasons") for t in targets if t.get("skill_id") == sid),
                [],
            ),
            "report_ok": report.get("ok"),
        }
        print(json.dumps(result, indent=2))
        # restore TORII_ROOT for caller
        os.environ["TORII_ROOT"] = str(root_real)
        return 0 if f165_ok else 1


def cmd_ingest(args: argparse.Namespace) -> int:
    """Package one run's agent-loop into a trajectory (H9-style)."""
    root = _root()
    out_dir = Path(args.out_dir).resolve()
    loop = out_dir / "agent-loop" / "agent-loop.json"
    if not loop.is_file():
        # try trace dir
        latest = out_dir / "latest-trace-dir.txt"
        if latest.is_file():
            tdir = Path(latest.read_text().strip())
            alt = tdir / "agent-loop" / "agent-loop.json"
            if alt.is_file():
                loop = alt
    if not loop.is_file():
        print("error: agent-loop.json not found", file=sys.stderr)
        return 1

    data = json.loads(loop.read_text(encoding="utf-8", errors="replace"))
    turns = data.get("tool_call_turns")
    try:
        turns_i = int(turns) if turns is not None else 0
    except (TypeError, ValueError):
        turns_i = 0

    pr = str(args.pr or os.environ.get("PR_NUMBER") or "unknown")
    repo = str(args.repo or os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or "unknown")
    tid = str(data.get("session_id") or f"pr{pr}-{_now()}")
    safe = _slug(f"pr{pr}-{tid}")[:80]

    traj_dir = _evo_root(root) / "trajectories" / safe
    traj_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(loop, traj_dir / "agent-loop.json")
    # companion artifacts if present
    for name in ("agent-loop.md", "hermes-usage.json", "timings.json"):
        src = out_dir / name
        if name == "agent-loop.md":
            src = out_dir / "agent-loop" / "agent-loop.md"
        if src.is_file():
            shutil.copy2(src, traj_dir / src.name)
    hermes_run = out_dir / "hermes-run.log"
    if hermes_run.is_file():
        # cap copy size
        raw = hermes_run.read_bytes()
        traj_dir.joinpath("hermes-run.log").write_bytes(raw[-200_000:])

    meta = {
        "feature": "F69",
        "ingested_at": _now(),
        "trajectory_id": safe,
        "repo": repo,
        "pr_number": pr,
        "tool_call_turns": turns_i,
        "message_count": data.get("message_count") or len(data.get("messages") or []),
        "model": data.get("model"),
        "session_id": data.get("session_id"),
        "signals": _signals_from_loop(data, out_dir),
    }
    (traj_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    ledger = _load_ledger(root)
    # de-dupe by trajectory_id
    ledger["trajectories"] = [
        t for t in ledger.get("trajectories") or [] if t.get("trajectory_id") != safe
    ]
    ledger["trajectories"].append(
        {
            "trajectory_id": safe,
            "path": (
                str(traj_dir.relative_to(root))
                if str(traj_dir).startswith(str(root))
                else str(traj_dir)
            ),
            "repo": repo,
            "pr_number": pr,
            "tool_call_turns": turns_i,
            "signals": meta["signals"],
            "ingested_at": meta["ingested_at"],
        }
    )
    # keep last 100
    ledger["trajectories"] = ledger["trajectories"][-100:]
    _save_ledger(root, ledger)

    print(f"trajectory={safe}")
    print(f"path={traj_dir}")
    print(f"tool_call_turns={turns_i}")
    print(f"signals={','.join(meta['signals']) or 'none'}")
    return 0


# F117: allowlisted tool-outcome catalog (pattern → skill). Never free-form log regex.
# Patterns are fixed product/security CLIs only — mined only when observed in-loop.
TOOL_PROBE_CATALOG: list[dict[str, str]] = [
    {
        "pattern": r"torii\.py\s+memory\b",
        "skill": "skill-prefer-memory-cli-early",
        "label": "torii.py memory",
    },
    {
        "pattern": r"torii_memory\.py\b",
        "skill": "skill-prefer-memory-cli-early",
        "label": "torii_memory.py",
    },
    {
        "pattern": r"archival_memory_search\.py\b",
        "skill": "skill-prefer-memory-cli-early",
        "label": "archival_memory_search",
    },
    {
        "pattern": r"memory_temporal_graph\.py\b",
        "skill": "skill-prefer-memory-cli-early",
        "label": "memory_temporal_graph",
    },
    {
        "pattern": r"memory_compound_write\.py\b",
        "skill": "skill-prefer-memory-cli-early",
        "label": "memory_compound_write",
    },
    {
        "pattern": r"torii\.py\s+doctor\b",
        "skill": "skill-prefer-product-cli",
        "label": "torii.py doctor",
    },
    {
        "pattern": r"torii\.py\s+status\b",
        "skill": "skill-prefer-product-cli",
        "label": "torii.py status",
    },
    {
        "pattern": r"torii\.py\s+budget\b",
        "skill": "skill-prefer-product-cli",
        "label": "torii.py budget",
    },
    {
        "pattern": r"second_agent_critic\.py\b",
        "skill": "skill-prefer-critic-early",
        "label": "second_agent_critic",
    },
    {
        "pattern": r"chain_revalidate\.py\b",
        "skill": "skill-f74-prefer-chain-json",
        "label": "chain_revalidate",
    },
    {
        "pattern": r"taint_prefilter\.py\b",
        "skill": "skill-f74-prefer-chain-json",
        "label": "taint_prefilter",
    },
    {
        "pattern": r"\brg\s+-n\b",
        "skill": "skill-tool-depth-hunks",
        "label": "rg -n",
    },
    {
        "pattern": r"\bsed\s+-n\b",
        "skill": "skill-tool-depth-hunks",
        "label": "sed -n",
    },
]

# Skill proposal bodies for novel F117 families (not already F112 memory)
F117_SKILL_TEMPLATES: dict[str, dict[str, str]] = {
    "skill-prefer-product-cli": {
        "title": "Call torii product CLI doctor/status early",
        "signal": "f117_product_cli_tools",
        "body": (
            "## Skill: prefer-product-cli (F117)\n\n"
            "When the product umbrella CLI is available (F110):\n"
            "1. Early mid-review call once:\n"
            "   `python3 scripts/torii.py doctor` or `python3 scripts/torii.py status`\n"
            "   `python3 scripts/torii.py budget -- status` when soft re-prompts are possible.\n"
            "2. Use doctor/status as readiness hints only — still require path:line evidence.\n"
            "3. Prefer product CLI over ad-hoc script hunting for memory/gate/budget surfaces.\n"
        ),
    },
    "skill-prefer-critic-early": {
        "title": "Run second-agent critic path evidence early",
        "signal": "f117_critic_tools",
        "body": (
            "## Skill: prefer-critic-early (F117)\n\n"
            "When dual-pass critic tooling is available:\n"
            "1. After draft findings, run:\n"
            "   `python3 scripts/second_agent_critic.py score --review REVIEW`\n"
            "2. Demote APPROVE claims without path:line; boost full_chain themes.\n"
            "3. Do not self-approve unvalidated narrative — checker is independent.\n"
        ),
    },
}


def _falsey(raw: str) -> bool:
    return raw.strip().lower() in {"0", "false", "no", "off", "disabled", "n", "none", ""}


def tool_probe_mine_enabled() -> bool:
    raw = (os.environ.get("TORII_TOOL_PROBE_MINE") or "1").strip().lower()
    return not _falsey(raw)


def _import_skill_router():
    import importlib.util

    path = Path(__file__).resolve().parent / "skill_router.py"
    name = "skill_router"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _collect_tool_blob(out_dir: Path) -> str:
    chunks: list[str] = []
    for rel in (
        "agent-loop/agent-loop.json",
        "agent-loop.json",
        "agent-loop/agent.log",
        "hermes.log",
        "skill-hits.json",
        "skill-attribution.json",
        "memory-tool-audit.json",
    ):
        p = out_dir / rel
        if p.is_file():
            try:
                chunks.append(p.read_text(encoding="utf-8", errors="replace")[:120_000])
            except OSError:
                continue
    return "\n".join(chunks)


def _load_probe_ledger(root: Path) -> dict[str, Any]:
    sr = _import_skill_router()
    path = sr.probe_ledger_path(root)
    if not path.is_file():
        return {
            "schema_version": 1,
            "feature": "F117",
            "updated_at": _now(),
            "skills": {},
            "history": [],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("schema_version", 1)
    data.setdefault("feature", "F117")
    data.setdefault("skills", {})
    data.setdefault("history", [])
    return data


def _save_probe_ledger(root: Path, ledger: dict[str, Any]) -> Path:
    sr = _import_skill_router()
    path = sr.probe_ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger["schema_version"] = 1
    ledger["feature"] = "F117"
    ledger["updated_at"] = _now()
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return path


def mine_tool_probes(
    out_dir: Path,
    *,
    root: Path | None = None,
    propose: bool = False,
    min_hits: int = 1,
) -> dict[str, Any]:
    """F117: observe allowlisted tools in-loop → durable probe ledger (+ optional propose)."""
    root = root or _root()
    out_dir = Path(out_dir)
    blob = _collect_tool_blob(out_dir)
    # also fold skill-hits tool_matched labels
    hits_doc: dict[str, Any] = {}
    hp = out_dir / "skill-hits.json"
    if hp.is_file():
        try:
            hits_doc = json.loads(hp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            hits_doc = {}

    observed: list[dict[str, str]] = []
    for entry in TOOL_PROBE_CATALOG:
        pat = entry["pattern"]
        try:
            rx = re.compile(pat, re.I)
        except re.error:
            continue
        if blob and rx.search(blob):
            observed.append(dict(entry))
            continue
        # skill-hits may already label tool_matched
        for h in hits_doc.get("hits") or []:
            if not isinstance(h, dict):
                continue
            labels = " ".join(str(x) for x in (h.get("tool_matched") or []))
            if h.get("tool_hit") and (rx.search(labels) or entry["label"].lower() in labels.lower()):
                observed.append(dict(entry))
                break

    ledger = _load_probe_ledger(root)
    skills = ledger.setdefault("skills", {})
    added: list[str] = []
    reinforced: list[str] = []
    for obs in observed:
        sid = obs["skill"]
        pat = obs["pattern"]
        ent = skills.get(sid) or {
            "id": sid,
            "patterns": [],
            "labels": [],
            "hits": 0,
            "source": "f117_mine",
        }
        pats = list(ent.get("patterns") or [])
        labels = list(ent.get("labels") or [])
        if pat not in pats:
            pats.append(pat)
            added.append(f"{sid}:{obs['label']}")
        else:
            reinforced.append(f"{sid}:{obs['label']}")
        if obs["label"] not in labels:
            labels.append(obs["label"])
        ent["patterns"] = pats[:16]
        ent["labels"] = labels[:16]
        ent["hits"] = int(ent.get("hits") or 0) + 1
        ent["last_seen"] = _now()
        ent["id"] = sid
        skills[sid] = ent

    # only keep patterns with hits >= min_hits for scoring (all stored, scored if hits ok)
    # skill_router uses all patterns; hits counter is for propose gate
    path = _save_probe_ledger(root, ledger)
    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "out_dir": str(out_dir),
            "observed_n": len(observed),
            "added": added[:16],
            "reinforced": reinforced[:16],
            "tool_hit_n": hits_doc.get("tool_hit_n"),
        }
    )
    ledger["history"] = hist[-80:]
    _save_probe_ledger(root, ledger)

    proposed: list[str] = []
    if propose:
        proposed = _propose_from_mined(root, skills, min_hits=min_hits)

    # novel families observed this run
    families = sorted({o["skill"] for o in observed})
    return {
        "feature": "F117",
        "ledger": str(path),
        "observed_n": len(observed),
        "observed_skills": families,
        "added": added,
        "reinforced": reinforced,
        "proposed": proposed,
        "skills_n": len(skills),
        "privacy_ok": "/Users/" not in json.dumps(skills),
    }


def _propose_from_mined(
    root: Path,
    skills: dict[str, Any],
    *,
    min_hits: int = 1,
) -> list[str]:
    """Create proposals for F117 skill families with enough mined hits."""
    proposals_dir = root / "agent" / "skills" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    for d in (
        proposals_dir,
        root / "agent" / "skills" / "active",
    ):
        if d.is_dir():
            for p in d.glob("*.md"):
                if p.name != "README.md":
                    existing.add(p.stem)
    created: list[str] = []
    ledger = _load_ledger(root)
    for sid, tmpl in F117_SKILL_TEMPLATES.items():
        ent = skills.get(sid) or {}
        if int(ent.get("hits") or 0) < min_hits:
            continue
        if sid in existing:
            continue
        path = proposals_dir / f"{sid}.md"
        header = (
            f"---\n"
            f"id: {sid}\n"
            f"feature: F117\n"
            f"status: proposal\n"
            f"signal: {tmpl['signal']}\n"
            f"created_at: {_now()}\n"
            f"title: {tmpl['title']}\n"
            f"---\n\n"
        )
        path.write_text(header + tmpl["body"], encoding="utf-8")
        entry = {
            "id": sid,
            "title": tmpl["title"],
            "path": str(path.relative_to(root)) if str(path).startswith(str(root)) else str(path),
            "signal": tmpl["signal"],
            "status": "proposal",
            "created_at": _now(),
            "eval": None,
            "feature": "F117",
        }
        ledger["proposals"] = [p for p in ledger.get("proposals") or [] if p.get("id") != sid]
        ledger["proposals"].append(entry)
        existing.add(sid)
        created.append(sid)
    if created:
        _save_ledger(root, ledger)
    return created


def _signals_from_loop(data: dict[str, Any], out_dir: Path) -> list[str]:
    signals: list[str] = []
    try:
        turns = int(data.get("tool_call_turns") or 0)
    except (TypeError, ValueError):
        turns = 0
    if turns == 0:
        signals.append("zero_tools")
    if turns >= 10:
        signals.append("deep_tools")
    # F49 recovery marker
    envp = out_dir / "tool-turns-reprompt.env"
    if envp.is_file():
        txt = envp.read_text(encoding="utf-8", errors="replace")
        if "reprompt=1" in txt or "recovered=1" in txt:
            signals.append("f49_recovered")
    # F105/F106 memory utilization + soft re-prompt recovery (F112)
    mem_env = out_dir / "memory-tool-reprompt.env"
    if mem_env.is_file():
        txt = mem_env.read_text(encoding="utf-8", errors="replace")
        if "reprompt=1" in txt or "attempted=1" in txt:
            signals.append("f106_memory_reprompt")
        if "recovered=1" in txt or "reason=reprompt_recovered" in txt:
            signals.append("f106_recovered")
        if "budget_blocked" in txt:
            signals.append("f108_budget_blocked")
    # F153: F152 recon-warm hub soft re-prompt → prefer hub-aware archival skill
    rw_env = out_dir / "recon-warm-reprompt.env"
    if rw_env.is_file():
        txt = rw_env.read_text(encoding="utf-8", errors="replace")
        if "reprompt=1" in txt or "attempted=1" in txt:
            signals.append("f152_recon_warm_reprompt")
        if "recovered=1" in txt or "reason=reprompt_recovered" in txt:
            signals.append("f152_recon_warm_recovered")
        if "budget_blocked" in txt:
            signals.append("f108_budget_blocked")
        if "recon_warm_hub_heat_idle" in txt or "reason=recon_warm" in txt:
            signals.append("f152_recon_warm_heat_idle")
    rw_dec = out_dir / "recon-warm-reprompt-decide.json"
    if rw_dec.is_file():
        try:
            d = json.loads(rw_dec.read_text(encoding="utf-8", errors="replace"))
            if isinstance(d, dict):
                if int(d.get("reprompt") or 0) == 1:
                    signals.append("f152_recon_warm_reprompt")
                if d.get("high") and d.get("local_idle"):
                    signals.append("f152_recon_warm_heat_idle")
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    audit_p = out_dir / "memory-tool-audit.json"
    if audit_p.is_file():
        try:
            audit = json.loads(audit_p.read_text(encoding="utf-8", errors="replace"))
            if isinstance(audit, dict):
                if audit.get("utilization_gap"):
                    signals.append("memory_utilization_gap")
                hits = int(audit.get("hit_count") or 0)
                if hits >= 1 and "torii_memory" in (audit.get("tools_used") or []):
                    signals.append("memory_tools_used")
                if audit.get("inject_offered") and hits == 0:
                    signals.append("memory_inject_unused")
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    # F114/F116/F117: skill-hits tool outcomes
    hits_p = out_dir / "skill-hits.json"
    if hits_p.is_file():
        try:
            hits = json.loads(hits_p.read_text(encoding="utf-8", errors="replace"))
            if isinstance(hits, dict):
                thr = int(hits.get("tool_hit_n") or 0)
                if thr >= 1:
                    signals.append("f114_tool_hit")
                for sid in hits.get("tool_outcome_skills") or []:
                    if "memory" in str(sid):
                        signals.append("f117_memory_tools")
                    if "product" in str(sid) or "cli" in str(sid):
                        signals.append("f117_product_cli_tools")
                # scan tool_matched labels
                blob_labels = " ".join(
                    str(x)
                    for h in (hits.get("hits") or [])
                    if isinstance(h, dict)
                    for x in (h.get("tool_matched") or [])
                )
                if "doctor" in blob_labels.lower() or "torii.py status" in blob_labels.lower():
                    signals.append("f117_product_cli_tools")
                if "second_agent_critic" in blob_labels.lower():
                    signals.append("f117_critic_tools")
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    attr_p = out_dir / "skill-attribution.json"
    if attr_p.is_file():
        try:
            attr = json.loads(attr_p.read_text(encoding="utf-8", errors="replace"))
            if isinstance(attr, dict) and int(attr.get("tool_hit_n") or 0) >= 1:
                signals.append("f115_tool_attr")
                for sid in attr.get("tool_contributors") or []:
                    if "memory" in str(sid):
                        signals.append("f117_memory_tools")
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    # F50
    for rev in out_dir.glob("review-*.md"):
        if ".raw." in rev.name:
            continue
        body = rev.read_text(encoding="utf-8", errors="replace")
        if "Severity calibration" in body or "approve_with_test_gap" in body:
            signals.append("f50_test_gap")
        if "REQUEST CHANGES" in body:
            signals.append("verdict_request_changes")
        if "**Verdict:** APPROVE" in body or "**Verdict:** APPROVE" in body:
            signals.append("verdict_approve")
        break
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for s in signals:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# F132: scorecard metric → skill proposal templates (privacy-safe themes only)
SCORECARD_GAP_TEMPLATES: dict[str, dict[str, str]] = {
    "recovery_ok": {
        "id": "skill-prefer-recovery-skills-active",
        "title": "Keep recovery skills active (memory/product/critic)",
        "body": (
            "## Skill: prefer-recovery-skills-active (F132)\n\n"
            "When product doctor or scorecard shows recovery_ok gap:\n"
            "1. Ensure active skills include memory/product/critic recovery skills.\n"
            "2. Call `python3 scripts/torii.py doctor` and "
            "`python3 scripts/skill_loop_status.py scorecard --shallow`.\n"
            "3. Prefer recovery CLIs mid-review; do not APPROVE with idle recovery.\n"
        ),
    },
    "recovery_hub_gap_ok": {
        "id": "skill-prefer-hub-gap-critic",
        "title": "Wire hub gap critic before soft APPROVE",
        "body": (
            "## Skill: prefer-hub-gap-critic (F132)\n\n"
            "When recovery_hub_gap_ok is false:\n"
            "1. Run `python3 scripts/second_agent_critic.py demote-eval`.\n"
            "2. Ensure f127_hub_gap checker is in the panel path.\n"
            "3. Demote APPROVE when multi-tenant hub gap_pressure is high and "
            "recovery tools are idle.\n"
        ),
    },
    "demote_eval_pass": {
        "id": "skill-prefer-demote-eval-check",
        "title": "Run critic demote-eval pack before claiming readiness",
        "body": (
            "## Skill: prefer-demote-eval-check (F132)\n\n"
            "Ops/install readiness requires measured demote rate:\n"
            "1. `python3 scripts/second_agent_critic.py demote-eval`\n"
            "2. Confirm weak APPROVE demotes; hub-gap idle APPROVE demotes.\n"
            "3. Surface critic_approve_demote_rate in product scorecard.\n"
        ),
    },
    "memory_util_eval_pass": {
        "id": "skill-prefer-memory-util-eval",
        "title": "Prove memory tools fire (util-eval delta)",
        "body": (
            "## Skill: prefer-memory-util-eval (F132)\n\n"
            "Mem0/Letta: memory only helps if tools are called.\n"
            "1. `python3 scripts/memory_tool_audit.py util-eval`\n"
            "2. Require memory_tool_util_delta ≥ 0.4 (good vs inject-unused weak).\n"
            "3. Mid-review call `python3 scripts/torii.py memory -- search` once.\n"
        ),
    },
    "workflow_ok": {
        "id": "skill-prefer-workflow-scorecard",
        "title": "Validate workflows-as-code graph readiness",
        "body": (
            "## Skill: prefer-workflow-scorecard (F132)\n\n"
            "When workflow_ok is false:\n"
            "1. `python3 scripts/torii.py workflow -- scorecard`\n"
            "2. `python3 scripts/workflow_as_code.py validate`\n"
            "3. Fix missing stage scripts before claiming install readiness.\n"
        ),
    },
    "dual_compound_triple_ready": {
        "id": "skill-prefer-dual-compound-ops",
        "title": "Close dual compound triple (skill+memory+workflow L3)",
        "body": (
            "## Skill: prefer-dual-compound-ops (F132)\n\n"
            "Brand readiness needs skill L3 + memory L3 + workflow L3:\n"
            "1. `python3 scripts/torii.py scorecard`\n"
            "2. Read dual_compound.triple_ready; fix the failing loop first.\n"
            "3. Prefer scorecard over vibe-based “we’re ready” claims.\n"
        ),
    },
    "brand_ready": {
        "id": "skill-prefer-product-scorecard",
        "title": "Run product scorecard as day-2 habit",
        "body": (
            "## Skill: prefer-product-scorecard (F132)\n\n"
            "Install/ops day-2 habit:\n"
            "1. `python3 scripts/torii.py doctor`\n"
            "2. `python3 scripts/torii.py scorecard`\n"
            "3. Treat brand_ready=false as blocking for Hub71 demos / ship claims.\n"
        ),
    },
}


def scorecard_gaps(metrics: dict[str, Any], *, brand_ready: bool | None = None) -> list[str]:
    """Return metric keys that are gaps (privacy-safe bool/level fields only)."""
    gaps: list[str] = []
    bool_keys = (
        "recovery_ok",
        "recovery_hub_gap_ok",
        "demote_eval_pass",
        "memory_util_eval_pass",
        "workflow_ok",
        "dual_compound_triple_ready",
    )
    for k in bool_keys:
        if k not in metrics:
            continue
        v = metrics.get(k)
        if v is False or v is None:
            gaps.append(k)
    if brand_ready is False and "brand_ready" not in gaps:
        gaps.append("brand_ready")
    # level gaps
    for lk, need in (
        ("skill_loop_level", ("L2", "L3")),
        ("memory_loop_level", ("L2", "L3")),
        ("workflow_level", ("L2", "L3")),
    ):
        lv = metrics.get(lk)
        if lv is not None and lv not in need:
            if lk == "workflow_level" and "workflow_ok" not in gaps:
                gaps.append("workflow_ok")
            elif lk == "skill_loop_level" and "recovery_ok" not in gaps:
                gaps.append("recovery_ok")
            elif lk == "memory_loop_level" and "memory_util_eval_pass" not in gaps:
                gaps.append("memory_util_eval_pass")
    return gaps


def propose_from_scorecard(
    root: Path,
    scorecard: dict[str, Any] | None = None,
    *,
    limit: int = 5,
    write: bool = True,
) -> dict[str, Any]:
    """F132: scorecard gap themes → skill proposals (self-evolution inter-test-time)."""
    root = root or _root()
    if scorecard is None:
        # load last product scorecard or run shallow via torii if available
        for cand in (
            root / ".torii" / "product-scorecard.json",
            root / "docs" / "brand" / "scorecard-metrics.md",
        ):
            if cand.suffix == ".json" and cand.is_file():
                try:
                    scorecard = json.loads(cand.read_text(encoding="utf-8"))
                    break
                except (OSError, json.JSONDecodeError):
                    continue
    if scorecard is None:
        scorecard = {"metrics": {}, "brand_ready": None}

    metrics = dict(scorecard.get("metrics") or {})
    # dual_compound triple into metrics if nested
    dc = scorecard.get("dual_compound") or {}
    if "dual_compound_triple_ready" not in metrics and "triple_ready" in dc:
        metrics["dual_compound_triple_ready"] = bool(dc.get("triple_ready"))
    gaps = scorecard_gaps(metrics, brand_ready=scorecard.get("brand_ready"))
    # always propose product-scorecard habit if no gaps (maintenance signal)
    if not gaps:
        gaps = ["brand_ready"]  # maintenance proposal only when fully green

    proposals_dir = root / "agent" / "skills" / "proposals"
    if write:
        proposals_dir.mkdir(parents=True, exist_ok=True)
    ledger = _load_ledger(root)
    existing = {p.get("id") for p in ledger.get("proposals") or []}
    for p in proposals_dir.glob("*.md") if proposals_dir.is_dir() else []:
        existing.add(p.stem)
    active = {
        p.stem
        for p in (root / "agent" / "skills" / "active").glob("*.md")
        if (root / "agent" / "skills" / "active").is_dir()
    }

    created: list[dict[str, Any]] = []
    for gap in gaps:
        if len(created) >= limit:
            break
        tmpl = SCORECARD_GAP_TEMPLATES.get(gap)
        if not tmpl:
            continue
        sid = tmpl["id"]
        if sid in existing or sid in active:
            continue
        body = (
            f"---\nid: {sid}\ntitle: {tmpl['title']}\n"
            f"themes: scorecard,ops,readiness,f132\n"
            f"always: false\n---\n\n{tmpl['body']}"
        )
        entry = {
            "id": sid,
            "title": tmpl["title"],
            "status": "proposed",
            "source": "scorecard_gap",
            "gap": gap,
            "feature": "F132",
            "created_at": _now(),
        }
        if write:
            path = proposals_dir / f"{sid}.md"
            path.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
            try:
                entry["path"] = str(path.resolve().relative_to(root.resolve()))
            except ValueError:
                entry["path"] = path.name
            ledger["proposals"] = [
                p for p in ledger.get("proposals") or [] if p.get("id") != sid
            ]
            ledger["proposals"].append(entry)
        created.append(entry)
        existing.add(sid)

    if write and created:
        hist = ledger.setdefault("history", [])
        hist.append(
            {
                "at": _now(),
                "event": "propose_scorecard",
                "feature": "F132",
                "gaps": gaps[:12],
                "created": [c["id"] for c in created],
            }
        )
        ledger["history"] = hist[-100:]
        _save_ledger(root, ledger)

    return {
        "feature": "F132",
        "gaps": gaps,
        "created_n": len(created),
        "created": created,
        "brand_ready": scorecard.get("brand_ready"),
        "metrics_keys": sorted(metrics.keys())[:24],
        "scored_at": _now(),
    }


def cmd_propose_scorecard(args: argparse.Namespace) -> int:
    """F132: propose skills from product scorecard gap themes."""
    root = _root()
    sc = None
    if getattr(args, "scorecard", None) and args.scorecard:
        p = Path(args.scorecard)
        if p.is_file():
            sc = json.loads(p.read_text(encoding="utf-8"))
    # optional: force synthetic gaps for fixture via env
    force_gaps = (os.environ.get("TORII_SCORECARD_FORCE_GAPS") or "").strip()
    if force_gaps and sc is None:
        sc = {
            "brand_ready": False,
            "metrics": {k: False for k in force_gaps.split(",") if k.strip()},
        }
    report = propose_from_scorecard(
        root,
        sc,
        limit=int(getattr(args, "limit", 5) or 5),
        write=not bool(getattr(args, "dry_run", False)),
    )
    print(json.dumps(report, indent=2))
    return 0 if report.get("created_n", 0) >= 0 else 1


def cmd_propose(args: argparse.Namespace) -> int:
    """Turn trajectory signals into skill proposals (H3 skill-file evolution lite)."""
    root = _root()
    ledger = _load_ledger(root)
    trajs = ledger.get("trajectories") or []
    if not trajs:
        print("error: no trajectories — run ingest first", file=sys.stderr)
        return 1

    # Aggregate signals
    sig_count: dict[str, int] = {}
    for t in trajs:
        for s in t.get("signals") or []:
            sig_count[s] = sig_count.get(s, 0) + 1

    proposals_dir = root / "agent" / "skills" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    existing = {p.get("id") for p in ledger.get("proposals") or []}
    existing |= {p.get("id") for p in ledger.get("adopted") or []}
    # also filesystem
    for p in proposals_dir.glob("*.md"):
        existing.add(p.stem)
    active = root / "agent" / "skills" / "active"
    if active.is_dir():
        for p in active.glob("*.md"):
            if p.name != "README.md":
                existing.add(p.stem)

    templates: list[dict[str, Any]] = []
    if sig_count.get("zero_tools", 0) >= 1 or sig_count.get("f49_recovered", 0) >= 1:
        templates.append(
            {
                "id": "skill-tool-depth-hunks",
                "title": "Tool depth: prefer diff hunks over file heads",
                "signal": "zero_tools|f49_recovered",
                "body": (
                    "## Skill: tool-depth-hunks (F69)\n\n"
                    "When reviewing multi-file code PRs:\n"
                    "1. Open the unified **diff file** first for exact `+/-` hunks.\n"
                    "2. Use `rg -n SYMBOL path` then `sed -n 'START,ENDp'` — never stop at `head`.\n"
                    "3. At least one tool must target a **changed region or symbol**.\n"
                    "4. If tools fail, say so; do not APPROVE on incomplete evidence.\n"
                ),
            }
        )
    if sig_count.get("f50_test_gap", 0) >= 1:
        templates.append(
            {
                "id": "skill-test-gap-blocking",
                "title": "Claim-to-fix: missing tests are blocking",
                "signal": "f50_test_gap",
                "body": (
                    "## Skill: test-gap-blocking (F69)\n\n"
                    "When the PR claims to fix production behavior:\n"
                    "1. Locate new production paths in the diff.\n"
                    "2. Check for tests covering those paths (table-driven / unit).\n"
                    "3. Missing tests → **Blocking** (not Suggestions), with a trigger scenario.\n"
                ),
            }
        )
    if sig_count.get("deep_tools", 0) >= 1:
        templates.append(
            {
                "id": "skill-preserve-deep-tools",
                "title": "Preserve deep tool patterns that worked",
                "signal": "deep_tools",
                "body": (
                    "## Skill: preserve-deep-tools (F69)\n\n"
                    "Prior high-quality runs used ≥10 tool turns. Prefer:\n"
                    "- package path + symbol citations\n"
                    "- reading tests next to production changes\n"
                    "- verifying error/retry paths for concurrency/schema gates\n"
                ),
            }
        )
    # F112: memory utilization gap / F106 recovery → call memory tools early
    if (
        sig_count.get("f106_recovered", 0) >= 1
        or sig_count.get("memory_utilization_gap", 0) >= 1
        or sig_count.get("memory_inject_unused", 0) >= 1
        or sig_count.get("f106_memory_reprompt", 0) >= 1
        or sig_count.get("f117_memory_tools", 0) >= 1
    ):
        templates.append(
            {
                "id": "skill-prefer-memory-cli-early",
                "title": "Call torii product/memory CLI early mid-review",
                "signal": "f106_recovered|memory_utilization_gap",
                "body": (
                    "## Skill: prefer-memory-cli-early (F112)\n\n"
                    "When memory sections are injected (F103 CLI / F98 archival / F100 graph / F70 TP):\n"
                    "1. **Before** finishing findings, call the product front door once:\n"
                    "   `python3 scripts/torii.py memory -- help`\n"
                    "   `python3 scripts/torii.py memory -- search -- -q \"auth OR sql OR pickle OR secret\"`\n"
                    "   or `python3 scripts/torii_memory.py search -- -q \"theme keywords\"`\n"
                    "2. Prefer **search/graph** on changed basenames (F100 multi-hop) before re-raising old themes.\n"
                    "3. Treat hits as **hints only** — still require path:line evidence to block.\n"
                    "4. Do not wait for a soft re-prompt (F106) — proactive use scores higher (F105 utilization).\n"
                    "5. Soft re-prompts share a budget (F108); early use avoids spending the only recovery slot.\n"
                ),
            }
        )
    # F153: F152 recon-warm hub re-prompt / heat idle → hub-aware archival early
    if (
        sig_count.get("f152_recon_warm_reprompt", 0) >= 1
        or sig_count.get("f152_recon_warm_recovered", 0) >= 1
        or sig_count.get("f152_recon_warm_heat_idle", 0) >= 1
    ):
        templates.append(
            {
                "id": "skill-prefer-hub-archival-early",
                "title": "Hub-aware archival search early (multi-tenant warm themes)",
                "signal": "f152_recon_warm_reprompt|f152_recon_warm_heat_idle",
                "body": (
                    "## Skill: prefer-hub-archival-early (F153)\n\n"
                    "When multi-tenant recon-warm hub heat is elevated (F148–F152):\n"
                    "1. **Before** finishing findings, run hub-aware archival paging:\n"
                    "   `python3 scripts/archival_memory_search.py auto --files changed.py`\n"
                    "   `python3 scripts/torii.py memory -- search -- -q \"hub warm themes\"`\n"
                    "   Keep `TORII_RECON_WARM_HUB_QUERY=1` (F149 expands auto-query).\n"
                    "2. Prefer hits with **hub_boost** / multi-tenant warm themes; still require path:line.\n"
                    "3. Do **not** re-raise F145-superseded cold TPs; skip hub-ignore APPROVE.\n"
                    "4. Proactive hub paging avoids spending the F108/F152 re-prompt slot.\n"
                    "5. If F152 already fired, call archival/memory once more with hub themes before verdict.\n"
                ),
                "feature": "F153",
            }
        )
    # F117: product CLI / critic tools observed in trajectories
    if sig_count.get("f117_product_cli_tools", 0) >= 1 or sig_count.get("f114_tool_hit", 0) >= 2:
        t = F117_SKILL_TEMPLATES["skill-prefer-product-cli"]
        templates.append(
            {
                "id": "skill-prefer-product-cli",
                "title": t["title"],
                "signal": t["signal"],
                "body": t["body"],
            }
        )
    if sig_count.get("f117_critic_tools", 0) >= 1:
        t = F117_SKILL_TEMPLATES["skill-prefer-critic-early"]
        templates.append(
            {
                "id": "skill-prefer-critic-early",
                "title": t["title"],
                "signal": t["signal"],
                "body": t["body"],
            }
        )
    # always offer soft mid-loop style nudge skill (H10)
    templates.append(
        {
            "id": "skill-soft-tool-nudge",
            "title": "Soft mid-review tool nudge",
            "signal": "h10_soft_nudge",
            "body": (
                "## Skill: soft-tool-nudge (F69 / H10)\n\n"
                "Prefer **fewer, deeper** tools over thrash:\n"
                "- Cap exploratory `find`/`ls` — jump to symbols from the PR title/diff.\n"
                "- After 3 tool turns without a finding, stop and write the review.\n"
                "- Prefer one solid Blocking item over five speculative nits.\n"
            ),
        }
    )

    limit = int(args.limit or 5)
    created = 0
    for tmpl in templates:
        if created >= limit:
            break
        pid = tmpl["id"]
        if pid in existing:
            continue
        path = proposals_dir / f"{pid}.md"
        feat = str(tmpl.get("feature") or "")
        if not feat:
            if tmpl["id"].startswith("skill-prefer-product") or tmpl[
                "id"
            ].startswith("skill-prefer-critic"):
                feat = "F117"
            elif "hub-archival" in tmpl["id"] or "f152" in tmpl["signal"]:
                feat = "F153"
            elif "memory-cli" in tmpl["id"] or "f106" in tmpl["signal"]:
                feat = "F112"
            else:
                feat = "F69"
        header = (
            f"---\n"
            f"id: {pid}\n"
            f"feature: {feat}\n"
            f"status: proposal\n"
            f"signal: {tmpl['signal']}\n"
            f"created_at: {_now()}\n"
            f"title: {tmpl['title']}\n"
            f"---\n\n"
        )
        path.write_text(header + tmpl["body"], encoding="utf-8")
        entry = {
            "id": pid,
            "title": tmpl["title"],
            "path": str(path.relative_to(root)),
            "signal": tmpl["signal"],
            "status": "proposal",
            "created_at": _now(),
            "eval": None,
            "feature": feat,
        }
        ledger["proposals"] = [p for p in ledger.get("proposals") or [] if p.get("id") != pid]
        ledger["proposals"].append(entry)
        existing.add(pid)
        created += 1
        print(f"proposal={pid} path={path}")

    _save_ledger(root, ledger)
    print(f"created={created}")
    print(f"signal_counts={json.dumps(sig_count)}")
    return 0 if created else 0


def _eval_proposal(path: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    # Heuristic quality: structure + actionability
    has_skill = "## Skill:" in text or text.lstrip().startswith("## Skill")
    bullets = len(re.findall(r"(?m)^\s*[-*]\s+\S", text))
    words = len(text.split())
    traj_n = len(ledger.get("trajectories") or [])

    structure = 5 if has_skill and bullets >= 3 else (3 if has_skill else 1)
    actionability = min(5, 2 + min(3, bullets))
    evidence = min(5, 1 + min(4, traj_n // 2 + 1))
    safety = 5  # skills are prompt snippets only — pure text
    size = 5 if 40 <= words <= 400 else (3 if words < 600 else 1)

    total = structure + actionability + evidence + safety + size
    recommend = "adopt" if total >= 18 and structure >= 3 else "revise"
    return {
        "scored_at": _now(),
        "dims": {
            "structure": structure,
            "actionability": actionability,
            "evidence": evidence,
            "safety": safety,
            "size": size,
        },
        "total": total,
        "max": 25,
        "recommend": recommend,
        "words": words,
        "bullets": bullets,
    }


def cmd_eval(args: argparse.Namespace) -> int:
    root = _root()
    ledger = _load_ledger(root)
    target = (args.proposal or "all").strip()
    n = 0
    for p in ledger.get("proposals") or []:
        if target not in ("all", p.get("id")):
            continue
        path = root / p["path"] if not Path(p["path"]).is_absolute() else Path(p["path"])
        ev = _eval_proposal(path, ledger)
        p["eval"] = ev
        p["status"] = "evaluated"
        n += 1
        print(f"{p['id']}: total={ev['total']}/25 recommend={ev['recommend']}")
    _save_ledger(root, ledger)
    print(f"evaluated={n}")
    return 0 if n else 1


def cmd_adopt(args: argparse.Namespace) -> int:
    root = _root()
    ledger = _load_ledger(root)
    pid = args.proposal_id.strip()
    prop = None
    for p in list(ledger.get("proposals") or []):
        if p.get("id") == pid:
            prop = p
            break
    if not prop:
        # filesystem-only proposal
        path = root / "agent" / "skills" / "proposals" / f"{pid}.md"
        if path.is_file():
            prop = {
                "id": pid,
                "path": str(path.relative_to(root)),
                "title": pid,
                "status": "proposal",
            }
        else:
            print(f"error: proposal not found: {pid}", file=sys.stderr)
            return 1

    ev = prop.get("eval") or {}
    if (ev.get("recommend") or "").lower() == "revise" and not args.force:
        print("error: eval recommend=revise; re-eval or --force", file=sys.stderr)
        return 2

    src = root / prop["path"] if not Path(prop["path"]).is_absolute() else Path(prop["path"])
    if not src.is_file():
        print(f"error: missing file {src}", file=sys.stderr)
        return 1

    active = root / "agent" / "skills" / "active"
    active.mkdir(parents=True, exist_ok=True)
    dest = active / f"{pid}.md"
    text = src.read_text(encoding="utf-8", errors="replace")
    # strip yaml front matter status → adopted
    text2 = re.sub(r"(?m)^status:\s*\w+\s*$", "status: adopted", text, count=1)
    if "status: adopted" not in text2:
        text2 = f"<!-- F69 adopted {_now()} -->\n" + text2
    dest.write_text(text2 if text2.endswith("\n") else text2 + "\n", encoding="utf-8")

    ledger["proposals"] = [p for p in ledger.get("proposals") or [] if p.get("id") != pid]
    ledger["adopted"] = [a for a in ledger.get("adopted") or [] if a.get("id") != pid]
    ledger["adopted"].append(
        {
            "id": pid,
            "title": prop.get("title") or pid,
            "path": str(dest.relative_to(root)),
            "adopted_at": _now(),
            "eval": ev,
            "feature": "F69",
        }
    )
    _save_ledger(root, ledger)
    print(f"adopted={pid}")
    print(f"path={dest}")
    return 0


def _active_skills(root: Path) -> list[Path]:
    active = root / "agent" / "skills" / "active"
    if not active.is_dir():
        return []
    return sorted(
        p
        for p in active.glob("*.md")
        if p.name != "README.md" and p.is_file()
    )


def cmd_inject(args: argparse.Namespace) -> int:
    """Inject adopted skills + optional soft nudge into a review prompt."""
    root = _root()
    prompt = Path(args.prompt)
    if not prompt.is_file():
        print(f"error: prompt not found: {prompt}", file=sys.stderr)
        return 1

    # feature toggle soft-off
    if (os.environ.get("TORII_SELF_EVOLVE") or "1").strip().lower() in (
        "0",
        "false",
        "off",
        "no",
    ):
        # still allow inject if skills exist? Default ON for inject of adopted skills
        pass

    skills = _active_skills(root)
    nudge = _nudge_block(root)
    if not skills and not nudge:
        print("injected=0")
        return 0

    blocks: list[str] = []
    if skills:
        parts = ["## Evolved skills (F69 — Torii-native; treat as reviewer discipline)\n"]
        for sp in skills[:8]:
            body = sp.read_text(encoding="utf-8", errors="replace")
            # drop yaml front matter
            body = re.sub(r"(?s)^---\n.*?\n---\n", "", body).strip()
            parts.append(body)
            parts.append("")
        blocks.append("\n".join(parts).rstrip())
    if nudge:
        blocks.append(nudge)

    injection = "\n\n".join(blocks) + "\n"
    original = prompt.read_text(encoding="utf-8", errors="replace")
    if "<!-- torii-f69-skills -->" in original:
        # replace previous injection
        new = re.sub(
            r"<!-- torii-f69-skills -->.*?<!-- /torii-f69-skills -->\n?",
            f"<!-- torii-f69-skills -->\n{injection}<!-- /torii-f69-skills -->\n",
            original,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # insert before ## PR metadata if present, else append
        marker = "## PR metadata"
        chunk = f"<!-- torii-f69-skills -->\n{injection}<!-- /torii-f69-skills -->\n\n"
        if marker in original:
            new = original.replace(marker, chunk + marker, 1)
        else:
            new = original.rstrip() + "\n\n" + chunk

    out = Path(args.out) if args.out else prompt
    out.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    print(f"injected={len(skills)}")
    print(f"nudge={'1' if nudge else '0'}")
    print(f"prompt={out}")
    return 0


def _nudge_block(root: Path) -> str:
    """H10 soft skill nudge from recent trajectories."""
    ledger = _load_ledger(root)
    recent = (ledger.get("trajectories") or [])[-10:]
    if not recent:
        return ""
    zero = sum(1 for t in recent if "zero_tools" in (t.get("signals") or []))
    recovered = sum(1 for t in recent if "f49_recovered" in (t.get("signals") or []))
    if zero == 0 and recovered == 0:
        return ""
    return (
        "## Soft skill nudge (F69 / H10 — from recent trajectories)\n\n"
        f"Recent runs: {zero} zero-tool first pass(es), {recovered} F49 recoveries.\n"
        "Prefer a **short tool pass** on changed hunks before finalizing the verdict.\n"
        "Avoid thrash: after enough evidence, write the review.\n"
    )


def cmd_nudge_text(args: argparse.Namespace) -> int:
    text = _nudge_block(_root())
    if text:
        print(text)
        return 0
    print("")
    return 0


def build_status_payload(root: Path | None = None) -> dict[str, Any]:
    """Buyer day-2 self-evolution status (no research F-IDs on the one-liner)."""
    root = root or _root()
    ledger = _load_ledger(root)
    active = _active_skills(root)
    trajs = list(ledger.get("trajectories") or [])
    props = list(ledger.get("proposals") or [])
    adopted = list(ledger.get("adopted") or [])
    pending = [
        p
        for p in props
        if str(p.get("status") or "").lower()
        in {"proposal", "proposed", "pending", "eval", ""}
    ]
    adopted_status = [
        p for p in props if str(p.get("status") or "").lower() in {"adopted", "active"}
    ]
    # Dual-gate discipline: default auto-adopt off; skills only land when gates pass
    auto_adopt = (os.environ.get("TORII_SELF_EVOLVE_AUTO_ADOPT") or "0").strip() == "1"
    dual_gate_default_safe = not auto_adopt
    docs_ok = (root / "docs" / "SELF-EVOLVE.md").is_file()
    # Readiness: ledger + active skills + docs + safe default
    self_evolve_ok = (
        docs_ok
        and len(active) >= 1
        and dual_gate_default_safe
        and (len(trajs) >= 1 or len(adopted) >= 1 or len(active) >= 3)
    )
    active_names = [s.name for s in active]
    # Prefer non-research skill names for buyer display (drop skill-fNN- prefix noise in summary)
    buyer_skills = [
        n.replace(".md", "")
        for n in active_names
        if not re.match(r"skill-f\d+", n, re.I)
    ][:8]
    return {
        "feature": "SELF_EVOLVE",
        "self_evolve_ok": self_evolve_ok,
        "dual_gate_default_safe": dual_gate_default_safe,
        "auto_adopt_enabled": auto_adopt,
        "docs_ok": docs_ok,
        "trajectories_n": len(trajs),
        "proposals_n": len(props),
        "pending_proposals_n": len(pending),
        "adopted_ledger_n": len(adopted),
        "adopted_proposals_n": len(adopted_status),
        "active_skills_n": len(active),
        "active_skills": active_names,
        "buyer_skills": buyer_skills,
        "evolution_root": str(_evo_root(root)),
        "scorecard_target": "self-evolution / JTBD (dims 6 + 3)",
        "dim_lift": "measured skill adopt without free-form prompt drift",
        "one_liner": (
            "Skills measure in under dual-gate adopt — not free-form drift "
            f"(active={len(active)} · pending={len(pending)} · "
            f"safe_default={dual_gate_default_safe})"
        ),
        "at": _now(),
    }


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    payload = build_status_payload(root)
    if bool(getattr(args, "text", False)):
        ledger = _load_ledger(root)
        print(f"evolution_root={payload.get('evolution_root')}")
        print(f"self_evolve_ok={payload.get('self_evolve_ok')}")
        print(f"trajectories={payload.get('trajectories_n')}")
        print(f"proposals={payload.get('proposals_n')}")
        print(f"pending={payload.get('pending_proposals_n')}")
        print(f"adopted_ledger={payload.get('adopted_ledger_n')}")
        print(f"active_skills={payload.get('active_skills_n')}")
        print(f"dual_gate_default_safe={payload.get('dual_gate_default_safe')}")
        print(str(payload.get("one_liner") or ""))
        for t in (ledger.get("trajectories") or [])[-5:]:
            print(
                f"  [traj] {t.get('trajectory_id')} tools={t.get('tool_call_turns')} "
                f"signals={t.get('signals')}"
            )
        for p in ledger.get("proposals") or []:
            rec = (p.get("eval") or {}).get("recommend", "-")
            print(f"  [prop] {p.get('id')} status={p.get('status')} recommend={rec}")
        for a in ledger.get("adopted") or []:
            print(f"  [adopted] {a.get('id')} path={a.get('path')}")
        for s in _active_skills(root):
            print(f"  [active] {s.name}")
        return 0 if payload.get("self_evolve_ok") else 1
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("self_evolve_ok") else 1


def cmd_mine_probes(args: argparse.Namespace) -> int:
    """F117: mine allowlisted tool probes from a run dir into durable ledger."""
    if not tool_probe_mine_enabled() and not getattr(args, "force", False):
        print(json.dumps({"feature": "F117", "skipped": 1, "reason": "disabled"}))
        return 0
    out_dir = Path(args.out_dir)
    if not out_dir.is_dir():
        print(json.dumps({"feature": "F117", "error": "no_out_dir", "ok": False}))
        return 1
    result = mine_tool_probes(
        out_dir,
        root=_root(),
        propose=bool(getattr(args, "propose", False)),
        min_hits=int(getattr(args, "min_hits", 1) or 1),
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """F117 hermetic: mine doctor CLI → durable probe scores skill-prefer-product-cli."""
    import tempfile

    root = _root()
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        os.environ["TORII_ROOT"] = str(td_path)
        os.environ["TORII_EVOLUTION_ROOT"] = str(td_path / "memory" / "evolution")
        os.environ["TORII_TOOL_OUTCOME_PROBES_FILE"] = str(
            td_path / ".torii" / "tool-outcome-probes.json"
        )
        out = td_path / "out"
        loop = out / "agent-loop"
        loop.mkdir(parents=True)
        # Live agent used product doctor + memory — F117 mines both
        (loop / "agent-loop.json").write_text(
            json.dumps(
                {
                    "tool_call_turns": 4,
                    "message_count": 6,
                    "session_id": "f117-sess",
                    "messages": [
                        {
                            "role": "tool",
                            "content": "python3 scripts/torii.py doctor\n"
                            "python3 scripts/torii.py memory -- search -q sql\n"
                            "python3 scripts/second_agent_critic.py score --review r.md\n",
                        }
                    ],
                    "steps": [
                        {"cmd": "python3 scripts/torii.py doctor"},
                        {"cmd": "python3 scripts/torii.py memory -- search -q sql"},
                        {"cmd": "python3 scripts/second_agent_critic.py score --review r.md"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (out / "skill-hits.json").write_text(
            json.dumps(
                {
                    "tool_hit_n": 2,
                    "tool_hit_rate": 0.5,
                    "tool_outcome_skills": [
                        "skill-prefer-memory-cli-early",
                    ],
                    "hits": [
                        {
                            "id": "skill-prefer-memory-cli-early",
                            "hit": True,
                            "tool_hit": True,
                            "tool_matched": ["torii.py memory"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (td_path / "agent" / "skills" / "proposals").mkdir(parents=True)
        (td_path / "agent" / "skills" / "active").mkdir(parents=True)

        mined = mine_tool_probes(out, root=td_path, propose=True, min_hits=1)
        ledger = _load_probe_ledger(td_path)
        product_patterns = (ledger.get("skills") or {}).get("skill-prefer-product-cli", {})
        critic_patterns = (ledger.get("skills") or {}).get("skill-prefer-critic-early", {})
        mem_patterns = (ledger.get("skills") or {}).get("skill-prefer-memory-cli-early", {})

        # Dynamic probes must make skill_router match product doctor
        sr = _import_skill_router()
        blob = "tool: python3 scripts/torii.py doctor\n"
        matched = sr.match_tool_outcome("skill-prefer-product-cli", blob, root=td_path)
        match_ok = len(matched) >= 1

        prop_product = (
            td_path / "agent" / "skills" / "proposals" / "skill-prefer-product-cli.md"
        ).is_file()
        prop_critic = (
            td_path / "agent" / "skills" / "proposals" / "skill-prefer-critic-early.md"
        ).is_file()

        # privacy: ledger has no absolute home paths from mining
        privacy_ok = bool(mined.get("privacy_ok"))

        # F153: recon-warm re-prompt env → propose skill-prefer-hub-archival-early
        f153_ok = False
        has_f152_sig = False
        prop_ok = False
        blob_ok = False
        try:
            (out / "recon-warm-reprompt.env").write_text(
                "reprompt=1\nattempted=1\nreason=recon_warm_hub_heat_idle\n"
                "heat=1.0\nhub_boost_n=0\nfeature=F152\n",
                encoding="utf-8",
            )
            (out / "recon-warm-reprompt-decide.json").write_text(
                json.dumps(
                    {
                        "feature": "F152",
                        "reprompt": 1,
                        "high": True,
                        "local_idle": True,
                        "heat": 1.0,
                        "hub_boost_n": 0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            loop_data = json.loads((loop / "agent-loop.json").read_text(encoding="utf-8"))
            evo = td_path / "memory" / "evolution"
            evo.mkdir(parents=True, exist_ok=True)
            sigs = _signals_from_loop(loop_data, out)
            has_f152_sig = any("f152" in s for s in sigs)
            led = _load_ledger(td_path)
            led["trajectories"] = [
                {
                    "trajectory_id": "f153-rw",
                    "tool_call_turns": 3,
                    "signals": list(dict.fromkeys(sigs)),
                    "created_at": _now(),
                }
            ]
            _save_ledger(td_path, led)

            class _A:
                limit = 5

            import contextlib
            import io

            _buf = io.StringIO()
            with contextlib.redirect_stdout(_buf):
                cmd_propose(_A())
            prop_hub = (
                td_path
                / "agent"
                / "skills"
                / "proposals"
                / "skill-prefer-hub-archival-early.md"
            )
            prop_body = (
                prop_hub.read_text(encoding="utf-8") if prop_hub.is_file() else ""
            )
            prop_ok = (
                prop_hub.is_file()
                and "F153" in prop_body
                and "hub-archival" in prop_body
                and "F149" in prop_body
            )
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from skill_auto_adopt import PROPOSAL_TOOL_BLOBS  # type: ignore

            blob_ok = "skill-prefer-hub-archival-early" in PROPOSAL_TOOL_BLOBS
            f153_ok = has_f152_sig and prop_ok and blob_ok
        except Exception:
            f153_ok = False

        fixture_pass = all(
            [
                mined.get("observed_n", 0) >= 3,
                bool(product_patterns.get("patterns")),
                bool(critic_patterns.get("patterns")),
                bool(mem_patterns.get("patterns")),
                match_ok,
                prop_product,
                prop_critic,
                privacy_ok,
                f153_ok,
            ]
        )

        # restore root env
        os.environ["TORII_ROOT"] = str(root)
        os.environ.pop("TORII_TOOL_OUTCOME_PROBES_FILE", None)
        os.environ.pop("TORII_EVOLUTION_ROOT", None)

        print(
            json.dumps(
                {
                    "feature": "F117",
                    "feature_hub_archival": "F153",
                    "fixture_pass": fixture_pass,
                    "observed_n": mined.get("observed_n"),
                    "observed_skills": mined.get("observed_skills"),
                    "product_patterns": product_patterns.get("patterns"),
                    "critic_patterns": critic_patterns.get("patterns"),
                    "mem_patterns": mem_patterns.get("patterns"),
                    "match_ok": match_ok,
                    "prop_product": prop_product,
                    "prop_critic": prop_critic,
                    "privacy_ok": privacy_ok,
                    "proposed": mined.get("proposed"),
                    "f153_ok": f153_ok,
                    "f153_has_signal": has_f152_sig,
                    "f153_prop_ok": prop_ok,
                    "f153_blob_ok": blob_ok,
                },
                indent=2,
            )
        )
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F69/F112/F117 Torii-native self-evolution")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="Package agent-loop → trajectory")
    pi.add_argument("--out-dir", required=True)
    pi.add_argument("--pr", default="")
    pi.add_argument("--repo", default="")
    pi.set_defaults(func=cmd_ingest)

    pp = sub.add_parser("propose", help="Create skill proposals from trajectories")
    pp.add_argument("--limit", type=int, default=5)
    pp.set_defaults(func=cmd_propose)

    psc = sub.add_parser(
        "propose-scorecard",
        help="F132 propose skills from product scorecard gap themes",
    )
    psc.add_argument("--scorecard", default="", help="path to product-scorecard.json")
    psc.add_argument("--limit", type=int, default=5)
    psc.add_argument("--dry-run", action="store_true")
    psc.set_defaults(func=cmd_propose_scorecard)

    pm = sub.add_parser("mine-probes", help="F117 mine allowlisted tool probes from run")
    pm.add_argument("--out-dir", required=True)
    pm.add_argument("--propose", action="store_true", help="Also write F117 skill proposals")
    pm.add_argument("--min-hits", type=int, default=1)
    pm.add_argument("--force", action="store_true")
    pm.set_defaults(func=cmd_mine_probes)

    prf = sub.add_parser(
        "refine-from-util",
        help="F165 GEPA-lite skill body refine from recovery/hub-archival util traces",
    )
    prf.add_argument("--out-dir", required=True)
    prf.add_argument(
        "--dry-run",
        action="store_true",
        help="Diagnose + mutate in memory; do not write skill files",
    )
    prf.add_argument(
        "--apply",
        action="store_true",
        help="Write refined bodies to agent/skills/active (default unless --dry-run)",
    )
    prf.add_argument(
        "--force-skills",
        default="",
        help="Comma-separated skill ids to refine even without gap",
    )
    prf.add_argument(
        "--min-gap",
        type=float,
        default=None,
        help="Chronic gap_rate threshold (default TORII_SKILL_REFINE_MIN_GAP=0.33)",
    )
    prf.set_defaults(func=cmd_refine_from_util)

    pe = sub.add_parser("eval", help="Score proposals offline")
    pe.add_argument("--proposal", default="all")
    pe.set_defaults(func=cmd_eval)

    pa = sub.add_parser("adopt", help="Move proposal → agent/skills/active")
    pa.add_argument("proposal_id")
    pa.add_argument("--force", action="store_true")
    pa.set_defaults(func=cmd_adopt)

    pj = sub.add_parser("inject", help="Inject active skills into prompt.md")
    pj.add_argument("--prompt", required=True)
    pj.add_argument("--out", default="")
    pj.set_defaults(func=cmd_inject)

    sub.add_parser("nudge-text", help="Print H10 soft nudge if warranted").set_defaults(
        func=cmd_nudge_text
    )
    pst = sub.add_parser(
        "status",
        help="Day-2 self-evolution readiness (JSON; --text for ledger dump)",
    )
    pst.add_argument(
        "--text",
        action="store_true",
        help="Human ledger dump (default: buyer JSON for torii.py soft peeks)",
    )
    pst.set_defaults(func=cmd_status)
    sub.add_parser("fixture", help="F117 hermetic mine+score fixture").set_defaults(
        func=cmd_fixture
    )
    sub.add_parser(
        "fixture-refine",
        help="F165 hermetic GEPA-lite refine-from-util fixture",
    ).set_defaults(func=cmd_fixture_refine)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
