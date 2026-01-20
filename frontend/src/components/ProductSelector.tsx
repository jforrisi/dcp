import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';

interface ProductSelectorProps {
  selectedProducts: number[];
  onSelectionChange: (productIds: number[]) => void;
}

export default function ProductSelector({ selectedProducts, onSelectionChange }: ProductSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: products = [], isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: apiService.getProducts,
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredProducts = products.filter((product) =>
    product.nombre.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const toggleProduct = (productId: number) => {
    if (selectedProducts.includes(productId)) {
      onSelectionChange(selectedProducts.filter((id) => id !== productId));
    } else {
      onSelectionChange([...selectedProducts, productId]);
    }
  };

  const selectedProductsData = products.filter((p) => selectedProducts.includes(p.id));

  return (
    <div className="relative" ref={dropdownRef}>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Productos
      </label>
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="input-field cursor-pointer flex items-center justify-between"
      >
        <span className="text-gray-600">
          {selectedProducts.length === 0
            ? 'Selecciona productos...'
            : `${selectedProducts.length} producto${selectedProducts.length > 1 ? 's' : ''} seleccionado${selectedProducts.length > 1 ? 's' : ''}`}
        </span>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-hidden">
          <div className="p-3 border-b border-gray-200">
            <input
              type="text"
              placeholder="Buscar productos..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent outline-none"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <div className="overflow-y-auto max-h-80">
            {isLoading ? (
              <div className="p-4 text-center text-gray-500">Cargando...</div>
            ) : filteredProducts.length === 0 ? (
              <div className="p-4 text-center text-gray-500">No se encontraron productos</div>
            ) : (
              filteredProducts.map((product) => (
                <label
                  key={product.id}
                  className="flex items-center p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                >
                  <input
                    type="checkbox"
                    checked={selectedProducts.includes(product.id)}
                    onChange={() => toggleProduct(product.id)}
                    className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <div className="ml-3 flex-1">
                    <div className="text-sm font-medium text-gray-900">{product.nombre}</div>
                    {product.unidad && (
                      <div className="text-xs text-gray-500">{product.unidad}</div>
                    )}
                  </div>
                </label>
              ))
            )}
          </div>
        </div>
      )}

      {selectedProductsData.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {selectedProductsData.map((product) => (
            <span
              key={product.id}
              className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-primary/10 text-primary border border-primary/20"
            >
              {product.nombre}
              <button
                onClick={() => toggleProduct(product.id)}
                className="ml-2 text-primary hover:text-primary-dark"
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
