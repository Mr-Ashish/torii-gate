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
SCHEMA = 1
MARKER_OPEN = "<!-- torii-f84-skill-router -->"
MARKER_CLOSE = "<!-- /torii-f84-skill-router -->"
F69_OPEN = "<!-- torii-f69-skills -->"
F69_CLOSE = "<!-- /torii-f69-skills -->"
HUB_MARKER_OPEN = "<!-- torii-f125-recovery-hub -->"
HUB_MARKER_CLOSE = "<!-- /torii-f125-recovery-hub -->"

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
}

# F119: default always priority when card.always (higher = keep under ALWAYS_MAX)
ALWAYS_PRIORITY_DEFAULT: dict[str, int] = {
    "skill-prefer-memory-cli-early": 100,
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


def recovery_hub_enabled() -> bool:
    """F125: consume federated recovery-util themes into always priority (default on)."""
    raw = (os.environ.get("TORII_RECOVERY_HUB_COMPOUND") or "1").strip().lower()
    return raw not in _FALSEY


def _is_skill_id_theme(theme: str) -> bool:
    t = (theme or "").strip().lower()
    if not t or t in ("recovery-util-ok", "recovery-util-gap", "recovery_util"):
        return False
    if t.startswith("recovery-util-hit-"):
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

    def _effective_always_prio(c: SkillCard) -> int:
        return int(c.always_priority or 0) + hub_priority_delta(c.id, hub_report)

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

    return {
        "feature": FEATURE,
        "feature_always_budget": "F119",
        "feature_hub_compound": FEATURE_HUB if recovery_hub_enabled() else None,
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
        "ranking": [
            {
                "id": c.id,
                "score": round(s, 2),
                "always": c.always,
                "always_priority": c.always_priority,
                "always_priority_effective": _effective_always_prio(c),
                "hub_delta": hub_priority_delta(c.id, hub_report),
                "always_deferred": c.id in always_deferred_set,
                "demoted": c.id in demoted and c.id not in always_selected_ids,
                "free_rider": c.id in free_riders and c.id not in always_selected_ids,
            }
            for s, c in ranked
        ],
    }


# F121: recovery skills that teach tool CLIs (must fire tools when always-injected)
RECOVERY_SKILL_IDS: frozenset[str] = frozenset(
    {
        "skill-prefer-memory-cli-early",
        "skill-prefer-product-cli",
        "skill-prefer-critic-early",
    }
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

    result = {
        "feature": FEATURE,
        "feature_compact": "F120" if compact_enabled() else None,
        "feature_hub_compound": FEATURE_HUB if recovery_hub_enabled() else None,
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
    }
    # write selection artifact next to prompt if OUT_DIR
    od = (os.environ.get("OUT_DIR") or "").strip()
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


def score_recovery_util(
    out_dir: Path | None = None,
    *,
    root: Path | None = None,
    hits_doc: dict[str, Any] | None = None,
    router_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """F121: recovery skills injected vs tool_hit — inject presence ≠ utilization.

    SkillsBench / Mem2Act: always-injected recovery skills must fire tool CLIs
    or they are idle prompt cost. Gap when recovery selected and tool_hit_n=0.
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
    recovery_injected = [
        s for s in selected if s in RECOVERY_SKILL_IDS
    ] or [s for s in always_sel if s in RECOVERY_SKILL_IDS]

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

    report = {
        "feature": "F121",
        "schema": SCHEMA,
        "scored_at": _now(),
        "recovery_ids": sorted(RECOVERY_SKILL_IDS),
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
        sig: dict[str, Any] = {
            "id": _slug(f"recovery-util-hit-{sid}"),
            "theme": _slug(sid),
            "cwe": [],
            "tags": ["recovery_util", "tool_outcome", "f124", "federated_skill"],
            "keywords": [sid.replace("skill-", "")[:48], "recovery-util", "tool-hit"],
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
        gap_sig: dict[str, Any] = {
            "id": "recovery-util-gap",
            "theme": "recovery-util-gap",
            "cwe": [],
            "tags": ["recovery_util", "utilization_gap", "f124", "federated_skill"],
            "keywords": ["recovery-util-gap", "idle-recovery"],
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
        }
        if th:
            gap_sig["tenant_hashes"] = [th]
            gap_sig["tenant_hash"] = th
        signals.append(gap_sig)
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


def recovery_reprompt_enabled() -> bool:
    """F122: soft re-prompt once on recovery util gap (default on)."""
    raw = (os.environ.get("TORII_RECOVERY_SKILL_REPROMPT") or "1").strip().lower()
    return raw not in _FALSEY


RECOVERY_REPROMPT_MARKER = "<!-- torii-f122-recovery-skill-reprompt -->"


def decide_recovery_reprompt(
    util: dict[str, Any],
    *,
    already_reprompted: bool = False,
    tool_call_turns: int = 0,
    reprompt_on: bool | None = None,
) -> dict[str, Any]:
    """F122: re-prompt when recovery skills injected but no tool hits (after tools ran)."""
    on = recovery_reprompt_enabled() if reprompt_on is None else bool(reprompt_on)
    gap = bool(util.get("utilization_gap"))
    n = int(util.get("recovery_injected_n") or 0)
    tool_n = int(util.get("tool_hit_n") or 0)
    out: dict[str, Any] = {
        "feature": "F122",
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
        "idle_ids": util.get("idle_ids") or [],
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
    if tool_n >= 1:
        out["reason"] = "recovery_tools_used"
        return out
    if tool_call_turns < 1:
        # F49 owns zero-tool recovery
        out["reason"] = "zero_tools_defer_f49"
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
) -> str:
    idle = idle_ids or sorted(RECOVERY_SKILL_IDS)
    idle_s = ", ".join(f"`{i}`" for i in idle[:6])
    return (
        "\n\n---\n\n"
        f"{RECOVERY_REPROMPT_MARKER}\n\n"
        f"## Recovery skill soft re-prompt (F122)\n\n"
        f"Your previous reply used **{tool_call_turns} tool turns** but **0 recovery "
        f"skill CLIs** after always-injecting: {idle_s} "
        f"(inject_chars≈{inject_chars}).\n\n"
        "Before finalizing, call **at least one** of these once via terminal:\n\n"
        "```bash\n"
        "python3 scripts/torii.py memory -- search -- -q \"auth OR sql OR pickle OR secret\"\n"
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
) -> Path:
    base = prompt_in.read_text(encoding="utf-8", errors="replace")
    if RECOVERY_REPROMPT_MARKER in base:
        text = base
    else:
        text = base.rstrip() + build_recovery_reprompt_suffix(
            idle_ids=idle_ids,
            tool_call_turns=tool_call_turns,
            inject_chars=inject_chars,
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
    """F122: key=value decide whether to soft re-prompt on recovery util gap."""
    od = Path(args.out_dir) if args.out_dir else Path(os.environ.get("OUT_DIR") or ".")
    already = False
    if args.already_env and Path(args.already_env).is_file():
        txt = Path(args.already_env).read_text(encoding="utf-8", errors="replace")
        if "attempted=1" in txt or "reprompt=1" in txt:
            already = True
    # ensure util scored
    util = score_recovery_util(od, root=_root())
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
        except Exception:
            pass
    dec = decide_recovery_reprompt(
        util, already_reprompted=already, tool_call_turns=turns
    )
    # key=value for shell (like F106)
    print(f"reprompt={dec['reprompt']}")
    print(f"enabled={int(bool(dec['enabled']))}")
    print(f"reason={dec['reason']}")
    print(f"utilization_gap={int(bool(dec['utilization_gap']))}")
    print(f"tool_hit_n={dec['tool_hit_n']}")
    print(f"recovery_injected_n={dec['recovery_injected_n']}")
    print(f"tool_call_turns={dec['tool_call_turns']}")
    print(f"inject_chars={dec.get('inject_chars') or 0}")
    print(f"util_rate={dec.get('util_rate')}")
    print(f"idle_ids={','.join(dec.get('idle_ids') or [])}")
    print("feature=F122")
    return 0


def cmd_hub_score(args: argparse.Namespace) -> int:
    """F125: post-score federated recovery util → priority deltas (+ optional inject)."""
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
    # OUT_DIR artifact
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        try:
            p = Path(od) / "recovery-hub-score.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(hub, indent=2) + "\n", encoding="utf-8")
            hub["artifact"] = str(p)
        except OSError:
            pass
    print(json.dumps(hub, indent=2))
    return 0 if hub.get("privacy_ok") else 1


def cmd_reprompt_write(args: argparse.Namespace) -> int:
    """F122: write nudged prompt for recovery skill re-run."""
    idle = [x for x in (args.idle_ids or "").split(",") if x.strip()]
    path = write_recovery_reprompt_prompt(
        prompt_in=Path(args.prompt_in),
        prompt_out=Path(args.prompt_out),
        idle_ids=idle or None,
        tool_call_turns=int(args.tool_turns or 0),
        inject_chars=int(args.inject_chars or 0),
    )
    print(json.dumps({"feature": "F122", "prompt_out": str(path), "ok": path.is_file()}))
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
            ]
        )
        payload = {
            "feature": FEATURE,
            "f114": True,
            "f119": True,
            "f120": True,
            "f121": True,
            "feature_always_budget": "F119",
            "feature_compact": "F120",
            "feature_util": "F121",
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

    pfed = sub.add_parser(
        "federate-util", help="F124 federate recovery util themes (privacy-safe)"
    )
    pfed.add_argument("--out-dir", default="")
    pfed.add_argument("--util-json", default="", help="path to recovery-skill-util.json")
    pfed.set_defaults(func=cmd_federate_util)

    prd = sub.add_parser(
        "reprompt-decide", help="F122 soft re-prompt decide on recovery util gap"
    )
    prd.add_argument("--out-dir", default="")
    prd.add_argument("--review", default="")
    prd.add_argument("--already-env", default="")
    prd.add_argument("--tool-turns", type=int, default=None)
    prd.set_defaults(func=cmd_reprompt_decide)

    prw = sub.add_parser(
        "reprompt-write", help="F122 write recovery-skill nudged prompt"
    )
    prw.add_argument("--prompt-in", required=True)
    prw.add_argument("--prompt-out", required=True)
    prw.add_argument("--idle-ids", default="")
    prw.add_argument("--tool-turns", default="0")
    prw.add_argument("--inject-chars", default="0")
    prw.set_defaults(func=cmd_reprompt_write)

    phub = sub.add_parser(
        "hub-score",
        help="F125 post-score hub recovery-util themes → always priority deltas",
    )
    phub.add_argument(
        "--inject",
        default="",
        help="optional prompt.md path to inject hub section",
    )
    phub.set_defaults(func=cmd_hub_score)

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
