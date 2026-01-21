"""
Script para exportar la tabla maestro completa a Excel
"""
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "series_tiempo.db"
EXCEL_NAME = "maestro_completo.xlsx"

# Conectar a la base de datos
conn = sqlite3.connect(DB_NAME)

# Leer la tabla maestro
df_maestro = pd.read_sql_query("SELECT * FROM maestro ORDER BY id", conn)

# Cerrar conexión
conn.close()

# Generar Excel
excel_path = EXCEL_NAME
df_maestro.to_excel(excel_path, index=False, engine="openpyxl")

print(f"[OK] Archivo Excel generado: {excel_path}")
print(f"   Total de registros: {len(df_maestro)}")
print(f"\nColumnas:")
for col in df_maestro.columns:
    print(f"   - {col}")

print(f"\nPrimeros registros:")
print(df_maestro.head().to_string(index=False))
