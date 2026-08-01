<!-- torii-review pr=191813 run=local head=eac6610a25d790595c55e5b9ff1ec74a2b2170d9 -->
## 🏴‍☠️ Torii Review — PR #191813

**Verdict:** COMMENT
**Confidence:** high
**Score:** 93/100
**Review effort:** 2/5

### Summary
Adds a `const at::Tensor&` overload of `isFwGradDefined` to avoid implicit `std::optional<Tensor>` construction at call sites that pass concrete Tensors. The existing optional overload now delegates to the new one. The change is pure optimization with identical semantics — a 5-line additive change with no behavioral risk.

### Walkthrough
- **`torch/csrc/autograd/functions/utils.h:94-96`** — New `isFwGradDefined(const at::Tensor& t)` overload: checks `t.defined()` then `t._fw_grad(0).defined()`. Semantically identical to the optional path when the optional is occupied.
- **`torch/csrc/autograd/functions/utils.h:98-99`** — Optional overload now delegates: `t.has_value() && isFwGradDefined(t.value())`. Safe because short-circuit `&&` prevents `value()` on empty optional.
- Existing callers in `isFwGradDefinedTensorList` (line 105, iterating `ITensorListRef` where elements are Tensors) and all generated `VariableType*.cpp` callers automatically pick up the new overload
