# Robo-CFO — Task List

## Phase 1: Foundation (sequential → merge to main)

- [ ] T1: Project scaffolding (pyproject.toml, Vite, CI skeleton)
- [ ] T2: Tax tables data (2026.json + loader)
- [ ] T3: Synthetic fixture (sample_state.json + MarketAssumptions with per_class)
- [ ] **CHECKPOINT A** — merge to main; parallel workstreams unblock

## Phase 2: Tax Engine (worktree-tax-engine)

- [ ] T4: Regime 1 — `compute_irpf` (IRPF + Lei 15.270/2025 reducer, TDD golden tests first)
- [ ] T5: Regime 2 — `compute_variable_income` (monthly, loss carryforward, regime isolation)
- [ ] T6: Regime 3 — `compute_fixed_income_tax` + `compute_come_cotas`
- [ ] T7: Regime 4 — `compute_irpfm` + `compute_annual_tax` (annual facade / TaxFn)
- [ ] **CHECKPOINT B** — merge tax-engine; Monte Carlo + Optimizer swap stub → real TaxFn

## Phase 3: Monte Carlo + Optimizer (parallel workstreams)

- [ ] T8: `run_simulation` — path sampling, IPCA, per-class assumptions, np.random.default_rng  (worktree-monte-carlo)
- [ ] T9: Built-in strategy catalogue + `build_custom_strategy`  (worktree-optimizer)
- [ ] T10: `optimize()` — full evaluation per candidate, KeyDriver selection  (worktree-optimizer)
- [ ] **CHECKPOINT C** — merge both; integration test with real TaxFn

## Phase 4: API + Explanation (worktree-api)

- [ ] T11: FastAPI skeleton + disclaimer middleware + `GET /health`
- [ ] T12: Jinja2 explanation templates (Portuguese) + Claude opt-in path
- [ ] T13: `POST /simulate` + `POST /optimize` endpoints (Pydantic v2)
- [ ] T14: `POST /optimize/explain` endpoint + Anthropic SDK wiring
- [ ] **CHECKPOINT D** — merge api

## Phase 5: Frontend (worktree-frontend)

- [ ] T15: Vite + React + TS scaffolding + TanStack Query + typed API client
- [ ] T16: `FanChart` component (Recharts p10/p50/p90)
- [ ] T17: `StrategyComparison` + `ExplanationCard` + `Disclaimer`
- [ ] T18: `Home` + `Results` pages
- [ ] **CHECKPOINT E** — merge frontend

## Phase 6: Integration + Ship

- [ ] T19: Docker Compose (backend + frontend, nginx proxy, .env)
- [ ] T20: GitHub Actions CI (4 parallel jobs, coverage gate)
- [ ] T21: README with disclaimer + architecture diagram
- [ ] **CHECKPOINT F** — all SPEC.md success criteria met
