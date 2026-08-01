#!/usr/bin/env python3
"""F84/F114: Progressive skill router + post-run skill hit + tool-outcome scoring.

Research drivers (2026):
  - Progressive disclosure (Claude Skills / Simon Willison / HN): inject a compact
    index of all skills; load full bodies only for relevant verticals.
  - Vercel agent evals: in 56% of cases skills were never invoked when dumped
    wholesale — routing + measurement closes the loop.
  - FederatedSkill (arXiv 2606.03143): share skill *usage themes*, not full
    trajectory text, for privacy-safe collaborative evolution signals.
  - Loop Engineering: measure what you ship (skill hit rate → evolve/drop).
  - F114: Mem2Act / tool-use outcome — skills that teach CLI calls must be
    scored on agent-loop invocations, not review prose alone (F113 memory skill).

Product thesis:
  F69/F82 dump up to 8 full active skills into every prompt. As the skill vault
  grows, context bloats and relevance drops. Highest ROI: **route skills by
  changed-path extensions + theme keywords**, inject index + selected bodies,
  then **score keyword hits in the review + tool invocations in the loop** so
  self-evolution knows which skills actually fire.

Commands:
  index   — catalog active skills (id, title, triggers, always)
  select  — rank/select top-K for given paths
  inject  — progressive inject into prompt.md (replaces F69 bulk when on)
  score   — post-run skill hit rate vs review body + optional tool outcomes
  fixture — hermetic offline good/weak path routing + hit score + tool outcome
  status  — active catalog summary

Env:
  TORII_ROOT
  TORII_SKILL_ROUTER          1 (default) | 0/off
  TORII_SKILL_ROUTER_MAX         default 4 full-body skills (includes always slots)
  TORII_SKILL_ROUTER_ALWAYS      comma ids always included (optional)
  TORII_SKILL_ROUTER_ALWAYS_MAX  default 3 always full-body slots (F119 budget)
  TORII_SKILL_ROUTER_ALWAYS_PRIO comma id:priority overrides (F119)
  TORII_SKILL_COMPACT            1 (default) | 0 — F120 SkillReducer-lite body compact
  TORII_SKILL_ALWAYS_MAX_CHARS   default 480 — always skill body cap after compact
  TORII_SKILL_FULL_MAX_CHARS     default 900 — non-always selected body cap
  TORII_SKILL_ROUTER_REPLACE  1 (default) | 0 — replace F69 skills block
  TORII_SKILL_TOOL_OUTCOME    1 (default) | 0 — F114 tool-invocation hit scoring
  TORII_RECOVERY_HUB_COMPOUND 1 (default) | 0 — F125 hub recovery-util post-score → always prio
  TORII_HUB_GAP_REPROMPT      1 (default) | 0 — F126 hub gap_pressure biases F122 re-prompt
  TORII_HUB_GAP_PRESSURE_THR  default 0.34 — re-prompt idle recovery when hub gap ≥ thr
  TORII_HUB_ARCHIVAL_UTIL     1 (default) | 0 — F155 hub-archival in recovery util stack
  TORII_SKILL_ROUTER_SYNTH    1 (default) | 0 — F160 synthesize skill-router.json from always skills
  TORII_HUB_ARCHIVAL_HUB      1 (default) | 0 — F161 multi-tenant hub-archival gap pressure
  TORII_HUB_ARCHIVAL_HUB_THR  default 0.34 — F161 re-prompt/critic bias thr
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F84"
FEATURE_HUB = "F125"
FEATURE_SCORECARD_HUB = "F138"
FEATURE_HUB_ARCHIVAL_UTIL = "F155"
FEATURE_HUB_ARCHIVAL_REPROMPT = "F157"
FEATURE_ROUTER_SYNTH = "F160"
FEATURE_HUB_ARCHIVAL_HUB = "F161"
FEATURE_HUB_ARCHIVAL_HUB_INJECT = "F162"
SCHEMA = 1
MARKER_OPEN = "<!-- torii-f84-skill-router -->"
MARKER_CLOSE = "<!-- /torii-f84-skill-router -->"
F69_OPEN = "<!-- torii-f69-skills -->"
F69_CLOSE = "<!-- /torii-f69-skills -->"
HUB_MARKER_OPEN = "<!-- torii-f125-recovery-hub -->"
HUB_MARKER_CLOSE = "<!-- /torii-f125-recovery-hub -->"
SCORECARD_HUB_MARKER_OPEN = "<!-- torii-f138-scorecard-hub -->"
SCORECARD_HUB_MARKER_CLOSE = "<!-- /torii-f138-scorecard-hub -->"
HA_HUB_MARKER_OPEN = "<!-- torii-f162-hub-archival-hub -->"
HA_HUB_MARKER_CLOSE = "<!-- /torii-f162-hub-archival-hub -->"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

# Extension → theme tags for routing
EXT_THEMES: dict[str, list[str]] = {
    ".py": ["python", "pickle", "sqli", "cmdi", "secrets", "taint", "chain"],
    ".js": ["javascript", "node", "xss", "sqli", "secrets", "taint"],
    ".ts": ["typescript", "javascript", "node", "xss", "taint"],
    ".tsx": ["typescript", "javascript", "react", "xss"],
    ".jsx": ["javascript", "react", "xss"],
    ".go": ["go", "cmdi", "secrets", "taint"],
    ".rs": ["rust", "memory", "taint"],
    ".java": ["java", "sqli", "secrets", "taint"],
    ".rb": ["ruby", "sqli", "secrets"],
    ".php": ["php", "sqli", "xss", "secrets"],
    ".sh": ["shell", "cmdi", "secrets"],
    ".yaml": ["config", "secrets", "ci"],
    ".yml": ["config", "secrets", "ci"],
    ".json": ["config", "secrets"],
    ".env": ["secrets", "config"],
    ".sql": ["sqli", "database"],
    ".md": ["docs"],
    ".toml": ["config"],
    ".c": ["c", "memory", "taint"],
    ".cpp": ["cpp", "memory", "taint"],
    ".h": ["c", "memory"],
}

# Skill-id / keyword heuristics when frontmatter lacks triggers
DEFAULT_TRIGGERS: dict[str, dict[str, Any]] = {
    "skill-f74-prefer-chain-json": {
        "themes": ["taint", "chain", "python", "javascript"],
        "keywords": ["chain", "taint", "source", "sink", "candidate", "unvalidated"],
        "exts": [".py", ".js", ".ts"],
        "always": False,
    },
    "skill-f74-exploit-scenario": {
        "themes": ["exploit", "attacker", "sqli", "cmdi", "pickle", "xss"],
        "keywords": ["attacker", "trigger", "exploit", "severity", "request changes"],
        "exts": [".py", ".js", ".ts", ".go", ".java"],
        "always": False,
    },
    "skill-tool-depth-hunks": {
        "themes": ["review", "diff", "tools"],
        "keywords": ["diff", "hunk", "rg -n", "sed -n", "changed region"],
        "exts": [],
        "always": True,
    },
    "skill-preserve-deep-tools": {
        "themes": ["review", "tools", "depth"],
        "keywords": ["tool turns", "package path", "symbol", "deep"],
        "exts": [],
        "always": True,
    },
    "skill-soft-tool-nudge": {
        "themes": ["review", "tools"],
        "keywords": ["fewer, deeper", "tool turns", "blocking"],
        "exts": [],
        "always": False,
    },
    "skill-f74-path-evidence": {
        "themes": ["path", "evidence", "review"],
        "keywords": ["path:line", "deep path", "basename", "unvalidated"],
        "exts": [],
        "always": True,
    },
    # F114: adopted F112/F113 recovery skill — always full body; score via tools
    "skill-prefer-memory-cli-early": {
        "themes": ["memory", "cli", "search", "graph", "utilization", "recovery"],
        "keywords": [
            "torii.py memory",
            "torii_memory",
            "memory search",
            "memory graph",
            "utilization",
            "f106",
        ],
        "exts": [],
        "always": True,
        "always_priority": 100,
    },
    # F119: F118 dual-gate adopted product/critic — always candidates under budget
    "skill-prefer-product-cli": {
        "themes": ["product", "cli", "doctor", "status", "budget", "readiness"],
        "keywords": [
            "torii.py doctor",
            "torii.py status",
            "torii.py budget",
            "product cli",
            "doctor",
        ],
        "exts": [],
        "always": True,
        "always_priority": 90,
    },
    "skill-prefer-critic-early": {
        "themes": ["critic", "checker", "path", "evidence", "revalidate"],
        "keywords": [
            "second_agent_critic",
            "chain_revalidate",
            "path:line",
            "dual-pass",
            "unvalidated",
        ],
        "exts": [],
        "always": True,
        "always_priority": 85,
    },
    # F154: F153 hub-archival recovery — always under F119 budget (below memory, above product)
    "skill-prefer-hub-archival-early": {
        "themes": [
            "archival",
            "hub",
            "recon_warm",
            "memory",
            "multi_tenant",
            "recovery",
        ],
        "keywords": [
            "archival_memory_search",
            "hub warm",
            "recon-warm",
            "TORII_RECON_WARM_HUB_QUERY",
            "hub_boost",
            "f149",
            "f152",
            "f153",
        ],
        "exts": [],
        "always": True,
        "always_priority": 95,
    },
}

# F119: default always priority when card.always (higher = keep under ALWAYS_MAX)
ALWAYS_PRIORITY_DEFAULT: dict[str, int] = {
    "skill-prefer-memory-cli-early": 100,
    "skill-prefer-hub-archival-early": 95,  # F154
    "skill-prefer-product-cli": 90,
    "skill-prefer-critic-early": 85,
    "skill-f74-path-evidence": 70,
    "skill-tool-depth-hunks": 50,
    "skill-preserve-deep-tools": 40,
    "skill-soft-tool-nudge": 20,
}

# F114: skill success measured by tool invocations (agent-loop / logs), not prose
TOOL_OUTCOME_PROBES: dict[str, list[re.Pattern[str]]] = {
    "skill-prefer-memory-cli-early": [
        re.compile(r"torii\.py\s+memory\b", re.I),
        re.compile(r"torii_memory\.py\b", re.I),
        re.compile(r"archival_memory_search\.py\b", re.I),
        re.compile(r"memory_temporal_graph\.py\b", re.I),
    ],
    # F154/F155: hub-aware archival recovery — tool_hit requires hub-boost evidence
    # (generic memory CLI alone does not satisfy this skill's purpose)
    "skill-prefer-hub-archival-early": [
        re.compile(r"hub_boost", re.I),
        re.compile(r"TORII_RECON_WARM_HUB(?:_QUERY)?\b", re.I),
        re.compile(r"recon[-_]?warm[-_]?hub", re.I),
        re.compile(r"hub[-_]?warm[-_]?(?:theme|query|boost)", re.I),
        re.compile(r"archival_memory_search\.py[^\n]{0,80}hub|hub[^\n]{0,80}archival_memory_search", re.I),
        re.compile(r"reprompt-decide[^\n]{0,40}RECON_WARM|RECON_WARM_HUB", re.I),
    ],
    # F118: F117 product/critic skills — baseline probes (also mined into durable ledger)
    "skill-prefer-product-cli": [
        re.compile(r"torii\.py\s+doctor\b", re.I),
        re.compile(r"torii\.py\s+status\b", re.I),
        re.compile(r"torii\.py\s+budget\b", re.I),
    ],
    "skill-prefer-critic-early": [
        re.compile(r"second_agent_critic\.py\b", re.I),
        re.compile(r"chain_revalidate\.py\b", re.I),
        re.compile(r"llm_critic\.py\b", re.I),
    ],
    "skill-tool-depth-hunks": [
        re.compile(r"\brg\s+-n\b", re.I),
        re.compile(r"\bsed\s+-n\b", re.I),
        re.compile(r"\bdiff\b", re.I),
    ],
    "skill-f74-prefer-chain-json": [
        re.compile(r"taint_prefilter|chain_revalidate|chain\.json|source.?sink", re.I),
    ],
}


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SKILL_ROUTER") or "1").strip().lower()
    return raw not in _FALSEY


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def replace_f69() -> bool:
    raw = (os.environ.get("TORII_SKILL_ROUTER_REPLACE") or "1").strip().lower()
    return raw not in _FALSEY


def tool_outcome_enabled() -> bool:
    """F114: score skills by agent-loop tool invocations (default on)."""
    raw = (os.environ.get("TORII_SKILL_TOOL_OUTCOME") or "1").strip().lower()
    return raw not in _FALSEY


def always_ids_env() -> set[str]:
    raw = (os.environ.get("TORII_SKILL_ROUTER_ALWAYS") or "").strip()
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def always_max() -> int:
    """F119: max always-on full-body skills (default 3) — SkillReducer context budget."""
    return _int_env("TORII_SKILL_ROUTER_ALWAYS_MAX", 3)


def always_priority_map() -> dict[str, int]:
    """F119: skill_id → priority (higher wins always slots)."""
    out = dict(ALWAYS_PRIORITY_DEFAULT)
    raw = (os.environ.get("TORII_SKILL_ROUTER_ALWAYS_PRIO") or "").strip()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                sid, pr = part.split(":", 1)
                try:
                    out[sid.strip()] = int(pr.strip())
                except ValueError:
                    continue
            else:
                out[part] = 80
    return out


def always_priority_for(sid: str, defaults: dict[str, Any] | None = None) -> int:
    prio_map = always_priority_map()
    if sid in prio_map:
        return int(prio_map[sid])
    if defaults and "always_priority" in defaults:
        try:
            return int(defaults["always_priority"])
        except (TypeError, ValueError):
            pass
    return 10


def hub_archival_hub_enabled() -> bool:
    """F161: multi-tenant hub-archival util gap pressure compound (default on)."""
    raw = (os.environ.get("TORII_HUB_ARCHIVAL_HUB") or "1").strip().lower()
    return raw not in _FALSEY


def refine_dual_hub_enabled() -> bool:
    """F169: promoted refine dual themes → always priority + prompt inject."""
    raw = (os.environ.get("TORII_REFINE_DUAL_HUB") or "1").strip().lower()
    return raw not in _FALSEY


REFINE_DUAL_HUB_MARKER_OPEN = "<!-- torii-f169-refine-dual-hub -->"
REFINE_DUAL_HUB_MARKER_CLOSE = "<!-- /torii-f169-refine-dual-hub -->"
FEATURE_REFINE_DUAL_HUB = "F169"


def hub_archival_hub_pressure_threshold() -> float:
    """F161: re-prompt/critic bias when multi-tenant ha gap_pressure ≥ thr."""
    raw = (os.environ.get("TORII_HUB_ARCHIVAL_HUB_THR") or "0.34").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.34


def load_hub_archival_hub_signals(root: Path | None = None) -> list[dict[str, Any]]:
    """F161: privacy-safe hub-archival util signals from federation store(s)."""
    root = root or _root()
    paths = [
        root / "memory" / "federation" / "recovery-util-signals.json",
        root / "memory" / "federation" / "federated-signals.json",
        root / "memory" / "federation" / "hub-archival-util-signals.json",
    ]
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        paths.insert(0, Path(od) / "recovery-util-signals.json")
        paths.insert(0, Path(od) / "hub-archival-util-signals.json")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
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
                or "f158" in tags
                or "f161" in tags
                or "hub-archival" in theme
                or "prefer-hub-archival" in theme
                or theme == "hub-archival-util-gap"
                or theme.startswith("hub-archival")
            )
            if not is_ha:
                continue
            blob = json.dumps(s, ensure_ascii=False)
            if "/Users/" in blob or "/home/" in blob:
                continue
            key = str(s.get("id") or theme)
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
    return out


def post_score_hub_archival_hub(
    signals: list[dict[str, Any]] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """F161: multi-tenant hub-archival util themes → gap_pressure + always prio.

    Privacy: skill ids, bins, tenant counts only — no paths/commands/tenant names.
    """
    root = root or _root()
    if not hub_archival_hub_enabled():
        return {
            "feature": FEATURE_HUB_ARCHIVAL_HUB,
            "enabled": False,
            "gap_pressure": 0.0,
            "priority_deltas": {},
            "privacy_ok": True,
            "reason": "hub_archival_hub_off",
        }
    signals = signals if signals is not None else load_hub_archival_hub_signals(root)
    gap_hits = 0
    ok_hits = 0
    gap_tenants = 0
    ok_tenants = 0
    skill_scores: dict[str, dict[str, Any]] = {}

    for s in signals:
        theme = str(s.get("theme") or s.get("id") or "").lower()
        hits = max(1, int(s.get("hits") or 1))
        tenants = max(1, int(s.get("tenants") or len(s.get("tenant_hashes") or []) or 1))
        util_bin = str(s.get("util_rate_bin") or "").lower()
        tags = [str(t).lower() for t in (s.get("tags") or [])]
        is_gap = (
            util_bin == "gap"
            or "utilization_gap" in tags
            or "hub_archival_idle" in tags
            or theme in ("hub-archival-util-gap", "recovery-util-gap")
            or theme.endswith("-gap")
            or bool(s.get("hub_archival_idle"))
        )
        is_ok = (
            util_bin in ("full", "partial", "ok", "hit")
            or "util_ok" in tags
            or "hub_boost" in tags
            and not is_gap
        )
        if is_gap:
            gap_hits += hits
            gap_tenants = max(gap_tenants, tenants)
        elif is_ok:
            ok_hits += hits
            ok_tenants = max(ok_tenants, tenants)

        sid = HUB_ARCHIVAL_SKILL_ID
        # only compound into hub-archival skill priority (not generic recovery)
        if (
            HUB_ARCHIVAL_SKILL_ID in theme
            or "prefer-hub-archival" in theme
            or "hub_archival" in tags
            or is_gap
            or is_ok
        ):
            ent = skill_scores.setdefault(
                sid,
                {
                    "skill_id": sid,
                    "hits": 0,
                    "tenants": 0,
                    "tool_hits": 0,
                    "gap_hits": 0,
                    "priority_delta": 0,
                    "util_rate_bin": util_bin or ("gap" if is_gap else "hit"),
                },
            )
            ent["hits"] = int(ent["hits"]) + hits
            ent["tenants"] = max(int(ent["tenants"]), tenants)
            if is_gap:
                ent["gap_hits"] = int(ent["gap_hits"]) + hits
            else:
                tool_hits = int(s.get("tool_hits") or (hits if util_bin == "hit" else 0))
                ent["tool_hits"] = int(ent["tool_hits"]) + max(0, tool_hits)

    for sid, ent in skill_scores.items():
        t = min(4, int(ent["tenants"]))
        h = min(8, int(ent["hits"]))
        th = min(6, int(ent["tool_hits"]))
        gh = min(6, int(ent.get("gap_hits") or 0))
        # boost tool hits; mild gap pressure still keeps skill visible (need recovery)
        delta = 5 + 8 * t + 2 * h + 3 * th + 2 * gh
        ent["priority_delta"] = min(40, int(delta))

    total_sys = gap_hits + ok_hits
    gap_pressure = round(gap_hits / total_sys, 4) if total_sys else 0.0
    blob = json.dumps({"skills": skill_scores, "gap": gap_hits, "ok": ok_hits})
    privacy_ok = "/Users/" not in blob and "/home/" not in blob

    return {
        "feature": FEATURE_HUB_ARCHIVAL_HUB,
        "schema": SCHEMA,
        "enabled": True,
        "signals_n": len(signals),
        "skill_n": len(skill_scores),
        "skills": skill_scores,
        "priority_deltas": {k: v["priority_delta"] for k, v in skill_scores.items()},
        "gap_hits": gap_hits,
        "ok_hits": ok_hits,
        "gap_tenants": gap_tenants,
        "ok_tenants": ok_tenants,
        "gap_pressure": gap_pressure,
        "thr": hub_archival_hub_pressure_threshold(),
        "high": gap_pressure >= hub_archival_hub_pressure_threshold() and gap_hits >= 1,
        "privacy_ok": privacy_ok,
        "hub_ok": privacy_ok,
        "skill_id": HUB_ARCHIVAL_SKILL_ID,
    }


def recovery_hub_enabled() -> bool:
    """F125: consume federated recovery-util themes into always priority (default on)."""
    raw = (os.environ.get("TORII_RECOVERY_HUB_COMPOUND") or "1").strip().lower()
    return raw not in _FALSEY


def scorecard_hub_enabled() -> bool:
    """F138: consume federated scorecard-util themes into select priority (default on)."""
    raw = (os.environ.get("TORII_SCORECARD_HUB_COMPOUND") or "1").strip().lower()
    return raw not in _FALSEY


def _is_skill_id_theme(theme: str) -> bool:
    t = (theme or "").strip().lower()
    if not t or t in (
        "recovery-util-ok",
        "recovery-util-gap",
        "recovery_util",
        "scorecard-util-ok",
        "scorecard-util-gap",
        "scorecard-ops-active",
    ):
        return False
    if t.startswith("recovery-util-hit-") or t.startswith("scorecard-util-hit-"):
        return True
    if t.startswith("scorecard-skill-"):
        return True
    if t.startswith("skill-"):
        return True
    return False


def _skill_id_from_hub_theme(theme: str, sid: str = "") -> str:
    """Map hub signal theme/id → recovery skill id (privacy-safe ids only)."""
    raw = (theme or sid or "").strip().lower()
    raw = re.sub(r"^recovery-util-hit-", "", raw)
    raw = re.sub(r"[^a-z0-9._-]+", "-", raw)[:64]
    if not raw or raw in ("recovery-util-ok", "recovery-util-gap"):
        return ""
    if not raw.startswith("skill-"):
        # keywords may be prefer-memory-cli-early without skill- prefix
        if raw.startswith("prefer-") or raw.startswith("f"):
            raw = f"skill-{raw}"
        else:
            return ""
    if "/" in raw or ".." in raw:
        return ""
    return raw


def load_recovery_hub_signals(root: Path | None = None) -> list[dict[str, Any]]:
    """Load privacy-safe recovery util signals from federation store(s)."""
    root = root or _root()
    paths = [
        root / "memory" / "federation" / "recovery-util-signals.json",
        root / "memory" / "federation" / "federated-signals.json",
    ]
    # also OUT_DIR copy if present
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        paths.insert(0, Path(od) / "recovery-util-signals.json")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
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
            src = str(s.get("source") or "").lower()
            is_rec = (
                "recovery_util" in tags
                or "federated_skill" in tags
                and ("recovery" in theme or "recovery" in src)
                or theme.startswith("recovery-util")
                or "recovery_skill_util" in src
                or theme.startswith("skill-prefer-")
            )
            if not is_rec and not _is_skill_id_theme(theme):
                # still keep pure skill themes from fitness federate when tool_outcome
                if "tool_outcome" not in tags and "skill_hit" not in tags:
                    continue
            blob = json.dumps(s, ensure_ascii=False)
            if "/Users/" in blob or "/home/" in blob:
                continue
            key = str(s.get("id") or theme)
            if key in seen:
                # merge hits lightly
                for existing in out:
                    if str(existing.get("id") or existing.get("theme")) == key:
                        existing["hits"] = int(existing.get("hits") or 0) + int(
                            s.get("hits") or 1
                        )
                        th = list(existing.get("tenant_hashes") or [])
                        for h in s.get("tenant_hashes") or []:
                            if h not in th:
                                th.append(h)
                        if th:
                            existing["tenant_hashes"] = th[:64]
                            existing["tenants"] = len(th)
                        break
                continue
            seen.add(key)
            out.append(dict(s))
    return out


def post_score_recovery_hub(
    signals: list[dict[str, Any]] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """F125: post-score hub recovery-util themes → per-skill always priority deltas.

    Privacy: skill_id + hits + tenant counts + util bins only (no paths/commands).
    """
    root = root or _root()
    signals = signals if signals is not None else load_recovery_hub_signals(root)
    skill_scores: dict[str, dict[str, Any]] = {}
    gap_hits = 0
    ok_hits = 0
    gap_tenants = 0
    ok_tenants = 0

    for s in signals:
        theme = str(s.get("theme") or s.get("id") or "").lower()
        hits = max(1, int(s.get("hits") or 1))
        tenants = max(1, int(s.get("tenants") or len(s.get("tenant_hashes") or []) or 1))
        util_bin = str(s.get("util_rate_bin") or "").lower()
        tags = [str(t).lower() for t in (s.get("tags") or [])]

        if theme in ("recovery-util-gap",) or util_bin == "gap" or "utilization_gap" in tags:
            gap_hits += hits
            gap_tenants = max(gap_tenants, tenants)
            continue
        if theme in ("recovery-util-ok",) or util_bin in ("full", "partial", "ok"):
            if theme.startswith("recovery-util"):
                ok_hits += hits
                ok_tenants = max(ok_tenants, tenants)
                continue

        sid = _skill_id_from_hub_theme(theme, str(s.get("id") or ""))
        if not sid:
            # try keywords for prefer-* skill names
            for kw in s.get("keywords") or []:
                sid = _skill_id_from_hub_theme(str(kw))
                if sid:
                    break
        if not sid:
            continue

        ent = skill_scores.setdefault(
            sid,
            {
                "skill_id": sid,
                "hits": 0,
                "tenants": 0,
                "tool_hits": 0,
                "priority_delta": 0,
                "util_rate_bin": util_bin or "hit",
            },
        )
        ent["hits"] = int(ent["hits"]) + hits
        ent["tenants"] = max(int(ent["tenants"]), tenants)
        tool_hits = int(s.get("tool_hits") or (hits if util_bin == "hit" else 0))
        ent["tool_hits"] = int(ent["tool_hits"]) + tool_hits
        if util_bin:
            ent["util_rate_bin"] = util_bin

    # priority_delta: multi-tenant tool hits compound (cap +40)
    for sid, ent in skill_scores.items():
        t = min(4, int(ent["tenants"]))
        h = min(8, int(ent["hits"]))
        th = min(6, int(ent["tool_hits"]))
        # base 5 + 8*tenants + 2*hits + 3*tool_hits
        delta = 5 + 8 * t + 2 * h + 3 * th
        ent["priority_delta"] = min(40, int(delta))

    # systemic gap pressure (0..1) for re-prompt soft bias / inject note
    total_sys = gap_hits + ok_hits
    gap_pressure = round(gap_hits / total_sys, 4) if total_sys else 0.0

    # privacy check
    blob = json.dumps(skill_scores)
    privacy_ok = "/Users/" not in blob and "/home/" not in blob and "C:\\\\Users" not in blob

    report: dict[str, Any] = {
        "feature": FEATURE_HUB,
        "schema": SCHEMA,
        "enabled": recovery_hub_enabled(),
        "signals_n": len(signals),
        "skill_n": len(skill_scores),
        "skills": skill_scores,
        "priority_deltas": {k: v["priority_delta"] for k, v in skill_scores.items()},
        "gap_hits": gap_hits,
        "ok_hits": ok_hits,
        "gap_tenants": gap_tenants,
        "ok_tenants": ok_tenants,
        "gap_pressure": gap_pressure,
        "privacy_ok": privacy_ok,
        "hub_ok": privacy_ok and (len(skill_scores) >= 1 or ok_hits >= 1 or gap_hits >= 0),
    }
    return report


def hub_priority_delta(sid: str, hub: dict[str, Any] | None = None) -> int:
    """Always-priority bump from hub post-score for one skill id."""
    if hub is None:
        return 0
    if not hub.get("enabled", True):
        return 0
    deltas = hub.get("priority_deltas") or {}
    try:
        return int(deltas.get(sid) or 0)
    except (TypeError, ValueError):
        return 0


def load_refine_dual_hub_signals(root: Path | None = None) -> list[dict[str, Any]]:
    """F169: privacy-safe promoted refine dual + dual signals from federation."""
    root = root or _root()
    paths = [
        root / "memory" / "federation" / "promoted-refine-dual-themes.json",
        root / "memory" / "federation" / "skill-refine-dual-signals.json",
    ]
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        paths.insert(0, Path(od) / "promoted-refine-dual-themes.json")
        paths.insert(0, Path(od) / "skill-refine-dual-signals.json")
        paths.insert(0, Path(od) / "refine-dual.json")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in paths:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        # refine-dual.json single-run paper metric → synthetic signal
        if p.name == "refine-dual.json" and isinstance(data, dict):
            for sid in data.get("refined_skill_ids") or []:
                sid_s = str(sid)
                if not sid_s.startswith("skill-") or sid_s in seen:
                    continue
                seen.add(sid_s)
                out.append(
                    {
                        "id": f"run-refine-dual-{sid_s}"[:64],
                        "theme": sid_s,
                        "skill_id": sid_s,
                        "tags": [
                            "refine_dual",
                            "f167",
                            "f169",
                            "dual_pass" if data.get("refine_dual_pass") else "dual_fail",
                        ],
                        "hits": 1,
                        "tenants": 1,
                        "tool_contrib_pp": float(
                            data.get("refine_tool_contribution_pp") or 0
                        ),
                        "dual_pass": bool(data.get("refine_dual_pass")),
                        "promoted": False,
                        "source": "refine_dual_run",
                    }
                )
            continue
        sigs = data.get("signals") if isinstance(data, dict) else data
        if not isinstance(sigs, list):
            continue
        promoted_scope = "promoted" in p.name or data.get("scope") == "promoted_refine_dual_themes"
        for s in sigs:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("skill_id") or s.get("theme") or s.get("id") or "")
            if not sid.startswith("skill-"):
                continue
            key = f"{sid}|{s.get('tenant_hash') or ''}|{s.get('id') or ''}"
            if key in seen:
                continue
            seen.add(key)
            tags = [str(t).lower() for t in (s.get("tags") or [])]
            if not any(
                t in tags
                for t in (
                    "refine_dual",
                    "f167",
                    "f168",
                    "f169",
                    "promoted_refine_dual",
                    "gepa",
                )
            ) and "refine" not in str(s.get("source") or "").lower():
                if not promoted_scope:
                    continue
            ent = dict(s)
            ent["skill_id"] = sid
            ent["theme"] = sid
            if promoted_scope or "promoted_refine_dual" in tags:
                ent["promoted"] = True
            out.append(ent)
    return out


def post_score_refine_dual_hub(
    root: Path | None = None,
    *,
    signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """F169: multi-tenant promoted refine dual → always priority deltas + fail pressure.

    Privacy-safe: skill ids + contrib bins + tenant counts only.
    Promoted themes get positive priority; dual_fail pressure surfaces for critic.
    """
    root = root or _root()
    if not refine_dual_hub_enabled():
        return {
            "feature": FEATURE_REFINE_DUAL_HUB,
            "enabled": False,
            "priority_deltas": {},
            "skills": {},
            "reason": "refine_dual_hub_off",
        }
    signals = signals if signals is not None else load_refine_dual_hub_signals(root)
    skills: dict[str, dict[str, Any]] = {}
    fail_hits = 0
    ok_hits = 0
    for s in signals:
        sid = str(s.get("skill_id") or s.get("theme") or "")
        if not sid.startswith("skill-"):
            continue
        ent = skills.setdefault(
            sid,
            {
                "skill_id": sid,
                "hits": 0,
                "tenants": 0,
                "tool_contrib_pp": 0.0,
                "promoted": False,
                "dual_fail_n": 0,
                "dual_pass_n": 0,
                "priority_delta": 0,
                "util_rate_bin": "zero",
            },
        )
        ent["hits"] += max(1, int(s.get("hits") or 1))
        tenants = int(s.get("tenants") or len(s.get("tenant_hashes") or []) or 1)
        ent["tenants"] = max(int(ent["tenants"]), tenants)
        ent["tool_contrib_pp"] = max(
            float(ent["tool_contrib_pp"]), float(s.get("tool_contrib_pp") or 0)
        )
        tags = [str(t).lower() for t in (s.get("tags") or [])]
        if s.get("promoted") or "promoted_refine_dual" in tags:
            ent["promoted"] = True
        dual_pass = s.get("dual_pass")
        if dual_pass is False or "dual_fail" in tags:
            ent["dual_fail_n"] = int(ent["dual_fail_n"]) + 1
            fail_hits += 1
        elif dual_pass or "dual_pass" in tags or ent["promoted"]:
            ent["dual_pass_n"] = int(ent["dual_pass_n"]) + 1
            ok_hits += 1
        bin_ = str(s.get("util_rate_bin") or "")
        if bin_:
            ent["util_rate_bin"] = bin_

    # F171/F172: chronic dual_fail from fitness + multi-tenant decay promote → always Δprio
    # F175: dual_pass revive re-boost supersedes decay
    fitness_decay: dict[str, int] = {}
    revive_boost: dict[str, int] = {}
    try:
        fit_path = root / ".torii" / "skill-fitness.json"
        envf = (os.environ.get("TORII_SKILL_FITNESS_FILE") or "").strip()
        if envf:
            fit_path = Path(envf)
        if fit_path.is_file():
            fit = json.loads(fit_path.read_text(encoding="utf-8"))
            for sid, ent in (fit.get("skills") or {}).items():
                if not isinstance(ent, dict):
                    continue
                if ent.get("refine_dual_chronic_fail") or int(
                    ent.get("refine_priority_decay") or 0
                ) < 0:
                    decay = int(ent.get("refine_priority_decay") or -15)
                    if decay >= 0:
                        decay = -15
                    fitness_decay[str(sid)] = decay
                    se = skills.setdefault(
                        str(sid),
                        {
                            "skill_id": str(sid),
                            "hits": int(ent.get("refine_dual_selected_n") or 0),
                            "tenants": int(ent.get("multi_tenant_decay_tenants") or 0),
                            "tool_contrib_pp": float(ent.get("last_refine_tool_pp") or 0),
                            "promoted": False,
                            "dual_fail_n": int(ent.get("refine_dual_fail_n") or 0),
                            "dual_pass_n": int(ent.get("refine_dual_pass_n") or 0),
                            "priority_delta": 0,
                            "util_rate_bin": "neg",
                        },
                    )
                    se["chronic_fail"] = True
                    se["dual_fail_rate"] = float(ent.get("refine_dual_fail_rate") or 0)
                    se["fitness_decay"] = decay
                    if ent.get("multi_tenant_decay"):
                        se["multi_tenant_decay"] = True
                        se["tenants"] = max(
                            int(se.get("tenants") or 0),
                            int(ent.get("multi_tenant_decay_tenants") or 0),
                        )
        # F172: multi-tenant promoted decay themes (privacy-safe federate)
        for rel in (
            "promoted-refine-dual-decay-themes.json",
            "skill-refine-dual-decay-signals.json",
        ):
            p = root / "memory" / "federation" / rel
            if not p.is_file():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for s in data.get("signals") or []:
                if not isinstance(s, dict):
                    continue
                sid = str(s.get("skill_id") or s.get("theme") or "")
                if not sid.startswith("skill-"):
                    continue
                decay = int(s.get("decay") or -20)
                if decay >= 0:
                    decay = -20
                prev = fitness_decay.get(sid, 0)
                fitness_decay[sid] = min(prev if prev < 0 else 0, decay)
                se = skills.setdefault(
                    sid,
                    {
                        "skill_id": sid,
                        "hits": int(s.get("hits") or 1),
                        "tenants": int(s.get("tenants") or 1),
                        "tool_contrib_pp": 0.0,
                        "promoted": False,
                        "dual_fail_n": 1,
                        "dual_pass_n": 0,
                        "priority_delta": 0,
                        "util_rate_bin": "neg",
                    },
                )
                se["chronic_fail"] = True
                se["fitness_decay"] = fitness_decay[sid]
                se["multi_tenant_decay"] = "promoted" in rel or bool(
                    s.get("tenants", 0) >= 2
                )
                se["tenants"] = max(int(se.get("tenants") or 0), int(s.get("tenants") or 1))
                se["dual_fail_rate"] = max(
                    float(se.get("dual_fail_rate") or 0), float(s.get("fail_rate") or 0.67)
                )
        # F175: multi-tenant dual_pass revive supersedes chronic decay
        revive_boost: dict[str, int] = {}
        for rel in (
            "promoted-refine-dual-revive-themes.json",
            "skill-refine-dual-revive-signals.json",
        ):
            p = root / "memory" / "federation" / rel
            if not p.is_file():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for s in data.get("signals") or []:
                if not isinstance(s, dict):
                    continue
                sid = str(s.get("skill_id") or s.get("theme") or "")
                if not sid.startswith("skill-"):
                    continue
                if not (s.get("dual_pass") or "revive" in str(s.get("tags") or [])):
                    continue
                boost = int(s.get("boost") or 16)
                if boost < 8:
                    boost = 16
                if "promoted" in rel:
                    boost = max(boost, 20)
                revive_boost[sid] = max(int(revive_boost.get(sid) or 0), boost)
                # clear fitness decay for revived skills
                if sid in fitness_decay:
                    del fitness_decay[sid]
                se = skills.setdefault(
                    sid,
                    {
                        "skill_id": sid,
                        "hits": int(s.get("hits") or 1),
                        "tenants": int(s.get("tenants") or 1),
                        "tool_contrib_pp": float(s.get("tool_pp") or 0),
                        "promoted": True,
                        "dual_fail_n": 0,
                        "dual_pass_n": max(1, int(s.get("hits") or 1)),
                        "priority_delta": 0,
                        "util_rate_bin": "pos",
                    },
                )
                se["chronic_fail"] = False
                se["multi_tenant_decay"] = False
                se["multi_tenant_revive"] = "promoted" in rel or int(
                    s.get("tenants") or 0
                ) >= 2
                se["promoted"] = True
                se["dual_pass_n"] = max(int(se.get("dual_pass_n") or 0), 1)
                se["tool_contrib_pp"] = max(
                    float(se.get("tool_contrib_pp") or 0), float(s.get("tool_pp") or 0)
                )
                se["tenants"] = max(int(se.get("tenants") or 0), int(s.get("tenants") or 1))
                se["revive_boost"] = revive_boost[sid]
        # also honor local fitness ledger revive flags
        try:
            fit_path2 = root / ".torii" / "skill-fitness.json"
            envf2 = (os.environ.get("TORII_SKILL_FITNESS_FILE") or "").strip()
            if envf2:
                fit_path2 = Path(envf2)
            if fit_path2.is_file():
                fit2 = json.loads(fit_path2.read_text(encoding="utf-8"))
                for sid, ent in (fit2.get("skills") or {}).items():
                    if not isinstance(ent, dict):
                        continue
                    if ent.get("refine_dual_revived") or ent.get("multi_tenant_revive"):
                        sid_s = str(sid)
                        # F176: free-rider gate — local revive with sticky multi_tenant_decay
                        # does not full-supersede decay; only multi_tenant_revive does.
                        mt_free_rider = bool(
                            ent.get("multi_tenant_decay")
                            or ent.get("local_revive_pending_mt")
                            or ent.get("free_rider_revive_blocked")
                        ) and not ent.get("multi_tenant_revive")
                        if not mt_free_rider and sid_s in fitness_decay:
                            del fitness_decay[sid_s]
                        if mt_free_rider:
                            # soft pending boost only (F176)
                            boost = max(4, min(8, int(ent.get("hub_priority_delta") or 4)))
                        else:
                            boost = max(12, int(ent.get("hub_priority_delta") or 12))
                        revive_boost[sid_s] = max(
                            int(revive_boost.get(sid_s) or 0), boost
                        )
                        se = skills.setdefault(
                            sid_s,
                            {
                                "skill_id": sid_s,
                                "hits": int(ent.get("refine_dual_selected_n") or 1),
                                "tenants": int(
                                    ent.get("multi_tenant_revive_tenants") or 1
                                ),
                                "tool_contrib_pp": float(
                                    ent.get("last_refine_tool_pp") or 0
                                ),
                                "promoted": not mt_free_rider,
                                "dual_fail_n": 0,
                                "dual_pass_n": int(ent.get("refine_dual_pass_n") or 1),
                                "priority_delta": 0,
                                "util_rate_bin": "pos" if not mt_free_rider else "pending",
                            },
                        )
                        se["chronic_fail"] = bool(mt_free_rider)
                        se["multi_tenant_decay"] = bool(
                            mt_free_rider or ent.get("multi_tenant_decay")
                        )
                        se["multi_tenant_revive"] = bool(ent.get("multi_tenant_revive"))
                        se["local_revive_pending_mt"] = bool(
                            ent.get("local_revive_pending_mt")
                        )
                        se["free_rider_revive_blocked"] = bool(mt_free_rider)
                        se["revive_pp_blocked"] = bool(ent.get("revive_pp_blocked"))
                        se["promoted"] = (not mt_free_rider) and bool(
                            ent.get("multi_tenant_revive") or ent.get("refine_dual_revived")
                        )
                        if mt_free_rider:
                            se["promoted"] = False
                        se["revive_boost"] = revive_boost[sid_s]
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        fitness_decay = {}
        revive_boost = {}

    priority_deltas: dict[str, int] = {}
    for sid, ent in skills.items():
        delta = 0
        if ent["promoted"] and not ent.get("chronic_fail"):
            # multi-tenant promoted refine dual — keep in always budget
            delta = 20 + min(20, 4 * min(5, int(ent["tenants"])))
            if float(ent["tool_contrib_pp"]) >= 50:
                delta += 8
            elif float(ent["tool_contrib_pp"]) >= 10:
                delta += 4
        elif int(ent["dual_pass_n"]) >= 1 and float(ent["tool_contrib_pp"]) > 0:
            delta = 8 + min(10, int(float(ent["tool_contrib_pp"]) / 10))
        # dual_fail without promote does not boost
        if int(ent["dual_fail_n"]) >= 1 and not ent["promoted"]:
            delta = min(delta, 0)
        # F171: chronic dual_fail decays always priority (negative delta)
        if sid in fitness_decay and not ent.get("multi_tenant_revive"):
            delta = min(delta, int(fitness_decay[sid]))
            ent["chronic_fail"] = True
            ent["fitness_decay"] = fitness_decay[sid]
        # F175/F176: dual_pass revive re-boost supersedes decay
        # F176 free-rider: sticky multi_tenant_decay / pending MT → soft boost only
        if sid in revive_boost or ent.get("multi_tenant_revive") or ent.get("revive_boost"):
            rb = int(
                revive_boost.get(sid)
                or ent.get("revive_boost")
                or 16
            )
            free_rider = bool(
                ent.get("free_rider_revive_blocked")
                or ent.get("local_revive_pending_mt")
                or (ent.get("multi_tenant_decay") and not ent.get("multi_tenant_revive"))
            )
            if free_rider and not ent.get("multi_tenant_revive"):
                rb = min(rb, 8)
                delta = max(delta, rb)
                # keep chronic/multi_tenant flags sticky for F173 critic
                ent["chronic_fail"] = True
                ent["multi_tenant_decay"] = True
                ent["free_rider_revive_blocked"] = True
            else:
                delta = max(delta, rb)
                ent["chronic_fail"] = False
                ent["multi_tenant_decay"] = False
        # also decay when local dual_fail_n dominates dual_pass_n (run-level chronic)
        df = int(ent["dual_fail_n"])
        dp = int(ent["dual_pass_n"])
        if (
            df >= 2
            and df > dp
            and not ent.get("promoted")
            and not ent.get("multi_tenant_revive")
            and sid not in revive_boost
        ):
            delta = min(delta, -10 - min(10, df))
            ent["chronic_fail"] = True
        ent["priority_delta"] = int(delta)
        # always record non-zero deltas (including negative F171 decay)
        if delta != 0:
            priority_deltas[sid] = int(delta)

    fail_pressure = 0.0
    if fail_hits + ok_hits > 0:
        fail_pressure = round(fail_hits / max(1, fail_hits + ok_hits), 4)
    high_fail = fail_pressure >= 0.5 and fail_hits >= 1
    chronic_n = sum(1 for e in skills.values() if e.get("chronic_fail"))

    blob = json.dumps({"skills": list(skills.keys()), "deltas": priority_deltas})
    privacy_ok = "/Users/" not in blob and "/home/" not in blob

    return {
        "feature": FEATURE_REFINE_DUAL_HUB,
        "feature_decay": "F171",
        "enabled": True,
        "signals_n": len(signals),
        "skills": skills,
        "priority_deltas": priority_deltas,
        "ok_hits": ok_hits,
        "fail_hits": fail_hits,
        "fail_pressure": fail_pressure,
        "high_fail": high_fail,
        "chronic_fail_n": chronic_n,
        "fitness_decay": fitness_decay,
        "privacy_ok": privacy_ok,
        "hub_ok": privacy_ok and (len(priority_deltas) >= 1 or fail_hits >= 0),
    }


def render_refine_dual_hub_section(hub: dict[str, Any]) -> str:
    """F169: privacy-safe prompt section for promoted refine dual themes."""
    lines = [
        REFINE_DUAL_HUB_MARKER_OPEN,
        "## Federated GEPA refine dual (F168/F169 hub)",
        "",
        "Cross-tenant refine dual outcomes (skill ids + contrib bins only; no bodies/paths):",
    ]
    skills = hub.get("skills") or {}
    if skills:
        ranked = sorted(
            skills.values(),
            key=lambda e: (-int(e.get("priority_delta") or 0), str(e.get("skill_id"))),
        )
        for e in ranked[:6]:
            promo = "promoted" if e.get("promoted") else "local"
            lines.append(
                f"- `{e.get('skill_id')}`: {promo} hits={e.get('hits')} "
                f"tenants={e.get('tenants')} tool_pp={e.get('tool_contrib_pp')} "
                f"Δprio={int(e.get('priority_delta') or 0):+d} fail_n={e.get('dual_fail_n')}"
                + (" chronic_decay" if e.get("chronic_fail") else "")
                + (
                    " free_rider_pending_mt"
                    if e.get("free_rider_revive_blocked") or e.get("local_revive_pending_mt")
                    else ""
                )
            )
    else:
        lines.append(
            "- (no promoted refine dual themes yet — keep hub_boost tools when GEPA refine is active)"
        )
    if int(hub.get("chronic_fail_n") or 0) >= 1:
        lines.append(
            f"- **F171 chronic dual_fail decay** on {int(hub.get('chronic_fail_n') or 0)} skill(s) — "
            "always budget demotes until hub_boost tools recover contribution_pp."
        )
    free_n = sum(
        1
        for e in (skills.values() if isinstance(skills, dict) else [])
        if isinstance(e, dict)
        and (
            e.get("free_rider_revive_blocked")
            or e.get("local_revive_pending_mt")
            or (e.get("multi_tenant_decay") and not e.get("multi_tenant_revive"))
        )
    )
    if free_n >= 1:
        lines.append(
            f"- **F176 free-rider revive gate** on {free_n} skill(s) — local dual_pass alone "
            "cannot clear multi-tenant decay; wait for multi-tenant revive promote before full always re-boost."
        )
    pp_n = sum(
        1
        for e in (skills.values() if isinstance(skills, dict) else [])
        if isinstance(e, dict) and e.get("revive_pp_blocked")
    )
    # also surface from fitness ledger via hub skills util_rate_bin pending already
    if pp_n >= 1:
        lines.append(
            f"- **F177 revive contribution_pp floor** on {pp_n} skill(s) — dual_pass without "
            "min tool_pp does not re-enter always budget (SkillOpt validation gate)."
        )
    if hub.get("high_fail"):
        lines.append(
            f"- **Refine dual fail_pressure={float(hub.get('fail_pressure') or 0):.2f}** — "
            "do not APPROVE while refined recovery skills idle hub_boost / archival tools."
        )
    elif int(hub.get("ok_hits") or 0) >= 1:
        lines.append(
            "- Promoted/positive refine dual — fire archival hub_boost tools early (F165 body)."
        )
    lines.append(REFINE_DUAL_HUB_MARKER_CLOSE)
    return "\n".join(lines) + "\n"


def inject_refine_dual_hub_into_prompt(
    prompt: Path,
    hub: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """F169: inject/replace promoted refine dual hub section into prompt."""
    root = root or _root()
    hub = hub if hub is not None else post_score_refine_dual_hub(root=root)
    if not refine_dual_hub_enabled():
        return {
            "feature": FEATURE_REFINE_DUAL_HUB,
            "injected": 0,
            "reason": "off",
            "hub": hub,
        }
    if int(hub.get("signals_n") or 0) < 1 and not hub.get("high_fail"):
        return {
            "feature": FEATURE_REFINE_DUAL_HUB,
            "injected": 0,
            "reason": "no_signals",
            "hub": hub,
        }
    section = render_refine_dual_hub_section(hub)
    try:
        original = prompt.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "feature": FEATURE_REFINE_DUAL_HUB,
            "injected": 0,
            "error": str(exc)[:120],
        }
    if REFINE_DUAL_HUB_MARKER_OPEN in original:
        new = re.sub(
            rf"{re.escape(REFINE_DUAL_HUB_MARKER_OPEN)}.*?{re.escape(REFINE_DUAL_HUB_MARKER_CLOSE)}\n?",
            section,
            original,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # place after hub-archival hub section if present
        if "<!-- /torii-f162-hub-archival-hub -->" in original:
            new = original.replace(
                "<!-- /torii-f162-hub-archival-hub -->",
                "<!-- /torii-f162-hub-archival-hub -->\n" + section,
                1,
            )
        else:
            new = original.rstrip() + "\n\n" + section
    try:
        prompt.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    except OSError as exc:
        return {
            "feature": FEATURE_REFINE_DUAL_HUB,
            "injected": 0,
            "error": str(exc)[:120],
        }
    return {
        "feature": FEATURE_REFINE_DUAL_HUB,
        "injected": 1,
        "chars": len(section),
        "priority_deltas": hub.get("priority_deltas"),
        "fail_pressure": hub.get("fail_pressure"),
        "hub": hub,
    }


def load_scorecard_hub_signals(root: Path | None = None) -> list[dict[str, Any]]:
    """Load privacy-safe scorecard util/ops signals from federation store(s)."""
    root = root or _root()
    paths = [
        root / "memory" / "federation" / "scorecard-util-signals.json",
        root / "memory" / "federation" / "scorecard-skill-signals.json",
    ]
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        paths.insert(0, Path(od) / "scorecard-util-signals.json")
        paths.insert(1, Path(od) / "scorecard-skill-signals.json")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in paths:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sigs = data.get("signals") if isinstance(data, dict) else data
        # F134 skill_ids without per-skill signal body
        extra_ids = []
        if isinstance(data, dict):
            extra_ids = list(data.get("skill_ids") or [])
        if not isinstance(sigs, list):
            sigs = []
        for s in list(sigs):
            if not isinstance(s, dict):
                continue
            tags = [str(t).lower() for t in (s.get("tags") or [])]
            theme = str(s.get("theme") or s.get("id") or "").lower()
            src = str(s.get("source") or "").lower()
            is_sc = (
                "scorecard_util" in tags
                or "scorecard_ops" in tags
                or "f136" in tags
                or "f134" in tags
                or "f138" in tags
                or theme.startswith("scorecard-")
                or "scorecard" in src
                or is_scorecard_skill_id(theme)
                or any(is_scorecard_skill_id(str(k)) for k in (s.get("keywords") or []))
            )
            if not is_sc and not _is_skill_id_theme(theme):
                continue
            blob = json.dumps(s, ensure_ascii=False)
            if "/Users/" in blob or "/home/" in blob:
                continue
            key = str(s.get("id") or theme)
            if key in seen:
                for existing in out:
                    if str(existing.get("id") or existing.get("theme")) == key:
                        existing["hits"] = int(existing.get("hits") or 0) + int(
                            s.get("hits") or 1
                        )
                        th = list(existing.get("tenant_hashes") or [])
                        for h in s.get("tenant_hashes") or []:
                            if h not in th:
                                th.append(h)
                        if th:
                            existing["tenant_hashes"] = th[:64]
                            existing["tenants"] = len(th)
                        break
                continue
            seen.add(key)
            out.append(dict(s))
        for sid in extra_ids:
            sid_s = str(sid).strip()
            if not is_scorecard_skill_id(sid_s) or sid_s in seen:
                continue
            seen.add(sid_s)
            out.append(
                {
                    "id": f"scorecard-skill-{sid_s}"[:64],
                    "theme": sid_s,
                    "tags": ["scorecard_ops", "f134", "f138", "federated_skill"],
                    "hits": 1,
                    "tool_hits": 1,
                    "source": "scorecard_skill_adopt",
                    "util_rate_bin": "hit",
                    "tenants": 1,
                }
            )
    return out


def post_score_scorecard_hub(
    signals: list[dict[str, Any]] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """F138: post-score hub scorecard-util themes → per-skill select priority deltas.

    Privacy: skill_id + hits + tenant counts + util bins only (no paths/commands).
    Mirrors F125 recovery hub compound for F136/F134 scorecard ops skills.
    """
    root = root or _root()
    signals = signals if signals is not None else load_scorecard_hub_signals(root)
    skill_scores: dict[str, dict[str, Any]] = {}
    gap_hits = 0
    ok_hits = 0
    gap_tenants = 0
    ok_tenants = 0

    for s in signals:
        theme = str(s.get("theme") or s.get("id") or "").lower()
        hits = max(1, int(s.get("hits") or 1))
        tenants = max(1, int(s.get("tenants") or len(s.get("tenant_hashes") or []) or 1))
        util_bin = str(s.get("util_rate_bin") or "").lower()
        tags = [str(t).lower() for t in (s.get("tags") or [])]

        if (
            theme in ("scorecard-util-gap",)
            or util_bin == "gap"
            or "utilization_gap" in tags
        ):
            gap_hits += hits
            gap_tenants = max(gap_tenants, tenants)
            continue
        if theme in ("scorecard-util-ok", "scorecard-ops-active") or util_bin in (
            "full",
            "partial",
            "ok",
        ):
            if theme.startswith("scorecard-util") or theme == "scorecard-ops-active":
                ok_hits += hits
                ok_tenants = max(ok_tenants, tenants)
                # scorecard-ops-active may carry skill_n only — no per-skill
                if theme == "scorecard-ops-active":
                    continue
                # util-ok aggregate: continue after counting
                if theme == "scorecard-util-ok":
                    continue

        sid = _skill_id_from_hub_theme(theme, str(s.get("id") or ""))
        # strip scorecard-skill- / scorecard-util-hit- prefixes
        if not sid:
            raw = re.sub(
                r"^(scorecard-util-hit-|scorecard-skill-)",
                "",
                theme,
            )
            sid = _skill_id_from_hub_theme(raw, raw)
        if not sid:
            for kw in s.get("keywords") or []:
                sid = _skill_id_from_hub_theme(str(kw))
                if sid and is_scorecard_skill_id(sid):
                    break
                sid = ""
        if not sid or not is_scorecard_skill_id(sid):
            # allow known scorecard ids only
            if sid and sid.startswith("skill-prefer-") and any(
                x in sid
                for x in (
                    "scorecard",
                    "demote-eval",
                    "memory-util",
                    "hub-gap",
                    "dual-compound",
                    "workflow",
                    "recovery-skills",
                )
            ):
                pass
            else:
                continue

        ent = skill_scores.setdefault(
            sid,
            {
                "skill_id": sid,
                "hits": 0,
                "tenants": 0,
                "tool_hits": 0,
                "priority_delta": 0,
                "util_rate_bin": util_bin or "hit",
            },
        )
        ent["hits"] = int(ent["hits"]) + hits
        ent["tenants"] = max(int(ent["tenants"]), tenants)
        tool_hits = int(s.get("tool_hits") or (hits if util_bin in ("hit", "full") else 0))
        ent["tool_hits"] = int(ent["tool_hits"]) + max(1, tool_hits)
        if util_bin:
            ent["util_rate_bin"] = util_bin

    for sid, ent in skill_scores.items():
        t = min(4, int(ent["tenants"]))
        h = min(8, int(ent["hits"]))
        th = min(6, int(ent["tool_hits"]))
        delta = 5 + 8 * t + 2 * h + 3 * th
        ent["priority_delta"] = min(40, int(delta))

    total_sys = gap_hits + ok_hits
    gap_pressure = round(gap_hits / total_sys, 4) if total_sys else 0.0

    blob = json.dumps(skill_scores)
    privacy_ok = (
        "/Users/" not in blob
        and "/home/" not in blob
        and "C:\\\\Users" not in blob
    )

    report: dict[str, Any] = {
        "feature": FEATURE_SCORECARD_HUB,
        "schema": SCHEMA,
        "enabled": scorecard_hub_enabled(),
        "signals_n": len(signals),
        "skill_n": len(skill_scores),
        "skills": skill_scores,
        "priority_deltas": {k: v["priority_delta"] for k, v in skill_scores.items()},
        "gap_hits": gap_hits,
        "ok_hits": ok_hits,
        "gap_tenants": gap_tenants,
        "ok_tenants": ok_tenants,
        "gap_pressure": gap_pressure,
        "privacy_ok": privacy_ok,
        "hub_ok": privacy_ok
        and (len(skill_scores) >= 1 or ok_hits >= 1 or gap_hits >= 0),
    }
    return report


def render_scorecard_hub_section(hub: dict[str, Any]) -> str:
    """Privacy-safe prompt section: hub scorecard util themes (ids + bins only)."""
    lines = [
        SCORECARD_HUB_MARKER_OPEN,
        "## Federated scorecard util (F138 hub compound)",
        "",
        "Cross-tenant scorecard-gap ops tool outcomes (skill ids + util bins only; no paths):",
    ]
    skills = hub.get("skills") or {}
    if skills:
        ranked = sorted(
            skills.values(),
            key=lambda e: (-int(e.get("priority_delta") or 0), str(e.get("skill_id"))),
        )
        for e in ranked[:8]:
            lines.append(
                f"- `{e.get('skill_id')}`: hits={e.get('hits')} tenants={e.get('tenants')} "
                f"tool_hits={e.get('tool_hits')} Δprio=+{e.get('priority_delta')} "
                f"bin={e.get('util_rate_bin')}"
            )
    else:
        lines.append(
            "- (no hub scorecard skill themes yet — local scorecard adopt applies)"
        )
    gp = float(hub.get("gap_pressure") or 0)
    if gp >= 0.34:
        lines.append(
            f"- **Hub scorecard util gap pressure={gp:.2f}** — prefer early "
            "doctor/scorecard/demote-eval CLI calls when ops skills are in scope."
        )
    elif int(hub.get("ok_hits") or 0) >= 1:
        lines.append(
            f"- Hub scorecard util_ok hits={hub.get('ok_hits')} — keep ops CLIs in the loop."
        )
    lines.append(SCORECARD_HUB_MARKER_CLOSE)
    return "\n".join(lines) + "\n"


def inject_scorecard_hub_into_prompt(
    prompt: Path,
    hub: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Inject/replace F138 hub scorecard section in prompt.md."""
    root = root or _root()
    hub = hub if hub is not None else post_score_scorecard_hub(root=root)
    if not scorecard_hub_enabled():
        return {
            "feature": FEATURE_SCORECARD_HUB,
            "injected": 0,
            "reason": "off",
            "hub": hub,
        }
    section = render_scorecard_hub_section(hub)
    try:
        original = prompt.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "feature": FEATURE_SCORECARD_HUB,
            "injected": 0,
            "error": str(exc)[:120],
        }
    if SCORECARD_HUB_MARKER_OPEN in original:
        new = re.sub(
            rf"{re.escape(SCORECARD_HUB_MARKER_OPEN)}.*?"
            rf"{re.escape(SCORECARD_HUB_MARKER_CLOSE)}\n?",
            section,
            original,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # place after recovery hub or skill router block
        if HUB_MARKER_CLOSE in original:
            new = original.replace(
                HUB_MARKER_CLOSE, HUB_MARKER_CLOSE + "\n\n" + section, 1
            )
        elif MARKER_CLOSE in original:
            new = original.replace(MARKER_CLOSE, MARKER_CLOSE + "\n\n" + section, 1)
        else:
            marker = "## PR metadata"
            if marker in original:
                new = original.replace(marker, section + "\n" + marker, 1)
            else:
                new = section + "\n" + original
    try:
        prompt.write_text(new, encoding="utf-8")
    except OSError as exc:
        return {
            "feature": FEATURE_SCORECARD_HUB,
            "injected": 0,
            "error": str(exc)[:120],
        }
    return {
        "feature": FEATURE_SCORECARD_HUB,
        "injected": 1,
        "chars": len(section),
        "skill_n": int(hub.get("skill_n") or 0),
        "gap_pressure": hub.get("gap_pressure"),
        "privacy_ok": hub.get("privacy_ok"),
    }


def render_recovery_hub_section(hub: dict[str, Any]) -> str:
    """Privacy-safe prompt section: hub recovery util themes (ids + bins only)."""
    lines = [
        HUB_MARKER_OPEN,
        "## Federated recovery util (F125 hub compound)",
        "",
        "Cross-tenant recovery tool outcomes (skill ids + util bins only; no paths):",
    ]
    skills = hub.get("skills") or {}
    if skills:
        ranked = sorted(
            skills.values(),
            key=lambda e: (-int(e.get("priority_delta") or 0), str(e.get("skill_id"))),
        )
        for e in ranked[:8]:
            lines.append(
                f"- `{e.get('skill_id')}`: hits={e.get('hits')} tenants={e.get('tenants')} "
                f"tool_hits={e.get('tool_hits')} Δprio=+{e.get('priority_delta')} "
                f"bin={e.get('util_rate_bin')}"
            )
    else:
        lines.append("- (no hub recovery skill themes yet — local always budget applies)")
    gp = float(hub.get("gap_pressure") or 0)
    if gp >= 0.34:
        lines.append(
            f"- **Hub gap pressure={gp:.2f}** — prefer early recovery CLI tool calls "
            "(memory/doctor/critic) before finalizing."
        )
    elif int(hub.get("ok_hits") or 0) >= 1:
        lines.append(
            f"- Hub util_ok hits={hub.get('ok_hits')} — keep recovery tools in the loop."
        )
    lines.append(HUB_MARKER_CLOSE)
    return "\n".join(lines) + "\n"


def inject_recovery_hub_into_prompt(
    prompt: Path,
    hub: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Inject/replace F125 hub recovery section in prompt.md."""
    root = root or _root()
    hub = hub if hub is not None else post_score_recovery_hub(root=root)
    if not recovery_hub_enabled():
        return {"feature": FEATURE_HUB, "injected": 0, "reason": "off", "hub": hub}
    section = render_recovery_hub_section(hub)
    try:
        original = prompt.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"feature": FEATURE_HUB, "injected": 0, "error": str(exc)[:120]}
    if HUB_MARKER_OPEN in original:
        new = re.sub(
            rf"{re.escape(HUB_MARKER_OPEN)}.*?{re.escape(HUB_MARKER_CLOSE)}\n?",
            section,
            original,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # place after skill router block when present
        if MARKER_CLOSE in original:
            new = original.replace(MARKER_CLOSE, MARKER_CLOSE + "\n\n" + section, 1)
        else:
            marker = "## PR metadata"
            if marker in original:
                new = original.replace(marker, section + "\n" + marker, 1)
            else:
                new = original.rstrip() + "\n\n" + section
    prompt.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    # artifact
    od = (os.environ.get("OUT_DIR") or "").strip()
    art = None
    if od:
        try:
            p = Path(od) / "recovery-hub-score.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(hub, indent=2) + "\n", encoding="utf-8")
            art = str(p)
        except OSError:
            pass
    return {
        "feature": FEATURE_HUB,
        "injected": 1,
        "skill_n": hub.get("skill_n"),
        "gap_pressure": hub.get("gap_pressure"),
        "privacy_ok": hub.get("privacy_ok"),
        "artifact": art,
        "hub": hub,
    }


def render_hub_archival_hub_section(hub: dict[str, Any]) -> str:
    """F162: privacy-safe prompt section for multi-tenant hub-archival util pressure."""
    gp = float(hub.get("gap_pressure") or 0)
    thr = float(hub.get("thr") or hub_archival_hub_pressure_threshold())
    high = bool(hub.get("high")) or gp >= thr
    lines = [
        HA_HUB_MARKER_OPEN,
        "## Federated hub-archival util (F161/F162 hub pressure)",
        "",
        "Cross-tenant hub-archival tool outcomes (skill ids + util bins only; no paths):",
    ]
    skills = hub.get("skills") or {}
    if skills:
        ranked = sorted(
            skills.values(),
            key=lambda e: (-int(e.get("priority_delta") or 0), str(e.get("skill_id"))),
        )
        for e in ranked[:6]:
            lines.append(
                f"- `{e.get('skill_id')}`: hits={e.get('hits')} tenants={e.get('tenants')} "
                f"tool_hits={e.get('tool_hits')} gap_hits={e.get('gap_hits')} "
                f"Δprio=+{e.get('priority_delta')} bin={e.get('util_rate_bin')}"
            )
    else:
        lines.append(
            "- (no hub-archival util themes yet — keep archival hub_boost when multi-tenant heat rises)"
        )
    if high:
        lines.append(
            f"- **Hub-archival gap pressure={gp:.2f}** (thr={thr:.2f}) — call "
            "`archival_memory_search` with hub warm themes so `hub_boost` evidence appears "
            "before finalizing (generic memory CLI is not enough)."
        )
    elif int(hub.get("ok_hits") or 0) >= 1:
        lines.append(
            f"- Hub-archival util_ok hits={hub.get('ok_hits')} — keep hub_boost archival in the loop."
        )
    lines.append(HA_HUB_MARKER_CLOSE)
    return "\n".join(lines) + "\n"


def inject_hub_archival_hub_into_prompt(
    prompt: Path,
    hub: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """F162: inject/replace multi-tenant hub-archival util pressure section."""
    root = root or _root()
    hub = hub if hub is not None else post_score_hub_archival_hub(root=root)
    if not hub_archival_hub_enabled():
        return {
            "feature": FEATURE_HUB_ARCHIVAL_HUB_INJECT,
            "injected": 0,
            "reason": "off",
            "hub": hub,
        }
    # skip empty noise when no signals and not high
    if int(hub.get("signals_n") or 0) < 1 and not hub.get("high"):
        return {
            "feature": FEATURE_HUB_ARCHIVAL_HUB_INJECT,
            "injected": 0,
            "reason": "no_signals",
            "hub": hub,
            "gap_pressure": hub.get("gap_pressure"),
        }
    section = render_hub_archival_hub_section(hub)
    try:
        original = prompt.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "feature": FEATURE_HUB_ARCHIVAL_HUB_INJECT,
            "injected": 0,
            "error": str(exc)[:120],
        }
    if HA_HUB_MARKER_OPEN in original:
        new = re.sub(
            rf"{re.escape(HA_HUB_MARKER_OPEN)}.*?{re.escape(HA_HUB_MARKER_CLOSE)}\n?",
            section,
            original,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # place after F125 recovery hub or skill router block
        if HUB_MARKER_CLOSE in original:
            new = original.replace(
                HUB_MARKER_CLOSE, HUB_MARKER_CLOSE + "\n\n" + section, 1
            )
        elif MARKER_CLOSE in original:
            new = original.replace(MARKER_CLOSE, MARKER_CLOSE + "\n\n" + section, 1)
        else:
            marker = "## PR metadata"
            if marker in original:
                new = original.replace(marker, section + "\n" + marker, 1)
            else:
                new = original.rstrip() + "\n\n" + section
    # privacy assert
    if "/Users/" in section or "/home/" in section:
        return {
            "feature": FEATURE_HUB_ARCHIVAL_HUB_INJECT,
            "injected": 0,
            "reason": "privacy_block",
            "hub": hub,
        }
    prompt.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    od = (os.environ.get("OUT_DIR") or "").strip()
    art = None
    if od:
        try:
            p = Path(od) / "hub-archival-hub-score.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(hub, indent=2) + "\n", encoding="utf-8")
            art = str(p)
        except OSError:
            pass
    return {
        "feature": FEATURE_HUB_ARCHIVAL_HUB_INJECT,
        "feature_hub": FEATURE_HUB_ARCHIVAL_HUB,
        "injected": 1,
        "gap_pressure": hub.get("gap_pressure"),
        "high": hub.get("high"),
        "skill_n": hub.get("skill_n"),
        "privacy_ok": hub.get("privacy_ok"),
        "artifact": art,
        "hub": hub,
    }


def active_skills_dir(root: Path | None = None) -> Path:
    return (root or _root()) / "agent" / "skills" / "active"


def list_active_skills(root: Path | None = None) -> list[Path]:
    d = active_skills_dir(root)
    if not d.is_dir():
        return []
    return sorted(
        p for p in d.glob("*.md") if p.is_file() and p.name != "README.md"
    )


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"(?s)^---\n(.*?)\n---\n(.*)$", text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta, m.group(2)


def _skill_id_from_path(p: Path, meta: dict[str, str]) -> str:
    return (meta.get("id") or p.stem).strip()


def _extract_keywords(body: str, limit: int = 12) -> list[str]:
    # Prefer bold/code tokens and multi-word security terms
    kws: list[str] = []
    for m in re.finditer(r"\*\*([^*]{3,40})\*\*", body):
        kws.append(m.group(1).strip().lower())
    for m in re.finditer(r"`([^`]{3,40})`", body):
        kws.append(m.group(1).strip().lower())
    # common security tokens present in body
    for tok in (
        "path:line",
        "taint",
        "chain",
        "source",
        "sink",
        "attacker",
        "exploit",
        "diff",
        "hunk",
        "unvalidated",
        "severity",
        "cwe",
        "pickle",
        "sqli",
        "cmdi",
        "secrets",
    ):
        if tok in body.lower() and tok not in kws:
            kws.append(tok)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for k in kws:
        k2 = k.strip().lower()
        if k2 and k2 not in seen:
            seen.add(k2)
            out.append(k2)
        if len(out) >= limit:
            break
    return out


@dataclass
class SkillCard:
    id: str
    path: str
    title: str
    themes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    exts: list[str] = field(default_factory=list)
    always: bool = False
    always_priority: int = 10
    body: str = ""
    chars: int = 0


def build_card(path: Path) -> SkillCard:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(raw)
    sid = _skill_id_from_path(path, meta)
    title = meta.get("title") or sid
    defaults = DEFAULT_TRIGGERS.get(sid, {})
    themes = [t.strip().lower() for t in (meta.get("themes") or "").split(",") if t.strip()]
    if not themes:
        themes = list(defaults.get("themes") or [])
    # free-form triggers: "python,taint"
    for key in ("triggers", "tags", "signal"):
        if meta.get(key):
            for part in re.split(r"[|,\s]+", meta[key]):
                p = part.strip().lower()
                if p and p not in themes:
                    themes.append(p)
    kws = _extract_keywords(body)
    for extra in defaults.get("keywords") or []:
        if extra.lower() not in kws:
            kws.append(extra.lower())
    exts = list(defaults.get("exts") or [])
    if meta.get("exts"):
        for e in meta["exts"].split(","):
            e = e.strip()
            if e and not e.startswith("."):
                e = "." + e
            if e and e not in exts:
                exts.append(e)
    always = bool(defaults.get("always"))
    if meta.get("always", "").lower() in ("1", "true", "yes"):
        always = True
    if sid in always_ids_env():
        always = True
    prio = always_priority_for(sid, defaults)
    if meta.get("always_priority", "").strip().isdigit():
        prio = int(meta["always_priority"].strip())
    body_clean = body.strip()
    return SkillCard(
        id=sid,
        path=str(path),
        title=title,
        themes=themes,
        keywords=kws[:16],
        exts=exts,
        always=always,
        always_priority=prio,
        body=body_clean,
        chars=len(body_clean),
    )


def catalog(root: Path | None = None) -> list[SkillCard]:
    return [build_card(p) for p in list_active_skills(root)]


def paths_from_args(
    paths: list[str] | None = None,
    paths_file: str | None = None,
    pr_json: str | None = None,
) -> list[str]:
    out: list[str] = []
    if paths:
        out.extend(paths)
    if paths_file:
        pf = Path(paths_file)
        if pf.is_file():
            for line in pf.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    out.append(line)
    if pr_json:
        pj = Path(pr_json)
        if pj.is_file():
            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
                files = data.get("files") or []
                for f in files:
                    if isinstance(f, dict):
                        p = f.get("path") or f.get("filename") or ""
                        if p:
                            out.append(str(p))
                    elif isinstance(f, str):
                        out.append(f)
            except (json.JSONDecodeError, OSError):
                pass
    # env fallbacks used by assemble-context
    for envk in ("FILES_PATH", "OUT_DIR"):
        if envk == "FILES_PATH":
            fp = (os.environ.get("FILES_PATH") or "").strip()
            if fp and Path(fp).is_file():
                for line in Path(fp).read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if line:
                        out.append(line)
        elif envk == "OUT_DIR":
            od = (os.environ.get("OUT_DIR") or "").strip()
            if od:
                for name in ("files.txt", "pr.json"):
                    cand = Path(od) / name
                    if cand.name == "files.txt" and cand.is_file():
                        for line in cand.read_text(encoding="utf-8", errors="replace").splitlines():
                            line = line.strip()
                            if line:
                                out.append(line)
                    elif cand.name == "pr.json" and cand.is_file() and not out:
                        out.extend(paths_from_args(pr_json=str(cand)))
    # de-dupe
    seen: set[str] = set()
    uniq: list[str] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def themes_from_paths(paths: list[str]) -> set[str]:
    themes: set[str] = set()
    exts_seen: set[str] = set()
    for p in paths:
        ext = Path(p).suffix.lower()
        if ext:
            exts_seen.add(ext)
            for t in EXT_THEMES.get(ext, []):
                themes.add(t)
        low = p.lower()
        for tok in (
            "test",
            "secret",
            "auth",
            "sql",
            "pickle",
            "cmd",
            "shell",
            "xss",
            "taint",
            "workflow",
            "ci",
        ):
            if tok in low:
                themes.add(tok if tok != "cmd" else "cmdi")
                if tok == "secret":
                    themes.add("secrets")
                if tok == "sql":
                    themes.add("sqli")
                if tok == "pickle":
                    themes.add("python")
    if not themes:
        themes.add("review")
    themes.add("review")
    themes.add("tools")
    return themes


def _load_fitness() -> tuple[dict[str, float], set[str]]:
    """F85: optional fitness boosts + demoted set from skill_fitness ledger."""
    raw = (os.environ.get("TORII_SKILL_FITNESS") or "1").strip().lower()
    if raw in _FALSEY:
        return {}, set()
    try:
        # import sibling module without requiring package install
        import importlib.util

        path = Path(__file__).resolve().parent / "skill_fitness.py"
        if not path.is_file():
            return {}, set()
        spec = importlib.util.spec_from_file_location("skill_fitness", path)
        if spec is None or spec.loader is None:
            return {}, set()
        mod = importlib.util.module_from_spec(spec)
        # register for dataclasses safety
        import sys as _sys

        _sys.modules.setdefault("skill_fitness", mod)
        spec.loader.exec_module(mod)
        if not mod.enabled():
            return {}, set()
        ledger = mod.load_ledger()
        return mod.fitness_boosts(ledger), mod.demoted_set(ledger)
    except Exception:
        return {}, set()


def _load_attribution() -> tuple[dict[str, float], set[str]]:
    """F89: contribution boosts + free-rider skip set from skill_attribution ledger."""
    raw = (os.environ.get("TORII_SKILL_ATTRIBUTION") or "1").strip().lower()
    if raw in _FALSEY:
        return {}, set()
    # allow disabling router-side only
    raw_r = (os.environ.get("TORII_SKILL_ATTR_ROUTER") or "1").strip().lower()
    if raw_r in _FALSEY:
        return {}, set()
    try:
        import importlib.util
        import sys as _sys

        path = Path(__file__).resolve().parent / "skill_attribution.py"
        if not path.is_file():
            return {}, set()
        if "skill_attribution" in _sys.modules:
            mod = _sys.modules["skill_attribution"]
        else:
            spec = importlib.util.spec_from_file_location("skill_attribution", path)
            if spec is None or spec.loader is None:
                return {}, set()
            mod = importlib.util.module_from_spec(spec)
            _sys.modules["skill_attribution"] = mod
            spec.loader.exec_module(mod)
        if not mod.enabled():
            return {}, set()
        ledger = mod.load_ledger()
        return mod.router_boosts(ledger), mod.free_rider_set(ledger)
    except Exception:
        return {}, set()


def score_skill(
    card: SkillCard,
    path_themes: set[str],
    paths: list[str],
    *,
    fitness_boost: float = 0.0,
    attr_boost: float = 0.0,
    force_not_always: bool = False,
) -> float:
    # Budgeted always → top rank; deferred always (F119) compete on themes/tools only
    if card.always and not force_not_always:
        return 1000.0
    score = 0.0
    if card.always and force_not_always:
        # soft residual for deferred always (still prefer recovery over noise)
        score += min(8.0, float(card.always_priority or 0) / 20.0)
    for t in card.themes:
        if t in path_themes:
            score += 3.0
    path_exts = {Path(p).suffix.lower() for p in paths if Path(p).suffix}
    for e in card.exts:
        if e in path_exts:
            score += 2.0
    # basename keyword soft match
    blob = " ".join(paths).lower()
    for kw in card.keywords[:8]:
        if len(kw) >= 4 and kw in blob:
            score += 0.5
    # slight preference for f74 security skills when any code ext present
    code_exts = path_exts - {".md", ".txt", ".rst"}
    if code_exts and card.id.startswith("skill-f74"):
        score += 1.0
    # F85 fitness from historical hit rates
    score += float(fitness_boost or 0.0)
    # F89 attribution contribution ranking
    score += float(attr_boost or 0.0)
    return score


def select_skills(
    cards: list[SkillCard],
    paths: list[str],
    max_full: int | None = None,
    max_always: int | None = None,
    root: Path | None = None,
    hub: dict[str, Any] | None = None,
) -> dict[str, Any]:
    max_full = max_full if max_full is not None else _int_env("TORII_SKILL_ROUTER_MAX", 4)
    max_always = max_always if max_always is not None else always_max()
    path_themes = themes_from_paths(paths)
    boosts, demoted = _load_fitness()
    attr_boosts, free_riders = _load_attribution()
    # free-riders join demote set for full-body skip (budgeted always still allowed)
    skip_full = set(demoted) | set(free_riders)

    # F125: hub recovery-util post-score → always priority compound
    hub_report = hub
    if hub_report is None and recovery_hub_enabled():
        try:
            hub_report = post_score_recovery_hub(root=root or _root())
        except Exception:
            hub_report = {"enabled": False, "priority_deltas": {}, "skills": {}}
    elif hub_report is None:
        hub_report = {"enabled": False, "priority_deltas": {}, "skills": {}}

    # F138: hub scorecard-util post-score → select priority for ops skills
    sc_hub_report: dict[str, Any] = {"enabled": False, "priority_deltas": {}, "skills": {}}
    if scorecard_hub_enabled():
        try:
            sc_hub_report = post_score_scorecard_hub(root=root or _root())
        except Exception:
            sc_hub_report = {"enabled": False, "priority_deltas": {}, "skills": {}}

    # F142: hub memory-util post-score → always/select priority for memory CLI skills
    mem_hub_report: dict[str, Any] = {
        "enabled": False,
        "priority_deltas": {},
        "skills": {},
    }
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from memory_tool_audit import (  # type: ignore
            memory_hub_enabled,
            post_score_memory_util_hub,
        )

        if memory_hub_enabled():
            mem_hub_report = post_score_memory_util_hub(root=root or _root())
    except Exception:
        mem_hub_report = {"enabled": False, "priority_deltas": {}, "skills": {}}

    # F161: multi-tenant hub-archival util gap → always priority for hub-archival skill
    ha_hub_report: dict[str, Any] = {
        "enabled": False,
        "priority_deltas": {},
        "skills": {},
    }
    if hub_archival_hub_enabled():
        try:
            ha_hub_report = post_score_hub_archival_hub(root=root or _root())
        except Exception:
            ha_hub_report = {"enabled": False, "priority_deltas": {}, "skills": {}}

    # F169: promoted refine dual → always priority for refined recovery skills
    rd_hub_report: dict[str, Any] = {
        "enabled": False,
        "priority_deltas": {},
        "skills": {},
    }
    if refine_dual_hub_enabled():
        try:
            rd_hub_report = post_score_refine_dual_hub(root=root or _root())
        except Exception:
            rd_hub_report = {"enabled": False, "priority_deltas": {}, "skills": {}}

    def _effective_always_prio(c: SkillCard) -> int:
        return (
            int(c.always_priority or 0)
            + hub_priority_delta(c.id, hub_report)
            + hub_priority_delta(c.id, sc_hub_report)
            + hub_priority_delta(c.id, mem_hub_report)
            + hub_priority_delta(c.id, ha_hub_report)
            + hub_priority_delta(c.id, rd_hub_report)
        )

    # F119: always-on budget — rank always candidates by always_priority (+ F125 hub), take top N
    always_cands = [c for c in cards if c.always]
    always_cands.sort(key=lambda c: (-_effective_always_prio(c), c.id))
    always_selected = always_cands[: max(0, max_always)]
    always_deferred = [c.id for c in always_cands[max(0, max_always) :]]
    always_selected_ids = {c.id for c in always_selected}
    always_deferred_set = set(always_deferred)

    ranked: list[tuple[float, SkillCard]] = []
    for c in cards:
        s = score_skill(
            c,
            path_themes,
            paths,
            fitness_boost=boosts.get(c.id, 0.0),
            attr_boost=attr_boosts.get(c.id, 0.0),
            force_not_always=(c.id in always_deferred_set),
        )
        # F125: small score bump so hub-hit recovery skills win residual slots
        hd = hub_priority_delta(c.id, hub_report)
        if hd and c.id in always_deferred_set:
            s += min(12.0, float(hd) / 4.0)
        # F138: hub-hit scorecard ops skills win residual full-body slots
        hd_sc = hub_priority_delta(c.id, sc_hub_report)
        if hd_sc:
            s += min(12.0, float(hd_sc) / 4.0)
        # F142: hub-hit memory util skills win always/residual slots
        hd_mem = hub_priority_delta(c.id, mem_hub_report)
        if hd_mem:
            s += min(12.0, float(hd_mem) / 4.0)
            if c.id in always_deferred_set:
                s += min(6.0, float(hd_mem) / 6.0)
        # F161: multi-tenant hub-archival util pressure keeps skill-prefer-hub-archival-early
        hd_ha = hub_priority_delta(c.id, ha_hub_report)
        if hd_ha:
            s += min(12.0, float(hd_ha) / 4.0)
            if c.id in always_deferred_set:
                s += min(8.0, float(hd_ha) / 5.0)
        # F169: promoted GEPA refine dual keeps refined recovery skills in always budget
        hd_rd = hub_priority_delta(c.id, rd_hub_report)
        if hd_rd:
            s += min(12.0, float(hd_rd) / 4.0)
            if c.id in always_deferred_set:
                s += min(8.0, float(hd_rd) / 5.0)
        ranked.append((s, c))
    ranked.sort(key=lambda x: (-x[0], x[1].id))

    selected: list[SkillCard] = list(always_selected)
    skipped_demoted: list[str] = []
    skipped_free_riders: list[str] = []

    # fill remaining full-body slots by score (deferred always compete without 1000)
    for s, c in ranked:
        if c in selected:
            continue
        if c.id in always_selected_ids:
            continue
        if c.id in skip_full:
            if c.id in free_riders and c.id not in skipped_free_riders:
                skipped_free_riders.append(c.id)
            if c.id in demoted and c.id not in skipped_demoted:
                skipped_demoted.append(c.id)
            continue
        if s <= 0 and len(selected) >= 1:
            continue
        if len(selected) >= max_full:
            if c.id in free_riders and c.id not in skipped_free_riders:
                skipped_free_riders.append(c.id)
            if c.id in demoted and c.id not in skipped_demoted:
                skipped_demoted.append(c.id)
            continue
        selected.append(c)

    # residual free-riders/demoted accounting
    selected_ids = {c.id for c in selected}
    for sid in free_riders:
        if sid not in selected_ids and sid not in skipped_free_riders:
            skipped_free_riders.append(sid)
    for sid in demoted:
        if sid not in selected_ids and sid not in skipped_demoted:
            if sid in always_selected_ids:
                continue
            skipped_demoted.append(sid)

    if not selected and ranked:
        fallback = [
            c
            for _, c in ranked
            if c.id in always_selected_ids or c.id not in skip_full
        ][: min(2, len(ranked))]
        selected = fallback or [c for _, c in ranked[: min(2, len(ranked))]]

    hub_deltas = {
        k: v
        for k, v in (hub_report.get("priority_deltas") or {}).items()
        if any(c.id == k for c in cards)
    }
    sc_hub_deltas = {
        k: v
        for k, v in (sc_hub_report.get("priority_deltas") or {}).items()
        if any(c.id == k for c in cards) or is_scorecard_skill_id(k)
    }

    return {
        "feature": FEATURE,
        "feature_always_budget": "F119",
        "feature_hub_compound": FEATURE_HUB if recovery_hub_enabled() else None,
        "feature_scorecard_hub": FEATURE_SCORECARD_HUB
        if scorecard_hub_enabled()
        else None,
        "schema": SCHEMA,
        "f89": True,
        "path_themes": sorted(path_themes),
        "paths_n": len(paths),
        "max_full": max_full,
        "max_always": max_always,
        "always_selected": [c.id for c in always_selected],
        "always_deferred": always_deferred,
        "catalog_n": len(cards),
        "selected": [c.id for c in selected],
        "selected_cards": selected,
        "demoted_skipped": skipped_demoted,
        "free_rider_skipped": skipped_free_riders,
        "fitness_boosts": {k: boosts[k] for k in boosts if any(c.id == k for c in cards)},
        "attr_boosts": {
            k: attr_boosts[k] for k in attr_boosts if any(c.id == k for c in cards)
        },
        "hub_priority_deltas": hub_deltas,
        "hub_gap_pressure": hub_report.get("gap_pressure"),
        "hub_skill_n": hub_report.get("skill_n"),
        "scorecard_hub_priority_deltas": sc_hub_deltas,
        "scorecard_hub_gap_pressure": sc_hub_report.get("gap_pressure"),
        "scorecard_hub_skill_n": sc_hub_report.get("skill_n"),
        "memory_hub_priority_deltas": {
            k: v
            for k, v in (mem_hub_report.get("priority_deltas") or {}).items()
        },
        "memory_hub_gap_pressure": mem_hub_report.get("gap_pressure"),
        "memory_hub_skill_n": mem_hub_report.get("skill_n"),
        "feature_memory_hub": "F142"
        if (mem_hub_report.get("enabled") or mem_hub_report.get("skill_n"))
        else None,
        "hub_archival_hub_priority_deltas": {
            k: v
            for k, v in (ha_hub_report.get("priority_deltas") or {}).items()
        },
        "hub_archival_hub_gap_pressure": ha_hub_report.get("gap_pressure"),
        "hub_archival_hub_high": ha_hub_report.get("high"),
        "feature_hub_archival_hub": FEATURE_HUB_ARCHIVAL_HUB
        if hub_archival_hub_enabled()
        else None,
        "refine_dual_hub_priority_deltas": {
            k: v
            for k, v in (rd_hub_report.get("priority_deltas") or {}).items()
        },
        "refine_dual_hub_fail_pressure": rd_hub_report.get("fail_pressure"),
        "refine_dual_hub_high_fail": rd_hub_report.get("high_fail"),
        "feature_refine_dual_hub": FEATURE_REFINE_DUAL_HUB
        if refine_dual_hub_enabled()
        else None,
        "ranking": [
            {
                "id": c.id,
                "score": round(s, 2),
                "always": c.always,
                "always_priority": c.always_priority,
                "always_priority_effective": _effective_always_prio(c),
                "hub_delta": hub_priority_delta(c.id, hub_report),
                "scorecard_hub_delta": hub_priority_delta(c.id, sc_hub_report),
                "hub_archival_hub_delta": hub_priority_delta(c.id, ha_hub_report),
                "memory_hub_delta": hub_priority_delta(c.id, mem_hub_report),
                "refine_dual_hub_delta": hub_priority_delta(c.id, rd_hub_report),
                "always_deferred": c.id in always_deferred_set,
                "demoted": c.id in demoted and c.id not in always_selected_ids,
                "free_rider": c.id in free_riders and c.id not in always_selected_ids,
            }
            for s, c in ranked
        ],
    }


# F121: recovery skills that teach tool CLIs (must fire tools when always-injected)
# F155: hub-archival joins recovery util stack (F121–F128) after F154 always adopt
HUB_ARCHIVAL_SKILL_ID = "skill-prefer-hub-archival-early"

RECOVERY_SKILL_IDS: frozenset[str] = frozenset(
    {
        "skill-prefer-memory-cli-early",
        "skill-prefer-product-cli",
        "skill-prefer-critic-early",
        HUB_ARCHIVAL_SKILL_ID,  # F155
    }
)

# F136: scorecard-gap ops skills (F132–F135) — inject ≠ utilization
SCORECARD_SKILL_IDS: frozenset[str] = frozenset(
    {
        "skill-prefer-product-scorecard",
        "skill-prefer-demote-eval-check",
        "skill-prefer-memory-util-eval",
        "skill-prefer-workflow-scorecard",
        "skill-prefer-hub-gap-critic",
        "skill-prefer-dual-compound-ops",
        "skill-prefer-recovery-skills-active",
    }
)


def is_scorecard_skill_id(sid: str) -> bool:
    """True if skill id is a known scorecard-gap ops skill (privacy-safe id only)."""
    s = str(sid or "").strip()
    if not s or "/" in s or ".." in s:
        return False
    if s in SCORECARD_SKILL_IDS:
        return True
    return any(
        x in s
        for x in (
            "scorecard",
            "demote-eval",
            "memory-util",
            "hub-gap",
            "dual-compound",
            "workflow-scorecard",
        )
    )


def compact_enabled() -> bool:
    """F120: SkillReducer-lite — compact full skill bodies on inject (default on)."""
    raw = (os.environ.get("TORII_SKILL_COMPACT") or "1").strip().lower()
    return raw not in _FALSEY


def always_max_chars() -> int:
    return _int_env("TORII_SKILL_ALWAYS_MAX_CHARS", 480)


def full_max_chars() -> int:
    return _int_env("TORII_SKILL_FULL_MAX_CHARS", 900)


def compact_skill_body(body: str, max_chars: int) -> tuple[str, int]:
    """Keep actionable rules (headings, numbered steps, code) under max_chars.

    Returns (text, chars_saved). SkillReducer stage-2 lite: drop background prose.
    """
    if not body:
        return body, 0
    original_len = len(body)
    if original_len <= max_chars:
        return body, 0
    keep: list[str] = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            if keep and keep[-1] != "":
                keep.append("")
            continue
        # actionable: headings, ordered/unordered lists, code, short imperatives
        if (
            s.startswith("#")
            or re.match(r"^\d+[\.)]\s+\S", s)
            or s.startswith(("-", "*", "•"))
            or "`" in s
            or s.lower().startswith(
                ("call ", "run ", "prefer ", "use ", "do not ", "never ", "always ")
            )
        ):
            keep.append(line.rstrip())
            continue
        # short policy lines with security verbs
        if len(s) <= 120 and any(
            k in s.lower()
            for k in (
                "path:line",
                "unvalidated",
                "request changes",
                "hint",
                "evidence",
                "budget",
            )
        ):
            keep.append(line.rstrip())
    text = "\n".join(keep).strip()
    if not text:
        text = body.strip()
    if len(text) > max_chars:
        cut = max_chars - 24
        text = text[: max(0, cut)].rstrip() + "\n…(F120 compacted)"
    saved = max(0, original_len - len(text))
    return text, saved


def render_injection(cards_all: list[SkillCard], selection: dict[str, Any]) -> str:
    selected_ids = set(selection.get("selected") or [])
    selected_cards: list[SkillCard] = selection.get("selected_cards") or [
        c for c in cards_all if c.id in selected_ids
    ]
    always_ids = set(selection.get("always_selected") or [])
    do_compact = compact_enabled()
    a_max = always_max_chars()
    f_max = full_max_chars()
    compact_meta: list[dict[str, Any]] = []
    lines: list[str] = [
        "## Skill router (F84/F119/F120 — progressive disclosure + compact)",
        "",
        "Use the **index** for awareness; follow **selected full skills** as reviewer discipline.",
        f"Routed themes: {', '.join(selection.get('path_themes') or []) or 'review'}.",
        "",
        "### Skill index (all active)",
        "",
    ]
    for c in cards_all:
        flag = " ★" if c.id in selected_ids else ""
        one = c.title
        themes = ",".join(c.themes[:4]) if c.themes else "general"
        lines.append(f"- `{c.id}`{flag} — {one} [{themes}]")
    lines.append("")
    lines.append("### Selected full skills")
    lines.append("")
    if not selected_cards:
        lines.append("_No skills selected._")
    for c in selected_cards:
        lines.append(f"#### {c.id}")
        lines.append("")
        body = c.body
        if do_compact:
            # budgeted always skills get tighter cap (SkillReducer always cost)
            is_always = c.always or c.id in always_ids
            cap = a_max if is_always else f_max
            body, saved = compact_skill_body(body, cap)
            if saved:
                compact_meta.append(
                    {"id": c.id, "saved": saved, "cap": cap, "always": is_always}
                )
        lines.append(body)
        lines.append("")
    # stash compact meta on selection for inject artifact (soft)
    if compact_meta:
        selection["f120_compact"] = compact_meta
        selection["f120_chars_saved"] = sum(int(x["saved"]) for x in compact_meta)
    return "\n".join(lines).rstrip() + "\n"


def inject_into_prompt(
    prompt: Path,
    root: Path | None = None,
    paths: list[str] | None = None,
    out: Path | None = None,
) -> dict[str, Any]:
    root = root or _root()
    cards = catalog(root)
    paths = paths if paths is not None else paths_from_args()
    hub_report = None
    if recovery_hub_enabled():
        try:
            hub_report = post_score_recovery_hub(root=root)
        except Exception:
            hub_report = None
    selection = select_skills(cards, paths, root=root, hub=hub_report)
    body = render_injection(cards, selection)
    chunk = f"{MARKER_OPEN}\n{body}{MARKER_CLOSE}\n"
    original = prompt.read_text(encoding="utf-8", errors="replace")

    # optionally strip F69 bulk skills block to avoid double injection
    stripped_f69 = False
    if replace_f69() and F69_OPEN in original:
        original = re.sub(
            rf"{re.escape(F69_OPEN)}.*?{re.escape(F69_CLOSE)}\n?",
            "",
            original,
            count=1,
            flags=re.DOTALL,
        )
        stripped_f69 = True

    if MARKER_OPEN in original:
        new = re.sub(
            rf"{re.escape(MARKER_OPEN)}.*?{re.escape(MARKER_CLOSE)}\n?",
            chunk,
            original,
            count=1,
            flags=re.DOTALL,
        )
    else:
        marker = "## PR metadata"
        if marker in original:
            new = original.replace(marker, chunk + "\n" + marker, 1)
        else:
            new = original.rstrip() + "\n\n" + chunk

    dest = out or prompt
    dest.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")

    # F125: inject hub recovery util compound section (soft)
    hub_inj: dict[str, Any] = {"injected": 0}
    if recovery_hub_enabled() and hub_report is not None:
        hub_inj = inject_recovery_hub_into_prompt(dest, hub=hub_report, root=root)
    # F138: inject hub scorecard util compound section (soft)
    sc_hub_inj: dict[str, Any] = {"injected": 0}
    if scorecard_hub_enabled():
        try:
            sc_hub_inj = inject_scorecard_hub_into_prompt(dest, root=root)
        except Exception as exc:
            sc_hub_inj = {"injected": 0, "soft_error": str(exc)[:80]}
    # F142: inject hub memory util compound section (soft)
    mem_hub_inj: dict[str, Any] = {"injected": 0}
    try:
        from memory_tool_audit import (  # type: ignore
            inject_memory_hub_into_prompt,
            memory_hub_enabled,
        )

        if memory_hub_enabled():
            mem_hub_inj = inject_memory_hub_into_prompt(dest, root=root)
    except Exception as exc:
        mem_hub_inj = {"injected": 0, "soft_error": str(exc)[:80]}
    # F162: inject multi-tenant hub-archival util pressure (soft)
    ha_hub_inj: dict[str, Any] = {"injected": 0}
    if hub_archival_hub_enabled():
        try:
            ha_hub_inj = inject_hub_archival_hub_into_prompt(dest, root=root)
        except Exception as exc:
            ha_hub_inj = {"injected": 0, "soft_error": str(exc)[:80]}
    # F169: inject promoted refine dual hub (soft)
    rd_hub_inj: dict[str, Any] = {"injected": 0}
    if refine_dual_hub_enabled():
        try:
            rd_hub_inj = inject_refine_dual_hub_into_prompt(dest, root=root)
        except Exception as exc:
            rd_hub_inj = {"injected": 0, "soft_error": str(exc)[:80]}

    result = {
        "feature": FEATURE,
        "feature_compact": "F120" if compact_enabled() else None,
        "feature_hub_compound": FEATURE_HUB if recovery_hub_enabled() else None,
        "feature_scorecard_hub": FEATURE_SCORECARD_HUB
        if scorecard_hub_enabled()
        else None,
        "injected": 1,
        "selected": selection["selected"],
        "always_selected": selection.get("always_selected"),
        "catalog_n": len(cards),
        "paths_n": selection["paths_n"],
        "path_themes": selection["path_themes"],
        "stripped_f69": stripped_f69,
        "prompt": str(dest),
        "chars": len(body),
        "inject_chars": len(body),
        "f120_chars_saved": selection.get("f120_chars_saved") or 0,
        "f120_compact": selection.get("f120_compact") or [],
        "hub_injected": int(hub_inj.get("injected") or 0),
        "hub_skill_n": selection.get("hub_skill_n"),
        "hub_gap_pressure": selection.get("hub_gap_pressure"),
        "hub_priority_deltas": selection.get("hub_priority_deltas"),
        "scorecard_hub_injected": int(sc_hub_inj.get("injected") or 0),
        "scorecard_hub_skill_n": selection.get("scorecard_hub_skill_n"),
        "scorecard_hub_gap_pressure": selection.get("scorecard_hub_gap_pressure"),
        "scorecard_hub_priority_deltas": selection.get(
            "scorecard_hub_priority_deltas"
        ),
        "memory_hub_injected": int(mem_hub_inj.get("injected") or 0),
        "memory_hub_skill_n": selection.get("memory_hub_skill_n"),
        "memory_hub_gap_pressure": selection.get("memory_hub_gap_pressure"),
        "memory_hub_priority_deltas": selection.get("memory_hub_priority_deltas"),
        "feature_memory_hub": selection.get("feature_memory_hub"),
        # F162
        "hub_archival_hub_injected": int(ha_hub_inj.get("injected") or 0),
        "hub_archival_hub_gap_pressure": ha_hub_inj.get("gap_pressure")
        if ha_hub_inj.get("injected")
        else selection.get("hub_archival_hub_gap_pressure"),
        "hub_archival_hub_high": ha_hub_inj.get("high"),
        "feature_hub_archival_hub_inject": FEATURE_HUB_ARCHIVAL_HUB_INJECT
        if ha_hub_inj.get("injected")
        else None,
        # F169
        "refine_dual_hub_injected": int(rd_hub_inj.get("injected") or 0),
        "refine_dual_hub_fail_pressure": rd_hub_inj.get("fail_pressure")
        if rd_hub_inj.get("injected")
        else selection.get("refine_dual_hub_fail_pressure"),
        "refine_dual_hub_priority_deltas": selection.get(
            "refine_dual_hub_priority_deltas"
        ),
        "feature_refine_dual_hub": FEATURE_REFINE_DUAL_HUB
        if rd_hub_inj.get("injected") or refine_dual_hub_enabled()
        else None,
    }
    # write selection artifact next to prompt if OUT_DIR (F160: also prompt parent)
    od = (os.environ.get("OUT_DIR") or "").strip()
    if not od and dest is not None:
        # F160: bench/live puts prompt.md under out_dir without assemble OUT_DIR race
        try:
            if dest.name in ("prompt.md", "prompt-in.md") and dest.parent.is_dir():
                od = str(dest.parent)
        except Exception:
            od = ""
    if od:
        art = Path(od) / "skill-router.json"
        try:
            art.write_text(
                json.dumps(
                    {
                        **{k: v for k, v in selection.items() if k != "selected_cards"},
                        "injected_at": _now(),
                        "inject_chars": len(body),
                        "f120_chars_saved": selection.get("f120_chars_saved") or 0,
                        "f120_compact": selection.get("f120_compact") or [],
                        "hub_injected": result.get("hub_injected"),
                        "synthesized": False,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            result["artifact"] = str(art)
        except OSError:
            pass
    return result


def _collect_tool_blob(
    out_dir: Path | None = None,
    agent_loop: Path | None = None,
    log_path: Path | None = None,
) -> str:
    """Gather agent-loop / log / memory-audit text for F114 tool-outcome probes."""
    chunks: list[str] = []
    candidates: list[Path] = []
    if agent_loop is not None:
        candidates.append(Path(agent_loop))
    if log_path is not None:
        candidates.append(Path(log_path))
    if out_dir is not None:
        od = Path(out_dir)
        candidates.extend(
            [
                od / "agent-loop" / "agent-loop.json",
                od / "agent-loop.json",
                od / "hermes.log",
                od / "run.log",
                od / "memory-tool-audit.json",
            ]
        )
    seen: set[str] = set()
    for p in candidates:
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key in seen or not p.is_file():
            continue
        seen.add(key)
        try:
            chunks.append(p.read_text(encoding="utf-8", errors="replace")[:120_000])
        except OSError:
            continue
    return "\n".join(chunks)


def probe_ledger_path(root: Path | None = None) -> Path:
    """F117: durable mined tool-outcome probes (merged with static TOOL_OUTCOME_PROBES)."""
    env = (os.environ.get("TORII_TOOL_OUTCOME_PROBES_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / "tool-outcome-probes.json"


def load_dynamic_probes(root: Path | None = None) -> dict[str, list[str]]:
    """skill_id → list of regex pattern strings (F117 mine ledger)."""
    p = probe_ledger_path(root)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, dict):
        return {}
    out: dict[str, list[str]] = {}
    for sid, ent in skills.items():
        if not isinstance(sid, str) or "/" in sid or not isinstance(ent, dict):
            continue
        pats = ent.get("patterns") or []
        if not isinstance(pats, list):
            continue
        clean = [str(x) for x in pats if isinstance(x, str) and 3 <= len(x) <= 120][:16]
        if clean:
            out[sid] = clean
    return out


def tool_probes_for(sid: str, root: Path | None = None) -> list[re.Pattern[str]]:
    """Static F114 probes + F117 mined dynamic probes for a skill id."""
    compiled: list[re.Pattern[str]] = list(TOOL_OUTCOME_PROBES.get(sid) or [])
    seen = {rx.pattern for rx in compiled}
    for pat in load_dynamic_probes(root).get(sid) or []:
        if pat in seen:
            continue
        try:
            compiled.append(re.compile(pat, re.I))
            seen.add(pat)
        except re.error:
            continue
    return compiled


def match_tool_outcome(
    sid: str, tool_blob: str, root: Path | None = None
) -> list[str]:
    """Return matched probe labels for a skill against tool/log blob."""
    if not tool_blob:
        return []
    matched: list[str] = []
    for rx in tool_probes_for(sid, root=root):
        m = rx.search(tool_blob)
        if m:
            matched.append(m.group(0)[:80])
    return matched


def score_hits(
    review: Path,
    root: Path | None = None,
    selected: list[str] | None = None,
    out_dir: Path | None = None,
    *,
    agent_loop: Path | None = None,
    log_path: Path | None = None,
    tool_blob: str | None = None,
) -> dict[str, Any]:
    root = root or _root()
    cards = catalog(root)
    text = review.read_text(encoding="utf-8", errors="replace").lower() if review.is_file() else ""
    by_id = {c.id: c for c in cards}
    if selected is None:
        # try skill-router.json
        od = out_dir or Path(os.environ.get("OUT_DIR") or ".")
        art = Path(od) / "skill-router.json"
        if art.is_file():
            try:
                selected = json.loads(art.read_text(encoding="utf-8")).get("selected") or []
            except (json.JSONDecodeError, OSError):
                selected = [c.id for c in cards]
        else:
            selected = [c.id for c in cards]

    # F114: tool-invocation blob (agent-loop / logs / audit)
    use_tools = tool_outcome_enabled()
    if tool_blob is None and use_tools:
        tool_blob = _collect_tool_blob(out_dir, agent_loop=agent_loop, log_path=log_path)
    elif tool_blob is None:
        tool_blob = ""

    hits: list[dict[str, Any]] = []
    hit_n = 0
    tool_hit_n = 0
    prose_hit_n = 0
    for sid in selected:
        c = by_id.get(sid)
        if not c:
            hits.append(
                {
                    "id": sid,
                    "hit": False,
                    "matched": [],
                    "missing": True,
                    "prose_hit": False,
                    "tool_hit": False,
                }
            )
            continue
        matched: list[str] = []
        # Generic tokens that appear in almost every review (noise for hit scoring)
        _PROSE_STOP = frozenset(
            {
                "review",
                "skill",
                "prefer",
                "early",
                "call",
                "with",
                "from",
                "this",
                "that",
                "when",
                "into",
                "over",
                "only",
                "path",
                "file",
                "line",
                "true",
                "false",
                "title",
                "tools",
                "depth",
                "hunks",
            }
        )
        # title tokens + keywords (skip ultra-generic words)
        probes = list(c.keywords[:10])
        for part in re.split(r"[\s\-_/]+", c.title.lower()):
            if len(part) >= 4 and part not in probes and part not in _PROSE_STOP:
                probes.append(part)
        # id tail
        tail = (
            sid.replace("skill-", "")
            .replace("f74-", "")
            .replace("prefer-", "")
            .replace("-", " ")
        )
        for part in tail.split():
            if len(part) >= 4 and part not in probes and part not in _PROSE_STOP:
                probes.append(part)
        for kw in probes:
            if len(kw) < 3:
                continue
            kl = kw.lower()
            if kl in _PROSE_STOP:
                continue
            if kl in text:
                matched.append(kl)
        prose_hit = len(matched) >= 1
        tool_matched = (
            match_tool_outcome(sid, tool_blob, root=root) if use_tools else []
        )
        tool_hit = len(tool_matched) >= 1
        # Combined: prose OR tool invocation proves skill fired
        is_hit = prose_hit or tool_hit
        if is_hit:
            hit_n += 1
        if prose_hit:
            prose_hit_n += 1
        if tool_hit:
            tool_hit_n += 1
        hits.append(
            {
                "id": sid,
                "hit": is_hit,
                "matched": matched[:8],
                "n_matched": len(matched),
                "prose_hit": prose_hit,
                "tool_hit": tool_hit,
                "tool_matched": tool_matched[:6],
            }
        )

    rate = (hit_n / len(selected)) if selected else 0.0
    tool_rate = (tool_hit_n / len(selected)) if selected else 0.0
    result = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "f114": True,
        "tool_outcome": use_tools,
        "scored_at": _now(),
        "selected_n": len(selected),
        "hit_n": hit_n,
        "hit_rate": round(rate, 4),
        "prose_hit_n": prose_hit_n,
        "tool_hit_n": tool_hit_n,
        "tool_hit_rate": round(tool_rate, 4),
        "hits": hits,
        "review": str(review),
        # privacy-safe federated theme: skill ids only
        "federated_skill_themes": [
            h["id"] for h in hits if h.get("hit") and not str(h["id"]).startswith("/")
        ],
        "tool_outcome_skills": [
            h["id"] for h in hits if h.get("tool_hit") and not str(h["id"]).startswith("/")
        ],
    }
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "skill-hits.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        result["artifact"] = str(out_dir / "skill-hits.json")
    return result


# --- CLI ---


def cmd_index(args: argparse.Namespace) -> int:
    cards = catalog(_root())
    payload = {
        "feature": FEATURE,
        "n": len(cards),
        "skills": [
            {
                "id": c.id,
                "title": c.title,
                "themes": c.themes,
                "keywords": c.keywords[:8],
                "exts": c.exts,
                "always": c.always,
                "chars": c.chars,
            }
            for c in cards
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_select(args: argparse.Namespace) -> int:
    paths = paths_from_args(
        paths=args.paths,
        paths_file=args.paths_file,
        pr_json=args.pr_json,
    )
    cards = catalog(_root())
    sel = select_skills(cards, paths, max_full=args.max)
    out = {k: v for k, v in sel.items() if k != "selected_cards"}
    print(json.dumps(out, indent=2))
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "injected": 0, "reason": "disabled"}))
        return 0
    prompt = Path(args.prompt)
    if not prompt.is_file():
        print(f"error: prompt not found: {prompt}", file=sys.stderr)
        return 1
    paths = paths_from_args(
        paths=args.paths,
        paths_file=args.paths_file,
        pr_json=args.pr_json,
    )
    result = inject_into_prompt(
        prompt,
        paths=paths,
        out=Path(args.out) if args.out else None,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    review = Path(args.review)
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is None and (os.environ.get("OUT_DIR") or "").strip():
        out_dir = Path(os.environ["OUT_DIR"])
    selected = None
    if args.selected:
        selected = [x.strip() for x in args.selected.split(",") if x.strip()]
    al = (getattr(args, "agent_loop", None) or "").strip()
    lg = (getattr(args, "log", None) or "").strip()
    result = score_hits(
        review,
        selected=selected,
        out_dir=out_dir,
        agent_loop=Path(al) if al else None,
        log_path=Path(lg) if lg else None,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cards = catalog(_root())
    always = [c.id for c in cards if c.always]
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "schema": SCHEMA,
                "f114": True,
                "enabled": enabled(),
                "tool_outcome": tool_outcome_enabled(),
                "active_n": len(cards),
                "always": always,
                "tool_probe_skills": sorted(TOOL_OUTCOME_PROBES.keys()),
                "max_full": _int_env("TORII_SKILL_ROUTER_MAX", 4),
                "replace_f69": replace_f69(),
                "ids": [c.id for c in cards],
            },
            indent=2,
        )
    )
    return 0


def hub_archival_util_enabled() -> bool:
    """F155: include hub-archival skill in recovery util scoring (default on)."""
    raw = (os.environ.get("TORII_HUB_ARCHIVAL_UTIL") or "1").strip().lower()
    return raw not in _FALSEY


def hub_archival_reprompt_enabled() -> bool:
    """F157: soft re-prompt when hub-archival inject ≠ hub_boost tools (default on)."""
    raw = (os.environ.get("TORII_HUB_ARCHIVAL_REPROMPT") or "1").strip().lower()
    return raw not in _FALSEY


def router_synth_enabled() -> bool:
    """F160: synthesize skill-router.json from always skills when artifact missing."""
    raw = (os.environ.get("TORII_SKILL_ROUTER_SYNTH") or "1").strip().lower()
    return raw not in _FALSEY


def ensure_skill_router_doc(
    out_dir: Path | None = None,
    *,
    root: Path | None = None,
    write: bool = True,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    """F160: load skill-router.json or synthesize from active always skills.

    Live bench (bench_security_gate live) skips assemble-context, so inject never
    writes skill-router.json and recovery util reports recovery_injected_n=0.
    Synthesize always_selected from catalog so F121–F159 measure real always skills.
    Privacy: skill ids only.
    """
    root = root or _root()
    od = Path(out_dir) if out_dir else None
    if od is None:
        env_od = (os.environ.get("OUT_DIR") or "").strip()
        if env_od:
            od = Path(env_od)
    if od:
        rp = od / "skill-router.json"
        if rp.is_file():
            try:
                data = json.loads(rp.read_text(encoding="utf-8"))
                if isinstance(data, dict) and (
                    data.get("selected") or data.get("always_selected")
                ):
                    return data
            except (OSError, json.JSONDecodeError):
                pass

    if not router_synth_enabled():
        return {
            "feature": FEATURE,
            "feature_router_synth": FEATURE_ROUTER_SYNTH,
            "selected": [],
            "always_selected": [],
            "synthesized": False,
            "reason": "synth_off",
        }

    cards = catalog(root)
    always_cards = [c for c in cards if c.always]
    # Prefer full select when paths available (richer always ranking under F119)
    if paths:
        try:
            sel = select_skills(cards, paths, root=root)
            always_ids = list(sel.get("always_selected") or [])
            selected_ids = list(sel.get("selected") or [])
            if not always_ids:
                always_ids = [c.id for c in always_cards]
            if not selected_ids:
                selected_ids = list(always_ids)
            doc: dict[str, Any] = {
                "feature": FEATURE,
                "feature_router_synth": FEATURE_ROUTER_SYNTH,
                "selected": selected_ids,
                "always_selected": always_ids,
                "synthesized": True,
                "synth_mode": "select_paths",
                "inject_chars": 0,
                "paths_n": len(paths),
                "scored_at": _now(),
                "reason": "missing_skill_router_artifact",
            }
        except Exception:
            always_ids = [c.id for c in always_cards]
            doc = {
                "feature": FEATURE,
                "feature_router_synth": FEATURE_ROUTER_SYNTH,
                "selected": always_ids[:],
                "always_selected": always_ids[:],
                "synthesized": True,
                "synth_mode": "always_catalog",
                "inject_chars": 0,
                "scored_at": _now(),
                "reason": "missing_skill_router_artifact",
            }
    else:
        always_ids = [c.id for c in always_cards]
        doc = {
            "feature": FEATURE,
            "feature_router_synth": FEATURE_ROUTER_SYNTH,
            "selected": always_ids[:],
            "always_selected": always_ids[:],
            "synthesized": True,
            "synth_mode": "always_catalog",
            "inject_chars": 0,
            "scored_at": _now(),
            "reason": "missing_skill_router_artifact",
        }

    if write and od:
        try:
            od.mkdir(parents=True, exist_ok=True)
            (od / "skill-router.json").write_text(
                json.dumps(doc, indent=2) + "\n", encoding="utf-8"
            )
            doc["artifact"] = str(od / "skill-router.json")
        except OSError:
            pass
    return doc


def score_recovery_util(
    out_dir: Path | None = None,
    *,
    root: Path | None = None,
    hits_doc: dict[str, Any] | None = None,
    router_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """F121/F155: recovery skills injected vs tool_hit — inject presence ≠ utilization.

    SkillsBench / Mem2Act: always-injected recovery skills must fire tool CLIs
    or they are idle prompt cost. Gap when recovery selected and tool_hit_n=0.

    F155: skill-prefer-hub-archival-early joins RECOVERY_SKILL_IDS so always
    inject under F119/F154 is measured for hub-boost tool outcomes (not prose).
    """
    root = root or _root()
    od = Path(out_dir) if out_dir else None
    router: dict[str, Any] = dict(router_doc or {})
    hits: dict[str, Any] = dict(hits_doc or {})
    if od:
        hp = od / "skill-hits.json"
        if not router:
            # F160: load or synthesize skill-router.json (bench live skips assemble)
            router = ensure_skill_router_doc(od, root=root, write=True)
        if not hits and hp.is_file():
            try:
                hits = json.loads(hp.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                hits = {}
    elif not router:
        router = ensure_skill_router_doc(None, root=root, write=False)

    selected = list(router.get("selected") or [])
    always_sel = list(router.get("always_selected") or [])
    recovery_ids = set(RECOVERY_SKILL_IDS)
    if not hub_archival_util_enabled():
        recovery_ids = recovery_ids - {HUB_ARCHIVAL_SKILL_ID}
    recovery_injected = [
        s for s in selected if s in recovery_ids
    ] or [s for s in always_sel if s in recovery_ids]

    by_id: dict[str, dict[str, Any]] = {}
    for h in hits.get("hits") or []:
        if isinstance(h, dict) and h.get("id"):
            by_id[str(h["id"])] = h

    tool_hit_ids: list[str] = []
    prose_hit_ids: list[str] = []
    idle: list[str] = []
    for sid in recovery_injected:
        h = by_id.get(sid) or {}
        if h.get("tool_hit"):
            tool_hit_ids.append(sid)
        else:
            # tool-taught recovery skills: prose-only still counts as idle
            idle.append(sid)
            if h.get("prose_hit") or h.get("hit"):
                prose_hit_ids.append(sid)

    n = len(recovery_injected)
    tool_n = len(tool_hit_ids)
    util_rate = (tool_n / n) if n else 1.0  # no recovery → no gap
    # gap: recovery was injected but none fired tools
    gap = bool(n >= 1 and tool_n == 0)

    inject_chars = int(router.get("inject_chars") or router.get("chars") or 0)
    f120_saved = int(router.get("f120_chars_saved") or 0)

    # F155: hub-archival slice (always_priority 95 skill must use hub-boost tools)
    hub_sid = HUB_ARCHIVAL_SKILL_ID
    hub_injected = hub_sid in recovery_injected
    hub_tool_hit = hub_sid in tool_hit_ids
    hub_idle = hub_sid in idle
    hub_gap = bool(hub_injected and not hub_tool_hit)

    report = {
        "feature": "F121",
        "feature_hub_archival_util": FEATURE_HUB_ARCHIVAL_UTIL,
        "feature_router_synth": FEATURE_ROUTER_SYNTH
        if router.get("synthesized")
        else None,
        "schema": SCHEMA,
        "scored_at": _now(),
        "recovery_ids": sorted(recovery_ids),
        "recovery_injected": recovery_injected,
        "recovery_injected_n": n,
        "tool_hit_ids": tool_hit_ids,
        "prose_only_ids": prose_hit_ids,
        "idle_ids": idle,
        "tool_hit_n": tool_n,
        "util_rate": round(util_rate, 4),
        "utilization_gap": gap,
        "inject_chars": inject_chars,
        "f120_chars_saved": f120_saved,
        "ok": not gap,
        "score": round(util_rate, 4),
        # F155 hub-archival util surface
        "hub_archival_id": hub_sid,
        "hub_archival_injected": hub_injected,
        "hub_archival_tool_hit": hub_tool_hit,
        "hub_archival_idle": hub_idle,
        "hub_archival_util_gap": hub_gap,
        "hub_archival_ok": (not hub_gap) if hub_injected else True,
        # F160
        "router_synthesized": bool(router.get("synthesized")),
        "router_synth_mode": router.get("synth_mode"),
    }
    if od:
        try:
            od.mkdir(parents=True, exist_ok=True)
            (od / "recovery-skill-util.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass
    return report


def federate_recovery_util(
    util: dict[str, Any],
    *,
    root: Path | None = None,
    tenant: str = "",
    dest: Path | None = None,
) -> dict[str, Any]:
    """F124: privacy-safe federate of recovery util themes (ids + rates only).

    Never includes paths, prompts, or tool command strings — skill_id + counters.
    """
    import hashlib
    import re as _re

    root = root or _root()
    tenant = tenant or (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    th = ""
    if tenant:
        th = hashlib.sha256(tenant.encode("utf-8")).hexdigest()[:12]

    signals: list[dict[str, Any]] = []
    tool_ids = list(util.get("tool_hit_ids") or [])
    idle_ids = list(util.get("idle_ids") or [])
    util_rate = float(util.get("util_rate") or 0)
    inject_chars = int(util.get("inject_chars") or 0)
    f120_saved = int(util.get("f120_chars_saved") or 0)

    def _slug(sid: str) -> str:
        return _re.sub(r"[^a-z0-9._-]+", "-", sid.lower())[:64]

    for sid in tool_ids:
        if "/" in sid or ".." in sid:
            continue
        tags = ["recovery_util", "tool_outcome", "f124", "federated_skill"]
        kws = [sid.replace("skill-", "")[:48], "recovery-util", "tool-hit"]
        # F155: hub-archival hit theme for multi-tenant recovery warm paging
        if sid == HUB_ARCHIVAL_SKILL_ID:
            tags.extend(["hub_archival", "f155", "hub_boost"])
            kws.extend(["hub-archival", "hub-boost", "recon-warm"])
        sig: dict[str, Any] = {
            "id": _slug(f"recovery-util-hit-{sid}"),
            "theme": _slug(sid),
            "cwe": [],
            "tags": tags,
            "keywords": kws,
            "path_basenames": [],
            "hits": 1,
            "tool_hits": 1,
            "source": "recovery_skill_util",
            "tenants": 1,
            "util_rate_bin": "hit",
        }
        if th:
            sig["tenant_hashes"] = [th]
            sig["tenant_hash"] = th
        signals.append(sig)

    # Aggregate gap signal (no skill list leakage beyond counts if idle empty)
    if util.get("utilization_gap"):
        gap_tags = ["recovery_util", "utilization_gap", "f124", "federated_skill"]
        gap_kws = ["recovery-util-gap", "idle-recovery"]
        # F155: tag when hub-archival specifically idle under inject
        if util.get("hub_archival_util_gap"):
            gap_tags.extend(["hub_archival", "f155", "hub_archival_idle"])
            gap_kws.extend(["hub-archival-gap", "hub-boost-idle"])
        gap_sig: dict[str, Any] = {
            "id": "recovery-util-gap",
            "theme": "recovery-util-gap",
            "cwe": [],
            "tags": gap_tags,
            "keywords": gap_kws,
            "path_basenames": [],
            "hits": 1,
            "source": "recovery_skill_util",
            "tenants": 1,
            "idle_n": len(idle_ids),
            "injected_n": int(util.get("recovery_injected_n") or 0),
            # bucketed only — not raw char counts that could fingerprint tenants
            "inject_chars_bucket": (
                "0"
                if inject_chars <= 0
                else "lt2k"
                if inject_chars < 2000
                else "2k-4k"
                if inject_chars < 4000
                else "gte4k"
            ),
            "util_rate_bin": "gap",
            "hub_archival_idle": bool(util.get("hub_archival_util_gap")),
        }
        if th:
            gap_sig["tenant_hashes"] = [th]
            gap_sig["tenant_hash"] = th
        signals.append(gap_sig)
    elif util.get("hub_archival_util_gap"):
        # F155: partial recovery ok but hub-archival specifically idle → soft signal
        ha_gap: dict[str, Any] = {
            "id": "hub-archival-util-gap",
            "theme": "hub-archival-util-gap",
            "cwe": [],
            "tags": [
                "recovery_util",
                "hub_archival",
                "utilization_gap",
                "f155",
                "federated_skill",
            ],
            "keywords": ["hub-archival-gap", "hub-boost-idle", "recon-warm"],
            "path_basenames": [],
            "hits": 1,
            "source": "recovery_skill_util",
            "tenants": 1,
            "util_rate_bin": "gap",
            "hub_archival_idle": True,
        }
        if th:
            ha_gap["tenant_hashes"] = [th]
            ha_gap["tenant_hash"] = th
        signals.append(ha_gap)
    elif tool_ids:
        # healthy util summary (no paths)
        ok_sig: dict[str, Any] = {
            "id": "recovery-util-ok",
            "theme": "recovery-util-ok",
            "cwe": [],
            "tags": ["recovery_util", "util_ok", "f124", "federated_skill"],
            "keywords": ["recovery-util-ok"],
            "path_basenames": [],
            "hits": max(1, len(tool_ids)),
            "source": "recovery_skill_util",
            "tenants": 1,
            "tool_hit_n": len(tool_ids),
            "util_rate_bin": (
                "full" if util_rate >= 0.99 else "partial" if util_rate >= 0.34 else "low"
            ),
            "f120_saved_bucket": (
                "0"
                if f120_saved <= 0
                else "lt500"
                if f120_saved < 500
                else "gte500"
            ),
        }
        if th:
            ok_sig["tenant_hashes"] = [th]
            ok_sig["tenant_hash"] = th
        signals.append(ok_sig)

    dest = dest or (root / "memory" / "federation" / "recovery-util-signals.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(signals)
    privacy_ok = "/Users/" not in blob and "/home/" not in blob and "C:\\\\Users" not in blob
    # strip any accidental absolute paths
    clean = []
    for s in signals:
        sb = json.dumps(s)
        if "/Users/" in sb or "/home/" in sb:
            continue
        clean.append(s)
    doc = {
        "schema_version": SCHEMA,
        "feature": "F124",
        "scope": "recovery_skill_util",
        "updated_at": _now(),
        "count": len(clean),
        "privacy": "skill_id_util_bins_tenant_hash_only",
        "privacy_ok": privacy_ok and len(clean) == len(signals),
        "signals": clean,
    }
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    hub = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from federated_hub_ingest import ingest as hub_ingest  # type: ignore

        hub = hub_ingest(
            root,
            clean,
            tenant=tenant,
            source_repo="recovery_skill_util",
            write_tenant=bool(tenant),
        )
    except Exception as exc:
        hub = {"soft_error": str(exc)[:120]}

    return {
        "feature": "F124",
        "fed_path": str(dest),
        "fed_n": len(clean),
        "privacy_ok": doc["privacy_ok"],
        "hub": hub,
        "signals": clean,
    }


def cmd_util(args: argparse.Namespace) -> int:
    """F121: score recovery skill tool utilization for a run dir (+ F124 federate)."""
    od = Path(args.out_dir) if args.out_dir else None
    if od is None and (os.environ.get("OUT_DIR") or "").strip():
        od = Path(os.environ["OUT_DIR"])
    if od is None:
        print(json.dumps({"feature": "F121", "error": "need --out-dir", "ok": False}))
        return 2
    report = score_recovery_util(od, root=_root())
    fed = None
    do_fed = True
    if getattr(args, "no_federate", False):
        do_fed = False
    raw_fed = (os.environ.get("TORII_RECOVERY_UTIL_FEDERATE") or "1").strip().lower()
    if raw_fed in _FALSEY:
        do_fed = False
    if do_fed:
        fed = federate_recovery_util(report, root=_root())
        report["federate"] = {
            "fed_n": fed.get("fed_n"),
            "privacy_ok": fed.get("privacy_ok"),
            "fed_path": fed.get("fed_path"),
        }
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


def score_scorecard_util(
    out_dir: Path | None = None,
    *,
    root: Path | None = None,
    hits_doc: dict[str, Any] | None = None,
    router_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """F136: scorecard-gap ops skills injected vs tool_hit — inject ≠ utilization.

    F132–F135 adopt/federate/fitness scorecard skills; without mid-run tool
    measurement they are dashboard theater (Mem2Act / SkillsBench / F121 pattern).
    Gap only when ≥1 scorecard skill was selected and none fired tools.
    No scorecard inject → ok=True (no false gap).
    """
    root = root or _root()
    od = Path(out_dir) if out_dir else None
    router: dict[str, Any] = dict(router_doc or {})
    hits: dict[str, Any] = dict(hits_doc or {})
    if od:
        rp = od / "skill-router.json"
        hp = od / "skill-hits.json"
        if not router and rp.is_file():
            try:
                router = json.loads(rp.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                router = {}
        if not hits and hp.is_file():
            try:
                hits = json.loads(hp.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                hits = {}

    selected = list(router.get("selected") or [])
    always_sel = list(router.get("always_selected") or [])
    pool = list(dict.fromkeys([*selected, *always_sel]))
    sc_injected = [s for s in pool if is_scorecard_skill_id(s)]

    by_id: dict[str, dict[str, Any]] = {}
    for h in hits.get("hits") or []:
        if isinstance(h, dict) and h.get("id"):
            by_id[str(h["id"])] = h

    tool_hit_ids: list[str] = []
    prose_hit_ids: list[str] = []
    idle: list[str] = []
    for sid in sc_injected:
        h = by_id.get(sid) or {}
        if h.get("tool_hit"):
            tool_hit_ids.append(sid)
        else:
            idle.append(sid)
            if h.get("prose_hit") or h.get("hit"):
                prose_hit_ids.append(sid)

    n = len(sc_injected)
    tool_n = len(tool_hit_ids)
    util_rate = (tool_n / n) if n else 1.0
    gap = bool(n >= 1 and tool_n == 0)
    inject_chars = int(router.get("inject_chars") or router.get("chars") or 0)

    report = {
        "feature": "F136",
        "schema": SCHEMA,
        "scored_at": _now(),
        "scorecard_ids": sorted(SCORECARD_SKILL_IDS),
        "scorecard_injected": sc_injected,
        "scorecard_injected_n": n,
        "tool_hit_ids": tool_hit_ids,
        "prose_only_ids": prose_hit_ids,
        "idle_ids": idle,
        "tool_hit_n": tool_n,
        "util_rate": round(util_rate, 4),
        "utilization_gap": gap,
        "inject_chars": inject_chars,
        "ok": not gap,
        "score": round(util_rate, 4),
    }
    if od:
        try:
            od.mkdir(parents=True, exist_ok=True)
            (od / "scorecard-skill-util.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass
    return report


def federate_scorecard_util(
    util: dict[str, Any],
    *,
    root: Path | None = None,
    tenant: str = "",
    dest: Path | None = None,
) -> dict[str, Any]:
    """F136: privacy-safe federate of scorecard util themes (ids + bins only)."""
    import hashlib
    import re as _re

    root = root or _root()
    tenant = tenant or (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    th = ""
    if tenant:
        th = hashlib.sha256(tenant.encode("utf-8")).hexdigest()[:12]

    signals: list[dict[str, Any]] = []
    tool_ids = list(util.get("tool_hit_ids") or [])
    idle_ids = list(util.get("idle_ids") or [])
    util_rate = float(util.get("util_rate") or 0)
    inject_chars = int(util.get("inject_chars") or 0)

    def _slug(sid: str) -> str:
        return _re.sub(r"[^a-z0-9._-]+", "-", sid.lower())[:64]

    for sid in tool_ids:
        if "/" in sid or ".." in sid:
            continue
        sig: dict[str, Any] = {
            "id": _slug(f"scorecard-util-hit-{sid}"),
            "theme": _slug(sid),
            "cwe": [],
            "tags": [
                "scorecard_util",
                "scorecard_ops",
                "tool_outcome",
                "f136",
                "federated_skill",
            ],
            "keywords": [sid.replace("skill-", "")[:48], "scorecard-util", "tool-hit"],
            "path_basenames": [],
            "hits": 1,
            "tool_hits": 1,
            "source": "scorecard_skill_util",
            "tenants": 1,
            "util_rate_bin": "hit",
        }
        if th:
            sig["tenant_hashes"] = [th]
            sig["tenant_hash"] = th
        signals.append(sig)

    if util.get("utilization_gap"):
        gap_sig: dict[str, Any] = {
            "id": "scorecard-util-gap",
            "theme": "scorecard-util-gap",
            "cwe": [],
            "tags": [
                "scorecard_util",
                "utilization_gap",
                "f136",
                "federated_skill",
            ],
            "keywords": ["scorecard-util-gap", "idle-scorecard"],
            "path_basenames": [],
            "hits": 1,
            "source": "scorecard_skill_util",
            "tenants": 1,
            "idle_n": len(idle_ids),
            "injected_n": int(util.get("scorecard_injected_n") or 0),
            "inject_chars_bucket": (
                "0"
                if inject_chars <= 0
                else "lt2k"
                if inject_chars < 2000
                else "2k-4k"
                if inject_chars < 4000
                else "gte4k"
            ),
            "util_rate_bin": "gap",
        }
        if th:
            gap_sig["tenant_hashes"] = [th]
            gap_sig["tenant_hash"] = th
        signals.append(gap_sig)
    elif tool_ids:
        ok_sig: dict[str, Any] = {
            "id": "scorecard-util-ok",
            "theme": "scorecard-util-ok",
            "cwe": [],
            "tags": ["scorecard_util", "util_ok", "f136", "federated_skill"],
            "keywords": ["scorecard-util-ok"],
            "path_basenames": [],
            "hits": max(1, len(tool_ids)),
            "source": "scorecard_skill_util",
            "tenants": 1,
            "tool_hit_n": len(tool_ids),
            "util_rate_bin": (
                "full"
                if util_rate >= 0.99
                else "partial"
                if util_rate >= 0.34
                else "low"
            ),
        }
        if th:
            ok_sig["tenant_hashes"] = [th]
            ok_sig["tenant_hash"] = th
        signals.append(ok_sig)

    dest = dest or (root / "memory" / "federation" / "scorecard-util-signals.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(signals)
    privacy_ok = (
        "/Users/" not in blob
        and "/home/" not in blob
        and "C:\\\\Users" not in blob
        and (not tenant or tenant not in blob)
    )
    clean = []
    for s in signals:
        sb = json.dumps(s)
        if "/Users/" in sb or "/home/" in sb:
            continue
        if tenant and tenant in sb:
            continue
        clean.append(s)
    doc = {
        "schema_version": SCHEMA,
        "feature": "F136",
        "scope": "scorecard_skill_util",
        "updated_at": _now(),
        "count": len(clean),
        "privacy": "skill_id_util_bins_tenant_hash_only",
        "privacy_ok": privacy_ok and len(clean) == len(signals),
        "signals": clean,
    }
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    hub = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from federated_hub_ingest import ingest as hub_ingest  # type: ignore

        hub_raw = hub_ingest(
            root,
            clean,
            tenant=tenant,
            source_repo="scorecard_skill_util",
            write_tenant=bool(tenant),
        )
        if isinstance(hub_raw, dict):
            hub = {
                "feature": hub_raw.get("feature"),
                "global_count": hub_raw.get("global_count"),
                "privacy_ok": hub_raw.get("privacy_ok"),
                "tenant_count": hub_raw.get("tenant_count"),
            }
        else:
            hub = {"ok": True}
    except Exception as exc:
        hub = {"soft_error": str(exc)[:120]}

    return {
        "feature": "F136",
        "fed_path": "memory/federation/scorecard-util-signals.json",
        "fed_n": len(clean),
        "privacy_ok": doc["privacy_ok"],
        "hub": hub,
        "signals": clean,
    }


def cmd_scorecard_util(args: argparse.Namespace) -> int:
    """F136: score scorecard-gap skill tool utilization (+ soft federate)."""
    od = Path(args.out_dir) if args.out_dir else None
    if od is None and (os.environ.get("OUT_DIR") or "").strip():
        od = Path(os.environ["OUT_DIR"])
    if od is None:
        print(json.dumps({"feature": "F136", "error": "need --out-dir", "ok": False}))
        return 2
    report = score_scorecard_util(od, root=_root())
    do_fed = not getattr(args, "no_federate", False)
    raw_fed = (os.environ.get("TORII_SCORECARD_UTIL_FEDERATE") or "1").strip().lower()
    if raw_fed in _FALSEY:
        do_fed = False
    if do_fed:
        fed = federate_scorecard_util(report, root=_root())
        report["federate"] = {
            "fed_n": fed.get("fed_n"),
            "privacy_ok": fed.get("privacy_ok"),
            "fed_path": fed.get("fed_path"),
        }
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


def recovery_reprompt_enabled() -> bool:
    """F122: soft re-prompt once on recovery util gap (default on)."""
    raw = (os.environ.get("TORII_RECOVERY_SKILL_REPROMPT") or "1").strip().lower()
    return raw not in _FALSEY


def scorecard_reprompt_enabled() -> bool:
    """F137: soft re-prompt once on scorecard util gap (default on)."""
    raw = (os.environ.get("TORII_SCORECARD_SKILL_REPROMPT") or "1").strip().lower()
    return raw not in _FALSEY


def hub_gap_reprompt_enabled() -> bool:
    """F126: multi-tenant hub gap_pressure can bias F122 re-prompt (default on)."""
    raw = (os.environ.get("TORII_HUB_GAP_REPROMPT") or "1").strip().lower()
    return raw not in _FALSEY


def hub_gap_pressure_threshold() -> float:
    """F126: re-prompt idle recovery when hub gap_pressure ≥ thr (default 0.34)."""
    raw = (os.environ.get("TORII_HUB_GAP_PRESSURE_THR") or "0.34").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.34


RECOVERY_REPROMPT_MARKER = "<!-- torii-f122-recovery-skill-reprompt -->"
SCORECARD_REPROMPT_MARKER = "<!-- torii-f137-scorecard-skill-reprompt -->"


def decide_scorecard_reprompt(
    util: dict[str, Any],
    *,
    already_reprompted: bool = False,
    tool_call_turns: int = 0,
    reprompt_on: bool | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """F137: re-prompt when scorecard-gap ops skills injected but idle tools.

    Mirrors F122 recovery util re-prompt. Requires tools already ran (else F49).
    No scorecard inject → no re-prompt (not a false positive).
    Soft hub bias: if federated scorecard-util-gap exists, treat partial idle same.
    """
    on = scorecard_reprompt_enabled() if reprompt_on is None else bool(reprompt_on)
    gap = bool(util.get("utilization_gap"))
    n = int(util.get("scorecard_injected_n") or 0)
    tool_n = int(util.get("tool_hit_n") or 0)
    idle = list(util.get("idle_ids") or [])
    util_rate = float(util.get("util_rate") or 0.0)

    # soft multi-tenant scorecard util gap pressure from federation file
    hub_gap = False
    root = root or _root()
    fed = root / "memory" / "federation" / "scorecard-util-signals.json"
    if fed.is_file():
        try:
            doc = json.loads(fed.read_text(encoding="utf-8"))
            for s in doc.get("signals") or []:
                if not isinstance(s, dict):
                    continue
                tags = s.get("tags") or []
                sid = str(s.get("id") or s.get("theme") or "")
                if "utilization_gap" in tags or sid == "scorecard-util-gap":
                    hub_gap = True
                    break
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    out: dict[str, Any] = {
        "feature": "F137",
        "reprompt": 0,
        "enabled": on,
        "reason": "ok",
        "utilization_gap": gap,
        "scorecard_injected_n": n,
        "tool_hit_n": tool_n,
        "tool_call_turns": tool_call_turns,
        "already_reprompted": bool(already_reprompted),
        "util_rate": util.get("util_rate"),
        "inject_chars": util.get("inject_chars"),
        "idle_ids": idle,
        "hub_scorecard_util_gap": int(hub_gap),
    }
    if not on:
        out["reason"] = "reprompt_off"
        return out
    if already_reprompted:
        out["reason"] = "already_reprompted"
        return out
    if n < 1:
        out["reason"] = "no_scorecard_injected"
        return out
    if tool_call_turns < 1:
        out["reason"] = "zero_tools_defer_f49"
        return out

    # classic full gap
    if gap and tool_n < 1:
        out["reprompt"] = 1
        out["reason"] = "scorecard_utilization_gap"
        if hub_gap:
            out["reason"] = "scorecard_utilization_gap+fed_gap"
        return out

    # partial idle + federated gap themes (multi-tenant)
    if hub_gap and idle and util_rate < 0.99:
        out["reprompt"] = 1
        out["reason"] = "scorecard_fed_gap_idle"
        return out

    if tool_n >= 1 and not idle:
        out["reason"] = "scorecard_tools_used"
        return out
    if tool_n >= 1 and idle and not hub_gap:
        out["reason"] = "partial_util_no_fed_gap"
        return out
    if not gap:
        out["reason"] = "no_gap"
        return out
    out["reprompt"] = 1
    out["reason"] = "scorecard_utilization_gap"
    return out


def build_scorecard_reprompt_suffix(
    *,
    idle_ids: list[str] | None = None,
    tool_call_turns: int = 0,
    inject_chars: int = 0,
    hub_scorecard_util_gap: bool = False,
) -> str:
    idle = idle_ids or sorted(SCORECARD_SKILL_IDS)[:4]
    idle_s = ", ".join(f"`{i}`" for i in idle[:6])
    hub_line = ""
    if hub_scorecard_util_gap:
        hub_line = (
            "\n**Federated scorecard util gap** (F136/F137 multi-tenant) — "
            "other tenants also leave scorecard CLIs idle; call ops tools before finalizing.\n"
        )
    return (
        "\n\n---\n\n"
        f"{SCORECARD_REPROMPT_MARKER}\n\n"
        "## Scorecard skill soft re-prompt (F137)\n\n"
        f"Your previous reply used **{tool_call_turns} tool turns** but scorecard-gap "
        f"ops skill CLIs remain idle for: {idle_s} "
        f"(inject_chars≈{inject_chars}).\n"
        f"{hub_line}\n"
        "Before finalizing, call **at least one** of these once via terminal:\n\n"
        "```bash\n"
        "python3 scripts/torii.py doctor\n"
        "python3 scripts/torii.py scorecard --shallow\n"
        "python3 scripts/second_agent_critic.py demote-eval\n"
        "python3 scripts/workflow_as_code.py scorecard\n"
        "```\n\n"
        "Treat doctor/scorecard hits as **readiness hints only** — still require "
        "path:line evidence for security findings. Then rewrite the review.\n"
    )


def decide_recovery_reprompt(
    util: dict[str, Any],
    *,
    already_reprompted: bool = False,
    tool_call_turns: int = 0,
    reprompt_on: bool | None = None,
    hub: dict[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """F122/F126/F157/F161: re-prompt on util gap, hub pressure, or hub-archival idle.

    F122: recovery injected + tools ran + zero recovery tool hits → re-prompt.
    F126: partial util (some idle) + hub gap_pressure ≥ thr → re-prompt idle skills
    so multi-tenant gap themes bias the paid recovery attempt under F108.
    F157: hub-archival specifically idle (partial recovery util) → re-prompt for
    hub_boost archival even when memory/product CLIs already fired (live F155).
    F161: multi-tenant hub-archival gap_pressure biases F157 when local ha idle.
    """
    on = recovery_reprompt_enabled() if reprompt_on is None else bool(reprompt_on)
    gap = bool(util.get("utilization_gap"))
    n = int(util.get("recovery_injected_n") or 0)
    tool_n = int(util.get("tool_hit_n") or 0)
    idle = list(util.get("idle_ids") or [])
    util_rate = float(util.get("util_rate") or 0.0)
    ha_gap = bool(util.get("hub_archival_util_gap"))
    ha_reprompt_on = hub_archival_reprompt_enabled()

    # F126: hub gap pressure (soft load)
    hub_report = hub
    if hub_report is None and hub_gap_reprompt_enabled() and recovery_hub_enabled():
        try:
            hub_report = post_score_recovery_hub(root=root or _root())
        except Exception:
            hub_report = {}
    gap_pressure = float((hub_report or {}).get("gap_pressure") or 0.0)
    thr = hub_gap_pressure_threshold()
    hub_bias_on = hub_gap_reprompt_enabled()

    # F161: multi-tenant hub-archival util gap pressure
    ha_hub: dict[str, Any] = {}
    if hub_archival_hub_enabled():
        try:
            ha_hub = post_score_hub_archival_hub(root=root or _root())
        except Exception:
            ha_hub = {}
    ha_gap_pressure = float((ha_hub or {}).get("gap_pressure") or 0.0)
    ha_thr = hub_archival_hub_pressure_threshold()
    ha_hub_high = bool((ha_hub or {}).get("high")) or (
        ha_gap_pressure >= ha_thr and int((ha_hub or {}).get("gap_hits") or 0) >= 1
    )

    out: dict[str, Any] = {
        "feature": "F122",
        "feature_hub_gap": "F126" if hub_bias_on else None,
        "feature_hub_archival_reprompt": FEATURE_HUB_ARCHIVAL_REPROMPT
        if ha_reprompt_on
        else None,
        "feature_hub_archival_hub": FEATURE_HUB_ARCHIVAL_HUB
        if hub_archival_hub_enabled()
        else None,
        "reprompt": 0,
        "enabled": on,
        "reason": "ok",
        "utilization_gap": gap,
        "recovery_injected_n": n,
        "tool_hit_n": tool_n,
        "tool_call_turns": tool_call_turns,
        "already_reprompted": bool(already_reprompted),
        "util_rate": util.get("util_rate"),
        "inject_chars": util.get("inject_chars"),
        "idle_ids": idle,
        "hub_gap_pressure": gap_pressure,
        "hub_gap_thr": thr,
        "hub_gap_bias": 0,
        "hub_archival_util_gap": int(ha_gap),
        "hub_archival_injected": int(bool(util.get("hub_archival_injected"))),
        "hub_archival_tool_hit": int(bool(util.get("hub_archival_tool_hit"))),
        "hub_archival_gap_pressure": ha_gap_pressure,
        "hub_archival_hub_thr": ha_thr,
        "hub_archival_hub_high": int(ha_hub_high),
        "hub_archival_hub_delta": int(
            ((ha_hub or {}).get("priority_deltas") or {}).get(HUB_ARCHIVAL_SKILL_ID)
            or 0
        ),
        "budget_kind": "f122",
    }
    if not on:
        out["reason"] = "reprompt_off"
        return out
    if already_reprompted:
        out["reason"] = "already_reprompted"
        return out
    if n < 1:
        out["reason"] = "no_recovery_injected"
        return out
    if tool_call_turns < 1:
        # F49 owns zero-tool recovery
        out["reason"] = "zero_tools_defer_f49"
        return out

    # F122 classic: full local gap (no recovery tools at all)
    if gap and tool_n < 1:
        out["reprompt"] = 1
        out["reason"] = "recovery_utilization_gap"
        if hub_bias_on and gap_pressure >= thr:
            out["hub_gap_bias"] = 1
            out["reason"] = "recovery_utilization_gap+hub_gap_pressure"
        # full gap that includes hub-archival still tags f157 for hermes budget kind
        if ha_gap and ha_reprompt_on:
            out["budget_kind"] = "f157"
            out["reason"] = f"{out['reason']}+hub_archival_util_gap"
        return out

    # F126: partial util — some recovery tools used, some idle; hub says gap common
    if (
        hub_bias_on
        and idle
        and gap_pressure >= thr
        and util_rate < 0.99
        and tool_n >= 0  # tools may have fired other recovery skills
    ):
        out["reprompt"] = 1
        out["hub_gap_bias"] = 1
        out["reason"] = "hub_gap_pressure_idle"
        if ha_gap and ha_reprompt_on:
            out["budget_kind"] = "f157"
            out["reason"] = "hub_gap_pressure_idle+hub_archival_util_gap"
        return out

    # F157: hub-archival inject ≠ hub_boost while other recovery tools may have fired
    if ha_reprompt_on and ha_gap:
        out["reprompt"] = 1
        out["reason"] = "hub_archival_util_gap"
        out["budget_kind"] = "f157"
        out["feature"] = FEATURE_HUB_ARCHIVAL_REPROMPT
        if ha_hub_high:
            out["reason"] = "hub_archival_util_gap+hub_archival_hub_pressure"
            out["feature"] = FEATURE_HUB_ARCHIVAL_HUB
        return out

    # F161: multi-tenant hub-archival gap pressure + local hub-archival idle
    # (covers edge where ha_gap flag missing but idle_ids includes hub-archival)
    if (
        ha_reprompt_on
        and ha_hub_high
        and HUB_ARCHIVAL_SKILL_ID in idle
        and int(util.get("hub_archival_injected") or 0)
    ):
        out["reprompt"] = 1
        out["reason"] = "hub_archival_hub_pressure_idle"
        out["budget_kind"] = "f157"
        out["feature"] = FEATURE_HUB_ARCHIVAL_HUB
        return out

    if tool_n >= 1 and not idle:
        out["reason"] = "recovery_tools_used"
        return out
    if tool_n >= 1 and idle and (not hub_bias_on or gap_pressure < thr):
        # F161: multi-tenant ha pressure can still re-prompt hub-archival idle
        if (
            ha_reprompt_on
            and ha_hub_high
            and HUB_ARCHIVAL_SKILL_ID in idle
        ):
            out["reprompt"] = 1
            out["reason"] = "hub_archival_hub_pressure_idle"
            out["budget_kind"] = "f157"
            out["feature"] = FEATURE_HUB_ARCHIVAL_HUB
            return out
        out["reason"] = "partial_util_hub_below_thr"
        return out
    if not gap:
        out["reason"] = "no_gap"
        return out
    out["reprompt"] = 1
    out["reason"] = "recovery_utilization_gap"
    return out


def build_recovery_reprompt_suffix(
    *,
    idle_ids: list[str] | None = None,
    tool_call_turns: int = 0,
    inject_chars: int = 0,
    hub_gap_pressure: float = 0.0,
    hub_gap_bias: bool = False,
    hub_archival_util_gap: bool = False,
) -> str:
    idle = idle_ids or sorted(RECOVERY_SKILL_IDS)
    idle_s = ", ".join(f"`{i}`" for i in idle[:6])
    hub_line = ""
    if hub_gap_bias or hub_gap_pressure >= hub_gap_pressure_threshold():
        hub_line = (
            f"\n**Hub gap pressure={hub_gap_pressure:.2f}** (F126 multi-tenant) — "
            "other tenants also under-use recovery CLIs; treat this as a hard "
            "tool call before finalizing.\n"
        )
    # F155/F157: when hub-archival idle, nudge hub_boost archival specifically
    ha_line = ""
    ha_idle = (
        hub_archival_util_gap
        or HUB_ARCHIVAL_SKILL_ID in (idle_ids or [])
        or HUB_ARCHIVAL_SKILL_ID in idle
    )
    if ha_idle:
        ha_line = (
            "\n**F157 hub-archival util gap:** call `archival_memory_search` with hub warm "
            "themes so `hub_boost` evidence appears (generic memory CLI is not enough).\n"
        )
    if hub_archival_util_gap and not hub_gap_bias:
        title = "## Hub-archival recovery soft re-prompt (F157)\n\n"
    elif hub_gap_bias:
        title = "## Recovery skill soft re-prompt (F122/F126)\n\n"
    else:
        title = "## Recovery skill soft re-prompt (F122)\n\n"
    return (
        "\n\n---\n\n"
        f"{RECOVERY_REPROMPT_MARKER}\n\n"
        f"{title}"
        f"Your previous reply used **{tool_call_turns} tool turns** but recovery "
        f"skill CLIs remain idle for: {idle_s} "
        f"(inject_chars≈{inject_chars}).\n"
        f"{hub_line}"
        f"{ha_line}\n"
        "Before finalizing, call **at least one** of these once via terminal:\n\n"
        "```bash\n"
        "python3 scripts/torii.py memory -- search -- -q \"auth OR sql OR pickle OR secret\"\n"
        "python3 scripts/archival_memory_search.py auto  # hub warm / hub_boost (F155)\n"
        "python3 scripts/torii.py doctor\n"
        "python3 scripts/second_agent_critic.py score --review REVIEW.md\n"
        "```\n\n"
        "Treat memory/doctor hits as **hints only** — still require path:line evidence. "
        "Then rewrite the review with evidence-backed findings.\n"
    )


def write_recovery_reprompt_prompt(
    *,
    prompt_in: Path,
    prompt_out: Path,
    idle_ids: list[str] | None = None,
    tool_call_turns: int = 0,
    inject_chars: int = 0,
    hub_gap_pressure: float = 0.0,
    hub_gap_bias: bool = False,
    hub_archival_util_gap: bool = False,
    scorecard_idle_ids: list[str] | None = None,
    scorecard_gap: bool = False,
    hub_scorecard_util_gap: bool = False,
    include_recovery: bool = True,
) -> Path:
    base = prompt_in.read_text(encoding="utf-8", errors="replace")
    text = base
    if include_recovery and RECOVERY_REPROMPT_MARKER not in text:
        text = text.rstrip() + build_recovery_reprompt_suffix(
            idle_ids=idle_ids,
            tool_call_turns=tool_call_turns,
            inject_chars=inject_chars,
            hub_gap_pressure=hub_gap_pressure,
            hub_gap_bias=hub_gap_bias,
            hub_archival_util_gap=hub_archival_util_gap,
        )
    # F137: append scorecard ops nudge when scorecard util gap
    if scorecard_gap and SCORECARD_REPROMPT_MARKER not in text:
        text = text.rstrip() + build_scorecard_reprompt_suffix(
            idle_ids=scorecard_idle_ids,
            tool_call_turns=tool_call_turns,
            inject_chars=inject_chars,
            hub_scorecard_util_gap=hub_scorecard_util_gap,
        )
    if not text.endswith("\n"):
        text += "\n"
    prompt_out.parent.mkdir(parents=True, exist_ok=True)
    prompt_out.write_text(text, encoding="utf-8")
    return prompt_out


def cmd_federate_util(args: argparse.Namespace) -> int:
    """F124: federate from out_dir recovery-skill-util.json or --util-json."""
    root = _root()
    util: dict[str, Any] = {}
    if args.util_json and Path(args.util_json).is_file():
        util = json.loads(Path(args.util_json).read_text(encoding="utf-8"))
    else:
        od = Path(args.out_dir) if args.out_dir else Path(os.environ.get("OUT_DIR") or ".")
        up = od / "recovery-skill-util.json"
        if up.is_file():
            util = json.loads(up.read_text(encoding="utf-8"))
        else:
            util = score_recovery_util(od, root=root)
    fed = federate_recovery_util(util, root=root)
    print(json.dumps(fed, indent=2))
    return 0 if fed.get("privacy_ok") else 1


def cmd_reprompt_decide(args: argparse.Namespace) -> int:
    """F122/F126/F137: key=value decide soft re-prompt (recovery + scorecard util)."""
    od = Path(args.out_dir) if args.out_dir else Path(os.environ.get("OUT_DIR") or ".")
    already = False
    if args.already_env and Path(args.already_env).is_file():
        txt = Path(args.already_env).read_text(encoding="utf-8", errors="replace")
        if "attempted=1" in txt or "reprompt=1" in txt:
            already = True
    # ensure util scored
    util = score_recovery_util(od, root=_root())
    sc_util = score_scorecard_util(od, root=_root())
    # tool turns from agent-loop if present
    turns = 0
    loop = od / "agent-loop" / "agent-loop.json"
    if not loop.is_file():
        loop = od / "agent-loop.json"
    if loop.is_file():
        try:
            data = json.loads(loop.read_text(encoding="utf-8"))
            turns = int(data.get("tool_call_turns") or 0)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            turns = 0
    if args.tool_turns is not None:
        turns = int(args.tool_turns)
    # score hits if missing so util can see tools
    if not (od / "skill-hits.json").is_file() and args.review:
        try:
            score_hits(
                Path(args.review),
                root=_root(),
                out_dir=od,
                agent_loop=loop if loop.is_file() else None,
            )
            util = score_recovery_util(od, root=_root())
            sc_util = score_scorecard_util(od, root=_root())
        except Exception:
            pass
    dec = decide_recovery_reprompt(
        util, already_reprompted=already, tool_call_turns=turns, root=_root()
    )
    sc_dec = decide_scorecard_reprompt(
        sc_util, already_reprompted=already, tool_call_turns=turns, root=_root()
    )
    # F137: OR scorecard gap into composite re-prompt (one paid attempt covers both)
    composite = dict(dec)
    composite["feature_scorecard"] = "F137"
    composite["scorecard_reprompt"] = sc_dec
    composite["scorecard_utilization_gap"] = sc_dec.get("utilization_gap")
    composite["scorecard_idle_ids"] = sc_dec.get("idle_ids") or []
    composite["scorecard_injected_n"] = sc_dec.get("scorecard_injected_n")
    composite["hub_scorecard_util_gap"] = sc_dec.get("hub_scorecard_util_gap")
    if int(dec.get("reprompt") or 0) == 1 and int(sc_dec.get("reprompt") or 0) == 1:
        composite["reason"] = f"{dec.get('reason')}+{sc_dec.get('reason')}"
        composite["reprompt"] = 1
    elif int(sc_dec.get("reprompt") or 0) == 1 and int(dec.get("reprompt") or 0) == 0:
        composite["reprompt"] = 1
        composite["reason"] = sc_dec.get("reason")
        # surface scorecard idle as idle_ids when recovery has none
        if not composite.get("idle_ids"):
            composite["idle_ids"] = list(sc_dec.get("idle_ids") or [])
        composite["utilization_gap"] = True
        composite["scorecard_only"] = 1
    # key=value for shell (like F106)
    print(f"reprompt={composite['reprompt']}")
    print(f"enabled={int(bool(composite['enabled']) or scorecard_reprompt_enabled())}")
    print(f"reason={composite['reason']}")
    print(f"utilization_gap={int(bool(composite['utilization_gap']))}")
    print(f"tool_hit_n={composite['tool_hit_n']}")
    print(f"recovery_injected_n={composite['recovery_injected_n']}")
    print(f"tool_call_turns={composite['tool_call_turns']}")
    print(f"inject_chars={composite.get('inject_chars') or 0}")
    print(f"util_rate={composite.get('util_rate')}")
    print(f"idle_ids={','.join(composite.get('idle_ids') or [])}")
    print(f"hub_gap_pressure={composite.get('hub_gap_pressure')}")
    print(f"hub_gap_thr={composite.get('hub_gap_thr')}")
    print(f"hub_gap_bias={composite.get('hub_gap_bias')}")
    print(f"feature_hub_gap={composite.get('feature_hub_gap') or ''}")
    print(f"scorecard_reprompt={int(sc_dec.get('reprompt') or 0)}")
    print(f"scorecard_utilization_gap={int(bool(sc_dec.get('utilization_gap')))}")
    print(f"scorecard_injected_n={sc_dec.get('scorecard_injected_n') or 0}")
    print(f"scorecard_idle_ids={','.join(sc_dec.get('idle_ids') or [])}")
    print(f"hub_scorecard_util_gap={int(sc_dec.get('hub_scorecard_util_gap') or 0)}")
    print(f"scorecard_only={int(composite.get('scorecard_only') or 0)}")
    print(f"hub_archival_util_gap={int(composite.get('hub_archival_util_gap') or 0)}")
    print(f"hub_archival_injected={int(composite.get('hub_archival_injected') or 0)}")
    print(f"hub_archival_tool_hit={int(composite.get('hub_archival_tool_hit') or 0)}")
    print(f"budget_kind={composite.get('budget_kind') or 'f122'}")
    print(
        f"feature_hub_archival_reprompt={composite.get('feature_hub_archival_reprompt') or ''}"
    )
    print("feature=F122")
    print("feature_scorecard=F137")
    if str(composite.get("budget_kind") or "") == "f157" or int(
        composite.get("hub_archival_util_gap") or 0
    ):
        print(f"feature_f157={FEATURE_HUB_ARCHIVAL_REPROMPT}")
    # soft write decide artifacts for traces
    try:
        (od / "recovery-reprompt-decide.json").write_text(
            json.dumps(composite, indent=2) + "\n", encoding="utf-8"
        )
        (od / "scorecard-reprompt-decide.json").write_text(
            json.dumps(sc_dec, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        pass
    return 0


def cmd_hub_score(args: argparse.Namespace) -> int:
    """F125/F126/F138: post-score hub recovery + scorecard util → priority deltas."""
    root = _root()
    hub = post_score_recovery_hub(root=root)
    inj = None
    inject_path = (getattr(args, "inject", None) or "").strip()
    if inject_path:
        inj = inject_recovery_hub_into_prompt(Path(inject_path), hub=hub, root=root)
        hub["inject"] = {
            "injected": inj.get("injected"),
            "artifact": inj.get("artifact"),
        }
    # F126: soft ingest hub tool themes into skill fitness ledger
    fitness_ingest = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from skill_fitness import ingest_hub_recovery  # type: ignore

        fitness_ingest = ingest_hub_recovery(hub, root=root)
        hub["fitness_ingest"] = {
            k: fitness_ingest.get(k)
            for k in ("feature", "ingested_n", "skills", "privacy_ok", "ledger")
            if k in fitness_ingest
        }
    except Exception as exc:
        hub["fitness_ingest"] = {"soft_error": str(exc)[:120]}
    # F138: scorecard hub post-score (+ optional inject + fitness)
    sc_hub = post_score_scorecard_hub(root=root)
    if inject_path and scorecard_hub_enabled():
        sc_inj = inject_scorecard_hub_into_prompt(
            Path(inject_path), hub=sc_hub, root=root
        )
        sc_hub["inject"] = {
            "injected": sc_inj.get("injected"),
            "chars": sc_inj.get("chars"),
        }
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from skill_fitness import ingest_scorecard_skills  # type: ignore

        # synthesize skill_ids from hub for fitness shield
        sc_doc = {
            "privacy_ok": sc_hub.get("privacy_ok", True),
            "skill_ids": list((sc_hub.get("skills") or {}).keys()),
            "signals": [
                {
                    "id": f"scorecard-hub-{sid}"[:64],
                    "theme": sid,
                    "tags": ["scorecard_ops", "f138", "tool_outcome"],
                    "keywords": [sid],
                    "path_basenames": [],
                    "hits": int((sc_hub.get("skills") or {}).get(sid, {}).get("hits") or 1),
                    "tool_hits": int(
                        (sc_hub.get("skills") or {}).get(sid, {}).get("tool_hits") or 1
                    ),
                }
                for sid in (sc_hub.get("skills") or {})
            ],
        }
        sc_fit = ingest_scorecard_skills(sc_doc, root=root, save=True)
        sc_hub["fitness_ingest"] = {
            k: sc_fit.get(k)
            for k in ("feature", "ingested_n", "skills", "privacy_ok", "scorecard_ops_ok")
            if k in sc_fit
        }
    except Exception as exc:
        sc_hub["fitness_ingest"] = {"soft_error": str(exc)[:120]}
    hub["scorecard_hub"] = {
        k: sc_hub.get(k)
        for k in (
            "feature",
            "skill_n",
            "priority_deltas",
            "gap_pressure",
            "privacy_ok",
            "hub_ok",
            "fitness_ingest",
            "inject",
        )
    }
    # OUT_DIR artifact
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        try:
            p = Path(od) / "recovery-hub-score.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(hub, indent=2) + "\n", encoding="utf-8")
            hub["artifact"] = str(p)
            p2 = Path(od) / "scorecard-hub-score.json"
            p2.write_text(json.dumps(sc_hub, indent=2) + "\n", encoding="utf-8")
            hub["scorecard_artifact"] = "scorecard-hub-score.json"
        except OSError:
            pass
    print(json.dumps(hub, indent=2))
    return 0 if hub.get("privacy_ok") and sc_hub.get("privacy_ok", True) else 1


def cmd_scorecard_hub_score(args: argparse.Namespace) -> int:
    """F138: post-score hub scorecard util themes only."""
    root = _root()
    sc_hub = post_score_scorecard_hub(root=root)
    inject_path = (getattr(args, "inject", None) or "").strip()
    if inject_path:
        sc_inj = inject_scorecard_hub_into_prompt(
            Path(inject_path), hub=sc_hub, root=root
        )
        sc_hub["inject"] = {
            "injected": sc_inj.get("injected"),
            "chars": sc_inj.get("chars"),
        }
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        try:
            p = Path(od) / "scorecard-hub-score.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(sc_hub, indent=2) + "\n", encoding="utf-8")
            sc_hub["artifact"] = str(p)
        except OSError:
            pass
    print(json.dumps(sc_hub, indent=2))
    return 0 if sc_hub.get("privacy_ok") else 1


def _flag_true(val: Any) -> bool:
    """Parse CLI/env flag: only 1/true/yes (not bare truthy strings like '0')."""
    return str(val or "").strip().lower() in ("1", "true", "yes", "on")


def cmd_reprompt_write(args: argparse.Namespace) -> int:
    """F122/F126/F137: write nudged prompt for recovery + scorecard skill re-run."""
    idle = [x for x in (args.idle_ids or "").split(",") if x.strip()]
    sc_idle = [
        x
        for x in (getattr(args, "scorecard_idle_ids", None) or "").split(",")
        if x.strip()
    ]
    hub_gp = 0.0
    hub_bias = False
    try:
        hub_gp = float(getattr(args, "hub_gap_pressure", 0) or 0)
    except (TypeError, ValueError):
        hub_gp = 0.0
    if _flag_true(getattr(args, "hub_gap_bias", "0")):
        hub_bias = True
    # soft load from env if shell passed hub keys
    env_gp = (os.environ.get("TORII_HUB_GAP_PRESSURE") or "").strip()
    if env_gp and hub_gp <= 0:
        try:
            hub_gp = float(env_gp)
        except ValueError:
            pass
    if _flag_true(os.environ.get("TORII_HUB_GAP_BIAS")):
        hub_bias = True
    sc_gap = False
    if _flag_true(getattr(args, "scorecard_gap", "0")):
        sc_gap = True
    if _flag_true(os.environ.get("TORII_SCORECARD_UTIL_GAP")):
        sc_gap = True
    hub_sc_gap = False
    if _flag_true(getattr(args, "hub_scorecard_util_gap", "0")):
        hub_sc_gap = True
    if _flag_true(os.environ.get("TORII_HUB_SCORECARD_UTIL_GAP")):
        hub_sc_gap = True
    include_recovery = True
    if _flag_true(getattr(args, "scorecard_only", "0")):
        include_recovery = False
        sc_gap = True
    # if scorecard idle provided without flag, still include scorecard section
    if sc_idle:
        sc_gap = True
    # F157: hub-archival util gap from CLI/env
    ha_gap = False
    if _flag_true(getattr(args, "hub_archival_util_gap", "0")):
        ha_gap = True
    if _flag_true(os.environ.get("TORII_HUB_ARCHIVAL_UTIL_GAP")):
        ha_gap = True
    if HUB_ARCHIVAL_SKILL_ID in idle:
        ha_gap = True
    path = write_recovery_reprompt_prompt(
        prompt_in=Path(args.prompt_in),
        prompt_out=Path(args.prompt_out),
        idle_ids=idle or None,
        tool_call_turns=int(args.tool_turns or 0),
        inject_chars=int(args.inject_chars or 0),
        hub_gap_pressure=hub_gp,
        hub_gap_bias=hub_bias,
        hub_archival_util_gap=ha_gap,
        scorecard_idle_ids=sc_idle or None,
        scorecard_gap=sc_gap,
        hub_scorecard_util_gap=hub_sc_gap,
        include_recovery=include_recovery,
    )
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    print(
        json.dumps(
            {
                "feature": "F122",
                "feature_scorecard": "F137" if sc_gap else None,
                "feature_hub_gap": "F126" if hub_bias or hub_gp > 0 else None,
                "feature_hub_archival_reprompt": FEATURE_HUB_ARCHIVAL_REPROMPT
                if ha_gap
                else None,
                "prompt_out": str(path),
                "hub_gap_pressure": hub_gp,
                "hub_gap_bias": int(hub_bias),
                "hub_archival_util_gap": int(ha_gap),
                "scorecard_gap": int(sc_gap),
                "scorecard_marker": int(SCORECARD_REPROMPT_MARKER in text),
                "f157_marker": int("F157" in text),
                "ok": path.is_file(),
            }
        )
    )
    return 0 if path.is_file() else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: py paths prefer chain/exploit skills; md-only prefers always; hits score."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        active = root / "agent" / "skills" / "active"
        active.mkdir(parents=True)
        # minimal skills
        (active / "skill-f74-prefer-chain-json.md").write_text(
            """---
id: skill-f74-prefer-chain-json
title: Prefer chain JSON over inference
themes: taint,chain,python
---

## Skill: prefer-chain-json

Align findings with **candidate source/sink pairs** and taint chain JSON.
Label **unvalidated** when no candidate matches.
""",
            encoding="utf-8",
        )
        (active / "skill-f74-exploit-scenario.md").write_text(
            """---
id: skill-f74-exploit-scenario
title: Exploit scenario language
themes: exploit,attacker,python
---

## Skill: exploit-scenario

Add one **attacker trigger** sentence for REQUEST CHANGES on a confirmed sink.
""",
            encoding="utf-8",
        )
        (active / "skill-tool-depth-hunks.md").write_text(
            """---
id: skill-tool-depth-hunks
title: Tool depth prefer diff hunks
always: true
---

## Skill: tool-depth-hunks

Open the unified **diff** file first for exact hunks. Use `rg -n` then `sed -n`.
""",
            encoding="utf-8",
        )
        (active / "skill-docs-only.md").write_text(
            """---
id: skill-docs-only
title: Docs prose style
themes: docs,markdown
---

## Skill: docs-only

Only relevant for markdown documentation tone.
""",
            encoding="utf-8",
        )
        # F114: memory-CLI recovery skill (always-on + tool outcome)
        (active / "skill-prefer-memory-cli-early.md").write_text(
            """---
id: skill-prefer-memory-cli-early
title: Call torii product/memory CLI early mid-review
always: true
themes: memory,cli,search
---

## Skill: prefer-memory-cli-early (F112/F113)

Call `python3 scripts/torii.py memory -- search` before finishing findings.
Also `python3 scripts/torii_memory.py search` is valid.
""",
            encoding="utf-8",
        )
        # F119: product-cli always candidate (higher prio than tool-depth)
        (active / "skill-prefer-product-cli.md").write_text(
            """---
id: skill-prefer-product-cli
title: Call torii product CLI doctor/status early
always: true
always_priority: 90
themes: product,cli,doctor
---

## Skill: prefer-product-cli (F117/F118)

Call `python3 scripts/torii.py doctor` early for readiness.
""",
            encoding="utf-8",
        )

        os.environ["TORII_ROOT"] = str(root)
        os.environ["TORII_SKILL_ROUTER"] = "1"
        os.environ["TORII_SKILL_ROUTER_MAX"] = "3"
        os.environ["TORII_SKILL_ROUTER_ALWAYS_MAX"] = "2"  # F119: budget 2 always slots
        os.environ["TORII_SKILL_ROUTER_REPLACE"] = "1"
        os.environ["TORII_SKILL_TOOL_OUTCOME"] = "1"

        cards = catalog(root)
        assert len(cards) == 6
        mem_card = next(c for c in cards if c.id == "skill-prefer-memory-cli-early")
        prod_card = next(c for c in cards if c.id == "skill-prefer-product-cli")
        memory_always_ok = mem_card.always is True
        product_always_ok = prod_card.always is True

        py_paths = ["src/app/auth.py", "lib/db.py", "tests/test_auth.py"]
        sel_py = select_skills(cards, py_paths, max_full=3, max_always=2)
        sel_ids = set(sel_py["selected"])
        always_sel = set(sel_py.get("always_selected") or [])
        always_def = set(sel_py.get("always_deferred") or [])
        # F119: top-priority recovery always (memory+product), tool-depth deferred
        always_ok = (
            "skill-prefer-memory-cli-early" in always_sel
            and "skill-prefer-product-cli" in always_sel
            and "skill-tool-depth-hunks" in always_def
        )
        # security skills preferred for remaining full slot
        sec_ok = bool(sel_ids & {"skill-f74-prefer-chain-json", "skill-f74-exploit-scenario"})
        # docs-only should rank low vs py code
        docs_not_first = sel_py["selected"][0] != "skill-docs-only" if sel_py["selected"] else True

        md_paths = ["README.md", "docs/guide.md"]
        sel_md = select_skills(cards, md_paths, max_full=3, max_always=2)
        md_ids = set(sel_md["selected"])
        always_in_md = "skill-prefer-memory-cli-early" in md_ids

        # inject
        prompt = root / "prompt.md"
        prompt.write_text(
            f"{F69_OPEN}\n## Evolved skills (bulk dump)\nfull dump of everything\n{F69_CLOSE}\n\n## PR metadata\nrepo: x\n",
            encoding="utf-8",
        )
        inj = inject_into_prompt(prompt, root=root, paths=py_paths)
        text = prompt.read_text(encoding="utf-8")
        inject_ok = MARKER_OPEN in text and "Skill router (F84" in text
        stripped_ok = inj.get("stripped_f69") is True and F69_OPEN not in text
        selected_body_ok = any(s in text for s in inj["selected"])

        # score hits: good review mentions chain/attacker/diff
        good_review = root / "good.md"
        good_review.write_text(
            """# Review
Found SQLi via source/sink taint chain. Attacker trigger: POST /login.
Opened unified diff hunks with rg -n.
Verdict: REQUEST_CHANGES
""",
            encoding="utf-8",
        )
        out_dir = root / "out"
        out_dir.mkdir()
        (out_dir / "skill-router.json").write_text(
            json.dumps({"selected": inj["selected"]}), encoding="utf-8"
        )
        good_hits = score_hits(
            good_review, root=root, selected=inj["selected"], out_dir=out_dir
        )

        weak_review = root / "weak.md"
        weak_review.write_text("# LGTM looks fine\nAPPROVE\n", encoding="utf-8")
        weak_hits = score_hits(
            weak_review, root=root, selected=inj["selected"], out_dir=None
        )

        # F114: tool-outcome — memory skill hits via agent-loop even if prose silent
        tool_loop = {
            "schema_version": 1,
            "tool_call_turns": 2,
            "steps": [
                {
                    "step": 0,
                    "kind": "assistant_tool_calls",
                    "tool_calls": [
                        {
                            "name": "terminal",
                            "arguments_preview": json.dumps(
                                {
                                    "command": (
                                        "python3 scripts/torii.py memory -- "
                                        'search -- -q "auth sql"'
                                    )
                                }
                            ),
                        }
                    ],
                }
            ],
            "messages": [],
        }
        (out_dir / "agent-loop").mkdir(exist_ok=True)
        (out_dir / "agent-loop" / "agent-loop.json").write_text(
            json.dumps(tool_loop) + "\n", encoding="utf-8"
        )
        silent_review = root / "silent.md"
        # Avoid prose stop-words and skill keywords (memory/search/torii)
        silent_review.write_text("# Verdict\nLGTM no findings.\nAPPROVE\n", encoding="utf-8")
        tool_sel = [
            "skill-prefer-memory-cli-early",
            "skill-tool-depth-hunks",
        ]
        tool_hits = score_hits(
            silent_review,
            root=root,
            selected=tool_sel,
            out_dir=out_dir,
        )
        mem_hit = next(
            (h for h in tool_hits.get("hits") or [] if h["id"] == "skill-prefer-memory-cli-early"),
            {},
        )
        tool_outcome_ok = bool(mem_hit.get("tool_hit")) and bool(mem_hit.get("hit"))
        tool_rate_ok = float(tool_hits.get("tool_hit_n") or 0) >= 1
        # weak: no tools, no prose → no hit for memory skill
        weak_tool = score_hits(
            silent_review,
            root=root,
            selected=["skill-prefer-memory-cli-early"],
            tool_blob="",  # force empty
        )
        weak_tool_ok = not any(h.get("hit") for h in weak_tool.get("hits") or [])

        good_rate = float(good_hits["hit_rate"])
        weak_rate = float(weak_hits["hit_rate"])
        rate_ok = good_rate > weak_rate and good_rate >= 0.3
        privacy_ok = not any(
            "/Users/" in str(x) for x in good_hits.get("federated_skill_themes") or []
        )
        memory_in_py = "skill-prefer-memory-cli-early" in set(inj["selected"])

        product_in_py = "skill-prefer-product-cli" in set(inj["selected"])
        # F120: fat always body is compacted under ALWAYS_MAX_CHARS
        fat = active / "skill-prefer-memory-cli-early.md"
        if fat.is_file():
            # append background bloat then re-inject
            fat.write_text(
                fat.read_text(encoding="utf-8")
                + "\n\n"
                + ("Background context not needed for the agent loop. " * 30)
                + "\n",
                encoding="utf-8",
            )
        os.environ["TORII_SKILL_COMPACT"] = "1"
        os.environ["TORII_SKILL_ALWAYS_MAX_CHARS"] = "480"
        cards2 = catalog(root)
        inj2 = inject_into_prompt(prompt, root=root, paths=py_paths)
        text2 = prompt.read_text(encoding="utf-8")
        compact_ok = int(inj2.get("f120_chars_saved") or 0) >= 1
        compact_marker_ok = "F120 compacted" in text2 or compact_ok
        # without compact, inject would be larger
        os.environ["TORII_SKILL_COMPACT"] = "0"
        inj3 = inject_into_prompt(prompt, root=root, paths=py_paths)
        chars_compact = int(inj2.get("chars") or 0)
        chars_full = int(inj3.get("chars") or 0)
        # restore compact on
        os.environ["TORII_SKILL_COMPACT"] = "1"
        smaller_ok = chars_compact <= chars_full

        # F121: recovery util — with tools no gap; silent without tools → gap
        util_out = root / "util-out"
        util_out.mkdir(exist_ok=True)
        (util_out / "skill-router.json").write_text(
            json.dumps(
                {
                    "selected": [
                        "skill-prefer-memory-cli-early",
                        "skill-prefer-product-cli",
                    ],
                    "always_selected": [
                        "skill-prefer-memory-cli-early",
                        "skill-prefer-product-cli",
                    ],
                    "inject_chars": int(inj2.get("inject_chars") or chars_compact or 0),
                    "f120_chars_saved": int(inj2.get("f120_chars_saved") or 0),
                }
            ),
            encoding="utf-8",
        )
        (util_out / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": "skill-prefer-memory-cli-early",
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                        },
                        {
                            "id": "skill-prefer-product-cli",
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                        },
                    ],
                    "tool_hit_n": 2,
                }
            ),
            encoding="utf-8",
        )
        util_good = score_recovery_util(util_out, root=root)
        util_gap_out = root / "util-gap"
        util_gap_out.mkdir(exist_ok=True)
        (util_gap_out / "skill-router.json").write_text(
            json.dumps(
                {
                    "selected": ["skill-prefer-product-cli"],
                    "always_selected": ["skill-prefer-product-cli"],
                    "inject_chars": 500,
                }
            ),
            encoding="utf-8",
        )
        (util_gap_out / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": "skill-prefer-product-cli",
                            "hit": False,
                            "tool_hit": False,
                            "prose_hit": False,
                        }
                    ],
                    "tool_hit_n": 0,
                }
            ),
            encoding="utf-8",
        )
        util_gap = score_recovery_util(util_gap_out, root=root)
        util_ok = (
            util_good.get("ok") is True
            and float(util_good.get("util_rate") or 0) >= 1.0
            and util_gap.get("utilization_gap") is True
            and util_gap.get("ok") is False
            and int(util_good.get("inject_chars") or 0) >= 1
        )
        # F155: hub-archival in recovery util — inject + hub_boost tool_hit vs idle gap
        ha_sid = HUB_ARCHIVAL_SKILL_ID
        ha_util_out = root / "util-hub-archival"
        ha_util_out.mkdir(exist_ok=True)
        (ha_util_out / "skill-router.json").write_text(
            json.dumps(
                {
                    "selected": [ha_sid, "skill-prefer-memory-cli-early"],
                    "always_selected": [ha_sid, "skill-prefer-memory-cli-early"],
                    "inject_chars": 720,
                }
            ),
            encoding="utf-8",
        )
        (ha_util_out / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": ha_sid,
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                            "tool_matched": ["hub_boost"],
                        },
                        {
                            "id": "skill-prefer-memory-cli-early",
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                        },
                    ],
                    "tool_hit_n": 2,
                }
            ),
            encoding="utf-8",
        )
        ha_util_good = score_recovery_util(ha_util_out, root=root)
        ha_gap_out = root / "util-hub-archival-gap"
        ha_gap_out.mkdir(exist_ok=True)
        (ha_gap_out / "skill-router.json").write_text(
            json.dumps(
                {
                    "selected": [ha_sid],
                    "always_selected": [ha_sid],
                    "inject_chars": 400,
                }
            ),
            encoding="utf-8",
        )
        (ha_gap_out / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": ha_sid,
                            "hit": True,
                            "tool_hit": False,
                            "prose_hit": True,
                        }
                    ],
                    "tool_hit_n": 0,
                }
            ),
            encoding="utf-8",
        )
        ha_util_gap = score_recovery_util(ha_gap_out, root=root)
        # hub-boost-strict tool probes: generic archival alone is not enough
        ha_probe_blob_ok = "hub_boost=1 archival_memory_search.py auto"
        ha_probe_blob_weak = "python3 scripts/archival_memory_search.py auto"
        ha_match_ok = match_tool_outcome(ha_sid, ha_probe_blob_ok, root=root)
        ha_match_weak = match_tool_outcome(ha_sid, ha_probe_blob_weak, root=root)
        ha_fed = federate_recovery_util(
            ha_util_good, root=root, tenant="fixture-tenant-ha"
        )
        ha_fed_gap = federate_recovery_util(
            ha_util_gap, root=root, tenant="fixture-tenant-ha"
        )
        ha_fed_blob = json.dumps(ha_fed.get("signals") or []) + json.dumps(
            ha_fed_gap.get("signals") or []
        )
        f155_ok = (
            ha_sid in RECOVERY_SKILL_IDS
            and ha_util_good.get("hub_archival_injected") is True
            and ha_util_good.get("hub_archival_tool_hit") is True
            and ha_util_good.get("hub_archival_util_gap") is False
            and ha_util_good.get("hub_archival_ok") is True
            and float(ha_util_good.get("util_rate") or 0) >= 1.0
            and ha_util_gap.get("hub_archival_util_gap") is True
            and ha_util_gap.get("utilization_gap") is True
            and ha_util_gap.get("hub_archival_ok") is False
            and len(ha_match_ok) >= 1
            and len(ha_match_weak) == 0
            and bool(ha_fed.get("privacy_ok"))
            and int(ha_fed.get("fed_n") or 0) >= 1
            and any(
                "hub_archival" in (s.get("tags") or [])
                or "f155" in (s.get("tags") or [])
                for s in (ha_fed.get("signals") or [])
                if isinstance(s, dict)
            )
            and bool(ha_fed_gap.get("privacy_ok"))
            and "/Users/" not in ha_fed_blob
            and "fixture-tenant-ha" not in ha_fed_blob
        )
        # F124: privacy-safe federate recovery util themes
        fed_ok_doc = federate_recovery_util(util_good, root=root, tenant="fixture-tenant-a")
        fed_gap_doc = federate_recovery_util(util_gap, root=root, tenant="fixture-tenant-a")
        fed_ok = (
            bool(fed_ok_doc.get("privacy_ok"))
            and int(fed_ok_doc.get("fed_n") or 0) >= 1
            and bool(fed_gap_doc.get("privacy_ok"))
            and "/Users/" not in json.dumps(fed_ok_doc.get("signals") or [])
            and "fixture-tenant-a" not in json.dumps(fed_ok_doc.get("signals") or [])
        )

        # F125: hub post-score compounds into always priority + inject
        os.environ["TORII_RECOVERY_HUB_COMPOUND"] = "1"
        # second tenant signal for multi-tenant boost
        federate_recovery_util(util_good, root=root, tenant="fixture-tenant-b")
        hub_score = post_score_recovery_hub(root=root)
        mem_delta = int((hub_score.get("priority_deltas") or {}).get(
            "skill-prefer-memory-cli-early"
        ) or 0)
        hub_privacy = bool(hub_score.get("privacy_ok"))
        hub_skills_ok = int(hub_score.get("skill_n") or 0) >= 1 and mem_delta >= 5
        # always priority: memory gets hub delta; with budget 1, product may defer without hub
        # seed a low-priority always and verify hub-hit recovery wins slot
        (active / "skill-prefer-critic-early.md").write_text(
            """---
id: skill-prefer-critic-early
title: Prefer second-agent critic early
always: true
always_priority: 85
themes: critic,panel
---

## Skill: prefer-critic-early

Call second-agent critic tools when uncertain.
""",
            encoding="utf-8",
        )
        # write synthetic hub favoring product over critic (product already in util)
        # re-score after multi-tenant federate
        hub_score2 = post_score_recovery_hub(root=root)
        cards_hub = catalog(root)
        # force budget 2 with hub: memory+product should win over critic if product has hub hits
        sel_hub = select_skills(
            cards_hub, py_paths, max_full=3, max_always=2, root=root, hub=hub_score2
        )
        hub_always = set(sel_hub.get("always_selected") or [])
        hub_rank_ok = (
            "skill-prefer-memory-cli-early" in hub_always
            and mem_delta >= 5
        )
        # inject hub section into prompt
        inj_hub = inject_into_prompt(prompt, root=root, paths=py_paths)
        text_hub = prompt.read_text(encoding="utf-8")
        hub_inject_ok = (
            HUB_MARKER_OPEN in text_hub
            and int(inj_hub.get("hub_injected") or 0) == 1
            and "F125" in text_hub
        )
        hub_ok = hub_privacy and hub_skills_ok and hub_rank_ok and hub_inject_ok
        hub_blob_ok = "/Users/" not in text_hub and "fixture-tenant" not in text_hub

        # F126: hub gap_pressure biases re-prompt on partial util (idle recovery)
        os.environ["TORII_HUB_GAP_REPROMPT"] = "1"
        os.environ["TORII_HUB_GAP_PRESSURE_THR"] = "0.30"
        # synthetic high gap pressure hub
        hub_gap_high = {
            "enabled": True,
            "gap_pressure": 0.6,
            "priority_deltas": {"skill-prefer-product-cli": 20},
            "skills": {
                "skill-prefer-product-cli": {
                    "skill_id": "skill-prefer-product-cli",
                    "hits": 2,
                    "tenants": 2,
                    "tool_hits": 1,
                    "priority_delta": 20,
                }
            },
            "privacy_ok": True,
        }
        util_partial = {
            "recovery_injected_n": 2,
            "tool_hit_n": 1,
            "util_rate": 0.5,
            "utilization_gap": False,
            "idle_ids": ["skill-prefer-product-cli"],
            "inject_chars": 800,
        }
        dec_hub = decide_recovery_reprompt(
            util_partial, tool_call_turns=3, hub=hub_gap_high, root=root
        )
        # full tools used, no idle → no re-prompt even with hub gap
        util_full = {
            "recovery_injected_n": 1,
            "tool_hit_n": 1,
            "util_rate": 1.0,
            "utilization_gap": False,
            "idle_ids": [],
            "inject_chars": 400,
        }
        dec_full = decide_recovery_reprompt(
            util_full, tool_call_turns=3, hub=hub_gap_high, root=root
        )
        # classic gap still works
        util_classic = {
            "recovery_injected_n": 1,
            "tool_hit_n": 0,
            "util_rate": 0.0,
            "utilization_gap": True,
            "idle_ids": ["skill-prefer-memory-cli-early"],
            "inject_chars": 400,
        }
        dec_classic = decide_recovery_reprompt(
            util_classic, tool_call_turns=2, hub=hub_gap_high, root=root
        )
        hub_gap_decide_ok = (
            int(dec_hub.get("reprompt") or 0) == 1
            and int(dec_hub.get("hub_gap_bias") or 0) == 1
            and "hub_gap" in str(dec_hub.get("reason") or "")
            and int(dec_full.get("reprompt") or 0) == 0
            and int(dec_classic.get("reprompt") or 0) == 1
        )
        # F126 fitness ingest from hub
        fit_ok = False
        try:
            import skill_fitness as _sf  # type: ignore

            os.environ["TORII_SKILL_FITNESS"] = "1"
            os.environ["TORII_SKILL_FITNESS_HUB"] = "1"
            fit = _sf.ingest_hub_recovery(hub_score2, root=root, save=True)
            fit_ok = (
                int(fit.get("ingested_n") or 0) >= 1
                and bool(fit.get("privacy_ok"))
                and "skill-prefer-memory-cli-early" in (fit.get("skills") or [])
            )
        except Exception as _exc:
            fit_ok = False

        f126_ok = hub_gap_decide_ok and fit_ok

        # F157: hub-archival util gap → soft re-prompt even with partial recovery util
        os.environ["TORII_HUB_ARCHIVAL_REPROMPT"] = "1"
        util_ha_partial = {
            "recovery_injected_n": 2,
            "tool_hit_n": 1,
            "util_rate": 0.5,
            "utilization_gap": False,
            "idle_ids": [HUB_ARCHIVAL_SKILL_ID],
            "inject_chars": 720,
            "hub_archival_util_gap": True,
            "hub_archival_injected": True,
            "hub_archival_tool_hit": False,
        }
        # low hub pressure so F126 does not steal the decision
        hub_low = {
            "enabled": True,
            "gap_pressure": 0.05,
            "priority_deltas": {},
            "skills": {},
            "privacy_ok": True,
        }
        dec_ha = decide_recovery_reprompt(
            util_ha_partial, tool_call_turns=3, hub=hub_low, root=root
        )
        util_ha_ok = {
            "recovery_injected_n": 2,
            "tool_hit_n": 2,
            "util_rate": 1.0,
            "utilization_gap": False,
            "idle_ids": [],
            "inject_chars": 720,
            "hub_archival_util_gap": False,
            "hub_archival_injected": True,
            "hub_archival_tool_hit": True,
        }
        dec_ha_ok = decide_recovery_reprompt(
            util_ha_ok, tool_call_turns=3, hub=hub_low, root=root
        )
        dec_ha_zero = decide_recovery_reprompt(
            util_ha_partial, tool_call_turns=0, hub=hub_low, root=root
        )
        prompt_ha = root / "prompt-ha-reprompt.md"
        prompt_ha.write_text("# Review\nDo security review.\n", encoding="utf-8")
        prompt_ha_out = root / "prompt-ha-reprompt-out.md"
        write_recovery_reprompt_prompt(
            prompt_in=prompt_ha,
            prompt_out=prompt_ha_out,
            idle_ids=[HUB_ARCHIVAL_SKILL_ID],
            tool_call_turns=3,
            inject_chars=720,
            hub_archival_util_gap=True,
            include_recovery=True,
        )
        ha_text = prompt_ha_out.read_text(encoding="utf-8")
        f157_ok = (
            int(dec_ha.get("reprompt") or 0) == 1
            and "hub_archival_util_gap" in str(dec_ha.get("reason") or "")
            and str(dec_ha.get("budget_kind") or "") == "f157"
            and int(dec_ha_ok.get("reprompt") or 0) == 0
            and int(dec_ha_zero.get("reprompt") or 0) == 0
            and dec_ha_zero.get("reason") == "zero_tools_defer_f49"
            and "F157" in ha_text
            and "hub_boost" in ha_text
            and "archival_memory_search" in ha_text
            and "/Users/" not in ha_text
        )

        # F160: synthesize skill-router when artifact missing → recovery injects always
        os.environ["TORII_SKILL_ROUTER_SYNTH"] = "1"
        synth_root = root / "f160-synth"
        synth_root.mkdir(exist_ok=True)
        active_s = synth_root / "agent" / "skills" / "active"
        active_s.mkdir(parents=True)
        for sid, prio, body in (
            (
                "skill-prefer-memory-cli-early",
                100,
                "Call torii memory CLI early.\n",
            ),
            (
                HUB_ARCHIVAL_SKILL_ID,
                95,
                "Call archival with hub_boost early.\n",
            ),
            (
                "skill-prefer-product-cli",
                90,
                "Call torii doctor early.\n",
            ),
        ):
            (active_s / f"{sid}.md").write_text(
                f"""---
id: {sid}
title: {sid}
always: true
always_priority: {prio}
themes: memory,archival,recovery
---

## Skill

{body}
""",
                encoding="utf-8",
            )
        # no skill-router.json yet — util must synth
        od_s = synth_root / "out"
        od_s.mkdir()
        (od_s / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": HUB_ARCHIVAL_SKILL_ID,
                            "tool_hit": False,
                            "hit": True,
                            "prose_hit": True,
                        },
                        {
                            "id": "skill-prefer-memory-cli-early",
                            "tool_hit": True,
                            "hit": True,
                        },
                    ],
                    "tool_hit_n": 1,
                }
            ),
            encoding="utf-8",
        )
        util_synth = score_recovery_util(od_s, root=synth_root)
        router_art = od_s / "skill-router.json"
        synth_doc = (
            json.loads(router_art.read_text(encoding="utf-8"))
            if router_art.is_file()
            else {}
        )
        f160_ok = (
            bool(util_synth.get("router_synthesized"))
            or bool(synth_doc.get("synthesized"))
        ) and (
            int(util_synth.get("recovery_injected_n") or 0) >= 2
            and util_synth.get("hub_archival_injected") is True
            and util_synth.get("hub_archival_util_gap") is True
            and HUB_ARCHIVAL_SKILL_ID in (util_synth.get("recovery_injected") or [])
            and router_art.is_file()
            and "skill-prefer-memory-cli-early"
            in (synth_doc.get("always_selected") or [])
            and "/Users/" not in json.dumps(synth_doc)
        )

        # F161: multi-tenant hub-archival gap pressure post-score + re-prompt bias
        os.environ["TORII_HUB_ARCHIVAL_HUB"] = "1"
        os.environ["TORII_HUB_ARCHIVAL_HUB_THR"] = "0.30"
        os.environ["TORII_HUB_ARCHIVAL_REPROMPT"] = "1"
        fed_ha = root / "memory" / "federation"
        fed_ha.mkdir(parents=True, exist_ok=True)
        (fed_ha / "hub-archival-util-signals.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "feature": "F161",
                    "privacy_ok": True,
                    "signals": [
                        {
                            "id": "hub-archival-util-gap",
                            "theme": "hub-archival-util-gap",
                            "tags": [
                                "hub_archival",
                                "utilization_gap",
                                "hub_archival_idle",
                                "f161",
                            ],
                            "hits": 5,
                            "tenants": 3,
                            "tenant_hashes": ["aaa", "bbb", "ccc"],
                            "util_rate_bin": "gap",
                            "hub_archival_idle": True,
                            "path_basenames": [],
                        },
                        {
                            "id": "recovery-util-hit-skill-prefer-hub-archival-early",
                            "theme": HUB_ARCHIVAL_SKILL_ID,
                            "tags": ["hub_archival", "f155", "hub_boost", "tool_outcome"],
                            "hits": 2,
                            "tool_hits": 2,
                            "tenants": 1,
                            "tenant_hashes": ["ddd"],
                            "util_rate_bin": "hit",
                            "path_basenames": [],
                        },
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        ha_hub = post_score_hub_archival_hub(root=root)
        ha_delta = int(
            (ha_hub.get("priority_deltas") or {}).get(HUB_ARCHIVAL_SKILL_ID) or 0
        )
        util_ha_idle = {
            "recovery_injected_n": 2,
            "tool_hit_n": 1,
            "util_rate": 0.5,
            "utilization_gap": False,
            "idle_ids": [HUB_ARCHIVAL_SKILL_ID],
            "inject_chars": 700,
            "hub_archival_util_gap": True,
            "hub_archival_injected": True,
            "hub_archival_tool_hit": False,
        }
        hub_low_gen = {
            "enabled": True,
            "gap_pressure": 0.05,
            "priority_deltas": {},
            "skills": {},
            "privacy_ok": True,
        }
        dec_ha_hub = decide_recovery_reprompt(
            util_ha_idle, tool_call_turns=3, hub=hub_low_gen, root=root
        )
        util_ha_ok_local = {
            "recovery_injected_n": 2,
            "tool_hit_n": 2,
            "util_rate": 1.0,
            "utilization_gap": False,
            "idle_ids": [],
            "inject_chars": 700,
            "hub_archival_util_gap": False,
            "hub_archival_injected": True,
            "hub_archival_tool_hit": True,
        }
        dec_ha_ok_hub = decide_recovery_reprompt(
            util_ha_ok_local, tool_call_turns=3, hub=hub_low_gen, root=root
        )
        f161_ok = (
            bool(ha_hub.get("privacy_ok"))
            and float(ha_hub.get("gap_pressure") or 0) >= 0.3
            and bool(ha_hub.get("high"))
            and ha_delta >= 5
            and int(dec_ha_hub.get("reprompt") or 0) == 1
            and (
                "hub_archival" in str(dec_ha_hub.get("reason") or "")
            )
            and int(dec_ha_hub.get("hub_archival_hub_high") or 0) == 1
            and int(dec_ha_ok_hub.get("reprompt") or 0) == 0
            and "/Users/" not in json.dumps(ha_hub)
            and "aaa" not in json.dumps(ha_hub.get("skills") or {})
        )

        # F162: inject hub-archival hub pressure section into prompt
        prompt_ha_hub = root / "prompt-ha-hub.md"
        prompt_ha_hub.write_text(
            "# Review\n## PR metadata\nDo security review.\n", encoding="utf-8"
        )
        inj_ha = inject_hub_archival_hub_into_prompt(
            prompt_ha_hub, hub=ha_hub, root=root
        )
        text_ha = prompt_ha_hub.read_text(encoding="utf-8")
        f162_ok = (
            int(inj_ha.get("injected") or 0) == 1
            and HA_HUB_MARKER_OPEN in text_ha
            and "F161" in text_ha
            and "hub_boost" in text_ha
            and "gap pressure" in text_ha.lower()
            and "/Users/" not in text_ha
            and "aaa" not in text_ha
            and bool(inj_ha.get("privacy_ok") or ha_hub.get("privacy_ok"))
        )

        # F136: scorecard util — tool hits ok; idle scorecard skill → gap; none → ok
        sc_util_out = root / "sc-util-out"
        sc_util_out.mkdir(exist_ok=True)
        sc_sid = "skill-prefer-product-scorecard"
        (sc_util_out / "skill-router.json").write_text(
            json.dumps(
                {
                    "selected": [sc_sid],
                    "always_selected": [],
                    "inject_chars": 600,
                }
            ),
            encoding="utf-8",
        )
        (sc_util_out / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": sc_sid,
                            "hit": True,
                            "tool_hit": True,
                            "prose_hit": False,
                        }
                    ],
                    "tool_hit_n": 1,
                }
            ),
            encoding="utf-8",
        )
        sc_util_good = score_scorecard_util(sc_util_out, root=root)
        sc_gap_out = root / "sc-util-gap"
        sc_gap_out.mkdir(exist_ok=True)
        (sc_gap_out / "skill-router.json").write_text(
            json.dumps(
                {
                    "selected": [sc_sid, "skill-prefer-demote-eval-check"],
                    "inject_chars": 900,
                }
            ),
            encoding="utf-8",
        )
        (sc_gap_out / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {
                            "id": sc_sid,
                            "hit": False,
                            "tool_hit": False,
                            "prose_hit": False,
                        },
                        {
                            "id": "skill-prefer-demote-eval-check",
                            "hit": True,
                            "tool_hit": False,
                            "prose_hit": True,
                        },
                    ],
                    "tool_hit_n": 0,
                }
            ),
            encoding="utf-8",
        )
        sc_util_gap = score_scorecard_util(sc_gap_out, root=root)
        sc_none_out = root / "sc-util-none"
        sc_none_out.mkdir(exist_ok=True)
        (sc_none_out / "skill-router.json").write_text(
            json.dumps({"selected": ["skill-prefer-product-cli"], "inject_chars": 100}),
            encoding="utf-8",
        )
        (sc_none_out / "skill-hits.json").write_text(
            json.dumps({"hits": [], "tool_hit_n": 0}),
            encoding="utf-8",
        )
        sc_util_none = score_scorecard_util(sc_none_out, root=root)
        sc_fed = federate_scorecard_util(
            sc_util_good, root=root, tenant="fixture-tenant-sc"
        )
        sc_fed_gap = federate_scorecard_util(
            sc_util_gap, root=root, tenant="fixture-tenant-sc"
        )
        sc_fed_blob = json.dumps(sc_fed.get("signals") or []) + json.dumps(
            sc_fed_gap.get("signals") or []
        )
        sc_util_ok = (
            sc_util_good.get("ok") is True
            and float(sc_util_good.get("util_rate") or 0) >= 1.0
            and sc_util_gap.get("utilization_gap") is True
            and sc_util_gap.get("ok") is False
            and sc_util_none.get("ok") is True
            and float(sc_util_none.get("util_rate") or 0) >= 1.0
            and int(sc_util_none.get("scorecard_injected_n") or 0) == 0
            and bool(sc_fed.get("privacy_ok"))
            and int(sc_fed.get("fed_n") or 0) >= 1
            and bool(sc_fed_gap.get("privacy_ok"))
            and "/Users/" not in sc_fed_blob
            and "fixture-tenant-sc" not in sc_fed_blob
        )

        # F137: scorecard util gap → re-prompt; good util → no re-prompt
        os.environ["TORII_SCORECARD_SKILL_REPROMPT"] = "1"
        sc_dec_gap = decide_scorecard_reprompt(
            sc_util_gap, already_reprompted=False, tool_call_turns=3, root=root
        )
        sc_dec_good = decide_scorecard_reprompt(
            sc_util_good, already_reprompted=False, tool_call_turns=3, root=root
        )
        sc_dec_none = decide_scorecard_reprompt(
            sc_util_none, already_reprompted=False, tool_call_turns=3, root=root
        )
        sc_dec_zero_tools = decide_scorecard_reprompt(
            sc_util_gap, already_reprompted=False, tool_call_turns=0, root=root
        )
        # federated gap bias on partial
        federate_scorecard_util(sc_util_gap, root=root, tenant="fixture-tenant-sc2")
        sc_partial = {
            "scorecard_injected_n": 2,
            "tool_hit_n": 1,
            "util_rate": 0.5,
            "utilization_gap": False,
            "idle_ids": ["skill-prefer-demote-eval-check"],
            "inject_chars": 500,
        }
        sc_dec_fed = decide_scorecard_reprompt(
            sc_partial, already_reprompted=False, tool_call_turns=4, root=root
        )
        prompt_in = root / "prompt-in.md"
        prompt_in.write_text("# Review prompt\nDo security review.\n", encoding="utf-8")
        prompt_out = root / "prompt-sc-reprompt.md"
        write_recovery_reprompt_prompt(
            prompt_in=prompt_in,
            prompt_out=prompt_out,
            idle_ids=[],
            tool_call_turns=3,
            inject_chars=600,
            scorecard_idle_ids=["skill-prefer-product-scorecard"],
            scorecard_gap=True,
            hub_scorecard_util_gap=True,
            include_recovery=False,
        )
        sc_prompt_text = prompt_out.read_text(encoding="utf-8")
        f137_ok = (
            int(sc_dec_gap.get("reprompt") or 0) == 1
            and "scorecard_utilization_gap" in str(sc_dec_gap.get("reason") or "")
            and int(sc_dec_good.get("reprompt") or 0) == 0
            and int(sc_dec_none.get("reprompt") or 0) == 0
            and sc_dec_none.get("reason") == "no_scorecard_injected"
            and int(sc_dec_zero_tools.get("reprompt") or 0) == 0
            and sc_dec_zero_tools.get("reason") == "zero_tools_defer_f49"
            and int(sc_dec_fed.get("reprompt") or 0) == 1
            and SCORECARD_REPROMPT_MARKER in sc_prompt_text
            and "torii.py doctor" in sc_prompt_text
            and "scorecard --shallow" in sc_prompt_text
            and "/Users/" not in sc_prompt_text
        )

        # F138: scorecard hub post-score → priority deltas + inject
        os.environ["TORII_SCORECARD_HUB_COMPOUND"] = "1"
        federate_scorecard_util(sc_util_good, root=root, tenant="fixture-tenant-sc3")
        federate_scorecard_util(sc_util_good, root=root, tenant="fixture-tenant-sc4")
        sc_hub = post_score_scorecard_hub(root=root)
        sc_sid = "skill-prefer-product-scorecard"
        sc_delta = int((sc_hub.get("priority_deltas") or {}).get(sc_sid) or 0)
        # plant active scorecard skill file for select rank
        (active / f"{sc_sid}.md").write_text(
            f"""---
id: {sc_sid}
title: Prefer product scorecard
themes: scorecard,ops,doctor
---

## Skill: product-scorecard

Call `python3 scripts/torii.py doctor` and scorecard early.
""",
            encoding="utf-8",
        )
        cards_sc = catalog(root)
        sel_sc = select_skills(
            cards_sc, ["src/auth.py"], max_full=6, max_always=2, root=root
        )
        sc_rank = next(
            (r for r in (sel_sc.get("ranking") or []) if r.get("id") == sc_sid),
            None,
        )
        sc_hub_delta_rank = int((sc_rank or {}).get("scorecard_hub_delta") or 0)
        sc_prompt = root / "prompt-sc-hub.md"
        sc_prompt.write_text("# Review\n## PR metadata\n", encoding="utf-8")
        sc_inj = inject_scorecard_hub_into_prompt(sc_prompt, hub=sc_hub, root=root)
        sc_text = sc_prompt.read_text(encoding="utf-8")
        f138_ok = (
            bool(sc_hub.get("privacy_ok"))
            and int(sc_hub.get("skill_n") or 0) >= 1
            and sc_delta >= 5
            and sc_hub_delta_rank >= 5
            and int(sc_inj.get("injected") or 0) == 1
            and SCORECARD_HUB_MARKER_OPEN in sc_text
            and sc_sid in sc_text
            and "/Users/" not in sc_text
            and "fixture-tenant" not in sc_text
            and bool(sel_sc.get("scorecard_hub_priority_deltas"))
        )

        fixture_pass = all(
            [
                always_ok,
                sec_ok,
                docs_not_first,
                always_in_md,
                inject_ok,
                stripped_ok,
                selected_body_ok,
                rate_ok,
                privacy_ok,
                good_hits.get("hit_n", 0) >= 1,
                memory_always_ok,
                product_always_ok,
                memory_in_py,
                product_in_py,
                tool_outcome_ok,
                tool_rate_ok,
                weak_tool_ok,
                compact_ok,
                smaller_ok,
                util_ok,
                fed_ok,
                hub_ok,
                hub_blob_ok,
                f126_ok,
                sc_util_ok,
                f137_ok,
                f138_ok,
                f155_ok,
                f157_ok,
                f160_ok,
                f161_ok,
                f162_ok,
            ]
        )
        payload = {
            "feature": FEATURE,
            "f114": True,
            "f119": True,
            "f120": True,
            "f121": True,
            "f136": True,
            "f137": True,
            "f138": True,
            "f155": True,
            "f157": True,
            "f160": True,
            "f161": True,
            "f162": True,
            "feature_hub_archival_util": FEATURE_HUB_ARCHIVAL_UTIL,
            "feature_hub_archival_reprompt": FEATURE_HUB_ARCHIVAL_REPROMPT,
            "feature_router_synth": FEATURE_ROUTER_SYNTH,
            "feature_hub_archival_hub": FEATURE_HUB_ARCHIVAL_HUB,
            "feature_hub_archival_hub_inject": FEATURE_HUB_ARCHIVAL_HUB_INJECT,
            "feature_always_budget": "F119",
            "feature_compact": "F120",
            "feature_util": "F121",
            "feature_scorecard_util": "F136",
            "feature_scorecard_reprompt": "F137",
            "feature_scorecard_hub": FEATURE_SCORECARD_HUB,
            "feature_hub_compound": FEATURE_HUB,
            "fixture_pass": fixture_pass,
            "always_ok": always_ok,
            "always_selected": list(always_sel),
            "always_deferred": list(always_def),
            "sec_ok": sec_ok,
            "docs_not_first": docs_not_first,
            "always_in_md": always_in_md,
            "inject_ok": inject_ok,
            "stripped_ok": stripped_ok,
            "selected_py": inj["selected"],
            "selected_md": sel_md["selected"],
            "good_hit_rate": good_rate,
            "weak_hit_rate": weak_rate,
            "rate_ok": rate_ok,
            "privacy_ok": privacy_ok,
            "good_hit_n": good_hits.get("hit_n"),
            "memory_always_ok": memory_always_ok,
            "product_always_ok": product_always_ok,
            "memory_in_py": memory_in_py,
            "product_in_py": product_in_py,
            "tool_outcome_ok": tool_outcome_ok,
            "tool_hit_n": tool_hits.get("tool_hit_n"),
            "tool_hit_rate": tool_hits.get("tool_hit_rate"),
            "weak_tool_ok": weak_tool_ok,
            "compact_ok": compact_ok,
            "compact_chars": chars_compact,
            "full_chars": chars_full,
            "f120_chars_saved": inj2.get("f120_chars_saved"),
            "smaller_ok": smaller_ok,
            "util_ok": util_ok,
            "util_rate_good": util_good.get("util_rate"),
            "util_gap": util_gap.get("utilization_gap"),
            "util_inject_chars": util_good.get("inject_chars"),
            "f124": True,
            "fed_ok": fed_ok,
            "fed_n": fed_ok_doc.get("fed_n"),
            "fed_privacy_ok": fed_ok_doc.get("privacy_ok"),
            "f125": True,
            "hub_ok": hub_ok,
            "hub_skill_n": hub_score.get("skill_n"),
            "hub_mem_delta": mem_delta,
            "hub_gap_pressure": hub_score.get("gap_pressure"),
            "hub_inject_ok": hub_inject_ok,
            "hub_rank_ok": hub_rank_ok,
            "hub_always": list(hub_always),
            "hub_blob_ok": hub_blob_ok,
            "f126": True,
            "f126_ok": f126_ok,
            "hub_gap_decide_ok": hub_gap_decide_ok,
            "hub_fitness_ok": fit_ok,
            "dec_hub_reason": dec_hub.get("reason"),
            "f136_sc_util_ok": sc_util_ok,
            "f136_sc_util_rate_good": sc_util_good.get("util_rate"),
            "f136_sc_util_gap": sc_util_gap.get("utilization_gap"),
            "f136_sc_none_ok": sc_util_none.get("ok"),
            "f136_sc_fed_n": sc_fed.get("fed_n"),
            "f136_sc_privacy_ok": sc_fed.get("privacy_ok"),
            "f137_ok": f137_ok,
            "f137_sc_reprompt_gap": sc_dec_gap.get("reprompt"),
            "f137_sc_reprompt_good": sc_dec_good.get("reprompt"),
            "f137_sc_reprompt_fed": sc_dec_fed.get("reprompt"),
            "f137_sc_reason": sc_dec_gap.get("reason"),
            "f137_prompt_has_marker": SCORECARD_REPROMPT_MARKER in sc_prompt_text,
            "f138_ok": f138_ok,
            "f138_sc_hub_skill_n": sc_hub.get("skill_n"),
            "f138_sc_hub_delta": sc_delta,
            "f138_sc_hub_inject": sc_inj.get("injected"),
            "f138_sc_hub_privacy": sc_hub.get("privacy_ok"),
            "f138_sc_hub_gap_pressure": sc_hub.get("gap_pressure"),
            "f155_ok": f155_ok,
            "f155_hub_archival_util_rate": ha_util_good.get("util_rate"),
            "f155_hub_archival_gap": ha_util_gap.get("hub_archival_util_gap"),
            "f155_hub_archival_in_recovery": ha_sid in RECOVERY_SKILL_IDS,
            "f155_hub_boost_probe_ok": len(ha_match_ok) >= 1,
            "f155_generic_archival_not_enough": len(ha_match_weak) == 0,
            "f155_fed_n": ha_fed.get("fed_n"),
            "f155_fed_privacy": ha_fed.get("privacy_ok"),
            "f157_ok": f157_ok,
            "f157_reprompt": dec_ha.get("reprompt"),
            "f157_reason": dec_ha.get("reason"),
            "f157_budget_kind": dec_ha.get("budget_kind"),
            "f157_ok_no_reprompt": int(dec_ha_ok.get("reprompt") or 0),
            "f157_prompt_has_f157": "F157" in ha_text,
            "f160_ok": f160_ok,
            "f160_recovery_injected_n": util_synth.get("recovery_injected_n"),
            "f160_hub_archival_injected": util_synth.get("hub_archival_injected"),
            "f160_hub_archival_gap": util_synth.get("hub_archival_util_gap"),
            "f160_router_synthesized": util_synth.get("router_synthesized"),
            "f160_always": synth_doc.get("always_selected"),
            "f161_ok": f161_ok,
            "f161_gap_pressure": ha_hub.get("gap_pressure"),
            "f161_high": ha_hub.get("high"),
            "f161_ha_delta": ha_delta,
            "f161_reprompt": dec_ha_hub.get("reprompt"),
            "f161_reason": dec_ha_hub.get("reason"),
            "f161_ok_local_no_reprompt": int(dec_ha_ok_hub.get("reprompt") or 0),
            "f162_ok": f162_ok,
            "f162_injected": inj_ha.get("injected"),
            "f162_marker": HA_HUB_MARKER_OPEN in text_ha,
            "f162_gap_pressure": inj_ha.get("gap_pressure"),
        }
        print(json.dumps(payload, indent=2))
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="F84 progressive skill router + hit scoring"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("index", help="Catalog active skills").set_defaults(func=cmd_index)
    sub.add_parser("status", help="Router status").set_defaults(func=cmd_status)
    sub.add_parser("fixture", help="Hermetic offline fixture").set_defaults(
        func=cmd_fixture
    )
    pu = sub.add_parser(
        "util", help="F121 recovery skill tool utilization score for a run"
    )
    pu.add_argument("--out-dir", default="")
    pu.add_argument(
        "--no-federate",
        action="store_true",
        help="F124: skip privacy-safe recovery util federation",
    )
    pu.set_defaults(func=cmd_util)

    pscu = sub.add_parser(
        "scorecard-util",
        help="F136 scorecard-gap skill tool utilization score for a run",
    )
    pscu.add_argument("--out-dir", default="")
    pscu.add_argument(
        "--no-federate",
        action="store_true",
        help="Skip privacy-safe scorecard util federation",
    )
    pscu.set_defaults(func=cmd_scorecard_util)

    pfed = sub.add_parser(
        "federate-util", help="F124 federate recovery util themes (privacy-safe)"
    )
    pfed.add_argument("--out-dir", default="")
    pfed.add_argument("--util-json", default="", help="path to recovery-skill-util.json")
    pfed.set_defaults(func=cmd_federate_util)

    prd = sub.add_parser(
        "reprompt-decide",
        help="F122/F137 soft re-prompt decide on recovery+scorecard util gap",
    )
    prd.add_argument("--out-dir", default="")
    prd.add_argument("--review", default="")
    prd.add_argument("--already-env", default="")
    prd.add_argument("--tool-turns", type=int, default=None)
    prd.set_defaults(func=cmd_reprompt_decide)

    prw = sub.add_parser(
        "reprompt-write",
        help="F122/F126/F137 write recovery+scorecard skill nudged prompt",
    )
    prw.add_argument("--prompt-in", required=True)
    prw.add_argument("--prompt-out", required=True)
    prw.add_argument("--idle-ids", default="")
    prw.add_argument("--tool-turns", default="0")
    prw.add_argument("--inject-chars", default="0")
    prw.add_argument(
        "--hub-gap-pressure",
        default="0",
        help="F126: multi-tenant gap_pressure for prompt bias text",
    )
    prw.add_argument(
        "--hub-gap-bias",
        default="0",
        help="F126: 1 if re-prompt was triggered by hub gap pressure",
    )
    prw.add_argument(
        "--scorecard-idle-ids",
        default="",
        help="F137: comma-separated idle scorecard skill ids",
    )
    prw.add_argument(
        "--scorecard-gap",
        default="0",
        help="F137: 1 to append scorecard ops re-prompt section",
    )
    prw.add_argument(
        "--hub-scorecard-util-gap",
        default="0",
        help="F137: 1 if federated scorecard-util-gap theme present",
    )
    prw.add_argument(
        "--scorecard-only",
        default="0",
        help="F137: 1 to write scorecard section without recovery section",
    )
    prw.add_argument(
        "--hub-archival-util-gap",
        default="0",
        help="F157: 1 if hub-archival skill inject ≠ hub_boost tools",
    )
    prw.set_defaults(func=cmd_reprompt_write)

    phub = sub.add_parser(
        "hub-score",
        help="F125/F138 post-score hub recovery+scorecard util → priority deltas",
    )
    phub.add_argument(
        "--inject",
        default="",
        help="optional prompt.md path to inject hub section",
    )
    phub.set_defaults(func=cmd_hub_score)

    psch = sub.add_parser(
        "scorecard-hub-score",
        help="F138 post-score hub scorecard-util themes → select priority deltas",
    )
    psch.add_argument(
        "--inject",
        default="",
        help="optional prompt.md path to inject scorecard hub section",
    )
    psch.set_defaults(func=cmd_scorecard_hub_score)

    ps = sub.add_parser("select", help="Select skills for paths")
    ps.add_argument("--paths", nargs="*", default=None)
    ps.add_argument("--paths-file", default=None)
    ps.add_argument("--pr-json", default=None)
    ps.add_argument("--max", type=int, default=None)
    ps.set_defaults(func=cmd_select)

    pi = sub.add_parser("inject", help="Progressive inject into prompt")
    pi.add_argument("--prompt", required=True)
    pi.add_argument("--out", default="")
    pi.add_argument("--paths", nargs="*", default=None)
    pi.add_argument("--paths-file", default=None)
    pi.add_argument("--pr-json", default=None)
    pi.add_argument("--force", action="store_true")
    pi.set_defaults(func=cmd_inject)

    pc = sub.add_parser(
        "score", help="Score skill hits in review + F114 tool outcomes"
    )
    pc.add_argument("--review", required=True)
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--selected", default="")
    pc.add_argument(
        "--agent-loop",
        default="",
        help="F114: path to agent-loop.json for tool-outcome scoring",
    )
    pc.add_argument(
        "--log",
        default="",
        help="F114: hermes/run log path for tool-outcome probes",
    )
    pc.set_defaults(func=cmd_score)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
