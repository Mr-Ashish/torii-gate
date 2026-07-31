#!/usr/bin/env python3
"""F69: Torii-native self-evolution (Hermes best practices, not a Hermes fork).

Patterns adopted from Hermes self-evolution / skill evolution (H3, H9, H10):
  - trajectory packaging from agent-loop runs
  - skill proposals from failure/recovery signals
  - offline eval of proposals
  - adopt → agent/skills/active/ injected into review prompts
  - soft skill nudge when prior runs show zero-tool thrash

Usage:
  python3 scripts/self_evolve.py ingest --out-dir DIR [--pr N] [--repo R]
  python3 scripts/self_evolve.py propose [--limit N]
  python3 scripts/self_evolve.py eval [--proposal ID|all]
  python3 scripts/self_evolve.py adopt PROPOSAL_ID [--force]
  python3 scripts/self_evolve.py inject --prompt PATH [--out PATH]
  python3 scripts/self_evolve.py status
  python3 scripts/self_evolve.py nudge-text   # print soft nudge if warranted

Env:
  TORII_ROOT
  TORII_SELF_EVOLVE=0|1          (default 0 for auto-propose in CI; CLI always works)
  TORII_SELF_EVOLVE_AUTO_ADOPT=0|1  (default 0)
  TORII_EVOLUTION_ROOT           (default: <root>/memory/evolution)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _root() -> Path:
    env = (os.environ.get("TORII_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _evo_root(root: Path) -> Path:
    env = (os.environ.get("TORII_EVOLUTION_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return root / "memory" / "evolution"


def _ledger_path(root: Path) -> Path:
    return _evo_root(root) / "ledger.json"


def _load_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.is_file():
        return {
            "schema_version": 1,
            "feature": "F69",
            "trajectories": [],
            "proposals": [],
            "adopted": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    for k in ("trajectories", "proposals", "adopted"):
        data.setdefault(k, [])
    return data


def _save_ledger(root: Path, data: dict[str, Any]) -> Path:
    path = _ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["schema_version"] = 1
    data["feature"] = "F69"
    data["updated_at"] = _now()
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", s.strip().lower())
    return s.strip("-")[:72] or "skill"


def cmd_ingest(args: argparse.Namespace) -> int:
    """Package one run's agent-loop into a trajectory (H9-style)."""
    root = _root()
    out_dir = Path(args.out_dir).resolve()
    loop = out_dir / "agent-loop" / "agent-loop.json"
    if not loop.is_file():
        # try trace dir
        latest = out_dir / "latest-trace-dir.txt"
        if latest.is_file():
            tdir = Path(latest.read_text().strip())
            alt = tdir / "agent-loop" / "agent-loop.json"
            if alt.is_file():
                loop = alt
    if not loop.is_file():
        print("error: agent-loop.json not found", file=sys.stderr)
        return 1

    data = json.loads(loop.read_text(encoding="utf-8", errors="replace"))
    turns = data.get("tool_call_turns")
    try:
        turns_i = int(turns) if turns is not None else 0
    except (TypeError, ValueError):
        turns_i = 0

    pr = str(args.pr or os.environ.get("PR_NUMBER") or "unknown")
    repo = str(args.repo or os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or "unknown")
    tid = str(data.get("session_id") or f"pr{pr}-{_now()}")
    safe = _slug(f"pr{pr}-{tid}")[:80]

    traj_dir = _evo_root(root) / "trajectories" / safe
    traj_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(loop, traj_dir / "agent-loop.json")
    # companion artifacts if present
    for name in ("agent-loop.md", "hermes-usage.json", "timings.json"):
        src = out_dir / name
        if name == "agent-loop.md":
            src = out_dir / "agent-loop" / "agent-loop.md"
        if src.is_file():
            shutil.copy2(src, traj_dir / src.name)
    hermes_run = out_dir / "hermes-run.log"
    if hermes_run.is_file():
        # cap copy size
        raw = hermes_run.read_bytes()
        traj_dir.joinpath("hermes-run.log").write_bytes(raw[-200_000:])

    meta = {
        "feature": "F69",
        "ingested_at": _now(),
        "trajectory_id": safe,
        "repo": repo,
        "pr_number": pr,
        "tool_call_turns": turns_i,
        "message_count": data.get("message_count") or len(data.get("messages") or []),
        "model": data.get("model"),
        "session_id": data.get("session_id"),
        "signals": _signals_from_loop(data, out_dir),
    }
    (traj_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    ledger = _load_ledger(root)
    # de-dupe by trajectory_id
    ledger["trajectories"] = [
        t for t in ledger.get("trajectories") or [] if t.get("trajectory_id") != safe
    ]
    ledger["trajectories"].append(
        {
            "trajectory_id": safe,
            "path": (
                str(traj_dir.relative_to(root))
                if str(traj_dir).startswith(str(root))
                else str(traj_dir)
            ),
            "repo": repo,
            "pr_number": pr,
            "tool_call_turns": turns_i,
            "signals": meta["signals"],
            "ingested_at": meta["ingested_at"],
        }
    )
    # keep last 100
    ledger["trajectories"] = ledger["trajectories"][-100:]
    _save_ledger(root, ledger)

    print(f"trajectory={safe}")
    print(f"path={traj_dir}")
    print(f"tool_call_turns={turns_i}")
    print(f"signals={','.join(meta['signals']) or 'none'}")
    return 0


def _signals_from_loop(data: dict[str, Any], out_dir: Path) -> list[str]:
    signals: list[str] = []
    try:
        turns = int(data.get("tool_call_turns") or 0)
    except (TypeError, ValueError):
        turns = 0
    if turns == 0:
        signals.append("zero_tools")
    if turns >= 10:
        signals.append("deep_tools")
    # F49 recovery marker
    envp = out_dir / "tool-turns-reprompt.env"
    if envp.is_file():
        txt = envp.read_text(encoding="utf-8", errors="replace")
        if "reprompt=1" in txt or "recovered=1" in txt:
            signals.append("f49_recovered")
    # F50
    for rev in out_dir.glob("review-*.md"):
        if ".raw." in rev.name:
            continue
        body = rev.read_text(encoding="utf-8", errors="replace")
        if "Severity calibration" in body or "approve_with_test_gap" in body:
            signals.append("f50_test_gap")
        if "REQUEST CHANGES" in body:
            signals.append("verdict_request_changes")
        if "**Verdict:** APPROVE" in body or "**Verdict:** APPROVE" in body:
            signals.append("verdict_approve")
        break
    return signals


def cmd_propose(args: argparse.Namespace) -> int:
    """Turn trajectory signals into skill proposals (H3 skill-file evolution lite)."""
    root = _root()
    ledger = _load_ledger(root)
    trajs = ledger.get("trajectories") or []
    if not trajs:
        print("error: no trajectories — run ingest first", file=sys.stderr)
        return 1

    # Aggregate signals
    sig_count: dict[str, int] = {}
    for t in trajs:
        for s in t.get("signals") or []:
            sig_count[s] = sig_count.get(s, 0) + 1

    proposals_dir = root / "agent" / "skills" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    existing = {p.get("id") for p in ledger.get("proposals") or []}
    existing |= {p.get("id") for p in ledger.get("adopted") or []}
    # also filesystem
    for p in proposals_dir.glob("*.md"):
        existing.add(p.stem)
    active = root / "agent" / "skills" / "active"
    if active.is_dir():
        for p in active.glob("*.md"):
            if p.name != "README.md":
                existing.add(p.stem)

    templates: list[dict[str, Any]] = []
    if sig_count.get("zero_tools", 0) >= 1 or sig_count.get("f49_recovered", 0) >= 1:
        templates.append(
            {
                "id": "skill-tool-depth-hunks",
                "title": "Tool depth: prefer diff hunks over file heads",
                "signal": "zero_tools|f49_recovered",
                "body": (
                    "## Skill: tool-depth-hunks (F69)\n\n"
                    "When reviewing multi-file code PRs:\n"
                    "1. Open the unified **diff file** first for exact `+/-` hunks.\n"
                    "2. Use `rg -n SYMBOL path` then `sed -n 'START,ENDp'` — never stop at `head`.\n"
                    "3. At least one tool must target a **changed region or symbol**.\n"
                    "4. If tools fail, say so; do not APPROVE on incomplete evidence.\n"
                ),
            }
        )
    if sig_count.get("f50_test_gap", 0) >= 1:
        templates.append(
            {
                "id": "skill-test-gap-blocking",
                "title": "Claim-to-fix: missing tests are blocking",
                "signal": "f50_test_gap",
                "body": (
                    "## Skill: test-gap-blocking (F69)\n\n"
                    "When the PR claims to fix production behavior:\n"
                    "1. Locate new production paths in the diff.\n"
                    "2. Check for tests covering those paths (table-driven / unit).\n"
                    "3. Missing tests → **Blocking** (not Suggestions), with a trigger scenario.\n"
                ),
            }
        )
    if sig_count.get("deep_tools", 0) >= 1:
        templates.append(
            {
                "id": "skill-preserve-deep-tools",
                "title": "Preserve deep tool patterns that worked",
                "signal": "deep_tools",
                "body": (
                    "## Skill: preserve-deep-tools (F69)\n\n"
                    "Prior high-quality runs used ≥10 tool turns. Prefer:\n"
                    "- package path + symbol citations\n"
                    "- reading tests next to production changes\n"
                    "- verifying error/retry paths for concurrency/schema gates\n"
                ),
            }
        )
    # always offer soft mid-loop style nudge skill (H10)
    templates.append(
        {
            "id": "skill-soft-tool-nudge",
            "title": "Soft mid-review tool nudge",
            "signal": "h10_soft_nudge",
            "body": (
                "## Skill: soft-tool-nudge (F69 / H10)\n\n"
                "Prefer **fewer, deeper** tools over thrash:\n"
                "- Cap exploratory `find`/`ls` — jump to symbols from the PR title/diff.\n"
                "- After 3 tool turns without a finding, stop and write the review.\n"
                "- Prefer one solid Blocking item over five speculative nits.\n"
            ),
        }
    )

    limit = int(args.limit or 5)
    created = 0
    for tmpl in templates:
        if created >= limit:
            break
        pid = tmpl["id"]
        if pid in existing:
            continue
        path = proposals_dir / f"{pid}.md"
        header = (
            f"---\n"
            f"id: {pid}\n"
            f"feature: F69\n"
            f"status: proposal\n"
            f"signal: {tmpl['signal']}\n"
            f"created_at: {_now()}\n"
            f"title: {tmpl['title']}\n"
            f"---\n\n"
        )
        path.write_text(header + tmpl["body"], encoding="utf-8")
        entry = {
            "id": pid,
            "title": tmpl["title"],
            "path": str(path.relative_to(root)),
            "signal": tmpl["signal"],
            "status": "proposal",
            "created_at": _now(),
            "eval": None,
        }
        ledger["proposals"] = [p for p in ledger.get("proposals") or [] if p.get("id") != pid]
        ledger["proposals"].append(entry)
        existing.add(pid)
        created += 1
        print(f"proposal={pid} path={path}")

    _save_ledger(root, ledger)
    print(f"created={created}")
    print(f"signal_counts={json.dumps(sig_count)}")
    return 0 if created else 0


def _eval_proposal(path: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    # Heuristic quality: structure + actionability
    has_skill = "## Skill:" in text or text.lstrip().startswith("## Skill")
    bullets = len(re.findall(r"(?m)^\s*[-*]\s+\S", text))
    words = len(text.split())
    traj_n = len(ledger.get("trajectories") or [])

    structure = 5 if has_skill and bullets >= 3 else (3 if has_skill else 1)
    actionability = min(5, 2 + min(3, bullets))
    evidence = min(5, 1 + min(4, traj_n // 2 + 1))
    safety = 5  # skills are prompt snippets only — pure text
    size = 5 if 40 <= words <= 400 else (3 if words < 600 else 1)

    total = structure + actionability + evidence + safety + size
    recommend = "adopt" if total >= 18 and structure >= 3 else "revise"
    return {
        "scored_at": _now(),
        "dims": {
            "structure": structure,
            "actionability": actionability,
            "evidence": evidence,
            "safety": safety,
            "size": size,
        },
        "total": total,
        "max": 25,
        "recommend": recommend,
        "words": words,
        "bullets": bullets,
    }


def cmd_eval(args: argparse.Namespace) -> int:
    root = _root()
    ledger = _load_ledger(root)
    target = (args.proposal or "all").strip()
    n = 0
    for p in ledger.get("proposals") or []:
        if target not in ("all", p.get("id")):
            continue
        path = root / p["path"] if not Path(p["path"]).is_absolute() else Path(p["path"])
        ev = _eval_proposal(path, ledger)
        p["eval"] = ev
        p["status"] = "evaluated"
        n += 1
        print(f"{p['id']}: total={ev['total']}/25 recommend={ev['recommend']}")
    _save_ledger(root, ledger)
    print(f"evaluated={n}")
    return 0 if n else 1


def cmd_adopt(args: argparse.Namespace) -> int:
    root = _root()
    ledger = _load_ledger(root)
    pid = args.proposal_id.strip()
    prop = None
    for p in list(ledger.get("proposals") or []):
        if p.get("id") == pid:
            prop = p
            break
    if not prop:
        # filesystem-only proposal
        path = root / "agent" / "skills" / "proposals" / f"{pid}.md"
        if path.is_file():
            prop = {
                "id": pid,
                "path": str(path.relative_to(root)),
                "title": pid,
                "status": "proposal",
            }
        else:
            print(f"error: proposal not found: {pid}", file=sys.stderr)
            return 1

    ev = prop.get("eval") or {}
    if (ev.get("recommend") or "").lower() == "revise" and not args.force:
        print("error: eval recommend=revise; re-eval or --force", file=sys.stderr)
        return 2

    src = root / prop["path"] if not Path(prop["path"]).is_absolute() else Path(prop["path"])
    if not src.is_file():
        print(f"error: missing file {src}", file=sys.stderr)
        return 1

    active = root / "agent" / "skills" / "active"
    active.mkdir(parents=True, exist_ok=True)
    dest = active / f"{pid}.md"
    text = src.read_text(encoding="utf-8", errors="replace")
    # strip yaml front matter status → adopted
    text2 = re.sub(r"(?m)^status:\s*\w+\s*$", "status: adopted", text, count=1)
    if "status: adopted" not in text2:
        text2 = f"<!-- F69 adopted {_now()} -->\n" + text2
    dest.write_text(text2 if text2.endswith("\n") else text2 + "\n", encoding="utf-8")

    ledger["proposals"] = [p for p in ledger.get("proposals") or [] if p.get("id") != pid]
    ledger["adopted"] = [a for a in ledger.get("adopted") or [] if a.get("id") != pid]
    ledger["adopted"].append(
        {
            "id": pid,
            "title": prop.get("title") or pid,
            "path": str(dest.relative_to(root)),
            "adopted_at": _now(),
            "eval": ev,
            "feature": "F69",
        }
    )
    _save_ledger(root, ledger)
    print(f"adopted={pid}")
    print(f"path={dest}")
    return 0


def _active_skills(root: Path) -> list[Path]:
    active = root / "agent" / "skills" / "active"
    if not active.is_dir():
        return []
    return sorted(
        p
        for p in active.glob("*.md")
        if p.name != "README.md" and p.is_file()
    )


def cmd_inject(args: argparse.Namespace) -> int:
    """Inject adopted skills + optional soft nudge into a review prompt."""
    root = _root()
    prompt = Path(args.prompt)
    if not prompt.is_file():
        print(f"error: prompt not found: {prompt}", file=sys.stderr)
        return 1

    # feature toggle soft-off
    if (os.environ.get("TORII_SELF_EVOLVE") or "1").strip().lower() in (
        "0",
        "false",
        "off",
        "no",
    ):
        # still allow inject if skills exist? Default ON for inject of adopted skills
        pass

    skills = _active_skills(root)
    nudge = _nudge_block(root)
    if not skills and not nudge:
        print("injected=0")
        return 0

    blocks: list[str] = []
    if skills:
        parts = ["## Evolved skills (F69 — Torii-native; treat as reviewer discipline)\n"]
        for sp in skills[:8]:
            body = sp.read_text(encoding="utf-8", errors="replace")
            # drop yaml front matter
            body = re.sub(r"(?s)^---\n.*?\n---\n", "", body).strip()
            parts.append(body)
            parts.append("")
        blocks.append("\n".join(parts).rstrip())
    if nudge:
        blocks.append(nudge)

    injection = "\n\n".join(blocks) + "\n"
    original = prompt.read_text(encoding="utf-8", errors="replace")
    if "<!-- torii-f69-skills -->" in original:
        # replace previous injection
        new = re.sub(
            r"<!-- torii-f69-skills -->.*?<!-- /torii-f69-skills -->\n?",
            f"<!-- torii-f69-skills -->\n{injection}<!-- /torii-f69-skills -->\n",
            original,
            count=1,
            flags=re.DOTALL,
        )
    else:
        # insert before ## PR metadata if present, else append
        marker = "## PR metadata"
        chunk = f"<!-- torii-f69-skills -->\n{injection}<!-- /torii-f69-skills -->\n\n"
        if marker in original:
            new = original.replace(marker, chunk + marker, 1)
        else:
            new = original.rstrip() + "\n\n" + chunk

    out = Path(args.out) if args.out else prompt
    out.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    print(f"injected={len(skills)}")
    print(f"nudge={'1' if nudge else '0'}")
    print(f"prompt={out}")
    return 0


def _nudge_block(root: Path) -> str:
    """H10 soft skill nudge from recent trajectories."""
    ledger = _load_ledger(root)
    recent = (ledger.get("trajectories") or [])[-10:]
    if not recent:
        return ""
    zero = sum(1 for t in recent if "zero_tools" in (t.get("signals") or []))
    recovered = sum(1 for t in recent if "f49_recovered" in (t.get("signals") or []))
    if zero == 0 and recovered == 0:
        return ""
    return (
        "## Soft skill nudge (F69 / H10 — from recent trajectories)\n\n"
        f"Recent runs: {zero} zero-tool first pass(es), {recovered} F49 recoveries.\n"
        "Prefer a **short tool pass** on changed hunks before finalizing the verdict.\n"
        "Avoid thrash: after enough evidence, write the review.\n"
    )


def cmd_nudge_text(args: argparse.Namespace) -> int:
    text = _nudge_block(_root())
    if text:
        print(text)
        return 0
    print("")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    ledger = _load_ledger(root)
    print(f"evolution_root={_evo_root(root)}")
    print(f"trajectories={len(ledger.get('trajectories') or [])}")
    print(f"proposals={len(ledger.get('proposals') or [])}")
    print(f"adopted_ledger={len(ledger.get('adopted') or [])}")
    print(f"active_skills={len(_active_skills(root))}")
    for t in (ledger.get("trajectories") or [])[-5:]:
        print(
            f"  [traj] {t.get('trajectory_id')} tools={t.get('tool_call_turns')} "
            f"signals={t.get('signals')}"
        )
    for p in ledger.get("proposals") or []:
        rec = (p.get("eval") or {}).get("recommend", "-")
        print(f"  [prop] {p.get('id')} status={p.get('status')} recommend={rec}")
    for a in ledger.get("adopted") or []:
        print(f"  [adopted] {a.get('id')} path={a.get('path')}")
    for s in _active_skills(root):
        print(f"  [active] {s.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F69 Torii-native self-evolution")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="Package agent-loop → trajectory")
    pi.add_argument("--out-dir", required=True)
    pi.add_argument("--pr", default="")
    pi.add_argument("--repo", default="")
    pi.set_defaults(func=cmd_ingest)

    pp = sub.add_parser("propose", help="Create skill proposals from trajectories")
    pp.add_argument("--limit", type=int, default=5)
    pp.set_defaults(func=cmd_propose)

    pe = sub.add_parser("eval", help="Score proposals offline")
    pe.add_argument("--proposal", default="all")
    pe.set_defaults(func=cmd_eval)

    pa = sub.add_parser("adopt", help="Move proposal → agent/skills/active")
    pa.add_argument("proposal_id")
    pa.add_argument("--force", action="store_true")
    pa.set_defaults(func=cmd_adopt)

    pj = sub.add_parser("inject", help="Inject active skills into prompt.md")
    pj.add_argument("--prompt", required=True)
    pj.add_argument("--out", default="")
    pj.set_defaults(func=cmd_inject)

    sub.add_parser("nudge-text", help="Print H10 soft nudge if warranted").set_defaults(
        func=cmd_nudge_text
    )
    sub.add_parser("status", help="Ledger + active skills").set_defaults(func=cmd_status)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
