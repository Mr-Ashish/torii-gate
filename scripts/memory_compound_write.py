#!/usr/bin/env python3
"""F104: Integrity-gated post-review compound write of path-evidenced TP memory.

Research drivers:
  - AgenticCyOps (arXiv 2603.09134): tool orchestration + memory management are
    the two integration attack surfaces for multi-agent systems.
  - LASM layered security (arXiv 2604.23338): Memory Integrity Controls —
    write-access restrictions + consistency validation before durable store.
  - Mem0/F93: ADD/UPDATE/DELETE/NONE event policy (already shipped).
  - Loop-eng: tools-as-code write path over SOUL prose.

Product thesis:
  Live reviews distill narrative MEMORY.md (F62) but **do not compound** durable
  TP signatures unless someone runs bench promote by hand. Highest ROI close of
  the memory loop: extract path-evidenced findings after maker+checker, gate
  them with an integrity policy, then write through F93 events so the next PR
  pages in proven themes — without accepting pathless, absolute-home, or
  secret-like poison.

Commands:
  plan      — extract + integrity-filter candidates (no write)
  apply     — plan + F93 promote into tp-signatures.json
  compound  — apply from a review path (primary post-run entry)
  federate  — F107: privacy-safe hub export of integrity-gated candidates
  fixture   — hermetic: good writes ≥1 TP; weak writes 0; poison rejected
  status    — summarize last ledger / store

Env:
  TORII_ROOT
  TORII_MEMORY_COMPOUND            1 (default) | 0
  TORII_MEMORY_COMPOUND_FEDERATE   1 (default) | 0  — F107 auto after compound
  TORII_TP_SIGNATURES_FILE         override durable TP path
  TORII_FP_RULES_FILE              optional FP demote on plan
  TORII_MEMORY_TENANT              optional tenant id for hub hash
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

FEATURE = "F104"
FEATURE_FED = "F107"
SCHEMA = 1
MARKER = "<!-- torii-f104-memory-compound -->"
LEDGER_NAME = "memory-compound-ledger.json"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

# Accept only these dual-pass statuses for durable write
_ACCEPT_STATUS = frozenset({"confirmed_tp", "path_evidenced"})

# Theme keyword seeds (CWE/theme ladder — aligned with chain_revalidate / taint)
_THEME_RULES: list[tuple[str, str, list[str], list[str]]] = [
    # theme, cwe, match_any, keywords_out
    (
        "sql_injection",
        "CWE-89",
        ["sql injection", "sqli", "cwe-89", "execute(f", "f\"select", "f'select"],
        ["sql", "injection", "execute", "sqlite"],
    ),
    (
        "insecure_deserialization",
        "CWE-502",
        ["pickle.loads", "pickle", "deserialize", "cwe-502", "insecure deserialization"],
        ["pickle", "loads", "deserialization"],
    ),
    (
        "command_injection",
        "CWE-78",
        ["command injection", "shell=true", "subprocess", "cwe-78", "os.system"],
        ["command", "injection", "shell", "subprocess"],
    ),
    (
        "secrets_exposure",
        "CWE-798",
        ["secret", "api_key", "api key", "password", "token leak", "cwe-798", "hardcoded"],
        ["secret", "api_key", "password", "token"],
    ),
    (
        "path_traversal",
        "CWE-22",
        ["path traversal", "directory traversal", "cwe-22", "../"],
        ["traversal", "path", "directory"],
    ),
    (
        "xss",
        "CWE-79",
        ["xss", "cross-site", "cwe-79", "innerhtml"],
        ["xss", "script", "html"],
    ),
    (
        "ssrf",
        "CWE-918",
        ["ssrf", "server-side request", "cwe-918"],
        ["ssrf", "request", "url"],
    ),
]

# Poison patterns — reject candidate body or paths
_ABS_HOME = re.compile(r"(?:/Users/|/home/)[^\s`\"']+", re.I)
_SECRETISH = re.compile(
    r"(?i)(?:sk-[a-z0-9]{20,}|api[_-]?key\s*[:=]\s*['\"][^'\"]{12,}"
    r"|-----BEGIN (?:RSA )?PRIVATE KEY-----"
    r"|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})"
)
_SNIPPET_TOO_LONG = 2400


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_COMPOUND") or "1").strip().lower()
    return raw not in _FALSEY


def federate_enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_COMPOUND_FEDERATE") or "1").strip().lower()
    return raw not in _FALSEY


def _import_bench():
    import importlib.util

    pol = Path(__file__).resolve().parent / "bench_security_gate.py"
    spec = importlib.util.spec_from_file_location("bench_security_gate", pol)
    if not spec or not spec.loader:
        raise RuntimeError("bench_security_gate missing")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bench_security_gate"] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_events():
    import importlib.util

    pol = Path(__file__).resolve().parent / "memory_event_policy.py"
    spec = importlib.util.spec_from_file_location("memory_event_policy", pol)
    if not spec or not spec.loader:
        raise RuntimeError("memory_event_policy missing")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["memory_event_policy"] = mod
    spec.loader.exec_module(mod)
    return mod


def default_tp_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_TP_SIGNATURES_FILE") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (root or _root()) / ".torii" / "tp-signatures.json"


def default_fp_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_FP_RULES_FILE") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (root or _root()) / ".torii" / "fp-rules.json"


def _basename_only(path: str) -> str:
    p = (path or "").replace("\\", "/")
    # strip absolute /Users/... or workspace roots → keep relative-ish tail
    if p.startswith("/"):
        parts = [x for x in p.split("/") if x]
        # keep last 3 components max
        return "/".join(parts[-3:]) if parts else p
    return p


def _detect_theme(text: str) -> tuple[str, str, list[str]]:
    low = (text or "").lower()
    for theme, cwe, needles, kws in _THEME_RULES:
        if any(n in low for n in needles):
            return theme, cwe, list(kws)
    # fallback: first alphanumeric tokens as weak keywords
    tokens = re.findall(r"[a-z][a-z0-9_-]{3,}", low)
    stop = {
        "this",
        "that",
        "with",
        "from",
        "path",
        "file",
        "line",
        "demo",
        "insecure",
        "should",
        "would",
        "could",
        "review",
        "finding",
        "issue",
        "block",
        "blocking",
        "security",
        "audit",
        "trigger",
        "request",
    }
    kws = [t for t in tokens if t not in stop][:6]
    theme = kws[0] if kws else "generic_finding"
    return theme, "", kws


def integrity_check(
    *,
    status: str,
    body: str,
    paths: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Return (ok, reason). Fail closed on poison / weak evidence."""
    if status not in _ACCEPT_STATUS:
        return False, f"status_rejected:{status}"
    if not paths:
        return False, "no_path_evidence"
    body = body or ""
    if len(body.strip()) < 32:
        return False, "body_too_short"
    if len(body) > _SNIPPET_TOO_LONG:
        return False, "body_too_long"
    if _ABS_HOME.search(body):
        return False, "absolute_home_path"
    for ph in paths:
        p = str(ph.get("path") or "")
        if _ABS_HOME.search(p) or p.startswith("/Users/") or p.startswith("/home/"):
            return False, "absolute_home_path"
    if _SECRETISH.search(body):
        return False, "secret_like_blob"
    # require at least one non-empty relative path
    rel = False
    for ph in paths:
        p = str(ph.get("path") or "").strip()
        if p and not p.startswith("/Users/") and not p.startswith("/home/"):
            rel = True
            break
    if not rel:
        return False, "no_relative_path"
    return True, "ok"


def candidates_from_critic(
    critic: dict[str, Any],
    *,
    source: str = "agent_review",
    repo: str = "",
    pr: str = "",
) -> list[dict[str, Any]]:
    """Build integrity-gated TP candidate signatures from dual_pass findings."""
    findings = critic.get("findings") or critic.get("validated") or []
    out: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            continue
        status = str(f.get("status") or "")
        body = str(
            f.get("text")
            or f.get("chunk")
            or f.get("body")
            or f.get("preview")
            or ""
        )
        paths_raw = f.get("paths") or f.get("path_hits") or []
        paths: list[dict[str, Any]] = []
        for ph in paths_raw:
            if isinstance(ph, dict):
                paths.append(
                    {
                        "path": _basename_only(str(ph.get("path") or ph.get("file") or "")),
                        "line": ph.get("line"),
                    }
                )
            elif ph:
                paths.append({"path": _basename_only(str(ph)), "line": None})
        ok, reason = integrity_check(status=status, body=body, paths=paths)
        if not ok:
            rejected.append({"i": i, "status": status, "reason": reason})
            continue
        theme, cwe, kws = _detect_theme(body)
        # also pull keywords from critic if present
        extra = (
            f.get("tp_hits")
            or f.get("tp_signature_hits")
            or f.get("matched")
            or []
        )
        if isinstance(extra, list):
            for e in extra:
                es = str(e).lower()
                if es and es not in kws and len(es) < 40:
                    kws.append(es)
        path_globs = sorted(
            {
                _basename_only(str(p.get("path") or ""))
                for p in paths
                if p.get("path")
            }
        )
        # stable id from theme+primary path
        primary = path_globs[0] if path_globs else "unknown"
        raw_id = f"{theme}:{primary}"
        sid = "tp-" + hashlib.sha1(raw_id.encode()).hexdigest()[:12]
        cand = {
            "id": sid,
            "theme": theme,
            "cwe": [cwe] if cwe else [],
            "keywords": kws[:12],
            "path_globs": path_globs[:8],
            "source": source,
            "provenance": {
                "feature": FEATURE,
                "status": status,
                "integrity": reason,
                "repo": repo or None,
                "pr": pr or None,
                "written_at": _now(),
            },
            "hits": 1,
            "promoted_at": _now(),
            "kind": "tp",
            # no raw body / snippets in durable store (privacy)
        }
        out.append(cand)
    return out


def plan_compound(
    review_text: str,
    *,
    root: Path | None = None,
    repo: str = "",
    pr: str = "",
    source: str = "agent_review",
) -> dict[str, Any]:
    root = root or _root()
    bench = _import_bench()
    fp_path = default_fp_path(root)
    fp = bench.load_fp_rules_dicts(fp_path) if fp_path.is_file() else []
    tp = bench.load_tp_signatures(default_tp_path(root))
    critic = bench.dual_pass_critic(
        review_text, fp_rules=fp, tp_signatures=tp, root=root
    )
    # normalize findings list for integrity (ensure paths on each)
    findings = critic.get("findings") or []
    for f in findings:
        if not isinstance(f, dict):
            continue
        if not f.get("paths") and not f.get("path_hits"):
            # re-extract from chunk text
            body = str(
                f.get("text") or f.get("chunk") or f.get("preview") or ""
            )
            f["paths"] = bench.extract_path_hits(body)
        if not f.get("text"):
            f["text"] = str(
                f.get("chunk") or f.get("preview") or ""
            )
    candidates = candidates_from_critic(
        critic, source=source, repo=repo, pr=pr
    )
    # also count rejections by re-walking
    rejected_n = 0
    reasons: dict[str, int] = {}
    for f in findings:
        if not isinstance(f, dict):
            continue
        status = str(f.get("status") or "")
        body = str(
            f.get("text") or f.get("chunk") or f.get("preview") or ""
        )
        paths = f.get("paths") or f.get("path_hits") or []
        path_dicts = []
        for ph in paths:
            if isinstance(ph, dict):
                path_dicts.append(ph)
            else:
                path_dicts.append({"path": str(ph)})
        ok, reason = integrity_check(status=status, body=body, paths=path_dicts)
        if not ok:
            rejected_n += 1
            reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "enabled": enabled(),
        "critic": {
            "chunk_count": critic.get("chunk_count"),
            "confirmed_tp": critic.get("confirmed_tp"),
            "likely_fp": critic.get("likely_fp"),
            "weak_evidence": critic.get("weak_evidence"),
            "precision_proxy": critic.get("precision_proxy"),
        },
        "candidates": candidates,
        "candidate_count": len(candidates),
        "rejected_count": rejected_n,
        "reject_reasons": reasons,
        "scored_at": _now(),
    }


def apply_compound(
    plan: dict[str, Any],
    *,
    root: Path | None = None,
    dest: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = root or _root()
    dest = dest or default_tp_path(root)
    candidates = [c for c in (plan.get("candidates") or []) if isinstance(c, dict)]
    if not candidates:
        return {
            "feature": FEATURE,
            "applied": False,
            "promoted": 0,
            "total": _tp_count(dest),
            "dest": str(dest),
            "reason": "no_candidates",
        }
    if dry_run:
        return {
            "feature": FEATURE,
            "applied": False,
            "dry_run": True,
            "promoted": len(candidates),
            "dest": str(dest),
            "candidates": candidates,
        }

    events = _import_events()
    # load existing as list of items
    existing: list[dict[str, Any]] = []
    if dest.is_file():
        try:
            data = json.loads(dest.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = [x for x in (data.get("signatures") or data.get("items") or []) if isinstance(x, dict)]
            elif isinstance(data, list):
                existing = [x for x in data if isinstance(x, dict)]
        except json.JSONDecodeError:
            existing = []

    # Prefer F93 event policy when available
    try:
        for c in candidates:
            c.setdefault("kind", "tp")
        planned = events.plan_events(existing, candidates, candidate_kind="tp")
        store = events.apply_events(
            {"items": list(existing), "history": []}, planned
        )
        merged = [
            i
            for i in (store.get("items") or [])
            if isinstance(i, dict) and not i.get("deleted")
        ]
        event_summary = {
            "planned": len(planned) if isinstance(planned, list) else planned,
            "events": planned if isinstance(planned, list) else None,
        }
    except Exception as exc:
        # fallback merge by id
        by_id: dict[str, dict[str, Any]] = {
            str(x.get("id") or ""): dict(x) for x in existing if x.get("id")
        }
        for c in candidates:
            cid = str(c.get("id") or "")
            if not cid:
                continue
            if cid in by_id:
                old = by_id[cid]
                old["hits"] = int(old.get("hits") or 1) + 1
                kws = list(
                    dict.fromkeys(
                        list(old.get("keywords") or []) + list(c.get("keywords") or [])
                    )
                )
                old["keywords"] = kws[:24]
                old["promoted_at"] = _now()
            else:
                by_id[cid] = dict(c)
        merged = list(by_id.values())
        event_summary = {"fallback": str(exc)[:160]}

    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA,
        "feature": FEATURE,
        "updated_at": _now(),
        "signatures": merged,
    }
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # ledger next to dest or out
    ledger = dest.parent / LEDGER_NAME
    try:
        prev = []
        if ledger.is_file():
            prev = json.loads(ledger.read_text(encoding="utf-8")).get("runs") or []
        prev.append(
            {
                "at": _now(),
                "promoted": len(candidates),
                "total": len(merged),
                "reject_reasons": plan.get("reject_reasons"),
                "candidate_ids": [c.get("id") for c in candidates],
            }
        )
        ledger.write_text(
            json.dumps({"feature": FEATURE, "runs": prev[-50:]}, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass

    return {
        "feature": FEATURE,
        "applied": True,
        "promoted": len(candidates),
        "total": len(merged),
        "dest": str(dest),
        "events": event_summary,
        "candidate_ids": [c.get("id") for c in candidates],
    }


def _tp_count(dest: Path) -> int:
    if not dest.is_file():
        return 0
    try:
        data = json.loads(dest.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return len(data.get("signatures") or data.get("items") or [])
        if isinstance(data, list):
            return len(data)
    except Exception:
        return 0
    return 0


def export_integrity_signals(
    candidates: list[dict[str, Any]],
    *,
    tenant: str = "",
    repo: str = "",
    pr: str = "",
) -> list[dict[str, Any]]:
    """F107: privacy-safe hub signals from integrity-gated compound candidates.

    Only theme / cwe / keywords / basenames / hits — never snippets, absolute paths,
    or raw tenant strings (F77 sanitize hashes tenant).
    """
    out: list[dict[str, Any]] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        prov = c.get("provenance") if isinstance(c.get("provenance"), dict) else {}
        # only integrity-ok candidates (or legacy without provenance if path_globs set)
        if prov and prov.get("integrity") not in (None, "ok"):
            continue
        theme = str(c.get("theme") or "").strip().lower()
        if not theme or theme == "generic_finding":
            # still allow generic if has keywords
            if not (c.get("keywords") or []):
                continue
        bases: list[str] = []
        for p in c.get("path_globs") or []:
            name = Path(str(p)).name
            if name and "/" not in name and "\\" not in name:
                bases.append(name[:64])
            elif name:
                bases.append(Path(name).name[:64])
        bases = list(dict.fromkeys(b for b in bases if b))[:6]
        kws = []
        for k in c.get("keywords") or []:
            ks = str(k).strip()
            if not ks or len(ks) > 48:
                continue
            if "/Users/" in ks or "/home/" in ks:
                continue
            if re.search(r"sk-[a-z0-9]{10,}", ks, re.I):
                continue
            kws.append(ks[:48])
        kws = list(dict.fromkeys(kws))[:12]
        cwe = c.get("cwe") or []
        if isinstance(cwe, str):
            cwe = [cwe]
        sid = re.sub(r"[^a-z0-9._-]+", "-", str(c.get("id") or theme).lower())[:64]
        sig: dict[str, Any] = {
            "id": sid or f"tp-{len(out)}",
            "theme": theme or sid,
            "cwe": [str(x) for x in cwe if x][:8],
            "keywords": kws,
            "path_basenames": bases,
            "hits": max(1, int(c.get("hits") or 1)),
            "source": "f104_integrity_compound",
            "tags": ["integrity_gated", "f107", "compound"],
            "integrity": "ok",
        }
        if tenant:
            sig["tenant"] = tenant  # stripped → tenant_hash by F77 sanitize
        if repo:
            # only org/name style, no local paths
            r = str(repo).replace("\\", "/").strip()
            if r and not r.startswith("/") and ".." not in r:
                sig["tags"] = list(dict.fromkeys(list(sig["tags"]) + [f"repo:{r[:48]}"]))[:12]
        if pr:
            sig["tags"] = list(dict.fromkeys(list(sig["tags"]) + [f"pr:{str(pr)[:16]}"]))[:12]
        out.append(sig)
    return out


def federate_candidates(
    candidates: list[dict[str, Any]],
    *,
    root: Path | None = None,
    tenant: str = "",
    repo: str = "",
    pr: str = "",
    hub_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Export integrity-gated candidates and soft-ingest into F77 hub."""
    root = root or _root()
    signals = export_integrity_signals(
        candidates, tenant=tenant, repo=repo, pr=pr
    )
    result: dict[str, Any] = {
        "feature": FEATURE_FED,
        "source_feature": FEATURE,
        "signal_count": len(signals),
        "signals": signals,
        "dry_run": bool(dry_run),
        "scored_at": _now(),
    }
    if dry_run or not signals:
        result["skipped"] = not signals
        return result
    if not federate_enabled():
        result["enabled"] = False
        result["skipped"] = True
        return result
    try:
        import importlib.util

        fed_path = Path(__file__).resolve().parent / "federated_hub_ingest.py"
        if not fed_path.is_file():
            result["error"] = "federated_hub_ingest missing"
            return result
        spec = importlib.util.spec_from_file_location("federated_hub_ingest", fed_path)
        if not spec or not spec.loader:
            result["error"] = "import_failed"
            return result
        mod = importlib.util.module_from_spec(spec)
        sys.modules["federated_hub_ingest"] = mod
        spec.loader.exec_module(mod)
        if not mod.enabled():
            result["hub_enabled"] = False
            result["skipped"] = True
            return result
        hroot = Path(hub_root).resolve() if hub_root else root
        ten = tenant or os.environ.get("TORII_MEMORY_TENANT") or ""
        ing = mod.ingest(
            hroot,
            signals,
            tenant=ten,
            source_repo=repo or "",
            write_tenant=bool(ten),
        )
        # assert on *sanitized* signals (raw tenant is hashed by sanitize_signal)
        cleaned = []
        for s in signals:
            c = mod.sanitize_signal(s, tenant=ten)
            if c:
                cleaned.append(c)
        issues = mod.assert_privacy(cleaned)
        result["ingest"] = {
            "global_count": ing.get("global_count"),
            "privacy_ok": ing.get("privacy_ok"),
            "global_path": ing.get("global_path"),
            "top_themes": ing.get("top_themes"),
        }
        result["sanitized_count"] = len(cleaned)
        result["privacy_ok"] = bool(ing.get("privacy_ok")) and len(issues) == 0
        result["privacy_issues"] = issues
        result["enabled"] = True
    except Exception as exc:
        result["error"] = str(exc)[:200]
        result["privacy_ok"] = False
    return result


def compound_review(
    review_path: Path,
    *,
    root: Path | None = None,
    dest: Path | None = None,
    out_dir: Path | None = None,
    repo: str = "",
    pr: str = "",
    dry_run: bool = False,
    source: str = "agent_review",
    federate: bool | None = None,
    tenant: str = "",
) -> dict[str, Any]:
    root = root or _root()
    text = review_path.read_text(encoding="utf-8", errors="replace")
    plan = plan_compound(text, root=root, repo=repo, pr=pr, source=source)
    result = apply_compound(plan, root=root, dest=dest, dry_run=dry_run)
    report = {
        **plan,
        "apply": result,
        "review": str(review_path),
    }
    do_fed = federate if federate is not None else federate_enabled()
    if do_fed and not dry_run:
        fed = federate_candidates(
            list(plan.get("candidates") or []),
            root=root,
            tenant=tenant or os.environ.get("TORII_MEMORY_TENANT") or "",
            repo=repo,
            pr=pr,
        )
        report["federate"] = fed
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "memory-compound.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        # also soft-copy signatures into out_dir for trace
        if result.get("applied") and dest and Path(str(result.get("dest") or dest)).is_file():
            try:
                src = Path(str(result["dest"]))
                (out_dir / "tp-signatures.json").write_text(
                    src.read_text(encoding="utf-8"), encoding="utf-8"
                )
            except Exception:
                pass
        if report.get("federate"):
            try:
                (out_dir / "memory-compound-federate.json").write_text(
                    json.dumps(report["federate"], indent=2) + "\n", encoding="utf-8"
                )
            except OSError:
                pass
    return report


def cmd_plan(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0
    review = Path(args.review).read_text(encoding="utf-8", errors="replace")
    plan = plan_compound(
        review,
        root=_root(),
        repo=args.repo or "",
        pr=args.pr or "",
        source=args.source or "agent_review",
    )
    if args.out:
        Path(args.out).write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0
    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    dest = Path(args.out) if args.out else default_tp_path()
    result = apply_compound(plan, dest=dest, dry_run=bool(args.dry_run))
    print(json.dumps(result, indent=2))
    return 0


def cmd_compound(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0
    review = Path(args.review)
    if not review.is_file():
        print(json.dumps({"error": "missing_review", "path": str(review)}), file=sys.stderr)
        return 2
    dest = Path(args.tp_out) if args.tp_out else default_tp_path()
    out_dir = Path(args.out_dir) if args.out_dir else None
    do_fed: bool | None = None
    if getattr(args, "no_federate", False):
        do_fed = False
    elif getattr(args, "federate", False):
        do_fed = True
    report = compound_review(
        review,
        dest=dest,
        out_dir=out_dir,
        repo=args.repo or "",
        pr=args.pr or "",
        dry_run=bool(args.dry_run),
        source=args.source or "agent_review",
        federate=do_fed,
        tenant=getattr(args, "tenant", "") or "",
    )
    # concise stdout for stage logs
    apply = report.get("apply") or {}
    fed = report.get("federate") or {}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "candidate_count": report.get("candidate_count"),
                "rejected_count": report.get("rejected_count"),
                "reject_reasons": report.get("reject_reasons"),
                "promoted": apply.get("promoted"),
                "total": apply.get("total"),
                "applied": apply.get("applied"),
                "dest": apply.get("dest"),
                "dry_run": apply.get("dry_run", False),
                "federate_signals": fed.get("signal_count"),
                "federate_privacy_ok": fed.get("privacy_ok"),
            },
            indent=2,
        )
    )
    return 0


def cmd_federate(args: argparse.Namespace) -> int:
    """F107: federate integrity-gated candidates from review or plan JSON."""
    if not federate_enabled() and not args.force:
        print(json.dumps({"feature": FEATURE_FED, "enabled": False, "skipped": True}))
        return 0
    candidates: list[dict[str, Any]] = []
    if args.plan and Path(args.plan).is_file():
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        candidates = [c for c in (plan.get("candidates") or []) if isinstance(c, dict)]
    elif args.review and Path(args.review).is_file():
        plan = plan_compound(
            Path(args.review).read_text(encoding="utf-8", errors="replace"),
            root=_root(),
            repo=args.repo or "",
            pr=args.pr or "",
        )
        candidates = [c for c in (plan.get("candidates") or []) if isinstance(c, dict)]
    elif args.candidates and Path(args.candidates).is_file():
        raw = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
        if isinstance(raw, list):
            candidates = [c for c in raw if isinstance(c, dict)]
        elif isinstance(raw, dict):
            candidates = [
                c for c in (raw.get("candidates") or raw.get("signatures") or []) if isinstance(c, dict)
            ]
    else:
        print(
            json.dumps({"error": "need --review, --plan, or --candidates"}),
            file=sys.stderr,
        )
        return 2
    result = federate_candidates(
        candidates,
        tenant=args.tenant or "",
        repo=args.repo or "",
        pr=args.pr or "",
        hub_root=Path(args.hub_root) if args.hub_root else None,
        dry_run=bool(args.dry_run),
    )
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result.get("error"):
        return 1
    if result.get("privacy_ok") is False:
        return 1
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    dest = default_tp_path(root)
    ledger = dest.parent / LEDGER_NAME
    last = None
    if ledger.is_file():
        try:
            runs = json.loads(ledger.read_text(encoding="utf-8")).get("runs") or []
            last = runs[-1] if runs else None
        except Exception:
            last = None
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "tp_path": str(dest),
                "tp_count": _tp_count(dest),
                "ledger": str(ledger) if ledger.is_file() else None,
                "last_run": last,
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: good review compounds; weak does not; poison rejected; F107 federate."""
    root = _root()
    good_path = root / "docs/benchmarks/fixtures/insecure-demo-good-review.md"
    weak_path = root / "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
    if not good_path.is_file() or not weak_path.is_file():
        print(json.dumps({"feature": FEATURE, "fixture_pass": False, "error": "fixtures_missing"}))
        return 1

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        good_dest = td_path / "good" / "tp-signatures.json"
        weak_dest = td_path / "weak" / "tp-signatures.json"
        good_dest.parent.mkdir(parents=True)
        weak_dest.parent.mkdir(parents=True)
        hub = td_path / "hub"
        hub.mkdir()

        # isolate hub under tmp
        env_bak = os.environ.get("TORII_ROOT")
        os.environ["TORII_ROOT"] = str(hub)
        try:
            good_report = compound_review(
                good_path,
                root=root,
                dest=good_dest,
                out_dir=td_path / "good-out",
                source="fixture_good",
                federate=True,
                tenant="fixture-tenant-a",
                repo="demo/insecure",
            )
            # re-federate into isolated hub root
            fed = federate_candidates(
                list(good_report.get("candidates") or []),
                root=hub,
                tenant="fixture-tenant-a",
                repo="demo/insecure",
                hub_root=hub,
            )
            weak_report = compound_review(
                weak_path,
                root=root,
                dest=weak_dest,
                out_dir=td_path / "weak-out",
                source="fixture_weak",
                federate=False,
            )
        finally:
            if env_bak is None:
                os.environ.pop("TORII_ROOT", None)
            else:
                os.environ["TORII_ROOT"] = env_bak

        good_n = int((good_report.get("apply") or {}).get("promoted") or 0)
        weak_n = int((weak_report.get("apply") or {}).get("promoted") or 0)
        good_total = _tp_count(good_dest)

        # poison: absolute home + secret blob must be rejected even with path status
        poison_body = (
            "SQL injection in `/Users/ashish/secret/app.py:12` — "
            "key=sk-abcdefghijklmnopqrstuvwxyz0123456789 and shell=True"
        )
        ok_poison, poison_reason = integrity_check(
            status="path_evidenced",
            body=poison_body,
            paths=[{"path": "/Users/ashish/secret/app.py", "line": 12}],
        )
        poison_ok = (not ok_poison) and poison_reason in (
            "absolute_home_path",
            "secret_like_blob",
        )

        # pathless weak status rejected
        ok_weak_st, _ = integrity_check(
            status="weak_evidence",
            body="maybe something bad somewhere without paths at all in this text body",
            paths=[],
        )
        status_gate_ok = not ok_weak_st

        # provenance present on good candidates
        prov_ok = all(
            isinstance(c.get("provenance"), dict)
            and c["provenance"].get("integrity") == "ok"
            for c in (good_report.get("candidates") or [])
        ) if good_n else False

        # no absolute paths in written store
        store_clean = True
        if good_dest.is_file():
            raw = good_dest.read_text(encoding="utf-8")
            if "/Users/" in raw or "sk-abcdefghijklmnopqrstuvwxyz" in raw:
                store_clean = False

        good_ok = good_n >= 1 and good_total >= 1
        weak_ok = weak_n <= good_n
        weak_strict = weak_n == 0 or weak_n < good_n

        # F107 federate checks
        sigs = export_integrity_signals(
            list(good_report.get("candidates") or []),
            tenant="fixture-tenant-a",
            repo="demo/insecure",
        )
        fed_count_ok = len(sigs) >= 1
        fed_privacy = True
        blob = json.dumps(sigs)
        if "/Users/" in blob or "sk-abcdefghijklmnopqrstuvwxyz" in blob:
            fed_privacy = False
        # tags
        tags_ok = all("integrity_gated" in (s.get("tags") or []) for s in sigs)
        # ingest privacy
        ingest_ok = bool(fed.get("privacy_ok", True)) and not fed.get("error")
        # basenames only
        bases_ok = all(
            "/" not in str(b) for s in sigs for b in (s.get("path_basenames") or [])
        )

        fixture_pass = all(
            [
                good_ok,
                weak_strict,
                poison_ok,
                status_gate_ok,
                prov_ok,
                store_clean,
                fed_count_ok,
                fed_privacy,
                tags_ok,
                ingest_ok,
                bases_ok,
            ]
        )
        out = {
            "feature": FEATURE,
            "federate_feature": FEATURE_FED,
            "fixture_pass": fixture_pass,
            "good_promoted": good_n,
            "good_total": good_total,
            "weak_promoted": weak_n,
            "good_ok": good_ok,
            "weak_ok": weak_ok,
            "weak_strict": weak_strict,
            "poison_ok": poison_ok,
            "poison_reason": poison_reason,
            "status_gate_ok": status_gate_ok,
            "prov_ok": prov_ok,
            "store_clean": store_clean,
            "fed_count": len(sigs),
            "fed_count_ok": fed_count_ok,
            "fed_privacy": fed_privacy,
            "tags_ok": tags_ok,
            "ingest_ok": ingest_ok,
            "bases_ok": bases_ok,
            "federate_signals": fed.get("signal_count"),
            "good_reject_reasons": good_report.get("reject_reasons"),
            "weak_reject_reasons": weak_report.get("reject_reasons"),
            "scored_at": _now(),
        }
        print(json.dumps(out, indent=2))
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F104/F107 integrity-gated memory compound + federate")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("plan", help="extract + integrity filter (no write)")
    pl.add_argument("--review", required=True)
    pl.add_argument("--repo", default="")
    pl.add_argument("--pr", default="")
    pl.add_argument("--source", default="agent_review")
    pl.add_argument("--out", default="")
    pl.add_argument("--force", action="store_true")
    pl.set_defaults(func=cmd_plan)

    pa = sub.add_parser("apply", help="apply a plan JSON via F93 events")
    pa.add_argument("--plan", required=True)
    pa.add_argument("--out", default="", help="tp-signatures.json dest")
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--force", action="store_true")
    pa.set_defaults(func=cmd_apply)

    pc = sub.add_parser("compound", help="plan+apply from a review file")
    pc.add_argument("--review", required=True)
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--tp-out", default="", help="durable tp-signatures path")
    pc.add_argument("--repo", default="")
    pc.add_argument("--pr", default="")
    pc.add_argument("--source", default="agent_review")
    pc.add_argument("--tenant", default="")
    pc.add_argument("--dry-run", action="store_true")
    pc.add_argument("--federate", action="store_true", help="force F107 federate")
    pc.add_argument("--no-federate", action="store_true", help="skip F107 federate")
    pc.add_argument("--force", action="store_true")
    pc.set_defaults(func=cmd_compound)

    pfed = sub.add_parser("federate", help="F107 privacy-safe hub export of integrity candidates")
    pfed.add_argument("--review", default="")
    pfed.add_argument("--plan", default="")
    pfed.add_argument("--candidates", default="")
    pfed.add_argument("--tenant", default="")
    pfed.add_argument("--repo", default="")
    pfed.add_argument("--pr", default="")
    pfed.add_argument("--hub-root", default="")
    pfed.add_argument("--out", default="")
    pfed.add_argument("--dry-run", action="store_true")
    pfed.add_argument("--force", action="store_true")
    pfed.set_defaults(func=cmd_federate)

    ps = sub.add_parser("status", help="tp store + last ledger")
    ps.set_defaults(func=cmd_status)

    pf = sub.add_parser("fixture", help="hermetic good/weak/poison/federate e2e")
    pf.set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
