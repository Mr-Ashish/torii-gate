#!/usr/bin/env python3
"""F85/F116/F126/F135: Skill fitness ledger — demote zombies + tool/scorecard shields.

Research drivers (2026):
  - FederatedSkill (arXiv 2606.03143): skill library as federation unit; share
    privacy-safe patches/themes, not raw trajectories — up to +44% success.
  - Agent Skill Evaluation & Evolution (arXiv 2606.11435): longitudinal skill
    quality tracking; dual-rollout with/without skills; drop skills that never
    contribute (dead library entries).
  - Trajectory eval 2026 / Mem2Act: tool trajectory is a first-class quality
    signal — F114 tool_hit_n must compound into demote/boost/federate, not
    sit as an inert counter.
  - SigLeak / contrastive skill signatures: tool-outcome themes are portable
    skill evidence without raw trajectories.
  - MUSE-Autoskill: skill lifecycle create → evaluate → refine/demote.
  - CoEvoSkills / EvoSkills: adopted skills need fitness feedback or they rot.
  - Prior Torii F84: skill-hits.json per run — no durable ledger, no demote,
    no hub federation of skill themes.
  - F134: scorecard skills federate themes but never entered the fitness ledger
    (recovery hub had F126; scorecard ops did not).

Product thesis:
  Measure (F84) without action is theater. Highest ROI: compound hit rates into
  a local fitness ledger, **soft-demote** chronically low-hit skills from full
  progressive inject (index-only), **shield tool-effective recovery skills**
  (F116), **ingest F134 scorecard skill themes into fitness** (F135), boost
  high-hit + tool-hit skills in the router, and emit F77-compatible federated
  skill themes (id + hits + tool_outcome tags only).

Commands:
  ingest   — fold skill-hits.json into .torii/skill-fitness.json
  status   — ledger summary
  demote   — mark low hit_rate skills after min samples (tool-shielded)
  boosts   — per-skill score deltas for skill_router (+ tool bonus)
  federate — write privacy-safe skill theme signals → hub ingest path
  cycle    — ingest → hub recovery → scorecard skills → demote → federate
  ingest-scorecard — F135 fold scorecard-skill-signals into ledger
  fixture  — hermetic: hit skill boosts; zombie demotes; tool+scorecard shield
  apply    — print demoted + boosts JSON for assemble/router

Env:
  TORII_ROOT
  TORII_SKILL_FITNESS           1 (default) | 0/off
  TORII_SKILL_FITNESS_FILE      override ledger path
  TORII_SKILL_FITNESS_MIN_N     default 3 samples before demote
  TORII_SKILL_FITNESS_DEMOTE    default 0.25 hit_rate threshold
  TORII_SKILL_FITNESS_BOOST     default 2.0 max path-score bonus
  TORII_SKILL_FITNESS_TOOL      1 (default) | 0 — F116 tool_hit shield/boost/federate
  TORII_SKILL_FITNESS_HUB       1 (default) | 0 — F126 ingest hub recovery-util deltas
  TORII_SKILL_FITNESS_SCORECARD 1 (default) | 0 — F135 ingest scorecard skill themes
  TORII_SKILL_FITNESS_HUB_ARCHIVAL 1 (default) | 0 — F158 ingest hub-archival util gap/hit
  TORII_MEMORY_TENANT           optional for federate tenant hash
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F85"
FEATURE_TOOL = "F116"
FEATURE_HUB = "F126"
FEATURE_SCORECARD = "F135"
FEATURE_HUB_ARCHIVAL = "F158"
SCHEMA = 1
LEDGER_NAME = "skill-fitness.json"
SCORECARD_FED_REL = "memory/federation/scorecard-skill-signals.json"
HUB_ARCHIVAL_SKILL_ID = "skill-prefer-hub-archival-early"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})
_PATH_RX = re.compile(r"(?:/Users/|/home/|C:\\\\Users\\\\)", re.I)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SKILL_FITNESS") or "1").strip().lower()
    return raw not in _FALSEY


def tool_fitness_enabled() -> bool:
    """F116: tool_hit_n shields demote, boosts router, federates tool themes."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_TOOL") or "1").strip().lower()
    return raw not in _FALSEY


def hub_archival_fitness_enabled() -> bool:
    """F158: fold hub-archival util gap/hit into fitness demote/boost."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_HUB_ARCHIVAL") or "1").strip().lower()
    return raw not in _FALSEY


def hub_fitness_enabled() -> bool:
    """F126: fold hub recovery-util post-score into local fitness ledger."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_HUB") or "1").strip().lower()
    return raw not in _FALSEY


def scorecard_fitness_enabled() -> bool:
    """F135: fold F134 scorecard-skill-signals into local fitness ledger."""
    raw = (os.environ.get("TORII_SKILL_FITNESS_SCORECARD") or "1").strip().lower()
    return raw not in _FALSEY


def _load_scorecard_fed_doc(root: Path) -> dict[str, Any] | None:
    """Load privacy-safe scorecard skill federation doc (F134)."""
    path = root / SCORECARD_FED_REL
    if not path.is_file():
        # also accept out_dir-style copy under .torii
        alt = root / ".torii" / "scorecard-skill-signals.json"
        path = alt if alt.is_file() else path
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def ingest_scorecard_skills(
    doc: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """F135: F134 scorecard skill themes → soft tool_hit / shield on ledger.

    Consumes scorecard-skill-signals.json (skill_ids + scorecard_ops tags only).
    Never stores paths, raw tenant names, or commands.
    Active ops skills get tool-hit shield so they are not demoted as zombies
    before live hits accumulate (CoEvoSkills: adopt without fitness = rot).
    """
    root = root or _root()
    if not scorecard_fitness_enabled():
        return {
            "feature": FEATURE_SCORECARD,
            "ingested_n": 0,
            "reason": "scorecard_fitness_off",
            "privacy_ok": True,
            "scorecard_ops_ok": False,
        }
    if doc is None:
        doc = _load_scorecard_fed_doc(root)
    if not isinstance(doc, dict):
        return {
            "feature": FEATURE_SCORECARD,
            "ingested_n": 0,
            "reason": "no_scorecard_signals",
            "privacy_ok": True,
            "scorecard_ops_ok": False,
        }

    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    skill_ids: list[str] = []
    for sid in doc.get("skill_ids") or []:
        sid_s = str(sid).strip()
        if sid_s and sid_s not in skill_ids:
            skill_ids.append(sid_s)
    for sig in doc.get("signals") or []:
        if not isinstance(sig, dict):
            continue
        tags = sig.get("tags") or []
        if "scorecard_ops" not in tags and "f134" not in tags:
            # still accept theme that maps to skill-prefer-*
            pass
        theme = str(sig.get("theme") or sig.get("id") or "")
        # reconstruct skill id from theme slug when possible
        if theme.startswith("skill-prefer-") or theme.startswith("skill-"):
            sid_s = theme[:96]
            if sid_s not in skill_ids:
                skill_ids.append(sid_s)
        # keywords may carry skill stem
        for kw in sig.get("keywords") or []:
            k = str(kw).strip()
            if k.startswith("skill-prefer-") and k not in skill_ids:
                skill_ids.append(k[:96])

    # also soft-load active scorecard skills from disk (ids only)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from skill_auto_adopt import list_active_scorecard_skills  # type: ignore

        for sid in list_active_scorecard_skills(root):
            if sid not in skill_ids:
                skill_ids.append(sid)
    except Exception:
        pass

    ingested: list[str] = []
    for sid in skill_ids:
        sid_s = str(sid).strip()
        if not sid_s or _PATH_RX.search(sid_s) or "/" in sid_s or ".." in sid_s:
            continue
        sid_s = re.sub(r"[^A-Za-z0-9._-]+", "-", sid_s)[:96]
        if not sid_s.startswith("skill-"):
            # map bare stems
            if sid_s.startswith("prefer-"):
                sid_s = f"skill-{sid_s}"
            else:
                continue
        # soft sample weight: scorecard ops are tool CLIs (doctor/scorecard)
        weight = 2
        ent = _skill_entry(ledger, sid_s)
        ent["selected_n"] = int(ent.get("selected_n") or 0) + weight
        ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + weight
        ent["hit_n"] = int(ent.get("hit_n") or 0) + weight
        sel = int(ent["selected_n"])
        ent["hit_rate"] = round(int(ent["hit_n"]) / sel, 4) if sel else 0.0
        ent["tool_hit_rate"] = (
            round(int(ent.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
        )
        ent["scorecard_ingested_n"] = int(ent.get("scorecard_ingested_n") or 0) + 1
        ent["scorecard_ops"] = True
        ent["last_seen"] = _now()
        ent["last_scorecard_at"] = _now()
        # never demote scorecard ops while tool fitness on
        if tool_fitness_enabled():
            ent["demoted"] = False
        ingested.append(sid_s)

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": "scorecard_skills",
            "feature": FEATURE_SCORECARD,
            "ingested_n": len(ingested),
            "skills": ingested[:16],
        }
    )
    ledger["history"] = hist[-100:]
    ledger["last_scorecard_ingest"] = {
        "at": _now(),
        "feature": FEATURE_SCORECARD,
        "skills": ingested[:16],
        "n": len(ingested),
        "privacy_ok": bool(doc.get("privacy_ok", True)),
    }
    if save:
        save_ledger(ledger, ledger_path(root))
    privacy_blob = json.dumps(ledger.get("last_scorecard_ingest") or {})
    privacy_ok = (
        "/Users/" not in privacy_blob
        and "/home/" not in privacy_blob
        and bool(doc.get("privacy_ok", True))
    )
    return {
        "feature": FEATURE_SCORECARD,
        "ingested_n": len(ingested),
        "skills": ingested[:16],
        "privacy_ok": privacy_ok,
        "scorecard_ops_ok": len(ingested) >= 1,
        "fed_skill_n": len(doc.get("skill_ids") or []),
    }


def ingest_hub_archival_util(
    util: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    out_dir: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """F158: fold hub-archival util slice into fitness ledger (hit shield / gap demote).

    Consumes F155 score_recovery_util fields:
      hub_archival_injected, hub_archival_tool_hit, hub_archival_util_gap

    Privacy: skill id + counters only — no paths, prompts, or tenant strings.
    SkillsBench / Assay: chronic inject≠hub_boost must compound into demote;
    tool_hit shields revive.
    """
    root = root or _root()
    if not hub_archival_fitness_enabled():
        return {
            "feature": FEATURE_HUB_ARCHIVAL,
            "ingested": 0,
            "reason": "hub_archival_fitness_off",
            "privacy_ok": True,
        }
    if util is None and out_dir is not None:
        up = Path(out_dir) / "recovery-skill-util.json"
        if up.is_file():
            try:
                util = json.loads(up.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                util = None
    if util is None:
        # soft score from out_dir router artifacts
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from skill_router import score_recovery_util  # type: ignore

            util = score_recovery_util(
                Path(out_dir) if out_dir else None, root=root
            )
        except Exception as exc:
            return {
                "feature": FEATURE_HUB_ARCHIVAL,
                "ingested": 0,
                "error": str(exc)[:120],
                "privacy_ok": True,
            }
    if not isinstance(util, dict):
        return {
            "feature": FEATURE_HUB_ARCHIVAL,
            "ingested": 0,
            "reason": "no_util",
            "privacy_ok": True,
        }

    injected = bool(util.get("hub_archival_injected"))
    tool_hit = bool(util.get("hub_archival_tool_hit"))
    gap = bool(util.get("hub_archival_util_gap"))
    if not injected:
        return {
            "feature": FEATURE_HUB_ARCHIVAL,
            "ingested": 0,
            "reason": "hub_archival_not_injected",
            "privacy_ok": True,
            "skill_id": HUB_ARCHIVAL_SKILL_ID,
        }

    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    sid = HUB_ARCHIVAL_SKILL_ID
    ent = _skill_entry(ledger, sid)
    ent["selected_n"] = int(ent.get("selected_n") or 0) + 1
    ent["hub_archival_selected_n"] = int(ent.get("hub_archival_selected_n") or 0) + 1
    if tool_hit:
        ent["hit_n"] = int(ent.get("hit_n") or 0) + 1
        ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + 1
        ent["hub_archival_hit_n"] = int(ent.get("hub_archival_hit_n") or 0) + 1
        ent["demoted"] = False  # revive on hub_boost evidence
    else:
        ent["miss_n"] = int(ent.get("miss_n") or 0) + 1
        if gap:
            ent["hub_archival_gap_n"] = int(ent.get("hub_archival_gap_n") or 0) + 1
    sel = int(ent["selected_n"])
    ent["hit_rate"] = round(int(ent.get("hit_n") or 0) / sel, 4) if sel else 0.0
    ent["tool_hit_rate"] = (
        round(int(ent.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
    )
    ha_sel = int(ent.get("hub_archival_selected_n") or 0)
    ha_hit = int(ent.get("hub_archival_hit_n") or 0)
    ha_gap_n = int(ent.get("hub_archival_gap_n") or 0)
    ent["hub_archival_util_rate"] = (
        round(ha_hit / ha_sel, 4) if ha_sel else 1.0
    )
    ent["hub_archival_gap_rate"] = (
        round(ha_gap_n / ha_sel, 4) if ha_sel else 0.0
    )
    ent["last_seen"] = _now()
    ent["last_hub_archival_at"] = _now()
    ent["hub_archival_ops"] = True

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": "hub_archival_util",
            "feature": FEATURE_HUB_ARCHIVAL,
            "skill_id": sid,
            "tool_hit": int(tool_hit),
            "util_gap": int(gap),
            "hub_archival_gap_n": ha_gap_n,
            "hub_archival_hit_n": ha_hit,
        }
    )
    ledger["history"] = hist[-100:]
    ledger["last_hub_archival_ingest"] = {
        "at": _now(),
        "feature": FEATURE_HUB_ARCHIVAL,
        "skill_id": sid,
        "tool_hit": int(tool_hit),
        "util_gap": int(gap),
        "gap_n": ha_gap_n,
        "hit_n": ha_hit,
        "util_rate": ent.get("hub_archival_util_rate"),
    }

    path = None
    if save:
        path = save_ledger(ledger, ledger_path(root))

    blob = json.dumps(ledger.get("last_hub_archival_ingest") or {})
    privacy_ok = "/Users/" not in blob and "/home/" not in blob

    return {
        "feature": FEATURE_HUB_ARCHIVAL,
        "ingested": 1,
        "skill_id": sid,
        "tool_hit": int(tool_hit),
        "util_gap": int(gap),
        "hub_archival_gap_n": ha_gap_n,
        "hub_archival_hit_n": ha_hit,
        "hub_archival_util_rate": ent.get("hub_archival_util_rate"),
        "hub_archival_gap_rate": ent.get("hub_archival_gap_rate"),
        "privacy_ok": privacy_ok,
        "ledger": str(path) if path else None,
    }


def ingest_hub_recovery(
    hub: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """F126: privacy-safe hub recovery themes → soft tool_hit / shield on ledger.

    Consumes F125 post_score_recovery_hub (skill_id + hits + tool_hits only).
    Never stores paths, tenants names, or commands.
    """
    root = root or _root()
    if not hub_fitness_enabled():
        return {
            "feature": FEATURE_HUB,
            "ingested_n": 0,
            "reason": "hub_fitness_off",
            "privacy_ok": True,
        }
    if hub is None:
        # soft load from federation store via skill_router
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from skill_router import post_score_recovery_hub  # type: ignore

            hub = post_score_recovery_hub(root=root)
        except Exception as exc:
            return {
                "feature": FEATURE_HUB,
                "ingested_n": 0,
                "error": str(exc)[:120],
                "privacy_ok": True,
            }
    ledger = ledger if ledger is not None else load_ledger(ledger_path(root))
    skills_doc = hub.get("skills") if isinstance(hub, dict) else None
    if not isinstance(skills_doc, dict):
        skills_doc = {}
    # also accept priority_deltas-only
    deltas = (hub.get("priority_deltas") or {}) if isinstance(hub, dict) else {}
    ingested: list[str] = []
    for sid, ent_h in skills_doc.items():
        sid_s = str(sid).strip()
        if not sid_s or _PATH_RX.search(sid_s) or "/" in sid_s or ".." in sid_s:
            continue
        sid_s = re.sub(r"[^A-Za-z0-9._-]+", "-", sid_s)[:96]
        if not sid_s.startswith("skill-"):
            continue
        hits = 1
        tool_hits = 0
        tenants = 1
        if isinstance(ent_h, dict):
            hits = max(1, int(ent_h.get("hits") or 1))
            tool_hits = max(0, int(ent_h.get("tool_hits") or 0))
            tenants = max(1, int(ent_h.get("tenants") or 1))
        # soft sample weight: cap so hub can't drown local
        weight = min(3, max(1, min(hits, tenants)))
        ent = _skill_entry(ledger, sid_s)
        ent["selected_n"] = int(ent.get("selected_n") or 0) + weight
        # hub tool themes count as tool hits (shield demote)
        th_add = min(3, max(1, tool_hits if tool_hits else weight))
        ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + th_add
        ent["hit_n"] = int(ent.get("hit_n") or 0) + min(weight, th_add)
        sel = int(ent["selected_n"])
        ent["hit_rate"] = round(int(ent["hit_n"]) / sel, 4) if sel else 0.0
        ent["tool_hit_rate"] = (
            round(int(ent.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
        )
        ent["hub_ingested_n"] = int(ent.get("hub_ingested_n") or 0) + 1
        ent["hub_priority_delta"] = int(
            (ent_h or {}).get("priority_delta")
            if isinstance(ent_h, dict)
            else deltas.get(sid_s)
            or 0
        )
        ent["last_seen"] = _now()
        ent["last_hub_at"] = _now()
        # never demote hub tool-effective recovery
        if tool_fitness_enabled() and int(ent.get("tool_hit_n") or 0) >= 1:
            ent["demoted"] = False
        ingested.append(sid_s)

    # deltas-only skills not in skills map
    for sid, delta in deltas.items():
        sid_s = str(sid).strip()
        if sid_s in ingested:
            continue
        if not sid_s.startswith("skill-") or "/" in sid_s:
            continue
        ent = _skill_entry(ledger, sid_s)
        ent["hub_priority_delta"] = int(delta or 0)
        ent["last_hub_at"] = _now()
        ingested.append(sid_s)

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": "hub_recovery",
            "feature": FEATURE_HUB,
            "ingested_n": len(ingested),
            "skills": ingested[:16],
            "gap_pressure": (hub or {}).get("gap_pressure") if isinstance(hub, dict) else None,
        }
    )
    ledger["history"] = hist[-100:]
    ledger["last_hub_ingest"] = {
        "at": _now(),
        "feature": FEATURE_HUB,
        "skills": ingested[:16],
        "n": len(ingested),
    }
    path = None
    if save:
        path = save_ledger(ledger, ledger_path(root))
    blob = json.dumps(ingested)
    privacy_ok = "/Users/" not in blob and "/home/" not in blob
    return {
        "feature": FEATURE_HUB,
        "ingested_n": len(ingested),
        "skills": ingested,
        "privacy_ok": privacy_ok,
        "ledger": str(path) if path else str(ledger_path(root)),
        "gap_pressure": (hub or {}).get("gap_pressure") if isinstance(hub, dict) else None,
    }


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def ledger_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_SKILL_FITNESS_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / LEDGER_NAME


def empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "updated_at": _now(),
        "skills": {},
        "history": [],
        "demoted": [],
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
    data.setdefault("history", [])
    data.setdefault("demoted", [])
    data.setdefault("schema_version", SCHEMA)
    data.setdefault("feature", FEATURE)
    return data


def save_ledger(ledger: dict[str, Any], path: Path | None = None) -> Path:
    p = path or ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = _now()
    ledger["feature"] = FEATURE
    ledger["schema_version"] = SCHEMA
    p.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return p


def _skill_entry(ledger: dict[str, Any], sid: str) -> dict[str, Any]:
    skills = ledger.setdefault("skills", {})
    if sid not in skills:
        skills[sid] = {
            "id": sid,
            "selected_n": 0,
            "hit_n": 0,
            "miss_n": 0,
            "hit_rate": 0.0,
            "demoted": False,
            "last_seen": "",
        }
    return skills[sid]


def ingest_hits(
    hits_doc: dict[str, Any],
    ledger: dict[str, Any] | None = None,
    *,
    run_id: str = "",
) -> dict[str, Any]:
    ledger = ledger if ledger is not None else load_ledger()
    for h in hits_doc.get("hits") or []:
        sid = str(h.get("id") or "").strip()
        if not sid or _PATH_RX.search(sid) or "/" in sid:
            continue
        # normalize skill ids only
        sid = re.sub(r"[^A-Za-z0-9._-]+", "-", sid)[:96]
        ent = _skill_entry(ledger, sid)
        ent["selected_n"] = int(ent.get("selected_n") or 0) + 1
        if h.get("hit"):
            ent["hit_n"] = int(ent.get("hit_n") or 0) + 1
        else:
            ent["miss_n"] = int(ent.get("miss_n") or 0) + 1
        # F114: track tool-invocation outcomes separately (prose-only skills leave 0)
        if h.get("tool_hit"):
            ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + 1
        sel = int(ent["selected_n"])
        ent["hit_rate"] = round(int(ent["hit_n"]) / sel, 4) if sel else 0.0
        # F116: tool_hit_rate for demote shield + federate
        ent["tool_hit_rate"] = (
            round(int(ent.get("tool_hit_n") or 0) / sel, 4) if sel else 0.0
        )
        ent["last_seen"] = _now()

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": run_id or hits_doc.get("review") or "",
            "hit_rate": hits_doc.get("hit_rate"),
            "selected_n": hits_doc.get("selected_n"),
            "hit_n": hits_doc.get("hit_n"),
            "tool_hit_n": hits_doc.get("tool_hit_n"),
            "tool_hit_rate": hits_doc.get("tool_hit_rate"),
            "themes": list(hits_doc.get("federated_skill_themes") or [])[:16],
        }
    )
    ledger["history"] = hist[-100:]
    return ledger


def _effective_rate(ent: dict[str, Any]) -> float:
    """F116: demote uses max(prose/combined hit_rate, tool_hit_rate)."""
    rate = float(ent.get("hit_rate") or 0.0)
    if not tool_fitness_enabled():
        return rate
    tool_rate = float(ent.get("tool_hit_rate") or 0.0)
    if tool_rate <= 0:
        n = int(ent.get("selected_n") or 0)
        tool_n = int(ent.get("tool_hit_n") or 0)
        tool_rate = (tool_n / n) if n else 0.0
    return max(rate, tool_rate)


def apply_demotions(ledger: dict[str, Any]) -> dict[str, Any]:
    min_n = _int_env("TORII_SKILL_FITNESS_MIN_N", 3)
    thr = _float_env("TORII_SKILL_FITNESS_DEMOTE", 0.25)
    # F158: chronic hub-archival util gap thr (gap_rate ≥ this after min samples)
    ha_gap_thr = _float_env("TORII_SKILL_FITNESS_HUB_ARCHIVAL_GAP_THR", 0.67)
    demoted: list[str] = []
    revived: list[str] = []
    shielded: list[str] = []
    ha_demoted: list[str] = []
    for sid, ent in (ledger.get("skills") or {}).items():
        n = int(ent.get("selected_n") or 0)
        rate = float(ent.get("hit_rate") or 0.0)
        eff = _effective_rate(ent)
        tool_n = int(ent.get("tool_hit_n") or 0)
        was = bool(ent.get("demoted"))
        # F116: tool-effective skills (any tool_hit with samples) never demote
        tool_shield = bool(tool_fitness_enabled() and tool_n >= 1 and n >= 1)
        if tool_shield and was:
            ent["demoted"] = False
            revived.append(sid)
            shielded.append(sid)
            continue
        if tool_shield:
            ent["demoted"] = False
            shielded.append(sid)
            continue
        # F158: hub-archival chronic util gap (inject ≠ hub_boost) → demote
        # even when always:true — soft demote hits fitness_boosts / router, not inject flag
        if (
            hub_archival_fitness_enabled()
            and sid == HUB_ARCHIVAL_SKILL_ID
            and int(ent.get("hub_archival_selected_n") or 0) >= min_n
        ):
            ha_gap_rate = float(ent.get("hub_archival_gap_rate") or 0.0)
            ha_hit = int(ent.get("hub_archival_hit_n") or 0)
            if ha_hit < 1 and ha_gap_rate >= ha_gap_thr:
                ent["demoted"] = True
                demoted.append(sid)
                ha_demoted.append(sid)
                continue
            if ha_hit >= 1 and float(ent.get("hub_archival_util_rate") or 0) >= 0.34:
                if was:
                    revived.append(sid)
                ent["demoted"] = False
                continue
        # never demote always-on core by id heuristic — skill_router still
        # respects always flag; ledger may still mark low performers for info
        if n >= min_n and eff < thr:
            ent["demoted"] = True
            demoted.append(sid)
        elif n >= min_n and eff >= thr + 0.15:
            # revive on sustained recovery
            if was:
                revived.append(sid)
            ent["demoted"] = False
        # if under min_n keep current demoted flag
    ledger["demoted"] = sorted(
        sid for sid, e in (ledger.get("skills") or {}).items() if e.get("demoted")
    )
    ledger["last_demote"] = {
        "at": _now(),
        "min_n": min_n,
        "threshold": thr,
        "newly_demoted": demoted,
        "revived": revived,
        "tool_shielded": shielded,
        "hub_archival_demoted": ha_demoted,
        "hub_archival_gap_thr": ha_gap_thr,
        "demoted_n": len(ledger["demoted"]),
        "feature_tool": FEATURE_TOOL if tool_fitness_enabled() else None,
        "feature_hub_archival": FEATURE_HUB_ARCHIVAL
        if hub_archival_fitness_enabled()
        else None,
    }
    return ledger


def fitness_boosts(ledger: dict[str, Any] | None = None) -> dict[str, float]:
    """Score deltas for skill_router: hit_rate + F116 tool bonus; demoted negative."""
    ledger = ledger if ledger is not None else load_ledger()
    max_boost = _float_env("TORII_SKILL_FITNESS_BOOST", 2.0)
    out: dict[str, float] = {}
    use_tool = tool_fitness_enabled()
    for sid, ent in (ledger.get("skills") or {}).items():
        n = int(ent.get("selected_n") or 0)
        if n < 1:
            continue
        rate = float(ent.get("hit_rate") or 0.0)
        if ent.get("demoted"):
            out[sid] = -max_boost  # strong penalty (unless always)
            continue
        # map hit_rate [0,1] → [0, max_boost] after min 1 sample; stronger after 3
        conf = min(1.0, n / 3.0)
        score = rate * max_boost * conf
        if use_tool:
            tool_n = int(ent.get("tool_hit_n") or 0)
            tool_rate = tool_n / n if n else 0.0
            # half-weight tool bonus so recovery skills rank above prose-only peers
            score += tool_rate * max_boost * 0.5 * conf
        # F158: hub-archival util_rate boost / chronic gap penalty (soft rank)
        if (
            hub_archival_fitness_enabled()
            and sid == HUB_ARCHIVAL_SKILL_ID
            and int(ent.get("hub_archival_selected_n") or 0) >= 1
        ):
            ha_rate = float(ent.get("hub_archival_util_rate") or 0.0)
            ha_gap = float(ent.get("hub_archival_gap_rate") or 0.0)
            score += ha_rate * max_boost * 0.6 * conf
            score -= ha_gap * max_boost * 0.8 * conf
        out[sid] = round(score, 3)
    return out


def demoted_set(ledger: dict[str, Any] | None = None) -> set[str]:
    ledger = ledger if ledger is not None else load_ledger()
    return set(ledger.get("demoted") or [])


def federate_signals(
    ledger: dict[str, Any] | None = None,
    *,
    tenant: str = "",
) -> list[dict[str, Any]]:
    """Privacy-safe F77-shaped signals for high-hit / tool-hit skills (ids only)."""
    ledger = ledger if ledger is not None else load_ledger()
    tenant = tenant or (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    th = ""
    if tenant:
        th = hashlib.sha256(tenant.encode("utf-8")).hexdigest()[:12]
    signals: list[dict[str, Any]] = []
    use_tool = tool_fitness_enabled()
    for sid, ent in (ledger.get("skills") or {}).items():
        if _PATH_RX.search(sid) or "/" in sid:
            continue
        hit_n = int(ent.get("hit_n") or 0)
        tool_n = int(ent.get("tool_hit_n") or 0)
        # F116: tool-only contributors still federate (even if prose hit_n=0)
        if hit_n < 1 and not (use_tool and tool_n >= 1):
            continue
        if ent.get("demoted"):
            continue
        theme = f"skill:{sid}" if not sid.startswith("skill") else sid
        # F77 theme is free-form lower slug
        theme_slug = re.sub(r"[^a-z0-9._-]+", "-", theme.lower())[:64]
        tags = ["skill_hit", "f85", "federated_skill"]
        keywords = [sid.replace("skill-", "")[:48], "skill-fitness"]
        if use_tool and tool_n >= 1:
            tags.extend(["tool_outcome", "f116"])
            keywords.append("tool-outcome")
        if ent.get("scorecard_ops") or int(ent.get("scorecard_ingested_n") or 0) >= 1:
            tags.extend(["scorecard_ops", "f135"])
            keywords.append("scorecard-ops")
        if ent.get("hub_archival_ops") or int(ent.get("hub_archival_hit_n") or 0) >= 1:
            tags.extend(["hub_archival", "f158", "hub_boost"])
            keywords.extend(["hub-archival", "hub-boost"])
        sig: dict[str, Any] = {
            "id": theme_slug,
            "theme": theme_slug,
            "cwe": [],
            "tags": tags,
            "keywords": keywords,
            "path_basenames": [],  # never paths
            "hits": max(1, hit_n, tool_n),
            "source": "skill_fitness",
            "tenants": 1,
        }
        if use_tool and tool_n >= 1:
            # privacy-safe count only — no commands/paths
            sig["tool_hits"] = tool_n
        if th:
            sig["tenant_hashes"] = [th]
            sig["tenant_hash"] = th
        signals.append(sig)

    # F161: chronic hub-archival util gap (even when demoted) → multi-tenant pressure
    if hub_archival_fitness_enabled():
        ha_ent = (ledger.get("skills") or {}).get(HUB_ARCHIVAL_SKILL_ID) or {}
        ha_gap_n = int(ha_ent.get("hub_archival_gap_n") or 0)
        ha_sel = int(ha_ent.get("hub_archival_selected_n") or 0)
        ha_gap_rate = float(ha_ent.get("hub_archival_gap_rate") or 0.0)
        if ha_sel >= 1 and ha_gap_n >= 1 and ha_gap_rate >= 0.34:
            gap_sig: dict[str, Any] = {
                "id": "hub-archival-util-gap",
                "theme": "hub-archival-util-gap",
                "cwe": [],
                "tags": [
                    "hub_archival",
                    "utilization_gap",
                    "hub_archival_idle",
                    "f161",
                    "f158",
                    "federated_skill",
                ],
                "keywords": ["hub-archival-gap", "hub-boost-idle", "chronic"],
                "path_basenames": [],
                "hits": max(1, ha_gap_n),
                "source": "skill_fitness_hub_archival",
                "tenants": 1,
                "util_rate_bin": "gap",
                "hub_archival_idle": True,
            }
            if th:
                gap_sig["tenant_hashes"] = [th]
                gap_sig["tenant_hash"] = th
            signals.append(gap_sig)
    return signals


def write_fed_file(
    signals: list[dict[str, Any]],
    root: Path | None = None,
    dest: Path | None = None,
) -> Path:
    root = root or _root()
    dest = dest or (root / "memory" / "federation" / "skill-fitness-signals.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # privacy assert
    issues = []
    for s in signals:
        blob = json.dumps(s)
        if "/Users/" in blob or "/home/" in blob:
            issues.append(s.get("id"))
    clean = [s for s in signals if s.get("id") not in issues]
    tool_n = sum(1 for s in clean if "tool_outcome" in (s.get("tags") or []))
    # F161: also write hub-archival slice for multi-tenant pressure consumers
    ha_sigs = [
        s
        for s in clean
        if "hub_archival" in (s.get("tags") or [])
        or str(s.get("theme") or "").startswith("hub-archival")
    ]
    if ha_sigs:
        try:
            ha_dest = root / "memory" / "federation" / "hub-archival-util-signals.json"
            ha_dest.write_text(
                json.dumps(
                    {
                        "schema_version": SCHEMA,
                        "feature": FEATURE_HUB_ARCHIVAL,
                        "feature_hub": "F161",
                        "scope": "hub_archival_util",
                        "updated_at": _now(),
                        "privacy_ok": True,
                        "signals": ha_sigs,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    doc = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "feature_tool": FEATURE_TOOL if tool_fitness_enabled() else None,
        "scope": "skill_fitness",
        "updated_at": _now(),
        "count": len(clean),
        "tool_outcome_n": tool_n,
        "privacy": "skill_id_hits_tenant_hash_only",
        "privacy_ok": len(issues) == 0,
        "privacy_issues": issues,
        "signals": clean,
    }
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return dest


def cycle(out_dir: Path | None = None, root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    ledger = load_ledger(ledger_path(root))
    ingested = False
    hits_path = None
    if out_dir:
        hits_path = Path(out_dir) / "skill-hits.json"
        if hits_path.is_file():
            try:
                hits = json.loads(hits_path.read_text(encoding="utf-8"))
                ledger = ingest_hits(hits, ledger, run_id=str(out_dir))
                ingested = True
            except (OSError, json.JSONDecodeError):
                pass
    # F126: fold hub recovery-util post-score into ledger before demote
    hub_fit = None
    if hub_fitness_enabled():
        try:
            hub_fit = ingest_hub_recovery(None, ledger, root=root, save=False)
            # ledger already mutated; ensure demote sees tool shields
        except Exception as exc:
            hub_fit = {"soft_error": str(exc)[:120]}
    # F135: fold F134 scorecard skill themes into ledger before demote
    sc_fit = None
    if scorecard_fitness_enabled():
        try:
            sc_fit = ingest_scorecard_skills(None, ledger, root=root, save=False)
        except Exception as exc:
            sc_fit = {"soft_error": str(exc)[:120]}
    # F158: fold hub-archival util gap/hit before demote
    ha_fit = None
    if hub_archival_fitness_enabled():
        try:
            ha_fit = ingest_hub_archival_util(
                None, ledger, root=root, out_dir=out_dir, save=False
            )
        except Exception as exc:
            ha_fit = {"soft_error": str(exc)[:120]}
    ledger = apply_demotions(ledger)
    path = save_ledger(ledger, ledger_path(root))
    signals = federate_signals(ledger)
    fed_path = write_fed_file(signals, root=root)
    # soft hub ingest if available
    hub_result = None
    try:
        sys.path.insert(0, str(root / "scripts"))
        from federated_hub_ingest import ingest as hub_ingest  # type: ignore

        tenant = (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
        hub_result = hub_ingest(
            root,
            signals,
            tenant=tenant,
            source_repo="skill_fitness",
            write_tenant=bool(tenant),
        )
    except Exception as exc:  # soft
        hub_result = {"soft_error": str(exc)[:120]}

    tool_skills = [
        sid
        for sid, e in (ledger.get("skills") or {}).items()
        if int(e.get("tool_hit_n") or 0) >= 1
    ]
    scorecard_skills = [
        sid
        for sid, e in (ledger.get("skills") or {}).items()
        if e.get("scorecard_ops") or int(e.get("scorecard_ingested_n") or 0) >= 1
    ]
    hub_archival_skills = [
        sid
        for sid, e in (ledger.get("skills") or {}).items()
        if e.get("hub_archival_ops")
        or int(e.get("hub_archival_selected_n") or 0) >= 1
    ]
    return {
        "feature": FEATURE,
        "feature_tool": FEATURE_TOOL if tool_fitness_enabled() else None,
        "feature_hub": FEATURE_HUB if hub_fitness_enabled() else None,
        "feature_scorecard": FEATURE_SCORECARD if scorecard_fitness_enabled() else None,
        "feature_hub_archival": FEATURE_HUB_ARCHIVAL
        if hub_archival_fitness_enabled()
        else None,
        "ingested": ingested,
        "hits_path": str(hits_path) if hits_path else None,
        "ledger": str(path),
        "demoted": list(ledger.get("demoted") or []),
        "tool_shielded": list((ledger.get("last_demote") or {}).get("tool_shielded") or []),
        "hub_archival_demoted": list(
            (ledger.get("last_demote") or {}).get("hub_archival_demoted") or []
        ),
        "tool_skills": tool_skills,
        "scorecard_skills": scorecard_skills,
        "hub_archival_skills": hub_archival_skills,
        "boosts": fitness_boosts(ledger),
        "fed_path": str(fed_path),
        "fed_n": len(signals),
        "tool_outcome_fed_n": sum(
            1 for s in signals if "tool_outcome" in (s.get("tags") or [])
        ),
        "hub": hub_result,
        "hub_fitness": hub_fit,
        "scorecard_fitness": sc_fit,
        "hub_archival_fitness": ha_fit,
        "privacy_ok": True,
    }


# --- CLI ---


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _root()
    out_dir = Path(args.out_dir) if args.out_dir else Path(os.environ.get("OUT_DIR") or ".")
    hits_path = Path(args.hits) if args.hits else out_dir / "skill-hits.json"
    if not hits_path.is_file():
        print(json.dumps({"feature": FEATURE, "ingested": 0, "reason": "no skill-hits.json"}))
        return 0
    hits = json.loads(hits_path.read_text(encoding="utf-8"))
    ledger = ingest_hits(hits, load_ledger(ledger_path(root)), run_id=str(out_dir))
    path = save_ledger(ledger, ledger_path(root))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "ingested": 1,
                "ledger": str(path),
                "skills_n": len(ledger.get("skills") or {}),
                "history_n": len(ledger.get("history") or []),
            },
            indent=2,
        )
    )
    return 0


def cmd_demote(args: argparse.Namespace) -> int:
    root = _root()
    ledger = apply_demotions(load_ledger(ledger_path(root)))
    path = save_ledger(ledger, ledger_path(root))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "ledger": str(path),
                "demoted": ledger.get("demoted") or [],
                "last_demote": ledger.get("last_demote"),
            },
            indent=2,
        )
    )
    return 0


def cmd_boosts(args: argparse.Namespace) -> int:
    b = fitness_boosts(load_ledger())
    print(json.dumps({"feature": FEATURE, "boosts": b, "demoted": sorted(demoted_set())}, indent=2))
    return 0


def cmd_federate(args: argparse.Namespace) -> int:
    root = _root()
    ledger = load_ledger(ledger_path(root))
    signals = federate_signals(ledger)
    dest = write_fed_file(signals, root=root, dest=Path(args.out) if args.out else None)
    hub = None
    if not args.no_hub:
        try:
            sys.path.insert(0, str(root / "scripts"))
            from federated_hub_ingest import ingest as hub_ingest  # type: ignore

            hub = hub_ingest(
                root,
                signals,
                tenant=(os.environ.get("TORII_MEMORY_TENANT") or "").strip(),
                source_repo="skill_fitness",
            )
        except Exception as exc:
            hub = {"soft_error": str(exc)[:120]}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fed_path": str(dest),
                "fed_n": len(signals),
                "privacy_ok": "/Users/" not in dest.read_text(encoding="utf-8"),
                "hub": hub,
            },
            indent=2,
        )
    )
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "skipped": 1, "reason": "disabled"}))
        return 0
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is None and (os.environ.get("OUT_DIR") or "").strip():
        out_dir = Path(os.environ["OUT_DIR"])
    result = cycle(out_dir=out_dir, root=_root())
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ledger = load_ledger()
    skills = ledger.get("skills") or {}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "ledger": str(ledger_path()),
                "skills_n": len(skills),
                "demoted": list(ledger.get("demoted") or []),
                "history_n": len(ledger.get("history") or []),
                "boosts": fitness_boosts(ledger),
                "top": sorted(
                    (
                        {
                            "id": s,
                            "hit_rate": e.get("hit_rate"),
                            "selected_n": e.get("selected_n"),
                            "demoted": e.get("demoted"),
                        }
                        for s, e in skills.items()
                    ),
                    key=lambda x: (-float(x.get("hit_rate") or 0), str(x["id"])),
                )[:10],
            },
            indent=2,
        )
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Machine-readable demoted set + boosts for skill_router."""
    ledger = load_ledger()
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "demoted": sorted(demoted_set(ledger)),
                "boosts": fitness_boosts(ledger),
            }
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    prev_env = {
        k: os.environ.get(k)
        for k in (
            "TORII_ROOT",
            "TORII_SKILL_FITNESS",
            "TORII_SKILL_FITNESS_MIN_N",
            "TORII_SKILL_FITNESS_DEMOTE",
            "TORII_SKILL_FITNESS_BOOST",
            "TORII_MEMORY_TENANT",
            "TORII_SKILL_FITNESS_SCORECARD",
        )
    }
    try:
        return _cmd_fixture_body()
    finally:
        for k, v in prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _cmd_fixture_body() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        os.environ["TORII_ROOT"] = str(root)
        os.environ["TORII_SKILL_FITNESS"] = "1"
        os.environ["TORII_SKILL_FITNESS_MIN_N"] = "3"
        os.environ["TORII_SKILL_FITNESS_DEMOTE"] = "0.34"
        os.environ["TORII_SKILL_FITNESS_BOOST"] = "2.0"
        os.environ["TORII_MEMORY_TENANT"] = "fixture-tenant-a"
        os.environ["TORII_SKILL_FITNESS_SCORECARD"] = "1"

        # good skill always hits; zombie never hits
        good = "skill-f74-prefer-chain-json"
        zombie = "skill-zombie-docs"
        ledger = empty_ledger()
        for i in range(4):
            hits = {
                "hit_rate": 0.5,
                "selected_n": 2,
                "hit_n": 1,
                "hits": [
                    {"id": good, "hit": True, "matched": ["chain"]},
                    {"id": zombie, "hit": False, "matched": []},
                ],
                "federated_skill_themes": [good],
                "review": f"run-{i}",
            }
            ledger = ingest_hits(hits, ledger, run_id=f"run-{i}")
        # one extra hit for good to push rate up
        ledger = ingest_hits(
            {
                "hits": [{"id": good, "hit": True, "matched": ["taint"]}],
                "federated_skill_themes": [good],
            },
            ledger,
            run_id="run-extra",
        )
        ledger = apply_demotions(ledger)
        path = save_ledger(ledger, ledger_path(root))

        boosts = fitness_boosts(ledger)
        demoted = demoted_set(ledger)
        zombie_demoted = zombie in demoted
        good_not_demoted = good not in demoted
        good_boost = boosts.get(good, 0) > 0
        zombie_pen = boosts.get(zombie, 0) < 0

        signals = federate_signals(ledger, tenant="fixture-tenant-a")
        fed_path = write_fed_file(signals, root=root)
        fed_text = fed_path.read_text(encoding="utf-8")
        privacy_ok = "/Users/" not in fed_text and "fixture-tenant-a" not in fed_text
        good_in_fed = any(good in str(s.get("id")) or good in str(s.get("theme")) for s in signals)
        zombie_not_fed = not any(zombie in str(s) for s in signals)

        # router integration: patch score via boosts API
        # simulate select preference: good boost > zombie
        order_ok = boosts.get(good, 0) > boosts.get(zombie, -99)

        # F116: tool-only recovery skill — low prose hit_rate but tool_hit_n>0 → shield
        tool_skill = "skill-prefer-memory-cli-early"
        for i in range(4):
            ledger = ingest_hits(
                {
                    "hits": [
                        {
                            "id": tool_skill,
                            # combined hit via tool (F114) may still be True;
                            # stress shield even when hit True only via tools
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                            "matched": [],
                        }
                    ],
                    "tool_hit_n": 1,
                    "tool_hit_rate": 1.0,
                    "hit_n": 1,
                    "selected_n": 1,
                    "hit_rate": 1.0,
                },
                ledger,
                run_id=f"tool-run-{i}",
            )
        # adversarial: force low hit_rate with tool hits still present
        ent_t = (ledger.get("skills") or {}).get(tool_skill) or {}
        ent_t["hit_rate"] = 0.1  # would demote without shield
        ent_t["selected_n"] = 4
        ent_t["hit_n"] = 1
        ent_t["tool_hit_n"] = 3
        ent_t["tool_hit_rate"] = 0.75
        ent_t["demoted"] = True  # was wrongly demoted pre-F116
        (ledger.setdefault("skills", {}))[tool_skill] = ent_t
        ledger = apply_demotions(ledger)
        tool_shielded = tool_skill not in demoted_set(ledger)
        tool_boost = fitness_boosts(ledger).get(tool_skill, 0) > fitness_boosts(ledger).get(
            zombie, -99
        )
        tool_sigs = federate_signals(ledger, tenant="fixture-tenant-a")
        tool_in_fed = any(
            tool_skill in str(s.get("id") or s.get("theme") or "")
            and "tool_outcome" in (s.get("tags") or [])
            for s in tool_sigs
        )
        tool_privacy = "/Users/" not in json.dumps(tool_sigs)

        # cycle with out_dir skill-hits
        out_dir = root / "out"
        out_dir.mkdir()
        (out_dir / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {"id": good, "hit": True, "matched": ["chain"]},
                        {"id": zombie, "hit": False, "matched": []},
                        {
                            "id": tool_skill,
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                            "matched": [],
                        },
                    ],
                    "hit_rate": 0.67,
                    "selected_n": 3,
                    "hit_n": 2,
                    "tool_hit_n": 1,
                    "tool_hit_rate": 0.33,
                    "federated_skill_themes": [good, tool_skill],
                }
            ),
            encoding="utf-8",
        )
        cyc = cycle(out_dir=out_dir, root=root)

        # F135: plant scorecard skill signals → fitness ingest shields ops skills
        sc_skill = "skill-prefer-product-scorecard"
        fed_dir = root / "memory" / "federation"
        fed_dir.mkdir(parents=True, exist_ok=True)
        sc_doc = {
            "schema_version": 1,
            "feature": "F133",
            "feature_federate": "F134",
            "privacy_ok": True,
            "skill_ids": [sc_skill, "skill-prefer-demote-eval-check"],
            "signals": [
                {
                    "id": "scorecard-skill-skill-prefer-product-scorecard",
                    "theme": sc_skill,
                    "tags": ["scorecard_ops", "federated_skill", "f134", "tool_outcome"],
                    "keywords": ["product-scorecard", "scorecard-gap"],
                    "path_basenames": [],
                    "hits": 1,
                    "tool_hits": 1,
                    "source": "scorecard_skill_adopt",
                }
            ],
        }
        (fed_dir / "scorecard-skill-signals.json").write_text(
            json.dumps(sc_doc, indent=2) + "\n", encoding="utf-8"
        )
        # adversarial: pretent demoted before ingest
        ent_sc = _skill_entry(ledger, sc_skill)
        ent_sc["selected_n"] = 4
        ent_sc["hit_n"] = 0
        ent_sc["hit_rate"] = 0.0
        ent_sc["demoted"] = True
        ledger.setdefault("skills", {})[sc_skill] = ent_sc
        sc_fit = ingest_scorecard_skills(sc_doc, ledger, root=root, save=True)
        ledger = apply_demotions(load_ledger(ledger_path(root)))
        sc_shielded = sc_skill not in demoted_set(ledger)
        sc_boost = fitness_boosts(ledger).get(sc_skill, 0) > 0
        sc_privacy = bool(sc_fit.get("privacy_ok")) and "fixture-tenant-a" not in json.dumps(
            sc_fit
        )
        sc_ops_ok = bool(sc_fit.get("scorecard_ops_ok"))
        sc_in_fed_out = any(
            sc_skill in str(s.get("id") or s.get("theme") or "")
            for s in federate_signals(ledger, tenant="fixture-tenant-a")
        )

        # F158: chronic hub-archival util gap → demote; hub_boost hit → revive/boost
        os.environ["TORII_SKILL_FITNESS_HUB_ARCHIVAL"] = "1"
        ha_sid = HUB_ARCHIVAL_SKILL_ID
        # 3 gap samples (inject idle)
        for i in range(3):
            util_gap = {
                "hub_archival_injected": True,
                "hub_archival_tool_hit": False,
                "hub_archival_util_gap": True,
                "util_rate": 0.5,
            }
            ingest_hub_archival_util(util_gap, ledger, root=root, save=False)
        ledger = apply_demotions(ledger)
        ha_gap_demoted = ha_sid in demoted_set(ledger)
        ha_gap_boost = fitness_boosts(ledger).get(ha_sid, 0)
        # revive with tool hit samples
        for i in range(2):
            util_hit = {
                "hub_archival_injected": True,
                "hub_archival_tool_hit": True,
                "hub_archival_util_gap": False,
                "util_rate": 1.0,
            }
            ingest_hub_archival_util(util_hit, ledger, root=root, save=False)
        ledger = apply_demotions(ledger)
        save_ledger(ledger, ledger_path(root))
        ha_revived = ha_sid not in demoted_set(ledger)
        ha_hit_boost = fitness_boosts(ledger).get(ha_sid, 0)
        ha_ent = (ledger.get("skills") or {}).get(ha_sid) or {}
        ha_privacy = "/Users/" not in json.dumps(ha_ent)
        ha_in_fed = any(
            ha_sid in str(s.get("id") or s.get("theme") or "")
            and "hub_archival" in (s.get("tags") or [])
            for s in federate_signals(ledger, tenant="fixture-tenant-a")
        )
        # cycle path: plant recovery-skill-util and run cycle
        (out_dir / "recovery-skill-util.json").write_text(
            json.dumps(
                {
                    "hub_archival_injected": True,
                    "hub_archival_tool_hit": True,
                    "hub_archival_util_gap": False,
                    "feature_hub_archival_util": "F155",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        cyc2 = cycle(out_dir=out_dir, root=root)
        f158_ok = (
            ha_gap_demoted
            and ha_revived
            and ha_hit_boost > ha_gap_boost
            and float(ha_ent.get("hub_archival_util_rate") or 0) > 0
            and int(ha_ent.get("hub_archival_hit_n") or 0) >= 2
            and ha_privacy
            and ha_in_fed
            and int((cyc2.get("hub_archival_fitness") or {}).get("ingested") or 0) >= 1
        )

        fixture_pass = all(
            [
                zombie_demoted,
                good_not_demoted,
                good_boost,
                zombie_pen,
                privacy_ok,
                good_in_fed,
                zombie_not_fed,
                order_ok,
                cyc.get("ingested") is True,
                path.is_file(),
                tool_shielded,
                tool_boost,
                tool_in_fed,
                tool_privacy,
                int(cyc.get("tool_outcome_fed_n") or 0) >= 1
                or tool_skill in (cyc.get("tool_skills") or []),
                # F135
                sc_shielded,
                sc_boost,
                sc_privacy,
                sc_ops_ok,
                int(sc_fit.get("ingested_n") or 0) >= 1,
                sc_in_fed_out,
                # F158
                f158_ok,
            ]
        )
        print(
            json.dumps(
                {
                    "feature": FEATURE,
                    "feature_tool": FEATURE_TOOL,
                    "feature_scorecard": FEATURE_SCORECARD,
                    "feature_hub_archival": FEATURE_HUB_ARCHIVAL,
                    "f116": True,
                    "f135": True,
                    "f158": True,
                    "fixture_pass": fixture_pass,
                    "zombie_demoted": zombie_demoted,
                    "good_not_demoted": good_not_demoted,
                    "good_boost": boosts.get(good),
                    "zombie_boost": boosts.get(zombie),
                    "privacy_ok": privacy_ok,
                    "good_in_fed": good_in_fed,
                    "zombie_not_fed": zombie_not_fed,
                    "tool_shielded": tool_shielded,
                    "tool_boost_ok": tool_boost,
                    "tool_in_fed": tool_in_fed,
                    "tool_outcome_fed_n": cyc.get("tool_outcome_fed_n"),
                    "tool_skills": cyc.get("tool_skills"),
                    "f135_sc_shielded": sc_shielded,
                    "f135_sc_boost": fitness_boosts(ledger).get(sc_skill),
                    "f135_sc_ops_ok": sc_ops_ok,
                    "f135_sc_privacy_ok": sc_privacy,
                    "f135_sc_ingested_n": sc_fit.get("ingested_n"),
                    "f135_sc_in_fed": sc_in_fed_out,
                    "f158_ok": f158_ok,
                    "f158_ha_gap_demoted": ha_gap_demoted,
                    "f158_ha_revived": ha_revived,
                    "f158_ha_gap_boost": ha_gap_boost,
                    "f158_ha_hit_boost": ha_hit_boost,
                    "f158_ha_util_rate": ha_ent.get("hub_archival_util_rate"),
                    "f158_ha_in_fed": ha_in_fed,
                    "f158_cycle_ingested": (cyc2.get("hub_archival_fitness") or {}).get(
                        "ingested"
                    ),
                    "demoted": sorted(demoted_set(ledger)),
                    "cycle_fed_n": cyc.get("fed_n"),
                    "ledger": str(path),
                },
                indent=2,
            )
        )
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F85 skill fitness ledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="Ingest skill-hits.json into ledger")
    pi.add_argument("--out-dir", default="")
    pi.add_argument("--hits", default="")
    pi.set_defaults(func=cmd_ingest)

    sub.add_parser("demote", help="Apply demotion thresholds").set_defaults(func=cmd_demote)
    sub.add_parser("boosts", help="Print fitness score deltas").set_defaults(func=cmd_boosts)
    sub.add_parser("status", help="Ledger summary").set_defaults(func=cmd_status)
    sub.add_parser("apply", help="JSON demoted+boosts for router").set_defaults(func=cmd_apply)
    sub.add_parser("fixture", help="Hermetic offline fixture").set_defaults(func=cmd_fixture)

    pf = sub.add_parser("federate", help="Emit skill themes to federation")
    pf.add_argument("--out", default="")
    pf.add_argument("--no-hub", action="store_true")
    pf.set_defaults(func=cmd_federate)

    pc = sub.add_parser("cycle", help="ingest → demote → federate")
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--force", action="store_true")
    pc.set_defaults(func=cmd_cycle)

    psc = sub.add_parser(
        "ingest-scorecard",
        help="F135 fold scorecard-skill-signals into fitness ledger",
    )
    psc.add_argument(
        "--file",
        default="",
        help="Optional path to scorecard-skill-signals.json",
    )
    psc.set_defaults(func=cmd_ingest_scorecard)

    pha = sub.add_parser(
        "ingest-hub-archival",
        help="F158 fold recovery hub-archival util gap/hit into fitness ledger",
    )
    pha.add_argument("--out-dir", default="")
    pha.add_argument(
        "--util",
        default="",
        help="Optional path to recovery-skill-util.json",
    )
    pha.set_defaults(func=cmd_ingest_hub_archival)

    args = p.parse_args(argv)
    return int(args.func(args))


def cmd_ingest_hub_archival(args: argparse.Namespace) -> int:
    """F158: CLI for hub-archival util → fitness ledger demote/boost."""
    root = _root()
    util = None
    out_dir = Path(args.out_dir) if args.out_dir else None
    if args.util:
        p = Path(args.util)
        if p.is_file():
            try:
                util = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    json.dumps(
                        {"feature": FEATURE_HUB_ARCHIVAL, "error": str(exc)[:120]}
                    )
                )
                return 1
    report = ingest_hub_archival_util(
        util, root=root, out_dir=out_dir, save=True
    )
    ledger = apply_demotions(load_ledger(ledger_path(root)))
    save_ledger(ledger, ledger_path(root))
    report["demoted"] = list(ledger.get("demoted") or [])
    report["hub_archival_demoted"] = list(
        (ledger.get("last_demote") or {}).get("hub_archival_demoted") or []
    )
    report["boost"] = fitness_boosts(ledger).get(HUB_ARCHIVAL_SKILL_ID)
    print(json.dumps(report, indent=2))
    return 0 if report.get("privacy_ok", True) else 1


def cmd_ingest_scorecard(args: argparse.Namespace) -> int:
    """F135: CLI for scorecard skill theme → fitness ledger."""
    root = _root()
    doc = None
    if args.file:
        p = Path(args.file)
        if p.is_file():
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(json.dumps({"feature": FEATURE_SCORECARD, "error": str(exc)[:120]}))
                return 1
    report = ingest_scorecard_skills(doc, root=root, save=True)
    # re-apply demotions so shields take effect
    ledger = apply_demotions(load_ledger(ledger_path(root)))
    save_ledger(ledger, ledger_path(root))
    report["demoted"] = list(ledger.get("demoted") or [])
    report["boosts"] = {
        k: v
        for k, v in fitness_boosts(ledger).items()
        if k in (report.get("skills") or [])
    }
    print(json.dumps(report, indent=2))
    return 0 if report.get("privacy_ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
