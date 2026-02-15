// Página Monitor Monetario LatAm
function PoliticaMonetariaPage() {
    const [data, setData] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);

    // Filtro de fechas para los gráficos (dd-mm-yyyy en inputs; internamente usamos yyyy-mm-dd para la API)
    const defaultHasta = () => {
        const d = new Date();
        return d.toISOString().slice(0, 10);
    };
    const defaultDesde = () => {
        const d = new Date();
        d.setFullYear(d.getFullYear() - 1);
        return d.toISOString().slice(0, 10);
    };
    const [fechaDesde, setFechaDesde] = React.useState(defaultDesde());
    const [fechaHasta, setFechaHasta] = React.useState(defaultHasta());
    const [tpmSeries, setTpmSeries] = React.useState([]);
    const [expSeries, setExpSeries] = React.useState([]);
    const [embiSeries, setEmbiSeries] = React.useState([]);
    const [monedasSeries, setMonedasSeries] = React.useState([]);
    const [loadingCharts, setLoadingCharts] = React.useState(false);

    React.useEffect(() => {
        fetch('/api/politica-monetaria')
            .then(res => {
                if (!res.ok) throw new Error('Error al cargar datos');
                return res.json();
            })
            .then(setData)
            .catch(e => {
                setError(e.message);
                setData([]);
            })
            .finally(() => setLoading(false));
    }, []);

    const cargarSeries = () => {
        setLoadingCharts(true);
        const params = new URLSearchParams({ desde: fechaDesde, hasta: fechaHasta });
        Promise.all([
            fetch(`/api/politica-monetaria/series/tpm?${params}`).then(r => r.json()),
            fetch(`/api/politica-monetaria/series/expectativas?${params}`).then(r => r.json()),
            fetch(`/api/politica-monetaria/series/embi?${params}`).then(r => r.json()),
            fetch(`/api/politica-monetaria/series/monedas?${params}`).then(r => r.json()),
        ])
            .then(([tpm, exp, embi, monedas]) => {
                setTpmSeries(Array.isArray(tpm) ? tpm : []);
                setExpSeries(Array.isArray(exp) ? exp : []);
                setEmbiSeries(Array.isArray(embi) ? embi : []);
                setMonedasSeries(Array.isArray(monedas) ? monedas : []);
            })
            .catch(() => {
                setTpmSeries([]);
                setExpSeries([]);
                setEmbiSeries([]);
                setMonedasSeries([]);
            })
            .finally(() => setLoadingCharts(false));
    };

    React.useEffect(() => {
        if (!fechaDesde || !fechaHasta) return;
        cargarSeries();
    }, []);

    const flagEmoji = (code) => {
        if (!code || code.length !== 2) return '';
        return code.split('').map(c => String.fromCodePoint(0x1F1E6 - 65 + c.charCodeAt(0))).join('');
    };

    const formatVariacionTpm = (row) => {
        if (row.variacion_tpm_pp == null) return '—';
        const sign = row.variacion_tpm_pp >= 0 ? '+' : '';
        const num = Number(row.variacion_tpm_pp);
        const pp = `${sign}${num} p.p.`;
        if (row.fecha_cambio_tpm) {
            const d = row.fecha_cambio_tpm.split('-');
            const short = d.length === 3 ? `${d[2].replace(/^0/, '')}-${d[1].replace(/^0/, '')}-${d[0].slice(-2)}` : row.fecha_cambio_tpm;
            return `${pp} (${short})`;
        }
        return pp;
    };

    const fmt = (v) => v != null ? Number(v).toFixed(2) : '—';

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 p-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-4">Monitor Monetario LatAm</h1>
                <p className="text-gray-600">Cargando...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 p-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-4">Monitor Monetario LatAm</h1>
                <p className="text-red-600">{error}</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Monitor Monetario LatAm</h1>

            {/* Tabla */}
            <div className="bg-white rounded-lg shadow overflow-hidden border border-gray-200 mb-8">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">País / Región</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Inflación interanual</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Expectativas de inflación</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Objetivo de inflación</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Tasa de política monetaria</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Variación TPM</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Tasa real</th>
                            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">EMBI</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {data.map((row, idx) => (
                            <tr key={row.id_pais} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                                    <span className="mr-2">{flagEmoji(row.codigo)}</span>
                                    {row.pais}
                                </td>
                                <td className={`px-4 py-3 whitespace-nowrap text-sm ${row.inflacion_en_rango ? 'text-green-600' : 'text-red-600'}`}>
                                    {row.inflacion_interanual != null ? `${fmt(row.inflacion_interanual)}%` : '—'}
                                </td>
                                <td className={`px-4 py-3 whitespace-nowrap text-sm ${row.expectativa_en_rango ? 'text-green-600' : 'text-red-600'}`}>
                                    {row.expectativas != null ? `${fmt(row.expectativas)}%` : '—'}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                    {row.objetivo || '—'}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                    {row.tpm != null ? `${fmt(row.tpm)}%` : '—'}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm font-bold text-gray-900">
                                    {formatVariacionTpm(row)}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                    {row.tasa_real != null ? `${fmt(row.tasa_real)}%` : '—'}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                                    {row.embi != null ? `${Number(row.embi).toFixed(0)} pb` : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Filtro de fechas para los gráficos (dd-mm-yyyy) */}
            <div className="mb-4 flex flex-wrap items-end gap-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Desde (dd-mm-aaaa)</label>
                    <input
                        type="date"
                        value={fechaDesde}
                        onChange={(e) => setFechaDesde(e.target.value)}
                        className="input-field w-40"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Hasta (dd-mm-aaaa)</label>
                    <input
                        type="date"
                        value={fechaHasta}
                        onChange={(e) => setFechaHasta(e.target.value)}
                        className="input-field w-40"
                    />
                </div>
                <button
                    type="button"
                    onClick={cargarSeries}
                    disabled={loadingCharts}
                    className="btn-primary px-4 py-2"
                >
                    {loadingCharts ? 'Cargando...' : 'Aplicar'}
                </button>
            </div>

            {/* Dos gráficos: TPM y Expectativas */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div className="bg-white rounded-lg shadow border border-gray-200 p-4">
                    <h2 className="text-lg font-semibold text-gray-800 mb-3">TPM</h2>
                    <div className="h-80">
                        {loadingCharts && tpmSeries.length === 0 ? (
                            <div className="flex items-center justify-center h-full text-gray-500">Cargando...</div>
                        ) : (
                            <CombinateChart data={tpmSeries} yAxisTitle="%" />
                        )}
                    </div>
                </div>
                <div className="bg-white rounded-lg shadow border border-gray-200 p-4">
                    <h2 className="text-lg font-semibold text-gray-800 mb-3">Expectativas de inflación</h2>
                    <div className="h-80">
                        {loadingCharts && expSeries.length === 0 ? (
                            <div className="flex items-center justify-center h-full text-gray-500">Cargando...</div>
                        ) : (
                            <CombinateChart data={expSeries} yAxisTitle="%" />
                        )}
                    </div>
                </div>
            </div>

            {/* Dos gráficos más: EMBI diario y Monedas (base 100) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg shadow border border-gray-200 p-4">
                    <h2 className="text-lg font-semibold text-gray-800 mb-3">EMBI (spread diario)</h2>
                    <div className="h-80">
                        {loadingCharts && embiSeries.length === 0 ? (
                            <div className="flex items-center justify-center h-full text-gray-500">Cargando...</div>
                        ) : (
                            <CombinateChart data={embiSeries} yAxisTitle="pb" />
                        )}
                    </div>
                </div>
                <div className="bg-white rounded-lg shadow border border-gray-200 p-4">
                    <h2 className="text-lg font-semibold text-gray-800 mb-3">Tipo de cambio USD/LC (base 100)</h2>
                    <div className="h-80">
                        {loadingCharts && monedasSeries.length === 0 ? (
                            <div className="flex items-center justify-center h-full text-gray-500">Cargando...</div>
                        ) : (
                            <CombinateChart data={monedasSeries} viewMode="base100" yAxisTitle="Base 100" />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
