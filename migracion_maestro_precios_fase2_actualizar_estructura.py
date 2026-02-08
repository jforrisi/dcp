"""
Fase 2: Actualizar estructura de maestro_precios
==================================================
Crea nueva estructura de maestro_precios con id_variable e id_pais en lugar de maestro_id.
NOTA: Esto eliminará todos los datos existentes en maestro_precios.
"""

import sqlite3
import os

DB_NAME = "series_tiempo.db"


def actualizar_estructura():
    """
    Actualiza la estructura de maestro_precios a usar id_variable e id_pais.
    """
    print("=" * 80)
    print("FASE 2: Actualizar estructura de maestro_precios")
    print("=" * 80)
    print("\n[ADVERTENCIA] Esta operación eliminará TODOS los datos existentes en maestro_precios.")
    print("[ADVERTENCIA] Asegúrate de tener un backup antes de continuar.\n")
    
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] Base de datos '{DB_NAME}' no encontrada.")
        return False
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar que las tablas de referencia existen
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('variables', 'pais_grupo')")
        tablas = [row[0] for row in cursor.fetchall()]
        
        if 'variables' not in tablas:
            print("[ERROR] Tabla 'variables' no existe. Ejecuta primero 'migracion_fase1_crear_tablas.py'.")
            return False
        
        if 'pais_grupo' not in tablas:
            print("[ERROR] Tabla 'pais_grupo' no existe. Ejecuta primero 'migracion_fase1_crear_tablas.py'.")
            return False
        
        # Verificar estructura actual
        cursor.execute("PRAGMA table_info(maestro_precios)")
        columnas_actuales = [col[1] for col in cursor.fetchall()]
        print(f"\n[INFO] Columnas actuales en 'maestro_precios': {', '.join(columnas_actuales)}")
        
        # Contar registros existentes
        cursor.execute("SELECT COUNT(*) FROM maestro_precios")
        count_actual = cursor.fetchone()[0]
        print(f"[INFO] Registros actuales en 'maestro_precios': {count_actual}")
        
        if count_actual > 0:
            print(f"\n[ADVERTENCIA] Se eliminarán {count_actual} registros existentes.")
        
        # Verificar si ya tiene la nueva estructura
        if 'id_variable' in columnas_actuales and 'id_pais' in columnas_actuales:
            if 'maestro_id' not in columnas_actuales:
                print("[OK] La tabla ya tiene la nueva estructura (id_variable, id_pais).")
                return True
            else:
                print("[WARN] La tabla tiene ambas estructuras. Se procederá a eliminar la antigua.")
        
        # Crear nueva tabla con nueva estructura
        print("\n[INFO] Creando nueva tabla 'maestro_precios_new'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maestro_precios_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_variable INTEGER NOT NULL,
                id_pais INTEGER NOT NULL,
                fecha DATE NOT NULL,
                valor NUMERIC(18, 6) NOT NULL,
                FOREIGN KEY (id_variable) REFERENCES variables(id_variable),
                FOREIGN KEY (id_pais) REFERENCES pais_grupo(id_pais)
            )
        """)
        
        # Crear índices
        print("[INFO] Creando índices...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_maestro_precios_id_variable
            ON maestro_precios_new (id_variable)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_maestro_precios_id_pais
            ON maestro_precios_new (id_pais)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_maestro_precios_fecha
            ON maestro_precios_new (fecha)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_maestro_precios_variable_pais_fecha
            ON maestro_precios_new (id_variable, id_pais, fecha)
        """)
        
        print("[OK] Índices creados.")
        
        # Eliminar tabla antigua
        print("\n[INFO] Eliminando tabla antigua 'maestro_precios'...")
        cursor.execute("DROP TABLE IF EXISTS maestro_precios")
        
        # Renombrar nueva tabla
        print("[INFO] Renombrando 'maestro_precios_new' a 'maestro_precios'...")
        cursor.execute("ALTER TABLE maestro_precios_new RENAME TO maestro_precios")
        
        conn.commit()
        
        # Verificar estructura final
        cursor.execute("PRAGMA table_info(maestro_precios)")
        columnas_finales = [col[1] for col in cursor.fetchall()]
        print(f"\n[INFO] Columnas finales en 'maestro_precios': {', '.join(columnas_finales)}")
        
        # Verificar índices
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='maestro_precios'
        """)
        indices = [row[0] for row in cursor.fetchall()]
        print(f"[INFO] Índices creados: {', '.join(indices)}")
        
        # Verificar que la estructura es correcta
        columnas_esperadas = ['id', 'id_variable', 'id_pais', 'fecha', 'valor']
        columnas_presentes = [col for col in columnas_esperadas if col in columnas_finales]
        
        if len(columnas_presentes) == len(columnas_esperadas):
            print("\n[OK] Estructura correcta. Todas las columnas esperadas están presentes.")
        else:
            faltantes = [col for col in columnas_esperadas if col not in columnas_finales]
            print(f"\n[ERROR] Faltan columnas: {', '.join(faltantes)}")
            return False
        
        # Verificar que maestro_id ya no existe
        if 'maestro_id' in columnas_finales:
            print("\n[WARN] Columna 'maestro_id' aún existe. Se recomienda eliminarla manualmente.")
        else:
            print("\n[OK] Columna 'maestro_id' eliminada correctamente.")
        
        print("\n" + "=" * 80)
        print("[OK] FASE 2 COMPLETADA: Estructura de maestro_precios actualizada")
        print("=" * 80)
        print("\n[INFO] La tabla ahora usa id_variable e id_pais en lugar de maestro_id.")
        print("[INFO] Los scripts de actualización deben ser modificados para usar la nueva estructura.")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error al actualizar estructura: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    actualizar_estructura()
