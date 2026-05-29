"""
Robo-CFO (Brazil) — Frozen interface contracts.

Brazilian version. Core structural difference vs the US model: in Brazil there is
NO stacking of capital gains on top of ordinary income. Taxation is fragmented into
PARALLEL regimes, and most investment income is taxed definitively/withheld at source,
separate from the annual adjustment. So the "tax engine" is not a single function — it
is a set of pure functions, one per regime, plus an annual aggregator.

Brazilian instrument and tax names (IRPF, IRPFM, FII, LCI/LCA, come-cotas, JCP, Tesouro,
CDB, pró-labore, IPCA) are kept as-is: they are proper nouns of real Brazilian instruments
and taxes, and translating them would break verification against Receita Federal sources.

Regimes modeled:
  1. IRPF        — taxable income (salary, pró-labore, rent): progressive table + the
                   Lei 15.270/2025 reducer (full exemption up to R$5,000/month, decreasing
                   reduction up to R$7,350/month).
  2. VARIABLE INCOME — stocks/ETFs and FII: MONTHLY assessment, gain exemption when total
                   monthly sales are up to R$20,000 (swing), 15% common, 20% day trade;
                   FII 20% with no exemption; losses offset only within the stock market.
  3. FIXED INCOME / FUNDS — regressive table (22.5% -> 15% by holding period), withheld at
                   source on redemption; semiannual come-cotas in open funds. LCI/LCA and
                   incentivized securities are exempt.
  4. IRPFM       — minimum tax on high earners (annual income > R$600k); dividends above
                   R$50k/month from the same source incur 10% withholding.

Design decisions (same as the US version):
  * stdlib only — imports with zero dependencies.
  * Money = float, rounded to cents at the boundary. Switching to Decimal is one alias change.
  * Tables/rates live in `TaxTables` (data, not code) — a new year is new data, never new logic.
  * `tax_fn` (the annual facade) is injectable -> simulator and optimizer build/test against a stub.
  * Explanations are STRUCTURED DATA; the narrative layer only renders them, never computes them.

SCOPE v1: federal/Union taxes only. PGBL/VGBL private pension is reserved for phase 2
(enum present, regime not detailed here).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

# ----------------------------------------------------------------------------- #
# Aliases & enums
# ----------------------------------------------------------------------------- #

Money = float          # BRL; rounded to cents at output.
Year = int
Rate = float           # decimal fraction, e.g. 0.275 == 27.5%


class DeclarationModel(str, Enum):
    SIMPLIFIED = "simplified"
    COMPLETE = "complete"


class AssetClass(str, Enum):
    TAXABLE_FIXED_INCOME = "taxable_fixed_income"     # Tesouro, CDB, RDB, LF — regressive
    EXEMPT_FIXED_INCOME = "exempt_fixed_income"       # LCI, LCA, CRI, CRA, incentivized debentures
    FIXED_INCOME_FUND = "fixed_income_fund"           # regressive + come-cotas
    MULTIMARKET_FUND = "multimarket_fund"             # regressive + come-cotas
    EQUITY_FUND = "equity_fund"                       # 15% on redemption, no come-cotas
    STOCKS = "stocks"                                 # variable income: R$20k exemption, 15%/20%
    EQUITY_ETF = "equity_etf"                         # like stocks (without the R$20k exemption)
    FII = "fii"                                       # 20% on gains; monthly distributions exempt
    SAVINGS = "savings"                               # poupança — exempt
    PGBL = "pgbl"                                     # phase 2
    VGBL = "vgbl"                                     # phase 2


class IncomeKind(str, Enum):
    SALARY = "salary"                  # taxable (progressive)
    PRO_LABORE = "pro_labore"          # taxable (progressive)
    RENT = "rent"                      # taxable (progressive)
    DIVIDENDS = "dividends"            # new rule: 10% withholding if > R$50k/month/source; IRPFM base
    JCP = "jcp"                        # withheld at source
    OTHER_TAXABLE = "other_taxable"
    EXEMPT = "exempt"                  # enters the IRPFM base only, not the regular IRPF


class TradeKind(str, Enum):
    SWING = "swing"                    # common stock operation: R$20k monthly exemption, 15%
    DAY_TRADE = "day_trade"            # 20%, no exemption
    FII = "fii"                        # 20%, no exemption


class GoalKind(str, Enum):
    RETIREMENT = "retirement"
    PURCHASE = "purchase"
    EDUCATION = "education"
    EMERGENCY_FUND = "emergency_fund"


class Objective(str, Enum):
    MAX_MEDIAN_NET_WORTH = "max_median_net_worth"
    MAX_SUCCESS_PROBABILITY = "max_success_probability"
    MIN_LIFETIME_TAX = "min_lifetime_tax"


class KeyDriver(str, Enum):
    """Fixed taxonomy for Explanation.key_drivers. The optimizer populates these strings;
    the rendering layer maps each value to a Portuguese label."""
    IRPF_REDUCER_BENEFIT = "irpf_reducer_benefit"           # Lei 15.270/2025 reducer materially reduces tax
    TAX_EFFICIENCY = "tax_efficiency"                       # total lifetime tax differs across strategies
    DEBT_COST_REDUCTION = "debt_cost_reduction"             # paying down high-cost debt improves net return
    SEQUENCE_OF_RETURNS_RISK = "sequence_of_returns_risk"   # path dispersion drives success probability
    VARIABLE_INCOME_EXEMPTION = "variable_income_exemption" # R$20k monthly swing exemption utilisation
    FIXED_INCOME_HOLDING_PERIOD = "fixed_income_holding_period"  # regressive table rate changes with time
    IRPFM_THRESHOLD = "irpfm_threshold"                     # strategy crosses or avoids the R$600k floor
    ASSET_ALLOCATION = "asset_allocation"                   # risk/return mix across asset classes


# ----------------------------------------------------------------------------- #
# Domain model — what the person HAS
# ----------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class Holding:
    id: str
    name: str
    asset_class: AssetClass
    balance: Money
    cost_basis: Money | None = None    # required to compute gain on sale
    acquisition_year: Year | None = None   # for the holding period (regressive table)


@dataclass(frozen=True, slots=True)
class Debt:
    id: str
    name: str
    balance: Money
    annual_interest_rate: Rate
    minimum_payment: Money


@dataclass(frozen=True, slots=True)
class IncomeStream:
    id: str
    name: str
    monthly_amount: Money
    kind: IncomeKind
    start_year: Year
    end_year: Year | None = None       # None == ongoing


@dataclass(frozen=True, slots=True)
class Goal:
    id: str
    name: str
    kind: GoalKind
    target_amount: Money
    target_year: Year


@dataclass(frozen=True, slots=True)
class Taxpayer:
    age: int
    retirement_age: int
    dependents: int = 0
    state: str | None = None           # UF code; reserved — state taxes are out of scope


@dataclass(frozen=True, slots=True)
class FinancialState:
    taxpayer: Taxpayer
    base_year: Year
    holdings: tuple[Holding, ...] = ()
    debts: tuple[Debt, ...] = ()
    incomes: tuple[IncomeStream, ...] = ()
    goals: tuple[Goal, ...] = ()
    annual_expenses: Money = 0.0
    deductible_expenses_annual: Money = 0.0   # health/education for the complete model


# ----------------------------------------------------------------------------- #
# Tax configuration — DATA, not code (one instance per calendar year)
# ----------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class IRPFBracket:
    lower_bound: Money         # tax base from which this rate applies
    rate: Rate
    deduction: Money           # "parcela a deduzir"


@dataclass(frozen=True, slots=True)
class RegressiveBand:
    max_days: int | None       # upper holding-period bound in days (None == longest band)
    rate: Rate                 # 0.225 / 0.20 / 0.175 / 0.15


@dataclass(frozen=True, slots=True)
class TaxTables:
    """All brackets/rates for one calendar year. A new year is a new instance."""
    year: Year
    # IRPF (regime 1)
    irpf_monthly_brackets: tuple[IRPFBracket, ...]
    irpf_annual_brackets: tuple[IRPFBracket, ...]
    irpf_exemption_limit_monthly: Money    # e.g. 5000.00 (Lei 15.270/2025)
    irpf_reduction_upper_limit_monthly: Money  # e.g. 7350.00 (end of the partial reduction)
    dependent_deduction_annual: Money
    simplified_discount_cap_annual: Money
    # Variable income (regime 2)
    equity_monthly_exemption: Money        # e.g. 20000.00
    equity_swing_rate: Rate                # 0.15
    equity_day_trade_rate: Rate            # 0.20
    fii_rate: Rate                         # 0.20
    # Fixed income / funds (regime 3)
    regressive_bands: tuple[RegressiveBand, ...]  # ascending by holding period
    come_cotas_rate: Rate                  # minimum rate applied semiannually
    equity_fund_rate: Rate                 # 0.15
    # Dividends / high income (regime 4)
    dividend_monthly_threshold_per_source: Money  # 50000.00 — above this, 10% withholding
    dividend_withholding_rate: Rate        # 0.10
    irpfm_income_floor_annual: Money       # 600000.00
    irpfm_income_ceiling_annual: Money     # 1200000.00
    irpfm_max_rate: Rate                   # 0.10


# ----------------------------------------------------------------------------- #
# Regime 1 — IRPF (taxable income, progressive + 2026 reducer). PURE function.
# ----------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class IRPFScenario:
    year: Year
    monthly_taxable_income: tuple[Money, ...]   # 12 values (salary + rent + pró-labore)
    deductible_expenses_annual: Money = 0.0
    dependents: int = 0


@dataclass(frozen=True, slots=True)
class IRPFResult:
    tax_due: Money
    tax_base: Money
    model_used: DeclarationModel          # whichever minimized the tax
    marginal_rate: Rate
    effective_rate: Rate
    reduction_applied: Money              # benefit from Lei 15.270/2025


def compute_irpf(scenario: IRPFScenario, tables: TaxTables) -> IRPFResult:
    """PURE. Applies the progressive table, picks simplified vs complete (whichever is cheaper),
    and applies the Lei 15.270/2025 reducer month by month.
    Invariants (lock as golden tests):
      * The reducer zeroes the tax for a monthly base up to `irpf_exemption_limit_monthly` and
        decays linearly up to `irpf_reduction_upper_limit_monthly`; it never produces negative tax.
      * model_used == the one that yields the lower tax_due.
      * effective_rate == tax_due / sum(income); 0 if the sum is 0.
    """
    raise NotImplementedError


# ----------------------------------------------------------------------------- #
# Regime 2 — Variable income (monthly). PURE function with loss carryforward.
# ----------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class MonthlyTrades:
    month: int                            # 1..12
    swing_sales_total: Money              # total stock sales in the month (for the R$20k exemption)
    swing_gain: Money                     # net swing profit in the month (may be negative)
    day_trade_gain: Money
    fii_gain: Money


@dataclass(frozen=True, slots=True)
class VariableIncomeResult:
    tax_due: Money
    exemption_applied: bool               # True if swing_sales_total <= exemption in the month(s)
    loss_carryforward_out: Money          # carry to the next period (only within the stock market)


def compute_variable_income(
    months: Sequence[MonthlyTrades],
    tables: TaxTables,
    loss_carryforward_in: Money = 0.0,
) -> VariableIncomeResult:
    """PURE. Month-by-month assessment:
      * swing: exempt if the month's `swing_sales_total` <= `equity_monthly_exemption`; else 15% on the gain.
      * day trade and FII: no exemption (20%).
      * losses offset future gains ONLY within variable income (they do not reduce IRPF).
    """
    raise NotImplementedError


# ----------------------------------------------------------------------------- #
# Regime 3 — Fixed income and funds (regressive + come-cotas). PURE functions.
# ----------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class Redemption:
    asset_class: AssetClass
    gain: Money                           # taxable income of the redemption
    days_held: int


def compute_fixed_income_tax(redemption: Redemption, tables: TaxTables) -> Money:
    """PURE. Applies the `regressive_bands` rate matching `days_held`.
    Exempt classes (EXEMPT_FIXED_INCOME, SAVINGS) return 0. EQUITY_FUND uses `equity_fund_rate`.
    """
    raise NotImplementedError


def compute_come_cotas(semiannual_gain: Money, tables: TaxTables) -> Money:
    """PURE. Semiannual prepayment on open funds (fixed income/multimarket) at `come_cotas_rate`,
    credited against the tax due at final redemption."""
    raise NotImplementedError


# ----------------------------------------------------------------------------- #
# Regime 4 + annual facade — IRPFM and yearly aggregation. PURE; this is the tax_fn.
# ----------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class AnnualTaxScenario:
    """Everything ONE simulated year needs. Built from the FinancialState upstream."""
    year: Year
    irpf: IRPFScenario
    variable_income_trades: tuple[MonthlyTrades, ...] = ()
    redemptions: tuple[Redemption, ...] = ()
    dividends_total_annual: Money = 0.0
    max_monthly_dividend_per_source: Money = 0.0   # trigger for the 10% withholding
    jcp_received_annual: Money = 0.0
    exempt_income_annual: Money = 0.0              # enters the IRPFM base only
    variable_income_loss_carryforward_in: Money = 0.0


@dataclass(frozen=True, slots=True)
class AnnualTaxResult:
    irpf: IRPFResult
    variable_income_tax: Money
    fixed_income_tax: Money
    dividend_withholding: Money           # 10% if above the per-source monthly threshold
    irpfm_additional: Money               # top-up of the high-income minimum tax
    total_tax: Money
    variable_income_loss_carryforward_out: Money


def compute_irpfm(total_annual_income: Money, tax_already_assessed: Money, tables: TaxTables) -> Money:
    """PURE. High-income minimum tax. Above `irpfm_income_floor_annual` the rate rises linearly
    from 0 to `irpfm_max_rate` up to `irpfm_income_ceiling_annual`, then stays at the cap above that.
    Returns only the TOP-UP (minimum minus what was already assessed), never negative. The base
    includes exempt income and income taxed at source.
    """
    raise NotImplementedError


def compute_annual_tax(scenario: AnnualTaxScenario, tables: TaxTables) -> AnnualTaxResult:
    """PURE — this is the facade injected into the simulator (see TaxFn). Orchestrates the four
    regimes for one year and returns the consolidated result. Must be fast: it is called once per
    year per path inside the Monte Carlo loop.
    Invariant: total_tax == irpf.tax_due + variable_income_tax + fixed_income_tax
                            + dividend_withholding + irpfm_additional (within cent rounding).
    """
    raise NotImplementedError


class TaxFn(Protocol):
    """Injection point: the annual facade. Lets the simulator and optimizer be built/tested against
    a stub before the real tax engine lands on main."""
    def __call__(self, scenario: AnnualTaxScenario, tables: TaxTables) -> AnnualTaxResult: ...


# ----------------------------------------------------------------------------- #
# Simulation — Monte Carlo over return PATHS (BRL, inflation via IPCA)
# ----------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class AssetClassAssumptions:
    """Per-asset-class return override. If an AssetClass is not listed in
    MarketAssumptions.per_class, the global mean_real_return / return_volatility apply."""
    asset_class: AssetClass
    mean_real_return: Rate
    return_volatility: Rate


@dataclass(frozen=True, slots=True)
class MarketAssumptions:
    mean_real_return: Rate                # global fallback, e.g. 0.05
    return_volatility: Rate               # global fallback annual std-dev
    ipca_mean: Rate = 0.04                # expected inflation
    ipca_volatility: Rate = 0.015
    per_class: tuple[AssetClassAssumptions, ...] = ()  # overrides global defaults per AssetClass


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    years: int
    n_paths: int = 10_000
    seed: int | None = None               # set for reproducibility


@dataclass(frozen=True, slots=True)
class YearPercentiles:
    year: Year
    p10: Money
    p50: Money
    p90: Money


@dataclass(frozen=True, slots=True)
class SimulationResult:
    success_probability: Rate             # fraction of paths that meet the goals
    terminal_p10: Money
    terminal_p50: Money
    terminal_p90: Money
    by_year: tuple[YearPercentiles, ...]
    paths_simulated: int


def run_simulation(
    state: FinancialState,
    assumptions: MarketAssumptions,
    config: SimulationConfig,
    tax_fn: TaxFn,
    tax_tables_by_year: Sequence[TaxTables],
) -> SimulationResult:
    """Samples return PATHS (not a single mean) to capture sequence-of-returns risk. Calls `tax_fn`
    once per simulated year per path — keep it pure and fast. `tax_fn` is injected so this engine
    can be built and tested against a stub before the real tax engine lands on main.
    """
    raise NotImplementedError


# ----------------------------------------------------------------------------- #
# Optimizer — evaluate candidate strategies, rank by objective
# ----------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class Strategy:
    id: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class StrategyOutcome:
    strategy: Strategy
    result: SimulationResult
    lifetime_tax: Money


@dataclass(frozen=True, slots=True)
class Explanation:
    """STRUCTURED numbers for the narrative layer to render — never prose itself. A template or LLM
    turns these into human text; it must not compute the numbers."""
    objective: Objective
    winner_id: str
    winner_metric: float
    runner_up_id: str | None
    delta_vs_runner_up: float
    key_drivers: tuple[KeyDriver, ...]


@dataclass(frozen=True, slots=True)
class Recommendation:
    objective: Objective
    ranked: tuple[StrategyOutcome, ...]   # best first
    explanation: Explanation


def optimize(
    state: FinancialState,
    candidates: Sequence[Strategy],
    objective: Objective,
    assumptions: MarketAssumptions,
    config: SimulationConfig,
    tax_fn: TaxFn,
    tax_tables_by_year: Sequence[TaxTables],
) -> Recommendation:
    """Evaluates each strategy via `run_simulation` and ranks by `objective`. The tax cost curve is
    NON-MONOTONIC (the R$20k exemption, brackets, IRPFM, the IRPF reducer), so ranking must come from
    full evaluation of each candidate — never from assuming a smooth objective.
    """
    raise NotImplementedError


__all__ = [
    "Money", "Year", "Rate",
    "DeclarationModel", "AssetClass", "IncomeKind", "TradeKind", "GoalKind", "Objective", "KeyDriver",
    "Holding", "Debt", "IncomeStream", "Goal", "Taxpayer", "FinancialState",
    "IRPFBracket", "RegressiveBand", "TaxTables",
    "IRPFScenario", "IRPFResult", "compute_irpf",
    "MonthlyTrades", "VariableIncomeResult", "compute_variable_income",
    "Redemption", "compute_fixed_income_tax", "compute_come_cotas",
    "AnnualTaxScenario", "AnnualTaxResult", "compute_irpfm", "compute_annual_tax", "TaxFn",
    "AssetClassAssumptions", "MarketAssumptions", "SimulationConfig",
    "YearPercentiles", "SimulationResult", "run_simulation",
    "Strategy", "StrategyOutcome", "Explanation", "Recommendation", "optimize",
]
