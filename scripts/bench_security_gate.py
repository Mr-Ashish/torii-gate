#!/usr/bin/env python3
"""F70: Labeled vuln e2e bench + dual-pass critic + TP signature compound memory.

Research drivers (2026):
  - QASecClaw: multi-agent SAST+LLM validation → large FP reduction
  - VulAgent: hypothesis-validation decouples discovery from confirmation
  - Self-evolving agents survey: inter-test-time memory evolution

Product thesis: each scored run compounds detection quality via TP signatures
(dual of F62/F64 FP rules) and measured precision/recall on labeled cases.

Commands:
  score     — score a review.md against a cases.json ground-truth pack
  critic    — dual-pass offline critic (path evidence + FP demote + TP boost)
  promote   — merge confirmed TPs into durable tp-signatures.json
  inject    — render trusted TP-signatures prompt section
  fixture   — offline e2e: good+weak fixtures vs insecure-demo cases
  live      — optional bounded real agent review of demo/insecure (needs API key)

Env:
  TORII_ROOT
  TORII_TP_SIGNATURES_FILE   override path for tp-signatures.json
  OPENROUTER_API_KEY         required only for `live`
  TORII_BENCH_MODEL          live model (default openai/gpt-4.1-mini)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F70"
TP_SCHEMA = 1
TP_FILENAME = "tp-signatures.json"
DEFAULT_CASES = "docs/benchmarks/cases/insecure-demo.json"
DEFAULT_GOOD = "docs/benchmarks/fixtures/insecure-demo-good-review.md"
DEFAULT_WEAK = "docs/benchmarks/fixtures/insecure-demo-weak-review.md"

# Path evidence: `path`, path:line, or markdown path tokens
_PATH_RX = re.compile(
    r"(?:"
    r"`([^`\n]+?\.(?:py|js|ts|tsx|go|java|rb|php|rs|c|cpp|h|jsx|vue|sql))(?::(\d{1,7}))?`"
    r"|"
    r"\b([\w./-]+?\.(?:py|js|ts|tsx|go|java|rb|php|rs|c|cpp|h|jsx|vue|sql))(?::(\d{1,7}))?\b"
    r")"
)
_VERDICT_RX = re.compile(
    r"\*\*Verdict:\*\*\s*(APPROVE|REQUEST\s*CHANGES|COMMENT|LGTM|CHANGES\s*REQUESTED)\b",
    re.I,
)
_FINDING_SPLIT = re.compile(r"(?m)^(?:\d+\.|[-*]|###)\s+")


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def normalize_verdict(raw: str) -> str:
    v = re.sub(r"\s+", " ", (raw or "").strip().upper())
    if v in ("REQUEST CHANGES", "REQUEST_CHANGES", "REQUEST-CHANGES", "CHANGES REQUESTED"):
        return "REQUEST_CHANGES"
    if v in ("LGTM",):
        return "APPROVE"
    if v in ("APPROVE", "COMMENT"):
        return v
    return "UNKNOWN"


def parse_verdict(text: str) -> str:
    m = _VERDICT_RX.search(text or "")
    if not m:
        return "UNKNOWN"
    return normalize_verdict(m.group(1))


def extract_path_hits(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in _PATH_RX.finditer(text or ""):
        path = (m.group(1) or m.group(3) or "").strip().strip("`")
        line_s = m.group(2) or m.group(4)
        if not path:
            continue
        key = f"{path}:{line_s or ''}"
        if key in seen:
            continue
        seen.add(key)
        line: int | None = None
        if line_s:
            try:
                line = int(line_s)
            except ValueError:
                line = None
        hits.append({"path": path, "line": line})
    return hits


def extract_finding_chunks(text: str) -> list[str]:
    """Split review into coarse finding-ish chunks for critic pass."""
    body = text or ""
    # Prefer Blocking + Security audit + Key findings regions
    regions: list[str] = []
    for hdr in (
        r"###\s+Blocking\b",
        r"###\s+Security audit\b",
        r"###\s+Key findings\b",
    ):
        m = re.search(hdr, body, re.I)
        if not m:
            continue
        start = m.end()
        nxt = re.search(r"(?m)^###\s+", body[start:])
        end = start + nxt.start() if nxt else len(body)
        regions.append(body[start:end])
    blob = "\n".join(regions) if regions else body
    parts = _FINDING_SPLIT.split(blob)
    chunks = [p.strip() for p in parts if p and len(p.strip()) > 24]
    return chunks[:40]


@dataclass
class CaseResult:
    case_id: str
    hit: bool
    matched_terms: list[str] = field(default_factory=list)
    path_ok: bool = False


@dataclass
class ScoreReport:
    feature: str = FEATURE
    pack_id: str = ""
    verdict: str = "UNKNOWN"
    expected_verdict: str = ""
    verdict_ok: bool = False
    tp: int = 0
    fn: int = 0
    required_total: int = 0
    recall: float = 0.0
    precision_proxy: float = 0.0  # critic-confirmed / all finding chunks
    cases: list[dict[str, Any]] = field(default_factory=list)
    path_hits: list[dict[str, Any]] = field(default_factory=list)
    critic: dict[str, Any] = field(default_factory=dict)
    score_pct: float = 0.0
    passed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_cases(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError(f"invalid cases pack: {path}")
    return data


def score_review(review_text: str, pack: dict[str, Any]) -> ScoreReport:
    text = review_text or ""
    low = _norm(text)
    verdict = parse_verdict(text)
    expected = normalize_verdict(str(pack.get("expected_verdict") or "REQUEST_CHANGES"))
    path_hits = extract_path_hits(text)
    path_blob = " ".join(h["path"] for h in path_hits).lower()

    case_results: list[CaseResult] = []
    tp = 0
    fn = 0
    required_total = 0
    for c in pack.get("cases") or []:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "case")
        required = bool(c.get("required", True))
        if required:
            required_total += 1
        terms = [str(t).lower() for t in (c.get("must_match_any") or []) if t]
        matched = [t for t in terms if t in low]
        # path soft check: any substring present in review or path hits
        path_ok = False
        for sub in c.get("path_substrings") or []:
            s = str(sub).lower()
            if s in low or s in path_blob:
                path_ok = True
                break
        hit = bool(matched) and (path_ok or not c.get("path_substrings"))
        # if path_substrings set but missing, still allow hit on strong multi-term match
        if not hit and len(matched) >= 2:
            hit = True
            path_ok = path_ok or bool(path_hits)
        cr = CaseResult(case_id=cid, hit=hit, matched_terms=matched, path_ok=path_ok)
        case_results.append(cr)
        if required:
            if hit:
                tp += 1
            else:
                fn += 1

    recall = (tp / required_total) if required_total else 0.0
    verdict_ok = verdict == expected if expected != "UNKNOWN" else True
    # composite: 70% recall + 30% verdict
    score_pct = round(100.0 * (0.7 * recall + 0.3 * (1.0 if verdict_ok else 0.0)), 1)
    # pass bar: all required cases + correct verdict direction when expected is RC
    passed = (fn == 0 and required_total > 0 and verdict_ok)

    return ScoreReport(
        pack_id=str(pack.get("id") or ""),
        verdict=verdict,
        expected_verdict=expected,
        verdict_ok=verdict_ok,
        tp=tp,
        fn=fn,
        required_total=required_total,
        recall=round(recall, 4),
        cases=[asdict(c) for c in case_results],
        path_hits=path_hits,
        score_pct=score_pct,
        passed=passed,
    )


def _tp_effective(sig: dict[str, Any]) -> float:
    """F95: 0–1 effective score from F94 annotations (or neutral legacy default)."""
    for key in ("effective_score", "effective"):
        if sig.get(key) is not None:
            try:
                return max(0.0, min(1.0, float(sig[key])))
            except (TypeError, ValueError):
                pass
    # No consolidation annotation → neutral (preserves pre-F95 confirm behavior)
    return 0.55


def _effective_confirm_floor() -> float:
    raw = (os.environ.get("TORII_TP_EFFECTIVE_FLOOR") or "0.25").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.25


def _load_supersede_index(
    memory_graph: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    """F101/F102: active supersedes targets from F100 graph (soft if missing).

    When ``paths`` set, F102 multi-hop expands co_path/same_theme neighborhood.
    """
    empty: dict[str, Any] = {
        "ids": set(),
        "themes": set(),
        "edges": [],
        "count": 0,
        "hop": {},
    }
    try:
        import importlib.util

        pol = Path(__file__).resolve().parent / "memory_temporal_graph.py"
        if not pol.is_file():
            return empty
        if (os.environ.get("TORII_GRAPH_SUPERSEDE") or "1").strip().lower() in (
            "0",
            "false",
            "off",
            "no",
        ):
            return empty
        spec = importlib.util.spec_from_file_location("memory_temporal_graph", pol)
        if not spec or not spec.loader:
            return empty
        mod = importlib.util.module_from_spec(spec)
        sys.modules["memory_temporal_graph"] = mod
        spec.loader.exec_module(mod)
        g = memory_graph
        if g is None:
            g = mod.load_or_build_graph(root or _root())
        idx = mod.superseded_index(g, paths=paths or None)
        return {
            "ids": set(idx.get("ids") or set()),
            "themes": set(idx.get("themes") or set()),
            "edges": list(idx.get("edges") or []),
            "count": int(idx.get("count") or 0),
            "hop": idx.get("hop") or {},
        }
    except Exception:
        return empty


def dual_pass_critic(
    review_text: str,
    *,
    fp_rules: list[dict[str, Any]] | None = None,
    tp_signatures: list[dict[str, Any]] | None = None,
    memory_graph: dict[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Pass-1 extract chunks; Pass-2 validate path evidence + FP demote + TP boost.

    Deterministic offline critic (no LLM) — cheap gate before optional live dual-agent.

    F95: TP boost is **effective-aware** — signatures with F94 `effective_score` below
    ``TORII_TP_EFFECTIVE_FLOOR`` (default 0.25) match as ``stale_tp_match`` (not confirmed),
    so decayed/low-importance memory cannot inflate precision.

    F101: **graph supersede demote** — if chunk matches a TP id/theme that is the target
    of an active F100 ``supersedes`` edge, status becomes ``superseded_tp`` (counts as FP),
    so resolved noise cannot re-confirm.

    F102: **multi-hop** — path seeds expand via co_path/same_theme so supersession on a
    sibling path/theme in the neighborhood also demotes.
    """
    chunks = extract_finding_chunks(review_text)
    fp_rules = fp_rules or []
    tp_signatures = tp_signatures or []
    validated: list[dict[str, Any]] = []
    likely_fp = 0
    confirmed_tp = 0
    weak_evidence = 0
    stale_tp = 0
    superseded_n = 0
    floor = _effective_confirm_floor()
    weighted_tp = 0.0
    # Preload graph once; re-index per chunk with path multi-hop
    _g_cache = memory_graph
    super_idx = _load_supersede_index(_g_cache, root=root, paths=None)
    hop_global = super_idx.get("hop") or {}

    for i, ch in enumerate(chunks):
        low = _norm(ch)
        paths = extract_path_hits(ch)
        has_path = bool(paths)
        # F102: path-scoped multi-hop supersede index for this finding
        path_list = []
        for ph in paths:
            if isinstance(ph, dict):
                path_list.append(str(ph.get("path") or ph.get("file") or ""))
            else:
                path_list.append(str(ph))
        path_list = [p for p in path_list if p]
        if path_list:
            super_idx = _load_supersede_index(_g_cache, root=root, paths=path_list)
        super_ids = super_idx.get("ids") or set()
        super_themes = super_idx.get("themes") or set()
        if super_idx.get("hop"):
            hop_global = super_idx.get("hop") or hop_global
        # FP demote: path matches a known FP rule and body lacks "new evidence"
        demoted = False
        demote_reason = ""
        for rule in fp_rules:
            rpath = str(rule.get("path") or "").lower()
            if rpath and rpath in low:
                demoted = True
                demote_reason = f"fp_rule:{rpath}"
                break
        # TP boost: keyword signature match, weighted by F94 effective_score
        tp_hits: list[str] = []
        tp_effs: list[float] = []
        tp_themes: list[str] = []
        best_eff = 0.0
        for sig in tp_signatures:
            if not isinstance(sig, dict):
                continue
            if sig.get("deleted") or sig.get("evicted"):
                continue
            kws = [str(k).lower() for k in (sig.get("keywords") or []) if k]
            if kws and any(k in low for k in kws):
                sid = str(sig.get("id") or sig.get("theme") or "sig")
                eff = _tp_effective(sig)
                tp_hits.append(sid)
                tp_effs.append(eff)
                th = _norm(str(sig.get("theme") or ""))
                if th:
                    tp_themes.append(th)
                best_eff = max(best_eff, eff)
        # F101: filter TP hits that are graph-superseded; demote only if none remain
        graph_hit = ""
        live_hits: list[str] = []
        live_effs: list[float] = []
        if super_ids or super_themes:
            for j, sid in enumerate(tp_hits):
                th = tp_themes[j] if j < len(tp_themes) else ""
                sid_super = sid in super_ids or f"tp:{sid}" in super_ids
                th_super = bool(th and th in super_themes)
                if sid_super or th_super:
                    if not graph_hit:
                        graph_hit = sid if sid_super else f"theme:{th}"
                    continue
                live_hits.append(sid)
                if j < len(tp_effs):
                    live_effs.append(tp_effs[j])
            # Theme-only demote when no TP signature hits but text is pure superseded theme
            if not tp_hits and not demoted:
                for th in super_themes:
                    needle = th.replace("_", " ")
                    if th and (needle in low or th in low):
                        graph_hit = f"theme:{th}"
                        break
        else:
            live_hits = list(tp_hits)
            live_effs = list(tp_effs)

        best_live = max(live_effs) if live_effs else 0.0
        if graph_hit and not live_hits and not demoted:
            demoted = True
            demote_reason = f"graph_supersedes:{graph_hit}"

        status = "candidate"
        if demoted and demote_reason.startswith("graph_supersedes:"):
            status = "superseded_tp"
            superseded_n += 1
            likely_fp += 1  # precision: treat as non-TP
        elif demoted:
            status = "likely_fp"
            likely_fp += 1
        elif live_hits and has_path and best_live >= floor:
            status = "confirmed_tp"
            confirmed_tp += 1
            weighted_tp += best_live
        elif live_hits and has_path and best_live < floor:
            # Stale / low-importance memory — path only, do not confirm
            status = "stale_tp_match"
            stale_tp += 1
        elif has_path and len(ch) > 40:
            status = "path_evidenced"
        else:
            status = "weak_evidence"
            weak_evidence += 1

        validated.append(
            {
                "index": i,
                "status": status,
                "has_path": has_path,
                "paths": paths[:5],
                "tp_signature_hits": live_hits or tp_hits,
                "tp_effective_max": round(best_live or best_eff, 4) if (live_hits or tp_hits) else None,
                "tp_effective_scores": [round(e, 4) for e in (live_effs or tp_effs)] if (live_effs or tp_effs) else [],
                "demote_reason": demote_reason,
                "graph_filtered": graph_hit or None,
                "preview": ch[:180].replace("\n", " "),
            }
        )

    total = len(validated) or 1
    precision_proxy = round(
        (confirmed_tp + sum(1 for v in validated if v["status"] == "path_evidenced"))
        / total,
        4,
    )
    # F95: effective-weighted precision (confirmed weighted by best_eff)
    eff_precision = round(
        (
            weighted_tp
            + 0.5 * sum(1 for v in validated if v["status"] == "path_evidenced")
            + 0.15 * stale_tp
        )
        / total,
        4,
    )
    return {
        "feature": FEATURE,
        "pass": "dual_offline",
        "effective_aware": True,
        "graph_supersede_aware": True,
        "graph_multi_hop": bool((hop_global or {}).get("multi_hop")),
        "graph_supersede_edges": int(super_idx.get("count") or 0),
        "graph_hop": hop_global or {},
        "effective_floor": floor,
        "chunk_count": len(chunks),
        "likely_fp": likely_fp,
        "confirmed_tp": confirmed_tp,
        "stale_tp_match": stale_tp,
        "superseded_tp": superseded_n,
        "weak_evidence": weak_evidence,
        "precision_proxy": precision_proxy,
        "effective_precision": eff_precision,
        "findings": validated,
    }


# ---------------------------------------------------------------------------
# TP signatures (compound memory — dual of F64 fp-rules)
# ---------------------------------------------------------------------------


def default_tp_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_TP_SIGNATURES_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    r = root or _root()
    return r / ".torii" / TP_FILENAME


def load_tp_signatures(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or default_tp_path()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        return [x for x in (data.get("signatures") or []) if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def save_tp_signatures(path: Path, signatures: list[dict[str, Any]]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": TP_SCHEMA,
        "feature": FEATURE,
        "updated_at": _now(),
        "count": len(signatures),
        "signatures": signatures,
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return path


def _sig_key(s: dict[str, Any]) -> str:
    return str(s.get("id") or "") or f"{s.get('theme')}|{','.join(s.get('keywords') or [])}"


def _maybe_consolidate_tp(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """F94: soft consolidate after write merge (importance/merge/decay/evict)."""
    try:
        import importlib.util

        if (os.environ.get("TORII_MEMORY_CONSOLIDATE") or "1").strip().lower() in (
            "0",
            "false",
            "off",
            "no",
        ):
            return items
        pol = Path(__file__).resolve().parent / "memory_consolidate.py"
        if not pol.is_file():
            return items
        spec = importlib.util.spec_from_file_location("memory_consolidate", pol)
        if not spec or not spec.loader:
            return items
        mod = importlib.util.module_from_spec(spec)
        sys.modules["memory_consolidate"] = mod
        spec.loader.exec_module(mod)
        if not mod.enabled():
            return items
        return mod.consolidate_items(items)
    except Exception:
        return items


def merge_tp_signatures(
    existing: list[dict[str, Any]], incoming: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge TP signatures; prefer F93 Mem0-style event policy when available."""
    # F93: ADD/UPDATE/DELETE/NONE write path (soft fallback to legacy union)
    try:
        import importlib.util

        pol = Path(__file__).resolve().parent / "memory_event_policy.py"
        if pol.is_file() and (os.environ.get("TORII_MEMORY_EVENTS") or "1").strip().lower() not in (
            "0",
            "false",
            "off",
            "no",
        ):
            spec = importlib.util.spec_from_file_location("memory_event_policy", pol)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["memory_event_policy"] = mod
                spec.loader.exec_module(mod)
                if mod.enabled():
                    for s in existing + incoming:
                        if isinstance(s, dict):
                            s.setdefault("kind", "tp")
                    events = mod.plan_events(existing, incoming, candidate_kind="tp")
                    store = mod.apply_events({"items": list(existing), "history": []}, events)
                    merged = [
                        i
                        for i in (store.get("items") or [])
                        if isinstance(i, dict) and not i.get("deleted")
                    ]
                    return _maybe_consolidate_tp(merged)
    except Exception:
        pass
    best: dict[str, dict[str, Any]] = {}
    for s in existing + incoming:
        if not isinstance(s, dict):
            continue
        k = _sig_key(s)
        if not k:
            continue
        if k not in best:
            best[k] = dict(s)
            best[k]["hits"] = int(s.get("hits") or 1)
            continue
        old = best[k]
        old["hits"] = int(old.get("hits") or 1) + int(s.get("hits") or 1)
        # union keywords
        kws = list(dict.fromkeys(list(old.get("keywords") or []) + list(s.get("keywords") or [])))
        old["keywords"] = kws[:24]
        if s.get("cwe") and not old.get("cwe"):
            old["cwe"] = s.get("cwe")
    return _maybe_consolidate_tp(list(best.values()))


def signatures_from_score(
    report: ScoreReport, pack: dict[str, Any]
) -> list[dict[str, Any]]:
    """Promote matched ground-truth cases into TP signatures."""
    by_id = {str(c.get("id")): c for c in (pack.get("cases") or []) if isinstance(c, dict)}
    out: list[dict[str, Any]] = []
    for cr in report.cases:
        if not cr.get("hit"):
            continue
        cid = str(cr.get("case_id") or "")
        base = by_id.get(cid) or {}
        kws = list(base.get("must_match_any") or [])[:12]
        if not kws and cr.get("matched_terms"):
            kws = list(cr["matched_terms"])
        out.append(
            {
                "id": cid or f"tp-{len(out)}",
                "theme": str(base.get("theme") or cid),
                "cwe": base.get("cwe") or [],
                "tags": base.get("tags") or [],
                "keywords": kws,
                "path_globs": list(base.get("path_substrings") or []),
                "source": "bench_promote",
                "hits": 1,
                "promoted_at": _now(),
            }
        )
    return out


def render_tp_section(signatures: list[dict[str, Any]], *, max_n: int = 16) -> str:
    if not signatures:
        return ""
    lines = [
        "<!-- torii-f70-tp-signatures -->",
        "## Known true-positive signatures (F70 compound memory)",
        "",
        "These patterns were confirmed on labeled benches or prior TP promotions.",
        "Prefer raising path-evidenced findings that match; do not skip them as noise.",
        "",
    ]
    for s in signatures[:max_n]:
        kws = ", ".join(str(k) for k in (s.get("keywords") or [])[:8])
        cwe = s.get("cwe") or []
        cwe_s = ",".join(cwe) if isinstance(cwe, list) else str(cwe)
        lines.append(
            f"- `{s.get('id')}` theme={s.get('theme') or '?'} "
            f"cwe={cwe_s or 'n/a'} hits={s.get('hits') or 1} keywords=[{kws}]"
        )
    lines.append("")
    return "\n".join(lines)


def inject_tp_into_prompt(prompt_path: Path, signatures: list[dict[str, Any]]) -> bool:
    section = render_tp_section(signatures)
    if not section:
        return False
    text = prompt_path.read_text(encoding="utf-8", errors="replace") if prompt_path.is_file() else ""
    marker = "<!-- torii-f70-tp-signatures -->"
    if marker in text:
        # replace existing block through next HTML comment or EOF soft
        text = re.sub(
            rf"{re.escape(marker)}[\s\S]*?(?=\n<!--|\Z)",
            section.rstrip() + "\n",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + "\n\n" + section
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return True


def load_fp_rules_dicts(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        return [x for x in (data.get("rules") or []) if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_score(args: argparse.Namespace) -> int:
    review = Path(args.review).read_text(encoding="utf-8", errors="replace")
    pack = load_cases(Path(args.cases))
    report = score_review(review, pack)
    critic = dual_pass_critic(
        review,
        fp_rules=load_fp_rules_dicts(Path(args.fp_rules) if args.fp_rules else None),
        tp_signatures=load_tp_signatures(Path(args.tp_signatures) if args.tp_signatures else None)
        if args.tp_signatures
        else load_tp_signatures(),
    )
    report.critic = critic
    report.precision_proxy = float(critic.get("precision_proxy") or 0.0)
    out = report.as_dict()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"pack={report.pack_id}")
        print(f"verdict={report.verdict} expected={report.expected_verdict} verdict_ok={int(report.verdict_ok)}")
        print(f"tp={report.tp} fn={report.fn} required={report.required_total} recall={report.recall}")
        print(f"score_pct={report.score_pct} passed={int(report.passed)}")
        print(f"critic_precision_proxy={report.precision_proxy}")
        for c in report.cases:
            print(f"  case {c['case_id']}: hit={int(c['hit'])} terms={c['matched_terms'][:4]}")
    return 0 if report.passed or args.soft else 1


def cmd_critic(args: argparse.Namespace) -> int:
    review = Path(args.review).read_text(encoding="utf-8", errors="replace")
    fp = load_fp_rules_dicts(Path(args.fp_rules) if args.fp_rules else None)
    tp = load_tp_signatures(Path(args.tp_signatures) if args.tp_signatures else None)
    result = dual_pass_critic(review, fp_rules=fp, tp_signatures=tp)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2) if args.json else (
        f"chunks={result['chunk_count']} confirmed_tp={result['confirmed_tp']} "
        f"likely_fp={result['likely_fp']} weak={result['weak_evidence']} "
        f"precision_proxy={result['precision_proxy']}"
    ))
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    score_path = Path(args.score_json)
    pack = load_cases(Path(args.cases)) if args.cases else None
    raw = json.loads(score_path.read_text(encoding="utf-8"))
    report = ScoreReport(
        pack_id=str(raw.get("pack_id") or ""),
        verdict=str(raw.get("verdict") or "UNKNOWN"),
        expected_verdict=str(raw.get("expected_verdict") or ""),
        verdict_ok=bool(raw.get("verdict_ok")),
        tp=int(raw.get("tp") or 0),
        fn=int(raw.get("fn") or 0),
        required_total=int(raw.get("required_total") or 0),
        recall=float(raw.get("recall") or 0),
        cases=list(raw.get("cases") or []),
        path_hits=list(raw.get("path_hits") or []),
        score_pct=float(raw.get("score_pct") or 0),
        passed=bool(raw.get("passed")),
    )
    if pack is None:
        # reconstruct minimal pack from cases hits only
        pack = {"id": report.pack_id, "cases": []}
    incoming = signatures_from_score(report, pack)
    dest = Path(args.out) if args.out else default_tp_path()
    merged = merge_tp_signatures(load_tp_signatures(dest), incoming)
    save_tp_signatures(dest, merged)
    print(f"tp_signatures={dest}")
    print(f"promoted={len(incoming)}")
    print(f"total={len(merged)}")
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    sigs = load_tp_signatures(Path(args.tp_signatures) if args.tp_signatures else None)
    if args.print_only:
        print(render_tp_section(sigs), end="")
        return 0
    prompt = Path(args.prompt)
    ok = inject_tp_into_prompt(prompt, sigs)
    print(f"injected={int(ok)} prompt={prompt} count={len(sigs)}")
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Offline e2e: score good + weak fixtures; promote TPs from good; emit metrics."""
    root = _root()
    cases_path = Path(args.cases) if args.cases else root / DEFAULT_CASES
    good_path = Path(args.good) if args.good else root / DEFAULT_GOOD
    weak_path = Path(args.weak) if args.weak else root / DEFAULT_WEAK
    out_dir = Path(args.out_dir) if args.out_dir else root / ".torii-out" / "bench-f70"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = load_cases(cases_path)
    good = good_path.read_text(encoding="utf-8", errors="replace")
    weak = weak_path.read_text(encoding="utf-8", errors="replace")

    good_report = score_review(good, pack)
    good_report.critic = dual_pass_critic(good, tp_signatures=load_tp_signatures())
    good_report.precision_proxy = float(good_report.critic.get("precision_proxy") or 0)

    weak_report = score_review(weak, pack)
    weak_report.critic = dual_pass_critic(weak)
    weak_report.precision_proxy = float(weak_report.critic.get("precision_proxy") or 0)

    # compound: promote from good into out_dir (always); local .torii only if --local-promote
    incoming = signatures_from_score(good_report, pack)
    tp_path = out_dir / TP_FILENAME
    merged = merge_tp_signatures(load_tp_signatures(tp_path), incoming)
    save_tp_signatures(tp_path, merged)
    if args.local_promote:
        save_tp_signatures(
            default_tp_path(root),
            merge_tp_signatures(load_tp_signatures(default_tp_path(root)), incoming),
        )

    metrics = {
        "feature": FEATURE,
        "at": _now(),
        "pack": pack.get("id"),
        "good": good_report.as_dict(),
        "weak": weak_report.as_dict(),
        "delta_recall": round(good_report.recall - weak_report.recall, 4),
        "tp_signatures_promoted": len(incoming),
        "tp_signatures_path": str(tp_path),
        "fixture_pass": bool(good_report.passed and not weak_report.passed),
    }
    (out_dir / "bench-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (out_dir / "bench-metrics.md").write_text(
        "\n".join(
            [
                f"# F70 bench metrics — `{pack.get('id')}`",
                "",
                f"- at: `{metrics['at']}`",
                f"- good: recall={good_report.recall} tp={good_report.tp}/{good_report.required_total} "
                f"verdict={good_report.verdict} passed={good_report.passed}",
                f"- weak: recall={weak_report.recall} tp={weak_report.tp}/{weak_report.required_total} "
                f"verdict={weak_report.verdict} passed={weak_report.passed}",
                f"- delta_recall (good−weak): **{metrics['delta_recall']}**",
                f"- fixture_pass (good hits all, weak misses): **{metrics['fixture_pass']}**",
                f"- TP signatures promoted: {len(incoming)} → `{tp_path}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"out_dir={out_dir}")
    print(f"good_recall={good_report.recall} good_passed={int(good_report.passed)}")
    print(f"weak_recall={weak_report.recall} weak_passed={int(weak_report.passed)}")
    print(f"delta_recall={metrics['delta_recall']}")
    print(f"fixture_pass={int(metrics['fixture_pass'])}")
    print(f"tp_promoted={len(incoming)}")
    print(f"metrics={out_dir / 'bench-metrics.json'}")
    return 0 if metrics["fixture_pass"] else 1


def cmd_live(args: argparse.Namespace) -> int:
    """Bounded real agent review on demo/insecure when OPENROUTER_API_KEY is set."""
    root = _root()
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    # load .env without printing secrets
    env_file = root / ".env"
    if not key and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not key:
        print("live_skipped=1 reason=no_OPENROUTER_API_KEY", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else root / ".torii-out" / "bench-f70-live"
    out_dir.mkdir(parents=True, exist_ok=True)
    demo = root / "demo" / "insecure" / "app.py"
    if not demo.is_file():
        print("error: demo/insecure/app.py missing", file=sys.stderr)
        return 1

    # Build a minimal review prompt + workspace context (no full PR assemble)
    model = (os.environ.get("TORII_BENCH_MODEL") or args.model or "openai/gpt-4.1-mini").strip()
    prompt_path = out_dir / "prompt.md"
    code = demo.read_text(encoding="utf-8", errors="replace")
    # inject TP signatures if any
    sigs = load_tp_signatures()
    tp_section = render_tp_section(sigs)
    prompt_path.write_text(
        "\n".join(
            [
                "# Task",
                "You are Torii Gate security reviewer. Review the following file for vulnerabilities.",
                "Produce Markdown with **Verdict:**, **Score:**, ### Summary, ### Blocking,",
                "### Security audit, ### Key findings, ### Tests & risk, ### What I checked.",
                "Every finding MUST cite a path (use `demo/insecure/app.py`). Prefer high-severity issues.",
                "",
                f"**Repo:** local-bench",
                f"**File under review:** `demo/insecure/app.py`",
                "",
                tp_section,
                "",
                "```python",
                code,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["OPENROUTER_API_KEY"] = key
    env["TORII_MODEL"] = model
    env["OPENROUTER_MODEL"] = model
    env["OUT_DIR"] = str(out_dir)
    env["PROMPT_PATH"] = str(prompt_path)
    env["TORII_ROOT"] = str(root)
    env["WORKSPACE_ROOT"] = str(root)
    env["PR_NUMBER"] = "bench-f70"
    # tight budget for bench
    env.setdefault("TORII_MAX_TURNS", "12")
    env.setdefault("TORII_REVIEW_TIMEOUT_SECONDS", str(args.timeout))

    hermes = root / "scripts" / "run-hermes-review.sh"
    if not hermes.is_file():
        print("error: run-hermes-review.sh missing", file=sys.stderr)
        return 1

    print(f"live_start model={model} out_dir={out_dir}", file=sys.stderr)
    rc = subprocess.call(["bash", str(hermes)], cwd=str(root), env=env)
    # find review artifact
    review_path = out_dir / "review.md"
    if not review_path.is_file():
        # common alternates
        for cand in sorted(out_dir.glob("review*.md")):
            review_path = cand
            break
    if not review_path.is_file():
        # hermes raw
        for name in ("hermes-output.md", "agent-output.md", "raw-review.md"):
            if (out_dir / name).is_file():
                review_path = out_dir / name
                break
    if not review_path.is_file():
        print(f"live_rc={rc} error=no_review_artifact", file=sys.stderr)
        return 1 if rc != 0 else 1

    pack = load_cases(root / DEFAULT_CASES)
    text = review_path.read_text(encoding="utf-8", errors="replace")
    report = score_review(text, pack)
    report.critic = dual_pass_critic(text, tp_signatures=load_tp_signatures())
    report.precision_proxy = float(report.critic.get("precision_proxy") or 0)
    if report.passed or report.tp > 0:
        incoming = signatures_from_score(report, pack)
        dest = out_dir / TP_FILENAME
        save_tp_signatures(dest, merge_tp_signatures(load_tp_signatures(dest), incoming))
        save_tp_signatures(
            default_tp_path(root),
            merge_tp_signatures(load_tp_signatures(default_tp_path(root)), incoming),
        )
    metrics = {
        "feature": FEATURE,
        "mode": "live",
        "at": _now(),
        "model": model,
        "hermes_rc": rc,
        "review": str(review_path),
        "score": report.as_dict(),
    }
    (out_dir / "bench-live-metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(f"live_rc={rc}")
    print(f"review={review_path}")
    print(f"recall={report.recall} tp={report.tp} fn={report.fn} passed={int(report.passed)}")
    print(f"verdict={report.verdict}")
    print(f"metrics={out_dir / 'bench-live-metrics.json'}")
    return 0 if report.passed else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F70 security bench + dual-pass critic + TP memory")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="score review vs ground-truth cases")
    s.add_argument("--review", required=True)
    s.add_argument("--cases", required=True)
    s.add_argument("--out", default=None)
    s.add_argument("--fp-rules", default=None)
    s.add_argument("--tp-signatures", default=None)
    s.add_argument("--json", action="store_true")
    s.add_argument("--soft", action="store_true", help="exit 0 even if not passed")

    c = sub.add_parser("critic", help="dual-pass offline critic")
    c.add_argument("--review", required=True)
    c.add_argument("--fp-rules", default=None)
    c.add_argument("--tp-signatures", default=None)
    c.add_argument("--out", default=None)
    c.add_argument("--json", action="store_true")

    pr = sub.add_parser("promote", help="promote TPs from score JSON into tp-signatures.json")
    pr.add_argument("--score-json", required=True)
    pr.add_argument("--cases", default=None)
    pr.add_argument("--out", default=None)

    inj = sub.add_parser("inject", help="inject TP signatures into prompt")
    inj.add_argument("--prompt", default=None)
    inj.add_argument("--tp-signatures", default=None)
    inj.add_argument("--print-only", action="store_true")

    fx = sub.add_parser("fixture", help="offline e2e good+weak fixtures")
    fx.add_argument("--cases", default=None)
    fx.add_argument("--good", default=None)
    fx.add_argument("--weak", default=None)
    fx.add_argument("--out-dir", default=None)
    fx.add_argument(
        "--local-promote",
        action="store_true",
        help="also merge TP signatures into .torii/tp-signatures.json",
    )
    fx.add_argument(
        "--no-local-promote",
        action="store_true",
        help=argparse.SUPPRESS,
    )  # back-compat no-op

    lv = sub.add_parser("live", help="bounded real agent e2e on demo/insecure")
    lv.add_argument("--out-dir", default=None)
    lv.add_argument("--model", default=None)
    lv.add_argument("--timeout", type=int, default=180)

    args = p.parse_args(argv)
    if args.cmd == "score":
        return cmd_score(args)
    if args.cmd == "critic":
        return cmd_critic(args)
    if args.cmd == "promote":
        return cmd_promote(args)
    if args.cmd == "inject":
        if not args.print_only and not args.prompt:
            print("error: --prompt required unless --print-only", file=sys.stderr)
            return 2
        return cmd_inject(args)
    if args.cmd == "fixture":
        return cmd_fixture(args)
    if args.cmd == "live":
        return cmd_live(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
