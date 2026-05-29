"""T10: optimize() — evaluates each Strategy via run_simulation, ranks by objective.

run_simulation lives in app/simulation/monte_carlo.py (built in a parallel worktree).
This module imports it so tests can patch it with a deterministic stub while the
real Monte Carlo implementation is pending.
"""
from __future__ import annotations

from collections.abc import Sequence

from contracts import (
    Explanation,
    FinancialState,
    KeyDriver,
    MarketAssumptions,
    Objective,
    Recommendation,
    SimulationConfig,
    SimulationResult,
    Strategy,
    StrategyOutcome,
    TaxFn,
    TaxTables,
)

# Import run_simulation so that tests can patch this module's reference.
# The simulation worktree will provide the real implementation; until then
# this raises NotImplementedError (which the tests stub out via unittest.mock).
try:
    from app.simulation.monte_carlo import run_simulation
except ImportError:  # pragma: no cover
    from contracts import run_simulation


# ---------------------------------------------------------------------------
# Lifetime tax helper
# ---------------------------------------------------------------------------

def _compute_lifetime_tax(result: SimulationResult) -> float:
    """Sum p50 across by_year as a proxy for lifetime tax cost.

    The real simulator carries total_tax per year; this approximation lets the
    optimizer rank strategies before the full tax engine is integrated.
    """
    return sum(yp.p50 for yp in result.by_year)


# ---------------------------------------------------------------------------
# Key driver selection — heuristic based on objective and outcome spread
# ---------------------------------------------------------------------------

def _select_key_drivers(
    objective: Objective,
    outcomes: list[StrategyOutcome],
) -> tuple[KeyDriver, ...]:
    drivers: list[KeyDriver] = []

    if objective == Objective.MAX_MEDIAN_NET_WORTH:
        drivers.append(KeyDriver.ASSET_ALLOCATION)
    elif objective == Objective.MAX_SUCCESS_PROBABILITY:
        drivers.append(KeyDriver.SEQUENCE_OF_RETURNS_RISK)
    elif objective == Objective.MIN_LIFETIME_TAX:
        drivers.append(KeyDriver.TAX_EFFICIENCY)
    else:
        drivers.append(KeyDriver.ASSET_ALLOCATION)

    # If multiple strategies exist and tax differs, surface TAX_EFFICIENCY
    if len(outcomes) > 1 and objective != Objective.MIN_LIFETIME_TAX:
        taxes = [o.lifetime_tax for o in outcomes]
        if max(taxes) - min(taxes) > 1.0:
            drivers.append(KeyDriver.TAX_EFFICIENCY)

    return tuple(drivers)


# ---------------------------------------------------------------------------
# Metric extractor — maps Objective → the value used for ranking
# ---------------------------------------------------------------------------

def _metric(outcome: StrategyOutcome, objective: Objective) -> float:
    if objective == Objective.MAX_MEDIAN_NET_WORTH:
        return outcome.result.terminal_p50
    if objective == Objective.MAX_SUCCESS_PROBABILITY:
        return outcome.result.success_probability
    if objective == Objective.MIN_LIFETIME_TAX:
        return -outcome.lifetime_tax  # negate: higher (less negative) = lower tax
    raise ValueError(f"Unknown objective: {objective}")  # pragma: no cover


# ---------------------------------------------------------------------------
# optimize() — public API matching contracts.py
# ---------------------------------------------------------------------------

def optimize(
    state: FinancialState,
    candidates: Sequence[Strategy],
    objective: Objective,
    assumptions: MarketAssumptions,
    config: SimulationConfig,
    tax_fn: TaxFn,
    tax_tables_by_year: Sequence[TaxTables],
) -> Recommendation:
    """Full evaluation of every candidate — no gradient shortcuts.

    The tax cost curve is non-monotonic (R$20k exemption cliff, IRPF brackets,
    IRPFM step, the reducer), so each strategy must be simulated independently.
    """
    outcomes: list[StrategyOutcome] = []
    for strategy in candidates:
        result = run_simulation(
            state=state,
            assumptions=assumptions,
            config=config,
            tax_fn=tax_fn,
            tax_tables_by_year=tax_tables_by_year,
        )
        lifetime_tax = _compute_lifetime_tax(result)
        outcomes.append(StrategyOutcome(
            strategy=strategy,
            result=result,
            lifetime_tax=lifetime_tax,
        ))

    # Rank: descending by metric (MIN_LIFETIME_TAX is negated inside _metric)
    ranked = tuple(sorted(outcomes, key=lambda o: _metric(o, objective), reverse=True))

    winner = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None

    winner_metric = _metric(winner, objective)
    runner_up_metric = _metric(runner_up, objective) if runner_up is not None else 0.0
    delta = winner_metric - runner_up_metric if runner_up is not None else 0.0

    explanation = Explanation(
        objective=objective,
        winner_id=winner.strategy.id,
        winner_metric=winner_metric,
        runner_up_id=runner_up.strategy.id if runner_up else None,
        delta_vs_runner_up=delta,
        key_drivers=_select_key_drivers(objective, outcomes),
    )

    return Recommendation(objective=objective, ranked=ranked, explanation=explanation)
