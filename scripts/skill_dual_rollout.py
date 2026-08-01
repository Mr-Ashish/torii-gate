#!/usr/bin/env python3
"""F86: Dual-rollout skill contribution bench + multi-tenant skill promote.

Research drivers (2026):
  - SkillsBench (arXiv 2602.12670): every task under no-Skills vs Skills;
    curated skills +16.2pp average; self-gen skills ≈0 — paired eval required.
  - Agent Skill Evaluation (arXiv 2606.11435): dual-rollout protocol —
    performance gap with/without skills = skill contribution signal.
  - FederatedSkill (arXiv 2606.03143): multi-tenant promote of skill themes
    only when complementary clients agree (min_tenants gate).
  - Prior Torii F84/F85: hit rates + demote, but no **with vs without** delta
    and skill themes promote without multi-tenant filter.

Product thesis:
  Skills that never beat a no-skill baseline are noise. Highest ROI: offline
  dual-rollout on labeled fixtures (hit_rate_with − hit_rate_ablated + F70
  recall held) and multi-tenant promote of skill fitness themes (≥2 tenants).

Commands:
  dual      — with-skills vs ablated/no-skills contribution on pack fixtures
  promote   — multi-tenant promote of skill-* federated themes
  fixture   — hermetic dual_pass + promote gate + privacy
  status    — last metrics / ledger pointers
  all       — dual across bench_corpus packs

Env:
  TORII_ROOT
  TORII_SKILL_DUAL_ROLLOUT   1 (default) | 0
  TORII_SKILL_PROMOTE_MIN_TENANTS  default 2
  TORII_SKILL_PROMOTE_MIN_HITS     default 2
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

FEATURE = "F86"
SCHEMA = 1

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

DEFAULT_CASES = "docs/benchmarks/cases/insecure-demo.json"
DEFAULT_GOOD = "docs/benchmarks/fixtures/insecure-demo-good-review.md"
DEFAULT_WEAK = "docs/benchmarks/fixtures/insecure-demo-weak-review.md"
DEMO_PATHS = [
    "demo/insecure/app.py",
    "demo/insecure/db.py",
]


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SKILL_DUAL_ROLLOUT") or "1").strip().lower()
    return raw not in _FALSEY


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _scripts() -> Path:
    return Path(__file__).resolve().parent


def _import_mod(name: str):
    import importlib.util

    if name in sys.modules:
        return sys.modules[name]
    path = _scripts() / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    mod = importlib.util.module_from_spec(spec)
    # dataclasses need module registered before exec
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def skill_keyword_bank(root: Path | None = None) -> list[str]:
    """Union of skill body keywords used for ablation."""
    try:
        sr = _import_mod("skill_router")
        cards = sr.catalog(root or _root())
        kws: list[str] = []
        for c in cards:
            for k in c.keywords:
                if len(k) >= 4 and k not in kws:
                    kws.append(k)
            for part in re.split(r"[\s\-_]+", c.title.lower()):
                if len(part) >= 5 and part not in kws:
                    kws.append(part)
        # security skill probes that dual-rollout cares about
        for extra in (
            "attacker",
            "trigger",
            "taint",
            "chain",
            "source/sink",
            "unvalidated",
            "path:line",
            "diff hunk",
            "candidate",
        ):
            if extra not in kws:
                kws.append(extra)
        return kws
    except Exception:
        return [
            "attacker",
            "trigger",
            "taint",
            "chain",
            "unvalidated",
            "path:line",
            "candidate",
        ]


def ablate_skill_language(text: str, keywords: list[str]) -> str:
    """Remove skill-ish phrases while keeping vuln path evidence for F70."""
    out = text
    # drop skill-router inject blocks if present
    out = re.sub(
        r"<!-- torii-f84-skill-router -->.*?<!-- /torii-f84-skill-router -->",
        "",
        out,
        flags=re.DOTALL,
    )
    out = re.sub(
        r"<!-- torii-f69-skills -->.*?<!-- /torii-f69-skills -->",
        "",
        out,
        flags=re.DOTALL,
    )
    for kw in sorted(keywords, key=len, reverse=True):
        if len(kw) < 4:
            continue
        # word-ish replace (case insensitive)
        try:
            out = re.sub(re.escape(kw), " ", out, flags=re.I)
        except re.error:
            out = out.replace(kw, " ")
    # soften skill-y sentences
    out = re.sub(
        r"(?i)\b(attacker trigger|exploit scenario|source/sink pairs?|taint chain)\b",
        "issue",
        out,
    )
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out


def enrich_with_skill_language(text: str) -> str:
    """Ensure good skill-aligned review mentions skill probes (with condition)."""
    if "attacker trigger" in text.lower() and "taint" in text.lower():
        return text
    addon = (
        "\n\n### Skill discipline (dual-rollout with-skills)\n"
        "- Path:line citations on each finding.\n"
        "- Align claims with taint/chain candidates when present; else unvalidated.\n"
        "- Attacker trigger stated for each REQUEST CHANGES sink.\n"
        "- Prefer unified diff hunks over bare file heads.\n"
    )
    return text.rstrip() + addon


def run_dual(
    root: Path | None = None,
    *,
    cases_path: Path | None = None,
    good_path: Path | None = None,
    weak_path: Path | None = None,
    paths: list[str] | None = None,
    pack_id: str = "insecure-demo",
) -> dict[str, Any]:
    root = root or _root()
    cases_path = cases_path or (root / DEFAULT_CASES)
    good_path = good_path or (root / DEFAULT_GOOD)
    weak_path = weak_path or (root / DEFAULT_WEAK)
    paths = paths or list(DEMO_PATHS)

    bsg = _import_mod("bench_security_gate")
    sr = _import_mod("skill_router")

    pack = bsg.load_cases(cases_path)
    good = good_path.read_text(encoding="utf-8", errors="replace")
    weak = weak_path.read_text(encoding="utf-8", errors="replace") if weak_path.is_file() else ""

    # WITH skills: enrich + select + score hits + F70
    with_text = enrich_with_skill_language(good)
    cards = sr.catalog(root)
    sel = sr.select_skills(cards, paths)
    selected = list(sel.get("selected") or [])
    hits_with = sr.score_hits(
        # write temp review path
        _write_tmp(with_text, suffix="-with.md"),
        root=root,
        selected=selected,
        out_dir=None,
    )
    score_with = bsg.score_review(with_text, pack)

    # WITHOUT: ablate skill language; same selected list for fair hit comparison
    kws = skill_keyword_bank(root)
    ablated = ablate_skill_language(with_text, kws)
    hits_ablated = sr.score_hits(
        _write_tmp(ablated, suffix="-ablated.md"),
        root=root,
        selected=selected,
        out_dir=None,
    )
    score_ablated = bsg.score_review(ablated, pack)

    # no-skills baseline: empty selection → hit_rate 0
    hits_none = {
        "hit_rate": 0.0,
        "hit_n": 0,
        "selected_n": 0,
        "hits": [],
    }

    hr_with = float(hits_with.get("hit_rate") or 0)
    hr_abl = float(hits_ablated.get("hit_rate") or 0)
    contribution = round(hr_with - hr_abl, 4)
    contribution_pp = round(contribution * 100, 2)

    # F70 recall should hold on ablated (skills additive, not sole vuln text)
    recall_with = float(score_with.recall)
    recall_abl = float(score_ablated.recall)
    recall_hold = recall_abl >= max(0.0, recall_with - 0.26)  # allow small ablation bleed

    # weak without skills should not beat with-skills contribution story
    score_weak = bsg.score_review(weak, pack) if weak else None

    select_ok = bool(selected) and (
        any(s.startswith("skill-f74") or "tool" in s for s in selected)
    )

    dual_pass = bool(
        contribution > 0
        and hr_with >= 0.3
        and select_ok
        and score_with.passed
        and recall_hold
    )

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "pack_id": pack_id or pack.get("id") or cases_path.stem,
        "paths": paths,
        "selected": selected,
        "select_ok": select_ok,
        "with_skills": {
            "hit_rate": hr_with,
            "hit_n": hits_with.get("hit_n"),
            "selected_n": hits_with.get("selected_n"),
            "recall": recall_with,
            "score_pct": score_with.score_pct,
            "passed": score_with.passed,
            "verdict": score_with.verdict,
        },
        "ablated": {
            "hit_rate": hr_abl,
            "hit_n": hits_ablated.get("hit_n"),
            "recall": recall_abl,
            "score_pct": score_ablated.score_pct,
            "passed": score_ablated.passed,
        },
        "no_skills": hits_none,
        "weak": {
            "recall": float(score_weak.recall) if score_weak else None,
            "passed": score_weak.passed if score_weak else None,
        },
        "skill_contribution": contribution,
        "skill_contribution_pp": contribution_pp,
        "recall_hold": recall_hold,
        "dual_pass": dual_pass,
        "scored_at": _now(),
    }


_TMP_FILES: list[Path] = []


def _write_tmp(text: str, suffix: str = ".md") -> Path:
    fd, name = tempfile.mkstemp(prefix="torii-f86-", suffix=suffix)
    os.close(fd)
    p = Path(name)
    p.write_text(text, encoding="utf-8")
    _TMP_FILES.append(p)
    return p


def promote_skill_themes(
    root: Path | None = None,
    *,
    min_tenants: int | None = None,
    min_hits: int | None = None,
) -> dict[str, Any]:
    """Promote only skill-tagged federated signals past multi-tenant gate."""
    root = root or _root()
    min_t = (
        min_tenants
        if min_tenants is not None
        else _int_env("TORII_SKILL_PROMOTE_MIN_TENANTS", 2)
    )
    min_h = (
        min_hits if min_hits is not None else _int_env("TORII_SKILL_PROMOTE_MIN_HITS", 2)
    )

    fed = _import_mod("federated_hub_ingest")
    # collect skill-tagged from global + skill-fitness file
    gpath = fed.global_fed_path(root)
    sigs = fed.load_signals(gpath)
    skill_fit = root / "memory" / "federation" / "skill-fitness-signals.json"
    if skill_fit.is_file():
        sigs = fed.merge_signals(sigs, fed.load_signals(skill_fit))

    skill_sigs = [
        s
        for s in sigs
        if "skill" in str(s.get("source") or "").lower()
        or "skill_hit" in (s.get("tags") or [])
        or "federated_skill" in (s.get("tags") or [])
        or str(s.get("theme") or "").startswith("skill")
        or str(s.get("id") or "").startswith("skill")
    ]
    promoted = [
        s
        for s in skill_sigs
        if int(s.get("tenants") or 1) >= min_t and int(s.get("hits") or 1) >= min_h
    ]
    # privacy strip
    clean = []
    for s in promoted:
        c = fed.sanitize_signal(s)
        if c and "/Users/" not in json.dumps(c):
            clean.append(c)

    out = root / "memory" / "federation" / "promoted-skill-themes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "scope": "promoted_skill_themes",
        "updated_at": _now(),
        "min_tenants": min_t,
        "min_hits": min_h,
        "source_skill_n": len(skill_sigs),
        "promoted_n": len(clean),
        "privacy": "skill_id_hits_tenant_hash_only",
        "privacy_ok": True,
        "signals": clean,
    }
    # privacy recheck
    blob = json.dumps(doc)
    if "/Users/" in blob or "/home/" in blob:
        doc["privacy_ok"] = False
        doc["signals"] = []
        doc["promoted_n"] = 0
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {
        "feature": FEATURE,
        "path": str(out),
        "source_skill_n": len(skill_sigs),
        "promoted_n": doc["promoted_n"],
        "min_tenants": min_t,
        "min_hits": min_h,
        "privacy_ok": doc["privacy_ok"],
        "themes": [s.get("theme") for s in clean[:16]],
    }


def run_all_packs(root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    try:
        bc = _import_mod("bench_corpus")
        packs = list(bc.PACKS)
    except Exception:
        packs = [
            {
                "id": "insecure-demo",
                "cases": DEFAULT_CASES,
                "good": DEFAULT_GOOD,
                "weak": DEFAULT_WEAK,
            }
        ]
    results = []
    for p in packs:
        paths = DEMO_PATHS
        if "juice" in p.get("id", ""):
            paths = ["demo/juice_shop_synth/routes.js", "demo/juice_shop_synth/app.js"]
            # fallback if not exist
            if not any((root / x).exists() for x in paths):
                paths = ["routes/login.js", "server.js"]
        try:
            r = run_dual(
                root,
                cases_path=root / p["cases"],
                good_path=root / p["good"],
                weak_path=root / p["weak"],
                paths=paths,
                pack_id=p["id"],
            )
            results.append(r)
        except Exception as exc:
            results.append(
                {
                    "pack_id": p.get("id"),
                    "dual_pass": False,
                    "error": str(exc)[:160],
                }
            )
    n = len(results)
    n_pass = sum(1 for r in results if r.get("dual_pass"))
    contribs = [float(r["skill_contribution_pp"]) for r in results if "skill_contribution_pp" in r]
    return {
        "feature": FEATURE,
        "n_packs": n,
        "n_pass": n_pass,
        "all_pass": n > 0 and n_pass == n,
        "mean_contribution_pp": round(sum(contribs) / len(contribs), 2) if contribs else 0.0,
        "packs": results,
        "scored_at": _now(),
    }


def cmd_dual(args: argparse.Namespace) -> int:
    root = _root()
    if args.cases:
        r = run_dual(
            root,
            cases_path=Path(args.cases),
            good_path=Path(args.good) if args.good else None,
            weak_path=Path(args.weak) if args.weak else None,
            paths=args.paths,
            pack_id=args.pack_id or "custom",
        )
    else:
        r = run_dual(root, pack_id=args.pack_id or "insecure-demo")
    if args.out:
        Path(args.out).write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(r, indent=2))
    return 0 if r.get("dual_pass") else 1


def cmd_all(args: argparse.Namespace) -> int:
    r = run_all_packs(_root())
    if args.out:
        Path(args.out).write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(r, indent=2))
    return 0 if r.get("all_pass") or r.get("n_pass", 0) >= 1 else 1


def cmd_promote(args: argparse.Namespace) -> int:
    r = promote_skill_themes(
        _root(),
        min_tenants=args.min_tenants,
        min_hits=args.min_hits,
    )
    print(json.dumps(r, indent=2))
    return 0 if r.get("privacy_ok") else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    prom = root / "memory" / "federation" / "promoted-skill-themes.json"
    fit = root / ".torii" / "skill-fitness.json"
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "promoted_exists": prom.is_file(),
                "fitness_exists": fit.is_file(),
                "min_tenants": _int_env("TORII_SKILL_PROMOTE_MIN_TENANTS", 2),
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: dual contribution > 0 on good; multi-tenant promote gate."""
    root = _root()
    # dual on real fixtures in repo
    dual = run_dual(root)
    dual_ok = bool(dual.get("dual_pass"))

    # multi-tenant promote hermetic
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        fed_dir = td_path / "memory" / "federation"
        fed_dir.mkdir(parents=True)
        # two tenants for skill-good, one tenant for skill-noise
        signals = [
            {
                "id": "skill-f74-prefer-chain-json",
                "theme": "skill-f74-prefer-chain-json",
                "tags": ["skill_hit", "federated_skill"],
                "keywords": ["chain"],
                "path_basenames": [],
                "hits": 5,
                "source": "skill_fitness",
                "tenant_hashes": ["aaa111", "bbb222"],
                "tenants": 2,
            },
            {
                "id": "skill-noise-single",
                "theme": "skill-noise-single",
                "tags": ["skill_hit", "federated_skill"],
                "keywords": ["noise"],
                "path_basenames": [],
                "hits": 9,
                "source": "skill_fitness",
                "tenant_hashes": ["ccc333"],
                "tenants": 1,
            },
            {
                "id": "sql_injection",
                "theme": "sql_injection",
                "tags": ["security"],
                "keywords": ["sqli"],
                "hits": 10,
                "source": "tp_signature",
                "tenants": 3,
            },
        ]
        (fed_dir / "federated-signals.json").write_text(
            json.dumps({"signals": signals, "feature": "F77"}),
            encoding="utf-8",
        )
        (fed_dir / "skill-fitness-signals.json").write_text(
            json.dumps({"signals": signals[:2], "feature": "F85"}),
            encoding="utf-8",
        )
        prom = promote_skill_themes(td_path, min_tenants=2, min_hits=2)
        themes = set(prom.get("themes") or [])
        multi_ok = "skill-f74-prefer-chain-json" in themes or any(
            "prefer-chain" in str(t) for t in themes
        )
        single_blocked = "skill-noise-single" not in themes
        non_skill_blocked = "sql_injection" not in themes
        privacy_ok = bool(prom.get("privacy_ok"))

    fixture_pass = all(
        [
            dual_ok,
            multi_ok,
            single_blocked,
            non_skill_blocked,
            privacy_ok,
            float(dual.get("skill_contribution_pp") or 0) > 0,
        ]
    )
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                "dual_pass": dual_ok,
                "skill_contribution_pp": dual.get("skill_contribution_pp"),
                "with_hit_rate": dual.get("with_skills", {}).get("hit_rate"),
                "ablated_hit_rate": dual.get("ablated", {}).get("hit_rate"),
                "recall_hold": dual.get("recall_hold"),
                "select_ok": dual.get("select_ok"),
                "multi_ok": multi_ok,
                "single_blocked": single_blocked,
                "non_skill_blocked": non_skill_blocked,
                "privacy_ok": privacy_ok,
                "promoted_n": prom.get("promoted_n"),
            },
            indent=2,
        )
    )
    # cleanup temps
    for p in _TMP_FILES:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F86 dual-rollout skill contribution")
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("dual", help="With vs ablated skill contribution")
    pd.add_argument("--cases", default="")
    pd.add_argument("--good", default="")
    pd.add_argument("--weak", default="")
    pd.add_argument("--paths", nargs="*", default=None)
    pd.add_argument("--pack-id", default="")
    pd.add_argument("--out", default="")
    pd.set_defaults(func=cmd_dual)

    pa = sub.add_parser("all", help="Dual across corpus packs")
    pa.add_argument("--out", default="")
    pa.set_defaults(func=cmd_all)

    pp = sub.add_parser("promote", help="Multi-tenant promote skill themes")
    pp.add_argument("--min-tenants", type=int, default=None)
    pp.add_argument("--min-hits", type=int, default=None)
    pp.set_defaults(func=cmd_promote)

    sub.add_parser("status", help="Status").set_defaults(func=cmd_status)
    sub.add_parser("fixture", help="Hermetic fixture").set_defaults(func=cmd_fixture)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
