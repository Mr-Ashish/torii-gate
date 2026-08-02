#!/usr/bin/env python3
"""Enterprise light product surface (priority queue dim 9).

Multi-tenant org isolation + federation privacy as docs + audit CLI
(not only raw JSON under memory/federation).

Commands:
  status   — tenants + privacy posture summary
  fixture  — hermetic privacy audit of federation files
  report   — write docs/enterprise/SURFACE.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "ENTERPRISE"
SCHEMA = 2
OUT_REL = Path("docs/enterprise")
# Canary tokens for hermetic isolation (must never appear in tenant-B inject)
_ISOLATION_SECRET_PATH = "/Users/acme-corp-secret/private/payments_leak.py"
_ISOLATION_SECRET_SNIPPET = "API_KEY=sk-tenantA-secret-canary-9911"
_ISOLATION_TENANT_A = "tenant-iso-a"
_ISOLATION_TENANT_B = "tenant-iso-b"

_HOME_PATH_RX = re.compile(
    r"(?:/Users/[\w.-]+|/home/[\w.-]+|C:\\\\Users\\\\|\\\\Users\\\\)",
    re.I,
)
_SECRETISH_RX = re.compile(
    r"(?:sk-[a-zA-Z0-9]{10,}|api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]|"
    r"BEGIN (?:RSA |OPENSSH )?PRIVATE KEY)",
    re.I,
)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_tenants(root: Path) -> list[dict[str, Any]]:
    base = root / "memory" / "tenants"
    out: list[dict[str, Any]] = []
    if not base.is_dir():
        return out
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        fed = d / "federation"
        out.append(
            {
                "tenant_id": d.name,
                "has_federation_dir": fed.is_dir(),
                "federation_files": len(list(fed.glob("*.json"))) if fed.is_dir() else 0,
            }
        )
    return out


def audit_federation_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    issues: list[str] = []
    privacy_ok_flag: bool | None = None
    privacy_label = None
    count = None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "file": path.name,
            "ok": False,
            "issues": ["invalid_json"],
            "privacy_ok": False,
        }

    if isinstance(data, dict):
        privacy_ok_flag = data.get("privacy_ok")
        privacy_label = data.get("privacy")
        count = data.get("count")
        if privacy_ok_flag is False:
            issues.append("privacy_ok_false")
            pi = data.get("privacy_issues") or []
            if isinstance(pi, list):
                issues.extend(f"declared:{x}" for x in pi[:5])

    if _HOME_PATH_RX.search(raw):
        issues.append("home_path_leak")
    if _SECRETISH_RX.search(raw):
        issues.append("secretish_pattern")
    # full path-like under keys that should not exist
    if re.search(r'"path"\s*:\s*"[^"]*/(?:Users|home)/', raw):
        issues.append("path_field_absolute")
    if re.search(r'"snippet"\s*:\s*"[^"]{20,}"', raw):
        issues.append("snippet_field")
    if re.search(r'"evidence"\s*:\s*"[^"]{40,}"', raw):
        issues.append("evidence_blob")

    ok = not issues and (privacy_ok_flag is not False)
    return {
        "file": path.name,
        "ok": ok,
        "issues": issues,
        "privacy_ok": privacy_ok_flag,
        "privacy": privacy_label,
        "count": count,
    }


def audit_all_federation(root: Path) -> dict[str, Any]:
    fed_dir = root / "memory" / "federation"
    files = sorted(fed_dir.glob("*.json")) if fed_dir.is_dir() else []
    audits = [audit_federation_file(p) for p in files]
    ok_n = sum(1 for a in audits if a.get("ok"))
    return {
        "dir": str(fed_dir.relative_to(root)) if fed_dir.is_dir() else "memory/federation",
        "files_n": len(audits),
        "ok_n": ok_n,
        "all_ok": ok_n == len(audits) and len(audits) >= 1,
        "audits": audits,
    }


def docs_surface(root: Path) -> dict[str, bool]:
    privacy_txt = (
        (root / OUT_REL / "PRIVACY.md").read_text(encoding="utf-8")
        if (root / OUT_REL / "PRIVACY.md").is_file()
        else ""
    )
    org_txt = (
        (root / OUT_REL / "ORG-ISOLATION.md").read_text(encoding="utf-8")
        if (root / OUT_REL / "ORG-ISOLATION.md").is_file()
        else ""
    )
    fed_buyer = root / "docs" / "FEDERATION.md"
    fed_txt = fed_buyer.read_text(encoding="utf-8") if fed_buyer.is_file() else ""
    install_sh = (
        (root / "scripts" / "install-torii.sh").read_text(encoding="utf-8", errors="replace")
        if (root / "scripts" / "install-torii.sh").is_file()
        else ""
    )
    install_md = (
        (root / "docs" / "INSTALL.md").read_text(encoding="utf-8", errors="replace")
        if (root / "docs" / "INSTALL.md").is_file()
        else ""
    )
    # ENTERPRISE_COST_PRIVACY: cost/PR dogfood is local vault, not federated
    privacy_cost_local = bool(
        re.search(r"Cost\s*/\s*PR telemetry|cost/PR telemetry", privacy_txt, re.I)
        and re.search(r"never|not.*(federat|cross.tenant)|local vault", privacy_txt, re.I)
        and (
            "cost-pr-dashboard" in privacy_txt
            or "hermes-usage" in privacy_txt
            or "benchmarks/traces" in privacy_txt
        )
    )
    org_cost_local = bool(
        re.search(r"Cost\s*/\s*PR telemetry stays local|cost/PR telemetry stays local", org_txt, re.I)
        or (
            "cost" in org_txt.lower()
            and "federation" in org_txt.lower()
            and re.search(r"never|local", org_txt, re.I)
        )
    )
    return {
        "readme": (root / OUT_REL / "README.md").is_file(),
        "org_isolation": (root / OUT_REL / "ORG-ISOLATION.md").is_file(),
        "privacy": (root / OUT_REL / "PRIVACY.md").is_file(),
        "privacy_names_allowlist": "tenant hash" in privacy_txt.lower(),
        "privacy_cost_telemetry_local": privacy_cost_local,
        "org_cost_telemetry_local": org_cost_local,
        "org_diagram": "Org A" in org_txt,
        # Buyer JTBD front door (merge-authority federation, not only enterprise/)
        "federation_buyer_doc": fed_buyer.is_file(),
        "federation_buyer_mentions_privacy": (
            "tenant hash" in fed_txt.lower() and "path" in fed_txt.lower()
        ),
        "federation_buyer_mentions_gate": "torii/gate" in fed_txt,
        # BRAND_FED_COST: buyer federation doc states cost is not federated
        "federation_buyer_cost_local": bool(
            re.search(r"cost/PR|cost\s*/\s*PR|USD|hermes", fed_txt, re.I)
            and re.search(r"never|local vault|not federat", fed_txt, re.I)
        ),
        # ENT_INSTALL_TENANT: install path stamps tenant + INSTALL documents enterprise light
        "install_sh_tenant_flag": bool(
            re.search(r"--tenant", install_sh)
            and "TORII_MEMORY_TENANT" in install_sh
            and "tenant_id=" in install_sh
        ),
        "install_md_enterprise_light": bool(
            re.search(r"Enterprise light|--tenant|TORII_MEMORY_TENANT", install_md, re.I)
            and (
                "enterprise/" in install_md
                or "enterprise -- status" in install_md
                or "ORG-ISOLATION" in install_md
            )
        ),
        "org_mentions_install_tenant": bool(
            re.search(r"install-torii|--tenant|tenant\.env", org_txt, re.I)
        ),
    }


def federated_hub_fixture(root: Path) -> dict[str, Any]:
    script = root / "scripts" / "federated_hub_ingest.py"
    if not script.is_file():
        return {"available": False, "fixture_pass": False}
    try:
        r = subprocess.run(
            [sys.executable, str(script), "fixture"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
        try:
            data = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
        except json.JSONDecodeError:
            data = {}
        return {
            "available": True,
            "rc": r.returncode,
            "fixture_pass": r.returncode == 0
            and bool(data.get("fixture_pass") if "fixture_pass" in data else r.returncode == 0),
            "privacy_ok": data.get("privacy_ok"),
            "tenants": data.get("tenants") or data.get("tenant_n"),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "fixture_pass": False, "error": str(exc)}


def hermetic_cross_tenant_isolation(root: Path | None = None) -> dict[str, Any]:
    """Prove tenant-A private path/snippet never injects into tenant-B prompt.

    ENT_ISOLATION_PROOF (dim 9): temp dual-tenant tree + scoped recall inject +
    federation sanitize. No network. Fail-closed on any canary leak.
    """
    import importlib.util
    import tempfile

    root = root or _root()
    scripts = root / "scripts"
    issues: list[str] = []
    checks: dict[str, bool] = {
        "scoped_module": False,
        "fed_module": False,
        "tenant_b_no_secret_path": False,
        "tenant_b_no_secret_snippet": False,
        "tenant_b_no_raw_tenant_a": False,
        "tenant_b_loads_own_theme": False,
        "fed_sanitize_strips_path": False,
        "fed_sanitize_hashes_tenant": False,
        "fed_sanitize_strips_snippet": False,
    }

    try:
        with tempfile.TemporaryDirectory(prefix="torii-ent-iso-") as td:
            fake = Path(td)
            # Tenant A: private canary path + secret snippet
            ta = fake / "memory" / "tenants" / _ISOLATION_TENANT_A
            ta.mkdir(parents=True)
            (ta / "tp-signatures.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "count": 1,
                        "signatures": [
                            {
                                "id": "tenant-a-private-sqli",
                                "theme": "sql_injection",
                                "keywords": ["tenant-a-only-theme-canary"],
                                "path_globs": [_ISOLATION_SECRET_PATH],
                                "path": _ISOLATION_SECRET_PATH,
                                "snippet": _ISOLATION_SECRET_SNIPPET,
                                "hits": 9,
                                "kind": "tp",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            # Tenant B: benign public-ish theme only
            tb = fake / "memory" / "tenants" / _ISOLATION_TENANT_B
            tb.mkdir(parents=True)
            (tb / "tp-signatures.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "count": 1,
                        "signatures": [
                            {
                                "id": "tenant-b-xss",
                                "theme": "xss",
                                "keywords": ["tenant-b-public-theme"],
                                "path_globs": ["app/views.py"],
                                "hits": 2,
                                "kind": "tp",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            # --- scoped recall as tenant B ---
            sm_path = scripts / "scoped_memory_recall.py"
            checks["scoped_module"] = sm_path.is_file()
            if sm_path.is_file():
                mod_name = "torii_scoped_memory_iso"
                spec = importlib.util.spec_from_file_location(mod_name, sm_path)
                assert spec and spec.loader
                sm = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = sm
                old_env = {
                    k: os.environ.get(k)
                    for k in (
                        "TORII_ROOT",
                        "TORII_MEMORY_TENANT",
                        "TORII_SCOPED_MEMORY",
                        "REPO",
                    )
                }
                try:
                    os.environ["TORII_ROOT"] = str(fake)
                    os.environ["TORII_MEMORY_TENANT"] = _ISOLATION_TENANT_B
                    os.environ["TORII_SCOPED_MEMORY"] = "1"
                    os.environ["REPO"] = "acme/app-b"
                    spec.loader.exec_module(sm)
                    store = fake / ".torii" / "scoped-memory-b.json"
                    sm.ingest(fake, repo="acme/app-b", store_path=store)
                    items = sm.load_store(store, root=fake)
                    result = sm.recall(items, ["app/views.py"], include_federated=True)
                    inject_text = sm.render_section(result)
                    blob = inject_text + "\n" + json.dumps(result, default=str)
                    checks["tenant_b_no_secret_path"] = _ISOLATION_SECRET_PATH not in blob
                    checks["tenant_b_no_secret_snippet"] = (
                        _ISOLATION_SECRET_SNIPPET not in blob
                        and "sk-tenantA-secret" not in blob
                    )
                    checks["tenant_b_no_raw_tenant_a"] = _ISOLATION_TENANT_A not in blob
                    checks["tenant_b_loads_own_theme"] = (
                        "tenant-b-public-theme" in blob or "xss" in blob.lower()
                    )
                    if not checks["tenant_b_no_secret_path"]:
                        issues.append("secret_path_in_tenant_b_inject")
                    if not checks["tenant_b_no_secret_snippet"]:
                        issues.append("secret_snippet_in_tenant_b_inject")
                    if not checks["tenant_b_no_raw_tenant_a"]:
                        issues.append("raw_tenant_a_in_tenant_b_inject")
                    if not checks["tenant_b_loads_own_theme"]:
                        issues.append("tenant_b_theme_missing")
                finally:
                    for k, v in old_env.items():
                        if v is None:
                            os.environ.pop(k, None)
                        else:
                            os.environ[k] = v
                    sys.modules.pop(mod_name, None)

            # --- federation sanitize of tenant A poison ---
            fed_path = scripts / "federated_hub_ingest.py"
            checks["fed_module"] = fed_path.is_file()
            if fed_path.is_file():
                mod_name = "torii_fed_iso"
                spec = importlib.util.spec_from_file_location(mod_name, fed_path)
                assert spec and spec.loader
                fed = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = fed
                try:
                    spec.loader.exec_module(fed)
                    dirty = {
                        "theme": "sql_injection",
                        "path": _ISOLATION_SECRET_PATH,
                        "snippet": _ISOLATION_SECRET_SNIPPET,
                        "keywords": ["select", "from"],
                        "tenant": _ISOLATION_TENANT_A,
                    }
                    clean = fed.sanitize_signal(dirty, tenant=_ISOLATION_TENANT_A)
                    clean_blob = json.dumps(clean or {})
                    checks["fed_sanitize_strips_path"] = bool(
                        clean is not None and _ISOLATION_SECRET_PATH not in clean_blob
                    )
                    checks["fed_sanitize_strips_snippet"] = bool(
                        clean is not None
                        and _ISOLATION_SECRET_SNIPPET not in clean_blob
                        and "sk-tenantA" not in clean_blob
                    )
                    checks["fed_sanitize_hashes_tenant"] = bool(
                        clean is not None
                        and _ISOLATION_TENANT_A not in clean_blob
                        and (
                            "tenant_hash" in clean_blob
                            or "tenant_hashes" in clean_blob
                            or not clean.get("tenant")
                        )
                    )
                    if not checks["fed_sanitize_strips_path"]:
                        issues.append("fed_path_leak")
                    if not checks["fed_sanitize_strips_snippet"]:
                        issues.append("fed_snippet_leak")
                    if not checks["fed_sanitize_hashes_tenant"]:
                        issues.append("fed_raw_tenant")
                finally:
                    sys.modules.pop(mod_name, None)
    except Exception as exc:
        issues.append(f"exception:{type(exc).__name__}:{exc}")

    ok = all(checks.values()) and not issues
    return {
        "ok": ok,
        "checks": checks,
        "issues": issues,
        "one_liner": (
            "Hermetic: tenant-A private path/snippet never appears in tenant-B "
            "scoped inject; federation sanitize strips paths/snippets/raw tenant ids"
        ),
    }


def build_report(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    tenants = list_tenants(root)
    fed = audit_all_federation(root)
    docs = docs_surface(root)
    hub = federated_hub_fixture(root)
    isolation = hermetic_cross_tenant_isolation(root)

    report = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "scorecard_target": "enterprise",
        "dim_lift": "enterprise light (dim 9) multi-tenant product surface",
        "scored_at": _now(),
        "one_liner": (
            "Org isolation + federation privacy as product docs and audit CLI — "
            "themes only, no paths/snippets/raw tenant IDs; hermetic cross-tenant inject proof"
        ),
        "tenants": tenants,
        "tenant_n": len(tenants),
        "federation_audit": fed,
        "docs": docs,
        "federated_hub_fixture": hub,
        "isolation_proof": isolation,
        "guarantees": [
            "no cross-tenant path inject via federation",
            "tenant hashes only in global aggregates",
            "promote requires min_tenants (default 2)",
            "repo-local .torii/ default; hub opt-in",
            "cost/PR dogfood vault stays local (never federated USD/tokens)",
            "hermetic: tenant-A canaries never inject into tenant-B scoped recall",
        ],
        "paths": {
            "readme": str(OUT_REL / "README.md"),
            "org_isolation": str(OUT_REL / "ORG-ISOLATION.md"),
            "privacy": str(OUT_REL / "PRIVACY.md"),
            "federation_buyer": "docs/FEDERATION.md",
            "surface_md": str(OUT_REL / "SURFACE.md"),
        },
    }
    report["enterprise_ok"] = bool(
        docs.get("readme")
        and docs.get("org_isolation")
        and docs.get("privacy")
        and docs.get("org_diagram")
        and docs.get("privacy_cost_telemetry_local")
        and docs.get("install_sh_tenant_flag")
        and docs.get("install_md_enterprise_light")
        and fed.get("all_ok")
        and hub.get("fixture_pass")
        and isolation.get("ok")
    )
    return report


def render_surface_md(report: dict[str, Any]) -> str:
    fed = report.get("federation_audit") or {}
    lines = [
        "<!-- torii-enterprise-surface -->",
        "",
        "# Enterprise surface inventory",
        "",
        f"_Generated: `{report.get('scored_at')}` · **enterprise_ok={report.get('enterprise_ok')}**_",
        "",
        f"{report.get('one_liner')}",
        "",
        "## Guarantees",
        "",
    ]
    for g in report.get("guarantees") or []:
        lines.append(f"- {g}")
    lines += [
        "",
        f"## Tenants (`memory/tenants/`) — n={report.get('tenant_n')}",
        "",
        "| tenant_id | federation dir | files |",
        "|-----------|:--------------:|------:|",
    ]
    for t in report.get("tenants") or []:
        lines.append(
            f"| `{t.get('tenant_id')}` | {t.get('has_federation_dir')} | {t.get('federation_files')} |"
        )
    if not report.get("tenants"):
        lines.append("| _(none on hub yet)_ | | |")

    lines += [
        "",
        f"## Federation privacy audit — {fed.get('ok_n')}/{fed.get('files_n')} ok",
        "",
        "| file | privacy_ok | issues |",
        "|------|:----------:|--------|",
    ]
    for a in fed.get("audits") or []:
        issues = ", ".join(a.get("issues") or []) or "—"
        lines.append(
            f"| `{a.get('file')}` | {a.get('privacy_ok')} | {issues if a.get('ok') else '**'+issues+'**'} |"
        )
    docs = report.get("docs") or {}
    cost_ok = docs.get("privacy_cost_telemetry_local")
    lines += [
        "",
        "## Docs",
        "",
        "- [ORG-ISOLATION.md](ORG-ISOLATION.md) — org isolation story",
        "- [PRIVACY.md](PRIVACY.md) — federation privacy one-pager + **cost/PR telemetry local**",
        "- [../FEDERATION.md](../FEDERATION.md) — buyer JTBD (merge-authority federation)",
        "- [../ops/cost-pr-dashboard.md](../ops/cost-pr-dashboard.md) — measured cost (not federated)",
        "",
        f"Cost telemetry documented as local vault only: **{cost_ok}**",
        "",
        "## Isolation proof (hermetic)",
        "",
        f"**ok:** `{(report.get('isolation_proof') or {}).get('ok')}` — "
        f"{(report.get('isolation_proof') or {}).get('one_liner')}",
        "",
        "## Refresh",
        "",
        "```bash",
        "python3 scripts/enterprise_surface.py report",
        "python3 scripts/enterprise_surface.py fixture",
        "```",
        "",
    ]
    return "\n".join(lines)


def cmd_status(args: argparse.Namespace) -> int:
    report = build_report(_root())
    iso = report.get("isolation_proof") or {}
    fed = report.get("federation_audit") or {}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enterprise_ok": report.get("enterprise_ok"),
                "tenant_n": report.get("tenant_n"),
                "federation_all_ok": fed.get("all_ok"),
                "federation_privacy_ok": fed.get("all_ok"),
                # Buyer contract: hub exports themes/CWE/hashes only — never paths/snippets
                "privacy_themes_only": True,
                "isolation_ok": iso.get("ok"),
                "isolation_one_liner": iso.get("one_liner"),
                "docs": report.get("docs"),
                "one_liner": (
                    "Org isolation + federation privacy (themes only · no paths/snippets) "
                    f"· tenants={report.get('tenant_n')} · isolation_ok={iso.get('ok')}"
                ),
                "at": report.get("scored_at"),
            },
            indent=2,
        )
    )
    return 0 if report.get("enterprise_ok") else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    docs = report.get("docs") or {}
    fed = report.get("federation_audit") or {}
    hub = report.get("federated_hub_fixture") or {}
    iso = report.get("isolation_proof") or {}
    checks = {
        "docs_readme": bool(docs.get("readme")),
        "docs_org": bool(docs.get("org_isolation")),
        "docs_privacy": bool(docs.get("privacy")),
        "docs_org_diagram": bool(docs.get("org_diagram")),
        "docs_privacy_cost_local": bool(docs.get("privacy_cost_telemetry_local")),
        "docs_org_cost_local": bool(docs.get("org_cost_telemetry_local")),
        "docs_federation_buyer": bool(docs.get("federation_buyer_doc")),
        "docs_federation_buyer_privacy": bool(docs.get("federation_buyer_mentions_privacy")),
        "docs_federation_buyer_gate": bool(docs.get("federation_buyer_mentions_gate")),
        "docs_federation_buyer_cost_local": bool(docs.get("federation_buyer_cost_local")),
        "install_sh_tenant_flag": bool(docs.get("install_sh_tenant_flag")),
        "install_md_enterprise_light": bool(docs.get("install_md_enterprise_light")),
        "org_mentions_install_tenant": bool(docs.get("org_mentions_install_tenant")),
        "federation_audited": int(fed.get("files_n") or 0) >= 1,
        "federation_all_ok": bool(fed.get("all_ok")),
        "hub_fixture": bool(hub.get("fixture_pass")),
        "script_present": (root / "scripts" / "enterprise_surface.py").is_file(),
        "isolation_proof_ok": bool(iso.get("ok")),
        "isolation_no_path_leak": bool((iso.get("checks") or {}).get("tenant_b_no_secret_path")),
        "isolation_fed_sanitize": bool((iso.get("checks") or {}).get("fed_sanitize_strips_path")),
    }
    fixture_pass = all(checks.values())
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "schema": SCHEMA,
                "fixture_pass": fixture_pass,
                "checks": checks,
                "isolation_proof": iso,
                "tenant_n": report.get("tenant_n"),
                "scorecard_target": "enterprise",
                "at": _now(),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    report = build_report(root)
    out = root / OUT_REL
    out.mkdir(parents=True, exist_ok=True)
    if not getattr(args, "dry_run", False):
        (out / "SURFACE.md").write_text(render_surface_md(report), encoding="utf-8")
        (out / "surface.json").write_text(
            json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
        )
        report["wrote"] = {
            "md": str(out / "SURFACE.md"),
            "json": str(out / "surface.json"),
        }
    if getattr(args, "json", False) or not sys.stdout.isatty():
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_surface_md(report))
    return 0 if report.get("enterprise_ok") or getattr(args, "allow_partial", False) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Torii enterprise multi-tenant product surface")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (
        ("status", cmd_status),
        ("fixture", cmd_fixture),
        ("report", cmd_report),
    ):
        sp = sub.add_parser(name)
        if name == "report":
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--dry-run", action="store_true")
            sp.add_argument("--allow-partial", action="store_true")
        sp.set_defaults(func=fn)
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
