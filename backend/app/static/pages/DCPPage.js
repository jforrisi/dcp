// Página unificada de MacroData
function DCPPage() {
    // Estado para cambiar entre vistas
    const [viewMode, setViewMode] = React.useState('pepuc'); // 'pepuc' o 'corrientes'
    
    // Estados compartidos
    const [fechaDesde, setFechaDesde] = React.useState(() => {
        const date = new Date();
        date.setMonth(date.getMonth() - 6);
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
    const [fullscreen, setFullscreen] = React.useState(false);
    
    // Estados para PEPUC
    const [productsDCP, setProductsDCP] = React.useState([]);
    const [selectedProductsDCP, setSelectedProductsDCP] = React.useState([]);
    const [dcpData, setDcpData] = React.useState([]);
    const [loadingDCP, setLoadingDCP] = React.useState(false);
    const [applyFiltersDCP, setApplyFiltersDCP] = React.useState(false);
    const [errorDCP, setErrorDCP] = React.useState(null);
    
    // Estados para Precios Corrientes
    const [selectedProductsCorrientes, setSelectedProductsCorrientes] = React.useState([]);
    const [timeSeriesData, setTimeSeriesData] = React.useState([]);
    const [loadingCorrientes, setLoadingCorrientes] = React.useState(false);
    const [applyFiltersCorrientes, setApplyFiltersCorrientes] = React.useState(false);

    // Cargar productos para PEPUC (también usado en Precios Corrientes)
    React.useEffect(() => {
        fetch(`${API_BASE}/dcp/products`)
            .then(res => res.json())
            .then(data => setProductsDCP(data))
            .catch(err => console.error('Error loading DCP products:', err));
    }, []);

    // Handler para PEPUC
    const handleApplyFiltersDCP = async () => {
        if (selectedProductsDCP.length === 0) {
            alert('Por favor selecciona al menos un producto');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }

        setLoadingDCP(true);
        setApplyFiltersDCP(true);
        setErrorDCP(null);

        try {
            const params = new URLSearchParams();
            selectedProductsDCP.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);

            const response = await fetch(`${API_BASE}/dcp/indices?${params}`);
            
            if (!response.ok) {
                let errorMessage = `Error ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.message || errorData.description || errorData.error || errorMessage;
                } catch (e) {
                    try {
                        const errorText = await response.text();
                        if (errorText) {
                            errorMessage = errorText;
                        }
                    } catch (e2) {
                        // Si todo falla, usar el mensaje por defecto
                    }
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            setDcpData(data);
            setErrorDCP(null);
        } catch (error) {
            console.error('Error loading indices:', error);
            const errorMessage = error.message || 'Error al cargar los datos';
            setErrorDCP(errorMessage);
            setDcpData([]);
        } finally {
            setLoadingDCP(false);
        }
    };
    
    // Handler para Precios Corrientes
    const handleApplyFiltersCorrientes = async () => {
        if (selectedProductsCorrientes.length === 0) {
            alert('Por favor selecciona al menos un producto');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }

        setLoadingCorrientes(true);
        setApplyFiltersCorrientes(true);

        try {
            const params = new URLSearchParams();
            selectedProductsCorrientes.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);

            const response = await fetch(`${API_BASE}/products/prices?${params}`);
            const data = await response.json();
            setTimeSeriesData(data);
        } catch (error) {
            console.error('Error loading time series:', error);
            alert('Error al cargar los datos');
        } finally {
            setLoadingCorrientes(false);
        }
    };

    // Download handlers
    const handleDownloadExcelDCP = async () => {
        if (selectedProductsDCP.length === 0) {
            alert('Por favor selecciona al menos un producto');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }

        try {
            const params = new URLSearchParams();
            selectedProductsDCP.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);

            const response = await fetch(`${API_BASE}/dcp/indices/export?${params}`);
            if (!response.ok) {
                throw new Error('Error al generar el archivo Excel');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'indices_precios_relativos.xlsx';
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
    
    const handleDownloadExcelCorrientes = async () => {
        if (selectedProductsCorrientes.length === 0) {
            alert('Por favor selecciona al menos un producto');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }

        try {
            const params = new URLSearchParams();
            selectedProductsCorrientes.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);

            const response = await fetch(`${API_BASE}/products/prices/export?${params}`);
            if (!response.ok) {
                throw new Error('Error al generar el archivo Excel');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'precios_corrientes.xlsx';
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

    return (
        <div className="min-h-screen bg-gray-50 p-2">
            <div className="w-full">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">MacroData</h1>
                </div>

                {/* Tabs para cambiar entre vistas */}
                <div className="mb-6">
                    <div className="border-b border-gray-200">
                        <nav className="-mb-px flex overflow-x-auto">
                            <button
                                onClick={() => {
                                    setViewMode('corrientes');
                                    setFullscreen(false);
                                }}
                                className={`py-3 px-4 font-medium text-sm transition-all border-b-2 whitespace-nowrap ${
                                    viewMode === 'corrientes'
                                        ? 'bg-gray-100 border-indigo-500 text-indigo-600'
                                        : 'bg-white text-gray-400 border-transparent hover:bg-gray-50 hover:text-gray-600'
                                }`}
                            >
                                Precios Corrientes -moneda original-
                            </button>
                            <button
                                onClick={() => {
                                    setViewMode('pepuc');
                                    setFullscreen(false);
                                }}
                                className={`py-3 px-4 font-medium text-sm transition-all border-b-2 whitespace-nowrap ${
                                    viewMode === 'pepuc'
                                        ? 'bg-gray-100 border-indigo-500 text-indigo-600'
                                        : 'bg-white text-gray-400 border-transparent hover:bg-gray-50 hover:text-gray-600'
                                }`}
                            >
                                Pesos Uruguayos Constantes
                            </button>
                        </nav>
                    </div>
                </div>

                {viewMode === 'pepuc' ? (
                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {/* Panel de controles a la izquierda - oculto en pantalla completa */}
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Selecciona producto o servicio
                                        </label>
                                        <VariableSelector
                                            selectedProducts={selectedProductsDCP}
                                            onSelectionChange={setSelectedProductsDCP}
                                            products={productsDCP.map(p => {
                                                const productCopy = {...p};
                                                delete productCopy.unidad;
                                                return {
                                                    ...productCopy,
                                                    displayName: p.nombre || `${p.nombre}${p.pais ? ` (${p.pais})` : ''}`
                                                };
                                            })}
                                            allProducts={productsDCP.map(p => {
                                                const productCopy = {...p};
                                                delete productCopy.unidad;
                                                return {
                                                    ...productCopy,
                                                    displayName: p.nombre || `${p.nombre}${p.pais ? ` (${p.pais})` : ''}`
                                                };
                                            })}
                                        />
                                    </div>

                                    <MonthYearPicker
                                        fechaDesde={fechaDesde}
                                        fechaHasta={fechaHasta}
                                        onFechaDesdeChange={setFechaDesde}
                                        onFechaHastaChange={setFechaHasta}
                                    />

                                    <div className="flex flex-col gap-2">
                                        <button onClick={handleApplyFiltersDCP} className="btn-primary w-full">
                                            {applyFiltersDCP ? 'Actualizar' : 'Aplicar Filtros'}
                                        </button>
                                        {applyFiltersDCP && dcpData.length > 0 && (
                                            <>
                                                <button 
                                                    onClick={() => setFullscreen(true)} 
                                                    className="px-4 py-2 rounded-lg font-medium transition-all bg-gray-200 text-gray-700 hover:bg-gray-300 w-full"
                                                >
                                                    Pantalla Completa
                                                </button>
                                                <button 
                                                    onClick={handleDownloadExcelDCP} 
                                                    className="px-4 py-2 rounded-lg font-medium transition-all bg-green-600 text-white hover:bg-green-700 w-full flex items-center justify-center gap-2"
                                                >
                                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                    </svg>
                                                    Descargar Excel
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Área del gráfico - ocupa todo en pantalla completa */}
                    <div className={fullscreen ? 'col-span-1' : 'lg:col-span-3'}>
                        {loadingDCP ? (
                            <div className="card">
                                <div className="flex items-center justify-center" style={{ height: '600px' }}>
                                    <div className="text-gray-500">Cargando datos...</div>
                                </div>
                            </div>
                        ) : errorDCP ? (
                            <div className="card">
                                <div className="flex items-center justify-center h-96">
                                    <div className="text-center text-red-600">
                                        <p className="font-bold mb-2">Error al cargar los datos:</p>
                                        <p className="text-sm">{errorDCP}</p>
                                        <p className="text-sm text-gray-500 mt-2">
                                            Por favor, verifica los filtros y la disponibilidad de datos.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ) : dcpData.length > 0 ? (
                            <>
                                <div className={`card ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>Gráfico en pesos uruguayos reales</h2>
                                            <p className="text-sm text-gray-600 mt-1">
                                                <strong>Fórmula:</strong> Precio internacional × TC / IPC
                                            </p>
                                        </div>
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
                                    <div style={{ height: fullscreen ? 'calc(100vh - 120px)' : '600px' }}>
                                        <Base100Chart data={dcpData} fullscreen={fullscreen} />
                                    </div>
                                    {/* Mostrar fuentes únicas al pie del gráfico */}
                                    {dcpData.length > 0 && (() => {
                                        const fuentesUnicas = [...new Set(dcpData.map(item => item.product_source).filter(f => f && f.trim() !== ''))];
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
                                
                                {/* Tabla de resumen - solo mostrar si no está en pantalla completa */}
                                {!fullscreen && (
                                    <div className="card mt-6">
                                        {dcpData.length > 0 ? (
                                            <SummaryTableDCP data={dcpData} fechaDesde={fechaDesde} fechaHasta={fechaHasta} />
                                        ) : (
                                            <div className="text-center py-4 text-gray-500">
                                                <p>No hay datos disponibles para mostrar en la tabla.</p>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="card">
                                <div className="flex items-center justify-center" style={{ height: '600px' }}>
                                    <div className="text-center">
                                        {applyFiltersDCP ? (
                                            <>
                                                <p className="text-gray-500 mb-2">No se encontraron datos</p>
                                                <p className="text-sm text-gray-400">
                                                    Intenta ajustar los filtros o seleccionar otros productos
                                                </p>
                                            </>
                                        ) : (
                                            <>
                                                <p className="text-gray-500 mb-2">Selecciona productos y fechas</p>
                                                <p className="text-sm text-gray-400">
                                                    Luego haz clic en "Aplicar Filtros" para visualizar la evolución del producto/servicio en pesos uruguayos reales
                                                </p>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
                ) : (
                /* Vista de Precios Corrientes */
                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Selecciona producto o servicio
                                        </label>
                                        <VariableSelector
                                            selectedProducts={selectedProductsCorrientes}
                                            onSelectionChange={setSelectedProductsCorrientes}
                                            products={productsDCP.map(p => {
                                                const productCopy = {...p};
                                                delete productCopy.unidad;
                                                return {
                                                    ...productCopy,
                                                    displayName: p.nombre || `${p.nombre}${p.pais ? ` (${p.pais})` : ''}`
                                                };
                                            })}
                                            allProducts={productsDCP.map(p => {
                                                const productCopy = {...p};
                                                delete productCopy.unidad;
                                                return {
                                                    ...productCopy,
                                                    displayName: p.nombre || `${p.nombre}${p.pais ? ` (${p.pais})` : ''}`
                                                };
                                            })}
                                        />
                                    </div>

                                    <MonthYearPicker
                                        fechaDesde={fechaDesde}
                                        fechaHasta={fechaHasta}
                                        onFechaDesdeChange={setFechaDesde}
                                        onFechaHastaChange={setFechaHasta}
                                    />

                                    <div className="flex flex-col gap-2">
                                        <button onClick={handleApplyFiltersCorrientes} className="btn-primary w-full">
                                            {applyFiltersCorrientes ? 'Actualizar' : 'Aplicar Filtros'}
                                        </button>
                                        {applyFiltersCorrientes && timeSeriesData.length > 0 && (
                                            <>
                                                <button 
                                                    onClick={() => setFullscreen(true)} 
                                                    className="px-4 py-2 rounded-lg font-medium transition-all bg-gray-200 text-gray-700 hover:bg-gray-300 w-full"
                                                >
                                                    Pantalla Completa
                                                </button>
                                                <button 
                                                    onClick={handleDownloadExcelCorrientes} 
                                                    className="px-4 py-2 rounded-lg font-medium transition-all bg-green-600 text-white hover:bg-green-700 w-full flex items-center justify-center gap-2"
                                                >
                                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                    </svg>
                                                    Descargar Excel
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <div className={fullscreen ? 'col-span-1' : 'lg:col-span-3'}>
                        {loadingCorrientes ? (
                            <div className="card">
                                <div className="flex items-center justify-center" style={{ height: '600px' }}>
                                    <div className="text-gray-500">Cargando datos...</div>
                                </div>
                            </div>
                        ) : timeSeriesData.length > 0 ? (
                            <div className={`card ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                                <div className="flex justify-between items-center mb-4">
                                    <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>Gráfico de Precios</h2>
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
                                <div style={{ height: fullscreen ? 'calc(100vh - 120px)' : '600px' }}>
                                    <CombinateChart data={timeSeriesData} fullscreen={fullscreen} yAxisTitle="Precio" />
                                </div>
                                {!fullscreen && timeSeriesData.length > 0 && (
                                    <div className="mt-6">
                                        <SummaryTablePrices data={timeSeriesData} fechaDesde={fechaDesde} fechaHasta={fechaHasta} />
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="card">
                                <div className="flex items-center justify-center" style={{ height: '600px' }}>
                                    <div className="text-center">
                                        {applyFiltersCorrientes ? (
                                            <>
                                                <p className="text-gray-500 mb-2">No se encontraron datos</p>
                                                <p className="text-sm text-gray-400">
                                                    Intenta ajustar los filtros o seleccionar otros productos
                                                </p>
                                            </>
                                        ) : (
                                            <>
                                                <p className="text-gray-500 mb-2">Selecciona productos y fechas</p>
                                                <p className="text-sm text-gray-400">
                                                    Luego haz clic en "Aplicar Filtros" para visualizar los datos
                                                </p>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
                )}
            </div>
        </div>
    );
}
