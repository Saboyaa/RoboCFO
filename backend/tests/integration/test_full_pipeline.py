"""
Checkpoint C integration test: real tax engine wired into Monte Carlo and Optimizer.

This is the critical merge-risk test from the plan:
  optimize() → run_simulation() → compute_annual_tax() (real TaxFn)
"""

import pytest
from contracts import Objective

from app.data.loader import (
    load_fixture,
    load_market_assumptions,
    load_tax_tables,
)
from app.optimizer.engine import optimize
from app.optimizer.strategies import BUILTIN_STRATEGIES
from app.simulation.monte_carlo import run_simulation
from app.tax.annual import compute_annual_tax


@pytest.fixture
def state():
    return load_fixture("sample_state")


@pytest.fixture
def assumptions():
    return load_market_assumptions()


@pytest.fixture
def tables():
    return [load_tax_tables(2026)]


@pytest.fixture
def config():
    # Fast config for integration tests — small n_paths
    from contracts import SimulationConfig
    return SimulationConfig(years=10, n_paths=200, seed=42)


def test_run_simulation_with_real_tax_fn(state, assumptions, config, tables):
    """Monte Carlo calls real compute_annual_tax on every path × year."""
    result = run_simulation(state, assumptions, config, compute_annual_tax, tables)
    assert result.paths_simulated == 200
    assert result.terminal_p10 < result.terminal_p50 < result.terminal_p90
    assert 0.0 <= result.success_probability <= 1.0
    assert len(result.by_year) == 10


def test_optimize_with_real_tax_fn(state, assumptions, config, tables):
    """optimize() evaluates all strategies via run_simulation with real tax engine."""
    recommendation = optimize(
        state=state,
        candidates=list(BUILTIN_STRATEGIES),
        objective=Objective.MAX_MEDIAN_NET_WORTH,
        assumptions=assumptions,
        config=config,
        tax_fn=compute_annual_tax,
        tax_tables_by_year=tables,
    )
    assert len(recommendation.ranked) == len(BUILTIN_STRATEGIES)
    assert recommendation.ranked[0].result.terminal_p50 >= recommendation.ranked[-1].result.terminal_p50
    assert recommendation.explanation.winner_id == recommendation.ranked[0].strategy.id
    assert len(recommendation.explanation.key_drivers) >= 1


def test_optimize_min_lifetime_tax(state, assumptions, config, tables):
    """MIN_LIFETIME_TAX objective ranks by lowest total tax paid."""
    recommendation = optimize(
        state=state,
        candidates=list(BUILTIN_STRATEGIES),
        objective=Objective.MIN_LIFETIME_TAX,
        assumptions=assumptions,
        config=config,
        tax_fn=compute_annual_tax,
        tax_tables_by_year=tables,
    )
    assert recommendation.explanation.objective == Objective.MIN_LIFETIME_TAX
    # Best strategy has lower or equal lifetime tax than worst
    assert recommendation.ranked[0].lifetime_tax <= recommendation.ranked[-1].lifetime_tax


def test_total_tax_invariant_holds_in_simulation(state, assumptions, config, tables):
    """Spot-check: AnnualTaxResult invariant holds when called from simulation path."""
    from contracts import AnnualTaxScenario, IRPFScenario
    scenario = AnnualTaxScenario(
        year=2026,
        irpf=IRPFScenario(year=2026, monthly_taxable_income=tuple([10_000.0] * 12)),
    )
    result = compute_annual_tax(scenario, tables[0])
    expected = (
        result.irpf.tax_due
        + result.variable_income_tax
        + result.fixed_income_tax
        + result.dividend_withholding
        + result.irpfm_additional
    )
    assert result.total_tax == pytest.approx(expected, abs=0.01)


def test_high_interest_debt_makes_debt_first_win(state, assumptions, tables):
    """With a very high debt interest rate, paying debt first must beat investing."""
    from contracts import Debt, SimulationConfig
    import dataclasses

    # Replace the vehicle debt with a 60% annual-rate debt — clearly predatory
    expensive_debt = Debt(
        id="expensive", name="Dívida cara", balance=35_000.0,
        annual_interest_rate=0.60, minimum_payment=900.0,
    )
    expensive_state = dataclasses.replace(state, debts=(expensive_debt,))
    config = SimulationConfig(years=20, n_paths=500, seed=7)

    from app.optimizer.strategies import BUILTIN_STRATEGIES
    from contracts import Objective

    recommendation = optimize(
        state=expensive_state,
        candidates=list(BUILTIN_STRATEGIES),
        objective=Objective.MAX_MEDIAN_NET_WORTH,
        assumptions=assumptions,
        config=config,
        tax_fn=compute_annual_tax,
        tax_tables_by_year=tables,
    )

    winner_id = recommendation.ranked[0].strategy.id
    assert winner_id == "debt_first", (
        f"With 60% debt interest, debt_first must win — got {winner_id}"
    )
