// Form component for Maestro
function MaestroForm({ initialData, onSubmit, onCancel }) {
    const [formData, setFormData] = React.useState({
        fuente: initialData?.fuente || '',
        periodicidad: initialData?.periodicidad || '',
        unidad: initialData?.unidad || '',
        activo: initialData?.activo !== undefined ? initialData.activo : true,
        observaciones: initialData?.pais || initialData?.observaciones || '', // Mapear desde 'pais' del backend
        id_variable: initialData?.id_variable || null,
        id_pais: initialData?.id_pais || null,
        link: initialData?.link || '',
        script_update: initialData?.script_update || '',
    });
    const [variables, setVariables] = React.useState([]);
    const [paises, setPaises] = React.useState([]);
    const [errors, setErrors] = React.useState({});
    const [loading, setLoading] = React.useState(true);
    
    // Estado para el selector de país
    const [isPaisOpen, setIsPaisOpen] = React.useState(false);
    const [paisSearchTerm, setPaisSearchTerm] = React.useState('');
    const paisDropdownRef = React.useRef(null);
    const paisInputRef = React.useRef(null);
    
    // Estado para modo múltiple de países
    const [multiPaisMode, setMultiPaisMode] = React.useState(false);
    const [selectedPaises, setSelectedPaises] = React.useState([]);
    const [paisMultiSearchTerm, setPaisMultiSearchTerm] = React.useState('');

    React.useEffect(() => {
        Promise.all([
            AdminAPI.getVariables(),
            AdminAPI.getPaises()
        ])
            .then(([vars, paisesData]) => {
                setVariables(vars);
                setPaises(paisesData);
                setLoading(false);
            })
            .catch(err => {
                alert('Error al cargar datos: ' + err.message);
                setLoading(false);
            });
    }, []);

    // Cerrar dropdown de país al hacer click fuera
    React.useEffect(() => {
        if (!isPaisOpen) return;

        const handleClickOutside = (event) => {
            if (paisDropdownRef.current && !paisDropdownRef.current.contains(event.target)) {
                setIsPaisOpen(false);
            }
        };

        const timeoutId = setTimeout(() => {
            if (paisInputRef.current) {
                try {
                    paisInputRef.current.focus();
                } catch (e) {}
            }
        }, 50);

        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('touchstart', handleClickOutside);
        window.addEventListener('click', handleClickOutside, true);

        return () => {
            clearTimeout(timeoutId);
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('touchstart', handleClickOutside);
            window.removeEventListener('click', handleClickOutside, true);
        };
    }, [isPaisOpen]);

    const filteredPaises = paises.filter(p => {
        const searchText = (p.nombre_pais_grupo || '').toLowerCase();
        return searchText.includes(paisSearchTerm.toLowerCase());
    });

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : (name === 'id_variable') 
                ? (value ? parseInt(value) : null) : value
        }));
        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: null }));
        }
    };

    const handlePaisSelect = (paisId) => {
        setFormData(prev => ({ ...prev, id_pais: paisId }));
        setIsPaisOpen(false);
        setPaisSearchTerm('');
    };

    const handleMultiPaisToggle = (paisId) => {
        setSelectedPaises(prev => {
            if (prev.includes(paisId)) {
                return prev.filter(id => id !== paisId);
            } else {
                return [...prev, paisId];
            }
        });
    };

    const filteredPaisesMulti = paises.filter(p => {
        const searchText = (p.nombre_pais_grupo || '').toLowerCase();
        return searchText.includes(paisMultiSearchTerm.toLowerCase());
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        
        const newErrors = {};
        if (!formData.periodicidad || !formData.periodicidad.trim()) {
            newErrors.periodicidad = 'La periodicidad es obligatoria';
        } else if (!['D', 'W', 'M'].includes(formData.periodicidad.toUpperCase())) {
            newErrors.periodicidad = 'Debe ser D, W o M';
        }
        
        if (multiPaisMode) {
            if (selectedPaises.length === 0) {
                newErrors.paises = 'Debe seleccionar al menos un país';
            }
        } else {
            if (!formData.id_pais) {
                newErrors.id_pais = 'Debe seleccionar un país';
            }
        }
        
        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }
        
        onSubmit(formData);
    };

    const handleSubmitBulk = (e) => {
        e.preventDefault();
        
        const newErrors = {};
        if (!formData.periodicidad || !formData.periodicidad.trim()) {
            newErrors.periodicidad = 'La periodicidad es obligatoria';
        } else if (!['D', 'W', 'M'].includes(formData.periodicidad.toUpperCase())) {
            newErrors.periodicidad = 'Debe ser D, W o M';
        }
        
        if (!formData.id_variable) {
            newErrors.id_variable = 'Debe seleccionar una variable';
        }
        
        if (selectedPaises.length === 0) {
            newErrors.paises = 'Debe seleccionar al menos un país';
        }
        
        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }
        
        // Preparar datos para creación múltiple
        const bulkData = {
            ...formData,
            id_paises: selectedPaises
        };
        onSubmit(bulkData);
    };

    const selectedPais = paises.find(p => p.id_pais === formData.id_pais);

    return (
        <form onSubmit={handleSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
                {/* Variable - Primero */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Variable *
                    </label>
                    {loading ? (
                        <div className="text-sm text-gray-500">Cargando...</div>
                    ) : (
                        <select
                            name="id_variable"
                            value={formData.id_variable || ''}
                            onChange={handleChange}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                            required
                        >
                            <option value="">Seleccionar variable</option>
                            {variables.map(v => (
                                <option key={v.id_variable} value={v.id_variable}>
                                    {v.id_nombre_variable}
                                </option>
                            ))}
                        </select>
                    )}
                </div>

                {/* País (FK) - Segundo, con buscador */}
                <div>
                    <div className="flex items-center justify-between mb-1">
                        <label className="block text-sm font-medium text-gray-700">
                            País *
                        </label>
                        {!initialData && (
                            <label className="flex items-center text-sm text-gray-600 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={multiPaisMode}
                                    onChange={(e) => {
                                        setMultiPaisMode(e.target.checked);
                                        if (!e.target.checked) {
                                            setSelectedPaises([]);
                                            setFormData(prev => ({ ...prev, id_pais: null }));
                                        }
                                    }}
                                    className="mr-1"
                                />
                                Múltiples países
                            </label>
                        )}
                    </div>
                    {loading ? (
                        <div className="text-sm text-gray-500">Cargando...</div>
                    ) : multiPaisMode ? (
                        <div className="border border-gray-300 rounded-lg p-3 max-h-64 overflow-y-auto">
                            <input
                                type="text"
                                placeholder="Buscar países..."
                                value={paisMultiSearchTerm}
                                onChange={(e) => setPaisMultiSearchTerm(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none mb-3"
                            />
                            <div className="space-y-2">
                                {filteredPaisesMulti.length === 0 ? (
                                    <div className="text-center text-gray-500 text-sm py-2">
                                        No se encontraron países
                                    </div>
                                ) : (
                                    filteredPaisesMulti.map((pais) => (
                                        <label key={pais.id_pais} className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={selectedPaises.includes(pais.id_pais)}
                                                onChange={() => handleMultiPaisToggle(pais.id_pais)}
                                                className="mr-2"
                                            />
                                            <span className="text-sm text-gray-900">{pais.nombre_pais_grupo}</span>
                                        </label>
                                    ))
                                )}
                            </div>
                            {selectedPaises.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-gray-200">
                                    <div className="text-xs text-gray-500 mb-1">
                                        Seleccionados: {selectedPaises.length}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="relative" ref={paisDropdownRef}>
                            <div
                                onClick={() => setIsPaisOpen(!isPaisOpen)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 cursor-pointer flex items-center justify-between bg-white"
                                role="button"
                                tabIndex={0}
                            >
                                <span className={selectedPais ? 'text-gray-900' : 'text-gray-500'}>
                                    {selectedPais ? selectedPais.nombre_pais_grupo : 'Seleccionar país...'}
                                </span>
                                <svg className={`w-5 h-5 text-gray-400 transition-transform ${isPaisOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </div>

                            {isPaisOpen && (
                                <div 
                                    className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-hidden"
                                    style={{ zIndex: 9999 }}
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    <div className="p-3 border-b border-gray-200">
                                        <input
                                            ref={paisInputRef}
                                            type="text"
                                            placeholder="Buscar país..."
                                            value={paisSearchTerm}
                                            onChange={(e) => {
                                                e.stopPropagation();
                                                setPaisSearchTerm(e.target.value);
                                            }}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                                            onClick={(e) => e.stopPropagation()}
                                            autoFocus={true}
                                        />
                                    </div>
                                    <div className="overflow-y-auto max-h-80">
                                        {filteredPaises.length === 0 ? (
                                            <div className="p-3 text-center text-gray-500 text-sm">
                                                No se encontraron países
                                            </div>
                                        ) : (
                                            filteredPaises.map((pais) => (
                                                <div
                                                    key={pais.id_pais}
                                                    onClick={() => handlePaisSelect(pais.id_pais)}
                                                    className="p-3 hover:bg-gray-50 active:bg-gray-100 cursor-pointer border-b border-gray-100 last:border-b-0"
                                                >
                                                    <div className="text-sm font-medium text-gray-900">
                                                        {pais.nombre_pais_grupo}
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                    {errors.id_pais && <p className="mt-1 text-sm text-red-600">{errors.id_pais}</p>}
                    {errors.paises && <p className="mt-1 text-sm text-red-600">{errors.paises}</p>}
                </div>

                {/* Periodicidad - Obligatoria */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Periodicidad *
                    </label>
                    <select
                        name="periodicidad"
                        value={formData.periodicidad}
                        onChange={handleChange}
                        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 ${
                            errors.periodicidad ? 'border-red-500' : 'border-gray-300'
                        }`}
                        required
                    >
                        <option value="">Seleccionar</option>
                        <option value="D">Diario (D)</option>
                        <option value="W">Semanal (W)</option>
                        <option value="M">Mensual (M)</option>
                    </select>
                    {errors.periodicidad && <p className="mt-1 text-sm text-red-600">{errors.periodicidad}</p>}
                </div>

                {/* Fuente */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Fuente
                    </label>
                    <input
                        type="text"
                        name="fuente"
                        value={formData.fuente}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                </div>

                {/* Unidad - No obligatorio */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Unidad
                    </label>
                    <input
                        type="text"
                        name="unidad"
                        value={formData.unidad}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                </div>

                {/* Observaciones (antes "País texto libre") */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Observaciones
                    </label>
                    <input
                        type="text"
                        name="observaciones"
                        value={formData.observaciones}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                        placeholder="Notas adicionales..."
                    />
                </div>

                {/* Link */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Link
                    </label>
                    <input
                        type="text"
                        name="link"
                        value={formData.link}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                </div>

                {/* Script de Actualización */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Script de Actualización
                    </label>
                    <input
                        type="text"
                        name="script_update"
                        value={formData.script_update}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                        placeholder="ej: 001_carne_exportacion.py"
                    />
                    <small className="text-xs text-gray-500 mt-1 block">
                        Nombre del script en update/direct/ o update/calculate/
                    </small>
                </div>
            </div>

            <div className="flex gap-4">
                <label className="flex items-center">
                    <input
                        type="checkbox"
                        name="activo"
                        checked={formData.activo}
                        onChange={handleChange}
                        className="mr-2"
                    />
                    Activo
                </label>
            </div>

            <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                    Cancelar
                </button>
                {!initialData && multiPaisMode ? (
                    <button 
                        type="button" 
                        onClick={handleSubmitBulk} 
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                        Crear para múltiples países ({selectedPaises.length})
                    </button>
                ) : (
                    <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
                        {initialData ? 'Actualizar' : 'Crear'}
                    </button>
                )}
            </div>
        </form>
    );
}
