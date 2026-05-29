# Progress log

Parallel workstreams append one line here after each committed slice.
Format: `[worktree] task: what was done`

## Foundation (main)
- [main] T1: project scaffolding — backend + frontend + CI skeleton
- [main] T2: tax tables 2026.json + loader — 12 golden tests
- [main] T3: synthetic fixture + loader — 14 tests
- [main] T4: compute_irpf + Lei 15.270/2025 reducer — 12 golden tests
- [main] T5: compute_variable_income — monthly, loss carryforward, regime isolation — 13 tests
- [main] T6: compute_fixed_income_tax + compute_come_cotas — regressive table — 15 tests
- [main] T7: compute_irpfm + compute_annual_tax (TaxFn facade) — total_tax invariant — 17 tests
- [main] CHECKPOINT B: 84 tests passing, tax engine complete

## Parallel workstreams (Phase 3–5)
