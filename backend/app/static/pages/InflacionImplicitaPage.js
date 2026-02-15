// Página Inflación implícita curva soberana (1-10 años)
// embeddedView: 'curva' | 'evolucion' cuando se usa como pestaña dentro de Curva de Rendimiento (solo muestra esa vista)
function InflacionImplicitaPage({ embeddedView }) {
    const [viewMode, setViewMode] = React.useState(embeddedView || 'curva'); // 'curva' | 'evolucion'
    const [fechasDisponibles, setFechasDisponibles] = React.useState([]);
    const [ultimaFecha, setUltimaFecha] = React.useState(null);
    const [selectedFechas, setSelectedFechas] = React.useState([]);
    const [plazos, setPlazos] = React.useState([]);
    const [selectedPlazos, setSelectedPlazos] = React.useState([]);
    const [fechaDesde, setFechaDesde] = React.useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - 365);
        return d.toISOString().split('T')[0];
    });
    const [fechaHasta, setFechaHasta] = React.useState(() => new Date().toISOString().split('T')[0]);
    const [curvaData, setCurvaData] = React.useState([]); // array de { fecha, plazos, valores }
    const [evolucionData, setEvolucionData] = React.useState([]); // array de { plazo, nombre_plazo, data: [{fecha,valor}] }
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState(null);
    const [fullscreen, setFullscreen] = React.useState(false);
    const chartCurvaRef = React.useRef(null);
    const chartEvolucionRef = React.useRef(null);
    const chartCurvaInstance = React.useRef(null);
    const chartEvolucionInstance = React.useRef(null);

    const formatFecha = (fechaStr) => {
        if (!fechaStr) return '';
        const p = fechaStr.split('-');
        if (p.length === 3) return `${p[2]}/${p[1]}/${p[0]}`;
        return fechaStr;
    };

    // Cargar fechas y plazos al montar
    React.useEffect(() => {
        fetch(`${API_BASE}/inflacion-implicita/fechas`)
            .then(res => res.json())
            .then(data => {
                setFechasDisponibles(data.fechas_disponibles || []);
                setUltimaFecha(data.ultima_fecha || null);
                if (data.ultima_fecha) setSelectedFechas(prev => (prev.length ? prev : [data.ultima_fecha]));
            })
            .catch(() => setFechasDisponibles([]));
        fetch(`${API_BASE}/inflacion-implicita/plazos`)
            .then(res => res.json())
            .then(data => {
                setPlazos(data.plazos || []);
                if (data.plazos && data.plazos.length) setSelectedPlazos(prev => (prev.length ? prev : [String(data.plazos[0].plazo)]));
            })
            .catch(() => setPlazos([]));
    }, []);

    React.useEffect(() => {
        if (ultimaFecha && selectedFechas.length === 0) setSelectedFechas([ultimaFecha]);
    }, [ultimaFecha]);

    const loadCurva = () => {
        const fechas = selectedFechas.length ? selectedFechas : (ultimaFecha ? [ultimaFecha] : []);
        if (!fechas.length) {
            setError('Seleccione al menos una fecha');
            return;
        }
        setLoading(true);
        setError(null);
        Promise.all(fechas.map(fecha => fetch(`${API_BASE}/inflacion-implicita/curva?fecha=${fecha}`).then(r => r.ok ? r.json() : Promise.reject(new Error(r.statusText)))))
            .then(arr => {
                setCurvaData(arr);
                setError(null);
            })
            .catch(err => {
                setError(err.message || 'Error al cargar la curva');
                setCurvaData([]);
            })
            .finally(() => setLoading(false));
    };

    const loadEvolucion = () => {
        const plazosIds = selectedPlazos.length ? selectedPlazos.map(p => Number(p)) : (plazos[0] ? [plazos[0].plazo] : []);
        if (!plazosIds.length) {
            setError('Seleccione al menos un plazo');
            return;
        }
        setLoading(true);
        setError(null);
        Promise.all(plazosIds.map(plazo => fetch(`${API_BASE}/inflacion-implicita/evolucion?plazo=${plazo}&fecha_desde=${fechaDesde}&fecha_hasta=${fechaHasta}`).then(r => r.ok ? r.json() : Promise.reject(new Error(r.statusText)))))
            .then(arr => {
                setEvolucionData(arr);
                setError(null);
            })
            .catch(err => {
                setError(err.message || 'Error al cargar la evolución');
                setEvolucionData([]);
            })
            .finally(() => setLoading(false));
    };

    const COLORS = ['rgb(99, 102, 241)', 'rgb(139, 92, 246)', 'rgb(236, 72, 153)', 'rgb(34, 197, 94)', 'rgb(234, 179, 8)', 'rgb(239, 68, 68)', 'rgb(20, 184, 166)', 'rgb(251, 146, 60)'];
    const COLORS_RGBA = ['rgba(99, 102, 241, 0.6)', 'rgba(139, 92, 246, 0.6)', 'rgba(236, 72, 153, 0.6)', 'rgba(34, 197, 94, 0.6)', 'rgba(234, 179, 8, 0.6)', 'rgba(239, 68, 68, 0.6)', 'rgba(20, 184, 166, 0.6)', 'rgba(251, 146, 60, 0.6)'];

    // Gráfico curva (plazos en X, una serie por fecha)
    React.useEffect(() => {
        if (!Array.isArray(curvaData) || curvaData.length === 0) return;
        const first = curvaData[0];
        if (!first || !first.plazos || !first.valores) return;
        if (chartCurvaInstance.current) {
            chartCurvaInstance.current.destroy();
            chartCurvaInstance.current = null;
        }
        const labels = first.plazos;
        const datasets = curvaData.map((d, i) => ({
            label: formatFecha(d.fecha),
            data: (d.valores || []).map(v => v == null ? 0 : Number(v)),
            backgroundColor: COLORS_RGBA[i % COLORS_RGBA.length],
            borderColor: COLORS[i % COLORS.length],
            borderWidth: 1
        }));
        const id = setTimeout(() => {
            if (!chartCurvaRef.current) return;
            const ctx = chartCurvaRef.current.getContext('2d');
            chartCurvaInstance.current = new Chart(ctx, {
            type: 'bar',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Inflación implícita por plazo' },
                    tooltip: { callbacks: { label: (ctx) => ctx.parsed.y != null ? ctx.parsed.y.toFixed(2) + '%' : 'N/A' } }
                },
                scales: {
                    y: { title: { display: true, text: 'Inflación implícita (%)' }, ticks: { callback: v => v + '%' } },
                    x: { title: { display: true, text: 'Plazo' } }
                }
            }
        });
        }, 50);
        return () => {
            clearTimeout(id);
            if (chartCurvaInstance.current) {
                chartCurvaInstance.current.destroy();
                chartCurvaInstance.current = null;
            }
        };
    }, [curvaData]);

    // Gráfico evolución (una serie por plazo)
    React.useEffect(() => {
        if (!Array.isArray(evolucionData) || evolucionData.length === 0) return;
        if (chartEvolucionInstance.current) {
            chartEvolucionInstance.current.destroy();
            chartEvolucionInstance.current = null;
        }
        const allFechas = [];
        evolucionData.forEach(s => (s.data || []).forEach(p => { if (p.fecha && !allFechas.includes(p.fecha)) allFechas.push(p.fecha); }));
        allFechas.sort();
        const byFecha = (arr, f) => (arr || []).find(x => x.fecha === f);
        const datasets = evolucionData.map((s, i) => ({
            label: s.nombre_plazo || (s.plazo + ' años'),
            data: allFechas.map(f => { const p = byFecha(s.data, f); return p != null ? Number(p.valor) : null; }),
            borderColor: COLORS[i % COLORS.length] || 'rgb(139, 92, 246)',
            backgroundColor: COLORS_RGBA[i % COLORS_RGBA.length].replace('0.6', '0.1'),
            fill: false,
            tension: 0.2
        }));
        const idEv = setTimeout(() => {
            if (!chartEvolucionRef.current) return;
            const ctx = chartEvolucionRef.current.getContext('2d');
            chartEvolucionInstance.current = new Chart(ctx, {
            type: 'line',
            data: { labels: allFechas.map(formatFecha), datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Evolución temporal - Inflación implícita' },
                    tooltip: { callbacks: { label: (ctx) => ctx.parsed.y != null ? ctx.parsed.y.toFixed(2) + '%' : '' } }
                },
                scales: {
                    y: { title: { display: true, text: 'Inflación implícita (%)' }, ticks: { callback: v => v + '%' } },
                    x: { title: { display: true, text: 'Fecha' } }
                }
            }
        });
        }, 50);
        return () => {
            clearTimeout(idEv);
            if (chartEvolucionInstance.current) {
                chartEvolucionInstance.current.destroy();
                chartEvolucionInstance.current = null;
            }
        };
    }, [evolucionData]);

    const onlyCurva = embeddedView === 'curva';
    const onlyEvolucion = embeddedView === 'evolucion';
    const showCurva = onlyCurva || (!onlyEvolucion && viewMode === 'curva');
    const showEvolucion = onlyEvolucion || (!onlyCurva && viewMode === 'evolucion');

    return (
        <div className={embeddedView ? 'w-full p-0' : 'min-h-screen p-6'}>
            {!embeddedView && (
                <>
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Inflación implícita - Curva soberana</h1>
                    <p className="text-gray-600 mb-6">Uruguay, plazos 1 a 10 años. Fuente: BEVSA (nominal y real).</p>
                </>
            )}
            {!embeddedView && (
            <div className="flex gap-2 mb-4">
                <button
                    type="button"
                    onClick={() => setViewMode('curva')}
                    className={`px-4 py-2 rounded-md font-medium ${viewMode === 'curva' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    Curva por plazo
                </button>
                <button
                    type="button"
                    onClick={() => setViewMode('evolucion')}
                    className={`px-4 py-2 rounded-md font-medium ${viewMode === 'evolucion' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'}`}
                >
                    Evolución por plazo
                </button>
            </div>
            )}

            {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md">{error}</div>}

            {showCurva && (embeddedView === 'curva' ? (
                /* Layout como Curva Soberana: panel izquierdo + gráfico */
                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">Selecciona fecha</label>
                                        <VariableSelector
                                            selectedProducts={selectedFechas}
                                            onSelectionChange={setSelectedFechas}
                                            products={fechasDisponibles.map(f => ({ id: f, nombre: f, displayName: `${formatFecha(f)}${f === ultimaFecha ? ' (Última)' : ''}` }))}
                                            allProducts={fechasDisponibles.map(f => ({ id: f, nombre: f, displayName: `${formatFecha(f)}${f === ultimaFecha ? ' (Última)' : ''}` }))}
                                        />
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        <button onClick={loadCurva} disabled={loading || selectedFechas.length === 0} className="btn-primary w-full">
                                            {loading ? 'Cargando...' : 'Aplicar Filtros'}
                                        </button>
                                        <button onClick={() => { setSelectedFechas([]); setCurvaData([]); setError(null); }} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors">Limpiar</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                    <div className={fullscreen ? 'col-span-1' : 'lg:col-span-3'}>
                        {loading ? (
                            <div className="card"><div className="flex items-center justify-center py-12"><div className="text-center"><div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div><p className="text-gray-600">Cargando datos...</p></div></div></div>
                        ) : Array.isArray(curvaData) && curvaData.length > 0 && curvaData[0].plazos && curvaData[0].plazos.length > 0 ? (
                            <div className={`card mb-6 ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                                <div className="flex justify-between items-center mb-4">
                                    <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>Inflación implícita por plazo</h2>
                                    <div className="flex gap-2">
                                        {fullscreen ? (
                                            <button onClick={() => setFullscreen(false)} className="px-3 py-1.5 rounded-lg font-medium transition-all bg-gray-200 text-gray-700 hover:bg-gray-300 text-sm" title="Salir de pantalla completa"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
                                        ) : (
                                            <button onClick={() => setFullscreen(true)} className="px-3 py-1.5 rounded-lg font-medium transition-all bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm" title="Pantalla completa"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg></button>
                                        )}
                                    </div>
                                </div>
                                <div className="print-chart-container" style={{ height: fullscreen ? 'calc(100vh - 120px)' : '500px', position: 'relative' }}><canvas ref={chartCurvaRef}></canvas></div>
                            </div>
                        ) : (
                            <div className="card"><div className="flex items-center justify-center py-12"><div className="text-center text-gray-500"><p>Selecciona una fecha para visualizar la curva de inflación implícita</p></div></div></div>
                        )}
                    </div>
                </div>
            ) : (
                <div className="card max-w-4xl">
                    <h2 className="text-lg font-semibold mb-3">Curva por fecha</h2>
                    <div className="flex flex-wrap items-end gap-4 mb-4">
                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Fecha</label>
                        <VariableSelector selectedProducts={selectedFechas} onSelectionChange={setSelectedFechas} products={fechasDisponibles.map(f => ({ id: f, nombre: f, displayName: `${formatFecha(f)}${f === ultimaFecha ? ' (Última)' : ''}` }))} allProducts={fechasDisponibles.map(f => ({ id: f, nombre: f, displayName: `${formatFecha(f)}${f === ultimaFecha ? ' (Última)' : ''}` }))} /></div>
                        <button type="button" onClick={loadCurva} disabled={loading || selectedFechas.length === 0} className="btn-primary">{loading ? 'Cargando...' : 'Ver curva'}</button>
                    </div>
                    <div className="print-chart-container" style={{ height: 360 }}><canvas ref={chartCurvaRef}></canvas></div>
                </div>
            ))}

            {showEvolucion && (embeddedView === 'evolucion' ? (
                /* Layout como Análisis temporal: panel izquierdo + gráfico */
                <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
                    {!fullscreen && (
                        <div className="lg:col-span-1">
                            <div className="card sticky top-6">
                                <div className="space-y-6">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">Selecciona plazos</label>
                                        <VariableSelector
                                            selectedProducts={selectedPlazos}
                                            onSelectionChange={setSelectedPlazos}
                                            products={plazos.map(p => ({ id: String(p.plazo), nombre: p.nombre, displayName: p.nombre }))}
                                            allProducts={plazos.map(p => ({ id: String(p.plazo), nombre: p.nombre, displayName: p.nombre }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">Rango de fechas</label>
                                        <DateRangePicker fechaDesde={fechaDesde} fechaHasta={fechaHasta} onFechaDesdeChange={setFechaDesde} onFechaHastaChange={setFechaHasta} />
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        <button onClick={loadEvolucion} disabled={loading || selectedPlazos.length === 0} className="btn-primary w-full">{loading ? 'Cargando...' : 'Aplicar Filtros'}</button>
                                        <button onClick={() => { setSelectedPlazos([]); setEvolucionData([]); setError(null); }} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors">Limpiar</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                    <div className={fullscreen ? 'col-span-1' : 'lg:col-span-3'}>
                        {loading ? (
                            <div className="card"><div className="flex items-center justify-center py-12"><div className="text-center"><div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div><p className="text-gray-600">Cargando datos...</p></div></div></div>
                        ) : evolucionData.length > 0 ? (
                            <div className={`card mb-6 ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                                <div className="flex justify-between items-center mb-4">
                                    <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>Evolución temporal - Inflación implícita</h2>
                                    <div className="flex gap-2">
                                        {fullscreen ? (
                                            <button onClick={() => setFullscreen(false)} className="px-3 py-1.5 rounded-lg font-medium transition-all bg-gray-200 text-gray-700 hover:bg-gray-300 text-sm" title="Salir de pantalla completa"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
                                        ) : (
                                            <button onClick={() => setFullscreen(true)} className="px-3 py-1.5 rounded-lg font-medium transition-all bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm" title="Pantalla completa"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg></button>
                                        )}
                                    </div>
                                </div>
                                <div className="print-chart-container" style={{ height: fullscreen ? 'calc(100vh - 120px)' : '500px' }}><canvas ref={chartEvolucionRef}></canvas></div>
                            </div>
                        ) : (
                            <div className="card"><div className="flex items-center justify-center py-12"><div className="text-center text-gray-500"><p>Selecciona un plazo y un rango de fechas, luego haz clic en &quot;Aplicar Filtros&quot; para visualizar la evolución</p></div></div></div>
                        )}
                    </div>
                </div>
            ) : (
                <div className="card max-w-4xl">
                    <h2 className="text-lg font-semibold mb-3">Evolución inflación implícita</h2>
                    <div className="flex flex-wrap items-end gap-4 mb-4">
                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Plazo</label>
                        <VariableSelector selectedProducts={selectedPlazos} onSelectionChange={setSelectedPlazos} products={plazos.map(p => ({ id: String(p.plazo), nombre: p.nombre, displayName: p.nombre }))} allProducts={plazos.map(p => ({ id: String(p.plazo), nombre: p.nombre, displayName: p.nombre }))} /></div>
                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Desde</label><input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="input-field w-40" /></div>
                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Hasta</label><input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="input-field w-40" /></div>
                        <button type="button" onClick={loadEvolucion} disabled={loading} className="btn-primary">{loading ? 'Cargando...' : 'Ver evolución'}</button>
                    </div>
                    <div className="print-chart-container" style={{ height: 360 }}><canvas ref={chartEvolucionRef}></canvas></div>
                </div>
            ))}
        </div>
    );
}
