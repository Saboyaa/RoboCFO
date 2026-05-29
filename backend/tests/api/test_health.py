"""Health endpoint and CORS tests — pre-existing; updated to async transport
to handle non-ASCII latin-1 header values (disclaimer header contains Portuguese
characters that starlette encodes as latin-1; the sync TestClient in newer starlette
versions enforces ASCII for header encoding).
"""
from __future__ import annotations

import httpx
import pytest

from app.main import app

DISCLAIMER = (
    "Este sistema é um simulador educacional. Não constitui assessoria financeira."
)


@pytest.fixture
def asgi_app() -> object:
    return app


@pytest.mark.anyio
async def test_health_returns_ok(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_disclaimer_header_present_on_health(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        resp = await client.get("/health")
    assert resp.headers["x-robo-cfo-disclaimer"] == DISCLAIMER


@pytest.mark.anyio
async def test_disclaimer_header_present_on_unknown_route(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        resp = await client.get("/nonexistent-route")
    assert "x-robo-cfo-disclaimer" in resp.headers


@pytest.mark.anyio
async def test_cors_preflight_vite_origin(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.anyio
async def test_cors_preflight_react_origin(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
