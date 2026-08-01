#!/usr/bin/env python3
"""
Apply a torii-run payload onto memory storage and prepare a commit.

Layouts (TORII_INGEST_LAYOUT):
  hub   (default) — memory/repos/{owner}--{repo}/ under HUB_ROOT
                    F65 multi-tenant: memory/tenants/{tenant}/repos/{slug}/
                    when TORII_MEMORY_TENANT is set
  local           — {TORII_MEMORY_PATH}/ (default .torii/) under TORII_MEMORY_ROOT

Reads CLIENT_PAYLOAD JSON from env (object with key "run" or the run object itself).
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_MEMORY_BYTES = int(os.environ.get("MAX_MEMORY_BYTES", "200000"))


def slugify_repo(source_repo: str) -> str:
    # owner/name -> owner--name
    s = source_repo.strip().replace("\\", "/")
    if "/" not in s:
        s = f"unknown/{s}"
    owner, name = s.split("/", 1)
    owner = re.sub(r"[^A-Za-z0-9._-]+", "-", owner)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
    return f"{owner}--{name}"


def sanitize_tenant(raw: str | None = None) -> str:
    """F65: optional multi-tenant hub namespace (empty = classic shared layout)."""
    t = (raw if raw is not None else os.environ.get("TORII_MEMORY_TENANT") or "").strip()
    if not t:
        return ""
    t = re.sub(r"[^A-Za-z0-9._-]+", "-", t)
    t = t.strip("-.")[:64]
    return t


def hub_repos_relpath(slug: str, tenant: str = "") -> str:
    """Relative hub path for a repo memory root (no trailing slash)."""
    if tenant:
        return f"memory/tenants/{tenant}/repos/{slug}"
    return f"memory/repos/{slug}"


def hub_repo_dir(root: Path, slug: str, tenant: str = "") -> Path:
    if tenant:
        return root / "memory" / "tenants" / tenant / "repos" / slug
    return root / "memory" / "repos" / slug


def rotate_memory(text: str, max_bytes: int) -> str:
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text if text.endswith("\n") else text + "\n"
    text = data[-max_bytes:].decode("utf-8", errors="ignore")
    idx = text.find("\n## ")
    if idx > 0:
        text = (
            "# Torii Gate review memory\n\n_(older entries rotated)_\n" + text[idx:]
        )
    else:
        text = "# Torii Gate review memory\n\n_(rotated)_\n" + text
    return text if text.endswith("\n") else text + "\n"


def _safe_trace_id(trace_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", trace_id)


def write_run_pack(
    repo_dir: Path,
    run: dict,
    source_repo: str,
    slug: str | None,
    *,
    tenant: str = "",
    hub_rel: str | None = None,
) -> tuple[Path, Path, dict]:
    """Write runs/{trace}/meta|review|summary + MEMORY.md under repo_dir. Returns (memory_file, run_dir, meta)."""
    pr = str(run.get("pr_number") or "unknown")
    trace_id = str(run.get("trace_id") or f"pr{pr}-run{run.get('run_id', 'unknown')}")
    safe_trace = _safe_trace_id(trace_id)

    run_dir = repo_dir / "runs" / safe_trace
    run_dir.mkdir(parents=True, exist_ok=True)

    review_md = run.get("review_md") or ""
    memory_block = run.get("memory_block") or ""
    meta = {
        "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_repo": source_repo,
        "slug": slug,
        "tenant": tenant or None,
        "trace_id": trace_id,
        "pr_number": pr,
        "run_id": run.get("run_id"),
        "run_attempt": run.get("run_attempt"),
        "model": run.get("model"),
        "status": run.get("status"),
        "verdict": run.get("verdict"),
        "review_truncated": run.get("review_truncated"),
        "timings": run.get("timings") or {},
        "meta": run.get("meta") or {},
        "schema_version": run.get("schema_version", 1),
        "layout": "local" if slug is None else "hub",
        "feature": "F65" if tenant else None,
    }

    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    if review_md:
        (run_dir / "review.md").write_text(
            review_md if review_md.endswith("\n") else review_md + "\n"
        )
    if memory_block:
        (run_dir / "summary.md").write_text(
            memory_block if memory_block.endswith("\n") else memory_block + "\n"
        )

    if slug is None:
        run_path_rel = f"{repo_dir.name}/runs/{safe_trace}"
    else:
        base = hub_rel or hub_repos_relpath(slug, tenant)
        run_path_rel = f"{base}/runs/{safe_trace}"

    latest_payload = {
        "trace_id": trace_id,
        "pr_number": pr,
        "verdict": run.get("verdict"),
        "status": run.get("status"),
        "ingested_at": meta["ingested_at"],
        "run_path": run_path_rel,
    }
    (repo_dir / "latest.json").write_text(json.dumps(latest_payload, indent=2) + "\n")

    memory_file = repo_dir / "MEMORY.md"
    if memory_file.exists():
        existing = memory_file.read_text(errors="replace")
    else:
        title = source_repo if source_repo else "repo"
        kind = "repo-local" if slug is None else "hub-ingested"
        existing = (
            f"# Torii Gate review memory — `{title}`\n\n"
            f"Cumulative notes from Torii PR reviews ({kind}).\n"
        )

    if memory_block and memory_block.strip() not in existing:
        existing = existing.rstrip() + "\n\n" + memory_block.strip() + "\n"
    existing = rotate_memory(existing, MAX_MEMORY_BYTES)
    memory_file.write_text(existing)

    # F64: merge durable structured FP rules (self-learn store)
    fp_rules = run.get("fp_rules")
    if isinstance(fp_rules, dict) or isinstance(fp_rules, list):
        merge_fp_rules_file(repo_dir / "fp-rules.json", fp_rules)

    return memory_file, run_dir, meta


def merge_fp_rules_file(path: Path, incoming: dict | list) -> None:
    """Upsert F64 fp-rules.json under memory root (local .torii or hub repo dir)."""
    rules_in: list = []
    if isinstance(incoming, dict):
        rules_in = list(incoming.get("rules") or [])
    elif isinstance(incoming, list):
        rules_in = list(incoming)
    if not rules_in:
        return

    existing_rules: list = []
    if path.is_file():
        try:
            prev = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(prev, dict):
                existing_rules = list(prev.get("rules") or [])
            elif isinstance(prev, list):
                existing_rules = list(prev)
        except json.JSONDecodeError:
            existing_rules = []

    def _key(r: dict) -> str:
        path_s = str(r.get("path") or "")
        line = r.get("line")
        kind = str(r.get("kind") or "false_positive")
        return f"{kind}|{path_s}:{line if line is not None else ''}"

    prio = {"thread_reply": 0, "issue_comment": 1, "rules": 2, "memory": 3}
    best: dict[str, dict] = {}
    for r in existing_rules + rules_in:
        if not isinstance(r, dict):
            continue
        k = _key(r)
        if k not in best:
            best[k] = r
            continue
        old = best[k]
        if prio.get(str(r.get("source") or ""), 9) < prio.get(str(old.get("source") or ""), 9):
            best[k] = r
    merged = list(best.values())
    doc = {
        "schema_version": 1,
        "feature": "F64",
        "count": len(merged),
        "rules": merged,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _index_entry(path: Path, rel: str, *, tenant: str | None = None) -> dict:
    latest: dict = {}
    lf = path / "latest.json"
    if lf.exists():
        try:
            latest = json.loads(lf.read_text())
        except json.JSONDecodeError:
            latest = {}
    entry: dict = {
        "slug": path.name,
        "path": rel,
        "latest": latest,
    }
    if tenant:
        entry["tenant"] = tenant
    return entry


def update_hub_index(root: Path, meta: dict) -> None:
    """Index classic memory/repos/* and F65 memory/tenants/*/repos/*."""
    index_path = root / "memory" / "index.json"
    repos: list[dict] = []
    repos_root = root / "memory" / "repos"
    if repos_root.exists():
        for p in sorted(repos_root.iterdir()):
            if p.is_dir() and (p / "MEMORY.md").exists():
                repos.append(_index_entry(p, f"memory/repos/{p.name}"))

    tenants_root = root / "memory" / "tenants"
    if tenants_root.exists():
        for tdir in sorted(tenants_root.iterdir()):
            if not tdir.is_dir():
                continue
            t_repos = tdir / "repos"
            if not t_repos.is_dir():
                continue
            tenant = tdir.name
            for p in sorted(t_repos.iterdir()):
                if p.is_dir() and (p / "MEMORY.md").exists():
                    repos.append(
                        _index_entry(
                            p,
                            f"memory/tenants/{tenant}/repos/{p.name}",
                            tenant=tenant,
                        )
                    )

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "updated_at": meta["ingested_at"],
                "schema_version": 2,
                "feature": "F65",
                "repos": repos,
            },
            indent=2,
        )
        + "\n"
    )


def load_run_payload() -> dict:
    raw = os.environ.get("CLIENT_PAYLOAD") or os.environ.get("TORII_RUN_PAYLOAD")
    if not raw:
        path = os.environ.get("CLIENT_PAYLOAD_FILE")
        if path and Path(path).exists():
            raw = Path(path).read_text()
        else:
            raise SystemExit("CLIENT_PAYLOAD missing")
    data = json.loads(raw)
    run = data.get("run") if isinstance(data, dict) and "run" in data else data
    if not isinstance(run, dict):
        raise SystemExit("invalid payload shape")
    return run


def main() -> int:
    try:
        run = load_run_payload()
    except SystemExit as e:
        print(str(e) or "payload error", file=sys.stderr)
        return 1

    source_repo = run.get("source_repo") or "unknown/unknown"
    layout = (os.environ.get("TORII_INGEST_LAYOUT") or "hub").strip().lower()
    pr = str(run.get("pr_number") or "unknown")
    trace_id = str(run.get("trace_id") or f"pr{pr}-run{run.get('run_id', 'unknown')}")

    if layout == "local":
        root = Path(os.environ.get("TORII_MEMORY_ROOT") or os.environ.get("HUB_ROOT") or ".").resolve()
        mem_rel = os.environ.get("TORII_MEMORY_PATH") or ".torii"
        repo_dir = (root / mem_rel).resolve()
        # Safety: keep under root
        if not str(repo_dir).startswith(str(root)):
            print(f"TORII_MEMORY_PATH escapes root: {repo_dir}", file=sys.stderr)
            return 1
        repo_dir.mkdir(parents=True, exist_ok=True)
        memory_file, run_dir, meta = write_run_pack(repo_dir, run, source_repo, slug=None)
        summary_path = root / ".torii-ingest-summary.txt"
        summary_path.write_text(
            f"local-ingest {source_repo} PR #{pr} trace={trace_id} verdict={run.get('verdict')}\n"
        )
        print(f"Wrote local memory under {repo_dir} trace={_safe_trace_id(trace_id)}")
        print(f"MEMORY={memory_file}")
        print(f"RUN_DIR={run_dir}")
        print("LAYOUT=local")
        # F77: still aggregate federated signals into HUB_ROOT/memory/federation when present
        try:
            import sys as _sys_f77l
            _scripts = Path(__file__).resolve().parent
            if str(_scripts) not in _sys_f77l.path:
                _sys_f77l.path.insert(0, str(_scripts))
            from federated_hub_ingest import ingest_from_run  # type: ignore

            _hub = Path(os.environ.get("HUB_ROOT") or root)
            _fed_res = ingest_from_run(_hub, run)
            if _fed_res:
                print(f"FEDERATED_HUB={_fed_res.get('global_path')}")
        except Exception:
            pass
        return 0

    # hub layout (default); F65 optional tenant namespace
    slug = slugify_repo(source_repo)
    tenant = sanitize_tenant(
        run.get("tenant") if isinstance(run.get("tenant"), str) else None
    )
    root = Path(os.environ.get("HUB_ROOT", ".")).resolve()
    repo_dir = hub_repo_dir(root, slug, tenant)
    hub_rel = hub_repos_relpath(slug, tenant)
    memory_file, run_dir, meta = write_run_pack(
        repo_dir,
        run,
        source_repo,
        slug=slug,
        tenant=tenant,
        hub_rel=hub_rel,
    )
    # F77: cross-tenant privacy-safe federated signal ingest (soft)
    try:
        import sys as _sys_f77
        _scripts = Path(__file__).resolve().parent
        if str(_scripts) not in _sys_f77.path:
            _sys_f77.path.insert(0, str(_scripts))
        from federated_hub_ingest import ingest_from_run  # type: ignore

        _fed_res = ingest_from_run(root, run)
        if _fed_res:
            print(f"FEDERATED_HUB={_fed_res.get('global_path')}")
            print(f"FEDERATED_COUNT={_fed_res.get('global_count')}")
            meta["federated_hub"] = {
                "count": _fed_res.get("global_count"),
                "privacy_ok": _fed_res.get("privacy_ok"),
                "top_themes": _fed_res.get("top_themes"),
            }
    except Exception as _fed_exc:
        print(f"federated_hub_ingest_soft_fail={_fed_exc}", file=sys.stderr)
    update_hub_index(root, meta)

    summary_path = root / ".torii-ingest-summary.txt"
    t_note = f" tenant={tenant}" if tenant else ""
    summary_path.write_text(
        f"ingest {source_repo} PR #{pr} trace={trace_id} verdict={run.get('verdict')}{t_note}\n"
    )
    print(f"Wrote memory for {hub_rel} trace={_safe_trace_id(trace_id)}")
    print(f"MEMORY={memory_file}")
    print(f"RUN_DIR={run_dir}")
    print("LAYOUT=hub")
    if tenant:
        print(f"TENANT={tenant}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
