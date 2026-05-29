"""Load versioned tax-table and fixture data from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contracts import (
    IRPFBracket,
    RegressiveBand,
    TaxTables,
    Year,
)

_DATA_DIR = Path(__file__).parent
_TAX_TABLES_DIR = _DATA_DIR / "tax_tables"
_FIXTURES_DIR = _DATA_DIR / "fixtures"


def load_tax_tables(year: Year) -> TaxTables:
    path = _TAX_TABLES_DIR / f"{year}.json"
    if not path.exists():
        raise FileNotFoundError(f"No tax tables for year {year} at {path}")
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return _parse_tax_tables(raw)


def _parse_tax_tables(raw: dict[str, Any]) -> TaxTables:
    return TaxTables(
        year=raw["year"],
        irpf_monthly_brackets=tuple(
            IRPFBracket(**b) for b in raw["irpf_monthly_brackets"]
        ),
        irpf_annual_brackets=tuple(
            IRPFBracket(**b) for b in raw["irpf_annual_brackets"]
        ),
        irpf_exemption_limit_monthly=raw["irpf_exemption_limit_monthly"],
        irpf_reduction_upper_limit_monthly=raw["irpf_reduction_upper_limit_monthly"],
        dependent_deduction_annual=raw["dependent_deduction_annual"],
        simplified_discount_cap_annual=raw["simplified_discount_cap_annual"],
        equity_monthly_exemption=raw["equity_monthly_exemption"],
        equity_swing_rate=raw["equity_swing_rate"],
        equity_day_trade_rate=raw["equity_day_trade_rate"],
        fii_rate=raw["fii_rate"],
        regressive_bands=tuple(
            RegressiveBand(**b) for b in raw["regressive_bands"]
        ),
        come_cotas_rate=raw["come_cotas_rate"],
        equity_fund_rate=raw["equity_fund_rate"],
        dividend_monthly_threshold_per_source=raw["dividend_monthly_threshold_per_source"],
        dividend_withholding_rate=raw["dividend_withholding_rate"],
        irpfm_income_floor_annual=raw["irpfm_income_floor_annual"],
        irpfm_income_ceiling_annual=raw["irpfm_income_ceiling_annual"],
        irpfm_max_rate=raw["irpfm_max_rate"],
    )
