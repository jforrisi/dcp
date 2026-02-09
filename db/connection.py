"""
Abstracción de conexión a base de datos.
Solo PostgreSQL vía DATABASE_URL (Azure/producción).
"""
import os
from pathlib import Path
from typing import Optional, Any

PROJECT_ROOT = Path(__file__).parent.parent

# Cargar .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def _get_database_url() -> Optional[str]:
    """Obtiene DATABASE_URL del entorno."""
    return os.environ.get("DATABASE_URL")


def _require_postgresql() -> str:
    """Obtiene DATABASE_URL o lanza error si no está configurada."""
    url = _get_database_url()
    if not url or not (url.startswith("postgresql://") or url.startswith("postgres://")):
        raise RuntimeError(
            "Configure DATABASE_URL para PostgreSQL. "
            "Ejemplo: postgresql://user:pass@host:5432/macrodata?sslmode=require"
        )
    return url


def is_postgresql() -> bool:
    """True si DATABASE_URL está configurada para PostgreSQL."""
    url = _get_database_url()
    return url is not None and (
        url.startswith("postgresql://") or url.startswith("postgres://")
    )


def get_db_connection(db_path: Optional[str] = None):
    """
    Devuelve una conexión a PostgreSQL.
    db_path se ignora (mantenido por compatibilidad).
    """
    url = _require_postgresql()
    import psycopg2
    from psycopg2.extras import RealDictCursor
    conn = psycopg2.connect(url)
    conn.cursor_factory = RealDictCursor
    return conn


def get_db_engine():
    """Devuelve SQLAlchemy engine para PostgreSQL."""
    from sqlalchemy import create_engine
    return create_engine(_require_postgresql())


def _convert_value(value: Any) -> Any:
    """Convierte bytes a string para JSON."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("utf-8", errors="replace")
    return value


def _row_to_dict(row) -> dict:
    """Convierte una fila a diccionario."""
    if hasattr(row, "keys"):
        return {k: _convert_value(row[k]) for k in row.keys()}
    return dict(row)


def _prepare_query_pg(query: str) -> str:
    """Convierte placeholders ? a %s para PostgreSQL."""
    return query.replace("?", "%s")


def execute_query(query: str, params: tuple = (), db_path: Optional[str] = None) -> list:
    """Ejecuta SELECT y devuelve lista de dicts."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(_prepare_query_pg(query), params)
        rows = cursor.fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def execute_query_single(query: str, params: tuple = (), db_path: Optional[str] = None) -> Optional[dict]:
    """Ejecuta SELECT y devuelve un solo resultado como dict."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(_prepare_query_pg(query), params)
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def execute_update(query: str, params: tuple = (), db_path: Optional[str] = None) -> tuple[bool, Optional[str], Optional[int]]:
    """Ejecuta INSERT, UPDATE o DELETE. Returns: (success, error_message, lastrowid)"""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        q = _prepare_query_pg(query)
        cursor.execute(q, params)
        conn.commit()
        lastrowid = None
        if "INSERT" in q.upper():
            try:
                cursor.execute("SELECT LASTVAL()")
                row = cursor.fetchone()
                lastrowid = row[0] if row else None
            except Exception:
                pass
        return (True, None, lastrowid)
    except Exception as e:
        conn.rollback()
        return (False, str(e), None)
    finally:
        conn.close()


def insert_dataframe(
    table: str,
    df,
    if_exists: str = "append",
    index: bool = False,
    db_path: Optional[str] = None,
):
    """Inserta un DataFrame en una tabla usando PostgreSQL."""
    engine = get_db_engine()
    df.to_sql(table, engine, if_exists=if_exists, index=index, method="multi")
