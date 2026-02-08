// Página de Cotizaciones de monedas
function CotizacionesPage() {
    const [products, setProducts] = React.useState([]);
    const [selectedProducts, setSelectedProducts] = React.useState([]);
    const [fechaDesde, setFechaDesde] = React.useState(() => {
        const date = new Date();
        date.setDate(date.getDate() - 30); // Últimos 30 días
        return date.toISOString().split('T')[0];
    });
    const [fechaHasta, setFechaHasta] = React.useState(() => {
        return new Date().toISOString().split('T')[0];
    });
    const [cotizacionesData, setCotizacionesData] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const [fullscreen, setFullscreen] = React.useState(false);
    const [error, setError] = React.useState(null);
    const [viewMode, setViewMode] = React.useState('nominal'); // 'nominal' o 'base100'
    const [rawData, setRawData] = React.useState([]); // Datos originales sin normalizar

    // Función para extraer nombre del país del nombre del producto
    // Usa id_variable de la base de datos: 20 = oficial (no se muestra), 21 = informal
    const extractCountryName = (productName, productPais, idVariable) => {
        // Obtener nombre base del país
        let countryName = productPais;
        
        // Limpiar el nombre del país: extraer solo el nombre base (antes de paréntesis)
        if (countryName) {
            // Si tiene paréntesis, extraer solo el nombre base
            const match = countryName.match(/^([^(]+)/);
            if (match) {
                countryName = match[1].trim();
            }
        }
        
        // Si no hay pais, intentar extraerlo del nombre
        if (!countryName) {
            // Mapeo de códigos de moneda a países
            const currencyToCountry = {
                'ARS': 'Argentina',
                'BRL': 'Brasil',
                'UYU': 'Uruguay',
                'CLP': 'Chile',
                'COP': 'Colombia',
                'PEN': 'Perú',
                'MXN': 'México',
                'PYG': 'Paraguay',
                'BOB': 'Bolivia',
                'VES': 'Venezuela',
                'AUD': 'Australia',
                'ZAR': 'Sudáfrica',
                'NZD': 'Nueva Zelanda'
            };
            
            // Buscar código de moneda en el nombre
            for (const [currency, country] of Object.entries(currencyToCountry)) {
                if (productName.includes(`/${currency}`) || productName.includes(` ${currency}`) || productName.includes(`(${currency}`)) {
                    countryName = country;
                    break;
                }
            }
            
            // Si no se encuentra, usar el nombre completo
            if (!countryName) {
                countryName = productName;
            }
        }
        
        // Si id_variable = 21, agregar "(Informal)"
        // id_variable = 20 es oficial, no se agrega nada (se sobreentiende)
        if (idVariable === 21) {
            return `${countryName} (Informal)`;
        }
        
        // Para id_variable = 20 o sin id_variable, solo devolver el país
        return countryName;
    };

    const loadCotizaciones = async (productIds, desde, hasta) => {
        if (productIds.length === 0) {
            setCotizacionesData([]);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams();
            productIds.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', desde);
            params.append('fecha_hasta', hasta);

            const response = await fetch(`${API_BASE}/cotizaciones?${params}`);
            
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
            setRawData(data); // Guardar datos originales
        } catch (error) {
            console.error('Error loading cotizaciones:', error);
            setError(error.message || 'Error al cargar los datos');
            setCotizacionesData([]);
        } finally {
            setLoading(false);
        }
    };

    // Cargar productos disponibles (sin cargar datos automáticamente)
    React.useEffect(() => {
        fetch(`${API_BASE}/cotizaciones/products`)
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
                console.error('Error loading cotizaciones products:', err);
                setError(err.message || 'Error al cargar los productos');
                setProducts([]);
            });
    }, []);

    const handleApplyFilters = () => {
        if (selectedProducts.length === 0) {
            alert('Por favor selecciona al menos un país');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }
        loadCotizaciones(selectedProducts, fechaDesde, fechaHasta);
    };

    // Actualizar datos cuando cambian los datos originales (sin normalizar aquí, CombinateChart lo hace)
    React.useEffect(() => {
        setCotizacionesData(rawData);
    }, [rawData]);

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

            const response = await fetch(`${API_BASE}/cotizaciones/export?${params}`);
            if (!response.ok) {
                throw new Error('Error al generar el archivo Excel');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'cotizaciones_latam.xlsx';
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

        const tableData = data
            .filter(item => item.summary && item.summary.precio_inicial !== null)
            .map(item => ({
                nombre: extractCountryName(item.product_name, item.pais, item.id_variable),
                intervalo: item.summary.fecha_inicial && item.summary.fecha_final
                    ? (() => {
                        const fechaIni = new Date(item.summary.fecha_inicial + 'T00:00:00');
                        const fechaFin = new Date(item.summary.fecha_final + 'T00:00:00');
                        const diaIni = String(fechaIni.getDate()).padStart(2, '0');
                        const mesIni = String(fechaIni.getMonth() + 1).padStart(2, '0');
                        const añoIni = String(fechaIni.getFullYear()).slice(-2);
                        const diaFin = String(fechaFin.getDate()).padStart(2, '0');
                        const mesFin = String(fechaFin.getMonth() + 1).padStart(2, '0');
                        const añoFin = String(fechaFin.getFullYear()).slice(-2);
                        return `${diaIni}-${mesIni}-${añoIni} - ${diaFin}-${mesFin}-${añoFin}`;
                    })()
                    : 'N/A',
                precioInicial: item.summary.precio_inicial,
                precioFinal: item.summary.precio_final,
                variacion: item.summary.variacion || 0.0
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

        const getVariacionColor = (valor) => {
            if (valor === 0 || Math.abs(valor) < 0.01) return 'text-gray-600';
            return valor >= 0 ? 'text-green-600' : 'text-red-600';
        };

        if (tableData.length === 0) {
            return (
                <div className="text-center py-8 text-gray-500">
                    <p>No hay datos de resumen disponibles para mostrar.</p>
                </div>
            );
        }

        return (
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                    <thead className="bg-gray-50">
                        <tr>
                            <th 
                                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('nombre')}
                            >
                                <div className="flex items-center">
                                    País/Cotización
                                    <SortIcon columnKey="nombre" />
                                </div>
                            </th>
                            <th 
                                className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('intervalo')}
                            >
                                <div className="flex items-center justify-center">
                                    Intervalo
                                    <SortIcon columnKey="intervalo" />
                                </div>
                            </th>
                            <th 
                                className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('precioInicial')}
                            >
                                <div className="flex items-center justify-end">
                                    Cotización Inicial
                                    <SortIcon columnKey="precioInicial" />
                                </div>
                            </th>
                            <th 
                                className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('precioFinal')}
                            >
                                <div className="flex items-center justify-end">
                                    Cotización Final
                                    <SortIcon columnKey="precioFinal" />
                                </div>
                            </th>
                            <th 
                                className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('variacion')}
                            >
                                <div className="flex items-center justify-end">
                                    Variación (%)
                                    <SortIcon columnKey="variacion" />
                                </div>
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.map((row, index) => (
                            <tr key={index} className="hover:bg-gray-50">
                                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                                    {row.nombre}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-center">
                                    {row.intervalo}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
                                    {row.precioInicial.toFixed(4)}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
                                    {row.precioFinal.toFixed(4)}
                                </td>
                                <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${getVariacionColor(row.variacion)}`}>
                                    {row.variacion >= 0 ? '+' : ''}{row.variacion.toFixed(2)}%
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    return (
        <div className="min-h-screen bg-gray-50 p-2">
            <div className="w-full">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Cotizaciones de monedas</h1>
                </div>

                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {/* Panel de controles */}
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
                                            products={Array.isArray(products) ? products.map(p => ({...p, displayName: extractCountryName(p.nombre, p.pais, p.id_variable)})) : []}
                                            allProducts={Array.isArray(products) ? products.map(p => ({...p, displayName: extractCountryName(p.nombre, p.pais, p.id_variable)})) : []}
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Visualización
                                        </label>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setViewMode('nominal')}
                                                className={`flex-1 px-3 py-2 rounded-lg font-medium transition-all ${
                                                    viewMode === 'nominal'
                                                        ? 'bg-indigo-600 text-white'
                                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                }`}
                                            >
                                                Nominal
                                            </button>
                                            <button
                                                onClick={() => setViewMode('base100')}
                                                className={`flex-1 px-3 py-2 rounded-lg font-medium transition-all ${
                                                    viewMode === 'base100'
                                                        ? 'bg-indigo-600 text-white'
                                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                }`}
                                            >
                                                Base 100
                                            </button>
                                        </div>
                                    </div>

                                    <DateRangePicker
                                        fechaDesde={fechaDesde}
                                        fechaHasta={fechaHasta}
                                        onFechaDesdeChange={setFechaDesde}
                                        onFechaHastaChange={setFechaHasta}
                                    />

                                    <div className="flex flex-col gap-2">
                                        <button onClick={handleApplyFilters} className="btn-primary w-full">
                                            Aplicar Filtros
                                        </button>
                                        {cotizacionesData.length > 0 && (
                                            <button 
                                                onClick={handleDownloadExcel} 
                                                className="px-4 py-2 rounded-lg font-medium transition-all bg-green-600 text-white hover:bg-green-700 w-full flex items-center justify-center gap-2"
                                            >
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                </svg>
                                                Descargar Excel
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Área del gráfico */}
                    <div className={fullscreen ? 'col-span-1' : 'lg:col-span-3'}>
                        {loading ? (
                            <div className="card">
                                <div className="flex items-center justify-center" style={{ height: '600px' }}>
                                    <div className="text-gray-500">Cargando datos...</div>
                                </div>
                            </div>
                        ) : error ? (
                            <div className="card">
                                <div className="flex items-center justify-center h-96">
                                    <div className="text-center text-red-600">
                                        <p className="font-bold mb-2">Error al cargar los datos:</p>
                                        <p className="text-sm">{error}</p>
                                    </div>
                                </div>
                            </div>
                        ) : cotizacionesData.length > 0 ? (
                            <>
                                <div className={`card ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                                    <div className="flex justify-between items-center mb-4">
                                        <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>
                                            Cotizaciones diarias
                                        </h2>
                                        <div className="flex gap-2">
                                            {fullscreen && (
                                                <button 
                                                    onClick={() => setFullscreen(false)} 
                                                    className="px-3 py-1.5 rounded-lg font-medium transition-all bg-gray-200 text-gray-700 hover:bg-gray-300 text-sm"
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
                                                >
                                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                                                    </svg>
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                    <div style={{ height: fullscreen ? 'calc(100vh - 120px)' : '600px' }}>
                                        <CombinateChart 
                                            data={cotizacionesData} 
                                            fullscreen={fullscreen} 
                                            extractCountryName={extractCountryName}
                                            viewMode={viewMode}
                                            yAxisTitle={viewMode === 'base100' ? 'Índice (base 100)' : 'Cotización'}
                                        />
                                    </div>
                                    {/* Mostrar fuentes únicas al pie del gráfico */}
                                    {cotizacionesData.length > 0 && (() => {
                                        const fuentesUnicas = [...new Set(cotizacionesData.map(item => item.product_source).filter(f => f && f.trim() !== ''))];
                                        if (fuentesUnicas.length > 0) {
                                            return (
                                                <div className="mt-2 text-xs text-gray-500 text-center">
                                                    <span className="font-medium">Fuentes:</span> {fuentesUnicas.join(', ')}
                                                </div>
                                            );
                                        }
                                        return null;
                                    })()}
                                </div>
                                
                                {/* Tabla de resumen - usar rawData para mostrar valores originales */}
                                {!fullscreen && (
                                    <div className="card mt-6">
                                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Resumen de Cotizaciones</h3>
                                        <SummaryTable data={rawData.length > 0 ? rawData : cotizacionesData} />
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="card">
                                <div className="flex items-center justify-center" style={{ height: '600px' }}>
                                    <div className="text-center">
                                        <p className="text-gray-500 mb-2">Selecciona países y fechas</p>
                                        <p className="text-sm text-gray-400">
                                            Luego haz clic en "Aplicar Filtros" para visualizar las cotizaciones
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
