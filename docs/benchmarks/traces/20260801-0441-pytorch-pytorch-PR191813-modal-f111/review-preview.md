<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** REQUEST CHANGES
**Confidence:** medium
**Score:** 69/100
**Review effort:** 2/5

> ⚠️ **Severity calibration (F50 / H20):** Review self-reported a **test gap** while verdict was APPROVE (`approve_with_test_gap` · match=`tests_no_line`). Torii upgrades to **REQUEST CHANGES** — missing tests for new production behavior are blocking, not Suggestions. Signal: _Relevant tests added/updated: no_

### Summary
Adds an `isFwGradDefined(const at::Tensor&)` overload to eliminate unnecessary `optional<Tensor>` construction at call sites passing plain `Tensor` arguments. The existing `optional<Tensor>` overload is refactored to delegate to the new one. Behavior is strictly preserved; this is a header-only inline change with zero functional delta.

### Walkthrough
- `torch/csrc/autograd/functions/utils.h:93-95` — New `isFwGradDefined(const at::Tensor& t)` overload: checks `t.defined() && t._fw_grad(0).defined()`. Logically identical to the body previously inline in the optional overload.
- `torch/csrc/autograd/functions/utils.h:98-99` — Refactored optional overl
