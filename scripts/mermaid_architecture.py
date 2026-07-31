#!/usr/bin/env python3
"""F57: deterministic Mermaid architecture diagram from PR changed files.

Pure code — no LLM. Groups paths by top-level package/module and emits a
flowchart the review prompt (and optional review body) can embed.

Usage:
  python3 scripts/mermaid_architecture.py render --files files.txt
  python3 scripts/mermaid_architecture.py render --pr-json pr.json
  python3 scripts/mermaid_architecture.py render --paths a.py b/c.py
  python3 scripts/mermaid_architecture.py section --pr-json pr.json
  python3 scripts/mermaid_architecture.py apply --review review.md --pr-json pr.json

Env:
  TORII_MERMAID=1 (default) | 0/off
  TORII_MERMAID_MAX_NODES=24
  TORII_MERMAID_MAX_FILES_PER_GROUP=6
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


_FILE_LINE_RE = re.compile(r"^-\s+`([^`]+)`")
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_]")


def _truthy(val: str | None, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "disabled")


def enabled(raw: str | None = None) -> bool:
    try:
        from feature_toggles import is_enabled  # type: ignore

        return bool(is_enabled("mermaid"))
    except Exception:
        v = raw if raw is not None else os.environ.get("TORII_MERMAID")
        return _truthy(v, default=True)


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def max_nodes() -> int:
    try:
        from feature_toggles import get_value  # type: ignore

        v = get_value("mermaid_max_nodes")
        if v is not None:
            return max(1, int(v))
    except Exception:
        pass
    return _int_env("TORII_MERMAID_MAX_NODES", 24)


def max_files_per_group() -> int:
    return _int_env("TORII_MERMAID_MAX_FILES_PER_GROUP", 6)


def parse_files_txt(text: str) -> list[str]:
    paths: list[str] = []
    for line in text.splitlines():
        m = _FILE_LINE_RE.match(line.strip())
        if m:
            paths.append(m.group(1).strip())
    return paths


def parse_pr_json(data: dict[str, Any] | list[Any]) -> list[str]:
    files = data.get("files") if isinstance(data, dict) else data
    if not isinstance(files, list):
        return []
    out: list[str] = []
    for f in files:
        if isinstance(f, str):
            out.append(f)
            continue
        if not isinstance(f, dict):
            continue
        path = f.get("path") or f.get("filename") or f.get("name")
        if path:
            out.append(str(path))
    return out


def collect_paths(
    *,
    paths: Iterable[str] | None = None,
    files_txt: str | None = None,
    pr_json: dict[str, Any] | list[Any] | None = None,
) -> list[str]:
    out: list[str] = []
    if paths:
        out.extend(p.strip() for p in paths if p and p.strip())
    if files_txt:
        out.extend(parse_files_txt(files_txt))
    if pr_json is not None:
        out.extend(parse_pr_json(pr_json))
    # unique preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for p in out:
        p = p.replace("\\", "/").lstrip("./")
        if not p or p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


def group_key(path: str) -> str:
    """Top-level package/module bucket for subgraphs."""
    parts = [x for x in path.split("/") if x and x != "."]
    if not parts:
        return "root"
    # common monorepo / odoo shapes
    if parts[0] in ("addons", "odoo") and len(parts) >= 2:
        if parts[0] == "odoo" and parts[1] == "addons" and len(parts) >= 3:
            return f"odoo/addons/{parts[2]}"
        if parts[0] == "addons":
            return f"addons/{parts[1]}"
        if parts[0] == "odoo" and len(parts) >= 2:
            return f"odoo/{parts[1]}"
    if parts[0] in ("src", "lib", "pkg", "packages", "apps", "services") and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    if len(parts) == 1:
        return "root"
    return parts[0]


def file_label(path: str) -> str:
    name = Path(path).name
    if len(name) > 40:
        name = name[:37] + "..."
    return name


def safe_node_id(prefix: str, raw: str) -> str:
    base = _SAFE_ID_RE.sub("_", raw)
    if not base or base[0].isdigit():
        base = f"n_{base}"
    return f"{prefix}_{base}"[:64]


def build_groups(paths: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for p in paths:
        groups[group_key(p)].append(p)
    # stable order: more files first, then name
    ordered = dict(
        sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    )
    return ordered


def render_mermaid(
    paths: list[str],
    *,
    title: str = "PR changed modules",
    max_n: int | None = None,
    max_per_group: int | None = None,
) -> str:
    """Return mermaid flowchart source (no fences)."""
    if not paths:
        return (
            "flowchart LR\n"
            "  empty[\"No changed files detected\"]\n"
        )
    max_n = max_n if max_n is not None else max_nodes()
    max_per_group = (
        max_per_group if max_per_group is not None else max_files_per_group()
    )
    groups = build_groups(paths)
    lines: list[str] = [
        "flowchart LR",
        f"  %% {title} ({len(paths)} files, {len(groups)} groups)",
    ]
    node_count = 0
    truncated = False
    group_ids: list[str] = []

    for gname, files in groups.items():
        if node_count >= max_n:
            truncated = True
            break
        gid = safe_node_id("g", gname)
        group_ids.append(gid)
        # mermaid subgraph title
        gtitle = gname.replace('"', "'")
        lines.append(f'  subgraph {gid}["{gtitle}"]')
        shown = 0
        for fpath in files:
            if node_count >= max_n or shown >= max_per_group:
                truncated = True
                break
            nid = safe_node_id("f", fpath)
            label = file_label(fpath).replace('"', "'")
            # tooltip-ish: full path in comment
            lines.append(f"    {nid}[\"{label}\"]")
            lines.append(f"    %% {fpath}")
            node_count += 1
            shown += 1
        rest = len(files) - shown
        if rest > 0:
            extra_id = safe_node_id("x", gname + "_more")
            lines.append(f'    {extra_id}["+{rest} more"]')
            node_count += 1
        lines.append("  end")

    # link groups in a chain for readability (not true deps)
    if len(group_ids) >= 2:
        lines.append("  %% group adjacency (not runtime deps)")
        for a, b in zip(group_ids, group_ids[1:]):
            lines.append(f"  {a} -.-> {b}")

    if truncated:
        lines.append(f"  note_trunc[\"diagram truncated at {max_n} nodes\"]")
    return "\n".join(lines) + "\n"


def render_section(
    paths: list[str],
    *,
    title: str = "PR changed modules",
    include_marker: bool = True,
) -> str:
    mm = render_mermaid(paths, title=title)
    parts = [
        "### Architecture diagram",
    ]
    if include_marker:
        parts.append("<!-- torii-mermaid -->")
    parts.extend(
        [
            "",
            f"_Auto-generated from {len(paths)} changed file(s) (F57). "
            "Edges between groups are adjacency, not proven runtime dependencies._",
            "",
            "```mermaid",
            mm.rstrip(),
            "```",
            "",
        ]
    )
    if paths:
        parts.append("<details><summary>Files in diagram</summary>")
        parts.append("")
        for p in paths[:80]:
            parts.append(f"- `{p}`")
        if len(paths) > 80:
            parts.append(f"- … +{len(paths) - 80} more")
        parts.append("")
        parts.append("</details>")
        parts.append("")
    return "\n".join(parts)


def apply_to_review(review: str, section: str) -> str:
    """Insert or replace ### Architecture diagram in a review body."""
    if "<!-- torii-mermaid -->" in review or "### Architecture diagram" in review:
        # replace existing architecture section through next ### or EOF
        pat = re.compile(
            r"### Architecture diagram\n.*?(?=\n### |\n## |\Z)",
            re.DOTALL,
        )
        if pat.search(review):
            return pat.sub(section.rstrip() + "\n\n", review, count=1)
    # insert after Walkthrough if present, else after Summary, else append before marker footer
    for anchor in ("### Walkthrough\n", "### Summary\n"):
        idx = review.find(anchor)
        if idx >= 0:
            # find end of this section
            rest = review[idx + len(anchor) :]
            m = re.search(r"\n### ", rest)
            if m:
                insert_at = idx + len(anchor) + m.start()
                return review[:insert_at] + "\n" + section + review[insert_at:]
    # before HTML marker footer / horizontal rule footer
    m = re.search(r"\n---\n\*Torii", review)
    if m:
        return review[: m.start()] + "\n" + section + review[m.start() :]
    return review.rstrip() + "\n\n" + section


def apply_to_prompt(prompt: str, section: str) -> str:
    """Replace {{ARCHITECTURE_DIAGRAM}} or inject before Required Markdown template."""
    if "{{ARCHITECTURE_DIAGRAM}}" in prompt:
        return prompt.replace("{{ARCHITECTURE_DIAGRAM}}", section.rstrip())
    # inject as trusted auto diagram after Changed files summary
    marker = "## Changed files summary\n"
    idx = prompt.find(marker)
    if idx >= 0:
        # after the files summary block (until next ##)
        rest = prompt[idx + len(marker) :]
        m = re.search(r"\n## ", rest)
        if m:
            at = idx + len(marker) + m.start()
            block = (
                "\n## Architecture diagram (auto, F57)\n\n"
                + section
                + "\nUse this diagram in **### Architecture diagram** "
                "(you may add a one-line note; do not invent deps).\n"
            )
            return prompt[:at] + block + prompt[at:]
    return prompt.rstrip() + "\n\n## Architecture diagram (auto, F57)\n\n" + section


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_paths_from_args(args: argparse.Namespace) -> list[str]:
    paths: list[str] = list(args.paths or [])
    files_txt = None
    pr_json = None
    if args.files:
        files_txt = Path(args.files).read_text(encoding="utf-8", errors="replace")
    if args.pr_json:
        pr_json = json.loads(
            Path(args.pr_json).read_text(encoding="utf-8", errors="replace")
        )
    return collect_paths(paths=paths, files_txt=files_txt, pr_json=pr_json)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F57 Mermaid architecture from PR files")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_path_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--files", type=Path, help="files.txt from assemble")
        sp.add_argument("--pr-json", type=Path, help="pr.json from assemble")
        sp.add_argument("--paths", nargs="*", default=[], help="explicit paths")

    pr = sub.add_parser("render", help="print mermaid source only")
    add_path_args(pr)
    pr.add_argument("--title", default="PR changed modules")

    ps = sub.add_parser("section", help="print ### Architecture diagram markdown")
    add_path_args(ps)
    ps.add_argument("--title", default="PR changed modules")

    pa = sub.add_parser("apply", help="insert section into review or prompt file")
    add_path_args(pa)
    pa.add_argument("--review", type=Path, help="review.md to patch")
    pa.add_argument("--prompt", type=Path, help="prompt.md to patch")
    pa.add_argument("--out", type=Path, default=None)
    pa.add_argument("--title", default="PR changed modules")
    pa.add_argument("--force", action="store_true", help="ignore TORII_MERMAID=0")

    args = p.parse_args(argv)
    paths = _load_paths_from_args(args)

    if args.cmd == "render":
        sys.stdout.write(render_mermaid(paths, title=args.title))
        return 0

    if args.cmd == "section":
        sys.stdout.write(render_section(paths, title=args.title))
        return 0

    if args.cmd == "apply":
        if not args.force and not enabled():
            print(json.dumps({"enabled": False, "paths": len(paths)}))
            return 0
        section = render_section(paths, title=args.title)
        if args.review:
            raw = args.review.read_text(encoding="utf-8", errors="replace")
            out = apply_to_review(raw, section)
            dest = args.out or args.review
            dest.write_text(out, encoding="utf-8")
            print(
                json.dumps(
                    {
                        "enabled": True,
                        "target": "review",
                        "paths": len(paths),
                        "path": str(dest),
                    }
                )
            )
            return 0
        if args.prompt:
            raw = args.prompt.read_text(encoding="utf-8", errors="replace")
            out = apply_to_prompt(raw, section)
            dest = args.out or args.prompt
            dest.write_text(out, encoding="utf-8")
            print(
                json.dumps(
                    {
                        "enabled": True,
                        "target": "prompt",
                        "paths": len(paths),
                        "path": str(dest),
                    }
                )
            )
            return 0
        print("error: --review or --prompt required", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
