// Componente de Gráfico Combinado - puede mostrar valores nominales o base 100
function CombinateChart({ data, fullscreen = false, extractCountryName, viewMode = 'nominal', yAxisTitle = null }) {
    const chartRef = React.useRef(null);
    const chartInstanceRef = React.useRef(null);

    React.useEffect(() => {
        if (!data || data.length === 0) return;

        if (chartInstanceRef.current) {
            chartInstanceRef.current.destroy();
        }

        // Preparar datos para Chart.js
        const allDates = new Set();
        data.forEach(series => {
            if (series.data && Array.isArray(series.data)) {
                series.data.forEach(item => allDates.add(item.fecha));
            } else if (series.precios && Array.isArray(series.precios)) {
                series.precios.forEach(price => allDates.add(price.fecha));
            }
        });
        
        // Ordenar fechas correctamente usando parseISODateLocal para evitar problemas de zona horaria
        const sortedDates = Array.from(allDates)
            .map(fecha => {
                const date = parseISODateLocal(fecha);
                return { fecha, date, timestamp: date ? date.getTime() : 0 };
            })
            .filter(item => item.date !== null)
            .sort((a, b) => a.timestamp - b.timestamp)
            .map(item => item.fecha);

        // Colores para las líneas
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
            'rgb(220, 38, 127)',   // fucsia
            'rgb(14, 165, 233)',   // sky
        ];

        // Normalizar a base 100 si es necesario
        const normalizeToBase100 = (values) => {
            if (viewMode !== 'base100' || values.length === 0) return values;
            const firstValue = values.find(v => v !== null && v !== undefined);
            if (!firstValue || firstValue === 0) return values;
            const factor = 100.0 / firstValue;
            return values.map(v => v !== null && v !== undefined ? v * factor : null);
        };

        const datasets = data.map((series, index) => {
            const values = series.data || series.precios || [];
            const productName = series.product_name || (series.producto && series.producto.nombre) || `Producto ${index + 1}`;
            
            // Crear mapa de datos por fecha
            const dataMap = new Map();
            values.forEach(item => {
                if (item.fecha) {
                    dataMap.set(item.fecha, item.valor);
                }
            });
            
            // Obtener valores para todas las fechas ordenadas
            let rawValues = sortedDates.map(fecha => dataMap.get(fecha) || null);
            
            // Normalizar a base 100 si es necesario
            rawValues = normalizeToBase100(rawValues);
            
            // Determinar label
            let label = productName;
            if (extractCountryName && series.product_name) {
                label = extractCountryName(series.product_name, series.pais, series.id_variable);
            } else if (series.pais) {
                label = series.pais;
            }
            
            return {
                label: label,
                data: rawValues,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                borderWidth: fullscreen ? 3 : 2,
                fill: false,
                tension: 0.1,
            };
        });

        const ctx = chartRef.current.getContext('2d');
        chartInstanceRef.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedDates.map(fecha => {
                    const date = parseISODateLocal(fecha);
                    if (!date) return fecha;
                    // Formato de fecha según el tipo de datos
                    // Si tiene día (fecha completa), mostrar dd-mm-yy, sino mostrar mes-año
                    if (fecha.includes('-') && fecha.split('-').length === 3) {
                        return date.toLocaleDateString('es-UY', { 
                            day: '2-digit', 
                            month: '2-digit', 
                            year: '2-digit' 
                        });
                    } else {
                        return date.toLocaleDateString('es-ES', { 
                            day: '2-digit', 
                            month: '2-digit', 
                            year: 'numeric' 
                        });
                    }
                }),
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: fullscreen ? 14 : 12,
                            },
                            padding: fullscreen ? 15 : 10,
                            usePointStyle: true,
                        },
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                const fecha = sortedDates[context[0].dataIndex];
                                const date = parseISODateLocal(fecha);
                                if (!date) return fecha;
                                if (fecha.includes('-') && fecha.split('-').length === 3) {
                                    return date.toLocaleDateString('es-UY', { 
                                        day: '2-digit', 
                                        month: '2-digit', 
                                        year: '2-digit' 
                                    });
                                } else {
                                    return date.toLocaleDateString('es-ES', { 
                                        day: '2-digit', 
                                        month: '2-digit', 
                                        year: 'numeric' 
                                    });
                                }
                            },
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y.toFixed(4);
                                }
                                return label;
                            },
                        },
                        titleFont: {
                            size: fullscreen ? 14 : 12,
                        },
                        bodyFont: {
                            size: fullscreen ? 13 : 11,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            font: {
                                size: fullscreen ? 14 : 12,
                            },
                        },
                        title: {
                            display: true,
                            text: yAxisTitle || (viewMode === 'base100' ? 'Índice (base 100)' : 'Precio'),
                            font: {
                                size: fullscreen ? 16 : 14,
                                weight: 'bold',
                            },
                        },
                    },
                    x: {
                        ticks: {
                            font: {
                                size: fullscreen ? 13 : 11,
                            },
                        },
                    },
                },
            },
        });

        return () => {
            if (chartInstanceRef.current) {
                chartInstanceRef.current.destroy();
            }
        };
    }, [data, fullscreen, viewMode, extractCountryName, yAxisTitle]);

    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
                <p className="text-gray-500">No hay datos para mostrar</p>
            </div>
        );
    }

    return <canvas ref={chartRef}></canvas>;
}
