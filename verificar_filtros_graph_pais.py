"""Script para verificar la tabla filtros_graph_pais y sus datos."""
import sqlite3
import os

DB_PATH = os.path.join('backend', 'series_tiempo.db')

def verificar_filtros_graph_pais():
    """Verifica si la tabla filtros_graph_pais existe y tiene datos."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='filtros_graph_pais'
        """)
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("[ERROR] La tabla 'filtros_graph_pais' NO existe")
            print("[INFO] Necesitas ejecutar la migración para crear la tabla")
            conn.close()
            return False
        
        print("[OK] La tabla 'filtros_graph_pais' existe")
        
        # Verificar datos para graph 2 (Cotizaciones)
        cursor.execute("""
            SELECT COUNT(*) FROM filtros_graph_pais WHERE id_graph = 2
        """)
        count_graph2 = cursor.fetchone()[0]
        print(f"\n[INFO] Registros para graph 2 (Cotizaciones): {count_graph2}")
        
        if count_graph2 > 0:
            cursor.execute("""
                SELECT f.id_pais, pg.nombre_pais_grupo 
                FROM filtros_graph_pais f
                LEFT JOIN pais_grupo pg ON f.id_pais = pg.id_pais
                WHERE f.id_graph = 2
                ORDER BY f.id_pais
            """)
            print("  Países para graph 2:")
            for row in cursor.fetchall():
                print(f"    - id_pais {row[0]}: {row[1]}")
        
        # Verificar datos para graph 3 (Inflación en dólares)
        cursor.execute("""
            SELECT COUNT(*) FROM filtros_graph_pais WHERE id_graph = 3
        """)
        count_graph3 = cursor.fetchone()[0]
        print(f"\n[INFO] Registros para graph 3 (Inflación en dólares): {count_graph3}")
        
        if count_graph3 > 0:
            cursor.execute("""
                SELECT f.id_pais, pg.nombre_pais_grupo 
                FROM filtros_graph_pais f
                LEFT JOIN pais_grupo pg ON f.id_pais = pg.id_pais
                WHERE f.id_graph = 3
                ORDER BY f.id_pais
            """)
            print("  Países para graph 3:")
            for row in cursor.fetchall():
                print(f"    - id_pais {row[0]}: {row[1]}")
            
            # Verificar si están los países esperados (76, 152, 484, 604, 858)
            expected_paises = [76, 152, 484, 604, 858]
            cursor.execute("""
                SELECT id_pais FROM filtros_graph_pais WHERE id_graph = 3
            """)
            actual_paises = [row[0] for row in cursor.fetchall()]
            
            print(f"\n[INFO] Países esperados para graph 3: {expected_paises}")
            print(f"[INFO] Países actuales para graph 3: {sorted(actual_paises)}")
            
            missing = set(expected_paises) - set(actual_paises)
            extra = set(actual_paises) - set(expected_paises)
            
            if missing:
                print(f"[WARN] Países faltantes: {sorted(missing)}")
            if extra:
                print(f"[WARN] Países adicionales: {sorted(extra)}")
            if not missing and not extra:
                print("[OK] Los países para graph 3 coinciden con los esperados")
        
        # Verificar estructura de la tabla
        cursor.execute("PRAGMA table_info(filtros_graph_pais)")
        columns = cursor.fetchall()
        print(f"\n[INFO] Estructura de la tabla:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Error al verificar filtros_graph_pais: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    verificar_filtros_graph_pais()
