// Página de Análisis de Licitaciones LRM
function LicitacionesLRMPage() {
    const [selectedCombinacion, setSelectedCombinacion] = React.useState(null); // {fecha, plazo}
    const [combinacionesDisponibles, setCombinacionesDisponibles] = React.useState([]);
    const [ultimaCombinacion, setUltimaCombinacion] = React.useState(null);
    
    // Datos de la licitación seleccionada
    const [licitacionData, setLicitacionData] = React.useState(null);
    const [bevsaRate, setBevsaRate] = React.useState(null);
    const [stats, setStats] = React.useState(null);
    const [curveData, setCurveData] = React.useState(null);
    const [timeseriesData, setTimeseriesData] = React.useState([]);
    const [expandedTable, setExpandedTable] = React.useState(false);
    
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState(null);
    const [updating, setUpdating] = React.useState(false);
    const [updateStatus, setUpdateStatus] = React.useState(null);
    const chartRef = React.useRef(null);
    const chartInstanceRef = React.useRef(null);
    const timeseriesChartRef = React.useRef(null);
    const timeseriesChartInstanceRef = React.useRef(null);

    // Función helper para formatear fechas en formato dd/mm/yyyy
    const formatFecha = (fechaStr) => {
        if (!fechaStr) return '';
        const partes = fechaStr.split('-');
        if (partes.length === 3) {
            const anio = partes[0];
            const mes = partes[1];
            const dia = partes[2];
            return `${dia}/${mes}/${anio}`;
        }
        const fecha = new Date(fechaStr);
        const dia = String(fecha.getDate()).padStart(2, '0');
        const mes = String(fecha.getMonth() + 1).padStart(2, '0');
        const anio = fecha.getFullYear();
        return `${dia}/${mes}/${anio}`;
    };

    // Formatear números con separadores de miles
    const formatNumber = (num) => {
        if (num === null || num === undefined) return 'N/A';
        const n = Number(num);
        if (Number.isNaN(n)) return 'N/A';
        return new Intl.NumberFormat('es-UY', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(n);
    };

    // Formatear porcentaje (acepta número, string u objeto desde la API/PostgreSQL)
    const formatPercent = (num) => {
        if (num === null || num === undefined) return 'N/A';
        const n = Number(num);
        if (!Number.isFinite(n)) return 'N/A';
        return n.toFixed(2) + '%';
    };

    // Función para obtener el color basado en la diferencia entre tasa_corte y tasa_bevsa
    const getTasaColor = (tasaCorte, tasaBevsa) => {
        if (tasaCorte === null || tasaCorte === undefined || 
            tasaBevsa === null || tasaBevsa === undefined) {
            return 'text-gray-900'; // Sin color si falta algún dato
        }
        
        const diferencia = Math.abs(parseFloat(tasaCorte) - parseFloat(tasaBevsa));
        
        if (diferencia <= 0.5) {
            return 'text-green-600'; // Verde si diferencia <= 0.5%
        } else if (diferencia <= 1.0) {
            return 'text-yellow-600'; // Amarillo si diferencia entre 0.5% y 1%
        } else {
            return 'text-red-600'; // Rojo si diferencia > 1%
        }
    };

    // Función para generar PDF
    const handleGeneratePDF = async () => {
        if (!selectedCombinacion || !selectedCombinacion.fecha || !selectedCombinacion.plazo) {
            alert('Por favor selecciona una licitación para generar el informe.');
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE}/licitaciones-lrm/generate-pdf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    fecha: selectedCombinacion.fecha,
                    plazo: selectedCombinacion.plazo
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Error ${response.status}`);
            }
            
            // Descargar el PDF
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `licitacion_lrm_${selectedCombinacion.fecha}_${selectedCombinacion.plazo}dias.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
        } catch (error) {
            console.error('Error generating PDF:', error);
            alert(`Error al generar PDF: ${error.message}`);
        }
    };

    // Función para actualizar datos
    const handleUpdate = async () => {
        if (updating) return;
        
        if (!confirm('¿Deseas actualizar los datos de Licitaciones LRM? Esto descargará el Excel desde BCU y actualizará la base de datos.')) {
            return;
        }
        
        setUpdating(true);
        setUpdateStatus(null);
        
        try {
            const response = await fetch(`${API_BASE}/licitaciones-lrm/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Error ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            setUpdateStatus({
                running: true,
                message: data.message,
                started_at: data.started_at
            });
            
            // Polling para obtener el estado
            const checkStatus = setInterval(async () => {
                try {
                    const statusRes = await fetch(`${API_BASE}/licitaciones-lrm/update/status`);
                    const status = await statusRes.json();
                    setUpdateStatus(status);
                    
                    if (!status.running) {
                        clearInterval(checkStatus);
                        setUpdating(false);
                        
                        if (status.returncode === 0) {
                            alert('Actualización completada exitosamente.');
                            try {
                                const datesRes = await fetch(`${API_BASE}/licitaciones-lrm/dates`);
                                if (datesRes.ok) {
                                    const datesData = await datesRes.json();
                                    const combinaciones = datesData.combinaciones || [];
                                    setCombinacionesDisponibles(combinaciones);
                                    const nuevaUltima = datesData.ultima_fecha && datesData.ultimo_plazo != null
                                        ? { fecha: datesData.ultima_fecha, plazo: datesData.ultimo_plazo }
                                        : null;
                                    if (nuevaUltima) {
                                        setUltimaCombinacion(nuevaUltima);
                                        setSelectedCombinacion(nuevaUltima);
                                    }
                                }
                            } catch (err) {
                                console.error('Error al refrescar combinaciones:', err);
                            }
                        } else {
                            // Mostrar error más detallado
                            let errorMsg = `Error en la actualización (código: ${status.returncode})\n\n`;
                            if (status.error) {
                                errorMsg += `Detalles:\n${status.error.substring(0, 1000)}`;
                                if (status.error.length > 1000) {
                                    errorMsg += '\n\n... (error truncado, ver consola para detalles completos)';
                                }
                            } else if (status.output) {
                                // Buscar líneas de error en el output
                                const outputLines = status.output.split('\n');
                                const errorLines = outputLines.filter(line => 
                                    line.toLowerCase().includes('error') || 
                                    line.toLowerCase().includes('exception') ||
                                    line.toLowerCase().includes('traceback') ||
                                    line.toLowerCase().includes('failed')
                                );
                                if (errorLines.length > 0) {
                                    errorMsg += `Últimas líneas de error:\n${errorLines.slice(-10).join('\n')}`;
                                } else {
                                    errorMsg += `Output:\n${status.output.substring(0, 500)}`;
                                }
                            } else {
                                errorMsg += 'Error desconocido. Verifique la consola del navegador para más detalles.';
                            }
                            alert(errorMsg);
                            console.error('Error completo:', status);
                        }
                    }
                } catch (err) {
                    console.error('Error checking status:', err);
                    clearInterval(checkStatus);
                    setUpdating(false);
                }
            }, 2000); // Verificar cada 2 segundos
            
        } catch (error) {
            console.error('Error al iniciar actualización:', error);
            alert(`Error: ${error.message}`);
            setUpdating(false);
        }
    };

    // Preparar combinaciones para VariableSelector
    const combinacionesParaSelector = React.useMemo(() => {
        if (!combinacionesDisponibles || !Array.isArray(combinacionesDisponibles)) {
            return [];
        }
        return combinacionesDisponibles.map((combinacion) => {
            // Usar un separador que no esté en las fechas (YYYY-MM-DD)
            const key = `${combinacion.fecha}|${combinacion.plazo}`;
            const esUltima = ultimaCombinacion && 
                combinacion.fecha === ultimaCombinacion.fecha && 
                combinacion.plazo === ultimaCombinacion.plazo;
            return {
                id: key,
                nombre: key,
                displayName: `${formatFecha(combinacion.fecha)} - ${combinacion.plazo} días${esUltima ? ' (Última)' : ''}`
            };
        });
    }, [combinacionesDisponibles, ultimaCombinacion]);

    // Cargar combinaciones disponibles al inicio
    React.useEffect(() => {
        console.log('[LicitacionesLRM] Cargando combinaciones desde:', `${API_BASE}/licitaciones-lrm/dates`);
        fetch(`${API_BASE}/licitaciones-lrm/dates`)
            .then(res => {
                console.log('[LicitacionesLRM] Response status:', res.status);
                if (!res.ok) {
                    throw new Error(`Error ${res.status}: ${res.statusText}`);
                }
                return res.json();
            })
            .then(data => {
                console.log('[LicitacionesLRM] Datos recibidos:', data);
                const combinaciones = data.combinaciones || [];
                setCombinacionesDisponibles(combinaciones);
                
                // Establecer última combinación
                if (data.ultima_fecha && data.ultimo_plazo !== undefined && data.ultimo_plazo !== null) {
                    const ultima = {
                        fecha: data.ultima_fecha,
                        plazo: data.ultimo_plazo
                    };
                    console.log('[LicitacionesLRM] Última combinación:', ultima);
                    setUltimaCombinacion(ultima);
                    // Por defecto, seleccionar la última combinación
                    setSelectedCombinacion(ultima);
                } else {
                    console.warn('[LicitacionesLRM] No se encontró última combinación:', {ultima_fecha: data.ultima_fecha, ultimo_plazo: data.ultimo_plazo});
                }
            })
            .catch(err => {
                console.error('[LicitacionesLRM] Error loading dates:', err);
                setError(`Error al cargar las combinaciones disponibles: ${err.message}`);
            });
    }, []);

    // Cargar datos cuando cambia la combinación seleccionada
    React.useEffect(() => {
        if (selectedCombinacion && selectedCombinacion.fecha && selectedCombinacion.plazo) {
            console.log('[LicitacionesLRM] Cargando datos para combinación:', selectedCombinacion);
            loadLicitacionData(selectedCombinacion.fecha, selectedCombinacion.plazo);
        } else {
            console.warn('[LicitacionesLRM] Combinación inválida:', selectedCombinacion);
        }
    }, [selectedCombinacion]);

    const loadLicitacionData = async (fecha, plazo) => {
        setLoading(true);
        setError(null);

        try {
            // Cargar datos de la licitación
            const licitacionRes = await fetch(`${API_BASE}/licitaciones-lrm/data?fecha=${fecha}&plazo=${plazo}`);
            if (!licitacionRes.ok) {
                const errorData = await licitacionRes.json().catch(() => ({}));
                const errorMsg = errorData.error || `Error ${licitacionRes.status}`;
                console.error('[LicitacionesLRM] Error al cargar datos:', errorMsg, {fecha, plazo});
                throw new Error(`${errorMsg} (fecha: ${fecha}, plazo: ${plazo})`);
            }
            const licitacion = await licitacionRes.json();
            setLicitacionData(licitacion);

            // Cargar tasa BEVSA para el plazo (del día de la licitación)
            if (plazo) {
                const bevsaRes = await fetch(`${API_BASE}/licitaciones-lrm/bevsa-rate?plazo=${plazo}&fecha_limite=${fecha}`);
                if (bevsaRes.ok) {
                    const bevsa = await bevsaRes.json();
                    setBevsaRate(bevsa);
                }

                // Cargar estadísticas de últimas 5 licitaciones
                const statsRes = await fetch(`${API_BASE}/licitaciones-lrm/stats?plazo=${plazo}&fecha_limite=${fecha}`);
                if (statsRes.ok) {
                    const statsData = await statsRes.json();
                    setStats(statsData);
                }

                // Cargar curva BEVSA del día (o más cercana)
                const curveRes = await fetch(`${API_BASE}/licitaciones-lrm/curve-by-date?fecha=${fecha}`);
                if (curveRes.ok) {
                    const curve = await curveRes.json();
                    setCurveData(curve);
                }

                // Cargar timeseries de últimos 40 días (igual que en el PDF)
                const timeseriesRes = await fetch(`${API_BASE}/licitaciones-lrm/bevsa-timeseries?plazo=${plazo}&fecha_hasta=${fecha}&dias=40`);
                if (timeseriesRes.ok) {
                    const timeseries = await timeseriesRes.json();
                    setTimeseriesData(timeseries.data || []);
                }
            }
        } catch (error) {
            console.error('Error loading licitacion data:', error);
            setError(error.message || 'Error al cargar los datos');
        } finally {
            setLoading(false);
        }
    };

    // Renderizar gráfico de curva BEVSA
    React.useEffect(() => {
        if (!curveData || !curveData.data || curveData.data.length === 0) {
            return;
        }

        requestAnimationFrame(() => {
            setTimeout(() => {
                if (!chartRef.current) {
                    return;
                }

                const ctx = chartRef.current.getContext('2d');
                
                if (chartInstanceRef.current) {
                    chartInstanceRef.current.destroy();
                }

                const labels = curveData.data
                    .filter(item => item.valor !== null && item.valor !== undefined)
                    .map(item => item.nombre);
                
                const valores = curveData.data
                    .filter(item => item.valor !== null && item.valor !== undefined)
                    .map(item => parseFloat(item.valor));

                const fechaMostrar = curveData.fecha_original === curveData.fecha 
                    ? formatFecha(curveData.fecha)
                    : `${formatFecha(curveData.fecha)} (más cercana)`;

                chartInstanceRef.current = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Tasa Nominal (%)',
                            data: valores,
                            borderColor: 'rgb(99, 102, 241)',
                            backgroundColor: 'rgba(99, 102, 241, 0.1)',
                            fill: false,
                            tension: 0.4,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: `Curva BEVSA Nominal - ${fechaMostrar}`,
                                font: {
                                    size: 16,
                                    weight: 'bold'
                                }
                            },
                            legend: {
                                display: true,
                                position: 'top'
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Tasa (%)'
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
            }, 300);
        });
    }, [curveData]);

    // Renderizar gráfico temporal de tasa BEVSA (40 días, 3 líneas de tasa corte)
    React.useEffect(() => {
        if (!timeseriesData || timeseriesData.length === 0 || !licitacionData) {
            return;
        }

        requestAnimationFrame(() => {
            setTimeout(() => {
                if (!timeseriesChartRef.current) {
                    return;
                }

                const ctx = timeseriesChartRef.current.getContext('2d');
                
                if (timeseriesChartInstanceRef.current) {
                    timeseriesChartInstanceRef.current.destroy();
                }

                const labels = timeseriesData.map(item => formatFecha(item.fecha));
                const fechasTs = timeseriesData.map(item => (item.fecha && String(item.fecha).split('T')[0]) || item.fecha);
                const valores = timeseriesData.map(item => parseFloat(item.valor) || 0);
                const plazoActual = licitacionData.plazo || selectedCombinacion?.plazo || 'N/A';

                const datasets = [
                    {
                        label: 'Tasa BEVSA',
                        data: valores,
                        borderColor: 'rgb(37, 99, 235)',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        fill: false,
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 4
                    }
                ];

                // Últimas 3 tasas de corte: color distinto, leyenda con fecha, punto/cruz en el día de la licitación
                const licits = (stats && stats.licitaciones) ? stats.licitaciones : [];
                const colores = ['rgb(220, 38, 38)', 'rgb(13, 148, 136)', 'rgb(124, 58, 237)']; // rojo, teal, violeta
                for (let idx = 0; idx < Math.min(3, licits.length); idx++) {
                    const lic = licits[idx];
                    const tc = lic.tasa_corte;
                    if (tc != null && Number.isFinite(Number(tc))) {
                        const valor = Number(tc);
                        const fechaLic = lic.fecha ? String(lic.fecha).split('T')[0] : null;
                        const indexDia = fechaLic != null ? fechasTs.indexOf(fechaLic) : -1;
                        const pointRadiusArr = indexDia >= 0
                            ? labels.map((_, i) => i === indexDia ? 8 : 0)
                            : 0;
                        datasets.push({
                            label: `Tasa corte ${formatFecha(lic.fecha)}`,
                            data: labels.map(() => valor),
                            borderColor: colores[idx],
                            backgroundColor: colores[idx],
                            fill: false,
                            tension: 0,
                            pointRadius: pointRadiusArr,
                            pointHoverRadius: indexDia >= 0 ? 10 : 2,
                            pointStyle: 'circle',
                            borderDash: [5, 5]
                        });
                    }
                }

                timeseriesChartInstanceRef.current = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: `Comportamiento de Tasa BEVSA ${plazoActual} días - Últimos 40 días`,
                                font: {
                                    size: 16,
                                    weight: 'bold'
                                }
                            },
                            legend: {
                                display: true,
                                position: 'top'
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                title: {
                                    display: true,
                                    text: 'Tasa (%)'
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
                                    text: 'Fecha'
                                },
                                ticks: {
                                    maxRotation: 45,
                                    minRotation: 45
                                }
                            }
                        }
                    }
                });
            }, 300);
        });
    }, [timeseriesData, licitacionData, selectedCombinacion, stats]);

    console.log('[LicitacionesLRM] Renderizando componente. Estado:', {
        selectedCombinacion,
        combinacionesDisponibles: combinacionesDisponibles.length,
        loading,
        error,
        licitacionData: !!licitacionData
    });

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-7xl mx-auto">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Análisis de Licitaciones LRM</h1>
                        {selectedCombinacion && selectedCombinacion.fecha && (
                            <p className="print-only mt-1 text-lg text-gray-600">
                                Licitación {formatFecha(selectedCombinacion.fecha)} – {selectedCombinacion.plazo} días
                            </p>
                        )}
                    </div>
                    <div className="no-print flex gap-3">
                        <button
                            type="button"
                            onClick={() => window.print()}
                            disabled={!selectedCombinacion || !selectedCombinacion.fecha}
                            className={`px-4 py-2 rounded-md font-medium flex items-center gap-2 transition-colors ${
                                !selectedCombinacion || !selectedCombinacion.fecha
                                    ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                                    : 'bg-emerald-600 text-white hover:bg-emerald-700'
                            }`}
                            title="Abre el diálogo de impresión para guardar como PDF (vista del front)"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 01-2 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2h-6a2 2 0 00-2 2v4a2 2 0 002 2h2z" />
                            </svg>
                            Imprimir / Guardar como PDF
                        </button>
                        <button
                            onClick={handleGeneratePDF}
                            disabled={!selectedCombinacion || !selectedCombinacion.fecha || !selectedCombinacion.plazo}
                            className={`px-4 py-2 rounded-md font-medium flex items-center gap-2 transition-colors ${
                                !selectedCombinacion || !selectedCombinacion.fecha || !selectedCombinacion.plazo
                                    ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                                    : 'bg-red-600 text-white hover:bg-red-700'
                            }`}
                            title="Descargar informe PDF generado en servidor"
                        >
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z" clipRule="evenodd" />
                            </svg>
                            Informe PDF (servidor)
                        </button>
                        <button
                            onClick={handleUpdate}
                            disabled={updating}
                            className={`px-4 py-2 rounded-md font-medium transition-colors ${
                                updating
                                    ? 'bg-gray-400 cursor-not-allowed text-white'
                                    : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                            }`}
                        >
                            {updating ? 'Actualizando...' : 'Actualizar'}
                        </button>
                    </div>
                </div>
                
                {updateStatus && (
                    <div className="no-print mb-6 p-3 bg-blue-50 border border-blue-200 rounded-md">
                        <div className="text-sm text-blue-800">
                            <strong>Estado:</strong> {updateStatus.running ? 'En progreso' : 'Completado'}
                            {updateStatus.step && (
                                <span className="ml-2">
                                    {updateStatus.step === 'download' ? '📥 Descargando Excel' : 
                                     updateStatus.step === 'update' ? '💾 Actualizando BD' : 
                                     updateStatus.step === 'completed' ? '✅ Completado' : 
                                     `(${updateStatus.step})`}
                                </span>
                            )}
                        </div>
                    </div>
                )}

                {/* Selector de licitación (fecha - plazo) */}
                <div className="no-print bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
                    <div className="flex items-center gap-4">
                        <div className="flex-1">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Seleccione una licitación (fecha - plazo)
                            </label>
                            {combinacionesParaSelector && combinacionesParaSelector.length > 0 ? (
                                <VariableSelector
                                    products={combinacionesParaSelector || []}
                                    selectedProducts={selectedCombinacion ? [`${selectedCombinacion.fecha}|${selectedCombinacion.plazo}`] : []}
                                    allProducts={combinacionesParaSelector || []}
                                    onSelectionChange={(items) => {
                                        if (items && items.length > 0) {
                                            // Parsear el ID para obtener fecha y plazo (usando | como separador)
                                            const parts = items[0].split('|');
                                            if (parts.length !== 2) {
                                                console.error('[LicitacionesLRM] Error al parsear ID:', items[0], 'parts:', parts);
                                                return;
                                            }
                                            const [fecha, plazoStr] = parts;
                                            const plazoNum = parseInt(plazoStr, 10);
                                            if (isNaN(plazoNum)) {
                                                console.error('[LicitacionesLRM] Error al parsear plazo:', plazoStr);
                                                return;
                                            }
                                            const nuevaCombinacion = {
                                                fecha: fecha,
                                                plazo: plazoNum
                                            };
                                            console.log('[LicitacionesLRM] Seleccionando combinación:', nuevaCombinacion);
                                            setSelectedCombinacion(nuevaCombinacion);
                                        } else {
                                            setSelectedCombinacion(null);
                                        }
                                    }}
                                />
                            ) : (
                                <div className="text-sm text-gray-500">
                                    {loading ? 'Cargando licitaciones...' : 'No hay licitaciones disponibles'}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
                        {error}
                    </div>
                )}

                {loading && (
                    <div className="text-center py-8">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                        <p className="mt-2 text-gray-600">Cargando datos...</p>
                    </div>
                )}

                {!loading && licitacionData && (
                    <div className="space-y-6">
                        {/* Título y datos principales */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            {/* Título en una línea */}
                            <h2 className="text-xl font-bold text-gray-900 mb-4">
                                Licitación del {formatFecha(licitacionData.fecha)} - Plazo {licitacionData.plazo} días
                            </h2>
                            
                            {/* Primera fila: 4 columnas */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                                <div>
                                    <p className="text-sm text-gray-600">Monto Licitado</p>
                                    <p className="text-lg font-semibold text-gray-900">
                                        {formatNumber(licitacionData.monto_licitado)}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Adjudicado</p>
                                    <p className="text-lg font-semibold text-gray-900">
                                        {formatPercent((licitacionData.adjudicado || 0) * 100)}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Tasa de Corte</p>
                                    <p className={`text-lg font-semibold ${getTasaColor(licitacionData.tasa_corte, bevsaRate?.ultimo_valor)}`}>
                                        {formatPercent(licitacionData.tasa_corte)}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-sm text-gray-600">Tasa BEVSA</p>
                                    <p className={`text-lg font-semibold ${getTasaColor(licitacionData.tasa_corte, bevsaRate?.ultimo_valor)}`}>
                                        {bevsaRate ? formatPercent(bevsaRate.ultimo_valor || 0) : 'N/A'}
                                    </p>
                                </div>
                            </div>

                            {/* Segunda fila: Mínimo y Máximo con fechas */}
                            {bevsaRate && (bevsaRate.min_5_dias !== null || bevsaRate.max_5_dias !== null) && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                                    <div>
                                        <p className="text-sm text-gray-600">Mínimo (5 días)</p>
                                        <div className="flex items-baseline gap-2">
                                            <p className="text-lg font-semibold text-green-600">
                                                {formatPercent(bevsaRate.min_5_dias || 0)}
                                            </p>
                                            {bevsaRate.fecha_min && (
                                                <p className="text-xs text-gray-500">
                                                    ({formatFecha(bevsaRate.fecha_min)})
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-600">Máximo (5 días)</p>
                                        <div className="flex items-baseline gap-2">
                                            <p className="text-lg font-semibold text-red-600">
                                                {formatPercent(bevsaRate.max_5_dias || 0)}
                                            </p>
                                            {bevsaRate.fecha_max && (
                                                <p className="text-xs text-gray-500">
                                                    ({formatFecha(bevsaRate.fecha_max)})
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )                            }
                        </div>

                        {/* Gráfico temporal 30 días (segundo bloque, igual que en el PDF) */}
                        {timeseriesData && timeseriesData.length > 0 && licitacionData && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-bold text-gray-900 mb-4">
                                    Comportamiento de Tasa BEVSA {licitacionData.plazo} días - Últimos 40 días
                                </h2>
                                <div className="print-chart-container" style={{ height: '400px', position: 'relative' }}>
                                    <canvas ref={timeseriesChartRef}></canvas>
                                </div>
                            </div>
                        )}

                        {/* Estadísticas - Últimas 5 Licitaciones */}
                        {stats && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-bold text-gray-900 mb-4">
                                    Estadísticas - Últimas 5 Licitaciones a {stats.plazo || licitacionData.plazo} días
                                </h2>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                                    <div>
                                        <p className="text-sm text-gray-600">Total Licitado</p>
                                        <p className="text-lg font-semibold text-gray-900">
                                            {formatNumber(stats.total_licitado)}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-600">Total Adjudicado</p>
                                        <p className="text-lg font-semibold text-gray-900">
                                            {formatNumber(stats.total_adjudicado)}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-600">% Adjudicación Ponderado</p>
                                        <p className="text-lg font-semibold text-indigo-600">
                                            {formatPercent(stats.porcentaje_adjudicacion)}
                                        </p>
                                    </div>
                                </div>
                                
                                {/* Tabla expandible/colapsable */}
                                {stats.licitaciones && stats.licitaciones.length > 0 && (
                                    <div>
                                        <button
                                            type="button"
                                            onClick={() => setExpandedTable(!expandedTable)}
                                            className="no-print flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700 mb-2"
                                        >
                                            {expandedTable ? (
                                                <>
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                                                    </svg>
                                                    Ocultar detalle
                                                </>
                                            ) : (
                                                <>
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                                    </svg>
                                                    Ver detalle ({stats.licitaciones.length} licitaciones)
                                                </>
                                            )}
                                        </button>
                                        
                                        {(expandedTable || true) && (
                                            <div className={`overflow-x-auto mt-2 print-expand-table ${!expandedTable ? 'hidden' : ''}`}>
                                                <table className="min-w-full divide-y divide-gray-200">
                                                    <thead className="bg-gray-50">
                                                        <tr>
                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                Fecha
                                                            </th>
                                                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                Monto Licitado
                                                            </th>
                                                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                % Adjudicado
                                                            </th>
                                                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                Monto Adjudicado
                                                            </th>
                                                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                Tasa de Corte
                                                            </th>
                                                            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                Tasa BEVSA
                                                            </th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                        {stats.licitaciones.map((lic, idx) => (
                                                            <tr key={idx}>
                                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                                                    {formatFecha(lic.fecha)}
                                                                </td>
                                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                                                                    {formatNumber(lic.monto_licitado)}
                                                                </td>
                                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                                                                    {formatPercent(lic.porcentaje_adjudicacion)}
                                                                </td>
                                                                <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                                                                    {formatNumber(lic.monto_adjudicado)}
                                                                </td>
                                                                <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-semibold ${getTasaColor(lic.tasa_corte, lic.tasa_bevsa)}`}>
                                                                    {formatPercent(lic.tasa_corte)}
                                                                </td>
                                                                <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-semibold ${getTasaColor(lic.tasa_corte, lic.tasa_bevsa)}`}>
                                                                    {lic.tasa_bevsa !== null && lic.tasa_bevsa !== undefined
                                                                        ? formatPercent(lic.tasa_bevsa)
                                                                        : 'N/A'}
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Gráfico de Curva BEVSA */}
                {curveData && curveData.data && curveData.data.length > 0 && (
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mt-6">
                        <h2 className="text-xl font-bold text-gray-900 mb-4">
                            Curva BEVSA Nominal - {curveData.fecha_original === curveData.fecha 
                                ? formatFecha(curveData.fecha)
                                : `${formatFecha(curveData.fecha)} (más cercana)`}
                        </h2>
                        <div className="print-chart-container" style={{ height: '400px', position: 'relative' }}>
                            <canvas ref={chartRef}></canvas>
                        </div>
                    </div>
                )}

            </div>
        </div>
    );
}
