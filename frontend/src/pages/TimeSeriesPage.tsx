import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, subMonths } from 'date-fns';
import ProductSelector from '../components/ProductSelector';
import DateRangePicker from '../components/DateRangePicker';
import TimeSeriesChart from '../components/TimeSeriesChart';
import StatsCard from '../components/StatsCard';
import { apiService } from '../services/api';

export default function TimeSeriesPage() {
  const [selectedProducts, setSelectedProducts] = useState<number[]>([]);
  const [fechaDesde, setFechaDesde] = useState(
    format(subMonths(new Date(), 6), 'yyyy-MM-dd')
  );
  const [fechaHasta, setFechaHasta] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [applyFilters, setApplyFilters] = useState(false);

  const { data: timeSeriesData = [], isLoading: isLoadingData } = useQuery({
    queryKey: ['timeSeries', selectedProducts, fechaDesde, fechaHasta, applyFilters],
    queryFn: () =>
      apiService.getMultipleProductsPrices(selectedProducts, fechaDesde, fechaHasta),
    enabled: applyFilters && selectedProducts.length > 0 && fechaDesde && fechaHasta,
  });

  // Get stats for first selected product
  const { data: stats, isLoading: isLoadingStats } = useQuery({
    queryKey: ['stats', selectedProducts[0], fechaDesde, fechaHasta, applyFilters],
    queryFn: () =>
      apiService.getProductStats(selectedProducts[0], fechaDesde, fechaHasta),
    enabled: applyFilters && selectedProducts.length > 0 && fechaDesde && fechaHasta,
  });

  const handleApplyFilters = () => {
    if (selectedProducts.length === 0) {
      alert('Por favor selecciona al menos un producto');
      return;
    }
    if (!fechaDesde || !fechaHasta) {
      alert('Por favor selecciona un rango de fechas');
      return;
    }
    setApplyFilters(true);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Series de Tiempo</h1>
          <p className="text-gray-600">Visualiza la evolución de precios a lo largo del tiempo</p>
        </div>

        <div className="card mb-6">
          <div className="space-y-6">
            <ProductSelector
              selectedProducts={selectedProducts}
              onSelectionChange={setSelectedProducts}
            />

            <DateRangePicker
              fechaDesde={fechaDesde}
              fechaHasta={fechaHasta}
              onFechaDesdeChange={setFechaDesde}
              onFechaHastaChange={setFechaHasta}
            />

            <div className="flex justify-end">
              <button onClick={handleApplyFilters} className="btn-primary">
                Aplicar Filtros
              </button>
            </div>
          </div>
        </div>

        {applyFilters && (
          <>
            {isLoadingData ? (
              <div className="card">
                <div className="flex items-center justify-center h-96">
                  <div className="text-gray-500">Cargando datos...</div>
                </div>
              </div>
            ) : timeSeriesData.length > 0 ? (
              <>
                <div className="card mb-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">Gráfico de Precios</h2>
                  <TimeSeriesChart data={timeSeriesData} />
                </div>

                <div className="mb-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">Estadísticas</h2>
                  <StatsCard stats={stats} isLoading={isLoadingStats} />
                </div>
              </>
            ) : (
              <div className="card">
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <p className="text-gray-500 mb-2">No se encontraron datos</p>
                    <p className="text-sm text-gray-400">
                      Intenta ajustar los filtros o seleccionar otros productos
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
                <p className="text-gray-500 mb-2">Selecciona productos y fechas</p>
                <p className="text-sm text-gray-400">
                  Luego haz clic en "Aplicar Filtros" para visualizar los datos
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
