"""POST /optimize and POST /optimize/explain endpoints — T13, T14.

Stub implementation: accepts a valid-shaped body, returns a hardcoded but
valid-shaped Recommendation.  The real optimizer will replace the stub call
in a later task.
"""
from __future__ import annotations

from contracts import Explanation, KeyDriver, Objective
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .simulate import (
    FinancialStateIn,
    MarketAssumptionsIn,
    SimulationConfigIn,
    SimulationResultOut,
    YearPercentilesOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic v2 request models
# ---------------------------------------------------------------------------


class StrategyIn(BaseModel):
    id: str
    name: str
    description: str


class OptimizeRequest(BaseModel):
    state: FinancialStateIn
    candidates: list[StrategyIn]
    objective: Objective
    assumptions: MarketAssumptionsIn
    config: SimulationConfigIn


# ---------------------------------------------------------------------------
# Pydantic v2 response models mirroring Recommendation
# ---------------------------------------------------------------------------


class StrategyOut(BaseModel):
    id: str
    name: str
    description: str


class StrategyOutcomeOut(BaseModel):
    strategy: StrategyOut
    result: SimulationResultOut
    lifetime_tax: float


class ExplanationOut(BaseModel):
    objective: Objective
    winner_id: str
    winner_metric: float
    runner_up_id: str | None
    delta_vs_runner_up: float
    key_drivers: list[str]


class RecommendationOut(BaseModel):
    objective: Objective
    ranked: list[StrategyOutcomeOut]
    explanation: ExplanationOut


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/optimize", response_model=RecommendationOut)
async def optimize(body: OptimizeRequest) -> RecommendationOut:
    """Evaluate candidate strategies and return a ranked Recommendation.

    Currently stubbed — returns a hardcoded valid-shaped result.
    """
    base = body.state.base_year
    years = body.config.years
    by_year = [
        YearPercentilesOut(
            year=base + i,
            p10=100_000.0 * (1 + i * 0.03),
            p50=200_000.0 * (1 + i * 0.05),
            p90=300_000.0 * (1 + i * 0.07),
        )
        for i in range(1, years + 1)
    ]

    winner = body.candidates[0] if body.candidates else StrategyIn(
        id="default", name="Default", description=""
    )
    runner_up = body.candidates[1] if len(body.candidates) > 1 else None

    stub_result = SimulationResultOut(
        success_probability=0.75,
        terminal_p10=by_year[-1].p10 if by_year else 0.0,
        terminal_p50=by_year[-1].p50 if by_year else 0.0,
        terminal_p90=by_year[-1].p90 if by_year else 0.0,
        by_year=by_year,
        paths_simulated=body.config.n_paths,
    )

    ranked = [
        StrategyOutcomeOut(
            strategy=StrategyOut(**candidate.model_dump()),
            result=stub_result,
            lifetime_tax=50_000.0,
        )
        for candidate in body.candidates
    ]

    explanation = ExplanationOut(
        objective=body.objective,
        winner_id=winner.id,
        winner_metric=stub_result.terminal_p50,
        runner_up_id=runner_up.id if runner_up else None,
        delta_vs_runner_up=0.0,
        key_drivers=[KeyDriver.TAX_EFFICIENCY.value, KeyDriver.ASSET_ALLOCATION.value],
    )

    return RecommendationOut(
        objective=body.objective,
        ranked=ranked,
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# POST /optimize/explain — T14
# ---------------------------------------------------------------------------


class ExplainRequest(BaseModel):
    explanation: ExplanationOut
    use_llm: bool = False


class ExplainResponse(BaseModel):
    text: str


@router.post("/optimize/explain", response_model=ExplainResponse)
async def explain(body: ExplainRequest) -> ExplainResponse:
    """Render an Explanation to a Portuguese narrative.

    Routes to render_explanation(use_llm=...).
    If use_llm=True and the LLM is not configured, returns 503.
    """
    from app.explanation.renderer import render_explanation

    # Reconstruct the contracts.Explanation dataclass from the request body
    exp = Explanation(
        objective=body.explanation.objective,
        winner_id=body.explanation.winner_id,
        winner_metric=body.explanation.winner_metric,
        runner_up_id=body.explanation.runner_up_id,
        delta_vs_runner_up=body.explanation.delta_vs_runner_up,
        key_drivers=tuple(
            KeyDriver(kd) for kd in body.explanation.key_drivers
        ),
    )

    try:
        text = render_explanation(exp, use_llm=body.use_llm)
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return ExplainResponse(text=text)


__all__ = ["router"]
