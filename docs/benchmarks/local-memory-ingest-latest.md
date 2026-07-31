# F28 local memory ingest micro-benchmark

Measured offline on macOS (no network; pure Python ingest path).

| Metric | Value |
|--------|-------|
| Runs | 20× `hub-ingest-run.py` layout=local |
| Total | ~1.79 s |
| Per-run | **~90 ms** |
| Output | `.torii/MEMORY.md` + `runs/{trace}/{meta,review,summary}` |

Notes:
- Does **not** include git clone/push (CI-only; depends on network + branch protection).
- Hub publish with `TORII_MEMORY_MODE=local` exits in &lt;10 ms with `skip hub publish`.
- Fat hermes traces remain Actions artifacts and are not part of this path.
