import axios from 'axios';

// In production, use relative URLs. In development, use localhost or env var
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.PROD ? '' : 'http://localhost:8000');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Product {
  id: number;
  nombre: string;
  tipo: string;
  unidad: string | null;
  categoria: string | null;
  fuente: string;
  periodicidad: string;
}

export interface PriceData {
  fecha: string;
  valor: number;
}

export interface TimeSeriesData {
  producto: Product;
  precios: PriceData[];
}

export interface Variation {
  id: number;
  nombre: string;
  unidad: string | null;
  precio_inicial: number;
  precio_final: number;
  variacion_percent: number;
}

export interface Stats {
  precio_actual: number | null;
  precio_minimo: number | null;
  precio_maximo: number | null;
  variacion_periodo: number | null;
  fecha_minima: string | null;
  fecha_maxima: string | null;
}

export const apiService = {
  // Get all products
  getProducts: async (): Promise<Product[]> => {
    const response = await api.get<Product[]>('/api/products');
    return response.data;
  },

  // Get prices for a single product
  getProductPrices: async (
    productId: number,
    fechaDesde?: string,
    fechaHasta?: string
  ): Promise<PriceData[]> => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    
    const response = await api.get<PriceData[]>(
      `/api/products/${productId}/prices?${params.toString()}`
    );
    return response.data;
  },

  // Get prices for multiple products
  getMultipleProductsPrices: async (
    productIds: number[],
    fechaDesde?: string,
    fechaHasta?: string
  ): Promise<TimeSeriesData[]> => {
    const params = new URLSearchParams();
    productIds.forEach(id => params.append('product_ids[]', id.toString()));
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    
    const response = await api.get<TimeSeriesData[]>(
      `/api/products/prices?${params.toString()}`
    );
    return response.data;
  },

  // Get price variations
  getVariations: async (
    fechaDesde: string,
    fechaHasta: string,
    orderBy: 'asc' | 'desc' = 'desc'
  ): Promise<Variation[]> => {
    const params = new URLSearchParams({
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
      order_by: orderBy,
    });
    
    const response = await api.get<Variation[]>(
      `/api/variations?${params.toString()}`
    );
    return response.data;
  },

  // Get product statistics
  getProductStats: async (
    productId: number,
    fechaDesde?: string,
    fechaHasta?: string
  ): Promise<Stats> => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    
    const response = await api.get<Stats>(
      `/api/stats/${productId}?${params.toString()}`
    );
    return response.data;
  },
};
