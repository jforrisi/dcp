// Componente de Navegación
function Navigation({ currentPage, onPageChange }) {
    const [isOpen, setIsOpen] = React.useState(false);
    const [searchTerm, setSearchTerm] = React.useState('');
    const dropdownRef = React.useRef(null);
    const inputRef = React.useRef(null);

    // Módulos disponibles
    const modulos = [
        { id: 'home', nombre: 'Inicio', displayName: 'Inicio' },
        { id: 'dcp', nombre: 'Precios de Exportación', displayName: 'Precios de Exportación' },
        { id: 'cotizaciones', nombre: 'Cotizaciones de monedas', displayName: 'Cotizaciones de monedas' },
        { id: 'inflacion-dolares', nombre: 'Inflación en dólares', displayName: 'Inflación en dólares' },
        { id: 'yield-curve', nombre: 'Curva de Rendimiento', displayName: 'Curva de Rendimiento' },
        { id: 'licitaciones-lrm', nombre: 'Licitaciones LRM', displayName: 'Licitaciones LRM' },
        { id: 'data-export', nombre: 'Descarga de Datos', displayName: 'Descarga de Datos' },
    ];

    // Normalizar currentPage para el selector (dcp y series son lo mismo)
    const currentPageNormalized = currentPage === 'series' ? 'dcp' : currentPage;
    const selectedModulo = modulos.find(m => m.id === currentPageNormalized) || null;

    const filteredModulos = modulos.filter(m => {
        const searchText = (m.displayName || m.nombre).toLowerCase();
        return searchText.includes(searchTerm.toLowerCase());
    });

    const handleSelectModulo = (id) => {
        onPageChange(id);
        setIsOpen(false);
        setSearchTerm('');
    };

    // Cerrar dropdown al hacer click fuera
    React.useEffect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
                setSearchTerm('');
            }
        };

        const timeoutId = setTimeout(() => {
            if (inputRef.current) {
                try {
                    inputRef.current.focus();
                } catch (e) {
                    // Ignorar errores de focus
                }
            }
        }, 50);

        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('touchstart', handleClickOutside);
        window.addEventListener('click', handleClickOutside, true);

        return () => {
            clearTimeout(timeoutId);
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('touchstart', handleClickOutside);
            window.removeEventListener('click', handleClickOutside, true);
        };
    }, [isOpen]);

    const handleToggle = (e) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setIsOpen(!isOpen);
    };

    return (
        <nav className="bg-white border-b border-gray-200 shadow-sm">
            <div className="w-full px-2 py-2">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                            </div>
                            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                                MacroData
                            </h1>
                        </div>
                        <button
                            onClick={() => onPageChange('home')}
                            className="px-3 py-1.5 text-sm font-medium text-gray-700 hover:text-indigo-600 hover:bg-gray-50 rounded-md transition-colors flex items-center gap-1.5"
                            title="Volver al inicio"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                            </svg>
                            <span>Home</span>
                        </button>
                    </div>

                    {/* Selector de módulo - minimalista, alineado a la derecha */}
                    <div className="flex items-center gap-3">
                        <span className="text-sm font-semibold text-gray-900 whitespace-nowrap">
                            SELECCIONE UN MÓDULO:
                        </span>
                        <div className="relative" ref={dropdownRef} style={{ minWidth: '200px' }}>
                            <div
                                onClick={handleToggle}
                                onTouchStart={(e) => {
                                    e.preventDefault();
                                    handleToggle(e);
                                }}
                                className="px-3 py-1.5 border border-gray-300 rounded-md cursor-pointer flex items-center justify-between hover:border-gray-400 transition-colors bg-white"
                                role="button"
                                tabIndex={0}
                                aria-expanded={isOpen}
                                aria-haspopup="listbox"
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault();
                                        handleToggle(e);
                                    }
                                }}
                            >
                                <span className="text-sm text-gray-700">
                                    {selectedModulo ? selectedModulo.displayName : 'Módulo'}
                                </span>
                                <svg
                                    className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'transform rotate-180' : ''}`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </div>

                            {isOpen && (
                                <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-hidden right-0">
                                    <div className="p-2 border-b border-gray-200">
                                        <input
                                            ref={inputRef}
                                            type="text"
                                            placeholder="Buscar..."
                                            value={searchTerm}
                                            onChange={(e) => setSearchTerm(e.target.value)}
                                            onClick={(e) => e.stopPropagation()}
                                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                        />
                                    </div>
                                    <div className="overflow-y-auto max-h-48">
                                        {filteredModulos.length > 0 ? (
                                            filteredModulos.map((modulo) => (
                                                <div
                                                    key={modulo.id}
                                                    onClick={() => handleSelectModulo(modulo.id)}
                                                    className={`px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 transition-colors ${
                                                        currentPageNormalized === modulo.id ? 'bg-indigo-50 text-indigo-600 font-medium' : 'text-gray-700'
                                                    }`}
                                                >
                                                    {modulo.displayName}
                                                </div>
                                            ))
                                        ) : (
                                            <div className="px-3 py-2 text-sm text-gray-500">No se encontraron módulos</div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
}
