"""Exportar tabla maestro completa a Excel."""
import sqlite3
import pandas as pd
from datetime import datetime

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("EXPORTANDO MAESTRO COMPLETO A EXCEL")
print("=" * 80)

# Obtener todos los registros del maestro
query = """
    SELECT 
        id,
        nombre,
        tipo,
        fuente,
        periodicidad,
        unidad,
        categoria,
        activo,
        moneda,
        nominal_real,
        es_cotizacion
    FROM maestro
    ORDER BY id
"""

df = pd.read_sql_query(query, conn)

print(f"\nTotal de registros: {len(df)}")
print(f"\nColumnas: {list(df.columns)}")

# Mostrar resumen
print("\n" + "=" * 80)
print("RESUMEN POR TIPO")
print("=" * 80)
print(df['tipo'].value_counts())

print("\n" + "=" * 80)
print("RESUMEN POR PERIODICIDAD")
print("=" * 80)
print(df['periodicidad'].value_counts())

print("\n" + "=" * 80)
print("COTIZACIONES (es_cotizacion = 1)")
print("=" * 80)
cotizaciones = df[df['es_cotizacion'] == 1]
print(f"Total: {len(cotizaciones)}")
if len(cotizaciones) > 0:
    print("\nIDs marcados como cotizaciones:")
    for idx, row in cotizaciones.iterrows():
        print(f"  ID {row['id']}: {row['nombre'][:60]}... | activo={row['activo']} | tipo={row['tipo']} | periodicidad={row['periodicidad']}")

# Exportar a Excel
excel_file = "maestro_completo.xlsx"
df.to_excel(excel_file, index=False, sheet_name='maestro')
print(f"\n✓ Exportado a: {excel_file}")

conn.close()
print("\n" + "=" * 80)
print("EXPORTACIÓN COMPLETA")
print("=" * 80)
