// Form component for Filtros (special - manages multiple countries per graph)
function FiltrosForm({ initialData, onSubmit, onCancel }) {
    const [selectedGraph, setSelectedGraph] = React.useState(initialData?.id_graph || null);
    const [selectedPaises, setSelectedPaises] = React.useState(new Set(initialData?.pais_ids || []));
    const [graphs, setGraphs] = React.useState([]);
    const [paises, setPaises] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);

    React.useEffect(() => {
        Promise.all([
            AdminAPI.getGraphs(),
            AdminAPI.getPaises()
        ])
            .then(([graphsData, paisesData]) => {
                setGraphs(graphsData);
                setPaises(paisesData);
                setLoading(false);
            })
            .catch(err => {
                alert('Error al cargar datos: ' + err.message);
                setLoading(false);
            });
    }, []);

    React.useEffect(() => {
        if (selectedGraph) {
            AdminAPI.getGraphFiltros(selectedGraph)
                .then(filtros => {
                    const paisIds = filtros.map(f => f.id_pais);
                    setSelectedPaises(new Set(paisIds));
                })
                .catch(err => {
                    console.error('Error al cargar filtros:', err);
                });
        }
    }, [selectedGraph]);

    const handleGraphChange = (e) => {
        const graphId = e.target.value ? parseInt(e.target.value) : null;
        setSelectedGraph(graphId);
        setSelectedPaises(new Set());
    };

    const handlePaisToggle = (paisId) => {
        setSelectedPaises(prev => {
            const newSet = new Set(prev);
            if (newSet.has(paisId)) {
                newSet.delete(paisId);
            } else {
                newSet.add(paisId);
            }
            return newSet;
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!selectedGraph) {
            alert('Por favor selecciona un graph');
            return;
        }

        setSaving(true);
        try {
            const paisIds = Array.from(selectedPaises);
            await AdminAPI.updateFiltrosBulk({
                id_graph: selectedGraph,
                pais_ids: paisIds
            });
            alert('Filtros guardados correctamente');
            if (onSubmit) {
                onSubmit({ id_graph: selectedGraph, pais_ids: paisIds });
            }
        } catch (err) {
            alert('Error al guardar filtros: ' + err.message);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <div className="text-center py-8 text-gray-500">Cargando...</div>;
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Graph *
                </label>
                <select
                    value={selectedGraph || ''}
                    onChange={handleGraphChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                >
                    <option value="">Seleccionar graph</option>
                    {graphs.map(g => (
                        <option key={g.id_graph} value={g.id_graph}>
                            {g.nombre_graph}
                        </option>
                    ))}
                </select>
            </div>

            {selectedGraph && (
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Países ({selectedPaises.size} seleccionados)
                    </label>
                    <div className="border border-gray-300 rounded-lg p-4 max-h-96 overflow-y-auto">
                        <div className="grid grid-cols-2 gap-2">
                            {paises.map(pais => (
                                <label key={pais.id_pais} className="flex items-center cursor-pointer hover:bg-gray-50 p-2 rounded">
                                    <input
                                        type="checkbox"
                                        checked={selectedPaises.has(pais.id_pais)}
                                        onChange={() => handlePaisToggle(pais.id_pais)}
                                        className="mr-2"
                                    />
                                    <span>{pais.nombre_pais_grupo}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            <div className="flex justify-end gap-3 pt-4">
                <button
                    type="button"
                    onClick={onCancel}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                    disabled={saving}
                >
                    Cancelar
                </button>
                <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                    disabled={saving || !selectedGraph}
                >
                    {saving ? 'Guardando...' : 'Guardar Filtros'}
                </button>
            </div>
        </form>
    );
}
