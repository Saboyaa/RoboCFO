import pytest
from contracts import TaxTables

from app.data.loader import load_tax_tables


def test_load_2026_returns_tax_tables() -> None:
    tables = load_tax_tables(2026)
    assert isinstance(tables, TaxTables)
    assert tables.year == 2026


def test_2026_irpf_exemption_limit() -> None:
    tables = load_tax_tables(2026)
    assert tables.irpf_exemption_limit_monthly == 5_000.00


def test_2026_irpf_reduction_upper_limit() -> None:
    tables = load_tax_tables(2026)
    assert tables.irpf_reduction_upper_limit_monthly == 7_350.00


def test_2026_equity_monthly_exemption() -> None:
    tables = load_tax_tables(2026)
    assert tables.equity_monthly_exemption == 20_000.00


def test_2026_irpfm_floor() -> None:
    tables = load_tax_tables(2026)
    assert tables.irpfm_income_floor_annual == 600_000.00


def test_2026_irpfm_ceiling() -> None:
    tables = load_tax_tables(2026)
    assert tables.irpfm_income_ceiling_annual == 1_200_000.00


def test_2026_has_five_irpf_monthly_brackets() -> None:
    tables = load_tax_tables(2026)
    # 0% exempt + 4 taxable bands
    assert len(tables.irpf_monthly_brackets) == 5


def test_2026_top_irpf_rate_is_27p5() -> None:
    tables = load_tax_tables(2026)
    assert tables.irpf_monthly_brackets[-1].rate == 0.275


def test_2026_regressive_bands_ascending_by_holding() -> None:
    tables = load_tax_tables(2026)
    # rates should descend as holding period increases
    rates = [b.rate for b in tables.regressive_bands]
    assert rates == sorted(rates, reverse=True)
    # last band has no upper bound
    assert tables.regressive_bands[-1].max_days is None


def test_2026_equity_rates() -> None:
    tables = load_tax_tables(2026)
    assert tables.equity_swing_rate == 0.15
    assert tables.equity_day_trade_rate == 0.20
    assert tables.fii_rate == 0.20


def test_2026_dividend_withholding() -> None:
    tables = load_tax_tables(2026)
    assert tables.dividend_monthly_threshold_per_source == 50_000.00
    assert tables.dividend_withholding_rate == 0.10


def test_unknown_year_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_tax_tables(9999)
