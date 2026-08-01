#!/usr/bin/env python3
"""Design partner / paid pilot product surface (PILOT_PATH + PILOT_READINESS).

Buyer gap: pricing + apply path exist, but operators need a Day-2 CLI that
answers "are we ready to run a design-partner / paid pilot?" with **measured**
success criteria (cost/PR · quieter · gate certs · public-eval) — not docs only.

Never invent customers. Fixture fails if pilot docs claim fake revenue/logos.

Commands:
  fixture | status | report | readiness
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

FEATURE = "PILOT"
SCHEMA = 2
OUT_REL = Path("docs/PILOT.md")
REPORT_REL = Path("docs/benchmarks/pilot-surface.md")


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _soft_json(root: Path, script: str, args: list[str], timeout: float = 45) -> dict[str, Any]:
    path = root / "scripts" / script
    if not path.is_file():
        return {}
    try:
        r = subprocess.run(
            [sys.executable, str(path), *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    out = (r.stdout or "").strip()
    if not out.startswith("{"):
        # some scripts print markdown then json — take last object
        idx = out.rfind("\n{")
        if idx >= 0:
            out = out[idx + 1 :]
        elif not out.startswith("{"):
            return {}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def build_doc_checks(root: Path) -> dict[str, Any]:
    pilot = root / OUT_REL
    pricing = root / "docs" / "PRICING.md"
    gtm = root / "docs" / "GTM.md"
    tmpl = root / ".github" / "ISSUE_TEMPLATE" / "design-partner.yml"
    readme = root / "README.md"
    product = root / "PRODUCT.md"
    landing = root / "docs" / "brand" / "landing.html"
    pt = _read(pilot)
    pr = _read(pricing)
    gt = _read(gtm)
    rm = _read(readme)
    prod = _read(product)
    land = _read(landing)
    tt = _read(tmpl)

    honesty = {
        "pre_revenue": bool(re.search(r"pre-revenue|pre.revenue", pt, re.I)),
        "zero_paid": bool(
            re.search(r"0 paid|Paid customers\s*\|\s*\*\*0\*\*|Revenue\s*\|\s*\*\*\$0", pt, re.I)
        ),
        "never_invent": bool(re.search(r"Never invent|no fake logo", pt, re.I)),
        "no_fake_arr": not bool(
            re.search(r"\$\d+M ARR|customers?:\s*[1-9]\d{1,}|Fortune 500 customers", pt, re.I)
        ),
    }
    structure = {
        "pilot_md": pilot.is_file(),
        "design_partner_section": "Design partner" in pt,
        "paid_pilot_section": bool(re.search(r"Paid pilot|Team pilot|Business pilot", pt, re.I)),
        "path_to_value": "install-torii" in pt and "torii/gate" in pt,
        "success_criteria": bool(
            re.search(r"Success criteria|time-to-signal|quieter", pt, re.I)
        ),
        "issue_template": tmpl.is_file() and "design-partner" in tt,
        "template_requires_repo": "Target repo" in tt or "repo" in tt.lower(),
        "pricing_links_pilot": bool(
            re.search(r"PILOT\.md|design partner|Design partner", pr, re.I)
        ),
        "readme_links_pilot": bool(re.search(r"PILOT\.md|design.partner|Design partner", rm, re.I)),
        "product_links_pilot": bool(
            re.search(r"PILOT\.md|design.partner|Design partner", prod, re.I)
        ),
        "landing_links_pilot": bool(
            re.search(r"PILOT\.md|design.partner|Design partner|pre-revenue", land, re.I)
        ),
        "cli_group_wired": bool(
            re.search(r'["\']pilot["\']\s*:', _read(root / "scripts" / "torii.py"))
        ),
        # GTM outreach pack (dim 11) — ready-to-send copy, no fake pipeline
        "gtm_md": gtm.is_file() and len(gt) > 400,
        "gtm_honest_traction": bool(
            re.search(r"0 paid|pre-revenue|Never invent", gt, re.I)
        ),
        "gtm_has_templates": bool(
            re.search(r"design-partner\.yml|Channel A|Channel B", gt, re.I)
        ),
        "gtm_path_to_value": "install-torii" in gt and "torii/gate" in gt,
        "pilot_links_gtm": bool(re.search(r"GTM\.md", pt)),
        "product_links_gtm": bool(re.search(r"GTM\.md", prod)),
        "landing_links_gtm": bool(re.search(r"GTM\.md", land)),
    }
    checks = {**structure, **{f"honesty_{k}": v for k, v in honesty.items()}}
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "checks": checks,
        "fixture_pass": all(checks.values()),
        "ok_n": sum(1 for v in checks.values() if v),
        "total": len(checks),
        "paths": {
            "pilot_md": str(OUT_REL),
            "issue_template": ".github/ISSUE_TEMPLATE/design-partner.yml",
            "pricing": "docs/PRICING.md",
        },
        "scorecard_target": "pricing / GTM / JTBD (dims 10 + 11 + 3)",
        "dim_lift": (
            "honest design-partner → paid pilot path + measured readiness "
            "without fake traction"
        ),
        "one_liner": (
            "Design partner apply path + paid pilot terms + measured readiness "
            "(cost · quieter · certs · public-eval); traction stays truthful (0 paid)"
        ),
        "at": _now(),
    }


def build_readiness(root: Path) -> dict[str, Any]:
    """Measured pilot success criteria from local dogfood vault (not inventing customers)."""
    docs = build_doc_checks(root)
    golden = _soft_json(root, "golden_path_metrics.py", ["status"], timeout=40)
    quieter = _soft_json(root, "quieter_over_time.py", ["status"], timeout=45)
    cert = _soft_json(root, "gate_certificate.py", ["status"], timeout=30)
    ops = _soft_json(root, "ops_dashboard.py", ["status"], timeout=40)
    pe = _soft_json(root, "public_eval.py", ["status"], timeout=30)
    commercial = _soft_json(root, "commercial_scorecard.py", ["status"], timeout=90)

    # Success criteria shared with PILOT.md (path-evidenced, not vanity comments)
    criteria: dict[str, bool] = {
        "docs_honest": bool(docs.get("fixture_pass")),
        "golden_path_ready": bool(golden.get("ready")),
        "time_to_signal_measured": (
            isinstance(golden.get("time_to_signal_p50_s"), (int, float))
            and float(golden.get("time_to_signal_p50_s") or 0) > 0
        ),
        "cost_honesty": bool(ops.get("cost_ok") or ops.get("ops_ok")),
        "gate_certs_in_vault": bool(
            cert.get("vault_ok")
            or (isinstance(cert.get("vault_n"), int) and int(cert.get("vault_n") or 0) >= 1)
        ),
        "quieter_surface": bool(quieter.get("quieter_ok")),
        "public_eval_fresh": bool(pe.get("public_eval_ok") and pe.get("freshness_ok")),
        "commercial_surfaces": bool(commercial.get("commercial_ok")),
    }
    # Partner install path readiness (docs + installable path) vs hub vault proof
    ready_n = sum(1 for v in criteria.values() if v)
    total = len(criteria)
    readiness_ok = ready_n >= 6 and bool(criteria["docs_honest"])  # allow 2 soft gaps
    full_ok = all(criteria.values())

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "pilot_ok": bool(docs.get("fixture_pass")),
        "readiness_ok": readiness_ok,
        "readiness_full_ok": full_ok,
        "ready_n": ready_n,
        "ready_total": total,
        "criteria": criteria,
        "measured": {
            "time_to_signal_p50_s": golden.get("time_to_signal_p50_s"),
            "dogfood_runs": golden.get("dogfood_runs"),
            "cost_p50_usd": ops.get("cost_p50"),
            "cost_ok": ops.get("cost_ok"),
            "vault_n": cert.get("vault_n"),
            "vault_cost_p50_usd": cert.get("vault_cost_p50_usd"),
            "quieter_ok": quieter.get("quieter_ok"),
            "getting_quieter": quieter.get("getting_quieter"),
            "quiet_score": quieter.get("quiet_score_all"),
            "public_eval_ok": pe.get("public_eval_ok"),
            "public_eval_freshness_ok": pe.get("freshness_ok"),
            "public_eval_model": pe.get("model_id"),
            "commercial_ok": commercial.get("commercial_ok"),
            "overall_est": commercial.get("overall_est"),
        },
        "docs": {
            "ok_n": docs.get("ok_n"),
            "total": docs.get("total"),
            "fixture_pass": docs.get("fixture_pass"),
        },
        "scorecard_target": "GTM / JTBD (dims 11 + 3)",
        "dim_lift": "measured pilot readiness closes free→partner path without fake traction",
        "one_liner": (
            f"Pilot readiness {ready_n}/{total} · docs_honest={criteria['docs_honest']} · "
            f"readiness_ok={readiness_ok} (pre-revenue · 0 paid)"
        ),
        "apply_url": (
            "https://github.com/Mr-Ashish/torii-gate/issues/new"
            "?template=design-partner.yml"
        ),
        "at": _now(),
    }


def build_checks(root: Path) -> dict[str, Any]:
    """Hermetic fixture = doc honesty (+ CLI wire). Readiness is soft-measured separately."""
    return build_doc_checks(root)


def cmd_fixture(args: argparse.Namespace) -> int:
    report = build_checks(_root())
    print(json.dumps(report, indent=2))
    return 0 if report.get("fixture_pass") else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    docs = build_doc_checks(root)
    # Prefer measured readiness for day-2 status; fall back to docs-only if peeks fail
    try:
        ready = build_readiness(root)
    except Exception:
        ready = {
            "pilot_ok": docs.get("fixture_pass"),
            "readiness_ok": docs.get("fixture_pass"),
            "ready_n": docs.get("ok_n"),
            "ready_total": docs.get("total"),
            "at": _now(),
        }
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "pilot_ok": ready.get("pilot_ok", docs.get("fixture_pass")),
                "readiness_ok": ready.get("readiness_ok"),
                "readiness_full_ok": ready.get("readiness_full_ok"),
                "ready_n": ready.get("ready_n"),
                "ready_total": ready.get("ready_total"),
                "ok_n": docs.get("ok_n"),
                "total": docs.get("total"),
                "criteria": ready.get("criteria"),
                "measured": ready.get("measured"),
                "one_liner": ready.get("one_liner"),
                "apply_url": ready.get("apply_url"),
                "at": ready.get("at") or _now(),
            },
            indent=2,
        )
    )
    return 0 if docs.get("fixture_pass") else 1


def cmd_readiness(args: argparse.Namespace) -> int:
    report = build_readiness(_root())
    print(json.dumps(report, indent=2))
    return 0 if report.get("readiness_ok") else 1


def cmd_report(args: argparse.Namespace) -> int:
    root = _root()
    docs = build_doc_checks(root)
    ready = build_readiness(root)
    out = root / REPORT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "<!-- torii-pilot-surface -->",
        "",
        "# Pilot / design-partner surface",
        "",
        f"_Generated: `{ready.get('at')}` · docs_pass=`{docs.get('fixture_pass')}` · "
        f"readiness_ok=`{ready.get('readiness_ok')}`_",
        "",
        str(ready.get("one_liner") or docs.get("one_liner") or ""),
        "",
        "## Doc honesty checks",
        "",
        "| Check | Pass |",
        "|-------|:----:|",
    ]
    for k, v in (docs.get("checks") or {}).items():
        lines.append(f"| `{k}` | {'yes' if v else 'no'} |")
    lines += [
        "",
        "## Measured readiness (shared success criteria)",
        "",
        "| Criterion | Pass |",
        "|-----------|:----:|",
    ]
    for k, v in (ready.get("criteria") or {}).items():
        lines.append(f"| `{k}` | {'yes' if v else 'no'} |")
    m = ready.get("measured") or {}
    lines += [
        "",
        "### Vault snapshot (local only)",
        "",
        f"- time-to-signal p50: **{m.get('time_to_signal_p50_s')}s** · dogfood_runs={m.get('dogfood_runs')}",
        f"- cost/PR p50: **${m.get('cost_p50_usd')}** · cost_ok={m.get('cost_ok')}",
        f"- gate certificates: n={m.get('vault_n')} · vault cost p50=${m.get('vault_cost_p50_usd')}",
        f"- quieter: ok={m.get('quieter_ok')} · getting_quieter={m.get('getting_quieter')} · score={m.get('quiet_score')}",
        f"- public eval: ok={m.get('public_eval_ok')} · freshness={m.get('public_eval_freshness_ok')} · model={m.get('public_eval_model')}",
        f"- commercial: ok={m.get('commercial_ok')} · overall_est={m.get('overall_est')}",
        "",
        "Source: [`docs/PILOT.md`](../PILOT.md) · issue template: "
        "`.github/ISSUE_TEMPLATE/design-partner.yml`",
        "",
        "```bash",
        "python3 scripts/pilot_surface.py fixture",
        "python3 scripts/pilot_surface.py readiness",
        "python3 scripts/torii.py pilot -- status",
        "```",
        "",
        f"Apply: {ready.get('apply_url')}",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                **docs,
                "readiness_ok": ready.get("readiness_ok"),
                "ready_n": ready.get("ready_n"),
                "ready_total": ready.get("ready_total"),
                "wrote": str(out.relative_to(root)),
            },
            indent=2,
        )
    )
    return 0 if docs.get("fixture_pass") else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    handlers = {
        "fixture": cmd_fixture,
        "status": cmd_status,
        "report": cmd_report,
        "readiness": cmd_readiness,
    }
    for name, fn in handlers.items():
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
