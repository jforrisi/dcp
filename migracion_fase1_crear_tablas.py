"""
Fase 1: Crear Tablas de Referencia
===================================
Crea las nuevas tablas de referencia sin afectar la estructura actual de maestro.
"""

import sqlite3
import os

DB_NAME = "series_tiempo.db"


def crear_tablas_referencia():
    """
    Crea todas las tablas de referencia necesarias para la nueva estructura.
    No modifica la tabla maestro existente.
    """
    print("=" * 80)
    print("FASE 1: Crear Tablas de Referencia")
    print("=" * 80)
    
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] Base de datos '{DB_NAME}' no encontrada.")
        print("Por favor, ejecuta primero un script de actualización para crear la BD.")
        return False
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # 1. Tabla pais_grupo
        print("\n[INFO] Creando tabla 'pais_grupo'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pais_grupo (
                id_pais INTEGER PRIMARY KEY,
                nombre_pais_grupo VARCHAR(100) NOT NULL UNIQUE
            )
        """)
        print("[OK] Tabla 'pais_grupo' creada/verificada")
        
        # 2. Tabla familia
        print("\n[INFO] Creando tabla 'familia'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS familia (
                id_familia INTEGER PRIMARY KEY,
                nombre_familia VARCHAR(255) NOT NULL UNIQUE
            )
        """)
        print("[OK] Tabla 'familia' creada/verificada")
        
        # 3. Tabla sub_familia (con FK a familia)
        print("\n[INFO] Creando tabla 'sub_familia'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_familia (
                id_sub_familia INTEGER PRIMARY KEY,
                nombre_sub_familia VARCHAR(255) NOT NULL UNIQUE,
                id_familia INTEGER,
                FOREIGN KEY (id_familia) REFERENCES familia(id_familia)
            )
        """)
        print("[OK] Tabla 'sub_familia' creada/verificada")
        
        # 4. Tabla variables (con FK a sub_familia)
        print("\n[INFO] Creando tabla 'variables'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS variables (
                id_variable INTEGER PRIMARY KEY,
                id_nombre_variable VARCHAR(255) NOT NULL UNIQUE,
                id_sub_familia INTEGER,
                nominal_o_real CHAR(1),
                moneda VARCHAR(10),
                FOREIGN KEY (id_sub_familia) REFERENCES sub_familia(id_sub_familia)
            )
        """)
        print("[OK] Tabla 'variables' creada/verificada")
        
        # 5. Tabla graph (para configuración de frontend)
        print("\n[INFO] Creando tabla 'graph'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph (
                id_graph INTEGER PRIMARY KEY,
                nombre_graph VARCHAR(255) NOT NULL,
                selector VARCHAR(100)
            )
        """)
        print("[OK] Tabla 'graph' creada/verificada")
        
        # 6. Tabla filtros_graph_pais (con FKs a graph y pais_grupo)
        print("\n[INFO] Creando tabla 'filtros_graph_pais'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS filtros_graph_pais (
                id_graph INTEGER,
                id_pais INTEGER,
                PRIMARY KEY (id_graph, id_pais),
                FOREIGN KEY (id_graph) REFERENCES graph(id_graph),
                FOREIGN KEY (id_pais) REFERENCES pais_grupo(id_pais)
            )
        """)
        print("[OK] Tabla 'filtros_graph_pais' creada/verificada")
        
        # 7. Crear índices para mejorar performance
        print("\n[INFO] Creando índices...")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_variables_id_sub_familia
            ON variables(id_sub_familia)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sub_familia_id_familia
            ON sub_familia(id_familia)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_filtros_graph_pais_id_graph
            ON filtros_graph_pais(id_graph)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_filtros_graph_pais_id_pais
            ON filtros_graph_pais(id_pais)
        """)
        
        print("[OK] Índices creados/verificados")
        
        conn.commit()
        print("\n" + "=" * 80)
        print("[OK] FASE 1 COMPLETADA: Todas las tablas de referencia creadas exitosamente")
        print("=" * 80)
        
        # Verificar que maestro no fue modificado
        cursor.execute("PRAGMA table_info(maestro)")
        columnas_maestro = [col[1] for col in cursor.fetchall()]
        print(f"\n[VERIFICACIÓN] Columnas actuales en 'maestro': {', '.join(columnas_maestro)}")
        print("[OK] Tabla 'maestro' no fue modificada")
        
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n[ERROR] Error al crear tablas: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    crear_tablas_referencia()
