#!/usr/bin/env python3
"""F56: named review lens recipes / prompt packs.

Deterministic loader + renderer for multi-lens checklists. Judgment stays with
the model; which lenses appear and their focus hints come from pack JSON under
agent/packs/*.json (or TORII_LENS_PACKS_DIR).

Usage:
  python3 scripts/lens_recipes.py list
  python3 scripts/lens_recipes.py get odoo
  python3 scripts/lens_recipes.py render security
  python3 scripts/lens_recipes.py apply --prompt path.md --out path.md
  python3 scripts/lens_recipes.py resolve   # print active pack id

Env:
  TORII_LENS_PACK=default|security|docs|odoo|performance|milvus|go|cpp|auto|...
  TORII_LENS_PACKS=0|off to skip apply (keep template as-is)
  TORII_LENS_PACKS_DIR= override directory of pack JSON files
  TORII_LENS_PACK=auto → pick pack from changed-file path_globs (F63)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


_PASS_RE = re.compile(
    r"(### Multi-lens pass \(H28 / F52\)\n)(.*?)(\n## PR metadata\n)",
    re.DOTALL,
)
_CHECKLIST_RE = re.compile(
    r"(### Multi-lens checklist\n)(.*?)(\n### Suggestions\n)",
    re.DOTALL,
)


def _truthy(val: str | None, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "disabled")


def packs_enabled(raw: str | None = None) -> bool:
    """TORII_LENS_PACKS=1 (default) | 0/off. Prefer F55 registry when present."""
    try:
        from feature_toggles import is_enabled  # type: ignore

        return bool(is_enabled("lens_packs"))
    except Exception:
        v = raw if raw is not None else os.environ.get("TORII_LENS_PACKS")
        return _truthy(v, default=True)


def default_packs_dir() -> Path:
    env = (os.environ.get("TORII_LENS_PACKS_DIR") or "").strip()
    if env:
        return Path(env)
    root = Path(os.environ.get("TORII_ROOT") or Path(__file__).resolve().parents[1])
    return root / "agent" / "packs"


def load_pack_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("id"):
        raise ValueError(f"invalid pack file: {path}")
    lenses = data.get("lenses")
    if not isinstance(lenses, list) or not lenses:
        raise ValueError(f"pack {data.get('id')} missing lenses")
    for i, lens in enumerate(lenses):
        if not isinstance(lens, dict) or not lens.get("id"):
            raise ValueError(f"pack {data.get('id')} lens[{i}] missing id")
    data.setdefault("name", data["id"])
    data.setdefault("description", "")
    data.setdefault("extra_focus", [])
    return data


def list_packs(packs_dir: Path | None = None) -> list[dict[str, Any]]:
    d = packs_dir or default_packs_dir()
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.json")):
        try:
            out.append(load_pack_file(p))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return out


def get_pack(pack_id: str, packs_dir: Path | None = None) -> dict[str, Any]:
    d = packs_dir or default_packs_dir()
    # exact file
    candidate = d / f"{pack_id}.json"
    if candidate.is_file():
        return load_pack_file(candidate)
    # search by id field
    for pack in list_packs(d):
        if pack["id"] == pack_id:
            return pack
    known = ", ".join(p["id"] for p in list_packs(d)) or "(none)"
    raise KeyError(f"unknown lens pack {pack_id!r}; known: {known}")


def active_pack_id(raw: str | None = None) -> str:
    try:
        from feature_toggles import get_value  # type: ignore

        v = get_value("lens_pack")
        if v is not None and str(v).strip():
            return str(v).strip().lower()
    except Exception:
        pass
    v = (raw if raw is not None else os.environ.get("TORII_LENS_PACK") or "security")
    v = str(v).strip().lower() or "security"
    return v


# Path-glob weights for auto pack selection (F63). More specific packs score higher.
_PACK_PRIORITY = {
    "milvus": 100,
    "odoo": 90,
    "security": 40,
    "performance": 40,
    "cpp": 70,
    "go": 60,
    "docs": 50,
    "default": 0,
}


def _glob_match(path: str, pattern: str) -> bool:
    """Minimal glob: ** / * segments; case-sensitive path."""
    import fnmatch

    p = path.replace("\\", "/").lstrip("./")
    pat = pattern.replace("\\", "/")
    if fnmatch.fnmatch(p, pat):
        return True
    if fnmatch.fnmatch(Path(p).name, pat):
        return True
    return False


def score_pack_for_paths(pack: dict[str, Any], paths: list[str]) -> int:
    """Score how well a pack matches changed paths via path_globs."""
    globs = pack.get("path_globs") or []
    if not globs or not paths:
        return 0
    hits = 0
    for path in paths:
        if not path:
            continue
        for g in globs:
            if _glob_match(str(path), str(g)):
                hits += 1
                break
    if hits == 0:
        return 0
    base = int(_PACK_PRIORITY.get(str(pack.get("id") or ""), 10))
    density = hits / max(1, len([p for p in paths if p]))
    return base + hits * 3 + int(density * 20)


def select_pack_for_paths(
    paths: list[str],
    packs_dir: Path | None = None,
    *,
    min_score: int = 15,
) -> dict[str, Any]:
    """Pick the best domain pack for changed paths; fall back to default."""
    packs = list_packs(packs_dir)
    best: dict[str, Any] | None = None
    best_score = -1
    for pack in packs:
        if pack.get("id") == "default":
            continue
        sc = score_pack_for_paths(pack, paths)
        if sc > best_score:
            best_score = sc
            best = pack
    if best is None or best_score < min_score:
        try:
            return get_pack("default", packs_dir)
        except KeyError:
            return _builtin_default()
    return best


def resolve_active(packs_dir: Path | None = None, paths: list[str] | None = None) -> dict[str, Any]:
    pid = active_pack_id()
    if pid in ("auto", "detect", "from_paths"):
        return select_pack_for_paths(list(paths or []), packs_dir)
    try:
        return get_pack(pid, packs_dir)
    except KeyError:
        # soft fallback to default
        try:
            return get_pack("default", packs_dir)
        except KeyError:
            return _builtin_default()


def _builtin_default() -> dict[str, Any]:
    """Fallback if agent/packs missing (install edge cases)."""
    return {
        "id": "default",
        "name": "Default multi-lens",
        "description": "Built-in F52 seven-lens pass.",
        "lenses": [
            {"id": "correctness", "hint": "regressions, edge cases, wrong defaults"},
            {"id": "security", "hint": "injection, authz, secrets, XSS"},
            {"id": "tests", "hint": "risky production paths covered?"},
            {"id": "performance", "hint": "N+1, unbounded loops (only if evidence)"},
            {"id": "api_contracts", "hint": "public API / payload breaks"},
            {"id": "concurrency", "hint": "races (only if concurrent surface)"},
            {"id": "maintainability", "hint": "real future defect risk only"},
        ],
        "extra_focus": [],
    }


def render_pass_section(pack: dict[str, Any]) -> str:
    lines = [
        "### Multi-lens pass (H28 / F52)",
        "",
        f"**Lens pack:** `{pack['id']}` — {pack.get('name') or pack['id']}",
    ]
    desc = (pack.get("description") or "").strip()
    if desc:
        lines.append(f"_{desc}_")
    lines.append("")
    lines.append(
        "Before writing the final verdict, walk these **lenses** on the new code "
        "(one mental pass each; not separate tool loops):"
    )
    lines.append("")
    for i, lens in enumerate(pack["lenses"], 1):
        lid = lens["id"]
        hint = (lens.get("hint") or "").strip()
        if hint:
            lines.append(f"{i}. **{lid}** — {hint}")
        else:
            lines.append(f"{i}. **{lid}**")
    lines.append("")
    lines.append(
        "Fill **### Multi-lens checklist** with `ok` / `concern` / `n/a` + one short note per lens."
    )
    lines.append(
        "Every `concern` must also appear under **Blocking** or **Key findings** with a trigger scenario."
    )
    lines.append(
        "Use `n/a` when the PR has no surface for that lens (e.g. pure docs → most lenses n/a)."
    )
    extra = pack.get("extra_focus") or []
    if extra:
        lines.append("")
        lines.append("**Pack focus:**")
        for item in extra:
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def render_checklist_section(pack: dict[str, Any]) -> str:
    lines = [
        "### Multi-lens checklist",
        f"<!-- torii-lens-pack:{pack['id']} -->",
        "| Lens | Status | Note |",
        "|------|--------|------|",
    ]
    for lens in pack["lenses"]:
        lines.append(f"| {lens['id']} | ok / concern / n/a | one short evidence note |")
    lines.append("")
    lines.append("- Status `concern` ⇒ finding also listed under Blocking or Key findings.")
    lines.append("- Prefer `n/a` over guessing when the PR has no relevant surface.")
    lines.append(f"- Active pack: `{pack['id']}` ({pack.get('name') or pack['id']}).")
    lines.append("")
    return "\n".join(lines)


def render_full(pack: dict[str, Any]) -> str:
    return render_pass_section(pack) + "\n" + render_checklist_section(pack)


def apply_to_prompt(prompt: str, pack: dict[str, Any] | None = None) -> str:
    """Rewrite Multi-lens pass + checklist blocks in an assembled prompt."""
    if pack is None:
        pack = resolve_active()
    text = prompt
    pass_body = render_pass_section(pack)
    # pass_body already ends with blank; avoid double ## header inside
    m = _PASS_RE.search(text)
    if m:
        text = text[: m.start()] + pass_body + m.group(3) + text[m.end() :]
    else:
        # inject after Review focus if section missing
        marker = "## Review focus\n"
        idx = text.find(marker)
        if idx >= 0:
            # after review focus bullets, before ## PR metadata
            pm = text.find("\n## PR metadata\n", idx)
            if pm >= 0:
                # find last ### Multi-lens or end of review focus
                text = text[:pm] + "\n" + pass_body + text[pm + 1 :]

    check_body = render_checklist_section(pack)
    m2 = _CHECKLIST_RE.search(text)
    if m2:
        text = text[: m2.start()] + check_body + m2.group(3) + text[m2.end() :]
    return text


def apply_file(
    prompt_path: Path,
    out_path: Path | None = None,
    pack_id: str | None = None,
    packs_dir: Path | None = None,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    if not packs_enabled():
        return {"enabled": False, "pack": None, "path": str(prompt_path)}
    if pack_id and pack_id not in ("auto", "detect", "from_paths"):
        pack = get_pack(pack_id, packs_dir)
    elif pack_id in ("auto", "detect", "from_paths"):
        pack = select_pack_for_paths(list(paths or []), packs_dir)
    else:
        pack = resolve_active(packs_dir, paths=paths)
    raw = prompt_path.read_text(encoding="utf-8")
    out = apply_to_prompt(raw, pack)
    dest = out_path or prompt_path
    dest.write_text(out, encoding="utf-8")
    return {
        "enabled": True,
        "pack": pack["id"],
        "name": pack.get("name"),
        "lenses": [x["id"] for x in pack["lenses"]],
        "path": str(dest),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="F56 named lens recipe packs")
    p.add_argument(
        "--packs-dir",
        default=None,
        help="directory of pack JSON (default agent/packs)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="list available packs")
    pl.add_argument("--json", action="store_true")

    pg = sub.add_parser("get", help="print one pack JSON")
    pg.add_argument("pack_id")

    pr = sub.add_parser("render", help="render pass+checklist markdown")
    pr.add_argument("pack_id", nargs="?", default=None)

    pa = sub.add_parser("apply", help="rewrite multi-lens sections in a prompt file")
    pa.add_argument("--prompt", required=True, type=Path)
    pa.add_argument("--out", type=Path, default=None)
    pa.add_argument("--pack", dest="pack_id", default=None)

    sub.add_parser("resolve", help="print active pack id")

    ps = sub.add_parser("select", help="auto-select pack from paths (F63)")
    ps.add_argument("--paths", nargs="*", default=[], help="changed file paths")
    ps.add_argument("--files", type=Path, default=None, help="files.txt one path per line")
    ps.add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    packs_dir = Path(args.packs_dir) if args.packs_dir else None

    if args.cmd == "list":
        packs = list_packs(packs_dir)
        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "id": x["id"],
                            "name": x.get("name"),
                            "description": x.get("description"),
                            "lenses": [L["id"] for L in x["lenses"]],
                        }
                        for x in packs
                    ],
                    indent=2,
                )
            )
        else:
            for x in packs:
                lids = ",".join(L["id"] for L in x["lenses"])
                print(f"{x['id']:16} {x.get('name') or '':24} lenses={lids}")
        return 0

    if args.cmd == "get":
        try:
            pack = get_pack(args.pack_id, packs_dir)
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(json.dumps(pack, indent=2))
        return 0

    if args.cmd == "render":
        pid = args.pack_id or active_pack_id()
        try:
            pack = get_pack(pid, packs_dir)
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(render_full(pack), end="")
        return 0

    if args.cmd == "apply":
        try:
            info = apply_file(
                args.prompt,
                out_path=args.out,
                pack_id=args.pack_id,
                packs_dir=packs_dir,
            )
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(json.dumps(info))
        return 0

    if args.cmd == "resolve":
        print(active_pack_id())
        return 0

    if args.cmd == "select":
        paths: list[str] = list(args.paths or [])
        if args.files and Path(args.files).is_file():
            paths.extend(
                ln.strip()
                for ln in Path(args.files).read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            )
        pack = select_pack_for_paths(paths, packs_dir)
        if args.json:
            print(
                json.dumps(
                    {
                        "pack": pack["id"],
                        "name": pack.get("name"),
                        "score": score_pack_for_paths(pack, paths),
                        "paths": paths[:40],
                    },
                    indent=2,
                )
            )
        else:
            print(pack["id"])
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
