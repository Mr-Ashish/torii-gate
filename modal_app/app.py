"""Torii Modal app — cheapest viable CPU profile.

Cost rules (Modal bills max(request, usage)):
  - Do NOT reserve high cpu/memory (defaults = 0.125 core, ~128MiB soft)
  - No GPU
  - Sparse shallow PR checkout (avoid monorepo full clone wall-time)
  - Cheap OpenRouter model default (gpt-4.1-mini)
  - Hermes baked in image once (amortized; not per-run cold install)

Run:
  modal run modal_app/app.py --bit 1
  modal run modal_app/app.py --bit 2
  modal run modal_app/app.py --bit 3 --repo Mr-Ashish/odoo --pr 3
  modal run modal_app/app.py --bit 4 --repo Mr-Ashish/odoo --pr 3   # dry enqueue plan
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, IO

import modal

APP_NAME = "torii-pr-review"
# F67: live log streaming to Modal UI (Hermes agent activity + stages)
# F66: Modal is the default prod live e2e host (lens auto + F65 tenant pass-through)
TORII_MODAL_VERSION = "0.8.0-f67"
HERMES_PIN = "53559aaf86b84dadae83cd9bb605ca476f9a0606"
# OpenRouter — keep Modal compute cheap AND LLM spend low
DEFAULT_MODEL = "openai/gpt-4.1-mini"
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Slim image: no build-essential/python3-dev (not needed if hermes install works without)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "curl", "ca-certificates", "jq", "bash")
    .run_commands(
        "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg "
        "| dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
        "chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg",
        'echo "deb [arch=$(dpkg --print-architecture) '
        "signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] "
        'https://cli.github.com/packages stable main" '
        "> /etc/apt/sources.list.d/github-cli.list",
        "apt-get update && apt-get install -y gh",
        # Hermes pin once per image (saves per-run install time = billable seconds)
        f"curl -fsSL https://hermes-agent.nousresearch.com/install.sh "
        f"| bash -s -- --skip-setup --commit {HERMES_PIN} --force-commit",
        "export PATH=\"$HOME/.local/bin:$HOME/.hermes/bin:$PATH\" && hermes --version",
        f"echo {HERMES_PIN} > /root/.hermes-pin",
    )
    .env(
        {
            "PATH": "/root/.local/bin:/root/.hermes/bin:/usr/local/bin:/usr/bin:/bin",
            "TORII_HERMES_PREBAKED": "1",
            "TORII_HERMES_COMMIT": HERMES_PIN,
        }
    )
    .pip_install("fastapi[standard]>=0.115.0")
    .add_local_dir(str(_REPO_ROOT / "scripts"), remote_path="/opt/torii/scripts")
    .add_local_dir(str(_REPO_ROOT / "agent"), remote_path="/opt/torii/agent")
)

app = modal.App(APP_NAME, image=image)

openrouter_secret = modal.Secret.from_name("torii-openrouter")
github_secret = modal.Secret.from_name("torii-github")
# Optional F33: put TORII_WEBHOOK_SECRET / TORII_WEBHOOK_TOKEN on this secret
# (create empty-safe: operators may fold keys into torii-github instead).
trace_vol = modal.Volume.from_name("torii-traces", create_if_missing=True)

# Import pure helpers (local tree or Modal image /opt/torii/scripts)
for _p in (str(_REPO_ROOT / "scripts"), "/opt/torii/scripts"):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from webhook_auth import authorize_webhook  # type: ignore
except ImportError:  # pragma: no cover — image always has scripts mount
    authorize_webhook = None  # type: ignore
try:
    from modal_parity import (  # type: ignore
        parse_paths_from_gh_filenames,
        path_skip_preflight,
        path_skip_stub_summary,
    )
except ImportError:  # pragma: no cover
    parse_paths_from_gh_filenames = None  # type: ignore
    path_skip_preflight = None  # type: ignore
    path_skip_stub_summary = None  # type: ignore

# Cheapest resource profile: Modal minimums (no cpu=/memory= reservation)
# https://modal.com/docs/guide/resources — default 0.125 core; over-request bills higher
_CHEAP = dict(
    # cpu omitted → 0.125 physical core min
    # memory omitted → soft minimum; hermes may burst — allow modest floor only if OOM
    timeout=60 * 25,  # hard cap wall time (kills runaway spend)
)


def _mlog(msg: str, *, stream: str = "stdout") -> None:
    """Emit a line into Modal function logs (UI + `modal app logs`).

    Modal captures container stdout/stderr. Anything only stored in files is
    invisible in the Modal UI unless we print it (with flush).
    """
    line = msg if msg.endswith("\n") else msg + "\n"
    if stream == "stderr":
        sys.stderr.write(line)
        sys.stderr.flush()
    else:
        sys.stdout.write(line)
        sys.stdout.flush()


def _banner(stage: str, detail: str = "") -> None:
    bar = "=" * 64
    _mlog(bar)
    _mlog(f"[torii/{stage}] {detail}".rstrip())
    _mlog(bar)


def _run(
    cmd: list[str],
    *,
    env: dict | None = None,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Quiet capture for short probes (not streamed to UI)."""
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, capture_output=True, text=True, check=False, env=merged, cwd=cwd
    )


def _pump_pipe(
    pipe: IO[str] | None,
    *,
    prefix: str,
    sink: list[str],
    to_stderr: bool = False,
) -> None:
    if pipe is None:
        return
    try:
        for raw in pipe:
            sink.append(raw)
            text = raw.rstrip("\n")
            _mlog(f"{prefix}{text}", stream="stderr" if to_stderr else "stdout")
    except Exception as e:  # noqa: BLE001
        _mlog(f"{prefix}[pump error: {e}]", stream="stderr")


def _run_stream(
    cmd: list[str],
    *,
    env: dict | None = None,
    cwd: str | None = None,
    label: str = "cmd",
) -> subprocess.CompletedProcess[str]:
    """Run a long command streaming stdout/stderr live into Modal UI logs.

    Unlike `_run` (capture_output=True), this prints every line with flush so
    operators can watch Hermes stages in the Modal dashboard / `modal run`.
    Full stdout/stderr are still collected for the result dict tails.
    """
    merged = {**os.environ, **(env or {})}
    _mlog(f"[torii/exec] start {label}: {' '.join(cmd[:8])}{'…' if len(cmd) > 8 else ''}")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=merged,
        cwd=cwd,
        bufsize=1,
    )
    out_buf: list[str] = []
    err_buf: list[str] = []
    t_out = threading.Thread(
        target=_pump_pipe,
        args=(proc.stdout,),
        kwargs={"prefix": f"[{label}:out] ", "sink": out_buf, "to_stderr": False},
        daemon=True,
    )
    t_err = threading.Thread(
        target=_pump_pipe,
        args=(proc.stderr,),
        kwargs={"prefix": f"[{label}:err] ", "sink": err_buf, "to_stderr": True},
        daemon=True,
    )
    t_out.start()
    t_err.start()
    rc = proc.wait()
    t_out.join(timeout=30)
    t_err.join(timeout=30)
    _mlog(f"[torii/exec] end {label} rc={rc}")
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=rc,
        stdout="".join(out_buf),
        stderr="".join(err_buf),
    )


def _tail_file_loop(
    path: Path,
    *,
    prefix: str,
    stop: threading.Event,
    poll_s: float = 0.4,
    start_at_end: bool = False,
) -> None:
    """Follow a growing file and print new lines to Modal logs (Hermes agent.log)."""
    pos = 0
    if start_at_end and path.is_file():
        try:
            pos = path.stat().st_size
        except OSError:
            pos = 0
    while not stop.is_set():
        try:
            if path.is_file():
                with path.open("r", encoding="utf-8", errors="replace") as fh:
                    fh.seek(pos)
                    chunk = fh.read()
                    if chunk:
                        pos = fh.tell()
                        for line in chunk.splitlines():
                            if line.strip():
                                _mlog(f"{prefix}{line}")
        except Exception as e:  # noqa: BLE001
            _mlog(f"{prefix}[tail error: {e}]", stream="stderr")
        stop.wait(poll_s)
    # final drain
    try:
        if path.is_file():
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                fh.seek(pos)
                for line in fh.read().splitlines():
                    if line.strip():
                        _mlog(f"{prefix}{line}")
    except Exception:  # noqa: BLE001
        pass


def _emit_artifact_summary(out_dir: Path, pr_number: int) -> dict[str, Any]:
    """Print key Hermes/agent-loop artifacts into Modal logs; return summary dict."""
    summary: dict[str, Any] = {}
    _banner("artifacts", f"OUT_DIR={out_dir}")

    # Hermes stderr (tool noise often lands here)
    for name in (
        f"hermes-{pr_number}.stderr",
        f"hermes-{pr_number}.reprompt.stderr",
        "hermes-run.log",
        "hermes-usage.json",
        "timings.json",
        "agent-loop/agent-loop.json",
        "agent-loop/agent-loop.md",
        f"review-{pr_number}.md",
    ):
        p = out_dir / name
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            size = -1
        summary[name] = size
        _mlog(f"[torii/artifact] {name} bytes={size}")

    # Structured agent-loop stats
    loop_json = out_dir / "agent-loop" / "agent-loop.json"
    if loop_json.is_file():
        try:
            data = json.loads(loop_json.read_text(encoding="utf-8", errors="replace"))
            tool_turns = data.get("tool_call_turns") or data.get("tool_turns")
            n_msgs = len(data.get("messages") or data.get("turns") or [])
            summary["agent_loop"] = {
                "tool_call_turns": tool_turns,
                "messages_or_turns": n_msgs,
                "keys": sorted(list(data.keys()))[:20],
            }
            _mlog(
                f"[torii/agent-loop] tool_call_turns={tool_turns} "
                f"messages_or_turns={n_msgs}"
            )
            # Sample tool names if present
            tools = data.get("tools") or data.get("tool_calls") or []
            if isinstance(tools, list) and tools:
                names = []
                for t in tools[:30]:
                    if isinstance(t, dict):
                        names.append(str(t.get("name") or t.get("tool") or t)[:80])
                    else:
                        names.append(str(t)[:80])
                _mlog(f"[torii/agent-loop] tools_sample={names[:12]}")
                summary["tools_sample"] = names[:12]
        except Exception as e:  # noqa: BLE001
            _mlog(f"[torii/agent-loop] parse failed: {e}", stream="stderr")

    # Tail hermes-run.log (offset-sliced agent activity)
    hrun = out_dir / "hermes-run.log"
    if hrun.is_file():
        try:
            text = hrun.read_text(encoding="utf-8", errors="replace")
            tail = text[-6000:] if len(text) > 6000 else text
            _banner("hermes-run.log tail", f"bytes={len(text)}")
            for line in tail.splitlines()[-80:]:
                _mlog(f"[hermes-run] {line}")
            summary["hermes_run_log_bytes"] = len(text)
        except Exception as e:  # noqa: BLE001
            _mlog(f"[hermes-run] read failed: {e}", stream="stderr")

    # Tail hermes stderr
    hse = out_dir / f"hermes-{pr_number}.stderr"
    if hse.is_file():
        try:
            text = hse.read_text(encoding="utf-8", errors="replace")
            tail = text[-4000:] if len(text) > 4000 else text
            _banner("hermes stderr tail", f"bytes={len(text)}")
            for line in tail.splitlines()[-60:]:
                _mlog(f"[hermes:err] {line}", stream="stderr")
            summary["hermes_stderr_bytes"] = len(text)
        except Exception as e:  # noqa: BLE001
            _mlog(f"[hermes:err] read failed: {e}", stream="stderr")

    return summary


@app.function()  # absolute minimum resources
def health() -> dict:
    return {
        "ok": True,
        "app": APP_NAME,
        "version": TORII_MODAL_VERSION,
        "runtime": "modal",
        "hermes_pin": HERMES_PIN,
        "profile": "cheap",
        "default_model": DEFAULT_MODEL,
    }


@app.function()
@modal.fastapi_endpoint(method="GET")
def health_http() -> dict:
    return health.local()


@app.function(secrets=[github_secret, openrouter_secret], timeout=180)
def probe_clone(repo: str = "Mr-Ashish/odoo") -> dict:
    """Bit 2: tools + secrets + shallow clone (no LLM)."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if not token or not os.environ.get("OPENROUTER_API_KEY"):
        return {"ok": False, "error": "missing secrets"}

    work = Path("/tmp/torii-probe")
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    # depth=1 only — never full history
    clone = _run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", url, str(work / "repo")],
        env={"GIT_TERMINAL_PROMPT": "0"},
    )
    if clone.returncode != 0:
        return {"ok": False, "error": "clone_failed", "stderr": (clone.stderr or "")[-600:]}

    head = _run(["git", "-C", str(work / "repo"), "rev-parse", "--short", "HEAD"])
    hermes = _run(["hermes", "--version"])
    prs = _run(
        ["gh", "pr", "list", "-R", repo, "--limit", "3", "--json", "number,title"],
        env={"GH_TOKEN": token, "GITHUB_TOKEN": token},
    )
    return {
        "ok": True,
        "bit": 2,
        "version": TORII_MODAL_VERSION,
        "repo": repo,
        "head": (head.stdout or "").strip(),
        "hermes": (hermes.stdout or hermes.stderr or "")[:120],
        "pr_list_rc": prs.returncode,
        "pr_list_preview": (prs.stdout or "")[:400],
        "profile": "cheap",
    }


def _list_pr_paths(repo: str, pr_number: int, token: str) -> list[str]:
    """List changed file paths for a PR (no clone)."""
    env = {
        **os.environ,
        "GH_TOKEN": token,
        "GITHUB_TOKEN": token,
        "GIT_TERMINAL_PROMPT": "0",
    }
    files_p = _run(
        [
            "gh",
            "api",
            f"repos/{repo}/pulls/{pr_number}/files",
            "--paginate",
            "-q",
            ".[].filename",
        ],
        env=env,
    )
    if parse_paths_from_gh_filenames is not None:
        return parse_paths_from_gh_filenames(files_p.stdout or "")
    paths = [ln.strip().lstrip("/") for ln in (files_p.stdout or "").splitlines() if ln.strip()]
    # unique
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _sparse_checkout_pr(repo: str, pr_number: int, workspace: Path, token: str) -> str:
    """Shallow clone + sparse paths for changed files only (monorepo-cheap)."""
    env = {
        **os.environ,
        "GH_TOKEN": token,
        "GITHUB_TOKEN": token,
        "GIT_TERMINAL_PROMPT": "0",
    }
    paths = _list_pr_paths(repo, pr_number, token)
    # unique top-level dirs + files, cap 40
    sparse: list[str] = []
    for p in paths[:80]:
        sparse.append(p)
        top = p.split("/")[0]
        if top and top not in sparse:
            sparse.append(top)
    sparse = sparse[:40]

    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True)

    # init empty + sparse
    _run(["git", "init"], cwd=str(workspace))
    _run(["git", "remote", "add", "origin", url], cwd=str(workspace))
    _run(["git", "config", "core.sparseCheckout", "true"], cwd=str(workspace))
    sparse_file = workspace / ".git" / "info" / "sparse-checkout"
    sparse_file.parent.mkdir(parents=True, exist_ok=True)
    if sparse:
        sparse_file.write_text("\n".join(sparse) + "\n")
    else:
        sparse_file.write_text("/*\n")  # fallback full tree shallow

    # fetch PR head only
    fetch = _run(
        [
            "git",
            "fetch",
            "--depth",
            "1",
            "origin",
            f"pull/{pr_number}/head:torii-pr",
        ],
        cwd=str(workspace),
        env=env,
    )
    if fetch.returncode != 0:
        # fallback: shallow full clone of default + pr checkout (still depth 1)
        shutil.rmtree(workspace, ignore_errors=True)
        c = _run(
            ["git", "clone", "--depth", "1", url, str(workspace)],
            env=env,
        )
        if c.returncode != 0:
            raise RuntimeError(f"clone failed: {(c.stderr or '')[-500:]}")
        _run(["gh", "pr", "checkout", str(pr_number)], cwd=str(workspace), env=env)
    else:
        _run(["git", "checkout", "torii-pr"], cwd=str(workspace))

    head = _run(["git", "rev-parse", "--short", "HEAD"], cwd=str(workspace))
    return (head.stdout or "").strip()


@app.function(
    secrets=[github_secret, openrouter_secret],
    # CHEAP: no cpu=/memory= reservation (Modal min). Only timeout.
    timeout=_CHEAP["timeout"],
    volumes={"/traces": trace_vol},
)
def review_pr(
    repo: str,
    pr_number: int,
    *,
    model: str = DEFAULT_MODEL,
    post_comment: bool = True,
) -> dict:
    """Bit 3: Torii Gate review on cheapest Modal profile + cheap LLM default.

    F67: streams orchestrator + Hermes agent.log / hermes stderr into Modal UI
    logs (print+flush). Previously capture_output=True hid all agent activity
    until a tiny orch_*_tail at the end.
    """
    t0 = time.time()
    _banner(
        "review_pr",
        f"repo={repo} pr={pr_number} model={model} post={post_comment} v={TORII_MODAL_VERSION}",
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    or_key = os.environ.get("OPENROUTER_API_KEY") or ""
    if not token or not or_key:
        _mlog("[torii] missing secrets", stream="stderr")
        return {"ok": False, "error": "missing secrets"}

    torii_root = Path("/opt/torii")
    if not (torii_root / "scripts" / "run-torii-review.sh").is_file():
        _mlog("[torii] pack missing under /opt/torii", stream="stderr")
        return {"ok": False, "error": "torii pack missing"}

    work = Path(f"/tmp/torii-run-{pr_number}-{int(t0)}")
    shutil.rmtree(work, ignore_errors=True)
    pack = work / "torii"
    workspace = work / "workspace"
    hermes_home = work / "hermes-home"
    out_dir = pack / ".torii-out"
    pack.mkdir(parents=True)
    shutil.copytree(torii_root / "scripts", pack / "scripts")
    shutil.copytree(torii_root / "agent", pack / "agent")
    for p in (pack / "scripts").iterdir():
        try:
            p.chmod(p.stat().st_mode | 0o111)
        except OSError:
            pass

    hermes_home.mkdir(parents=True)
    (hermes_home / "memories").mkdir(parents=True)
    (hermes_home / "logs").mkdir(parents=True)
    seed = pack / "agent" / "MEMORY.seed.md"
    if seed.is_file():
        shutil.copy(seed, hermes_home / "memories" / "MEMORY.md")
    out_dir.mkdir(parents=True)

    env = {
        **os.environ,
        "OPENROUTER_API_KEY": or_key,
        "GH_TOKEN": token,
        "GITHUB_TOKEN": token,
        "TORII_ROOT": str(pack),
        "WORKSPACE_ROOT": str(workspace),
        "HERMES_HOME": str(hermes_home),
        "OUT_DIR": str(out_dir),
        "TRACE_ROOT": str(out_dir / "traces"),
        "REPO": repo,
        "GITHUB_REPOSITORY": repo,
        "PR_NUMBER": str(pr_number),
        "TORII_MODEL": model,
        "OPENROUTER_MODEL": model,
        "TORII_HERMES_PREBAKED": "1",
        "TORII_HERMES_COMMIT": HERMES_PIN,
        # F66 prod defaults: local memory in-container; hub opt-in via Modal secret/env
        "TORII_MEMORY_MODE": os.environ.get("TORII_MEMORY_MODE", "local"),
        "TORII_LOCAL_PUBLISH": os.environ.get("TORII_LOCAL_PUBLISH", "0"),
        "TORII_HUB_PUBLISH": os.environ.get("TORII_HUB_PUBLISH", "0"),
        # F65 multi-tenant hub namespace (empty = classic shared layout)
        "TORII_MEMORY_TENANT": os.environ.get("TORII_MEMORY_TENANT", ""),
        "TORII_HUB_REPO": os.environ.get(
            "TORII_HUB_REPO", "Mr-Ashish/torii-gate"
        ),
        "POST_COMMENT": "1" if post_comment else "0",
        "TRIGGER_COMMENT": "modal cheap e2e",
        "MAX_DIFF_BYTES": os.environ.get("MAX_DIFF_BYTES", "400000"),
        "TORII_TOOLSETS": "terminal",
        "TORII_HOST": "modal",  # F31/F66 Run Console host label (prod default e2e)
        # F67: stream Hermes stderr + agent activity (scripts tee when set)
        "TORII_STREAM_LOGS": "1",
        # F63: domain pack auto-select from changed paths (default product)
        "TORII_LENS_PACK": os.environ.get("TORII_LENS_PACK", "auto"),
        "TORII_LENS_PACKS": os.environ.get("TORII_LENS_PACKS", "1"),
        # F36: wall-clock (script default 1500s if unset)
        "TORII_REVIEW_TIMEOUT_SECONDS": os.environ.get(
            "TORII_REVIEW_TIMEOUT_SECONDS", "1500"
        ),
        # F41: Hermes max_turns (script default 40 if unset; 0/off disables)
        "TORII_MAX_TURNS": os.environ.get("TORII_MAX_TURNS", "40"),
        # F42: auto model tier (off by default; auto|cheap|full)
        "TORII_MODEL_TIER": os.environ.get("TORII_MODEL_TIER", "off"),
        "TORII_MODEL_CHEAP": os.environ.get("TORII_MODEL_CHEAP", ""),
        "TORII_MODEL_FULL": os.environ.get("TORII_MODEL_FULL", ""),
        # F43: hard preflight cost (auto hard when TORII_MAX_COST_USD set)
        "TORII_MAX_COST_USD": os.environ.get("TORII_MAX_COST_USD", ""),
        "TORII_PREFLIGHT_COST": os.environ.get("TORII_PREFLIGHT_COST", ""),
        "TORII_PREFLIGHT_ACTION": os.environ.get("TORII_PREFLIGHT_ACTION", ""),
        "PATH": os.environ.get(
            "PATH",
            "/root/.local/bin:/root/.hermes/bin:/usr/local/bin:/usr/bin:/bin",
        ),
        # Force line-buffered Python/Hermes children where possible
        "PYTHONUNBUFFERED": "1",
    }
    _mlog(
        f"[torii/env] HERMES_HOME={hermes_home} OUT_DIR={out_dir} "
        f"WORKSPACE={workspace} STREAM_LOGS=1 LENS_PACK={env.get('TORII_LENS_PACK')}"
    )

    # ------------------------------------------------------------------
    # F39: path-skip preflight (F38) BEFORE clone / OpenRouter spend
    # ------------------------------------------------------------------
    path_skip_info: dict[str, Any] | None = None
    try:
        pr_paths = _list_pr_paths(repo, pr_number, token)
    except Exception as e:  # noqa: BLE001
        pr_paths = []
        path_skip_info = {"skip": False, "reason": f"list_paths_error:{e}"}

    force_skip = (os.environ.get("TORII_SKIP_PATHS_FORCE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if path_skip_preflight is not None and pr_paths is not None:
        path_skip_info = path_skip_preflight(
            pr_paths,
            globs_raw=os.environ.get("TORII_SKIP_PATH_GLOBS"),
            force=force_skip,
        )

    if path_skip_info and path_skip_info.get("skip"):
        summary, blocking = (
            path_skip_stub_summary(
                str(path_skip_info.get("sample") or ""),
                str(path_skip_info.get("globs") or ""),
            )
            if path_skip_stub_summary
            else (
                "Path-skip: all paths matched globs (F39 Modal).",
                "None — free skip.",
            )
        )
        # F40: durable signal for Run Console pack
        try:
            (out_dir / "ops-signals.env").write_text(
                "PATH_SKIP=1\n"
                f"sample={path_skip_info.get('sample') or ''}\n"
                f"globs={path_skip_info.get('globs') or ''}\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        stub_script = pack / "scripts" / "write-failure-review.sh"
        review_path: Path | None = None
        if stub_script.is_file():
            _run(
                [
                    "bash",
                    str(stub_script),
                    str(pr_number),
                    str(out_dir),
                    summary,
                    blocking,
                ],
                env=env,
            )
            cands = [
                p
                for p in sorted(out_dir.glob("review-*.md"))
                if ".raw." not in p.name
            ]
            review_path = cands[0] if cands else None
        post_rc = None
        verdict_rc = None
        if post_comment and review_path and review_path.is_file():
            post = _run(
                [
                    "bash",
                    str(pack / "scripts" / "post-review-comment.sh"),
                    str(review_path),
                    str(pr_number),
                ],
                env=env,
            )
            post_rc = post.returncode
            # F39: labels/status even on free skip (COMMENT)
            if (pack / "scripts" / "report-verdict.sh").is_file():
                v = _run(
                    [
                        "bash",
                        str(pack / "scripts" / "report-verdict.sh"),
                        str(review_path),
                        "0",
                    ],
                    env={
                        **env,
                        "TORII_INLINE_COMMENTS": "0",
                        "PIPELINE_RC": "0",
                    },
                )
                verdict_rc = v.returncode
        return {
            "ok": True,
            "bit": 3,
            "profile": "cheap",
            "version": TORII_MODAL_VERSION,
            "repo": repo,
            "pr_number": pr_number,
            "model": model,
            "path_skip": path_skip_info,
            "skipped_paid": True,
            "orch_rc": 0,
            "post_rc": post_rc,
            "verdict_rc": verdict_rc,
            "review_path": str(review_path) if review_path else None,
            "elapsed_s": round(time.time() - t0, 1),
            "note": "F39 path-skip: no OpenRouter / no clone",
        }

    try:
        _banner("checkout", f"sparse PR head {repo}#{pr_number}")
        head_sha = _sparse_checkout_pr(repo, pr_number, workspace, token)
        _mlog(f"[torii/checkout] head={head_sha}")
    except Exception as e:  # noqa: BLE001
        _mlog(f"[torii/checkout] FAILED: {e}", stream="stderr")
        return {"ok": False, "error": f"checkout: {e}", "elapsed_s": round(time.time() - t0, 1)}

    # Full SHA for F22 commit status + F9 inline
    head_full_p = _run(["git", "rev-parse", "HEAD"], cwd=str(workspace))
    head_full = (head_full_p.stdout or "").strip() or head_sha
    env["HEAD_SHA"] = head_full
    env["WORKSPACE_ROOT"] = str(workspace)

    # F67: follow Hermes agent.log + stderr while orchestrator runs
    stop_tails = threading.Event()
    agent_log = hermes_home / "logs" / "agent.log"
    hermes_stderr = out_dir / f"hermes-{pr_number}.stderr"
    hermes_run_log = out_dir / "hermes-run.log"
    tails = [
        threading.Thread(
            target=_tail_file_loop,
            args=(agent_log,),
            kwargs={"prefix": "[hermes-agent] ", "stop": stop_tails, "start_at_end": False},
            daemon=True,
            name="tail-agent-log",
        ),
        threading.Thread(
            target=_tail_file_loop,
            args=(hermes_stderr,),
            kwargs={"prefix": "[hermes:err-live] ", "stop": stop_tails, "start_at_end": False},
            daemon=True,
            name="tail-hermes-stderr",
        ),
        threading.Thread(
            target=_tail_file_loop,
            args=(hermes_run_log,),
            kwargs={"prefix": "[hermes-run-live] ", "stop": stop_tails, "start_at_end": False},
            daemon=True,
            name="tail-hermes-run",
        ),
    ]
    for t in tails:
        t.start()

    orch = pack / "scripts" / "run-torii-review.sh"
    _banner("orchestrator", f"run-torii-review.sh pr={pr_number}")
    try:
        proc = _run_stream(
            ["bash", str(orch)],
            env=env,
            label="orch",
        )
    finally:
        stop_tails.set()
        for t in tails:
            t.join(timeout=5)

    orch_rc = proc.returncode
    _mlog(f"[torii/orchestrator] rc={orch_rc}")

    review_files = [
        p
        for p in sorted(out_dir.glob("review-*.md"))
        if ".raw." not in p.name
    ]
    review_path = review_files[0] if review_files else None

    # F67: dump Hermes/agent-loop artifacts into Modal logs
    artifact_summary = _emit_artifact_summary(out_dir, pr_number)

    post_rc = None
    if post_comment and review_path and review_path.is_file():
        _banner("post_comment", f"{repo}#{pr_number}")
        post = _run_stream(
            [
                "bash",
                str(pack / "scripts" / "post-review-comment.sh"),
                str(review_path),
                str(pr_number),
            ],
            env=env,
            label="post",
        )
        post_rc = post.returncode
        _mlog(f"[torii/post] rc={post_rc}")

    # ------------------------------------------------------------------
    # F39: GHA-parity signals — commit status, PR review, inline, labels
    # ------------------------------------------------------------------
    verdict_rc = None
    if review_path and review_path.is_file() and (pack / "scripts" / "report-verdict.sh").is_file():
        _banner("report_verdict", f"pipeline_rc={orch_rc}")
        v_env = {
            **env,
            "HEAD_SHA": head_full,
            "PIPELINE_RC": str(orch_rc),
            "TORII_INLINE_DIFF": str(out_dir / "pr.diff"),
        }
        v = _run_stream(
            [
                "bash",
                str(pack / "scripts" / "report-verdict.sh"),
                str(review_path),
                str(orch_rc),
            ],
            env=v_env,
            label="verdict",
        )
        verdict_rc = v.returncode
        _mlog(f"[torii/verdict] rc={verdict_rc}")

    run_id = f"{repo.replace('/', '--')}-pr{pr_number}-{int(t0)}"
    vol_dest = Path("/traces") / run_id
    vol_err = None
    try:
        if out_dir.exists():
            _banner("trace_volume", f"copy → {vol_dest}")
            shutil.copytree(out_dir, vol_dest, dirs_exist_ok=True)
            # Also write a small modal-visible index of what was streamed
            index = {
                "version": TORII_MODAL_VERSION,
                "repo": repo,
                "pr": pr_number,
                "run_id": run_id,
                "artifact_summary": artifact_summary,
                "orch_rc": orch_rc,
            }
            (vol_dest / "modal-run-index.json").write_text(
                json.dumps(index, indent=2) + "\n", encoding="utf-8"
            )
            # Persist a concatenated stream hint file for offline replay
            stream_note = out_dir / "modal-stream-note.txt"
            stream_note.write_text(
                "F67: live logs were printed to Modal function stdout/stderr.\n"
                "Re-fetch: modal app logs torii-pr-review  OR dashboard run page.\n"
                f"Volume path: {vol_dest}\n"
                f"Artifacts: {json.dumps(artifact_summary)}\n",
                encoding="utf-8",
            )
            shutil.copy2(stream_note, vol_dest / "modal-stream-note.txt")
            trace_vol.commit()
            _mlog(f"[torii/traces] committed volume path={vol_dest}")
    except Exception as e:  # noqa: BLE001
        vol_err = str(e)
        _mlog(f"[torii/traces] volume error: {e}", stream="stderr")

    preview = ""
    if review_path and review_path.is_file():
        preview = review_path.read_text(errors="replace")[:1200]
        _banner("review_preview", f"{review_path.name}")
        for line in preview.splitlines()[:40]:
            _mlog(f"[review] {line}")

    # F31: surface Run Console bundle path (orchestrator writes run-bundle.json)
    run_bundle = out_dir / "run-bundle.json"
    if not run_bundle.is_file() and (pack / "scripts" / "pack-run-for-ui.py").is_file():
        # Soft fallback if older orchestrator missed pack stage
        latest = out_dir / "latest-trace-dir.txt"
        pack_src = Path(latest.read_text().strip()) if latest.is_file() else out_dir
        _run(
            [
                "python3",
                str(pack / "scripts" / "pack-run-for-ui.py"),
                "--dir",
                str(pack_src if pack_src.is_dir() else out_dir),
                "-o",
                str(run_bundle),
                "--host",
                "modal",
                "--soft",
            ],
            env=env,
        )
        if run_bundle.is_file() and vol_dest.exists():
            try:
                shutil.copy2(run_bundle, vol_dest / "run-bundle.json")
                trace_vol.commit()
            except Exception:  # noqa: BLE001
                pass

    elapsed = round(time.time() - t0, 1)
    _banner(
        "done",
        f"ok={orch_rc == 0 and bool(review_path)} orch_rc={orch_rc} "
        f"elapsed_s={elapsed} review={bool(review_path)}",
    )

    return {
        "ok": orch_rc == 0 and bool(review_path),
        "bit": 3,
        "profile": "cheap",
        "version": TORII_MODAL_VERSION,
        "repo": repo,
        "pr_number": pr_number,
        "head": head_sha,
        "model": model,
        "orch_rc": orch_rc,
        "post_rc": post_rc,
        "verdict_rc": verdict_rc,
        "path_skip": path_skip_info,
        "skipped_paid": False,
        "review_path": str(review_path) if review_path else None,
        "run_bundle": str(run_bundle) if run_bundle.is_file() else None,
        "review_preview": preview,
        "orch_stderr_tail": (proc.stderr or "")[-4000:],
        "orch_stdout_tail": (proc.stdout or "")[-2000:],
        "artifact_summary": artifact_summary,
        "elapsed_s": elapsed,
        "trace_volume_path": str(vol_dest),
        "trace_volume_error": vol_err,
        "resources": "default-min (no cpu/memory reservation)",
        "log_streaming": True,
        "stream_note": (
            "Live logs streamed to Modal UI via print+flush; "
            "Hermes agent.log / hermes stderr tailed during orchestrator"
        ),
    }


_TORII_TRIGGER_RE = re.compile(
    r"@torii\b.*\breview\b",
    re.IGNORECASE | re.DOTALL,
)


def parse_enqueue_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Parse simple API or GitHub issue_comment webhook → enqueue plan.

    Simple API:
      {"repo": "owner/name", "pr": 3, "model": "...", "post_comment": true}

    GitHub issue_comment (PR thread):
      action=created, issue.pull_request set, comment.body matches @torii … review
    """
    if not isinstance(item, dict):
        return {"ok": False, "error": "body must be a JSON object"}

    # --- simple API ---
    if item.get("repo") and item.get("pr") is not None:
        try:
            pr_n = int(item["pr"])
        except (TypeError, ValueError):
            return {"ok": False, "error": "pr must be an int"}
        repo = str(item["repo"]).strip()
        if "/" not in repo:
            return {"ok": False, "error": "repo must be owner/name"}
        model = str(item.get("model") or DEFAULT_MODEL)
        post = item.get("post_comment", True)
        if isinstance(post, str):
            post = post.strip().lower() not in ("0", "false", "no", "off")
        return {
            "ok": True,
            "source": "api",
            "repo": repo,
            "pr_number": pr_n,
            "model": model,
            "post_comment": bool(post),
            "trigger": "api",
        }

    # --- GitHub webhook (issue_comment on a PR) ---
    action = item.get("action")
    issue = item.get("issue") or {}
    comment = item.get("comment") or {}
    repository = item.get("repository") or {}
    if issue.get("pull_request") and repository.get("full_name"):
        body = (comment.get("body") or "") if isinstance(comment, dict) else ""
        if action and action not in ("created", "edited"):
            return {
                "ok": False,
                "skipped": True,
                "error": f"ignore action={action}",
                "source": "github",
            }
        if not _TORII_TRIGGER_RE.search(body):
            return {
                "ok": False,
                "skipped": True,
                "error": "comment does not match @torii review",
                "source": "github",
            }
        try:
            pr_n = int(issue.get("number"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "issue.number missing", "source": "github"}
        return {
            "ok": True,
            "source": "github",
            "repo": str(repository["full_name"]),
            "pr_number": pr_n,
            "model": str(item.get("model") or DEFAULT_MODEL),
            "post_comment": True,
            "trigger": (body or "")[:200],
            "comment_id": comment.get("id") if isinstance(comment, dict) else None,
        }

    return {
        "ok": False,
        "error": "unrecognized payload (need repo+pr or GitHub issue_comment on a PR)",
    }


def plan_enqueue(
    repo: str,
    pr_number: int,
    *,
    model: str = DEFAULT_MODEL,
    post_comment: bool = True,
) -> dict[str, Any]:
    """Bit 4 dry plan — no Modal spawn, no Hermes (free)."""
    return {
        "ok": True,
        "bit": 4,
        "dry_run": True,
        "spawned": False,
        "version": TORII_MODAL_VERSION,
        "repo": repo,
        "pr_number": pr_number,
        "model": model or DEFAULT_MODEL,
        "post_comment": post_comment,
        "note": "Pass spawn=True / webhook without dry_run to review_pr.spawn",
    }


@app.function(secrets=[github_secret, openrouter_secret], timeout=120)
def enqueue_review(
    repo: str,
    pr_number: int,
    *,
    model: str = DEFAULT_MODEL,
    post_comment: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Bit 4: spawn review_pr (or return plan when dry_run). Never runs Hermes here."""
    if dry_run:
        return plan_enqueue(repo, pr_number, model=model, post_comment=post_comment)
    # Spawn — returns immediately; worker runs separately
    call = review_pr.spawn(
        repo, pr_number, model=model or DEFAULT_MODEL, post_comment=post_comment
    )
    call_id = getattr(call, "object_id", None) or getattr(call, "objectId", None) or str(call)
    return {
        "ok": True,
        "bit": 4,
        "dry_run": False,
        "spawned": True,
        "version": TORII_MODAL_VERSION,
        "repo": repo,
        "pr_number": pr_number,
        "model": model or DEFAULT_MODEL,
        "post_comment": post_comment,
        "call_id": call_id,
        "profile": "cheap",
    }


@app.function(secrets=[github_secret, openrouter_secret], timeout=60)
@modal.fastapi_endpoint(method="POST")
async def review_webhook(request: Any) -> dict:
    """HTTP doorbell: auth (F33) → parse body → spawn review_pr.

    Hermes never runs in this handler. Deploy: `modal deploy modal_app/app.py`.

    Auth (env on the function / secrets) — F34 fail-closed:
      TORII_WEBHOOK_SECRET  → require X-Hub-Signature-256 (GitHub)
      TORII_WEBHOOK_TOKEN   → require Authorization: Bearer … or X-Torii-Token
      neither set           → denied unless TORII_WEBHOOK_ALLOW_OPEN=1 (dev)

    TORII_WEBHOOK_DRY_RUN=1 → plan only (no spawn).
    """
    # FastAPI Request (Modal fastapi_endpoint) — fall back if a plain dict is passed in tests
    raw: bytes
    headers: dict[str, str] = {}
    if hasattr(request, "body") and callable(request.body):
        raw = await request.body()
        try:
            headers = {k: v for k, v in request.headers.items()}
        except Exception:  # noqa: BLE001
            headers = {}
    elif isinstance(request, dict):
        raw = json.dumps(request).encode("utf-8")
        headers = {}
    else:
        return {
            "ok": False,
            "bit": 4,
            "version": TORII_MODAL_VERSION,
            "error": "unsupported request type",
            "auth": "denied",
        }

    if authorize_webhook is None:
        auth = {
            "ok": False,
            "auth": "denied",
            "error": "webhook_auth module missing on image",
        }
    else:
        auth = authorize_webhook(raw, headers)

    if not auth.get("ok"):
        return {
            "ok": False,
            "bit": 4,
            "version": TORII_MODAL_VERSION,
            "auth": auth.get("auth", "denied"),
            "error": auth.get("error", "unauthorized"),
        }

    try:
        item = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {
            "ok": False,
            "bit": 4,
            "version": TORII_MODAL_VERSION,
            "auth": auth.get("auth"),
            "error": "body is not JSON",
        }

    plan = parse_enqueue_payload(item if isinstance(item, dict) else {})
    if not plan.get("ok"):
        # skipped is still HTTP 200-ish for GitHub (avoid retries); surface ok=false
        return {
            **plan,
            "bit": 4,
            "version": TORII_MODAL_VERSION,
            "auth": auth.get("auth"),
            "auth_warning": auth.get("warning"),
        }
    dry = os.environ.get("TORII_WEBHOOK_DRY_RUN", "").strip() in ("1", "true", "yes")
    result = enqueue_review.local(
        plan["repo"],
        int(plan["pr_number"]),
        model=str(plan.get("model") or DEFAULT_MODEL),
        post_comment=bool(plan.get("post_comment", True)),
        dry_run=dry,
    )
    result["source"] = plan.get("source")
    result["trigger"] = plan.get("trigger")
    result["auth"] = auth.get("auth")
    if auth.get("warning"):
        result["auth_warning"] = auth["warning"]
    if plan.get("comment_id") is not None:
        result["comment_id"] = plan["comment_id"]
    return result


@app.local_entrypoint()
def main(
    bit: int = 1,
    repo: str = "Mr-Ashish/odoo",
    pr: int = 3,
    model: str = DEFAULT_MODEL,
    post_comment: bool = True,
    spawn: bool = False,
) -> None:
    if bit == 2:
        result = probe_clone.remote(repo=repo)
        print(json.dumps(result, indent=2)[:2000])
        assert result.get("ok"), result
        print("BIT2_OK")
        return
    if bit == 3:
        print(f"CHEAP review_pr {repo}#{pr} model={model}")
        result = review_pr.remote(repo, pr, model=model, post_comment=post_comment)
        slim = {k: v for k, v in result.items() if k != "review_preview"}
        print(json.dumps(slim, indent=2))
        if result.get("review_preview"):
            print("--- preview ---")
            print(result["review_preview"][:800])
        assert result.get("ok"), result
        print("BIT3_OK")
        return
    if bit == 4:
        # Default dry plan (no OpenRouter spend). --spawn to actually enqueue.
        print(f"BIT4 enqueue plan {repo}#{pr} model={model} spawn={spawn}")
        if spawn:
            result = enqueue_review.remote(
                repo, pr, model=model, post_comment=post_comment, dry_run=False
            )
        else:
            result = plan_enqueue(repo, pr, model=model, post_comment=post_comment)
            # Also exercise payload parser with simple API shape
            parsed = parse_enqueue_payload(
                {"repo": repo, "pr": pr, "model": model, "post_comment": post_comment}
            )
            result["parsed_ok"] = parsed.get("ok")
            gh = parse_enqueue_payload(
                {
                    "action": "created",
                    "issue": {"number": pr, "pull_request": {"url": "x"}},
                    "comment": {"id": 1, "body": "@torii review this pr"},
                    "repository": {"full_name": repo},
                }
            )
            result["github_parse_ok"] = gh.get("ok")
            result["github_skip"] = parse_enqueue_payload(
                {
                    "action": "created",
                    "issue": {"number": pr, "pull_request": {"url": "x"}},
                    "comment": {"body": "lgtm"},
                    "repository": {"full_name": repo},
                }
            ).get("skipped")
            # F33/F34: pure auth self-check (no network)
            if authorize_webhook is not None:
                body = b'{"repo":"a/b","pr":1}'
                # F34: default fail-closed when no creds
                closed = authorize_webhook(
                    body, {}, secret="", token="", allow_open=False
                )
                result["auth_fail_closed_ok"] = (
                    closed.get("ok") is False and closed.get("auth") == "denied"
                )
                open_auth = authorize_webhook(
                    body, {}, secret="", token="", allow_open=True
                )
                result["auth_open_ok"] = open_auth.get("auth") == "open" and open_auth.get(
                    "ok"
                )
                from webhook_auth import github_hmac_hex  # type: ignore

                sec = "test-secret"
                sig = f"sha256={github_hmac_hex(body, sec)}"
                good = authorize_webhook(
                    body, {"X-Hub-Signature-256": sig}, secret=sec, token=""
                )
                bad = authorize_webhook(
                    body, {"X-Hub-Signature-256": "sha256=dead"}, secret=sec, token=""
                )
                tok = authorize_webhook(
                    body,
                    {"Authorization": "Bearer s3cr3t"},
                    secret="",
                    token="s3cr3t",
                )
                denied = authorize_webhook(body, {}, secret=sec, token="")
                result["auth_hmac_ok"] = good.get("ok") is True
                result["auth_hmac_bad"] = bad.get("ok") is False
                result["auth_bearer_ok"] = tok.get("ok") is True
                result["auth_denied_ok"] = denied.get("ok") is False
        print(json.dumps(result, indent=2)[:2500])
        assert result.get("ok"), result
        if not spawn:
            assert result.get("parsed_ok") and result.get("github_parse_ok")
            assert result.get("github_skip") is True
            if authorize_webhook is not None:
                assert result.get("auth_fail_closed_ok")
                assert result.get("auth_open_ok")
                assert result.get("auth_hmac_ok")
                assert result.get("auth_hmac_bad")
                assert result.get("auth_bearer_ok")
                assert result.get("auth_denied_ok")
        print("BIT4_OK")
        return
    result = health.remote()
    print(result)
    assert result.get("ok")
    print("BIT1_OK")
