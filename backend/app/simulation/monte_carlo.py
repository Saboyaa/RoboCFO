"""Monte Carlo simulation engine for Robo-CFO (Brazil).

Samples return paths (not a single mean) to capture sequence-of-returns risk.
All monetary values in BRL; inflation modeled via IPCA (stochastic).
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from contracts import (
    AnnualTaxScenario,
    AssetClass,
    FinancialState,
    IRPFScenario,
    MarketAssumptions,
    SimulationConfig,
    SimulationResult,
    TaxFn,
    TaxTables,
    YearPercentiles,
)


def _build_per_class_lookup(assumptions: MarketAssumptions) -> dict[AssetClass, tuple[float, float]]:
    """Return a mapping from AssetClass -> (mean_real_return, return_volatility)."""
    return {
        ac.asset_class: (ac.mean_real_return, ac.return_volatility)
        for ac in assumptions.per_class
    }


def _portfolio_weighted_params(
    state: FinancialState,
    assumptions: MarketAssumptions,
) -> tuple[float, float]:
    """Compute a total-portfolio-weighted mean and volatility from holdings.

    For each holding, looks up the per-class override or falls back to global.
    Returns (weighted_mean, weighted_vol) where the weights are the fraction of
    total portfolio balance. If no holdings, returns the global defaults.
    """
    per_class = _build_per_class_lookup(assumptions)
    total_balance = sum(h.balance for h in state.holdings)

    if total_balance <= 0.0 or not state.holdings:
        return assumptions.mean_real_return, assumptions.return_volatility

    weighted_mean = 0.0
    weighted_vol = 0.0
    for holding in state.holdings:
        weight = holding.balance / total_balance
        mean, vol = per_class.get(
            holding.asset_class,
            (assumptions.mean_real_return, assumptions.return_volatility),
        )
        weighted_mean += weight * mean
        weighted_vol += weight * vol

    return weighted_mean, weighted_vol


def _make_dummy_tax_scenario(year: int, state: FinancialState) -> AnnualTaxScenario:
    """Build a minimal AnnualTaxScenario for the simulator.

    The simulator does not need real income/trade data — it calls tax_fn
    once per year per path and subtracts total_tax from wealth. The tax_fn
    stub (used in tests) always returns zero; the real facade will receive
    richer data from the optimizer. This keeps the simulation loop pure and fast.
    """
    irpf_scenario = IRPFScenario(
        year=year,
        monthly_taxable_income=tuple(
            sum(
                inc.monthly_amount
                for inc in state.incomes
                if inc.start_year <= year and (inc.end_year is None or inc.end_year >= year)
            )
            for _ in range(12)
        ),
        deductible_expenses_annual=state.deductible_expenses_annual,
        dependents=state.taxpayer.dependents,
    )
    return AnnualTaxScenario(year=year, irpf=irpf_scenario)


def run_simulation(
    state: FinancialState,
    assumptions: MarketAssumptions,
    config: SimulationConfig,
    tax_fn: TaxFn,
    tax_tables_by_year: Sequence[TaxTables],
) -> SimulationResult:
    """Samples return PATHS (not a single mean) to capture sequence-of-returns risk.

    Calls `tax_fn` once per simulated year per path.
    Uses np.random.default_rng(seed) for ALL randomness — never legacy np.random.seed.
    """
    rng = np.random.default_rng(config.seed)

    n_paths = config.n_paths
    years = config.years
    base_year = state.base_year

    # --- Compute portfolio parameters (weighted mean/vol across holdings) ---
    per_class_lookup = _build_per_class_lookup(assumptions)
    total_balance = sum(h.balance for h in state.holdings)
    initial_wealth = total_balance

    # Build year-indexed tax tables lookup (year -> tables)
    tables_by_year: dict[int, TaxTables] = {t.year: t for t in tax_tables_by_year}

    # --- Pre-build tax scenarios per year (same for all paths) ---
    tax_scenarios = [
        _make_dummy_tax_scenario(base_year + y + 1, state)
        for y in range(years)
    ]

    # --- Compute per-year portfolio mean/vol from holdings ---
    # We use weighted portfolio mean and vol. For simplicity, the same
    # asset mix is held throughout (no rebalancing in this engine).
    if total_balance > 0.0 and state.holdings:
        weighted_mean = 0.0
        weighted_vol = 0.0
        for holding in state.holdings:
            weight = holding.balance / total_balance
            m, v = per_class_lookup.get(
                holding.asset_class,
                (assumptions.mean_real_return, assumptions.return_volatility),
            )
            weighted_mean += weight * m
            weighted_vol += weight * v
    else:
        weighted_mean = assumptions.mean_real_return
        weighted_vol = assumptions.return_volatility

    # --- Sample returns and IPCA for all paths and years at once ---
    # Shape: (n_paths, years)
    real_returns = rng.normal(
        loc=weighted_mean,
        scale=weighted_vol if weighted_vol > 0.0 else 1e-12,
        size=(n_paths, years),
    )
    # IPCA paths
    ipca_rates = rng.normal(
        loc=assumptions.ipca_mean,
        scale=assumptions.ipca_volatility if assumptions.ipca_volatility > 0.0 else 1e-12,
        size=(n_paths, years),
    )

    # --- Simulate paths ---
    # wealth[i, y] = wealth at end of year y for path i
    wealth = np.empty((n_paths, years), dtype=np.float64)
    current_wealth = np.full(n_paths, initial_wealth, dtype=np.float64)

    # Annual net savings = total income - annual expenses
    # (before tax; tax_fn deducts taxes separately)
    annual_income = sum(
        inc.monthly_amount * 12
        for inc in state.incomes
        if inc.start_year <= base_year
    )
    annual_net_savings = annual_income - state.annual_expenses

    for y in range(years):
        year = base_year + y + 1
        # Nominal return = real return + IPCA (approximate, additive)
        nominal_return = real_returns[:, y] + ipca_rates[:, y]

        # Apply return to wealth
        current_wealth = current_wealth * (1.0 + nominal_return)

        # Add net savings (can be negative if expenses > income)
        current_wealth += annual_net_savings

        # Apply taxes — call tax_fn with the prebuilt scenario
        tables = tables_by_year.get(year)
        if tables is not None:
            tax_result = tax_fn(tax_scenarios[y], tables)
            current_wealth -= tax_result.total_tax

        # Record wealth at this year
        wealth[:, y] = current_wealth

    # --- Compute output statistics ---
    # Terminal wealth is the last year
    terminal_wealth = wealth[:, -1]

    # Success = fraction of paths where terminal wealth >= sum of goal targets
    goal_threshold = sum(g.target_amount for g in state.goals)
    if goal_threshold <= 0.0:
        success_probability = 1.0
    else:
        success_probability = float(np.mean(terminal_wealth >= goal_threshold))

    # Terminal percentiles
    terminal_p10 = float(np.percentile(terminal_wealth, 10))
    terminal_p50 = float(np.percentile(terminal_wealth, 50))
    terminal_p90 = float(np.percentile(terminal_wealth, 90))

    # Per-year percentiles
    by_year_list: list[YearPercentiles] = []
    for y in range(years):
        year_wealth = wealth[:, y]
        by_year_list.append(
            YearPercentiles(
                year=base_year + y + 1,
                p10=float(np.percentile(year_wealth, 10)),
                p50=float(np.percentile(year_wealth, 50)),
                p90=float(np.percentile(year_wealth, 90)),
            )
        )

    return SimulationResult(
        success_probability=success_probability,
        terminal_p10=terminal_p10,
        terminal_p50=terminal_p50,
        terminal_p90=terminal_p90,
        by_year=tuple(by_year_list),
        paths_simulated=n_paths,
    )
