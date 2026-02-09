// Main Admin App Component
function AdminApp() {
    const [loggedIn, setLoggedIn] = React.useState(null);
    const [activeTab, setActiveTab] = React.useState('familia');
    const [familiaData, setFamiliaData] = React.useState([]);
    const [subFamiliaData, setSubFamiliaData] = React.useState([]);
    const [variableData, setVariableData] = React.useState([]);
    const [maestroData, setMaestroData] = React.useState([]);
    const [graphData, setGraphData] = React.useState([]);
    const [paisData, setPaisData] = React.useState([]);
    const [filtrosData, setFiltrosData] = React.useState([]);
    
    // Estados para filtros y paginación de maestro
    const [maestroFilters, setMaestroFilters] = React.useState({
        variable_nombre: '',
        pais_nombre: ''
    });
    const [maestroPage, setMaestroPage] = React.useState(1);
    const [maestroPagination, setMaestroPagination] = React.useState(null);
    
    const [loading, setLoading] = React.useState({});
    const [errors, setErrors] = React.useState({});

    const loadData = async (tab) => {
        if (tab === 'actualizar') return;
        
        setLoading(prev => ({ ...prev, [tab]: true }));
        setErrors(prev => ({ ...prev, [tab]: null }));
        
        try {
            switch (tab) {
                case 'familia':
                    const familias = await AdminAPI.getFamilias();
                    setFamiliaData(familias);
                    break;
                case 'sub-familia':
                    const subFamilias = await AdminAPI.getSubFamilias();
                    setSubFamiliaData(subFamilias);
                    break;
                case 'variables':
                    const variables = await AdminAPI.getVariables();
                    setVariableData(variables);
                    break;
                case 'maestro':
                    const maestroResponse = await AdminAPI.getMaestro({
                        ...maestroFilters,
                        page: maestroPage,
                        per_page: 50
                    });
                    if (maestroResponse.data) {
                        setMaestroData(maestroResponse.data);
                        setMaestroPagination(maestroResponse.pagination);
                    } else {
                        // Compatibilidad con respuesta antigua
                        setMaestroData(maestroResponse);
                    }
                    break;
                case 'graph':
                    const graphs = await AdminAPI.getGraphs();
                    setGraphData(graphs);
                    break;
                case 'pais-grupo':
                    const paises = await AdminAPI.getPaises();
                    setPaisData(paises);
                    break;
                case 'filtros':
                    const filtros = await AdminAPI.getFiltros();
                    setFiltrosData(filtros);
                    break;
            }
        } catch (err) {
            setErrors(prev => ({ ...prev, [tab]: err.message }));
        } finally {
            setLoading(prev => ({ ...prev, [tab]: false }));
        }
    };

    React.useEffect(() => {
        loadData(activeTab);
    }, [activeTab]);

    // Verificar sesión al montar
    React.useEffect(() => {
        AdminAPI.checkSession()
            .then(() => setLoggedIn(true))
            .catch(() => setLoggedIn(false));
    }, []);

    const handleLogout = async () => {
        try {
            await AdminAPI.logout();
        } catch (e) {
            // Ignorar error de red
        } finally {
            AdminAPI.clearToken();
            setLoggedIn(false);
        }
    };

    if (loggedIn === null) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    if (!loggedIn) {
        return <AdminLogin onLoginSuccess={() => setLoggedIn(true)} />;
    }

    const handleCreate = async (tab, data) => {
        try {
            switch (tab) {
                case 'familia':
                    await AdminAPI.createFamilia(data);
                    break;
                case 'sub-familia':
                    await AdminAPI.createSubFamilia(data);
                    break;
                case 'variables':
                    await AdminAPI.createVariable(data);
                    break;
                case 'maestro':
                    // Si viene id_paises (array), usar creación múltiple
                    if (data.id_paises && Array.isArray(data.id_paises)) {
                        await AdminAPI.createMaestroBulk(data);
                    } else {
                        await AdminAPI.createMaestro(data);
                    }
                    break;
                case 'graph':
                    await AdminAPI.createGraph(data);
                    break;
                case 'pais-grupo':
                    await AdminAPI.createPais(data);
                    break;
            }
            await loadData(tab);
        } catch (err) {
            throw err;
        }
    };

    const handleUpdate = async (tab, id, data) => {
        try {
            switch (tab) {
                case 'familia':
                    await AdminAPI.updateFamilia(id, data);
                    break;
                case 'sub-familia':
                    await AdminAPI.updateSubFamilia(id, data);
                    break;
                case 'variables':
                    await AdminAPI.updateVariable(id, data);
                    break;
                case 'maestro':
                    // id es un objeto con id_variable e id_pais para maestro
                    if (typeof id === 'object' && id.id_variable && id.id_pais) {
                        await AdminAPI.updateMaestro(id.id_variable, id.id_pais, data);
                    } else {
                        throw new Error('ID inválido para maestro: debe ser {id_variable, id_pais}');
                    }
                    break;
                case 'graph':
                    await AdminAPI.updateGraph(id, data);
                    break;
                case 'pais-grupo':
                    await AdminAPI.updatePais(id, data);
                    break;
            }
            await loadData(tab);
        } catch (err) {
            throw err;
        }
    };

    const handleDelete = async (tab, item) => {
        try {
            const id = item.id || item.id_familia || item.id_sub_familia || item.id_variable || item.id_graph || item.id_pais;
            switch (tab) {
                case 'familia':
                    await AdminAPI.deleteFamilia(id);
                    break;
                case 'sub-familia':
                    await AdminAPI.deleteSubFamilia(id);
                    break;
                case 'variables':
                    await AdminAPI.deleteVariable(id);
                    break;
                case 'maestro':
                    // Para maestro, usar clave compuesta
                    if (item.id_variable && item.id_pais) {
                        await AdminAPI.deleteMaestro(item.id_variable, item.id_pais);
                    } else {
                        throw new Error('ID inválido para maestro: debe tener id_variable e id_pais');
                    }
                    break;
                case 'graph':
                    await AdminAPI.deleteGraph(id);
                    break;
                case 'pais-grupo':
                    await AdminAPI.deletePais(id);
                    break;
            }
            await loadData(tab);
        } catch (err) {
            throw err;
        }
    };

    const tabs = [
        { id: 'actualizar', label: 'Actualizar' },
        { id: 'familia', label: 'Familia' },
        { id: 'sub-familia', label: 'Sub-Familia' },
        { id: 'variables', label: 'Variables' },
        { id: 'maestro', label: 'Maestro' },
        { id: 'graph', label: 'Graph' },
        { id: 'pais-grupo', label: 'País Grupo' },
        { id: 'filtros', label: 'Filtros' },
    ];

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="bg-white shadow-sm border-b">
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex justify-between items-center mb-4">
                        <h1 className="text-2xl font-bold text-gray-900">Panel de Administración</h1>
                        <button
                            onClick={handleLogout}
                            className="text-sm text-gray-600 hover:text-gray-900 px-3 py-1 rounded hover:bg-gray-100"
                        >
                            Cerrar sesión
                        </button>
                    </div>
                    <div className="flex space-x-1 border-b">
                        {tabs.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`px-4 py-2 font-medium text-sm transition-colors ${
                                    activeTab === tab.id
                                        ? 'text-indigo-600 border-b-2 border-indigo-600'
                                        : 'text-gray-600 hover:text-gray-900'
                                }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 py-6">
                {activeTab === 'actualizar' && <UpdateTab />}

                {activeTab === 'familia' && (
                    <CRUDTable
                        title="Familias"
                        columns={[
                            { key: 'id_familia', label: 'ID' },
                            { key: 'nombre_familia', label: 'Nombre' },
                        ]}
                        data={familiaData}
                        loading={loading['familia']}
                        error={errors['familia']}
                        onCreate={(data) => handleCreate('familia', data)}
                        onUpdate={(id, data) => handleUpdate('familia', id, data)}
                        onDelete={(item) => handleDelete('familia', item)}
                        FormComponent={FamiliaForm}
                        getRowKey={(row) => row.id_familia}
                    />
                )}

                {activeTab === 'sub-familia' && (
                    <CRUDTable
                        title="Sub-Familias"
                        columns={[
                            { key: 'id_sub_familia', label: 'ID' },
                            { key: 'nombre_sub_familia', label: 'Nombre' },
                            { key: 'nombre_familia', label: 'Familia' },
                        ]}
                        data={subFamiliaData}
                        loading={loading['sub-familia']}
                        error={errors['sub-familia']}
                        onCreate={(data) => handleCreate('sub-familia', data)}
                        onUpdate={(id, data) => handleUpdate('sub-familia', id, data)}
                        onDelete={(item) => handleDelete('sub-familia', item)}
                        FormComponent={SubFamiliaForm}
                        getRowKey={(row) => row.id_sub_familia}
                    />
                )}

                {activeTab === 'variables' && (
                    <CRUDTable
                        title="Variables"
                        columns={[
                            { key: 'id_variable', label: 'ID' },
                            { key: 'id_nombre_variable', label: 'Nombre' },
                            { key: 'tipo_serie', label: 'Tipo de Serie' },
                            { key: 'nombre_sub_familia', label: 'Sub-Familia' },
                            { key: 'nominal_o_real', label: 'N/R' },
                            { key: 'moneda', label: 'Moneda' },
                        ]}
                        data={variableData}
                        loading={loading['variables']}
                        error={errors['variables']}
                        onCreate={(data) => handleCreate('variables', data)}
                        onUpdate={(id, data) => handleUpdate('variables', id, data)}
                        onDelete={(item) => handleDelete('variables', item)}
                        FormComponent={VariableForm}
                        getRowKey={(row) => row.id_variable}
                    />
                )}

                {activeTab === 'maestro' && (
                    <CRUDTable
                        title="Maestro"
                        columns={[
                            { key: 'id_variable', label: 'ID Variable' },
                            { key: 'variable_nombre', label: 'Nombre' },
                            { key: 'pais_nombre', label: 'País' },
                            { key: 'periodicidad', label: 'Periodicidad' },
                            { key: 'cantidad_datos', label: 'Cantidad de Datos', render: (val) => val || 0 },
                            { key: 'ultima_fecha', label: 'Última Fecha', render: (val) => {
                                if (!val) return 'N/A';
                                // Parsear la fecha correctamente para evitar problemas de zona horaria
                                const dateParts = val.split('-');
                                if (dateParts.length === 3) {
                                    const date = new Date(parseInt(dateParts[0]), parseInt(dateParts[1]) - 1, parseInt(dateParts[2]));
                                    return date.toLocaleDateString('es-ES');
                                }
                                return new Date(val).toLocaleDateString('es-ES');
                            }},
                            { key: 'fuente', label: 'Fuente' },
                            { key: 'unidad', label: 'Unidad' },
                            { key: 'activo', label: 'Activo', render: (val) => val ? 'Sí' : 'No' },
                            { key: 'script_update', label: 'Script Update' },
                        ]}
                        data={maestroData}
                        loading={loading['maestro']}
                        error={errors['maestro']}
                        onCreate={(data) => handleCreate('maestro', data)}
                        onUpdate={(id, data) => handleUpdate('maestro', id, data)}
                        onDelete={(item) => handleDelete('maestro', item)}
                        FormComponent={MaestroForm}
                        getRowKey={(row) => `${row.id_variable}_${row.id_pais}`}
                        actionsFirst={true}
                        filters={() => (
                            <div>
                                <div className="grid grid-cols-2 gap-4 mb-3">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Filtrar por Variable
                                        </label>
                                        <input
                                            type="text"
                                            value={maestroFilters.variable_nombre}
                                            onChange={(e) => {
                                                setMaestroFilters({...maestroFilters, variable_nombre: e.target.value});
                                                setMaestroPage(1);
                                            }}
                                            onKeyPress={(e) => {
                                                if (e.key === 'Enter') {
                                                    loadData('maestro');
                                                }
                                            }}
                                            placeholder="Nombre de variable..."
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Filtrar por País
                                        </label>
                                        <input
                                            type="text"
                                            value={maestroFilters.pais_nombre}
                                            onChange={(e) => {
                                                setMaestroFilters({...maestroFilters, pais_nombre: e.target.value});
                                                setMaestroPage(1);
                                            }}
                                            onKeyPress={(e) => {
                                                if (e.key === 'Enter') {
                                                    loadData('maestro');
                                                }
                                            }}
                                            placeholder="Nombre de país..."
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        />
                                    </div>
                                </div>
                                <div className="flex justify-end">
                                    <button
                                        onClick={() => {
                                            setMaestroPage(1);
                                            loadData('maestro');
                                        }}
                                        className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                                    >
                                        Aplicar Filtros
                                    </button>
                                </div>
                            </div>
                        )}
                        pagination={maestroPagination}
                        onPageChange={(newPage) => {
                            setMaestroPage(newPage);
                            loadData('maestro');
                        }}
                    />
                )}

                {activeTab === 'graph' && (
                    <CRUDTable
                        title="Graphs"
                        columns={[
                            { key: 'id_graph', label: 'ID' },
                            { key: 'nombre_graph', label: 'Nombre' },
                            { key: 'selector', label: 'Selector' },
                        ]}
                        data={graphData}
                        loading={loading['graph']}
                        error={errors['graph']}
                        onCreate={(data) => handleCreate('graph', data)}
                        onUpdate={(id, data) => handleUpdate('graph', id, data)}
                        onDelete={(item) => handleDelete('graph', item)}
                        FormComponent={GraphForm}
                        getRowKey={(row) => row.id_graph}
                    />
                )}

                {activeTab === 'pais-grupo' && (
                    <CRUDTable
                        title="Países"
                        columns={[
                            { key: 'id_pais', label: 'ID' },
                            { key: 'nombre_pais_grupo', label: 'Nombre' },
                        ]}
                        data={paisData}
                        loading={loading['pais-grupo']}
                        error={errors['pais-grupo']}
                        onCreate={(data) => handleCreate('pais-grupo', data)}
                        onUpdate={(id, data) => handleUpdate('pais-grupo', id, data)}
                        onDelete={(item) => handleDelete('pais-grupo', item)}
                        FormComponent={({ initialData, onSubmit, onCancel }) => (
                            <form onSubmit={(e) => {
                                e.preventDefault();
                                const formData = { nombre_pais_grupo: e.target.nombre.value };
                                onSubmit(formData);
                            }} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Nombre del País *
                                    </label>
                                    <input
                                        type="text"
                                        name="nombre"
                                        defaultValue={initialData?.nombre_pais_grupo || ''}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                                        required
                                    />
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
                        )}
                        getRowKey={(row) => row.id_pais}
                    />
                )}

                {activeTab === 'filtros' && (
                    <div className="bg-white rounded-lg shadow-md p-6">
                        <h2 className="text-2xl font-bold text-gray-900 mb-4">Filtros Graph-País</h2>
                        <FiltrosForm
                            onSubmit={async () => {
                                const filtros = await AdminAPI.getFiltros();
                                setFiltrosData(filtros);
                            }}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}

// Render the app
ReactDOM.render(React.createElement(AdminApp), document.getElementById('root'));
