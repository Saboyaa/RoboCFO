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

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", padding: "0 16px" }}>
      <h1>Resultado da Simulação</h1>
      <Disclaimer />
      <h2>Evolução Patrimonial (P10 / P50 / P90)</h2>
      <FanChart data={[...simulation.by_year]} />
      <h2 style={{ marginTop: 32 }}>Comparação de Estratégias</h2>
      <StrategyComparison ranked={recommendation.ranked} />
      <h2>Explicação</h2>
      <ExplanationCard explanation={explanation} templateText={templateText} />
    </div>
  );
}
