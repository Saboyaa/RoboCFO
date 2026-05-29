"""Tests for backend/app/main.py — T11.

We use httpx.AsyncClient with ASGITransport rather than Starlette's sync TestClient
because the sync TestClient in Starlette 1.2 calls .decode() (UTF-8) on ASGI header bytes,
which fails for latin-1 non-ASCII characters in the disclaimer header.  The async transport
preserves the header values correctly.
"""
from __future__ import annotations

import httpx
import pytest

DISCLAIMER = (
    "Este sistema é um simulador educacional. Não constitui assessoria financeira."
)


@pytest.fixture
def asgi_app() -> object:
    from app.main import app

    return app


@pytest.mark.anyio
async def test_health_returns_ok(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app), base_url="http://test"  # type: ignore[arg-type]
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_disclaimer_header_on_health(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app), base_url="http://test"  # type: ignore[arg-type]
    ) as client:
        response = await client.get("/health")
    assert response.headers["x-robo-cfo-disclaimer"] == DISCLAIMER


@pytest.mark.anyio
async def test_disclaimer_header_on_404(asgi_app: object) -> None:
    """Middleware must inject header even on non-2xx responses."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app), base_url="http://test"  # type: ignore[arg-type]
    ) as client:
        response = await client.get("/nonexistent-route")
    assert "x-robo-cfo-disclaimer" in response.headers
    assert response.headers["x-robo-cfo-disclaimer"] == DISCLAIMER


@pytest.mark.anyio
async def test_cors_allowed_origin_localhost_5173(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app), base_url="http://test"  # type: ignore[arg-type]
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.anyio
async def test_cors_allowed_origin_localhost_3000(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app), base_url="http://test"  # type: ignore[arg-type]
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.anyio
async def test_cors_disallowed_origin(asgi_app: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app), base_url="http://test"  # type: ignore[arg-type]
    ) as client:
        response = await client.get(
            "/health", headers={"Origin": "http://evil.example.com"}
        )
    # CORS middleware should not echo back the disallowed origin
    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"
