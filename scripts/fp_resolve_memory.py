#!/usr/bin/env python3
"""F62: false-positive resolve + memory update.

Deterministic control plane (no LLM):
  1. Mine author replies on Torii inline threads (+ optional PR issue comments)
  2. Classify as false_positive | resolved via regex
  3. Attach parent finding path/line + short quote
  4. Merge with existing MEMORY.md ``## FP patterns`` section
  5. Inject a trusted prompt section: do not re-raise without new evidence
  6. Persist structured FP bullets into MEMORY.md after a successful review
  7. F64: durable `.torii/fp-rules.json` (structured self-learn store)

Usage:
  python3 scripts/fp_resolve_memory.py classify --body "not a bug, by design"
  python3 scripts/fp_resolve_memory.py plan \\
    --comments comments.json [--memory MEMORY.md] [--issue-comments ic.json]
  python3 scripts/fp_resolve_memory.py assemble \\
    --repo o/r --pr 3 --out-dir .torii-out
  python3 scripts/fp_resolve_memory.py update \\
    --out-dir .torii-out [--memory path/to/MEMORY.md]
  python3 scripts/fp_resolve_memory.py section --json fp-resolve.json

Env:
  TORII_FP_RESOLVE          1 (default) | 0/off
  TORII_FP_RESOLVE_MAX      max patterns kept (default 24)
  TORII_FP_RESOLVE_FIXTURE  path to JSON list of review comments (no network)
  TORII_FP_RESOLVE_ISSUE_FIXTURE  optional PR conversation comments JSON
  TORII_FP_RULES_FILE            path to durable fp-rules.json (F64)
  GH_TOKEN for live fetch
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from feature_toggles import is_enabled as _toggle_enabled  # type: ignore
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from feature_toggles import is_enabled as _toggle_enabled  # type: ignore
    except ImportError:
        _toggle_enabled = None  # type: ignore


_DEFAULT_MAX = 24

_TORII_INLINE_MARKERS = (
    "<!-- torii-inline -->",
    "<!-- torii-inline-review",
    "torii inline findings",
    "🏴‍☠️ torii inline",
)

# Author pushback → treat prior finding as false positive / won't-fix.
_FP_RX = re.compile(
    r"(?i)\b(?:"
    r"false[\s-]?positive|not\s+a\s+bug|not\s+a\s+defect|"
    r"by\s+design|intentional(?:ly)?|working\s+as\s+intended|"
    r"expected\s+behaviou?r|wont\s*fix|won't\s+fix|"
    r"will\s+not\s+fix|not\s+applicable|n/?a\s+for\s+this|"
    r"won't\s+address|will\s+not\s+address|disagree(?:\s+with)?|"
    r"invalid\s+finding|already\s+safe|already\s+handled|"
    r"not\s+a\s+concern|no\s+issue\s+here|spurious|"
    r"out\s+of\s+scope|won't\s+change|wont\s+change|"
    r"this\s+is\s+fine|lgtm\s+on\s+this|not\s+a\s+problem|"
    r"pre-?existing|unrelated\s+to\s+this\s+pr|"
    r"won't\s+reopen|dismiss(?:ed|ing)?\s+(?:this\s+)?finding"
    r")\b"
)

# Author claims the finding is fixed in current head.
_RESOLVED_RX = re.compile(
    r"(?i)\b(?:"
    r"fixed(?:\s+in\s+(?:latest|head|this\s+push))?|"
    r"resolved|addressed|done\s+in\s+(?:latest|head|new\s+commit)|"
    r"pushed\s+a\s+fix|updated\s+the\s+code|landed\s+in|"
    r"should\s+be\s+fixed|this\s+is\s+fixed|now\s+fixed|"
    r"fixed\s+in\s+(?:the\s+)?(?:latest\s+)?commits?|"
    r"addressed\s+in\s+(?:the\s+)?latest|"
    r"see\s+(?:the\s+)?(?:latest\s+)?commit"
    r")\b"
)

# Soft: author reaction-style short acks that alone are weak — need path context.
_WEAK_RESOLVED_RX = re.compile(
    r"(?i)^\s*(?:fixed|done|resolved|addressed|👍|✅|lgtm)\s*[.!]?\s*$"
)

_PATH_LINE_IN_BODY = re.compile(
    r"`(?P<path>[^`\n]+?)(?::(?P<line>\d{1,7}))?`"
)

_FP_MEM_LINE = re.compile(
    r"^-+\s*"
    r"(?:`(?P<path>[^`]+)`\s*)?"
    r"(?:kind=(?P<kind>false_positive|resolved)\s*)?"
    r"(?:pr=#?(?P<pr>\d+)\s*)?"
    r"(?:reason=\"(?P<reason>[^\"]*)\")?"
    r"(?P<rest>.*)$",
    re.IGNORECASE,
)

_FP_SECTION_HDR = re.compile(
    r"^##\s+FP patterns\s*$", re.MULTILINE | re.IGNORECASE
)


def _truthy(val: str | None, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "disabled", "n")


def enabled(raw: str | None = None) -> bool:
    if _toggle_enabled is not None:
        try:
            return bool(_toggle_enabled("fp_resolve"))
        except Exception:
            pass
    v = raw if raw is not None else os.environ.get("TORII_FP_RESOLVE")
    return _truthy(v, default=True)


def max_patterns() -> int:
    try:
        return max(1, min(80, int(os.environ.get("TORII_FP_RESOLVE_MAX") or _DEFAULT_MAX)))
    except ValueError:
        return _DEFAULT_MAX



RULES_SCHEMA_VERSION = 1
RULES_FILENAME = "fp-rules.json"


def rules_path_candidates(memory_path: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    """Ordered candidates for durable F64 fp-rules.json."""
    out: list[Path] = []
    env = (os.environ.get("TORII_FP_RULES_FILE") or "").strip()
    if env:
        out.append(Path(env))
    if out_dir is not None:
        out.append(Path(out_dir) / RULES_FILENAME)
        out.append(Path(out_dir) / "fp-resolve-rules.json")
    hermes = os.environ.get("HERMES_HOME", "")
    if hermes:
        out.append(Path(hermes) / "memories" / RULES_FILENAME)
    if memory_path is not None:
        mp = Path(memory_path)
        out.append(mp.parent / RULES_FILENAME if mp.name.lower().endswith(".md") else mp / RULES_FILENAME)
    mem_root = (os.environ.get("TORII_MEMORY_PATH") or ".torii").strip()
    out.append(Path(mem_root) / RULES_FILENAME)
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[Path] = []
    for c in out:
        k = str(c)
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq


def patterns_from_rules_file(path: Path | None) -> list["FpPattern"]:
    if not path or not Path(path).is_file():
        return []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return []
    rules = data.get("rules") if isinstance(data, dict) else data
    if not isinstance(rules, list):
        return []
    out: list[FpPattern] = []
    for x in rules:
        if not isinstance(x, dict):
            continue
        line = x.get("line")
        try:
            line_i = int(line) if line is not None and str(line).strip() != "" else None
        except (TypeError, ValueError):
            line_i = None
        out.append(
            FpPattern(
                kind=str(x.get("kind") or "false_positive"),
                path=str(x.get("path") or ""),
                line=line_i,
                reason=str(x.get("reason") or ""),
                pr=str(x.get("pr") or ""),
                parent_id=x.get("parent_id"),
                reply_id=x.get("reply_id"),
                source=str(x.get("source") or "rules"),
                author=str(x.get("author") or ""),
            )
        )
    return out


def load_rules_file(
    *,
    memory_path: Path | None = None,
    out_dir: Path | None = None,
    explicit: Path | None = None,
) -> tuple[list["FpPattern"], str]:
    """Load first existing durable rules file. Returns (patterns, source_path)."""
    cands: list[Path] = []
    if explicit is not None:
        cands.append(Path(explicit))
    cands.extend(rules_path_candidates(memory_path=memory_path, out_dir=out_dir))
    for c in cands:
        if c.is_file():
            pats = patterns_from_rules_file(c)
            if pats or c.stat().st_size > 2:
                return pats, str(c)
    return [], ""


def rules_document(patterns: list["FpPattern"]) -> dict[str, Any]:
    return {
        "schema_version": RULES_SCHEMA_VERSION,
        "feature": "F64",
        "count": len(patterns),
        "rules": [p.as_dict() for p in patterns],
    }


def save_rules_file(path: Path, patterns: list["FpPattern"]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # merge with existing on disk
    existing = patterns_from_rules_file(path)
    merged = merge_patterns(patterns, existing)
    path.write_text(json.dumps(rules_document(merged), indent=2) + "\n", encoding="utf-8")
    return path


def is_torii_inline_body(body: str) -> bool:
    if not body:
        return False
    low = body.lower()
    return any(m in low for m in _TORII_INLINE_MARKERS)


def normalize_path(raw: str) -> str:
    s = (raw or "").strip().strip("`").strip()
    if s.startswith(("a/", "b/")):
        s = s[2:]
    if re.search(r":\d+$", s):
        s = re.sub(r":\d+$", "", s)
    return s


def classify_body(body: str) -> str | None:
    """Return 'false_positive' | 'resolved' | None."""
    text = (body or "").strip()
    if not text:
        return None
    # Prefer FP when both match (author said fixed but also "not a bug")
    if _FP_RX.search(text):
        return "false_positive"
    if _RESOLVED_RX.search(text) or _WEAK_RESOLVED_RX.search(text):
        return "resolved"
    return None


def extract_path_line(body: str, fallback: dict[str, Any] | None = None) -> tuple[str, int | None]:
    path = ""
    line: int | None = None
    if fallback:
        path = normalize_path(str(fallback.get("path") or ""))
        try:
            raw_line = fallback.get("line") or fallback.get("original_line")
            if raw_line is not None and str(raw_line).strip() != "":
                line = int(raw_line)
        except (TypeError, ValueError):
            line = None
    if not path and body:
        m = _PATH_LINE_IN_BODY.search(body)
        if m:
            path = normalize_path(m.group("path") or "")
            if m.group("line"):
                try:
                    line = int(m.group("line"))
                except ValueError:
                    pass
    return path, line


def short_quote(body: str, limit: int = 160) -> str:
    s = re.sub(r"\s+", " ", (body or "").strip())
    # drop HTML comments
    s = re.sub(r"<!--.*?-->", "", s).strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "…"


@dataclass
class FpPattern:
    kind: str  # false_positive | resolved
    path: str = ""
    line: int | None = None
    reason: str = ""
    pr: str = ""
    parent_id: int | None = None
    reply_id: int | None = None
    source: str = ""  # thread_reply | issue_comment | memory
    author: str = ""

    def key(self) -> str:
        """Dedupe identity: kind + path + line (reason may differ; prefer better source)."""
        path = normalize_path(self.path) if self.path else "?"
        if self.line is not None:
            return f"{self.kind}|{path}:{self.line}"
        return f"{self.kind}|{path}"

    def display_target(self) -> str:
        if self.path and self.line:
            return f"`{self.path}:{self.line}`"
        if self.path:
            return f"`{self.path}`"
        return "_(unanchored)_"

    def memory_bullet(self) -> str:
        parts = [f"- {self.display_target()}"]
        parts.append(f"kind={self.kind}")
        if self.pr:
            parts.append(f"pr=#{self.pr}")
        reason = self.reason.replace('"', "'")[:180]
        if reason:
            parts.append(f'reason="{reason}"')
        return " ".join(parts)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def parse_memory_fp_section(memory_md: str) -> list[FpPattern]:
    """Extract FP patterns from MEMORY.md ## FP patterns section."""
    if not memory_md:
        return []
    m = _FP_SECTION_HDR.search(memory_md)
    if not m:
        return []
    rest = memory_md[m.end() :]
    # until next ## heading
    stop = re.search(r"\n##\s+", rest)
    if stop:
        rest = rest[: stop.start()]
    out: list[FpPattern] = []
    for line in rest.splitlines():
        s = line.strip()
        if not s.startswith("-"):
            continue
        path = ""
        line_no: int | None = None
        kind = "false_positive"
        pr = ""
        reason = ""
        pm = re.search(r"`([^`]+)`", s)
        if pm:
            raw = pm.group(1)
            if re.search(r":\d+$", raw):
                path = normalize_path(raw)
                try:
                    line_no = int(raw.rsplit(":", 1)[-1])
                except ValueError:
                    path = normalize_path(raw)
            else:
                path = normalize_path(raw)
        km = re.search(r"kind=(false_positive|resolved)", s, re.I)
        if km:
            kind = km.group(1).lower()
        prm = re.search(r"pr=#?(\d+)", s, re.I)
        if prm:
            pr = prm.group(1)
        rm = re.search(r'reason="([^"]*)"', s)
        if rm:
            reason = rm.group(1)
        else:
            # freeform after dash without structured fields
            if "kind=" not in s and not reason:
                reason = re.sub(r"^-+\s*", "", s)
                reason = re.sub(r"`[^`]+`", "", reason).strip(" -:")
        out.append(
            FpPattern(
                kind=kind,
                path=path,
                line=line_no,
                reason=short_quote(reason, 180),
                pr=pr,
                source="memory",
            )
        )
    return out


def _is_bot_login(login: str) -> bool:
    low = (login or "").lower()
    if not low:
        return False
    if low.endswith("[bot]") or low.endswith("-bot"):
        return True
    if "torii" in low or low in ("github-actions[bot]", "copilot-pull-request-reviewer[bot]"):
        return True
    return False


def patterns_from_review_comments(
    comments: list[dict[str, Any]],
    *,
    pr: str = "",
) -> list[FpPattern]:
    """Walk review comments; author replies to Torii roots become FP patterns."""
    by_id: dict[int, dict[str, Any]] = {}
    for c in comments:
        try:
            cid = int(c.get("id") or 0)
        except (TypeError, ValueError):
            continue
        if cid:
            by_id[cid] = c

    out: list[FpPattern] = []
    for c in comments:
        body = str(c.get("body") or "")
        user = c.get("user") or {}
        login = str(user.get("login") or c.get("user_login") or "")
        if _is_bot_login(login):
            continue
        kind = classify_body(body)
        if not kind:
            continue
        parent_id = c.get("in_reply_to_id") or c.get("in_reply_to")
        parent: dict[str, Any] | None = None
        if parent_id is not None:
            try:
                parent = by_id.get(int(parent_id))
            except (TypeError, ValueError):
                parent = None
        # Prefer replies under Torii roots; allow top-level author notes that cite a path
        if parent is not None:
            pbody = str(parent.get("body") or "")
            if not is_torii_inline_body(pbody) and "torii" not in pbody.lower():
                # still allow if parent path is present (review comment on file)
                if not (parent.get("path") or parent.get("line")):
                    continue
            path, line = extract_path_line(pbody, parent)
            if not path:
                path, line = extract_path_line(body, c)
            reason_src = body
            try:
                pid = int(parent.get("id") or parent_id or 0) or None
            except (TypeError, ValueError):
                pid = None
        else:
            # top-level author review comment with path + FP language
            path, line = extract_path_line(body, c)
            if not path:
                continue
            reason_src = body
            pid = None
        try:
            rid = int(c.get("id") or 0) or None
        except (TypeError, ValueError):
            rid = None
        out.append(
            FpPattern(
                kind=kind,
                path=path,
                line=line,
                reason=short_quote(reason_src),
                pr=str(pr or ""),
                parent_id=pid,
                reply_id=rid,
                source="thread_reply",
                author=login,
            )
        )
    return out


def patterns_from_issue_comments(
    comments: list[dict[str, Any]],
    *,
    pr: str = "",
) -> list[FpPattern]:
    """PR conversation comments that explicitly mark a path finding as FP/resolved."""
    out: list[FpPattern] = []
    for c in comments:
        body = str(c.get("body") or "")
        user = c.get("user") or {}
        login = str(user.get("login") or c.get("user_login") or "")
        if _is_bot_login(login):
            continue
        kind = classify_body(body)
        if not kind:
            continue
        path, line = extract_path_line(body, None)
        # require a path cite for issue-comment signals (noise control)
        if not path:
            continue
        try:
            rid = int(c.get("id") or 0) or None
        except (TypeError, ValueError):
            rid = None
        out.append(
            FpPattern(
                kind=kind,
                path=path,
                line=line,
                reason=short_quote(body),
                pr=str(pr or ""),
                reply_id=rid,
                source="issue_comment",
                author=login,
            )
        )
    return out


def merge_patterns(*groups: list[FpPattern], limit: int | None = None) -> list[FpPattern]:
    """Dedupe by key; prefer thread_reply over issue_comment over memory."""
    prio = {"thread_reply": 0, "issue_comment": 1, "rules": 2, "memory": 3, "": 4}
    best: dict[str, FpPattern] = {}
    for group in groups:
        for p in group:
            k = p.key()
            if k not in best or prio.get(p.source, 9) < prio.get(best[k].source, 9):
                best[k] = p
    items = list(best.values())
    # false_positive first, then resolved; path stable
    items.sort(
        key=lambda x: (
            0 if x.kind == "false_positive" else 1,
            x.path or "",
            x.line or 0,
        )
    )
    lim = limit if limit is not None else max_patterns()
    return items[:lim]


def render_section(patterns: list[FpPattern], *, title: str = "Known false positives / resolved findings (F62)") -> str:
    lines = [f"## {title}", ""]
    if not patterns:
        lines.append(
            "_No author-resolved or false-positive signals on this PR yet._"
        )
        lines.append("")
        return "\n".join(lines)
    lines.append(
        "Do **not** re-raise these without **new evidence** in the current diff "
        "(code changed, new trigger, or stronger proof). Prefer silence over "
        "repeating dismissed noise (D1 signal)."
    )
    lines.append("")
    lines.append("| Kind | Target | Why (author/memory) | Source |")
    lines.append("|------|--------|---------------------|--------|")
    for p in patterns:
        why = (p.reason or "—").replace("|", "\\|")
        if len(why) > 100:
            why = why[:99] + "…"
        src = p.source or "—"
        if p.author:
            src = f"{src}/{p.author}"
        lines.append(
            f"| {p.kind} | {p.display_target()} | {why} | {src} |"
        )
    lines.append("")
    lines.append(
        "If you still flag a matching path, explain what is **new** vs the prior dismissal."
    )
    lines.append("")
    return "\n".join(lines)


def render_markdown(patterns: list[FpPattern]) -> str:
    lines = ["# FP resolve + memory (F62)", ""]
    lines.append(f"count={len(patterns)}")
    lines.append("")
    for p in patterns:
        lines.append(p.memory_bullet())
    lines.append("")
    return "\n".join(lines)


def render_memory_section(patterns: list[FpPattern]) -> str:
    """Standalone ## FP patterns block for MEMORY.md merge."""
    lines = ["## FP patterns", ""]
    lines.append(
        "Author-resolved or false-positive findings. Do not re-raise without new evidence."
    )
    lines.append("")
    if not patterns:
        lines.append("- _(none yet)_")
    else:
        for p in patterns:
            lines.append(p.memory_bullet())
    lines.append("")
    return "\n".join(lines)


def apply_to_prompt(prompt: str, section: str) -> str:
    """Inject trusted FP section into assembled prompt."""
    if "{{FP_RESOLVE}}" in prompt:
        return prompt.replace("{{FP_RESOLVE}}", section.rstrip())
    block = "\n" + section.rstrip() + "\n"
    # Prefer after linked issues / before changed files
    for marker in (
        "## Changed files summary\n",
        "## Suggested test plan (auto, F61)\n",
        "## Required Markdown template\n",
    ):
        idx = prompt.find(marker)
        if idx >= 0:
            return prompt[:idx] + block + "\n" + prompt[idx:]
    return prompt.rstrip() + "\n" + block


def merge_into_memory(memory_md: str, patterns: list[FpPattern], *, max_bytes: int = 100_000) -> str:
    """Upsert ## FP patterns section in MEMORY.md text."""
    if not patterns:
        if not memory_md:
            return ""
        return memory_md if memory_md.endswith("\n") else memory_md + "\n"
    existing = parse_memory_fp_section(memory_md)
    merged = merge_patterns(patterns, existing)
    section = render_memory_section(merged)
    text = memory_md or "# Torii Gate review memory\n\n"
    m = _FP_SECTION_HDR.search(text)
    if m:
        before = text[: m.start()]
        rest = text[m.end() :]
        stop = re.search(r"\n##\s+", rest)
        after = rest[stop.start() :] if stop else ""
        text = before.rstrip() + "\n\n" + section.rstrip() + "\n" + after
    else:
        text = text.rstrip() + "\n\n" + section
    data = text.encode("utf-8")
    if len(data) > max_bytes:
        text = data[-max_bytes:].decode("utf-8", errors="ignore")
        idx = text.find("\n## ")
        if idx > 0:
            text = "# Torii Gate review memory\n\n_(older entries rotated)_\n" + text[idx:]
        else:
            text = "# Torii Gate review memory\n\n_(rotated)_\n" + text
    return text if text.endswith("\n") else text + "\n"


def finding_matches_fp(finding_text: str, patterns: list[FpPattern]) -> FpPattern | None:
    """If a review finding line cites a known FP path, return the pattern."""
    if not finding_text or not patterns:
        return None
    path, line = extract_path_line(finding_text, None)
    if not path:
        return None
    for p in patterns:
        if not p.path:
            continue
        if normalize_path(p.path) != normalize_path(path):
            continue
        if p.line is not None and line is not None and p.line != line:
            # path-level FP still matches if kind is false_positive and reason strong
            if p.kind == "false_positive":
                return p
            continue
        return p
    return None


def _gh_json(args: list[str]) -> Any:
    env = os.environ.copy()
    token = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN") or ""
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    proc = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh failed")
    return json.loads(proc.stdout or "[]")


def fetch_review_comments(repo: str, pr: str | int) -> list[dict[str, Any]]:
    fixture = os.environ.get("TORII_FP_RESOLVE_FIXTURE", "").strip()
    if fixture:
        return json.loads(Path(fixture).read_text(encoding="utf-8"))
    # pull request review comments (inline)
    data = _gh_json(
        [
            "api",
            f"repos/{repo}/pulls/{pr}/comments",
            "--paginate",
        ]
    )
    if isinstance(data, list):
        return data
    return []


def fetch_issue_comments(repo: str, pr: str | int) -> list[dict[str, Any]]:
    fixture = os.environ.get("TORII_FP_RESOLVE_ISSUE_FIXTURE", "").strip()
    if fixture:
        return json.loads(Path(fixture).read_text(encoding="utf-8"))
    data = _gh_json(
        [
            "api",
            f"repos/{repo}/issues/{pr}/comments",
            "--paginate",
        ]
    )
    if isinstance(data, list):
        return data
    return []


def load_json_list(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("comments"), list):
        return data["comments"]
    return []


def build_plan(
    *,
    review_comments: list[dict[str, Any]] | None = None,
    issue_comments: list[dict[str, Any]] | None = None,
    memory_md: str = "",
    rules: list[FpPattern] | None = None,
    pr: str = "",
    limit: int | None = None,
) -> list[FpPattern]:
    thr = patterns_from_review_comments(review_comments or [], pr=pr)
    iss = patterns_from_issue_comments(issue_comments or [], pr=pr)
    mem = parse_memory_fp_section(memory_md)
    rul = list(rules or [])
    return merge_patterns(thr, iss, rul, mem, limit=limit)


def assemble(
    *,
    repo: str,
    pr: str | int,
    out_dir: Path,
    memory_path: Path | None = None,
    prompt_path: Path | None = None,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "enabled": "0",
        "count": "0",
        "fp": "0",
        "resolved": "0",
        "source": "none",
    }
    if not enabled():
        (out_dir / "fp-resolve.env").write_text(
            "FP_RESOLVE=0\nFP_RESOLVE_COUNT=0\n", encoding="utf-8"
        )
        return result

    memory_md = ""
    mem_src = ""
    candidates = []
    if memory_path:
        candidates.append(Path(memory_path))
    # common locations
    hermes = os.environ.get("HERMES_HOME", "")
    if hermes:
        candidates.append(Path(hermes) / "memories" / "MEMORY.md")
    torii_root = Path(os.environ.get("TORII_ROOT") or Path(__file__).resolve().parents[1])
    candidates.append(torii_root / "agent" / "MEMORY.seed.md")
    # target-repo local pack may be preloaded into OUT_DIR
    candidates.append(out_dir / "memory-before.md")
    for c in candidates:
        try:
            if c.is_file() and c.stat().st_size > 0:
                memory_md = c.read_text(encoding="utf-8", errors="replace")
                mem_src = str(c)
                break
        except OSError:
            continue

    review_comments: list[dict[str, Any]] = []
    issue_comments: list[dict[str, Any]] = []
    src = "memory" if memory_md else "none"
    try:
        review_comments = fetch_review_comments(repo, pr)
        src = "live" if not os.environ.get("TORII_FP_RESOLVE_FIXTURE") else "fixture"
    except Exception as e:
        (out_dir / "fp-resolve-fetch.err").write_text(str(e), encoding="utf-8")
    try:
        issue_comments = fetch_issue_comments(repo, pr)
    except Exception:
        issue_comments = []

    rules_pats, rules_src = load_rules_file(
        memory_path=Path(memory_path) if memory_path else None,
        out_dir=out_dir,
    )
    if rules_src:
        mem_src = (mem_src + f"+rules:{rules_src}") if mem_src else f"rules:{rules_src}"

    patterns = build_plan(
        review_comments=review_comments,
        issue_comments=issue_comments,
        memory_md=memory_md,
        rules=rules_pats,
        pr=str(pr),
    )
    sec = render_section(patterns)
    (out_dir / "fp-resolve.json").write_text(
        json.dumps([p.as_dict() for p in patterns], indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "fp-resolve.md").write_text(render_markdown(patterns), encoding="utf-8")
    (out_dir / "fp-resolve-section.md").write_text(sec, encoding="utf-8")

    # prompt inject
    ppath = prompt_path
    if ppath is None and os.environ.get("PROMPT_PATH"):
        ppath = Path(os.environ["PROMPT_PATH"])
    if ppath is None:
        cand = out_dir / "prompt.md"
        if cand.is_file():
            ppath = cand
    if ppath and ppath.is_file():
        prompt = ppath.read_text(encoding="utf-8", errors="replace")
        ppath.write_text(apply_to_prompt(prompt, sec), encoding="utf-8")

    n_fp = sum(1 for p in patterns if p.kind == "false_positive")
    n_res = sum(1 for p in patterns if p.kind == "resolved")
    result = {
        "enabled": "1",
        "count": str(len(patterns)),
        "fp": str(n_fp),
        "resolved": str(n_res),
        "source": src,
        "memory_src": mem_src,
    }
    env_lines = [
        f"FP_RESOLVE=1",
        f"FP_RESOLVE_COUNT={len(patterns)}",
        f"FP_RESOLVE_FP={n_fp}",
        f"FP_RESOLVE_RESOLVED={n_res}",
        f"FP_RESOLVE_SOURCE={src}",
    ]
    (out_dir / "fp-resolve.env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    return result


def update_memory(
    *,
    out_dir: Path,
    memory_path: Path | None = None,
    patterns: list[FpPattern] | None = None,
) -> dict[str, Any]:
    """Persist FP patterns into MEMORY.md after review."""
    out_dir = Path(out_dir)
    if not enabled():
        return {"updated": "0", "reason": "disabled"}

    if patterns is None:
        jpath = out_dir / "fp-resolve.json"
        if jpath.is_file():
            raw = json.loads(jpath.read_text(encoding="utf-8"))
            patterns = [
                FpPattern(
                    kind=str(x.get("kind") or "false_positive"),
                    path=str(x.get("path") or ""),
                    line=x.get("line"),
                    reason=str(x.get("reason") or ""),
                    pr=str(x.get("pr") or ""),
                    parent_id=x.get("parent_id"),
                    reply_id=x.get("reply_id"),
                    source=str(x.get("source") or "thread_reply"),
                    author=str(x.get("author") or ""),
                )
                for x in raw
                if isinstance(x, dict)
            ]
        else:
            patterns = []

    # Only persist live/thread signals (not pure memory echo)
    to_write = [p for p in patterns if p.source in ("thread_reply", "issue_comment")]
    if not to_write:
        return {"updated": "0", "reason": "no_new_signals", "count": "0"}

    mem_path = memory_path
    if mem_path is None:
        hermes = os.environ.get("HERMES_HOME", "")
        if hermes:
            mem_path = Path(hermes) / "memories" / "MEMORY.md"
    if mem_path is None:
        return {"updated": "0", "reason": "no_memory_path"}

    mem_path = Path(mem_path)
    existing = ""
    if mem_path.is_file():
        existing = mem_path.read_text(encoding="utf-8", errors="replace")
    else:
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        existing = "# Torii Gate review memory\n\n"

    new_text = merge_into_memory(existing, to_write)
    mem_path.write_text(new_text, encoding="utf-8")
    # also dump memory block artifact for hub ingest consumers
    (out_dir / "fp-resolve-memory-section.md").write_text(
        render_memory_section(merge_patterns(to_write, parse_memory_fp_section(new_text))),
        encoding="utf-8",
    )
    # F64: durable structured rules next to MEMORY + OUT_DIR
    rules_targets = [
        out_dir / RULES_FILENAME,
        mem_path.parent / RULES_FILENAME,
    ]
    env_rules = (os.environ.get("TORII_FP_RULES_FILE") or "").strip()
    if env_rules:
        rules_targets.insert(0, Path(env_rules))
    written_rules = ""
    for rt in rules_targets:
        try:
            save_rules_file(rt, to_write)
            if not written_rules:
                written_rules = str(rt)
        except OSError:
            continue
    return {
        "updated": "1",
        "count": str(len(to_write)),
        "memory": str(mem_path),
        "rules": written_rules,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F62 FP resolve + memory update")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("classify", help="classify a single body")
    c.add_argument("--body", required=True)

    pl = sub.add_parser("plan", help="build FP plan from JSON comments")
    pl.add_argument("--comments", type=Path, help="review comments JSON list")
    pl.add_argument("--issue-comments", type=Path, default=None)
    pl.add_argument("--memory", type=Path, default=None)
    pl.add_argument("--rules", type=Path, default=None, help="F64 fp-rules.json")
    pl.add_argument("--pr", default="")
    pl.add_argument("--json", action="store_true")

    a = sub.add_parser("assemble", help="fetch + write artifacts + inject prompt")
    a.add_argument("--repo", required=True)
    a.add_argument("--pr", required=True)
    a.add_argument("--out-dir", type=Path, required=True)
    a.add_argument("--memory", type=Path, default=None)
    a.add_argument("--prompt", type=Path, default=None)

    u = sub.add_parser("update", help="merge FP patterns into MEMORY.md")
    u.add_argument("--out-dir", type=Path, required=True)
    u.add_argument("--memory", type=Path, default=None)

    s = sub.add_parser("section", help="render section from json")
    s.add_argument("--json", type=Path, required=True)

    m = sub.add_parser("merge-memory", help="merge patterns json into memory file")
    m.add_argument("--memory", type=Path, required=True)
    m.add_argument("--patterns", type=Path, required=True)

    args = p.parse_args(argv)

    if args.cmd == "classify":
        kind = classify_body(args.body) or "none"
        print(f"kind={kind}")
        return 0

    if args.cmd == "plan":
        mem = ""
        if args.memory and args.memory.is_file():
            mem = args.memory.read_text(encoding="utf-8", errors="replace")
        rules = patterns_from_rules_file(args.rules) if getattr(args, "rules", None) else []
        patterns = build_plan(
            review_comments=load_json_list(args.comments),
            issue_comments=load_json_list(args.issue_comments),
            memory_md=mem,
            rules=rules,
            pr=args.pr,
        )
        if args.json:
            print(json.dumps([p.as_dict() for p in patterns], indent=2))
        else:
            print(render_section(patterns), end="")
            print(f"count={len(patterns)}")
        return 0

    if args.cmd == "assemble":
        r = assemble(
            repo=args.repo,
            pr=args.pr,
            out_dir=args.out_dir,
            memory_path=args.memory,
            prompt_path=args.prompt,
        )
        for k, v in r.items():
            print(f"{k}={v}")
        return 0

    if args.cmd == "update":
        r = update_memory(out_dir=args.out_dir, memory_path=args.memory)
        for k, v in r.items():
            print(f"{k}={v}")
        return 0

    if args.cmd == "section":
        raw = json.loads(args.json.read_text(encoding="utf-8"))
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
        print(render_section(patterns), end="")
        return 0

    if args.cmd == "merge-memory":
        mem = args.memory.read_text(encoding="utf-8", errors="replace") if args.memory.is_file() else "# Torii Gate review memory\n"
        raw = json.loads(args.patterns.read_text(encoding="utf-8"))
        patterns = [
            FpPattern(
                kind=str(x.get("kind") or "false_positive"),
                path=str(x.get("path") or ""),
                line=x.get("line"),
                reason=str(x.get("reason") or ""),
                pr=str(x.get("pr") or ""),
                source=str(x.get("source") or "thread_reply"),
                author=str(x.get("author") or ""),
            )
            for x in raw
            if isinstance(x, dict)
        ]
        new = merge_into_memory(mem, patterns)
        args.memory.write_text(new, encoding="utf-8")
        print(f"memory={args.memory}")
        print(f"count={len(patterns)}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
