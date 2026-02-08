"""Diagnóstico: Verificar registros de IPC para inflación en dólares."""
import sqlite3
import os

DB_PATH = os.path.join('backend', 'series_tiempo.db')

def diagnosticar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 80)
    print("DIAGNÓSTICO: IPC para inflación en dólares")
    print("=" * 80)
    
    # Países de filtros_graph_pais para graph 3
    paises_ids = [76, 152, 484, 604, 858]  # Brasil, Chile, México, Perú, Uruguay
    
    for id_pais in paises_ids:
        # Obtener nombre del país
        cursor.execute("SELECT nombre_pais_grupo FROM pais_grupo WHERE id_pais = ?", (id_pais,))
        pais_row = cursor.fetchone()
        nombre_pais = pais_row['nombre_pais_grupo'] if pais_row else f"id={id_pais}"
        
        print(f"\n--- {nombre_pais} (id_pais={id_pais}) ---")
        
        # Buscar registros de IPC (periodicidad = 'M', nombre contiene IPC)
        query_ipc = """
            SELECT 
                m.id_variable,
                m.id_pais,
                v.id_nombre_variable,
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
            GROUP BY m.id_variable, m.id_pais, v.id_nombre_variable, m.periodicidad, m.activo
        """
        cursor.execute(query_ipc, (id_pais,))
        ipc_records = cursor.fetchall()
        
        if ipc_records:
            for row in ipc_records:
                activo_str = "SÍ" if row['activo'] == 1 else "NO"
                print(f"  ✓ IPC encontrado:")
                print(f"    - id_variable: {row['id_variable']}")
                print(f"    - nombre: {row['id_nombre_variable']}")
                print(f"    - activo: {activo_str}")
                print(f"    - cantidad_datos: {row['cantidad_datos']}")
        else:
            print(f"  ✗ NO se encontró IPC para este país")
            
            # Verificar si hay algún registro de maestro con periodicidad M para este país
            cursor.execute("""
                SELECT m.id_variable, v.id_nombre_variable, m.periodicidad, m.activo
                FROM maestro m
                LEFT JOIN variables v ON m.id_variable = v.id_variable
                WHERE m.id_pais = ? AND m.periodicidad = 'M'
                LIMIT 5
            """, (id_pais,))
            otros_mensuales = cursor.fetchall()
            if otros_mensuales:
                print(f"    (Pero hay {len(otros_mensuales)} registros mensuales para este país)")
                for row in otros_mensuales:
                    print(f"      - {row['id_nombre_variable']} (id_variable={row['id_variable']}, activo={row['activo']})")
        
        # Verificar cotizaciones (periodicidad = 'D')
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM maestro m
            WHERE m.id_pais = ?
            AND m.periodicidad = 'D'
            AND (m.activo = 1 OR CAST(m.activo AS INTEGER) = 1)
        """, (id_pais,))
        cotizacion_count = cursor.fetchone()['count']
        print(f"  Cotizaciones diarias (activas): {cotizacion_count}")
    
    conn.close()

if __name__ == "__main__":
    diagnosticar()
