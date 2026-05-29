"""
Golden tests for compute_variable_income (Regime 2).

Key rules:
  - Swing trade: exempt if month's swing_sales_total <= R$20,000; else 15% on swing_gain
  - Day trade: 20% on day_trade_gain, no exemption
  - FII: 20% on fii_gain, no exemption
  - Losses offset future gains ONLY within variable income (not IRPF)
  - loss_carryforward_out carries to the next period (within variable income only)
"""

import pytest
from contracts import MonthlyTrades

from app.data.loader import load_tax_tables
from app.tax.variable_income import compute_variable_income


@pytest.fixture
def tables_2026():
    return load_tax_tables(2026)


def month(
    m: int,
    swing_sales: float = 0.0,
    swing_gain: float = 0.0,
    day_trade: float = 0.0,
    fii: float = 0.0,
) -> MonthlyTrades:
    return MonthlyTrades(
        month=m,
        swing_sales_total=swing_sales,
        swing_gain=swing_gain,
        day_trade_gain=day_trade,
        fii_gain=fii,
    )


# ── Swing exemption ───────────────────────────────────────────────────────────

def test_swing_exempt_when_sales_below_threshold(tables_2026) -> None:
    """Sales R$19,999 < R$20,000 → exempt regardless of gain."""
    result = compute_variable_income(
        [month(1, swing_sales=19_999.00, swing_gain=5_000.00)],
        tables_2026,
    )
    assert result.tax_due == 0.00
    assert result.exemption_applied is True


def test_swing_exempt_at_exact_threshold(tables_2026) -> None:
    """Sales == R$20,000 exactly → still exempt."""
    result = compute_variable_income(
        [month(1, swing_sales=20_000.00, swing_gain=3_000.00)],
        tables_2026,
    )
    assert result.tax_due == 0.00
    assert result.exemption_applied is True


def test_swing_taxed_when_sales_above_threshold(tables_2026) -> None:
    """Sales R$20,001 > R$20,000 → 15% on swing_gain.
    gain = 5000 → tax = 5000 × 0.15 = 750.00
    """
    result = compute_variable_income(
        [month(1, swing_sales=20_001.00, swing_gain=5_000.00)],
        tables_2026,
    )
    assert result.tax_due == pytest.approx(750.00, abs=0.01)
    assert result.exemption_applied is False


def test_swing_loss_above_threshold_no_tax(tables_2026) -> None:
    """Sales above threshold but gain is negative → no tax (not negative)."""
    result = compute_variable_income(
        [month(1, swing_sales=25_000.00, swing_gain=-2_000.00)],
        tables_2026,
    )
    assert result.tax_due == 0.00
    assert result.loss_carryforward_out == pytest.approx(2_000.00, abs=0.01)


# ── Day trade ─────────────────────────────────────────────────────────────────

def test_day_trade_taxed_at_20_percent(tables_2026) -> None:
    """Day trade gain R$3,000 → tax = 3000 × 0.20 = 600.00 (no exemption)."""
    result = compute_variable_income(
        [month(1, day_trade=3_000.00)],
        tables_2026,
    )
    assert result.tax_due == pytest.approx(600.00, abs=0.01)


def test_day_trade_exempt_threshold_does_not_apply(tables_2026) -> None:
    """Day trade is never exempt regardless of swing_sales_total."""
    result = compute_variable_income(
        [month(1, swing_sales=1_000.00, day_trade=500.00)],
        tables_2026,
    )
    assert result.tax_due == pytest.approx(100.00, abs=0.01)


# ── FII ───────────────────────────────────────────────────────────────────────

def test_fii_taxed_at_20_percent(tables_2026) -> None:
    """FII gain R$2,000 → tax = 2000 × 0.20 = 400.00."""
    result = compute_variable_income(
        [month(1, fii=2_000.00)],
        tables_2026,
    )
    assert result.tax_due == pytest.approx(400.00, abs=0.01)


# ── Loss carryforward ─────────────────────────────────────────────────────────

def test_loss_in_month1_offsets_gain_in_month2(tables_2026) -> None:
    """
    Month 1: swing_sales=25k, gain=-3000 → carryforward=3000
    Month 2: swing_sales=25k, gain=+5000 → net gain = 5000-3000 = 2000 → tax = 300
    total tax = 300
    """
    result = compute_variable_income(
        [
            month(1, swing_sales=25_000.00, swing_gain=-3_000.00),
            month(2, swing_sales=25_000.00, swing_gain=5_000.00),
        ],
        tables_2026,
    )
    assert result.tax_due == pytest.approx(300.00, abs=0.01)
    assert result.loss_carryforward_out == 0.00


def test_loss_carryforward_input_reduces_first_month(tables_2026) -> None:
    """
    Carryforward in = 2000, month gain = 3000 → net = 1000 → tax = 150
    """
    result = compute_variable_income(
        [month(1, swing_sales=25_000.00, swing_gain=3_000.00)],
        tables_2026,
        loss_carryforward_in=2_000.00,
    )
    assert result.tax_due == pytest.approx(150.00, abs=0.01)
    assert result.loss_carryforward_out == 0.00


def test_excess_loss_becomes_carryforward_out(tables_2026) -> None:
    """Total losses across all months exceed total gains → carry out."""
    result = compute_variable_income(
        [
            month(1, swing_sales=25_000.00, swing_gain=-5_000.00),
            month(2, swing_sales=25_000.00, swing_gain=2_000.00),
        ],
        tables_2026,
    )
    assert result.tax_due == 0.00
    assert result.loss_carryforward_out == pytest.approx(3_000.00, abs=0.01)


# ── Regime isolation: losses do NOT reduce IRPF ───────────────────────────────

def test_variable_income_loss_does_not_appear_in_irpf_result(tables_2026) -> None:
    """Loss carryforward is contained within variable income — not exported to IRPF."""
    result = compute_variable_income(
        [month(1, swing_sales=25_000.00, swing_gain=-10_000.00)],
        tables_2026,
    )
    # The loss is captured in carryforward_out, not in some IRPF-reducing field
    assert result.loss_carryforward_out == pytest.approx(10_000.00, abs=0.01)
    assert result.tax_due == 0.00
    # VariableIncomeResult has no IRPF field — the isolation is structural


# ── Combined month ────────────────────────────────────────────────────────────

def test_combined_swing_day_trade_fii_same_month(tables_2026) -> None:
    """
    swing_sales=25k, swing_gain=2000 → swing_tax=300
    day_trade=1000 → dt_tax=200
    fii=500 → fii_tax=100
    total = 600
    """
    result = compute_variable_income(
        [month(1, swing_sales=25_000.00, swing_gain=2_000.00, day_trade=1_000.00, fii=500.00)],
        tables_2026,
    )
    assert result.tax_due == pytest.approx(600.00, abs=0.01)


def test_zero_activity_yields_zero_tax(tables_2026) -> None:
    result = compute_variable_income([], tables_2026)
    assert result.tax_due == 0.00
    assert result.loss_carryforward_out == 0.00
