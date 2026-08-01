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

1. Prefer the pre-injected **Archival search → core (F98)** section if present.
2. Or run via terminal (workspace):
   `python3 scripts/archival_memory_search.py auto --files path1,path2`
   / `python3 scripts/archival_memory_search.py search -q "theme keywords"`
3. Treat promoted hits as **hints for this PR only** — still require path:line evidence to block.
4. Do **not** re-raise archival FP themes without new path evidence.
5. Prefer **core** tier items over archival noise for blocking severity.

**Why:** Cold stores stay cold until path tokens match; just-in-time paging, not full dump.
