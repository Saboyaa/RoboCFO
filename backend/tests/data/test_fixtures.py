from contracts import (
    AssetClass,
    FinancialState,
    MarketAssumptions,
    SimulationConfig,
)

from app.data.loader import load_dev_sim_config, load_fixture, load_market_assumptions


def test_load_sample_state_returns_financial_state() -> None:
    state = load_fixture("sample_state")
    assert isinstance(state, FinancialState)


def test_sample_state_taxpayer_age() -> None:
    state = load_fixture("sample_state")
    assert state.taxpayer.age == 35


def test_sample_state_has_stocks_holding() -> None:
    state = load_fixture("sample_state")
    classes = {h.asset_class for h in state.holdings}
    assert AssetClass.STOCKS in classes


def test_sample_state_has_fixed_income_holding() -> None:
    state = load_fixture("sample_state")
    classes = {h.asset_class for h in state.holdings}
    assert AssetClass.TAXABLE_FIXED_INCOME in classes


def test_sample_state_has_exempt_fixed_income() -> None:
    state = load_fixture("sample_state")
    classes = {h.asset_class for h in state.holdings}
    assert AssetClass.EXEMPT_FIXED_INCOME in classes


def test_sample_state_has_fii_holding() -> None:
    state = load_fixture("sample_state")
    classes = {h.asset_class for h in state.holdings}
    assert AssetClass.FII in classes


def test_sample_state_has_at_least_one_debt() -> None:
    state = load_fixture("sample_state")
    assert len(state.debts) >= 1


def test_sample_state_has_income_stream() -> None:
    state = load_fixture("sample_state")
    assert len(state.incomes) >= 1


def test_sample_state_has_retirement_goal() -> None:
    from contracts import GoalKind
    state = load_fixture("sample_state")
    kinds = {g.kind for g in state.goals}
    assert GoalKind.RETIREMENT in kinds


def test_load_market_assumptions_has_per_class_overrides() -> None:
    assumptions = load_market_assumptions()
    assert isinstance(assumptions, MarketAssumptions)
    assert len(assumptions.per_class) >= 2


def test_market_assumptions_has_stocks_override() -> None:
    assumptions = load_market_assumptions()
    classes = {a.asset_class for a in assumptions.per_class}
    assert AssetClass.STOCKS in classes


def test_market_assumptions_has_fixed_income_override() -> None:
    assumptions = load_market_assumptions()
    classes = {a.asset_class for a in assumptions.per_class}
    assert AssetClass.TAXABLE_FIXED_INCOME in classes


def test_dev_sim_config() -> None:
    cfg = load_dev_sim_config()
    assert isinstance(cfg, SimulationConfig)
    assert cfg.seed == 42
    assert cfg.n_paths == 100
    assert cfg.years == 30


def test_unknown_fixture_raises_file_not_found() -> None:
    import pytest
    with pytest.raises(FileNotFoundError):
        load_fixture("nonexistent_fixture")
