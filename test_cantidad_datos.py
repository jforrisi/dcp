"""Test script para verificar cantidad_datos."""
import sqlite3
import sys
import os

# Asegurar que estamos en el directorio correcto
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'backend', 'series_tiempo.db')

if not os.path.exists(db_path):
    print(f"ERROR: No se encuentra la base de datos en {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("VERIFICACIÓN: Cantidad de datos en maestro_precios")
print("=" * 80)

# 1. Total de registros
cursor.execute("SELECT COUNT(*) FROM maestro_precios")
total = cursor.fetchone()[0]
print(f"\n1. Total registros en maestro_precios: {total}")

# 2. Verificar algunos registros de maestro_precios
cursor.execute("""
    SELECT id_variable, id_pais, COUNT(*) as cnt 
    FROM maestro_precios 
    GROUP BY id_variable, id_pais 
    ORDER BY cnt DESC 
    LIMIT 5
""")
print("\n2. Top 5 combinaciones en maestro_precios:")
for row in cursor.fetchall():
    print(f"   id_variable={row[0]}, id_pais={row[1]}: {row[2]} registros")

# 3. Verificar algunos registros de maestro
cursor.execute("""
    SELECT m.id_variable, m.id_pais, v.id_nombre_variable, pg.nombre_pais_grupo
    FROM maestro m
    LEFT JOIN variables v ON m.id_variable = v.id_variable
    LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
    LIMIT 5
""")
print("\n3. Primeros 5 registros de maestro:")
for row in cursor.fetchall():
    id_var, id_pais, nombre, pais = row[0], row[1], row[2], row[3]
    # Verificar cantidad de datos
    cursor.execute("""
        SELECT COUNT(*) 
        FROM maestro_precios 
        WHERE id_variable = ? AND id_pais = ?
    """, (id_var, id_pais))
    count = cursor.fetchone()[0]
    print(f"   id_variable={id_var}, id_pais={id_pais}: {nombre} ({pais}) - {count} datos")

# 4. Probar la query exacta del endpoint
print("\n4. Probando query del endpoint (primeros 3 registros):")
cursor.execute("""
    SELECT m.id_variable, m.id_pais, v.id_nombre_variable, pg.nombre_pais_grupo,
           COALESCE((
               SELECT COUNT(*) 
               FROM maestro_precios mp 
               WHERE mp.id_variable = m.id_variable AND mp.id_pais = m.id_pais
           ), 0) as cantidad_datos
    FROM maestro m
    LEFT JOIN variables v ON m.id_variable = v.id_variable
    LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
    LIMIT 3
""")
for row in cursor.fetchall():
    print(f"   id_variable={row[0]}, id_pais={row[1]}: {row[2]} ({row[3]}) - cantidad_datos={row[4]}")

# 5. Verificar si hay registros en maestro_precios que no coinciden con maestro
cursor.execute("""
    SELECT COUNT(DISTINCT mp.id_variable || '_' || mp.id_pais) as mp_combos
    FROM maestro_precios mp
    LEFT JOIN maestro m ON mp.id_variable = m.id_variable AND mp.id_pais = m.id_pais
    WHERE m.id_variable IS NULL
""")
sin_maestro = cursor.fetchone()[0]
print(f"\n5. Combinaciones en maestro_precios sin registro en maestro: {sin_maestro}")

conn.close()
