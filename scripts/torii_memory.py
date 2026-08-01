#!/usr/bin/env python3
"""F103: Unified Torii memory CLI for Hermes/terminal agents (tools-as-code front door).

Research / product drivers:
  - MemGPT/Letta expose memory as explicit tools (search, core, archival)
  - Torii shipped F75–F102 as many scripts; agents must guess which to call
  - Loop-eng: prefer one discoverable entrypoint over tribal knowledge

Product thesis:
  Highest ROI agentic-loop slice: **one CLI** that dispatches to compound memory
  tools (search, graph, tiers, consolidate, events, recall, loop status) with a
  stable help surface injectable into prompts.

Usage (from TORII_ROOT or any cwd with TORII_ROOT set):
  python3 scripts/torii_memory.py help
  python3 scripts/torii_memory.py status
  python3 scripts/torii_memory.py search -- -q "sql injection"
  python3 scripts/torii_memory.py search-auto -- --files app.py,db.py
  python3 scripts/torii_memory.py graph -- build
  python3 scripts/torii_memory.py graph -- query --path app.py --hops 2
  python3 scripts/torii_memory.py tiers -- status
  python3 scripts/torii_memory.py consolidate -- fixture
  python3 scripts/torii_memory.py events -- fixture
  python3 scripts/torii_memory.py recall -- fixture
  python3 scripts/torii_memory.py loop -- scorecard --shallow
  python3 scripts/torii_memory.py doctor   # all fixtures soft

After ``--``, remaining args pass through to the underlying script.

Env:
  TORII_ROOT
  TORII_MEMORY_CLI   1 (default) | 0
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

FEATURE = "F103"
SCHEMA = 1
MARKER = "<!-- torii-f103-memory-cli -->"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

# command → script relative to scripts/
COMMANDS: dict[str, dict[str, Any]] = {
    "search": {
        "script": "archival_memory_search.py",
        "default_args": ["search"],
        "help": "MemGPT-style archival search (F98)",
        "examples": ['search -- -q "sql injection"', "search -- status"],
    },
    "search-auto": {
        "script": "archival_memory_search.py",
        "default_args": ["auto"],
        "help": "Auto-search from changed paths + optional promote",
        "examples": ["search-auto -- --files app.py,db.py --prompt /tmp/p.md"],
    },
    "promote": {
        "script": "archival_memory_search.py",
        "default_args": ["promote"],
        "help": "Promote search hits into core inject section",
        "examples": ['promote -- -q "pickle" --prompt prompt.md'],
    },
    "graph": {
        "script": "memory_temporal_graph.py",
        "default_args": [],
        "help": "Zep-style temporal graph build/query/inject (F100–F102)",
        "examples": [
            "graph -- build",
            "graph -- query --path app.py --hops 2",
            "graph -- fixture",
        ],
    },
    "tiers": {
        "script": "memory_tiers.py",
        "default_args": [],
        "help": "Letta-style core/archival tiers (F97)",
        "examples": ["tiers -- status", "tiers -- fixture"],
    },
    "consolidate": {
        "script": "memory_consolidate.py",
        "default_args": [],
        "help": "Importance/merge/decay/evict (F94)",
        "examples": ["consolidate -- run --kind tp", "consolidate -- fixture"],
    },
    "events": {
        "script": "memory_event_policy.py",
        "default_args": [],
        "help": "ADD/UPDATE/DELETE/NONE write policy (F93)",
        "examples": ["events -- fixture", "events -- status"],
    },
    "recall": {
        "script": "scoped_memory_recall.py",
        "default_args": [],
        "help": "Scoped path/effective recall inject (F75/F96)",
        "examples": ["recall -- fixture", "recall -- status"],
    },
    "loop": {
        "script": "memory_loop_status.py",
        "default_args": [],
        "help": "Memory compound loop L0–L3 readiness (F96)",
        "examples": ["loop -- scorecard --shallow", "loop -- fixture"],
    },
    "federate": {
        "script": "federated_hub_ingest.py",
        "default_args": [],
        "help": "Privacy-safe federated signals (F77/F95)",
        "examples": ["federate -- fixture", "federate -- status"],
    },
}


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def enabled() -> bool:
    raw = (os.environ.get("TORII_MEMORY_CLI") or "1").strip().lower()
    return raw not in _FALSEY


def _scripts_dir(root: Path | None = None) -> Path:
    return (root or _root()) / "scripts"


def help_payload() -> dict[str, Any]:
    cmds = []
    for name, meta in COMMANDS.items():
        cmds.append(
            {
                "cmd": name,
                "script": meta["script"],
                "help": meta["help"],
                "examples": meta.get("examples") or [],
            }
        )
    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "entrypoint": "python3 scripts/torii_memory.py",
        "one_liner": "One front door for Torii compound memory tools (search/graph/tiers/loop).",
        "usage": "python3 scripts/torii_memory.py <cmd> [-- <passthrough args>]",
        "commands": cmds,
        "builtins": ["help", "status", "doctor", "inject-hint"],
        "scored_at": _now(),
    }


def render_help_text() -> str:
    p = help_payload()
    lines = [
        f"# Torii memory CLI ({FEATURE})",
        "",
        p["one_liner"],
        "",
        f"Usage: `{p['usage']}`",
        "",
        "| Cmd | Script | Purpose |",
        "|-----|--------|---------|",
    ]
    for c in p["commands"]:
        lines.append(f"| `{c['cmd']}` | `{c['script']}` | {c['help']} |")
    lines += [
        "",
        "Builtins: `help` · `status` · `doctor` · `inject-hint`",
        "",
        "Examples:",
        "```bash",
        'python3 scripts/torii_memory.py search -- -q "sql injection"',
        "python3 scripts/torii_memory.py graph -- query --path app.py --hops 2",
        "python3 scripts/torii_memory.py loop -- scorecard --shallow",
        "python3 scripts/torii_memory.py doctor",
        "```",
        "",
    ]
    return "\n".join(lines)


def render_inject_hint() -> str:
    return (
        f"{MARKER}\n"
        "## Memory tools (F103 — unified CLI)\n\n"
        "Use the workspace terminal with the **Torii memory front door** (do not invent paths):\n\n"
        "```bash\n"
        "python3 scripts/torii_memory.py help\n"
        "python3 scripts/torii_memory.py search -- -q \"theme keywords\"\n"
        "python3 scripts/torii_memory.py search-auto -- --files path1,path2\n"
        "python3 scripts/torii_memory.py graph -- query --path <file> --hops 2\n"
        "python3 scripts/torii_memory.py loop -- scorecard --shallow\n"
        "```\n\n"
        "Prefer **search / graph** before re-raising themes that may be FP-resolved. "
        "Still require path:line evidence to block.\n"
        "<!-- /torii-f103-memory-cli -->\n"
    )


def run_command(cmd: str, passthrough: list[str], *, root: Path | None = None) -> int:
    root = root or _root()
    meta = COMMANDS.get(cmd)
    if not meta:
        print(json.dumps({"error": "unknown_cmd", "cmd": cmd, "feature": FEATURE}), file=sys.stderr)
        return 2
    script = _scripts_dir(root) / meta["script"]
    if not script.is_file():
        print(
            json.dumps(
                {"error": "missing_script", "script": str(script), "feature": FEATURE}
            ),
            file=sys.stderr,
        )
        return 2
    args = [sys.executable, str(script), *list(meta.get("default_args") or []), *passthrough]
    # If default_args empty and passthrough empty, show underlying help
    if not meta.get("default_args") and not passthrough:
        args = [sys.executable, str(script), "--help"]
    env = {**os.environ, "TORII_ROOT": str(root)}
    try:
        r = subprocess.run(args, cwd=str(root), env=env)
        return int(r.returncode)
    except OSError as exc:
        print(json.dumps({"error": str(exc), "feature": FEATURE}), file=sys.stderr)
        return 2


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    present = {}
    for name, meta in COMMANDS.items():
        p = _scripts_dir(root) / meta["script"]
        present[name] = p.is_file()
    # soft peek loop + graph
    extras: dict[str, Any] = {}
    try:
        r = subprocess.run(
            [sys.executable, str(_scripts_dir(root) / "memory_loop_status.py"), "scorecard", "--shallow"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "TORII_ROOT": str(root)},
        )
        if r.returncode == 0 and r.stdout.strip():
            extras["memory_loop"] = json.loads(r.stdout)
    except Exception as exc:
        extras["memory_loop_error"] = str(exc)[:120]
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "enabled": enabled(),
                "root": str(root),
                "commands_present": present,
                "all_present": all(present.values()),
                "extras": extras,
            },
            indent=2,
        )
    )
    return 0 if all(present.values()) else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run cheap fixtures for core memory tools (soft report)."""
    root = _root()
    # Avoid nesting memory_loop fixture (it would re-enter this doctor).
    fixtures = [
        ("events", ["fixture"]),
        ("consolidate", ["fixture"]),
        ("tiers", ["fixture"]),
        ("search", ["fixture"]),
        ("graph", ["fixture"]),
        ("recall", ["fixture"]),
        ("loop", ["scorecard", "--shallow"]),
        ("federate", ["fixture"]),
    ]
    results = []
    all_ok = True
    for name, fargs in fixtures:
        meta = COMMANDS[name]
        script = _scripts_dir(root) / meta["script"]
        if not script.is_file():
            results.append({"cmd": name, "ok": False, "error": "missing"})
            all_ok = False
            continue
        try:
            r = subprocess.run(
                [sys.executable, str(script), *fargs],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=90,
                env={**os.environ, "TORII_ROOT": str(root)},
            )
            ok = r.returncode == 0
            # prefer fixture_pass in JSON when present
            try:
                data = json.loads(r.stdout)
                if "fixture_pass" in data:
                    ok = ok and bool(data["fixture_pass"])
                if name == "loop":
                    ok = ok and data.get("level") in ("L2", "L3") and bool(
                        data.get("ready", True)
                    )
            except (json.JSONDecodeError, TypeError):
                if "fixture_pass=1" in (r.stdout or ""):
                    ok = True
            results.append(
                {
                    "cmd": name,
                    "ok": ok,
                    "rc": r.returncode,
                    "script": meta["script"],
                }
            )
            if not ok:
                all_ok = False
        except Exception as exc:
            results.append({"cmd": name, "ok": False, "error": str(exc)[:120]})
            all_ok = False
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "doctor_pass": all_ok,
                "results": results,
                "scored_at": _now(),
            },
            indent=2,
        )
    )
    return 0 if all_ok else 1


def cmd_inject_hint(args: argparse.Namespace) -> int:
    section = render_inject_hint()
    if args.prompt:
        p = Path(args.prompt)
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        if MARKER in text:
            import re

            text = re.sub(
                r"<!-- torii-f103-memory-cli -->.*?<!-- /torii-f103-memory-cli -->\n?",
                section,
                text,
                count=1,
                flags=re.S,
            )
        else:
            text = text.rstrip() + "\n\n" + section
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(json.dumps({"feature": FEATURE, "injected": True, "prompt": args.prompt}))
        return 0
    print(section)
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: help lists cmds; status; doctor; inject-hint."""
    h = help_payload()
    help_ok = len(h.get("commands") or []) >= 8 and "search" in {
        c["cmd"] for c in h["commands"]
    }
    # status
    st = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "status"],
        cwd=str(_root()),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(_root())},
    )
    status_ok = st.returncode == 0
    try:
        status_data = json.loads(st.stdout)
        status_ok = status_ok and bool(status_data.get("all_present"))
    except json.JSONDecodeError:
        status_ok = False
    # doctor
    dr = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "doctor"],
        cwd=str(_root()),
        capture_output=True,
        text=True,
        env={**os.environ, "TORII_ROOT": str(_root())},
        timeout=300,
    )
    doctor_ok = False
    try:
        ddata = json.loads(dr.stdout)
        doctor_ok = bool(ddata.get("doctor_pass"))
    except json.JSONDecodeError:
        doctor_ok = False
    hint = render_inject_hint()
    hint_ok = MARKER in hint and "torii_memory.py" in hint
    fixture_pass = all([help_ok, status_ok, doctor_ok, hint_ok])
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "fixture_pass": fixture_pass,
                "help_ok": help_ok,
                "status_ok": status_ok,
                "doctor_ok": doctor_ok,
                "hint_ok": hint_ok,
                "commands_n": len(h.get("commands") or []),
            },
            indent=2,
        )
    )
    return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv or argv[0] in ("-h", "--help", "help"):
        if argv and argv[0] == "help" and len(argv) > 1 and argv[1] == "--json":
            print(json.dumps(help_payload(), indent=2))
        else:
            # human help to stdout; JSON on --json only
            if "--json" in argv:
                print(json.dumps(help_payload(), indent=2))
            else:
                print(render_help_text())
        return 0

    cmd = argv[0]
    rest = argv[1:]
    # split on --
    if "--" in rest:
        i = rest.index("--")
        passthrough = rest[i + 1 :]
        pre = rest[:i]
    else:
        # allow: graph build  OR  graph -- build
        passthrough = rest
        pre = []

    if cmd == "status":
        return cmd_status(argparse.Namespace())
    if cmd == "doctor":
        return cmd_doctor(argparse.Namespace())
    if cmd == "inject-hint":
        p = argparse.ArgumentParser()
        p.add_argument("--prompt", default="")
        # parse known from pre+passthrough loosely
        ns, _ = p.parse_known_args(pre + passthrough)
        return cmd_inject_hint(ns)
    if cmd == "fixture":
        return cmd_fixture(argparse.Namespace())
    if cmd == "help":
        print(render_help_text())
        return 0

    if not enabled() and cmd not in ("help", "status"):
        print(json.dumps({"feature": FEATURE, "enabled": False, "skipped": True}))
        return 0

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}\n", file=sys.stderr)
        print(render_help_text(), file=sys.stderr)
        return 2

    # If user wrote: graph build  (no --), passthrough is all rest
    return run_command(cmd, passthrough)


if __name__ == "__main__":
    raise SystemExit(main())
