// API utilities for admin panel
const API_BASE_ADMIN = '/api/admin';

async function fetchAdmin(endpoint, options = {}) {
    const url = `${API_BASE_ADMIN}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    try {
        console.log(`[AdminAPI] Fetching: ${url}`, options.method || 'GET');
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
                errorData = { error: `Error ${response.status}: ${response.statusText}` };
            }
            
            const errorMessage = errorData.error || `Error ${response.status}: ${response.statusText}`;
            const fullError = new Error(`${errorMessage} (${url})`);
            fullError.status = response.status;
            fullError.url = url;
            console.error(`[AdminAPI] Error ${response.status} on ${url}:`, errorData);
            throw fullError;
        }
        
        const data = await response.json();
        console.log(`[AdminAPI] Success on ${url}:`, Array.isArray(data) ? `${data.length} items` : 'data received');
        return data;
    } catch (error) {
        // Si es un error de red (fetch falló completamente)
        if (error instanceof TypeError && error.message.includes('fetch')) {
            const networkError = new Error(`Error de red: No se pudo conectar al servidor (${url})`);
            networkError.url = url;
            networkError.originalError = error;
            console.error(`[AdminAPI] Network error on ${url}:`, error);
            throw networkError;
        }
        // Re-lanzar otros errores (ya tienen el formato correcto)
        throw error;
    }
}

const AdminAPI = {
    // Familia
    getFamilias: () => fetchAdmin('/familia'),
    getFamilia: (id) => fetchAdmin(`/familia/${id}`),
    createFamilia: (data) => fetchAdmin('/familia', { method: 'POST', body: JSON.stringify(data) }),
    updateFamilia: (id, data) => fetchAdmin(`/familia/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteFamilia: (id) => fetchAdmin(`/familia/${id}`, { method: 'DELETE' }),
    
    // Sub-Familia
    getSubFamilias: (familiaId) => {
        const endpoint = familiaId ? `/sub-familia?familia_id=${familiaId}` : '/sub-familia';
        return fetchAdmin(endpoint);
    },
    getSubFamilia: (id) => fetchAdmin(`/sub-familia/${id}`),
    createSubFamilia: (data) => fetchAdmin('/sub-familia', { method: 'POST', body: JSON.stringify(data) }),
    updateSubFamilia: (id, data) => fetchAdmin(`/sub-familia/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteSubFamilia: (id) => fetchAdmin(`/sub-familia/${id}`, { method: 'DELETE' }),
    
    // Variables
    getVariables: (subFamiliaId) => {
        const endpoint = subFamiliaId ? `/variables?sub_familia_id=${subFamiliaId}` : '/variables';
        return fetchAdmin(endpoint);
    },
    getVariable: (id) => fetchAdmin(`/variables/${id}`),
    createVariable: (data) => fetchAdmin('/variables', { method: 'POST', body: JSON.stringify(data) }),
    updateVariable: (id, data) => fetchAdmin(`/variables/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteVariable: (id) => fetchAdmin(`/variables/${id}`, { method: 'DELETE' }),
    
    // Graph
    getGraphs: () => fetchAdmin('/graph'),
    getGraph: (id) => fetchAdmin(`/graph/${id}`),
    getGraphFiltros: (id) => fetchAdmin(`/graph/${id}/filtros`),
    createGraph: (data) => fetchAdmin('/graph', { method: 'POST', body: JSON.stringify(data) }),
    updateGraph: (id, data) => fetchAdmin(`/graph/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteGraph: (id) => fetchAdmin(`/graph/${id}`, { method: 'DELETE' }),
    
    // Filtros
    getFiltros: (graphId) => {
        const endpoint = graphId ? `/filtros?graph_id=${graphId}` : '/filtros';
        return fetchAdmin(endpoint);
    },
    createFiltro: (data) => fetchAdmin('/filtros', { method: 'POST', body: JSON.stringify(data) }),
    deleteFiltro: (graphId, paisId) => fetchAdmin(`/filtros?graph_id=${graphId}&id_pais=${paisId}`, { method: 'DELETE' }),
    updateFiltrosBulk: (data) => fetchAdmin('/filtros/bulk', { method: 'PUT', body: JSON.stringify(data) }),
    
    // Maestro (usa clave compuesta: id_variable + id_pais)
    getMaestro: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.activo !== undefined) params.append('activo', filters.activo);
        if (filters.variable_id) params.append('variable_id', filters.variable_id);
        if (filters.pais_id) params.append('pais_id', filters.pais_id);
        if (filters.variable_nombre) params.append('variable_nombre', filters.variable_nombre);
        if (filters.pais_nombre) params.append('pais_nombre', filters.pais_nombre);
        if (filters.page) params.append('page', filters.page);
        if (filters.per_page) params.append('per_page', filters.per_page);
        const query = params.toString();
        return fetchAdmin(`/maestro${query ? '?' + query : ''}`);
    },
    getMaestroRecord: (id_variable, id_pais) => fetchAdmin(`/maestro/${id_variable}/${id_pais}`),
    createMaestro: (data) => fetchAdmin('/maestro', { method: 'POST', body: JSON.stringify(data) }),
    createMaestroBulk: (data) => fetchAdmin('/maestro/bulk', { method: 'POST', body: JSON.stringify(data) }),
    updateMaestro: (id_variable, id_pais, data) => fetchAdmin(`/maestro/${id_variable}/${id_pais}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteMaestro: (id_variable, id_pais) => fetchAdmin(`/maestro/${id_variable}/${id_pais}`, { method: 'DELETE' }),
    
    // Pais Grupo
    getPaises: () => fetchAdmin('/pais-grupo'),
    getPais: (id) => fetchAdmin(`/pais-grupo/${id}`),
    createPais: (data) => fetchAdmin('/pais-grupo', { method: 'POST', body: JSON.stringify(data) }),
    updatePais: (id, data) => fetchAdmin(`/pais-grupo/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deletePais: (id) => fetchAdmin(`/pais-grupo/${id}`, { method: 'DELETE' }),
    
    // Tipo Serie
    getTiposSerie: () => fetchAdmin('/tipo-serie'),
};
