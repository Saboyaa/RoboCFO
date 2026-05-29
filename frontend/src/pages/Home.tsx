import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import { MOCK_RECOMMENDATION, MOCK_SIMULATION_RESULT } from "../api/client";
import type { Recommendation, SimulationResult } from "../api/types";

export interface ResultsState {
  recommendation: Recommendation;
  simulation: SimulationResult;
}

export default function Home() {
  const [years, setYears] = useState(30);
  const navigate = useNavigate();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const state: ResultsState = {
      recommendation: MOCK_RECOMMENDATION,
      simulation: { ...MOCK_SIMULATION_RESULT, by_year: MOCK_SIMULATION_RESULT.by_year.slice(0, years) },
    };
    navigate("/results", { state });
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center gap-3">
          <span className="text-2xl">📊</span>
          <div>
            <h1 className="text-lg font-bold text-white">Robo-CFO</h1>
            <p className="text-xs text-slate-500">Simulador de finanças pessoais · Brasil</p>
          </div>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-6 py-16">
        <div className="w-full max-w-lg">
          {/* Hero */}
          <div className="mb-8 text-center">
            <div className="mb-4 inline-flex rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-1.5 text-sm text-blue-400">
              Simulador educacional
            </div>
            <h2 className="mb-3 text-4xl font-bold text-white">
              Tome decisões financeiras<br />
              <span className="text-blue-400">com clareza</span>
            </h2>
            <p className="text-slate-400">
              Compare estratégias de investimento e dívida via simulação Monte Carlo com tributação brasileira real.
            </p>
          </div>

          {/* Card */}
          <div className="rounded-2xl border border-slate-700/60 bg-slate-800/60 p-8 shadow-xl backdrop-blur">
            <Disclaimer />

            <form onSubmit={handleSubmit} className="mt-6 space-y-6">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-300">
                  Horizonte de simulação
                </label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min={5}
                    max={50}
                    value={years}
                    onChange={e => setYears(Number(e.target.value))}
                    className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-700 accent-blue-500"
                  />
                  <span className="w-20 text-right text-2xl font-bold text-blue-400">{years} <span className="text-sm font-normal text-slate-400">anos</span></span>
                </div>
              </div>

              {/* Feature pills */}
              <div className="grid grid-cols-3 gap-2 text-center">
                {[
                  { icon: '🎯', label: '5 estratégias' },
                  { icon: '📈', label: '10.000 caminhos' },
                  { icon: '🇧🇷', label: 'IR brasileiro' },
                ].map(f => (
                  <div key={f.label} className="rounded-lg border border-slate-700/50 bg-slate-800 py-3">
                    <div className="text-lg">{f.icon}</div>
                    <div className="mt-1 text-xs text-slate-400">{f.label}</div>
                  </div>
                ))}
              </div>

              <button
                type="submit"
                className="w-full rounded-xl bg-blue-600 px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-blue-500/20 transition-all hover:bg-blue-500 hover:shadow-blue-500/30 active:scale-95"
              >
                Simular agora →
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
