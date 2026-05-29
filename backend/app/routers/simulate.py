"""POST /simulate endpoint — T13.

Stub implementation: accepts a valid-shaped body, returns a hardcoded but
valid-shaped SimulationResult.  The real Monte Carlo engine will replace
the stub call in a later task.
"""
from __future__ import annotations

from contracts import AssetClass, GoalKind, IncomeKind
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic v2 request models mirroring contracts types
# ---------------------------------------------------------------------------


class TaxpayerIn(BaseModel):
    age: int
    retirement_age: int
    dependents: int = 0
    state: str | None = None


class HoldingIn(BaseModel):
    id: str
    name: str
    asset_class: AssetClass
    balance: float
    cost_basis: float | None = None
    acquisition_year: int | None = None


class DebtIn(BaseModel):
    id: str
    name: str
    balance: float
    annual_interest_rate: float
    minimum_payment: float


class IncomeStreamIn(BaseModel):
    id: str
    name: str
    monthly_amount: float
    kind: IncomeKind
    start_year: int
    end_year: int | None = None


class GoalIn(BaseModel):
    id: str
    name: str
    kind: GoalKind
    target_amount: float
    target_year: int


class FinancialStateIn(BaseModel):
    taxpayer: TaxpayerIn
    base_year: int
    holdings: list[HoldingIn] = []
    debts: list[DebtIn] = []
    incomes: list[IncomeStreamIn] = []
    goals: list[GoalIn] = []
    annual_expenses: float = 0.0
    deductible_expenses_annual: float = 0.0


class AssetClassAssumptionsIn(BaseModel):
    asset_class: AssetClass
    mean_real_return: float
    return_volatility: float


class MarketAssumptionsIn(BaseModel):
    mean_real_return: float
    return_volatility: float
    ipca_mean: float = 0.04
    ipca_volatility: float = 0.015
    per_class: list[AssetClassAssumptionsIn] = []


class SimulationConfigIn(BaseModel):
    years: int
    n_paths: int = 10_000
    seed: int | None = None


class SimulateRequest(BaseModel):
    state: FinancialStateIn
    assumptions: MarketAssumptionsIn
    config: SimulationConfigIn


# ---------------------------------------------------------------------------
# Pydantic v2 response models mirroring SimulationResult
# ---------------------------------------------------------------------------


class YearPercentilesOut(BaseModel):
    year: int
    p10: float
    p50: float
    p90: float


class SimulationResultOut(BaseModel):
    success_probability: float
    terminal_p10: float
    terminal_p50: float
    terminal_p90: float
    by_year: list[YearPercentilesOut]
    paths_simulated: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/simulate", response_model=SimulationResultOut)
async def simulate(body: SimulateRequest) -> SimulationResultOut:
    """Run a Monte Carlo simulation.

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
    return SimulationResultOut(
        success_probability=0.75,
        terminal_p10=by_year[-1].p10 if by_year else 0.0,
        terminal_p50=by_year[-1].p50 if by_year else 0.0,
        terminal_p90=by_year[-1].p90 if by_year else 0.0,
        by_year=by_year,
        paths_simulated=body.config.n_paths,
    )


__all__ = ["router", "FinancialStateIn", "MarketAssumptionsIn", "SimulationConfigIn"]
