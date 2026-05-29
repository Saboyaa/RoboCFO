"""Tests for POST /optimize/explain — T14."""
from __future__ import annotations

import httpx
import pytest

DISCLAIMER = (
    "Este sistema é um simulador educacional. Não constitui assessoria financeira."
)

EXPLANATION_BODY = {
    "objective": "max_median_net_worth",
    "winner_id": "invest_renda_fixa",
    "winner_metric": 1_500_000.0,
    "runner_up_id": "equilibrado",
    "delta_vs_runner_up": 75_000.0,
    "key_drivers": ["tax_efficiency", "asset_allocation"],
}

EXPLAIN_BODY_TEMPLATE = {
    "explanation": EXPLANATION_BODY,
    "use_llm": False,
}

EXPLAIN_BODY_LLM = {
    "explanation": EXPLANATION_BODY,
    "use_llm": True,
}


@pytest.fixture
def asgi_app() -> object:
    from app.main import app

    return app


# ---------------------------------------------------------------------------
# Template path (use_llm=False)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_explain_template_returns_200(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize/explain", json=EXPLAIN_BODY_TEMPLATE)
    assert r.status_code == 200


@pytest.mark.anyio
async def test_explain_template_returns_text_field(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize/explain", json=EXPLAIN_BODY_TEMPLATE)
    data = r.json()
    assert "text" in data
    assert isinstance(data["text"], str)
    assert len(data["text"]) > 0


@pytest.mark.anyio
async def test_explain_text_contains_winner_id(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize/explain", json=EXPLAIN_BODY_TEMPLATE)
    assert "invest_renda_fixa" in r.json()["text"]


@pytest.mark.anyio
async def test_explain_has_disclaimer_header(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize/explain", json=EXPLAIN_BODY_TEMPLATE)
    assert r.headers.get("x-robo-cfo-disclaimer") == DISCLAIMER


@pytest.mark.anyio
async def test_explain_missing_explanation_returns_422(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize/explain", json={"use_llm": False})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# LLM path with no key → 503
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_explain_llm_no_key_returns_503(
    asgi_app: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize/explain", json=EXPLAIN_BODY_LLM)
    assert r.status_code == 503
    # Response should have a clear message
    data = r.json()
    assert "detail" in data
    assert len(data["detail"]) > 0


@pytest.mark.anyio
async def test_explain_llm_provider_none_returns_503(
    asgi_app: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        r = await client.post("/optimize/explain", json=EXPLAIN_BODY_LLM)
    assert r.status_code == 503
