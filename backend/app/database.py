"""Database connection and utilities for SQLite."""
import sqlite3
from pathlib import Path
from typing import Optional

# Path to the database file (in the root of the project)
DB_PATH = Path(__file__).parent.parent.parent / "series_tiempo.db"


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def execute_query(query: str, params: tuple = ()) -> list:
    """Execute a SELECT query and return results as list of dicts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def execute_query_single(query: str, params: tuple = ()) -> Optional[dict]:
    """Execute a SELECT query and return a single result as dict."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
