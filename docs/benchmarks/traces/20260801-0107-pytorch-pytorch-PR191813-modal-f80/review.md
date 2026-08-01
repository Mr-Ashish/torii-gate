<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 2/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
This PR adds a new `isFwGradDefined(const at::Tensor&)` overload and refactors the existing `optional<Tensor>` overload to delegate to it. The change eliminates an unnecessary `std::optional<Tensor>` temporary construction on hot autograd paths where callers already hold a concrete `Tensor`. The refactoring is behavior-preserving, additive, and header-only — zero ABI risk.

### Walkthrough
- **`torch/csrc/autograd/functions/utils.h:94`** — New `inline` overload accepting `const at::Tensor&` directly, avoiding the `optional<Tensor>` ctor on the hot path.
- **`torch/csrc/autograd/functions/utils.h:98-99`** — Existing `optional<Tensor>` overload simplif
