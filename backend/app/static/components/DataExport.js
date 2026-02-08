// Componente de Exportación de Datos - Sección (no modal)
function DataExport() {
    const [families, setFamilies] = React.useState([]);
    const [subfamilies, setSubfamilies] = React.useState([]);
    const [variables, setVariables] = React.useState([]); // Siempre inicializar como array
    const [countries, setCountries] = React.useState([]);
    const [previewData, setPreviewData] = React.useState([]);
    
    const [selectedFamily, setSelectedFamily] = React.useState(null);
    const [selectedSubfamilies, setSelectedSubfamilies] = React.useState([]);
    const [selectedVariables, setSelectedVariables] = React.useState([]);
    const [selectedCountries, setSelectedCountries] = React.useState([]);
    const [fechaDesde, setFechaDesde] = React.useState('');
    const [fechaHasta, setFechaHasta] = React.useState('');
    
    const [loading, setLoading] = React.useState(false);
    const [loadingPreview, setLoadingPreview] = React.useState(false);

    // Cargar familias
    React.useEffect(() => {
        fetch('/api/export/families')
            .then(res => res.json())
            .then(data => {
                // Asegurarse de que data sea un array
                if (Array.isArray(data)) {
                    setFamilies(data);
                } else {
                    console.error('Error: respuesta no es un array:', data);
                    setFamilies([]);
                }
            })
            .catch(err => {
                console.error('Error cargando familias:', err);
                setFamilies([]);
            });
    }, []);

    // Cargar todas las variables al inicio (sin necesidad de familia)
    React.useEffect(() => {
        fetch('/api/export/variables')
            .then(res => res.json())
            .then(data => {
                // Asegurarse de que data sea un array
                if (Array.isArray(data)) {
                    setVariables(data);
                } else {
                    console.error('Error: respuesta no es un array:', data);
                    setVariables([]);
                }
            })
            .catch(err => {
                console.error('Error cargando variables:', err);
                setVariables([]);
            });
    }, []);

    // Cargar subfamilias cuando se selecciona familia
    React.useEffect(() => {
        if (!selectedFamily) {
            setSubfamilies([]);
            return;
        }
        fetch(`/api/export/subfamilies?familia_id=${selectedFamily}`)
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data)) {
                    setSubfamilies(data);
                } else {
                    setSubfamilies([]);
                }
            })
            .catch(err => {
                console.error('Error cargando subfamilias:', err);
                setSubfamilies([]);
            });
    }, [selectedFamily]);

    // Cargar variables cuando se seleccionan subfamilias (opcional)
    React.useEffect(() => {
        if (selectedSubfamilies.length === 0) {
            // Si no hay subfamilias seleccionadas, recargar todas las variables
            fetch('/api/export/variables')
                .then(res => res.json())
                .then(data => {
                    if (Array.isArray(data)) {
                        setVariables(data);
                    } else {
                        setVariables([]);
                    }
                })
                .catch(err => {
                    console.error('Error cargando variables:', err);
                    setVariables([]);
                });
            return;
        }
        const params = selectedSubfamilies.map(id => `subfamilia_ids[]=${id}`).join('&');
        fetch(`/api/export/variables?${params}`)
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data)) {
                    setVariables(data);
                } else {
                    console.error('Error: respuesta no es un array:', data);
                    setVariables([]);
                }
            })
            .catch(err => {
                console.error('Error cargando variables:', err);
                setVariables([]);
            });
    }, [selectedSubfamilies]);

    // Cargar países cuando se seleccionan variables
    React.useEffect(() => {
        if (selectedVariables.length === 0) {
            setCountries([]);
            setSelectedCountries([]);
            return;
        }
        const params = selectedVariables.map(id => `variable_ids[]=${id}`).join('&');
        fetch(`/api/export/countries?${params}`)
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data)) {
                    setCountries(data);
                } else {
                    setCountries([]);
                }
            })
            .catch(err => {
                console.error('Error cargando países:', err);
                setCountries([]);
            });
    }, [selectedVariables]);

    const handleLoadPreview = async () => {
        if (selectedVariables.length === 0 || selectedCountries.length === 0) {
            alert('Seleccione variables y países');
            return;
        }
        
        setLoadingPreview(true);
        try {
            const params = new URLSearchParams();
            selectedVariables.forEach(id => params.append('variable_ids[]', id));
            selectedCountries.forEach(id => params.append('pais_ids[]', id));
            if (fechaDesde) params.append('fecha_desde', fechaDesde);
            if (fechaHasta) params.append('fecha_hasta', fechaHasta);
            
            const response = await fetch(`/api/export/preview?${params}`);
            const data = await response.json();
            // Asegurarse de que data sea un array
            if (Array.isArray(data)) {
                setPreviewData(data);
            } else {
                console.error('Error: preview no es un array:', data);
                setPreviewData([]);
            }
        } catch (error) {
            console.error('Error cargando preview:', error);
            setPreviewData([]);
            alert('Error al cargar preview');
        } finally {
            setLoadingPreview(false);
        }
    };

    const handleDownload = async () => {
        if (selectedVariables.length === 0 || selectedCountries.length === 0) {
            alert('Seleccione variables y países');
            return;
        }
        
        setLoading(true);
        try {
            const params = new URLSearchParams();
            selectedVariables.forEach(id => params.append('variable_ids[]', id));
            selectedCountries.forEach(id => params.append('pais_ids[]', id));
            if (fechaDesde) params.append('fecha_desde', fechaDesde);
            if (fechaHasta) params.append('fecha_hasta', fechaHasta);
            
            const response = await fetch(`/api/export/download?${params}`);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `exportacion_datos_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error descargando:', error);
            alert('Error al descargar archivo');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Descarga de Datos</h2>

            {/* Dos secciones arriba al medio */}
            <div className="grid grid-cols-2 gap-6 mb-6">
                {/* Izquierda: Familias/Subfamilia y Variables */}
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Familia
                        </label>
                        <select
                            value={selectedFamily || ''}
                            onChange={(e) => {
                                setSelectedFamily(e.target.value ? parseInt(e.target.value) : null);
                                setSelectedSubfamilies([]);
                            }}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md"
                        >
                            <option value="">Todas las familias</option>
                            {Array.isArray(families) && families.map(f => (
                                <option key={f.id_familia} value={f.id_familia}>
                                    {f.nombre_familia}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Selector de Subfamilias (múltiple) */}
                    {Array.isArray(subfamilies) && subfamilies.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Subfamilias (puede seleccionar varias)
                            </label>
                            <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-md p-2">
                                {subfamilies.map(sf => (
                                    <label key={sf.id_sub_familia} className="flex items-center space-x-2 py-1">
                                        <input
                                            type="checkbox"
                                            checked={selectedSubfamilies.includes(sf.id_sub_familia)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setSelectedSubfamilies([...selectedSubfamilies, sf.id_sub_familia]);
                                                } else {
                                                    setSelectedSubfamilies(selectedSubfamilies.filter(id => id !== sf.id_sub_familia));
                                                }
                                            }}
                                            className="rounded"
                                        />
                                        <span>{sf.nombre_sub_familia}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Selector de Variables (múltiple) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Variables (puede seleccionar varias)
                        </label>
                        <div className="max-h-60 overflow-y-auto border border-gray-300 rounded-md p-2">
                            {!Array.isArray(variables) || variables.length === 0 ? (
                                <p className="text-sm text-gray-500">Cargando variables...</p>
                            ) : (
                                variables.map(v => (
                                    <label key={v.id_variable} className="flex items-center space-x-2 py-1">
                                        <input
                                            type="checkbox"
                                            checked={selectedVariables.includes(v.id_variable)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setSelectedVariables([...selectedVariables, v.id_variable]);
                                                } else {
                                                    setSelectedVariables(selectedVariables.filter(id => id !== v.id_variable));
                                                }
                                            }}
                                            className="rounded"
                                        />
                                        <span className="text-sm">{v.nombre}</span>
                                    </label>
                                ))
                            )}
                        </div>
                    </div>
                </div>

                {/* Derecha: Países */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Países (puede seleccionar varios)
                    </label>
                    {!Array.isArray(countries) || countries.length === 0 ? (
                        <div className="border border-gray-300 rounded-md p-4 text-center">
                            <p className="text-sm text-gray-500">
                                {selectedVariables.length === 0 
                                    ? 'Seleccione variables primero' 
                                    : 'Cargando países...'}
                            </p>
                        </div>
                    ) : (
                        <div className="max-h-96 overflow-y-auto border border-gray-300 rounded-md p-2">
                            {countries.map(c => (
                                <label key={c.id_pais} className="flex items-center space-x-2 py-1">
                                    <input
                                        type="checkbox"
                                        checked={selectedCountries.includes(c.id_pais)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setSelectedCountries([...selectedCountries, c.id_pais]);
                                            } else {
                                                setSelectedCountries(selectedCountries.filter(id => id !== c.id_pais));
                                            }
                                        }}
                                        className="rounded"
                                    />
                                    <span className="text-sm">{c.nombre_pais}</span>
                                </label>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Intervalo de fechas */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Fecha Desde
                    </label>
                    <input
                        type="date"
                        value={fechaDesde}
                        onChange={(e) => setFechaDesde(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Fecha Hasta
                    </label>
                    <input
                        type="date"
                        value={fechaHasta}
                        onChange={(e) => setFechaHasta(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                </div>
            </div>

            {/* Botón Cargar Datos */}
            <div className="mb-6">
                <button
                    onClick={handleLoadPreview}
                    disabled={loadingPreview || selectedVariables.length === 0 || selectedCountries.length === 0}
                    className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                    {loadingPreview ? 'Cargando...' : 'Cargar Datos'}
                </button>
            </div>

            {/* Tabla Preview - Formato Pivotado */}
            {previewData.length > 0 && (
                <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-3">Últimas 10 filas</h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 border border-gray-300">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border border-gray-300">
                                        Variable
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border border-gray-300">
                                        País
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border border-gray-300">
                                        Fecha
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border border-gray-300">
                                        Valor
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {previewData.map((row, rowIdx) => (
                                    <tr key={rowIdx} className="hover:bg-gray-50">
                                        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border border-gray-300">
                                            {row.variable || '-'}
                                        </td>
                                        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border border-gray-300">
                                            {row.pais || '-'}
                                        </td>
                                        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border border-gray-300">
                                            {row.fecha || '-'}
                                        </td>
                                        <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900 border border-gray-300">
                                            {row.valor !== null && row.valor !== undefined 
                                                ? typeof row.valor === 'number' 
                                                    ? row.valor.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                                    : row.valor
                                                : '-'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Botón Descargar Datos */}
            <button
                onClick={handleDownload}
                disabled={loading || selectedVariables.length === 0 || selectedCountries.length === 0 || previewData.length === 0}
                className="w-full bg-green-600 text-white py-3 px-4 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
            >
                {loading ? 'Descargando...' : 'Descargar Datos'}
            </button>
        </div>
    );
}
