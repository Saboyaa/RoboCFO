import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import { useOptimize } from "../api/client";
import type { Recommendation, SimulationResult } from "../api/types";

export interface ResultsState {
  recommendation: Recommendation;
  simulation: SimulationResult;
  years: number;
}

// Sample fixture — mirrors backend/app/data/fixtures/sample_state.json
const SAMPLE_STATE = {
  taxpayer: { age: 35, retirement_age: 65, dependents: 1, state: "SP" },
  base_year: 2026,
  holdings: [
    { id: "stocks-01", name: "Ações (IBOV)", asset_class: "stocks", balance: 80000, cost_basis: 60000, acquisition_year: 2022 },
    { id: "cdb-01", name: "CDB 120% CDI", asset_class: "taxable_fixed_income", balance: 50000, cost_basis: 45000, acquisition_year: 2023 },
    { id: "lci-01", name: "LCI 95% CDI", asset_class: "exempt_fixed_income", balance: 30000, cost_basis: 28000, acquisition_year: 2024 },
    { id: "fii-01", name: "FII XPLG11", asset_class: "fii", balance: 25000, cost_basis: 22000, acquisition_year: 2023 },
    { id: "poupanca-01", name: "Poupança", asset_class: "savings", balance: 15000, cost_basis: 15000, acquisition_year: 2024 },
  ],
  debts: [
    { id: "financ-01", name: "Financiamento Veículo", balance: 35000, annual_interest_rate: 0.18, minimum_payment: 900 },
  ],
  incomes: [
    { id: "salary-01", name: "Salário CLT", monthly_amount: 12000, kind: "salary", start_year: 2026, end_year: null },
    { id: "fii-dist-01", name: "Rendimentos FII", monthly_amount: 200, kind: "exempt", start_year: 2026, end_year: null },
  ],
  goals: [
    { id: "retirement-01", name: "Aposentadoria", kind: "retirement", target_amount: 3000000, target_year: 2056 },
  ],
  annual_expenses: 84000,
  deductible_expenses_annual: 8400,
};

const SAMPLE_ASSUMPTIONS = {
  mean_real_return: 0.05,
  return_volatility: 0.12,
  ipca_mean: 0.04,
  ipca_volatility: 0.015,
  per_class: [
    { asset_class: "stocks", mean_real_return: 0.07, return_volatility: 0.20 },
    { asset_class: "taxable_fixed_income", mean_real_return: 0.04, return_volatility: 0.01 },
    { asset_class: "exempt_fixed_income", mean_real_return: 0.04, return_volatility: 0.01 },
    { asset_class: "fii", mean_real_return: 0.06, return_volatility: 0.15 },
  ],
};

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const totalInvestments = SAMPLE_STATE.holdings.reduce((s, h) => s + h.balance, 0);
const monthlyIncome = SAMPLE_STATE.incomes.reduce((s, i) => s + i.monthly_amount, 0);
const monthlyExpenses = SAMPLE_STATE.annual_expenses / 12;
const monthlyDebtMin = SAMPLE_STATE.debts.reduce((s, d) => s + d.minimum_payment, 0);
const monthlySavings = monthlyIncome - monthlyExpenses - monthlyDebtMin;
const totalDebt = SAMPLE_STATE.debts.reduce((s, d) => s + d.balance, 0);

export default function Home() {
  const [years, setYears] = useState(30);
  const navigate = useNavigate();
  const { mutate, isPending, isError } = useOptimize();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutate(
      {
        state: SAMPLE_STATE,
        candidates: [],  // backend uses all built-in strategies
        objective: "max_median_net_worth",
        assumptions: SAMPLE_ASSUMPTIONS,
        config: { years, n_paths: 1000, seed: 42 },
      },
      {
        onSuccess: (recommendation) => {
          const simulation = recommendation.ranked[0].result;
          navigate("/results", { state: { recommendation, simulation, years } satisfies ResultsState });
        },
      },
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center gap-3">
          <span className="text-2xl">📊</span>
          <div>
            <h1 className="text-lg font-bold text-white">Robo-CFO</h1>
            <p className="text-xs text-slate-500">Simulador educacional de finanças pessoais · Brasil</p>
          </div>
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl space-y-6">
          {/* Hero */}
          <div className="text-center">
            <div className="mb-3 inline-flex rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-1.5 text-sm text-blue-400">
              Simulador educacional — dados sintéticos
            </div>
            <h2 className="mb-3 text-4xl font-bold text-white">
              Compare estratégias<br />
              <span className="text-blue-400">com tributação brasileira real</span>
            </h2>
            <p className="text-slate-400">
              Monte Carlo com 1.000 caminhos, IRPF + renda variável + renda fixa + IRPFM.
            </p>
          </div>

          {/* Financial snapshot */}
          <div className="rounded-2xl border border-slate-700/60 bg-slate-800/60 p-6">
            <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Perfil simulado — 35 anos, São Paulo</p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "Patrimônio inicial", value: brl.format(totalInvestments), color: "text-emerald-400" },
                { label: "Renda mensal", value: brl.format(monthlyIncome), color: "text-blue-400" },
                { label: "Poupança mensal", value: brl.format(monthlySavings), color: "text-sky-400" },
                { label: "Dívida total (18% a.a.)", value: brl.format(totalDebt), color: "text-rose-400" },
              ].map(k => (
                <div key={k.label} className="rounded-xl border border-slate-700/50 bg-slate-800 p-3">
                  <p className="text-xs text-slate-500">{k.label}</p>
                  <p className={`mt-1 text-base font-bold tabular-nums ${k.color}`}>{k.value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Simulation config + submit */}
          <div className="rounded-2xl border border-slate-700/60 bg-slate-800/60 p-6">
            <Disclaimer />
            <form onSubmit={handleSubmit} className="mt-5 space-y-5">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-300">
                  Horizonte de simulação
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="range" min={5} max={50} value={years}
                    onChange={e => setYears(Number(e.target.value))}
                    className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-blue-500"
                  />
                  <span className="w-24 text-right text-2xl font-bold text-blue-400">
                    {years} <span className="text-sm font-normal text-slate-400">anos</span>
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span className="rounded border border-slate-700 px-2 py-1">5 estratégias</span>
                <span className="rounded border border-slate-700 px-2 py-1">1.000 caminhos MC</span>
                <span className="rounded border border-slate-700 px-2 py-1">IPCA estocástico</span>
                <span className="rounded border border-slate-700 px-2 py-1">IR real</span>
              </div>

              {isError && (
                <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
                  Erro ao conectar com o backend. Verifique se o servidor está rodando.
                </p>
              )}

              <button
                type="submit"
                disabled={isPending}
                className="w-full rounded-xl bg-blue-600 px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isPending ? "Simulando…" : "Simular agora →"}
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
