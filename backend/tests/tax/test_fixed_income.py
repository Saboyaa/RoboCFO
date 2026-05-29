"""
Golden tests for compute_fixed_income_tax and compute_come_cotas (Regime 3).

Regressive table (2026):
  <= 180 days  → 22.5%
  <= 360 days  → 20.0%
  <= 720 days  → 17.5%
  >  720 days  → 15.0%

Exempt asset classes: EXEMPT_FIXED_INCOME, SAVINGS → always 0.
EQUITY_FUND → flat equity_fund_rate (15%).
Come-cotas: semiannual prepayment at come_cotas_rate (15%) on open funds.
"""

import pytest
from contracts import AssetClass, Redemption

from app.data.loader import load_tax_tables
from app.tax.fixed_income import compute_come_cotas, compute_fixed_income_tax


@pytest.fixture
def tables_2026():
    return load_tax_tables(2026)


def redemption(asset_class: AssetClass, gain: float, days: int) -> Redemption:
    return Redemption(asset_class=asset_class, gain=gain, days_held=days)


# ── Regressive table boundaries ───────────────────────────────────────────────

def test_180_days_taxed_at_22p5(tables_2026) -> None:
    """Exactly 180 days → first band: 22.5%."""
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=10_000.00, days=180)
    assert compute_fixed_income_tax(r, tables_2026) == pytest.approx(2_250.00, abs=0.01)


def test_181_days_taxed_at_20(tables_2026) -> None:
    """181 days → second band: 20%."""
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=10_000.00, days=181)
    assert compute_fixed_income_tax(r, tables_2026) == pytest.approx(2_000.00, abs=0.01)


def test_360_days_taxed_at_20(tables_2026) -> None:
    """Exactly 360 days → still second band: 20%."""
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=10_000.00, days=360)
    assert compute_fixed_income_tax(r, tables_2026) == pytest.approx(2_000.00, abs=0.01)


def test_361_days_taxed_at_17p5(tables_2026) -> None:
    """361 days → third band: 17.5%."""
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=10_000.00, days=361)
    assert compute_fixed_income_tax(r, tables_2026) == pytest.approx(1_750.00, abs=0.01)


def test_720_days_taxed_at_17p5(tables_2026) -> None:
    """Exactly 720 days → third band: 17.5%."""
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=10_000.00, days=720)
    assert compute_fixed_income_tax(r, tables_2026) == pytest.approx(1_750.00, abs=0.01)


def test_721_days_taxed_at_15(tables_2026) -> None:
    """721 days → final band: 15%."""
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=10_000.00, days=721)
    assert compute_fixed_income_tax(r, tables_2026) == pytest.approx(1_500.00, abs=0.01)


def test_long_holding_taxed_at_15(tables_2026) -> None:
    """5 years (1825 days) → final band: 15%."""
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=10_000.00, days=1825)
    assert compute_fixed_income_tax(r, tables_2026) == pytest.approx(1_500.00, abs=0.01)


# ── Exempt asset classes ──────────────────────────────────────────────────────

def test_exempt_fixed_income_returns_zero(tables_2026) -> None:
    r = redemption(AssetClass.EXEMPT_FIXED_INCOME, gain=50_000.00, days=180)
    assert compute_fixed_income_tax(r, tables_2026) == 0.00


def test_savings_returns_zero(tables_2026) -> None:
    r = redemption(AssetClass.SAVINGS, gain=5_000.00, days=365)
    assert compute_fixed_income_tax(r, tables_2026) == 0.00


# ── Equity fund (flat rate) ───────────────────────────────────────────────────

def test_equity_fund_uses_flat_15_percent(tables_2026) -> None:
    """EQUITY_FUND always uses equity_fund_rate (15%), ignoring holding period."""
    r_short = redemption(AssetClass.EQUITY_FUND, gain=10_000.00, days=10)
    r_long = redemption(AssetClass.EQUITY_FUND, gain=10_000.00, days=1000)
    short_tax = compute_fixed_income_tax(r_short, tables_2026)
    long_tax = compute_fixed_income_tax(r_long, tables_2026)
    assert short_tax == pytest.approx(1_500.00, abs=0.01)
    assert long_tax == pytest.approx(1_500.00, abs=0.01)


# ── Zero gain ────────────────────────────────────────────────────────────────

def test_zero_gain_returns_zero(tables_2026) -> None:
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=0.0, days=200)
    assert compute_fixed_income_tax(r, tables_2026) == 0.00


def test_negative_gain_returns_zero(tables_2026) -> None:
    r = redemption(AssetClass.TAXABLE_FIXED_INCOME, gain=-1_000.00, days=200)
    assert compute_fixed_income_tax(r, tables_2026) == 0.00


# ── Come-cotas ────────────────────────────────────────────────────────────────

def test_come_cotas_applies_minimum_rate(tables_2026) -> None:
    """Semiannual prepayment = gain × come_cotas_rate (15%)."""
    tax = compute_come_cotas(semiannual_gain=20_000.00, tables=tables_2026)
    assert tax == pytest.approx(3_000.00, abs=0.01)


def test_come_cotas_zero_gain_returns_zero(tables_2026) -> None:
    assert compute_come_cotas(semiannual_gain=0.0, tables=tables_2026) == 0.00


def test_come_cotas_negative_gain_returns_zero(tables_2026) -> None:
    assert compute_come_cotas(semiannual_gain=-500.0, tables=tables_2026) == 0.00
