// Componente de Tabla Resumen para DCP
function SummaryTableDCP({ data, fechaDesde, fechaHasta }) {
    const [sortConfig, setSortConfig] = React.useState({ key: null, direction: 'asc' });
    
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

    // Preparar datos para la tabla
    const tableData = data
        .filter(product => {
            const hasSummary = product.summary !== null && product.summary !== undefined;
            const hasPrecioInicial = hasSummary && product.summary.precio_inicial !== null && product.summary.precio_inicial !== undefined;
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
