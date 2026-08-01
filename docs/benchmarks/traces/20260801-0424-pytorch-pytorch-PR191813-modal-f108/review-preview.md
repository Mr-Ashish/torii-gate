<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 1/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
Adds a `const at::Tensor&` overload of `isFwGradDefined` that skips an unnecessary `std::optional<Tensor>` construction when callers already hold a concrete `Tensor`. The existing `optional` overload is refactored to delegate to the new one. Well-scoped, minimal diff (+5/−1), preserves semantics fully.

### Walkthrough
- `torch/csrc/autograd/functions/utils.h:94` — new `isFwGradDefined(const at::Tensor&)` overload: same logic as before (`t.defined() && t._fw_grad(0).defined()`) without the optional wrapper.
- `torch/csrc/autograd/functions/utils.h:98` — existing `optional<Tensor>&` overload now delegates to the new `Tensor&` overload via `isFwGradDef
