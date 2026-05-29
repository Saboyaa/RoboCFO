import { useLocation, Navigate } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import FanChart from "../components/FanChart";
import StrategyComparison from "../components/StrategyComparison";
import ExplanationCard from "../components/ExplanationCard";
import type { ResultsState } from "./Home";

const KEY_DRIVER_LABELS: Record<string, string> = {
  irpf_reducer_benefit: "Benefício do redutor IRPF (Lei 15.270/2025)",
  tax_efficiency: "Eficiência tributária",
  debt_cost_reduction: "Redução do custo da dívida",
  sequence_of_returns_risk: "Risco de sequência de retornos",
  variable_income_exemption: "Isenção de renda variável (R$20k)",
  fixed_income_holding_period: "Prazo de renda fixa (tabela regressiva)",
  irpfm_threshold: "Limiar do IRPFM (R$600k)",
  asset_allocation: "Alocação de ativos",
};

export default function Results() {
  const location = useLocation();
  const state = location.state as ResultsState | null;
  if (!state) return <Navigate to="/" replace />;

  const { recommendation, simulation } = state;
  const winner = recommendation.ranked[0];
  const { explanation } = recommendation;

  const templateText =
    `A estratégia "${winner.strategy.name}" superou as demais com patrimônio mediano de ` +
    `R$ ${winner.result.terminal_p50.toLocaleString("pt-BR")} ao longo dos anos simulados. ` +
    `Principais fatores: ${explanation.key_drivers.map(k => KEY_DRIVER_LABELS[k] ?? k).join(", ")}.`;

  const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <svg className="h-4 w-4 text-white" viewBox="0 0 20 20" fill="currentColor"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Robo-CFO</h1>
              <p className="text-xs text-slate-500">Simulador de finanças pessoais · Brasil</p>
            </div>
          </div>
          <a href="/" className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-400 transition-colors hover:border-slate-500 hover:text-slate-200">
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd"/></svg>
            Nova simulação
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-6 py-8">
        <Disclaimer />

        {/* KPI strip */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: 'Probabilidade de sucesso', value: `${(simulation.success_probability * 100).toFixed(0)}%`, color: 'text-emerald-400' },
            { label: 'Patrimônio mediano (P50)', value: brl.format(simulation.terminal_p50), color: 'text-blue-400' },
            { label: 'Cenário pessimista (P10)', value: brl.format(simulation.terminal_p10), color: 'text-rose-400' },
            { label: 'Cenário otimista (P90)', value: brl.format(simulation.terminal_p90), color: 'text-sky-400' },
          ].map(kpi => (
            <div key={kpi.label} className="rounded-xl border border-slate-700/60 bg-slate-800/50 p-4">
              <p className="text-xs text-slate-500">{kpi.label}</p>
              <p className={`mt-1 text-xl font-bold tabular-nums ${kpi.color}`}>{kpi.value}</p>
            </div>
          ))}
        </div>

        {/* Chart */}
        <div className="rounded-xl border border-slate-700/60 bg-slate-800/50 p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Evolução patrimonial — Monte Carlo
          </h2>
          <FanChart data={[...simulation.by_year]} />
        </div>

        {/* Strategy table */}
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Comparação de estratégias
          </h2>
          <StrategyComparison ranked={recommendation.ranked} />
        </div>

        {/* Explanation */}
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Análise
          </h2>
          <ExplanationCard explanation={explanation} templateText={templateText} />
        </div>
      </main>
    </div>
  );
}
