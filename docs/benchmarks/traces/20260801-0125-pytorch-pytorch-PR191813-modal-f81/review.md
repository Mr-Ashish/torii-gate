<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 2/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
Adds a `const at::Tensor&` overload of `isFwGradDefined` to avoid constructing temporary `std::optional<at::Tensor>` objects at call sites that already hold a plain `Tensor`. The existing `optional` overload now delegates to the new one, preserving exact semantics while eliminating the overhead. A clean, backward-compatible micro-optimization with no behavioral change.

### Walkthrough
- **New overload** `torch/csrc/autograd/functions/utils.h:94`: `isFwGradDefined(const at::Tensor&)` — directly checks `t.defined() && t._fw_grad(0).defined()`, skipping the `optional` wrapper.
- **Delegation** `torch/csrc/autograd/functions/utils.h:98-99`: existing `op
