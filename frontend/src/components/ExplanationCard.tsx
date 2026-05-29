import { useState } from "react";
import { useExplain } from "../api/client";
import type { Explanation } from "../api/types";

interface Props {
  explanation: Explanation;
  templateText: string;
}

function SparkleIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
    </svg>
  );
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
      <p className="text-sm leading-relaxed text-slate-300">{templateText}</p>

      {!expanded && (
        <button
          onClick={handleExplain}
          className="mt-4 flex items-center gap-2 rounded-lg border border-blue-500/40 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-400 transition-colors hover:bg-blue-500/20"
        >
          <SparkleIcon /> Elaborar com IA
        </button>
      )}

      {isPending && (
        <div className="mt-4 flex items-center gap-2 text-sm text-slate-400">
          <Spinner /> Gerando explicação…
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
