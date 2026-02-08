"""Análisis para decidir si separar datos diarios en otra tabla"""

import sqlite3
import os

DB_NAME = "series_tiempo.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

print("=" * 80)
print("ANÁLISIS: ¿SEPARAR DATOS DIARIOS EN OTRA TABLA?")
print("=" * 80)

# 1. Estado actual
cursor.execute("SELECT COUNT(*) FROM maestro_precios")
total_actual = cursor.fetchone()[0]

cursor.execute("""
    SELECT m.periodicidad, COUNT(DISTINCT m.id_variable) as vars, COUNT(mp.id) as registros
    FROM maestro m
    LEFT JOIN maestro_precios mp ON m.id_variable = mp.id_variable AND m.id_pais = mp.id_pais
    GROUP BY m.periodicidad
""")
periodicidades = cursor.fetchall()

print("\n1. ESTADO ACTUAL DE maestro_precios:")
print(f"   Total de registros: {total_actual:,}")
print(f"\n   Registros por periodicidad:")
for per, vars_count, regs in periodicidades:
    per_str = per or "NULL"
    print(f"     {per_str:<5} | {vars_count:>3} variables | {regs:>8,} registros")

# 2. Proyección con curva de pesos
nuevos_registros = 2190 * 15  # 32,850
total_proyectado = total_actual + nuevos_registros

print(f"\n2. PROYECCIÓN CON CURVA DE PESOS:")
print(f"   Registros a agregar: {nuevos_registros:,}")
print(f"   Total proyectado: {total_proyectado:,}")

# 3. Tamaño estimado de la tabla
cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
db_size = cursor.fetchone()[0]
print(f"\n3. TAMAÑO DE BASE DE DATOS:")
print(f"   Tamaño actual: {db_size / (1024*1024):.2f} MB")

# 4. Variables diarias actuales
cursor.execute("""
    SELECT COUNT(DISTINCT m.id_variable) as vars_diarias
    FROM maestro m
    WHERE m.periodicidad = 'D'
""")
vars_diarias = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(mp.id) as regs_diarios
    FROM maestro_precios mp
    JOIN maestro m ON mp.id_variable = m.id_variable AND mp.id_pais = m.id_pais
    WHERE m.periodicidad = 'D'
""")
regs_diarios = cursor.fetchone()[0]

print(f"\n4. VARIABLES DIARIAS ACTUALES:")
print(f"   Variables con periodicidad 'D': {vars_diarias}")
print(f"   Registros diarios actuales: {regs_diarios:,}")

# 5. Índices existentes
cursor.execute("""
    SELECT name, sql 
    FROM sqlite_master 
    WHERE type='index' AND tbl_name='maestro_precios'
""")
indices = cursor.fetchall()

print(f"\n5. ÍNDICES EN maestro_precios:")
for idx_name, idx_sql in indices:
    print(f"   - {idx_name}")

print("\n" + "=" * 80)
print("RECOMENDACION:")
print("=" * 80)
print("""
MANTENER TODO EN maestro_precios:

VENTAJAS:
  - SQLite puede manejar facilmente 125K+ registros
  - Estructura normalizada y consistente
  - Queries mas simples (sin UNIONs)
  - Indices ya optimizados para busquedas
  - Codigo backend ya migrado y funcionando
  - Mantenimiento mas simple

DESVENTAJAS DE SEPARAR:
  - Queries mas complejas (necesitarian UNIONs o multiples queries)
  - Mas codigo de mantenimiento
  - Riesgo de inconsistencias entre tablas
  - Sin beneficio real de performance (SQLite maneja bien este volumen)

CONCLUSION:
  Mantener todo en maestro_precios es la mejor opcion.
  Solo considerar separar si llegas a millones de registros.
""")

conn.close()
