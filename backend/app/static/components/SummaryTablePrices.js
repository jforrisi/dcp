// Componente de Tabla Resumen para Precios de Exportación
function SummaryTablePrices({ data, fechaDesde, fechaHasta }) {
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
        .filter(product => product.summary && product.summary.precio_inicial !== null)
        .map(product => ({
            nombre: product.product_name,
            intervalo: formatIntervalo(product.summary.fecha_inicial, product.summary.fecha_final),
            precioInicial: product.summary.precio_inicial,
            precioFinal: product.summary.precio_final,
            variacionNominal: product.summary.variacion_nominal || 0.0
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
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Resumen de Precios</h3>
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th 
                                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('nombre')}
                            >
                                Nombre <SortIcon columnKey="nombre" />
                            </th>
                            <th 
                                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('intervalo')}
                            >
                                Intervalo <SortIcon columnKey="intervalo" />
                            </th>
                            <th 
                                className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('precioInicial')}
                            >
                                Precio Inicial <SortIcon columnKey="precioInicial" />
                            </th>
                            <th 
                                className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('precioFinal')}
                            >
                                Precio Final <SortIcon columnKey="precioFinal" />
                            </th>
                            <th 
                                className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('variacionNominal')}
                            >
                                Var. Nominal (%) <SortIcon columnKey="variacionNominal" />
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {sortedData.map((row, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{row.nombre}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{row.intervalo}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">{row.precioInicial.toFixed(2)}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">{row.precioFinal.toFixed(2)}</td>
                                <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${row.variacionNominal >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {row.variacionNominal >= 0 ? '+' : ''}{row.variacionNominal.toFixed(2)}%
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
