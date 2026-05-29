"""Regime 4 — IRPFM (high-income minimum tax)."""

from __future__ import annotations

from contracts import Money, TaxTables


def compute_irpfm(
    total_annual_income: Money,
    tax_already_assessed: Money,
    tables: TaxTables,
) -> Money:
    """PURE. Returns only the TOP-UP (minimum_tax - already_assessed), never negative.

    Rate rises linearly from 0 to irpfm_max_rate between the floor and ceiling,
    then stays at the cap above the ceiling. The base includes exempt income and
    income taxed at source (caller is responsible for passing the correct total).
    """
    floor = tables.irpfm_income_floor_annual
    ceiling = tables.irpfm_income_ceiling_annual
    max_rate = tables.irpfm_max_rate

    if total_annual_income <= floor:
        return 0.0

    if total_annual_income >= ceiling:
        effective_rate = max_rate
    else:
        effective_rate = max_rate * (total_annual_income - floor) / (ceiling - floor)

    minimum_tax = total_annual_income * effective_rate
    top_up = minimum_tax - tax_already_assessed
    return round(max(0.0, top_up), 2)
