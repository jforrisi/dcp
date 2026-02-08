// Generic CRUD Table Component
function CRUDTable({ 
    title, 
    columns, 
    data, 
    loading, 
    error,
    onCreate, 
    onUpdate, 
    onDelete,
    FormComponent,
    getRowKey = (row, index) => row.id || index,
    actionsFirst = false,
    filters = null,
    pagination = null,
    onPageChange = null
}) {
    const [isModalOpen, setIsModalOpen] = React.useState(false);
    const [editingItem, setEditingItem] = React.useState(null);
    const [deleteConfirm, setDeleteConfirm] = React.useState(null);

    const handleCreate = () => {
        setEditingItem(null);
        setIsModalOpen(true);
    };

    const handleEdit = (item) => {
        setEditingItem(item);
        setIsModalOpen(true);
    };

    const handleDelete = (item) => {
        setDeleteConfirm(item);
    };

    const confirmDelete = async () => {
        if (deleteConfirm && onDelete) {
            try {
                await onDelete(deleteConfirm);
                setDeleteConfirm(null);
            } catch (err) {
                alert('Error al eliminar: ' + err.message);
            }
        }
    };

    const handleSubmit = async (formData) => {
        try {
            if (editingItem) {
                // Use getRowKey to get the ID, which handles different ID field names (id, id_variable, etc.)
                const itemId = getRowKey(editingItem, 0);
                // Para maestro, itemId es una string como "id_variable_id_pais", necesitamos parsearlo
                if (typeof itemId === 'string' && itemId.includes('_') && editingItem.id_variable && editingItem.id_pais) {
                    // Es maestro con clave compuesta
                    await onUpdate({ id_variable: editingItem.id_variable, id_pais: editingItem.id_pais }, formData);
                } else {
                    await onUpdate(itemId, formData);
                }
            } else {
                await onCreate(formData);
            }
            setIsModalOpen(false);
            setEditingItem(null);
        } catch (err) {
            alert('Error al guardar: ' + err.message);
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
                <button
                    onClick={handleCreate}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                    + Crear Nuevo
                </button>
            </div>

            {/* Filtros */}
            {filters && (
                <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                    {filters()}
                </div>
            )}

            {error && (
                <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="text-center py-8 text-gray-500">Cargando...</div>
            ) : (
                <>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                {actionsFirst && (
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Acciones
                                    </th>
                                )}
                                {columns.map((col, idx) => (
                                    <th
                                        key={idx}
                                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                                    >
                                        {col.label}
                                    </th>
                                ))}
                                {!actionsFirst && (
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Acciones
                                    </th>
                                )}
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {data.length === 0 ? (
                                <tr>
                                    <td colSpan={columns.length + 1} className="px-6 py-4 text-center text-gray-500">
                                        No hay datos
                                    </td>
                                </tr>
                            ) : (
                                data.map((row, index) => (
                                    <tr key={getRowKey(row, index)} className="hover:bg-gray-50">
                                        {actionsFirst && (
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <button
                                                    onClick={() => handleEdit(row)}
                                                    className="text-indigo-600 hover:text-indigo-900 mr-3"
                                                >
                                                    Editar
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(row)}
                                                    className="text-red-600 hover:text-red-900"
                                                >
                                                    Eliminar
                                                </button>
                                            </td>
                                        )}
                                        {columns.map((col, colIdx) => (
                                            <td key={colIdx} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {col.render ? col.render(row[col.key], row) : row[col.key]}
                                            </td>
                                        ))}
                                        {!actionsFirst && (
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <button
                                                    onClick={() => handleEdit(row)}
                                                    className="text-indigo-600 hover:text-indigo-900 mr-3"
                                                >
                                                    Editar
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(row)}
                                                    className="text-red-600 hover:text-red-900"
                                                >
                                                    Eliminar
                                                </button>
                                            </td>
                                        )}
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
                
                {/* Paginación */}
                {pagination && pagination.pages > 1 && (
                    <div className="mt-4 flex items-center justify-between">
                        <div className="text-sm text-gray-700">
                            Mostrando {((pagination.page - 1) * pagination.per_page) + 1} a {Math.min(pagination.page * pagination.per_page, pagination.total)} de {pagination.total} resultados
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => onPageChange && onPageChange(pagination.page - 1)}
                                disabled={pagination.page === 1}
                                className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                            >
                                Anterior
                            </button>
                            <span className="px-3 py-1 text-sm text-gray-700">
                                Página {pagination.page} de {pagination.pages}
                            </span>
                            <button
                                onClick={() => onPageChange && onPageChange(pagination.page + 1)}
                                disabled={pagination.page >= pagination.pages}
                                className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                            >
                                Siguiente
                            </button>
                        </div>
                    </div>
                )}
                </>
            )}

            {/* Modal para crear/editar */}
            {isModalOpen && FormComponent && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-xl font-bold">
                                {editingItem ? 'Editar' : 'Crear Nuevo'}
                            </h3>
                            <button
                                onClick={() => {
                                    setIsModalOpen(false);
                                    setEditingItem(null);
                                }}
                                className="text-gray-500 hover:text-gray-700"
                            >
                                ✕
                            </button>
                        </div>
                        <FormComponent
                            initialData={editingItem}
                            onSubmit={handleSubmit}
                            onCancel={() => {
                                setIsModalOpen(false);
                                setEditingItem(null);
                            }}
                        />
                    </div>
                </div>
            )}

            {/* Modal de confirmación de eliminación */}
            {deleteConfirm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-md w-full">
                        <h3 className="text-xl font-bold mb-4">Confirmar Eliminación</h3>
                        <p className="mb-4">
                            ¿Estás seguro de que deseas eliminar este registro?
                        </p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setDeleteConfirm(null)}
                                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={confirmDelete}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                            >
                                Eliminar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
