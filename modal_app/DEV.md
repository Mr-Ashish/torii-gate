# DEV — engineering knowledge

> How this part of the system is built.

## Design decisions

- The Modal entrypoint is a first-class host in the F31 Run Console contract: `review_pr` exports `TORII_HOST=modal` so `pack-run-for-ui.py` stamps the bundle's host label as `modal` instead of falling through the `GITHUB_ACTIONS`/else auto-detect to `local`.
- `review_pr` also returns the `run_bundle` path in its result, so a Modal caller gets the console bundle handle back directly rather than having to download an Actions artifact (the GHA path's only option).

- F34 deliberately reverses F33's behaviour rather than extending it: F33 allowed unauthenticated requests with a warning when no secret/token was configured; F34 makes that same state `auth=denied` so the production-safe posture is the default and misconfiguration is loud instead of silent.
- The open-mode escape hatch is exposed on three surfaces that must stay in sync: env `TORII_WEBHOOK_ALLOW_OPEN=1`, the `allow_open=True` argument on the auth helper, and the `--allow-open` flag on `scripts/webhook_auth.py`. All three exist for dev/self-check only — none is a supported production configuration.

- The F36 default of **1500s** is chosen to sit just under Modal's `review_pr` hard cap (~25m) rather than under the GHA job cap (90m) — the tighter host sets the shared default, so the same number is safe on both. Changing `DEFAULT_SECONDS` in `scripts/run-with-timeout.py` without re-checking the Modal function timeout would let a Modal run be killed by the platform instead of by the helper (losing the honest 124 stub and job-summary section).

- **F39:** `review_pr` must call the same pure gates as GHA rather than re-implementing them — `scripts/modal_parity.py` wraps F38 `path-skip-check` for preflight; post-review signals go through `report-verdict.sh` (not ad-hoc gh calls in app.py). Path-skip runs **before** sparse clone so a docs-only Modal run never pays for git fetch or Hermes.
- On path-skip, Modal still posts a stub COMMENT + report-verdict labels when `post_comment=True`, so operators see an honest free skip instead of silence.

## Architecture

- Bit 4 (F32) splits the enqueue path into four units in `modal_app/app.py`: `parse_enqueue_payload` (normalize an incoming request into repo/pr/model/post_comment), `plan_enqueue` (pure plan, no side effects), `enqueue_review` (the spawn call), and `review_webhook` (the HTTP entrypoint). Parsing/planning are separable from spawning so the parser can be self-checked without any OpenRouter spend.
- `review_webhook` accepts two payload shapes: the simple API `{repo, pr, model, post_comment}`, and a raw GitHub `issue_comment` event whose comment body matches `@torii … review` and whose issue is a PR. There is no third shape — non-PR issue comments and non-matching bodies are not enqueued.

- On a free skip the run is not silent — it still posts a stub COMMENT built by `path_skip_stub_summary()` and still invokes `report-verdict.sh` so labels/status appear (`skipped_paid: true`).
- Shared logic lives in the pure helper `scripts/modal_parity.py` (`path_skip_preflight`, `path_skip_stub_summary`), which re-exports `decide`/`load_paths`/`parse_globs` from the hyphenated `scripts/path-skip-check.py` via `importlib.util.spec_from_file_location` — Modal and GHA therefore share one decision function instead of two copies.
- Host contract knobs: `TORII_SKIP_PATH_GLOBS` (globs), `TORII_SKIP_PATHS_FORCE=1` (force skip), `TORII_REVIEW_TIMEOUT_SECONDS` (default 1500). App profile stamp `TORII_MODAL_VERSION = "0.6.0-f39"` is returned in every result payload.

## Pitfalls

- **F33/F34:** production must set `TORII_WEBHOOK_SECRET` and/or `TORII_WEBHOOK_TOKEN` on the Modal function (e.g. fold into `torii-github`). **F34 fail-closed:** if neither is set, requests are **denied** unless `TORII_WEBHOOK_ALLOW_OPEN=1` (dev escape only).
- HMAC verification needs the **raw** request body (not a re-serialized dict). The webhook reads `await request.body()` before `json.loads`; do not switch back to a typed `item: dict` parameter or signatures will never match.
- Two independent dry switches exist and they are easy to confuse: `TORII_WEBHOOK_DRY_RUN=1` makes the *deployed HTTP handler* plan-only, while the CLI `--bit 4` is dry by default and needs `--spawn` to actually enqueue. Setting one does not affect the other — a "dry" CLI run says nothing about the deployed webhook's behaviour.
- Do not add work (Hermes, cloning, review assembly) to the HTTP handler even for convenience; the spawn-only rule is what keeps the request short-lived and the billed work inside `review_pr`.

- The path listing step fails open too: an API error records `path_skip_info = {"skip": False, "reason": "list_paths_error:…"}` and continues to the paid path — check that `reason` when a docs-only PR unexpectedly costs OpenRouter spend.
- Because the helper is imported by file path from the `scripts/` directory inside the packaged app, the F10 pack must ship both `scripts/modal_parity.py` and `scripts/path-skip-check.py`; shipping only one silently disables the gate.

- **F41:** Modal `review_pr` forwards `TORII_MAX_TURNS` (default 40) into the pipeline env so bit-3 matches GHA iteration budget.

## F80 secrets

```bash
python3 scripts/modal_secrets_bootstrap.py apply
modal run modal_app/app.py --bit 3 --repo pytorch/pytorch --pr 191813 --no-post-comment
```

