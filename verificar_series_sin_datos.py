"""
Script para verificar qué series no tienen datos en maestro_precios
"""
import sqlite3
import pandas as pd

DB_NAME = "series_tiempo.db"

conn = sqlite3.connect(DB_NAME)

# Obtener todas las series con conteo de registros
query = """
    SELECT 
        m.id,
        m.nombre,
        m.tipo,
        m.periodicidad,
        m.activo,
        COUNT(mp.id) as total_registros
    FROM maestro m
    LEFT JOIN maestro_precios mp ON m.id = mp.maestro_id
    GROUP BY m.id, m.nombre, m.tipo, m.periodicidad, m.activo
    ORDER BY m.id
"""

df_series = pd.read_sql_query(query, conn)

conn.close()

print("=" * 100)
print("VERIFICACION DE DATOS POR SERIE")
print("=" * 100)

# Separar series con y sin datos
series_con_datos = df_series[df_series['total_registros'] > 0]
series_sin_datos = df_series[df_series['total_registros'] == 0]

print(f"\nTotal de series: {len(df_series)}")
print(f"Series con datos: {len(series_con_datos)}")
print(f"Series sin datos: {len(series_sin_datos)}")

if len(series_sin_datos) > 0:
    print("\n" + "=" * 100)
    print("SERIES SIN DATOS:")
    print("=" * 100)
    print(f"\n{'ID':<5} {'Nombre':<50} {'Tipo':<5} {'Periodicidad':<12} {'Activo':<8}")
    print("-" * 100)
    
    for _, row in series_sin_datos.iterrows():
        activo_str = "SI" if row['activo'] == 1 else "NO"
        print(f"{row['id']:<5} {row['nombre']:<50} {row['tipo']:<5} {row['periodicidad']:<12} {activo_str:<8}")
    
    print("\n" + "=" * 100)
    print("RESUMEN:")
    print("=" * 100)
    print(f"Total de series sin datos: {len(series_sin_datos)}")
    
    # Agrupar por tipo
    print("\nSeries sin datos por tipo:")
    sin_datos_por_tipo = series_sin_datos.groupby('tipo').size()
    for tipo, count in sin_datos_por_tipo.items():
        tipo_nombre = {"P": "Productos", "S": "Servicios", "M": "Macro"}.get(tipo, tipo)
        print(f"   {tipo_nombre} ({tipo}): {count}")
else:
    print("\n[OK] Todas las series tienen datos cargados")

print("\n" + "=" * 100)
print("TODAS LAS SERIES (con conteo de registros):")
print("=" * 100)
print(f"\n{'ID':<5} {'Nombre':<50} {'Tipo':<5} {'Registros':<12} {'Estado'}")
print("-" * 100)

for _, row in df_series.iterrows():
    estado = "CON DATOS" if row['total_registros'] > 0 else "SIN DATOS"
    print(f"{row['id']:<5} {row['nombre']:<50} {row['tipo']:<5} {row['total_registros']:<12} {estado}")

print("\n" + "=" * 100)
