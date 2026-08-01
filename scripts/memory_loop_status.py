#!/usr/bin/env python3
"""F96: Memory compound loop readiness scorecard (write→recall→consolidate→critic→federate).

Research / product drivers:
  - Loop Engineering readiness scorecards L0–L3 (skill_loop F91 pattern)
  - Memory stack F70–F95 shipped intelligence; ops could not answer
    "is the memory path ready on this checkout?"
  - F95 federated effective scores; F75 inject must prefer promoted strength

Product thesis:
  One deterministic status for the **memory compound loop** so installs, smoke,
  and Hub demos prove write policy + consolidation + effective critic +
  federation + scoped inject are present and green.

Loop stages:
  write (F93) → consolidate (F94) → effective_critic (F95) → federate (F77/F95)
  → scoped_recall (F75/F96) → tp_promote (F70)

Commands:
  status    — full JSON readiness
  scorecard — compact level + stage flags
  fixture   — hermetic offline pass on product tree (expects L3)
  markdown  — short MD block for install-guide / PRODUCT

Env:
  TORII_ROOT
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F96"
SCHEMA = 1

LOOP_STAGES: list[dict[str, Any]] = [
    {
        "id": "write",
        "feature": "F93",
        "script": "memory_event_policy.py",
        "fixture_cmd": ["fixture"],
        "one_liner": "Mem0 ADD/UPDATE/DELETE/NONE write policy",
    },
    {
        "id": "consolidate",
        "feature": "F94",
        "script": "memory_consolidate.py",
        "fixture_cmd": ["fixture"],
        "one_liner": "Importance · merge · decay · eviction",
    },
    {
        "id": "effective_critic",
        "feature": "F95",
        "script": "bench_security_gate.py",
        "fixture_cmd": ["fixture"],
        "one_liner": "Dual-pass TP confirm gated by effective_score",
    },
    {
        "id": "federate",
        "feature": "F77/F95",
        "script": "federated_hub_ingest.py",
        "fixture_cmd": ["fixture"],
        "one_liner": "Privacy-safe multi-tenant + effective strength",
    },
    {
        "id": "scoped_recall",
        "feature": "F75/F96",
        "script": "scoped_memory_recall.py",
        "fixture_cmd": ["fixture"],
        "one_liner": "Budgeted inject ranked by path + effective",
    },
    {
        "id": "tiers",
        "feature": "F97",
        "script": "memory_tiers.py",
        "fixture_cmd": ["fixture"],
        "one_liner": "Letta-style core vs archival inject budgets",
    },
    {
        "id": "archival_search",
        "feature": "F98",
        "script": "archival_memory_search.py",
        "fixture_cmd": ["fixture"],
        "one_liner": "MemGPT-style search cold stores + promote to core",
    },
    {
        "id": "tp_store",
        "feature": "F70",
        "script": "bench_security_gate.py",
        "one_liner": "Durable tp-signatures promote path",
        "soft_only": True,
    },
]


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scripts(root: Path) -> Path:
    return root / "scripts"


def check_script(root: Path, name: str) -> bool:
    return (_scripts(root) / name).is_file()


def pack_lists_script(root: Path, name: str) -> bool:
    install = root / "scripts" / "install-torii.sh"
    if not install.is_file():
        return False
    text = install.read_text(encoding="utf-8", errors="replace")
    return name in text


def run_soft_fixture(root: Path, script: str, args: list[str]) -> dict[str, Any]:
    path = _scripts(root) / script
    if not path.is_file():
        return {"ok": False, "error": "missing_script"}
    try:
        r = subprocess.run(
            [sys.executable, str(path), *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
        entry: dict[str, Any] = {"ok": r.returncode == 0, "rc": r.returncode}
        try:
            data = json.loads(r.stdout)
            entry["data_keys"] = list(data.keys())[:12]
            if "fixture_pass" in data:
                entry["fixture_pass"] = data["fixture_pass"]
                entry["ok"] = entry["ok"] and bool(data["fixture_pass"])
        except (json.JSONDecodeError, TypeError, ValueError):
            # bench_security_gate fixture prints key=value lines
            if "fixture_pass=1" in (r.stdout or ""):
                entry["fixture_pass"] = True
                entry["ok"] = True
            elif r.returncode != 0:
                entry["ok"] = False
        return entry
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def assess(root: Path | None = None, *, deep: bool = True) -> dict[str, Any]:
    root = root or _root()
    stages_out: list[dict[str, Any]] = []
    for st in LOOP_STAGES:
        script = st["script"]
        present = check_script(root, script)
        in_pack = pack_lists_script(root, script)
        entry: dict[str, Any] = {
            "id": st["id"],
            "feature": st["feature"],
            "script": script,
            "one_liner": st["one_liner"],
            "script_ok": present,
            "pack_ok": in_pack,
            "ok": present and (in_pack or st.get("soft_only")),
        }
        stages_out.append(entry)

    # wiring: assemble scoped + run consolidate/federate/events
    assemble = (
        (root / "scripts" / "assemble-context.sh").read_text(encoding="utf-8", errors="replace")
        if (root / "scripts" / "assemble-context.sh").is_file()
        else ""
    )
    run_sh = (
        (root / "scripts" / "run-torii-review.sh").read_text(encoding="utf-8", errors="replace")
        if (root / "scripts" / "run-torii-review.sh").is_file()
        else ""
    )
    bench = (
        (root / "scripts" / "bench_security_gate.py").read_text(encoding="utf-8", errors="replace")
        if (root / "scripts" / "bench_security_gate.py").is_file()
        else ""
    )
    wire = {
        "assemble_scoped_memory": "scoped_memory" in assemble or "F75" in assemble,
        "run_memory_consolidate": "memory_consolidate.py" in run_sh,
        "run_memory_federate": "federate" in run_sh and "memory_consolidate" in run_sh,
        "run_fed_promote": "federated_hub_ingest.py" in run_sh,
        "bench_effective_aware": "effective_aware" in bench or "_tp_effective" in bench,
        "scoped_promoted_pref": "promoted-signals" in (
            (root / "scripts" / "scoped_memory_recall.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "scoped_memory_recall.py").is_file()
            else ""
        ),
        "scoped_memory_tiers": "memory_tiers" in (
            (root / "scripts" / "scoped_memory_recall.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "scoped_memory_recall.py").is_file()
            else ""
        ),
        "assemble_archival_search": "archival_memory_search" in (
            (root / "scripts" / "assemble-context.sh").read_text(
                encoding="utf-8", errors="replace"
            )
            if (root / "scripts" / "assemble-context.sh").is_file()
            else ""
        ),
    }
    wire_ok = all(wire.values())

    deep_results: dict[str, Any] = {}
    if deep:
        for st in LOOP_STAGES:
            if st.get("fixture_cmd"):
                deep_results[st["id"]] = run_soft_fixture(
                    root, st["script"], list(st["fixture_cmd"])
                )

    deep_ok = True
    if deep:
        deep_ok = all(v.get("ok") for v in deep_results.values()) if deep_results else False

    stage_ok_n = sum(1 for s in stages_out if s["ok"])
    stage_total = len(stages_out)
    points = 0
    points += stage_ok_n  # max 6
    points += 1 if wire_ok else 0
    points += 2 if deep_ok else 0
    max_points = stage_total + 1 + 2  # 9
    pct = round(100.0 * points / max_points, 1) if max_points else 0.0
    if pct >= 95 and deep_ok and wire_ok and stage_ok_n == stage_total:
        level = "L3"
    elif pct >= 75:
        level = "L2"
    elif pct >= 50:
        level = "L1"
    else:
        level = "L0"

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "loop": "write → consolidate → effective_critic → federate → scoped_recall → tiers → archival_search → tp_store",
        "scored_at": _now(),
        "level": level,
        "pct": pct,
        "points": points,
        "max_points": max_points,
        "ready": level in ("L2", "L3") and stage_ok_n == stage_total,
        "stages": stages_out,
        "stages_ok": stage_ok_n,
        "stages_total": stage_total,
        "wiring": wire,
        "wiring_ok": wire_ok,
        "deep": deep_results if deep else None,
        "deep_ok": deep_ok if deep else None,
        "one_liner": "Stale memory does not confirm findings or crowd the inject budget.",
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"## Memory compound loop readiness ({FEATURE})",
        "",
        f"**Loop:** `{report.get('loop')}`  ·  **Level:** {report.get('level')}  ·  **{report.get('pct')}%**",
        "",
        report.get("one_liner") or "",
        "",
        "| Stage | Feature | Script | Pack | OK |",
        "|-------|---------|--------|:----:|:--:|",
    ]
    for s in report.get("stages") or []:
        lines.append(
            f"| {s.get('id')} | {s.get('feature')} | `{s.get('script')}` | "
            f"{'✓' if s.get('pack_ok') else '·'} | {'✓' if s.get('ok') else '✗'} |"
        )
    lines.extend(
        [
            "",
            f"- Wiring (assemble/run/bench): **{'ok' if report.get('wiring_ok') else 'gap'}**",
            f"- Deep fixtures: **{'ok' if report.get('deep_ok') else 'skipped/fail'}**",
            f"- Ready: **{report.get('ready')}**",
            "",
        ]
    )
    return "\n".join(lines)


def cmd_status(args: argparse.Namespace) -> int:
    report = assess(_root(), deep=not args.shallow)
    print(json.dumps(report, indent=2))
    return 0 if report.get("ready") else 1


def cmd_scorecard(args: argparse.Namespace) -> int:
    report = assess(_root(), deep=not args.shallow)
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "level": report["level"],
                "pct": report["pct"],
                "ready": report["ready"],
                "stages_ok": f"{report['stages_ok']}/{report['stages_total']}",
                "wiring_ok": report["wiring_ok"],
                "deep_ok": report.get("deep_ok"),
                "loop": report["loop"],
            },
            indent=2,
        )
    )
    return 0 if report.get("ready") else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    report = assess(_root(), deep=True)
    fixture_pass = (
        report.get("level") == "L3"
        and report.get("ready")
        and report.get("deep_ok")
        and report.get("wiring_ok")
    )
    out = {
        "feature": FEATURE,
        "fixture_pass": fixture_pass,
        "level": report.get("level"),
        "pct": report.get("pct"),
        "ready": report.get("ready"),
        "wiring_ok": report.get("wiring_ok"),
        "deep_ok": report.get("deep_ok"),
        "stages_ok": report.get("stages_ok"),
        "stages_total": report.get("stages_total"),
    }
    print(json.dumps(out, indent=2))
    return 0 if fixture_pass else 1


def cmd_markdown(args: argparse.Namespace) -> int:
    report = assess(_root(), deep=not args.shallow)
    print(to_markdown(report))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F96 memory compound loop readiness")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, func in (
        ("status", cmd_status),
        ("scorecard", cmd_scorecard),
        ("fixture", cmd_fixture),
        ("markdown", cmd_markdown),
    ):
        sp = sub.add_parser(name)
        sp.add_argument("--shallow", action="store_true", help="skip deep fixtures")
        sp.set_defaults(func=func)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
