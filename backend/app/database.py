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


def _convert_value(value):
    """Convert bytes to string for JSON serialization."""
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return value.decode('utf-8', errors='replace')
    return value

def execute_query(query: str, params: tuple = ()) -> list:
    """Execute a SELECT query and return results as list of dicts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    # Convert rows to dicts and handle bytes
    result = []
    for row in rows:
        row_dict = {}
        for key in row.keys():
            row_dict[key] = _convert_value(row[key])
        result.append(row_dict)
    return result


def execute_query_single(query: str, params: tuple = ()) -> Optional[dict]:
    """Execute a SELECT query and return a single result as dict."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    # Convert row to dict and handle bytes
    result = {}
    for key in row.keys():
        result[key] = _convert_value(row[key])
    return result


def execute_update(query: str, params: tuple = ()) -> tuple[bool, Optional[str], Optional[int]]:
    """
    Execute an INSERT, UPDATE, or DELETE query.
    Returns: (success: bool, error_message: Optional[str], lastrowid: Optional[int])
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        lastrowid = cursor.lastrowid
        conn.close()
        return (True, None, lastrowid)
    except Exception as e:
        conn.rollback()
        error_msg = str(e)
        conn.close()
        return (False, error_msg, None)
