<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 2/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
Adds an `isFwGradDefined(const at::Tensor&)` overload to avoid constructing a temporary `std::optional<at::Tensor>` at call sites that already have a concrete `Tensor`. The existing `optional` overload now delegates to the new one. Semantics are identical; the change is purely a call-path optimization. No behavior change, no ABI break (both are `inline`).

### Walkthrough
- `torch/csrc/autograd/functions/utils.h:94` — new `isFwGradDefined(const at::Tensor& t)` overload: directly checks `t.defined() && t._fw_grad(0).defined()`.
- `torch/csrc/autograd/functions/utils.h:99` — existing `optional<Tensor>` overload now delegates via `isFwGradDefined(t.valu
