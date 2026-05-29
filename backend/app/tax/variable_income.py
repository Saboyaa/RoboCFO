"""Regime 2 — Variable income (stocks/ETFs/FII), monthly assessment."""

from __future__ import annotations

from collections.abc import Sequence

from contracts import (
    Money,
    MonthlyTrades,
    TaxTables,
    VariableIncomeResult,
)


def compute_variable_income(
    months: Sequence[MonthlyTrades],
    tables: TaxTables,
    loss_carryforward_in: Money = 0.0,
) -> VariableIncomeResult:
    """PURE. Month-by-month assessment.

    Swing: exempt if swing_sales_total <= equity_monthly_exemption, else 15%.
    Day trade and FII: 20%, never exempt.
    Losses offset gains within variable income only — never reduce IRPF.
    """
    total_tax: Money = 0.0
    carryforward: Money = loss_carryforward_in
    any_exemption = False

    for m in months:
        exempt = m.swing_sales_total <= tables.equity_monthly_exemption

        if exempt:
            any_exemption = True
            # Losses from exempt months are excluded from carryforward (both
            # gains and losses are fully outside the taxable scope for that month)
            swing_tax: Money = 0.0
        else:
            swing_tax, carryforward = _tax_after_carryforward(
                m.swing_gain, carryforward, tables.equity_swing_rate
            )

        day_trade_tax, carryforward = _tax_after_carryforward(
            m.day_trade_gain, carryforward, tables.equity_day_trade_rate
        )
        fii_tax, carryforward = _tax_after_carryforward(
            m.fii_gain, carryforward, tables.fii_rate
        )

        total_tax += swing_tax + day_trade_tax + fii_tax

    return VariableIncomeResult(
        tax_due=round(total_tax, 2),
        exemption_applied=any_exemption,
        loss_carryforward_out=round(carryforward, 2),
    )


def _tax_after_carryforward(
    gain: Money, carryforward: Money, rate: float
) -> tuple[Money, Money]:
    """Apply carryforward to gain; return (tax_owed, remaining_carryforward)."""
    if gain <= 0:
        return 0.0, carryforward + (-gain)
    net = gain - carryforward
    if net <= 0:
        return 0.0, -net
    return round(net * rate, 2), 0.0
