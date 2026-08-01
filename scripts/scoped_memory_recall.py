#!/usr/bin/env python3
"""F75: Scoped memory recall over TP/FP (Mem0 multi-scope, deterministic).

Research drivers (2026):
  - Mem0 (arXiv 2504.19413 / Apache-2.0): multi-scope memory
    (user/agent/run/app) + selective retrieval; conflict detection on update
  - Memory security surveys (arXiv 2604.16548, longitudinal safety):
    segment memory, label provenance, prevent cross-scope poisoning
  - Torii stack: F64 fp-rules, F70 tp-signatures, F71 federated (theme-only),
    F65 tenant — but inject was **unscoped dump** of all signatures

Product thesis:
  Highest ROI memory architecture slice: **scoped, budgeted recall** that
  ranks TP/FP by (1) path match to changed files, (2) scope priority
  (run > repo > tenant > agent/global), (3) hits; then **conflict-resolves**
  FP vs TP before prompt inject. No vector DB / no LLM — tools-as-code.

Scopes (Torii mapping of Mem0 hierarchy):
  run     — current out_dir artifacts
  repo    — target .torii/ (tp-signatures, fp-rules)
  tenant  — TORII_MEMORY_TENANT namespace (F65)
  agent   — hub/agent-global durable memory (memory/, federated)
  global  — privacy-safe federated theme signals only

Commands:
  ingest   — build unified scoped store from TP/FP/federated sources
  recall   — path+scope filtered ranking for a PR file list
  conflict — resolve TP vs FP overlaps
  inject   — budgeted prompt sections (replaces blind full TP dump when on)
  fixture  — offline good/weak isolation + path filter
  score    — metrics: path_precision, conflict_resolved, budget_ok
  status   — store summary

Env:
  TORII_ROOT
  TORII_SCOPED_MEMORY        1 (default) | 0/off
  TORII_SCOPED_MEMORY_FILE   override store path
  TORII_SCOPED_TP_MAX        default 8
  TORII_SCOPED_FP_MAX        default 12
  TORII_SCOPED_REPLACE_TP    1 (default) | 0 — replace F70 bulk TP section
  TORII_MEMORY_TENANT        optional tenant id
  TORII_TP_SIGNATURES_FILE / TORII_FP_RULES_FILE / TORII_FEDERATED_SIGNALS_FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F75"
SCHEMA = 1
MARKER = "<!-- torii-f75-scoped-memory -->"
STORE_NAME = "scoped-memory.json"

# Narrower scopes win ties when scores equal
SCOPE_RANK = {
    "run": 50,
    "repo": 40,
    "tenant": 30,
    "agent": 20,
    "global": 10,
}

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SCOPED_MEMORY") or "1").strip().lower()
    return raw not in _FALSEY


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def default_store_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_SCOPED_MEMORY_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    r = root or _root()
    return r / ".torii" / STORE_NAME


def _tenant_id() -> str:
    t = (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    t = re.sub(r"[^A-Za-z0-9._-]+", "-", t).strip("-")[:64]
    return t


def _slug_repo(repo: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "--", (repo or "").strip())[:96] or "unknown"


def _item_id(kind: str, scope: str, raw_id: str, theme: str) -> str:
    base = f"{kind}|{scope}|{raw_id or theme}"
    h = hashlib.sha256(base.encode()).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9-]+", "-", (raw_id or theme or "x").lower())[:40]
    return f"{kind}-{scope}-{slug}-{h}"


def _safe_provenance(path: Path | str, root: Path | None = None) -> str:
    """Store relative/redacted provenance only (no home-dir absolute paths)."""
    s = str(path)
    s = s.replace("\\", "/")
    # strip home prefixes
    s = re.sub(r"^/Users/[^/]+/", "", s)
    s = re.sub(r"^/home/[^/]+/", "", s)
    r = root or _root()
    try:
        rel = str(Path(path).resolve().relative_to(r.resolve()))
        return rel.replace("\\", "/")
    except Exception:
        # keep tail after known anchors
        for anchor in ("torii/", ".torii/", "memory/", "Documents/experiments/"):
            if anchor in s:
                return s.split(anchor, 1)[-1] if anchor != "torii/" else "torii/" + s.split("torii/", 1)[-1]
        return Path(s).name or "[redacted]"


@dataclass
class MemoryItem:
    id: str
    kind: str  # tp | fp | federated
    scope: str  # run|repo|tenant|agent|global
    theme: str = ""
    cwe: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    path_globs: list[str] = field(default_factory=list)
    path: str = ""  # single path for FP rules
    reason: str = ""
    hits: int = 1
    source: str = ""
    repo: str = ""
    tenant: str = ""
    provenance: str = ""
    raw_id: str = ""
    # F94 consolidation annotations (optional)
    importance_score: float | None = None
    decay_weight: float | None = None
    effective_score: float | None = None
    last_seen: str = ""
    # F146/F147 reconsolidation → core tier promote
    last_retrieved_at: str = ""
    reconsolidated_at: str = ""
    reconsolidation_feature: str = ""
    active: bool | None = None
    superseded_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _tp_path(root: Path) -> Path:
    env = (os.environ.get("TORII_TP_SIGNATURES_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return root / ".torii" / "tp-signatures.json"


def _fp_path(root: Path) -> Path:
    env = (os.environ.get("TORII_FP_RULES_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return root / ".torii" / "fp-rules.json"


def _fed_path(root: Path) -> Path:
    """F96: prefer multi-tenant **promoted** signals (often carry effective_score)."""
    env = (os.environ.get("TORII_FEDERATED_SIGNALS_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    # Prefer promoted (F77/F95 gate) over raw global aggregate
    for cand in (
        root / "memory" / "federation" / "promoted-signals.json",
        root / "memory" / "federation" / "federated-signals.json",  # F77 hub
        root / ".torii" / "promoted-signals.json",
        root / ".torii" / "federated-signals.json",
        root / "memory" / "federated-signals.json",
    ):
        if cand.is_file():
            return cand
    return root / "memory" / "federation" / "promoted-signals.json"


def load_tp_items(
    path: Path,
    *,
    scope: str,
    repo: str = "",
    tenant: str = "",
    provenance: str = "",
) -> list[MemoryItem]:
    data = _load_json(path)
    if data is None:
        return []
    sigs = data.get("signatures") if isinstance(data, dict) else data
    if not isinstance(sigs, list):
        return []
    out: list[MemoryItem] = []
    for s in sigs:
        if not isinstance(s, dict):
            continue
        raw_id = str(s.get("id") or "")
        theme = str(s.get("theme") or raw_id or "unknown")
        cwe = s.get("cwe") or []
        if isinstance(cwe, str):
            cwe = [cwe]
        kws = [str(k) for k in (s.get("keywords") or [])][:24]
        globs = [str(g) for g in (s.get("path_globs") or [])][:16]
        def _f(v: Any) -> float | None:
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        active_raw = s.get("active")
        active_v: bool | None
        if active_raw is None:
            active_v = None
        else:
            active_v = bool(active_raw)
        out.append(
            MemoryItem(
                id=_item_id("tp", scope, raw_id, theme),
                kind="tp",
                scope=scope,
                theme=theme,
                cwe=[str(c) for c in cwe],
                keywords=kws,
                path_globs=globs,
                hits=int(s.get("hits") or 1),
                source=str(s.get("source") or "tp-signatures"),
                repo=repo,
                tenant=tenant,
                provenance=_safe_provenance(provenance or path),
                raw_id=raw_id,
                importance_score=_f(s.get("importance_score")),
                decay_weight=_f(s.get("decay_weight")),
                effective_score=_f(s.get("effective_score")),
                last_seen=str(s.get("last_seen") or s.get("updated_at") or ""),
                last_retrieved_at=str(
                    s.get("last_retrieved_at") or s.get("reconsolidated_at") or ""
                ),
                reconsolidated_at=str(s.get("reconsolidated_at") or ""),
                reconsolidation_feature=str(s.get("reconsolidation_feature") or ""),
                active=active_v,
                superseded_by=str(s.get("superseded_by") or ""),
            )
        )
    return out


def load_fp_items(
    path: Path,
    *,
    scope: str,
    repo: str = "",
    tenant: str = "",
    provenance: str = "",
) -> list[MemoryItem]:
    data = _load_json(path)
    if data is None:
        return []
    rules = data.get("rules") if isinstance(data, dict) else data
    if not isinstance(rules, list):
        return []
    out: list[MemoryItem] = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        path_s = str(r.get("path") or "")
        kind_s = str(r.get("kind") or "false_positive")
        reason = str(r.get("reason") or "")[:200]
        raw_id = str(r.get("parent_id") or r.get("id") or path_s or "fp")
        theme = kind_s
        # light theme inference from reason
        low = reason.lower()
        if "sql" in low:
            theme = "sql_injection"
        elif "pickle" in low or "deserial" in low:
            theme = "insecure_deserialization"
        elif "shell" in low or "command" in low:
            theme = "command_injection"
        elif "secret" in low or "api" in low:
            theme = "secrets_exposure"
        out.append(
            MemoryItem(
                id=_item_id("fp", scope, raw_id, path_s or theme),
                kind="fp",
                scope=scope,
                theme=theme,
                path=path_s,
                path_globs=[path_s] if path_s else [],
                keywords=[w for w in re.findall(r"[a-zA-Z0-9_-]{3,}", reason.lower())][
                    :12
                ],
                hits=1,
                source=str(r.get("source") or "fp-rules"),
                reason=reason,
                repo=repo,
                tenant=tenant,
                provenance=_safe_provenance(provenance or path),
                raw_id=raw_id,
            )
        )
    return out


def load_federated_items(
    path: Path,
    *,
    scope: str = "global",
    tenant: str = "",
) -> list[MemoryItem]:
    """Privacy-safe theme/CWE/keywords + F95 effective scores — no private paths (F71/F96)."""
    data = _load_json(path)
    if data is None:
        return []
    sigs = data.get("signals") if isinstance(data, dict) else data
    if not isinstance(sigs, list):
        return []
    out: list[MemoryItem] = []
    for s in sigs:
        if not isinstance(s, dict):
            continue
        theme = str(s.get("theme") or s.get("id") or "unknown")
        # hard privacy: drop any path-like fields
        cwe = s.get("cwe") or []
        if isinstance(cwe, str):
            cwe = [cwe]
        kws = [str(k) for k in (s.get("keywords") or [])][:16]
        # reject if any keyword looks like absolute home path
        kws = [k for k in kws if "/Users/" not in k and not k.startswith("/home/")]

        def _f(v: Any) -> float | None:
            if v is None:
                return None
            try:
                return max(0.0, min(1.0, float(v)))
            except (TypeError, ValueError):
                return None

        # basenames only (never inject as path_globs for privacy)
        src_label = "promoted-signals" if "promoted" in path.name else "federated-signals"
        out.append(
            MemoryItem(
                id=_item_id("federated", scope, str(s.get("id") or theme), theme),
                kind="federated",
                scope=scope,
                theme=theme,
                cwe=[str(c) for c in cwe],
                keywords=kws,
                path_globs=[],  # never paths from federated
                hits=int(s.get("hits") or 1),
                source=src_label,
                tenant=tenant,
                provenance=_safe_provenance(path),
                raw_id=str(s.get("id") or theme),
                importance_score=_f(s.get("importance_score")),
                decay_weight=_f(s.get("decay_weight")),
                effective_score=_f(s.get("effective_score")),
            )
        )
    return out


def _max_eff(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    return max(a or 0.0, b or 0.0)


def merge_items(items: list[MemoryItem]) -> list[MemoryItem]:
    """Dedupe by kind+raw theme+scope preference; sum hits; max effective_score (F96)."""
    best: dict[str, MemoryItem] = {}
    for it in items:
        # key ignores scope so we can keep highest-priority scope copy + hits
        k = f"{it.kind}|{it.raw_id or it.theme}|{it.path}"
        if k not in best:
            best[k] = it
            continue
        old = best[k]
        # prefer narrower scope
        if SCOPE_RANK.get(it.scope, 0) > SCOPE_RANK.get(old.scope, 0):
            it.hits = int(old.hits) + int(it.hits)
            # union keywords
            it.keywords = list(dict.fromkeys(list(it.keywords) + list(old.keywords)))[:24]
            it.path_globs = list(
                dict.fromkeys(list(it.path_globs) + list(old.path_globs))
            )[:16]
            it.effective_score = _max_eff(it.effective_score, old.effective_score)
            it.importance_score = _max_eff(it.importance_score, old.importance_score)
            best[k] = it
        else:
            old.hits = int(old.hits) + int(it.hits)
            old.keywords = list(
                dict.fromkeys(list(old.keywords) + list(it.keywords))
            )[:24]
            old.path_globs = list(
                dict.fromkeys(list(old.path_globs) + list(it.path_globs))
            )[:16]
            old.effective_score = _max_eff(old.effective_score, it.effective_score)
            old.importance_score = _max_eff(old.importance_score, it.importance_score)
            best[k] = old
    return list(best.values())


def ingest(
    root: Path,
    *,
    repo: str = "",
    out_dir: Path | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    """Build unified scoped store from available sources."""
    tenant = _tenant_id()
    repo = repo or (os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or "")
    items: list[MemoryItem] = []

    # repo scope: local .torii
    tp = _tp_path(root)
    if tp.is_file():
        items.extend(
            load_tp_items(tp, scope="repo", repo=repo, tenant=tenant, provenance=str(tp))
        )
    fp = _fp_path(root)
    if fp.is_file():
        items.extend(
            load_fp_items(fp, scope="repo", repo=repo, tenant=tenant, provenance=str(fp))
        )

    # run scope: out_dir copies
    if out_dir:
        od = Path(out_dir)
        for name, loader, kind_scope in (
            ("tp-signatures.json", load_tp_items, "run"),
            ("fp-rules.json", load_fp_items, "run"),
        ):
            p = od / name
            if p.is_file():
                if name.startswith("tp"):
                    items.extend(
                        loader(p, scope="run", repo=repo, tenant=tenant, provenance=str(p))
                    )
                else:
                    items.extend(
                        loader(p, scope="run", repo=repo, tenant=tenant, provenance=str(p))
                    )

    # tenant: if tenant set and hub path exists
    if tenant:
        ten_dir = root / "memory" / "tenants" / tenant
        for name, loader in (
            ("tp-signatures.json", load_tp_items),
            ("fp-rules.json", load_fp_items),
        ):
            p = ten_dir / name
            if p.is_file():
                items.extend(
                    loader(p, scope="tenant", repo=repo, tenant=tenant, provenance=str(p))
                )

    # agent: hub memory/repos/{slug}
    if repo:
        slug = _slug_repo(repo.replace("/", "--"))
        hub = root / "memory" / "repos" / slug
        for name, loader in (
            ("tp-signatures.json", load_tp_items),
            ("fp-rules.json", load_fp_items),
        ):
            p = hub / name
            if p.is_file():
                items.extend(
                    loader(p, scope="agent", repo=repo, tenant=tenant, provenance=str(p))
                )

    # global federated (privacy-safe)
    fed = _fed_path(root)
    if fed.is_file():
        items.extend(load_federated_items(fed, scope="global", tenant=tenant))
    if out_dir and (Path(out_dir) / "federated-signals.json").is_file():
        items.extend(
            load_federated_items(
                Path(out_dir) / "federated-signals.json",
                scope="run",
                tenant=tenant,
            )
        )

    merged = merge_items(items)
    store_path = store_path or default_store_path(root)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "updated_at": _now(),
        "repo": repo,
        "tenant": tenant,
        "count": len(merged),
        "items": [m.to_dict() for m in merged],
        "by_kind": {
            "tp": sum(1 for m in merged if m.kind == "tp"),
            "fp": sum(1 for m in merged if m.kind == "fp"),
            "federated": sum(1 for m in merged if m.kind == "federated"),
        },
        "by_scope": {
            s: sum(1 for m in merged if m.scope == s)
            for s in SCOPE_RANK
        },
    }
    store_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {
        "feature": FEATURE,
        "store": str(store_path),
        "count": len(merged),
        "by_kind": doc["by_kind"],
        "by_scope": doc["by_scope"],
    }


def load_store(path: Path | None = None, root: Path | None = None) -> list[MemoryItem]:
    p = path or default_store_path(root)
    data = _load_json(p)
    if not isinstance(data, dict):
        return []
    out: list[MemoryItem] = []
    for d in data.get("items") or []:
        if not isinstance(d, dict):
            continue
        def _f(v: Any) -> float | None:
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        out.append(
            MemoryItem(
                id=str(d.get("id") or ""),
                kind=str(d.get("kind") or ""),
                scope=str(d.get("scope") or "repo"),
                theme=str(d.get("theme") or ""),
                cwe=[str(c) for c in (d.get("cwe") or [])],
                keywords=[str(k) for k in (d.get("keywords") or [])],
                path_globs=[str(g) for g in (d.get("path_globs") or [])],
                path=str(d.get("path") or ""),
                reason=str(d.get("reason") or ""),
                hits=int(d.get("hits") or 1),
                source=str(d.get("source") or ""),
                repo=str(d.get("repo") or ""),
                tenant=str(d.get("tenant") or ""),
                provenance=str(d.get("provenance") or ""),
                raw_id=str(d.get("raw_id") or ""),
                importance_score=_f(d.get("importance_score")),
                decay_weight=_f(d.get("decay_weight")),
                effective_score=_f(d.get("effective_score")),
                last_seen=str(d.get("last_seen") or ""),
                last_retrieved_at=str(
                    d.get("last_retrieved_at") or d.get("reconsolidated_at") or ""
                ),
                reconsolidated_at=str(d.get("reconsolidated_at") or ""),
                reconsolidation_feature=str(d.get("reconsolidation_feature") or ""),
                active=(
                    None
                    if d.get("active") is None
                    else bool(d.get("active"))
                ),
                superseded_by=str(d.get("superseded_by") or ""),
            )
        )
    return out


def _normalize_path(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def path_match(item: MemoryItem, changed_paths: list[str]) -> float:
    """0-1 score: does item touch any changed path?"""
    if not changed_paths:
        return 0.0
    globs = [ _normalize_path(g) for g in (item.path_globs or []) if g]
    if item.path:
        globs.append(_normalize_path(item.path))
    if not globs:
        return 0.0  # theme-only: no path boost
    best = 0.0
    for cp in changed_paths:
        cpn = _normalize_path(cp)
        base = Path(cpn).name
        for g in globs:
            if not g:
                continue
            if g == cpn or cpn.endswith("/" + g) or cpn.endswith(g):
                best = max(best, 1.0)
            elif g == base or cpn.endswith("/" + base) and g in cpn:
                best = max(best, 0.6)
            elif g in cpn or cpn in g:
                best = max(best, 0.75)
            elif Path(g).name == base:
                best = max(best, 0.5)
    return best


def rank_score(item: MemoryItem, changed_paths: list[str]) -> float:
    pm = path_match(item, changed_paths)
    scope_w = SCOPE_RANK.get(item.scope, 0) / 50.0
    hits_w = min(1.0, (item.hits or 1) / 10.0)
    # F94/F96: effective_score from consolidation or promoted federated signals
    eff_w = 0.0
    try:
        raw_eff = getattr(item, "effective_score", None)
        if raw_eff is None and hasattr(item, "to_dict"):
            raw_eff = (item.to_dict() or {}).get("effective_score")
        if raw_eff is not None:
            eff_w = max(0.0, min(1.0, float(raw_eff)))
    except (TypeError, ValueError):
        eff_w = 0.0
    # F96: promoted federated high-strength themes get a theme boost (still < path match)
    fed_boost = 0.0
    if item.kind == "federated" and eff_w >= 0.5:
        fed_boost = 0.06 * eff_w
    # path match dominates; theme-only items still rank via scope+hits but lower
    if pm > 0:
        base = 0.48 * pm + 0.20 * scope_w + 0.16 * hits_w
        return base + (0.14 * eff_w if eff_w else 0.02 * hits_w) + fed_boost
    base = 0.14 * scope_w + 0.10 * hits_w + (0.05 if item.kind == "tp" else 0.0)
    # theme-only: effective is the main quality signal (F96)
    return base + (0.14 * eff_w if eff_w else 0.0) + fed_boost


@dataclass
class Conflict:
    theme: str
    tp_id: str
    fp_id: str
    resolution: str  # prefer_fp | prefer_tp | needs_evidence
    reason: str


def detect_conflicts(
    items: list[MemoryItem],
    changed_paths: list[str],
) -> tuple[list[Conflict], set[str]]:
    """Return conflicts and set of item ids to suppress on inject."""
    tps = [i for i in items if i.kind == "tp"]
    fps = [i for i in items if i.kind == "fp"]
    conflicts: list[Conflict] = []
    suppress: set[str] = set()

    for tp in tps:
        for fp in fps:
            # theme overlap or keyword overlap
            theme_hit = (
                tp.theme
                and fp.theme
                and (
                    tp.theme == fp.theme
                    or tp.theme in fp.theme
                    or fp.theme in tp.theme
                    or fp.theme in ("false_positive", "resolved")
                )
            )
            # also match if FP path is under a TP path_glob
            fp_pm = path_match(fp, changed_paths) if changed_paths else (
                1.0 if fp.path else 0.0
            )
            tp_pm = path_match(tp, changed_paths)
            path_related = False
            if fp.path and tp.path_globs:
                fpn = _normalize_path(fp.path)
                for g in tp.path_globs:
                    gn = _normalize_path(g)
                    if gn in fpn or fpn.endswith(gn) or Path(fpn).name == Path(gn).name:
                        path_related = True
                        break
            if not theme_hit and not path_related:
                # unanchored FP vs any TP: only conflict if both touch same changed path
                if not (fp_pm > 0 and tp_pm > 0):
                    continue

            # Resolution policy (Mem0-style conflict + Torii FP semantics):
            # 1) Path-anchored FP on a changed/matched path → prefer FP (don't re-raise)
            # 2) TP path-matched + FP unanchored → prefer TP
            # 3) Both path-matched same area → needs_evidence (show both, mark conflict)
            if fp.path and (fp_pm >= 0.5 or path_related):
                if tp_pm >= 0.5 or path_related:
                    res = "needs_evidence"
                    reason = "path-anchored FP and path-matched TP overlap"
                    # do not fully suppress TP; inject conflict note
                else:
                    res = "prefer_fp"
                    reason = "path-anchored FP suppresses theme-only TP"
                    suppress.add(tp.id)
            elif not fp.path and tp_pm >= 0.5:
                res = "prefer_tp"
                reason = "path-matched TP beats unanchored FP"
                suppress.add(fp.id)
            elif not fp.path and tp_pm < 0.5:
                res = "prefer_fp"
                reason = "unanchored FP vs theme-only TP → caution suppress TP bulk"
                # don't suppress — just note; bulk TP still useful for benches
                continue
            else:
                res = "needs_evidence"
                reason = "ambiguous FP/TP overlap"

            conflicts.append(
                Conflict(
                    theme=tp.theme or fp.theme,
                    tp_id=tp.id,
                    fp_id=fp.id,
                    resolution=res,
                    reason=reason,
                )
            )
    return conflicts, suppress


def recall(
    items: list[MemoryItem],
    changed_paths: list[str],
    *,
    tp_max: int | None = None,
    fp_max: int | None = None,
    fed_max: int = 6,
    include_federated: bool = True,
) -> dict[str, Any]:
    tp_max = tp_max if tp_max is not None else _int_env("TORII_SCOPED_TP_MAX", 8)
    fp_max = fp_max if fp_max is not None else _int_env("TORII_SCOPED_FP_MAX", 12)

    conflicts, suppress = detect_conflicts(items, changed_paths)

    scored: list[tuple[float, MemoryItem]] = []
    for it in items:
        if it.id in suppress:
            continue
        if it.kind == "federated" and not include_federated:
            continue
        scored.append((rank_score(it, changed_paths), it))
    scored.sort(key=lambda x: (-x[0], -SCOPE_RANK.get(x[1].scope, 0), -x[1].hits))

    tps = [(s, i) for s, i in scored if i.kind == "tp"][:tp_max]
    fps = [(s, i) for s, i in scored if i.kind == "fp"][:fp_max]
    feds = [(s, i) for s, i in scored if i.kind == "federated"][:fed_max]

    path_matched_tp = sum(1 for s, i in tps if path_match(i, changed_paths) > 0)
    result: dict[str, Any] = {
        "feature": FEATURE,
        "changed_paths": changed_paths,
        "tp": [
            {**i.to_dict(), "score": round(s, 4), "path_match": path_match(i, changed_paths)}
            for s, i in tps
        ],
        "fp": [
            {**i.to_dict(), "score": round(s, 4), "path_match": path_match(i, changed_paths)}
            for s, i in fps
        ],
        "federated": [
            {**i.to_dict(), "score": round(s, 4)}
            for s, i in feds
        ],
        "conflicts": [asdict(c) for c in conflicts],
        "suppressed": sorted(suppress),
        "metrics": {
            "tp_returned": len(tps),
            "fp_returned": len(fps),
            "fed_returned": len(feds),
            "path_matched_tp": path_matched_tp,
            "conflict_count": len(conflicts),
            "suppress_count": len(suppress),
        },
    }
    # F97: Letta-style core/archival tiers (soft)
    try:
        if (os.environ.get("TORII_MEMORY_TIERS") or "1").strip().lower() not in _FALSEY:
            import importlib.util

            tier_path = Path(__file__).resolve().parent / "memory_tiers.py"
            if tier_path.is_file():
                spec = importlib.util.spec_from_file_location("memory_tiers", tier_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["memory_tiers"] = mod
                    spec.loader.exec_module(mod)
                    if mod.enabled():
                        result = mod.apply_to_recall_result(result)
    except Exception:
        pass
    return result


def render_section(result: dict[str, Any]) -> str:
    lines = [
        MARKER,
        "## Scoped memory recall (F75 — Mem0 multi-scope, budgeted)",
        "",
        "Selective TP/FP memory ranked by **path match → scope → hits → effective_score** (F94/F96).",
        "Promoted federated themes carry privacy-safe **effective_score**; stale low-strength items rank down.",
        "Conflicts: path-anchored FP suppresses theme-only TP; path-matched TP beats unanchored FP.",
        "Do **not** re-raise FP-suppressed themes without **new** path evidence.",
        "",
    ]
    # F97: surface tiers first when present
    tiers = result.get("tiers") if isinstance(result.get("tiers"), dict) else None
    if tiers and result.get("tiers_enabled"):
        try:
            import importlib.util

            tier_path = Path(__file__).resolve().parent / "memory_tiers.py"
            if tier_path.is_file():
                spec = importlib.util.spec_from_file_location("memory_tiers_render", tier_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    tier_md = mod.render_tiers_section(result)
                    # embed without outer double blank
                    for ln in tier_md.strip().splitlines():
                        if ln.startswith("<!--"):
                            continue
                        lines.append(ln)
                    lines.append("")
        except Exception:
            pass
    tps = result.get("tp") or []
    if tps:
        lines.append("### True-positive signatures (scoped)")
        for s in tps:
            kws = ", ".join((s.get("keywords") or [])[:6])
            cwe = ",".join(s.get("cwe") or []) or "n/a"
            tier = s.get("tier") or ""
            tier_s = f" tier={tier}" if tier else ""
            lines.append(
                f"- `{s.get('raw_id') or s.get('id')}` scope={s.get('scope')} "
                f"theme={s.get('theme')} cwe={cwe} hits={s.get('hits')} "
                f"path_match={s.get('path_match', 0)}{tier_s} keywords=[{kws}]"
            )
        lines.append("")
    fps = result.get("fp") or []
    if fps:
        lines.append("### False-positive / resolved (scoped)")
        for s in fps:
            path = s.get("path") or "(unanchored)"
            tier = s.get("tier") or ""
            tier_s = f" tier={tier}" if tier else ""
            lines.append(
                f"- scope={s.get('scope')} path=`{path}`{tier_s} "
                f"kind/theme={s.get('theme')} — { (s.get('reason') or '')[:80] }"
            )
        lines.append("")
    confs = result.get("conflicts") or []
    if confs:
        lines.append("### Memory conflicts (resolved)")
        for c in confs[:8]:
            lines.append(
                f"- theme={c.get('theme')} → **{c.get('resolution')}** "
                f"({c.get('reason')})"
            )
        lines.append("")
    feds = result.get("federated") or []
    if feds:
        lines.append("### Federated themes (global, path-free)")
        for s in feds[:6]:
            kws = ", ".join((s.get("keywords") or [])[:5])
            tier = s.get("tier") or ""
            tier_s = f" tier={tier}" if tier else ""
            lines.append(
                f"- `{s.get('theme')}` hits={s.get('hits')}{tier_s} keywords=[{kws}]"
            )
        lines.append("")
    lines.append("<!-- /torii-f75-scoped-memory -->")
    return "\n".join(lines) + "\n"


def inject_into_prompt(
    prompt_path: Path,
    result: dict[str, Any],
    *,
    replace_tp: bool | None = None,
) -> bool:
    if not enabled():
        return False
    path = Path(prompt_path)
    if not path.is_file() and not path.parent.exists():
        return False
    section = render_section(result)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""

    if MARKER in text:
        text = re.sub(
            r"<!-- torii-f75-scoped-memory -->.*?<!-- /torii-f75-scoped-memory -->\n?",
            section,
            text,
            count=1,
            flags=re.S,
        )
    else:
        text = text.rstrip() + "\n\n" + section

    # Optionally replace bulk F70 TP section with pointer (budget tokens)
    if replace_tp is None:
        raw = (os.environ.get("TORII_SCOPED_REPLACE_TP") or "1").strip().lower()
        replace_tp = raw not in _FALSEY
    if replace_tp and "<!-- torii-f70-tp-signatures -->" in text:
        stub = (
            "<!-- torii-f70-tp-signatures -->\n"
            "## Known true-positive signatures (F70 → superseded by F75 scoped recall)\n\n"
            "See **Scoped memory recall (F75)** below for path/scope-ranked TP/FP.\n\n"
        )
        text = re.sub(
            r"<!-- torii-f70-tp-signatures -->[\s\S]*?(?=\n<!--|\Z)",
            stub,
            text,
            count=1,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return True


def parse_changed_paths(files_arg: str, root: Path) -> list[str]:
    """Accept comma list, files.txt / JSON list path, or a single changed path.

    Important: a *source file* that exists on disk (e.g. demo/insecure/app.py)
    must NOT be read as a path list — only known list artifacts are loaded.
    """
    if not files_arg:
        return []
    raw = files_arg.strip()
    p = Path(raw)
    is_list_artifact = False
    if p.is_file():
        name = p.name.lower()
        is_list_artifact = (
            name in {"files.txt", "changed.txt", "paths.txt", "changed-files.txt"}
            or name.endswith(".files.txt")
            or p.suffix.lower() in {".json", ".list"}
            or "files.txt" in str(p).replace("\\", "/")
        )
    if p.is_file() and is_list_artifact:
        text = p.read_text(encoding="utf-8", errors="replace")
        paths: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("Total:") or line.startswith("#"):
                continue
            m = re.search(r"`([^`]+)`", line)
            if m:
                paths.append(m.group(1))
                continue
            if re.match(r"^[\w./-]+\.\w+", line):
                paths.append(line.split()[0])
        if paths:
            return paths
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [
                    str(x.get("path") or x.get("filename") or x)
                    if isinstance(x, dict)
                    else str(x)
                    for x in data
                ]
        except json.JSONDecodeError:
            pass
        return paths
    if "," in raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return [raw]


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _root()
    out = ingest(
        root,
        repo=args.repo or "",
        out_dir=Path(args.out_dir) if args.out_dir else None,
        store_path=Path(args.store) if args.store else None,
    )
    print(json.dumps(out, indent=2))
    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    root = _root()
    store = Path(args.store) if args.store else default_store_path(root)
    if not store.is_file() or args.refresh:
        ingest(
            root,
            repo=args.repo or "",
            out_dir=Path(args.out_dir) if args.out_dir else None,
            store_path=store,
        )
    items = load_store(store, root)
    paths = parse_changed_paths(args.files or "", root)
    result = recall(
        items,
        paths,
        tp_max=args.tp_max,
        fp_max=args.fp_max,
    )
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


def cmd_conflict(args: argparse.Namespace) -> int:
    root = _root()
    store = Path(args.store) if args.store else default_store_path(root)
    if not store.is_file():
        ingest(root, store_path=store)
    items = load_store(store, root)
    paths = parse_changed_paths(args.files or "", root)
    conflicts, suppress = detect_conflicts(items, paths)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "conflicts": [asdict(c) for c in conflicts],
                "suppressed": sorted(suppress),
            },
            indent=2,
        )
    )
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    root = _root()
    store = Path(args.store) if args.store else default_store_path(root)
    if not store.is_file() or args.refresh:
        ingest(
            root,
            repo=args.repo or "",
            out_dir=Path(args.out_dir) if args.out_dir else None,
            store_path=store,
        )
    items = load_store(store, root)
    paths = parse_changed_paths(args.files or "", root)
    result = recall(items, paths)
    ok = inject_into_prompt(Path(args.prompt), result)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "injected": ok,
                "prompt": args.prompt,
                "metrics": result.get("metrics"),
            },
            indent=2,
        )
    )
    return 0 if ok else 1


def cmd_score(args: argparse.Namespace) -> int:
    """Score a recall JSON or recompute from store+files."""
    if args.recall_json:
        result = json.loads(Path(args.recall_json).read_text(encoding="utf-8"))
    else:
        root = _root()
        store = Path(args.store) if args.store else default_store_path(root)
        if not store.is_file():
            ingest(root, store_path=store)
        items = load_store(store, root)
        paths = parse_changed_paths(args.files or "", root)
        result = recall(items, paths)
    m = result.get("metrics") or {}
    tp_n = int(m.get("tp_returned") or 0)
    path_tp = int(m.get("path_matched_tp") or 0)
    path_precision = (path_tp / tp_n) if tp_n else 1.0
    # budget: returned ≤ max
    tp_max = _int_env("TORII_SCOPED_TP_MAX", 8)
    budget_ok = tp_n <= tp_max
    payload = {
        "feature": FEATURE,
        "path_precision": round(path_precision, 4),
        "path_matched_tp": path_tp,
        "tp_returned": tp_n,
        "conflict_count": m.get("conflict_count") or 0,
        "suppress_count": m.get("suppress_count") or 0,
        "budget_ok": budget_ok,
        "passed": budget_ok and (tp_n == 0 or path_precision >= 0.0),
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Isolated offline fixture: path filter, conflict, inject, privacy."""
    import tempfile

    root = _root()
    td = Path(tempfile.mkdtemp(prefix="torii-f75-"))
    torii = td / ".torii"
    torii.mkdir(parents=True)
    # TP with path_globs for demo/insecure and a distractor
    tp_doc = {
        "schema_version": 1,
        "signatures": [
            {
                "id": "sqli-search",
                "theme": "sql_injection",
                "cwe": ["CWE-89"],
                "keywords": ["sql injection", "sqli"],
                "path_globs": ["demo/insecure/app.py", "app.py"],
                "hits": 5,
            },
            {
                "id": "unrelated-xss",
                "theme": "xss",
                "cwe": ["CWE-79"],
                "keywords": ["xss", "innerHTML"],
                "path_globs": ["frontend/widget.js"],
                "hits": 9,
            },
            {
                "id": "pickle-load",
                "theme": "insecure_deserialization",
                "cwe": ["CWE-502"],
                "keywords": ["pickle", "loads"],
                "path_globs": ["demo/insecure/app.py"],
                "hits": 3,
            },
        ],
    }
    (torii / "tp-signatures.json").write_text(
        json.dumps(tp_doc, indent=2) + "\n", encoding="utf-8"
    )
    # FP: path-anchored on app.py sql + unanchored
    fp_doc = {
        "schema_version": 1,
        "rules": [
            {
                "kind": "false_positive",
                "path": "demo/insecure/app.py",
                "reason": "sql helper is parameterized — false positive on sqli",
                "source": "fixture",
            },
            {
                "kind": "false_positive",
                "path": "",
                "reason": "generic noise",
                "source": "fixture",
            },
        ],
    }
    (torii / "fp-rules.json").write_text(
        json.dumps(fp_doc, indent=2) + "\n", encoding="utf-8"
    )
    # federated with poison path attempt
    fed = {
        "signals": [
            {
                "id": "sql_injection",
                "theme": "sql_injection",
                "cwe": ["CWE-89"],
                "keywords": ["sql injection", "cwe-89"],
                "hits": 10,
                "effective_score": 0.4,
            },
            {
                "id": "poison",
                "theme": "secrets_exposure",
                "keywords": ["/Users/evil/secret", "api_key"],
                "hits": 1,
            },
        ]
    }
    (torii / "federated-signals.json").write_text(
        json.dumps(fed, indent=2) + "\n", encoding="utf-8"
    )
    # F96: promoted signals preferred + higher effective ranks first
    fed_dir = td / "memory" / "federation"
    fed_dir.mkdir(parents=True, exist_ok=True)
    promoted = {
        "signals": [
            {
                "id": "command_injection",
                "theme": "command_injection",
                "cwe": ["CWE-78"],
                "keywords": ["shell=true", "command injection"],
                "hits": 6,
                "effective_score": 0.91,
                "importance_score": 0.85,
            },
            {
                "id": "weak_info",
                "theme": "info_disclosure",
                "keywords": ["debug"],
                "hits": 20,
                "effective_score": 0.08,
            },
        ]
    }
    (fed_dir / "promoted-signals.json").write_text(
        json.dumps(promoted, indent=2) + "\n", encoding="utf-8"
    )

    old = {
        "TORII_ROOT": os.environ.get("TORII_ROOT"),
        "TORII_TP_SIGNATURES_FILE": os.environ.get("TORII_TP_SIGNATURES_FILE"),
        "TORII_FP_RULES_FILE": os.environ.get("TORII_FP_RULES_FILE"),
        "TORII_FEDERATED_SIGNALS_FILE": os.environ.get("TORII_FEDERATED_SIGNALS_FILE"),
        "TORII_SCOPED_MEMORY_FILE": os.environ.get("TORII_SCOPED_MEMORY_FILE"),
        "TORII_SCOPED_MEMORY": os.environ.get("TORII_SCOPED_MEMORY"),
        "TORII_SCOPED_TP_MAX": os.environ.get("TORII_SCOPED_TP_MAX"),
    }
    try:
        os.environ["TORII_ROOT"] = str(td)
        os.environ["TORII_TP_SIGNATURES_FILE"] = str(torii / "tp-signatures.json")
        os.environ["TORII_FP_RULES_FILE"] = str(torii / "fp-rules.json")
        # Prefer promoted-signals via _fed_path (unset explicit fed file after writing promoted)
        os.environ.pop("TORII_FEDERATED_SIGNALS_FILE", None)
        os.environ["TORII_SCOPED_MEMORY_FILE"] = str(torii / STORE_NAME)
        os.environ["TORII_SCOPED_MEMORY"] = "1"
        os.environ["TORII_SCOPED_TP_MAX"] = "4"

        ing = ingest(td, repo="fixture/demo")
        items = load_store(default_store_path(td), td)
        paths = ["demo/insecure/app.py"]
        result = recall(items, paths, tp_max=4, fp_max=8)

        # path-matched TPs should rank above widget.js xss when both returned
        tp_ids = [t.get("raw_id") or t.get("id") for t in result["tp"]]
        # xss has higher hits but wrong path — if returned, should score lower than sqli/pickle
        scores = {t.get("raw_id"): t.get("score") for t in result["tp"]}
        path_ok = True
        if "sqli-search" in scores and "unrelated-xss" in scores:
            path_ok = float(scores["sqli-search"]) > float(scores["unrelated-xss"])
        # at least one path-matched TP present
        path_matched = any(
            (t.get("path_match") or 0) > 0 for t in result["tp"]
        )
        # conflict: FP on app.py vs TP sqli
        has_conflict = len(result.get("conflicts") or []) >= 1
        # privacy: no /Users/ in federated keywords in store
        privacy_ok = True
        for it in items:
            for kw in it.keywords:
                if "/Users/" in kw:
                    privacy_ok = False
        # F96: promoted high-effective federated ranks above low-effective
        fed_items = [i for i in items if i.kind == "federated"]
        fed_by_theme = {i.theme: i for i in fed_items}
        promoted_ok = (
            "command_injection" in fed_by_theme
            and float(fed_by_theme["command_injection"].effective_score or 0) >= 0.9
        )
        # theme-only rank: high effective > low effective (no path match)
        high = MemoryItem(
            id="h", kind="federated", scope="global", theme="command_injection",
            hits=2, effective_score=0.91,
        )
        low = MemoryItem(
            id="l", kind="federated", scope="global", theme="info_disclosure",
            hits=20, effective_score=0.08,
        )
        effective_rank_ok = rank_score(high, []) > rank_score(low, [])
        # inject
        prompt = td / "prompt.md"
        prompt.write_text("# prompt\n\n<!-- torii-f70-tp-signatures -->\n## bulk TP\n- all\n\n", encoding="utf-8")
        inj = inject_into_prompt(prompt, result, replace_tp=True)
        body = prompt.read_text(encoding="utf-8")
        inject_ok = inj and MARKER in body and "Scoped memory recall" in body
        # superseded stub
        replace_ok = "superseded by F75" in body

        fixture_pass = (
            ing["count"] >= 3
            and path_matched
            and path_ok
            and has_conflict
            and privacy_ok
            and inject_ok
            and replace_ok
            and promoted_ok
            and effective_rank_ok
            and result["metrics"]["tp_returned"] <= 4
        )
        payload = {
            "feature": FEATURE,
            "feature_f96": True,
            "fixture_pass": fixture_pass,
            "tmpdir": str(td),
            "ingest_count": ing["count"],
            "tp_ids": tp_ids,
            "scores": scores,
            "path_matched": path_matched,
            "path_ok": path_ok,
            "has_conflict": has_conflict,
            "privacy_ok": privacy_ok,
            "promoted_ok": promoted_ok,
            "effective_rank_ok": effective_rank_ok,
            "inject_ok": inject_ok,
            "replace_ok": replace_ok,
            "metrics": result["metrics"],
            "conflicts": result.get("conflicts"),
        }
        print(json.dumps(payload, indent=2))
        return 0 if fixture_pass else 1
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    store = Path(args.store) if args.store else default_store_path(root)
    data = _load_json(store) if store.is_file() else {}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "store": str(store),
                "exists": store.is_file(),
                "count": (data or {}).get("count") if isinstance(data, dict) else 0,
                "by_kind": (data or {}).get("by_kind") if isinstance(data, dict) else {},
                "by_scope": (data or {}).get("by_scope") if isinstance(data, dict) else {},
                "tp_max": _int_env("TORII_SCOPED_TP_MAX", 8),
                "fp_max": _int_env("TORII_SCOPED_FP_MAX", 12),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="F75 scoped memory recall (Mem0 multi-scope over TP/FP)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="Build unified scoped store")
    pi.add_argument("--repo", default="")
    pi.add_argument("--out-dir", default="")
    pi.add_argument("--store", default="")
    pi.set_defaults(func=cmd_ingest)

    pr = sub.add_parser("recall", help="Path+scope ranked recall")
    pr.add_argument("--files", default="", help="comma paths or files.txt")
    pr.add_argument("--repo", default="")
    pr.add_argument("--out-dir", default="")
    pr.add_argument("--store", default="")
    pr.add_argument("--out", default="")
    pr.add_argument("--tp-max", type=int, default=None)
    pr.add_argument("--fp-max", type=int, default=None)
    pr.add_argument("--refresh", action="store_true")
    pr.set_defaults(func=cmd_recall)

    pc = sub.add_parser("conflict", help="TP vs FP conflict report")
    pc.add_argument("--files", default="")
    pc.add_argument("--store", default="")
    pc.set_defaults(func=cmd_conflict)

    pj = sub.add_parser("inject", help="Budgeted inject into prompt")
    pj.add_argument("--prompt", required=True)
    pj.add_argument("--files", default="")
    pj.add_argument("--repo", default="")
    pj.add_argument("--out-dir", default="")
    pj.add_argument("--store", default="")
    pj.add_argument("--json-out", default="")
    pj.add_argument("--refresh", action="store_true")
    pj.set_defaults(func=cmd_inject)

    ps = sub.add_parser("score", help="Metrics for a recall")
    ps.add_argument("--recall-json", default="")
    ps.add_argument("--files", default="")
    ps.add_argument("--store", default="")
    ps.set_defaults(func=cmd_score)

    sub.add_parser("fixture", help="Offline isolation fixture").set_defaults(
        func=cmd_fixture
    )
    pst = sub.add_parser("status", help="Store summary")
    pst.add_argument("--store", default="")
    pst.set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
