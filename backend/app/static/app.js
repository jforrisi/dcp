const { useState, useEffect, useRef } = React;

// Detectar automáticamente la URL base de la API
const getApiBase = () => {
    // En producción (Railway), usar ruta relativa
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        return '/api';
    }
    // En desarrollo local
    return 'http://localhost:8000/api';
};

const API_BASE = getApiBase();

// Componente de Selector de Productos
function ProductSelector({ selectedProducts, onSelectionChange, products, allProducts }) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const dropdownRef = useRef(null);
    const inputRef = useRef(null);

    const filteredProducts = products.filter(p => {
        const searchText = (p.displayName || p.nombre).toLowerCase();
        return searchText.includes(searchTerm.toLowerCase());
    });

    const toggleProduct = (id) => {
        if (selectedProducts.includes(id)) {
            onSelectionChange(selectedProducts.filter(i => i !== id));
        } else {
            onSelectionChange([...selectedProducts, id]);
        }
    };

    // Cerrar dropdown al hacer click fuera y auto-focus
    useEffect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };

        // Auto-focus en el input cuando se abre
        const timeoutId = setTimeout(() => {
            if (inputRef.current) {
                try {
                    inputRef.current.focus();
                } catch (e) {
                    // Ignorar errores de focus en algunos navegadores
                }
            }
        }, 50);

        // Agregar listeners para cerrar al hacer click fuera
        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('touchstart', handleClickOutside);
        // También escuchar clicks en el documento
        window.addEventListener('click', handleClickOutside, true);

        return () => {
            clearTimeout(timeoutId);
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('touchstart', handleClickOutside);
            window.removeEventListener('click', handleClickOutside, true);
        };
    }, [isOpen]);

    // Usar allProducts si está disponible, sino usar products
    const productsForDisplay = allProducts || products;

    const handleToggle = (e) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setIsOpen(!isOpen);
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <div
                onClick={handleToggle}
                onTouchStart={(e) => {
                    e.preventDefault();
                    handleToggle(e);
                }}
                className="input-field cursor-pointer flex items-center justify-between"
                role="button"
                tabIndex={0}
                aria-expanded={isOpen}
                aria-haspopup="listbox"
                onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
                        e.preventDefault();
                        handleToggle(e);
                    }
                }}
            >
                <span className="text-gray-600">
                    {selectedProducts.length === 0
                        ? 'Selecciona productos...'
                        : `${selectedProducts.length} producto${selectedProducts.length > 1 ? 's' : ''} seleccionado${selectedProducts.length > 1 ? 's' : ''}`}
                </span>
                <svg className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </div>

            {isOpen && (
                <div 
                    className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-hidden"
                    style={{ 
                        position: 'absolute', 
                        zIndex: 9999,
                        WebkitOverflowScrolling: 'touch'
                    }}
                    onClick={(e) => e.stopPropagation()}
                    onTouchStart={(e) => e.stopPropagation()}
                >
                    <div className="p-3 border-b border-gray-200">
                        <input
                            ref={inputRef}
                            type="text"
                            placeholder="Buscar productos..."
                            value={searchTerm}
                            onChange={(e) => {
                                e.stopPropagation();
                                setSearchTerm(e.target.value);
                            }}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                            onClick={(e) => e.stopPropagation()}
                            onTouchStart={(e) => e.stopPropagation()}
                            onFocus={(e) => e.stopPropagation()}
                            autoFocus={true}
                        />
                    </div>
                    <div 
                        className="overflow-y-auto max-h-80" 
                        style={{ WebkitOverflowScrolling: 'touch' }}
                    >
                        {filteredProducts.length === 0 ? (
                            <div className="p-3 text-center text-gray-500 text-sm">
                                No se encontraron productos
                            </div>
                        ) : (
                            filteredProducts.map((product) => (
                                <label
                                    key={product.id}
                                    className="flex items-center p-3 hover:bg-gray-50 active:bg-gray-100 cursor-pointer border-b border-gray-100 last:border-b-0"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                    }}
                                    onTouchStart={(e) => {
                                        e.stopPropagation();
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedProducts.includes(product.id)}
                                        onChange={(e) => {
                                            e.stopPropagation();
                                            toggleProduct(product.id);
                                        }}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                        }}
                                        onTouchStart={(e) => {
                                            e.stopPropagation();
                                        }}
                                        className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                                    />
                                    <div className="ml-3 flex-1">
                                        <div className="text-sm font-medium text-gray-900">{product.displayName || product.nombre}</div>
                                        {product.unidad && (
                                            <div className="text-xs text-gray-500">{product.unidad}</div>
                                        )}
                                    </div>
                                </label>
                            ))
                        )}
                    </div>
                </div>
            )}

            {selectedProducts.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                    {productsForDisplay.filter(p => selectedProducts.includes(p.id)).map((product) => (
                        <span
                            key={product.id}
                            className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-indigo-100 text-indigo-700 border border-indigo-200"
                        >
                            {product.displayName || product.nombre}
                            <button
                                onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    toggleProduct(product.id);
                                }}
                                onTouchStart={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    toggleProduct(product.id);
                                }}
                                className="ml-2 text-indigo-700 hover:text-indigo-900 focus:outline-none"
                                type="button"
                                aria-label={`Eliminar ${product.nombre}`}
                            >
                                ×
                            </button>
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}

// Componente de Selector de Mes/Año
function MonthYearPicker({ fechaDesde, fechaHasta, onFechaDesdeChange, onFechaHastaChange }) {
    // Convertir fecha completa (YYYY-MM-DD) a formato mes (YYYY-MM)
    const toMonthFormat = (fecha) => {
        if (!fecha) return '';
        return fecha.substring(0, 7); // Toma YYYY-MM
    };

    // Convertir formato mes (YYYY-MM) a fecha completa
    const fromMonthFormat = (monthValue, isEnd = false) => {
        if (!monthValue) return '';
        if (isEnd) {
            // Para "hasta", usar el último día del mes
            const [year, month] = monthValue.split('-');
            const lastDay = new Date(year, month, 0).getDate();
            return `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
        } else {
            // Para "desde", usar el primer día del mes
            return `${monthValue}-01`;
        }
    };

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Desde (Mes/Año)
                </label>
                <input
                    type="month"
                    value={toMonthFormat(fechaDesde)}
                    onChange={(e) => onFechaDesdeChange(fromMonthFormat(e.target.value, false))}
                    className="input-field"
                />
            </div>
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hasta (Mes/Año)
                </label>
                <input
                    type="month"
                    value={toMonthFormat(fechaHasta)}
                    onChange={(e) => onFechaHastaChange(fromMonthFormat(e.target.value, true))}
                    className="input-field"
                />
            </div>
        </div>
    );
}

// Parsear "YYYY-MM-DD" como fecha LOCAL (evita corrimiento por zona horaria)
function parseISODateLocal(isoDateStr) {
    if (!isoDateStr) return null;
    // Soporta "YYYY-MM-DD" y también "YYYY-MM-DDTHH:MM:SS"
    const datePart = String(isoDateStr).split('T')[0].split(' ')[0];
    const [y, m, d] = datePart.split('-').map(n => parseInt(n, 10));
    if (!y || !m || !d) return null;
    return new Date(y, m - 1, d);
}

// Componente de Gráfico de Líneas
function TimeSeriesChart({ data, fullscreen = false }) {
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
                series.data.forEach(price => allDates.add(price.fecha));
            } else if (series.precios && Array.isArray(series.precios)) {
                series.precios.forEach(price => allDates.add(price.fecha));
            }
        });
        const sortedDates = Array.from(allDates).sort();

        // Colores para las líneas - definidos fuera del map para que todas las series tengan colores distintos
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
            const prices = series.data || series.precios || [];
            const productName = series.product_name || (series.producto && series.producto.nombre) || `Producto ${index + 1}`;
            
            const values = sortedDates.map(date => {
                const price = prices.find(p => p.fecha === date);
                return price ? price.valor : null;
            });

            return {
                label: productName,
                data: values,
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
                labels: sortedDates.map(d => {
                    const date = parseISODateLocal(d) || new Date(d);
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
                            text: 'Precio',
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
    }, [data, fullscreen]);

    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
                <p className="text-gray-500">No hay datos para mostrar</p>
            </div>
        );
    }

    return <canvas ref={chartRef}></canvas>;
}

// Componente de Gráfico de Índices de Precios Relativos
function DCPChart({ data, fullscreen = false }) {
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
        const sortedDates = Array.from(allDates).sort();

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
            const productName = series.product_name || `Producto ${index + 1}`;
            
            const values = sortedDates.map(date => {
                const item = indices.find(i => i.fecha === date);
                return item ? item.valor : null;
            });

            return {
                label: productName,
                data: values,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                borderWidth: fullscreen ? 3 : 2,
                fill: false,
                tension: 0.1,
            };
        });

        const ctx = chartRef.current.getContext('2d');
        
        // Agregar dataset para línea de referencia en y=100
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
        
        chartInstanceRef.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedDates.map(d => {
                    const date = parseISODateLocal(d) || new Date(d);
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
                            filter: function(item, chart) {
                                // Ocultar la línea de referencia de la leyenda
                                return item.text !== 'Base 100';
                            },
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
                        filter: function(tooltipItem) {
                            // Ocultar tooltip para la línea de referencia
                            return tooltipItem.datasetIndex !== datasets.length - 1;
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
                            text: 'Índice de precios en pesos uruguayos reales (base 100)',
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
    }, [data, fullscreen]);

    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
                <p className="text-gray-500">No hay datos para mostrar</p>
            </div>
        );
    }

    return <canvas ref={chartRef}></canvas>;
}

// Componente de Tabla de Resumen de Índices
function SummaryTable({ data, fechaDesde, fechaHasta }) {
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
    
    // Formatear fechas para mostrar
    const formatFecha = (fechaStr) => {
        if (!fechaStr) return '';
        try {
            // Si es formato YYYY-MM-DD, agregar hora para evitar problemas de zona horaria
            let fecha = fechaStr.includes('T') ? new Date(fechaStr) : new Date(fechaStr + 'T00:00:00');
            return fecha.toLocaleDateString('es-UY', { year: 'numeric', month: 'long', day: 'numeric' });
        } catch (e) {
            return fechaStr;
        }
    };
    
    // Obtener fechas del summary (fechas reales del producto) o del filtro como fallback
    let fechaInicial = '';
    let fechaFinal = '';
    
    // Priorizar fechas del summary si están disponibles (son las fechas reales del producto)
    if (data.length > 0 && data[0].summary) {
        if (data[0].summary.fecha_inicial) {
            fechaInicial = formatFecha(data[0].summary.fecha_inicial);
        }
        if (data[0].summary.fecha_final) {
            fechaFinal = formatFecha(data[0].summary.fecha_final);
        }
    }
    
    // Si no hay fechas del summary, usar las del filtro como fallback
    if (!fechaInicial && fechaDesde) {
        fechaInicial = formatFecha(fechaDesde);
    }
    if (!fechaFinal && fechaHasta) {
        fechaFinal = formatFecha(fechaHasta);
    }

    // Formatear intervalo como MM/YY - MM/YY
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

    // Debug: ver qué datos llegan
    console.log('SummaryTable recibió datos:', data);
    
    // Preparar datos para la tabla
    const tableData = data
        .filter(product => {
            const hasSummary = product.summary !== null && product.summary !== undefined;
            const hasPrecioInicial = hasSummary && product.summary.precio_inicial !== null && product.summary.precio_inicial !== undefined;
            if (!hasSummary) {
                console.log('Producto sin summary:', product.product_name, product);
            } else if (!hasPrecioInicial) {
                console.log('Producto sin precio_inicial:', product.product_name, product.summary);
            }
            return hasPrecioInicial;
        })
        .map(product => ({
            nombre: product.product_name,
            intervalo: formatIntervalo(product.summary.fecha_inicial, product.summary.fecha_final),
            precioInicial: product.summary.precio_inicial,
            precioFinal: product.summary.precio_final,
            moneda: product.moneda || 'uyu',
            variacionPrecioNominal: product.summary.variacion_precio_nominal || 0.0,
            variacionTc: product.summary.variacion_tc,
            variacionIpc: product.summary.variacion_ipc,
            variacionReal: product.summary.variacion_real
        }));
    
    console.log('TableData procesado:', tableData);

    // Función de ordenamiento
    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    // Aplicar ordenamiento
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

    const formatMoneda = (moneda) => {
        const monedas = {
            'usd': 'USD',
            'eur': 'EUR',
            'uyu': 'UYU'
        };
        return monedas[moneda] || moneda.toUpperCase();
    };

    const formatVariacion = (valor, esPorcentaje = true) => {
        if (valor === 0 || Math.abs(valor) < 0.01) {
            return esPorcentaje ? '0.00%' : '0.00';
        }
        const signo = valor >= 0 ? '+' : '';
        return esPorcentaje ? `${signo}${valor.toFixed(2)}%` : `${signo}${valor.toFixed(2)}`;
    };

    const getVariacionColor = (valor) => {
        if (valor === 0 || Math.abs(valor) < 0.01) return 'text-gray-600';
        return valor >= 0 ? 'text-green-600' : 'text-red-600';
    };

    if (tableData.length === 0) {
        return (
            <div className="text-center py-8 text-gray-500">
                <p>No hay datos de resumen disponibles para mostrar.</p>
                <p className="text-sm mt-2">Verifica que los productos tengan datos en el rango seleccionado.</p>
            </div>
        );
    }

    return (
        <div className="mt-6">
            <div className="mb-4">
                <h4 className="text-base font-semibold text-gray-900">Resumen a precios reales</h4>
                {(fechaInicial || fechaFinal) && (
                    <p className="text-sm text-gray-600 mt-1">
                        del {fechaInicial} al {fechaFinal}
                    </p>
                )}
            </div>
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                <thead className="bg-gray-50">
                    <tr>
                        <th 
                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                            onClick={() => handleSort('nombre')}
                        >
                            <div className="flex items-center">
                                Nombre
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
                                Precio Inicial
                                <SortIcon columnKey="precioInicial" />
                            </div>
                        </th>
                        <th 
                            className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                            onClick={() => handleSort('precioFinal')}
                        >
                            <div className="flex items-center justify-end">
                                Precio Final
                                <SortIcon columnKey="precioFinal" />
                            </div>
                        </th>
                        <th 
                            className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                            onClick={() => handleSort('moneda')}
                        >
                            <div className="flex items-center justify-center">
                                Moneda
                                <SortIcon columnKey="moneda" />
                            </div>
                        </th>
                        <th 
                            className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                            onClick={() => handleSort('variacionPrecioNominal')}
                        >
                            <div className="flex items-center justify-end">
                                Var. precio nominal (%)
                                <SortIcon columnKey="variacionPrecioNominal" />
                            </div>
                        </th>
                        <th 
                            className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                            onClick={() => handleSort('variacionTc')}
                        >
                            <div className="flex items-center justify-end">
                                Var. TC (%)
                                <SortIcon columnKey="variacionTc" />
                            </div>
                        </th>
                        <th 
                            className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                            onClick={() => handleSort('variacionIpc')}
                        >
                            <div className="flex items-center justify-end">
                                Var. Inflación (%)
                                <SortIcon columnKey="variacionIpc" />
                            </div>
                        </th>
                        <th 
                            className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                            onClick={() => handleSort('variacionReal')}
                        >
                            <div className="flex items-center justify-end">
                                Var. Real (%)
                                <SortIcon columnKey="variacionReal" />
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
                                {row.precioInicial.toFixed(2)}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
                                {row.precioFinal.toFixed(2)}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-center">
                                {formatMoneda(row.moneda)}
                            </td>
                            <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${getVariacionColor(row.variacionPrecioNominal)}`}>
                                {formatVariacion(row.variacionPrecioNominal)}
                            </td>
                            <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${getVariacionColor(row.variacionTc)}`}>
                                {formatVariacion(row.variacionTc)}
                            </td>
                            <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${getVariacionColor(row.variacionIpc)}`}>
                                {formatVariacion(row.variacionIpc)}
                            </td>
                            <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${getVariacionColor(row.variacionReal)}`}>
                                {formatVariacion(row.variacionReal)}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            </div>
        </div>
    );
}

// Página de Índices de Precios Relativos
function DCPPage() {
    const [products, setProducts] = useState([]);
    const [selectedProducts, setSelectedProducts] = useState([]);
    const [tipoFilter, setTipoFilter] = useState('Todos'); // Filtro Producto/Servicio/Interno
    const [fechaDesde, setFechaDesde] = useState(() => {
        const date = new Date();
        date.setMonth(date.getMonth() - 6);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        return `${year}-${month}-01`;
    });
    const [fechaHasta, setFechaHasta] = useState(() => {
        const date = new Date();
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const lastDay = new Date(year, date.getMonth() + 1, 0).getDate();
        return `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
    });
    const [dcpData, setDcpData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [applyFilters, setApplyFilters] = useState(false);
    const [fullscreen, setFullscreen] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetch(`${API_BASE}/products`)
            .then(res => res.json())
            .then(data => setProducts(data))
            .catch(err => console.error('Error loading products:', err));
    }, []);

    const handleApplyFilters = async () => {
        if (selectedProducts.length === 0) {
            alert('Por favor selecciona al menos un producto');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }

        setLoading(true);
        setApplyFilters(true);
        setError(null); // Limpiar error previo

        try {
            const params = new URLSearchParams();
            selectedProducts.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);

            const response = await fetch(`${API_BASE}/dcp/indices?${params}`);
            
            if (!response.ok) {
                let errorMessage = `Error ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.message || errorData.description || errorData.error || errorMessage;
                } catch (e) {
                    // Si no se puede parsear como JSON, intentar leer como texto
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
            setError(null); // Limpiar error si todo está bien
        } catch (error) {
            console.error('Error loading indices:', error);
            const errorMessage = error.message || 'Error al cargar los datos';
            setError(errorMessage);
            setDcpData([]); // Limpiar datos en caso de error
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadExcel = async () => {
        if (selectedProducts.length === 0) {
            alert('Por favor selecciona al menos un producto');
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

    return (
        <div className="min-h-screen bg-gray-50 p-2">
            <div className="w-full">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Analiza la evolución de los precios relativos</h1>
                </div>

                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {/* Panel de controles a la izquierda - oculto en pantalla completa */}
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Tipo
                                        </label>
                                        <select
                                            value={tipoFilter}
                                            onChange={(e) => setTipoFilter(e.target.value)}
                                            className="input-field"
                                        >
                                            <option value="Todos">Todos</option>
                                            <option value="Producto">Producto (exportación)</option>
                                            <option value="Servicio">Servicio (exportación)</option>
                                            <option value="Interno">Producto/Servicio interno</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Selecciona producto o servicio
                                        </label>
                                        <ProductSelector
                                            selectedProducts={selectedProducts}
                                            onSelectionChange={setSelectedProducts}
                                            products={tipoFilter === 'Todos' 
                                                ? products 
                                                : products.filter(p => {
                                                    if (tipoFilter === 'Producto') return p.tipo === 'P';
                                                    if (tipoFilter === 'Servicio') return p.tipo === 'S';
                                                    if (tipoFilter === 'Interno') return p.tipo === 'M';
                                                    return true;
                                                })
                                            }
                                            allProducts={products}
                                        />
                                    </div>

                                    <MonthYearPicker
                                        fechaDesde={fechaDesde}
                                        fechaHasta={fechaHasta}
                                        onFechaDesdeChange={setFechaDesde}
                                        onFechaHastaChange={setFechaHasta}
                                    />

                                    <div className="flex flex-col gap-2">
                                        <button onClick={handleApplyFilters} className="btn-primary w-full">
                                            {applyFilters ? 'Actualizar' : 'Aplicar Filtros'}
                                        </button>
                                        {applyFilters && dcpData.length > 0 && (
                                            <>
                                                <button 
                                                    onClick={() => setFullscreen(true)} 
                                                    className="px-4 py-2 rounded-lg font-medium transition-all bg-gray-200 text-gray-700 hover:bg-gray-300 w-full"
                                                >
                                                    Pantalla Completa
                                                </button>
                                                <button 
                                                    onClick={handleDownloadExcel} 
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
                                        <DCPChart data={dcpData} fullscreen={fullscreen} />
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
                                            <SummaryTable data={dcpData} fechaDesde={fechaDesde} fechaHasta={fechaHasta} />
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
                                        {applyFilters ? (
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
            </div>
        </div>
    );
}

// Página de Precios Corrientes
function TimeSeriesPage() {
    const [products, setProducts] = useState([]);
    const [selectedProducts, setSelectedProducts] = useState([]);
    const [tipoFilter, setTipoFilter] = useState('Todos'); // Filtro Producto/Servicio/Interno
    const [fechaDesde, setFechaDesde] = useState(() => {
        const date = new Date();
        date.setMonth(date.getMonth() - 6);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        return `${year}-${month}-01`;
    });
    const [fechaHasta, setFechaHasta] = useState(() => {
        const date = new Date();
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const lastDay = new Date(year, date.getMonth() + 1, 0).getDate();
        return `${year}-${month}-${String(lastDay).padStart(2, '0')}`;
    });
    const [timeSeriesData, setTimeSeriesData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [applyFilters, setApplyFilters] = useState(false);
    const [fullscreen, setFullscreen] = useState(false);

    useEffect(() => {
        fetch(`${API_BASE}/products`)
            .then(res => res.json())
            .then(data => setProducts(data))
            .catch(err => console.error('Error loading products:', err));
    }, []);

    const handleApplyFilters = async () => {
        if (selectedProducts.length === 0) {
            alert('Por favor selecciona al menos un producto');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            alert('Por favor selecciona un rango de fechas');
            return;
        }

        setLoading(true);
        setApplyFilters(true);

        try {
            const params = new URLSearchParams();
            selectedProducts.forEach(id => params.append('product_ids[]', id));
            params.append('fecha_desde', fechaDesde);
            params.append('fecha_hasta', fechaHasta);

            const response = await fetch(`${API_BASE}/products/prices?${params}`);
            const data = await response.json();
            setTimeSeriesData(data);
        } catch (error) {
            console.error('Error loading time series:', error);
            alert('Error al cargar los datos');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadExcel = async () => {
        if (selectedProducts.length === 0) {
            alert('Por favor selecciona al menos un producto');
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

            const response = await fetch(`${API_BASE}/products/prices/export?${params}`);
            if (!response.ok) {
                throw new Error('Error al generar el archivo Excel');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Generate filename from response headers or use default
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
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Precios Corrientes</h1>
                    <p className="text-gray-600">Visualiza la evolución de precios a lo largo del tiempo</p>
                </div>

                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {/* Panel de controles a la izquierda - oculto en pantalla completa */}
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Tipo
                                        </label>
                                        <select
                                            value={tipoFilter}
                                            onChange={(e) => setTipoFilter(e.target.value)}
                                            className="input-field"
                                        >
                                            <option value="Todos">Todos</option>
                                            <option value="Producto">Producto (exportación)</option>
                                            <option value="Servicio">Servicio (exportación)</option>
                                            <option value="Interno">Producto/Servicio interno</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Productos
                                        </label>
                                        <ProductSelector
                                            selectedProducts={selectedProducts}
                                            onSelectionChange={setSelectedProducts}
                                            products={tipoFilter === 'Todos'
                                                ? products
                                                : products.filter(p => {
                                                    if (tipoFilter === 'Producto') return p.tipo === 'P';
                                                    if (tipoFilter === 'Servicio') return p.tipo === 'S';
                                                    if (tipoFilter === 'Interno') return p.tipo === 'M';
                                                    return true;
                                                })
                                            }
                                            allProducts={products}
                                        />
                                    </div>

                                    <MonthYearPicker
                                        fechaDesde={fechaDesde}
                                        fechaHasta={fechaHasta}
                                        onFechaDesdeChange={setFechaDesde}
                                        onFechaHastaChange={setFechaHasta}
                                    />

                                    <div className="flex flex-col gap-2">
                                        <button onClick={handleApplyFilters} className="btn-primary w-full">
                                            {applyFilters ? 'Actualizar' : 'Aplicar Filtros'}
                                        </button>
                                        {applyFilters && timeSeriesData.length > 0 && (
                                            <>
                                                <button 
                                                    onClick={() => setFullscreen(true)} 
                                                    className="px-4 py-2 rounded-lg font-medium transition-all bg-gray-200 text-gray-700 hover:bg-gray-300 w-full"
                                                >
                                                    Pantalla Completa
                                                </button>
                                                <button 
                                                    onClick={handleDownloadExcel} 
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
                        {loading ? (
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
                                    <TimeSeriesChart data={timeSeriesData} fullscreen={fullscreen} />
                                </div>
                            </div>
                        ) : (
                            <div className="card">
                                <div className="flex items-center justify-center" style={{ height: '600px' }}>
                                    <div className="text-center">
                                        {applyFilters ? (
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
            </div>
        </div>
    );
}
// Componente de Gráfico de Cotizaciones LATAM
function CotizacionesChart({ data, fullscreen = false, extractCountryName }) {
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
        // Ordenar fechas correctamente usando parseISODateLocal para evitar problemas de zona horaria
        const sortedDates = Array.from(allDates)
            .map(fecha => {
                const date = parseISODateLocal(fecha);
                return { fecha, date, timestamp: date ? date.getTime() : 0 };
            })
            .filter(item => item.date !== null)
            .sort((a, b) => a.timestamp - b.timestamp)
            .map(item => item.fecha); // Mantener el formato ISO original para usar como key

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
        ];

        const datasets = data.map((series, index) => {
            const values = series.data || [];
            const dataMap = new Map(values.map(item => [item.fecha, item.valor]));
            
            return {
                label: extractCountryName ? extractCountryName(series.product_name) : series.product_name,
                data: sortedDates.map(fecha => dataMap.get(fecha) || null),
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                borderWidth: 2,
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
                    return date.toLocaleDateString('es-UY', { 
                        day: '2-digit', 
                        month: '2-digit', 
                        year: '2-digit' 
                    });
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
                            usePointStyle: true,
                        },
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                // Mostrar fecha en formato dd-mm-yy
                                const fecha = sortedDates[context[0].dataIndex];
                                const date = parseISODateLocal(fecha);
                                if (!date) return fecha;
                                return date.toLocaleDateString('es-UY', { 
                                    day: '2-digit', 
                                    month: '2-digit', 
                                    year: '2-digit' 
                                });
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
                            text: data.length > 0 && data[0].viewMode === 'base100' 
                                ? 'Índice (base 100)' 
                                : 'Cotización',
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
    }, [data, fullscreen]);

    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
                <p className="text-gray-500">No hay datos para mostrar</p>
            </div>
        );
    }

    return <canvas ref={chartRef}></canvas>;
}

// Página de Cotizaciones LATAM
function CotizacionesLATAMPage() {
    const [products, setProducts] = useState([]);
    const [selectedProducts, setSelectedProducts] = useState([]);
    const [fechaDesde, setFechaDesde] = useState(() => {
        const date = new Date();
        date.setDate(date.getDate() - 30); // Últimos 30 días
        return date.toISOString().split('T')[0];
    });
    const [fechaHasta, setFechaHasta] = useState(() => {
        return new Date().toISOString().split('T')[0];
    });
    const [cotizacionesData, setCotizacionesData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [fullscreen, setFullscreen] = useState(false);
    const [error, setError] = useState(null);
    const [viewMode, setViewMode] = useState('nominal'); // 'nominal' o 'base100'
    const [rawData, setRawData] = useState([]); // Datos originales sin normalizar

    // Función para extraer nombre del país del nombre del producto
    const extractCountryName = (productName) => {
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
        
        // Casos especiales: Argentina tiene dos variantes (CCL y Oficial)
        if (productName.includes('Argentina')) {
            if (productName.includes('CCL') || productName.includes('Dólar CCL')) {
                return 'Argentina (CCL)';
            }
            if (productName.includes('Oficial')) {
                return 'Argentina (Oficial)';
            }
        }
        
        // Intentar extraer del nombre (buscar entre paréntesis)
        const match = productName.match(/\(([^)]+)\)/);
        if (match) {
            const textInParens = match[1];
            // Buscar nombres de países conocidos (incluyendo variantes en inglés)
            const countries = [
                'Argentina', 'Brasil', 'Uruguay', 'Chile', 'Colombia', 'Perú', 
                'México', 'Paraguay', 'Bolivia', 'Venezuela',
                'Australia', 'Sudáfrica', 'South Africa', 'Nueva Zelanda', 'New Zealand'
            ];
            for (const country of countries) {
                if (textInParens.includes(country)) {
                    // Normalizar nombres en inglés a español
                    if (country === 'South Africa') return 'Sudáfrica';
                    if (country === 'New Zealand') return 'Nueva Zelanda';
                    return country;
                }
            }
        }
        
        // Si no se encuentra, buscar código de moneda en el nombre
        for (const [currency, country] of Object.entries(currencyToCountry)) {
            if (productName.includes(`/${currency}`) || productName.includes(` ${currency}`) || productName.includes(`(${currency}`)) {
                return country;
            }
        }
        
        // Si nada funciona, devolver el nombre completo
        return productName;
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
    useEffect(() => {
        fetch(`${API_BASE}/cotizaciones/products`)
            .then(res => res.json())
            .then(data => {
                setProducts(data);
            })
            .catch(err => console.error('Error loading cotizaciones products:', err));
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

    // Aplicar normalización cuando cambian los datos o el modo de visualización
    useEffect(() => {
        if (viewMode === 'base100' && rawData.length > 0) {
            const normalizedData = rawData.map(series => {
                if (!series.data || series.data.length === 0) return series;
                
                const firstValue = series.data[0].valor;
                if (firstValue === 0) return series;
                
                const factor = 100.0 / firstValue;
                const normalizedData = series.data.map(item => ({
                    ...item,
                    valor: item.valor * factor
                }));
                
                return {
                    ...series,
                    data: normalizedData
                };
            });
            setCotizacionesData(normalizedData);
        } else {
            setCotizacionesData(rawData);
        }
    }, [rawData, viewMode]);

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
        const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

        const tableData = data
            .filter(item => item.summary && item.summary.precio_inicial !== null)
            .map(item => ({
                                nombre: extractCountryName(item.product_name),
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
                                        <ProductSelector
                                            selectedProducts={selectedProducts}
                                            onSelectionChange={setSelectedProducts}
                                            products={products.map(p => ({...p, displayName: extractCountryName(p.nombre)}))}
                                            allProducts={products.map(p => ({...p, displayName: extractCountryName(p.nombre)}))}
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

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Desde
                                        </label>
                                        <input
                                            type="date"
                                            value={fechaDesde}
                                            onChange={(e) => setFechaDesde(e.target.value)}
                                            className="input-field w-full"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Hasta
                                        </label>
                                        <input
                                            type="date"
                                            value={fechaHasta}
                                            onChange={(e) => setFechaHasta(e.target.value)}
                                            className="input-field w-full"
                                        />
                                    </div>

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
                                        <CotizacionesChart 
                                            data={cotizacionesData.map(d => ({...d, viewMode}))} 
                                            fullscreen={fullscreen} 
                                            extractCountryName={extractCountryName} 
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
                                
                                {/* Tabla de resumen */}
                                {!fullscreen && (
                                    <div className="card mt-6">
                                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Resumen de Cotizaciones</h3>
                                        <SummaryTable data={cotizacionesData} />
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

// Componente de Navegación
function Navigation({ currentPage, onPageChange }) {
    return (
        <nav className="bg-white border-b border-gray-200 shadow-sm">
            <div className="w-full px-2 py-2">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        </div>
                        <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            Índice de precios relativos
                        </h1>
                    </div>

                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => onPageChange('dcp')}
                            className={`px-4 py-2 rounded-lg font-medium transition-all ${
                                currentPage === 'dcp'
                                    ? 'bg-indigo-600 text-white'
                                    : 'text-gray-700 hover:bg-gray-100'
                            }`}
                        >
                            Índice de precios relativos
                        </button>
                        <button
                            onClick={() => onPageChange('cotizaciones')}
                            className={`px-4 py-2 rounded-lg font-medium transition-all ${
                                currentPage === 'cotizaciones'
                                    ? 'bg-indigo-600 text-white'
                                    : 'text-gray-700 hover:bg-gray-100'
                            }`}
                        >
                            Cotizaciones de monedas
                        </button>
                        <button
                            onClick={() => onPageChange('series')}
                            className={`px-4 py-2 rounded-lg font-medium transition-all ${
                                currentPage === 'series'
                                    ? 'bg-indigo-600 text-white'
                                    : 'text-gray-700 hover:bg-gray-100'
                            }`}
                        >
                            Precios Corrientes
                        </button>
                    </div>
                </div>
            </div>
        </nav>
    );
}

// App Principal
function App() {
    const [currentPage, setCurrentPage] = useState('dcp');

    return (
        <div className="min-h-screen bg-gray-50">
            <Navigation currentPage={currentPage} onPageChange={setCurrentPage} />
            {currentPage === 'dcp' && <DCPPage />}
            {currentPage === 'cotizaciones' && <CotizacionesLATAMPage />}
            {currentPage === 'series' && <TimeSeriesPage />}
        </div>
    );
}

// Renderizar la app
ReactDOM.render(<App />, document.getElementById('root'));
