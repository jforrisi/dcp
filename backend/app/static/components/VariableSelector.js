// Componente de Selector de Variables (genérico: países/variables/productos)
function VariableSelector({ selectedProducts, onSelectionChange, products, allProducts }) {
    const [isOpen, setIsOpen] = React.useState(false);
    const [searchTerm, setSearchTerm] = React.useState('');
    const dropdownRef = React.useRef(null);
    const inputRef = React.useRef(null);

    const filteredProducts = products.filter(p => {
        const searchText = (p.displayName || p.nombre).toLowerCase();
        return searchText.includes(searchTerm.toLowerCase());
    });

    const toggleProduct = (id) => {
        if (selectedProducts.includes(id)) {
            onSelectionChange(selectedProducts.filter(i => i !== id));
        } else {
            onSelectionChange([...selectedProducts, id]);
        }
    };

    // Cerrar dropdown al hacer click fuera y auto-focus
    React.useEffect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };

        // Auto-focus en el input cuando se abre
        const timeoutId = setTimeout(() => {
            if (inputRef.current) {
                try {
                    inputRef.current.focus();
                } catch (e) {
                    // Ignorar errores de focus en algunos navegadores
                }
            }
        }, 50);

        // Agregar listeners para cerrar al hacer click fuera
        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('touchstart', handleClickOutside);
        // También escuchar clicks en el documento
        window.addEventListener('click', handleClickOutside, true);

        return () => {
            clearTimeout(timeoutId);
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('touchstart', handleClickOutside);
            window.removeEventListener('click', handleClickOutside, true);
        };
    }, [isOpen]);

    // Usar allProducts si está disponible, sino usar products
    const productsForDisplay = allProducts || products;

    const handleToggle = (e) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setIsOpen(!isOpen);
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <div
                onClick={handleToggle}
                onTouchStart={(e) => {
                    e.preventDefault();
                    handleToggle(e);
                }}
                className="input-field cursor-pointer flex items-center justify-between"
                role="button"
                tabIndex={0}
                aria-expanded={isOpen}
                aria-haspopup="listbox"
                onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
                        e.preventDefault();
                        handleToggle(e);
                    }
                }}
            >
                <span className="text-gray-600">
                    {selectedProducts.length === 0
                        ? 'Selecciona variables...'
                        : `${selectedProducts.length} variable${selectedProducts.length > 1 ? 's' : ''} seleccionada${selectedProducts.length > 1 ? 's' : ''}`}
                </span>
                <svg className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </div>

            {isOpen && (
                <div 
                    className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-hidden"
                    style={{ 
                        position: 'absolute', 
                        zIndex: 9999,
                        WebkitOverflowScrolling: 'touch'
                    }}
                    onClick={(e) => e.stopPropagation()}
                    onTouchStart={(e) => e.stopPropagation()}
                >
                    <div className="p-3 border-b border-gray-200">
                        <input
                            ref={inputRef}
                            type="text"
                            placeholder="Buscar variables..."
                            value={searchTerm}
                            onChange={(e) => {
                                e.stopPropagation();
                                setSearchTerm(e.target.value);
                            }}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                            onClick={(e) => e.stopPropagation()}
                            onTouchStart={(e) => e.stopPropagation()}
                            onFocus={(e) => e.stopPropagation()}
                            autoFocus={true}
                        />
                    </div>
                    <div 
                        className="overflow-y-auto max-h-80" 
                        style={{ WebkitOverflowScrolling: 'touch' }}
                    >
                        {filteredProducts.length === 0 ? (
                            <div className="p-3 text-center text-gray-500 text-sm">
                                No se encontraron variables
                            </div>
                        ) : (
                            filteredProducts.map((product) => (
                                <label
                                    key={product.id}
                                    className="flex items-center p-3 hover:bg-gray-50 active:bg-gray-100 cursor-pointer border-b border-gray-100 last:border-b-0"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                    }}
                                    onTouchStart={(e) => {
                                        e.stopPropagation();
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedProducts.includes(product.id)}
                                        onChange={(e) => {
                                            e.stopPropagation();
                                            toggleProduct(product.id);
                                        }}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                        }}
                                        onTouchStart={(e) => {
                                            e.stopPropagation();
                                        }}
                                        className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                                    />
                                    <div className="ml-3 flex-1">
                                        <div className="text-sm font-medium text-gray-900">{product.displayName || product.nombre}</div>
                                    </div>
                                </label>
                            ))
                        )}
                    </div>
                </div>
            )}

            {selectedProducts.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                    {productsForDisplay.filter(p => selectedProducts.includes(p.id)).map((product) => (
                        <span
                            key={product.id}
                            className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-indigo-100 text-indigo-700 border border-indigo-200"
                        >
                            {product.displayName || product.nombre}
                            <button
                                onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    toggleProduct(product.id);
                                }}
                                onTouchStart={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    toggleProduct(product.id);
                                }}
                                className="ml-2 text-indigo-700 hover:text-indigo-900 focus:outline-none"
                                type="button"
                                aria-label={`Eliminar ${product.nombre}`}
                            >
                                ×
                            </button>
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}
