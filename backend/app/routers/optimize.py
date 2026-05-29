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
async def optimize_endpoint(body: OptimizeRequest) -> RecommendationOut:
    """Evaluate candidate strategies via real Monte Carlo and return ranked Recommendation."""
    from contracts import Strategy

    from app.data.loader import load_tax_tables
    from app.optimizer.engine import optimize
    from app.optimizer.strategies import BUILTIN_STRATEGIES
    from app.tax.annual import compute_annual_tax

    from .simulate import (
        _result_out,
        _to_financial_state,
        _to_market_assumptions,
        _to_sim_config,
    )

    state = _to_financial_state(body.state)
    assumptions = _to_market_assumptions(body.assumptions)
    config = _to_sim_config(body.config)
    tables = [load_tax_tables(state.base_year)]

    # Use provided candidates if given, otherwise run all built-in strategies
    candidates: list[Strategy] = (
        [Strategy(id=c.id, name=c.name, description=c.description) for c in body.candidates]
        if body.candidates
        else list(BUILTIN_STRATEGIES)
    )

    recommendation = optimize(
        state=state,
        candidates=candidates,
        objective=body.objective,
        assumptions=assumptions,
        config=config,
        tax_fn=compute_annual_tax,
        tax_tables_by_year=tables,
    )

    ranked_out = [
        StrategyOutcomeOut(
            strategy=StrategyOut(
                id=o.strategy.id,
                name=o.strategy.name,
                description=o.strategy.description,
            ),
            result=_result_out(o.result),
            lifetime_tax=o.lifetime_tax,
        )
        for o in recommendation.ranked
    ]

    exp = recommendation.explanation
    explanation_out = ExplanationOut(
        objective=exp.objective,
        winner_id=exp.winner_id,
        winner_metric=exp.winner_metric,
        runner_up_id=exp.runner_up_id,
        delta_vs_runner_up=exp.delta_vs_runner_up,
        key_drivers=[kd.value for kd in exp.key_drivers],
    )

    return RecommendationOut(
        objective=recommendation.objective,
        ranked=ranked_out,
        explanation=explanation_out,
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
