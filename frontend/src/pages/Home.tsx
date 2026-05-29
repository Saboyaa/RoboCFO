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

const ASSUMPTIONS = {
  mean_real_return: 0.05,
  return_volatility: 0.12,
  ipca_mean: 0.04,
  ipca_volatility: 0.015,
  per_class: [
    { asset_class: "stocks",               mean_real_return: 0.07, return_volatility: 0.20 },
    { asset_class: "taxable_fixed_income", mean_real_return: 0.04, return_volatility: 0.01 },
    { asset_class: "exempt_fixed_income",  mean_real_return: 0.04, return_volatility: 0.01 },
    { asset_class: "fii",                  mean_real_return: 0.06, return_volatility: 0.15 },
  ],
};

interface Profile {
  age: number;
  retirementAge: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  stocks: number;
  fixedIncome: number;
  exemptFixedIncome: number;
  fii: number;
  savings: number;
  debtBalance: number;
  debtRate: number;        // % a.a.
  debtMinPayment: number;
  retirementGoal: number;
}

const DEFAULTS: Profile = {
  age: 35,
  retirementAge: 65,
  monthlyIncome: 12200,
  monthlyExpenses: 7000,
  stocks: 80000,
  fixedIncome: 50000,
  exemptFixedIncome: 30000,
  fii: 25000,
  savings: 15000,
  debtBalance: 35000,
  debtRate: 18,
  debtMinPayment: 900,
  retirementGoal: 3000000,
};

function buildState(p: Profile, years: number) {
  const retirementYear = 2026 + (p.retirementAge - p.age);
  return {
    taxpayer: { age: p.age, retirement_age: p.retirementAge, dependents: 0, state: null },
    base_year: 2026,
    holdings: [
      { id: "stocks", name: "Ações",           asset_class: "stocks",               balance: p.stocks,           cost_basis: p.stocks * 0.8,  acquisition_year: 2023 },
      { id: "cdb",    name: "Renda Fixa (CDB)", asset_class: "taxable_fixed_income", balance: p.fixedIncome,      cost_basis: p.fixedIncome,   acquisition_year: 2024 },
      { id: "lci",    name: "LCI/LCA",          asset_class: "exempt_fixed_income",  balance: p.exemptFixedIncome, cost_basis: p.exemptFixedIncome, acquisition_year: 2024 },
      { id: "fii",    name: "FII",              asset_class: "fii",                  balance: p.fii,              cost_basis: p.fii * 0.9,    acquisition_year: 2023 },
      { id: "poup",   name: "Poupança",         asset_class: "savings",              balance: p.savings,          cost_basis: p.savings,       acquisition_year: 2024 },
    ].filter(h => h.balance > 0),
    debts: p.debtBalance > 0 ? [
      { id: "debt", name: "Dívida", balance: p.debtBalance, annual_interest_rate: p.debtRate / 100, minimum_payment: p.debtMinPayment },
    ] : [],
    incomes: [
      { id: "salary", name: "Renda mensal", monthly_amount: p.monthlyIncome, kind: "salary", start_year: 2026, end_year: null },
    ],
    goals: [
      { id: "ret", name: "Aposentadoria", kind: "retirement", target_amount: p.retirementGoal, target_year: retirementYear + years },
    ],
    annual_expenses: p.monthlyExpenses * 12,
    deductible_expenses_annual: 0,
  };
}

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

function NumInput({ label, value, onChange, prefix = "R$", min = 0, hint }: {
  label: string; value: number; onChange: (v: number) => void;
  prefix?: string; min?: number; hint?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-400">{label}</label>
      <div className="relative">
        {prefix && (
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-xs text-slate-500">{prefix}</span>
        )}
        <input
          type="number" min={min} step="any" value={value}
          onChange={e => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
          className={`w-full rounded-lg border border-slate-700 bg-slate-900 py-2 text-sm text-white focus:border-blue-500 focus:outline-none ${prefix ? "pl-8 pr-3" : "px-3"}`}
        />
      </div>
      {hint && <p className="mt-1 text-xs text-slate-600">{hint}</p>}
    </div>
  );
}

const STORAGE_KEY = "robo-cfo-profile-v1";

function loadProfile(): Profile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
}

export default function Home() {
  const [years, setYears] = useState(() => Number(localStorage.getItem("robo-cfo-years") || 30));
  const [profile, setProfile] = useState<Profile>(loadProfile);
  const [showEdit, setShowEdit] = useState(false);
  const navigate = useNavigate();
  const { mutate, isPending, isError } = useOptimize();

  function set(k: keyof Profile) {
    return (v: number) => setProfile(p => {
      const next = { ...p, [k]: v };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }

  function handleYears(v: number) {
    setYears(v);
    localStorage.setItem("robo-cfo-years", String(v));
  }

  const totalInvestments = profile.stocks + profile.fixedIncome + profile.exemptFixedIncome + profile.fii + profile.savings;
  const monthlySavings = profile.monthlyIncome - profile.monthlyExpenses - (profile.debtBalance > 0 ? profile.debtMinPayment : 0);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutate(
      {
        state: buildState(profile, years),
        candidates: [],
        objective: "max_median_net_worth",
        assumptions: ASSUMPTIONS,
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
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="mx-auto flex max-w-3xl items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
            <svg className="h-4 w-4 text-white" viewBox="0 0 20 20" fill="currentColor"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Robo-CFO</h1>
            <p className="text-xs text-slate-500">Simulador educacional · Brasil</p>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl space-y-5 px-6 py-10">
        <div className="text-center">
          <h2 className="mb-2 text-3xl font-bold text-white">
            Compare estratégias com <span className="text-blue-400">tributação real</span>
          </h2>
          <p className="text-sm text-slate-400">Monte Carlo · IRPF · Renda variável · Renda fixa · IRPFM</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Snapshot bar */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Patrimônio", value: brl.format(totalInvestments), color: "text-emerald-400" },
              { label: "Renda mensal", value: brl.format(profile.monthlyIncome), color: "text-blue-400" },
              { label: "Poupança/mês", value: brl.format(monthlySavings), color: monthlySavings >= 0 ? "text-sky-400" : "text-rose-400" },
              { label: "Dívida", value: brl.format(profile.debtBalance), color: "text-rose-400" },
            ].map(k => (
              <div key={k.label} className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-3">
                <p className="text-xs text-slate-500">{k.label}</p>
                <p className={`mt-1 font-bold tabular-nums ${k.color}`}>{k.value}</p>
              </div>
            ))}
          </div>

          {/* Edit toggle */}
          <button
            type="button"
            onClick={() => setShowEdit(v => !v)}
            className="flex w-full items-center justify-between rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-3 text-sm text-slate-300 hover:bg-slate-800"
          >
            <span className="font-medium">{showEdit ? "Ocultar dados financeiros" : "Editar dados financeiros"}</span>
            <svg className={`h-4 w-4 text-slate-500 transition-transform ${showEdit ? "rotate-180" : ""}`} viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd"/></svg>
          </button>

          {showEdit && (
            <div className="rounded-2xl border border-slate-700/60 bg-slate-800/40 p-5 space-y-5">
              {/* Pessoa */}
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Perfil</p>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <NumInput label="Idade atual" value={profile.age} onChange={set("age")} prefix="" min={18} />
                  <NumInput label="Idade de aposentadoria" value={profile.retirementAge} onChange={set("retirementAge")} prefix="" min={40} />
                  <NumInput label="Meta de aposentadoria" value={profile.retirementGoal} onChange={set("retirementGoal")} />
                </div>
              </div>

              {/* Renda & gastos */}
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Fluxo de caixa</p>
                <div className="grid grid-cols-2 gap-3">
                  <NumInput label="Renda mensal bruta" value={profile.monthlyIncome} onChange={set("monthlyIncome")} />
                  <NumInput label="Gastos mensais" value={profile.monthlyExpenses} onChange={set("monthlyExpenses")} />
                </div>
              </div>

              {/* Investimentos */}
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Patrimônio investido</p>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <NumInput label="Ações / ETFs" value={profile.stocks} onChange={set("stocks")} hint="15% ganho, isento ≤R$20k/mês" />
                  <NumInput label="Renda fixa (CDB, Tesouro)" value={profile.fixedIncome} onChange={set("fixedIncome")} hint="Tabela regressiva 22,5%→15%" />
                  <NumInput label="LCI / LCA / CRI / CRA" value={profile.exemptFixedIncome} onChange={set("exemptFixedIncome")} hint="Isento de IR" />
                  <NumInput label="FII" value={profile.fii} onChange={set("fii")} hint="20% sobre ganho de capital" />
                  <NumInput label="Poupança" value={profile.savings} onChange={set("savings")} hint="Isenta" />
                </div>
              </div>

              {/* Dívida */}
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Dívidas</p>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <NumInput label="Saldo devedor" value={profile.debtBalance} onChange={set("debtBalance")} />
                  <NumInput label="Taxa anual (%)" value={profile.debtRate} onChange={set("debtRate")} prefix="%" min={0} />
                  <NumInput label="Parcela mínima/mês" value={profile.debtMinPayment} onChange={set("debtMinPayment")} />
                </div>
              </div>
            </div>
          )}

          {/* Horizon + submit */}
          <div className="rounded-2xl border border-slate-700/60 bg-slate-800/60 p-5 space-y-4">
            <Disclaimer />
            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-medium text-slate-300">Horizonte de simulação</label>
                <span className="text-2xl font-bold text-blue-400">{years} <span className="text-sm font-normal text-slate-400">anos</span></span>
              </div>
              <input
                type="range" min={5} max={50} value={years}
                onChange={e => handleYears(Number(e.target.value))}
                className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-blue-500"
              />
            </div>

            {isError && (
              <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
                Erro ao conectar com o backend. Verifique se o servidor está rodando.
              </p>
            )}

            <button
              type="submit" disabled={isPending}
              className="w-full rounded-xl bg-blue-600 px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-500 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isPending ? "Simulando…" : "Simular agora →"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
