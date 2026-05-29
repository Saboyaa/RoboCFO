import { useMutation } from "@tanstack/react-query";
import type {
  SimulationResult,
  Recommendation,
  ExplainRequest,
  ExplainResponse,
} from "./types";

// ---------------------------------------------------------------------------
// Mock fixture data (used until the real backend is wired)
// ---------------------------------------------------------------------------

export const MOCK_SIMULATION_RESULT: SimulationResult = {
  success_probability: 0.78,
  terminal_p10: 450_000,
  terminal_p50: 1_200_000,
  terminal_p90: 2_800_000,
  paths_simulated: 10_000,
  by_year: Array.from({ length: 30 }, (_, i) => ({
    year: 2026 + i,
    p10: 100_000 * Math.pow(1.02, i + 1),
    p50: 100_000 * Math.pow(1.05, i + 1),
    p90: 100_000 * Math.pow(1.09, i + 1),
  })),
} as const;

export const MOCK_RECOMMENDATION: Recommendation = {
  objective: "max_median_net_worth",
  ranked: [
    {
      strategy: {
        id: "invest_first_fixed",
        name: "Investir primeiro (renda fixa)",
        description: "Prioriza investimentos em renda fixa antes de quitar dívidas.",
      },
      result: MOCK_SIMULATION_RESULT,
      lifetime_tax: 85_000,
    },
    {
      strategy: {
        id: "balanced",
        name: "Equilibrado: metade dívida, metade investimento",
        description: "Divide recursos entre pagamento de dívidas e investimentos.",
      },
      result: {
        ...MOCK_SIMULATION_RESULT,
        terminal_p50: 1_050_000,
        success_probability: 0.71,
      },
      lifetime_tax: 72_000,
    },
    {
      strategy: {
        id: "pay_debt_first",
        name: "Quitar dívidas de alto custo primeiro",
        description: "Foca em eliminar dívidas caras antes de investir.",
      },
      result: {
        ...MOCK_SIMULATION_RESULT,
        terminal_p50: 980_000,
        success_probability: 0.65,
      },
      lifetime_tax: 61_000,
    },
  ],
  explanation: {
    objective: "max_median_net_worth",
    winner_id: "invest_first_fixed",
    winner_metric: 1_200_000,
    runner_up_id: "balanced",
    delta_vs_runner_up: 150_000,
    key_drivers: ["tax_efficiency", "fixed_income_holding_period", "asset_allocation"],
  },
} as const;

// ---------------------------------------------------------------------------
// Mock API functions (replace with real fetch once backend is ready)
// ---------------------------------------------------------------------------

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function mockSimulate(_vars: { years: number }): Promise<SimulationResult> {
  await delay(300);
  return MOCK_SIMULATION_RESULT;
}

async function mockOptimize(_vars: { years: number }): Promise<Recommendation> {
  await delay(500);
  return MOCK_RECOMMENDATION;
}

async function mockExplain(_req: ExplainRequest): Promise<ExplainResponse> {
  await delay(800);
  return {
    text:
      "A estratégia vencedora, 'Investir primeiro (renda fixa)', supera as demais em " +
      "R$ 150.000 no patrimônio mediano ao final do período. Os principais fatores são a " +
      "eficiência fiscal dos investimentos em renda fixa com prazos superiores a 720 dias " +
      "(alíquota de 15%) e a diversificação da carteira, que reduz o risco de sequência de retornos. " +
      "Consulte um profissional habilitado antes de tomar decisões financeiras.",
  };
}

// ---------------------------------------------------------------------------
// TanStack Query hooks
// ---------------------------------------------------------------------------

export function useSimulate() {
  return useMutation<SimulationResult, Error, { years: number }>({
    mutationFn: mockSimulate,
  });
}

export function useOptimize() {
  return useMutation<Recommendation, Error, { years: number }>({
    mutationFn: mockOptimize,
  });
}

export function useExplain() {
  return useMutation<ExplainResponse, Error, ExplainRequest>({
    mutationFn: mockExplain,
  });
}
