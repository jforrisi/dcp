import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { TimeSeriesData } from '../services/api';

interface TimeSeriesChartProps {
  data: TimeSeriesData[];
}

const COLORS = [
  '#6366f1', // primary
  '#8b5cf6', // secondary
  '#10b981', // success
  '#ef4444', // danger
  '#f59e0b', // amber
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#14b8a6', // teal
];

export default function TimeSeriesChart({ data }: TimeSeriesChartProps) {
  const chartData = useMemo(() => {
    if (data.length === 0) return [];

    // Get all unique dates
    const allDates = new Set<string>();
    data.forEach((series) => {
      series.precios.forEach((price) => {
        allDates.add(price.fecha);
      });
    });

    const sortedDates = Array.from(allDates).sort();

    // Build chart data structure
    return sortedDates.map((date) => {
      const dataPoint: Record<string, string | number> = {
        fecha: date,
      };

      data.forEach((series) => {
        const price = series.precios.find((p) => p.fecha === date);
        dataPoint[series.producto.nombre] = price ? price.valor : null;
      });

      return dataPoint;
    });
  }, [data]);

  const formatDate = (dateStr: string) => {
    try {
      return format(parseISO(dateStr), 'dd/MM/yyyy');
    } catch {
      return dateStr;
    }
  };

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
        <p className="text-gray-500">No hay datos para mostrar</p>
      </div>
    );
  }

  return (
    <div className="w-full h-96">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="fecha"
            tickFormatter={formatDate}
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis stroke="#6b7280" style={{ fontSize: '12px' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '12px',
            }}
            labelFormatter={(value) => formatDate(value as string)}
            formatter={(value: number) => [
              value !== null ? value.toFixed(2) : 'N/A',
              'Valor',
            ]}
          />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />
          {data.map((series, index) => (
            <Line
              key={series.producto.id}
              type="monotone"
              dataKey={series.producto.nombre}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
