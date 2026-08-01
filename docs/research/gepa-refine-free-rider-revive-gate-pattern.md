# F176 — free-rider multi-tenant dual_pass revive gate

## Sources
- **FederatedSkill** (arXiv 2606.03143): multi-tenant gates for promote *and* demote; recovery must multi-tenant gate free-rider re-boost.
- **GEPA** (arXiv 2507.19457): reflective evolution needs recoverability — but re-entry must not erase multi-tenant evidence.
- Torii F175: dual_pass local revive cleared `multi_tenant_decay` on single-tenant dual_pass → free-rider always re-boost.
- Hermes / SkillOpt: validation-gated recovery after reject.

## Insight
F175 closed decay→revive but local dual_pass free-rode multi-tenant demote. Highest ROI: sticky multi_tenant_decay until FederatedSkill promote; soft local boost only; critic demote free-rider APPROVE.

## Ship
- `refine_dual_revive_mt_gate_enabled` + ingest sticky flags (`local_revive_pending_mt`, `free_rider_revive_blocked`)
- router soft revive boost when free-rider; full supersede only on multi_tenant_revive
- prompt section free-rider line
- `f176_free_rider_revive` critic + demote-eval `free_rider_revive_idle_approve`
- hermes F176 notice; `free_rider_revive_ok`; `refine_loop_ok` AND F176
- fixture-refine-revive asserts free_rider_gate_ok then multi-tenant clear

## Metric
- Offline: free_rider_gate_ok + multi_ledger after promote; demote-eval free_rider_revive_idle_demoted
- Live: hermes F176 notice; refine_loop_ok
