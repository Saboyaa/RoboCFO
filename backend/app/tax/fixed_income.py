"""Regime 3 — Fixed income and funds (regressive table + come-cotas)."""

from __future__ import annotations

from contracts import (
    AssetClass,
    Money,
    Redemption,
    TaxTables,
)

_EXEMPT_CLASSES = {AssetClass.EXEMPT_FIXED_INCOME, AssetClass.SAVINGS}
_COME_COTAS_CLASSES = {AssetClass.FIXED_INCOME_FUND, AssetClass.MULTIMARKET_FUND}


def compute_fixed_income_tax(redemption: Redemption, tables: TaxTables) -> Money:
    """PURE. Regressive table by days_held; exempt classes return 0;
    EQUITY_FUND uses the flat equity_fund_rate regardless of holding period.
    """
    if redemption.gain <= 0:
        return 0.0
    if redemption.asset_class in _EXEMPT_CLASSES:
        return 0.0
    if redemption.asset_class == AssetClass.EQUITY_FUND:
        return round(redemption.gain * tables.equity_fund_rate, 2)
    rate = _regressive_rate(redemption.days_held, tables)
    return round(redemption.gain * rate, 2)


def compute_come_cotas(semiannual_gain: Money, tables: TaxTables) -> Money:
    """PURE. Semiannual prepayment on open funds at come_cotas_rate."""
    if semiannual_gain <= 0:
        return 0.0
    return round(semiannual_gain * tables.come_cotas_rate, 2)


def _regressive_rate(days_held: int, tables: TaxTables) -> float:
    for band in tables.regressive_bands:
        if band.max_days is None or days_held <= band.max_days:
            return band.rate
    return tables.regressive_bands[-1].rate
