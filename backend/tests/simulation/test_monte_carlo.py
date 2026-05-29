"""Tests for run_simulation — invariant-only, no magic numbers.

See SPEC.md § "Monte Carlo tests (stochastic)" for the testing philosophy.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from contracts import (
    AnnualTaxResult,
    AnnualTaxScenario,
    AssetClass,
    AssetClassAssumptions,
    DeclarationModel,
    FinancialState,
    Goal,
    GoalKind,
    Holding,
    IRPFResult,
    MarketAssumptions,
    SimulationConfig,
    Taxpayer,
    TaxTables,
)

from app.simulation.monte_carlo import run_simulation

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent.parent / "backend" / "app" / "data" / "fixtures"


def _zero_irpf_result() -> IRPFResult:
    return IRPFResult(
        tax_due=0.0,
        tax_base=0.0,
        model_used=DeclarationModel.SIMPLIFIED,
        marginal_rate=0.0,
        effective_rate=0.0,
        reduction_applied=0.0,
    )


def _zero_tax_result() -> AnnualTaxResult:
    return AnnualTaxResult(
        irpf=_zero_irpf_result(),
        variable_income_tax=0.0,
        fixed_income_tax=0.0,
        dividend_withholding=0.0,
        irpfm_additional=0.0,
        total_tax=0.0,
        variable_income_loss_carryforward_out=0.0,
    )


def zero_tax_fn(scenario: AnnualTaxScenario, tables: TaxTables) -> AnnualTaxResult:  # noqa: ARG001
    """Stub tax function that always returns zero tax."""
    return _zero_tax_result()


# --------------------------------------------------------------------------- #
# Minimal fixtures
# --------------------------------------------------------------------------- #

def _minimal_state(*, n_goals: int = 1, goal_amount: float = 100_000.0) -> FinancialState:
    goals = tuple(
        Goal(
            id=f"g{i}",
            name=f"Goal {i}",
            kind=GoalKind.RETIREMENT,
            target_amount=goal_amount,
            target_year=2036,
        )
        for i in range(n_goals)
    )
    return FinancialState(
        taxpayer=Taxpayer(age=35, retirement_age=65),
        base_year=2026,
        holdings=(
            Holding(
                id="h1",
                name="Stocks",
                asset_class=AssetClass.STOCKS,
                balance=200_000.0,
            ),
        ),
        goals=goals,
        annual_expenses=0.0,
    )


def _default_assumptions() -> MarketAssumptions:
    return MarketAssumptions(
        mean_real_return=0.05,
        return_volatility=0.12,
        ipca_mean=0.04,
        ipca_volatility=0.015,
    )


def _default_config(*, seed: int | None = 42, n_paths: int = 500, years: int = 10) -> SimulationConfig:
    return SimulationConfig(years=years, n_paths=n_paths, seed=seed)


# --------------------------------------------------------------------------- #
# Structural invariants
# --------------------------------------------------------------------------- #

def test_terminal_percentile_ordering() -> None:
    """p10 < p50 < p90 for any realistic scenario with non-zero volatility."""
    result = run_simulation(
        _minimal_state(),
        _default_assumptions(),
        _default_config(n_paths=1000),
        zero_tax_fn,
        [],
    )
    assert result.terminal_p10 < result.terminal_p50
    assert result.terminal_p50 < result.terminal_p90


def test_success_probability_bounded() -> None:
    """success_probability must be in [0.0, 1.0]."""
    result = run_simulation(
        _minimal_state(),
        _default_assumptions(),
        _default_config(),
        zero_tax_fn,
        [],
    )
    assert 0.0 <= result.success_probability <= 1.0


def test_paths_simulated_matches_config() -> None:
    """paths_simulated must equal config.n_paths."""
    n = 200
    result = run_simulation(
        _minimal_state(),
        _default_assumptions(),
        SimulationConfig(years=5, n_paths=n, seed=7),
        zero_tax_fn,
        [],
    )
    assert result.paths_simulated == n


def test_by_year_length_matches_years() -> None:
    """by_year must have exactly config.years entries."""
    years = 7
    result = run_simulation(
        _minimal_state(),
        _default_assumptions(),
        SimulationConfig(years=years, n_paths=300, seed=1),
        zero_tax_fn,
        [],
    )
    assert len(result.by_year) == years


def test_by_year_percentile_ordering() -> None:
    """At every year, p10 <= p50 <= p90."""
    result = run_simulation(
        _minimal_state(),
        _default_assumptions(),
        _default_config(n_paths=500),
        zero_tax_fn,
        [],
    )
    for yp in result.by_year:
        assert yp.p10 <= yp.p50, f"year {yp.year}: p10={yp.p10} > p50={yp.p50}"
        assert yp.p50 <= yp.p90, f"year {yp.year}: p50={yp.p50} > p90={yp.p90}"


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

def test_seed_reproducibility() -> None:
    """Same seed must produce identical SimulationResult on two consecutive calls."""
    cfg = SimulationConfig(years=10, n_paths=500, seed=42)
    state = _minimal_state()
    assumptions = _default_assumptions()

    r1 = run_simulation(state, assumptions, cfg, zero_tax_fn, [])
    r2 = run_simulation(state, assumptions, cfg, zero_tax_fn, [])

    assert r1.terminal_p10 == r2.terminal_p10
    assert r1.terminal_p50 == r2.terminal_p50
    assert r1.terminal_p90 == r2.terminal_p90
    assert r1.success_probability == r2.success_probability
    assert r1.by_year == r2.by_year


# --------------------------------------------------------------------------- #
# Zero-volatility: p10 == p50 == p90 within R$0.01
# --------------------------------------------------------------------------- #

def test_zero_volatility_percentiles_converge() -> None:
    """With zero return and IPCA volatility, all paths are identical -> p10 == p50 == p90."""
    assumptions = MarketAssumptions(
        mean_real_return=0.05,
        return_volatility=0.0,
        ipca_mean=0.04,
        ipca_volatility=0.0,
    )
    result = run_simulation(
        _minimal_state(),
        assumptions,
        SimulationConfig(years=10, n_paths=200, seed=99),
        zero_tax_fn,
        [],
    )
    assert abs(result.terminal_p10 - result.terminal_p50) <= 0.01, (
        f"p10={result.terminal_p10} vs p50={result.terminal_p50}"
    )
    assert abs(result.terminal_p50 - result.terminal_p90) <= 0.01, (
        f"p50={result.terminal_p50} vs p90={result.terminal_p90}"
    )


# --------------------------------------------------------------------------- #
# Per-class override
# --------------------------------------------------------------------------- #

def test_per_class_override_affects_result() -> None:
    """When STOCKS has a much higher mean return, terminal wealth should be higher."""
    base_assumptions = MarketAssumptions(
        mean_real_return=0.03,
        return_volatility=0.0,   # deterministic for cleaner comparison
        ipca_mean=0.04,
        ipca_volatility=0.0,
    )
    high_stocks_assumptions = MarketAssumptions(
        mean_real_return=0.03,
        return_volatility=0.0,
        ipca_mean=0.04,
        ipca_volatility=0.0,
        per_class=(
            AssetClassAssumptions(
                asset_class=AssetClass.STOCKS,
                mean_real_return=0.12,   # much higher than global 0.03
                return_volatility=0.0,
            ),
        ),
    )
    cfg = SimulationConfig(years=10, n_paths=100, seed=1)
    state = _minimal_state()  # state has STOCKS holding

    result_base = run_simulation(state, base_assumptions, cfg, zero_tax_fn, [])
    result_high = run_simulation(state, high_stocks_assumptions, cfg, zero_tax_fn, [])

    assert result_high.terminal_p50 > result_base.terminal_p50, (
        f"Expected higher terminal p50 with STOCKS override. "
        f"base={result_base.terminal_p50}, high={result_high.terminal_p50}"
    )


# --------------------------------------------------------------------------- #
# Success probability edge cases
# --------------------------------------------------------------------------- #

def test_impossible_goal_has_low_success_probability() -> None:
    """An astronomically large goal should produce near-zero success probability."""
    state = _minimal_state(goal_amount=1_000_000_000.0)  # 1 billion BRL
    result = run_simulation(
        state,
        _default_assumptions(),
        _default_config(n_paths=500),
        zero_tax_fn,
        [],
    )
    assert result.success_probability < 0.1, (
        f"Expected near-zero success for impossible goal, got {result.success_probability}"
    )


def test_no_goals_has_full_success_probability() -> None:
    """With no goals, every path is successful -> success_probability == 1.0."""
    state = FinancialState(
        taxpayer=Taxpayer(age=35, retirement_age=65),
        base_year=2026,
        holdings=(
            Holding(
                id="h1",
                name="Stocks",
                asset_class=AssetClass.STOCKS,
                balance=100_000.0,
            ),
        ),
        goals=(),  # no goals
        annual_expenses=0.0,
    )
    result = run_simulation(
        state,
        _default_assumptions(),
        _default_config(n_paths=300),
        zero_tax_fn,
        [],
    )
    assert result.success_probability == 1.0


# --------------------------------------------------------------------------- #
# Performance
# --------------------------------------------------------------------------- #

def test_performance_1000_paths_10_years() -> None:
    """n_paths=1000, years=10 must complete in under 2 seconds."""
    # Load sample fixture for a realistic test
    sample_path = FIXTURES_DIR / "sample_state.json"
    if sample_path.exists():
        raw = json.loads(sample_path.read_text())
        holdings = tuple(
            Holding(
                id=h["id"],
                name=h["name"],
                asset_class=AssetClass(h["asset_class"]),
                balance=h["balance"],
                cost_basis=h.get("cost_basis"),
                acquisition_year=h.get("acquisition_year"),
            )
            for h in raw.get("holdings", [])
        )
        state = FinancialState(
            taxpayer=Taxpayer(
                age=raw["taxpayer"]["age"],
                retirement_age=raw["taxpayer"]["retirement_age"],
                dependents=raw["taxpayer"].get("dependents", 0),
                state=raw["taxpayer"].get("state"),
            ),
            base_year=raw["base_year"],
            holdings=holdings,
            annual_expenses=raw.get("annual_expenses", 0.0),
        )
    else:
        state = _minimal_state()

    cfg = SimulationConfig(years=10, n_paths=1000, seed=42)
    start = time.perf_counter()
    run_simulation(state, _default_assumptions(), cfg, zero_tax_fn, [])
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, f"Performance test failed: {elapsed:.2f}s > 2.0s"
