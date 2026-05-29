# Implementation Plan: Robo-CFO (Brazil)

## Overview

Educational personal-finance decision simulator for Brazilian taxpayers. A FastAPI backend
implements four parallel Brazilian federal tax regimes, a Monte Carlo simulator (path-based,
IPCA inflation), and a strategy optimizer. A React + TypeScript frontend renders fan charts,
strategy comparisons, and LLM-elaborated explanations. All deployed via Docker Compose with
GitHub Actions CI.

The core constraint: `contracts.py` is frozen. Every workstream imports from it; none modifies it.

---

## Dependency Graph

```
contracts.py (frozen)
        │
        ▼
 PHASE 1 — FOUNDATION (sequential, merge to main)
 ┌─────────────────────────────────────────────┐
 │ T1: Project scaffolding                     │
 │ T2: Tax tables data (2026.json + loader)    │
 │ T3: Synthetic fixture (sample_state.json)   │
 └──────────────────┬──────────────────────────┘
                    │ CHECKPOINT A — merge to main
         ┌──────────┴──────────────────────────────┐
         │                                          │
         ▼                                          ▼
 PHASE 2 — TAX ENGINE          PHASES 3–5 (parallel, stub TaxFn)
 worktree-tax-engine            worktree-monte-carlo
 ┌────────────────┐             worktree-optimizer
 │ T4: IRPF       │             worktree-api
 │ T5: Var income │             worktree-frontend
 │ T6: Fixed inc  │
 │ T7: IRPFM +    │
 │     annual     │
 └───────┬────────┘
         │ CHECKPOINT B — merge tax-engine to main
         │ (Monte Carlo + Optimizer swap stub → real TaxFn here)
         │
         ▼
 PHASE 6 — INTEGRATION + SHIP (sequential)
 T19: Docker Compose
 T20: GitHub Actions CI
 T21: README + disclaimer
         │ CHECKPOINT F — all success criteria met
```

---

## Architecture Decisions

- **Four separate tax functions, not one** — Brazilian regimes are parallel, not stacked.
  `compute_annual_tax` is the facade that orchestrates them; it's the `TaxFn` injected everywhere.
- **TaxFn as a Protocol** — Monte Carlo and Optimizer code against the interface and swap in a stub
  until the real engine lands on main. Zero coupling between workstreams.
- **NumPy only in Monte Carlo** — the tax hot path is pure Python; NumPy is used only for sampling
  paths and computing percentiles. `np.random.default_rng(seed)` (not legacy global seed).
- **Pydantic v2 for API I/O** — contracts types are frozen dataclasses; Pydantic models mirror them
  at the API boundary. Any drift between them is caught by integration tests.
- **Jinja2 templates are the default** — LLM path is opt-in per request; templates are always
  available and have zero latency. LLM only elaborates; never computes.

---

## Phase 1: Foundation

> **Single session. Merge to main before any parallel work starts.**
> All subsequent workstreams depend on this scaffolding and data.

---

### Task 1: Project scaffolding

**Description:** Set up the monorepo layout, Python toolchain (ruff, mypy, pytest), Vite + React
skeleton, and the basic CI skeleton file. No business logic yet — just a green, lint-clean, type-clean
repo that every workstream can branch from.

**Acceptance criteria:**
- [ ] `backend/` has `pyproject.toml` with ruff, mypy (strict), pytest, uvicorn, fastapi, pydantic v2 dependencies
- [ ] `frontend/` has `package.json` with React 18, TypeScript 5, Vite, Recharts, TanStack Query, Vitest
- [ ] `cd backend && ruff check .` exits 0
- [ ] `cd backend && mypy app/` exits 0 (app/ contains only `__init__.py` at this point)
- [ ] `cd frontend && npm run build` exits 0
- [ ] `.github/workflows/ci.yml` skeleton exists with jobs: `backend-lint`, `backend-test`, `frontend-lint`, `frontend-test`

**Verification:**
- [ ] `cd backend && ruff check . && mypy app/`
- [ ] `cd frontend && npm run build && npm test`

**Dependencies:** None

**Files:**
- `backend/pyproject.toml`, `backend/app/__init__.py`
- `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`
- `frontend/src/main.tsx`, `frontend/src/App.tsx` (stub)
- `.github/workflows/ci.yml`

**Scope:** M (5 files, pure config)

---

### Task 2: Tax tables data file + loader

**Description:** Write `backend/app/data/tax_tables/2026.json` containing the full `TaxTables` for
calendar year 2026 (Lei 15.270/2025 in effect), and a `load_tax_tables(year)` function that
deserialises it into a `TaxTables` dataclass. This is the "data, not code" rule materialised.

**Acceptance criteria:**
- [ ] `2026.json` contains all fields of `TaxTables`: IRPF monthly/annual brackets, exemption limits,
  dependent deduction, simplified discount cap, variable income rates, regressive bands, come-cotas rate,
  dividend threshold, IRPFM floor/ceiling/rate
- [ ] `load_tax_tables(2026)` returns a `TaxTables` instance that round-trips (serialise → deserialise)
- [ ] `load_tax_tables(9999)` raises `FileNotFoundError` (no silent fallback)
- [ ] Golden values verified against Receita Federal sources:
  - `irpf_exemption_limit_monthly == 5000.00`
  - `irpf_reduction_upper_limit_monthly == 7350.00`
  - `equity_monthly_exemption == 20000.00`
  - `irpfm_income_floor_annual == 600000.00`

**Verification:**
- [ ] `pytest tests/data/test_tax_tables.py -v`

**Dependencies:** T1

**Files:**
- `backend/app/data/tax_tables/2026.json`
- `backend/app/data/loader.py`
- `backend/tests/data/test_tax_tables.py`

**Scope:** S

---

### Task 3: Synthetic fixture

**Description:** Write `sample_state.json` — a realistic synthetic `FinancialState` for a
35-year-old Brazilian professional: mixed holdings (stocks, CDB, LCI, FII), one debt, salary +
dividend income, and a retirement goal. Also write `load_fixture(name)` and a `MarketAssumptions`
fixture with per-class overrides. This is the dev/demo input for every workstream.

**Acceptance criteria:**
- [ ] `load_fixture("sample_state")` returns a valid `FinancialState` (mypy-clean)
- [ ] The fixture includes at least one holding of each major `AssetClass`
  (STOCKS, TAXABLE_FIXED_INCOME, EXEMPT_FIXED_INCOME, FII)
- [ ] The fixture includes a `MarketAssumptions` with `per_class` overrides for STOCKS and TAXABLE_FIXED_INCOME
- [ ] `SimulationConfig(years=30, n_paths=100, seed=42)` is included as the dev config

**Verification:**
- [ ] `pytest tests/data/test_fixtures.py -v`
- [ ] `python -c "from app.data.loader import load_fixture; s = load_fixture('sample_state'); print(s.taxpayer.age)"` prints `35`

**Dependencies:** T1

**Files:**
- `backend/app/data/fixtures/sample_state.json`
- `backend/app/data/fixtures/market_assumptions.json`
- `backend/app/data/loader.py` (extended)
- `backend/tests/data/test_fixtures.py`

**Scope:** S

---

### Checkpoint A — Foundation complete

- [ ] `pytest tests/data/` all green
- [ ] `ruff check . && mypy app/` clean
- [ ] **Merge to `main`** — this is the baseline all parallel workstreams branch from
- [ ] All parallel workstreams (tax-engine, monte-carlo, optimizer, api, frontend) may now start

---

## Phase 2: Tax Engine

> **One worktree (`worktree-tax-engine`). Sequential within — each regime's golden tests must
> pass before the next regime starts. Merge to `main` as Checkpoint B.**
>
> Other workstreams start in parallel against the `TaxFn` stub.

---

### Task 4: Regime 1 — `compute_irpf`

**Description:** Implement `compute_irpf` from `contracts.py`. Apply the 2026 progressive table,
pick simplified vs complete (whichever is cheaper), and apply the Lei 15.270/2025 reducer
month by month. Golden tests first, then implementation (TDD).

**Acceptance criteria:**
- [ ] Monthly income = R$4,999/month (all 12) → `tax_due == 0.00`, `reduction_applied > 0`
- [ ] Monthly income = R$7,351/month (all 12) → `reduction_applied == 0.00` (above reducer ceiling)
- [ ] Monthly income = R$0 → `effective_rate == 0.0`
- [ ] `model_used` is always the one with lower `tax_due`
- [ ] `effective_rate == round(tax_due / sum(monthly_taxable_income) * 12, 6)` (or 0 if income = 0)
- [ ] `tax_due` is never negative
- [ ] `mypy` clean, `ruff` clean

**Verification:**
- [ ] `pytest tests/tax/test_irpf.py -v` (all golden tests pass)
- [ ] `pytest --cov=app/tax/irpf tests/tax/test_irpf.py` coverage ≥ 90%

**Dependencies:** T2 (needs `TaxTables` for 2026)

**Files:**
- `backend/app/tax/irpf.py`
- `backend/tests/tax/test_irpf.py`

**Scope:** M

---

### Task 5: Regime 2 — `compute_variable_income`

**Description:** Implement `compute_variable_income`. Month-by-month: swing exempt when
`swing_sales_total ≤ R$20k`, 15% otherwise; day trade 20%; FII 20%. Loss carryforward stays
within the variable income regime — it must NOT reduce IRPF.

**Acceptance criteria:**
- [ ] Swing month with `swing_sales_total = 19_999` → `tax_due == 0.00`, `exemption_applied == True`
- [ ] Swing month with `swing_sales_total = 20_001` and `swing_gain = 5_000` → `tax_due == 750.00`
- [ ] Loss in month 1 offsets gain in month 2 within the same call
- [ ] Loss carryforward propagates: `loss_carryforward_out > 0` when total losses exceed total gains
- [ ] A loss in this regime does NOT appear in `IRPFResult.tax_due` (isolation test)

**Verification:**
- [ ] `pytest tests/tax/test_variable_income.py -v`

**Dependencies:** T2, T4 (understand regime isolation before implementing)

**Files:**
- `backend/app/tax/variable_income.py`
- `backend/tests/tax/test_variable_income.py`

**Scope:** M

---

### Task 6: Regime 3 — `compute_fixed_income_tax` + `compute_come_cotas`

**Description:** Implement the regressive table (22.5% → 15% by `days_held`) and come-cotas
(semiannual prepayment on open funds). Exempt classes return 0. `EQUITY_FUND` uses the flat rate.

**Acceptance criteria:**
- [ ] `days_held = 180` → 22.5% (first band)
- [ ] `days_held = 181` → 20% (second band)
- [ ] `days_held = 721` → 15% (final band)
- [ ] `AssetClass.EXEMPT_FIXED_INCOME` → `tax == 0.00`
- [ ] `AssetClass.SAVINGS` → `tax == 0.00`
- [ ] `AssetClass.EQUITY_FUND` → `tax == gain * equity_fund_rate`
- [ ] `compute_come_cotas(gain=1000, tables)` returns `gain * come_cotas_rate`

**Verification:**
- [ ] `pytest tests/tax/test_fixed_income.py -v`

**Dependencies:** T2

**Files:**
- `backend/app/tax/fixed_income.py`
- `backend/tests/tax/test_fixed_income.py`

**Scope:** S

---

### Task 7: Regime 4 + annual facade — `compute_irpfm` + `compute_annual_tax`

**Description:** Implement `compute_irpfm` (top-up only, never negative; base includes exempt
income) and `compute_annual_tax` (orchestrates all four regimes). Lock the `total_tax` invariant
as a golden test. This function becomes the `TaxFn` injected into the simulator.

**Acceptance criteria:**
- [ ] `total_annual_income = 500_000` → `compute_irpfm` returns `0.00` (below floor)
- [ ] `total_annual_income = 900_000, tax_already_assessed = 0` → returns the IRPFM amount, > 0
- [ ] `compute_irpfm` never returns a negative value
- [ ] `compute_annual_tax` invariant: `total_tax == irpf.tax_due + variable_income_tax + fixed_income_tax + dividend_withholding + irpfm_additional` to within R$0.01 for 5 scenario fixtures
- [ ] `compute_annual_tax` satisfies the `TaxFn` Protocol (mypy verifies this)

**Verification:**
- [ ] `pytest tests/tax/test_irpfm.py tests/tax/test_annual.py -v`
- [ ] `mypy app/tax/annual.py` exits 0

**Dependencies:** T4, T5, T6

**Files:**
- `backend/app/tax/irpfm.py`
- `backend/app/tax/annual.py`
- `backend/tests/tax/test_irpfm.py`
- `backend/tests/tax/test_annual.py`

**Scope:** M

---

### Checkpoint B — Tax engine complete

- [ ] All tax tests green: `pytest tests/tax/ -v`
- [ ] Coverage ≥ 90% on `app/tax/`: `pytest --cov=app/tax tests/tax/`
- [ ] `ruff check . && mypy app/` clean
- [ ] **Merge `worktree-tax-engine` to `main`**
- [ ] Monte Carlo and Optimizer workstreams swap their stub `TaxFn` for the real `compute_annual_tax`

---

## Phase 3: Monte Carlo + Optimizer

> **Two parallel worktrees. Both stub `TaxFn` with a zero-returning fake until Checkpoint B
> merges. After the swap, integration tests run with the real tax engine.**

### ⚠️ CROSS-DEPENDENCY WARNING
`optimize()` calls `run_simulation()` — these two workstreams share a function call. Define
the `run_simulation` signature (already in `contracts.py`) carefully. When merging, the
optimizer's stub `run_simulation` must be replaced by the real one. Run integration tests
immediately after both branches merge.

---

### Task 8: Monte Carlo — `run_simulation`

**Description:** Implement `run_simulation`. Sample `n_paths` return paths using
`np.random.default_rng(seed)`. Apply per-asset-class return assumptions (fallback to global if
not in `per_class`). Model IPCA stochastically. Call `tax_fn` once per year per path. Compute
`YearPercentiles` (p10/p50/p90) at each year and terminal wealth. `success_probability` =
fraction of paths where terminal wealth ≥ sum of goal `target_amount`s.

**Acceptance criteria:**
- [ ] `terminal_p10 < terminal_p50 < terminal_p90` for any realistic scenario
- [ ] `0.0 <= success_probability <= 1.0`
- [ ] With `seed=42`, result is identical across two calls (determinism)
- [ ] Zero-volatility scenario (all `return_volatility=0.0`): p10 == p50 == p90 (within R$0.01)
- [ ] `paths_simulated == config.n_paths`
- [ ] Per-class override applies: STOCKS path uses its own `mean_real_return`, not the global one
- [ ] `n_paths=10_000` with the sample fixture completes in < 3s on a laptop CPU

**Verification:**
- [ ] `pytest tests/simulation/test_monte_carlo.py -v`
- [ ] `python -c "from app.simulation.monte_carlo import run_simulation; ..."` timing check

**Dependencies:** T1 (scaffold), T3 (fixture) — uses stub TaxFn until T7 merges

**Files:**
- `backend/app/simulation/monte_carlo.py`
- `backend/tests/simulation/test_monte_carlo.py`

**Scope:** M

---

### Task 9: Built-in strategy catalogue

**Description:** Define the pre-built `Strategy` objects and a `CustomStrategy` builder. The
catalogue is a simple module-level tuple of `Strategy` instances. The builder accepts allocation
fractions and debt-payoff priority and returns a `Strategy` with `id="custom"`.

**Acceptance criteria:**
- [ ] `BUILTIN_STRATEGIES` contains exactly 5 strategies (matches SPEC.md list)
- [ ] Each strategy has a unique `id`, a Portuguese `name`, and a one-sentence `description`
- [ ] `build_custom_strategy(debt_fraction=0.5, invest_asset_class=AssetClass.TAXABLE_FIXED_INCOME)`
  returns a `Strategy` with `id="custom"`
- [ ] `id` values are stable strings (used as keys in `Explanation.winner_id`)

**Verification:**
- [ ] `pytest tests/optimizer/test_strategies.py -v`

**Dependencies:** T1

**Files:**
- `backend/app/optimizer/strategies.py`
- `backend/tests/optimizer/test_strategies.py`

**Scope:** XS

---

### Task 10: Optimizer — `optimize()`

**Description:** Implement `optimize()`. For each candidate `Strategy`, call `run_simulation`
(injected — stub until Phase 2 merges), collect `StrategyOutcome`, rank by `objective`. Build
the `Explanation` by comparing winner vs runner-up and selecting `KeyDriver` values. The tax
cost curve is non-monotonic — ranking must come from full evaluation, never gradient assumptions.

**Acceptance criteria:**
- [ ] With 2 strategies, the winner is the one with the better `objective` metric
- [ ] `ranked[0]` is always the strategy with the best metric; `ranked[-1]` is the worst
- [ ] `explanation.winner_id == ranked[0].strategy.id`
- [ ] `explanation.delta_vs_runner_up == ranked[0].result.terminal_p50 - ranked[1].result.terminal_p50`
  (for `MAX_MEDIAN_NET_WORTH` objective)
- [ ] `explanation.key_drivers` contains at least one `KeyDriver` value
- [ ] With stub `tax_fn`, result is deterministic for fixed seed

**Verification:**
- [ ] `pytest tests/optimizer/test_optimizer.py -v`

**Dependencies:** T8 (calls run_simulation), T9

**Files:**
- `backend/app/optimizer/engine.py`
- `backend/tests/optimizer/test_optimizer.py`

**Scope:** M

---

### Checkpoint C — Simulation + Optimizer complete

- [ ] `pytest tests/simulation/ tests/optimizer/ -v` all green
- [ ] After Checkpoint B merge: swap stub TaxFn → real `compute_annual_tax` in both workstreams
- [ ] Integration test: `optimize()` with real `tax_fn` and sample fixture produces a `Recommendation`
- [ ] Merge `worktree-monte-carlo` and `worktree-optimizer` to `main`

---

## Phase 4: API + Explanation

> **One worktree (`worktree-api`). Can start from Checkpoint A with stub simulation output.
> Wires to real engines after Checkpoint C.**

---

### Task 11: FastAPI app skeleton + disclaimer middleware

**Description:** Create `app/main.py` with CORS configured for the frontend dev origin, and a
middleware that injects `X-Robo-CFO-Disclaimer` on every response. Add a `GET /health` endpoint.

**Acceptance criteria:**
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] Every response includes header `X-Robo-CFO-Disclaimer: Este sistema é um simulador educacional. Não constitui assessoria financeira.`
- [ ] CORS allows `http://localhost:5173` (Vite dev) and `http://localhost:3000`
- [ ] `mypy app/main.py` clean

**Verification:**
- [ ] `pytest tests/api/test_health.py -v`
- [ ] `curl -I http://localhost:8000/health` shows the disclaimer header

**Dependencies:** T1

**Files:**
- `backend/app/main.py`
- `backend/tests/api/test_health.py`

**Scope:** S

---

### Task 12: Jinja2 explanation templates (Portuguese)

**Description:** Write `render_explanation(explanation: Explanation, use_llm: bool = False) -> str`.
When `use_llm=False`: Jinja2 template that produces a 2–3 sentence Portuguese narrative from the
structured fields. When `use_llm=True`: send `Explanation` struct + template output as context to
Claude; the LLM may only elaborate, not recompute. Load `ANTHROPIC_API_KEY` from environment.

**Acceptance criteria:**
- [ ] `render_explanation(explanation, use_llm=False)` returns a non-empty Portuguese string with
  no computation (all numbers come from the `Explanation` struct)
- [ ] The template renders each of the 8 `KeyDriver` values to a Portuguese label (smoke test all 8)
- [ ] `render_explanation(explanation, use_llm=True)` calls the Anthropic SDK; if
  `ANTHROPIC_API_KEY` is not set, raises `EnvironmentError` with a clear message
- [ ] The LLM prompt explicitly instructs the model NOT to recompute numbers

**Verification:**
- [ ] `pytest tests/explanation/test_renderer.py -v` (LLM test skipped if no API key)
- [ ] Template output for a known `Explanation` fixture matches expected Portuguese text (snapshot)

**Dependencies:** T1

**Files:**
- `backend/app/explanation/renderer.py`
- `backend/app/explanation/templates/recommendation.j2`
- `backend/tests/explanation/test_renderer.py`

**Scope:** M

---

### Task 13: `/simulate` and `/optimize` endpoints

**Description:** Wire up `POST /simulate` and `POST /optimize`. Pydantic v2 models mirror the
contracts types at the API boundary. Both endpoints call the real engines after Checkpoint C;
until then, they call stubs that return valid-shaped responses.

**Acceptance criteria:**
- [ ] `POST /simulate` with valid body returns `SimulationResult`-shaped JSON (200)
- [ ] `POST /optimize` with valid body returns `Recommendation`-shaped JSON (200)
- [ ] Invalid body (missing required field) returns 422 with detail
- [ ] Both responses include the disclaimer header (from T11 middleware)
- [ ] Pydantic models are mypy-clean

**Verification:**
- [ ] `pytest tests/api/test_endpoints.py -v`

**Dependencies:** T11, T8 (or stub), T10 (or stub)

**Files:**
- `backend/app/routers/simulate.py`
- `backend/app/routers/optimize.py`
- `backend/tests/api/test_endpoints.py`

**Scope:** M

---

### Task 14: `/optimize/explain` endpoint + Claude integration

**Description:** `POST /optimize/explain` calls `render_explanation`. When `use_llm=true` in the
body, the Claude API is called. The response is `{ "text": "<narrative>" }`.

**Acceptance criteria:**
- [ ] `use_llm=false` returns template text synchronously (< 50ms)
- [ ] `use_llm=true` with a valid API key returns a longer Portuguese elaboration
- [ ] `use_llm=true` without `ANTHROPIC_API_KEY` returns 503 with a clear error message
- [ ] The LLM response never introduces numbers not present in the `Explanation` struct
  (checked by asserting that all numbers in the response appear in the input)

**Verification:**
- [ ] `pytest tests/api/test_explain.py -v` (LLM path skipped without API key)

**Dependencies:** T12, T13

**Files:**
- `backend/app/routers/optimize.py` (extended)
- `backend/tests/api/test_explain.py`

**Scope:** S

---

### Checkpoint D — API complete

- [ ] `pytest tests/api/ tests/explanation/ -v` all green
- [ ] `ruff check . && mypy app/` clean
- [ ] Integration test: sample fixture → `POST /optimize` → valid `Recommendation` JSON
- [ ] Merge `worktree-api` to `main`

---

## Phase 5: Frontend

> **Worktree `worktree-frontend`. Can mock API responses throughout. Integrates with real API
> after Checkpoint D.**

### ⚠️ CROSS-DEPENDENCY WARNING
The frontend API client (`client.ts`) is typed against the JSON shapes from the API. If the
Pydantic models in the API workstream drift from the contract types, the TypeScript types will
disagree silently. After both workstreams merge, run an end-to-end smoke test immediately.

---

### Task 15: Vite + React + TypeScript scaffolding + API client

**Description:** Set up `frontend/` with React 18, TypeScript 5, Vite, TanStack Query, and
Recharts. Write `api/client.ts` with typed fetch wrappers for all three endpoints. Use mock
handlers (MSW or simple stubs) for dev against the fixture shape.

**Acceptance criteria:**
- [ ] `npm run dev` starts the app on port 5173 with no errors
- [ ] `npm run build` produces a production build
- [ ] `client.ts` exports `useSimulate`, `useOptimize`, `useExplain` TanStack Query hooks
- [ ] TypeScript types in `client.ts` match the contract shapes exactly (no `any`)
- [ ] `npm test` exits 0

**Dependencies:** T1

**Files:**
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/main.tsx`, `frontend/src/App.tsx`

**Scope:** M

---

### Task 16: `FanChart` component

**Description:** Recharts area chart showing three lines (p10, p50, p90) over years.
X-axis = year, Y-axis = BRL (formatted as `R$ X.XXX`). Responsive container.

**Acceptance criteria:**
- [ ] Renders with mock `SimulationResult` without errors
- [ ] Three distinct line/area series visible: p10 (red), p50 (green), p90 (blue)
- [ ] X-axis labels are years; Y-axis labels are BRL-formatted
- [ ] Vitest snapshot test passes

**Verification:**
- [ ] `npm test` — snapshot + render test

**Dependencies:** T15

**Files:**
- `frontend/src/components/FanChart.tsx`
- `frontend/src/__tests__/FanChart.test.tsx`

**Scope:** S

---

### Task 17: `StrategyComparison` + `ExplanationCard`

**Description:** `StrategyComparison` shows a ranked table of strategies with their p50 terminal
wealth. `ExplanationCard` renders the template text and a "Explicar mais" button that calls
`useExplain` with `use_llm=true`.

**Acceptance criteria:**
- [ ] `StrategyComparison` renders top strategy highlighted (first row)
- [ ] `ExplanationCard` shows template text by default
- [ ] "Explicar mais" button triggers the LLM endpoint call; shows loading state; renders result
- [ ] `Disclaimer` component is always visible above the explanation
- [ ] Vitest snapshot tests for both components

**Verification:**
- [ ] `npm test`

**Dependencies:** T15

**Files:**
- `frontend/src/components/StrategyComparison.tsx`
- `frontend/src/components/ExplanationCard.tsx`
- `frontend/src/components/Disclaimer.tsx`
- `frontend/src/__tests__/StrategyComparison.test.tsx`
- `frontend/src/__tests__/ExplanationCard.test.tsx`

**Scope:** M

---

### Task 18: Home + Results pages

**Description:** `Home.tsx` — pre-loads the sample fixture and shows a brief form (only
`SimulationConfig.years` is editable for now; financial state comes from the fixture). On submit,
calls `useOptimize` and navigates to `Results.tsx`. `Results.tsx` — renders `FanChart`,
`StrategyComparison`, and `ExplanationCard` side by side. Disclaimer always visible.

**Acceptance criteria:**
- [ ] Submitting the form with years=30 calls `POST /optimize` (or the mock)
- [ ] Results page renders fan chart + strategy table + explanation without errors
- [ ] Disclaimer is visible on both pages
- [ ] `npm run build` clean

**Verification:**
- [ ] `npm test` — page-level render tests

**Dependencies:** T15, T16, T17

**Files:**
- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/Results.tsx`
- `frontend/src/__tests__/Home.test.tsx`

**Scope:** M

---

### Checkpoint E — Frontend complete

- [ ] `npm run build` clean, `npm test` green
- [ ] End-to-end manual check: `docker compose up`, submit form, fan chart renders
- [ ] Merge `worktree-frontend` to `main`

---

## Phase 6: Integration + Ship

> **Sequential. Run after all workstreams have merged.**

---

### Task 19: Docker Compose

**Description:** `docker-compose.yml` with two services: `backend` (FastAPI on port 8000) and
`frontend` (Vite production build served by nginx on port 80). Backend reads `ANTHROPIC_API_KEY`
from `.env`. Frontend container proxies `/api` to the backend.

**Acceptance criteria:**
- [ ] `docker compose up --build` starts both services in < 60s
- [ ] `curl http://localhost:80` returns the React app
- [ ] `curl http://localhost:80/api/health` returns `{"status": "ok"}` (proxied)
- [ ] `ANTHROPIC_API_KEY` is read from `.env` (not hardcoded)

**Verification:**
- [ ] `docker compose up --build && curl http://localhost:80/api/health`

**Dependencies:** All prior phases

**Files:**
- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `.env.example`

**Scope:** M

---

### Task 20: GitHub Actions CI

**Description:** Complete the CI pipeline from Task 1's skeleton. Four jobs run in parallel:
`backend-lint` (ruff + mypy), `backend-test` (pytest --cov), `frontend-lint` (eslint + tsc),
`frontend-test` (vitest). Coverage gate: backend ≥ 80%.

**Acceptance criteria:**
- [ ] All four jobs run on every push and PR
- [ ] CI fails if backend coverage < 80%
- [ ] `ANTHROPIC_API_KEY` is not required for CI (LLM tests are skipped gracefully)
- [ ] CI passes on a clean checkout with no local changes

**Verification:**
- [ ] Push to a branch and confirm all CI jobs pass in GitHub

**Dependencies:** T1 (CI skeleton), T19

**Files:**
- `.github/workflows/ci.yml` (completed)

**Scope:** S

---

### Task 21: README + disclaimer

**Description:** `README.md` with: project description (educational simulator, NOT financial
advice — prominent), setup instructions (`docker compose up`), architecture diagram (ASCII),
and a note on the frozen contracts pattern.

**Acceptance criteria:**
- [ ] Disclaimer appears in the first 10 lines of the README
- [ ] `docker compose up` instructions are correct and tested
- [ ] The four tax regimes are briefly described

**Dependencies:** T19, T20

**Files:**
- `README.md`

**Scope:** XS

---

### Checkpoint F — Ship

- [ ] `docker compose up` → full stack working end-to-end
- [ ] `POST /optimize` with sample fixture returns in < 5s (10,000 paths, 30 years)
- [ ] Fan chart renders in browser
- [ ] "Explicar mais" returns narrative without recomputing numbers
- [ ] GitHub Actions CI passes on `main`
- [ ] All success criteria in SPEC.md checked off

---

## Parallelization Map

| Workstream | Worktree | Start after | Blocks on | Hidden merge risk |
|---|---|---|---|---|
| `tax-engine` | `worktree-tax-engine` | Checkpoint A | Checkpoint B | None — fully isolated |
| `monte-carlo` | `worktree-monte-carlo` | Checkpoint A | Checkpoint C | Must swap stub TaxFn for real after B |
| `optimizer` | `worktree-optimizer` | Checkpoint A | Checkpoint C | Calls `run_simulation` — integration test required |
| `api` | `worktree-api` | Checkpoint A | Checkpoint D | Pydantic shapes must match TypeScript types |
| `frontend` | `worktree-frontend` | Checkpoint A | Checkpoint E | TypeScript types vs API JSON shapes |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Monte Carlo hot path too slow (> 5s for 10k paths) | High | Profile early with `n_paths=100`; vectorise percentile computation with NumPy; tax pure-Python is the bottleneck — measure before optimising |
| Pydantic models drift from contracts types | High | Write a single `conftest.py` fixture that constructs each contracts type via the Pydantic model and asserts round-trip equality |
| IRPF reducer law interpretation error | High | Lock golden tests to Receita Federal published examples before implementation; document the source URL |
| NumPy version change breaks RNG determinism | Medium | Use `np.random.default_rng(seed)` (stable API); pin NumPy version in `pyproject.toml` |
| LLM recomputes numbers in explanation | Medium | The prompt explicitly prohibits it; the `test_explain.py` assertion checks that all numbers in the LLM output appear in the input struct |
| Optimizer/Monte Carlo integration after swap | Medium | Dedicated integration test in `tests/integration/test_full_pipeline.py` that runs with real TaxFn |
