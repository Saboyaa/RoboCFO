import { useState } from "react";
import { useExplain } from "../api/client";
import type { Explanation } from "../api/types";

interface Props {
  explanation: Explanation;
  templateText: string;
}

export default function ExplanationCard({ explanation, templateText }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { mutate, data, isPending, isError } = useExplain();

  function handleExplain() {
    setExpanded(true);
    mutate({ explanation, use_llm: true });
  }

  return (
    <div style={{ border: "1px solid #e2e8f0", borderRadius: 6, padding: 16, marginBottom: 16 }}>
      <p style={{ margin: "0 0 12px 0" }}>{templateText}</p>
      {!expanded && (
        <button onClick={handleExplain} style={{ cursor: "pointer" }}>
          Explicar mais
        </button>
      )}
      {isPending && <p style={{ color: "#64748b" }}>Carregando explicação…</p>}
      {isError && <p style={{ color: "#dc2626" }}>Serviço indisponível</p>}
      {data && <p style={{ marginTop: 12, background: "#f8fafc", padding: 12, borderRadius: 4 }}>{data.text}</p>}
    </div>
  );
}
