---
id: skill-archival-memory-search
feature: F98/F99
status: adopted
source: product_memory_loop
created_at: 2026-08-01T03:15:00Z
title: Archival memory search when cold facts may apply
---

## Skill: archival-memory-search (MemGPT-style paging)

When the PR touches paths that may match **prior FP/TP or MEMORY.md history**:

1. Prefer the pre-injected **Archival search → core (F98)** and **Memory tools (F103)** sections if present.
2. Prefer the unified front door (F103) via terminal:
   `python3 scripts/torii_memory.py help`
   `python3 scripts/torii_memory.py search -- -q "theme keywords"`
   `python3 scripts/torii_memory.py search-auto -- --files path1,path2`
   `python3 scripts/torii_memory.py graph -- query --path path1 --hops 2`
   `python3 scripts/torii_memory.py compound -- status`  # F104 post-run integrity write
3. Treat promoted hits as **hints for this PR only** — still require path:line evidence to block.
   Path-evidenced findings compound into durable TP only via F104 integrity gate (not free-form).
4. Do **not** re-raise archival FP themes without new path evidence.
5. Prefer **core** tier items over archival noise for blocking severity.

**Why:** Cold stores stay cold until path tokens match; just-in-time paging, not full dump.
