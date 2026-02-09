// Enlace de descarga que usa fetch con token (evita href sin Authorization)
function LogDownloadLink({ filename }) {
    const [loading, setLoading] = React.useState(false);
    const handleClick = async () => {
        setLoading(true);
        try {
            const opts = { credentials: 'include' };
            const token = typeof AdminAPI !== 'undefined' && AdminAPI.getToken ? AdminAPI.getToken() : null;
            if (token) opts.headers = { 'Authorization': `Bearer ${token}` };
            const r = await fetch(`${window.location.origin}/api/update/logs/${filename}`, opts);
            if (!r.ok) throw new Error('Error al descargar');
            const blob = await r.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            a.click();
            URL.revokeObjectURL(a.href);
        } catch (e) {
            console.error('Error descargando log:', e);
        } finally {
            setLoading(false);
        }
    };
    return (
        <button
            type="button"
            onClick={handleClick}
            disabled={loading}
            className="text-indigo-600 hover:text-indigo-800 underline disabled:opacity-50"
        >
            {loading ? '...' : 'Descargar'}
        </button>
    );
}

function formatElapsed(seconds) {
    if (seconds == null || seconds < 0) return '--';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// Tab de Actualización de Base de Datos
function UpdateTab() {
    const [updating, setUpdating] = React.useState(false);
    const [updateLog, setUpdateLog] = React.useState([]);
    const [elapsedSeconds, setElapsedSeconds] = React.useState(null);
    const [updateLogs, setUpdateLogs] = React.useState([]);
    const logRef = React.useRef(null);

    React.useEffect(() => {
        AdminAPI.getUpdateLogs()
            .then(data => {
                if (Array.isArray(data)) setUpdateLogs(data);
            })
            .catch(err => console.error('Error cargando logs:', err));
    }, []);

    const pollIntervalRef = React.useRef(null);
    // Al montar: comprobar si hay actualización en curso y mostrar progreso + polling
    React.useEffect(() => {
        const checkAndPoll = async () => {
            try {
                const status = await AdminAPI.getUpdateStatus();
                if (status.running) {
                    setUpdating(true);
                    if (status.progress?.length) setUpdateLog(status.progress);
                    setElapsedSeconds(status.elapsed_seconds ?? 0);
                    pollIntervalRef.current = setInterval(async () => {
                        try {
                            const s = await AdminAPI.getUpdateStatus();
                            if (s.progress?.length) setUpdateLog(s.progress);
                            if (s.elapsed_seconds != null) setElapsedSeconds(s.elapsed_seconds);
                            if (!s.running) {
                                clearInterval(pollIntervalRef.current);
                                pollIntervalRef.current = null;
                                setUpdating(false);
                                if (s.returncode === 0) {
                                    setUpdateLog(prev => [...prev, '✓ Actualización completada exitosamente']);
                                } else {
                                    setUpdateLog(prev => [...prev, `✗ Error: ${s.error || 'Error desconocido'}`]);
                                }
                                AdminAPI.getUpdateLogs().then(data => Array.isArray(data) && setUpdateLogs(data));
                            }
                        } catch (_) {}
                    }, 2000);
                }
            } catch (_) {}
        };
        checkAndPoll();
        return () => {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        };
    }, []);

    // Auto-scroll en el log cuando cambian las líneas
    React.useEffect(() => {
        if (logRef.current && updating) {
            logRef.current.scrollTop = logRef.current.scrollHeight;
        }
    }, [updateLog, updating]);

    const handleCancelUpdate = async () => {
        if (!updating) return;
        try {
            await AdminAPI.cancelUpdate();
            setUpdateLog(prev => [...prev, '⏹ Actualización cancelada por el usuario']);
            setUpdating(false);
        } catch (err) {
            setUpdateLog(prev => [...prev, `Error al cancelar: ${err.message}`]);
        }
    };

    const handleUpdateDataset = async () => {
        if (updating) return;
        setUpdating(true);
        setUpdateLog(['Iniciando actualización...']);
        setElapsedSeconds(0);
        
        try {
            await AdminAPI.runUpdate();
            
            const pollInterval = setInterval(async () => {
                try {
                    const status = await AdminAPI.getUpdateStatus();
                    
                    if (status.progress && status.progress.length > 0) {
                        setUpdateLog(status.progress);
                    }
                    if (status.elapsed_seconds != null) {
                        setElapsedSeconds(status.elapsed_seconds);
                    }
                    
                    if (!status.running) {
                        clearInterval(pollInterval);
                        setUpdating(false);
                        
                        if (status.returncode === 0) {
                            setUpdateLog(prev => [...prev, '✓ Actualización completada exitosamente']);
                        } else {
                            setUpdateLog(prev => [...prev, `✗ Error: ${status.error || 'Error desconocido'}`]);
                        }
                        
                        AdminAPI.getUpdateLogs()
                            .then(data => {
                                if (Array.isArray(data)) setUpdateLogs(data);
                            })
                            .catch(err => console.error('Error cargando logs:', err));
                    }
                } catch (err) {
                    console.error('Error obteniendo estado:', err);
                }
            }, 2000);
            
        } catch (error) {
            setUpdateLog(prev => [...prev, `Error: ${error.message}`]);
            setUpdating(false);
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Actualizar Base de Datos</h2>
            <p className="text-gray-600 mb-6">
                Ejecuta la actualización completa del dataset. Este proceso puede tardar varios minutos.
            </p>
            
            <div className="flex justify-center gap-4 mb-6">
                <button
                    onClick={handleUpdateDataset}
                    disabled={updating}
                    className="px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                    {updating ? 'Actualizando...' : 'Actualizar dataset'}
                </button>
                {updating && (
                    <button
                        onClick={handleCancelUpdate}
                        className="px-6 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 font-medium"
                    >
                        Cancelar actualización
                    </button>
                )}
            </div>

            {updating && (
                <p className="text-sm text-amber-700 bg-amber-50 rounded p-3 mb-4">
                    Podés cerrar esta pestaña. La actualización sigue en el servidor. Al volver verás el estado y los logs.
                </p>
            )}
            
            {updating && (
                <div className="mb-6 bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-semibold text-gray-700">Progreso...</h3>
                        <div className="flex items-center gap-4">
                            <span className="text-xs text-gray-500">Tiempo: {formatElapsed(elapsedSeconds)}</span>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
                        </div>
                    </div>
                    <div ref={logRef} className="bg-white rounded p-3 max-h-80 overflow-y-auto border text-xs font-mono">
                        <pre className="text-gray-700 whitespace-pre-wrap">
                            {updateLog.length > 0 ? (Array.isArray(updateLog) ? updateLog.join('\n') : updateLog) : 'Iniciando actualización...'}
                        </pre>
                    </div>
                </div>
            )}
            
            {updateLogs.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-2">Últimas actualizaciones:</h3>
                    <div className="space-y-1">
                        {updateLogs.map((log, idx) => (
                            <div key={idx} className="flex items-center justify-between text-xs">
                                <span className="text-gray-600">{log.date}</span>
                                <LogDownloadLink filename={log.filename} />
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
