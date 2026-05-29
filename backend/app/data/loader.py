"""Load versioned tax-table and fixture data from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
    IRPFBracket,
    MarketAssumptions,
    RegressiveBand,
    SimulationConfig,
    Taxpayer,
    TaxTables,
    Year,
)

_DATA_DIR = Path(__file__).parent
_TAX_TABLES_DIR = _DATA_DIR / "tax_tables"
_FIXTURES_DIR = _DATA_DIR / "fixtures"


def load_tax_tables(year: Year) -> TaxTables:
    path = _TAX_TABLES_DIR / f"{year}.json"
    if not path.exists():
        raise FileNotFoundError(f"No tax tables for year {year} at {path}")
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return _parse_tax_tables(raw)


def load_fixture(name: str) -> FinancialState:
    path = _FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No fixture '{name}' at {path}")
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return _parse_financial_state(raw)


def load_market_assumptions() -> MarketAssumptions:
    path = _FIXTURES_DIR / "market_assumptions.json"
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return MarketAssumptions(
        mean_real_return=raw["mean_real_return"],
        return_volatility=raw["return_volatility"],
        ipca_mean=raw["ipca_mean"],
        ipca_volatility=raw["ipca_volatility"],
        per_class=tuple(
            AssetClassAssumptions(
                asset_class=AssetClass(pc["asset_class"]),
                mean_real_return=pc["mean_real_return"],
                return_volatility=pc["return_volatility"],
            )
            for pc in raw.get("per_class", [])
        ),
    )


def load_dev_sim_config() -> SimulationConfig:
    return SimulationConfig(years=30, n_paths=100, seed=42)


def _parse_financial_state(raw: dict[str, Any]) -> FinancialState:
    tp = raw["taxpayer"]
    return FinancialState(
        taxpayer=Taxpayer(
            age=tp["age"],
            retirement_age=tp["retirement_age"],
            dependents=tp.get("dependents", 0),
            state=tp.get("state"),
        ),
        base_year=raw["base_year"],
        holdings=tuple(
            Holding(
                id=h["id"],
                name=h["name"],
                asset_class=AssetClass(h["asset_class"]),
                balance=h["balance"],
                cost_basis=h.get("cost_basis"),
                acquisition_year=h.get("acquisition_year"),
            )
            for h in raw.get("holdings", [])
        ),
        debts=tuple(
            Debt(
                id=d["id"],
                name=d["name"],
                balance=d["balance"],
                annual_interest_rate=d["annual_interest_rate"],
                minimum_payment=d["minimum_payment"],
            )
            for d in raw.get("debts", [])
        ),
        incomes=tuple(
            IncomeStream(
                id=i["id"],
                name=i["name"],
                monthly_amount=i["monthly_amount"],
                kind=IncomeKind(i["kind"]),
                start_year=i["start_year"],
                end_year=i.get("end_year"),
            )
            for i in raw.get("incomes", [])
        ),
        goals=tuple(
            Goal(
                id=g["id"],
                name=g["name"],
                kind=GoalKind(g["kind"]),
                target_amount=g["target_amount"],
                target_year=g["target_year"],
            )
            for g in raw.get("goals", [])
        ),
        annual_expenses=raw.get("annual_expenses", 0.0),
        deductible_expenses_annual=raw.get("deductible_expenses_annual", 0.0),
    )


def _parse_tax_tables(raw: dict[str, Any]) -> TaxTables:
    return TaxTables(
        year=raw["year"],
        irpf_monthly_brackets=tuple(
            IRPFBracket(**b) for b in raw["irpf_monthly_brackets"]
        ),
        irpf_annual_brackets=tuple(
            IRPFBracket(**b) for b in raw["irpf_annual_brackets"]
        ),
        irpf_exemption_limit_monthly=raw["irpf_exemption_limit_monthly"],
        irpf_reduction_upper_limit_monthly=raw["irpf_reduction_upper_limit_monthly"],
        dependent_deduction_annual=raw["dependent_deduction_annual"],
        simplified_discount_cap_annual=raw["simplified_discount_cap_annual"],
        equity_monthly_exemption=raw["equity_monthly_exemption"],
        equity_swing_rate=raw["equity_swing_rate"],
        equity_day_trade_rate=raw["equity_day_trade_rate"],
        fii_rate=raw["fii_rate"],
        regressive_bands=tuple(
            RegressiveBand(**b) for b in raw["regressive_bands"]
        ),
        come_cotas_rate=raw["come_cotas_rate"],
        equity_fund_rate=raw["equity_fund_rate"],
        dividend_monthly_threshold_per_source=raw["dividend_monthly_threshold_per_source"],
        dividend_withholding_rate=raw["dividend_withholding_rate"],
        irpfm_income_floor_annual=raw["irpfm_income_floor_annual"],
        irpfm_income_ceiling_annual=raw["irpfm_income_ceiling_annual"],
        irpfm_max_rate=raw["irpfm_max_rate"],
    )
