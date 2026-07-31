#!/usr/bin/env python3
"""Phase 1: Convert a Torii Gate review Markdown (+ optional sidecars) to OpenUI Lang.

Deterministic — no LLM. Output is openui-lang suitable for @openuidev/react-lang Renderer
with the default openuiChatLibrary (Stack, CardHeader, Callout, TextContent, Table, Col, …).

Usage:
  python3 scripts/review-to-openui.py \\
    --review docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/review.md \\
    --usage docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/hermes-usage.json \\
    --timings docs/showcase/e2e-odoo-pr3-opus5-agentic-loop/timings.json \\
    -o docs/showcase/openui-torii/review.openui

See docs/OPENUI-INTEGRATION.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def esc(s: str) -> str:
    """Escape for OpenUI Lang double-quoted strings."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
        .replace("\t", " ")
    )


def field(md: str, name: str) -> str:
    m = re.search(rf"^\*\*{re.escape(name)}:\*\*\s*(.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def section(md: str, heading: str) -> str:
    """Body under ### heading until next ### or end."""
    pat = rf"^### {re.escape(heading)}\s*\n(.*?)(?=^### |\Z)"
    m = re.search(pat, md, re.M | re.S)
    return (m.group(1).strip() if m else "") or ""


def parse_findings_table(md: str) -> list[dict[str, str]]:
    """Parse markdown table under ### Key findings."""
    body = section(md, "Key findings")
    if not body:
        return []
    rows: list[dict[str, str]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|\s*-+", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() in {"severity", "sev"}:
            continue
        rows.append(
            {
                "severity": cells[0],
                "file": cells[1] if len(cells) > 1 else "",
                "issue": cells[2] if len(cells) > 2 else "",
                "trigger": cells[3] if len(cells) > 3 else "",
            }
        )
    return rows


def parse_blocking_bullets(md: str) -> list[str]:
    body = section(md, "Blocking")
    items: list[str] = []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("- ") or s.startswith("* "):
            items.append(re.sub(r"^[-*]\s+", "", s))
        elif s.startswith("**") and items:
            # continuation of multi-line bullet title already captured
            items[-1] = items[-1] + " " + s
        elif s and items and not s.startswith("#"):
            items[-1] = items[-1] + " " + s
    # Keep first sentence / cap length
    out = []
    for it in items:
        it = re.sub(r"\s+", " ", it).strip()
        if len(it) > 280:
            it = it[:277] + "…"
        if it and it.lower() not in {"none", "- none"}:
            out.append(it)
    return out


def verdict_variant(verdict: str) -> str:
    v = verdict.upper()
    if "APPROVE" in v:
        return "success"
    if "REQUEST" in v or "CHANGES" in v:
        return "error"
    if "COMMENT" in v:
        return "info"
    return "warning"


def load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def load_kv_env(path: Path | None) -> dict[str, str]:
    if not path or not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def build_openui(
    review_md: str,
    *,
    usage: dict[str, Any] | None = None,
    timings: dict[str, Any] | None = None,
    memory: dict[str, str] | None = None,
    title: str = "Torii Review",
) -> str:
    usage = usage or {}
    timings = timings or {}
    memory = memory or {}

    verdict = field(review_md, "Verdict") or "UNKNOWN"
    score = field(review_md, "Score") or "n/a"
    effort = field(review_md, "Review effort") or "n/a"
    confidence = field(review_md, "Confidence") or ""
    summary = section(review_md, "Summary") or "(no summary)"
    security = section(review_md, "Security audit") or field(review_md, "Security audit") or "n/a"
    findings = parse_findings_table(review_md)
    blocking = parse_blocking_bullets(review_md)

    # Truncate summary for UI card
    summary_short = re.sub(r"\s+", " ", summary).strip()
    if len(summary_short) > 600:
        summary_short = summary_short[:597] + "…"

    lines: list[str] = []
    # Root first for streaming-friendly shell
    children = ["hdr", "verdictCallout", "metaText", "summaryCard"]
    if blocking:
        children.append("blockingCallout")
    if findings:
        children.append("findingsHeader")
        children.append("findingsTable")
    children.append("securityText")
    if usage:
        children.append("costCard")
    if timings.get("stages"):
        children.append("stagesHeader")
        children.append("stagesTable")
    if memory:
        children.append("memoryCard")
    children.append("footer")

    lines.append(f"root = Stack([{', '.join(children)}])")
    lines.append(f'hdr = CardHeader("{esc(title)}", "Interactive review · OpenUI")')
    lines.append(
        f'verdictCallout = Callout("{verdict_variant(verdict)}", '
        f'"Verdict: {esc(verdict)}", "Score {esc(score)} · Effort {esc(effort)}'
        + (f' · Confidence {esc(confidence)}' if confidence else "")
        + '")'
    )
    lines.append(
        f'metaText = TextContent("Torii structured review rendered via OpenUI Lang '
        f'(deterministic converter — no second LLM).", "small")'
    )
    lines.append(f'summaryCard = TextContent("{esc(summary_short)}", "default")')

    if blocking:
        bl = " | ".join(esc(b[:120]) for b in blocking[:5])
        lines.append(
            f'blockingCallout = Callout("error", "Blocking ({len(blocking)})", "{bl}")'
        )

    if findings:
        lines.append('findingsHeader = CardHeader("Key findings", "")')
        sevs = [esc(f["severity"]) for f in findings]
        files = [esc(f["file"][:80]) for f in findings]
        issues = [esc(f["issue"][:120]) for f in findings]
        lines.append(
            "findingsTable = Table(["
            f'Col("Severity", [{", ".join(chr(34)+s+chr(34) for s in sevs)}], "string"), '
            f'Col("File", [{", ".join(chr(34)+s+chr(34) for s in files)}], "string"), '
            f'Col("Issue", [{", ".join(chr(34)+s+chr(34) for s in issues)}], "string")'
            "])"
        )

    sec_short = re.sub(r"\s+", " ", security).strip()
    if len(sec_short) > 400:
        sec_short = sec_short[:397] + "…"
    lines.append(
        f'securityText = TextContent("**Security audit:** {esc(sec_short)}", "small")'
    )

    if usage:
        model = str(usage.get("model") or "unknown")
        cost = usage.get("estimated_cost_usd")
        try:
            cost_s = f"${float(cost):.2f}" if cost is not None else "n/a"
        except (TypeError, ValueError):
            cost_s = "n/a"
        tokens = usage.get("total_tokens", "n/a")
        calls = usage.get("api_calls", "n/a")
        lines.append(
            f'costCard = Callout("info", "Cost / usage (F21)", '
            f'"model=`{esc(model)}` · ~{esc(cost_s)} · {esc(str(tokens))} tokens · '
            f'{esc(str(calls))} API calls")'
        )

    stages = timings.get("stages") if isinstance(timings.get("stages"), list) else []
    if stages:
        lines.append('stagesHeader = CardHeader("Pipeline stages", "")')
        names = [esc(str(s.get("name", "?"))) for s in stages if isinstance(s, dict)]
        secs = [str(int(s.get("seconds", 0))) for s in stages if isinstance(s, dict)]
        rcs = [str(int(s.get("exit_code", 0))) for s in stages if isinstance(s, dict)]
        lines.append(
            "stagesTable = Table(["
            f'Col("Stage", [{", ".join(chr(34)+n+chr(34) for n in names)}], "string"), '
            f'Col("Seconds", [{", ".join(secs)}], "number"), '
            f'Col("Exit", [{", ".join(rcs)}], "number")'
            "])"
        )

    if memory:
        src = memory.get("MEMORY_SOURCE", "?")
        loc = memory.get("LOCAL_PUBLISH", "?")
        hub = memory.get("HUB_PUBLISH", "?")
        lines.append(
            f'memoryCard = Callout("neutral", "Memory health (F30)", '
            f'"source={esc(src)} · local_publish={esc(loc)} · hub={esc(hub)}")'
        )

    lines.append(
        'footer = TextContent("Generated by scripts/review-to-openui.py · '
        'Torii × OpenUI Phase 1", "small")'
    )
    lines.append("")  # trailing newline
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review", type=Path, required=True, help="Torii Gate review.md path")
    p.add_argument("--usage", type=Path, default=None, help="hermes-usage.json")
    p.add_argument("--timings", type=Path, default=None, help="timings.json")
    p.add_argument("--memory-health", type=Path, default=None, help="memory-health.env")
    p.add_argument("--title", default="Torii Review", help="Card header title")
    p.add_argument("-o", "--out", type=Path, default=None, help="Write .openui file")
    args = p.parse_args(argv)

    if not args.review.is_file():
        print(f"missing review: {args.review}", file=sys.stderr)
        return 1

    md = args.review.read_text(encoding="utf-8", errors="replace")
    openui = build_openui(
        md,
        usage=load_json(args.usage),
        timings=load_json(args.timings),
        memory=load_kv_env(args.memory_health),
        title=args.title,
    )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(openui, encoding="utf-8")
        print(args.out)
    else:
        sys.stdout.write(openui)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
