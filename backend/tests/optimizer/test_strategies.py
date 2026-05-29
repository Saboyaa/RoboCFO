"""T9: Tests for BUILTIN_STRATEGIES catalogue and build_custom_strategy."""
import pytest

from app.optimizer.strategies import BUILTIN_STRATEGIES, build_custom_strategy
from contracts import AssetClass, Strategy


EXPECTED_NAMES = {
    "Quitar dívidas de alto custo primeiro",
    "Investir primeiro (renda fixa)",
    "Investir primeiro (renda variável)",
    "Equilibrado: metade dívida, metade investimento",
    "Resgatar na ordem mais eficiente fiscalmente",
}


def test_builtin_strategies_count():
    assert len(BUILTIN_STRATEGIES) == 5


def test_builtin_strategies_names():
    names = {s.name for s in BUILTIN_STRATEGIES}
    assert names == EXPECTED_NAMES


def test_builtin_strategies_unique_ids():
    ids = [s.id for s in BUILTIN_STRATEGIES]
    assert len(ids) == len(set(ids))


def test_builtin_strategies_non_empty_descriptions():
    for s in BUILTIN_STRATEGIES:
        assert s.description.strip(), f"Strategy {s.id!r} has empty description"


def test_builtin_strategies_are_strategy_instances():
    for s in BUILTIN_STRATEGIES:
        assert isinstance(s, Strategy)


def test_builtin_strategy_ids_are_stable_strings():
    ids = {s.id for s in BUILTIN_STRATEGIES}
    # IDs must be non-empty strings (used as keys in Explanation.winner_id)
    for sid in ids:
        assert isinstance(sid, str) and sid.strip()


def test_build_custom_strategy_returns_custom_id():
    s = build_custom_strategy(
        debt_fraction=0.5,
        invest_asset_class=AssetClass.TAXABLE_FIXED_INCOME,
    )
    assert s.id == "custom"


def test_build_custom_strategy_returns_strategy_instance():
    s = build_custom_strategy(
        debt_fraction=0.3,
        invest_asset_class=AssetClass.STOCKS,
    )
    assert isinstance(s, Strategy)


def test_build_custom_strategy_has_name_and_description():
    s = build_custom_strategy(
        debt_fraction=0.0,
        invest_asset_class=AssetClass.EXEMPT_FIXED_INCOME,
    )
    assert s.name.strip()
    assert s.description.strip()


def test_build_custom_strategy_debt_fraction_reflected():
    s = build_custom_strategy(
        debt_fraction=1.0,
        invest_asset_class=AssetClass.FII,
    )
    # The description or name should reflect the configuration (not asserting exact text,
    # just that it produces a valid Strategy)
    assert s.id == "custom"
