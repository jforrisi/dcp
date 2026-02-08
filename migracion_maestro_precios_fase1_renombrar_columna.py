"""
Fase 1: Renombrar id_nombre_variable a id_variable en maestro
===============================================================
Renombra la columna id_nombre_variable a id_variable para coincidir con el Excel.
"""

import sqlite3
import os

DB_NAME = "series_tiempo.db"


def renombrar_columna():
    """
    Renombra id_nombre_variable a id_variable en la tabla maestro.
    """
    print("=" * 80)
    print("FASE 1: Renombrar id_nombre_variable a id_variable en maestro")
    print("=" * 80)
    
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] Base de datos '{DB_NAME}' no encontrada.")
        return False
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar columnas actuales
        cursor.execute("PRAGMA table_info(maestro)")
        columnas_actuales = [col[1] for col in cursor.fetchall()]
        print(f"\n[INFO] Columnas actuales en 'maestro': {', '.join(columnas_actuales)}")
        
        # Verificar si id_nombre_variable existe
        if 'id_nombre_variable' not in columnas_actuales:
            print("[WARN] Columna 'id_nombre_variable' no existe. Puede que ya haya sido renombrada.")
            if 'id_variable' in columnas_actuales:
                print("[OK] Columna 'id_variable' ya existe. No se requiere acción.")
                return True
            else:
                print("[ERROR] Ni 'id_nombre_variable' ni 'id_variable' existen.")
                return False
        
        # Verificar si id_variable ya existe
        if 'id_variable' in columnas_actuales:
            print("[WARN] Columna 'id_variable' ya existe. Verificando datos...")
            cursor.execute("SELECT COUNT(*) FROM maestro WHERE id_nombre_variable IS NOT NULL")
            count_old = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM maestro WHERE id_variable IS NOT NULL")
            count_new = cursor.fetchone()[0]
            print(f"[INFO] Registros con id_nombre_variable: {count_old}")
            print(f"[INFO] Registros con id_variable: {count_new}")
            
            if count_old > 0 and count_new == 0:
                # Copiar datos de id_nombre_variable a id_variable
                print("[INFO] Copiando datos de id_nombre_variable a id_variable...")
                cursor.execute("""
                    UPDATE maestro 
                    SET id_variable = id_nombre_variable 
                    WHERE id_nombre_variable IS NOT NULL AND id_variable IS NULL
                """)
                conn.commit()
                print("[OK] Datos copiados.")
            
            # Eliminar columna antigua (SQLite no soporta DROP COLUMN directamente)
            # Usaremos una estrategia de recreación de tabla
            print("[INFO] Eliminando columna 'id_nombre_variable'...")
            # Esto requiere recrear la tabla, pero por ahora solo renombramos
            print("[WARN] SQLite no soporta DROP COLUMN. La columna 'id_nombre_variable' permanecerá.")
            print("[INFO] Se recomienda usar una herramienta externa para eliminar la columna si es necesario.")
            return True
        
        # Renombrar columna usando ALTER TABLE ... RENAME COLUMN (SQLite 3.25.0+)
        print("\n[INFO] Renombrando columna 'id_nombre_variable' a 'id_variable'...")
        try:
            cursor.execute("ALTER TABLE maestro RENAME COLUMN id_nombre_variable TO id_variable")
            conn.commit()
            print("[OK] Columna renombrada exitosamente.")
        except sqlite3.OperationalError as e:
            # Si RENAME COLUMN no funciona, usar estrategia de copia
            print(f"[WARN] RENAME COLUMN no disponible: {e}")
            print("[INFO] Usando estrategia de copia...")
            
            # Agregar nueva columna
            cursor.execute("ALTER TABLE maestro ADD COLUMN id_variable INTEGER")
            
            # Copiar datos
            cursor.execute("""
                UPDATE maestro 
                SET id_variable = id_nombre_variable 
                WHERE id_nombre_variable IS NOT NULL
            """)
            conn.commit()
            print("[OK] Datos copiados a nueva columna 'id_variable'.")
            print("[WARN] Columna 'id_nombre_variable' permanece. Se recomienda eliminarla manualmente.")
        
        # Verificar resultado
        cursor.execute("PRAGMA table_info(maestro)")
        columnas_finales = [col[1] for col in cursor.fetchall()]
        print(f"\n[INFO] Columnas finales en 'maestro': {', '.join(columnas_finales)}")
        
        if 'id_variable' in columnas_finales:
            cursor.execute("SELECT COUNT(*) FROM maestro WHERE id_variable IS NOT NULL")
            count = cursor.fetchone()[0]
            print(f"[OK] Columna 'id_variable' existe con {count} registros con valores.")
        else:
            print("[ERROR] Columna 'id_variable' no se creó correctamente.")
            return False
        
        print("\n" + "=" * 80)
        print("[OK] FASE 1 COMPLETADA: Columna renombrada exitosamente")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error al renombrar columna: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    renombrar_columna()
