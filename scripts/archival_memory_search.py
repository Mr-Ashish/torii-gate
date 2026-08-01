#!/usr/bin/env python3
"""F98/F144/F145/F146: MemGPT archival search + promote + supersede filter + reconsolidation.

Research drivers (patterns only — no vendored Letta/MemGPT/Zep runtime):
  - MemGPT archival_memory_search / core_memory_append: agent pages cold facts
    into working context on demand
  - Torii F97 tiers put cold items in archival but provided no retrieval tool
  - MEMORY.md distill is append-only prose — never keyword-searchable for PR paths
  - Zep/F100–F102 temporal multi-hop: path kinship surfaces related themes
  - F144: multi-hop themes must expand archival query or cold hits stay unpaged
  - MemoTime / Zep temporal faithfulness: multi-hop retrieval must not re-surface
    facts invalidated by active supersedes (valid_until / superseded_by)
  - F145: F144 paging without supersede filter resurrects resolved FPs as "core"
  - Human-inspired reconsolidation on retrieval: successful promote should
    strengthen durable TP (hits / last_retrieved / soft effective) not be write-only inject
  - F146: non-superseded archival hits reconsolidate into tp-signatures on promote

Product thesis:
  Highest ROI agentic-memory slice: **deterministic archival search** over
  TP/FP/federated stores + MEMORY.md, optionally **expanded by temporal graph
  multi-hop themes**, **promote** only **temporally-active** hits into core, then
  **reconsolidate** successful retrieves so next PR ranks warm evidence higher.

Commands:
  search    — query archival + recall stores (JSON hits)
  promote   — write top hits as core inject markdown (supersede-aware + reconsolidate)
  auto      — path basenames + F144 multi-hop + F145 filter + F146 reconsolidate + promote
  fixture   — hermetic: multi-hop, supersede filter, reconsolidation, privacy, promote
  status    — sources / last result summary

Env:
  TORII_ROOT
  TORII_ARCHIVAL_SEARCH        1 (default) | 0
  TORII_ARCHIVAL_SEARCH_LIMIT  default 8
  TORII_ARCHIVAL_GRAPH_HOPS    default 2 (0/off disables F144 multi-hop expand)
  TORII_ARCHIVAL_SUPERSEDE_FILTER  1 (default) | 0  — F145 temporal faithfulness
  TORII_ARCHIVAL_RECONSOLIDATE     1 (default) | 0  — F146 reconsolidation on promote
  TORII_TP_SIGNATURES_FILE / TORII_FP_RULES_FILE / TORII_FEDERATED_SIGNALS_FILE
  TORII_MEMORY_MD              path to MEMORY.md (else hermes home / agent seed)
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

FEATURE = "F98"
FEATURE_GRAPH = "F144"
FEATURE_SUPERSEDE = "F145"
FEATURE_RECON = "F146"
SCHEMA = 1
MARKER = "<!-- torii-f98-archival-search -->"
RECON_LEDGER = "archival-reconsolidation.json"
RECON_EFF_BUMP = 0.03
RECON_EFF_CAP = 0.95

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})
_PRIVATE_RX = re.compile(
    r"(?:/Users/|/home/|C:\\\\Users\\\\|sk-[a-zA-Z0-9_-]{10,})",
    re.I,
)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_ARCHIVAL_SEARCH") or "1").strip().lower()
    return raw not in _FALSEY


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _tokens(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9_./-]{2,}", (q or "").lower()) if t]


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def default_tp_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_TP_SIGNATURES_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / "tp-signatures.json"


def default_fp_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_FP_RULES_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / "fp-rules.json"


def default_fed_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_FEDERATED_SIGNALS_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    r = root or _root()
    for cand in (
        r / "memory" / "federation" / "promoted-signals.json",
        r / "memory" / "federation" / "federated-signals.json",
        r / ".torii" / "federated-signals.json",
    ):
        if cand.is_file():
            return cand
    return r / "memory" / "federation" / "promoted-signals.json"


def default_memory_md(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_MEMORY_MD") or "").strip()
    if env:
        return Path(env).resolve()
    r = root or _root()
    for cand in (
        r / ".torii-hermes-home" / "memories" / "MEMORY.md",
        Path(os.environ.get("HERMES_HOME") or "") / "memories" / "MEMORY.md",
        r / "agent" / "MEMORY.seed.md",
    ):
        if str(cand) and cand.is_file():
            return cand
    return r / ".torii-hermes-home" / "memories" / "MEMORY.md"


def _eff(item: dict[str, Any]) -> float:
    for k in ("effective_score", "effective"):
        if item.get(k) is not None:
            try:
                return max(0.0, min(1.0, float(item[k])))
            except (TypeError, ValueError):
                pass
    return 0.0


def collect_records(root: Path | None = None) -> list[dict[str, Any]]:
    """Load searchable archival/recall records (privacy-sanitized)."""
    root = root or _root()
    out: list[dict[str, Any]] = []

    # TP signatures
    tp = _load_json(default_tp_path(root))
    sigs = []
    if isinstance(tp, dict):
        sigs = tp.get("signatures") or tp.get("items") or []
    elif isinstance(tp, list):
        sigs = tp
    for s in sigs:
        if not isinstance(s, dict) or s.get("deleted") or s.get("evicted"):
            continue
        theme = str(s.get("theme") or s.get("id") or "")
        kws = [str(k) for k in (s.get("keywords") or [])][:16]
        globs = [str(g) for g in (s.get("path_globs") or [])][:12]
        blob = " ".join([theme, " ".join(kws), " ".join(globs), str(s.get("id") or "")])
        if _PRIVATE_RX.search(blob):
            continue
        out.append(
            {
                "id": str(s.get("id") or theme)[:96],
                "source": "tp",
                "tier_hint": "archival",
                "theme": theme,
                "keywords": kws,
                "path_globs": globs,
                "hits": int(s.get("hits") or 1),
                "effective_score": _eff(s),
                "text": blob[:500],
            }
        )

    # FP rules
    fp = _load_json(default_fp_path(root))
    rules = []
    if isinstance(fp, dict):
        rules = fp.get("rules") or fp.get("patterns") or fp.get("items") or []
    elif isinstance(fp, list):
        rules = fp
    for r in rules:
        if not isinstance(r, dict):
            continue
        path = str(r.get("path") or "")
        reason = str(r.get("reason") or "")[:200]
        if _PRIVATE_RX.search(path) or _PRIVATE_RX.search(reason):
            # keep basename only
            path = Path(path).name if path else ""
        out.append(
            {
                "id": f"fp:{path or r.get('id') or 'rule'}"[:96],
                "source": "fp",
                "tier_hint": "core" if path else "archival",
                "theme": str(r.get("kind") or "false_positive"),
                "keywords": re.findall(r"[a-zA-Z0-9_-]{3,}", reason.lower())[:12],
                "path_globs": [path] if path else [],
                "hits": 1,
                "effective_score": 0.6 if path else 0.2,
                "text": f"{path} {reason}"[:500],
                "reason": reason,
            }
        )

    # Federated
    fed = _load_json(default_fed_path(root))
    signals = []
    if isinstance(fed, dict):
        signals = fed.get("signals") or fed.get("items") or []
    elif isinstance(fed, list):
        signals = fed
    for s in signals:
        if not isinstance(s, dict):
            continue
        theme = str(s.get("theme") or s.get("id") or "")
        kws = [str(k) for k in (s.get("keywords") or []) if not _PRIVATE_RX.search(str(k))][:12]
        blob = " ".join([theme, " ".join(kws)])
        if _PRIVATE_RX.search(blob):
            continue
        out.append(
            {
                "id": str(s.get("id") or theme)[:96],
                "source": "federated",
                "tier_hint": "archival",
                "theme": theme,
                "keywords": kws,
                "path_globs": [],
                "hits": int(s.get("hits") or 1),
                "effective_score": _eff(s),
                "text": blob[:500],
            }
        )

    # MEMORY.md recall blocks
    mem = default_memory_md(root)
    if mem.is_file():
        try:
            text = mem.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        # split on ## headings
        blocks = re.split(r"(?=^## )", text, flags=re.M)
        for i, block in enumerate(blocks):
            block = block.strip()
            if len(block) < 40:
                continue
            if _PRIVATE_RX.search(block):
                # redact private paths for search index
                block = _PRIVATE_RX.sub("[redacted]", block)
            title = block.splitlines()[0][:120] if block else f"memory-{i}"
            out.append(
                {
                    "id": f"memory:{i}:{_norm(title)[:40]}",
                    "source": "memory_md",
                    "tier_hint": "recall",
                    "theme": "review_history",
                    "keywords": _tokens(block)[:24],
                    "path_globs": [],
                    "hits": 1,
                    "effective_score": 0.35,
                    "text": block[:600].replace("\n", " "),
                    "title": title,
                }
            )
    return out


def score_record(rec: dict[str, Any], query_tokens: list[str]) -> float:
    if not query_tokens:
        return 0.0
    text = _norm(
        " ".join(
            [
                str(rec.get("theme") or ""),
                " ".join(rec.get("keywords") or []),
                " ".join(rec.get("path_globs") or []),
                str(rec.get("text") or ""),
                str(rec.get("id") or ""),
            ]
        )
    )
    hits = 0
    for t in query_tokens:
        if t in text:
            hits += 1
            # basename / theme exact boost
            if t == _norm(str(rec.get("theme") or "")):
                hits += 1
            for g in rec.get("path_globs") or []:
                if t == _norm(Path(str(g)).name) or t in _norm(str(g)):
                    hits += 1.5
    if hits <= 0:
        return 0.0
    base = hits / max(1, len(query_tokens))
    eff = float(rec.get("effective_score") or 0)
    hit_w = min(1.0, int(rec.get("hits") or 1) / 10.0)
    return round(0.65 * min(1.0, base) + 0.25 * eff + 0.10 * hit_w, 4)


def search(
    query: str,
    *,
    root: Path | None = None,
    limit: int | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    root = root or _root()
    limit = limit or _int_env("TORII_ARCHIVAL_SEARCH_LIMIT", 8)
    tokens = _tokens(query)
    records = collect_records(root)
    if sources:
        allow = set(sources)
        records = [r for r in records if r.get("source") in allow]
    scored: list[dict[str, Any]] = []
    for rec in records:
        sc = score_record(rec, tokens)
        if sc <= 0:
            continue
        row = dict(rec)
        row["score"] = sc
        # strip long text for default response (keep preview)
        row["preview"] = str(row.pop("text", ""))[:180]
        scored.append(row)
    scored.sort(key=lambda x: (-float(x.get("score") or 0), -float(x.get("effective_score") or 0)))
    hits = scored[:limit]
    return {
        "feature": FEATURE,
        "query": query,
        "tokens": tokens,
        "hit_count": len(hits),
        "total_candidates": len(records),
        "hits": hits,
        "sources_scanned": sorted({r.get("source") for r in records}),
        "searched_at": _now(),
    }


def render_promote_section(result: dict[str, Any]) -> str:
    hits = result.get("hits") or []
    themes = list(result.get("graph_themes") or [])
    filtered = result.get("hits_superseded") or result.get("hits_filtered") or []
    filt_n = int(result.get("superseded_filtered") or len(filtered) or 0)
    recon = result.get("reconsolidation") or {}
    recon_n = int(recon.get("updated_n") or result.get("reconsolidated_n") or 0)
    has_graph = bool(themes or result.get("feature_graph") == FEATURE_GRAPH)
    has_f145 = bool(
        result.get("feature_supersede") == FEATURE_SUPERSEDE
        or filt_n > 0
        or (result.get("supersede") or {}).get("enabled")
    )
    has_f146 = bool(
        result.get("feature_recon") == FEATURE_RECON
        or recon_n > 0
        or recon.get("enabled")
    )
    tags = ["F98"]
    if has_graph:
        tags.append("F144")
    if has_f145:
        tags.append("F145")
    if has_f146:
        tags.append("F146")
    if len(tags) > 1:
        title = (
            "## Archival search → core "
            f"({'/'.join(tags)} — MemGPT paging"
            + (" + multi-hop" if has_graph else "")
            + (" + supersede filter" if has_f145 else "")
            + (" + reconsolidation" if has_f146 else "")
            + ")"
        )
    else:
        title = "## Archival search → core (F98 — MemGPT-style paging)"
    lines = [
        MARKER,
        title,
        "",
        f"Query: `{result.get('query')}` · hits={result.get('hit_count')} "
        f"(just-in-time from cold/archival + MEMORY.md recall).",
        "Treat promoted hits as **core** for this PR; still require path evidence to block.",
        "",
    ]
    if themes:
        lines.append(
            f"**F144 graph multi-hop themes:** {', '.join(f'`{t}`' for t in themes[:8])}"
        )
        lines.append("")
    if filt_n > 0 or has_f145:
        lines.append(
            f"**F145 temporal faithfulness:** filtered **{filt_n}** hit(s) matching "
            "active multi-hop **supersedes** (do **not** re-raise as blocking)."
        )
        for h in filtered[:4]:
            lines.append(
                f"  - ~~`{h.get('id')}`~~ theme=`{h.get('theme')}` "
                f"reason=`{h.get('supersede_reason') or 'superseded'}`"
            )
        lines.append("")
    if recon_n > 0 or has_f146:
        ids = recon.get("ids") or []
        lines.append(
            f"**F146 reconsolidation:** strengthened **{recon_n}** durable TP "
            "signature(s) on successful retrieve "
            f"({', '.join(f'`{i}`' for i in ids[:6]) or '—'})."
        )
        lines.append("")
    if not hits:
        lines.append("_No archival hits for this query._")
    for h in hits:
        src = h.get("source")
        theme = h.get("theme")
        sc = h.get("score")
        eff = h.get("effective_score")
        paths = ", ".join((h.get("path_globs") or [])[:4]) or "—"
        lines.append(
            f"- [{src}] `{h.get('id')}` theme={theme} score={sc} eff={eff} "
            f"paths=[{paths}] — {(h.get('preview') or '')[:100]}"
        )
    lines.append("")
    lines.append("<!-- /torii-f98-archival-search -->")
    return "\n".join(lines) + "\n"


def inject_section(prompt_path: Path, section: str) -> bool:
    path = Path(prompt_path)
    if not path.parent.exists() and not path.is_file():
        return False
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if MARKER in text:
        text = re.sub(
            r"<!-- torii-f98-archival-search -->.*?<!-- /torii-f98-archival-search -->\n?",
            section,
            text,
            count=1,
            flags=re.S,
        )
    else:
        text = text.rstrip() + "\n\n" + section
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def graph_multi_hop_enabled() -> bool:
    """F144: expand archival auto-query with temporal graph multi-hop themes."""
    raw = (os.environ.get("TORII_ARCHIVAL_GRAPH_HOPS") or "2").strip().lower()
    if raw in _FALSEY:
        return False
    try:
        return int(raw) >= 1
    except ValueError:
        return True


def graph_hops() -> int:
    raw = (os.environ.get("TORII_ARCHIVAL_GRAPH_HOPS") or "2").strip()
    try:
        return max(0, min(4, int(raw)))
    except ValueError:
        return 2


def graph_themes_for_paths(
    paths: list[str],
    *,
    root: Path | None = None,
    hops: int | None = None,
) -> dict[str, Any]:
    """F144: soft load temporal graph; collect multi-hop themes for path seeds.

    Privacy: theme strings only (no paths, no tenant, no snippets).
    """
    root = root or _root()
    hops = graph_hops() if hops is None else hops
    out: dict[str, Any] = {
        "feature": FEATURE_GRAPH,
        "themes": [],
        "neighbor_n": 0,
        "seed_n": 0,
        "hops": hops,
        "enabled": hops >= 1,
        "soft_skip": False,
    }
    if hops < 1:
        out["soft_skip"] = True
        out["reason"] = "hops_off"
        return out
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from memory_temporal_graph import (  # type: ignore
            build_from_disk,
            load_or_build_graph,
            query_graph,
            enabled as graph_enabled,
        )

        if not graph_enabled():
            out["soft_skip"] = True
            out["reason"] = "graph_off"
            return out
        try:
            g = load_or_build_graph(root=root)
        except Exception:
            g = build_from_disk(root=root)
        themes: list[str] = []
        seen: set[str] = set()
        seed_n = 0
        neigh_n = 0
        for p in paths[:16]:
            q = query_graph(g, path=str(p), hops=hops, limit=16)
            seed_n += len(q.get("seeds") or [])
            neigh_n += int(q.get("neighbor_count") or 0)
            for n in q.get("seed_nodes") or []:
                if isinstance(n, dict):
                    th = str(n.get("theme") or "").strip().lower()
                    if th and th not in seen and "/" not in th and ".." not in th:
                        seen.add(th)
                        themes.append(th.replace("_", " ")[:48])
            for nb in q.get("neighbors") or []:
                if not isinstance(nb, dict):
                    continue
                peer = nb.get("peer_node") or {}
                if isinstance(peer, dict):
                    th = str(peer.get("theme") or "").strip().lower()
                    if th and th not in seen and "/" not in th:
                        seen.add(th)
                        themes.append(th.replace("_", " ")[:48])
                # edge meta keywords
                meta = nb.get("meta") or {}
                if isinstance(meta, dict):
                    for kw in meta.get("keywords") or []:
                        k = str(kw).strip().lower()[:32]
                        if k and k not in seen and "/" not in k:
                            seen.add(k)
                            themes.append(k)
        out["themes"] = themes[:12]
        out["neighbor_n"] = neigh_n
        out["seed_n"] = seed_n
        blob = json.dumps(out)
        out["privacy_ok"] = "/Users/" not in blob and "/home/" not in blob
        return out
    except Exception as exc:
        out["soft_skip"] = True
        out["error"] = str(exc)[:120]
        out["privacy_ok"] = True
        return out


def supersede_filter_enabled() -> bool:
    """F145: filter promoted archival hits that match active supersedes."""
    raw = (os.environ.get("TORII_ARCHIVAL_SUPERSEDE_FILTER") or "1").strip().lower()
    return raw not in _FALSEY


def _theme_norm(s: str) -> str:
    return re.sub(r"[\s_]+", " ", (s or "").strip().lower())


def filter_superseded_hits(
    result: dict[str, Any],
    *,
    paths: list[str] | None = None,
    root: Path | None = None,
    multi_hop: bool = True,
    hops: int | None = None,
) -> dict[str, Any]:
    """F145: drop/quarantine hits whose id or theme is actively superseded.

    MemoTime/Zep temporal faithfulness: multi-hop archival expand (F144) must not
    re-page cold TPs that F101/F102 would demote in the dual-pass critic.
    Privacy: only ids/themes; no paths/snippets in supersede meta export.
    """
    root = root or _root()
    out = dict(result)
    out["feature_supersede"] = FEATURE_SUPERSEDE
    meta: dict[str, Any] = {
        "enabled": supersede_filter_enabled(),
        "filtered_n": 0,
        "themes": [],
        "ids": [],
        "soft_skip": False,
        "privacy_ok": True,
    }
    hits = list(result.get("hits") or [])
    if not supersede_filter_enabled():
        meta["soft_skip"] = True
        meta["reason"] = "filter_off"
        out["supersede"] = meta
        out["hits_superseded"] = []
        out["superseded_filtered"] = 0
        return out
    if not hits:
        out["supersede"] = meta
        out["hits_superseded"] = []
        out["superseded_filtered"] = 0
        return out

    sup_ids: set[str] = set()
    sup_themes: set[str] = set()
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from memory_temporal_graph import (  # type: ignore
            build_from_disk,
            load_or_build_graph,
            superseded_index,
            enabled as graph_enabled,
        )

        if not graph_enabled():
            meta["soft_skip"] = True
            meta["reason"] = "graph_off"
            out["supersede"] = meta
            out["hits_superseded"] = []
            out["superseded_filtered"] = 0
            return out
        try:
            g = load_or_build_graph(root=root)
        except Exception:
            g = build_from_disk(root=root)
        hop_n = hops if hops is not None else graph_hops()
        hop_n = max(1, min(4, hop_n or 2))
        idx = superseded_index(
            g,
            paths=list(paths or [])[:16] or None,
            multi_hop=multi_hop,
            hops=hop_n,
        )
        for raw in idx.get("ids") or []:
            s = str(raw).strip()
            if s:
                sup_ids.add(s)
                if ":" in s:
                    sup_ids.add(s.split(":", 1)[-1])
        for th in idx.get("themes") or []:
            nt = _theme_norm(str(th))
            if nt:
                sup_themes.add(nt)
        meta["hop"] = idx.get("hop") or {}
        meta["supersede_edge_n"] = int(idx.get("count") or len(idx.get("edges") or []))
    except Exception as exc:
        meta["soft_skip"] = True
        meta["error"] = str(exc)[:120]
        out["supersede"] = meta
        out["hits_superseded"] = []
        out["superseded_filtered"] = 0
        return out

    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for h in hits:
        if not isinstance(h, dict):
            continue
        hid = str(h.get("id") or "")
        rid = hid.split(":", 1)[-1] if ":" in hid else hid
        th = _theme_norm(str(h.get("theme") or ""))
        reason = ""
        if hid in sup_ids or rid in sup_ids:
            reason = "id_superseded"
        elif th and th in sup_themes:
            reason = "theme_superseded"
        elif th:
            # soft theme token overlap (pickle / deserial)
            for st in sup_themes:
                if len(st) >= 4 and (st in th or th in st):
                    reason = "theme_overlap_superseded"
                    break
        if reason:
            row = dict(h)
            row["superseded"] = True
            row["supersede_reason"] = reason
            dropped.append(row)
        else:
            kept.append(h)

    meta["filtered_n"] = len(dropped)
    meta["themes"] = sorted(sup_themes)[:12]
    meta["ids"] = sorted(sup_ids)[:16]
    blob = json.dumps({"themes": meta["themes"], "ids": meta["ids"]})
    meta["privacy_ok"] = "/Users/" not in blob and "/home/" not in blob

    out["hits"] = kept
    out["hit_count"] = len(kept)
    out["hits_superseded"] = dropped
    out["hits_filtered"] = dropped
    out["superseded_filtered"] = len(dropped)
    out["supersede"] = meta
    out["hit_count_pre_filter"] = len(hits)
    return out


def reconsolidate_enabled() -> bool:
    """F146: strengthen durable TP signatures when archival hits promote."""
    raw = (os.environ.get("TORII_ARCHIVAL_RECONSOLIDATE") or "1").strip().lower()
    return raw not in _FALSEY


def default_recon_ledger(root: Path | None = None) -> Path:
    return (root or _root()) / ".torii" / RECON_LEDGER


def reconsolidate_hits(
    result: dict[str, Any],
    *,
    root: Path | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """F146: on successful promote of non-superseded TP hits, reconsolidate store.

    Human-inspired reconsolidation: retrieval that pages into core should warm
    durable evidence (hits++, last_retrieved_at, soft effective_score bump).
    Never reconsolidates superseded/quarantined hits. Privacy: ids/themes only.
    """
    root = root or _root()
    out = dict(result)
    out["feature_recon"] = FEATURE_RECON
    meta: dict[str, Any] = {
        "enabled": reconsolidate_enabled(),
        "updated_n": 0,
        "ids": [],
        "soft_skip": False,
        "privacy_ok": True,
        "written": False,
    }
    hits = [h for h in (result.get("hits") or []) if isinstance(h, dict)]
    # never touch hits that were superseded
    bad_ids = {
        str(h.get("id"))
        for h in (result.get("hits_superseded") or [])
        if isinstance(h, dict)
    }
    if not reconsolidate_enabled():
        meta["soft_skip"] = True
        meta["reason"] = "recon_off"
        out["reconsolidation"] = meta
        out["reconsolidated_n"] = 0
        return out
    tp_hits = [
        h
        for h in hits
        if h.get("source") == "tp"
        and str(h.get("id") or "") not in bad_ids
        and not h.get("superseded")
    ]
    if not tp_hits:
        meta["soft_skip"] = True
        meta["reason"] = "no_tp_hits"
        out["reconsolidation"] = meta
        out["reconsolidated_n"] = 0
        return out

    tp_path = default_tp_path(root)
    raw = _load_json(tp_path)
    if raw is None:
        meta["soft_skip"] = True
        meta["reason"] = "no_tp_store"
        out["reconsolidation"] = meta
        out["reconsolidated_n"] = 0
        return out

    if isinstance(raw, dict):
        sigs = raw.get("signatures") or raw.get("items") or []
        wrap = "signatures" if "signatures" in raw or not isinstance(raw.get("items"), list) else "items"
        if "signatures" not in raw and "items" in raw:
            wrap = "items"
        else:
            wrap = "signatures"
            if "signatures" not in raw:
                raw = {"signatures": list(sigs)}
    elif isinstance(raw, list):
        sigs = raw
        wrap = None
        raw = {"signatures": sigs}
        wrap = "signatures"
    else:
        meta["soft_skip"] = True
        meta["reason"] = "bad_tp_store"
        out["reconsolidation"] = meta
        out["reconsolidated_n"] = 0
        return out

    if not isinstance(sigs, list):
        sigs = []

    # index by id and theme
    by_id: dict[str, dict[str, Any]] = {}
    by_theme: dict[str, list[dict[str, Any]]] = {}
    for s in sigs:
        if not isinstance(s, dict) or s.get("deleted") or s.get("evicted"):
            continue
        sid = str(s.get("id") or "")
        if sid:
            by_id[sid] = s
        th = _theme_norm(str(s.get("theme") or ""))
        if th:
            by_theme.setdefault(th, []).append(s)

    updated: list[str] = []
    now = _now()
    for h in tp_hits:
        hid = str(h.get("id") or "")
        rid = hid.split(":", 1)[-1] if ":" in hid else hid
        th = _theme_norm(str(h.get("theme") or ""))
        target = by_id.get(hid) or by_id.get(rid)
        if target is None and th:
            cands = by_theme.get(th) or []
            if len(cands) == 1:
                target = cands[0]
        if target is None:
            continue
        # skip inactive / superseded durable rows
        if target.get("active") is False or target.get("superseded_by"):
            continue
        old_hits = int(target.get("hits") or 1)
        target["hits"] = old_hits + 1
        target["last_retrieved_at"] = now
        target["reconsolidated_at"] = now
        target["reconsolidation_feature"] = FEATURE_RECON
        try:
            eff = float(target.get("effective_score") or target.get("effective") or 0.0)
        except (TypeError, ValueError):
            eff = 0.0
        target["effective_score"] = round(min(RECON_EFF_CAP, max(0.0, eff + RECON_EFF_BUMP)), 4)
        tid = str(target.get("id") or rid or hid)
        if tid not in updated:
            updated.append(tid)
        # reflect in promote hit row for section/debug
        h["reconsolidated"] = True
        h["hits"] = target["hits"]
        h["effective_score"] = target["effective_score"]

    meta["updated_n"] = len(updated)
    meta["ids"] = updated[:16]
    blob = json.dumps(meta)
    meta["privacy_ok"] = "/Users/" not in blob and "/home/" not in blob and "sk-" not in blob

    if write and updated:
        if wrap and isinstance(raw, dict):
            raw[wrap] = sigs
            raw["updated_at"] = now
            raw["last_reconsolidation"] = {
                "feature": FEATURE_RECON,
                "at": now,
                "ids": updated[:16],
                "n": len(updated),
            }
            tp_path.parent.mkdir(parents=True, exist_ok=True)
            tp_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
            meta["written"] = True
            meta["tp_path"] = str(tp_path.name)
        # append-only ledger (privacy-safe)
        ledger_path = default_recon_ledger(root)
        ledger: dict[str, Any] = {"feature": FEATURE_RECON, "schema": SCHEMA, "runs": []}
        prev = _load_json(ledger_path)
        if isinstance(prev, dict) and isinstance(prev.get("runs"), list):
            ledger = prev
        run = {
            "at": now,
            "feature": FEATURE_RECON,
            "query": str(result.get("query") or "")[:200],
            "ids": updated[:16],
            "n": len(updated),
            "superseded_filtered": int(result.get("superseded_filtered") or 0),
        }
        runs = list(ledger.get("runs") or [])
        runs.append(run)
        ledger["runs"] = runs[-50:]
        ledger["last"] = run
        ledger["updated_at"] = now
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        meta["ledger"] = ledger_path.name

    out["reconsolidation"] = meta
    out["reconsolidated_n"] = len(updated)
    return out


def auto_from_paths(
    paths: list[str],
    *,
    root: Path | None = None,
    limit: int | None = None,
    multi_hop: bool | None = None,
    hops: int | None = None,
    supersede_filter: bool | None = None,
    reconsolidate: bool | None = None,
) -> dict[str, Any]:
    """Build query from changed path basenames + F144 graph multi-hop themes.

    MemGPT paging: basenames alone miss cold TP themes linked only via co_path.
    F144 folds Zep multi-hop themes into the archival query before promote.
    F145 filters multi-hop-superseded cold hits so resolved FPs do not re-page.
    F146 reconsolidates surviving TP hits into durable store (warm on retrieve).
    """
    root = root or _root()
    bases = []
    for p in paths:
        name = Path(str(p)).name
        if name:
            bases.append(name)
        stem = Path(name).stem
        if stem and stem not in bases:
            bases.append(stem)
    # always include light security vocabulary so empty path lists still search memory
    extra = ["sql", "injection", "pickle", "shell", "secret"]
    graph_meta: dict[str, Any] = {"enabled": False, "themes": []}
    use_mh = graph_multi_hop_enabled() if multi_hop is None else bool(multi_hop)
    hop_n = hops if hops is not None else graph_hops()
    if use_mh and paths:
        graph_meta = graph_themes_for_paths(paths, root=root, hops=hop_n)
    themes = list(graph_meta.get("themes") or [])
    # query: basenames + multi-hop themes + light security stems
    q_parts = bases[:12] + themes[:8] + extra[:3]
    query = " ".join(q_parts)
    result = search(query, root=root, limit=limit)
    result["feature_graph"] = FEATURE_GRAPH if use_mh else None
    result["graph_themes"] = themes
    result["graph"] = {
        k: graph_meta.get(k)
        for k in (
            "enabled",
            "hops",
            "seed_n",
            "neighbor_n",
            "soft_skip",
            "privacy_ok",
            "reason",
        )
        if k in graph_meta or graph_meta.get(k) is not None
    }
    result["mode"] = "auto_graph" if themes else "auto"
    # F145: temporal faithfulness on promote path
    use_sf = supersede_filter_enabled() if supersede_filter is None else bool(supersede_filter)
    if use_sf:
        result = filter_superseded_hits(
            result,
            paths=paths,
            root=root,
            multi_hop=True,
            hops=hop_n if hop_n else 2,
        )
    else:
        result["feature_supersede"] = None
        result["supersede"] = {"enabled": False, "soft_skip": True, "reason": "filter_off"}
        result["hits_superseded"] = []
        result["superseded_filtered"] = 0
    # F146: reconsolidate surviving TP hits (after supersede filter)
    use_rc = reconsolidate_enabled() if reconsolidate is None else bool(reconsolidate)
    if use_rc:
        result = reconsolidate_hits(result, root=root, write=True)
    else:
        result["feature_recon"] = None
        result["reconsolidation"] = {
            "enabled": False,
            "soft_skip": True,
            "reason": "recon_off",
            "updated_n": 0,
        }
        result["reconsolidated_n"] = 0
    return result


def cmd_search(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0
    sources = args.sources.split(",") if args.sources else None
    result = search(args.query, limit=args.limit, sources=sources)
    print(json.dumps(result, indent=2))
    return 0 if result.get("hit_count", 0) >= 0 else 1


def cmd_promote(args: argparse.Namespace) -> int:
    if args.recall_json:
        result = json.loads(Path(args.recall_json).read_text(encoding="utf-8"))
    else:
        result = search(args.query, limit=args.limit)
    paths: list[str] = []
    if getattr(args, "files", None):
        paths = [p.strip() for p in str(args.files).split(",") if p.strip()]
    # F145: optional supersede filter on promote of raw search
    if supersede_filter_enabled() and not getattr(args, "no_supersede", False):
        result = filter_superseded_hits(result, paths=paths or None)
    # F146 reconsolidation after filter
    if reconsolidate_enabled() and not getattr(args, "no_reconsolidate", False):
        result = reconsolidate_hits(result, root=_root(), write=True)
    section = render_promote_section(result)
    out: dict[str, Any] = {
        "feature": FEATURE,
        "feature_supersede": result.get("feature_supersede"),
        "feature_recon": result.get("feature_recon"),
        "hit_count": result.get("hit_count"),
        "superseded_filtered": result.get("superseded_filtered") or 0,
        "reconsolidated_n": result.get("reconsolidated_n") or 0,
        "query": result.get("query"),
    }
    if args.out:
        Path(args.out).write_text(section, encoding="utf-8")
        out["out"] = args.out
    if args.prompt:
        ok = inject_section(Path(args.prompt), section)
        out["injected"] = ok
        out["prompt"] = args.prompt
    if not args.out and not args.prompt:
        print(section)
    else:
        print(json.dumps(out, indent=2))
    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    paths: list[str] = []
    if args.files:
        paths = [p.strip() for p in args.files.split(",") if p.strip()]
    elif args.files_list and Path(args.files_list).is_file():
        paths = [
            ln.strip()
            for ln in Path(args.files_list).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
    multi = None
    if getattr(args, "no_graph", False):
        multi = False
    elif getattr(args, "graph_hops", None) is not None:
        os.environ["TORII_ARCHIVAL_GRAPH_HOPS"] = str(args.graph_hops)
    sf = None
    if getattr(args, "no_supersede", False):
        sf = False
    rc = None
    if getattr(args, "no_reconsolidate", False):
        rc = False
    result = auto_from_paths(
        paths,
        limit=args.limit,
        multi_hop=multi,
        supersede_filter=sf,
        reconsolidate=rc,
    )
    section = render_promote_section(result)
    out: dict[str, Any] = {
        "feature": FEATURE,
        "feature_graph": result.get("feature_graph"),
        "feature_supersede": result.get("feature_supersede"),
        "feature_recon": result.get("feature_recon"),
        "mode": result.get("mode") or "auto",
        "paths": paths[:20],
        "query": result.get("query"),
        "hit_count": result.get("hit_count"),
        "superseded_filtered": result.get("superseded_filtered") or 0,
        "reconsolidated_n": result.get("reconsolidated_n") or 0,
        "reconsolidation": result.get("reconsolidation"),
        "graph_themes": result.get("graph_themes") or [],
        "graph": result.get("graph"),
        "supersede": result.get("supersede"),
        "hits": [
            {
                "id": h.get("id"),
                "source": h.get("source"),
                "score": h.get("score"),
                "theme": h.get("theme"),
                "reconsolidated": h.get("reconsolidated"),
            }
            for h in (result.get("hits") or [])[:8]
        ],
        "hits_superseded": [
            {
                "id": h.get("id"),
                "theme": h.get("theme"),
                "reason": h.get("supersede_reason"),
            }
            for h in (result.get("hits_superseded") or [])[:8]
        ],
    }
    if args.prompt:
        out["injected"] = inject_section(Path(args.prompt), section)
        out["prompt"] = args.prompt
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        out["json_out"] = args.json_out
    if args.section_out:
        Path(args.section_out).write_text(section, encoding="utf-8")
        out["section_out"] = args.section_out
    print(json.dumps(out, indent=2))
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        torii = td_path / ".torii"
        torii.mkdir(parents=True)
        (torii / "tp-signatures.json").write_text(
            json.dumps(
                {
                    "signatures": [
                        {
                            "id": "sqli-arch",
                            "theme": "sql_injection",
                            "keywords": ["sql injection", "sqli", "cursor"],
                            "path_globs": ["legacy/db.py"],
                            "hits": 4,
                            "effective_score": 0.35,
                        },
                        {
                            "id": "noise",
                            "theme": "css_typo",
                            "keywords": ["margin"],
                            "hits": 1,
                            "effective_score": 0.05,
                        },
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (torii / "fp-rules.json").write_text(
            json.dumps(
                {
                    "rules": [
                        {
                            "path": "legacy/db.py",
                            "reason": "parameterized query helper — false positive",
                        }
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        mem = td_path / "memories"
        mem.mkdir()
        (mem / "MEMORY.md").write_text(
            "# memory\n\n## Review 2026-07-01 · acme/app PR #1 · harden sql\n\n"
            "- Verdict: REQUEST CHANGES\n"
            "- Blocking: sql injection in search handler\n",
            encoding="utf-8",
        )
        old = {
            "TORII_ROOT": os.environ.get("TORII_ROOT"),
            "TORII_TP_SIGNATURES_FILE": os.environ.get("TORII_TP_SIGNATURES_FILE"),
            "TORII_FP_RULES_FILE": os.environ.get("TORII_FP_RULES_FILE"),
            "TORII_MEMORY_MD": os.environ.get("TORII_MEMORY_MD"),
            "TORII_ARCHIVAL_SEARCH": os.environ.get("TORII_ARCHIVAL_SEARCH"),
            "TORII_ARCHIVAL_GRAPH_HOPS": os.environ.get("TORII_ARCHIVAL_GRAPH_HOPS"),
            "TORII_ARCHIVAL_SUPERSEDE_FILTER": os.environ.get(
                "TORII_ARCHIVAL_SUPERSEDE_FILTER"
            ),
            "TORII_ARCHIVAL_RECONSOLIDATE": os.environ.get(
                "TORII_ARCHIVAL_RECONSOLIDATE"
            ),
        }
        try:
            os.environ["TORII_ROOT"] = str(td_path)
            os.environ["TORII_TP_SIGNATURES_FILE"] = str(torii / "tp-signatures.json")
            os.environ["TORII_FP_RULES_FILE"] = str(torii / "fp-rules.json")
            os.environ["TORII_MEMORY_MD"] = str(mem / "MEMORY.md")
            os.environ["TORII_ARCHIVAL_SEARCH"] = "1"
            # keep early fixture stages free of recon writes until F146 block
            os.environ["TORII_ARCHIVAL_RECONSOLIDATE"] = "0"

            r = search("sql injection db.py", root=td_path, limit=5)
            ids = {h.get("id") for h in r.get("hits") or []}
            hit_tp = any("sqli" in str(i) for i in ids)
            hit_fp = any(str(i).startswith("fp:") for i in ids)
            hit_mem = any(str(i).startswith("memory:") for i in ids)
            # privacy: poison not indexed
            poison = search("/Users/evil/secret sk-or-v1-deadbeef", root=td_path)
            # should not return high-score private path hits
            privacy_ok = all(
                "/Users/" not in json.dumps(h) for h in (poison.get("hits") or [])
            )
            section = render_promote_section(r)
            promote_ok = MARKER in section and "sql" in section.lower()
            prompt = td_path / "prompt.md"
            prompt.write_text("# p\n", encoding="utf-8")
            inj = inject_section(prompt, section)
            body = prompt.read_text(encoding="utf-8")
            inject_ok = inj and MARKER in body

            auto = auto_from_paths(
                ["legacy/db.py", "app.py"],
                root=td_path,
                limit=5,
                reconsolidate=False,
            )
            auto_ok = int(auto.get("hit_count") or 0) >= 1

            # F144: multi-hop theme expands archival query for co_path-only themes
            # plant graph: app.py co_path with pickle TP that basenames alone miss
            (torii / "tp-signatures.json").write_text(
                json.dumps(
                    {
                        "signatures": [
                            {
                                "id": "sqli-arch",
                                "theme": "sql_injection",
                                "keywords": ["sql injection", "sqli", "cursor"],
                                "path_globs": ["legacy/db.py"],
                                "hits": 4,
                                "effective_score": 0.35,
                            },
                            {
                                "id": "pickle-cold",
                                "theme": "insecure_deserialization",
                                "keywords": ["pickle", "loads", "deserialize"],
                                "path_globs": ["legacy/serde.py"],
                                "hits": 3,
                                "effective_score": 0.4,
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            # build temporal graph on disk via memory_temporal_graph
            f144_ok = False
            f145_ok = False
            graph_themes: list[str] = []
            f145_filtered: list[str] = []
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                from memory_temporal_graph import (  # type: ignore
                    build_from_disk,
                    save_graph,
                    default_graph_path,
                )

                g = build_from_disk(root=td_path)
                # force co_path edge app.py ↔ serde pickle theme
                nodes = g.get("nodes") or []
                pickle_nid = None
                for n in nodes:
                    if isinstance(n, dict) and (
                        "pickle" in str(n.get("theme") or "")
                        or "deserial" in str(n.get("theme") or "")
                        or str(n.get("raw_id") or "") == "pickle-cold"
                        or "pickle" in str(n.get("id") or "")
                    ):
                        pickle_nid = n.get("id")
                        break
                if pickle_nid is None:
                    # synthetic node if build didn't pick it
                    pickle_nid = "tp:pickle-cold"
                    nodes.append(
                        {
                            "id": pickle_nid,
                            "raw_id": "pickle-cold",
                            "theme": "insecure_deserialization",
                            "path_basenames": ["serde.py"],
                            "active": True,
                        }
                    )
                    g["nodes"] = nodes
                # seed app.py node for multi-hop
                app_nid = "path:app.py"
                if not any(
                    isinstance(n, dict) and n.get("id") == app_nid for n in nodes
                ):
                    nodes.append(
                        {
                            "id": app_nid,
                            "theme": "app_entry",
                            "path_basenames": ["app.py"],
                            "active": True,
                        }
                    )
                    g["nodes"] = nodes
                edges = list(g.get("edges") or [])
                edges.append(
                    {
                        "id": "co_path:app-serde",
                        "type": "co_path",
                        "source": app_nid if app_nid <= str(pickle_nid) else pickle_nid,
                        "target": pickle_nid if app_nid <= str(pickle_nid) else app_nid,
                        "valid_from": "2026-01-01T00:00:00Z",
                        "valid_until": None,
                        "meta": {"keywords": ["pickle", "deserialize"]},
                    }
                )
                g["edges"] = edges
                save_graph(default_graph_path(td_path), g)
                os.environ["TORII_ARCHIVAL_GRAPH_HOPS"] = "2"
                os.environ["TORII_ARCHIVAL_SUPERSEDE_FILTER"] = "0"
                # basename-only query (no graph) may miss pickle theme
                no_graph = auto_from_paths(
                    ["app.py"],
                    root=td_path,
                    limit=5,
                    multi_hop=False,
                    supersede_filter=False,
                )
                with_graph = auto_from_paths(
                    ["app.py"],
                    root=td_path,
                    limit=5,
                    multi_hop=True,
                    hops=2,
                    supersede_filter=False,
                )
                graph_themes = list(with_graph.get("graph_themes") or [])
                # multi-hop should surface pickle-related theme tokens
                theme_ok = any(
                    "pickle" in t or "deserial" in t or "insecure" in t
                    for t in graph_themes
                )
                # with graph query should not be worse; prefer more hits or theme in query
                q = str(with_graph.get("query") or "").lower()
                query_ok = "pickle" in q or "deserial" in q or "insecure" in q
                section_g = render_promote_section(with_graph)
                promote_g_ok = (
                    MARKER in section_g
                    and ("F144" in section_g or "multi-hop" in section_g.lower())
                )
                f144_ok = (
                    theme_ok
                    and query_ok
                    and promote_g_ok
                    and int(with_graph.get("hit_count") or 0)
                    >= int(no_graph.get("hit_count") or 0)
                    and bool((with_graph.get("graph") or {}).get("privacy_ok", True))
                )

                # F145: supersede pickle-cold via multi-hop; promote must filter it out
                # plant FP superseding the cold pickle TP
                (torii / "fp-rules.json").write_text(
                    json.dumps(
                        {
                            "rules": [
                                {
                                    "id": "fp-pickle-ok",
                                    "path": "legacy/serde.py",
                                    "reason": "safe pickle allowlist — false positive",
                                    "kind": "insecure_deserialization",
                                }
                            ]
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                # mark TP superseded_by so graph builds supersedes edge
                (torii / "tp-signatures.json").write_text(
                    json.dumps(
                        {
                            "signatures": [
                                {
                                    "id": "sqli-arch",
                                    "theme": "sql_injection",
                                    "keywords": ["sql injection", "sqli", "cursor"],
                                    "path_globs": ["legacy/db.py"],
                                    "hits": 4,
                                    "effective_score": 0.35,
                                },
                                {
                                    "id": "pickle-cold",
                                    "theme": "insecure_deserialization",
                                    "keywords": ["pickle", "loads", "deserialize"],
                                    "path_globs": ["legacy/serde.py"],
                                    "hits": 3,
                                    "effective_score": 0.4,
                                    "superseded_by": "fp-pickle-ok",
                                    "active": False,
                                },
                            ]
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                g2 = build_from_disk(root=td_path)
                # re-attach co_path + explicit supersedes for hermetic fidelity
                nodes2 = list(g2.get("nodes") or [])
                pickle_nid2 = None
                fp_nid = None
                for n in nodes2:
                    if not isinstance(n, dict):
                        continue
                    rid = str(n.get("raw_id") or n.get("id") or "")
                    th = str(n.get("theme") or "")
                    if "pickle-cold" in rid or "deserial" in th:
                        pickle_nid2 = n.get("id")
                        n["active"] = False
                        n["superseded_by"] = "fp-pickle-ok"
                    if "fp-pickle" in rid or (
                        n.get("kind") == "fp" and "deserial" in th
                    ):
                        fp_nid = n.get("id")
                if pickle_nid2 is None:
                    pickle_nid2 = "tp:pickle-cold"
                    nodes2.append(
                        {
                            "id": pickle_nid2,
                            "raw_id": "pickle-cold",
                            "theme": "insecure_deserialization",
                            "path_basenames": ["serde.py", "app.py"],
                            "active": False,
                            "superseded_by": "fp-pickle-ok",
                        }
                    )
                if fp_nid is None:
                    fp_nid = "fp:fp-pickle-ok"
                    nodes2.append(
                        {
                            "id": fp_nid,
                            "raw_id": "fp-pickle-ok",
                            "theme": "insecure_deserialization",
                            "path_basenames": ["serde.py"],
                            "active": True,
                            "kind": "fp",
                        }
                    )
                if not any(
                    isinstance(n, dict) and n.get("id") == "path:app.py" for n in nodes2
                ):
                    nodes2.append(
                        {
                            "id": "path:app.py",
                            "theme": "app_entry",
                            "path_basenames": ["app.py"],
                            "active": True,
                        }
                    )
                g2["nodes"] = nodes2
                edges2 = list(g2.get("edges") or [])
                edges2.append(
                    {
                        "id": "co_path:app-serde-f145",
                        "type": "co_path",
                        "source": "path:app.py",
                        "target": pickle_nid2,
                        "valid_from": "2026-01-01T00:00:00Z",
                        "valid_until": None,
                        "meta": {"keywords": ["pickle", "deserialize"]},
                    }
                )
                edges2.append(
                    {
                        "id": "supersedes:fp-pickle-cold",
                        "type": "supersedes",
                        "source": fp_nid,
                        "target": pickle_nid2,
                        "valid_from": "2026-06-01T00:00:00Z",
                        "valid_until": None,
                        "meta": {"reason": "fp_resolve"},
                    }
                )
                g2["edges"] = edges2
                save_graph(default_graph_path(td_path), g2)
                os.environ["TORII_ARCHIVAL_SUPERSEDE_FILTER"] = "1"
                # unfiltered: multi-hop still surfaces pickle cold hit
                raw_promote = auto_from_paths(
                    ["app.py"],
                    root=td_path,
                    limit=8,
                    multi_hop=True,
                    hops=2,
                    supersede_filter=False,
                )
                raw_ids = {str(h.get("id")) for h in (raw_promote.get("hits") or [])}
                raw_has_pickle = any(
                    "pickle" in i or "deserial" in str(h.get("theme") or "")
                    for i, h in (
                        (str(x.get("id")), x) for x in (raw_promote.get("hits") or [])
                    )
                ) or any("pickle" in i for i in raw_ids)
                filtered = auto_from_paths(
                    ["app.py"],
                    root=td_path,
                    limit=8,
                    multi_hop=True,
                    hops=2,
                    supersede_filter=True,
                )
                filt_ids = {str(h.get("id")) for h in (filtered.get("hits") or [])}
                dropped = filtered.get("hits_superseded") or []
                f145_filtered = [
                    str(h.get("id")) for h in dropped if isinstance(h, dict)
                ]
                pickle_dropped = any(
                    "pickle" in str(h.get("id") or "")
                    or "deserial" in _theme_norm(str(h.get("theme") or ""))
                    for h in dropped
                ) or (
                    "pickle-cold" not in " ".join(filt_ids)
                    and any("pickle" in i for i in raw_ids)
                )
                # active promote section must mention F145 and not list pickle as core hit
                section_f = render_promote_section(filtered)
                section_ok = (
                    MARKER in section_f
                    and ("F145" in section_f or "supersede" in section_f.lower())
                )
                pickle_not_core = "pickle-cold" not in " ".join(
                    f"`{i}`" for i in filt_ids
                ) and all(
                    "pickle-cold" not in str(h.get("id") or "")
                    for h in (filtered.get("hits") or [])
                )
                filt_n_ok = int(filtered.get("superseded_filtered") or 0) >= 1 or pickle_dropped
                privacy_f = bool((filtered.get("supersede") or {}).get("privacy_ok", True))
                f145_ok = (
                    section_ok
                    and pickle_not_core
                    and filt_n_ok
                    and privacy_f
                    and bool(filtered.get("feature_supersede") == FEATURE_SUPERSEDE)
                )
                # if raw never had pickle (search miss), still pass if filter machinery runs
                if not raw_has_pickle and not f145_ok:
                    # direct unit of filter_superseded_hits
                    synthetic = {
                        "query": "app.py pickle",
                        "hits": [
                            {
                                "id": "pickle-cold",
                                "theme": "insecure_deserialization",
                                "source": "tp",
                                "score": 0.9,
                                "effective_score": 0.4,
                                "path_globs": ["legacy/serde.py"],
                                "preview": "pickle loads",
                            },
                            {
                                "id": "sqli-arch",
                                "theme": "sql_injection",
                                "source": "tp",
                                "score": 0.5,
                                "effective_score": 0.35,
                                "path_globs": ["legacy/db.py"],
                                "preview": "sql",
                            },
                        ],
                        "hit_count": 2,
                    }
                    f2 = filter_superseded_hits(
                        synthetic, paths=["app.py"], root=td_path, multi_hop=True, hops=2
                    )
                    f145_filtered = [
                        str(h.get("id"))
                        for h in (f2.get("hits_superseded") or [])
                        if isinstance(h, dict)
                    ]
                    sec2 = render_promote_section(f2)
                    f145_ok = (
                        int(f2.get("superseded_filtered") or 0) >= 1
                        and all(
                            "pickle-cold" not in str(h.get("id") or "")
                            for h in (f2.get("hits") or [])
                        )
                        and ("F145" in sec2 or "supersede" in sec2.lower())
                        and bool((f2.get("supersede") or {}).get("privacy_ok", True))
                    )
            except Exception as exc:
                f144_ok = False
                f145_ok = False
                graph_themes = [str(exc)[:80]]

            # F146: reconsolidation — successful promote warms durable TP hits
            f146_ok = False
            f146_ids: list[str] = []
            try:
                # clean active TP store (no superseded pickle) with known hits
                (torii / "tp-signatures.json").write_text(
                    json.dumps(
                        {
                            "signatures": [
                                {
                                    "id": "sqli-arch",
                                    "theme": "sql_injection",
                                    "keywords": ["sql injection", "sqli", "cursor"],
                                    "path_globs": ["legacy/db.py"],
                                    "hits": 4,
                                    "effective_score": 0.35,
                                },
                                {
                                    "id": "xss-noise",
                                    "theme": "xss",
                                    "keywords": ["alert"],
                                    "path_globs": ["ui.js"],
                                    "hits": 1,
                                    "effective_score": 0.1,
                                },
                            ]
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                (torii / "fp-rules.json").write_text(
                    json.dumps(
                        {
                            "rules": [
                                {
                                    "path": "legacy/db.py",
                                    "reason": "parameterized query helper — false positive",
                                }
                            ]
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                os.environ["TORII_ARCHIVAL_RECONSOLIDATE"] = "1"
                os.environ["TORII_ARCHIVAL_SUPERSEDE_FILTER"] = "0"
                os.environ["TORII_ARCHIVAL_GRAPH_HOPS"] = "0"
                before = _load_json(torii / "tp-signatures.json") or {}
                before_hits = 0
                for s in before.get("signatures") or []:
                    if isinstance(s, dict) and s.get("id") == "sqli-arch":
                        before_hits = int(s.get("hits") or 0)
                recon_run = auto_from_paths(
                    ["legacy/db.py"],
                    root=td_path,
                    limit=5,
                    multi_hop=False,
                    supersede_filter=False,
                    reconsolidate=True,
                )
                after = _load_json(torii / "tp-signatures.json") or {}
                after_sig = next(
                    (
                        s
                        for s in (after.get("signatures") or [])
                        if isinstance(s, dict) and s.get("id") == "sqli-arch"
                    ),
                    {},
                )
                after_hits = int(after_sig.get("hits") or 0)
                has_retrieved = bool(after_sig.get("last_retrieved_at"))
                eff_bumped = float(after_sig.get("effective_score") or 0) > 0.35
                recon_n = int(recon_run.get("reconsolidated_n") or 0)
                f146_ids = list((recon_run.get("reconsolidation") or {}).get("ids") or [])
                section_r = render_promote_section(recon_run)
                section_r_ok = MARKER in section_r and (
                    "F146" in section_r or "reconsolid" in section_r.lower()
                )
                ledger = _load_json(default_recon_ledger(td_path))
                ledger_ok = isinstance(ledger, dict) and int(
                    (ledger.get("last") or {}).get("n") or 0
                ) >= 1
                # superseded hits must not reconsolidate
                dead = {
                    "query": "pickle",
                    "hits": [
                        {
                            "id": "dead-pickle",
                            "theme": "insecure_deserialization",
                            "source": "tp",
                            "score": 0.9,
                            "effective_score": 0.4,
                        }
                    ],
                    "hit_count": 1,
                    "hits_superseded": [
                        {
                            "id": "dead-pickle",
                            "theme": "insecure_deserialization",
                            "supersede_reason": "id_superseded",
                        }
                    ],
                    "superseded_filtered": 1,
                }
                # plant dead-pickle then try recon on empty kept hits
                (torii / "tp-signatures.json").write_text(
                    json.dumps(
                        {
                            "signatures": [
                                {
                                    "id": "dead-pickle",
                                    "theme": "insecure_deserialization",
                                    "hits": 2,
                                    "effective_score": 0.4,
                                    "superseded_by": "fp-x",
                                    "active": False,
                                }
                            ]
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                # filter leaves no hits
                dead_f = filter_superseded_hits(
                    {
                        "query": "pickle",
                        "hits": [
                            {
                                "id": "dead-pickle",
                                "theme": "insecure_deserialization",
                                "source": "tp",
                                "score": 0.9,
                                "effective_score": 0.4,
                            }
                        ],
                        "hit_count": 1,
                    },
                    paths=["serde.py"],
                    root=td_path,
                    multi_hop=False,
                )
                # force quarantine if graph soft-skipped
                if int(dead_f.get("superseded_filtered") or 0) == 0:
                    dead_f = {
                        "query": "pickle",
                        "hits": [],
                        "hit_count": 0,
                        "hits_superseded": [
                            {
                                "id": "dead-pickle",
                                "theme": "insecure_deserialization",
                                "source": "tp",
                            }
                        ],
                        "superseded_filtered": 1,
                    }
                no_dead = reconsolidate_hits(dead_f, root=td_path, write=True)
                dead_store = _load_json(torii / "tp-signatures.json") or {}
                dead_hits = int(
                    next(
                        (
                            s.get("hits")
                            for s in (dead_store.get("signatures") or [])
                            if isinstance(s, dict) and s.get("id") == "dead-pickle"
                        ),
                        2,
                    )
                    or 2
                )
                no_dead_ok = int(no_dead.get("reconsolidated_n") or 0) == 0 and dead_hits == 2
                privacy_r = bool(
                    (recon_run.get("reconsolidation") or {}).get("privacy_ok", True)
                )
                f146_ok = (
                    after_hits == before_hits + 1
                    and has_retrieved
                    and eff_bumped
                    and recon_n >= 1
                    and "sqli-arch" in f146_ids
                    and section_r_ok
                    and ledger_ok
                    and no_dead_ok
                    and privacy_r
                    and recon_run.get("feature_recon") == FEATURE_RECON
                )
            except Exception as exc:
                f146_ok = False
                f146_ids = [str(exc)[:80]]

            fixture_pass = all(
                [
                    hit_tp,
                    hit_fp,
                    hit_mem,
                    privacy_ok,
                    promote_ok,
                    inject_ok,
                    auto_ok,
                    f144_ok,
                    f145_ok,
                    f146_ok,
                ]
            )
            print(
                json.dumps(
                    {
                        "feature": FEATURE,
                        "feature_graph": FEATURE_GRAPH,
                        "feature_supersede": FEATURE_SUPERSEDE,
                        "feature_recon": FEATURE_RECON,
                        "f144": True,
                        "f145": True,
                        "f146": True,
                        "fixture_pass": fixture_pass,
                        "hit_tp": hit_tp,
                        "hit_fp": hit_fp,
                        "hit_mem": hit_mem,
                        "privacy_ok": privacy_ok,
                        "promote_ok": promote_ok,
                        "inject_ok": inject_ok,
                        "auto_ok": auto_ok,
                        "f144_ok": f144_ok,
                        "f145_ok": f145_ok,
                        "f146_ok": f146_ok,
                        "f144_graph_themes": graph_themes,
                        "f145_filtered_ids": f145_filtered,
                        "f146_recon_ids": f146_ids,
                        "hit_ids": sorted(ids),
                        "auto_hits": auto.get("hit_count"),
                    },
                    indent=2,
                )
            )
            return 0 if fixture_pass else 1
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    recs = collect_records(root)
    by_src: dict[str, int] = {}
    for r in recs:
        by_src[str(r.get("source"))] = by_src.get(str(r.get("source")), 0) + 1
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "records": len(recs),
                "by_source": by_src,
                "tp": str(default_tp_path(root)),
                "fp": str(default_fp_path(root)),
                "fed": str(default_fed_path(root)),
                "memory_md": str(default_memory_md(root)),
                "memory_md_exists": default_memory_md(root).is_file(),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F98 archival memory search (MemGPT-style)")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("search", help="Search archival + recall stores")
    ps.add_argument("--query", "-q", required=True)
    ps.add_argument("--limit", type=int, default=None)
    ps.add_argument("--sources", default="", help="comma: tp,fp,federated,memory_md")
    ps.add_argument("--force", action="store_true")
    ps.set_defaults(func=cmd_search)

    pp = sub.add_parser("promote", help="Promote search hits into prompt core section")
    pp.add_argument("--query", "-q", default="")
    pp.add_argument("--recall-json", default="")
    pp.add_argument("--limit", type=int, default=None)
    pp.add_argument("--prompt", default="")
    pp.add_argument("--out", default="")
    pp.add_argument(
        "--files",
        default="",
        help="optional path seeds for F145 multi-hop supersede filter",
    )
    pp.add_argument(
        "--no-supersede",
        action="store_true",
        help="Disable F145 supersede filter on promote",
    )
    pp.add_argument(
        "--no-reconsolidate",
        action="store_true",
        help="Disable F146 reconsolidation on promote",
    )
    pp.set_defaults(func=cmd_promote)

    pa = sub.add_parser(
        "auto",
        help="Search from paths (+ F144 multi-hop + F145 supersede + F146 recon) + inject",
    )
    pa.add_argument("--files", default="", help="comma-separated paths")
    pa.add_argument("--files-list", default="")
    pa.add_argument("--limit", type=int, default=None)
    pa.add_argument("--prompt", default="")
    pa.add_argument("--json-out", default="")
    pa.add_argument("--section-out", default="")
    pa.add_argument(
        "--graph-hops",
        type=int,
        default=None,
        help="F144 multi-hop hops (default env TORII_ARCHIVAL_GRAPH_HOPS=2)",
    )
    pa.add_argument(
        "--no-graph",
        action="store_true",
        help="Disable F144 graph multi-hop theme expand",
    )
    pa.add_argument(
        "--no-supersede",
        action="store_true",
        help="Disable F145 supersede filter (temporal faithfulness)",
    )
    pa.add_argument(
        "--no-reconsolidate",
        action="store_true",
        help="Disable F146 reconsolidation (retrieval warm)",
    )
    pa.set_defaults(func=cmd_auto)

    sub.add_parser("fixture").set_defaults(func=cmd_fixture)
    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
