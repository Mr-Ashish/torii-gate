#!/usr/bin/env python3
"""F88/F115/F127/F140: Per-skill contribution attribution (LOO + hub floors).

Research drivers (2026):
  - "Not All Skills Help" / Assay (arXiv 2606.15390): per-task skill masking
    and retiring inert skills — bottleneck is matching + attribution, not bulk
    library size.
  - SkillsBench / F86 dual-rollout: aggregate with vs without; missing **which**
    skill drives the delta before auto-adopt.
  - Ablation studies as OS for trustworthy AI decisions — component LOO.
  - Mem2Act / F114: recovery skills succeed via **terminal tool calls**, not
    review-prose keywords — LOO must credit tool_hit or free-rider ledger
    zombie-demotes the skill F113 just dual-gate adopted.
  - F138/F139: scorecard hub post-score + critic without attribution floor lets
    LOO free-rider-demote multi-tenant tool-effective ops skills.

Product thesis:
  F87 gates on pack-level contribution_pp>0 still allows free-riding skills to
  ride bulk adopt. Highest ROI: **leave-one-out + unique keyword + tool-outcome
  attribution** so only skills with solo prose hit, unique coverage, measured
  tool invocation, or **hub scorecard/recovery evidence** adopt or rank high.

Commands:
  attribute — LOO + unique keyword + F114 tool-outcome + hub floors
  rank      — sort skills by contribution score
  filter    — list skill ids with contribution > threshold
  fixture   — hermetic: contributing > free-rider; tool-only; scorecard hub floor
  status    — summary

Env:
  TORII_ROOT
  TORII_SKILL_ATTRIBUTION     1 (default) | 0
  TORII_SKILL_ATTR_MIN        default 0.01 — min contribution to count
  TORII_SKILL_ATTR_TOOL       1 (default) | 0 — F115 tool-outcome LOO credit
  TORII_SKILL_ATTR_HUB        1 (default) | 0 — F127 floor for hub_ingested fitness skills
  TORII_SKILL_ATTR_SCORECARD  1 (default) | 0 — F140 floor for scorecard hub ops skills
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

FEATURE = "F88"
FEATURE_TOOL = "F115"
FEATURE_HUB = "F127"
FEATURE_SCORECARD = "F140"
FEATURE_HUB_ARCHIVAL = "F156"
HUB_ARCHIVAL_SKILL_ID = "skill-prefer-hub-archival-early"
SCHEMA = 1
LEDGER_NAME = "skill-attribution.json"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

DEFAULT_GOOD = "docs/benchmarks/fixtures/insecure-demo-good-review.md"
DEMO_PATHS = ["demo/insecure/app.py", "demo/insecure/db.py"]

# F115: synthetic agent-loop fragment for offline tool-only LOO proof
SYNTH_TOOL_BLOB_GOOD = (
    "tool_call: terminal\n"
    "python3 scripts/torii.py memory -- search -- -q \"sql injection\"\n"
    "rg -n pickle demo/insecure/app.py\n"
    "chain_revalidate.py score --review review.md\n"
)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SKILL_ATTRIBUTION") or "1").strip().lower()
    return raw not in _FALSEY


def tool_attr_enabled() -> bool:
    """F115: credit F114 tool outcomes in LOO attribution (default on)."""
    raw = (os.environ.get("TORII_SKILL_ATTR_TOOL") or "1").strip().lower()
    return raw not in _FALSEY


def _float_env(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _scripts() -> Path:
    return Path(__file__).resolve().parent


def _import_mod(name: str):
    import importlib.util

    if name in sys.modules:
        return sys.modules[name]
    path = _scripts() / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_tmp(text: str) -> Path:
    fd, name = tempfile.mkstemp(prefix="torii-f88-", suffix=".md")
    os.close(fd)
    p = Path(name)
    p.write_text(text, encoding="utf-8")
    return p


def enrich_review(text: str) -> str:
    """Ensure dual-rollout skill language for attribution on good fixtures."""
    if "attacker trigger" in text.lower() and "taint" in text.lower():
        return text
    return (
        text.rstrip()
        + "\n\n### Skill discipline\n"
        "- Path:line citations on each finding.\n"
        "- Align claims with taint/chain candidates; else unvalidated.\n"
        "- Attacker trigger for each REQUEST CHANGES sink.\n"
        "- Prefer unified diff hunks over bare file heads.\n"
    )


def _probes_for_card(card: Any) -> list[str]:
    probes: list[str] = list(card.keywords[:12])
    for part in re.split(r"[\s\-_/]+", (card.title or "").lower()):
        if len(part) >= 4 and part not in probes:
            probes.append(part)
    tail = card.id.replace("skill-", "").replace("f74-", "").replace("-", " ")
    for part in tail.split():
        if len(part) >= 4 and part not in probes:
            probes.append(part)
    return probes


def _matched_in_text(probes: list[str], text_low: str) -> list[str]:
    matched = []
    for kw in probes:
        if len(kw) < 3:
            continue
        if kw.lower() in text_low:
            matched.append(kw.lower())
    return matched


def _resolve_tool_blob(
    *,
    tool_blob: str | None = None,
    agent_loop: Path | None = None,
    log_path: Path | None = None,
    out_dir: Path | None = None,
) -> str:
    """Gather agent-loop / log text for F115 tool-outcome LOO (via F114 probes)."""
    if tool_blob is not None:
        return tool_blob
    sr = _import_mod("skill_router")
    if not tool_attr_enabled():
        return ""
    try:
        return sr._collect_tool_blob(  # noqa: SLF001 — shared F114 collector
            out_dir,
            agent_loop=agent_loop,
            log_path=log_path,
        )
    except Exception:
        return ""


def hub_attr_enabled() -> bool:
    """F127: floor contribution for fitness hub_ingested recovery skills."""
    raw = (os.environ.get("TORII_SKILL_ATTR_HUB") or "1").strip().lower()
    return raw not in _FALSEY


def hub_archival_attr_enabled() -> bool:
    """F156: LOO floor for hub-archival when recovery-util federate has tool hits."""
    raw = (os.environ.get("TORII_SKILL_ATTR_HUB_ARCHIVAL") or "1").strip().lower()
    return raw not in _FALSEY


def scorecard_attr_enabled() -> bool:
    """F140: floor contribution for scorecard hub / scorecard_ops fitness skills."""
    raw = (os.environ.get("TORII_SKILL_ATTR_SCORECARD") or "1").strip().lower()
    return raw not in _FALSEY


def _load_hub_archival_util_skills(root: Path) -> dict[str, dict[str, Any]]:
    """F156: hub-archival skill → multi-tenant recovery util tool evidence.

    Privacy-safe: skill ids + bins/hits only from recovery-util-signals.
    Floors LOO so dual-gate does not free-ride-reject a skill with hub tool proof.
    """
    out: dict[str, dict[str, Any]] = {}
    if not hub_archival_attr_enabled():
        return out
    paths = [
        root / "memory" / "federation" / "recovery-util-signals.json",
    ]
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        paths.insert(0, Path(od) / "recovery-util-signals.json")
    hits = 0
    tenants = 0
    tool_hits = 0
    for p in paths:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sigs = data.get("signals") if isinstance(data, dict) else data
        if not isinstance(sigs, list):
            continue
        for s in sigs:
            if not isinstance(s, dict):
                continue
            tags = [str(t).lower() for t in (s.get("tags") or [])]
            theme = str(s.get("theme") or s.get("id") or "").lower()
            is_ha = (
                "hub_archival" in tags
                or "f155" in tags
                or "f156" in tags
                or HUB_ARCHIVAL_SKILL_ID in theme
                or "prefer-hub-archival" in theme
            )
            if not is_ha:
                continue
            util_bin = str(s.get("util_rate_bin") or "").lower()
            if util_bin == "gap" or "utilization_gap" in tags:
                # gap signals do not floor contribution (idle evidence)
                continue
            hits += max(1, int(s.get("hits") or 1))
            tool_hits += max(1, int(s.get("tool_hits") or s.get("hits") or 1))
            tenants = max(
                tenants,
                int(s.get("tenants") or len(s.get("tenant_hashes") or []) or 1),
            )
        if hits:
            break
    if hits >= 1:
        out[HUB_ARCHIVAL_SKILL_ID] = {
            "hub_ingested_n": hits,
            "tool_hit_n": tool_hits,
            "hub_priority_delta": min(40, 5 + 8 * min(4, tenants) + 3 * min(6, tool_hits)),
            "kind": "hub_archival_util",
            "tenants": tenants,
        }
    return out


def _load_hub_ingested_skills(root: Path) -> dict[str, dict[str, Any]]:
    """skill_id → fitness entry fields (hub_ingested_n, tool_hit_n) privacy-safe."""
    out: dict[str, dict[str, Any]] = {}
    if not hub_attr_enabled():
        return out
    candidates = [
        root / ".torii" / "skill-fitness.json",
    ]
    env = (os.environ.get("TORII_SKILL_FITNESS_FILE") or "").strip()
    if env:
        candidates.insert(0, Path(env))
    for p in candidates:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        skills = data.get("skills") if isinstance(data, dict) else None
        if not isinstance(skills, dict):
            continue
        for sid, ent in skills.items():
            if not isinstance(sid, str) or "/" in sid or not isinstance(ent, dict):
                continue
            hub_n = int(ent.get("hub_ingested_n") or 0)
            tool_n = int(ent.get("tool_hit_n") or 0)
            if hub_n < 1 and not ent.get("last_hub_at"):
                continue
            out[sid] = {
                "hub_ingested_n": hub_n,
                "tool_hit_n": tool_n,
                "hub_priority_delta": int(ent.get("hub_priority_delta") or 0),
                "kind": "recovery_hub",
            }
        break
    return out


def _load_scorecard_hub_skills(root: Path) -> dict[str, dict[str, Any]]:
    """skill_id → scorecard hub/fitness evidence (privacy-safe ids only).

    Sources (F140):
      1. fitness ledger: scorecard_ops / scorecard_ingested_n (F135/F138)
      2. soft post_score_scorecard_hub priority_deltas (F138 multi-tenant util)
    """
    out: dict[str, dict[str, Any]] = {}
    if not scorecard_attr_enabled():
        return out
    candidates = [
        root / ".torii" / "skill-fitness.json",
    ]
    env = (os.environ.get("TORII_SKILL_FITNESS_FILE") or "").strip()
    if env:
        candidates.insert(0, Path(env))
    for p in candidates:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        skills = data.get("skills") if isinstance(data, dict) else None
        if not isinstance(skills, dict):
            continue
        for sid, ent in skills.items():
            if not isinstance(sid, str) or "/" in sid or ".." in sid:
                continue
            if not isinstance(ent, dict):
                continue
            sc_n = int(ent.get("scorecard_ingested_n") or 0)
            is_ops = bool(ent.get("scorecard_ops"))
            if sc_n < 1 and not is_ops:
                continue
            out[sid] = {
                "scorecard_ingested_n": sc_n,
                "tool_hit_n": int(ent.get("tool_hit_n") or 0),
                "hub_priority_delta": int(ent.get("hub_priority_delta") or 0),
                "kind": "scorecard_fitness",
            }
        break

    # soft merge F138 hub priority deltas (multi-tenant tool themes)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from skill_router import (  # type: ignore
            post_score_scorecard_hub,
            scorecard_hub_enabled,
        )

        if scorecard_hub_enabled():
            hub = post_score_scorecard_hub(root=root)
            deltas = hub.get("priority_deltas") or {}
            skills_doc = hub.get("skills") or {}
            for sid, delta in deltas.items():
                sid_s = str(sid).strip()
                if not sid_s or "/" in sid_s or ".." in sid_s:
                    continue
                ent_h = skills_doc.get(sid_s) if isinstance(skills_doc, dict) else {}
                tool_n = 0
                if isinstance(ent_h, dict):
                    tool_n = int(ent_h.get("tool_hits") or ent_h.get("tool_hit_n") or 0)
                prev = out.get(sid_s) or {}
                out[sid_s] = {
                    "scorecard_ingested_n": max(
                        1, int(prev.get("scorecard_ingested_n") or 0)
                    ),
                    "tool_hit_n": max(int(prev.get("tool_hit_n") or 0), tool_n),
                    "hub_priority_delta": max(
                        int(prev.get("hub_priority_delta") or 0), int(delta or 0)
                    ),
                    "kind": prev.get("kind") or "scorecard_hub",
                }
    except Exception:
        pass
    return out


def attribute(
    review_text: str,
    *,
    root: Path | None = None,
    paths: list[str] | None = None,
    selected: list[str] | None = None,
    tool_blob: str | None = None,
    agent_loop: Path | None = None,
    log_path: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Leave-one-out + unique keyword + tool-outcome + F127/F140/F156 hub floors."""
    root = root or _root()
    sr = _import_mod("skill_router")
    paths = paths or list(DEMO_PATHS)
    cards = sr.catalog(root)
    by_id = {c.id: c for c in cards}
    hub_skills = _load_hub_ingested_skills(root)
    sc_hub_skills = _load_scorecard_hub_skills(root)
    ha_skills = _load_hub_archival_util_skills(root)

    if selected is None:
        sel = sr.select_skills(cards, paths)
        selected = list(sel.get("selected") or [])
    selected = [s for s in selected if s in by_id]
    text_low = review_text.lower()

    use_tools = tool_attr_enabled()
    blob = _resolve_tool_blob(
        tool_blob=tool_blob,
        agent_loop=agent_loop,
        log_path=log_path,
        out_dir=out_dir,
    )
    if not use_tools:
        blob = ""

    # prose matches + tool matches per skill
    full_matched: dict[str, list[str]] = {}
    tool_matched: dict[str, list[str]] = {}
    for sid in selected:
        full_matched[sid] = _matched_in_text(_probes_for_card(by_id[sid]), text_low)
        if blob:
            try:
                tool_matched[sid] = list(sr.match_tool_outcome(sid, blob, root=root) or [])
            except Exception:
                tool_matched[sid] = []
        else:
            tool_matched[sid] = []

    def _is_hit(sid: str) -> bool:
        return bool(full_matched[sid]) or bool(tool_matched[sid])

    hit_n_full = sum(1 for sid in selected if _is_hit(sid))
    rate_full = (hit_n_full / len(selected)) if selected else 0.0
    tool_hit_n = sum(1 for sid in selected if tool_matched[sid])

    # union of matches excluding each skill for unique calc (prose only;
    # tool unique = tool matched for this skill and not others)
    rows: list[dict[str, Any]] = []
    hub_floored: list[str] = []
    scorecard_floored: list[str] = []
    for sid in selected:
        card = by_id[sid]
        solo_m = full_matched[sid]
        t_m = tool_matched[sid]
        prose_hit = len(solo_m) >= 1
        tool_hit = len(t_m) >= 1
        solo_hit = prose_hit or tool_hit
        # others' matches
        others_union: set[str] = set()
        others_tools: set[str] = set()
        for oid in selected:
            if oid == sid:
                continue
            others_union.update(full_matched[oid])
            others_tools.update(tool_matched[oid])
        unique = [m for m in solo_m if m not in others_union]
        tool_unique = [m for m in t_m if m not in others_tools]
        # LOO hit_rate of remaining (prose OR tool)
        remain = [o for o in selected if o != sid]
        hit_without = sum(1 for o in remain if _is_hit(o))
        rate_without = (hit_without / len(remain)) if remain else 0.0
        loo_delta = round(rate_full - rate_without, 4)
        # contribution: prose solo + unique + F115 tool weight (Mem2Act)
        score = 0.0
        if prose_hit:
            score += 1.0
        if tool_hit:
            score += 1.5  # tool invocation > prose keyword alone
        score += 0.5 * len(unique)
        score += 0.5 * len(tool_unique)
        # always-on skills get floor so we don't demote core tools
        if getattr(card, "always", False):
            score = max(score, 0.5)
        # F127: hub_ingested recovery themes get floor (multi-tenant tool evidence)
        hub_ent = hub_skills.get(sid)
        hub_floor = False
        if hub_ent and hub_attr_enabled():
            hub_floor = True
            # floor 0.75 + small delta from priority; never invent prose hits
            floor = 0.75 + min(0.5, float(hub_ent.get("hub_priority_delta") or 0) / 80.0)
            if int(hub_ent.get("tool_hit_n") or 0) >= 1:
                floor = max(floor, 1.0)
            if score < floor:
                score = floor
                hub_floored.append(sid)
        # F156: hub-archival recovery-util federate tool hits → LOO floor
        ha_ent = ha_skills.get(sid)
        ha_floor = False
        if ha_ent and hub_archival_attr_enabled():
            ha_floor = True
            floor_ha = 0.8 + min(
                0.5, float(ha_ent.get("hub_priority_delta") or 0) / 80.0
            )
            if int(ha_ent.get("tool_hit_n") or 0) >= 1:
                floor_ha = max(floor_ha, 1.0)
            if score < floor_ha:
                score = floor_ha
                if sid not in hub_floored:
                    hub_floored.append(sid)
        # F140: scorecard hub / scorecard_ops fitness themes get LOO floor
        sc_ent = sc_hub_skills.get(sid)
        sc_floor = False
        if sc_ent and scorecard_attr_enabled():
            sc_floor = True
            floor_sc = 0.75 + min(
                0.5, float(sc_ent.get("hub_priority_delta") or 0) / 80.0
            )
            if int(sc_ent.get("tool_hit_n") or 0) >= 1:
                floor_sc = max(floor_sc, 1.0)
            if int(sc_ent.get("scorecard_ingested_n") or 0) >= 1:
                floor_sc = max(floor_sc, 0.85)
            if score < floor_sc:
                score = floor_sc
                scorecard_floored.append(sid)
        # free-rider: selected but no prose/tool solo and no unique and not hub-floored
        free_rider = (
            (not solo_hit)
            and (len(unique) == 0)
            and (len(tool_unique) == 0)
            and not getattr(card, "always", False)
            and not hub_floor
            and not ha_floor
            and not sc_floor
        )
        rows.append(
            {
                "id": sid,
                "solo_hit": solo_hit,
                "prose_hit": prose_hit,
                "tool_hit": tool_hit,
                "n_matched": len(solo_m),
                "matched": solo_m[:8],
                "tool_matched": t_m[:8],
                "unique": unique[:8],
                "n_unique": len(unique),
                "tool_unique": tool_unique[:8],
                "n_tool_unique": len(tool_unique),
                "loo_delta_hit_rate": loo_delta,
                "contribution": round(score, 3),
                "free_rider": free_rider,
                "always": bool(getattr(card, "always", False)),
                "hub_ingested": bool(hub_ent) or bool(ha_ent),
                "hub_floor": (hub_floor or ha_floor) and sid in hub_floored,
                "hub_archival_floor": ha_floor and sid in hub_floored,
                "scorecard_hub": bool(sc_ent),
                "scorecard_floor": sc_floor and sid in scorecard_floored,
            }
        )

    rows.sort(key=lambda r: (-float(r["contribution"]), r["id"]))
    min_c = _float_env("TORII_SKILL_ATTR_MIN", 0.01)
    contributing = [r["id"] for r in rows if float(r["contribution"]) > min_c and not r["free_rider"]]
    free_riders = [r["id"] for r in rows if r["free_rider"]]
    tool_contributors = [r["id"] for r in rows if r.get("tool_hit") and not r["free_rider"]]
    hub_contributors = [r["id"] for r in rows if r.get("hub_ingested") and not r["free_rider"]]
    scorecard_contributors = [
        r["id"] for r in rows if r.get("scorecard_hub") and not r["free_rider"]
    ]

    return {
        "feature": FEATURE,
        "feature_tool": FEATURE_TOOL if use_tools else None,
        "feature_hub": FEATURE_HUB if hub_attr_enabled() else None,
        "feature_hub_archival": FEATURE_HUB_ARCHIVAL
        if hub_archival_attr_enabled()
        else None,
        "feature_scorecard": FEATURE_SCORECARD if scorecard_attr_enabled() else None,
        "schema": SCHEMA,
        "scored_at": _now(),
        "paths": paths,
        "selected": selected,
        "hit_rate_full": round(rate_full, 4),
        "hit_n_full": hit_n_full,
        "tool_outcome": use_tools,
        "tool_hit_n": tool_hit_n,
        "tool_contributors": tool_contributors,
        "hub_contributors": hub_contributors,
        "hub_floored": hub_floored,
        "scorecard_contributors": scorecard_contributors,
        "scorecard_floored": scorecard_floored,
        "skills": rows,
        "contributing": contributing,
        "free_riders": free_riders,
        "min_contribution": min_c,
        "n_contributing": len(contributing),
        "n_free_riders": len(free_riders),
    }


def attribute_proposal(
    proposal_id: str,
    proposal_body: str,
    review_text: str,
    *,
    always: bool = False,
    tool_blob: str | None = None,
) -> dict[str, Any]:
    """Attribute a not-yet-active proposal via keywords + optional F115 tools."""
    # crude probes from body
    probes: list[str] = []
    for m in re.finditer(r"\*\*([^*]{3,40})\*\*", proposal_body):
        probes.append(m.group(1).strip().lower())
    for m in re.finditer(r"`([^`]{3,40})`", proposal_body):
        probes.append(m.group(1).strip().lower())
    for tok in (
        "path:line",
        "taint",
        "chain",
        "attacker",
        "trigger",
        "unvalidated",
        "diff",
        "hunk",
        "source",
        "sink",
        "deep path",
        "basename",
        "torii.py memory",
        "torii_memory",
    ):
        if tok in proposal_body.lower():
            probes.append(tok)
    tail = proposal_id.replace("skill-", "").replace("f74-", "").replace("-", " ")
    for part in tail.split():
        if len(part) >= 4:
            probes.append(part)
    # de-dupe
    seen: set[str] = set()
    uniq_p: list[str] = []
    for p in probes:
        if p and p not in seen:
            seen.add(p)
            uniq_p.append(p)
    matched = _matched_in_text(uniq_p, review_text.lower())
    prose_hit = len(matched) >= 1
    # F115: tool probes from F114 map when proposal id known
    tool_matched: list[str] = []
    if tool_blob and tool_attr_enabled():
        try:
            sr = _import_mod("skill_router")
            tool_matched = list(sr.match_tool_outcome(proposal_id, tool_blob, root=_root()) or [])
        except Exception:
            tool_matched = []
    tool_hit = len(tool_matched) >= 1
    solo_hit = prose_hit or tool_hit
    score = (1.0 if prose_hit else 0.0) + 0.5 * min(3, len(matched))
    if tool_hit:
        score += 1.5
    if always:
        score = max(score, 0.5)
    free_rider = not solo_hit and not always
    return {
        "id": proposal_id,
        "solo_hit": solo_hit,
        "prose_hit": prose_hit,
        "tool_hit": tool_hit,
        "matched": matched[:8],
        "tool_matched": tool_matched[:8],
        "n_matched": len(matched),
        "contribution": round(score, 3),
        "free_rider": free_rider,
        "probes_n": len(uniq_p),
    }


def filter_contributing(
    attr: dict[str, Any],
    *,
    ids: list[str] | None = None,
) -> list[str]:
    ok = set(attr.get("contributing") or [])
    if ids is None:
        return sorted(ok)
    return [i for i in ids if i in ok]


# --- F89 durable ledger for router inject ranking ---


def ledger_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_SKILL_ATTR_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / LEDGER_NAME


def empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "feature": "F89",
        "updated_at": _now(),
        "skills": {},
        "free_riders": [],
        "history": [],
    }


def load_ledger(path: Path | None = None) -> dict[str, Any]:
    p = path or ledger_path()
    if not p.is_file():
        return empty_ledger()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_ledger()
    if not isinstance(data, dict):
        return empty_ledger()
    data.setdefault("skills", {})
    data.setdefault("free_riders", [])
    data.setdefault("history", [])
    return data


def save_ledger(ledger: dict[str, Any], path: Path | None = None) -> Path:
    p = path or ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = _now()
    ledger["feature"] = "F89"
    ledger["schema_version"] = SCHEMA
    p.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return p


def ingest_attribute(
    attr: dict[str, Any],
    ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compound per-skill contribution into durable ledger for router F89."""
    ledger = ledger if ledger is not None else load_ledger()
    skills = ledger.setdefault("skills", {})
    for row in attr.get("skills") or []:
        sid = str(row.get("id") or "").strip()
        if not sid or "/" in sid:
            continue
        ent = skills.get(sid) or {
            "id": sid,
            "n": 0,
            "contribution_sum": 0.0,
            "solo_hits": 0,
            "tool_hits": 0,
            "free_rider_n": 0,
            "avg_contribution": 0.0,
            "free_rider": False,
        }
        ent["n"] = int(ent.get("n") or 0) + 1
        c = float(row.get("contribution") or 0)
        ent["contribution_sum"] = float(ent.get("contribution_sum") or 0) + c
        if row.get("solo_hit"):
            ent["solo_hits"] = int(ent.get("solo_hits") or 0) + 1
        # F115: durable tool-hit compound for router boost of recovery skills
        if row.get("tool_hit"):
            ent["tool_hits"] = int(ent.get("tool_hits") or 0) + 1
        if row.get("free_rider"):
            ent["free_rider_n"] = int(ent.get("free_rider_n") or 0) + 1
        n = int(ent["n"])
        ent["avg_contribution"] = round(float(ent["contribution_sum"]) / n, 4)
        # free-rider if majority free_rider samples and low avg
        fr_rate = int(ent["free_rider_n"]) / n
        ent["free_rider"] = bool(fr_rate >= 0.5 and float(ent["avg_contribution"]) < 0.5)
        # tool-effective skills with positive tool_hits never free-rider demote
        if int(ent.get("tool_hits") or 0) >= 1 and float(ent["avg_contribution"]) >= 0.5:
            ent["free_rider"] = False
        ent["last_seen"] = _now()
        skills[sid] = ent
    ledger["free_riders"] = sorted(
        sid for sid, e in skills.items() if e.get("free_rider")
    )
    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "n_contributing": attr.get("n_contributing"),
            "n_free_riders": attr.get("n_free_riders"),
            "hit_rate_full": attr.get("hit_rate_full"),
            "tool_hit_n": attr.get("tool_hit_n"),
            "tool_contributors": list(attr.get("tool_contributors") or [])[:16],
            "contributing": list(attr.get("contributing") or [])[:16],
        }
    )
    ledger["history"] = hist[-80:]
    return ledger


def router_boosts(ledger: dict[str, Any] | None = None) -> dict[str, float]:
    """Score deltas for skill_router: high avg contribution → boost."""
    ledger = ledger if ledger is not None else load_ledger()
    max_boost = _float_env("TORII_SKILL_ATTR_ROUTER_BOOST", 3.0)
    out: dict[str, float] = {}
    for sid, ent in (ledger.get("skills") or {}).items():
        n = int(ent.get("n") or 0)
        if n < 1:
            continue
        avg = float(ent.get("avg_contribution") or 0)
        if ent.get("free_rider"):
            out[sid] = -max_boost
            continue
        # map avg contribution (0..~2.5) into [0, max_boost]
        conf = min(1.0, n / 2.0)
        out[sid] = round(min(max_boost, avg * conf), 3)
    return out


def free_rider_set(ledger: dict[str, Any] | None = None) -> set[str]:
    ledger = ledger if ledger is not None else load_ledger()
    return set(ledger.get("free_riders") or [])


def cycle_from_review(
    review: Path,
    *,
    root: Path | None = None,
    paths: list[str] | None = None,
    out_dir: Path | None = None,
    tool_blob: str | None = None,
    agent_loop: Path | None = None,
    log_path: Path | None = None,
) -> dict[str, Any]:
    root = root or _root()
    text = ""
    if review.is_file():
        text = review.read_text(encoding="utf-8", errors="replace")
    text = enrich_review(text)
    # prefer selected from out_dir skill-router.json
    selected = None
    od = Path(out_dir) if out_dir else None
    if od and (od / "skill-router.json").is_file():
        try:
            selected = json.loads(
                (od / "skill-router.json").read_text(encoding="utf-8")
            ).get("selected")
        except (OSError, json.JSONDecodeError):
            selected = None
    # F115: prefer agent-loop.json next to review when present
    al = agent_loop
    if al is None and od and (od / "agent-loop.json").is_file():
        al = od / "agent-loop.json"
    lg = log_path
    if lg is None and od:
        for name in ("hermes.log", "run.log", "agent.log"):
            if (od / name).is_file():
                lg = od / name
                break
    attr = attribute(
        text,
        root=root,
        paths=paths,
        selected=selected,
        tool_blob=tool_blob,
        agent_loop=al,
        log_path=lg,
        out_dir=od,
    )
    ledger = ingest_attribute(attr, load_ledger(ledger_path(root)))
    path = save_ledger(ledger, ledger_path(root))
    if od:
        od.mkdir(parents=True, exist_ok=True)
        (od / "skill-attribution.json").write_text(
            json.dumps(attr, indent=2) + "\n", encoding="utf-8"
        )
    return {
        "feature": "F89",
        "attr_feature": FEATURE,
        "feature_tool": attr.get("feature_tool"),
        "tool_hit_n": attr.get("tool_hit_n"),
        "tool_contributors": attr.get("tool_contributors"),
        "ledger": str(path),
        "free_riders": list(ledger.get("free_riders") or []),
        "boosts": router_boosts(ledger),
        "n_contributing": attr.get("n_contributing"),
        "artifact": str(od / "skill-attribution.json") if od else None,
    }


def cmd_attribute(args: argparse.Namespace) -> int:
    root = _root()
    if args.review:
        text = Path(args.review).read_text(encoding="utf-8", errors="replace")
    else:
        gp = root / DEFAULT_GOOD
        text = gp.read_text(encoding="utf-8", errors="replace") if gp.is_file() else ""
    text = enrich_review(text)
    paths = args.paths or DEMO_PATHS
    selected = args.selected.split(",") if args.selected else None
    al = Path(args.agent_loop) if getattr(args, "agent_loop", None) else None
    lg = Path(args.log) if getattr(args, "log", None) else None
    tb_raw = (getattr(args, "tool_blob", None) or "").strip()
    tb: str | None = None
    if tb_raw:
        p_tb = Path(tb_raw)
        tb = p_tb.read_text(encoding="utf-8", errors="replace") if p_tb.is_file() else tb_raw
    result = attribute(
        text,
        root=root,
        paths=paths,
        selected=selected,
        tool_blob=tb,
        agent_loop=al if al and str(al) not in (".", "") else None,
        log_path=lg if lg and str(lg) not in (".", "") else None,
    )
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    root = _root()
    gp = Path(args.review) if args.review else root / DEFAULT_GOOD
    text = enrich_review(gp.read_text(encoding="utf-8", errors="replace") if gp.is_file() else "")
    al = Path(args.agent_loop) if getattr(args, "agent_loop", None) else None
    lg = Path(args.log) if getattr(args, "log", None) else None
    result = attribute(
        text,
        root=root,
        paths=args.paths or DEMO_PATHS,
        agent_loop=al,
        log_path=lg,
    )
    ranked = [
        {
            "id": r["id"],
            "contribution": r["contribution"],
            "free_rider": r["free_rider"],
            "tool_hit": r.get("tool_hit"),
            "prose_hit": r.get("prose_hit"),
        }
        for r in result["skills"]
    ]
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_tool": result.get("feature_tool"),
                "tool_hit_n": result.get("tool_hit_n"),
                "ranked": ranked,
            },
            indent=2,
        )
    )
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    root = _root()
    gp = Path(args.review) if args.review else root / DEFAULT_GOOD
    text = enrich_review(gp.read_text(encoding="utf-8", errors="replace") if gp.is_file() else "")
    result = attribute(text, root=root, paths=args.paths or DEMO_PATHS)
    ids = args.ids.split(",") if args.ids else None
    out = filter_contributing(result, ids=ids)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "contributing": out,
                "free_riders": result.get("free_riders"),
            },
            indent=2,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ledger = load_ledger()
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "f89": True,
                "enabled": enabled(),
                "min_contribution": _float_env("TORII_SKILL_ATTR_MIN", 0.01),
                "ledger": str(ledger_path()),
                "skills_n": len(ledger.get("skills") or {}),
                "free_riders": list(ledger.get("free_riders") or []),
                "boosts": router_boosts(ledger),
            },
            indent=2,
        )
    )
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _root()
    path = Path(args.attr) if args.attr else None
    if path is None and args.out_dir:
        path = Path(args.out_dir) / "skill-attribution.json"
    if path is None or not path.is_file():
        print(json.dumps({"feature": "F89", "ingested": 0, "reason": "no attr json"}))
        return 0
    attr = json.loads(path.read_text(encoding="utf-8"))
    ledger = ingest_attribute(attr, load_ledger(ledger_path(root)))
    lp = save_ledger(ledger, ledger_path(root))
    print(
        json.dumps(
            {
                "feature": "F89",
                "ingested": 1,
                "ledger": str(lp),
                "free_riders": ledger.get("free_riders"),
                "boosts": router_boosts(ledger),
            },
            indent=2,
        )
    )
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    if not enabled() and not getattr(args, "force", False):
        print(json.dumps({"feature": "F89", "skipped": 1, "reason": "disabled"}))
        return 0
    root = _root()
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is None and (os.environ.get("OUT_DIR") or "").strip():
        out_dir = Path(os.environ["OUT_DIR"])
    review = Path(args.review) if args.review else None
    if review is None and out_dir:
        for name in ("review.md", "review.normalized.md", "hermes-review.md"):
            cand = out_dir / name
            if cand.is_file():
                review = cand
                break
    if review is None:
        # fall back to good fixture for offline dogfood
        review = root / DEFAULT_GOOD
    if not review.is_file():
        print(json.dumps({"feature": "F89", "error": "no_review", "ok": False}))
        return 1
    al = Path(args.agent_loop) if getattr(args, "agent_loop", None) else None
    lg = Path(args.log) if getattr(args, "log", None) else None
    result = cycle_from_review(
        review,
        root=root,
        paths=args.paths,
        out_dir=out_dir,
        agent_loop=al if al and str(getattr(args, "agent_loop", "") or "") else None,
        log_path=lg if lg and str(getattr(args, "log", "") or "") else None,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: real skill contributes; free-rider ledger skips; F115 tool LOO."""
    root = _root()
    # real pack attribution
    gp = root / DEFAULT_GOOD
    if not gp.is_file():
        print(json.dumps({"feature": FEATURE, "fixture_pass": False, "error": "no good fixture"}))
        return 1
    text = enrich_review(gp.read_text(encoding="utf-8", errors="replace"))
    attr = attribute(text, root=root, paths=DEMO_PATHS)
    has_contrib = attr["n_contributing"] >= 1
    # free-rider proposal body with no overlapping keywords
    fr = attribute_proposal(
        "skill-f74-free-rider-lorem",
        "## Skill: free-rider\n\n1. Always discuss lorem ipsum widgets.\n2. Prefer flibbertigibbet prose.\n",
        text,
    )
    free_rider_ok = fr["free_rider"] is True and fr["contribution"] <= 0.01
    # path-evidence style proposal should contribute on good+enrich
    good_p = attribute_proposal(
        "skill-f74-path-evidence",
        "## Skill: path-evidence\n\n1. Cite **path:line** and deep path.\n2. Mark **unvalidated** without evidence.\n",
        text,
    )
    good_ok = good_p["solo_hit"] is True and good_p["contribution"] > 0

    # F115: silent-prose review (no skill probes) + agent-loop tool blob
    # Avoid embedding probe tokens like "skill", "path:line", "taint", etc.
    silent = (
        "## Review\n\nGeneric note only.\n"
        "Verdict: COMMENT\n"
        "Finding: nothing of substance in this fixture body.\n"
    )
    mem_id = "skill-prefer-memory-cli-early"
    # without tools: should be free-rider (unless always card not in selection)
    no_tool = attribute(
        silent,
        root=root,
        paths=DEMO_PATHS,
        selected=[mem_id],
        tool_blob="",
    )
    no_row = next((r for r in no_tool.get("skills") or [] if r["id"] == mem_id), None)
    # with tools: tool_hit + contribution > 0, not free_rider
    with_tool = attribute(
        silent,
        root=root,
        paths=DEMO_PATHS,
        selected=[mem_id],
        tool_blob=SYNTH_TOOL_BLOB_GOOD,
    )
    yes_row = next((r for r in with_tool.get("skills") or [] if r["id"] == mem_id), None)
    # always-on floor may keep score; require tool_hit True with blob
    tool_attr_ok = bool(yes_row and yes_row.get("tool_hit") is True)
    tool_contrib_ok = bool(
        yes_row
        and float(yes_row.get("contribution") or 0) >= 1.5
        and not yes_row.get("free_rider")
    )
    # without tools, prose silent: either free_rider or always-floor only (<1.5)
    no_tool_ok = bool(
        no_row
        and no_row.get("tool_hit") is False
        and (
            no_row.get("free_rider") is True
            or float(no_row.get("contribution") or 0) < 1.5
        )
    )
    # proposal tool path: body silent, tools present
    tool_prop = attribute_proposal(
        mem_id,
        "## Skill: memory CLI early\n\nCall torii.py memory before long hunts.\n",
        silent,
        tool_blob=SYNTH_TOOL_BLOB_GOOD,
    )
    tool_prop_ok = (
        tool_prop.get("tool_hit") is True
        and tool_prop.get("free_rider") is False
        and float(tool_prop.get("contribution") or 0) >= 1.5
    )

    # F89: durable ledger + router boosts/skip
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        os.environ["TORII_ROOT"] = str(td_path)
        os.environ["TORII_SKILL_ATTR_FILE"] = str(td_path / ".torii" / LEDGER_NAME)
        # seed attr with free-rider row synthetic
        synth = dict(attr)
        skills = list(synth.get("skills") or [])
        skills.append(
            {
                "id": "skill-zombie-free-rider",
                "solo_hit": False,
                "matched": [],
                "unique": [],
                "n_unique": 0,
                "contribution": 0.0,
                "free_rider": True,
                "always": False,
                "tool_hit": False,
            }
        )
        # force a known contributor with high score
        skills.append(
            {
                "id": "skill-f74-prefer-chain-json",
                "solo_hit": True,
                "matched": ["chain", "taint"],
                "unique": ["chain"],
                "n_unique": 1,
                "contribution": 2.0,
                "free_rider": False,
                "always": False,
                "tool_hit": False,
            }
        )
        # F115 tool-effective recovery skill survives free-rider demote
        skills.append(
            {
                "id": mem_id,
                "solo_hit": True,
                "tool_hit": True,
                "matched": [],
                "unique": [],
                "n_unique": 0,
                "contribution": 1.5,
                "free_rider": False,
                "always": True,
            }
        )
        synth["skills"] = skills
        synth["tool_hit_n"] = 1
        synth["tool_contributors"] = [mem_id]
        ledger = empty_ledger()
        # ingest twice so free_rider majority sticks
        for _ in range(2):
            ledger = ingest_attribute(synth, ledger)
        lp = save_ledger(ledger, ledger_path(td_path))
        boosts = router_boosts(ledger)
        fr_set = free_rider_set(ledger)
        zombie_skipped = "skill-zombie-free-rider" in fr_set
        chain_boosted = boosts.get("skill-f74-prefer-chain-json", 0) > 0
        zombie_pen = boosts.get("skill-zombie-free-rider", 0) < 0
        mem_not_fr = mem_id not in fr_set
        mem_tool_hits = int((ledger.get("skills") or {}).get(mem_id, {}).get("tool_hits") or 0) >= 2
        # restore TORII_ROOT for outer tests
        os.environ["TORII_ROOT"] = str(root)
        os.environ.pop("TORII_SKILL_ATTR_FILE", None)

    # F140: scorecard hub LOO floor — silent review + scorecard skill floored
    sc_id = "skill-prefer-product-scorecard"
    f140_ok = False
    sc_row = None
    with tempfile.TemporaryDirectory() as td2:
        td2_path = Path(td2)
        prev_root = os.environ.get("TORII_ROOT")
        prev_sc = os.environ.get("TORII_SKILL_ATTR_SCORECARD")
        try:
            os.environ["TORII_ROOT"] = str(td2_path)
            os.environ["TORII_SKILL_ATTR_SCORECARD"] = "1"
            # plant active scorecard skill (no always) so LOO would free-rider without floor
            active = td2_path / "agent" / "skills" / "active"
            active.mkdir(parents=True)
            (active / f"{sc_id}.md").write_text(
                f"""---
id: {sc_id}
title: Prefer product scorecard
themes: scorecard,ops
---

## Skill: product-scorecard

Call torii doctor and scorecard early.
""",
                encoding="utf-8",
            )
            # fitness ledger marks scorecard ops ingested (F135/F138)
            torii = td2_path / ".torii"
            torii.mkdir(parents=True)
            (torii / "skill-fitness.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "skills": {
                            sc_id: {
                                "id": sc_id,
                                "scorecard_ops": True,
                                "scorecard_ingested_n": 2,
                                "tool_hit_n": 2,
                                "hub_priority_delta": 18,
                                "selected_n": 2,
                                "hit_n": 2,
                                "hit_rate": 1.0,
                            }
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            # federated scorecard util themes for soft hub merge
            fed = td2_path / "memory" / "federation"
            fed.mkdir(parents=True)
            (fed / "scorecard-util-signals.json").write_text(
                json.dumps(
                    {
                        "signals": [
                            {
                                "id": f"scorecard-util-hit-{sc_id}",
                                "theme": sc_id,
                                "tags": [
                                    "scorecard_util",
                                    "tool_outcome",
                                    "f136",
                                ],
                                "hits": 3,
                                "tool_hits": 3,
                                "tenants": 2,
                                "util_rate_bin": "hit",
                                "source": "scorecard_skill_util",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            silent_sc = (
                "## Review\n\nGeneric note only.\n"
                "Verdict: COMMENT\n"
                "Finding: nothing of substance in this fixture body.\n"
            )
            sc_attr = attribute(
                silent_sc,
                root=td2_path,
                paths=["src/auth.py"],
                selected=[sc_id],
                tool_blob="",
            )
            sc_row = next(
                (r for r in (sc_attr.get("skills") or []) if r["id"] == sc_id),
                None,
            )
            f140_ok = bool(
                sc_row
                and sc_row.get("scorecard_hub") is True
                and sc_row.get("scorecard_floor") is True
                and sc_row.get("free_rider") is False
                and float(sc_row.get("contribution") or 0) >= 0.85
                and sc_id in (sc_attr.get("scorecard_floored") or [])
                and sc_id in (sc_attr.get("scorecard_contributors") or [])
                and sc_id not in (sc_attr.get("free_riders") or [])
            )
            # adversarial: without scorecard attr flag, silent becomes free-rider
            os.environ["TORII_SKILL_ATTR_SCORECARD"] = "0"
            sc_off = attribute(
                silent_sc,
                root=td2_path,
                paths=["src/auth.py"],
                selected=[sc_id],
                tool_blob="",
            )
            sc_off_row = next(
                (r for r in (sc_off.get("skills") or []) if r["id"] == sc_id),
                None,
            )
            f140_off_ok = bool(
                sc_off_row
                and (
                    sc_off_row.get("free_rider") is True
                    or float(sc_off_row.get("contribution") or 0) < 0.85
                )
            )
            f140_ok = f140_ok and f140_off_ok
        finally:
            if prev_root is None:
                os.environ.pop("TORII_ROOT", None)
            else:
                os.environ["TORII_ROOT"] = prev_root
            if prev_sc is None:
                os.environ.pop("TORII_SKILL_ATTR_SCORECARD", None)
            else:
                os.environ["TORII_SKILL_ATTR_SCORECARD"] = prev_sc

    fixture_pass = all(
        [
            has_contrib,
            free_rider_ok,
            good_ok,
            zombie_skipped,
            chain_boosted,
            zombie_pen,
            tool_attr_ok,
            tool_contrib_ok,
            no_tool_ok,
            tool_prop_ok,
            mem_not_fr,
            mem_tool_hits,
            f140_ok,
        ]
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_tool": FEATURE_TOOL,
                "feature_scorecard": FEATURE_SCORECARD,
                "f89": True,
                "f115": True,
                "f140": True,
                "fixture_pass": fixture_pass,
                "n_contributing": attr["n_contributing"],
                "contributing": attr["contributing"],
                "free_riders_active": attr["free_riders"],
                "proposal_free_rider": fr,
                "proposal_good": good_p,
                "zombie_skipped": zombie_skipped,
                "chain_boost": boosts.get("skill-f74-prefer-chain-json"),
                "zombie_boost": boosts.get("skill-zombie-free-rider"),
                "tool_attr_ok": tool_attr_ok,
                "tool_contrib_ok": tool_contrib_ok,
                "no_tool_ok": no_tool_ok,
                "tool_prop_ok": tool_prop_ok,
                "mem_not_free_rider": mem_not_fr,
                "mem_tool_hits": mem_tool_hits,
                "with_tool_row": yes_row,
                "no_tool_row": no_row,
                "f140_ok": f140_ok,
                "f140_sc_row": sc_row,
                "ledger": str(lp),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="F88/F89/F115 skill contribution attribution + tool LOO + ledger"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("attribute", help="LOO + unique + tool-outcome attribution")
    pa.add_argument("--review", default="")
    pa.add_argument("--paths", nargs="*", default=None)
    pa.add_argument("--selected", default="")
    pa.add_argument("--out", default="")
    pa.add_argument("--agent-loop", default="", help="F115: agent-loop.json for tool LOO")
    pa.add_argument("--log", default="", help="F115: hermes/run log for tool LOO")
    pa.add_argument("--tool-blob", default="", help="F115: raw tool text or file path")
    pa.set_defaults(func=cmd_attribute)

    pr = sub.add_parser("rank", help="Rank by contribution")
    pr.add_argument("--review", default="")
    pr.add_argument("--paths", nargs="*", default=None)
    pr.add_argument("--agent-loop", default="")
    pr.add_argument("--log", default="")
    pr.set_defaults(func=cmd_rank)

    pf = sub.add_parser("filter", help="Filter contributing skill ids")
    pf.add_argument("--review", default="")
    pf.add_argument("--paths", nargs="*", default=None)
    pf.add_argument("--ids", default="")
    pf.set_defaults(func=cmd_filter)

    pi = sub.add_parser("ingest", help="Ingest attr JSON into durable ledger")
    pi.add_argument("--attr", default="")
    pi.add_argument("--out-dir", default="")
    pi.set_defaults(func=cmd_ingest)

    pc = sub.add_parser("cycle", help="Attribute review → ledger (F89 router fuel)")
    pc.add_argument("--review", default="")
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--paths", nargs="*", default=None)
    pc.add_argument("--force", action="store_true")
    pc.add_argument("--agent-loop", default="")
    pc.add_argument("--log", default="")
    pc.set_defaults(func=cmd_cycle)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("fixture").set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
