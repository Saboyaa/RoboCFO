"""T10: optimize() — evaluates each Strategy via run_simulation, ranks by objective.

run_simulation lives in app/simulation/monte_carlo.py (built in a parallel worktree).
This module imports it so tests can patch it with a deterministic stub while the
real Monte Carlo implementation is pending.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from contracts import (
    AssetClass,
    Explanation,
    FinancialState,
    Holding,
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
# Strategy-specific state transformation
# ---------------------------------------------------------------------------

def _apply_strategy(state: FinancialState, strategy_id: str) -> FinancialState:
    """Return a modified FinancialState reflecting the strategy's allocation logic.

    Each strategy changes how the annual surplus is split between extra debt
    payoff and new investment. We model this by:
      - debt_first: pay off all debt immediately from holdings; after that,
        freed minimum payments compound as additional savings.
      - invest_fixed / invest_variable: keep debt, add annual interest cost
        as an additional expense (debt drag).
      - balanced: pay half the debt from holdings, half the interest drags.
      - tax_efficient_redemption: same as invest_fixed with slight tax benefit.
    """
    total_debt = sum(d.balance for d in state.debts)
    total_holdings = sum(h.balance for h in state.holdings)

    if total_debt <= 0.0:
        return state  # nothing to differentiate

    def _scale_holdings(fraction: float) -> tuple[Holding, ...]:
        return tuple(
            dataclasses.replace(h, balance=h.balance * fraction)
            for h in state.holdings
        )

    if strategy_id == "debt_first":
        # Liquidate holdings to pay off the full debt immediately.
        # After that: no more minimum payments → net savings increases.
        remaining_holdings = max(0.0, total_holdings - total_debt)
        fraction = remaining_holdings / total_holdings if total_holdings > 0 else 0.0
        new_holdings = _scale_holdings(fraction)
        # Remove debts and their minimum payments (freed cash already in savings)
        return dataclasses.replace(state, holdings=new_holdings, debts=())

    if strategy_id == "balanced":
        # Pay off 50% of the debt; keep 50% draining as interest.
        partial_pay = total_debt * 0.5
        remaining_holdings = max(0.0, total_holdings - partial_pay)
        fraction = remaining_holdings / total_holdings if total_holdings > 0 else 0.0
        new_holdings = _scale_holdings(fraction)
        # Keep half the debt, half the interest cost
        half_debts = tuple(
            dataclasses.replace(d, balance=d.balance * 0.5)
            for d in state.debts
        )
        return dataclasses.replace(state, holdings=new_holdings, debts=half_debts)

    if strategy_id == "invest_variable":
        # Same debt drag as invest_fixed but boost equity allocation/return
        # by shifting all holdings to STOCKS assumptions.
        boosted = tuple(
            dataclasses.replace(h, asset_class=AssetClass.STOCKS)
            if h.asset_class not in (AssetClass.EXEMPT_FIXED_INCOME, AssetClass.SAVINGS)
            else h
            for h in state.holdings
        )
        return dataclasses.replace(state, holdings=boosted)

    if strategy_id == "tax_efficient_redemption":
        # Invest normally but model a 10% reduction in annual expenses from
        # tax efficiency (better holding periods → lower regressive rate).
        tax_saving = state.annual_expenses * 0.05
        return dataclasses.replace(
            state, annual_expenses=max(0.0, state.annual_expenses - tax_saving)
        )

    # invest_fixed and any unknown id: keep debt, pay only minimum (already
    # subtracted in run_simulation), let interest erode real wealth.
    return state


# ---------------------------------------------------------------------------
# Lifetime tax helper
# ---------------------------------------------------------------------------

def _compute_lifetime_tax(result: SimulationResult) -> float:
    """Approximate lifetime tax as the sum of absolute wealth loss from the
    median path vs the p90 path — a proxy for tax drag across all years."""
    return sum(yp.p90 - yp.p50 for yp in result.by_year)


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
        strategy_state = _apply_strategy(state, strategy.id)
        result = run_simulation(
            state=strategy_state,
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
