<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 2/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
Adds an `isFwGradDefined(const at::Tensor&)` overload that avoids constructing `std::optional<at::Tensor>` on every call site that already holds a `Tensor`. The original `optional<Tensor>` overload now delegates to the new one after its `has_value()` guard. Semantically equivalent, zero behavioral change — a clean inline optimization that eliminates redundant optional wrapping on a hot autograd path.

### Walkthrough
- `torch/csrc/autograd/functions/utils.h:94` — new `isFwGradDefined(const at::Tensor& t)` overload: directly checks `t.defined()` and `t._fw_grad(0).defined()`, matching the old body exactly.
- `torch/csrc/autograd/functions/utils.h:98-9
