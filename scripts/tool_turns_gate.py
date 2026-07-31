#!/usr/bin/env python3
"""F45 + F49 + F51: tool-turns gate (H12), soft re-prompt (H15), tool depth (H26).

Agentic review is the product differentiator. A no-tool run on a multi-file
code PR can APPROVE while missing real gaps (odoo e2e #2 mini vs GHA).

F45 gate:
  - Detects zero tool-call turns + multi-file + not docs-only
  - Downgrades APPROVE → COMMENT (fail closed on merge-green signal)
  - Injects a visible ⚠️ callout + caps score / confidence
  - Writes tool-turns-gate.env for pack/UI chips

F49 soft re-prompt (H15):
  - Same eligibility as F45, once per review
  - Builds a short tool-nudge suffix so hermes -z can re-run before F45 annotate
  - Writes tool-turns-reprompt.env for pack/UI chips

F51 tool depth (H26):
  - Re-prompt suffix (and review prompt) forbid head-only reads of large files
  - Prefer unified diff hunks / rg+line-range around changed symbols
  - Evidenced on odoo e2e #6: F49 0→1 tools but `head -80 misc.py` missed street_split

Usage:
  python3 scripts/tool_turns_gate.py decide \\
    --tool-turns 0 --file-count 4 --path a.js --path b.js
  python3 scripts/tool_turns_gate.py apply \\
    --review review.md --tool-turns 0 --file-count 4 --out review.md
  python3 scripts/tool_turns_gate.py reprompt-decide \\
    --tool-turns 0 --file-count 4 --path a.js --path b.js
  python3 scripts/tool_turns_gate.py reprompt-write \\
    --prompt-in prompt.md --prompt-out prompt-reprompt.md \\
    --tool-turns 0 --file-count 4 --path a.js

Env:
  TORII_TOOL_TURNS_GATE       1 (default) | 0/off
  TORII_TOOL_TURNS_MIN_FILES  default 2 (multi-file threshold)
  TORII_TOOL_TURNS_GATE_VERDICTS  comma list; default APPROVE
  TORII_TOOL_TURNS_REPROMPT   1 (default) | 0/off  (F49/H15 soft re-prompt)

Stdout decide key=value:
  gate=0|1 reason=... tool_turns=N file_count=N docs_only=true|false enabled=...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

DEFAULT_MIN_FILES = 2
DEFAULT_VERDICTS = ("APPROVE",)

# Align with F38/F42 docs-adjacent globs — docs-only PRs may legitimately skip tools.
DOCS_GLOBS: list[str] = [
    "*.md",
    "*.mdx",
    "*.markdown",
    "*.rst",
    "*.txt",
    "*.adoc",
    "docs/**",
    "**/docs/**",
    "doc/**",
    "**/doc/**",
    "LICENSE*",
    "COPYING*",
    "CHANGELOG*",
    "CHANGES*",
    "HISTORY*",
    "AUTHORS*",
    "CONTRIBUTING*",
    "CODE_OF_CONDUCT*",
    "*.mdc",
]

_VERDICT_RX = re.compile(
    r"^(\*\*Verdict:\*\*\s*)(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_SCORE_RX = re.compile(
    r"^(\*\*Score:\*\*\s*)(\d+)(\s*(?:/100)?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_CONF_RX = re.compile(
    r"^(\*\*Confidence:\*\*\s*)(low|medium|high)\b(.*)$",
    re.MULTILINE | re.IGNORECASE,
)
_GATE_BANNER_RX = re.compile(
    r"Incomplete agentic review \(F45\)",
    re.IGNORECASE,
)

# Score ceiling after fail-closed (still visible but not merge-green confidence).
SCORE_CAP = 55


def enabled(raw: str | None = None) -> bool:
    v = (
        raw
        if raw is not None
        else (os.environ.get("TORII_TOOL_TURNS_GATE") or "1")
    )
    s = str(v).strip().lower()
    return s not in ("0", "false", "off", "no", "none", "disabled")


def reprompt_enabled(raw: str | None = None) -> bool:
    """F49/H15: soft re-prompt once when zero tools on multi-file code (default on)."""
    v = (
        raw
        if raw is not None
        else (os.environ.get("TORII_TOOL_TURNS_REPROMPT") or "1")
    )
    s = str(v).strip().lower()
    return s not in ("0", "false", "off", "no", "none", "disabled")


def min_files(raw: str | None = None) -> int:
    v = (
        raw
        if raw is not None
        else (os.environ.get("TORII_TOOL_TURNS_MIN_FILES") or str(DEFAULT_MIN_FILES))
    )
    try:
        n = int(str(v).strip(), 10)
    except (TypeError, ValueError):
        return DEFAULT_MIN_FILES
    return max(1, n)


def gate_verdicts(raw: str | None = None) -> set[str]:
    v = (
        raw
        if raw is not None
        else (os.environ.get("TORII_TOOL_TURNS_GATE_VERDICTS") or "APPROVE")
    )
    s = str(v).strip()
    if not s or s.lower() in ("all", "*"):
        return {"APPROVE", "REQUEST_CHANGES", "COMMENT", "UNKNOWN"}
    out: set[str] = set()
    for part in s.split(","):
        p = part.strip().upper().replace(" ", "_").replace("-", "_")
        if not p:
            continue
        if p in ("APPROVE", "APPROVED", "LGTM"):
            out.add("APPROVE")
        elif p in ("REQUEST_CHANGES", "REQUESTCHANGES", "CHANGES_REQUESTED"):
            out.add("REQUEST_CHANGES")
        elif p in ("COMMENT", "COMMENTS", "NEUTRAL"):
            out.add("COMMENT")
        else:
            out.add(p)
    return out or set(DEFAULT_VERDICTS)


def normalize_path(p: str) -> str:
    s = (p or "").strip().lstrip("/")
    if s.startswith("./"):
        s = s[2:]
    return s


def path_matches_docs(path: str) -> bool:
    path = normalize_path(path)
    if not path:
        return False
    base = path.rsplit("/", 1)[-1]
    for g in DOCS_GLOBS:
        g = g.strip().lstrip("/")
        if not g:
            continue
        if fnmatch(path, g) or fnmatch(base, g):
            return True
        if g.endswith("/**"):
            prefix = g[:-3]
            if path == prefix or path.startswith(prefix + "/"):
                return True
    return False


def is_docs_only(paths: list[str]) -> bool:
    if not paths:
        return False
    return all(path_matches_docs(p) for p in paths)


def load_paths(paths_file: Path | None, extra: list[str]) -> list[str]:
    out: list[str] = []
    if paths_file is not None and paths_file.is_file():
        for line in paths_file.read_text(encoding="utf-8", errors="replace").splitlines():
            n = normalize_path(line)
            if n:
                out.append(n)
    for p in extra:
        n = normalize_path(p)
        if n:
            out.append(n)
    seen: set[str] = set()
    uniq: list[str] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def read_tool_turns(
    *,
    tool_turns: int | None = None,
    loop_json: Path | None = None,
) -> int | None:
    if tool_turns is not None:
        try:
            return max(0, int(tool_turns))
        except (TypeError, ValueError):
            return None
    if loop_json is not None and loop_json.is_file():
        try:
            data = json.loads(loop_json.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, dict) and "tool_call_turns" in data:
                return max(0, int(data["tool_call_turns"]))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None
    return None


def parse_verdict_token(text: str) -> str:
    m = _VERDICT_RX.search(text or "")
    if not m:
        return "UNKNOWN"
    raw = m.group(2)
    s = re.sub(r"\s+", " ", (raw or "").strip())
    s = re.sub(r"\s*[\(\[].*$", "", s).strip().rstrip(".").strip().upper()
    s = s.replace("-", "_").replace(" ", "_")
    if s in ("APPROVE", "APPROVED", "LGTM"):
        return "APPROVE"
    if s.startswith("REQUEST"):
        return "REQUEST_CHANGES"
    if s.startswith("COMMENT"):
        return "COMMENT"
    return "UNKNOWN"


def decide(
    *,
    tool_turns: int | None,
    file_count: int = 0,
    paths: list[str] | None = None,
    min_files_n: int | None = None,
    gate_on: bool | None = None,
    verdicts: set[str] | None = None,
    verdict: str | None = None,
) -> dict[str, Any]:
    """Return gate decision dict (pure; no I/O)."""
    on = enabled() if gate_on is None else bool(gate_on)
    mf = min_files() if min_files_n is None else max(1, int(min_files_n))
    paths = [normalize_path(p) for p in (paths or []) if normalize_path(p)]
    try:
        fc = max(0, int(file_count))
    except (TypeError, ValueError):
        fc = 0
    if fc == 0 and paths:
        fc = len(paths)
    docs = is_docs_only(paths) if paths else False
    tt: int | None
    try:
        tt = None if tool_turns is None else max(0, int(tool_turns))
    except (TypeError, ValueError):
        tt = None

    base: dict[str, Any] = {
        "enabled": on,
        "gate": 0,
        "reason": "ok",
        "tool_turns": tt if tt is not None else "",
        "file_count": fc,
        "min_files": mf,
        "docs_only": docs,
        "verdict": (verdict or "").upper() or "",
        "action": "none",
    }

    if not on:
        base["reason"] = "gate_off"
        return base
    if tt is None:
        base["reason"] = "tool_turns_unknown"
        return base
    if tt > 0:
        base["reason"] = "tools_used"
        return base
    if docs:
        base["reason"] = "docs_only"
        return base
    if fc < mf:
        base["reason"] = "below_min_files"
        return base

    # Multi-file code PR with zero tools — candidate for fail-closed.
    base["gate"] = 1
    base["reason"] = "zero_tools_multi_file_code"
    base["action"] = "downgrade_approve"

    vset = verdicts if verdicts is not None else gate_verdicts()
    v = (verdict or "").strip().upper().replace(" ", "_").replace("-", "_")
    if v and v not in vset:
        # Still flag the smell, but do not rewrite non-target verdicts.
        base["action"] = "annotate_only"
        base["reason"] = "zero_tools_multi_file_code_nontarget_verdict"
    return base


def should_reprompt(
    *,
    tool_turns: int | None,
    file_count: int = 0,
    paths: list[str] | None = None,
    min_files_n: int | None = None,
    reprompt_on: bool | None = None,
    already_reprompted: bool = False,
) -> dict[str, Any]:
    """F49/H15: whether to soft re-prompt once (independent of F45 gate toggle).

    Eligibility mirrors the zero-tools multi-file code smell, but is controlled
    by TORII_TOOL_TURNS_REPROMPT (not TORII_TOOL_TURNS_GATE). F45 still runs
    after the second attempt if tools remain zero.
    """
    on = reprompt_enabled() if reprompt_on is None else bool(reprompt_on)
    # Reuse decide() with gate forced on so we share docs/min-files logic.
    d = decide(
        tool_turns=tool_turns,
        file_count=file_count,
        paths=paths,
        min_files_n=min_files_n,
        gate_on=True,
    )
    out: dict[str, Any] = {
        "reprompt": 0,
        "enabled": on,
        "reason": "ok",
        "tool_turns": d.get("tool_turns", ""),
        "file_count": d.get("file_count", 0),
        "min_files": d.get("min_files", DEFAULT_MIN_FILES),
        "docs_only": d.get("docs_only", False),
        "already_reprompted": bool(already_reprompted),
        "gate_reason": d.get("reason", ""),
    }
    if not on:
        out["reason"] = "reprompt_off"
        return out
    if already_reprompted:
        out["reason"] = "already_reprompted"
        return out
    if d.get("tool_turns") == "" or d.get("tool_turns") is None:
        out["reason"] = "tool_turns_unknown"
        return out
    try:
        tt = int(d["tool_turns"])  # type: ignore[arg-type]
    except (TypeError, ValueError):
        out["reason"] = "tool_turns_unknown"
        return out
    if tt > 0:
        out["reason"] = "tools_used"
        return out
    if d.get("docs_only"):
        out["reason"] = "docs_only"
        return out
    if int(d.get("file_count") or 0) < int(d.get("min_files") or DEFAULT_MIN_FILES):
        out["reason"] = "below_min_files"
        return out
    # Candidate: zero tools + multi-file code
    out["reprompt"] = 1
    out["reason"] = "zero_tools_multi_file_code"
    return out


def build_reprompt_suffix(
    *,
    tool_turns: int = 0,
    file_count: int = 0,
    paths: list[str] | None = None,
) -> str:
    """Soft nudge appended to the original review prompt (H15 + H26 tool depth)."""
    paths = [normalize_path(p) for p in (paths or []) if normalize_path(p)]
    sample = paths[:12]
    more = len(paths) - len(sample)
    files_block = ""
    if sample:
        bullets = "\n".join(f"  - `{p}`" for p in sample)
        if more > 0:
            bullets += f"\n  - … and {more} more"
        files_block = f"\nChanged paths (from the PR):\n{bullets}\n"
    return (
        "\n\n---\n\n"
        "## Soft re-prompt (Torii H15 / F49 + H26 / F51)\n\n"
        f"Your previous reply used **{tool_turns} tool turns** on a multi-file "
        f"code PR (**{file_count}** files). That is incomplete for an agentic "
        "review: do **not** finalize from the diff text alone.\n\n"
        "Before writing the final review you **must** use workspace tools at "
        "least once:\n"
        "1. Inspect **changed hunks** (not just file prologues) under the workspace\n"
        "2. Spot-check related tests (or note they are missing)\n"
        "3. Only then emit the full review in the required Markdown contract\n\n"
        "**Tool depth (H26 / F51) — critical:**\n"
        "- Do **not** stop after `head` / first-N-lines on large files. Headers "
        "miss mid-file symbols (e.g. a regex deep in `misc.py`).\n"
        "- Prefer the unified **diff file** for exact `+/-` hunks, or "
        "`rg`/`grep -n` for symbols from the PR title/summary/changed paths.\n"
        "- After a symbol hit: read a **line range** around it "
        "(`sed -n 'START,ENDp' path` or equivalent). At least one tool must "
        "target a **changed region or symbol**, not only file prologues.\n"
        "- Do not claim you reviewed a symbol you only saw via `head`.\n\n"
        "Prefer terminal/file tools over guessing. If a path is missing, say so "
        "explicitly instead of approving on incomplete evidence.\n"
        f"{files_block}"
    )


def write_reprompt_prompt(
    *,
    prompt_in: Path,
    prompt_out: Path,
    tool_turns: int = 0,
    file_count: int = 0,
    paths: list[str] | None = None,
) -> str:
    base = prompt_in.read_text(encoding="utf-8", errors="replace")
    suffix = build_reprompt_suffix(
        tool_turns=tool_turns,
        file_count=file_count,
        paths=paths,
    )
    # Avoid stacking multiple H15/H26 blocks if called twice.
    # Prefix match: title may be "…H15 / F49)" or "…H15 / F49 + H26 / F51)".
    marker = "## Soft re-prompt (Torii H15"
    if marker in base:
        text = base
    else:
        text = base.rstrip() + suffix
        if not text.endswith("\n"):
            text += "\n"
    prompt_out.parent.mkdir(parents=True, exist_ok=True)
    prompt_out.write_text(text, encoding="utf-8")
    return text


def write_reprompt_env(path: Path, data: dict[str, Any]) -> None:
    keys = [
        "reprompt",
        "enabled",
        "reason",
        "attempted",
        "tool_turns_before",
        "tool_turns_after",
        "file_count",
        "recovered",
        "rc",
        "skipped_reason",
    ]
    lines: list[str] = []
    for k in keys:
        if k not in data:
            continue
        v = data[k]
        if isinstance(v, bool):
            vv = "1" if v else "0"
        else:
            vv = str(v).replace("\n", " ").replace("\r", "")
        lines.append(f"{k}={vv}")
    # Always include attempted default
    if "attempted" not in data:
        lines.insert(0 if not lines else len(lines), "attempted=0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def banner_md(*, tool_turns: int, file_count: int, reason: str) -> str:
    return (
        f"> ⚠️ **Incomplete agentic review (F45):** Hermes recorded "
        f"**{tool_turns} tool turns** on a multi-file code PR "
        f"({file_count} files). Torii fail-closed: **APPROVE is not allowed** "
        f"without workspace tools (`{reason}`). Re-run so the agent reads "
        f"changed files, or treat findings as low-trust.\n"
    )


def apply_to_review(
    text: str,
    *,
    decision: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Rewrite review body when gate fires. Returns (new_text, mut_meta)."""
    meta: dict[str, Any] = {
        "mutated": False,
        "verdict_before": parse_verdict_token(text),
        "verdict_after": parse_verdict_token(text),
        "score_capped": False,
        "banner_added": False,
    }
    if not decision.get("gate"):
        return text, meta

    body = text or ""
    v_before = meta["verdict_before"]
    action = decision.get("action") or "downgrade_approve"
    tt = decision.get("tool_turns")
    try:
        tt_i = int(tt) if tt != "" and tt is not None else 0
    except (TypeError, ValueError):
        tt_i = 0
    fc = int(decision.get("file_count") or 0)
    reason = str(decision.get("reason") or "zero_tools_multi_file_code")

    if action == "downgrade_approve" and v_before == "APPROVE":
        def _repl_v(m: re.Match[str]) -> str:
            return f"{m.group(1)}COMMENT"

        new_body, n = _VERDICT_RX.subn(_repl_v, body, count=1)
        if n:
            body = new_body
            meta["mutated"] = True
            meta["verdict_after"] = "COMMENT"
        # confidence → low
        def _repl_c(m: re.Match[str]) -> str:
            return f"{m.group(1)}low{m.group(3)}"

        body2, nc = _CONF_RX.subn(_repl_c, body, count=1)
        if nc:
            body = body2
            meta["mutated"] = True
        # score cap
        def _repl_s(m: re.Match[str]) -> str:
            try:
                sc = int(m.group(2))
            except ValueError:
                return m.group(0)
            if sc > SCORE_CAP:
                meta["score_capped"] = True
                meta["mutated"] = True
                return f"{m.group(1)}{SCORE_CAP}{m.group(3)}"
            return m.group(0)

        body = _SCORE_RX.sub(_repl_s, body, count=1)
    else:
        meta["verdict_after"] = v_before

    # Banner once
    if not _GATE_BANNER_RX.search(body):
        ban = banner_md(tool_turns=tt_i, file_count=fc, reason=reason)
        # Insert after first heading block / score fields if present
        m = re.search(
            r"(^\*\*(?:Verdict|Confidence|Score|Review effort):\*\*.*\n)+",
            body,
            re.MULTILINE,
        )
        if m:
            insert_at = m.end()
            body = body[:insert_at] + "\n" + ban + body[insert_at:]
        else:
            body = ban + "\n" + body
        meta["banner_added"] = True
        meta["mutated"] = True

    meta["verdict_after"] = parse_verdict_token(body)
    return body, meta


def write_env(path: Path, decision: dict[str, Any], mut: dict[str, Any] | None = None) -> None:
    lines = [
        f"gate={'1' if decision.get('gate') else '0'}",
        f"enabled={'1' if decision.get('enabled') else '0'}",
        f"reason={decision.get('reason', '')}",
        f"tool_turns={decision.get('tool_turns', '')}",
        f"file_count={decision.get('file_count', '')}",
        f"min_files={decision.get('min_files', '')}",
        f"docs_only={'true' if decision.get('docs_only') else 'false'}",
        f"action={decision.get('action', 'none')}",
        f"verdict_before={(mut or {}).get('verdict_before', decision.get('verdict', ''))}",
        f"verdict_after={(mut or {}).get('verdict_after', '')}",
        f"mutated={'1' if (mut or {}).get('mutated') else '0'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _emit_kv(d: dict[str, Any]) -> None:
    for k, v in d.items():
        if isinstance(v, bool):
            vv = "true" if v else "false"
        else:
            vv = str(v).replace("\n", " ").replace("\r", "")
        print(f"{k}={vv}")


def cmd_decide(args: argparse.Namespace) -> int:
    paths = load_paths(
        Path(args.paths_file) if args.paths_file else None,
        list(args.path or []),
    )
    tt = read_tool_turns(
        tool_turns=args.tool_turns,
        loop_json=Path(args.loop_json) if args.loop_json else None,
    )
    d = decide(
        tool_turns=tt,
        file_count=args.file_count if args.file_count is not None else 0,
        paths=paths,
        min_files_n=args.min_files,
        gate_on=enabled(args.enabled) if args.enabled is not None else None,
        verdict=args.verdict,
    )
    _emit_kv(d)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    paths = load_paths(
        Path(args.paths_file) if args.paths_file else None,
        list(args.path or []),
    )
    tt = read_tool_turns(
        tool_turns=args.tool_turns,
        loop_json=Path(args.loop_json) if args.loop_json else None,
    )
    review_path = Path(args.review)
    if not review_path.is_file():
        print(f"error: review not found: {review_path}", file=sys.stderr)
        return 1
    body = review_path.read_text(encoding="utf-8", errors="replace")
    verdict = args.verdict or parse_verdict_token(body)
    d = decide(
        tool_turns=tt,
        file_count=args.file_count if args.file_count is not None else 0,
        paths=paths,
        min_files_n=args.min_files,
        gate_on=enabled(args.enabled) if args.enabled is not None else None,
        verdict=verdict,
    )
    d["verdict"] = verdict
    new_body, mut = apply_to_review(body, decision=d)
    out = Path(args.out) if args.out else review_path
    out.write_text(new_body, encoding="utf-8")
    if args.env_out:
        write_env(Path(args.env_out), d, mut)
    meta = {**d, **mut, "out": str(out)}
    _emit_kv(meta)
    return 0


def cmd_reprompt_decide(args: argparse.Namespace) -> int:
    paths = load_paths(
        Path(args.paths_file) if args.paths_file else None,
        list(args.path or []),
    )
    tt = read_tool_turns(
        tool_turns=args.tool_turns,
        loop_json=Path(args.loop_json) if args.loop_json else None,
    )
    d = should_reprompt(
        tool_turns=tt,
        file_count=args.file_count if args.file_count is not None else 0,
        paths=paths,
        min_files_n=args.min_files,
        reprompt_on=(
            reprompt_enabled(args.reprompt_enabled)
            if args.reprompt_enabled is not None
            else None
        ),
        already_reprompted=bool(args.already),
    )
    _emit_kv(d)
    return 0


def cmd_reprompt_write(args: argparse.Namespace) -> int:
    paths = load_paths(
        Path(args.paths_file) if args.paths_file else None,
        list(args.path or []),
    )
    tt = read_tool_turns(
        tool_turns=args.tool_turns,
        loop_json=Path(args.loop_json) if args.loop_json else None,
    )
    if tt is None:
        tt = 0
    pin = Path(args.prompt_in)
    if not pin.is_file():
        print(f"error: prompt not found: {pin}", file=sys.stderr)
        return 1
    pout = Path(args.prompt_out)
    fc = args.file_count if args.file_count is not None else (len(paths) or 0)
    write_reprompt_prompt(
        prompt_in=pin,
        prompt_out=pout,
        tool_turns=int(tt),
        file_count=int(fc),
        paths=paths,
    )
    _emit_kv(
        {
            "prompt_out": str(pout),
            "bytes": pout.stat().st_size if pout.is_file() else 0,
            "tool_turns": tt,
            "file_count": fc,
        }
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--tool-turns", type=int, default=None)
        sp.add_argument(
            "--loop-json",
            default=None,
            help="agent-loop.json path (reads tool_call_turns)",
        )
        sp.add_argument("--file-count", type=int, default=None)
        sp.add_argument("--path", action="append", default=[])
        sp.add_argument("--paths-file", default=None)
        sp.add_argument("--min-files", type=int, default=None)
        sp.add_argument(
            "--enabled",
            default=None,
            help="override TORII_TOOL_TURNS_GATE (1/0)",
        )
        sp.add_argument("--verdict", default=None)

    d = sub.add_parser("decide", help="Print gate decision key=value")
    add_common(d)
    d.set_defaults(func=cmd_decide)

    a = sub.add_parser("apply", help="Rewrite review.md when gate fires")
    add_common(a)
    a.add_argument("--review", required=True, help="Path to normalized review.md")
    a.add_argument("--out", default=None, help="Output path (default: in-place)")
    a.add_argument(
        "--env-out",
        default=None,
        help="Write tool-turns-gate.env key=value for pack/UI",
    )
    a.set_defaults(func=cmd_apply)

    rd = sub.add_parser(
        "reprompt-decide",
        help="F49/H15: print soft re-prompt decision key=value",
    )
    add_common(rd)
    rd.add_argument(
        "--reprompt-enabled",
        default=None,
        help="override TORII_TOOL_TURNS_REPROMPT (1/0)",
    )
    rd.add_argument(
        "--already",
        action="store_true",
        help="already re-prompted once this run (forces skip)",
    )
    rd.set_defaults(func=cmd_reprompt_decide)

    rw = sub.add_parser(
        "reprompt-write",
        help="F49/H15: write prompt + soft tool-nudge suffix",
    )
    add_common(rw)
    rw.add_argument("--prompt-in", required=True, help="Original prompt path")
    rw.add_argument("--prompt-out", required=True, help="Nudged prompt output path")
    rw.set_defaults(func=cmd_reprompt_write)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
