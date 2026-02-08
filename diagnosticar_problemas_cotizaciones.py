"""Script para diagnosticar problemas en cotizaciones e inflación en dólares."""
import sqlite3
import os

DB_PATH = os.path.join('backend', 'series_tiempo.db')

def diagnosticar():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("DIAGNÓSTICO: Problemas en Cotizaciones e Inflación en Dólares")
    print("=" * 80)
    
    # 1. Verificar países en filtros_graph_pais
    print("\n1. PAÍSES EN FILTROS_GRAPH_PAIS")
    print("-" * 80)
    
    # Graph 2 (Cotizaciones)
    cursor.execute("""
        SELECT f.id_pais, pg.nombre_pais_grupo, COUNT(*) as count
        FROM filtros_graph_pais f
        LEFT JOIN pais_grupo pg ON f.id_pais = pg.id_pais
        WHERE f.id_graph = 2
        GROUP BY f.id_pais, pg.nombre_pais_grupo
        ORDER BY pg.nombre_pais_grupo
    """)
    print("\n  Graph 2 (Cotizaciones):")
    for row in cursor.fetchall():
        print(f"    - id_pais {row[0]}: {row[1]} (aparece {row[2]} veces)")
    
    # Graph 3 (Inflación en dólares)
    cursor.execute("""
        SELECT f.id_pais, pg.nombre_pais_grupo, COUNT(*) as count
        FROM filtros_graph_pais f
        LEFT JOIN pais_grupo pg ON f.id_pais = pg.id_pais
        WHERE f.id_graph = 3
        GROUP BY f.id_pais, pg.nombre_pais_grupo
        ORDER BY pg.nombre_pais_grupo
    """)
    print("\n  Graph 3 (Inflación en dólares):")
    for row in cursor.fetchall():
        print(f"    - id_pais {row[0]}: {row[1]} (aparece {row[2]} veces)")
    
    # 2. Verificar cotizaciones para Chile (duplicados)
    print("\n2. COTIZACIONES PARA CHILE (verificar duplicados)")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            m.id_variable, 
            m.id_pais,
            v.id_nombre_variable as nombre,
            pg.nombre_pais_grupo as pais,
            m.periodicidad,
            m.activo,
            COUNT(mp.fecha) as cantidad_datos
        FROM maestro m
        LEFT JOIN variables v ON m.id_variable = v.id_variable
        LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
        LEFT JOIN maestro_precios mp ON m.id_variable = mp.id_variable AND m.id_pais = mp.id_pais
        WHERE pg.nombre_pais_grupo LIKE '%Chile%'
        AND m.periodicidad = 'D'
        AND (m.activo = 1 OR CAST(m.activo AS INTEGER) = 1)
        GROUP BY m.id_variable, m.id_pais, v.id_nombre_variable, pg.nombre_pais_grupo, m.periodicidad, m.activo
        ORDER BY pg.nombre_pais_grupo, v.id_nombre_variable
    """)
    print("\n  Cotizaciones de Chile:")
    for row in cursor.fetchall():
        print(f"    - id_variable={row[0]}, id_pais={row[1]}: {row[2]} ({row[3]}) - {row[5]} datos")
    
    # 3. Verificar Argentina (Oficial vs Informal)
    print("\n3. ARGENTINA: OFICIAL vs INFORMAL")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            m.id_variable, 
            m.id_pais,
            v.id_nombre_variable as nombre,
            pg.nombre_pais_grupo as pais,
            m.periodicidad,
            m.activo,
            COUNT(mp.fecha) as cantidad_datos,
            MIN(mp.fecha) as fecha_min,
            MAX(mp.fecha) as fecha_max
        FROM maestro m
        LEFT JOIN variables v ON m.id_variable = v.id_variable
        LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
        LEFT JOIN maestro_precios mp ON m.id_variable = mp.id_variable AND m.id_pais = mp.id_pais
        WHERE pg.nombre_pais_grupo LIKE '%Argentina%'
        AND m.periodicidad = 'D'
        AND (m.activo = 1 OR CAST(m.activo AS INTEGER) = 1)
        GROUP BY m.id_variable, m.id_pais, v.id_nombre_variable, pg.nombre_pais_grupo, m.periodicidad, m.activo
        ORDER BY pg.nombre_pais_grupo, v.id_nombre_variable
    """)
    print("\n  Cotizaciones de Argentina:")
    for row in cursor.fetchall():
        print(f"    - id_variable={row[0]}, id_pais={row[1]}: {row[2]} ({row[3]})")
        print(f"      Datos: {row[6]} registros, desde {row[7]} hasta {row[8]}")
    
    # 4. Verificar Uruguay (duplicados en inflación en dólares)
    print("\n4. URUGUAY: COTIZACIONES (para inflación en dólares)")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            m.id_variable, 
            m.id_pais,
            v.id_nombre_variable as nombre,
            pg.nombre_pais_grupo as pais,
            m.periodicidad,
            m.activo,
            COUNT(mp.fecha) as cantidad_datos
        FROM maestro m
        LEFT JOIN variables v ON m.id_variable = v.id_variable
        LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
        LEFT JOIN maestro_precios mp ON m.id_variable = mp.id_variable AND m.id_pais = mp.id_pais
        WHERE pg.nombre_pais_grupo LIKE '%Uruguay%'
        AND m.periodicidad = 'D'
        AND (m.activo = 1 OR CAST(m.activo AS INTEGER) = 1)
        GROUP BY m.id_variable, m.id_pais, v.id_nombre_variable, pg.nombre_pais_grupo, m.periodicidad, m.activo
        ORDER BY pg.nombre_pais_grupo, v.id_nombre_variable
    """)
    print("\n  Cotizaciones de Uruguay:")
    for row in cursor.fetchall():
        print(f"    - id_variable={row[0]}, id_pais={row[1]}: {row[2]} ({row[3]}) - {row[6]} datos")
    
    # 5. Verificar IPC para países en filtros_graph_pais graph 3
    print("\n5. IPC DISPONIBLE PARA PAÍSES EN FILTROS_GRAPH_PAIS (Graph 3)")
    print("-" * 80)
    cursor.execute("""
        SELECT DISTINCT f.id_pais, pg.nombre_pais_grupo
        FROM filtros_graph_pais f
        LEFT JOIN pais_grupo pg ON f.id_pais = pg.id_pais
        WHERE f.id_graph = 3
        ORDER BY pg.nombre_pais_grupo
    """)
    paises_graph3 = cursor.fetchall()
    
    for id_pais, nombre_pais in paises_graph3:
        print(f"\n  {nombre_pais} (id_pais={id_pais}):")
        cursor.execute("""
            SELECT 
                m.id_variable,
                m.id_pais,
                v.id_nombre_variable as nombre,
                m.periodicidad,
                m.activo,
                COUNT(mp.fecha) as cantidad_datos
            FROM maestro m
            LEFT JOIN variables v ON m.id_variable = v.id_variable
            LEFT JOIN maestro_precios mp ON m.id_variable = mp.id_variable AND m.id_pais = mp.id_pais
            WHERE m.id_pais = ?
            AND m.periodicidad = 'M'
            AND (
                v.id_nombre_variable LIKE '%IPC%' 
                OR v.id_nombre_variable LIKE '%índice de precios%' 
                OR v.id_nombre_variable LIKE '%indice de precios%'
            )
            AND (m.activo = 1 OR CAST(m.activo AS INTEGER) = 1)
            GROUP BY m.id_variable, m.id_pais, v.id_nombre_variable, m.periodicidad, m.activo
        """, (id_pais,))
        ipc_records = cursor.fetchall()
        if ipc_records:
            for row in ipc_records:
                print(f"    - IPC: id_variable={row[0]}, {row[2]} - {row[5]} datos")
        else:
            print(f"    - [SIN IPC] No se encontró IPC para este país")
    
    conn.close()

if __name__ == "__main__":
    diagnosticar()
