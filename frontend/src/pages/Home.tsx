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
    <div style={{ maxWidth: 600, margin: "40px auto", padding: "0 16px" }}>
      <h1>Robo-CFO</h1>
      <Disclaimer />
      <form onSubmit={handleSubmit}>
        <label style={{ display: "block", marginBottom: 8 }}>
          Anos de simulação
          <input
            type="number"
            min={5}
            max={50}
            value={years}
            onChange={e => setYears(Number(e.target.value))}
            style={{ display: "block", marginTop: 4, padding: "6px 10px", fontSize: 16, width: 120 }}
          />
        </label>
        <button type="submit" style={{ marginTop: 16, padding: "8px 24px", fontSize: 16, cursor: "pointer" }}>
          Simular
        </button>
      </form>
    </div>
  );
}
