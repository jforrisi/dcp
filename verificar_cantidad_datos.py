"""Script para verificar por qué cantidad_datos muestra 0 en maestro."""
import sqlite3
import os

DB_PATH = os.path.join('backend', 'series_tiempo.db')

def verificar():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("VERIFICACIÓN: Cantidad de datos en maestro_precios")
    print("=" * 80)
    
    # 1. Verificar total de registros en maestro_precios
    cursor.execute("SELECT COUNT(*) FROM maestro_precios")
    total = cursor.fetchone()[0]
    print(f"\n1. Total de registros en maestro_precios: {total}")
    
    # 2. Verificar combinaciones únicas
    cursor.execute("""
        SELECT COUNT(DISTINCT id_variable || '_' || id_pais) 
        FROM maestro_precios
    """)
    unicos = cursor.fetchone()[0]
    print(f"2. Combinaciones únicas (id_variable, id_pais): {unicos}")
    
    # 3. Top 10 combinaciones con más datos
    cursor.execute("""
        SELECT id_variable, id_pais, COUNT(*) as cnt 
        FROM maestro_precios 
        GROUP BY id_variable, id_pais 
        ORDER BY cnt DESC 
        LIMIT 10
    """)
    print("\n3. Top 10 combinaciones con más datos:")
    for row in cursor.fetchall():
        print(f"   id_variable={row[0]}, id_pais={row[1]}: {row[2]} registros")
    
    # 4. Verificar algunos registros de maestro
    cursor.execute("""
        SELECT m.id_variable, m.id_pais, v.id_nombre_variable, pg.nombre_pais_grupo
        FROM maestro m
        LEFT JOIN variables v ON m.id_variable = v.id_variable
        LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
        LIMIT 5
    """)
    print("\n4. Primeros 5 registros de maestro:")
    for row in cursor.fetchall():
        id_var, id_pais, nombre, pais = row
        # Verificar cantidad de datos para este registro
        cursor.execute("""
            SELECT COUNT(*) 
            FROM maestro_precios 
            WHERE id_variable = ? AND id_pais = ?
        """, (id_var, id_pais))
        count = cursor.fetchone()[0]
        print(f"   id_variable={id_var}, id_pais={id_pais}: {nombre} ({pais}) - {count} datos")
    
    # 5. Probar la query exacta que usa el endpoint
    print("\n5. Probando query del endpoint (primeros 3 registros):")
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
    
    # 6. Verificar si hay NULLs en id_variable o id_pais en maestro
    cursor.execute("""
        SELECT COUNT(*) 
        FROM maestro 
        WHERE id_variable IS NULL OR id_pais IS NULL
    """)
    nulls = cursor.fetchone()[0]
    print(f"\n6. Registros en maestro con id_variable o id_pais NULL: {nulls}")
    
    # 7. Verificar estructura de maestro_precios
    cursor.execute("PRAGMA table_info(maestro_precios)")
    columns = cursor.fetchall()
    print("\n7. Estructura de maestro_precios:")
    for col in columns:
        print(f"   - {col[1]} ({col[2]})")
    
    conn.close()

if __name__ == "__main__":
    verificar()
