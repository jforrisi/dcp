// Página de Inflación en dólares
function InflacionDolaresPage() {
    const [products, setProducts] = React.useState([]);
    const [selectedProducts, setSelectedProducts] = React.useState([]);
    const [fechaDesde, setFechaDesde] = React.useState(() => {
        const date = new Date();
        date.setMonth(date.getMonth() - 12); // Últimos 12 meses
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        return `${year}-${month}-01`;
    });
    const [fechaHasta, setFechaHasta] = React.useState(() => {
        const date = new Date();
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const lastDay = new Date(year, date.getMonth() + 1, 0).getDate();
        return `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
    });
    const [inflacionData, setInflacionData] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const [fullscreen, setFullscreen] = React.useState(false);
    const [error, setError] = React.useState(null);

    // Cargar productos disponibles
    React.useEffect(() => {
        fetch(`${API_BASE}/inflacion-dolares/products`)
            .then(res => {
                if (!res.ok) {
                    throw new Error(`Error ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                // Asegurar que data sea un array
                if (Array.isArray(data)) {
                    setProducts(data);
                } else if (data.error) {
                    console.error('Error del servidor:', data.error);
                    setError(data.error);
                    setProducts([]);
                } else {
                    setProducts([]);
                }
            })
            .catch(err => {
                console.error('Error loading products:', err);
                setError(err.message || 'Error al cargar los productos');
                setProducts([]);
            });
    }, []);

    const handleApplyFilters = async () => {
        if (selectedProducts.length === 0) {
            alert('Por favor selecciona al menos un país');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams();
            selectedProducts.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);

            const response = await fetch(`${API_BASE}/inflacion-dolares?${params}`);
            
            if (!response.ok) {
                let errorMessage = `Error ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // Ignorar
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            setInflacionData(data);
        } catch (error) {
            console.error('Error loading inflacion dolares:', error);
            setError(error.message || 'Error al cargar los datos');
            setInflacionData([]);
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadExcel = async () => {
        if (selectedProducts.length === 0) {
            alert('Por favor selecciona al menos un país');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }

        try {
            const params = new URLSearchParams();
            selectedProducts.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);

            const response = await fetch(`${API_BASE}/inflacion-dolares/export?${params}`);
            if (!response.ok) {
                throw new Error('Error al generar el archivo Excel');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'inflacion_dolares.xlsx';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error downloading Excel:', error);
            alert('Error al descargar el archivo Excel');
        }
    };

    // Tabla de resumen
    const SummaryTable = ({ data }) => {
        const [sortConfig, setSortConfig] = React.useState({ key: null, direction: 'asc' });

        const formatIntervalo = (fechaInicialStr, fechaFinalStr) => {
            if (!fechaInicialStr || !fechaFinalStr) return 'N/A';
            try {
                const fechaInicial = fechaInicialStr.includes('T') ? new Date(fechaInicialStr) : new Date(fechaInicialStr + 'T00:00:00');
                const fechaFinal = fechaFinalStr.includes('T') ? new Date(fechaFinalStr) : new Date(fechaFinalStr + 'T00:00:00');
                
                const mesInicial = String(fechaInicial.getMonth() + 1).padStart(2, '0');
                const añoInicial = String(fechaInicial.getFullYear()).slice(-2);
                const mesFinal = String(fechaFinal.getMonth() + 1).padStart(2, '0');
                const añoFinal = String(fechaFinal.getFullYear()).slice(-2);
                
                return `${mesInicial}/${añoInicial} - ${mesFinal}/${añoFinal}`;
            } catch (e) {
                return 'N/A';
            }
        };

        const tableData = data
            .filter(item => item.summary && item.summary.indice_inicial !== null)
            .map(item => ({
                pais: item.pais || item.product_name,
                intervalo: formatIntervalo(item.summary.fecha_inicial, item.summary.fecha_final),
                indiceInicial: item.summary.indice_inicial,
                indiceFinal: item.summary.indice_final,
                variacionTC: item.summary.variacion_tc || 0.0,
                variacionInflacion: item.summary.variacion_ipc || 0.0,
                inflacionDolares: item.summary.variacion_indice || 0.0
            }));

        const handleSort = (key) => {
            let direction = 'asc';
            if (sortConfig.key === key && sortConfig.direction === 'asc') {
                direction = 'desc';
            }
            setSortConfig({ key, direction });
        };

        const sortedData = [...tableData].sort((a, b) => {
            if (sortConfig.key === null) return 0;
            let aVal = a[sortConfig.key];
            let bVal = b[sortConfig.key];
            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }
            if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });

        const SortIcon = ({ columnKey }) => {
            if (sortConfig.key !== columnKey) {
                return <span className="text-gray-400 ml-1 text-xs">↕</span>;
            }
            return sortConfig.direction === 'asc' 
                ? <span className="text-indigo-600 ml-1 text-xs">↑</span>
                : <span className="text-indigo-600 ml-1 text-xs">↓</span>;
        };

        if (tableData.length === 0) {
            return (
                <div className="text-center py-4 text-gray-500">
                    <p>No hay datos de resumen disponibles para mostrar.</p>
                </div>
            );
        }

        return (
            <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Resumen de Inflación en Dólares</h3>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th 
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('pais')}
                                >
                                    País <SortIcon columnKey="pais" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('intervalo')}
                                >
                                    Intervalo <SortIcon columnKey="intervalo" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('indiceInicial')}
                                >
                                    Índice Inicio <SortIcon columnKey="indiceInicial" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('indiceFinal')}
                                >
                                    Índice Fin <SortIcon columnKey="indiceFinal" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('variacionTC')}
                                >
                                    Var. TC (%) <SortIcon columnKey="variacionTC" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('variacionInflacion')}
                                >
                                    Var. Inflación (%) <SortIcon columnKey="variacionInflacion" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('inflacionDolares')}
                                >
                                    Inflación en Dólares (%) <SortIcon columnKey="inflacionDolares" />
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {sortedData.map((row, idx) => (
                                <tr key={idx} className="hover:bg-gray-50">
                                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                                        {row.pais}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                                        {row.intervalo}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                                        {row.indiceInicial.toFixed(2)}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                                        {row.indiceFinal.toFixed(2)}
                                    </td>
                                    <td className={`px-4 py-3 whitespace-nowrap text-sm text-right ${
                                        row.variacionTC >= 0 ? 'text-green-600' : 'text-red-600'
                                    }`}>
                                        {row.variacionTC >= 0 ? '+' : ''}{row.variacionTC.toFixed(2)}%
                                    </td>
                                    <td className={`px-4 py-3 whitespace-nowrap text-sm text-right ${
                                        row.variacionInflacion >= 0 ? 'text-green-600' : 'text-red-600'
                                    }`}>
                                        {row.variacionInflacion >= 0 ? '+' : ''}{row.variacionInflacion.toFixed(2)}%
                                    </td>
                                    <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-semibold ${
                                        row.inflacionDolares >= 0 ? 'text-green-600' : 'text-red-600'
                                    }`}>
                                        {row.inflacionDolares >= 0 ? '+' : ''}{row.inflacionDolares.toFixed(2)}%
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    return (
        <div className="min-h-screen bg-gray-50 p-2">
            <div className="w-full">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Inflación en dólares</h1>
                </div>

                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {/* Panel de controles a la izquierda */}
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Selecciona país
                                        </label>
                                        <VariableSelector
                                            selectedProducts={selectedProducts}
                                            onSelectionChange={setSelectedProducts}
                                            products={products.map(p => ({...p, displayName: p.pais || p.nombre}))}
                                            allProducts={products.map(p => ({...p, displayName: p.pais || p.nombre}))}
                                        />
                                    </div>

                                    <MonthYearPicker
                                        fechaDesde={fechaDesde}
                                        fechaHasta={fechaHasta}
                                        onFechaDesdeChange={setFechaDesde}
                                        onFechaHastaChange={setFechaHasta}
                                    />

                                    <div className="flex flex-col gap-2">
                                        <button
                                            onClick={handleApplyFilters}
                                            disabled={loading}
                                            className="btn-primary w-full"
                                        >
                                            {loading ? 'Cargando...' : 'Aplicar Filtros'}
                                        </button>
                                        <button
                                            onClick={handleDownloadExcel}
                                            disabled={loading || inflacionData.length === 0}
                                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed w-full"
                                        >
                                            Descargar Excel
                                        </button>
                                        <button
                                            onClick={() => {
                                                setSelectedProducts([]);
                                                setInflacionData([]);
                                                setError(null);
                                            }}
                                            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                                        >
                                            Limpiar
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Área principal */}
                    <div className={fullscreen ? 'col-span-1' : 'lg:col-span-3'}>
                        {error && (
                            <div className="card mb-6 bg-red-50 border border-red-200">
                                <p className="text-red-800">
                                    <strong>Error al cargar los datos:</strong><br />
                                    {error}
                                </p>
                            </div>
                        )}

                        {loading ? (
                            <div className="card">
                                <div className="flex items-center justify-center py-12">
                                    <div className="text-center">
                                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
                                        <p className="text-gray-600">Cargando datos...</p>
                                    </div>
                                </div>
                            </div>
                        ) : inflacionData.length > 0 ? (
                            <>
                                <div className={`card mb-6 ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                                    <div className="flex justify-between items-center mb-4">
                                        <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>Gráfico de Inflación en Dólares</h2>
                                        <div className="flex gap-2">
                                            {fullscreen && (
                                                <button 
                                                    onClick={() => setFullscreen(false)} 
                                                    className="px-3 py-1.5 rounded-lg font-medium transition-all bg-gray-200 text-gray-700 hover:bg-gray-300 text-sm"
                                                    title="Salir de pantalla completa"
                                                >
                                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                    </svg>
                                                </button>
                                            )}
                                            {!fullscreen && (
                                                <button 
                                                    onClick={() => setFullscreen(true)} 
                                                    className="px-3 py-1.5 rounded-lg font-medium transition-all bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm"
                                                    title="Pantalla completa"
                                                >
                                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                                                    </svg>
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                    <div style={{ height: fullscreen ? 'calc(100vh - 120px)' : '400px' }}>
                                        <Base100Chart data={inflacionData} fullscreen={fullscreen} />
                                    </div>
                                </div>

                                {!fullscreen && <SummaryTable data={inflacionData} />}
                            </>
                        ) : (
                            <div className="card">
                                <div className="text-center py-12 text-gray-500">
                                    <p>Selecciona países y un rango de fechas, luego haz clic en "Aplicar Filtros" para visualizar la inflación en dólares.</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
