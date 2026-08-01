<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 1/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
Adds a non-optional overload of `isFwGradDefined(const at::Tensor&)` so callers passing a plain `Tensor` (common in generated `VariableType*.cpp`) skip the `optional<Tensor>` constructor. The original `optional<Tensor>` overload now delegates to the new one. Change is mechanical, header-only, and preserves existing signatures — no ABI break, no behavioral change.

### Walkthrough
- **New overload** `isFwGradDefined(const at::Tensor&)` at `torch/csrc/autograd/functions/utils.h:94`: does `t.defined() && t._fw_grad(0).defined()` — identical logic sans the `optional` wrapper.
- **Refactored overload** `isFwGradDefined(const std::optional<at::Tensor>&)` a
