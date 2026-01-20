"""Pydantic models for API responses."""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class ProductResponse(BaseModel):
    """Product information."""
    id: int
    nombre: str
    tipo: str
    unidad: Optional[str] = None
    categoria: Optional[str] = None
    fuente: str
    periodicidad: str

    class Config:
        from_attributes = True


class PriceDataResponse(BaseModel):
    """Single price data point."""
    fecha: date
    valor: float

    class Config:
        from_attributes = True


class TimeSeriesDataResponse(BaseModel):
    """Time series data for a product."""
    producto: ProductResponse
    precios: List[PriceDataResponse]


class VariationResponse(BaseModel):
    """Price variation data."""
    id: int
    nombre: str
    unidad: Optional[str]
    precio_inicial: float
    precio_final: float
    variacion_percent: float


class StatsResponse(BaseModel):
    """Statistics for a product."""
    precio_actual: Optional[float]
    precio_minimo: Optional[float]
    precio_maximo: Optional[float]
    variacion_periodo: Optional[float]
    fecha_minima: Optional[date]
    fecha_maxima: Optional[date]
