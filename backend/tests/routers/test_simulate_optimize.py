"""Tests for POST /simulate and POST /optimize — T13."""
from __future__ import annotations

import httpx
import pytest

DISCLAIMER = (
    "Este sistema é um simulador educacional. Não constitui assessoria financeira."
)

# ---------------------------------------------------------------------------
# Minimal valid payloads
# ---------------------------------------------------------------------------

TAXPAYER = {
    "age": 40,
    "retirement_age": 65,
    "dependents": 0,
    "state": None,
}

FINANCIAL_STATE = {
    "taxpayer": TAXPAYER,
    "base_year": 2026,
    "holdings": [],
    "debts": [],
    "incomes": [],
    "goals": [],
    "annual_expenses": 0.0,
    "deductible_expenses_annual": 0.0,
}

MARKET_ASSUMPTIONS = {
    "mean_real_return": 0.05,
    "return_volatility": 0.12,
    "ipca_mean": 0.04,
    "ipca_volatility": 0.015,
    "per_class": [],
}

SIM_CONFIG = {
    "years": 10,
    "n_paths": 100,
    "seed": 42,
}

SIMULATE_BODY = {
    "state": FINANCIAL_STATE,
    "assumptions": MARKET_ASSUMPTIONS,
    "config": SIM_CONFIG,
}

STRATEGY = {
    "id": "invest_renda_fixa",
    "name": "Investir primeiro (renda fixa)",
    "description": "Prioriza investimentos em renda fixa antes de quitar dívidas.",
}

OPTIMIZE_BODY = {
    "state": FINANCIAL_STATE,
    "candidates": [STRATEGY],
    "objective": "max_median_net_worth",
    "assumptions": MARKET_ASSUMPTIONS,
    "config": SIM_CONFIG,
}


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def asgi_app() -> object:
    from app.main import app

    return app


# ---------------------------------------------------------------------------
# POST /simulate
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_simulate_returns_200(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/simulate", json=SIMULATE_BODY)
    assert r.status_code == 200


@pytest.mark.anyio
async def test_simulate_response_shape(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/simulate", json=SIMULATE_BODY)
    data = r.json()
    assert "success_probability" in data
    assert "terminal_p10" in data
    assert "terminal_p50" in data
    assert "terminal_p90" in data
    assert "by_year" in data
    assert "paths_simulated" in data


@pytest.mark.anyio
async def test_simulate_has_disclaimer_header(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/simulate", json=SIMULATE_BODY)
    assert r.headers.get("x-robo-cfo-disclaimer") == DISCLAIMER


@pytest.mark.anyio
async def test_simulate_missing_field_returns_422(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        # Missing 'config' field
        r = await client.post("/simulate", json={"state": FINANCIAL_STATE})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /optimize
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_optimize_returns_200(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize", json=OPTIMIZE_BODY)
    assert r.status_code == 200


@pytest.mark.anyio
async def test_optimize_response_shape(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize", json=OPTIMIZE_BODY)
    data = r.json()
    assert "objective" in data
    assert "ranked" in data
    assert "explanation" in data
    # Check explanation shape
    exp = data["explanation"]
    assert "objective" in exp
    assert "winner_id" in exp
    assert "winner_metric" in exp
    assert "runner_up_id" in exp
    assert "delta_vs_runner_up" in exp
    assert "key_drivers" in exp


@pytest.mark.anyio
async def test_optimize_has_disclaimer_header(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize", json=OPTIMIZE_BODY)
    assert r.headers.get("x-robo-cfo-disclaimer") == DISCLAIMER


@pytest.mark.anyio
async def test_optimize_missing_field_returns_422(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        # Missing 'objective' and 'candidates'
        r = await client.post("/optimize", json={"state": FINANCIAL_STATE})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_optimize_invalid_objective_returns_422(asgi_app: object) -> None:
    body = {**OPTIMIZE_BODY, "objective": "not_a_valid_objective"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize", json=body)
    assert r.status_code == 422
