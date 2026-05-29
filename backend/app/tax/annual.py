"""Annual tax facade — orchestrates all four regimes. This is the TaxFn."""

from __future__ import annotations

from contracts import (
    AnnualTaxResult,
    AnnualTaxScenario,
    Money,
    TaxTables,
)

from app.tax.fixed_income import compute_fixed_income_tax
from app.tax.irpf import compute_irpf
from app.tax.irpfm import compute_irpfm
from app.tax.variable_income import compute_variable_income


def compute_annual_tax(scenario: AnnualTaxScenario, tables: TaxTables) -> AnnualTaxResult:
    """PURE facade — called once per simulated year per Monte Carlo path.

    Invariant: total_tax == irpf.tax_due + variable_income_tax + fixed_income_tax
                            + dividend_withholding + irpfm_additional (within cent rounding).
    """
    # Regime 1: IRPF
    irpf_result = compute_irpf(scenario.irpf, tables)

    # Regime 2: Variable income
    var_result = compute_variable_income(
        scenario.variable_income_trades,
        tables,
        loss_carryforward_in=scenario.variable_income_loss_carryforward_in,
    )

    # Regime 3: Fixed income redemptions
    fixed_tax: Money = sum(
        compute_fixed_income_tax(r, tables) for r in scenario.redemptions
    )

    # Regime 4a: Dividend withholding (10% on monthly amount exceeding threshold)
    dividend_withholding: Money = 0.0
    if scenario.max_monthly_dividend_per_source > tables.dividend_monthly_threshold_per_source:
        dividend_withholding = round(
            scenario.dividends_total_annual * tables.dividend_withholding_rate, 2
        )

    # Regime 4b: IRPFM top-up
    tax_already_assessed = (
        irpf_result.tax_due
        + var_result.tax_due
        + fixed_tax
        + dividend_withholding
        + scenario.jcp_received_annual * 0.15  # JCP withheld at source (15%)
    )
    total_annual_income = (
        sum(scenario.irpf.monthly_taxable_income)
        + scenario.dividends_total_annual
        + scenario.jcp_received_annual
        + scenario.exempt_income_annual
    )
    irpfm_additional = compute_irpfm(total_annual_income, tax_already_assessed, tables)

    total_tax = round(
        irpf_result.tax_due
        + var_result.tax_due
        + fixed_tax
        + dividend_withholding
        + irpfm_additional,
        2,
    )

    return AnnualTaxResult(
        irpf=irpf_result,
        variable_income_tax=round(var_result.tax_due, 2),
        fixed_income_tax=round(fixed_tax, 2),
        dividend_withholding=round(dividend_withholding, 2),
        irpfm_additional=irpfm_additional,
        total_tax=total_tax,
        variable_income_loss_carryforward_out=var_result.loss_carryforward_out,
    )
