import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Variation } from '../services/api';

interface VariationBarChartProps {
  data: Variation[];
}

export default function VariationBarChart({ data }: VariationBarChartProps) {
  const chartData = data.map((item) => ({
    nombre: item.nombre.length > 20 ? item.nombre.substring(0, 20) + '...' : item.nombre,
    nombreCompleto: item.nombre,
    variacion: Number(item.variacion_percent.toFixed(2)),
  }));

  const getColor = (value: number) => {
    if (value >= 0) return '#10b981'; // success (green)
    return '#ef4444'; // danger (red)
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
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
          layout="vertical"
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            type="number"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            tickFormatter={(value) => `${value}%`}
          />
          <YAxis
            dataKey="nombre"
            type="category"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            width={200}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '12px',
            }}
            formatter={(value: number) => [`${value.toFixed(2)}%`, 'Variación']}
            labelFormatter={(value, payload) => {
              if (payload && payload[0]) {
                return payload[0].payload.nombreCompleto;
              }
              return value;
            }}
          />
          <Bar dataKey="variacion" radius={[0, 8, 8, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.variacion)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
