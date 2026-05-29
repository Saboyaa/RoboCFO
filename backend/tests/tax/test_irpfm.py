"""
Golden tests for compute_irpfm (Regime 4 — high-income minimum tax).

Rules:
  - Base includes ALL income (regular + exempt + withheld-at-source)
  - Annual income <= R$600k: no IRPFM
  - R$600k < income <= R$1.2M: linear 0→10%
  - Annual income > R$1.2M: flat 10%
  - Returns only the TOP-UP (minimum_tax - already_assessed), never negative
"""

import pytest

from app.data.loader import load_tax_tables
from app.tax.irpfm import compute_irpfm


@pytest.fixture
def tables_2026():
    return load_tax_tables(2026)


# ── Below floor ───────────────────────────────────────────────────────────────

def test_income_below_floor_returns_zero(tables_2026) -> None:
    """R$500k annual < R$600k floor → IRPFM = 0."""
    assert compute_irpfm(500_000.00, 0.00, tables_2026) == 0.00


def test_income_at_exact_floor_returns_zero(tables_2026) -> None:
    """R$600k exactly → IRPFM = 0 (linear starts above the floor)."""
    assert compute_irpfm(600_000.00, 0.00, tables_2026) == 0.00


# ── Linear band (R$600k – R$1.2M) ────────────────────────────────────────────

def test_income_midpoint_linear_band(tables_2026) -> None:
    """
    R$900k is midpoint of R$600k–R$1.2M.
    Rate = 10% × (900k - 600k) / (1200k - 600k) = 10% × 0.5 = 5%
    Minimum tax = 900k × 5% = 45k
    No prior assessment → top-up = 45k
    """
    assert compute_irpfm(900_000.00, 0.00, tables_2026) == pytest.approx(45_000.00, abs=0.10)


def test_income_just_above_floor(tables_2026) -> None:
    """R$600,001 → very small IRPFM, > 0."""
    result = compute_irpfm(600_001.00, 0.00, tables_2026)
    assert result > 0.00


def test_income_at_ceiling(tables_2026) -> None:
    """
    R$1.2M exactly → rate = 10%
    Minimum tax = 1_200_000 × 10% = 120_000
    """
    assert compute_irpfm(1_200_000.00, 0.00, tables_2026) == pytest.approx(120_000.00, abs=0.10)


# ── Above ceiling ─────────────────────────────────────────────────────────────

def test_income_above_ceiling_flat_10(tables_2026) -> None:
    """
    R$2M > R$1.2M → rate stays at 10%
    Minimum tax = 2_000_000 × 10% = 200_000
    """
    assert compute_irpfm(2_000_000.00, 0.00, tables_2026) == pytest.approx(200_000.00, abs=0.10)


# ── Top-up logic ──────────────────────────────────────────────────────────────

def test_top_up_is_minimum_minus_already_assessed(tables_2026) -> None:
    """
    Income R$900k → minimum = 45k.
    Already assessed R$30k → top-up = 15k.
    """
    assert compute_irpfm(900_000.00, 30_000.00, tables_2026) == pytest.approx(15_000.00, abs=0.10)


def test_top_up_never_negative(tables_2026) -> None:
    """Already assessed more than the minimum → top-up = 0, never negative."""
    assert compute_irpfm(900_000.00, 60_000.00, tables_2026) == 0.00


def test_top_up_zero_when_assessed_equals_minimum(tables_2026) -> None:
    assert compute_irpfm(900_000.00, 45_000.00, tables_2026) == 0.00
