"""
Módulo de conexión a base de datos.
PostgreSQL vía DATABASE_URL (Azure/producción).
"""
from .connection import (
    get_db_connection,
    get_db_engine,
    execute_query,
    execute_query_single,
    execute_update,
    insert_dataframe,
    is_postgresql,
)

__all__ = [
    "get_db_connection",
    "get_db_engine",
    "execute_query",
    "execute_query_single",
    "execute_update",
    "insert_dataframe",
    "is_postgresql",
]
