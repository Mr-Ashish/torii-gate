#!/usr/bin/env bash
# Write a contract-compliant failure review markdown file.
# Usage: write-failure-review.sh <pr_number> <out_dir> <summary_line>
set -euo pipefail

PR_NUMBER="${1:?pr number}"
OUT_DIR="${2:?out dir}"
SUMMARY="${3:-Torii failed. Check Actions logs.}"
BLOCKING="${4:-Re-run after fixing the failure.}"

mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/review-${PR_NUMBER}.md"

cat >"$OUT" <<EOF
<!-- torii-review pr=${PR_NUMBER} -->
## 🏴‍☠️ Torii Review — PR #${PR_NUMBER}

**Verdict:** COMMENT
**Confidence:** low

### Summary
${SUMMARY}

### Blocking
- ${BLOCKING}

### Suggestions
- None

### Nits
- None

### Tests & risk
- Coverage: n/a
- Risk: n/a
- Rollback: n/a

### What I checked
- Failure path only

---
*Torii · Hermes Agent · OpenRouter · memory-backed review*
EOF

echo "$OUT"
