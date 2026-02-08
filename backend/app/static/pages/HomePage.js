// Página Home - Dashboard de Análisis Macroeconómicos y Financieros
function HomePage() {
    const [tickerData, setTickerData] = React.useState([]);
    const [loadingTicker, setLoadingTicker] = React.useState(true);

    // Cargar datos del ticker
    React.useEffect(() => {
        const fetchTickerData = async () => {
            try {
                const response = await fetch('/api/ticker/ticker');
                const result = await response.json();
                if (result.success && result.data) {
                    setTickerData(result.data);
                }
            } catch (error) {
                console.error('Error cargando datos del ticker:', error);
            } finally {
                setLoadingTicker(false);
            }
        };

        fetchTickerData();
        // Actualizar cada 5 minutos
        const interval = setInterval(fetchTickerData, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    const modulos = [
        {
            id: 'dcp',
            nombre: 'MacroData',
            descripcion: 'Análisis de precios corrientes y en pesos uruguayos constantes',
            icono: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
            ),
            color: 'from-blue-500 to-blue-600'
        },
        {
            id: 'cotizaciones',
            nombre: 'Cotizaciones de monedas',
            descripcion: 'Evolución de tipos de cambio y cotizaciones',
            icono: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            ),
            color: 'from-green-500 to-green-600'
        },
        {
            id: 'inflacion-dolares',
            nombre: 'Inflación en dólares',
            descripcion: 'Análisis de inflación expresada en dólares por país',
            icono: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
            ),
            color: 'from-purple-500 to-purple-600'
        },
        {
            id: 'yield-curve',
            nombre: 'Curva de Rendimiento',
            descripcion: 'Curva de rendimiento y análisis temporal de tasas',
            icono: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
            ),
            color: 'from-indigo-500 to-indigo-600'
        },
        {
            id: 'licitaciones-lrm',
            nombre: 'Licitaciones LRM',
            descripcion: 'Análisis de licitaciones LRM del BCU con comparación BEVSA',
            icono: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
            ),
            color: 'from-teal-500 to-teal-600'
        },
        {
            id: 'data-export',
            nombre: 'Descarga de Datos',
            descripcion: 'Exporta datos personalizados a Excel',
            icono: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
            ),
            color: 'from-orange-500 to-orange-600'
        }
    ];

    // Obtener onPageChange desde el contexto global o evento
    const handleSelectModule = (moduleId) => {
        // Disparar evento personalizado para cambiar de página
        window.dispatchEvent(new CustomEvent('navigateToModule', { detail: { moduleId } }));
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Ticker estilo Wall Street */}
            {!loadingTicker && tickerData.length > 0 && (
                <div className="sticky top-0 z-50 shadow-lg">
                    <Ticker data={tickerData} />
                </div>
            )}

            <div className="p-6">
                <div className="max-w-7xl mx-auto">
                    {/* Header */}
                    <div className="text-center mb-12">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">
                        ANÁLISIS MACROECONÓMICOS Y FINANCIEROS
                    </h1>
                    <p className="text-lg text-gray-600">
                        Seleccione un módulo para comenzar el análisis
                    </p>
                </div>

                {/* Grid de módulos */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {modulos.map((modulo) => (
                        <div
                            key={modulo.id}
                            onClick={() => handleSelectModule(modulo.id)}
                            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md hover:border-indigo-300 transition-all group"
                        >
                            <div className="flex items-start gap-4">
                                <div className={`w-16 h-16 bg-gradient-to-br ${modulo.color} rounded-lg flex items-center justify-center text-white flex-shrink-0 group-hover:scale-110 transition-transform`}>
                                    {modulo.icono}
                                </div>
                                <div className="flex-1">
                                    <h3 className="text-xl font-semibold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors">
                                        {modulo.nombre}
                                    </h3>
                                    <p className="text-gray-600 text-sm">
                                        {modulo.descripcion}
                                    </p>
                                </div>
                                <svg className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </div>
                        </div>
                    ))}
                </div>

                </div>
            </div>
        </div>
    );
}
