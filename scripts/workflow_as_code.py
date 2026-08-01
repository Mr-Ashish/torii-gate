#!/usr/bin/env python3
"""F79: Workflows-as-code for Torii Gate pipeline + install UX guide.

Research / product drivers:
  - Loop Engineering: loops as explicit skills + readiness scorecards
  - Agent pipelines as declarative graphs (stages, soft-fail, entries)
  - Install UX deep link: show which F70–F78 capabilities ship in pack

Commands:
  validate       — workflow YAML + scripts exist on disk
  plan           — print stage graph + phases
  status         — readiness L0–L3 for this checkout
  install-guide  — end-user install + capability matrix (markdown)
  fixture        — offline validate+status pass
  scorecard      — compact JSON readiness
  pack-check     — ensure pack_scripts listed are in install-torii RUNTIME_SCRIPTS

Env:
  TORII_ROOT
  TORII_WORKFLOW_FILE   override path to torii-gate.workflow.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F79"
SCHEMA = 1
DEFAULT_WF = "docs/workflows/torii-gate.workflow.yaml"


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def workflow_path(root: Path | None = None) -> Path:
    env = (os.environ.get("TORII_WORKFLOW_FILE") or "").strip()
    if env:
        return Path(env).resolve()
    return (root or _root()) / DEFAULT_WF


def _load_yaml(path: Path) -> dict[str, Any]:
    """Minimal YAML subset loader (no PyYAML dependency).

    Supports: nested maps, lists of scalars/maps, strings, bools, ints.
    Good enough for our workflow file; falls back to json if .json.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)

    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return _mini_yaml(text)


def _mini_yaml(text: str) -> dict[str, Any]:
    """Very small indentation-based YAML parser for our schema."""
    # Strip comments
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.strip().startswith("#"):
            continue
        # remove trailing comments not in quotes
        if "#" in raw and not re.search(r"['\"].*#.*['\"]", raw):
            raw = raw.split("#", 1)[0].rstrip()
        if raw.strip():
            lines.append(raw)

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    def parse_val(s: str) -> Any:
        s = s.strip()
        if not s or s == "|" or s == ">":
            return ""
        if (s.startswith('"') and s.endswith('"')) or (
            s.startswith("'") and s.endswith("'")
        ):
            return s[1:-1]
        if s.lower() in ("true", "false"):
            return s.lower() == "true"
        if s.lower() in ("null", "~"):
            return None
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s

    i = 0
    while i < len(lines):
        line = lines[i]
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        # pop stack to parent
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if content.startswith("- "):
            item_raw = content[2:].strip()
            if not isinstance(parent, list):
                # malformed — skip
                i += 1
                continue
            if ":" in item_raw and not item_raw.startswith("{"):
                # map item
                key, _, rest = item_raw.partition(":")
                key = key.strip()
                rest = rest.strip()
                obj: dict[str, Any] = {}
                if rest:
                    obj[key] = parse_val(rest)
                else:
                    obj[key] = {}
                    # will nest next lines into obj[key] if deeper — simplify: flat map item
                parent.append(obj)
                if not rest:
                    # peek if next lines are nested under this list item
                    stack.append((indent, obj))
            else:
                parent.append(parse_val(item_raw))
            i += 1
            continue

        if ":" in content:
            key, _, rest = content.partition(":")
            key = key.strip()
            rest = rest.strip()
            if not isinstance(parent, dict):
                i += 1
                continue
            if rest:
                # folded multi-line >
                if rest in (">", "|"):
                    # collect following more-indented as string
                    buf = []
                    j = i + 1
                    while j < len(lines):
                        ln = lines[j]
                        ind = len(ln) - len(ln.lstrip(" "))
                        if ind <= indent:
                            break
                        buf.append(ln.strip())
                        j += 1
                    parent[key] = " ".join(buf)
                    i = j
                    continue
                parent[key] = parse_val(rest)
            else:
                # look ahead
                if i + 1 < len(lines):
                    nxt = lines[i + 1]
                    nind = len(nxt) - len(nxt.lstrip(" "))
                    if nind > indent and nxt.strip().startswith("- "):
                        parent[key] = []
                        stack.append((indent, parent[key]))
                    elif nind > indent:
                        parent[key] = {}
                        stack.append((indent, parent[key]))
                    else:
                        parent[key] = None
                else:
                    parent[key] = None
            i += 1
            continue

        i += 1

    return root


def load_workflow(root: Path | None = None) -> tuple[dict[str, Any], Path]:
    path = workflow_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"workflow missing: {path}")
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("workflow root must be a mapping")
    return data, path


def validate(root: Path, wf: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            issues.append(f"{name}: {detail}")

    check("schema_version", int(wf.get("schema_version") or 0) >= 1)
    check("name", bool(wf.get("name")))
    stages = wf.get("stages") or []
    check("stages_nonempty", isinstance(stages, list) and len(stages) >= 3, f"n={len(stages) if isinstance(stages, list) else 0}")

    missing_scripts: list[str] = []
    for st in stages if isinstance(stages, list) else []:
        if not isinstance(st, dict):
            continue
        script = str(st.get("script") or "")
        if not script:
            issues.append(f"stage {st.get('id')} missing script")
            continue
        p = root / script
        ok = p.is_file()
        if not ok:
            missing_scripts.append(script)
        checks.append({"name": f"stage:{st.get('id')}", "ok": ok, "detail": script})

    entries = wf.get("entries") or {}
    if isinstance(entries, dict):
        for k, v in entries.items():
            p = root / str(v)
            ok = p.is_file()
            checks.append({"name": f"entry:{k}", "ok": ok, "detail": str(v)})
            if not ok:
                issues.append(f"entry {k} missing {v}")

    caps = wf.get("capabilities") or []
    cap_ok = 0
    for c in caps if isinstance(caps, list) else []:
        if not isinstance(c, dict):
            continue
        script = str(c.get("script") or "")
        p = root / script
        ok = p.is_file()
        if ok:
            cap_ok += 1
        checks.append(
            {"name": f"cap:{c.get('id')}", "ok": ok, "detail": f"{c.get('feature')} {script}"}
        )
        if not ok:
            issues.append(f"capability {c.get('id')} missing {script}")

    pack = wf.get("pack_scripts") or []
    pack_present = 0
    for s in pack if isinstance(pack, list) else []:
        p = root / "scripts" / str(s)
        # also allow path already with scripts/
        if not p.is_file():
            p = root / str(s)
        ok = p.is_file()
        if ok:
            pack_present += 1
        checks.append({"name": f"pack:{s}", "ok": ok, "detail": str(s)})

    n_ok = sum(1 for c in checks if c["ok"])
    n = len(checks) or 1
    pct = round(100.0 * n_ok / n, 1)
    if pct >= 95 and not missing_scripts:
        level = "L3"
    elif pct >= 80:
        level = "L2"
    elif pct >= 50:
        level = "L1"
    else:
        level = "L0"

    return {
        "feature": FEATURE,
        "valid": len(issues) == 0,
        "level": level,
        "passed": n_ok,
        "total": n,
        "pct": pct,
        "issues": issues,
        "missing_scripts": missing_scripts,
        "capabilities_ok": cap_ok,
        "capabilities_total": len(caps) if isinstance(caps, list) else 0,
        "pack_present": pack_present,
        "pack_total": len(pack) if isinstance(pack, list) else 0,
        "checks": checks,
    }


def plan(wf: dict[str, Any]) -> dict[str, Any]:
    stages = []
    for st in wf.get("stages") or []:
        if not isinstance(st, dict):
            continue
        stages.append(
            {
                "id": st.get("id"),
                "phase": st.get("phase"),
                "script": st.get("script"),
                "soft": bool(st.get("soft")),
                "feature": st.get("feature"),
                "when": st.get("when"),
            }
        )
    by_phase: dict[str, list[str]] = {}
    for s in stages:
        ph = str(s.get("phase") or "other")
        by_phase.setdefault(ph, []).append(str(s.get("id")))
    return {
        "feature": FEATURE,
        "name": wf.get("name"),
        "stages": stages,
        "by_phase": by_phase,
        "entries": wf.get("entries") or {},
        "capabilities": [
            {
                "id": c.get("id"),
                "feature": c.get("feature"),
                "one_liner": c.get("one_liner"),
            }
            for c in (wf.get("capabilities") or [])
            if isinstance(c, dict)
        ],
    }


def pack_check(root: Path, wf: dict[str, Any]) -> dict[str, Any]:
    """Ensure pack_scripts appear in install-torii.sh RUNTIME_SCRIPTS."""
    install = root / "scripts" / "install-torii.sh"
    text = install.read_text(encoding="utf-8") if install.is_file() else ""
    # extract RUNTIME_SCRIPTS=( ... )
    m = re.search(r"RUNTIME_SCRIPTS=\((.*?)\)\s*\n\n", text, re.S)
    listed: set[str] = set()
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            listed.add(line.split("#")[0].strip())

    required = [str(s) for s in (wf.get("pack_scripts") or [])]
    missing = [s for s in required if s not in listed and Path(s).name not in listed]
    # also file existence
    disk_missing = []
    for s in required:
        p = root / "scripts" / s
        if not p.is_file():
            disk_missing.append(s)
    return {
        "feature": FEATURE,
        "install_lists_all": len(missing) == 0,
        "missing_from_install": missing,
        "disk_missing": disk_missing,
        "required_count": len(required),
        "listed_count": len(listed),
    }


def install_guide(root: Path, wf: dict[str, Any], report: dict[str, Any]) -> str:
    lines = [
        f"# Torii Gate — install guide (F79 workflows-as-code)",
        "",
        f"Generated: `{_now()}` · readiness **{report.get('level')}** ({report.get('pct')}%)",
        "",
        "## One-liner",
        "",
        "Torii is the **security merge authority** for every PR: maker agent + checker panel + compound memory.",
        "",
        "## Install (target repo)",
        "",
        "```bash",
        "# from torii-gate checkout",
        "./scripts/install-torii.sh /path/to/your-app",
        "# or hub-managed thin caller:",
        "./scripts/install-torii.sh --caller /path/to/your-app",
        "```",
        "",
        "### Next steps",
        "",
        "1. Commit installed workflows + agent/scripts; push default branch.",
        "2. Secret: `OPENROUTER_API_KEY` (and optional `TORII_HUB_TOKEN`).",
        "3. Optional vars: `TORII_MODEL=deepseek/deepseek-v4-pro`, `TORII_SECOND_CRITIC=1`, `TORII_SCOPED_MEMORY=1`.",
        "4. Branch protection: require status context **`torii/gate`**.",
        "5. On a PR: `@torii review this pr`",
        "",
        "## Pipeline (workflows-as-code)",
        "",
        "```text",
    ]
    for st in wf.get("stages") or []:
        if not isinstance(st, dict):
            continue
        soft = "soft" if st.get("soft") else "hard"
        lines.append(
            f"  [{st.get('phase')}] {st.get('id')} → {st.get('script')} ({soft})"
        )
    lines += [
        "```",
        "",
        "Validate anytime:",
        "",
        "```bash",
        "python3 scripts/workflow_as_code.py validate",
        "python3 scripts/workflow_as_code.py status",
        "./scripts/smoke-torii-gate.sh",
        "```",
        "",
        "## Capability matrix (what you get)",
        "",
        "| Feature | Capability | Script |",
        "|---------|------------|--------|",
    ]
    for c in wf.get("capabilities") or []:
        if not isinstance(c, dict):
            continue
        script = str(c.get("script") or "")
        exists = (root / script).is_file()
        mark = "yes" if exists else "MISSING"
        lines.append(
            f"| {c.get('feature')} | {c.get('one_liner')} | `{script}` ({mark}) |"
        )
    lines += [
        "",
        "## Mental model",
        "",
        "- **Maker** — Hermes agent writes the security review.",
        "- **Checker** — F78 multi-checker panel (path/chain/fitness/memory) demotes weak APPROVE.",
        "- **Skill loop** — `route → hit → fitness → dual → attr → inject` (skills that do not contribute do not re-inflate prompts).",
        "- **Memory loop** — `write → consolidate → effective_critic → federate → recall → tiers → archival_search` (stale memory does not confirm or crowd inject).",
        "- **Gate** — `torii/gate` commit status is the merge signal.",
        "",
    ]
    # F91: skill compound loop readiness block
    try:
        import importlib.util

        slp = root / "scripts" / "skill_loop_status.py"
        if slp.is_file():
            spec = importlib.util.spec_from_file_location("skill_loop_status", slp)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["skill_loop_status"] = mod
                spec.loader.exec_module(mod)
                sl_report = mod.assess(root, deep=False)
                lines.append(mod.to_markdown(sl_report).rstrip())
                lines.append("")
                lines.append(
                    "Deep skill-loop proof: `python3 scripts/skill_loop_status.py fixture`"
                )
                lines.append("")
    except Exception:
        lines.append(
            "## Skill compound loop readiness (F91)\n\n"
            "_skill_loop_status.py not available — re-install pack._\n"
        )
    # F96/F99: memory compound loop readiness
    try:
        import importlib.util

        mlp = root / "scripts" / "memory_loop_status.py"
        if mlp.is_file():
            spec = importlib.util.spec_from_file_location("memory_loop_status", mlp)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["memory_loop_status"] = mod
                spec.loader.exec_module(mod)
                ml_report = mod.assess(root, deep=False)
                lines.append(mod.to_markdown(ml_report).rstrip())
                lines.append("")
                lines.append(
                    "Deep memory-loop proof: `python3 scripts/memory_loop_status.py fixture`"
                )
                lines.append("")
    except Exception:
        lines.append(
            "## Memory compound loop readiness (F96)\n\n"
            "_memory_loop_status.py not available — re-install pack._\n"
        )
    lines += [
        "## Offline proof (no API key)",
        "",
        "```bash",
        "./scripts/smoke-torii-gate.sh",
        "python3 scripts/bench_corpus.py all",
        "python3 scripts/second_agent_critic.py fixture",
        "python3 scripts/skill_loop_status.py scorecard",
        "python3 scripts/memory_loop_status.py scorecard",
        "```",
        "",
    ]
    return "\n".join(lines) + "\n"


def cmd_validate(args: argparse.Namespace) -> int:
    root = _root()
    wf, path = load_workflow(root)
    report = validate(root, wf)
    report["workflow"] = str(path)
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


def cmd_plan(args: argparse.Namespace) -> int:
    root = _root()
    wf, path = load_workflow(root)
    out = plan(wf)
    out["workflow"] = str(path)
    print(json.dumps(out, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    wf, path = load_workflow(root)
    report = validate(root, wf)
    pc = pack_check(root, wf)
    report["workflow"] = str(path)
    report["pack_check"] = pc
    # readiness combines validate + pack install list
    if report["valid"] and pc.get("install_lists_all") and not pc.get("disk_missing"):
        report["ready"] = True
    else:
        report["ready"] = False
        if not pc.get("install_lists_all"):
            report["level"] = min(report["level"], "L2") if report["level"] == "L3" else report["level"]
    print(json.dumps(report, indent=2))
    return 0 if report.get("ready") else 1


def cmd_install_guide(args: argparse.Namespace) -> int:
    root = _root()
    wf, _ = load_workflow(root)
    report = validate(root, wf)
    md = install_guide(root, wf, report)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(json.dumps({"feature": FEATURE, "wrote": str(out), "level": report["level"]}))
    else:
        sys.stdout.write(md)
    return 0


def cmd_pack_check(args: argparse.Namespace) -> int:
    root = _root()
    wf, _ = load_workflow(root)
    print(json.dumps(pack_check(root, wf), indent=2))
    pc = pack_check(root, wf)
    return 0 if pc.get("install_lists_all") and not pc.get("disk_missing") else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = _root()
    wf, path = load_workflow(root)
    report = validate(root, wf)
    planned = plan(wf)
    # stages must include maker + checker phases
    phases = set((planned.get("by_phase") or {}).keys())
    phase_ok = "maker" in phases and "checker" in phases and "pre" in phases
    guide = install_guide(root, wf, report)
    guide_ok = (
        "torii/gate" in guide
        and "Maker" in guide
        and "F78" in guide
        and ("Skill compound" in guide or "skill loop" in guide.lower() or "F91" in guide)
    )
    fixture_pass = report["valid"] and phase_ok and guide_ok and report["pct"] >= 90
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                "valid": report["valid"],
                "level": report["level"],
                "pct": report["pct"],
                "phase_ok": phase_ok,
                "guide_ok": guide_ok,
                "stages": len(planned.get("stages") or []),
                "capabilities": len(planned.get("capabilities") or []),
                "workflow": str(path),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def cmd_scorecard(args: argparse.Namespace) -> int:
    root = _root()
    wf, _ = load_workflow(root)
    report = validate(root, wf)
    pc = pack_check(root, wf)
    skill_loop: dict[str, Any] | None = None
    memory_loop: dict[str, Any] | None = None
    try:
        import importlib.util

        slp = root / "scripts" / "skill_loop_status.py"
        if slp.is_file():
            spec = importlib.util.spec_from_file_location("skill_loop_status", slp)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["skill_loop_status"] = mod
                spec.loader.exec_module(mod)
                sl = mod.assess(root, deep=False)
                skill_loop = {
                    "level": sl.get("level"),
                    "pct": sl.get("pct"),
                    "ready": sl.get("ready"),
                    "stages_ok": f"{sl.get('stages_ok')}/{sl.get('stages_total')}",
                    "skills_n": sl.get("active_skills_n"),
                    "wiring_ok": sl.get("wiring_ok"),
                }
        mlp = root / "scripts" / "memory_loop_status.py"
        if mlp.is_file():
            spec = importlib.util.spec_from_file_location("memory_loop_status", mlp)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["memory_loop_status"] = mod
                spec.loader.exec_module(mod)
                if hasattr(mod, "assess"):
                    ml = mod.assess(root, deep=False)
                    memory_loop = {
                        "level": ml.get("level"),
                        "pct": ml.get("pct"),
                        "ready": ml.get("ready"),
                        "stages_ok": f"{ml.get('stages_ok')}/{ml.get('stages_total')}",
                        "wiring_ok": ml.get("wiring_ok"),
                    }
    except Exception as exc:
        if skill_loop is None:
            skill_loop = {"error": str(exc)[:120]}
        else:
            memory_loop = {"error": str(exc)[:120]}
    # F131 dual compound: skill + memory next to workflow graph
    dual = {
        "skill_level": (skill_loop or {}).get("level"),
        "memory_level": (memory_loop or {}).get("level"),
        "workflow_level": report["level"],
        "both_loops_l3": (skill_loop or {}).get("level") == "L3"
        and (memory_loop or {}).get("level") == "L3",
        "triple_ready": (skill_loop or {}).get("level") == "L3"
        and (memory_loop or {}).get("level") == "L3"
        and report["level"] == "L3"
        and bool(report.get("valid")),
    }
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "feature_dual": "F131",
                "level": report["level"],
                "pct": report["pct"],
                "valid": report["valid"],
                "pack_install_lists_all": pc.get("install_lists_all"),
                "missing_from_install": pc.get("missing_from_install"),
                "skill_loop": skill_loop,
                "memory_loop": memory_loop,
                "dual_compound": dual,
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F79 Torii workflows-as-code")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").set_defaults(func=cmd_validate)
    sub.add_parser("plan").set_defaults(func=cmd_plan)
    sub.add_parser("status").set_defaults(func=cmd_status)
    ig = sub.add_parser("install-guide", help="Markdown install + capability matrix")
    ig.add_argument("--out", default="")
    ig.set_defaults(func=cmd_install_guide)
    sub.add_parser("pack-check").set_defaults(func=cmd_pack_check)
    sub.add_parser("fixture").set_defaults(func=cmd_fixture)
    sub.add_parser("scorecard").set_defaults(func=cmd_scorecard)
    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
