import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { formatDate } from '@/utils/format';

interface DrawdownData {
  date: string;
  drawdown: number;
}

interface DrawdownChartProps {
  data: DrawdownData[];
  maxDrawdown?: number;
  height?: number;
}

export function DrawdownChart({ data, maxDrawdown = 20, height = 200 }: DrawdownChartProps) {
  const { t } = useTranslation();

  const chartData = useMemo(() => {
    return data.map((d) => ({
      ...d,
      displayDate: formatDate(d.date),
      drawdown: -Math.abs(d.drawdown),
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="displayDate"
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}%`}
          domain={[-maxDrawdown, 0]}
        />
        <Tooltip
          formatter={(value) => [`${(value as number).toFixed(2)}%`, t('risk.drawdown')]}
          labelFormatter={(label) => `${t('risk.date')}: ${label}`}
          contentStyle={{
            backgroundColor: 'rgba(255,255,255,0.95)',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
        <ReferenceLine y={-maxDrawdown * 0.5} stroke="#eab308" strokeDasharray="5 5" />
        <ReferenceLine y={-maxDrawdown * 0.8} stroke="#ef4444" strokeDasharray="5 5" />
        <Area
          type="monotone"
          dataKey="drawdown"
          stroke="#ef4444"
          fill="url(#drawdownGradient)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
