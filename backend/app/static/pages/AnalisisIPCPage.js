// Analisis IPC Uruguay
const IPC_COLORS = [
    '#3b82f6','#ef4444','#10b981','#f59e0b','#8b5cf6',
    '#ec4899','#06b6d4','#84cc16','#f97316','#6366f1',
    '#14b8a6','#e11d48','#a855f7',
];

function useChartDelayed(chartRef, chartInstanceRef, buildChart, deps) {
    React.useEffect(() => {
        const check = () => {
            if (typeof Chart === 'undefined') { setTimeout(check, 100); return; }
            const canvas = chartRef.current;
            if (!canvas) { setTimeout(check, 100); return; }
            const ctx = canvas.getContext('2d');
            if (!ctx) return;
            if (chartInstanceRef.current) { chartInstanceRef.current.destroy(); chartInstanceRef.current = null; }
            const inst = buildChart(ctx);
            if (inst) chartInstanceRef.current = inst;
        };
        let tid;
        const fid = requestAnimationFrame(() => { tid = setTimeout(check, 200); });
        return () => {
            cancelAnimationFrame(fid);
            if (tid) clearTimeout(tid);
            if (chartInstanceRef.current) { chartInstanceRef.current.destroy(); chartInstanceRef.current = null; }
        };
    }, deps);
}

function AnalisisIPCPage() {
    const [tab, setTab] = React.useState('evolucion');
    const [fechas, setFechas] = React.useState([]);
    const [divisiones, setDivisiones] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [ipcLoad, setIpcLoad] = React.useState({ fechasErr: null, rubrosErr: null });

    React.useEffect(() => {
        let alive = true;
        (async () => {
            setLoading(true);
            let f = [];
            let d = [];
            let fechasErr = null;
            let rubrosErr = null;
            try {
                const rf = await fetch('/api/analisis-ipc/fechas');
                if (rf.ok) {
                    const j = await rf.json();
                    f = Array.isArray(j.fechas) ? j.fechas : [];
                } else {
                    fechasErr = rf.status;
                }
            } catch (e) {
                fechasErr = 'network';
            }
            try {
                const rr = await fetch('/api/analisis-ipc/rubros');
                if (rr.ok) {
                    const j = await rr.json();
                    d = Array.isArray(j.rubros) ? j.rubros : [];
                } else {
                    rubrosErr = rr.status;
                }
            } catch (e) {
                rubrosErr = 'network';
            }
            if (!alive) return;
            setFechas(f);
            setDivisiones(d);
            setIpcLoad({ fechasErr, rubrosErr });
            setLoading(false);
        })();
        return () => { alive = false; };
    }, []);

    if (loading) return (
        <div className="card"><div className="flex items-center justify-center py-12"><div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
            <p className="text-gray-600">Cargando datos IPC...</p>
        </div></div></div>
    );

    const tabs = [
        {id:'evolucion', label:'Evolucion Inflacion'},
        {id:'cascada', label:'Impacto Inflacion'},
        {id:'contribuciones', label:'Evolucion del impacto por division'},
    ];

    return (
        <div className="min-h-screen bg-gray-50 p-2">
            <div className="w-full">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Analisis IPC Uruguay</h1>
                </div>
                <div className="mb-6"><div className="border-b border-gray-200">
                    <nav className="-mb-px flex overflow-x-auto">
                        {tabs.map(t => (
                            <button key={t.id} onClick={() => setTab(t.id)}
                                className={`py-3 px-4 font-medium text-sm transition-all border-b-2 whitespace-nowrap ${
                                    tab === t.id ? 'bg-gray-100 border-indigo-500 text-indigo-600'
                                                 : 'bg-white text-gray-400 border-transparent hover:bg-gray-50 hover:text-gray-600'
                                }`}>{t.label}</button>
                        ))}
                    </nav>
                </div></div>
                {tab === 'evolucion' && (
                    <EvolucionTab
                        fechas={fechas}
                        divisiones={divisiones}
                        hayFechasEnBd={fechas.length > 0}
                        ipcLoad={ipcLoad}
                    />
                )}
                {tab === 'cascada' && <CascadaTab fechas={fechas} />}
                {tab === 'contribuciones' && <ContribucionesTab fechas={fechas} divisiones={divisiones} />}
            </div>
        </div>
    );
}


// ═══════════════════════════════════════════════════════════════
// Arbol IPC (division -> grupo -> clase -> subclase -> producto)
// ═══════════════════════════════════════════════════════════════

/** Query string para hijos directos; alineado con GET /rubros. Nunca usar division= si el nodo es grupo/clase/subclase. */
function ipcRubroChildrenQuery(rubro) {
    const nz = (v) => v != null && String(v).trim() !== '';
    if (rubro.nivel === 'general') {
        return 'hijos_de=general';
    }
    if (String(rubro.division) === '99' && rubro.nivel !== 'division') {
        return 'hijos_de=general';
    }

    const n = rubro.nivel;
    if (n === 'producto') return null;
    if (n === 'subclase') {
        return nz(rubro.subclase) ? 'subclase=' + encodeURIComponent(String(rubro.subclase)) : null;
    }
    if (n === 'clase') {
        return nz(rubro.clase) ? 'clase=' + encodeURIComponent(String(rubro.clase)) : null;
    }
    if (n === 'grupo') {
        return nz(rubro.grupo) ? 'grupo=' + encodeURIComponent(String(rubro.grupo)) : null;
    }
    if (n === 'division') {
        return nz(rubro.division) ? 'division=' + encodeURIComponent(String(rubro.division)) : null;
    }

    // Sin columna nivel en respuesta antigua: el codigo mas fino define el siguiente fetch.
    if (nz(rubro.producto)) return null;
    if (nz(rubro.subclase)) return 'subclase=' + encodeURIComponent(String(rubro.subclase));
    if (nz(rubro.clase)) return 'clase=' + encodeURIComponent(String(rubro.clase));
    if (nz(rubro.grupo)) return 'grupo=' + encodeURIComponent(String(rubro.grupo));
    if (nz(rubro.division)) return 'division=' + encodeURIComponent(String(rubro.division));
    return null;
}

function IPCEvolucionTreeNode({rubro, selectedIds, onToggle, depth, rubrosCacheRef}) {
    const [expanded, setExpanded] = React.useState(false);
    const [children, setChildren] = React.useState(null);
    const [loadingCh, setLoadingCh] = React.useState(false);

    const isChecked = selectedIds.indexOf(rubro.id) !== -1;
    const childQuery = ipcRubroChildrenQuery(rubro);
    const canExpand = childQuery != null && rubro.has_children !== false;

    const doExpand = () => {
        if (!canExpand) return;
        if (expanded) { setExpanded(false); return; }
        const params = childQuery;
        if (!params) return;
        if (children) { setExpanded(true); return; }
        const cached = rubrosCacheRef && rubrosCacheRef.current.get(params);
        if (cached != null) {
            setChildren(cached);
            setExpanded(true);
            return;
        }
        setLoadingCh(true);
        fetch('/api/analisis-ipc/rubros?' + params)
            .then(r => r.json())
            .then(d => {
                const list = d.rubros || [];
                if (rubrosCacheRef) rubrosCacheRef.current.set(params, list);
                setChildren(list);
                setExpanded(true);
                setLoadingCh(false);
            })
            .catch(() => setLoadingCh(false));
    };

    return (
        <div>
            <div className={`flex items-center py-1.5 rounded hover:bg-gray-50 text-sm ${isChecked ? 'bg-indigo-50' : ''}`}
                style={{paddingLeft: (8 + depth * 16) + 'px'}}>
                <span onClick={doExpand}
                    className={`w-5 h-5 flex items-center justify-center flex-shrink-0 rounded text-sm leading-none cursor-pointer border ${
                        canExpand
                            ? 'text-indigo-600 border-indigo-200 bg-indigo-50 hover:bg-indigo-100 font-semibold'
                            : 'text-gray-300 border-transparent'
                    }`}>
                    {canExpand ? (loadingCh ? '\u2026' : (expanded ? '\u2212' : '+')) : '\u2022'}
                </span>
                <input type="checkbox" checked={isChecked} onChange={() => onToggle(rubro.id)}
                    className="mx-1 h-3.5 w-3.5 text-indigo-600 border-gray-300 rounded flex-shrink-0 cursor-pointer" />
                <span onClick={doExpand} className={`flex-1 truncate cursor-pointer ${isChecked ? 'text-indigo-700 font-medium' : 'text-gray-800'}`}
                    title={rubro.descripcion}>{rubro.etiqueta}</span>
                {rubro.ponderacion != null && (
                    <span className="text-xs text-gray-400 ml-1 flex-shrink-0">{(rubro.ponderacion * 100).toFixed(1)}%</span>
                )}
            </div>
            {expanded && children && children.map(c => (
                <IPCEvolucionTreeNode key={c.id} rubro={c} selectedIds={selectedIds} onToggle={onToggle} depth={depth + 1} rubrosCacheRef={rubrosCacheRef} />
            ))}
        </div>
    );
}

/** Primer día del mes, N meses antes del mes de ultimaIso (YYYY-MM-DD). */
function ipcPrimerDiaMesMas(ultimaIso, mesesAtras) {
    if (!ultimaIso) return '';
    const parts = ultimaIso.slice(0, 10).split('-');
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (!Number.isFinite(y) || !Number.isFinite(m)) return '';
    const d = new Date(y, m - 1, 1);
    d.setMonth(d.getMonth() - mesesAtras);
    const yy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    return `${yy}-${mm}-01`;
}

/** Último día del mes calendario de la fecha ISO (según mes de ultimaIso). */
function ipcUltimoDiaDelMes(ultimaIso) {
    if (!ultimaIso) return '';
    const parts = ultimaIso.slice(0, 10).split('-');
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (!Number.isFinite(y) || !Number.isFinite(m)) return '';
    const last = new Date(y, m, 0).getDate();
    return `${y}-${String(m).padStart(2, '0')}-${String(last).padStart(2, '0')}`;
}

/** Rango por defecto: 18 meses calendario hasta el último mes con dato (no recortado al mes más viejo en BD). */
function ipcRangoDefault18Meses(fechas) {
    if (!fechas || fechas.length === 0) return { desde: '', hasta: '' };
    const ultima = fechas[0];
    return {
        desde: ipcPrimerDiaMesMas(ultima, 18),
        hasta: ipcUltimoDiaDelMes(ultima),
    };
}

/** Si la BD no tiene fechas aún: últimos 18 meses hasta el mes calendario actual (inputs siempre útiles). */
function ipcRangoCalendarioUltimos18Meses() {
    const now = new Date();
    const y = now.getFullYear();
    const mo = now.getMonth() + 1;
    const primerMesActual = `${y}-${String(mo).padStart(2, '0')}-01`;
    return {
        desde: ipcPrimerDiaMesMas(primerMesActual, 18),
        hasta: ipcUltimoDiaDelMes(primerMesActual),
    };
}

// ═══════════════════════════════════════════════════════════════
// TAB 1: Evolucion de inflacion interanual (flujo tipo Cotizaciones)
// ═══════════════════════════════════════════════════════════════
function EvolucionTab({ fechas, divisiones, hayFechasEnBd = false, ipcLoad = {} }) {
    const chartRef = React.useRef(null);
    const chartInst = React.useRef(null);
    const [fullscreen, setFullscreen] = React.useState(false);
    const evolucionRubrosSelectionRef = React.useRef(false);
    const fechasClave = fechas.length > 0 ? fechas[0] : 'sin-fechas-bd';

    const general = divisiones.find(d => d.nivel === 'general' || String(d.division) === '99');
    const generalId = general != null ? general.id : null;

    const [fechaDesde, setFechaDesde] = React.useState('');
    const [fechaHasta, setFechaHasta] = React.useState('');
    const [selectedIds, setSelectedIds] = React.useState([]);

    const [appliedDesde, setAppliedDesde] = React.useState('');
    const [appliedHasta, setAppliedHasta] = React.useState('');
    const [appliedIds, setAppliedIds] = React.useState([]);

    const [seriesData, setSeriesData] = React.useState([]);
    const [loadingSeries, setLoadingSeries] = React.useState(false);
    const [errorMsg, setErrorMsg] = React.useState(null);
    const [autoScale, setAutoScale] = React.useState(true);
    const [yMinStr, setYMinStr] = React.useState('0');
    const [yMaxStr, setYMaxStr] = React.useState('8');

    const rubrosCacheRef = React.useRef(new Map());
    const divisionesPrefetchKey = React.useMemo(
        () => (divisiones && divisiones.length ? divisiones.map(d => String(d.id)).join(',') : ''),
        [divisiones],
    );

    /** Precarga en segundo plano todos los niveles del arbol (mismas URLs que al expandir +) para que no haya ida al servidor en cada clic. */
    React.useEffect(() => {
        if (!divisionesPrefetchKey || ipcLoad.rubrosErr) return;
        let cancelled = false;
        const cache = rubrosCacheRef.current;
        cache.clear();
        const seenQ = new Set();
        const queue = [];
        const pushQ = (q) => {
            if (!q || seenQ.has(q)) return;
            seenQ.add(q);
            queue.push(q);
        };
        for (const r of divisiones) {
            const q = ipcRubroChildrenQuery(r);
            if (q && r.has_children !== false) pushQ(q);
        }
        (async () => {
            while (queue.length > 0 && !cancelled) {
                const q = queue.shift();
                if (cache.has(q)) {
                    const list = cache.get(q) || [];
                    for (const child of list) {
                        const cq = ipcRubroChildrenQuery(child);
                        if (cq && child.has_children !== false) pushQ(cq);
                    }
                    continue;
                }
                try {
                    const res = await fetch('/api/analisis-ipc/rubros?' + q);
                    if (!res.ok || cancelled) continue;
                    const j = await res.json();
                    const list = j.rubros || [];
                    cache.set(q, list);
                    for (const child of list) {
                        const cq = ipcRubroChildrenQuery(child);
                        if (cq && child.has_children !== false) pushQ(cq);
                    }
                } catch (_) { /* ignorar ramas con error */ }
            }
        })();
        return () => { cancelled = true; };
    }, [divisionesPrefetchKey, ipcLoad.rubrosErr]);

    /* Un solo efecto: periodo aplicado + GENERAL aplicado en el mismo ciclo, asi el fetch del grafico corre al entrar sin pulsar Aplicar. */
    React.useEffect(() => {
        const { desde, hasta } =
            fechasClave !== 'sin-fechas-bd'
                ? ipcRangoDefault18Meses([fechasClave])
                : ipcRangoCalendarioUltimos18Meses();
        if (desde && hasta) {
            setFechaDesde(desde);
            setFechaHasta(hasta);
            setAppliedDesde(desde);
            setAppliedHasta(hasta);
        }
        if (generalId != null && !evolucionRubrosSelectionRef.current) {
            setSelectedIds([generalId]);
            setAppliedIds([generalId]);
            evolucionRubrosSelectionRef.current = true;
        }
    }, [fechasClave, generalId]);

    const handleApplyFilters = () => {
        setErrorMsg(null);
        let ids = selectedIds;
        if (ids.length === 0 && general) {
            ids = [general.id];
            setSelectedIds(ids);
        }
        if (ids.length === 0) {
            setErrorMsg('No hay rubros cargados o no marcaste ninguno. Revisá el maestro IPC o elegí al menos un ítem en el árbol.');
            return;
        }
        if (!fechaDesde || !fechaHasta) {
            setErrorMsg('Indica mes/año desde y hasta.');
            return;
        }
        if (fechaDesde > fechaHasta) {
            setErrorMsg('El periodo desde no puede ser posterior al hasta.');
            return;
        }
        setAppliedDesde(fechaDesde);
        setAppliedHasta(fechaHasta);
        setAppliedIds([...ids]);
    };

    React.useEffect(() => {
        if (appliedIds.length === 0 || !appliedDesde || !appliedHasta) {
            setSeriesData([]);
            return;
        }
        setLoadingSeries(true);
        fetch('/api/analisis-ipc/inflacion-serie?ids=' + appliedIds.join(',') +
            '&fecha_desde=' + appliedDesde + '&fecha_hasta=' + appliedHasta)
            .then(r => r.json())
            .then(d => {
                if (d.error) { setErrorMsg(d.error); setSeriesData([]); }
                else { setSeriesData(d.series || []); }
                setLoadingSeries(false);
            })
            .catch(() => { setLoadingSeries(false); setErrorMsg('Error al cargar la serie.'); setSeriesData([]); });
    }, [appliedIds.join(','), appliedDesde, appliedHasta]);

    // Chart
    useChartDelayed(chartRef, chartInst, (ctx) => {
        if (seriesData.length === 0) return null;
        const allF = {};
        seriesData.forEach(s => s.data.forEach(p => { allF[p.fecha] = true; }));
        const fSorted = Object.keys(allF).sort();

        const datasets = seriesData.map((s, i) => {
            const dm = {};
            s.data.forEach(p => { dm[p.fecha] = p.valor; });
            return {
                label: s.nombre,
                data: fSorted.map(f => dm[f] != null ? dm[f] : null),
                borderColor: IPC_COLORS[i % IPC_COLORS.length],
                backgroundColor: 'transparent',
                tension: 0.3, pointRadius: 1.5, borderWidth: 2, spanGaps: true,
            };
        });

        // Banda meta BCU 3-6%
        datasets.push({
            label: 'Meta sup. (6%)', data: fSorted.map(() => 6),
            borderColor: 'rgba(156,163,175,0.35)', borderDash: [4,4],
            borderWidth: 1, pointRadius: 0, fill: false,
        });
        datasets.push({
            label: 'Meta inf. (3%)', data: fSorted.map(() => 3),
            borderColor: 'rgba(156,163,175,0.35)', borderDash: [4,4],
            borderWidth: 1, pointRadius: 0,
            fill: '-1', backgroundColor: 'rgba(156,163,175,0.05)',
        });

        // Objetivo BCU 4.5%
        datasets.push({
            label: 'Objetivo BCU (4.5%)', data: fSorted.map(() => 4.5),
            borderColor: '#111827', borderDash: [0],
            borderWidth: 1.5, pointRadius: 0, fill: false,
        });

        const pctTicks = { callback: v => v.toFixed(1) + '%' };
        const yTitle = { display: true, text: 'Inflacion interanual (%)' };
        let yConfig;
        if (autoScale) {
            yConfig = { ticks: { ...pctTicks }, title: yTitle };
        } else {
            const parseY = (s) => {
                const n = parseFloat(String(s || '').replace(',', '.').trim());
                return Number.isFinite(n) ? n : null;
            };
            const ymin = parseY(yMinStr);
            const ymax = parseY(yMaxStr);
            yConfig = {
                min: ymin !== null ? ymin : 0,
                max: ymax !== null ? ymax : 8,
                ticks: { ...pctTicks, stepSize: 1 },
                title: yTitle,
            };
        }

        return new Chart(ctx, {
            type: 'line',
            data: {labels: fSorted.map(f => f.slice(0,7)), datasets},
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: {mode:'index', intersect: false},
                plugins: {
                    legend: {position:'top', labels: {boxWidth: 12, font: {size: 11},
                        filter: it => !it.text.startsWith('Meta') && !it.text.startsWith('Objetivo')}},
                    tooltip: {
                        filter: it => !it.dataset.label.startsWith('Meta') && !it.dataset.label.startsWith('Objetivo'),
                        callbacks: {label: ctx2 => ctx2.dataset.label + ': ' + (ctx2.parsed.y != null ? ctx2.parsed.y.toFixed(2) : '-') + '%'},
                    },
                    title: {display: false},
                },
                scales: { y: yConfig, x: {ticks: {maxTicksLimit: 24, font: {size: 10}}} },
            },
        });
    }, [seriesData, fullscreen, autoScale, yMinStr, yMaxStr]);

    const toggleId = (id) => {
        setSelectedIds(prev => prev.indexOf(id) !== -1 ? prev.filter(x => x !== id) : [...prev, id]);
    };

    return (
        <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
            {!fullscreen && (
                <div className="lg:col-span-1">
                    <div className="card sticky top-6 space-y-4" style={{maxHeight:'calc(100vh - 100px)', overflowY:'auto'}}>
                        <div>
                            <h3 className="text-sm font-semibold text-gray-800 mb-2">Periodo (mes / año)</h3>
                            {ipcLoad.fechasErr && (
                                <p className="text-xs text-red-800 bg-red-50 border border-red-200 rounded-lg p-2 mb-2">
                                    No se pudieron leer las fechas desde la API (codigo {String(ipcLoad.fechasErr)}). Revisá consola red y <code className="bg-red-100 px-1 rounded">DATABASE_URL</code>.
                                </p>
                            )}
                            {!hayFechasEnBd && !ipcLoad.fechasErr && (
                                <p className="text-xs text-blue-900 bg-blue-50 border border-blue-200 rounded-lg p-2 mb-2">
                                    No hay meses en <code className="bg-blue-100 px-1 rounded">ipc_desagregados_valores</code>. El periodo se muestra igual (ultimos 18 meses calendario) para que puedas configurar; cargá series con{' '}
                                    <code className="bg-blue-100 px-1 rounded">036_ipc_uy_desagregado_ine.py</code>.
                                </p>
                            )}
                            <MonthYearPicker
                                fechaDesde={fechaDesde}
                                fechaHasta={fechaHasta}
                                onFechaDesdeChange={setFechaDesde}
                                onFechaHastaChange={setFechaHasta}
                            />
                            <p className="text-xs text-gray-400 mt-2">
                                Con datos en BD: desde = 18 meses antes del ultimo mes con serie. Sin datos: mismos 18 meses respecto al mes actual. Luego pulsá Aplicar.
                            </p>
                        </div>

                        <button type="button" onClick={handleApplyFilters} className="btn-primary w-full">
                            Aplicar filtros
                        </button>
                        {errorMsg && (
                            <p className="text-xs text-red-700 bg-red-50 border border-red-100 rounded-lg px-2 py-2 mt-2" role="alert">{errorMsg}</p>
                        )}

                        <div className="border-t border-gray-200 pt-3">
                            <h3 className="text-sm font-semibold text-gray-800 mb-2">Rubros IPC</h3>
                            <p className="text-xs text-gray-500 mb-2">Pulsa <span className="font-mono text-indigo-600">+</span> para desplegar (el arbol se precarga al abrir la pestaña). Marca varios rubros para comparar.</p>
                            {ipcLoad.rubrosErr && (
                                <p className="text-xs text-red-800 bg-red-50 border border-red-200 rounded-lg p-2 mb-2">
                                    Error al cargar rubros (codigo {String(ipcLoad.rubrosErr)}).
                                </p>
                            )}
                            {divisiones.length === 0 ? (
                                <div className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
                                    <p>No hay rubros en la respuesta de la API.</p>
                                    <p>
                                        Cargá el maestro una vez:{' '}
                                        <code className="bg-amber-100 px-1 rounded">python scripts/carga_inicial_ipc_desagregados_desde_export.py</code>
                                        {' '}(Excel tipo export, columna <code className="bg-amber-100 px-1 rounded">nivel</code>).
                                    </p>
                                    <p className="text-amber-800">
                                        Si ya cargaste datos y la columna <code className="bg-amber-100 px-1 rounded">nivel</code> es NULL, recargá la pagina: el servidor ahora tambien lista filas COICOP de solo-división sin nivel.
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-0.5">
                                    {divisiones.map(r => (
                                        <IPCEvolucionTreeNode key={r.id} rubro={r} selectedIds={selectedIds} onToggle={toggleId} depth={0} rubrosCacheRef={rubrosCacheRef} />
                                    ))}
                                </div>
                            )}
                            <div className="mt-3 pt-2 border-t border-gray-100 flex flex-wrap gap-2">
                                <button type="button" className="text-xs text-indigo-600 hover:underline"
                                    onClick={() => setSelectedIds(general ? [general.id] : [])}>Solo general</button>
                                <button type="button" className="text-xs text-indigo-600 hover:underline"
                                    onClick={() => setSelectedIds([])}>Limpiar seleccion</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
            <div className={fullscreen ? 'col-span-1' : 'lg:col-span-3'}>
                {fullscreen && errorMsg && (
                    <div className="card mb-4 bg-red-50 border border-red-100 text-sm text-red-800">{errorMsg}</div>
                )}

                {!fullscreen && appliedDesde && appliedHasta && (
                    <p className="text-xs text-gray-500 mb-2">Mostrando: {appliedDesde} a {appliedHasta} ({appliedIds.length} serie{appliedIds.length !== 1 ? 's' : ''})</p>
                )}

                {loadingSeries ? (
                    <div className="card"><div className="flex items-center justify-center py-12"><div className="text-center">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
                        <p className="text-gray-600">Cargando datos...</p>
                    </div></div></div>
                ) : seriesData.length > 0 ? (
                    <div className={`card ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                        <div className="flex justify-between items-center mb-3">
                            <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>Variacion interanual</h2>
                            <button type="button" onClick={() => setFullscreen(!fullscreen)}
                                className="px-3 py-1.5 rounded-lg transition-all bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    {fullscreen
                                        ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />}
                                </svg>
                            </button>
                        </div>
                        <div className="mb-3 flex flex-wrap items-center gap-4 text-sm">
                            <label className="flex items-center gap-2 text-gray-700 cursor-pointer">
                                <input type="checkbox" checked={autoScale} onChange={e => setAutoScale(e.target.checked)}
                                    className="h-3.5 w-3.5 text-indigo-600 border-gray-300 rounded" />
                                Eje Y automatico
                            </label>
                            {!autoScale && (
                                <div className="flex flex-wrap items-center gap-3 text-gray-600">
                                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Eje Y (%)</span>
                                    <label className="flex items-center gap-1.5">
                                        <span className="text-xs">Min</span>
                                        <input type="text" inputMode="decimal" value={yMinStr} onChange={e => setYMinStr(e.target.value)}
                                            className="w-16 border border-gray-300 rounded px-2 py-1 text-sm" placeholder="0" />
                                    </label>
                                    <label className="flex items-center gap-1.5">
                                        <span className="text-xs">Max</span>
                                        <input type="text" inputMode="decimal" value={yMaxStr} onChange={e => setYMaxStr(e.target.value)}
                                            className="w-16 border border-gray-300 rounded px-2 py-1 text-sm" placeholder="8" />
                                    </label>
                                </div>
                            )}
                        </div>
                        <div style={{height: fullscreen ? 'calc(100vh - 120px)' : '500px', position:'relative'}}>
                            <canvas ref={chartRef}></canvas>
                        </div>
                        <p className="text-xs text-gray-400 mt-2 text-right">Banda gris: rango meta BCU (3%-6%) | Linea negra: objetivo 4.5%</p>
                    </div>
                ) : appliedIds.length > 0 && !loadingSeries ? (
                    <div className="card"><div className="flex items-center justify-center py-12">
                        <p className="text-gray-500">No hay datos para el periodo y rubros elegidos (revisá vistas <code className="text-gray-700">v_ipc_inflacion</code> y valores en BD).</p>
                    </div></div>
                ) : (
                    <div className="card border border-dashed border-gray-200 bg-white">
                        <h3 className="text-sm font-semibold text-gray-800 mb-2">Variación interanual</h3>
                        <p className="text-sm text-gray-600 mb-3">
                            Elegí mes/año desde–hasta y rubros a la izquierda y pulsá <strong>Aplicar filtros</strong>. Con GENERAL y datos en base, el gráfico aparece acá al cargar.
                        </p>
                        {!hayFechasEnBd && !ipcLoad.fechasErr && (
                            <p className="text-xs text-blue-900 bg-blue-50 border border-blue-100 rounded-lg p-2">
                                Sin filas en <code className="bg-blue-100 px-1 rounded">ipc_desagregados_valores</code> el gráfico quedará vacío hasta correr el ETL de valores.
                            </p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}


// ═══════════════════════════════════════════════════════════════
// TAB 2: Cascada waterfall (floating bars)
// ═══════════════════════════════════════════════════════════════
function CascadaTab({fechas}) {
    const chartRef = React.useRef(null);
    const chartInst = React.useRef(null);
    const [fecha, setFecha] = React.useState(fechas[0] || '');
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [fullscreen, setFullscreen] = React.useState(false);

    React.useEffect(() => {
        if (!fecha) return;
        setLoading(true);
        fetch('/api/analisis-ipc/cascada?fecha=' + fecha)
            .then(r => r.json())
            .then(d => { setData(d); setLoading(false); })
            .catch(() => setLoading(false));
    }, [fecha]);

    useChartDelayed(chartRef, chartInst, (ctx) => {
        if (!data || !data.divisiones || data.divisiones.length === 0) return null;
        const sorted = [...data.divisiones].sort((a, b) => a.aporte - b.aporte);
        const labels = sorted.map(d => d.etiqueta);
        labels.push('TOTAL');

        // Floating bars: cada dato es [start, end]
        const floatingData = [];
        const colors = [];
        let running = 0;
        for (const item of sorted) {
            const start = running;
            running += item.aporte;
            floatingData.push([start, running]);
            colors.push(item.aporte >= 0 ? 'rgba(59,130,246,0.85)' : 'rgba(239,68,68,0.85)');
        }
        // Barra TOTAL: de 0 al total
        floatingData.push([0, running]);
        colors.push('rgba(99,102,241,0.85)');

        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Aporte',
                    data: floatingData,
                    backgroundColor: colors,
                    borderWidth: 0,
                    barPercentage: 0.7,
                    categoryPercentage: 0.85,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: {display: false},
                    tooltip: {callbacks: {label: ctx2 => {
                        const idx = ctx2.dataIndex;
                        if (idx === sorted.length) return 'Total: ' + running.toFixed(2) + '%';
                        const val = sorted[idx].aporte;
                        return sorted[idx].etiqueta + ': ' + (val >= 0 ? '+' : '') + val.toFixed(2) + '%';
                    }}},
                    title: {display: true, text: 'Impacto en la inflacion por division', font: {size: 16, weight: 'bold'}},
                },
                scales: {
                    x: {ticks: {maxRotation: 55, font: {size: 10}}},
                    y: {ticks: {callback: v => v.toFixed(1) + '%'}, title: {display: true, text: 'Aporte (pp)'}},
                },
            },
            plugins: [{
                id: 'wfLabels', afterDraw(chart) {
                    const meta = chart.getDatasetMeta(0); const c = chart.ctx;
                    c.save(); c.font = '10px Inter, sans-serif'; c.textAlign = 'center';
                    meta.data.forEach((bar, i) => {
                        const val = (i === sorted.length) ? running : sorted[i].aporte;
                        c.fillStyle = val >= 0 ? '#1e40af' : '#991b1b';
                        const yTop = Math.min(bar.y, bar.base);
                        const yBot = Math.max(bar.y, bar.base);
                        const yPos = val >= 0 ? yTop - 6 : yBot + 14;
                        c.fillText((val >= 0 ? '+' : '') + val.toFixed(2) + '%', bar.x, yPos);
                    }); c.restore();
                },
            }, {
                id: 'wfConnectors', afterDraw(chart) {
                    const meta = chart.getDatasetMeta(0); const c = chart.ctx;
                    c.save(); c.strokeStyle = '#9ca3af'; c.lineWidth = 1; c.setLineDash([3,3]);
                    for (let i = 0; i < meta.data.length - 2; i++) {
                        const curr = meta.data[i];
                        const next = meta.data[i + 1];
                        const yEnd = sorted[i].aporte >= 0 ? curr.y : curr.base;
                        c.beginPath(); c.moveTo(curr.x + curr.width/2, yEnd);
                        c.lineTo(next.x - next.width/2, yEnd); c.stroke();
                    }
                    c.restore();
                },
            }],
        });
    }, [data, fullscreen]);

    const formatMes = (f) => { try { return new Date(f + 'T12:00:00').toLocaleDateString('es-UY', {month:'long', year:'numeric'}); } catch(e) { return f; } };

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                    <label className="text-sm font-medium text-gray-700">Mes de analisis:</label>
                    <select value={fecha} onChange={e => setFecha(e.target.value)} className="text-sm border border-gray-300 rounded-lg px-3 py-2">
                        {fechas.map(f => <option key={f} value={f}>{(() => { try { return new Date(f+'T12:00:00').toLocaleDateString('es-UY',{month:'short',year:'numeric'}); } catch(e) { return f; }})()}</option>)}
                    </select>
                </div>
                {data && (
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span>Inflacion interanual <strong className="text-gray-900">{formatMes(fecha)}</strong>: <strong className="text-indigo-600 ml-1">{(data.inflacion_general || 0).toFixed(2)}%</strong></span>
                        <span className="text-gray-400">|</span>
                        <span>Suma aportes: <strong>{(data.suma_aportes || 0).toFixed(2)}%</strong></span>
                    </div>
                )}
            </div>
            {loading ? (
                <div className="card"><div className="flex items-center justify-center py-12"><div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
                    <p className="text-gray-600">Cargando datos...</p>
                </div></div></div>
            ) : data && data.divisiones ? (
                <>
                    <div className={`card ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                        <div className="flex justify-between items-center mb-4">
                            <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>Impacto en la inflacion por division</h2>
                            <button onClick={() => setFullscreen(!fullscreen)} className="px-3 py-1.5 rounded-lg transition-all bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    {fullscreen ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                 : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />}
                                </svg>
                            </button>
                        </div>
                        <div style={{height: fullscreen ? 'calc(100vh - 120px)' : '500px', position:'relative'}}><canvas ref={chartRef}></canvas></div>
                    </div>
                    <div className="card">
                        <h3 className="text-xl font-semibold text-gray-900 mb-4">Detalle Numerico</h3>
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50"><tr>
                                    {['Division','Ponderacion','Inflacion propia','Aporte a inflacion'].map(h =>
                                        <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">{h}</th>)}
                                </tr></thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {[...data.divisiones].sort((a,b) => b.aporte - a.aporte).map(d => (
                                        <tr key={d.division} className="hover:bg-gray-50">
                                            <td className="px-4 py-3 text-sm font-medium text-gray-900">{d.etiqueta}</td>
                                            <td className="px-4 py-3 text-sm text-gray-700 text-right">{(d.ponderacion * 100).toFixed(1)}%</td>
                                            <td className={`px-4 py-3 text-sm text-right ${d.inflacion_propia != null ? (d.inflacion_propia >= 0 ? 'text-red-500' : 'text-green-600') : 'text-gray-400'}`}>
                                                {d.inflacion_propia != null ? (d.inflacion_propia >= 0 ? '+' : '') + d.inflacion_propia.toFixed(2) + '%' : '-'}
                                            </td>
                                            <td className={`px-4 py-3 text-sm text-right font-semibold ${d.aporte >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                                                {(d.aporte >= 0 ? '+' : '') + d.aporte.toFixed(2)}%</td>
                                        </tr>
                                    ))}
                                    <tr className="bg-gray-50 font-bold">
                                        <td className="px-4 py-3 text-sm text-gray-900">TOTAL</td>
                                        <td className="px-4 py-3 text-sm text-right">100.0%</td>
                                        <td className="px-4 py-3 text-sm text-right text-red-500">{(data.inflacion_general || 0).toFixed(2)}%</td>
                                        <td className="px-4 py-3 text-sm text-right text-indigo-600">{(data.inflacion_general || 0).toFixed(2)}%</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            ) : null}
        </div>
    );
}


// ═══════════════════════════════════════════════════════════════
// TAB 3: Impacto por division — barras apiladas + linea inflacion general
// ═══════════════════════════════════════════════════════════════
function ContribucionesTab({fechas, divisiones}) {
    const chartRef = React.useRef(null);
    const chartInst = React.useRef(null);
    const [fullscreen, setFullscreen] = React.useState(false);
    const divsOnly = React.useMemo(
        () => divisiones.filter(d => String(d.division) !== '99'),
        [divisiones],
    );
    const divsKey = divsOnly.map(d => String(d.division)).sort().join('|');
    const [selectedDivs, setSelectedDivs] = React.useState([]);
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [fechaDesde, setFechaDesde] = React.useState('');
    const [fechaHasta, setFechaHasta] = React.useState('');
    const [detalleFecha, setDetalleFecha] = React.useState('');
    const [cascadaDetalle, setCascadaDetalle] = React.useState(null);
    const [loadingDetalle, setLoadingDetalle] = React.useState(false);

    const ultimaFechaClave = fechas.length > 0 ? fechas[0] : '';
    React.useEffect(() => {
        if (!fechas || fechas.length === 0) return;
        const { desde, hasta } = ipcRangoDefault18Meses(fechas);
        setFechaDesde(desde);
        setFechaHasta(hasta);
    }, [ultimaFechaClave]);

    React.useEffect(() => {
        if (divsOnly.length === 0) {
            setSelectedDivs([]);
            return;
        }
        setSelectedDivs(divsOnly.map(d => d.division));
    }, [divsKey]);

    React.useEffect(() => {
        if (fechaHasta) setDetalleFecha(fechaHasta);
    }, [fechaHasta]);

    React.useEffect(() => {
        if (!fechaDesde || !fechaHasta) return;
        setLoading(true);
        fetch('/api/analisis-ipc/contribuciones-serie?fecha_desde=' + fechaDesde + '&fecha_hasta=' + fechaHasta)
            .then(r => r.json()).then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
    }, [fechaDesde, fechaHasta]);

    React.useEffect(() => {
        if (!detalleFecha) return;
        setLoadingDetalle(true);
        fetch('/api/analisis-ipc/cascada?fecha=' + detalleFecha)
            .then(r => r.json())
            .then(d => { setCascadaDetalle(d.error ? null : d); setLoadingDetalle(false); })
            .catch(() => { setCascadaDetalle(null); setLoadingDetalle(false); });
    }, [detalleFecha]);

    const colorIdxByDivision = React.useMemo(() => {
        const m = {};
        divsOnly.forEach((d, i) => { m[d.division] = i; });
        return m;
    }, [divsKey]);

    useChartDelayed(chartRef, chartInst, (ctx) => {
        if (!data || !data.series) return null;
        const filtered = data.series.filter(s => selectedDivs.indexOf(s.division) !== -1);
        const allF = {};
        filtered.forEach(s => s.data.forEach(p => { allF[p.fecha] = true; }));
        if (data.inflacion_general) data.inflacion_general.forEach(p => { allF[p.fecha] = true; });
        const fSorted = Object.keys(allF).sort();
        const byInflG = {};
        if (data.inflacion_general) data.inflacion_general.forEach(p => { byInflG[p.fecha] = p.valor; });

        const barDatasets = filtered.map((s) => {
            const byF = {};
            s.data.forEach(p => { byF[p.fecha] = p.valor; });
            const ci = colorIdxByDivision[s.division] != null ? colorIdxByDivision[s.division] : 0;
            const hex = IPC_COLORS[ci % IPC_COLORS.length];
            return {
                type: 'bar',
                label: s.etiqueta,
                data: fSorted.map(f => (byF[f] != null ? byF[f] : 0)),
                stack: 'impacto',
                backgroundColor: hex.length === 7 ? hex + 'D9' : hex,
                borderWidth: 0,
                borderRadius: 2,
            };
        });

        const lineDataset = {
            type: 'line',
            label: 'Inflacion general',
            data: fSorted.map(f => (byInflG[f] != null ? byInflG[f] : null)),
            stack: '_infl_general',
            borderColor: '#111827',
            backgroundColor: 'transparent',
            borderWidth: 2.5,
            pointRadius: 2,
            tension: 0.25,
            borderDash: [6, 3],
            spanGaps: true,
            order: 10,
            yAxisID: 'y',
        };

        const datasets = barDatasets.length > 0 ? [...barDatasets, lineDataset] : [lineDataset];

        return new Chart(ctx, {
            type: 'bar',
            data: { labels: fSorted.map(f => f.slice(0, 7)), datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12, font: { size: 10 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx2) => {
                                const v = ctx2.parsed.y;
                                if (v == null) return ctx2.dataset.label + ': -';
                                return ctx2.dataset.label + ': ' + Number(v).toFixed(2) + '%';
                            },
                        },
                    },
                    title: {
                        display: true,
                        text: 'Evolucion del impacto por division (aporte apilado) e inflacion general',
                        font: { size: 16, weight: 'bold' },
                    },
                },
                scales: {
                    x: { stacked: true, ticks: { maxRotation: 45, font: { size: 10 } } },
                    y: {
                        stacked: true,
                        ticks: { callback: (v) => v.toFixed(2) + '%' },
                        title: { display: true, text: 'Aporte / inflacion (%)' },
                    },
                },
            },
        });
    }, [data, selectedDivs.join(','), fullscreen, divsKey]);

    const selectSoloDivision = (cod) => { setSelectedDivs([cod]); };
    const formatMesTabla = (f) => {
        try {
            return new Date(f + 'T12:00:00').toLocaleDateString('es-UY', { month: 'long', year: 'numeric' });
        } catch (e) {
            return f;
        }
    };

    return (
        <div className={`grid grid-cols-1 gap-6 ${fullscreen ? '' : 'lg:grid-cols-4'}`}>
            {!fullscreen && (
                <div className="lg:col-span-1"><div className="card sticky top-6">
                    <h3 className="text-sm font-medium text-gray-700 mb-3">Rango de fechas</h3>
                    <div className="space-y-2 mb-4">
                        <div><label className="block text-xs text-gray-500 mb-1">Desde</label>
                            <select value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="w-full text-sm border border-gray-300 rounded-lg px-2 py-1.5">
                                {fechas.slice().reverse().map(f => <option key={f} value={f}>{f.slice(0,7)}</option>)}
                            </select></div>
                        <div><label className="block text-xs text-gray-500 mb-1">Hasta</label>
                            <select value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="w-full text-sm border border-gray-300 rounded-lg px-2 py-1.5">
                                {fechas.map(f => <option key={f} value={f}>{f.slice(0,7)}</option>)}
                            </select></div>
                    </div>
                    <h3 className="text-sm font-medium text-gray-700 mb-1">Divisiones</h3>
                    <p className="text-xs text-gray-500 mb-2">Clic en una fila: solo esa division. Todas / Ninguna abajo.</p>
                    <div className="space-y-1">
                        {divsOnly.map((d, i) => {
                            const isOn = selectedDivs.indexOf(d.division) !== -1;
                            return (
                                <button
                                    key={d.division}
                                    type="button"
                                    onClick={() => selectSoloDivision(d.division)}
                                    className={`w-full flex items-center gap-2 text-sm text-left py-1.5 px-2 rounded-md border transition-colors ${
                                        isOn ? 'border-indigo-200 bg-indigo-50/80 text-gray-900' : 'border-transparent hover:bg-gray-50 text-gray-400'
                                    }`}
                                >
                                    <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: IPC_COLORS[i % IPC_COLORS.length] }}></span>
                                    <span className="flex-1 truncate">{d.etiqueta}</span>
                                </button>
                            );
                        })}
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-200 flex flex-wrap gap-2">
                        <button type="button" className="text-xs text-indigo-600 hover:underline" onClick={() => setSelectedDivs(divsOnly.map(d => d.division))}>Todas</button>
                        <button type="button" className="text-xs text-indigo-600 hover:underline" onClick={() => setSelectedDivs([])}>Ninguna</button>
                    </div>
                </div></div>
            )}
            <div className={fullscreen ? 'col-span-1' : 'lg:col-span-3'}>
                <div className="space-y-6">
                    {loading ? (
                        <div className="card"><div className="flex items-center justify-center py-12"><div className="text-center">
                            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
                            <p className="text-gray-600">Cargando datos...</p>
                        </div></div></div>
                    ) : data && data.series ? (
                        <div className={`card ${fullscreen ? 'fixed inset-2 z-50 bg-white shadow-2xl' : ''}`}>
                            <div className="flex justify-between items-center mb-4">
                                <h2 className={`font-semibold text-gray-900 ${fullscreen ? 'text-2xl' : 'text-xl'}`}>Evolucion del impacto por division</h2>
                                <button type="button" onClick={() => setFullscreen(!fullscreen)} className="px-3 py-1.5 rounded-lg transition-all bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        {fullscreen ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                     : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />}
                                    </svg>
                                </button>
                            </div>
                            <div style={{ height: fullscreen ? 'calc(100vh - 120px)' : '500px', position: 'relative' }}><canvas ref={chartRef}></canvas></div>
                            <p className="text-xs text-gray-400 mt-2 text-right">Barras apiladas: aporte por division (mes). Linea negra punteada: inflacion general.</p>
                        </div>
                    ) : (
                        <div className="card"><div className="flex items-center justify-center py-12"><p className="text-gray-500">Sin datos en el periodo.</p></div></div>
                    )}

                    {!fullscreen && data && data.series && (
                        <div className="card">
                            <div className="flex flex-wrap items-center gap-4 mb-4">
                                <h3 className="text-xl font-semibold text-gray-900">Detalle numerico por mes</h3>
                                <div className="flex items-center gap-2">
                                    <label className="text-sm font-medium text-gray-700">Mes:</label>
                                    <select value={detalleFecha} onChange={e => setDetalleFecha(e.target.value)} className="text-sm border border-gray-300 rounded-lg px-3 py-2">
                                        {fechas.map(f => (
                                            <option key={f} value={f}>{(() => { try { return new Date(f + 'T12:00:00').toLocaleDateString('es-UY', { month: 'short', year: 'numeric' }); } catch (e) { return f; } })()}</option>
                                        ))}
                                    </select>
                                </div>
                                {cascadaDetalle && (
                                    <div className="text-sm text-gray-600">
                                        Inflacion interanual <strong className="text-gray-900">{formatMesTabla(detalleFecha)}</strong>:
                                        <strong className="text-indigo-600 ml-1">{(cascadaDetalle.inflacion_general || 0).toFixed(2)}%</strong>
                                        <span className="text-gray-400 mx-2">|</span>
                                        Suma aportes: <strong>{(cascadaDetalle.suma_aportes || 0).toFixed(2)}%</strong>
                                    </div>
                                )}
                            </div>
                            {loadingDetalle ? (
                                <p className="text-sm text-gray-500">Cargando detalle...</p>
                            ) : cascadaDetalle && cascadaDetalle.divisiones ? (
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50"><tr>
                                            {['Division', 'Ponderacion', 'Inflacion propia', 'Aporte a inflacion'].map(h =>
                                                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">{h}</th>)}
                                        </tr></thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {[...cascadaDetalle.divisiones].sort((a, b) => b.aporte - a.aporte).map(d => (
                                                <tr key={d.division} className="hover:bg-gray-50">
                                                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{d.etiqueta}</td>
                                                    <td className="px-4 py-3 text-sm text-gray-700 text-right">{(d.ponderacion * 100).toFixed(1)}%</td>
                                                    <td className={`px-4 py-3 text-sm text-right ${d.inflacion_propia != null ? (d.inflacion_propia >= 0 ? 'text-red-500' : 'text-green-600') : 'text-gray-400'}`}>
                                                        {d.inflacion_propia != null ? (d.inflacion_propia >= 0 ? '+' : '') + d.inflacion_propia.toFixed(2) + '%' : '-'}
                                                    </td>
                                                    <td className={`px-4 py-3 text-sm text-right font-semibold ${d.aporte >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                                                        {(d.aporte >= 0 ? '+' : '') + d.aporte.toFixed(2)}%</td>
                                                </tr>
                                            ))}
                                            <tr className="bg-gray-50 font-bold">
                                                <td className="px-4 py-3 text-sm text-gray-900">TOTAL</td>
                                                <td className="px-4 py-3 text-sm text-right">100.0%</td>
                                                <td className="px-4 py-3 text-sm text-right text-red-500">{(cascadaDetalle.inflacion_general || 0).toFixed(2)}%</td>
                                                <td className="px-4 py-3 text-sm text-right text-indigo-600">{(cascadaDetalle.inflacion_general || 0).toFixed(2)}%</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <p className="text-sm text-gray-500">No hay detalle para ese mes (revisá datos de cascada en BD).</p>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
