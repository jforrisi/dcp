"""
Script para migrar datos de SQLite a PostgreSQL.
Uso:
  1. Crear Azure PostgreSQL y obtener DATABASE_URL
  2. Ejecutar schema_postgresql.sql en la base vacía
  3. python scripts/migrate_sqlite_to_postgres.py

Variables de entorno:
  DATABASE_URL: postgresql://user:pass@host:5432/dbname
  SQLITE_PATH: ruta a series_tiempo.db (default: series_tiempo.db en raíz)
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SQLITE_PATH = Path(os.environ.get("SQLITE_PATH", str(PROJECT_ROOT / "series_tiempo.db")))
DATABASE_URL = os.environ.get("DATABASE_URL")

TABLES_ORDER = [
    "pais_grupo",
    "familia",
    "tipo_serie",
    "sub_familia",
    "variables",
    "graph",
    "filtros_graph_pais",
    "maestro",
    "maestro_precios",
]


def main():
    if not DATABASE_URL or not DATABASE_URL.startswith(("postgresql://", "postgres://")):
        print("[ERROR] Definí DATABASE_URL con la conexión a PostgreSQL")
        print("  Ejemplo: postgresql://user:pass@host:5432/dbname")
        sys.exit(1)

    if not SQLITE_PATH.exists():
        print(f"[ERROR] No se encuentra SQLite en: {SQLITE_PATH}")
        sys.exit(1)

    import sqlite3
    import psycopg2
    from psycopg2.extras import execute_values

    print(f"[INFO] Origen SQLite: {SQLITE_PATH}")
    print(f"[INFO] Destino PostgreSQL: {DATABASE_URL.split('@')[-1]}")
    print()

    sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(DATABASE_URL)
    valid_id_variables = set()
    valid_id_paises = set()

    try:
        for table in TABLES_ORDER:
            cur_check = sqlite_conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cur_check.fetchone():
                print(f"[SKIP] Tabla {table} no existe en SQLite")
                continue

            cursor_sqlite = sqlite_conn.cursor()
            cursor_sqlite.execute(f"SELECT * FROM {table}")
            rows = cursor_sqlite.fetchall()
            col_names = [d[0] for d in cursor_sqlite.description]

            if not rows:
                print(f"[OK] {table}: 0 filas (vacía)")
                continue

            # Construir INSERT (execute_values usa un solo %s)
            cols = col_names
            if table == "maestro_precios" and "id" in col_names:
                cols = [c for c in col_names if c != "id"]  # SERIAL auto-genera id
            cols_str = ", ".join(f'"{c}"' for c in cols)
            insert_sql = f'INSERT INTO {table} ({cols_str}) VALUES %s'
            # ON CONFLICT para saltar duplicados
            if table == "variables":
                insert_sql += " ON CONFLICT (id_variable) DO NOTHING"
            elif table == "maestro_precios":
                pass  # Sin unique en (id_variable, id_pais, fecha), insertar todo
            elif table in ("pais_grupo", "familia", "tipo_serie", "sub_familia", "graph"):
                pk_col = {"pais_grupo": "id_pais", "familia": "id_familia", "tipo_serie": "id_tipo_serie",
                          "sub_familia": "id_sub_familia", "graph": "id_graph"}[table]
                insert_sql += f" ON CONFLICT ({pk_col}) DO NOTHING"
            elif table == "filtros_graph_pais":
                insert_sql += " ON CONFLICT (id_graph, id_pais) DO NOTHING"
            elif table == "maestro":
                insert_sql += " ON CONFLICT (id) DO NOTHING"

            # Convertir filas a listas (manejar fechas, bytes, etc.)
            values = []
            for row in rows:
                vals = list(row)
                for i, v in enumerate(vals):
                    if v is None:
                        continue
                    if hasattr(v, "isoformat"):
                        vals[i] = v.isoformat()
                    elif isinstance(v, bytes):
                        # SQLite guarda algunos int como bytes; convertir a int
                        try:
                            vals[i] = int.from_bytes(v, "little") if len(v) <= 8 else v.decode("utf-8", errors="replace")
                        except Exception:
                            vals[i] = 1 if v else 0
                values.append(tuple(vals))

            # Filtrar maestro por FKs válidos (variables y pais_grupo ya migrados)
            if table == "maestro" and "id_variable" in col_names and "id_pais" in col_names:
                idx_var = col_names.index("id_variable")
                idx_pais = col_names.index("id_pais")
                rows = [r for r in rows if r[idx_var] in valid_id_variables and r[idx_pais] in valid_id_paises]
                if len(rows) == 0:
                    print(f"[WARN] {table}: 0 filas después de filtrar por FK")
                    continue
                # Reconstruir values desde rows filtrados
                values = []
                for row in rows:
                    vals = list(row)
                    for i, v in enumerate(vals):
                        if v is None:
                            continue
                        if hasattr(v, "isoformat"):
                            vals[i] = v.isoformat()
                        elif isinstance(v, bytes):
                            try:
                                vals[i] = int.from_bytes(v, "little") if len(v) <= 8 else v.decode("utf-8", errors="replace")
                            except Exception:
                                vals[i] = 1 if v else 0
                    values.append(tuple(vals))

            # maestro_precios: filtrar por FKs válidos y excluir id (SERIAL auto-genera)
            if table == "maestro_precios" and "id_variable" in col_names and "id_pais" in col_names:
                idx_var = col_names.index("id_variable")
                idx_pais = col_names.index("id_pais")
                idx_id = col_names.index("id") if "id" in col_names else -1
                rows = [r for r in rows if r[idx_var] in valid_id_variables and r[idx_pais] in valid_id_paises]
                values = []
                for row in rows:
                    vals = [row[i] for i in range(len(row)) if i != idx_id] if idx_id >= 0 else list(row)
                    for i, v in enumerate(vals):
                        if v is None:
                            continue
                        if hasattr(v, "isoformat"):
                            vals[i] = v.isoformat()
                        elif isinstance(v, bytes):
                            try:
                                vals[i] = int.from_bytes(v, "little") if len(v) <= 8 else v.decode("utf-8", errors="replace")
                            except Exception:
                                vals[i] = 1 if v else 0
                    values.append(tuple(vals))

            try:
                with pg_conn.cursor() as cur:
                    execute_values(cur, insert_sql, values, page_size=500)
                pg_conn.commit()
                print(f"[OK] {table}: {len(rows)} filas migradas")
                if table == "pais_grupo" and "id_pais" in col_names:
                    valid_id_paises = {r[col_names.index("id_pais")] for r in rows}
                if table == "variables" and "id_variable" in col_names:
                    valid_id_variables = {r[col_names.index("id_variable")] for r in rows}
            except Exception as e:
                pg_conn.rollback()
                print(f"[ERROR] {table}: {e}")
                raise

        print()
        print("[OK] Migración completada")
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
