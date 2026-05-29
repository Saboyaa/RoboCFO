"""POST /simulate endpoint."""
from __future__ import annotations

from contracts import (
    AssetClass,
    AssetClassAssumptions,
    Debt,
    FinancialState,
    Goal,
    GoalKind,
    Holding,
    IncomeKind,
    IncomeStream,
    MarketAssumptions,
    SimulationConfig,
    SimulationResult,
    Taxpayer,
)
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
# Conversion helpers: Pydantic In → contracts dataclasses
# ---------------------------------------------------------------------------


def _to_financial_state(s: FinancialStateIn) -> FinancialState:
    return FinancialState(
        taxpayer=Taxpayer(
            age=s.taxpayer.age,
            retirement_age=s.taxpayer.retirement_age,
            dependents=s.taxpayer.dependents,
            state=s.taxpayer.state,
        ),
        base_year=s.base_year,
        holdings=tuple(
            Holding(
                id=h.id, name=h.name, asset_class=h.asset_class,
                balance=h.balance, cost_basis=h.cost_basis,
                acquisition_year=h.acquisition_year,
            )
            for h in s.holdings
        ),
        debts=tuple(
            Debt(
                id=d.id, name=d.name, balance=d.balance,
                annual_interest_rate=d.annual_interest_rate,
                minimum_payment=d.minimum_payment,
            )
            for d in s.debts
        ),
        incomes=tuple(
            IncomeStream(
                id=i.id, name=i.name, monthly_amount=i.monthly_amount,
                kind=i.kind, start_year=i.start_year, end_year=i.end_year,
            )
            for i in s.incomes
        ),
        goals=tuple(
            Goal(
                id=g.id, name=g.name, kind=g.kind,
                target_amount=g.target_amount, target_year=g.target_year,
            )
            for g in s.goals
        ),
        annual_expenses=s.annual_expenses,
        deductible_expenses_annual=s.deductible_expenses_annual,
    )


def _to_market_assumptions(a: MarketAssumptionsIn) -> MarketAssumptions:
    return MarketAssumptions(
        mean_real_return=a.mean_real_return,
        return_volatility=a.return_volatility,
        ipca_mean=a.ipca_mean,
        ipca_volatility=a.ipca_volatility,
        per_class=tuple(
            AssetClassAssumptions(
                asset_class=pc.asset_class,
                mean_real_return=pc.mean_real_return,
                return_volatility=pc.return_volatility,
            )
            for pc in a.per_class
        ),
    )


def _to_sim_config(c: SimulationConfigIn) -> SimulationConfig:
    return SimulationConfig(years=c.years, n_paths=c.n_paths, seed=c.seed)


def _result_out(r: SimulationResult) -> SimulationResultOut:
    return SimulationResultOut(
        success_probability=r.success_probability,
        terminal_p10=r.terminal_p10,
        terminal_p50=r.terminal_p50,
        terminal_p90=r.terminal_p90,
        by_year=[
            YearPercentilesOut(year=yp.year, p10=yp.p10, p50=yp.p50, p90=yp.p90)
            for yp in r.by_year
        ],
        paths_simulated=r.paths_simulated,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/simulate", response_model=SimulationResultOut)
async def simulate(body: SimulateRequest) -> SimulationResultOut:
    from app.data.loader import load_tax_tables
    from app.simulation.monte_carlo import run_simulation
    from app.tax.annual import compute_annual_tax

    state = _to_financial_state(body.state)
    assumptions = _to_market_assumptions(body.assumptions)
    config = _to_sim_config(body.config)
    tables = [load_tax_tables(state.base_year)]

    result = run_simulation(state, assumptions, config, compute_annual_tax, tables)
    return _result_out(result)


__all__ = [
    "router",
    "FinancialStateIn", "MarketAssumptionsIn", "SimulationConfigIn",
    "SimulationResultOut", "YearPercentilesOut",
    "_to_financial_state", "_to_market_assumptions", "_to_sim_config", "_result_out",
]
