"""Regime 1 — IRPF (taxable income, progressive + Lei 15.270/2025 reducer)."""

from __future__ import annotations

from contracts import (
    DeclarationModel,
    IRPFBracket,
    IRPFResult,
    IRPFScenario,
    Money,
    Rate,
    TaxTables,
)


def compute_irpf(scenario: IRPFScenario, tables: TaxTables) -> IRPFResult:
    """PURE. Applies the progressive table, picks simplified vs complete
    (whichever is cheaper), and applies the Lei 15.270/2025 reducer month by month.
    """
    monthly_incomes = scenario.monthly_taxable_income
    annual_income: Money = sum(monthly_incomes)

    # Step 1: compute total reducer benefit from monthly incomes
    total_reduction: Money = 0.0
    for income in monthly_incomes:
        gross = _apply_brackets(income, tables.irpf_monthly_brackets)
        total_reduction += _monthly_reducer(income, gross, tables)

    # Step 2: annual tax under complete model
    complete_deductions = (
        scenario.deductible_expenses_annual
        + scenario.dependents * tables.dependent_deduction_annual
    )
    complete_base = max(0.0, annual_income - complete_deductions)
    complete_gross = _apply_brackets(complete_base, tables.irpf_annual_brackets)
    complete_net = max(0.0, complete_gross - total_reduction)

    # Step 3: annual tax under simplified model (20% standard discount, capped)
    simplified_deduction = min(
        annual_income * 0.20, tables.simplified_discount_cap_annual
    )
    simplified_base = max(0.0, annual_income - simplified_deduction)
    simplified_gross = _apply_brackets(simplified_base, tables.irpf_annual_brackets)
    simplified_net = max(0.0, simplified_gross - total_reduction)

    # Step 4: pick the model that yields the lower tax
    if complete_net <= simplified_net:
        tax_due = complete_net
        tax_base = complete_base
        model_used = DeclarationModel.COMPLETE
    else:
        tax_due = simplified_net
        tax_base = simplified_base
        model_used = DeclarationModel.SIMPLIFIED

    # Step 5: marginal rate — rate of the highest applicable annual bracket
    marginal_rate: Rate = _marginal_rate(tax_base, tables.irpf_annual_brackets)

    effective_rate: Rate = (
        round(tax_due / annual_income, 6) if annual_income > 0 else 0.0
    )

    return IRPFResult(
        tax_due=round(tax_due, 2),
        tax_base=round(tax_base, 2),
        model_used=model_used,
        marginal_rate=marginal_rate,
        effective_rate=effective_rate,
        reduction_applied=round(total_reduction, 2),
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _apply_brackets(income: Money, brackets: tuple[IRPFBracket, ...]) -> Money:
    """Return the gross tax for the given income using the bracket table."""
    tax: Money = 0.0
    for bracket in reversed(brackets):
        if income >= bracket.lower_bound:
            tax = income * bracket.rate - bracket.deduction
            break
    return max(0.0, tax)


def _monthly_reducer(income: Money, gross_tax: Money, tables: TaxTables) -> Money:
    """Lei 15.270/2025: reduction amount for one month. Always >= 0."""
    exemption = tables.irpf_exemption_limit_monthly
    ceiling = tables.irpf_reduction_upper_limit_monthly
    if income <= exemption:
        return gross_tax
    if income >= ceiling:
        return 0.0
    fraction = (ceiling - income) / (ceiling - exemption)
    return gross_tax * fraction


def _marginal_rate(tax_base: Money, brackets: tuple[IRPFBracket, ...]) -> Rate:
    for bracket in reversed(brackets):
        if tax_base >= bracket.lower_bound:
            return bracket.rate
    return 0.0
