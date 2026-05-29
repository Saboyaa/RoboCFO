// TypeScript types mirroring contracts.py (frozen).  No `any`.

export type Money = number;
export type Year = number;
export type Rate = number;

export type AssetClass =
  | "taxable_fixed_income"
  | "exempt_fixed_income"
  | "fixed_income_fund"
  | "multimarket_fund"
  | "equity_fund"
  | "stocks"
  | "equity_etf"
  | "fii"
  | "savings"
  | "pgbl"
  | "vgbl";

export type IncomeKind =
  | "salary"
  | "pro_labore"
  | "rent"
  | "dividends"
  | "jcp"
  | "other_taxable"
  | "exempt";

export type GoalKind = "retirement" | "purchase" | "education" | "emergency_fund";

export type Objective =
  | "max_median_net_worth"
  | "max_success_probability"
  | "min_lifetime_tax";

export type KeyDriver =
  | "irpf_reducer_benefit"
  | "tax_efficiency"
  | "debt_cost_reduction"
  | "sequence_of_returns_risk"
  | "variable_income_exemption"
  | "fixed_income_holding_period"
  | "irpfm_threshold"
  | "asset_allocation";

export interface YearPercentiles {
  readonly year: Year;
  readonly p10: Money;
  readonly p50: Money;
  readonly p90: Money;
}

export interface SimulationResult {
  readonly success_probability: Rate;
  readonly terminal_p10: Money;
  readonly terminal_p50: Money;
  readonly terminal_p90: Money;
  readonly by_year: readonly YearPercentiles[];
  readonly paths_simulated: number;
}

export interface Strategy {
  readonly id: string;
  readonly name: string;
  readonly description: string;
}

export interface StrategyOutcome {
  readonly strategy: Strategy;
  readonly result: SimulationResult;
  readonly lifetime_tax: Money;
}

export interface Explanation {
  readonly objective: Objective;
  readonly winner_id: string;
  readonly winner_metric: number;
  readonly runner_up_id: string | null;
  readonly delta_vs_runner_up: number;
  readonly key_drivers: readonly KeyDriver[];
}

export interface Recommendation {
  readonly objective: Objective;
  readonly ranked: readonly StrategyOutcome[];
  readonly explanation: Explanation;
}

export interface AssetClassAssumptions {
  readonly asset_class: AssetClass;
  readonly mean_real_return: Rate;
  readonly return_volatility: Rate;
}

export interface MarketAssumptions {
  readonly mean_real_return: Rate;
  readonly return_volatility: Rate;
  readonly ipca_mean?: Rate;
  readonly ipca_volatility?: Rate;
  readonly per_class?: readonly AssetClassAssumptions[];
}

export interface SimulationConfig {
  readonly years: number;
  readonly n_paths?: number;
  readonly seed?: number | null;
}

export interface Holding {
  readonly id: string;
  readonly name: string;
  readonly asset_class: AssetClass;
  readonly balance: Money;
  readonly cost_basis?: Money | null;
  readonly acquisition_year?: Year | null;
}

export interface Debt {
  readonly id: string;
  readonly name: string;
  readonly balance: Money;
  readonly annual_interest_rate: Rate;
  readonly minimum_payment: Money;
}

export interface IncomeStream {
  readonly id: string;
  readonly name: string;
  readonly monthly_amount: Money;
  readonly kind: IncomeKind;
  readonly start_year: Year;
  readonly end_year?: Year | null;
}

export interface Goal {
  readonly id: string;
  readonly name: string;
  readonly kind: GoalKind;
  readonly target_amount: Money;
  readonly target_year: Year;
}

export interface Taxpayer {
  readonly age: number;
  readonly retirement_age: number;
  readonly dependents?: number;
  readonly state?: string | null;
}

export interface FinancialState {
  readonly taxpayer: Taxpayer;
  readonly base_year: Year;
  readonly holdings?: readonly Holding[];
  readonly debts?: readonly Debt[];
  readonly incomes?: readonly IncomeStream[];
  readonly goals?: readonly Goal[];
  readonly annual_expenses?: Money;
  readonly deductible_expenses_annual?: Money;
}

export interface ExplainRequest {
  readonly explanation: Explanation;
  readonly use_llm: boolean;
}

export interface ExplainResponse {
  readonly text: string;
}
