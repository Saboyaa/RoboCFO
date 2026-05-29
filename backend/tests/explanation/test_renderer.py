"""Tests for explanation renderer — T12."""
from __future__ import annotations

import os

import pytest
from contracts import Explanation, KeyDriver, Objective

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ALL_KEY_DRIVERS = list(KeyDriver)

FULL_EXPLANATION = Explanation(
    objective=Objective.MAX_MEDIAN_NET_WORTH,
    winner_id="invest_renda_fixa",
    winner_metric=1_500_000.0,
    runner_up_id="equilibrado",
    delta_vs_runner_up=75_000.0,
    key_drivers=tuple(ALL_KEY_DRIVERS),
)

MINIMAL_EXPLANATION = Explanation(
    objective=Objective.MIN_LIFETIME_TAX,
    winner_id="winner",
    winner_metric=50_000.0,
    runner_up_id=None,
    delta_vs_runner_up=0.0,
    key_drivers=(),
)


# ---------------------------------------------------------------------------
# Template path (use_llm=False)
# ---------------------------------------------------------------------------


def test_render_returns_string() -> None:
    from app.explanation.renderer import render_explanation

    result = render_explanation(FULL_EXPLANATION, use_llm=False)
    assert isinstance(result, str)
    assert len(result) > 0


def test_render_contains_winner_id() -> None:
    from app.explanation.renderer import render_explanation

    result = render_explanation(FULL_EXPLANATION, use_llm=False)
    assert FULL_EXPLANATION.winner_id in result


def test_render_contains_objective_name() -> None:
    from app.explanation.renderer import render_explanation

    result = render_explanation(FULL_EXPLANATION, use_llm=False)
    # Objective value should appear in the output
    assert Objective.MAX_MEDIAN_NET_WORTH.value in result


def test_render_contains_winner_metric() -> None:
    from app.explanation.renderer import render_explanation

    result = render_explanation(FULL_EXPLANATION, use_llm=False)
    # 1500000.0 should appear in some form
    assert "1500000" in result or "1.500.000" in result or "1,500,000" in result


def test_render_contains_runner_up_id() -> None:
    from app.explanation.renderer import render_explanation

    result = render_explanation(FULL_EXPLANATION, use_llm=False)
    assert FULL_EXPLANATION.runner_up_id in result


def test_render_handles_no_runner_up() -> None:
    from app.explanation.renderer import render_explanation

    result = render_explanation(MINIMAL_EXPLANATION, use_llm=False)
    assert isinstance(result, str)
    assert len(result) > 0


def test_render_no_runner_up_does_not_crash() -> None:
    """runner_up_id=None must not cause a KeyError or AttributeError."""
    from app.explanation.renderer import render_explanation

    result = render_explanation(MINIMAL_EXPLANATION, use_llm=False)
    assert "None" not in result  # None should be handled gracefully in template


def test_render_all_key_drivers_have_portuguese_labels() -> None:
    """Every KeyDriver enum value must map to a non-empty Portuguese label."""
    from app.explanation.renderer import render_explanation

    result = render_explanation(FULL_EXPLANATION, use_llm=False)
    # All 8 drivers must produce some Portuguese content (not the raw enum value alone)
    for driver in ALL_KEY_DRIVERS:
        assert driver.value in result or any(
            label in result
            for label in [
                "Redutor",
                "Eficiência",
                "Dívida",
                "Sequência",
                "Isenção",
                "Prazo",
                "IRPFM",
                "Alocação",
            ]
        ), f"KeyDriver {driver.value} not represented in output"


def test_render_each_key_driver_portuguese_label() -> None:
    """Each individual KeyDriver produces a Portuguese label in isolation."""
    from app.explanation.renderer import render_explanation

    expected_labels = {
        KeyDriver.IRPF_REDUCER_BENEFIT: "Redutor",
        KeyDriver.TAX_EFFICIENCY: "Eficiência",
        KeyDriver.DEBT_COST_REDUCTION: "Dívida",
        KeyDriver.SEQUENCE_OF_RETURNS_RISK: "Sequência",
        KeyDriver.VARIABLE_INCOME_EXEMPTION: "Isenção",
        KeyDriver.FIXED_INCOME_HOLDING_PERIOD: "Prazo",
        KeyDriver.IRPFM_THRESHOLD: "IRPFM",
        KeyDriver.ASSET_ALLOCATION: "Alocação",
    }
    for driver, label in expected_labels.items():
        explanation = Explanation(
            objective=Objective.MAX_SUCCESS_PROBABILITY,
            winner_id="w",
            winner_metric=0.8,
            runner_up_id=None,
            delta_vs_runner_up=0.0,
            key_drivers=(driver,),
        )
        result = render_explanation(explanation, use_llm=False)
        assert label in result, f"Expected '{label}' for {driver.value} in:\n{result}"


def test_render_delta_vs_runner_up_appears() -> None:
    from app.explanation.renderer import render_explanation

    result = render_explanation(FULL_EXPLANATION, use_llm=False)
    assert "75000" in result or "75.000" in result


# ---------------------------------------------------------------------------
# LLM path (use_llm=True)
# ---------------------------------------------------------------------------

_HAS_KEY = bool(os.environ.get("DEEPSEEK_API_KEY")) and os.environ.get(
    "LLM_PROVIDER", "none"
) not in ("none",)


def test_llm_path_raises_environment_error_when_provider_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If LLM_PROVIDER is 'none', EnvironmentError must be raised with a clear message."""
    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from app.explanation import renderer

    # Reload module to pick up env changes (renderer caches nothing at module level)
    with pytest.raises(EnvironmentError, match=r"(?i)(provider|key|llm|deepseek)"):
        renderer.render_explanation(FULL_EXPLANATION, use_llm=True)


def test_llm_path_raises_environment_error_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If DEEPSEEK_API_KEY is absent, EnvironmentError must be raised."""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from app.explanation import renderer

    with pytest.raises(EnvironmentError, match=r"(?i)(api.?key|deepseek)"):
        renderer.render_explanation(FULL_EXPLANATION, use_llm=True)


@pytest.mark.skipif(not _HAS_KEY, reason="DEEPSEEK_API_KEY not set or LLM_PROVIDER=none")
def test_llm_path_returns_non_empty_string() -> None:
    from app.explanation.renderer import render_explanation

    result = render_explanation(FULL_EXPLANATION, use_llm=True)
    assert isinstance(result, str)
    assert len(result) > 50  # should be a real narrative, not empty
