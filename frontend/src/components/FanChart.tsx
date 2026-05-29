import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { YearPercentiles } from "../api/types";

interface FanChartProps {
  data: readonly YearPercentiles[];
  height?: number;
}

const brl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

const tooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#f1f5f9',
};

export default function FanChart({ data, height = 340 }: FanChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data as YearPercentiles[]} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <defs>
          <linearGradient id="p90grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="p50grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="p10grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="year"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          axisLine={{ stroke: '#334155' }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => brl.format(v)}
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={120}
        />
        <Tooltip
          formatter={(v: number) => [brl.format(v)]}
          contentStyle={tooltipStyle}
          labelStyle={{ color: '#94a3b8', marginBottom: 4 }}
        />
        <Legend
          wrapperStyle={{ paddingTop: 16, fontSize: 13, color: '#94a3b8' }}
        />
        <Area type="monotone" dataKey="p90" name="Otimista (P90)" stroke="#3b82f6" strokeWidth={1.5} fill="url(#p90grad)" dot={false} />
        <Area type="monotone" dataKey="p50" name="Mediano (P50)" stroke="#10b981" strokeWidth={2.5} fill="url(#p50grad)" dot={false} />
        <Area type="monotone" dataKey="p10" name="Pessimista (P10)" stroke="#f43f5e" strokeWidth={1.5} fill="url(#p10grad)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
