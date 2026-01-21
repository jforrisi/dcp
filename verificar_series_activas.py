"""
Script para verificar el estado activo de todas las series
"""
import sqlite3
import pandas as pd

DB_NAME = "series_tiempo.db"

conn = sqlite3.connect(DB_NAME)

# Leer todas las series con su estado activo
df_maestro = pd.read_sql_query(
    "SELECT id, nombre, tipo, activo FROM maestro ORDER BY id",
    conn
)

conn.close()

print("=" * 80)
print("ESTADO DE SERIES EN LA BASE DE DATOS")
print("=" * 80)

# Contar por estado
total = len(df_maestro)
activas = len(df_maestro[df_maestro['activo'] == 1])
inactivas = len(df_maestro[df_maestro['activo'] == 0])

print(f"\nTotal de series: {total}")
print(f"Series activas: {activas}")
print(f"Series inactivas: {inactivas}")

# Mostrar todas las series con su estado
print("\n" + "=" * 80)
print("DETALLE POR SERIE")
print("=" * 80)
print(f"\n{'ID':<5} {'Estado':<10} {'Tipo':<5} {'Nombre'}")
print("-" * 80)

for _, row in df_maestro.iterrows():
    estado = "ACTIVA" if row['activo'] == 1 else "INACTIVA"
    estado_icono = "[OK]" if row['activo'] == 1 else "[X]"
    print(f"{row['id']:<5} {estado_icono} {estado:<8} {row['tipo']:<5} {row['nombre']}")

# Mostrar series inactivas si las hay
if inactivas > 0:
    print("\n" + "=" * 80)
    print("SERIES INACTIVAS:")
    print("=" * 80)
    inactivas_df = df_maestro[df_maestro['activo'] == 0]
    for _, row in inactivas_df.iterrows():
        print(f"  ID {row['id']}: {row['nombre']}")

print("\n" + "=" * 80)
