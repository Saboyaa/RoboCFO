import type { StrategyOutcome } from "../api/types";

interface Props {
  ranked: readonly StrategyOutcome[];
}

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export default function StrategyComparison({ ranked }: Props) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 16 }}>
      <thead>
        <tr style={{ background: "#f1f5f9" }}>
          <th style={{ padding: "8px 12px", textAlign: "left" }}>#</th>
          <th style={{ padding: "8px 12px", textAlign: "left" }}>Estratégia</th>
          <th style={{ padding: "8px 12px", textAlign: "right" }}>Patrimônio mediano</th>
        </tr>
      </thead>
      <tbody>
        {ranked.map((outcome, i) => (
          <tr
            key={outcome.strategy.id}
            style={{
              background: i === 0 ? "#f0fdf4" : "transparent",
              borderBottom: "1px solid #e2e8f0",
            }}
          >
            <td style={{ padding: "8px 12px" }}>{i + 1}</td>
            <td style={{ padding: "8px 12px" }}>
              <strong>{outcome.strategy.name}</strong>
              <div style={{ fontSize: 12, color: "#64748b" }}>{outcome.strategy.description}</div>
            </td>
            <td style={{ padding: "8px 12px", textAlign: "right" }}>
              {brl.format(outcome.result.terminal_p50)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
