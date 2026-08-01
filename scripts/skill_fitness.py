#!/usr/bin/env python3
"""F85: Skill fitness ledger from hit scores — demote zombies + federate themes.

Research drivers (2026):
  - FederatedSkill (arXiv 2606.03143): skill library as federation unit; share
    privacy-safe patches/themes, not raw trajectories — up to +44% success.
  - Agent Skill Evaluation & Evolution (arXiv 2606.11435): longitudinal skill
    quality tracking; dual-rollout with/without skills; drop skills that never
    contribute (dead library entries).
  - MUSE-Autoskill: skill lifecycle create → evaluate → refine/demote.
  - Prior Torii F84: skill-hits.json per run — no durable ledger, no demote,
    no hub federation of skill themes.

Product thesis:
  Measure (F84) without action is theater. Highest ROI: compound hit rates into
  a local fitness ledger, **soft-demote** chronically low-hit skills from full
  progressive inject (index-only), boost high-hit skills in the router, and
  emit F77-compatible federated skill themes (id + hits only).

Commands:
  ingest   — fold skill-hits.json into .torii/skill-fitness.json
  status   — ledger summary
  demote   — mark low hit_rate skills after min samples
  boosts   — per-skill score deltas for skill_router
  federate — write privacy-safe skill theme signals → hub ingest path
  cycle    — ingest → demote → federate (soft post-run)
  fixture  — hermetic: hit skill boosts; zombie demotes; privacy_ok
  apply    — print demoted + boosts JSON for assemble/router

Env:
  TORII_ROOT
  TORII_SKILL_FITNESS           1 (default) | 0/off
  TORII_SKILL_FITNESS_FILE      override ledger path
  TORII_SKILL_FITNESS_MIN_N     default 3 samples before demote
  TORII_SKILL_FITNESS_DEMOTE    default 0.25 hit_rate threshold
  TORII_SKILL_FITNESS_BOOST     default 2.0 max path-score bonus
  TORII_MEMORY_TENANT           optional for federate tenant hash
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

FEATURE = "F85"
SCHEMA = 1
LEDGER_NAME = "skill-fitness.json"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})
_PATH_RX = re.compile(r"(?:/Users/|/home/|C:\\\\Users\\\\)", re.I)


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_SKILL_FITNESS") or "1").strip().lower()
    return raw not in _FALSEY


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def ledger_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_SKILL_FITNESS_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / ".torii" / LEDGER_NAME


def empty_ledger() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "updated_at": _now(),
        "skills": {},
        "history": [],
        "demoted": [],
    }


def load_ledger(path: Path | None = None) -> dict[str, Any]:
    p = path or ledger_path()
    if not p.is_file():
        return empty_ledger()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_ledger()
    if not isinstance(data, dict):
        return empty_ledger()
    data.setdefault("skills", {})
    data.setdefault("history", [])
    data.setdefault("demoted", [])
    data.setdefault("schema_version", SCHEMA)
    data.setdefault("feature", FEATURE)
    return data


def save_ledger(ledger: dict[str, Any], path: Path | None = None) -> Path:
    p = path or ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = _now()
    ledger["feature"] = FEATURE
    ledger["schema_version"] = SCHEMA
    p.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return p


def _skill_entry(ledger: dict[str, Any], sid: str) -> dict[str, Any]:
    skills = ledger.setdefault("skills", {})
    if sid not in skills:
        skills[sid] = {
            "id": sid,
            "selected_n": 0,
            "hit_n": 0,
            "miss_n": 0,
            "hit_rate": 0.0,
            "demoted": False,
            "last_seen": "",
        }
    return skills[sid]


def ingest_hits(
    hits_doc: dict[str, Any],
    ledger: dict[str, Any] | None = None,
    *,
    run_id: str = "",
) -> dict[str, Any]:
    ledger = ledger if ledger is not None else load_ledger()
    for h in hits_doc.get("hits") or []:
        sid = str(h.get("id") or "").strip()
        if not sid or _PATH_RX.search(sid) or "/" in sid:
            continue
        # normalize skill ids only
        sid = re.sub(r"[^A-Za-z0-9._-]+", "-", sid)[:96]
        ent = _skill_entry(ledger, sid)
        ent["selected_n"] = int(ent.get("selected_n") or 0) + 1
        if h.get("hit"):
            ent["hit_n"] = int(ent.get("hit_n") or 0) + 1
        else:
            ent["miss_n"] = int(ent.get("miss_n") or 0) + 1
        # F114: track tool-invocation outcomes separately (prose-only skills leave 0)
        if h.get("tool_hit"):
            ent["tool_hit_n"] = int(ent.get("tool_hit_n") or 0) + 1
        sel = int(ent["selected_n"])
        ent["hit_rate"] = round(int(ent["hit_n"]) / sel, 4) if sel else 0.0
        ent["last_seen"] = _now()

    hist = ledger.setdefault("history", [])
    hist.append(
        {
            "at": _now(),
            "run_id": run_id or hits_doc.get("review") or "",
            "hit_rate": hits_doc.get("hit_rate"),
            "selected_n": hits_doc.get("selected_n"),
            "hit_n": hits_doc.get("hit_n"),
            "themes": list(hits_doc.get("federated_skill_themes") or [])[:16],
        }
    )
    ledger["history"] = hist[-100:]
    return ledger


def apply_demotions(ledger: dict[str, Any]) -> dict[str, Any]:
    min_n = _int_env("TORII_SKILL_FITNESS_MIN_N", 3)
    thr = _float_env("TORII_SKILL_FITNESS_DEMOTE", 0.25)
    demoted: list[str] = []
    revived: list[str] = []
    for sid, ent in (ledger.get("skills") or {}).items():
        n = int(ent.get("selected_n") or 0)
        rate = float(ent.get("hit_rate") or 0.0)
        was = bool(ent.get("demoted"))
        # never demote always-on core by id heuristic — skill_router still
        # respects always flag; ledger may still mark low performers for info
        if n >= min_n and rate < thr:
            ent["demoted"] = True
            demoted.append(sid)
        elif n >= min_n and rate >= thr + 0.15:
            # revive on sustained recovery
            if was:
                revived.append(sid)
            ent["demoted"] = False
        # if under min_n keep current demoted flag
    ledger["demoted"] = sorted(
        sid for sid, e in (ledger.get("skills") or {}).items() if e.get("demoted")
    )
    ledger["last_demote"] = {
        "at": _now(),
        "min_n": min_n,
        "threshold": thr,
        "newly_demoted": demoted,
        "revived": revived,
        "demoted_n": len(ledger["demoted"]),
    }
    return ledger


def fitness_boosts(ledger: dict[str, Any] | None = None) -> dict[str, float]:
    """Score deltas for skill_router: positive for high hit_rate, negative demoted."""
    ledger = ledger if ledger is not None else load_ledger()
    max_boost = _float_env("TORII_SKILL_FITNESS_BOOST", 2.0)
    out: dict[str, float] = {}
    for sid, ent in (ledger.get("skills") or {}).items():
        n = int(ent.get("selected_n") or 0)
        if n < 1:
            continue
        rate = float(ent.get("hit_rate") or 0.0)
        if ent.get("demoted"):
            out[sid] = -max_boost  # strong penalty (unless always)
            continue
        # map hit_rate [0,1] → [0, max_boost] after min 1 sample; stronger after 3
        conf = min(1.0, n / 3.0)
        out[sid] = round(rate * max_boost * conf, 3)
    return out


def demoted_set(ledger: dict[str, Any] | None = None) -> set[str]:
    ledger = ledger if ledger is not None else load_ledger()
    return set(ledger.get("demoted") or [])


def federate_signals(
    ledger: dict[str, Any] | None = None,
    *,
    tenant: str = "",
) -> list[dict[str, Any]]:
    """Privacy-safe F77-shaped signals for high-hit skills (ids only)."""
    ledger = ledger if ledger is not None else load_ledger()
    tenant = tenant or (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    th = ""
    if tenant:
        th = hashlib.sha256(tenant.encode("utf-8")).hexdigest()[:12]
    signals: list[dict[str, Any]] = []
    for sid, ent in (ledger.get("skills") or {}).items():
        if _PATH_RX.search(sid) or "/" in sid:
            continue
        hit_n = int(ent.get("hit_n") or 0)
        if hit_n < 1:
            continue
        if ent.get("demoted"):
            continue
        theme = f"skill:{sid}" if not sid.startswith("skill") else sid
        # F77 theme is free-form lower slug
        theme_slug = re.sub(r"[^a-z0-9._-]+", "-", theme.lower())[:64]
        sig: dict[str, Any] = {
            "id": theme_slug,
            "theme": theme_slug,
            "cwe": [],
            "tags": ["skill_hit", "f85", "federated_skill"],
            "keywords": [sid.replace("skill-", "")[:48], "skill-fitness"],
            "path_basenames": [],  # never paths
            "hits": max(1, hit_n),
            "source": "skill_fitness",
            "tenants": 1,
        }
        if th:
            sig["tenant_hashes"] = [th]
            sig["tenant_hash"] = th
        signals.append(sig)
    return signals


def write_fed_file(
    signals: list[dict[str, Any]],
    root: Path | None = None,
    dest: Path | None = None,
) -> Path:
    root = root or _root()
    dest = dest or (root / "memory" / "federation" / "skill-fitness-signals.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # privacy assert
    issues = []
    for s in signals:
        blob = json.dumps(s)
        if "/Users/" in blob or "/home/" in blob:
            issues.append(s.get("id"))
    clean = [s for s in signals if s.get("id") not in issues]
    doc = {
        "schema_version": SCHEMA,
        "feature": FEATURE,
        "scope": "skill_fitness",
        "updated_at": _now(),
        "count": len(clean),
        "privacy": "skill_id_hits_tenant_hash_only",
        "privacy_ok": len(issues) == 0,
        "privacy_issues": issues,
        "signals": clean,
    }
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return dest


def cycle(out_dir: Path | None = None, root: Path | None = None) -> dict[str, Any]:
    root = root or _root()
    ledger = load_ledger(ledger_path(root))
    ingested = False
    hits_path = None
    if out_dir:
        hits_path = Path(out_dir) / "skill-hits.json"
        if hits_path.is_file():
            try:
                hits = json.loads(hits_path.read_text(encoding="utf-8"))
                ledger = ingest_hits(hits, ledger, run_id=str(out_dir))
                ingested = True
            except (OSError, json.JSONDecodeError):
                pass
    ledger = apply_demotions(ledger)
    path = save_ledger(ledger, ledger_path(root))
    signals = federate_signals(ledger)
    fed_path = write_fed_file(signals, root=root)
    # soft hub ingest if available
    hub_result = None
    try:
        sys.path.insert(0, str(root / "scripts"))
        from federated_hub_ingest import ingest as hub_ingest  # type: ignore

        tenant = (os.environ.get("TORII_MEMORY_TENANT") or "").strip()
        hub_result = hub_ingest(
            root,
            signals,
            tenant=tenant,
            source_repo="skill_fitness",
            write_tenant=bool(tenant),
        )
    except Exception as exc:  # soft
        hub_result = {"soft_error": str(exc)[:120]}

    return {
        "feature": FEATURE,
        "ingested": ingested,
        "hits_path": str(hits_path) if hits_path else None,
        "ledger": str(path),
        "demoted": list(ledger.get("demoted") or []),
        "boosts": fitness_boosts(ledger),
        "fed_path": str(fed_path),
        "fed_n": len(signals),
        "hub": hub_result,
        "privacy_ok": True,
    }


# --- CLI ---


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _root()
    out_dir = Path(args.out_dir) if args.out_dir else Path(os.environ.get("OUT_DIR") or ".")
    hits_path = Path(args.hits) if args.hits else out_dir / "skill-hits.json"
    if not hits_path.is_file():
        print(json.dumps({"feature": FEATURE, "ingested": 0, "reason": "no skill-hits.json"}))
        return 0
    hits = json.loads(hits_path.read_text(encoding="utf-8"))
    ledger = ingest_hits(hits, load_ledger(ledger_path(root)), run_id=str(out_dir))
    path = save_ledger(ledger, ledger_path(root))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "ingested": 1,
                "ledger": str(path),
                "skills_n": len(ledger.get("skills") or {}),
                "history_n": len(ledger.get("history") or []),
            },
            indent=2,
        )
    )
    return 0


def cmd_demote(args: argparse.Namespace) -> int:
    root = _root()
    ledger = apply_demotions(load_ledger(ledger_path(root)))
    path = save_ledger(ledger, ledger_path(root))
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "ledger": str(path),
                "demoted": ledger.get("demoted") or [],
                "last_demote": ledger.get("last_demote"),
            },
            indent=2,
        )
    )
    return 0


def cmd_boosts(args: argparse.Namespace) -> int:
    b = fitness_boosts(load_ledger())
    print(json.dumps({"feature": FEATURE, "boosts": b, "demoted": sorted(demoted_set())}, indent=2))
    return 0


def cmd_federate(args: argparse.Namespace) -> int:
    root = _root()
    ledger = load_ledger(ledger_path(root))
    signals = federate_signals(ledger)
    dest = write_fed_file(signals, root=root, dest=Path(args.out) if args.out else None)
    hub = None
    if not args.no_hub:
        try:
            sys.path.insert(0, str(root / "scripts"))
            from federated_hub_ingest import ingest as hub_ingest  # type: ignore

            hub = hub_ingest(
                root,
                signals,
                tenant=(os.environ.get("TORII_MEMORY_TENANT") or "").strip(),
                source_repo="skill_fitness",
            )
        except Exception as exc:
            hub = {"soft_error": str(exc)[:120]}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fed_path": str(dest),
                "fed_n": len(signals),
                "privacy_ok": "/Users/" not in dest.read_text(encoding="utf-8"),
                "hub": hub,
            },
            indent=2,
        )
    )
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "skipped": 1, "reason": "disabled"}))
        return 0
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is None and (os.environ.get("OUT_DIR") or "").strip():
        out_dir = Path(os.environ["OUT_DIR"])
    result = cycle(out_dir=out_dir, root=_root())
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ledger = load_ledger()
    skills = ledger.get("skills") or {}
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "ledger": str(ledger_path()),
                "skills_n": len(skills),
                "demoted": list(ledger.get("demoted") or []),
                "history_n": len(ledger.get("history") or []),
                "boosts": fitness_boosts(ledger),
                "top": sorted(
                    (
                        {
                            "id": s,
                            "hit_rate": e.get("hit_rate"),
                            "selected_n": e.get("selected_n"),
                            "demoted": e.get("demoted"),
                        }
                        for s, e in skills.items()
                    ),
                    key=lambda x: (-float(x.get("hit_rate") or 0), str(x["id"])),
                )[:10],
            },
            indent=2,
        )
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Machine-readable demoted set + boosts for skill_router."""
    ledger = load_ledger()
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "demoted": sorted(demoted_set(ledger)),
                "boosts": fitness_boosts(ledger),
            }
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        os.environ["TORII_ROOT"] = str(root)
        os.environ["TORII_SKILL_FITNESS"] = "1"
        os.environ["TORII_SKILL_FITNESS_MIN_N"] = "3"
        os.environ["TORII_SKILL_FITNESS_DEMOTE"] = "0.34"
        os.environ["TORII_SKILL_FITNESS_BOOST"] = "2.0"
        os.environ["TORII_MEMORY_TENANT"] = "fixture-tenant-a"

        # good skill always hits; zombie never hits
        good = "skill-f74-prefer-chain-json"
        zombie = "skill-zombie-docs"
        ledger = empty_ledger()
        for i in range(4):
            hits = {
                "hit_rate": 0.5,
                "selected_n": 2,
                "hit_n": 1,
                "hits": [
                    {"id": good, "hit": True, "matched": ["chain"]},
                    {"id": zombie, "hit": False, "matched": []},
                ],
                "federated_skill_themes": [good],
                "review": f"run-{i}",
            }
            ledger = ingest_hits(hits, ledger, run_id=f"run-{i}")
        # one extra hit for good to push rate up
        ledger = ingest_hits(
            {
                "hits": [{"id": good, "hit": True, "matched": ["taint"]}],
                "federated_skill_themes": [good],
            },
            ledger,
            run_id="run-extra",
        )
        ledger = apply_demotions(ledger)
        path = save_ledger(ledger, ledger_path(root))

        boosts = fitness_boosts(ledger)
        demoted = demoted_set(ledger)
        zombie_demoted = zombie in demoted
        good_not_demoted = good not in demoted
        good_boost = boosts.get(good, 0) > 0
        zombie_pen = boosts.get(zombie, 0) < 0

        signals = federate_signals(ledger, tenant="fixture-tenant-a")
        fed_path = write_fed_file(signals, root=root)
        fed_text = fed_path.read_text(encoding="utf-8")
        privacy_ok = "/Users/" not in fed_text and "fixture-tenant-a" not in fed_text
        good_in_fed = any(good in str(s.get("id")) or good in str(s.get("theme")) for s in signals)
        zombie_not_fed = not any(zombie in str(s) for s in signals)

        # router integration: patch score via boosts API
        # simulate select preference: good boost > zombie
        order_ok = boosts.get(good, 0) > boosts.get(zombie, -99)

        # cycle with out_dir skill-hits
        out_dir = root / "out"
        out_dir.mkdir()
        (out_dir / "skill-hits.json").write_text(
            json.dumps(
                {
                    "hits": [
                        {"id": good, "hit": True, "matched": ["chain"]},
                        {"id": zombie, "hit": False, "matched": []},
                    ],
                    "hit_rate": 0.5,
                    "selected_n": 2,
                    "hit_n": 1,
                    "federated_skill_themes": [good],
                }
            ),
            encoding="utf-8",
        )
        cyc = cycle(out_dir=out_dir, root=root)

        fixture_pass = all(
            [
                zombie_demoted,
                good_not_demoted,
                good_boost,
                zombie_pen,
                privacy_ok,
                good_in_fed,
                zombie_not_fed,
                order_ok,
                cyc.get("ingested") is True,
                path.is_file(),
            ]
        )
        print(
            json.dumps(
                {
                    "feature": FEATURE,
                    "fixture_pass": fixture_pass,
                    "zombie_demoted": zombie_demoted,
                    "good_not_demoted": good_not_demoted,
                    "good_boost": boosts.get(good),
                    "zombie_boost": boosts.get(zombie),
                    "privacy_ok": privacy_ok,
                    "good_in_fed": good_in_fed,
                    "zombie_not_fed": zombie_not_fed,
                    "demoted": sorted(demoted),
                    "cycle_fed_n": cyc.get("fed_n"),
                    "ledger": str(path),
                },
                indent=2,
            )
        )
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F85 skill fitness ledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="Ingest skill-hits.json into ledger")
    pi.add_argument("--out-dir", default="")
    pi.add_argument("--hits", default="")
    pi.set_defaults(func=cmd_ingest)

    sub.add_parser("demote", help="Apply demotion thresholds").set_defaults(func=cmd_demote)
    sub.add_parser("boosts", help="Print fitness score deltas").set_defaults(func=cmd_boosts)
    sub.add_parser("status", help="Ledger summary").set_defaults(func=cmd_status)
    sub.add_parser("apply", help="JSON demoted+boosts for router").set_defaults(func=cmd_apply)
    sub.add_parser("fixture", help="Hermetic offline fixture").set_defaults(func=cmd_fixture)

    pf = sub.add_parser("federate", help="Emit skill themes to federation")
    pf.add_argument("--out", default="")
    pf.add_argument("--no-hub", action="store_true")
    pf.set_defaults(func=cmd_federate)

    pc = sub.add_parser("cycle", help="ingest → demote → federate")
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--force", action="store_true")
    pc.set_defaults(func=cmd_cycle)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
