// API utilities for admin panel - usar origin para mismo host/puerto (evita CORS y Tracking Prevention)
const API_BASE_ADMIN = `${window.location.origin}/api/admin`;

// Token en memoria (evita cookies bloqueadas por Tracking Prevention de Edge)
let _adminToken = null;

async function fetchAdmin(endpoint, options = {}) {
    const url = `${API_BASE_ADMIN}${endpoint}`;
    const headers = { 'Content-Type': 'application/json' };
    if (_adminToken) {
        headers['Authorization'] = `Bearer ${_adminToken}`;
    }
    const defaultOptions = {
        credentials: 'include',
        headers,
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
    setToken: (token) => { _adminToken = token; },
    clearToken: () => { _adminToken = null; },
    getToken: () => _adminToken,
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
    
    // Auth
    login: (user, password) => fetchAdmin('/login', { method: 'POST', body: JSON.stringify({ user, password }) }),
    logout: () => fetchAdmin('/logout', { method: 'POST' }),
    checkSession: () => fetchAdmin('/check'),
    
    // Update (usa /api/update, mismo origin, con token si hay)
    runUpdate: async () => {
        const opts = { method: 'POST', credentials: 'include' };
        if (_adminToken) opts.headers = { 'Authorization': `Bearer ${_adminToken}` };
        const r = await fetch(`${window.location.origin}/api/update/run`, opts);
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.error || `Error ${r.status}`);
        return data;
    },
    getUpdateStatus: () => {
        const opts = { credentials: 'include' };
        if (_adminToken) opts.headers = { 'Authorization': `Bearer ${_adminToken}` };
        return fetch(`${window.location.origin}/api/update/status`, opts).then(r => r.json());
    },
    cancelUpdate: async () => {
        const opts = { method: 'POST', credentials: 'include' };
        if (_adminToken) opts.headers = { 'Authorization': `Bearer ${_adminToken}` };
        const r = await fetch(`${window.location.origin}/api/update/cancel`, opts);
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.error || `Error ${r.status}`);
        return data;
    },
    getUpdateLogs: () => {
        const opts = { credentials: 'include' };
        if (_adminToken) opts.headers = { 'Authorization': `Bearer ${_adminToken}` };
        return fetch(`${window.location.origin}/api/update/logs`, opts).then(r => r.json());
    },
};
