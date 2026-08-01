<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 1/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
Adds an `isFwGradDefined(const at::Tensor& t)` overload to `torch/csrc/autograd/functions/utils.h`, avoiding unnecessary `optional<Tensor>` construction at every call site that already passes a concrete `Tensor`. The existing `optional` overload now delegates to the new one, eliminating the duplicated `_fw_grad` check. Microbenchmarks show 12–27% speedup on targeted autograd ops. No behavioral change; purely additive and refactoring.

### Walkthrough
- `torch/csrc/autograd/functions/utils.h:94` — new `isFwGradDefined(const at::Tensor& t)` overload checks `t.defined()` then `t._fw_grad(0).defined()`. Semantics identical to the engaged-optional path of
