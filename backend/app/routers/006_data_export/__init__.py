"""Data export module."""
from .router import bp

# Exportar el blueprint directamente
data_export = bp

__all__ = ['data_export']
