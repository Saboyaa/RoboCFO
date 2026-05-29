"""FastAPI application entry point — Robo-CFO Brazil."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Load .env from repo root (two levels up from backend/)
_ENV_PATH = Path(__file__).parent.parent.parent / ".." / ".." / ".env"
load_dotenv(_ENV_PATH.resolve())

DISCLAIMER = (
    "Este sistema é um simulador educacional. Não constitui assessoria financeira."
)

app = FastAPI(title="Robo-CFO Brazil", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Disclaimer middleware — injected on every response
@app.middleware("http")
async def add_disclaimer_header(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Robo-CFO-Disclaimer"] = DISCLAIMER
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from app.routers import optimize as optimize_router  # noqa: E402
from app.routers import simulate as simulate_router  # noqa: E402

app.include_router(simulate_router.router)
app.include_router(optimize_router.router)

__all__ = ["app"]
