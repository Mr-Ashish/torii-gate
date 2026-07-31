#!/usr/bin/env python3
"""F9/F9b/F9c: post path-anchored inline GitHub PR review comments.

Maps Key findings (+ Blocking bullets) onto lines in pr.diff:
  F9  — first *added* line per file (fallback)
  F9b — prefer path:line / L### hints when that line is a changed `+` line
        (else nearest changed line, else first)
  F9c — ### Code suggestions → GitHub ```suggestion``` apply blocks
        (multi-line when the suggestion's `-` lines match PR `+` lines)
  F54 — per finding: copy-pasteable Fix-it agent prompt (Claude Code ready)
  F60 — re-review: reply in existing Torii inline threads (in_reply_to)
  F62 — skip planned findings that match known FP/resolved patterns

Usage:
  python3 scripts/post-inline-comments.py plan \\
    --review review.md --diff pr.diff

  python3 scripts/post-inline-comments.py post \\
    --review review.md --diff pr.diff --repo owner/name --pr 3 --commit SHA

Env:
  TORII_INLINE_COMMENTS=1 (default) | 0/off to skip
  TORII_INLINE_MAX=6
  TORII_INLINE_SEVERITY=critical,high   (comma list; empty = all)
  TORII_INLINE_SUGGESTIONS=1 (default) | 0/off to skip F9c
  TORII_SUGGESTION_MAX=3
  TORII_FIXIT_PROMPTS=1 (default) | 0/off to skip F54 fix-it agent prompts
  (bools resolved via F55 scripts/feature_toggles.py + optional .torii/toggles.json)
  GH_TOKEN / GITHUB_TOKEN for post
  TORII_INLINE_FIXTURE=path.json  — write planned payload instead of API (tests)

Soft-fail policy: never raises for network; plan mode is pure offline.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# F55: shared toggle resolution (env > .torii/toggles.json > default)
try:
    from feature_toggles import is_enabled as _toggle_enabled  # type: ignore
except ImportError:  # pragma: no cover - script dir on path for CLI
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from feature_toggles import is_enabled as _toggle_enabled  # type: ignore


SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
    "blocking": 0,
}

# path:123 or path#L123 (optional backticks already stripped)
_PATH_LINE_RE = re.compile(
    r"^(?P<path>.+?)(?::|#L)(?P<line>\d{1,7})$",
    re.I,
)
# standalone line hints in free text
_LINE_HINT_RE = re.compile(
    r"(?:^|[\s(`])(?:L|line\s*)(\d{1,7})(?:\b|$)",
    re.I,
)


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def split_path_line(raw: str) -> tuple[str, int | None]:
    """Return (path, line_hint) from a File cell like `foo.py:42` or `foo.py`."""
    s = (raw or "").strip().strip("`").strip()
    if not s:
        return "", None
    # take first token (ignore trailing notes)
    s = s.split()[0]
    if s.startswith(("a/", "b/")):
        s = s[2:]
    m = _PATH_LINE_RE.match(s)
    if m:
        return m.group("path"), int(m.group("line"))
    return s, None


def normalize_path(raw: str) -> str:
    path, _ = split_path_line(raw)
    return path


def extract_line_hint(*parts: str, path_cell: str = "") -> int | None:
    """F9b: pull a line number from path cell or free text (issue/trigger)."""
    _, from_path = split_path_line(path_cell)
    if from_path is not None and from_path > 0:
        return from_path
    blob = " ".join(p for p in parts if p)
    # Prefer path:line embedded in text
    for m in re.finditer(r"[\w./+-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|rb|md|sh|yml|yaml):(\d{1,7})", blob):
        n = int(m.group(1))
        if n > 0:
            return n
    m2 = _LINE_HINT_RE.search(blob)
    if m2:
        n = int(m2.group(1))
        if n > 0:
            return n
    return None


def parse_findings(review_md: str) -> list[dict[str, Any]]:
    """Parse Key findings table + Blocking bullets into finding dicts."""
    findings: list[dict[str, Any]] = []

    # Key findings table — optional 5th Line column; File may be path:line
    m = re.search(
        r"^### Key findings\s*\n(.*?)(?=^### |\Z)",
        review_md,
        re.M | re.S,
    )
    body = m.group(1) if m else ""
    header_has_line = False
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|\s*-+", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        head0 = cells[0].lower()
        if head0 in {"severity", "sev", "level"}:
            header_has_line = any(c.lower() in {"line", "ln", "lineno"} for c in cells)
            continue
        path_cell = cells[1]
        path = normalize_path(path_cell)
        issue = cells[2][:500]
        trigger = cells[3][:300] if len(cells) > 3 else ""
        line_hint = extract_line_hint(issue, trigger, path_cell=path_cell)
        if header_has_line and len(cells) >= 5:
            try:
                col = int(re.sub(r"[^\d]", "", cells[4]) or "0")
                if col > 0:
                    line_hint = col
            except ValueError:
                pass
        findings.append(
            {
                "severity": cells[0].lower(),
                "file": path,
                "issue": issue,
                "trigger": trigger,
                "line_hint": line_hint,
                "source": "findings",
            }
        )

    # Blocking bullets: **`path` — text** or **path:42 — text**
    bm = re.search(
        r"^### Blocking\s*\n(.*?)(?=^### |\Z)",
        review_md,
        re.M | re.S,
    )
    bbody = bm.group(1) if bm else ""
    for line in bbody.splitlines():
        s = line.strip()
        if not s.startswith(("- ", "* ")):
            continue
        s = re.sub(r"^[-*]\s+", "", s)
        mm = re.match(
            r"\*\*[`']?([^`'*]+?)[`']?\s*[—–-]\s*(.+?)\*\*",
            s,
        )
        if not mm:
            mm = re.match(r"[`']?([^\s`']+\.[a-zA-Z0-9:]+(?:#L\d+)?)[`']?\s*[—–-]\s*(.+)", s)
        if not mm:
            continue
        path_cell = mm.group(1)
        path = normalize_path(path_cell)
        issue = mm.group(2).strip()[:500]
        findings.append(
            {
                "severity": "blocking",
                "file": path,
                "issue": issue,
                "trigger": "",
                "line_hint": extract_line_hint(issue, path_cell=path_cell),
                "source": "blocking",
            }
        )

    return findings


def added_lines_by_path(diff_text: str) -> dict[str, list[int]]:
    """Map path → sorted unique new-file line numbers that have an added (+) line."""
    result: dict[str, list[int]] = {}
    current: str | None = None
    new_line = 0
    in_hunk = False

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            current = None
            in_hunk = False
            continue
        if raw.startswith("+++ "):
            path = raw[4:].strip()
            if path == "/dev/null":
                current = None
                continue
            if path.startswith("b/"):
                path = path[2:]
            current = path
            result.setdefault(current, [])
            continue
        if raw.startswith("@@"):
            mm = re.search(r"\+(\d+)(?:,\d+)?", raw)
            if mm:
                new_line = int(mm.group(1))
                in_hunk = True
            else:
                in_hunk = False
            continue
        if not in_hunk or current is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            result.setdefault(current, []).append(new_line)
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            pass
        else:
            new_line += 1

    for p, lst in list(result.items()):
        # unique preserve order
        seen: set[int] = set()
        uniq: list[int] = []
        for n in lst:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        result[p] = uniq
    return result


def first_added_lines(diff_text: str) -> dict[str, int]:
    """Map path → first new-file line number that has an added (+) line."""
    return {p: lines[0] for p, lines in added_lines_by_path(diff_text).items() if lines}


def resolve_path(path: str, known: dict[str, Any]) -> str | None:
    if path in known:
        return path
    for dp in known:
        if dp.endswith("/" + path) or dp.endswith(path) or path.endswith(dp):
            return dp
    return None


def resolve_anchor_line(
    path: str,
    hint: int | None,
    added: dict[str, list[int]],
) -> tuple[int | None, str]:
    """Pick comment line + how it was chosen (exact|nearest|first).

    F9b: only pin to a line that exists as a changed `+` line (GitHub requires
    the line to be part of the diff for multi-line-safe single-line comments).
    """
    lines = added.get(path) or []
    if not lines:
        return None, "none"
    if hint is not None and hint in lines:
        return hint, "exact"
    if hint is not None:
        # nearest changed line (same file)
        nearest = min(lines, key=lambda n: (abs(n - hint), n))
        return nearest, "nearest"
    return lines[0], "first"


def severity_allowed(sev: str, allow: set[str]) -> bool:
    if not allow:
        return True
    return sev.lower() in allow


def plan_comments(
    review_md: str,
    diff_text: str,
    *,
    max_n: int = 6,
    severities: set[str] | None = None,
    include_suggestions: bool | None = None,
    suggestion_max: int | None = None,
) -> list[dict[str, Any]]:
    allow = severities if severities is not None else set()
    added = added_lines_by_path(diff_text)
    findings = parse_findings(review_md)

    # Prefer higher severity; one comment per file (first wins after sort)
    findings.sort(key=lambda f: SEVERITY_RANK.get(str(f["severity"]), 9))

    planned: list[dict[str, Any]] = []
    seen_files: set[str] = set()
    for f in findings:
        if not severity_allowed(str(f["severity"]), allow):
            continue
        path = str(f.get("file") or "")
        if not path or path in seen_files:
            continue
        resolved = resolve_path(path, added)
        if resolved is None:
            continue
        path = resolved
        hint = f.get("line_hint")
        if isinstance(hint, str) and hint.isdigit():
            hint = int(hint)
        if not isinstance(hint, int):
            hint = None
        line, anchor = resolve_anchor_line(path, hint, added)
        if line is None:
            continue
        seen_files.add(path)
        body = f"**{str(f['severity']).upper()}** — {f['issue']}"
        if f.get("trigger"):
            body += f"\n\n_Trigger:_ {f['trigger']}"
        if hint is not None:
            body += f"\n\n_Anchor:_ L{hint} → L{line} ({anchor})"
        fixit = ""
        if fixit_prompts_enabled_from_env():
            fixit = format_fixit_prompt(
                path=path,
                line=int(line),
                severity=str(f["severity"]),
                issue=str(f["issue"]),
                trigger=str(f.get("trigger") or ""),
                source=str(f.get("source") or "findings"),
            )
            if fixit:
                body += "\n\n" + fixit
        body += "\n\n<!-- torii-inline -->"
        planned.append(
            {
                "path": path,
                "line": int(line),
                "side": "RIGHT",
                "body": body[:65000],
                "severity": f["severity"],
                "source": f["source"],
                "line_hint": hint,
                "anchor": anchor,
                "kind": "finding",
                "fixit": bool(fixit),
            }
        )
        if len(planned) >= max_n:
            break

    # F9c: GitHub apply-suggestion blocks from ### Code suggestions
    if include_suggestions is None:
        include_suggestions = suggestions_enabled_from_env()
    if include_suggestions:
        smax = suggestion_max if suggestion_max is not None else suggestion_max_from_env()
        for sc in plan_suggestions(review_md, diff_text, max_n=smax):
            planned.append(sc)
    return planned


# ---------------------------------------------------------------------------
# F9c: Code suggestions → GitHub ```suggestion``` apply blocks
# ---------------------------------------------------------------------------

# Trailing (`path`) or (path) — path is last parenthetical (title may contain `code`)
_TITLE_PATH_RE = re.compile(
    r"^####\s+(.+?)\s+\(`?([^)`\n]+)`?\)\s*$",
    re.M,
)
_FENCE_RE = re.compile(
    r"```(?P<lang>diff|suggestion|patch)?\s*\n(?P<body>.*?)```",
    re.M | re.S | re.I,
)


def suggestions_enabled_from_env() -> bool:
    """TORII_INLINE_SUGGESTIONS via F55 registry (default on)."""
    return bool(_toggle_enabled("inline_suggestions"))


def suggestion_max_from_env() -> int:
    try:
        return max(1, min(10, int(os.environ.get("TORII_SUGGESTION_MAX") or "3")))
    except ValueError:
        return 3


def parse_code_suggestions(review_md: str) -> list[dict[str, Any]]:
    """Parse ### Code suggestions into {title, path, minus, plus, kind} dicts."""
    m = re.search(
        r"^### Code suggestions\s*\n(.*?)(?=^### |\Z)",
        review_md,
        re.M | re.S,
    )
    if not m:
        return []
    body = m.group(1)
    if re.match(r"^\s*None\b", body.strip(), re.I):
        return []

    # Split on #### headings
    parts = re.split(r"(?=^#### )", body, flags=re.M)
    out: list[dict[str, Any]] = []
    for part in parts:
        part = part.strip()
        if not part.startswith("####"):
            continue
        first = part.splitlines()[0]
        tm = _TITLE_PATH_RE.match(first)
        if not tm:
            # try path only in backticks at end: #### title `path`
            tm2 = re.match(r"^####\s+(.+?)\s+`([^`]+)`\s*$", first)
            if not tm2:
                continue
            title, path_raw = tm2.group(1), tm2.group(2)
        else:
            title, path_raw = tm.group(1), tm.group(2)
        path = normalize_path(path_raw)
        if not path:
            continue
        fm = _FENCE_RE.search(part)
        if not fm:
            continue
        lang = (fm.group("lang") or "").lower()
        fbody = fm.group("body")
        minus: list[str] = []
        plus: list[str] = []
        if lang in ("diff", "patch", ""):
            for raw in fbody.splitlines():
                if raw.startswith("+") and not raw.startswith("+++"):
                    plus.append(raw[1:])
                elif raw.startswith("-") and not raw.startswith("---"):
                    minus.append(raw[1:])
                elif raw.startswith("\\"):
                    continue
                elif lang == "" and not minus and not plus:
                    # bare fence without +/- → treat as pure suggestion body
                    plus.append(raw)
                # context lines (no prefix) ignored for mapping
        elif lang == "suggestion":
            plus = fbody.splitlines()
            # no minus — cannot multi-map; plan_suggestions may still pin to first line
        if not plus and not minus:
            continue
        out.append(
            {
                "title": title.strip()[:200],
                "path": path,
                "minus": minus,
                "plus": plus,
                "lang": lang or "diff",
            }
        )
    return out


def added_line_contents_by_path(diff_text: str) -> dict[str, list[tuple[int, str]]]:
    """Map path → [(new_line_no, content_without_plus), ...] for all `+` lines."""
    result: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    new_line = 0
    in_hunk = False
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            current = None
            in_hunk = False
            m = re.search(r" b/(.+)$", raw)
            if m:
                path = m.group(1)
                if path.startswith("b/"):
                    path = path[2:]
                current = path
                result.setdefault(current, [])
            continue
        if raw.startswith("+++ "):
            p = raw[4:].strip()
            if p != "/dev/null":
                if p.startswith("b/"):
                    p = p[2:]
                current = p
                result.setdefault(current, [])
            continue
        if raw.startswith("@@"):
            mm = re.search(r"\+(\d+)(?:,\d+)?", raw)
            if mm:
                new_line = int(mm.group(1))
                in_hunk = True
            else:
                in_hunk = False
            continue
        if not in_hunk or current is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            result.setdefault(current, []).append((new_line, raw[1:]))
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            pass
        else:
            new_line += 1
    return result


def find_contiguous_added_block(
    path: str,
    minus_lines: list[str],
    contents: dict[str, list[tuple[int, str]]],
) -> tuple[int, int] | None:
    """Locate minus_lines as a contiguous sequence of PR `+` lines. Return (start, end)."""
    if not minus_lines:
        return None
    # normalize trailing whitespace for matching
    target = [ln.rstrip("\n\r") for ln in minus_lines]
    rows = contents.get(path) or []
    # also try resolve_path keys
    if not rows:
        for k in contents:
            if k.endswith("/" + path) or k.endswith(path) or path.endswith(k):
                rows = contents[k]
                path = k
                break
    hay = [c.rstrip("\n\r") for _, c in rows]
    n, m = len(hay), len(target)
    if m == 0 or n < m:
        return None
    for i in range(n - m + 1):
        if hay[i : i + m] == target:
            start = rows[i][0]
            end = rows[i + m - 1][0]
            return start, end
    # fuzzy: strip all whitespace
    t2 = [re.sub(r"\s+", " ", t.strip()) for t in target]
    h2 = [re.sub(r"\s+", " ", h.strip()) for h in hay]
    for i in range(n - m + 1):
        if h2[i : i + m] == t2:
            start = rows[i][0]
            end = rows[i + m - 1][0]
            return start, end
    return None


# ---------------------------------------------------------------------------
# F54: Fix-it agent prompt per inline finding (Claude Code / coding-agent ready)
# ---------------------------------------------------------------------------


def fixit_prompts_enabled_from_env() -> bool:
    """TORII_FIXIT_PROMPTS via F55 registry (default on)."""
    return bool(_toggle_enabled("fixit_prompts"))


def _slug_commit_subject(issue: str, path: str) -> str:
    """Short conventional-commit subject from issue text."""
    base = (issue or "").strip()
    # drop trailing period and collapse whitespace
    base = re.sub(r"\s+", " ", base).rstrip(".")
    if len(base) > 72:
        base = base[:69].rstrip() + "..."
    area = Path(path).stem if path else "review"
    area = re.sub(r"[^a-zA-Z0-9_-]+", "-", area).strip("-").lower() or "review"
    if not base:
        base = f"address review finding in {area}"
    return f"fix({area}): {base[:60]}"


def format_fixit_prompt(
    *,
    path: str,
    line: int,
    severity: str,
    issue: str,
    trigger: str = "",
    source: str = "findings",
) -> str:
    """Return a collapsible, copy-pasteable agent prompt for this finding.

    Designed for Claude Code / Cursor / coding agents: file+line+issue,
    acceptance criteria, how-to-fix, verify checklist, commit message.
    """
    sev = (severity or "medium").upper()
    issue_s = (issue or "").strip() or "(see review finding)"
    trigger_s = (trigger or "").strip()
    commit = _slug_commit_subject(issue_s, path)
    trigger_block = (
        f"- Trigger scenario: {trigger_s}\n" if trigger_s else ""
    )
    verify_trigger = (
        f"- [ ] Reproduce the trigger: {trigger_s}\n" if trigger_s else ""
    )
    # Prompt body is fenced so authors can select-all copy without the summary chrome
    agent_prompt = f"""You are implementing a fix for a Torii PR-review finding on the current PR branch.

## Finding
- File: `{path}`
- Line: {line}
- Severity: {sev}
- Source: {source}
- Issue: {issue_s}
{trigger_block}
## Acceptance criteria
1. The defect described above is fixed at `{path}` (around line {line}) or the nearest correct call site.
2. Behavior under the trigger scenario no longer fails (if a trigger was given).
3. Add or adjust a focused regression test when the finding implies a fail mode; do not weaken existing assertions.
4. No unrelated refactors or drive-by cleanups.
5. Diff stays reviewable (prefer the smallest correct change).

## How to fix
1. Open `{path}` near line {line} and read surrounding context + the PR diff for that file.
2. Address: {issue_s}
3. Prefer the concrete code suggestion in the full Torii Gate review when one maps to this file; otherwise implement the minimal correct fix.
4. Keep public APIs stable unless the finding requires a contract change (document it in the commit body).

## Verify
{verify_trigger}- [ ] Run the most relevant unit/integration tests for this area
- [ ] Confirm no new linter/type errors on touched files
- [ ] Re-read the changed hunks against the acceptance criteria

## Commit
Suggested message:
```
{commit}
```
Push to the existing PR branch (do not force-push shared history).
"""
    # Collapse in GitHub UI so inline threads stay scannable
    block = (
        "<details>\n"
        "<summary>🛠️ Fix-it prompt (copy for Claude Code / agent)</summary>\n\n"
        "Paste into your coding agent on this PR branch:\n\n"
        f"````markdown\n{agent_prompt.strip()}\n````\n\n"
        "<!-- torii-fixit -->\n"
        "</details>"
    )
    return block


def format_suggestion_body(title: str, plus_lines: list[str]) -> str:
    # GitHub apply block — no language tag extras inside
    inner = "\n".join(plus_lines)
    # GitHub forbids trailing fence issues; ensure single trailing newline before close
    body = f"**Suggestion (F9c):** {title}\n\n```suggestion\n{inner}\n```\n\n<!-- torii-suggestion -->"
    return body[:65000]


def plan_suggestions(
    review_md: str,
    diff_text: str,
    *,
    max_n: int = 3,
) -> list[dict[str, Any]]:
    """Plan F9c multi-line suggestion comments."""
    specs = parse_code_suggestions(review_md)
    contents = added_line_contents_by_path(diff_text)
    added = added_lines_by_path(diff_text)
    planned: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()

    for spec in specs:
        path = str(spec["path"])
        resolved = resolve_path(path, contents) or resolve_path(path, added)
        if resolved is None:
            continue
        path = resolved
        minus: list[str] = list(spec.get("minus") or [])
        plus: list[str] = list(spec.get("plus") or [])
        title = str(spec.get("title") or "code suggestion")

        start_line: int | None = None
        end_line: int | None = None
        anchor = "none"

        if minus:
            block = find_contiguous_added_block(path, minus, contents)
            if block:
                start_line, end_line = block
                anchor = "exact_minus" if start_line != end_line else "exact_minus_1"
        if start_line is None:
            # Fallback: pin to first added line (single-line suggestion only if 1 + line)
            lines = added.get(path) or []
            if not lines:
                continue
            start_line = end_line = lines[0]
            anchor = "first"
            # Without minus mapping, only safe if we replace a single known line:
            # use first + line content as implicit minus when plus is replacement-sized
            if not minus and plus:
                # single-line replace of first added line
                end_line = start_line
            elif not plus:
                continue

        if not plus:
            # deletion-only suggestion: empty suggestion body
            plus = [""]

        key = (path, int(start_line), int(end_line or start_line))
        if key in seen:
            continue
        seen.add(key)

        comment: dict[str, Any] = {
            "path": path,
            "line": int(end_line or start_line),
            "side": "RIGHT",
            "body": format_suggestion_body(title, plus),
            "severity": "suggestion",
            "source": "code_suggestions",
            "kind": "suggestion",
            "anchor": anchor,
            "title": title,
        }
        if start_line is not None and end_line is not None and start_line != end_line:
            comment["start_line"] = int(start_line)
            comment["start_side"] = "RIGHT"
        planned.append(comment)
        if len(planned) >= max_n:
            break
    return planned


def enabled_from_env() -> bool:
    """TORII_INLINE_COMMENTS via F55 registry (default on)."""
    return bool(_toggle_enabled("inline_comments"))


def severity_set_from_env() -> set[str]:
    raw = (os.environ.get("TORII_INLINE_SEVERITY") or "critical,high,blocking").strip()
    if not raw or raw.lower() in ("*", "all"):
        return set()
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def max_from_env() -> int:
    try:
        return max(1, min(20, int(os.environ.get("TORII_INLINE_MAX") or "6")))
    except ValueError:
        return 6


def post_review(
    repo: str,
    pr: int,
    commit: str,
    comments: list[dict[str, Any]],
    *,
    event: str = "COMMENT",
) -> dict[str, Any]:
    """Submit a PR review with inline comments via gh api."""
    if not comments:
        return {"ok": True, "posted": 0, "skipped": "no comments"}

    n_find = sum(1 for c in comments if c.get("kind") != "suggestion")
    n_sug = sum(1 for c in comments if c.get("kind") == "suggestion")
    n_fixit = sum(1 for c in comments if c.get("fixit"))
    bits = []
    if n_find:
        bits.append(f"{n_find} finding note(s)")
    if n_sug:
        bits.append(f"{n_sug} apply-suggestion(s) (F9c)")
    if n_fixit:
        bits.append(f"{n_fixit} fix-it prompt(s) (F54)")
    body = (
        "## 🏴‍☠️ Torii inline findings (F9/F9c/F54)\n\n"
        + (", ".join(bits) if bits else f"{len(comments)} note(s)")
        + " — path-anchored on changed lines "
        "(see full PR comment for context). Expand **Fix-it prompt** on a "
        "finding to copy a Claude Code / coding-agent task.\n\n"
        f"<!-- torii-inline-review pr={pr} -->"
    )
    api_comments: list[dict[str, Any]] = []
    for c in comments:
        item: dict[str, Any] = {
            "path": c["path"],
            "line": c["line"],
            "side": c.get("side") or "RIGHT",
            "body": c["body"],
        }
        # F9c multi-line
        if c.get("start_line") is not None and int(c["start_line"]) != int(c["line"]):
            item["start_line"] = int(c["start_line"])
            item["start_side"] = c.get("start_side") or "RIGHT"
        api_comments.append(item)
    payload = {
        "commit_id": commit,
        "event": event,
        "body": body,
        "comments": api_comments,
    }

    # Fixture path first — offline tests need no token
    fixture = (os.environ.get("TORII_INLINE_FIXTURE") or "").strip()
    if fixture:
        Path(fixture).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "posted": len(comments), "fixture": fixture}

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        return {"ok": False, "error": "GH_TOKEN/GITHUB_TOKEN missing"}

    proc = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            "-H",
            "Accept: application/vnd.github+json",
            f"/repos/{repo}/pulls/{pr}/reviews",
            "--input",
            "-",
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GH_TOKEN": token, "GITHUB_TOKEN": token},
    )
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": (proc.stderr or proc.stdout or "gh api failed")[-800:],
            "posted": 0,
        }
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        data = {}
    return {
        "ok": True,
        "posted": len(comments),
        "review_id": data.get("id"),
        "html_url": data.get("html_url"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--review", type=Path, required=True)
        p.add_argument("--diff", type=Path, required=True)
        p.add_argument("--max", type=int, default=None)
        p.add_argument(
            "--severity",
            default=None,
            help="Comma list (default env TORII_INLINE_SEVERITY or critical,high,blocking)",
        )

    p_plan = sub.add_parser("plan", help="Offline plan (JSON to stdout)")
    add_common(p_plan)

    p_post = sub.add_parser("post", help="Post inline review comments via gh")
    add_common(p_post)
    p_post.add_argument("--repo", required=True)
    p_post.add_argument("--pr", type=int, required=True)
    p_post.add_argument("--commit", default="", help="Head SHA (required unless fixture)")
    p_post.add_argument(
        "--force",
        action="store_true",
        help="Ignore TORII_INLINE_COMMENTS=0",
    )

    args = ap.parse_args(argv)
    review_md = read_text(args.review)
    diff_text = read_text(args.diff)
    max_n = args.max if args.max is not None else max_from_env()
    if args.severity is not None:
        sev = (
            set()
            if args.severity.strip().lower() in ("*", "all", "")
            else {x.strip().lower() for x in args.severity.split(",") if x.strip()}
        )
    else:
        sev = severity_set_from_env()

    comments = plan_comments(review_md, diff_text, max_n=max_n, severities=sev)

    # F62: drop planned findings that match known FP/resolved patterns (soft)
    fp_suppressed = 0
    try:
        from fp_resolve_memory import (  # type: ignore
            enabled as _fp_enabled,
            build_plan as _fp_build,
            FpPattern,
        )

        if _fp_enabled():
            patterns: list[Any] = []
            # Prefer assemble artifact
            for cand in (
                Path(os.environ.get("OUT_DIR") or "") / "fp-resolve.json",
                Path("fp-resolve.json"),
            ):
                if cand.is_file():
                    try:
                        raw = json.loads(cand.read_text(encoding="utf-8"))
                        patterns = [
                            FpPattern(
                                kind=str(x.get("kind") or "false_positive"),
                                path=str(x.get("path") or ""),
                                line=x.get("line"),
                                reason=str(x.get("reason") or ""),
                                pr=str(x.get("pr") or ""),
                                source=str(x.get("source") or ""),
                                author=str(x.get("author") or ""),
                            )
                            for x in raw
                            if isinstance(x, dict)
                        ]
                        break
                    except (OSError, json.JSONDecodeError, TypeError):
                        patterns = []
            if patterns:
                kept: list[dict[str, Any]] = []
                for c in comments:
                    if c.get("kind") == "suggestion":
                        kept.append(c)
                        continue
                    path = str(c.get("path") or "")
                    line = c.get("line")
                    blob = f"`{path}:{line}` {c.get('body') or ''}" if line else f"`{path}` {c.get('body') or ''}"
                    hit = None
                    for p in patterns:
                        if not p.path:
                            continue
                        if normalize_path(p.path) != normalize_path(path):
                            continue
                        if p.line is not None and line is not None and int(p.line) != int(line):
                            if p.kind != "false_positive":
                                continue
                        hit = p
                        break
                    if hit is not None:
                        fp_suppressed += 1
                        continue
                    kept.append(c)
                comments = kept
    except Exception:
        fp_suppressed = 0

    if args.cmd == "plan":
        print(
            json.dumps(
                {
                    "ok": True,
                    "count": len(comments),
                    "findings": sum(1 for c in comments if c.get("kind") != "suggestion"),
                    "suggestions": sum(1 for c in comments if c.get("kind") == "suggestion"),
                    "fixit": sum(1 for c in comments if c.get("fixit")),
                    "fixit_enabled": fixit_prompts_enabled_from_env(),
                    "fp_suppressed": fp_suppressed,
                    "comments": comments,
                    "files_in_diff": len(first_added_lines(diff_text)),
                },
                indent=2,
            )
        )
        return 0

    # post
    if not args.force and not enabled_from_env():
        print(json.dumps({"ok": True, "skipped": "TORII_INLINE_COMMENTS off", "posted": 0}))
        return 0
    if not comments:
        print(
            json.dumps(
                {
                    "ok": True,
                    "posted": 0,
                    "skipped": "no mappable findings",
                    "fp_suppressed": fp_suppressed,
                }
            )
        )
        return 0

    # F60: split into thread replies vs new top-level inlines
    reply_posted = 0
    reply_meta: dict[str, Any] = {"enabled": False, "matched": 0}
    try:
        from reply_on_thread import (  # type: ignore
            enabled as _reply_enabled,
            fetch_review_comments,
            plan_replies,
            post_replies,
        )
    except ImportError:
        _reply_enabled = None  # type: ignore
        fetch_review_comments = None  # type: ignore
        plan_replies = None  # type: ignore
        post_replies = None  # type: ignore

    if (
        _reply_enabled is not None
        and plan_replies is not None
        and post_replies is not None
        and _reply_enabled()
    ):
        existing_path = (os.environ.get("TORII_REPLY_EXISTING") or "").strip()
        if existing_path and Path(existing_path).is_file():
            try:
                existing = json.loads(Path(existing_path).read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = []
        elif (os.environ.get("TORII_INLINE_FIXTURE") or "").strip():
            # Offline fixture runs: no network fetch unless TORII_REPLY_EXISTING set
            existing = []
        else:
            existing = fetch_review_comments(args.repo, args.pr) if fetch_review_comments else []
        if existing:
            split = plan_replies(comments, existing)
            reply_meta = {
                "enabled": True,
                "matched": split.get("matched", 0),
                "roots_indexed": split.get("roots_indexed", 0),
            }
            if split.get("replies"):
                pr_res = post_replies(args.repo, args.pr, split["replies"])
                reply_posted = int(pr_res.get("posted") or 0)
                reply_meta["post"] = pr_res
            comments = list(split.get("new_inlines") or [])

    if not comments and reply_posted:
        print(
            json.dumps(
                {
                    "ok": True,
                    "posted": 0,
                    "replies_posted": reply_posted,
                    "f60": reply_meta,
                    "skipped": "all findings replied on existing threads",
                },
                indent=2,
            )
        )
        return 0
    if not comments:
        print(json.dumps({"ok": True, "posted": 0, "skipped": "no mappable findings", "f60": reply_meta}))
        return 0

    commit = (args.commit or os.environ.get("HEAD_SHA") or "").strip()
    if not commit and not (os.environ.get("TORII_INLINE_FIXTURE") or "").strip():
        print(
            json.dumps({"ok": False, "error": "commit SHA required", "posted": 0}),
            file=sys.stderr,
        )
        return 0  # soft
    result = post_review(args.repo, args.pr, commit or "0" * 40, comments)
    result["replies_posted"] = reply_posted
    result["f60"] = reply_meta
    print(json.dumps(result, indent=2))
    return 0  # always soft for pipeline


if __name__ == "__main__":
    raise SystemExit(main())
