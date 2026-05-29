export default function Disclaimer() {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
      <span className="mt-0.5 shrink-0 text-base">⚠️</span>
      <p>
        <span className="font-semibold">Aviso legal:</span> Este é um simulador educacional.
        Não constitui assessoria financeira. Os valores são ilustrativos.{" "}
        <span className="opacity-75">Consulte um profissional habilitado antes de tomar decisões financeiras.</span>
      </p>
    </div>
  );
}
