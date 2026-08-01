#!/usr/bin/env python3
"""F84: Progressive skill router + post-run skill hit scoring.

Research drivers (2026):
  - Progressive disclosure (Claude Skills / Simon Willison / HN): inject a compact
    index of all skills; load full bodies only for relevant verticals.
  - Vercel agent evals: in 56% of cases skills were never invoked when dumped
    wholesale — routing + measurement closes the loop.
  - FederatedSkill (arXiv 2606.03143): share skill *usage themes*, not full
    trajectory text, for privacy-safe collaborative evolution signals.
  - Loop Engineering: measure what you ship (skill hit rate → evolve/drop).

Product thesis:
  F69/F82 dump up to 8 full active skills into every prompt. As the skill vault
  grows, context bloats and relevance drops. Highest ROI: **route skills by
  changed-path extensions + theme keywords**, inject index + selected bodies,
  then **score keyword hits in the review** so self-evolution knows which
  skills actually fire.

Commands:
  index   — catalog active skills (id, title, triggers, always)
  select  — rank/select top-K for given paths
  inject  — progressive inject into prompt.md (replaces F69 bulk when on)
  score   — post-run skill hit rate vs review body
  fixture — hermetic offline good/weak path routing + hit score
  status  — active catalog summary

Env:
  TORII_ROOT
  TORII_SKILL_ROUTER          1 (default) | 0/off
  TORII_SKILL_ROUTER_MAX      default 4 full skills (plus always-on core)
  TORII_SKILL_ROUTER_ALWAYS   comma ids always included (optional)
  TORII_SKILL_ROUTER_REPLACE  1 (default) | 0 — replace F69 skills block
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEATURE = "F84"
SCHEMA = 1
MARKER_OPEN = "<!-- torii-f84-skill-router -->"
MARKER_CLOSE = "<!-- /torii-f84-skill-router -->"
F69_OPEN = "<!-- torii-f69-skills -->"
F69_CLOSE = "<!-- /torii-f69-skills -->"

_FALSEY = frozenset({"0", "false", "no", "off", "disabled", "n", "none", ""})

# Extension → theme tags for routing
EXT_THEMES: dict[str, list[str]] = {
    ".py": ["python", "pickle", "sqli", "cmdi", "secrets", "taint", "chain"],
    ".js": ["javascript", "node", "xss", "sqli", "secrets", "taint"],
    ".ts": ["typescript", "javascript", "node", "xss", "taint"],
    ".tsx": ["typescript", "javascript", "react", "xss"],
    ".jsx": ["javascript", "react", "xss"],
    ".go": ["go", "cmdi", "secrets", "taint"],
    ".rs": ["rust", "memory", "taint"],
    ".java": ["java", "sqli", "secrets", "taint"],
    ".rb": ["ruby", "sqli", "secrets"],
    ".php": ["php", "sqli", "xss", "secrets"],
    ".sh": ["shell", "cmdi", "secrets"],
    ".yaml": ["config", "secrets", "ci"],
    ".yml": ["config", "secrets", "ci"],
    ".json": ["config", "secrets"],
    ".env": ["secrets", "config"],
    ".sql": ["sqli", "database"],
    ".md": ["docs"],
    ".toml": ["config"],
    ".c": ["c", "memory", "taint"],
    ".cpp": ["cpp", "memory", "taint"],
    ".h": ["c", "memory"],
}

# Skill-id / keyword heuristics when frontmatter lacks triggers
DEFAULT_TRIGGERS: dict[str, dict[str, Any]] = {
    "skill-f74-prefer-chain-json": {
        "themes": ["taint", "chain", "python", "javascript"],
        "keywords": ["chain", "taint", "source", "sink", "candidate", "unvalidated"],
        "exts": [".py", ".js", ".ts"],
        "always": False,
    },
    "skill-f74-exploit-scenario": {
        "themes": ["exploit", "attacker", "sqli", "cmdi", "pickle", "xss"],
        "keywords": ["attacker", "trigger", "exploit", "severity", "request changes"],
        "exts": [".py", ".js", ".ts", ".go", ".java"],
        "always": False,
    },
    "skill-tool-depth-hunks": {
        "themes": ["review", "diff", "tools"],
        "keywords": ["diff", "hunk", "rg -n", "sed -n", "changed region"],
        "exts": [],
        "always": True,
    },
    "skill-preserve-deep-tools": {
        "themes": ["review", "tools", "depth"],
        "keywords": ["tool turns", "package path", "symbol", "deep"],
        "exts": [],
        "always": True,
    },
    "skill-soft-tool-nudge": {
        "themes": ["review", "tools"],
        "keywords": ["fewer, deeper", "tool turns", "blocking"],
        "exts": [],
        "always": False,
    },
    "skill-f74-path-evidence": {
        "themes": ["path", "evidence", "review"],
        "keywords": ["path:line", "deep path", "basename", "unvalidated"],
        "exts": [],
        "always": True,
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
    raw = (os.environ.get("TORII_SKILL_ROUTER") or "1").strip().lower()
    return raw not in _FALSEY


def _int_env(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def replace_f69() -> bool:
    raw = (os.environ.get("TORII_SKILL_ROUTER_REPLACE") or "1").strip().lower()
    return raw not in _FALSEY


def always_ids_env() -> set[str]:
    raw = (os.environ.get("TORII_SKILL_ROUTER_ALWAYS") or "").strip()
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def active_skills_dir(root: Path | None = None) -> Path:
    return (root or _root()) / "agent" / "skills" / "active"


def list_active_skills(root: Path | None = None) -> list[Path]:
    d = active_skills_dir(root)
    if not d.is_dir():
        return []
    return sorted(
        p for p in d.glob("*.md") if p.is_file() and p.name != "README.md"
    )


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"(?s)^---\n(.*?)\n---\n(.*)$", text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta, m.group(2)


def _skill_id_from_path(p: Path, meta: dict[str, str]) -> str:
    return (meta.get("id") or p.stem).strip()


def _extract_keywords(body: str, limit: int = 12) -> list[str]:
    # Prefer bold/code tokens and multi-word security terms
    kws: list[str] = []
    for m in re.finditer(r"\*\*([^*]{3,40})\*\*", body):
        kws.append(m.group(1).strip().lower())
    for m in re.finditer(r"`([^`]{3,40})`", body):
        kws.append(m.group(1).strip().lower())
    # common security tokens present in body
    for tok in (
        "path:line",
        "taint",
        "chain",
        "source",
        "sink",
        "attacker",
        "exploit",
        "diff",
        "hunk",
        "unvalidated",
        "severity",
        "cwe",
        "pickle",
        "sqli",
        "cmdi",
        "secrets",
    ):
        if tok in body.lower() and tok not in kws:
            kws.append(tok)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for k in kws:
        k2 = k.strip().lower()
        if k2 and k2 not in seen:
            seen.add(k2)
            out.append(k2)
        if len(out) >= limit:
            break
    return out


@dataclass
class SkillCard:
    id: str
    path: str
    title: str
    themes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    exts: list[str] = field(default_factory=list)
    always: bool = False
    body: str = ""
    chars: int = 0


def build_card(path: Path) -> SkillCard:
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(raw)
    sid = _skill_id_from_path(path, meta)
    title = meta.get("title") or sid
    defaults = DEFAULT_TRIGGERS.get(sid, {})
    themes = [t.strip().lower() for t in (meta.get("themes") or "").split(",") if t.strip()]
    if not themes:
        themes = list(defaults.get("themes") or [])
    # free-form triggers: "python,taint"
    for key in ("triggers", "tags", "signal"):
        if meta.get(key):
            for part in re.split(r"[|,\s]+", meta[key]):
                p = part.strip().lower()
                if p and p not in themes:
                    themes.append(p)
    kws = _extract_keywords(body)
    for extra in defaults.get("keywords") or []:
        if extra.lower() not in kws:
            kws.append(extra.lower())
    exts = list(defaults.get("exts") or [])
    if meta.get("exts"):
        for e in meta["exts"].split(","):
            e = e.strip()
            if e and not e.startswith("."):
                e = "." + e
            if e and e not in exts:
                exts.append(e)
    always = bool(defaults.get("always"))
    if meta.get("always", "").lower() in ("1", "true", "yes"):
        always = True
    if sid in always_ids_env():
        always = True
    body_clean = body.strip()
    return SkillCard(
        id=sid,
        path=str(path),
        title=title,
        themes=themes,
        keywords=kws[:16],
        exts=exts,
        always=always,
        body=body_clean,
        chars=len(body_clean),
    )


def catalog(root: Path | None = None) -> list[SkillCard]:
    return [build_card(p) for p in list_active_skills(root)]


def paths_from_args(
    paths: list[str] | None = None,
    paths_file: str | None = None,
    pr_json: str | None = None,
) -> list[str]:
    out: list[str] = []
    if paths:
        out.extend(paths)
    if paths_file:
        pf = Path(paths_file)
        if pf.is_file():
            for line in pf.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    out.append(line)
    if pr_json:
        pj = Path(pr_json)
        if pj.is_file():
            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
                files = data.get("files") or []
                for f in files:
                    if isinstance(f, dict):
                        p = f.get("path") or f.get("filename") or ""
                        if p:
                            out.append(str(p))
                    elif isinstance(f, str):
                        out.append(f)
            except (json.JSONDecodeError, OSError):
                pass
    # env fallbacks used by assemble-context
    for envk in ("FILES_PATH", "OUT_DIR"):
        if envk == "FILES_PATH":
            fp = (os.environ.get("FILES_PATH") or "").strip()
            if fp and Path(fp).is_file():
                for line in Path(fp).read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if line:
                        out.append(line)
        elif envk == "OUT_DIR":
            od = (os.environ.get("OUT_DIR") or "").strip()
            if od:
                for name in ("files.txt", "pr.json"):
                    cand = Path(od) / name
                    if cand.name == "files.txt" and cand.is_file():
                        for line in cand.read_text(encoding="utf-8", errors="replace").splitlines():
                            line = line.strip()
                            if line:
                                out.append(line)
                    elif cand.name == "pr.json" and cand.is_file() and not out:
                        out.extend(paths_from_args(pr_json=str(cand)))
    # de-dupe
    seen: set[str] = set()
    uniq: list[str] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def themes_from_paths(paths: list[str]) -> set[str]:
    themes: set[str] = set()
    exts_seen: set[str] = set()
    for p in paths:
        ext = Path(p).suffix.lower()
        if ext:
            exts_seen.add(ext)
            for t in EXT_THEMES.get(ext, []):
                themes.add(t)
        low = p.lower()
        for tok in (
            "test",
            "secret",
            "auth",
            "sql",
            "pickle",
            "cmd",
            "shell",
            "xss",
            "taint",
            "workflow",
            "ci",
        ):
            if tok in low:
                themes.add(tok if tok != "cmd" else "cmdi")
                if tok == "secret":
                    themes.add("secrets")
                if tok == "sql":
                    themes.add("sqli")
                if tok == "pickle":
                    themes.add("python")
    if not themes:
        themes.add("review")
    themes.add("review")
    themes.add("tools")
    return themes


def score_skill(card: SkillCard, path_themes: set[str], paths: list[str]) -> float:
    if card.always:
        return 1000.0
    score = 0.0
    for t in card.themes:
        if t in path_themes:
            score += 3.0
    path_exts = {Path(p).suffix.lower() for p in paths if Path(p).suffix}
    for e in card.exts:
        if e in path_exts:
            score += 2.0
    # basename keyword soft match
    blob = " ".join(paths).lower()
    for kw in card.keywords[:8]:
        if len(kw) >= 4 and kw in blob:
            score += 0.5
    # slight preference for f74 security skills when any code ext present
    code_exts = path_exts - {".md", ".txt", ".rst"}
    if code_exts and card.id.startswith("skill-f74"):
        score += 1.0
    return score


def select_skills(
    cards: list[SkillCard],
    paths: list[str],
    max_full: int | None = None,
) -> dict[str, Any]:
    max_full = max_full if max_full is not None else _int_env("TORII_SKILL_ROUTER_MAX", 4)
    path_themes = themes_from_paths(paths)
    ranked: list[tuple[float, SkillCard]] = []
    for c in cards:
        s = score_skill(c, path_themes, paths)
        ranked.append((s, c))
    ranked.sort(key=lambda x: (-x[0], x[1].id))

    selected: list[SkillCard] = []
    # always first
    for s, c in ranked:
        if c.always and c not in selected:
            selected.append(c)
    # then top by score until max_full (always count toward max)
    for s, c in ranked:
        if c in selected:
            continue
        if s <= 0 and len(selected) >= 1:
            continue
        if len(selected) >= max_full:
            break
        selected.append(c)

    # if nothing selected, take top 2 by score or first always
    if not selected and ranked:
        selected = [c for _, c in ranked[: min(2, len(ranked))]]

    return {
        "feature": FEATURE,
        "schema": SCHEMA,
        "path_themes": sorted(path_themes),
        "paths_n": len(paths),
        "max_full": max_full,
        "catalog_n": len(cards),
        "selected": [c.id for c in selected],
        "selected_cards": selected,
        "ranking": [
            {"id": c.id, "score": round(s, 2), "always": c.always} for s, c in ranked
        ],
    }


def render_injection(cards_all: list[SkillCard], selection: dict[str, Any]) -> str:
    selected_ids = set(selection.get("selected") or [])
    selected_cards: list[SkillCard] = selection.get("selected_cards") or [
        c for c in cards_all if c.id in selected_ids
    ]
    lines: list[str] = [
        "## Skill router (F84 — progressive disclosure)",
        "",
        "Use the **index** for awareness; follow **selected full skills** as reviewer discipline.",
        f"Routed themes: {', '.join(selection.get('path_themes') or []) or 'review'}.",
        "",
        "### Skill index (all active)",
        "",
    ]
    for c in cards_all:
        flag = " ★" if c.id in selected_ids else ""
        one = c.title
        themes = ",".join(c.themes[:4]) if c.themes else "general"
        lines.append(f"- `{c.id}`{flag} — {one} [{themes}]")
    lines.append("")
    lines.append("### Selected full skills")
    lines.append("")
    if not selected_cards:
        lines.append("_No skills selected._")
    for c in selected_cards:
        lines.append(f"#### {c.id}")
        lines.append("")
        lines.append(c.body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def inject_into_prompt(
    prompt: Path,
    root: Path | None = None,
    paths: list[str] | None = None,
    out: Path | None = None,
) -> dict[str, Any]:
    root = root or _root()
    cards = catalog(root)
    paths = paths if paths is not None else paths_from_args()
    selection = select_skills(cards, paths)
    body = render_injection(cards, selection)
    chunk = f"{MARKER_OPEN}\n{body}{MARKER_CLOSE}\n"
    original = prompt.read_text(encoding="utf-8", errors="replace")

    # optionally strip F69 bulk skills block to avoid double injection
    stripped_f69 = False
    if replace_f69() and F69_OPEN in original:
        original = re.sub(
            rf"{re.escape(F69_OPEN)}.*?{re.escape(F69_CLOSE)}\n?",
            "",
            original,
            count=1,
            flags=re.DOTALL,
        )
        stripped_f69 = True

    if MARKER_OPEN in original:
        new = re.sub(
            rf"{re.escape(MARKER_OPEN)}.*?{re.escape(MARKER_CLOSE)}\n?",
            chunk,
            original,
            count=1,
            flags=re.DOTALL,
        )
    else:
        marker = "## PR metadata"
        if marker in original:
            new = original.replace(marker, chunk + "\n" + marker, 1)
        else:
            new = original.rstrip() + "\n\n" + chunk

    dest = out or prompt
    dest.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")

    result = {
        "feature": FEATURE,
        "injected": 1,
        "selected": selection["selected"],
        "catalog_n": len(cards),
        "paths_n": selection["paths_n"],
        "path_themes": selection["path_themes"],
        "stripped_f69": stripped_f69,
        "prompt": str(dest),
        "chars": len(body),
    }
    # write selection artifact next to prompt if OUT_DIR
    od = (os.environ.get("OUT_DIR") or "").strip()
    if od:
        art = Path(od) / "skill-router.json"
        try:
            art.write_text(
                json.dumps(
                    {
                        **{k: v for k, v in selection.items() if k != "selected_cards"},
                        "injected_at": _now(),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            result["artifact"] = str(art)
        except OSError:
            pass
    return result


def score_hits(
    review: Path,
    root: Path | None = None,
    selected: list[str] | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    root = root or _root()
    cards = catalog(root)
    text = review.read_text(encoding="utf-8", errors="replace").lower() if review.is_file() else ""
    by_id = {c.id: c for c in cards}
    if selected is None:
        # try skill-router.json
        od = out_dir or Path(os.environ.get("OUT_DIR") or ".")
        art = Path(od) / "skill-router.json"
        if art.is_file():
            try:
                selected = json.loads(art.read_text(encoding="utf-8")).get("selected") or []
            except (json.JSONDecodeError, OSError):
                selected = [c.id for c in cards]
        else:
            selected = [c.id for c in cards]

    hits: list[dict[str, Any]] = []
    hit_n = 0
    for sid in selected:
        c = by_id.get(sid)
        if not c:
            hits.append({"id": sid, "hit": False, "matched": [], "missing": True})
            continue
        matched: list[str] = []
        # title tokens + keywords
        probes = list(c.keywords[:10])
        for part in re.split(r"[\s\-_/]+", c.title.lower()):
            if len(part) >= 4 and part not in probes:
                probes.append(part)
        # id tail
        tail = sid.replace("skill-", "").replace("f74-", "").replace("-", " ")
        for part in tail.split():
            if len(part) >= 4 and part not in probes:
                probes.append(part)
        for kw in probes:
            if len(kw) < 3:
                continue
            if kw.lower() in text:
                matched.append(kw.lower())
        is_hit = len(matched) >= 1
        if is_hit:
            hit_n += 1
        hits.append(
            {
                "id": sid,
                "hit": is_hit,
                "matched": matched[:8],
                "n_matched": len(matched),
            }
        )

    rate = (hit_n / len(selected)) if selected else 0.0
    result = {
        "feature": FEATURE,
        "schema": SCHEMA,
        "scored_at": _now(),
        "selected_n": len(selected),
        "hit_n": hit_n,
        "hit_rate": round(rate, 4),
        "hits": hits,
        "review": str(review),
        # privacy-safe federated theme: skill ids only
        "federated_skill_themes": [
            h["id"] for h in hits if h.get("hit") and not str(h["id"]).startswith("/")
        ],
    }
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "skill-hits.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        result["artifact"] = str(out_dir / "skill-hits.json")
    return result


# --- CLI ---


def cmd_index(args: argparse.Namespace) -> int:
    cards = catalog(_root())
    payload = {
        "feature": FEATURE,
        "n": len(cards),
        "skills": [
            {
                "id": c.id,
                "title": c.title,
                "themes": c.themes,
                "keywords": c.keywords[:8],
                "exts": c.exts,
                "always": c.always,
                "chars": c.chars,
            }
            for c in cards
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_select(args: argparse.Namespace) -> int:
    paths = paths_from_args(
        paths=args.paths,
        paths_file=args.paths_file,
        pr_json=args.pr_json,
    )
    cards = catalog(_root())
    sel = select_skills(cards, paths, max_full=args.max)
    out = {k: v for k, v in sel.items() if k != "selected_cards"}
    print(json.dumps(out, indent=2))
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    if not enabled() and not args.force:
        print(json.dumps({"feature": FEATURE, "injected": 0, "reason": "disabled"}))
        return 0
    prompt = Path(args.prompt)
    if not prompt.is_file():
        print(f"error: prompt not found: {prompt}", file=sys.stderr)
        return 1
    paths = paths_from_args(
        paths=args.paths,
        paths_file=args.paths_file,
        pr_json=args.pr_json,
    )
    result = inject_into_prompt(
        prompt,
        paths=paths,
        out=Path(args.out) if args.out else None,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    review = Path(args.review)
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is None and (os.environ.get("OUT_DIR") or "").strip():
        out_dir = Path(os.environ["OUT_DIR"])
    selected = None
    if args.selected:
        selected = [x.strip() for x in args.selected.split(",") if x.strip()]
    result = score_hits(review, selected=selected, out_dir=out_dir)
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cards = catalog(_root())
    always = [c.id for c in cards if c.always]
    print(
        json.dumps(
            {
                "feature": FEATURE,
                "schema": SCHEMA,
                "enabled": enabled(),
                "active_n": len(cards),
                "always": always,
                "max_full": _int_env("TORII_SKILL_ROUTER_MAX", 4),
                "replace_f69": replace_f69(),
                "ids": [c.id for c in cards],
            },
            indent=2,
        )
    )
    return 0


def cmd_fixture(args: argparse.Namespace) -> int:
    """Hermetic: py paths prefer chain/exploit skills; md-only prefers always; hits score."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        active = root / "agent" / "skills" / "active"
        active.mkdir(parents=True)
        # minimal skills
        (active / "skill-f74-prefer-chain-json.md").write_text(
            """---
id: skill-f74-prefer-chain-json
title: Prefer chain JSON over inference
themes: taint,chain,python
---

## Skill: prefer-chain-json

Align findings with **candidate source/sink pairs** and taint chain JSON.
Label **unvalidated** when no candidate matches.
""",
            encoding="utf-8",
        )
        (active / "skill-f74-exploit-scenario.md").write_text(
            """---
id: skill-f74-exploit-scenario
title: Exploit scenario language
themes: exploit,attacker,python
---

## Skill: exploit-scenario

Add one **attacker trigger** sentence for REQUEST CHANGES on a confirmed sink.
""",
            encoding="utf-8",
        )
        (active / "skill-tool-depth-hunks.md").write_text(
            """---
id: skill-tool-depth-hunks
title: Tool depth prefer diff hunks
always: true
---

## Skill: tool-depth-hunks

Open the unified **diff** file first for exact hunks. Use `rg -n` then `sed -n`.
""",
            encoding="utf-8",
        )
        (active / "skill-docs-only.md").write_text(
            """---
id: skill-docs-only
title: Docs prose style
themes: docs,markdown
---

## Skill: docs-only

Only relevant for markdown documentation tone.
""",
            encoding="utf-8",
        )

        os.environ["TORII_ROOT"] = str(root)
        os.environ["TORII_SKILL_ROUTER"] = "1"
        os.environ["TORII_SKILL_ROUTER_MAX"] = "3"
        os.environ["TORII_SKILL_ROUTER_REPLACE"] = "1"

        cards = catalog(root)
        assert len(cards) == 4

        py_paths = ["src/app/auth.py", "lib/db.py", "tests/test_auth.py"]
        sel_py = select_skills(cards, py_paths, max_full=3)
        sel_ids = set(sel_py["selected"])
        # always skill present
        always_ok = "skill-tool-depth-hunks" in sel_ids
        # security skills preferred for py
        sec_ok = bool(sel_ids & {"skill-f74-prefer-chain-json", "skill-f74-exploit-scenario"})
        # docs-only should rank low vs py code
        docs_not_first = sel_py["selected"][0] != "skill-docs-only" if sel_py["selected"] else True

        md_paths = ["README.md", "docs/guide.md"]
        sel_md = select_skills(cards, md_paths, max_full=3)
        md_ids = set(sel_md["selected"])
        always_in_md = "skill-tool-depth-hunks" in md_ids

        # inject
        prompt = root / "prompt.md"
        prompt.write_text(
            f"{F69_OPEN}\n## Evolved skills (bulk dump)\nfull dump of everything\n{F69_CLOSE}\n\n## PR metadata\nrepo: x\n",
            encoding="utf-8",
        )
        inj = inject_into_prompt(prompt, root=root, paths=py_paths)
        text = prompt.read_text(encoding="utf-8")
        inject_ok = MARKER_OPEN in text and "Skill router (F84" in text
        stripped_ok = inj.get("stripped_f69") is True and F69_OPEN not in text
        selected_body_ok = any(s in text for s in inj["selected"])

        # score hits: good review mentions chain/attacker/diff
        good_review = root / "good.md"
        good_review.write_text(
            """# Review
Found SQLi via source/sink taint chain. Attacker trigger: POST /login.
Opened unified diff hunks with rg -n.
Verdict: REQUEST_CHANGES
""",
            encoding="utf-8",
        )
        out_dir = root / "out"
        out_dir.mkdir()
        (out_dir / "skill-router.json").write_text(
            json.dumps({"selected": inj["selected"]}), encoding="utf-8"
        )
        good_hits = score_hits(
            good_review, root=root, selected=inj["selected"], out_dir=out_dir
        )

        weak_review = root / "weak.md"
        weak_review.write_text("# LGTM looks fine\nAPPROVE\n", encoding="utf-8")
        weak_hits = score_hits(
            weak_review, root=root, selected=inj["selected"], out_dir=None
        )

        good_rate = float(good_hits["hit_rate"])
        weak_rate = float(weak_hits["hit_rate"])
        rate_ok = good_rate > weak_rate and good_rate >= 0.3
        privacy_ok = not any(
            "/Users/" in str(x) for x in good_hits.get("federated_skill_themes") or []
        )

        fixture_pass = all(
            [
                always_ok,
                sec_ok,
                docs_not_first,
                always_in_md,
                inject_ok,
                stripped_ok,
                selected_body_ok,
                rate_ok,
                privacy_ok,
                good_hits.get("hit_n", 0) >= 1,
            ]
        )
        payload = {
            "feature": FEATURE,
            "fixture_pass": fixture_pass,
            "always_ok": always_ok,
            "sec_ok": sec_ok,
            "docs_not_first": docs_not_first,
            "always_in_md": always_in_md,
            "inject_ok": inject_ok,
            "stripped_ok": stripped_ok,
            "selected_py": inj["selected"],
            "selected_md": sel_md["selected"],
            "good_hit_rate": good_rate,
            "weak_hit_rate": weak_rate,
            "rate_ok": rate_ok,
            "privacy_ok": privacy_ok,
            "good_hit_n": good_hits.get("hit_n"),
        }
        print(json.dumps(payload, indent=2))
        return 0 if fixture_pass else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="F84 progressive skill router + hit scoring"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("index", help="Catalog active skills").set_defaults(func=cmd_index)
    sub.add_parser("status", help="Router status").set_defaults(func=cmd_status)
    sub.add_parser("fixture", help="Hermetic offline fixture").set_defaults(
        func=cmd_fixture
    )

    ps = sub.add_parser("select", help="Select skills for paths")
    ps.add_argument("--paths", nargs="*", default=None)
    ps.add_argument("--paths-file", default=None)
    ps.add_argument("--pr-json", default=None)
    ps.add_argument("--max", type=int, default=None)
    ps.set_defaults(func=cmd_select)

    pi = sub.add_parser("inject", help="Progressive inject into prompt")
    pi.add_argument("--prompt", required=True)
    pi.add_argument("--out", default="")
    pi.add_argument("--paths", nargs="*", default=None)
    pi.add_argument("--paths-file", default=None)
    pi.add_argument("--pr-json", default=None)
    pi.add_argument("--force", action="store_true")
    pi.set_defaults(func=cmd_inject)

    pc = sub.add_parser("score", help="Score skill hits in review")
    pc.add_argument("--review", required=True)
    pc.add_argument("--out-dir", default="")
    pc.add_argument("--selected", default="")
    pc.set_defaults(func=cmd_score)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
