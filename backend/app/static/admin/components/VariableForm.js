// Form component for Variable
function VariableForm({ initialData, onSubmit, onCancel }) {
    const [formData, setFormData] = React.useState({
        id_nombre_variable: initialData?.id_nombre_variable || '',
        id_familia: initialData?.id_familia || null,
        id_sub_familia: initialData?.id_sub_familia || null,
        nominal_o_real: initialData?.nominal_o_real || '',
        moneda: initialData?.moneda || '',
        id_tipo_serie: initialData?.id_tipo_serie || 1,
    });
    const [familias, setFamilias] = React.useState([]);
    const [subFamilias, setSubFamilias] = React.useState([]);
    const [errors, setErrors] = React.useState({});
    const [loading, setLoading] = React.useState(true);
    const [familiaError, setFamiliaError] = React.useState(null);

    // Cargar familias al inicio
    React.useEffect(() => {
        setFamiliaError(null);
        
        // Cargar familias
        AdminAPI.getFamilias()
            .then(familiasData => {
                const familiasArray = Array.isArray(familiasData) ? familiasData : [];
                console.log('[VariableForm] Familias cargadas:', familiasArray.length);
                setFamilias(familiasArray);
            })
            .catch(err => {
                console.error('[VariableForm] Error al cargar familias:', err);
                const errorMessage = err.message || 'Error desconocido al cargar familias';
                setFamiliaError(errorMessage);
                setFamilias([]);
            })
            .finally(() => {
                setLoading(false);
            });
    }, []);

    // Si hay initialData con id_sub_familia, obtener la familia de esa sub-familia
    React.useEffect(() => {
        if (initialData?.id_sub_familia && !formData.id_familia) {
            AdminAPI.getSubFamilia(initialData.id_sub_familia)
                .then(data => {
                    if (data && data.id_familia) {
                        setFormData(prev => ({ ...prev, id_familia: data.id_familia }));
                        // Cargar sub-familias de esa familia
                        AdminAPI.getSubFamilias(data.id_familia)
                            .then(subFams => {
                                setSubFamilias(subFams);
                            })
                            .catch(err => {
                                console.error('Error al cargar sub-familias:', err);
                            });
                    }
                })
                .catch(err => {
                    console.error('Error al obtener sub-familia:', err);
                });
        }
    }, [initialData?.id_sub_familia]);

    // Cargar sub-familias cuando cambia la familia
    React.useEffect(() => {
        if (formData.id_familia) {
            AdminAPI.getSubFamilias(formData.id_familia)
                .then(data => {
                    setSubFamilias(data);
                })
                .catch(err => {
                    alert('Error al cargar sub-familias: ' + err.message);
                });
        } else {
            setSubFamilias([]);
        }
    }, [formData.id_familia]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        const newFormData = { ...formData };
        
        if (name === 'id_familia') {
            // Si cambia la familia, limpiar la sub-familia seleccionada
            newFormData.id_familia = value ? parseInt(value) : null;
            newFormData.id_sub_familia = null;
        } else if (name === 'id_sub_familia') {
            newFormData.id_sub_familia = value ? parseInt(value) : null;
        } else if (name === 'id_tipo_serie') {
            newFormData.id_tipo_serie = value ? parseInt(value) : 1;
        } else {
            newFormData[name] = value;
        }
        
        setFormData(newFormData);
        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: null }));
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        
        const newErrors = {};
        if (!formData.id_nombre_variable.trim()) {
            newErrors.id_nombre_variable = 'El nombre es requerido';
        }
        if (formData.nominal_o_real && !['n', 'r'].includes(formData.nominal_o_real.toLowerCase())) {
            newErrors.nominal_o_real = 'Debe ser "n" o "r"';
        }
        
        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }
        
        onSubmit(formData);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombre de Variable *
                </label>
                <input
                    type="text"
                    name="id_nombre_variable"
                    value={formData.id_nombre_variable}
                    onChange={handleChange}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 ${
                        errors.id_nombre_variable ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="Ej: Arroz, Servicios de arquitectura"
                />
                {errors.id_nombre_variable && (
                    <p className="mt-1 text-sm text-red-600">{errors.id_nombre_variable}</p>
                )}
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Familia
                </label>
                {loading && !familias.length ? (
                    <div className="text-sm text-gray-500">Cargando familias...</div>
                ) : familiaError ? (
                    <div className="text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200">
                        Error: {familiaError}
                    </div>
                ) : (
                    <select
                        name="id_familia"
                        value={formData.id_familia || ''}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">Seleccionar familia</option>
                        {Array.isArray(familias) && familias.length > 0 ? (
                            familias.map(f => (
                                <option key={f.id_familia} value={f.id_familia}>
                                    {f.nombre_familia}
                                </option>
                            ))
                        ) : (
                            <option value="" disabled>No hay familias disponibles</option>
                        )}
                    </select>
                )}
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sub-Familia
                </label>
                {!formData.id_familia ? (
                    <select
                        disabled
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-500"
                    >
                        <option value="">Primero seleccione una familia</option>
                    </select>
                ) : (
                    <select
                        name="id_sub_familia"
                        value={formData.id_sub_familia || ''}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">Sin sub-familia</option>
                        {Array.isArray(subFamilias) && subFamilias.length > 0 ? (
                            subFamilias.map(sf => (
                                <option key={sf.id_sub_familia} value={sf.id_sub_familia}>
                                    {sf.nombre_sub_familia}
                                </option>
                            ))
                        ) : (
                            <option value="" disabled>No hay sub-familias disponibles</option>
                        )}
                    </select>
                )}
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nominal o Real
                </label>
                <div className="flex gap-4">
                    <label className="flex items-center">
                        <input
                            type="radio"
                            name="nominal_o_real"
                            value="n"
                            checked={formData.nominal_o_real === 'n'}
                            onChange={handleChange}
                            className="mr-2"
                        />
                        Nominal (n)
                    </label>
                    <label className="flex items-center">
                        <input
                            type="radio"
                            name="nominal_o_real"
                            value="r"
                            checked={formData.nominal_o_real === 'r'}
                            onChange={handleChange}
                            className="mr-2"
                        />
                        Real (r)
                    </label>
                    <label className="flex items-center">
                        <input
                            type="radio"
                            name="nominal_o_real"
                            value=""
                            checked={!formData.nominal_o_real}
                            onChange={handleChange}
                            className="mr-2"
                        />
                        Ninguno
                    </label>
                </div>
                {errors.nominal_o_real && (
                    <p className="mt-1 text-sm text-red-600">{errors.nominal_o_real}</p>
                )}
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Moneda
                </label>
                <select
                    name="moneda"
                    value={formData.moneda || ''}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                >
                    <option value="">Sin moneda (será LC)</option>
                    <option value="LC">LC (Moneda Local)</option>
                    <option value="USD">USD (Dólar Estadounidense)</option>
                    <option value="EUR">EUR (Euro)</option>
                </select>
            </div>

            {/* Campo tipo_serie deshabilitado temporalmente - siempre usa valor por defecto 1 */}
            <input type="hidden" name="id_tipo_serie" value="1" />

            <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                    Cancelar
                </button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
                    {initialData ? 'Actualizar' : 'Crear'}
                </button>
            </div>
        </form>
    );
}
