import { Stats } from '../services/api';
import { format } from 'date-fns';

interface StatsCardProps {
  stats: Stats | null;
  isLoading?: boolean;
}

export default function StatsCard({ stats, isLoading }: StatsCardProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const formatValue = (value: number | null) => {
    if (value === null) return 'N/A';
    return value.toFixed(2);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      return format(new Date(dateStr), 'dd/MM/yyyy');
    } catch {
      return dateStr;
    }
  };

  const formatVariation = (variation: number | null) => {
    if (variation === null) return 'N/A';
    const sign = variation >= 0 ? '+' : '';
    const color = variation >= 0 ? 'text-success' : 'text-danger';
    return <span className={color}>{sign}{variation.toFixed(2)}%</span>;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Precio Actual</span>
          <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="text-2xl font-bold text-gray-900">{formatValue(stats.precio_actual)}</div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Variación Período</span>
          <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        </div>
        <div className="text-2xl font-bold">{formatVariation(stats.variacion_periodo)}</div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Precio Mínimo</span>
          <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div className="text-2xl font-bold text-gray-900">{formatValue(stats.precio_minimo)}</div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Precio Máximo</span>
          <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div className="text-2xl font-bold text-gray-900">{formatValue(stats.precio_maximo)}</div>
      </div>
    </div>
  );
}
