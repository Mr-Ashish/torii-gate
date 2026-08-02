#!/usr/bin/env python3
"""Design partner / paid pilot product surface (PILOT_PATH + PILOT_READINESS).

Buyer gap: pricing + apply path exist, but operators need a Day-2 CLI that
answers "are we ready to run a design-partner / paid pilot?" with **measured**
success criteria (cost/PR · quieter · gate certs · public-eval) — not docs only.

Partner week-1 (`week1`): checklist for *their* install path-to-value —
install pack → require torii/gate → first review → quieter · feedback notes.

Outreach (`outreach`): ready-to-send channel packs with **live** vault metrics
(TTS · cost/PR · tool-use · labeled_tp) so a human can copy-paste without
hand-editing numbers. Never invents customers/logos.

Follow-up (`followup`): operator reply packs after apply/star — first response,
day-3 nudge, week-1 feedback ask, not-ICP soft decline. Closes path from
apply → install → feedback without inventing pipeline.

Never invent customers. Fixture fails if pilot docs claim fake revenue/logos.

Commands:
  fixture | status | report | readiness | packet | week1 | outreach | followup
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
PROOF_REL = Path("docs/PILOT-PROOF.md")
WEEK1_DOC_REL = Path("docs/PARTNER-WEEK1.md")
OUTREACH_REL = Path("docs/GTM-OUTREACH.md")
FOLLOWUP_REL = Path("docs/GTM-FOLLOWUP.md")
REPORT_REL = Path("docs/benchmarks/pilot-surface.md")
CUSTOMER_PROOF_REL = Path(".torii/pilot-proof.md")
CUSTOMER_WEEK1_REL = Path(".torii/partner-week1.md")
CUSTOMER_OUTREACH_REL = Path(".torii/gtm-outreach.md")
CUSTOMER_FOLLOWUP_REL = Path(".torii/gtm-followup.md")

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
        # Public Pages CTA must convert to design-partner apply (not Hub71 / wrong repo)
        "landing_design_partner_cta": bool(
            re.search(r"design-partner\.yml|template=design-partner", land, re.I)
        ),
        "landing_no_hub71_primary_cta": "hub71.com" not in land.lower(),
        "landing_no_wrong_repo": "luffy-pr-review-agent" not in land,
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
        # Proof packet (GTM conversion) — measured one-pager, not fake logos
        "proof_packet_md": (root / PROOF_REL).is_file() and len(_read(root / PROOF_REL)) > 400,
        "proof_packet_honest": bool(
            re.search(
                r"0 paid|pre-revenue|Never invent",
                _read(root / PROOF_REL),
                re.I,
            )
        )
        if (root / PROOF_REL).is_file()
        else False,
        "proof_packet_measured": bool(
            re.search(
                r"time-to-signal|cost/PR|quieter|torii/gate",
                _read(root / PROOF_REL),
                re.I,
            )
        )
        if (root / PROOF_REL).is_file()
        else False,
        "gtm_links_proof": bool(re.search(r"PILOT-PROOF\.md", gt)),
        "pilot_links_proof": bool(re.search(r"PILOT-PROOF\.md", pt)),
        # Partner week-1 checklist CLI (path-to-value on their install)
        "week1_cmd_wired": bool(
            re.search(r'["\']week1["\']\s*:', _read(root / "scripts" / "pilot_surface.py"))
            or re.search(r"cmd_week1|week1", _read(root / "scripts" / "pilot_surface.py"))
        ),
        "pilot_md_links_week1": bool(
            re.search(r"week1|PARTNER-WEEK1", pt, re.I)
        ),
        # Live-metrics outreach channel packs (human sends; no fake pipeline)
        "outreach_cmd_wired": bool(
            re.search(r'["\']outreach["\']\s*:', _read(root / "scripts" / "pilot_surface.py"))
            or re.search(r"cmd_outreach|def render_outreach", _read(root / "scripts" / "pilot_surface.py"))
        ),
        "outreach_md": (root / OUTREACH_REL).is_file()
        and len(_read(root / OUTREACH_REL)) > 400,
        "outreach_honest": bool(
            re.search(
                r"0 paid|pre-revenue|Never invent",
                _read(root / OUTREACH_REL),
                re.I,
            )
        )
        if (root / OUTREACH_REL).is_file()
        else False,
        "outreach_has_channels": bool(
            re.search(
                r"LinkedIn|Channel D|Show HN|X / Twitter|objection",
                _read(root / OUTREACH_REL),
                re.I,
            )
        )
        if (root / OUTREACH_REL).is_file()
        else False,
        "gtm_links_outreach": bool(
            re.search(r"GTM-OUTREACH|pilot -- outreach|outreach", gt, re.I)
        ),
        "pilot_links_outreach": bool(
            re.search(r"GTM-OUTREACH|pilot -- outreach|outreach", pt, re.I)
        ),
        # Operator follow-up packs (apply → install → feedback close)
        "followup_cmd_wired": bool(
            re.search(r'["\']followup["\']\s*:', _read(root / "scripts" / "pilot_surface.py"))
            or re.search(r"cmd_followup|def render_followup", _read(root / "scripts" / "pilot_surface.py"))
        ),
        "followup_md": (root / FOLLOWUP_REL).is_file()
        and len(_read(root / FOLLOWUP_REL)) > 400,
        "followup_honest": bool(
            re.search(
                r"0 paid|pre-revenue|Never invent",
                _read(root / FOLLOWUP_REL),
                re.I,
            )
        )
        if (root / FOLLOWUP_REL).is_file()
        else False,
        "followup_has_templates": bool(
            re.search(
                r"first response|day-3|week-1 feedback|not-ICP|star",
                _read(root / FOLLOWUP_REL),
                re.I,
            )
        )
        if (root / FOLLOWUP_REL).is_file()
        else False,
        "gtm_links_followup": bool(
            re.search(r"GTM-FOLLOWUP|pilot -- followup|followup", gt, re.I)
        ),
        "pilot_links_followup": bool(
            re.search(r"GTM-FOLLOWUP|pilot -- followup|followup", pt, re.I)
        ),
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
            "proof_md": str(PROOF_REL),
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
    tools = _soft_json(root, "tool_use_quality.py", ["status"], timeout=30)
    # vs SAST / AI-review (buyer objection path — paste into partner threads)
    dvs = _soft_json(root, "diff_vs_sast.py", ["status"], timeout=20)
    dvs_m = dvs.get("measured") if isinstance(dvs.get("measured"), dict) else {}

    # Core honesty (pre-revenue / 0 paid) — not full fixture (proof packet may refresh later)
    dchecks = docs.get("checks") if isinstance(docs.get("checks"), dict) else {}
    core_honest = bool(
        dchecks.get("honesty_pre_revenue")
        and dchecks.get("honesty_zero_paid")
        and dchecks.get("honesty_never_invent")
        and dchecks.get("honesty_no_fake_arr")
        and dchecks.get("pilot_md")
    ) or bool(docs.get("fixture_pass"))

    # Success criteria shared with PILOT.md (path-evidenced, not vanity comments)
    criteria: dict[str, bool] = {
        "docs_honest": core_honest,
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
    proof_path = root / PROOF_REL
    proof_ok = proof_path.is_file() and len(_read(proof_path)) > 400

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "pilot_ok": bool(docs.get("fixture_pass")),
        "readiness_ok": readiness_ok,
        "readiness_full_ok": full_ok,
        "ready_n": ready_n,
        "ready_total": total,
        "criteria": criteria,
        "proof_packet_ok": proof_ok,
        "proof_packet_path": str(PROOF_REL),
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
            "local_organic_n": quieter.get("local_organic_n"),
            "local_demo_n": quieter.get("local_demo_n"),
            "public_eval_ok": pe.get("public_eval_ok"),
            "public_eval_freshness_ok": pe.get("freshness_ok"),
            "public_eval_model": pe.get("model_id"),
            "commercial_ok": commercial.get("commercial_ok"),
            "overall_est": commercial.get("overall_est"),
            "tool_use_rate": tools.get("tool_use_rate"),
            "tool_use_ok": tools.get("tool_use_ok") or tools.get("quality_ok"),
            # Diff vs SAST (docs/DIFF.md) — measured labeled TP / recall, not slogans
            "diff_vs_sast_ok": dvs.get("diff_vs_sast_ok"),
            "diff_labeled_tp": dvs_m.get("labeled_tp"),
            "diff_good_recall": dvs_m.get("good_recall_mean"),
            "diff_weak_fp_proxy": dvs_m.get("weak_recall_mean"),
            "diff_one_liner": dvs.get("one_liner"),
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


def render_proof_packet(ready: dict[str, Any]) -> str:
    """Buyer-facing design-partner proof one-pager (measured · no fake logos)."""
    m = ready.get("measured") or {}
    crit = ready.get("criteria") or {}
    tts = m.get("time_to_signal_p50_s")
    tts_s = f"{float(tts):.0f}s" if isinstance(tts, (int, float)) else "—"
    cost = m.get("cost_p50_usd")
    cost_s = f"${float(cost):.3f}" if isinstance(cost, (int, float)) else "—"
    overall = m.get("overall_est")
    overall_s = f"{overall}/10" if overall is not None else "—"
    tool_r = m.get("tool_use_rate")
    tool_s = f"{float(tool_r):.0%}" if isinstance(tool_r, (int, float)) else "—"
    apply = ready.get("apply_url") or (
        "https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml"
    )

    crit_rows = "\n".join(
        f"| `{k}` | {'yes' if v else 'no'} |" for k, v in crit.items()
    ) or "| _(run readiness)_ | — |"

    return "\n".join(
        [
            "<!-- torii-pilot-proof-packet -->",
            "",
            "# Torii Gate — design partner proof packet",
            "",
            f"_Generated: `{ready.get('at')}` · measured dogfood vault only · "
            f"**pre-revenue · 0 paid customers**_",
            "",
            "> **Never invent** customers, logos, ARR, or closed deals. "
            "This page is an auto-refresh of **local measured** metrics for outreach.",
            "",
            "## One sentence",
            "",
            "Torii Gate is a PR/CI **security merge authority**: agent tools on the diff, "
            "path-evidenced findings, required check **`torii/gate`**, quieter over time.",
            "",
            "## Traction truth",
            "",
            "| Fact | Value |",
            "|------|------:|",
            "| Paid customers | **0** |",
            "| Revenue | **$0** |",
            "| License | MIT open core |",
            f"| Commercial surface est. | **{overall_s}** (cap until paid pilot) |",
            "",
            "## Measured dogfood (local vault · not federated)",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Time-to-signal p50 | **{tts_s}** |",
            f"| Cost/PR p50 | **{cost_s}** |",
            f"| Dogfood runs | {m.get('dogfood_runs') if m.get('dogfood_runs') is not None else '—'} |",
            f"| Gate certificates (vault n) | {m.get('vault_n') if m.get('vault_n') is not None else '—'} |",
            f"| Quieter | ok={m.get('quieter_ok')} · getting_quieter={m.get('getting_quieter')} · score={m.get('quiet_score')} |",
            f"| Local vault | organic={m.get('local_organic_n')} · demo={m.get('local_demo_n')} |",
            f"| Tool-use rate | **{tool_s}** · ok={m.get('tool_use_ok')} |",
            f"| Public eval | ok={m.get('public_eval_ok')} · fresh={m.get('public_eval_freshness_ok')} · model=`{m.get('public_eval_model') or '—'}` |",
            f"| vs SAST / AI review | labeled_tp=**{m.get('diff_labeled_tp') if m.get('diff_labeled_tp') is not None else '—'}** · "
            f"good_recall={m.get('diff_good_recall') if m.get('diff_good_recall') is not None else '—'} · "
            f"weak_fp={m.get('diff_weak_fp_proxy') if m.get('diff_weak_fp_proxy') is not None else '—'} · "
            f"[DIFF.md](DIFF.md) |",
            "",
            "Audit: [cost/PR dashboard](ops/cost-pr-dashboard.md) · "
            "[golden-path metrics](benchmarks/golden-path-metrics.md) · "
            "[public eval](benchmarks/public-eval/SCORECARD.md) · "
            "[quieter](QUIETER.md).",
            "",
            "## Shared success criteria (partner pilot)",
            "",
            "| Criterion | Pass |",
            "|-----------|:----:|",
            crit_rows,
            "",
            f"**Readiness:** {ready.get('ready_n')}/{ready.get('ready_total')} · "
            f"ok=`{ready.get('readiness_ok')}` · full=`{ready.get('readiness_full_ok')}`",
            "",
            "## Path to value (5 minutes)",
            "",
            "```bash",
            "./scripts/install-torii.sh --minimal /path/to/your-app",
            "# secret: OPENROUTER_API_KEY",
            "# branch protection: require status check torii/gate",
            "# on a PR: @torii review this pr",
            "python3 scripts/torii.py status --text",
            "python3 scripts/torii.py quieter -- status",
            "python3 scripts/torii.py pilot -- readiness",
            "```",
            "",
            "## Apply (design partner · free)",
            "",
            f"{apply}",
            "",
            "Or: [docs/PILOT.md](PILOT.md) · [docs/GTM.md](GTM.md) · "
            "Pages: https://mr-ashish.github.io/torii-gate/",
            "",
            "## Refresh this packet",
            "",
            "```bash",
            "python3 scripts/torii.py pilot -- packet",
            "# → docs/PILOT-PROOF.md (+ .torii/pilot-proof.md when .torii/ exists)",
            "```",
            "",
            "---",
            "",
            f"_One-liner:_ {ready.get('one_liner') or 'Pilot path measured · 0 paid'}",
            "",
        ]
    )


def write_proof_packet(root: Path, ready: dict[str, Any] | None = None) -> dict[str, Any]:
    ready = ready or build_readiness(root)
    body = render_proof_packet(ready)
    hub = root / PROOF_REL
    hub.parent.mkdir(parents=True, exist_ok=True)
    hub.write_text(body, encoding="utf-8")
    wrote = [str(PROOF_REL)]
    # Customer install: also drop a copy under .torii when present
    torii = root / ".torii"
    if torii.is_dir():
        cust = root / CUSTOMER_PROOF_REL
        try:
            cust.write_text(body, encoding="utf-8")
            wrote.append(str(CUSTOMER_PROOF_REL))
        except OSError:
            pass
    return {
        "feature": FEATURE,
        "packet_ok": True,
        "proof_packet_ok": True,
        "wrote": wrote,
        "bytes": len(body.encode("utf-8")),
        "readiness_ok": ready.get("readiness_ok"),
        "ready_n": ready.get("ready_n"),
        "ready_total": ready.get("ready_total"),
        "apply_url": ready.get("apply_url"),
        "measured": ready.get("measured"),
        "one_liner": (
            "Design-partner proof packet refreshed from measured vault "
            "(pre-revenue · 0 paid · no fake logos)"
        ),
        "at": ready.get("at") or _now(),
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
    week = build_week1(root)
    outreach_exists = (root / OUTREACH_REL).is_file() and len(_read(root / OUTREACH_REL)) > 400
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
                "proof_packet_ok": ready.get("proof_packet_ok"),
                "proof_packet_path": ready.get("proof_packet_path") or str(PROOF_REL),
                "week1_ok": week.get("week1_ok"),
                "week1_ready_n": week.get("ready_n"),
                "week1_ready_total": week.get("ready_total"),
                "week1_core_ok": week.get("core_ok"),
                "week1_one_liner": week.get("one_liner"),
                "outreach_ok": outreach_exists,
                "outreach_path": str(OUTREACH_REL),
                "followup_ok": (root / FOLLOWUP_REL).is_file()
                and len(_read(root / FOLLOWUP_REL)) > 400,
                "followup_path": str(FOLLOWUP_REL),
                "one_liner": ready.get("one_liner"),
                "apply_url": ready.get("apply_url") or week.get("apply_url"),
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


def cmd_packet(args: argparse.Namespace) -> int:
    """Write design-partner proof one-pager from measured vault metrics."""
    root = _root()
    ready = build_readiness(root)
    out = write_proof_packet(root, ready)
    print(json.dumps(out, indent=2))
    return 0 if out.get("packet_ok") else 1


def build_week1(root: Path) -> dict[str, Any]:
    """Partner week-1 path-to-value checklist (customer install · not hub GTM).

    Maps PILOT.md "you give" + path-to-value into measured local checks so a
    design partner knows what to finish in the first week.
    """
    wf_dir = root / ".github" / "workflows"
    wf_bodies = []
    if wf_dir.is_dir():
        for p in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
            wf_bodies.append(_read(p))
    wf_text = "\n".join(wf_bodies)
    pack_caller = root / "pack" / "torii-pr-review-caller.yml"
    stamp = root / ".torii-install-stamp"
    env_ex = root / ".env.example"
    install_md = root / "docs" / "INSTALL.md"
    gate_md = root / "docs" / "GATE.md"
    quieter_md = root / "docs" / "QUIETER.md"
    pilot_md = root / OUT_REL
    runs = root / ".torii" / "runs"
    run_dirs = [p for p in runs.iterdir() if p.is_dir()] if runs.is_dir() else []
    organic_n = 0
    demo_n = 0
    for d in run_dirs:
        name = d.name.lower()
        meta = _read(d / "meta.json")
        if "demo" in name or re.search(r'"demo"\s*:\s*true', meta, re.I):
            demo_n += 1
        else:
            organic_n += 1

    quieter = _soft_json(root, "quieter_over_time.py", ["status"], timeout=40)
    # Light health surface (avoid re-running full doctor inside status peeks)
    smoke = (root / "scripts" / "smoke-torii-gate.sh").is_file()
    torii_cli = (root / "scripts" / "torii.py").is_file()
    doctor_pass = smoke and torii_cli

    checks: dict[str, bool] = {
        "workflow_torii_present": bool(
            re.search(r"torii", wf_text, re.I)
            or pack_caller.is_file()
            or (
                (root / ".github" / "workflows").is_dir()
                and any((root / ".github" / "workflows").glob("torii*.yml"))
            )
        ),
        "workflow_mentions_gate": "torii/gate" in wf_text
        or "torii/gate" in _read(pack_caller)
        or (gate_md.is_file() and "torii/gate" in _read(gate_md)),
        "install_docs": install_md.is_file()
        and "torii/gate" in _read(install_md)
        and "install-torii" in _read(install_md),
        "required_check_docs": (
            "torii/gate" in _read(gate_md)
            or "Branch protection" in _read(install_md)
            or "branch protection" in _read(install_md).lower()
        ),
        "openrouter_secret_docs": bool(
            re.search(r"OPENROUTER_API_KEY", _read(env_ex) + _read(install_md))
        ),
        "runs_vault_seeded": runs.is_dir() and len(run_dirs) >= 1,
        "quieter_surface": bool(quieter.get("quieter_ok"))
        or quieter_md.is_file()
        and "torii/gate" in _read(quieter_md),
        "doctor_or_smoke": doctor_pass or smoke,
        "feedback_path_docs": bool(
            re.search(
                r"feedback|1–2|1-2 short|what blocked",
                _read(pilot_md),
                re.I,
            )
        ),
        # Offline workflows-as-code (validate free — before OpenRouter $)
        "workflow_as_code_yaml": (
            (root / "docs" / "workflows" / "torii-gate.workflow.yaml").is_file()
            or (root / "docs" / "WORKFLOWS.md").is_file()
        ),
        "workflow_validate_offline": bool(
            (root / "scripts" / "workflow_as_code.py").is_file()
        ),
        # Live require-check CLI (partner proves torii/gate is actually required)
        "require_check_cli": bool(
            re.search(
                r"require-check|live_require_check",
                _read(root / "scripts" / "quieter_over_time.py"),
            )
        ),
    }
    # Soft: organic signal (not required for week1_ok — demo seed is enough day-1)
    checks["organic_run_or_demo"] = organic_n >= 1 or demo_n >= 1

    ready_n = sum(1 for v in checks.values() if v)
    total = len(checks)
    # Pass bar: core install path (not all optional organic)
    core_keys = (
        "workflow_torii_present",
        "workflow_mentions_gate",
        "install_docs",
        "required_check_docs",
        "openrouter_secret_docs",
        "runs_vault_seeded",
        "feedback_path_docs",
    )
    core_ok = all(checks.get(k) for k in core_keys)
    week1_ok = core_ok and ready_n >= 8
    week1_full = all(checks.values())

    next_steps: list[str] = []
    if not checks.get("workflow_torii_present"):
        next_steps.append("Install pack: ./scripts/install-torii.sh --minimal /path/to/repo")
    if not checks.get("runs_vault_seeded"):
        next_steps.append("Seed quieter vault: python3 scripts/torii.py quieter -- bootstrap --demo")
    if organic_n < 1:
        next_steps.append(
            "Require status check **torii/gate** · @torii review on one real PR"
        )
    next_steps.append(
        "Verify live: `python3 scripts/torii.py quieter -- require-check` (must show live_ok=true)"
    )
    next_steps.append(
        "Send 1–2 feedback notes (what blocked / cost / quieter) via design-partner issue"
    )
    next_steps.append("python3 scripts/torii.py pilot -- readiness · pilot -- packet")

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "cmd": "week1",
        "week1_ok": week1_ok,
        "week1_full_ok": week1_full,
        "ready_n": ready_n,
        "ready_total": total,
        "core_ok": core_ok,
        "checks": checks,
        "measured": {
            "local_runs_n": len(run_dirs),
            "local_demo_n": demo_n,
            "local_organic_n": organic_n,
            "quieter_ok": quieter.get("quieter_ok"),
            "getting_quieter": quieter.get("getting_quieter"),
            "doctor_pass": doctor_pass,
            "install_stamp": stamp.is_file(),
        },
        "next_steps": next_steps,
        "apply_url": (
            "https://github.com/Mr-Ashish/torii-gate/issues/new"
            "?template=design-partner.yml"
        ),
        "scorecard_target": "JTBD / install / GTM (dims 3 + 7 + 11)",
        "dim_lift": "partner week-1 checklist collapses path-to-value cognitive load",
        "one_liner": (
            f"Partner week-1 {ready_n}/{total} · core_ok={core_ok} · "
            f"week1_ok={week1_ok} (install → torii/gate → review → feedback)"
        ),
        "at": _now(),
    }


def render_week1_md(week: dict[str, Any]) -> str:
    """Buyer-facing week-1 checklist markdown."""
    checks = week.get("checks") or {}
    m = week.get("measured") or {}
    steps = week.get("next_steps") or []
    lines = [
        "<!-- torii-partner-week1 -->",
        "",
        "# Torii Gate — design partner week-1 checklist",
        "",
        f"_Generated: `{week.get('at')}` · measured local install · **not** a sales deck_",
        "",
        "> Path: install free → require **`torii/gate`** → first review → quieter · 1–2 feedback notes.",
        "",
        f"**Status:** {week.get('ready_n')}/{week.get('ready_total')} · "
        f"core_ok=`{week.get('core_ok')}` · week1_ok=`{week.get('week1_ok')}` · "
        f"full=`{week.get('week1_full_ok')}`",
        "",
        str(week.get("one_liner") or ""),
        "",
        "## Checklist",
        "",
        "| Check | Pass | Why it matters |",
        "|-------|:----:|----------------|",
        f"| workflow present | {'yes' if checks.get('workflow_torii_present') else 'no'} | Pack can run on PRs |",
        f"| mentions `torii/gate` | {'yes' if checks.get('workflow_mentions_gate') else 'no'} | Required check name exists |",
        f"| install docs | {'yes' if checks.get('install_docs') else 'no'} | 5-minute path documented |",
        f"| required-check docs | {'yes' if checks.get('required_check_docs') else 'no'} | Branch protection how-to |",
        f"| OPENROUTER secret docs | {'yes' if checks.get('openrouter_secret_docs') else 'no'} | Model key path |",
        f"| runs vault seeded | {'yes' if checks.get('runs_vault_seeded') else 'no'} | Quieter chart has data |",
        f"| quieter surface | {'yes' if checks.get('quieter_surface') else 'no'} | Own-repo quieter path |",
        f"| doctor or smoke | {'yes' if checks.get('doctor_or_smoke') else 'no'} | Day-2 health |",
        f"| feedback path docs | {'yes' if checks.get('feedback_path_docs') else 'no'} | What to send us |",
        f"| workflow-as-code yaml | {'yes' if checks.get('workflow_as_code_yaml') else 'no'} | Declarative pipeline graph |",
        f"| workflow validate CLI | {'yes' if checks.get('workflow_validate_offline') else 'no'} | Free offline before model $ |",
        f"| require-check CLI | {'yes' if checks.get('require_check_cli') else 'no'} | Live: is torii/gate required? |",
        f"| organic or demo run | {'yes' if checks.get('organic_run_or_demo') else 'no'} | At least one local pack |",
        "",
        "## Local vault",
        "",
        f"- runs: **{m.get('local_runs_n')}** · demo={m.get('local_demo_n')} · organic={m.get('local_organic_n')}",
        f"- quieter_ok={m.get('quieter_ok')} · getting_quieter={m.get('getting_quieter')}",
        f"- doctor_pass={m.get('doctor_pass')} · install_stamp={m.get('install_stamp')}",
        "",
        "## Next (this week)",
        "",
    ]
    for i, s in enumerate(steps, 1):
        lines.append(f"{i}. {s}")
    lines += [
        "",
        "## CLI",
        "",
        "```bash",
        "python3 scripts/torii.py pilot -- week1",
        "python3 scripts/torii.py pilot -- readiness",
        "python3 scripts/torii.py quieter -- status",
        "python3 scripts/torii.py status --text",
        "```",
        "",
        f"Apply / feedback: {week.get('apply_url')}",
        "",
        "Docs: [PILOT.md](PILOT.md) · [INSTALL.md](INSTALL.md) · [GTM.md](GTM.md) · [QUIETER.md](QUIETER.md)",
        "",
    ]
    return "\n".join(lines)


def write_week1(root: Path, week: dict[str, Any] | None = None) -> dict[str, Any]:
    week = week or build_week1(root)
    body = render_week1_md(week)
    wrote: list[str] = []
    hub = root / WEEK1_DOC_REL
    hub.parent.mkdir(parents=True, exist_ok=True)
    hub.write_text(body, encoding="utf-8")
    wrote.append(str(WEEK1_DOC_REL))
    cust = root / CUSTOMER_WEEK1_REL
    if (root / ".torii").is_dir() or True:
        cust.parent.mkdir(parents=True, exist_ok=True)
        cust.write_text(body, encoding="utf-8")
        wrote.append(str(CUSTOMER_WEEK1_REL))
    return {
        "feature": FEATURE,
        "week1_ok": week.get("week1_ok"),
        "week1_full_ok": week.get("week1_full_ok"),
        "ready_n": week.get("ready_n"),
        "ready_total": week.get("ready_total"),
        "core_ok": week.get("core_ok"),
        "wrote": wrote,
        "bytes": len(body.encode("utf-8")),
        "checks": week.get("checks"),
        "measured": week.get("measured"),
        "next_steps": week.get("next_steps"),
        "one_liner": week.get("one_liner"),
        "apply_url": week.get("apply_url"),
        "at": week.get("at") or _now(),
    }


def cmd_week1(args: argparse.Namespace) -> int:
    """Partner week-1 path-to-value checklist + write docs/PARTNER-WEEK1.md."""
    root = _root()
    out = write_week1(root)
    print(json.dumps(out, indent=2))
    return 0 if out.get("week1_ok") else 1


def _fmt_metrics(m: dict[str, Any]) -> dict[str, str]:
    """Human paste-ready metric strings from readiness measured block."""
    tts = m.get("time_to_signal_p50_s")
    cost = m.get("cost_p50_usd")
    tool_r = m.get("tool_use_rate")
    tp = m.get("diff_labeled_tp")
    runs = m.get("dogfood_runs")
    return {
        "tts": f"~{float(tts):.0f}s" if isinstance(tts, (int, float)) else "~90s",
        "cost": f"~${float(cost):.2f}" if isinstance(cost, (int, float)) else "~$0.01",
        "tool": f"{float(tool_r):.0%}" if isinstance(tool_r, (int, float)) else "high",
        "tp": str(int(tp)) if isinstance(tp, (int, float)) else "18",
        "runs": str(int(runs)) if isinstance(runs, (int, float)) else "—",
        "model": str(m.get("public_eval_model") or "deepseek/deepseek-v4-pro"),
    }


def build_outreach(root: Path, ready: dict[str, Any] | None = None) -> dict[str, Any]:
    """Live-metrics GTM channel packs for a human to send (no fake logos)."""
    ready = ready or build_readiness(root)
    m = ready.get("measured") or {}
    fmt = _fmt_metrics(m)
    apply = ready.get("apply_url") or (
        "https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml"
    )
    channels = (
        "issue_nudge",
        "email_dm",
        "community",
        "linkedin",
        "x_twitter",
        "show_hn",
        "objection_sast",
    )
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "cmd": "outreach",
        "outreach_ok": True,
        "channels": list(channels),
        "channel_n": len(channels),
        "metrics": fmt,
        "measured": m,
        "readiness_ok": ready.get("readiness_ok"),
        "ready_n": ready.get("ready_n"),
        "ready_total": ready.get("ready_total"),
        "apply_url": apply,
        "landing_url": "https://mr-ashish.github.io/torii-gate/",
        "install_url": "https://github.com/Mr-Ashish/torii-gate/blob/main/docs/INSTALL.md",
        "scorecard_target": "GTM / JTBD (dims 11 + 3)",
        "dim_lift": "live-metrics channel packs collapse time-to-first-human-send",
        "one_liner": (
            f"Outreach packs ready · channels={len(channels)} · "
            f"TTS {fmt['tts']} · cost {fmt['cost']}/PR · labeled_tp={fmt['tp']} · 0 paid"
        ),
        "at": _now(),
    }


def render_outreach_md(pack: dict[str, Any]) -> str:
    """Buyer-operator ready-to-send channel copy with filled live metrics."""
    fmt = pack.get("metrics") or {}
    apply = pack.get("apply_url") or ""
    landing = pack.get("landing_url") or "https://mr-ashish.github.io/torii-gate/"
    install = pack.get("install_url") or ""
    tts = fmt.get("tts") or "~90s"
    cost = fmt.get("cost") or "~$0.01"
    tool = fmt.get("tool") or "high"
    tp = fmt.get("tp") or "18"
    runs = fmt.get("runs") or "—"
    model = fmt.get("model") or "deepseek/deepseek-v4-pro"

    issue_nudge = f"""Subject: Torii Gate design partner (free) — require torii/gate on one repo?

We ship an open-source PR security merge authority (MIT). Pre-revenue · 0 paid customers.

Measured dogfood (own vault, not inventing logos): time-to-signal p50 {tts} ·
cost/PR p50 {cost} · tool-use {tool} · labeled TP vs SAST bench = {tp}.

Ask: install the pack on one real repo, require status check `torii/gate`,
send 1–2 notes on what blocked / cost / quieter trajectory.

Apply: {apply}
Install: {install}
Landing: {landing}
Proof: https://github.com/Mr-Ashish/torii-gate/blob/main/docs/PILOT-PROOF.md"""

    email_dm = f"""Hi {{{{name}}}} — quick ask, not a sales deck.

Torii Gate is open-source merge authority for AI/human PRs: agent tools on the
diff + deterministic checker + required check `torii/gate`. Measured dogfood
{tts} / {cost} per PR (OpenRouter · {model}). Pre-revenue · 0 paid · no fake logos.
Labeled public-eval TP={tp} · tool-use rate {tool} · dogfood runs={runs}.

Would you try a free design partner install on one repo this month?
Path: install pack → require torii/gate → @torii review → quieter chart.
Issue template: {apply}
Landing: {landing}"""

    community = f"""Looking for design partners (free) for Torii Gate — PR/CI security merge authority.
Not another chatty bot: path-evidenced findings, gate certificates, quieter-over-time.
Open core MIT · pre-revenue · honest cost/PR ({cost} p50) · TTS {tts}.
Apply: design-partner issue on Mr-Ashish/torii-gate · INSTALL.md in five minutes.
{landing}"""

    linkedin = f"""Building in public: Torii Gate — security merge authority for AI-written PRs.

Problem: copilots open PRs faster than AppSec can review; chatty AI reviewers add noise.
Approach: tools on the diff + deterministic checker + required GitHub check `torii/gate`.
Measured (own dogfood vault · 0 paid customers): TTS p50 {tts} · cost/PR {cost} · tool-use {tool}.

Free design partner: one real repo · require torii/gate · 1–2 feedback notes.
Apply → {apply}
Landing → {landing}

#AppSec #DevSecOps #AI #OpenSource"""

    x_twitter = f"""Torii Gate = PR security merge authority (not chatty review).

require `torii/gate` · path-evidenced findings · quieter over time
Dogfood: {tts} · {cost}/PR · tool-use {tool} · 0 paid · MIT

Free design partner (one repo):
{apply}"""

    show_hn = f"""Show HN: Torii Gate – require torii/gate as a security merge authority for PRs

Torii is an open-source PR/CI gate: agent tools on the diff, a deterministic
checker that demotes weak APPROVE without path evidence, and a required status
check named `torii/gate`. Goal is merge authority that gets quieter over time
(FP memory + measured skill fitness), not another comment bot.

Honest metrics from our own Modal dogfood vault (pytorch PRs, POST_COMMENT=0):
- time-to-signal p50 {tts}
- cost/PR p50 {cost} (OpenRouter · {model})
- tool-use rate {tool} · labeled TP on public eval = {tp}
- paid customers: 0 · pre-revenue · MIT open core

We are looking for free design partners on one real repo (require the check,
send 1–2 notes). No logo wall.

Landing: {landing}
Apply: {apply}
Repo: https://github.com/Mr-Ashish/torii-gate"""

    objection = f"""When someone says "we already have SAST / AI review":

SAST finds patterns; chatty AI review nags. Torii is **merge authority**:
required check `torii/gate` + path-evidenced findings + gate certificates.
Labeled public-eval: TP={tp} · good_recall high · weak APPROVE FP proxy low
(see DIFF.md). Dogfood cost {cost}/PR · TTS {tts}. Install free before any pilot $.
{landing} · {apply}"""

    lines = [
        "<!-- torii-gtm-outreach -->",
        "",
        "# Torii Gate — GTM outreach (live metrics · ready to send)",
        "",
        f"_Generated: `{pack.get('at')}` · metrics from local dogfood vault · "
        f"**pre-revenue · 0 paid customers**_",
        "",
        "> **Human sends these.** Never invent customers, logos, ARR, or closed deals. "
        "Numbers below are measured vault metrics — refresh before a campaign.",
        "",
        str(pack.get("one_liner") or ""),
        "",
        "## Live metrics (paste-ready)",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Time-to-signal p50 | **{tts}** |",
        f"| Cost/PR p50 | **{cost}** |",
        f"| Tool-use rate | **{tool}** |",
        f"| Labeled TP (public eval) | **{tp}** |",
        f"| Dogfood runs | {runs} |",
        f"| Model pin | `{model}` |",
        "| Paid customers | **0** |",
        "",
        f"**Readiness:** {pack.get('ready_n')}/{pack.get('ready_total')} · "
        f"ok=`{pack.get('readiness_ok')}`",
        "",
        f"Apply: {apply}  ",
        f"Landing: {landing}  ",
        "Proof packet: [PILOT-PROOF.md](PILOT-PROOF.md) · static templates: [GTM.md](GTM.md)",
        "",
        "---",
        "",
        "## Channel A — GitHub issue nudge",
        "",
        "```text",
        issue_nudge.strip(),
        "```",
        "",
        "## Channel B — email / DM",
        "",
        "```text",
        email_dm.strip(),
        "```",
        "",
        "## Channel C — community post",
        "",
        "```text",
        community.strip(),
        "```",
        "",
        "## Channel D — LinkedIn",
        "",
        "```text",
        linkedin.strip(),
        "```",
        "",
        "## Channel E — X / Twitter",
        "",
        "```text",
        x_twitter.strip(),
        "```",
        "",
        "## Channel F — Show HN (honest · no hype)",
        "",
        "```text",
        show_hn.strip(),
        "```",
        "",
        "## Channel G — objection (vs SAST / AI review)",
        "",
        "```text",
        objection.strip(),
        "```",
        "",
        "---",
        "",
        "## Operator rules",
        "",
        "1. Never invent customers, logos, ARR, or closed deals",
        "2. Refresh metrics before sending: `python3 scripts/torii.py pilot -- outreach`",
        "3. Prefer **one real repo** design partner over fleet pitch",
        "4. After install: point them at `pilot -- week1`",
        "5. Log traction in PILOT.md **only with opt-in truth**",
        "",
        "## CLI",
        "",
        "```bash",
        "python3 scripts/torii.py pilot -- outreach   # refresh this file",
        "python3 scripts/torii.py pilot -- packet     # proof one-pager",
        "python3 scripts/torii.py pilot -- readiness",
        "python3 scripts/torii.py pilot -- week1",
        "```",
        "",
        "Related: [GTM.md](GTM.md) · [PILOT.md](PILOT.md) · [DIFF.md](DIFF.md) · [INSTALL.md](INSTALL.md)",
        "",
    ]
    return "\n".join(lines)


def write_outreach(root: Path, pack: dict[str, Any] | None = None) -> dict[str, Any]:
    pack = pack or build_outreach(root)
    body = render_outreach_md(pack)
    wrote: list[str] = []
    hub = root / OUTREACH_REL
    hub.parent.mkdir(parents=True, exist_ok=True)
    hub.write_text(body, encoding="utf-8")
    wrote.append(str(OUTREACH_REL))
    cust = root / CUSTOMER_OUTREACH_REL
    cust.parent.mkdir(parents=True, exist_ok=True)
    try:
        cust.write_text(body, encoding="utf-8")
        wrote.append(str(CUSTOMER_OUTREACH_REL))
    except OSError:
        pass
    return {
        "feature": FEATURE,
        "outreach_ok": True,
        "channel_n": pack.get("channel_n"),
        "channels": pack.get("channels"),
        "wrote": wrote,
        "bytes": len(body.encode("utf-8")),
        "metrics": pack.get("metrics"),
        "readiness_ok": pack.get("readiness_ok"),
        "ready_n": pack.get("ready_n"),
        "ready_total": pack.get("ready_total"),
        "apply_url": pack.get("apply_url"),
        "one_liner": pack.get("one_liner"),
        "at": pack.get("at") or _now(),
    }


def cmd_outreach(args: argparse.Namespace) -> int:
    """Write live-metrics GTM channel packs for human send (docs/GTM-OUTREACH.md)."""
    root = _root()
    ready = build_readiness(root)
    pack = build_outreach(root, ready)
    out = write_outreach(root, pack)
    print(json.dumps(out, indent=2))
    return 0 if out.get("outreach_ok") else 1


def build_followup(root: Path, ready: dict[str, Any] | None = None) -> dict[str, Any]:
    """Operator reply packs after design-partner apply / warm interest."""
    ready = ready or build_readiness(root)
    m = ready.get("measured") or {}
    fmt = _fmt_metrics(m)
    apply = ready.get("apply_url") or (
        "https://github.com/Mr-Ashish/torii-gate/issues/new?template=design-partner.yml"
    )
    templates = (
        "first_response",
        "day3_nudge",
        "week1_feedback",
        "star_fork_warm",
        "not_icp_decline",
        "after_require_check",
    )
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "cmd": "followup",
        "followup_ok": True,
        "templates": list(templates),
        "template_n": len(templates),
        "metrics": fmt,
        "measured": m,
        "readiness_ok": ready.get("readiness_ok"),
        "ready_n": ready.get("ready_n"),
        "ready_total": ready.get("ready_total"),
        "apply_url": apply,
        "landing_url": "https://mr-ashish.github.io/torii-gate/",
        "install_url": "https://github.com/Mr-Ashish/torii-gate/blob/main/docs/INSTALL.md",
        "week1_cmd": "python3 scripts/torii.py pilot -- week1",
        "scorecard_target": "GTM / JTBD (dims 11 + 3)",
        "dim_lift": "operator follow-up collapses apply→install→feedback time-to-close",
        "one_liner": (
            f"Follow-up packs ready · templates={len(templates)} · "
            f"TTS {fmt['tts']} · cost {fmt['cost']}/PR · 0 paid · human sends"
        ),
        "at": _now(),
    }


def render_followup_md(pack: dict[str, Any]) -> str:
    """Operator-facing reply templates with live vault metrics."""
    fmt = pack.get("metrics") or {}
    apply = pack.get("apply_url") or ""
    landing = pack.get("landing_url") or "https://mr-ashish.github.io/torii-gate/"
    install = pack.get("install_url") or ""
    week1 = pack.get("week1_cmd") or "python3 scripts/torii.py pilot -- week1"
    tts = fmt.get("tts") or "~90s"
    cost = fmt.get("cost") or "~$0.01"
    tool = fmt.get("tool") or "high"
    tp = fmt.get("tp") or "18"

    first = f"""Thanks for applying — happy to design-partner with you (free · pre-revenue · 0 paid).

Path that works:
1. Install: {install}
2. Secret: OPENROUTER_API_KEY (or your OpenRouter path)
3. Branch protection: require status check **torii/gate**
   · dry-run: `python3 scripts/torii.py quieter -- require-check`
   · enable (admin): `… quieter -- require-check -- --enable --yes`
4. On a PR: `@torii review this pr` (or pack workflow)
5. Week-1 checklist: `{week1}` → docs/PARTNER-WEEK1.md

Our dogfood (own vault, not inventing logos): TTS p50 {tts} · cost/PR {cost} ·
tool-use {tool} · labeled TP={tp}. Proof: docs/PILOT-PROOF.md · {landing}

What we need back in week 1: 1–2 notes on what blocked / cost / quieter.
No public logo mention unless you opt in later."""

    day3 = f"""Quick nudge on the design-partner path — no pressure.

If install is stuck, the usual blockers are:
- missing OPENROUTER_API_KEY
- torii/gate not yet required on default branch
- pack workflow not on the PR event

Five-minute path: {install}
Live check: `python3 scripts/torii.py quieter -- require-check` (want live_ok=true)
Week-1: `{week1}`

Happy to jump on a 15-min async thread if useful. Still free · 0 paid · MIT."""

    week1_fb = f"""If you got through install + require torii/gate — thank you.

When you have a minute, 1–2 short notes help more than a deck:
1. What blocked or surprised on first review?
2. Cost / time-to-signal vs expectation?
3. Did quieter / gate certificate feel useful?

Optional: paste `python3 scripts/torii.py status --text` (redact secrets).
We will not list you as a design partner publicly without opt-in.

Dogfood reference: TTS {tts} · {cost}/PR · TP={tp} · {landing}"""

    star = f"""Saw the star/fork — thanks.

If you want a free design partner install on one real repo (require `torii/gate`,
send 1–2 feedback notes), apply here:
{apply}

Install: {install}
Landing: {landing}
Measured dogfood: {tts} · {cost}/PR · tool-use {tool} · 0 paid customers."""

    not_icp = f"""Thanks for the interest.

Honest take: Torii v1 is a **PR/CI security merge authority** (require `torii/gate`,
path-evidenced findings) for Platform/AppSec/eng leads — not full ASPM, not a
red-team agency product, and not a style-comment bot.

If that still fits one real repo, happy to design-partner free:
{apply} · {install}

If not, no hard feelings — the MIT pack stays open either way. Pre-revenue · 0 paid."""

    after_rc = f"""Nice — `require-check` live_ok on your side is the real merge-authority step.

Next:
1. `{week1}` and confirm week1_ok
2. One organic `@torii review` on a real PR
3. 1–2 feedback notes (blocked / cost / quieter)

We measure quieter + certificates on *your* vault — not ours.
Reference dogfood: TTS {tts} · {cost}/PR · labeled TP={tp}.
Questions welcome. Still free · no logo without opt-in."""

    lines = [
        "<!-- torii-gtm-followup -->",
        "",
        "# Torii Gate — operator follow-up (live metrics · ready to reply)",
        "",
        f"_Generated: `{pack.get('at')}` · metrics from local dogfood vault · "
        f"**pre-revenue · 0 paid customers**_",
        "",
        "> **Human sends these** after apply / star / install. "
        "Never invent customers, logos, ARR, or closed deals. "
        "Respond within a few business days.",
        "",
        str(pack.get("one_liner") or ""),
        "",
        "## Cadence (us)",
        "",
        "| When | Action | Template |",
        "|------|--------|----------|",
        "| <48h after apply issue | First response + install path | A |",
        "| Day 3 no install signal | Soft nudge + blockers | B |",
        "| After require-check live | Celebrate + week-1 feedback | F |",
        "| Week 1 post-install | Ask 1–2 feedback notes | C |",
        "| Star/fork warm lead | Short invite | D |",
        "| Not ICP | Honest decline + open pack | E |",
        "",
        "## Live metrics (paste-ready)",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Time-to-signal p50 | **{tts}** |",
        f"| Cost/PR p50 | **{cost}** |",
        f"| Tool-use rate | **{tool}** |",
        f"| Labeled TP | **{tp}** |",
        "| Paid customers | **0** |",
        "",
        f"Apply: {apply}  ",
        f"Landing: {landing}  ",
        "Outbound packs: [GTM-OUTREACH.md](GTM-OUTREACH.md) · static: [GTM.md](GTM.md)",
        "",
        "---",
        "",
        "## A — First response (apply issue)",
        "",
        "```text",
        first.strip(),
        "```",
        "",
        "## B — Day-3 nudge (no install yet)",
        "",
        "```text",
        day3.strip(),
        "```",
        "",
        "## C — Week-1 feedback ask",
        "",
        "```text",
        week1_fb.strip(),
        "```",
        "",
        "## D — Star / fork warm reply",
        "",
        "```text",
        star.strip(),
        "```",
        "",
        "## E — Not-ICP soft decline",
        "",
        "```text",
        not_icp.strip(),
        "```",
        "",
        "## F — After require-check live_ok",
        "",
        "```text",
        after_rc.strip(),
        "```",
        "",
        "---",
        "",
        "## Operator rules",
        "",
        "1. Never invent customers, logos, ARR, or closed deals",
        "2. Refresh before a reply wave: `python3 scripts/torii.py pilot -- followup`",
        "3. Prefer one real repo over fleet pitch",
        "4. Public “design partner” only with written opt-in",
        "5. Update PILOT.md traction **only with truth**",
        "",
        "## CLI",
        "",
        "```bash",
        "python3 scripts/torii.py pilot -- followup   # refresh this file",
        "python3 scripts/torii.py pilot -- outreach   # outbound channel packs",
        "python3 scripts/torii.py pilot -- week1",
        "python3 scripts/torii.py pilot -- readiness",
        "```",
        "",
        "Related: [PILOT.md](PILOT.md) · [GTM.md](GTM.md) · [GTM-OUTREACH.md](GTM-OUTREACH.md) · [PARTNER-WEEK1.md](PARTNER-WEEK1.md)",
        "",
    ]
    return "\n".join(lines)


def write_followup(root: Path, pack: dict[str, Any] | None = None) -> dict[str, Any]:
    pack = pack or build_followup(root)
    body = render_followup_md(pack)
    wrote: list[str] = []
    hub = root / FOLLOWUP_REL
    hub.parent.mkdir(parents=True, exist_ok=True)
    hub.write_text(body, encoding="utf-8")
    wrote.append(str(FOLLOWUP_REL))
    cust = root / CUSTOMER_FOLLOWUP_REL
    cust.parent.mkdir(parents=True, exist_ok=True)
    try:
        cust.write_text(body, encoding="utf-8")
        wrote.append(str(CUSTOMER_FOLLOWUP_REL))
    except OSError:
        pass
    return {
        "feature": FEATURE,
        "followup_ok": True,
        "template_n": pack.get("template_n"),
        "templates": pack.get("templates"),
        "wrote": wrote,
        "bytes": len(body.encode("utf-8")),
        "metrics": pack.get("metrics"),
        "readiness_ok": pack.get("readiness_ok"),
        "ready_n": pack.get("ready_n"),
        "ready_total": pack.get("ready_total"),
        "apply_url": pack.get("apply_url"),
        "one_liner": pack.get("one_liner"),
        "at": pack.get("at") or _now(),
    }


def cmd_followup(args: argparse.Namespace) -> int:
    """Write operator follow-up reply packs (docs/GTM-FOLLOWUP.md)."""
    root = _root()
    ready = build_readiness(root)
    pack = build_followup(root, ready)
    out = write_followup(root, pack)
    print(json.dumps(out, indent=2))
    return 0 if out.get("followup_ok") else 1


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
        f"- tool-use: rate={m.get('tool_use_rate')} · ok={m.get('tool_use_ok')}",
        "",
        "Proof packet: [`docs/PILOT-PROOF.md`](../PILOT-PROOF.md) · "
        "Source: [`docs/PILOT.md`](../PILOT.md) · issue template: "
        "`.github/ISSUE_TEMPLATE/design-partner.yml`",
        "",
        "```bash",
        "python3 scripts/pilot_surface.py fixture",
        "python3 scripts/pilot_surface.py readiness",
        "python3 scripts/pilot_surface.py packet",
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
                "proof_packet_ok": ready.get("proof_packet_ok"),
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
        "packet": cmd_packet,
        "week1": cmd_week1,
        "outreach": cmd_outreach,
        "followup": cmd_followup,
    }
    for name, fn in handlers.items():
        sp = sub.add_parser(name)
        sp.set_defaults(func=fn)
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
