#!/usr/bin/env python3
"""F98: MemGPT-style archival_memory_search + promote-to-core (tools-as-code).

Research drivers (patterns only — no vendored Letta/MemGPT runtime):
  - MemGPT archival_memory_search / core_memory_append: agent pages cold facts
    into working context on demand
  - Torii F97 tiers put cold items in archival but provided no retrieval tool
  - MEMORY.md distill is append-only prose — never keyword-searchable for PR paths

Product thesis:
  Highest ROI agentic-memory slice: **deterministic archival search** over
  TP/FP/federated stores + MEMORY.md recall blocks, then optional **promote**
  of hits into a core inject section for the current run (just-in-time paging).

Commands:
  search    — query archival + recall stores (JSON hits)
  promote   — write top hits as core inject markdown
  auto      — search from changed-path basenames + promote (assemble soft path)
  fixture   — hermetic: hit archival theme, miss poison privacy, promote inject
  status    — sources / last result summary

Env:
  TORII_ROOT
  TORII_ARCHIVAL_SEARCH        1 (default) | 0
  TORII_ARCHIVAL_SEARCH_LIMIT  default 8
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
SCHEMA = 1
MARKER = "<!-- torii-f98-archival-search -->"

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
    lines = [
        MARKER,
        "## Archival search → core (F98 — MemGPT-style paging)",
        "",
        f"Query: `{result.get('query')}` · hits={result.get('hit_count')} "
        f"(just-in-time from cold/archival + MEMORY.md recall).",
        "Treat promoted hits as **core** for this PR; still require path evidence to block.",
        "",
    ]
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


def auto_from_paths(
    paths: list[str],
    *,
    root: Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build query from changed path basenames + common security stems."""
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
    query = " ".join(bases[:12] + extra[:3])
    return search(query, root=root, limit=limit)


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
    section = render_promote_section(result)
    out: dict[str, Any] = {
        "feature": FEATURE,
        "hit_count": result.get("hit_count"),
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
    result = auto_from_paths(paths, limit=args.limit)
    section = render_promote_section(result)
    out: dict[str, Any] = {
        "feature": FEATURE,
        "mode": "auto",
        "paths": paths[:20],
        "query": result.get("query"),
        "hit_count": result.get("hit_count"),
        "hits": [
            {"id": h.get("id"), "source": h.get("source"), "score": h.get("score"), "theme": h.get("theme")}
            for h in (result.get("hits") or [])[:8]
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
        }
        try:
            os.environ["TORII_ROOT"] = str(td_path)
            os.environ["TORII_TP_SIGNATURES_FILE"] = str(torii / "tp-signatures.json")
            os.environ["TORII_FP_RULES_FILE"] = str(torii / "fp-rules.json")
            os.environ["TORII_MEMORY_MD"] = str(mem / "MEMORY.md")
            os.environ["TORII_ARCHIVAL_SEARCH"] = "1"

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

            auto = auto_from_paths(["legacy/db.py", "app.py"], root=td_path, limit=5)
            auto_ok = int(auto.get("hit_count") or 0) >= 1

            fixture_pass = all(
                [hit_tp, hit_fp, hit_mem, privacy_ok, promote_ok, inject_ok, auto_ok]
            )
            print(
                json.dumps(
                    {
                        "feature": FEATURE,
                        "fixture_pass": fixture_pass,
                        "hit_tp": hit_tp,
                        "hit_fp": hit_fp,
                        "hit_mem": hit_mem,
                        "privacy_ok": privacy_ok,
                        "promote_ok": promote_ok,
                        "inject_ok": inject_ok,
                        "auto_ok": auto_ok,
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
    pp.set_defaults(func=cmd_promote)

    pa = sub.add_parser("auto", help="Search from changed paths + optional inject")
    pa.add_argument("--files", default="", help="comma-separated paths")
    pa.add_argument("--files-list", default="")
    pa.add_argument("--limit", type=int, default=None)
    pa.add_argument("--prompt", default="")
    pa.add_argument("--json-out", default="")
    pa.add_argument("--section-out", default="")
    pa.set_defaults(func=cmd_auto)

    sub.add_parser("fixture").set_defaults(func=cmd_fixture)
    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
