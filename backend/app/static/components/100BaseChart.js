// Componente de Gráfico con Base 100 (unificado para DCP e Inflación en dólares)
function Base100Chart({ data, fullscreen = false, yAxisTitle, showReferenceLine = false }) {
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
            }
        });
        
        // Ordenar fechas correctamente usando parseISODateLocal
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

        const datasets = data.map((series, index) => {
            const indices = series.data || [];
            const productName = series.pais || series.product_name || `Serie ${index + 1}`;
            const dataMap = new Map(indices.map(item => [item.fecha, item.valor]));
            
            return {
                label: productName,
                data: sortedDates.map(fecha => dataMap.get(fecha) || null),
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                borderWidth: fullscreen ? 3 : 2,
                fill: false,
                tension: 0.1,
            };
        });

        // Agregar línea de referencia en y=100 si se solicita
        if (showReferenceLine) {
            const referenceLine = {
                label: 'Base 100',
                data: sortedDates.map(() => 100),
                borderColor: 'rgba(0, 0, 0, 0.3)',
                backgroundColor: 'transparent',
                borderWidth: 1,
                borderDash: [5, 5],
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
                tension: 0,
            };
            datasets.push(referenceLine);
        }

        const ctx = chartRef.current.getContext('2d');
        
        chartInstanceRef.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedDates.map(fecha => {
                    const date = parseISODateLocal(fecha);
                    if (!date) return fecha;
                    return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
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
                            usePointStyle: !showReferenceLine,
                            filter: showReferenceLine ? function(item, chart) {
                                // Ocultar la línea de referencia de la leyenda
                                return item.text !== 'Base 100';
                            } : undefined,
                        },
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        titleFont: {
                            size: fullscreen ? 14 : 12,
                        },
                        bodyFont: {
                            size: fullscreen ? 13 : 11,
                        },
                        filter: showReferenceLine ? function(tooltipItem) {
                            // Ocultar tooltip para la línea de referencia
                            return tooltipItem.datasetIndex !== datasets.length - 1;
                        } : undefined,
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
                            text: yAxisTitle || 'Índice (base 100)',
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
    }, [data, fullscreen, yAxisTitle, showReferenceLine]);

    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
                <p className="text-gray-500">No hay datos para mostrar</p>
            </div>
        );
    }

    return <canvas ref={chartRef}></canvas>;
}
