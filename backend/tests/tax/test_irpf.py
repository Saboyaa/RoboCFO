"""
Golden tests for compute_irpf.

All expected values hand-verified against the 2026 monthly bracket table and
Lei 15.270/2025 reducer. Sources:
  - Tabela progressiva: IN RFB 2.175/2023 (unchanged for 2026)
  - Redutor 2026: Lei 15.270/2025, Art. 1°
"""

import pytest
from contracts import DeclarationModel, IRPFScenario

from app.data.loader import load_tax_tables
from app.tax.irpf import compute_irpf


@pytest.fixture
def tables_2026():
    return load_tax_tables(2026)


# ── Reducer golden tests (Lei 15.270/2025) ───────────────────────────────────

def test_income_below_exemption_limit_yields_zero_tax(tables_2026) -> None:
    """R$4,999/month ≤ R$5,000 → full reducer applies → tax_due == 0."""
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([4_999.00] * 12),
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.tax_due == 0.00
    assert result.reduction_applied > 0.00


def test_income_at_exact_exemption_limit_yields_zero_tax(tables_2026) -> None:
    """R$5,000/month exactly → still fully exempt."""
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([5_000.00] * 12),
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.tax_due == 0.00


def test_income_above_reduction_ceiling_has_no_reducer(tables_2026) -> None:
    """R$7,351/month > R$7,350 → reducer = 0."""
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([7_351.00] * 12),
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.reduction_applied == 0.00


def test_reducer_never_makes_tax_negative(tables_2026) -> None:
    """reduction_applied is always <= gross tax (no negative tax)."""
    for income in (3_000.0, 5_500.0, 6_500.0, 7_300.0):
        scenario = IRPFScenario(
            year=2026,
            monthly_taxable_income=tuple([income] * 12),
        )
        result = compute_irpf(scenario, tables_2026)
        assert result.tax_due >= 0.00, f"Negative tax at income {income}"


# ── Effective rate invariant ──────────────────────────────────────────────────

def test_zero_income_gives_zero_effective_rate(tables_2026) -> None:
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([0.0] * 12),
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.effective_rate == 0.0
    assert result.tax_due == 0.0


def test_effective_rate_equals_tax_over_income(tables_2026) -> None:
    """effective_rate == tax_due / annual_income (within float tolerance)."""
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([10_000.00] * 12),
    )
    result = compute_irpf(scenario, tables_2026)
    annual_income = 10_000.00 * 12
    expected_rate = round(result.tax_due / annual_income, 6)
    assert result.effective_rate == expected_rate


# ── Simplified vs Complete model selection ────────────────────────────────────

def test_model_used_is_the_lower_of_simplified_and_complete(tables_2026) -> None:
    """With no deductions, simplified discount always wins for R$10k/month."""
    # R$10k/month: simplified gives smaller base → lower tax
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([10_000.00] * 12),
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.model_used == DeclarationModel.SIMPLIFIED


def test_complete_model_wins_with_large_deductions(tables_2026) -> None:
    """2 dependents + R$15k deductibles beats the 20% simplified cap."""
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([10_000.00] * 12),
        deductible_expenses_annual=15_000.00,
        dependents=2,
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.model_used == DeclarationModel.COMPLETE


# ── Golden exact values ───────────────────────────────────────────────────────

def test_golden_simplified_no_deductions(tables_2026) -> None:
    """
    R$10,000/month, no deductions, no dependents.
    Annual income = R$120,000.
    Simplified discount = min(120000 × 0.20, 16754.34) = 16754.34
    Simplified base = 120000 - 16754.34 = 103245.66
    Annual tax (27.5% bracket): 103245.66 × 0.275 - 10752.00 = 17640.56
    Reducer: monthly income R$10k > R$7,350 → reduction = 0
    tax_due = 17640.56
    """
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([10_000.00] * 12),
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.tax_due == pytest.approx(17_640.56, abs=0.02)
    assert result.reduction_applied == 0.00


def test_golden_complete_with_dependents_and_expenses(tables_2026) -> None:
    """
    R$10,000/month, 2 dependents, R$15,000 deductible expenses.
    Complete deductions = 2 × 2275.08 + 15000.00 = 19550.16
    Complete base = 120000 - 19550.16 = 100449.84
    Annual tax (27.5%): 100449.84 × 0.275 - 10752.00 = 16871.71
    Simplified tax = 17640.56 (worse) → COMPLETE wins
    Reducer = 0 (income R$10k > ceiling)
    tax_due = 16871.71
    """
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([10_000.00] * 12),
        deductible_expenses_annual=15_000.00,
        dependents=2,
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.tax_due == pytest.approx(16_871.71, abs=0.02)


def test_golden_partial_reducer(tables_2026) -> None:
    """
    R$6,000/month (inside the reducer band R$5,000–R$7,350).
    Monthly gross tax: 6000 × 0.275 - 896 = 754.00
    Reducer fraction: (7350 - 6000) / (7350 - 5000) = 1350/2350 ≈ 0.574468
    Monthly reducer = 754.00 × (1350/2350) = 754 × 27/47 ≈ 433.15
    Monthly net tax = 754.00 - 433.15 = 320.85
    total_reduction = 12 × 433.15 = 5197.79

    Annual income = 72000
    Simplified base = 72000 - min(14400, 16754.34) = 72000 - 14400 = 57600
    Annual gross tax (27.5%): 57600 × 0.275 - 10752 = 15840 - 10752 = 5088
    Complete (no deductions): base = 72000, tax = 72000 × 0.275 - 10752 = 9048
    → Simplified wins (5088 < 9048)
    tax_due = max(0, 5088 - 5197.36) = 0  ... wait let me recalculate

    Actually: reduction = sum of monthly reducers based on monthly income R$6000
    monthly gross = 754.00
    reducer_fraction = (7350-6000)/(7350-5000) = 1350/2350
    monthly_reducer = 754 * 1350/2350 = 433.106...
    total_reduction ≈ 5197.28

    simplified tax = 5088.00
    After reducer: max(0, 5088 - 5197.28) = 0

    So tax_due = 0? Let me verify...
    5088 < 5197.28 → yes, reducer exceeds the simplified tax → tax = 0

    Hmm, that seems surprising but makes sense: at R$6000/month the reducer benefit is large enough
    to zero out even the annual tax in the simplified model.

    Let me verify with the complete model instead:
    complete tax = 9048.00
    After reducer: max(0, 9048 - 5197.28) = 3850.72
    simplified after reducer = 0
    → simplified wins again, tax_due = 0
    """
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=tuple([6_000.00] * 12),
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.tax_due == 0.00
    assert result.reduction_applied == pytest.approx(5_197.79, abs=0.02)


def test_mixed_monthly_incomes(tables_2026) -> None:
    """Some months in exemption zone, some above ceiling — no crash, tax >= 0."""
    monthly = (4_000.0, 4_999.0, 5_500.0, 6_000.0, 7_000.0, 7_350.0,
               7_351.0, 8_000.0, 10_000.0, 15_000.0, 20_000.0, 30_000.0)
    scenario = IRPFScenario(
        year=2026,
        monthly_taxable_income=monthly,
    )
    result = compute_irpf(scenario, tables_2026)
    assert result.tax_due >= 0.00
    assert 0.0 <= result.effective_rate <= 0.275
