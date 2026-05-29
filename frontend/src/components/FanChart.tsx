import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { YearPercentiles } from "../api/types";

interface FanChartProps {
  data: YearPercentiles[];
  height?: number;
}

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export default function FanChart({ data, height = 320 }: FanChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 24, left: 16, bottom: 8 }}>
        <XAxis dataKey="year" />
        <YAxis tickFormatter={(v: number) => brl.format(v)} width={110} />
        <Tooltip formatter={(v: number) => brl.format(v)} />
        <Legend />
        <Line type="monotone" dataKey="p10" name="P10" stroke="#ef4444" dot={false} />
        <Line type="monotone" dataKey="p50" name="P50" stroke="#22c55e" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="p90" name="P90" stroke="#3b82f6" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
