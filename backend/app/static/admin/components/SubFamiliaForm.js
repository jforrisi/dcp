// Form component for SubFamilia
function SubFamiliaForm({ initialData, onSubmit, onCancel }) {
    const [formData, setFormData] = React.useState({
        nombre_sub_familia: initialData?.nombre_sub_familia || '',
        id_familia: initialData?.id_familia || null,
    });
    const [familias, setFamilias] = React.useState([]);
    const [errors, setErrors] = React.useState({});
    const [loading, setLoading] = React.useState(true);
    const [loadError, setLoadError] = React.useState(null);

    React.useEffect(() => {
        setLoadError(null);
        AdminAPI.getFamilias()
            .then(data => {
                // Validar que sea un array
                const familiasArray = Array.isArray(data) ? data : [];
                console.log('[SubFamiliaForm] Familias cargadas:', familiasArray.length);
                setFamilias(familiasArray);
                setLoading(false);
            })
            .catch(err => {
                console.error('[SubFamiliaForm] Error al cargar familias:', err);
                const errorMessage = err.message || 'Error desconocido al cargar familias';
                setLoadError(errorMessage);
                setFamilias([]);
                setLoading(false);
                alert(`Error al cargar familias: ${errorMessage}\n\nPor favor, verifica la consola para más detalles.`);
            });
    }, []);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: name === 'id_familia' ? (value ? parseInt(value) : null) : value }));
        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: null }));
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        
        const newErrors = {};
        if (!formData.nombre_sub_familia.trim()) {
            newErrors.nombre_sub_familia = 'El nombre es requerido';
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
                    Nombre de Sub-Familia *
                </label>
                <input
                    type="text"
                    name="nombre_sub_familia"
                    value={formData.nombre_sub_familia}
                    onChange={handleChange}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 ${
                        errors.nombre_sub_familia ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="Ej: Materias primas, Precio de exportación"
                />
                {errors.nombre_sub_familia && (
                    <p className="mt-1 text-sm text-red-600">{errors.nombre_sub_familia}</p>
                )}
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Familia
                </label>
                {loading ? (
                    <div className="text-sm text-gray-500">Cargando familias...</div>
                ) : loadError ? (
                    <div className="text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200">
                        Error: {loadError}
                    </div>
                ) : (
                    <select
                        name="id_familia"
                        value={formData.id_familia || ''}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">Sin familia</option>
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
