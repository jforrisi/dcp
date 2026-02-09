"""Export SQLite schema for PostgreSQL migration."""
import sqlite3
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATHS = [
    PROJECT_ROOT / "series_tiempo.db",
    PROJECT_ROOT / "update" / "direct" / "series_tiempo.db",
    PROJECT_ROOT / "update" / "historicos" / "series_tiempo.db",
    PROJECT_ROOT / "backend" / "series_tiempo.db",
]


def main():
    db_path = None
    for p in DB_PATHS:
        if p.exists():
            db_path = p
            break

    if not db_path:
        print("No series_tiempo.db found")
        sys.exit(1)

    print(f"Using: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cursor.fetchall()]
    print("Tables:", tables)

    schema = []
    for t in tables:
        cursor.execute(f"PRAGMA table_info({t})")
        cols = cursor.fetchall()
        schema.append((t, cols))

    conn.close()
    return schema


if __name__ == "__main__":
    schema = main()
    for t, cols in schema:
        print(f"\n--- {t} ---")
        for c in cols:
            print(f"  {c[1]} {c[2]}")
