import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, subMonths } from 'date-fns';
import DateRangePicker from '../components/DateRangePicker';
import VariationBarChart from '../components/VariationBarChart';
import { apiService } from '../services/api';

export default function VariationComparisonPage() {
  const [fechaDesde, setFechaDesde] = useState(
    format(subMonths(new Date(), 6), 'yyyy-MM-dd')
  );
  const [fechaHasta, setFechaHasta] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [orderBy, setOrderBy] = useState<'asc' | 'desc'>('desc');
  const [applyFilters, setApplyFilters] = useState(false);

  const { data: variations = [], isLoading } = useQuery({
    queryKey: ['variations', fechaDesde, fechaHasta, orderBy, applyFilters],
    queryFn: () => apiService.getVariations(fechaDesde, fechaHasta, orderBy),
    enabled: applyFilters && fechaDesde && fechaHasta,
  });

  const handleApplyFilters = () => {
    if (!fechaDesde || !fechaHasta) {
      alert('Por favor selecciona un rango de fechas');
      return;
    }
    setApplyFilters(true);
  };

  const formatVariation = (variation: number) => {
    const sign = variation >= 0 ? '+' : '';
    return `${sign}${variation.toFixed(2)}%`;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Variación de Precios</h1>
          <p className="text-gray-600">Compara la variación de precios entre productos</p>
        </div>

        <div className="card mb-6">
          <div className="space-y-6">
            <DateRangePicker
              fechaDesde={fechaDesde}
              fechaHasta={fechaHasta}
              onFechaDesdeChange={setFechaDesde}
              onFechaHastaChange={setFechaHasta}
            />

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <label className="text-sm font-medium text-gray-700">Ordenar por:</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setOrderBy('desc')}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      orderBy === 'desc'
                        ? 'bg-primary text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Mayor a Menor
                  </button>
                  <button
                    onClick={() => setOrderBy('asc')}
                    className={`px-4 py-2 rounded-lg font-medium transition-all ${
                      orderBy === 'asc'
                        ? 'bg-primary text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Menor a Mayor
                  </button>
                </div>
              </div>

              <button onClick={handleApplyFilters} className="btn-primary">
                Aplicar Filtros
              </button>
            </div>
          </div>
        </div>

        {applyFilters && (
          <>
            {isLoading ? (
              <div className="card">
                <div className="flex items-center justify-center h-96">
                  <div className="text-gray-500">Cargando datos...</div>
                </div>
              </div>
            ) : variations.length > 0 ? (
              <>
                <div className="card mb-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">
                    Gráfico de Variaciones
                  </h2>
                  <VariationBarChart data={variations} />
                </div>

                <div className="card">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">
                    Lista de Productos
                  </h2>
                  <div className="space-y-3">
                    {variations.map((variation) => (
                      <div
                        key={variation.id}
                        className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900">{variation.nombre}</h3>
                          {variation.unidad && (
                            <p className="text-sm text-gray-500">{variation.unidad}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="text-right">
                            <p className="text-sm text-gray-600">Precio Inicial</p>
                            <p className="font-medium text-gray-900">
                              {variation.precio_inicial.toFixed(2)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm text-gray-600">Precio Final</p>
                            <p className="font-medium text-gray-900">
                              {variation.precio_final.toFixed(2)}
                            </p>
                          </div>
                          <div className="text-right min-w-[100px]">
                            <p className="text-sm text-gray-600">Variación</p>
                            <p
                              className={`font-bold text-lg ${
                                variation.variacion_percent >= 0
                                  ? 'text-success'
                                  : 'text-danger'
                              }`}
                            >
                              {formatVariation(variation.variacion_percent)}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="card">
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <p className="text-gray-500 mb-2">No se encontraron datos</p>
                    <p className="text-sm text-gray-400">
                      Intenta ajustar el rango de fechas
                    </p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {!applyFilters && (
          <div className="card">
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <p className="text-gray-500 mb-2">Selecciona un rango de fechas</p>
                <p className="text-sm text-gray-400">
                  Luego haz clic en "Aplicar Filtros" para visualizar las variaciones
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
