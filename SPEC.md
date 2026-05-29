# Spec: Robo-CFO (Brazil)

> **AVISO LEGAL / DISCLAIMER:** This is an educational simulator. It is NOT financial advice.
> Numbers are illustrative. Consult a qualified professional before making financial decisions.

---

## Objective

An educational personal-finance decision simulator for Brazilian taxpayers. Given a person's full
financial picture (holdings by asset class, debts, income streams, goals), the system evaluates
candidate strategies via Monte Carlo simulation, ranks them by a chosen objective, and explains
the reasoning with structured data rendered into narrative text.

**Core user questions answered:**
- "Should I pay down debt or invest?"
- "Am I on track to retire at age X?"
- "What is the most tax-efficient order to redeem my investments?"

**What success looks like:**
- A user inputs a synthetic financial state and receives a ranked strategy comparison with a
  Monte Carlo fan chart (p10/p50/p90 paths) and a human-readable explanation.
- The tax engine produces verifiably correct results for the four Brazilian federal tax regimes.
- The system runs end-to-end in `docker compose up` with zero manual steps.
- GitHub Actions CI passes on every push (lint, type-check, tests).

---

## Tech Stack

| Layer | Choice | Key libraries |
|---|---|---|
| Backend language | Python 3.12+ | stdlib, dataclasses, typing |
| API framework | FastAPI | uvicorn, Pydantic v2 |
| Tax / simulation core | Pure Python (no NumPy on the hot path) | `contracts.py` (frozen) |
| Explanation — fast path | Jinja2 templates (deterministic, Portuguese) | jinja2 |
| Explanation — opt-in | Claude API (Anthropic SDK) | anthropic |
| Frontend | React 18 + TypeScript 5 | Vite, Recharts, TanStack Query |
| Testing (backend) | pytest + pytest-cov | — |
| Testing (frontend) | Vitest + React Testing Library | — |
| CI | GitHub Actions | — |
| Containerization | Docker + Docker Compose | — |

---

## Commands

```bash
# Local dev (full stack)
docker compose up --build

# Backend only
cd backend && uvicorn app.main:app --reload --port 8000

# Backend tests
cd backend && pytest --cov=app tests/ -v

# Backend lint + type-check
cd backend && ruff check . && mypy app/

# Frontend dev
cd frontend && npm run dev

# Frontend tests
cd frontend && npm test

# Frontend build
cd frontend && npm run build

# Frontend lint
cd frontend && npm run lint
```

---

## Project Structure

```
robo-cfo/
├── contracts.py                  # FROZEN — single source of truth; no workstream modifies this
├── SPEC.md                       # this file
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml                # lint, type-check, test (backend + frontend)
│
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, disclaimer middleware
│   │   ├── routers/
│   │   │   ├── simulate.py       # POST /simulate
│   │   │   └── optimize.py       # POST /optimize
│   │   ├── tax/
│   │   │   ├── irpf.py           # Regime 1: compute_irpf
│   │   │   ├── variable_income.py # Regime 2: compute_variable_income
│   │   │   ├── fixed_income.py   # Regime 3: compute_fixed_income_tax, compute_come_cotas
│   │   │   ├── irpfm.py          # Regime 4: compute_irpfm
│   │   │   └── annual.py         # compute_annual_tax (the TaxFn facade)
│   │   ├── simulation/
│   │   │   └── monte_carlo.py    # run_simulation
│   │   ├── optimizer/
│   │   │   ├── strategies.py     # built-in Strategy catalogue
│   │   │   └── engine.py         # optimize()
│   │   ├── explanation/
│   │   │   ├── templates/        # Jinja2 .j2 templates (Portuguese)
│   │   │   └── renderer.py       # render_explanation(explanation, use_llm=False)
│   │   └── data/
│   │       ├── tax_tables/
│   │       │   └── 2026.json     # TaxTables for 2026 (Lei 15.270/2025 in effect)
│   │       └── fixtures/
│   │           └── sample_state.json  # synthetic FinancialState for dev/demo
│   └── tests/
│       ├── tax/
│       │   ├── test_irpf.py      # golden tests (see Testing Strategy)
│       │   ├── test_variable_income.py
│       │   ├── test_fixed_income.py
│       │   └── test_irpfm.py
│       ├── simulation/
│       │   └── test_monte_carlo.py
│       └── optimizer/
│           └── test_optimizer.py
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── Disclaimer.tsx    # always visible; required
    │   │   ├── StrategyComparison.tsx
    │   │   ├── FanChart.tsx      # Recharts: p10/p50/p90 paths
    │   │   └── ExplanationCard.tsx  # shows template text + "Explicar mais" LLM button
    │   ├── pages/
    │   │   ├── Home.tsx
    │   │   └── Results.tsx
    │   └── api/
    │       └── client.ts         # TanStack Query hooks for /simulate and /optimize
    ├── vite.config.ts
    └── package.json
```

---

## Frozen Contracts (`contracts.py`)

**No workstream may modify `contracts.py`.** It is the single source of truth for all parallel agents.

Key types every workstream depends on:

| Type | Purpose |
|---|---|
| `FinancialState` | Everything the person HAS (holdings, debts, income, goals) |
| `TaxTables` | All brackets/rates for one calendar year (data, not code) |
| `AnnualTaxScenario` / `AnnualTaxResult` | Input/output of `compute_annual_tax` |
| `TaxFn` | `Protocol` — injectable facade; simulator and optimizer test against a stub |
| `SimulationResult` | p10/p50/p90 paths + success probability |
| `Recommendation` / `Explanation` | Optimizer output; `Explanation` is structured data only |

---

## Tax Engine — Four Parallel Regimes

Brazilian investment taxation is **not stacked** on ordinary income. Each regime is independent:

### Regime 1 — IRPF (taxable income)
- Input: `IRPFScenario` (12 monthly income values, deductibles, dependents)
- Output: `IRPFResult`
- Lei 15.270/2025 reducer: full exemption up to R$5,000/month; linearly decreasing up to R$7,350/month
- Picks `simplified` vs `complete` declaration — whichever yields lower tax
- **Golden tests** (must pass before implementation is accepted):
  - Monthly income = R$4,999 → tax_due = R$0.00
  - Monthly income = R$7,351 → reduction_applied = R$0.00 (no reducer benefit)
  - effective_rate = tax_due / annual_income; 0 if income = 0

### Regime 2 — Variable income (monthly assessment)
- Input: `Sequence[MonthlyTrades]`, loss carryforward
- Output: `VariableIncomeResult`
- Swing: exempt if `swing_sales_total` ≤ R$20,000 in the month; else 15%
- Day trade: 20%, no exemption
- FII: 20%, no exemption
- Losses offset only within variable income (do NOT reduce IRPF)

### Regime 3 — Fixed income and funds
- `compute_fixed_income_tax`: regressive table by `days_held` (22.5% → 15%)
- Exempt classes (`EXEMPT_FIXED_INCOME`, `SAVINGS`) return 0
- `EQUITY_FUND` uses flat `equity_fund_rate` (15%)
- `compute_come_cotas`: semiannual prepayment at `come_cotas_rate`

### Regime 4 — IRPFM + annual facade
- `compute_irpfm`: high-income minimum tax; only the TOP-UP is returned (never negative)
- `compute_annual_tax`: orchestrates all four regimes; this is the `TaxFn` injected into the simulator
- **Invariant:** `total_tax == irpf.tax_due + variable_income_tax + fixed_income_tax + dividend_withholding + irpfm_additional` (within cent rounding)

### Data-not-code rule
All brackets, rates, and thresholds live in `backend/app/data/tax_tables/<year>.json`.
A new calendar year = a new JSON file. No logic changes.

---

## Monte Carlo Simulation

- Samples **return paths** (not a single mean) to capture sequence-of-returns risk
- All monetary values in **BRL**; inflation modeled via **IPCA** (stochastic, per `MarketAssumptions`)
- Calls `tax_fn` once per year per path — must be pure and fast
- `tax_fn` is injected; the Monte Carlo engine builds/tests against a stub before the real tax engine lands
- Output: `SimulationResult` with `success_probability`, terminal percentiles, and `by_year` fan data

---

## Optimizer

- Evaluates each `Strategy` candidate via `run_simulation`, ranks by `Objective`
- **The tax cost curve is non-monotonic** (R$20k exemption cliff, IRPF brackets, IRPFM step, the reducer)
  → ranking must come from full simulation of each candidate, never from gradient assumptions
- Built-in strategies (pre-defined catalogue in `strategies.py`):
  - "Quitar dívidas de alto custo primeiro"
  - "Investir primeiro (renda fixa)"
  - "Investir primeiro (renda variável)"
  - "Equilibrado: metade dívida, metade investimento"
  - "Resgatar na ordem mais eficiente fiscalmente"
- User-defined strategies: user configures allocation % and debt-payoff priority; treated as a `Strategy`
  with `id = "custom"` by the API

---

## Explanation Layer

The `Explanation` dataclass carries **structured numbers only** — `winner_id`, `winner_metric`,
`delta_vs_runner_up`, `key_drivers` (a fixed taxonomy of driver strings, not free prose).

**Fast path (default):** Jinja2 templates in `backend/app/explanation/templates/` render the
explanation into Portuguese narrative. Deterministic, zero latency, fully auditable.

**LLM path (opt-in):** The frontend's `ExplanationCard` has an "Explicar mais" button. On click,
the API calls `render_explanation(explanation, use_llm=True)`, which sends the structured
`Explanation` + the template-rendered text as context to Claude. The LLM may only elaborate — it
receives the numbers from the struct and must not recompute them.

---

## API Endpoints

```
POST /simulate
  Body:  { state: FinancialState, assumptions: MarketAssumptions, config: SimulationConfig }
  Returns: SimulationResult

POST /optimize
  Body:  { state: FinancialState, candidates: Strategy[], objective: Objective,
           assumptions: MarketAssumptions, config: SimulationConfig }
  Returns: Recommendation

POST /optimize/explain
  Body:  { explanation: Explanation, use_llm: bool }
  Returns: { text: string }   # template or LLM-rendered Portuguese narrative
```

A disclaimer header is injected on every response:
`X-Robo-CFO-Disclaimer: Este sistema é um simulador educacional. Não constitui assessoria financeira.`

---

## Code Style

```python
# Pure function — no side effects, no I/O, no global state
def compute_irpf(scenario: IRPFScenario, tables: TaxTables) -> IRPFResult:
    monthly_taxes = [_tax_for_month(m, tables) for m in scenario.monthly_taxable_income]
    ...
    return IRPFResult(
        tax_due=round(tax_due, 2),
        tax_base=round(tax_base, 2),
        model_used=model_used,
        marginal_rate=marginal_rate,
        effective_rate=round(effective_rate, 6),
        reduction_applied=round(reduction_applied, 2),
    )
```

- Types from `contracts.py` everywhere — no `dict` for domain objects
- `Money` values rounded to 2 decimal places at output boundaries only
- Brazilian tax terms (IRPF, IRPFM, FII, come-cotas, pró-labore) kept as-is
- Ruff for formatting and linting; mypy in strict mode for `app/`

---

## Testing Strategy

**Framework:** pytest (backend), Vitest + React Testing Library (frontend)

**Test levels:**

| Level | Location | What it covers |
|---|---|---|
| Golden / contract tests | `tests/tax/` | Each regime function against known correct values from Receita Federal examples |
| Unit | `tests/` | Pure functions in isolation with stubs |
| Integration | `tests/` | `compute_annual_tax` with real sub-functions; `optimize` with real `tax_fn` |
| Snapshot | `frontend/` | Key UI components (FanChart, StrategyComparison) |

**Coverage target:** 90%+ on `app/tax/`, 80%+ overall backend

**Critical invariants locked as golden tests:**
- `compute_irpf`: zero tax for monthly income ≤ R$5,000
- `compute_annual_tax`: `total_tax` invariant (within cent rounding)
- `compute_variable_income`: losses do not reduce IRPF regime
- `optimize`: winner strategy is the one with the best `objective` metric across all paths

---

## Boundaries

**Always:**
- Run `pytest` before committing any tax-engine change
- Use types from `contracts.py` — never raw `dict` for domain objects
- Round `Money` to 2 decimal places only at output boundaries
- Show the disclaimer on every UI screen and in every API response

**Ask first:**
- Modifying `contracts.py` (it is frozen)
- Adding a Python dependency (stdlib-first policy on the hot path)
- Changing the `TaxTables` JSON schema (breaks existing year configs)
- Adding a new `AssetClass` or `IncomeKind` enum value

**Never:**
- Compute prose in the tax engine, simulator, or optimizer (explanation = structured data only)
- Allow the LLM path to recompute numbers (it may only render what's in `Explanation`)
- Commit secrets or API keys (use environment variables)
- Model state taxes (ICMS, ISS, ITCMD — out of scope v1)
- Implement PGBL/VGBL logic (phase 2)

---

## Out of Scope (v1)

| Item | Reason |
|---|---|
| State taxes (ICMS, ISS, ITCMD, ITBI) | Federal/Union only |
| PGBL / VGBL private pension | Phase 2 (enum present in contracts, regime not implemented) |
| AMT, exotic credits | Not applicable in Brazilian system |
| Open Finance / Pluggy / Belvo integration | Phase 2 (synthetic data only now) |
| Multi-year bracket configs | Single configurable year per run |
| Authentication / multi-user | Portfolio piece; single synthetic user |
| Cloud deployment | Local Docker + GitHub Actions CI only |

---

## Success Criteria

- [ ] `docker compose up` runs the full stack with no manual steps
- [ ] `POST /optimize` with the sample fixture returns a ranked `Recommendation` in < 5s (10,000 paths, 30 years)
- [ ] Golden tests for all four tax regimes pass (see Testing Strategy)
- [ ] `total_tax` invariant holds to within R$0.01 for all test scenarios
- [ ] Monte Carlo fan chart renders in the browser with p10/p50/p90 lines
- [ ] "Explicar mais" button returns LLM-rendered Portuguese narrative without recomputing numbers
- [ ] GitHub Actions CI passes: ruff, mypy, pytest, vitest
- [ ] Disclaimer visible on every page and in every API response header

---

## `KeyDriver` Taxonomy (fixed)

`Explanation.key_drivers` is `tuple[KeyDriver, ...]`. The `KeyDriver` enum is defined in `contracts.py`.
The rendering layer maps each value to a Portuguese label.

| Value | Meaning |
|---|---|
| `irpf_reducer_benefit` | Lei 15.270/2025 reducer materially reduces tax |
| `tax_efficiency` | Total lifetime tax differs across strategies |
| `debt_cost_reduction` | Paying down high-cost debt improves net return |
| `sequence_of_returns_risk` | Path dispersion drives success probability |
| `variable_income_exemption` | R$20k monthly swing exemption utilisation |
| `fixed_income_holding_period` | Regressive table rate changes with holding time |
| `irpfm_threshold` | Strategy crosses or avoids the R$600k annual floor |
| `asset_allocation` | Risk/return mix across asset classes |

---

## Per-Asset-Class Return Assumptions

`MarketAssumptions` carries a global `mean_real_return` / `return_volatility` as a fallback, plus an
optional `per_class: tuple[AssetClassAssumptions, ...]` for overrides. If an `AssetClass` is not listed
in `per_class`, the global defaults apply.

Example usage (a fixture):
```python
MarketAssumptions(
    mean_real_return=0.05,
    return_volatility=0.12,
    ipca_mean=0.04,
    ipca_volatility=0.015,
    per_class=(
        AssetClassAssumptions(AssetClass.STOCKS, mean_real_return=0.07, return_volatility=0.20),
        AssetClassAssumptions(AssetClass.TAXABLE_FIXED_INCOME, mean_real_return=0.04, return_volatility=0.02),
    ),
)
```

---

## Simulation Seed and Testing Philosophy

### Tax engine tests (pure, deterministic)
`compute_irpf`, `compute_variable_income`, `compute_fixed_income_tax`, `compute_come_cotas`,
`compute_irpfm`, `compute_annual_tax` are pure functions with no randomness. Golden tests assert
**exact values** hand-verified against Receita Federal examples. No seed involved.

### Monte Carlo tests (stochastic)
- **Fix the seed** in test fixtures via `SimulationConfig(seed=42, ...)` for reproducibility. When a
  test fails, rerunning produces the identical failure.
- **Do not assert exact magic numbers** on Monte Carlo output (e.g., `terminal_p50 == 1_847_200`).
  That number is an artifact of the RNG and breaks on any legitimate sampling change.
- **Assert invariants and tolerances instead:**
  - `result.terminal_p10 < result.terminal_p50 < result.terminal_p90`
  - `0.0 <= result.success_probability <= 1.0`
  - Convergence: p50 with `n_paths=10_000` is within ±5% of p50 with `n_paths=50_000` for the same seed
  - Cases with analytical answers (e.g., zero-volatility, zero-tax stub) land within a confidence band
- **Use `np.random.default_rng(seed)`** (the Generator API, documented stability policy) — never the
  legacy `np.random.seed` global. Always pass the seed explicitly; never depend on RNG state set by
  another test.
- Seed guarantees determinism only within the same library version and environment. Lean on tolerances,
  not exact figures, for stochastic assertions.
