#!/usr/bin/env python3
"""Normalize Hermes output into a GitHub-safe Torii Gate review Markdown contract."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_CHARS = 60_000

# Core contract — keep in sync with agent/review-prompt.md
REQUIRED_SNIPPETS = (
    "**Verdict:**",
    "**Score:**",
    "### Summary",
    "### Blocking",
    "### Security audit",
    "### Tests & risk",
)

# Soft sections we try to ensure exist (repair path only)
SOFT_SECTIONS = (
    "### Walkthrough",
    "### Architecture diagram",
    "### Key findings",
    "### Multi-lens checklist",
    "### Suggestions",
    "### Code suggestions",
    "### Nits",
    "### Suggested test plan",
    "### What I checked",
)

# F18: scrub secrets before the body hits GitHub PR comments / distill.
# Keep patterns aligned with scripts/save-trace.sh + build-hub-payload.py.
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-or-v1-[A-Za-z0-9_-]{10,}"), "[OPENROUTER_KEY_REDACTED]"),
    (re.compile(r"(OPENROUTER_API_KEY=)\S+"), r"\1[REDACTED]"),
    (
        re.compile(r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)", re.I),
        r"\1[REDACTED]",
    ),
    (re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"), "[GITHUB_TOKEN_REDACTED]"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "[GITHUB_TOKEN_REDACTED]"),
)


def redact_secrets(text: str) -> str:
    """Remove accidental API keys / tokens from model output before post."""
    out = text
    for rx, repl in _SECRET_PATTERNS:
        out = rx.sub(repl, out)
    return out


# F27: always-visible trust banner when assemble-context truncated the PR diff.
_TRUNCATION_BANNER = (
    "> ⚠️ **Diff truncated (F27)** — this review only saw the first "
    "`MAX_DIFF_BYTES` of the PR diff. Treat findings as incomplete; "
    "confidence may be lower than a full-diff review.\n"
)
_TRUNCATION_MARKER = "Diff truncated (F27)"


def inject_diff_truncated_banner(text: str, truncated: bool) -> str:
    """Insert a Markdown callout near the top when the assembled diff was capped."""
    if not truncated:
        return text
    if _TRUNCATION_MARKER in text:
        return text
    body = text.lstrip("\n")
    # Prefer after HTML marker / title, before **Verdict:**
    m = re.search(r"^(\*\*Verdict:\*\*)", body, re.M)
    if m:
        return body[: m.start()] + _TRUNCATION_BANNER + "\n" + body[m.start() :]
    # After first heading line
    lines = body.splitlines(keepends=True)
    if lines and lines[0].startswith("#"):
        return lines[0] + "\n" + _TRUNCATION_BANNER + "\n" + "".join(lines[1:])
    return _TRUNCATION_BANNER + "\n" + body


def strip_outer_fence(text: str) -> str:
    t = text.strip()
    if not (t.startswith("```") and t.endswith("```")):
        return t
    lines = t.splitlines()
    if len(lines) < 2:
        return t
    body = "\n".join(lines[1:-1])
    first = body.lstrip().splitlines()[:1]
    if first and first[0].strip().lower() in {"markdown", "md"}:
        body = "\n".join(body.splitlines()[1:])
    return body.strip()


# F44: hermes chat -q echoes "Query: …" + the full prompt (including the
# required Markdown *template*) before the real model answer. The template
# already contains every REQUIRED_SNIPPET, so a naive contract check would
# treat the polluted blob as valid and post the prompt to GitHub.
_REVIEW_HEADING_RX = re.compile(
    r"(?:^|\n)(?:#{1,3}\s*)?(?:🏴‍☠️\s*)?Torii Review\s*[—\-–]?\s*PR\s*#?\s*\d*",
    re.IGNORECASE,
)
_PLACEHOLDER_VERDICT_RX = re.compile(
    r"(?:\*\*)?Verdict:(?:\*\*)?\s*<[^>\n]+>",
    re.IGNORECASE,
)
_REAL_VERDICT_RX = re.compile(
    r"(?:\*\*)?Verdict:(?:\*\*)?\s*"
    r"(APPROVE|REQUEST\s*CHANGES|COMMENT|LGTM|CHANGES\s*REQUESTED)\b",
    re.IGNORECASE,
)
# Hermes TUI / CLI chrome — only lines that are *not* valid review content.
# Do NOT treat bare ─── rules as chrome: models often use them between findings.
_HERMES_CHROME_LINE_RX = re.compile(
    r"(?:"
    r"^Query:\s*"
    r"|^Initializing agent\b"
    r"|^Resume this session with:\s*"
    r"|^Session:\s+\S+"
    r"|^Duration:\s+"
    r"|^Messages:\s+\d+"
    r"|^[╭╰].*[╮╯]\s*$"  # full-width TUI box top/bottom
    r"|^╭─\s*⚕"  # Hermes panel header
    r"|^⚕\s*Hermes\b"
    r"|^⚠\s+tirith\b"
    r")",
    re.MULTILINE | re.IGNORECASE,
)
# Trailing session footer starts here — drop everything after
_HERMES_FOOTER_RX = re.compile(
    r"\n(?:Resume this session with:|Session:\s+\d{8}_\d+)",
    re.IGNORECASE,
)
_SECTION_ALIASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^#{0,3}\s*Summary\s*$", re.I | re.M), "### Summary"),
    (re.compile(r"^#{0,3}\s*Walkthrough\s*$", re.I | re.M), "### Walkthrough"),
    (re.compile(r"^#{0,3}\s*Architecture(?:\s+diagram)?\s*$", re.I | re.M), "### Architecture diagram"),
    (re.compile(r"^#{0,3}\s*Blocking\s*$", re.I | re.M), "### Blocking"),
    (re.compile(r"^#{0,3}\s*Key findings\s*$", re.I | re.M), "### Key findings"),
    (re.compile(r"^#{0,3}\s*Security audit\s*$", re.I | re.M), "### Security audit"),
    (re.compile(r"^#{0,3}\s*Multi-lens checklist\s*$", re.I | re.M), "### Multi-lens checklist"),
    (re.compile(r"^#{0,3}\s*Suggestions\s*$", re.I | re.M), "### Suggestions"),
    (re.compile(r"^#{0,3}\s*Code suggestions\s*$", re.I | re.M), "### Code suggestions"),
    (re.compile(r"^#{0,3}\s*Nits\s*$", re.I | re.M), "### Nits"),
    (re.compile(r"^#{0,3}\s*Tests\s*&\s*risk\s*$", re.I | re.M), "### Tests & risk"),
    (re.compile(r"^#{0,3}\s*What I checked\s*$", re.I | re.M), "### What I checked"),
)
_META_LINE_ALIASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\*{0,2}Verdict:\*{0,2}\s*", re.I | re.M), "**Verdict:** "),
    (re.compile(r"^\*{0,2}Confidence:\*{0,2}\s*", re.I | re.M), "**Confidence:** "),
    (re.compile(r"^\*{0,2}Score:\*{0,2}\s*", re.I | re.M), "**Score:** "),
    (re.compile(r"^\*{0,2}Review effort:\*{0,2}\s*", re.I | re.M), "**Review effort:** "),
)


def _looks_like_template_only(text: str) -> bool:
    """True when the only verdict is the angle-bracket prompt placeholder."""
    if _PLACEHOLDER_VERDICT_RX.search(text) and not _REAL_VERDICT_RX.search(text):
        return True
    # Template body often keeps the angle brackets even when bold labels exist
    if _PLACEHOLDER_VERDICT_RX.search(text):
        # Real verdict may coexist if model answered then chrome kept template
        # — only "template only" when no concrete token outside placeholders.
        without_ph = _PLACEHOLDER_VERDICT_RX.sub("", text)
        if not _REAL_VERDICT_RX.search(without_ph):
            return True
    return False


def _candidate_score(chunk: str) -> int:
    """Higher = more likely the model’s actual review (not the prompt template)."""
    if not chunk or len(chunk) < 40:
        return -100
    score = 0
    if _PLACEHOLDER_VERDICT_RX.search(chunk):
        score -= 50
    if _REAL_VERDICT_RX.search(chunk):
        score += 40
    if "**Verdict:**" in chunk or re.search(r"^Verdict:\s*\w", chunk, re.M):
        score += 5
    for snip in ("### Summary", "### Blocking", "### Security audit", "### Tests & risk"):
        if snip in chunk:
            score += 3
    # Unbolded section labels from chat mode still count
    for label in ("Summary", "Blocking", "Security audit", "Tests & risk"):
        if re.search(rf"^#{{0,3}}\s*{re.escape(label)}\s*$", chunk, re.M | re.I):
            score += 2
    if "Required Markdown template" in chunk or "Trust boundary" in chunk:
        score -= 30
    if chunk.lstrip().startswith("Query:"):
        score -= 40
    # Prefer chunks that look finished (footer or Tests section)
    if "Torii · Hermes Agent" in chunk or "### What I checked" in chunk:
        score += 5
    return score


def extract_agent_review(text: str) -> str:
    """F44: pull the real review out of hermes chat -q / TUI chrome + prompt echo.

    When ``hermes -z`` fails, the chat fallback prints ``Query:`` + the full
    prompt (which embeds the Markdown *template* with every required snippet)
    before the agent answer. Posting that blob is a trust/ops failure.
    """
    t = text.strip()
    if not t:
        return t

    # Fast path: clean one-shot output already looks like a review
    if (
        t.startswith("## ")
        and "Torii Review" in t[:80]
        and not t.startswith("Query:")
        and not _looks_like_template_only(t)
        and _REAL_VERDICT_RX.search(t)
    ):
        return t

    matches = list(_REVIEW_HEADING_RX.finditer(t))
    if not matches:
        # No heading — strip obvious chrome lines and return remainder
        lines = [ln for ln in t.splitlines() if not _HERMES_CHROME_LINE_RX.match(ln)]
        cleaned = "\n".join(lines).strip()
        return cleaned or t

    best: str | None = None
    best_score = -10_000
    for i, m in enumerate(matches):
        start = m.start()
        # If match began at a newline, keep content from the heading line
        if start > 0 and t[start] == "\n":
            start += 1
        end = matches[i + 1].start() if i + 1 < len(matches) else len(t)
        chunk = t[start:end]
        # Drop Hermes session footer if present inside this slice
        foot = _HERMES_FOOTER_RX.search(chunk)
        if foot:
            chunk = chunk[: foot.start()]
        # Drop TUI chrome lines but keep in-body ─── separators between findings
        chunk_lines: list[str] = []
        for ln in chunk.splitlines():
            if _HERMES_CHROME_LINE_RX.match(ln):
                continue
            chunk_lines.append(ln)
        chunk = "\n".join(chunk_lines).strip()
        sc = _candidate_score(chunk)
        # Later candidates win ties (model answer usually last)
        if sc >= best_score:
            best_score = sc
            best = chunk

    if best is None or best_score < 10:
        # Fall back to last heading slice even if weak — ensure_contract may repair
        last = matches[-1]
        start = last.start() + (1 if last.start() > 0 and t[last.start()] == "\n" else 0)
        best = t[start:].strip()
        foot = _HERMES_FOOTER_RX.search(best)
        if foot:
            best = best[: foot.start()].strip()

    # Strip leading fence if model wrapped only the answer
    if best.startswith("```"):
        best = strip_outer_fence(best)
    return best


def normalize_loose_headings(text: str) -> str:
    """Promote chat-mode unbolded labels to the hard contract form."""
    out = text
    for rx, repl in _META_LINE_ALIASES:
        out = rx.sub(repl, out)
    for rx, repl in _SECTION_ALIASES:
        out = rx.sub(repl, out)
    # Ensure title has ##
    out = re.sub(
        r"^(?!#)((?:🏴‍☠️\s*)?Torii Review\s*[—\-–].*)$",
        r"## \1",
        out,
        count=1,
        flags=re.M,
    )
    return out


def ensure_contract(text: str, pr: str) -> str:
    t = text.strip()
    # F44: reject prompt-template echo even if REQUIRED_SNIPPETS are present
    template_only = _looks_like_template_only(t)
    missing = [s for s in REQUIRED_SNIPPETS if s not in t]
    if not missing and not template_only:
        body = t
        # Append missing soft headings only if completely absent (do not invent content)
        for sec in SOFT_SECTIONS:
            if sec not in body:
                # leave as-is; soft sections are guidance for the model, not hard repair
                pass
    else:
        reason = (
            "prompt/template echo or placeholder verdict (F44)"
            if template_only
            else f"missing: {', '.join(missing)}"
        )
        # Keep only a short raw snippet to avoid re-posting the full prompt
        raw_snip = t
        if len(raw_snip) > 4000:
            raw_snip = raw_snip[:4000].rstrip() + "\n…\n_(raw truncated by normalizer)_\n"
        body = f"""## 🏴‍☠️ Torii Review — PR #{pr}

**Verdict:** COMMENT
**Confidence:** low
**Score:** 40/100
**Review effort:** 2/5

### Summary
Agent output did not match the review contract ({reason}). Raw content preserved below.

### Walkthrough
- Contract repair only — re-run for a full structured review

### Blocking
- None (contract repair — re-run if this looks incomplete)

### Key findings
None — normalizer fallback.

### Security audit
No

### Suggestions
- None

### Code suggestions
None

### Nits
- None

### Tests & risk
- Relevant tests added/updated: unknown
- Coverage: unknown
- Risk: unknown
- Rollback: n/a

### What I checked
- Normalizer only

### Raw agent output
{raw_snip}
"""

    marker = f"<!-- torii-review pr={pr}"
    if marker not in body:
        body = f"<!-- torii-review pr={pr} -->\n{body}"

    if "Torii · Hermes Agent" not in body:
        body = body.rstrip() + "\n\n---\n*Torii · Hermes Agent · OpenRouter · memory-backed review*\n"

    if len(body) > MAX_CHARS:
        body = (
            body[: MAX_CHARS - 200].rstrip()
            + "\n\n…\n\n_(truncated to fit GitHub comment size limit)_\n"
        )
    return body.rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", "-i", required=True, type=Path)
    p.add_argument("--output", "-o", required=True, type=Path)
    p.add_argument("--pr", required=True)
    p.add_argument("--run-id", default="local")
    p.add_argument(
        "--head-sha",
        default="",
        help="F59: PR head SHA recorded in HTML marker for incremental reviews",
    )
    p.add_argument(
        "--diff-truncated",
        action="store_true",
        help="F27: inject visible banner that assembled PR diff was size-capped",
    )
    args = p.parse_args(argv)

    raw = args.input.read_text(errors="replace")
    cleaned = strip_outer_fence(raw)
    # F44: drop hermes chat chrome + prompt echo before contract checks
    cleaned = extract_agent_review(cleaned)
    cleaned = normalize_loose_headings(cleaned)
    cleaned = strip_outer_fence(cleaned)
    # Redact before contract repair so fallback "raw agent output" is also scrubbed.
    cleaned = redact_secrets(cleaned)
    final = ensure_contract(cleaned, str(args.pr))
    final = redact_secrets(final)
    # F27 after contract so repair path also gets the banner
    final = inject_diff_truncated_banner(final, args.diff_truncated)
    head = (args.head_sha or "").strip()
    marker_new = f"<!-- torii-review pr={args.pr} run={args.run_id}"
    if head:
        marker_new += f" head={head[:40]}"
    marker_new += " -->"
    final = final.replace(
        f"<!-- torii-review pr={args.pr} -->",
        marker_new,
        1,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(final)
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
