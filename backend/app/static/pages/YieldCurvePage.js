// Página de Curva de Rendimiento (Yield Curve)
function YieldCurvePage() {
    // Estados para vista de curva
    const [selectedTipos, setSelectedTipos] = React.useState(['nominal']); // Array: puede contener 'nominal', 'real', o ambos
    const [selectedFechas, setSelectedFechas] = React.useState([]);
    const [fechasDisponibles, setFechasDisponibles] = React.useState([]);
    const [ultimaFecha, setUltimaFecha] = React.useState(null);
    const [curveData, setCurveData] = React.useState([]); // Array de curvas, una por fecha
    const [tableData, setTableData] = React.useState(null);
    
    // Estados para vista temporal
    const [viewMode, setViewMode] = React.useState('curva'); // 'curva' | 'temporal' | 'inflacion-implicita'
    const [selectedPlazos, setSelectedPlazos] = React.useState([]);
    const [fechaDesde, setFechaDesde] = React.useState(() => {
        const date = new Date();
        date.setDate(date.getDate() - 90); // Últimos 90 días por defecto
        return date.toISOString().split('T')[0];
    });
    const [fechaHasta, setFechaHasta] = React.useState(() => {
        return new Date().toISOString().split('T')[0];
    });
    const [timeseriesData, setTimeseriesData] = React.useState([]);
    
    // Estados compartidos
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState(null);
    const [fullscreen, setFullscreen] = React.useState(false);
    const chartRef = React.useRef(null);
    const chartInstanceRef = React.useRef(null);

    // Función helper para formatear fechas en formato dd/mm/yyyy
    const formatFecha = (fechaStr) => {
        if (!fechaStr) return '';
        // Parsear fecha manualmente para evitar problemas de zona horaria
        // Formato esperado: YYYY-MM-DD
        const partes = fechaStr.split('-');
        if (partes.length === 3) {
            const anio = partes[0];
            const mes = partes[1];
            const dia = partes[2];
            return `${dia}/${mes}/${anio}`;
        }
        // Fallback: usar Date si el formato no es YYYY-MM-DD
        const fecha = new Date(fechaStr);
        const dia = String(fecha.getDate()).padStart(2, '0');
        const mes = String(fecha.getMonth() + 1).padStart(2, '0');
        const anio = fecha.getFullYear();
        return `${dia}/${mes}/${anio}`;
    };

    // Preparar fechas para VariableSelector
    const fechasParaSelector = React.useMemo(() => {
        return fechasDisponibles.map((fecha, idx) => ({
            id: fecha,
            nombre: fecha,
            displayName: `${formatFecha(fecha)}${fecha === ultimaFecha ? ' (Última)' : ''}`
        }));
    }, [fechasDisponibles, ultimaFecha]);

    // Preparar plazos para el selector (vista temporal)
    // Incluye tanto nominales como reales con su tipo indicado
    const plazosParaSelector = React.useMemo(() => {
        const plazos = [];
        
        // Plazos nominales (id_variable 37-51)
        const nominales = [
            { id: 37, nombre: '1 mes', tipo: 'nominal' },
            { id: 38, nombre: '2 meses', tipo: 'nominal' },
            { id: 39, nombre: '3 meses', tipo: 'nominal' },
            { id: 40, nombre: '6 meses', tipo: 'nominal' },
            { id: 41, nombre: '9 meses', tipo: 'nominal' },
            { id: 42, nombre: '1 año', tipo: 'nominal' },
            { id: 43, nombre: '2 años', tipo: 'nominal' },
            { id: 44, nombre: '3 años', tipo: 'nominal' },
            { id: 45, nombre: '4 años', tipo: 'nominal' },
            { id: 46, nombre: '5 años', tipo: 'nominal' },
            { id: 47, nombre: '6 años', tipo: 'nominal' },
            { id: 48, nombre: '7 años', tipo: 'nominal' },
            { id: 49, nombre: '8 años', tipo: 'nominal' },
            { id: 50, nombre: '9 años', tipo: 'nominal' },
            { id: 51, nombre: '10 años', tipo: 'nominal' },
        ];
        
        // Plazos reales (id_variable 73-84, 69-72)
        const reales = [
            { id: 73, nombre: '3 meses', tipo: 'real' },
            { id: 74, nombre: '6 meses', tipo: 'real' },
            { id: 75, nombre: '1 año', tipo: 'real' },
            { id: 76, nombre: '2 años', tipo: 'real' },
            { id: 77, nombre: '3 años', tipo: 'real' },
            { id: 78, nombre: '4 años', tipo: 'real' },
            { id: 79, nombre: '5 años', tipo: 'real' },
            { id: 80, nombre: '6 años', tipo: 'real' },
            { id: 81, nombre: '7 años', tipo: 'real' },
            { id: 82, nombre: '8 años', tipo: 'real' },
            { id: 83, nombre: '9 años', tipo: 'real' },
            { id: 84, nombre: '10 años', tipo: 'real' },
            { id: 69, nombre: '15 años', tipo: 'real' },
            { id: 70, nombre: '20 años', tipo: 'real' },
            { id: 71, nombre: '25 años', tipo: 'real' },
            { id: 72, nombre: '30 años', tipo: 'real' },
        ];
        
        // Combinar y formatear
        [...nominales, ...reales].forEach(plazo => {
            plazos.push({
                id: String(plazo.id),
                nombre: plazo.nombre,
                displayName: `${plazo.nombre} (${plazo.tipo === 'nominal' ? 'nominal' : 'real'})`,
                tipo: plazo.tipo
            });
        });
        
        return plazos;
    }, []);

    // Cargar fechas disponibles al inicio
    React.useEffect(() => {
        fetch(`${API_BASE}/yield-curve/dates`)
            .then(res => res.json())
            .then(data => {
                const fechas = data.fechas_disponibles || [];
                setFechasDisponibles(fechas);
                setUltimaFecha(data.ultima_fecha);
                // Por defecto, seleccionar la última fecha
                if (data.ultima_fecha) {
                    setSelectedFechas([data.ultima_fecha]);
                }
            })
            .catch(err => {
                console.error('Error loading dates:', err);
                setError('Error al cargar las fechas disponibles');
            });
    }, []);

    // No cargar automáticamente - esperar a que el usuario haga clic en "Aplicar Filtros"

    const handleApplyFilters = async () => {
        if (selectedTipos.length === 0) {
            alert('Por favor selecciona al menos un tipo (Nominal o Real)');
            return;
        }
        if (selectedFechas.length === 0) {
            alert('Por favor selecciona al menos una fecha');
            return;
        }
        
        setLoading(true);
        setError(null);

        try {
            // Cargar datos para todas las combinaciones de fecha y tipo
            const allPromises = [];
            selectedFechas.forEach(fecha => {
                selectedTipos.forEach(tipo => {
                    allPromises.push(
                        fetch(`${API_BASE}/yield-curve/data?fecha=${fecha}&tipo=${tipo}`)
                            .then(res => {
                                if (!res.ok) {
                                    throw new Error(`Error ${res.status} para fecha ${fecha} y tipo ${tipo}`);
                                }
                                return res.json();
                            })
                            .then(result => ({
                                fecha: fecha,
                                fecha_display: formatFecha(fecha),
                                tipo: tipo,
                                data: result.data || []
                            }))
                    );
                });
            });

            const curvesResults = await Promise.all(allPromises);
            console.log('Datos de curvas recibidos:', curvesResults);
            
            // Formatear datos para el gráfico (similar a Base100Chart)
            const formattedData = curvesResults.map(curve => ({
                fecha: curve.fecha,
                fecha_display: curve.fecha_display,
                tipo: curve.tipo,
                data: curve.data
                    .filter(item => item.valor !== null && item.valor !== undefined)
                    .map(item => ({
                        fecha: item.nombre, // Usar el nombre del plazo como "fecha" para el eje X
                        valor: parseFloat(item.valor)
                    }))
            }));
            
            setCurveData(formattedData);

            // Cargar datos de la tabla usando la PRIMERA fecha y tipo seleccionados
            const primeraFecha = selectedFechas[0];
            const primerTipo = selectedTipos[0];
            const tableResponse = await fetch(`${API_BASE}/yield-curve/table?fecha=${primeraFecha}&tipo=${primerTipo}`);
            if (!tableResponse.ok) {
                throw new Error(`Error ${tableResponse.status}`);
            }
            const tableResult = await tableResponse.json();
            console.log('Datos de tabla recibidos:', tableResult);
            setTableData(tableResult);
        } catch (err) {
            console.error('Error loading data:', err);
            setError(err.message || 'Error al cargar los datos');
            setCurveData([]);
            setTableData(null);
        } finally {
            setLoading(false);
        }
    };

    // Función para cargar datos temporales
    const handleLoadTimeseries = async () => {
        if (selectedPlazos.length === 0) {
            alert('Por favor selecciona al menos un plazo');
            return;
        }
        
        setLoading(true);
        setError(null);
        
        try {
            const params = new URLSearchParams();
            selectedPlazos.forEach(id => params.append('id_variables[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);
            
            const response = await fetch(`${API_BASE}/yield-curve/timeseries?${params}`);
            if (!response.ok) {
                throw new Error(`Error ${response.status}`);
            }
            const result = await response.json();
            
            // Formatear datos para Base100Chart
            const formattedData = result.data.map(plazo => ({
                plazo: plazo.nombre,
                data: plazo.data
                    .filter(item => item.valor !== null && item.valor !== undefined)
                    .map(item => ({
                        fecha: item.fecha,
                        valor: parseFloat(item.valor)
                    }))
            }));
            
            setTimeseriesData(formattedData);
        } catch (err) {
            console.error('Error loading timeseries:', err);
            setError(err.message || 'Error al cargar los datos');
            setTimeseriesData([]);
        } finally {
            setLoading(false);
        }
    };

    // Renderizar gráfico
    React.useEffect(() => {
        console.log('useEffect gráfico - curveData:', curveData, 'chartRef.current:', chartRef.current);
        
        if (!curveData || curveData.length === 0) {
            console.log('No hay datos, limpiando gráfico');
            // Limpiar gráfico si no hay datos
            if (chartInstanceRef.current) {
                chartInstanceRef.current.destroy();
                chartInstanceRef.current = null;
            }
            return;
        }

        // Verificar que Chart esté disponible (esperar a que se cargue)
        const checkChart = () => {
            if (typeof Chart === 'undefined') {
                console.warn('Chart.js aún no está disponible, reintentando...');
                setTimeout(checkChart, 100);
                return;
            }

            const canvas = chartRef.current;
            if (!canvas) {
                console.warn('Canvas aún no está disponible, reintentando...');
                setTimeout(checkChart, 100);
                return;
            }

            const ctx = canvas.getContext('2d');
            if (!ctx) {
                console.error('No se pudo obtener el contexto del canvas');
                return;
            }

            // Destruir gráfico anterior si existe
            if (chartInstanceRef.current) {
                chartInstanceRef.current.destroy();
                chartInstanceRef.current = null;
            }

            // Obtener todos los plazos únicos (labels del eje X)
            const allPlazos = new Set();
            curveData.forEach(curve => {
                curve.data.forEach(item => {
                    if (item.fecha) allPlazos.add(item.fecha);
                });
            });
            const labels = Array.from(allPlazos).sort((a, b) => {
                // Ordenar por orden de plazos: 1 mes, 2 meses, 3 meses, etc.
                const orden = ['1 mes', '2 meses', '3 meses', '6 meses', '9 meses', '1 año', 
                              '2 años', '3 años', '4 años', '5 años', '6 años', '7 años', 
                              '8 años', '9 años', '10 años'];
                const indexA = orden.indexOf(a);
                const indexB = orden.indexOf(b);
                if (indexA !== -1 && indexB !== -1) return indexA - indexB;
                if (indexA !== -1) return -1;
                if (indexB !== -1) return 1;
                return a.localeCompare(b);
            });

            // Colores para cada curva (fecha)
            const colors = [
                'rgb(59, 130, 246)',   // azul brillante
                'rgb(239, 68, 68)',    // rojo
                'rgb(34, 197, 94)',    // verde
                'rgb(245, 158, 11)',   // amarillo/naranja
                'rgb(168, 85, 247)',   // púrpura
                'rgb(236, 72, 153)',   // rosa
                'rgb(6, 182, 212)',    // cyan
                'rgb(251, 146, 60)',   // naranja
                'rgb(99, 102, 241)',   // índigo
                'rgb(20, 184, 166)',   // teal
            ];

            // Crear datasets para cada fecha y tipo
            const datasets = curveData.map((curve, index) => {
                const dataMap = new Map(curve.data.map(item => [item.fecha, item.valor]));
                const tipoLabel = curve.tipo === 'nominal' ? 'Nominal' : 'Real';
                return {
                    label: `${curve.fecha_display} - ${tipoLabel}`,
                    data: labels.map(plazo => dataMap.get(plazo) || null),
                    borderColor: colors[index % colors.length],
                    backgroundColor: 'transparent',
                    borderWidth: fullscreen ? 3 : 2,
                    fill: false, // Sin sombra
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: colors[index % colors.length],
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                };
            });

            console.log('Datos para gráfico:', { labels, datasetsCount: datasets.length });

            if (labels.length === 0 || datasets.length === 0) {
                console.warn('No hay datos válidos para mostrar');
                return;
            }

            try {
                chartInstanceRef.current = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels, // Eje X: strings (nombres de plazos)
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
                                    }
                                }
                            },
                            title: {
                                display: true,
                                text: 'Curva de Rendimiento - Uruguay',
                                font: {
                                    size: 16,
                                    weight: 'bold'
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true, // Arrancar en 0
                                title: {
                                    display: true,
                                    text: 'Tasa de Rendimiento (%)'
                                },
                                ticks: {
                                    callback: function(value) {
                                        return value.toFixed(2) + '%';
                                    }
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Plazo'
                                }
                            }
                        }
                    }
                });
                console.log('Gráfico creado exitosamente con', labels.length, 'plazos y', datasets.length, 'fechas');
            } catch (err) {
                console.error('Error al crear el gráfico:', err);
                console.error('Stack:', err.stack);
            }
        };

        // Esperar a que el canvas esté renderizado
        // Usar requestAnimationFrame + setTimeout para asegurar que el DOM esté actualizado
        let timeoutId;
        let frameId = requestAnimationFrame(() => {
            timeoutId = setTimeout(checkChart, 300);
        });

        // Cleanup
        return () => {
            if (frameId) cancelAnimationFrame(frameId);
            if (timeoutId) clearTimeout(timeoutId);
            if (chartInstanceRef.current) {
                chartInstanceRef.current.destroy();
                chartInstanceRef.current = null;
            }
        };
    }, [curveData, fullscreen]);

    // Tabla de variaciones (estilo similar a InflacionDolaresPage)
    const VariationsTable = ({ data }) => {
        const [sortConfig, setSortConfig] = React.useState({ key: null, direction: 'asc' });

        if (!data || !data.data) return null;

        const formatVariation = (value) => {
            if (value === null || value === undefined) return 'N/A';
            const sign = value >= 0 ? '+' : '';
            return `${sign}${value.toFixed(2)}`;
        };

        const getVariationColor = (value) => {
            if (value === null || value === undefined) return 'text-gray-500';
            return value >= 0 ? 'text-green-600' : 'text-red-600';
        };

        const tableDataRows = data.data.map(row => ({
            plazo: row.nombre,
            valorReferencia: row.valor_referencia,
            variacion5d: row.variacion_5_dias,
            variacion30d: row.variacion_30_dias,
            variacion360d: row.variacion_360_dias,
            variacionAnio: row.variacion_anio_actual
        }));

        const handleSort = (key) => {
            let direction = 'asc';
            if (sortConfig.key === key && sortConfig.direction === 'asc') {
                direction = 'desc';
            }
            setSortConfig({ key, direction });
        };

        const sortedData = [...tableDataRows].sort((a, b) => {
            if (sortConfig.key === null) return 0;
            let aVal = a[sortConfig.key];
            let bVal = b[sortConfig.key];
            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }
            if (aVal === null || aVal === undefined) return 1;
            if (bVal === null || bVal === undefined) return -1;
            if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
            return 0;
        });

        const SortIcon = ({ columnKey }) => {
            if (sortConfig.key !== columnKey) {
                return <span className="text-gray-400">↕</span>;
            }
            return sortConfig.direction === 'asc' ? <span>↑</span> : <span>↓</span>;
        };

        return (
            <div className="card">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">Tabla de Variaciones</h2>
                    {data.fecha_referencia && (
                        <span className="text-sm text-gray-600">
                            Fecha de referencia: <strong>{formatFecha(data.fecha_referencia)}</strong>
                        </span>
                    )}
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th 
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('plazo')}
                                >
                                    Plazo <SortIcon columnKey="plazo" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('valorReferencia')}
                                >
                                    Valor (%) <SortIcon columnKey="valorReferencia" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('variacion5d')}
                                >
                                    Var. 5 días (pp) <SortIcon columnKey="variacion5d" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('variacion30d')}
                                >
                                    Var. 30 días (pp) <SortIcon columnKey="variacion30d" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('variacion360d')}
                                >
                                    Var. 360 días (pp) <SortIcon columnKey="variacion360d" />
                                </th>
                                <th 
                                    className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                    onClick={() => handleSort('variacionAnio')}
                                >
                                    Var. Año Actual (pp) <SortIcon columnKey="variacionAnio" />
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {sortedData.map((row, idx) => (
                                <tr key={idx} className="hover:bg-gray-50">
                                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                                        {row.plazo}
                                    </td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">
                                        {row.valorReferencia !== null ? row.valorReferencia.toFixed(2) : 'N/A'}
                                    </td>
                                    <td className={`px-4 py-3 whitespace-nowrap text-sm text-right ${getVariationColor(row.variacion5d)}`}>
                                        {formatVariation(row.variacion5d)}
                                    </td>
                                    <td className={`px-4 py-3 whitespace-nowrap text-sm text-right ${getVariationColor(row.variacion30d)}`}>
                                        {formatVariation(row.variacion30d)}
                                    </td>
                                    <td className={`px-4 py-3 whitespace-nowrap text-sm text-right ${getVariationColor(row.variacion360d)}`}>
                                        {formatVariation(row.variacion360d)}
                                    </td>
                                    <td className={`px-4 py-3 whitespace-nowrap text-sm text-right ${getVariationColor(row.variacionAnio)}`}>
                                        {formatVariation(row.variacionAnio)}
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
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Curva de Rendimiento - Uruguay</h1>
                </div>

                {/* Tabs para cambiar entre vistas */}
                <div className="mb-6">
                    <div className="border-b border-gray-200">
                        <nav className="-mb-px flex overflow-x-auto">
                            <button
                                onClick={() => {
                                    setViewMode('curva');
                                    setFullscreen(false);
                                }}
                                className={`py-3 px-4 font-medium text-sm transition-all border-b-2 whitespace-nowrap ${
                                    viewMode === 'curva'
                                        ? 'bg-gray-100 border-indigo-500 text-indigo-600'
                                        : 'bg-white text-gray-400 border-transparent hover:bg-gray-50 hover:text-gray-600'
                                }`}
                            >
                                Curva Soberana
                            </button>
                            <button
                                onClick={() => {
                                    setViewMode('temporal');
                                    setFullscreen(false);
                                }}
                                className={`py-3 px-4 font-medium text-sm transition-all border-b-2 whitespace-nowrap ${
                                    viewMode === 'temporal'
                                        ? 'bg-gray-100 border-indigo-500 text-indigo-600'
                                        : 'bg-white text-gray-400 border-transparent hover:bg-gray-50 hover:text-gray-600'
                                }`}
                            >
                                Análisis temporal
                            </button>
                            <button
                                onClick={() => {
                                    setViewMode('inflacion-implicita-curva');
                                    setFullscreen(false);
                                }}
                                className={`py-3 px-4 font-medium text-sm transition-all border-b-2 whitespace-nowrap ${
                                    viewMode === 'inflacion-implicita-curva'
                                        ? 'bg-gray-100 border-indigo-500 text-indigo-600'
                                        : 'bg-white text-gray-400 border-transparent hover:bg-gray-50 hover:text-gray-600'
                                }`}
                            >
                                Inflación implícita (curva)
                            </button>
                            <button
                                onClick={() => {
                                    setViewMode('inflacion-implicita-temporal');
                                    setFullscreen(false);
                                }}
                                className={`py-3 px-4 font-medium text-sm transition-all border-b-2 whitespace-nowrap ${
                                    viewMode === 'inflacion-implicita-temporal'
                                        ? 'bg-gray-100 border-indigo-500 text-indigo-600'
                                        : 'bg-white text-gray-400 border-transparent hover:bg-gray-50 hover:text-gray-600'
                                }`}
                            >
                                Inflación implícita (evolución)
                            </button>
                        </nav>
                    </div>
                </div>

                {viewMode === 'inflacion-implicita-curva' ? (
                <InflacionImplicitaPage embeddedView="curva" />
                ) : viewMode === 'inflacion-implicita-temporal' ? (
                <InflacionImplicitaPage embeddedView="evolucion" />
                ) : viewMode === 'curva' ? (
                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {/* Panel de controles a la izquierda */}
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Tipo de Curva
                                        </label>
                                        <div className="space-y-2">
                                            <label className="flex items-center">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedTipos.includes('nominal')}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setSelectedTipos([...selectedTipos, 'nominal']);
                                                        } else {
                                                            setSelectedTipos(selectedTipos.filter(t => t !== 'nominal'));
                                                        }
                                                    }}
                                                    className="mr-2 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                                                />
                                                <span className="text-sm text-gray-700">Nominal</span>
                                            </label>
                                            <label className="flex items-center">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedTipos.includes('real')}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setSelectedTipos([...selectedTipos, 'real']);
                                                        } else {
                                                            setSelectedTipos(selectedTipos.filter(t => t !== 'real'));
                                                        }
                                                    }}
                                                    className="mr-2 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                                                />
                                                <span className="text-sm text-gray-700">Real</span>
                                            </label>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Selecciona fecha
                                        </label>
                                        <VariableSelector
                                            selectedProducts={selectedFechas}
                                            onSelectionChange={setSelectedFechas}
                                            products={fechasParaSelector}
                                            allProducts={fechasParaSelector}
                                        />
                                    </div>

                                    <div className="flex flex-col gap-2">
                                        <button
                                            onClick={handleApplyFilters}
                                            disabled={loading || selectedTipos.length === 0 || selectedFechas.length === 0}
                                            className="btn-primary w-full"
                                        >
                                            {loading ? 'Cargando...' : 'Aplicar Filtros'}
                                        </button>
                                        <button
                                            onClick={() => {
                                                setSelectedTipos(['nominal']);
                                                setSelectedFechas([]);
                                                setCurveData([]);
                                                setTableData(null);
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
                        ) : curveData && curveData.length > 0 ? (
                            <>
                                <div className={`card mb-6 ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                                    <div className="flex justify-between items-center mb-4">
                                        <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>
                                            Curva de Rendimiento
                                        </h2>
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
                                    <div style={{ height: fullscreen ? 'calc(100vh - 120px)' : '500px', position: 'relative' }}>
                                        {/* Canvas siempre renderizado, como en Base100Chart */}
                                        <canvas ref={chartRef}></canvas>
                                    </div>
                                </div>

                                {!fullscreen && tableData && <VariationsTable data={tableData} />}
                            </>
                        ) : (
                            <div className="card">
                                <div className="flex items-center justify-center py-12">
                                    <div className="text-center text-gray-500">
                                        <p>Selecciona una fecha para visualizar la curva de rendimiento</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
                ) : (
                /* Vista Temporal */
                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {/* Panel de controles a la izquierda */}
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Selecciona plazos
                                        </label>
                                        <VariableSelector
                                            selectedProducts={selectedPlazos}
                                            onSelectionChange={setSelectedPlazos}
                                            products={plazosParaSelector}
                                            allProducts={plazosParaSelector}
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Rango de fechas
                                        </label>
                                        <DateRangePicker
                                            fechaDesde={fechaDesde}
                                            fechaHasta={fechaHasta}
                                            onFechaDesdeChange={setFechaDesde}
                                            onFechaHastaChange={setFechaHasta}
                                        />
                                    </div>

                                    <div className="flex flex-col gap-2">
                                        <button
                                            onClick={handleLoadTimeseries}
                                            disabled={loading || selectedPlazos.length === 0}
                                            className="btn-primary w-full"
                                        >
                                            {loading ? 'Cargando...' : 'Aplicar Filtros'}
                                        </button>
                                        <button
                                            onClick={() => {
                                                setSelectedPlazos([]);
                                                setTimeseriesData([]);
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
                        ) : timeseriesData.length > 0 ? (
                            <div className={`card mb-6 ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                                <div className="flex justify-between items-center mb-4">
                                    <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>
                                        Evolución Temporal de Tasas
                                    </h2>
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
                                <div style={{ height: fullscreen ? 'calc(100vh - 120px)' : '500px' }}>
                                    <Base100Chart 
                                        data={timeseriesData.map(plazo => ({
                                            pais: plazo.plazo,
                                            data: plazo.data
                                        }))}
                                        fullscreen={fullscreen}
                                        yAxisTitle="Tasa de Rendimiento (%)"
                                    />
                                </div>
                            </div>
                        ) : (
                            <div className="card">
                                <div className="flex items-center justify-center py-12">
                                    <div className="text-center text-gray-500">
                                        <p>Selecciona plazos y un rango de fechas, luego haz clic en "Aplicar Filtros" para visualizar la evolución temporal</p>
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
