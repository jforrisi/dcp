// Form component for Familia
function FamiliaForm({ initialData, onSubmit, onCancel }) {
    const [formData, setFormData] = React.useState({
        nombre_familia: initialData?.nombre_familia || '',
    });
    const [errors, setErrors] = React.useState({});

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: null }));
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        
        const newErrors = {};
        if (!formData.nombre_familia.trim()) {
            newErrors.nombre_familia = 'El nombre es requerido';
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
                    Nombre de Familia *
                </label>
                <input
                    type="text"
                    name="nombre_familia"
                    value={formData.nombre_familia}
                    onChange={handleChange}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                        errors.nombre_familia ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="Ej: Financiero, Precio Internacional"
                />
                {errors.nombre_familia && (
                    <p className="mt-1 text-sm text-red-600">{errors.nombre_familia}</p>
                )}
            </div>

            <div className="flex justify-end gap-3 pt-4">
                <button
                    type="button"
                    onClick={onCancel}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                    Cancelar
                </button>
                <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                    {initialData ? 'Actualizar' : 'Crear'}
                </button>
            </div>
        </form>
    );
}
