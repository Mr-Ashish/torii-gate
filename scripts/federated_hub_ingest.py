#!/usr/bin/env python3
"""F77: Cross-tenant hub federated signal ingest (privacy-preserving).

Research drivers (2026):
  - Multi-tenant agent FL privacy (IETF draft-kale-agntcy-federated-privacy):
    aggregate without raw tenant data; secure aggregation mindset
  - Memory isolation (RAG multi-tenant): never surface one tenant's private
    paths/snippets to another
  - Torii prior: F65 tenant layout, F71 federate() local, F75 scoped recall
    — missing **hub-side multi-tenant merge + promote gate**

Product thesis:
  Each tenant/run emits privacy-safe signals (theme/CWE/keywords/basenames).
  Hub ingests them into `memory/federation/`, counts unique tenant hashes,
  and only **promotes** themes seen across ≥ min_tenants (poison/noise filter).

Commands:
  collect   — gather signals from files / tenant trees
  ingest    — merge into hub federation (+ tenant-local copy)
  promote   — filter global store by min_tenants / min_hits
  status    — federation summary
  fixture   — two synthetic tenants → multi-tenant aggregate + privacy
  from-run  — ingest from a hub-run payload object / JSON file

Env:
  TORII_ROOT / HUB_ROOT
  TORII_FEDERATED_HUB          1 (default) | 0
  TORII_FED_MIN_TENANTS        default 2 for promote
  TORII_FED_MIN_HITS           default 2 for promote
  TORII_MEMORY_TENANT          optional tenant id for tenant-local write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F77"
SCHEMA = 1
FED_NAME = "federated-signals.json"
GLOBAL_REL = "memory/federation"
TENANT_FED_REL = "memory/tenants/{tenant}/federation"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})
_PRIVATE_PATH_RX = re.compile(
    r"(?:/Users/|/home/|C:\\\\Users\\\\|\\\\Users\\\\|/private/var/|/tmp/[A-Za-z0-9_-]{12,})",
    re.I,
)


def _root() -> Path:
    for key in ("HUB_ROOT", "TORII_ROOT"):
        env = (os.environ.get(key) or "").strip()
        if env:
            return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_FEDERATED_HUB") or "1").strip().lower()
    return raw not in _FALSEY


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def sanitize_tenant(raw: str | None = None) -> str:
    t = (raw if raw is not None else os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    if not t:
        return ""
    t = re.sub(r"[^A-Za-z0-9._-]+", "-", t).strip("-.")[:64]
    return t


def tenant_hash(tenant: str) -> str:
    """Non-reversible short hash — never store raw tenant in global aggregate fields."""
    if not tenant:
        return ""
    return hashlib.sha256(tenant.encode("utf-8")).hexdigest()[:12]


def global_fed_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_FEDERATED_HUB_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / GLOBAL_REL / FED_NAME


def tenant_fed_path(root: Path, tenant: str) -> Path:
    t = sanitize_tenant(tenant)
    return root / TENANT_FED_REL.format(tenant=t) / FED_NAME


def load_signals(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        items = data.get("signals") or []
    elif isinstance(data, list):
        items = data
    else:
        return []
    return [x for x in items if isinstance(x, dict)]


def sanitize_signal(s: dict[str, Any], *, tenant: str = "") -> dict[str, Any] | None:
    """Strip to privacy-safe fields; reject poison."""
    theme = str(s.get("theme") or s.get("id") or "").strip().lower()
    if not theme or theme == "untrusted_input":
        return None
    sid = re.sub(r"[^a-z0-9._-]+", "-", str(s.get("id") or theme))[:64]
    cwe = s.get("cwe") or []
    if isinstance(cwe, str):
        cwe = [cwe]
    kws: list[str] = []
    for k in s.get("keywords") or []:
        ks = str(k).strip()
        if not ks or len(ks) > 48:
            continue
        if _PRIVATE_PATH_RX.search(ks) or "/Users/" in ks:
            continue
        if re.search(r"sk-[a-z0-9_-]{8,}", ks, re.I):
            continue
        if ks.count("/") >= 2:
            continue
        kws.append(ks[:48])
    kws = list(dict.fromkeys(kws))[:12]
    bases: list[str] = []
    for b in s.get("path_basenames") or []:
        bs = str(b).replace("\\", "/").strip()
        if not bs or "/" in bs or "\\" in bs:
            # keep only basename
            bs = Path(bs).name
        if bs and not _PRIVATE_PATH_RX.search(bs):
            bases.append(bs[:64])
    bases = list(dict.fromkeys(bases))[:6]
    tags = [str(t) for t in (s.get("tags") or []) if str(t)][:10]
    out: dict[str, Any] = {
        "id": sid,
        "theme": theme,
        "cwe": [str(c) for c in cwe][:8],
        "tags": tags,
        "keywords": kws,
        "path_basenames": bases,
        "hits": max(1, int(s.get("hits") or 1)),
        "source": str(s.get("source") or "hub_ingest")[:32],
    }
    # unique tenant hashes for multi-tenant count
    th_set: list[str] = []
    if s.get("tenant_hashes") and isinstance(s["tenant_hashes"], list):
        th_set = [str(x) for x in s["tenant_hashes"] if x][:32]
    th = str(s.get("tenant_hash") or "")
    if tenant:
        th = tenant_hash(tenant) or th
    if th and th not in th_set:
        th_set.append(th)
    if th_set:
        out["tenant_hashes"] = th_set
        out["tenants"] = len(th_set)
    else:
        out["tenants"] = max(1, int(s.get("tenants") or 1))
    # never keep raw tenant name or paths/snippets
    return out


def assert_privacy(signals: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    for s in signals:
        blob = json.dumps(s, ensure_ascii=False)
        if _PRIVATE_PATH_RX.search(blob):
            issues.append(f"private_path in {s.get('id')}")
        if "snippet" in s or "code" in s or "review_md" in s:
            issues.append(f"raw_code_field in {s.get('id')}")
        if s.get("tenant") and not s.get("tenant_hash"):
            # raw tenant string on global signal is discouraged
            issues.append(f"raw_tenant_field in {s.get('id')}")
        for p in s.get("path_basenames") or []:
            if "/" in str(p) or "\\" in str(p):
                issues.append(f"multi_segment_path in {s.get('id')}: {p}")
        for k in s.get("keywords") or []:
            if re.search(r"sk-[a-z0-9_-]{10,}", str(k), re.I):
                issues.append(f"secret_keyword in {s.get('id')}")
    return issues


def merge_signals(
    existing: list[dict[str, Any]], incoming: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for s in existing + incoming:
        clean = sanitize_signal(s)
        if not clean:
            continue
        sid = clean["id"]
        if sid not in by_id:
            by_id[sid] = clean
            continue
        cur = by_id[sid]
        cur["hits"] = int(cur.get("hits") or 0) + int(clean.get("hits") or 1)
        # union tenant hashes
        th = list(cur.get("tenant_hashes") or [])
        for h in clean.get("tenant_hashes") or []:
            if h not in th:
                th.append(h)
        if th:
            cur["tenant_hashes"] = th[:64]
            cur["tenants"] = len(th)
        else:
            cur["tenants"] = max(int(cur.get("tenants") or 1), int(clean.get("tenants") or 1))
        cur["keywords"] = list(
            dict.fromkeys(list(cur.get("keywords") or []) + list(clean.get("keywords") or []))
        )[:12]
        cur["cwe"] = list(
            dict.fromkeys(list(cur.get("cwe") or []) + list(clean.get("cwe") or []))
        )[:8]
        cur["path_basenames"] = list(
            dict.fromkeys(
                list(cur.get("path_basenames") or []) + list(clean.get("path_basenames") or [])
            )
        )[:8]
        cur["tags"] = list(
            dict.fromkeys(list(cur.get("tags") or []) + list(clean.get("tags") or []))
        )[:10]
        # prefer richer source label
        if clean.get("source") and clean["source"] != cur.get("source"):
            cur["source"] = f"{cur.get('source')}+{clean['source']}"[:48]
    out = sorted(
        by_id.values(),
        key=lambda x: (-int(x.get("tenants") or 0), -int(x.get("hits") or 0), str(x.get("id"))),
    )
    return out


def write_store(
    path: Path,
    signals: list[dict[str, Any]],
    *,
    scope: str = "global",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issues = assert_privacy(signals)
    if issues:
        # drop offenders
        bad_ids = set()
        for i in issues:
            m = re.search(r" in ([^\s:]+)", i)
            if m:
                bad_ids.add(m.group(1))
        signals = [s for s in signals if str(s.get("id")) not in bad_ids]
        issues = assert_privacy(signals)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, Any] = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "scope": scope,
        "updated_at": _now(),
        "count": len(signals),
        "privacy": "theme_cwe_keywords_basenames_tenant_hash_only",
        "privacy_ok": len(issues) == 0,
        "privacy_issues": issues,
        "signals": signals,
    }
    if extra:
        doc.update(extra)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def collect_from_paths(paths: list[Path], *, tenant: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        if not p.is_file():
            continue
        for s in load_signals(p):
            clean = sanitize_signal(s, tenant=tenant)
            if clean:
                out.append(clean)
    return out


def collect_from_tenant_tree(root: Path) -> list[dict[str, Any]]:
    """Walk memory/tenants/*/ and classic repos for federated-signals.json."""
    found: list[dict[str, Any]] = []
    tenants_root = root / "memory" / "tenants"
    if tenants_root.is_dir():
        for tdir in sorted(tenants_root.iterdir()):
            if not tdir.is_dir():
                continue
            tenant = tdir.name
            candidates = [
                tdir / "federation" / FED_NAME,
                tdir / FED_NAME,
            ]
            for repo in (tdir / "repos").glob("*") if (tdir / "repos").is_dir() else []:
                candidates.append(repo / FED_NAME)
                candidates.append(repo / ".torii" / FED_NAME)
            found.extend(collect_from_paths(candidates, tenant=tenant))
    # classic shared
    for p in [
        root / "memory" / "federation" / FED_NAME,
        root / ".torii" / FED_NAME,
        root / "memory" / FED_NAME,
    ]:
        found.extend(collect_from_paths([p], tenant=""))
    return found


def ingest(
    root: Path,
    incoming: list[dict[str, Any]],
    *,
    tenant: str = "",
    source_repo: str = "",
    write_tenant: bool = True,
) -> dict[str, Any]:
    """Merge incoming into global hub federation (+ tenant local)."""
    cleaned = []
    for s in incoming:
        c = sanitize_signal(s, tenant=tenant)
        if c:
            cleaned.append(c)

    gpath = global_fed_path(root)
    existing = load_signals(gpath)
    merged = merge_signals(existing, cleaned)
    gdoc = write_store(
        gpath,
        merged,
        scope="global",
        extra={
            "last_source_repo": source_repo or None,
            "last_tenant_hash": tenant_hash(tenant) if tenant else None,
        },
    )

    tdoc = None
    tpath = None
    if write_tenant and tenant:
        tpath = tenant_fed_path(root, tenant)
        t_existing = load_signals(tpath)
        t_merged = merge_signals(t_existing, cleaned)
        tdoc = write_store(
            tpath,
            t_merged,
            scope="tenant",
            extra={"tenant_hash": tenant_hash(tenant)},
        )

    # INDEX
    idx = root / GLOBAL_REL / "INDEX.md"
    idx.parent.mkdir(parents=True, exist_ok=True)
    top = merged[:12]
    lines = [
        "# Hub federated security signals (F77)",
        "",
        f"Updated: `{_now()}`",
        "",
        "Privacy-safe aggregate (theme / CWE / keywords / basenames / tenant_hash).",
        "No raw tenant names, paths under home, snippets, or secrets.",
        "",
        f"**Global signals:** {len(merged)}  ·  privacy_ok={gdoc.get('privacy_ok')}",
        "",
        "| Theme | Tenants | Hits | CWE |",
        "|-------|--------:|-----:|-----|",
    ]
    for s in top:
        lines.append(
            f"| `{s.get('theme')}` | {s.get('tenants') or 1} | {s.get('hits') or 1} | "
            f"{','.join(s.get('cwe') or []) or 'n/a'} |"
        )
    lines.append("")
    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "feature": FEATURE,
        "global_path": str(gpath),
        "global_count": len(merged),
        "privacy_ok": gdoc.get("privacy_ok"),
        "privacy_issues": gdoc.get("privacy_issues") or [],
        "tenant_path": str(tpath) if tpath else None,
        "tenant_count": (tdoc or {}).get("count") if tdoc else None,
        "index": str(idx),
        "top_themes": [s.get("theme") for s in top[:5]],
    }


def promote(
    root: Path,
    *,
    min_tenants: int | None = None,
    min_hits: int | None = None,
    dest: Path | None = None,
) -> dict[str, Any]:
    """Filter global signals by multi-tenant / hit thresholds."""
    min_t = min_tenants if min_tenants is not None else _int_env("TORII_FED_MIN_TENANTS", 2)
    min_h = min_hits if min_hits is not None else _int_env("TORII_FED_MIN_HITS", 2)
    gpath = global_fed_path(root)
    sigs = load_signals(gpath)
    promoted = [
        s
        for s in sigs
        if int(s.get("tenants") or 1) >= min_t and int(s.get("hits") or 1) >= min_h
    ]
    out = dest or (root / GLOBAL_REL / "promoted-signals.json")
    doc = write_store(
        out,
        promoted,
        scope="promoted",
        extra={"min_tenants": min_t, "min_hits": min_h, "source_count": len(sigs)},
    )
    return {
        "feature": FEATURE,
        "source_count": len(sigs),
        "promoted_count": len(promoted),
        "min_tenants": min_t,
        "min_hits": min_h,
        "path": str(out),
        "privacy_ok": doc.get("privacy_ok"),
        "themes": [s.get("theme") for s in promoted[:16]],
    }


def ingest_from_run(
    root: Path,
    run: dict[str, Any],
) -> dict[str, Any] | None:
    """Called from hub-ingest-run when payload carries federated_signals."""
    if not enabled():
        return None
    fed = run.get("federated_signals")
    signals: list[dict[str, Any]] = []
    if isinstance(fed, dict):
        signals = [x for x in (fed.get("signals") or []) if isinstance(x, dict)]
    elif isinstance(fed, list):
        signals = [x for x in fed if isinstance(x, dict)]
    if not signals:
        return None
    tenant = sanitize_tenant(
        run.get("tenant") if isinstance(run.get("tenant"), str) else None
    )
    source_repo = str(run.get("source_repo") or "")
    return ingest(
        root,
        signals,
        tenant=tenant,
        source_repo=source_repo,
        write_tenant=bool(tenant),
    )


def cmd_collect(args: argparse.Namespace) -> int:
    root = _root()
    paths = [Path(p) for p in (args.paths or [])]
    tenant = sanitize_tenant(args.tenant or None)
    signals = collect_from_paths(paths, tenant=tenant)
    if args.walk_tenants:
        signals = merge_signals(signals, collect_from_tenant_tree(root))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "count": len(signals),
                "signals": signals[:50],
            },
            indent=2,
        )
    )
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _root()
    tenant = sanitize_tenant(args.tenant or None)
    incoming: list[dict[str, Any]] = []
    if args.file:
        incoming.extend(collect_from_paths([Path(args.file)], tenant=tenant))
    if args.walk_tenants:
        incoming = merge_signals(incoming, collect_from_tenant_tree(root))
    if args.signals_json:
        data = json.loads(Path(args.signals_json).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            incoming.extend(data.get("signals") or [])
        elif isinstance(data, list):
            incoming.extend(data)
    result = ingest(
        root,
        incoming,
        tenant=tenant,
        source_repo=args.repo or "",
        write_tenant=bool(tenant) and not args.no_tenant_write,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("privacy_ok") else 1


def cmd_promote(args: argparse.Namespace) -> int:
    root = _root()
    result = promote(
        root,
        min_tenants=args.min_tenants,
        min_hits=args.min_hits,
        dest=Path(args.out) if args.out else None,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    gpath = global_fed_path(root)
    sigs = load_signals(gpath)
    multi = sum(1 for s in sigs if int(s.get("tenants") or 1) >= 2)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "global_path": str(gpath),
                "exists": gpath.is_file(),
                "count": len(sigs),
                "multi_tenant_themes": multi,
                "top": [
                    {
                        "theme": s.get("theme"),
                        "tenants": s.get("tenants"),
                        "hits": s.get("hits"),
                    }
                    for s in sigs[:8]
                ],
            },
            indent=2,
        )
    )
    return 0


def cmd_from_run(args: argparse.Namespace) -> int:
    root = _root()
    data = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    run = data.get("run") if isinstance(data, dict) and "run" in data else data
    if not isinstance(run, dict):
        print(json.dumps({"error": "invalid_payload"}))
        return 2
    result = ingest_from_run(root, run)
    print(json.dumps(result or {"skipped": True, "reason": "no_signals_or_disabled"}, indent=2))
    return 0 if result is None or result.get("privacy_ok") else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    """Two tenants contribute overlapping + unique themes; privacy holds."""
    import tempfile

    td = Path(tempfile.mkdtemp(prefix="torii-f77-"))
    # tenant A signals
    a_signals = [
        {
            "id": "sql_injection",
            "theme": "sql_injection",
            "cwe": ["CWE-89"],
            "keywords": ["sql injection", "cwe-89"],
            "path_basenames": ["app.py"],
            "hits": 3,
            "source": "tp_signature",
        },
        {
            "id": "xss",
            "theme": "xss",
            "cwe": ["CWE-79"],
            "keywords": ["xss", "reflected"],
            "path_basenames": ["routes.js"],
            "hits": 1,
            "source": "taint_prefilter",
        },
    ]
    # tenant B: overlap sqli + unique cmdi + poison attempt
    b_signals = [
        {
            "id": "sql_injection",
            "theme": "sql_injection",
            "cwe": ["CWE-89"],
            "keywords": ["sqli", "cwe-89"],
            "path_basenames": ["query.py"],
            "hits": 2,
            "source": "tp_signature",
        },
        {
            "id": "command_injection",
            "theme": "command_injection",
            "cwe": ["CWE-78"],
            "keywords": ["command injection", "child_process"],
            "path_basenames": ["routes.js"],
            "hits": 4,
            "source": "taint_prefilter",
        },
        {
            "id": "poison",
            "theme": "secrets_exposure",
            "keywords": ["/Users/evil/secret.key", "sk-or-v1-deadbeefdeadbeef"],
            "path_basenames": ["/Users/evil/app.py"],
            "hits": 99,
            "source": "attack",
            "snippet": "api_key=sk-or-v1-deadbeef",
        },
    ]
    r_a = ingest(td, a_signals, tenant="acme-alpha", source_repo="acme/a")
    r_b = ingest(td, b_signals, tenant="acme-beta", source_repo="acme/b")
    prom = promote(td, min_tenants=2, min_hits=1)
    g = load_signals(global_fed_path(td))
    sqli = next((s for s in g if s.get("theme") == "sql_injection"), None)
    poison = next((s for s in g if "poison" in str(s.get("id")) or s.get("theme") == "secrets_exposure"), None)
    # privacy: no /Users/ in store file
    raw = (td / GLOBAL_REL / FED_NAME).read_text(encoding="utf-8")
    privacy_file_ok = "/Users/" not in raw and "sk-or-v1" not in raw and "snippet" not in raw
    # multi-tenant: sqli should have tenants>=2
    multi_ok = bool(sqli and int(sqli.get("tenants") or 0) >= 2)
    # poison keywords stripped or theme dropped
    poison_ok = True
    if poison:
        for k in poison.get("keywords") or []:
            if "/Users/" in str(k) or "sk-or" in str(k):
                poison_ok = False
        for b in poison.get("path_basenames") or []:
            if "/" in str(b):
                poison_ok = False
    # promote only multi-tenant
    prom_themes = set(prom.get("themes") or [])
    promote_ok = "sql_injection" in prom_themes and "xss" not in prom_themes

    fixture_pass = (
        r_a.get("privacy_ok")
        and r_b.get("privacy_ok")
        and privacy_file_ok
        and multi_ok
        and poison_ok
        and promote_ok
        and int(prom.get("promoted_count") or 0) >= 1
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                "tmpdir": str(td),
                "global_count": len(g),
                "sqli_tenants": (sqli or {}).get("tenants"),
                "sqli_hits": (sqli or {}).get("hits"),
                "privacy_file_ok": privacy_file_ok,
                "multi_ok": multi_ok,
                "poison_ok": poison_ok,
                "promote_ok": promote_ok,
                "promoted": prom.get("themes"),
                "ingest_a": r_a,
                "ingest_b": {k: r_b[k] for k in ("global_count", "privacy_ok", "top_themes") if k in r_b},
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F77 cross-tenant hub federated ingest")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("collect", help="Collect privacy-safe signals")
    pc.add_argument("paths", nargs="*", default=[])
    pc.add_argument("--tenant", default="")
    pc.add_argument("--walk-tenants", action="store_true")
    pc.set_defaults(func=cmd_collect)

    pi = sub.add_parser("ingest", help="Merge into hub federation")
    pi.add_argument("--file", default="", help="federated-signals.json path")
    pi.add_argument("--signals-json", default="")
    pi.add_argument("--tenant", default="")
    pi.add_argument("--repo", default="")
    pi.add_argument("--walk-tenants", action="store_true")
    pi.add_argument("--no-tenant-write", action="store_true")
    pi.set_defaults(func=cmd_ingest)

    pp = sub.add_parser("promote", help="Filter by min tenants/hits")
    pp.add_argument("--min-tenants", type=int, default=None)
    pp.add_argument("--min-hits", type=int, default=None)
    pp.add_argument("--out", default="")
    pp.set_defaults(func=cmd_promote)

    sub.add_parser("status", help="Federation summary").set_defaults(func=cmd_status)

    pf = sub.add_parser("from-run", help="Ingest from hub-run payload JSON")
    pf.add_argument("--payload", required=True)
    pf.set_defaults(func=cmd_from_run)

    sub.add_parser("fixture", help="Offline two-tenant privacy fixture").set_defaults(
        func=cmd_fixture
    )

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
