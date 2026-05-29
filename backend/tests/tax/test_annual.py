"""
Tests for compute_annual_tax — the annual facade (TaxFn).

Critical invariant: total_tax == irpf.tax_due + variable_income_tax +
fixed_income_tax + dividend_withholding + irpfm_additional (within R$0.01).
"""

import pytest
from contracts import (
    AnnualTaxScenario,
    AssetClass,
    IRPFScenario,
    MonthlyTrades,
    Redemption,
    TaxFn,
)

from app.data.loader import load_tax_tables
from app.tax.annual import compute_annual_tax


@pytest.fixture
def tables_2026():
    return load_tax_tables(2026)


def _simple_scenario(year: int = 2026, monthly_income: float = 10_000.0) -> AnnualTaxScenario:
    return AnnualTaxScenario(
        year=year,
        irpf=IRPFScenario(
            year=year,
            monthly_taxable_income=tuple([monthly_income] * 12),
        ),
    )


# ── total_tax invariant ───────────────────────────────────────────────────────

def test_total_tax_invariant_simple(tables_2026) -> None:
    """total_tax == sum of all component taxes within R$0.01."""
    scenario = _simple_scenario()
    result = compute_annual_tax(scenario, tables_2026)
    expected = (
        result.irpf.tax_due
        + result.variable_income_tax
        + result.fixed_income_tax
        + result.dividend_withholding
        + result.irpfm_additional
    )
    assert result.total_tax == pytest.approx(expected, abs=0.01)


def test_total_tax_invariant_with_redemptions(tables_2026) -> None:
    scenario = AnnualTaxScenario(
        year=2026,
        irpf=IRPFScenario(
            year=2026,
            monthly_taxable_income=tuple([10_000.0] * 12),
        ),
        redemptions=(
            Redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=20_000.0, days_held=400),
            Redemption(AssetClass.EQUITY_FUND, gain=5_000.0, days_held=200),
        ),
    )
    result = compute_annual_tax(scenario, tables_2026)
    expected = (
        result.irpf.tax_due
        + result.variable_income_tax
        + result.fixed_income_tax
        + result.dividend_withholding
        + result.irpfm_additional
    )
    assert result.total_tax == pytest.approx(expected, abs=0.01)


def test_total_tax_invariant_with_variable_income(tables_2026) -> None:
    scenario = AnnualTaxScenario(
        year=2026,
        irpf=IRPFScenario(
            year=2026,
            monthly_taxable_income=tuple([8_000.0] * 12),
        ),
        variable_income_trades=(
            MonthlyTrades(1, swing_sales_total=25_000.0, swing_gain=3_000.0,
                          day_trade_gain=1_000.0, fii_gain=500.0),
        ),
    )
    result = compute_annual_tax(scenario, tables_2026)
    expected = (
        result.irpf.tax_due
        + result.variable_income_tax
        + result.fixed_income_tax
        + result.dividend_withholding
        + result.irpfm_additional
    )
    assert result.total_tax == pytest.approx(expected, abs=0.01)


def test_total_tax_invariant_high_income_with_irpfm(tables_2026) -> None:
    """R$55k/month (R$660k annual) — above IRPFM floor."""
    scenario = _simple_scenario(monthly_income=55_000.0)
    result = compute_annual_tax(scenario, tables_2026)
    expected = (
        result.irpf.tax_due
        + result.variable_income_tax
        + result.fixed_income_tax
        + result.dividend_withholding
        + result.irpfm_additional
    )
    assert result.total_tax == pytest.approx(expected, abs=0.01)


def test_total_tax_invariant_with_dividends(tables_2026) -> None:
    """Dividends above R$50k/month threshold trigger 10% withholding."""
    scenario = AnnualTaxScenario(
        year=2026,
        irpf=IRPFScenario(
            year=2026,
            monthly_taxable_income=tuple([10_000.0] * 12),
        ),
        dividends_total_annual=200_000.0,
        max_monthly_dividend_per_source=60_000.0,  # > R$50k threshold
    )
    result = compute_annual_tax(scenario, tables_2026)
    assert result.dividend_withholding > 0.0
    expected = (
        result.irpf.tax_due
        + result.variable_income_tax
        + result.fixed_income_tax
        + result.dividend_withholding
        + result.irpfm_additional
    )
    assert result.total_tax == pytest.approx(expected, abs=0.01)


# ── TaxFn protocol compliance ─────────────────────────────────────────────────

def test_compute_annual_tax_satisfies_taxfn_protocol(tables_2026) -> None:
    """mypy enforces this statically; this test makes it explicit at runtime."""
    tax_fn: TaxFn = compute_annual_tax
    result = tax_fn(_simple_scenario(), tables_2026)
    assert result.total_tax >= 0.0


# ── Loss carryforward propagates ──────────────────────────────────────────────

def test_variable_income_loss_carryforward_propagates(tables_2026) -> None:
    scenario = AnnualTaxScenario(
        year=2026,
        irpf=IRPFScenario(year=2026, monthly_taxable_income=tuple([5_000.0] * 12)),
        variable_income_trades=(
            MonthlyTrades(1, swing_sales_total=25_000.0, swing_gain=-8_000.0,
                          day_trade_gain=0.0, fii_gain=0.0),
        ),
    )
    result = compute_annual_tax(scenario, tables_2026)
    assert result.variable_income_loss_carryforward_out == pytest.approx(8_000.0, abs=0.01)


# ── Zero scenario ─────────────────────────────────────────────────────────────

def test_zero_scenario_all_taxes_zero(tables_2026) -> None:
    scenario = _simple_scenario(monthly_income=0.0)
    result = compute_annual_tax(scenario, tables_2026)
    assert result.total_tax == 0.0
    assert result.irpf.tax_due == 0.0
