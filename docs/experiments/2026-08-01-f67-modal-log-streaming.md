# F67 — Modal live log streaming (Hermes agent activity in UI)

**Date:** 2026-08-01  
**Status:** shipping  
**Tag:** PRODUCT_FEATURE | OPS | MODAL | OBSERVABILITY

## Analysis (why logs were invisible)

### Torii Modal path (before)

1. `review_pr` ran the orchestrator with `_run()` → `subprocess.run(..., capture_output=True)`.
2. **All** orchestrator stdout/stderr was buffered in memory.
3. Hermes itself redirects: `hermes … >RAW 2>STDERR_FILE` — agent tools land in files,
   not the parent process stream.
4. Modal UI only shows container **stdout/stderr** (Modal Python SDK docs:
   function prints appear in app/function logs; `modal.enable_output()` is for local SDK
   consumers of those remote logs).
5. Result JSON only returned `orch_stderr_tail` (−1500 chars) and `orch_stdout_tail` (−800).
6. Full traces were copied to Volume `torii-traces` but **not** visible live in the UI.

### Modal client (cloned `/tmp/modal-client`)

- Logs are collected from container stdout/stderr file descriptors
  (`py/modal/_logs.py`, `io_streams.py`, `FunctionCallLogsManager`).
- `print(..., flush=True)` / writing to `sys.stdout`/`sys.stderr` is the supported way
  for user code to emit dashboard-visible logs.
- There is no separate “agent log upload” API for free-form files; files must be
  printed or written to a Volume/Object store.

## Fix

1. **`_run_stream`**: Popen + line-pump threads → `[label:out|err]` into Modal logs.
2. **Background tails** of `HERMES_HOME/logs/agent.log`, `hermes-{pr}.stderr`,
   `hermes-run.log` while orchestrator runs.
3. **`TORII_STREAM_LOGS=1`** (set on Modal): `run-hermes-review.sh` tees Hermes
   stderr to file **and** process stderr.
4. **Post-run `_emit_artifact_summary`**: agent-loop tool stats + log tails.
5. Volume still stores full `.torii-out` + `modal-run-index.json`.

Version: `0.8.0-f67`.

## Verify

```bash
./scripts/trigger-review.sh modal Mr-Ashish/milvus 6 --cheap --post
# Dashboard run should show [orch:err], [hermes-agent], [hermes:err-live], …
# Result JSON: "log_streaming": true, "version": "0.8.0-f67"
```
