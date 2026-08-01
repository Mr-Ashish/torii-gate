<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 1/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
This PR adds a `const at::Tensor&` overload of `isFwGradDefined` to avoid constructing `std::optional<at::Tensor>` on every call site that passes a plain `Tensor` (the common case). The existing `optional<Tensor>` overload is refactored to delegate to the new overload. Semantics are preserved; the change is a clean, low-risk optimization in a header-only inline function. No security or correctness concerns.

### Walkthrough
- `torch/csrc/autograd/functions/utils.h:93` — New overload `isFwGradDefined(const at::Tensor& t)` checks `t.defined()` then `t._fw_grad(0).defined()`, matching the old `optional` path's logic without the wrapper.
- `torch/csrc/au
