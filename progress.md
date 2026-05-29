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

## API workstream (Phase 3–5)
- [api] T11: FastAPI skeleton — CORS, disclaimer middleware, GET /health — 6 tests (async httpx transport)
- [api] T12: Explanation renderer — Jinja2 template + DeepSeek LLM path, all 8 KeyDriver Portuguese labels — 12 tests
- [api] T13: POST /simulate + POST /optimize — Pydantic v2 request/response models, stub implementations — 9 tests
- [api] T14: POST /optimize/explain — routes to render_explanation, 503 on missing LLM config — 7 tests

## Parallel workstreams (Phase 3–5)
- [optimizer] T9: BUILTIN_STRATEGIES (5 strategies) + build_custom_strategy — 10 tests
- [optimizer] T10: optimize() — full candidate evaluation, rank by objective, Explanation with key_drivers — 17 tests
- [monte-carlo] T8: run_simulation — 11 tests green
- [monte-carlo] T8: run_simulation — 11 invariant tests, vectorised numpy, seed reproducibility verified
- [optimizer] T10: optimize() — full evaluation per candidate, KeyDriver selection — 43 tests
- [frontend] T15-T18: types + hooks + FanChart + StrategyComparison + ExplanationCard + Home + Results — 14 tests, build clean
- [api] T11: FastAPI skeleton — CORS, disclaimer middleware, GET /health
- [api] T12: Jinja2 explanation templates + DeepSeek LLM path — 13 tests
- [api] T13: POST /simulate + POST /optimize endpoints — 9 tests
- [api] T14: POST /optimize/explain — 7 tests, 503 on missing config
- [api] T11-T14 CHECKPOINT D ready: 123 tests pass (1 skipped LLM), ruff+mypy clean; httpx.AsyncClient transport for latin-1 disclaimer header
