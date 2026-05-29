"""T10: Tests for optimize() in app/optimizer/engine.py.

run_simulation is stubbed: terminal_p50 = 100_000 * (strategy_index + 1),
making ranking deterministic.
"""
from __future__ import annotations

from collections.abc import Sequence
from unittest.mock import patch

import pytest
from contracts import (
    AnnualTaxResult,
    AnnualTaxScenario,
    Explanation,
    FinancialState,
    IRPFBracket,
    IRPFResult,
    KeyDriver,
    MarketAssumptions,
    Objective,
    Recommendation,
    RegressiveBand,
    SimulationConfig,
    SimulationResult,
    Strategy,
    StrategyOutcome,
    TaxFn,
    Taxpayer,
    TaxTables,
    YearPercentiles,
)

from app.optimizer.engine import optimize
from app.optimizer.strategies import BUILTIN_STRATEGIES

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_sim_result(index: int) -> SimulationResult:
    """Deterministic stub: terminal_p50 = 100_000 * (index + 1)."""
    terminal_p50 = 100_000.0 * (index + 1)
    return SimulationResult(
        success_probability=0.5 + 0.1 * index,
        terminal_p10=terminal_p50 * 0.5,
        terminal_p50=terminal_p50,
        terminal_p90=terminal_p50 * 1.5,
        by_year=(
            YearPercentiles(
                year=2026,
                p10=terminal_p50 * 0.5,
                p50=terminal_p50,
                p90=terminal_p50 * 1.5,
            ),
        ),
        paths_simulated=1_000,
    )


@pytest.fixture()
def minimal_state() -> FinancialState:
    return FinancialState(
        taxpayer=Taxpayer(age=35, retirement_age=65),
        base_year=2026,
    )


@pytest.fixture()
def assumptions() -> MarketAssumptions:
    return MarketAssumptions(mean_real_return=0.05, return_volatility=0.12)


@pytest.fixture()
def sim_config() -> SimulationConfig:
    return SimulationConfig(years=10, n_paths=100, seed=42)


@pytest.fixture()
def stub_tax_fn() -> TaxFn:
    """Minimal stub — the optimizer only receives the AnnualTaxResult total_tax."""

    def _tax_fn(scenario: AnnualTaxScenario, tables: TaxTables) -> AnnualTaxResult:  # noqa: ARG001
        return AnnualTaxResult(
            irpf=IRPFResult(
                tax_due=0.0,
                tax_base=0.0,
                model_used=None,  # type: ignore[arg-type]
                marginal_rate=0.0,
                effective_rate=0.0,
                reduction_applied=0.0,
            ),
            variable_income_tax=0.0,
            fixed_income_tax=0.0,
            dividend_withholding=0.0,
            irpfm_additional=0.0,
            total_tax=1_000.0,
            variable_income_loss_carryforward_out=0.0,
        )

    return _tax_fn  # type: ignore[return-value]


@pytest.fixture()
def tax_tables(stub_tax_fn: TaxFn) -> list[TaxTables]:
    """Single-year stub table."""
    bracket = IRPFBracket(lower_bound=0.0, rate=0.0, deduction=0.0)
    band = RegressiveBand(max_days=None, rate=0.15)
    return [
        TaxTables(
            year=2026,
            irpf_monthly_brackets=(bracket,),
            irpf_annual_brackets=(bracket,),
            irpf_exemption_limit_monthly=5_000.0,
            irpf_reduction_upper_limit_monthly=7_350.0,
            dependent_deduction_annual=0.0,
            simplified_discount_cap_annual=0.0,
            equity_monthly_exemption=20_000.0,
            equity_swing_rate=0.15,
            equity_day_trade_rate=0.20,
            fii_rate=0.20,
            regressive_bands=(band,),
            come_cotas_rate=0.15,
            equity_fund_rate=0.15,
            dividend_monthly_threshold_per_source=50_000.0,
            dividend_withholding_rate=0.10,
            irpfm_income_floor_annual=600_000.0,
            irpfm_income_ceiling_annual=1_200_000.0,
            irpfm_max_rate=0.10,
        )
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_strategies(n: int) -> list[Strategy]:
    return list(BUILTIN_STRATEGIES[:n])


# ---------------------------------------------------------------------------
# Tests — T10 acceptance criteria
# ---------------------------------------------------------------------------


def _stub_run_simulation(candidates: Sequence[Strategy]) -> dict[str, SimulationResult]:
    """Map each strategy id → a deterministic SimulationResult by position."""
    return {s.id: make_sim_result(i) for i, s in enumerate(candidates)}


class TestOptimizeRanking:
    """ranked[0] is always the strategy with the best objective metric."""

    def _run(
        self,
        candidates: Sequence[Strategy],
        objective: Objective,
        state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> Recommendation:
        sim_map = _stub_run_simulation(candidates)

        def fake_run_simulation(
            state_: FinancialState,  # noqa: ARG001
            assumptions_: MarketAssumptions,  # noqa: ARG001
            config_: SimulationConfig,  # noqa: ARG001
            tax_fn_: TaxFn,  # noqa: ARG001
            tax_tables_by_year_: Sequence[TaxTables],  # noqa: ARG001
        ) -> SimulationResult:
            # Return results in order of the *current* strategy being evaluated.
            # Since optimize() iterates candidates in order, we track call count.
            raise NotImplementedError("Should be patched per-strategy via side_effect")

        # Build side_effect list: each call returns the next result in order.
        side_effects = [sim_map[s.id] for s in candidates]
        with patch("app.optimizer.engine.run_simulation", side_effect=side_effects):
            return optimize(
                state=state,
                candidates=candidates,
                objective=objective,
                assumptions=assumptions,
                config=sim_config,
                tax_fn=stub_tax_fn,
                tax_tables_by_year=tax_tables,
            )

    def test_max_median_net_worth_winner_is_last_candidate(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        """With stub results, terminal_p50 increases with index → last candidate wins."""
        candidates = make_strategies(3)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert rec.ranked[0].strategy.id == candidates[-1].id

    def test_max_success_probability_winner_is_last_candidate(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        """success_probability increases with index → last candidate wins."""
        candidates = make_strategies(3)
        rec = self._run(
            candidates,
            Objective.MAX_SUCCESS_PROBABILITY,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert rec.ranked[0].strategy.id == candidates[-1].id

    def test_min_lifetime_tax_winner_is_first_candidate(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        """lifetime_tax is derived from by_year; first candidate (lower p50) has lower tax sum → wins."""
        candidates = make_strategies(3)
        rec = self._run(
            candidates,
            Objective.MIN_LIFETIME_TAX,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        # First candidate has the smallest terminal_p50 → smallest lifetime_tax sum
        assert rec.ranked[0].strategy.id == candidates[0].id

    def test_ranked_tuple_length_matches_candidates(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(4)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert len(rec.ranked) == len(candidates)

    def test_ranked_items_are_strategy_outcomes(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(2)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        for outcome in rec.ranked:
            assert isinstance(outcome, StrategyOutcome)


class TestOptimizeExplanation:
    """explanation.winner_id == ranked[0].strategy.id, key_drivers non-empty."""

    def _run(
        self,
        candidates: Sequence[Strategy],
        objective: Objective,
        state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> Recommendation:
        sim_map = _stub_run_simulation(candidates)
        side_effects = [sim_map[s.id] for s in candidates]
        with patch("app.optimizer.engine.run_simulation", side_effect=side_effects):
            return optimize(
                state=state,
                candidates=candidates,
                objective=objective,
                assumptions=assumptions,
                config=sim_config,
                tax_fn=stub_tax_fn,
                tax_tables_by_year=tax_tables,
            )

    def test_winner_id_matches_ranked_first(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(3)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert rec.explanation.winner_id == rec.ranked[0].strategy.id

    def test_key_drivers_non_empty(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        for obj in Objective:
            candidates = make_strategies(2)
            rec = self._run(
                candidates,
                obj,
                minimal_state,
                assumptions,
                sim_config,
                stub_tax_fn,
                tax_tables,
            )
            assert len(rec.explanation.key_drivers) >= 1, f"No key_drivers for {obj}"

    def test_key_drivers_are_key_driver_instances(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(2)
        rec = self._run(
            candidates,
            Objective.MIN_LIFETIME_TAX,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        for kd in rec.explanation.key_drivers:
            assert isinstance(kd, KeyDriver)

    def test_min_lifetime_tax_has_tax_efficiency_driver(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(2)
        rec = self._run(
            candidates,
            Objective.MIN_LIFETIME_TAX,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert KeyDriver.TAX_EFFICIENCY in rec.explanation.key_drivers

    def test_explanation_objective_matches(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(2)
        for obj in Objective:
            rec = self._run(
                candidates,
                obj,
                minimal_state,
                assumptions,
                sim_config,
                stub_tax_fn,
                tax_tables,
            )
            assert rec.explanation.objective == obj


class TestOptimizeRunnerUp:
    """With 1 strategy: runner_up_id is None. With 2+: delta_vs_runner_up > 0."""

    def _run(
        self,
        candidates: Sequence[Strategy],
        objective: Objective,
        state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> Recommendation:
        sim_map = _stub_run_simulation(candidates)
        side_effects = [sim_map[s.id] for s in candidates]
        with patch("app.optimizer.engine.run_simulation", side_effect=side_effects):
            return optimize(
                state=state,
                candidates=candidates,
                objective=objective,
                assumptions=assumptions,
                config=sim_config,
                tax_fn=stub_tax_fn,
                tax_tables_by_year=tax_tables,
            )

    def test_single_strategy_runner_up_is_none(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(1)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert rec.explanation.runner_up_id is None

    def test_two_strategies_runner_up_is_not_none(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(2)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert rec.explanation.runner_up_id is not None

    def test_two_strategies_delta_positive_when_winner_beats_runner_up(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        """Stub gives clearly different values → delta_vs_runner_up > 0."""
        candidates = make_strategies(2)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert rec.explanation.delta_vs_runner_up > 0

    def test_runner_up_id_is_ranked_second(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(3)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert rec.explanation.runner_up_id == rec.ranked[1].strategy.id


class TestOptimizeReturnTypes:
    """optimize() returns a Recommendation with the correct types."""

    def _run(
        self,
        candidates: Sequence[Strategy],
        objective: Objective,
        state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> Recommendation:
        sim_map = _stub_run_simulation(candidates)
        side_effects = [sim_map[s.id] for s in candidates]
        with patch("app.optimizer.engine.run_simulation", side_effect=side_effects):
            return optimize(
                state=state,
                candidates=candidates,
                objective=objective,
                assumptions=assumptions,
                config=sim_config,
                tax_fn=stub_tax_fn,
                tax_tables_by_year=tax_tables,
            )

    def test_returns_recommendation(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(2)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert isinstance(rec, Recommendation)

    def test_explanation_is_explanation_type(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(2)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert isinstance(rec.explanation, Explanation)

    def test_winner_metric_is_float(
        self,
        minimal_state: FinancialState,
        assumptions: MarketAssumptions,
        sim_config: SimulationConfig,
        stub_tax_fn: TaxFn,
        tax_tables: list[TaxTables],
    ) -> None:
        candidates = make_strategies(2)
        rec = self._run(
            candidates,
            Objective.MAX_MEDIAN_NET_WORTH,
            minimal_state,
            assumptions,
            sim_config,
            stub_tax_fn,
            tax_tables,
        )
        assert isinstance(rec.explanation.winner_metric, float)
