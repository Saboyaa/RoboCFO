import type { StrategyOutcome } from "../api/types";

interface Props {
  ranked: readonly StrategyOutcome[];
}

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

const RANK_COLORS = ['text-emerald-400', 'text-blue-400', 'text-slate-400', 'text-slate-500', 'text-slate-600'];
const RANK_BADGES = ['🥇', '🥈', '🥉', '4º', '5º'];

export default function StrategyComparison({ ranked }: Props) {
  const best = ranked[0]?.result.terminal_p50 ?? 1;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-700/60 bg-slate-800/50">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-700/60 bg-slate-800">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">#</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">Estratégia</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-400">Patrimônio mediano</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-400 hidden sm:table-cell">Prob. sucesso</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/40">
          {ranked.map((outcome, i) => {
            const pct = Math.round((outcome.result.terminal_p50 / best) * 100);
            return (
              <tr
                key={outcome.strategy.id}
                className={`transition-colors ${i === 0 ? 'bg-emerald-500/5' : 'hover:bg-slate-700/30'}`}
              >
                <td className={`px-4 py-4 text-lg ${RANK_COLORS[i] ?? 'text-slate-500'}`}>
                  {RANK_BADGES[i] ?? `${i + 1}º`}
                </td>
                <td className="px-4 py-4">
                  <div className={`font-medium ${i === 0 ? 'text-emerald-300' : 'text-slate-200'}`}>
                    {outcome.strategy.name}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{outcome.strategy.description}</div>
                  <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-slate-700">
                    <div
                      className={`h-full rounded-full ${i === 0 ? 'bg-emerald-500' : 'bg-slate-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </td>
                <td className={`px-4 py-4 text-right font-semibold tabular-nums ${i === 0 ? 'text-emerald-400' : 'text-slate-300'}`}>
                  {brl.format(outcome.result.terminal_p50)}
                </td>
                <td className="px-4 py-4 text-right text-sm text-slate-400 hidden sm:table-cell">
                  {(outcome.result.success_probability * 100).toFixed(0)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
