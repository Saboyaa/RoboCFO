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
    <div className="rounded-xl border border-slate-700/60 bg-slate-800/50 p-5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-xl">🤖</span>
        <p className="text-sm leading-relaxed text-slate-300">{templateText}</p>
      </div>

      {!expanded && (
        <button
          onClick={handleExplain}
          className="mt-4 flex items-center gap-2 rounded-lg border border-blue-500/40 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-400 transition-colors hover:bg-blue-500/20"
        >
          <span>✨</span> Explicar mais com IA
        </button>
      )}

      {isPending && (
        <div className="mt-4 flex items-center gap-2 text-sm text-slate-400">
          <span className="animate-spin">⏳</span> Gerando explicação…
        </div>
      )}

      {isError && (
        <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          Serviço indisponível. Verifique a configuração do LLM_PROVIDER.
        </div>
      )}

      {data && (
        <div className="mt-4 rounded-lg border border-blue-500/20 bg-blue-500/5 px-4 py-3 text-sm leading-relaxed text-slate-300">
          {data.text}
        </div>
      )}
    </div>
  );
}
