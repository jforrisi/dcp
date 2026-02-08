// Detectar automáticamente la URL base de la API
const getApiBase = () => {
    // En producción (Railway), usar ruta relativa
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        return '/api';
    }
    // En desarrollo local
    return 'http://localhost:8000/api';
};

const API_BASE = getApiBase();

// Parsear "YYYY-MM-DD" como fecha LOCAL (evita corrimiento por zona horaria)
function parseISODateLocal(isoDateStr) {
    if (!isoDateStr) return null;
    // Soporta "YYYY-MM-DD" y también "YYYY-MM-DDTHH:MM:SS"
    const datePart = String(isoDateStr).split('T')[0].split(' ')[0];
    const [y, m, d] = datePart.split('-').map(n => parseInt(n, 10));
    if (!y || !m || !d) return null;
    return new Date(y, m - 1, d);
}
