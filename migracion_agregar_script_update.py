"""
Migración: Agregar columna script_update a tabla maestro
"""
import sqlite3
import shutil
from datetime import datetime

DB_NAME = "series_tiempo.db"
BACKUP_NAME = f"series_tiempo_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def verificar_columna_existe(cursor, nombre_columna):
    """Verifica si una columna existe en la tabla maestro"""
    cursor.execute("PRAGMA table_info(maestro)")
    columnas = [row[1] for row in cursor.fetchall()]
    return nombre_columna in columnas

def main():
    print("=" * 60)
    print("MIGRACIÓN: Agregar columna script_update a tabla maestro")
    print("=" * 60)
    
    # Crear backup
    print(f"\n[INFO] Creando backup de la base de datos...")
    try:
        shutil.copy2(DB_NAME, BACKUP_NAME)
        print(f"[OK] Backup creado: {BACKUP_NAME}")
    except Exception as e:
        print(f"[ERROR] No se pudo crear backup: {e}")
        return
    
    # Conectar a la base de datos
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        if verificar_columna_existe(cursor, 'script_update'):
            print("[INFO] La columna 'script_update' ya existe en la tabla 'maestro'")
            print("[INFO] No se realizará ninguna modificación")
        else:
            # Agregar columna
            print("\n[INFO] Agregando columna 'script_update' a la tabla 'maestro'...")
            cursor.execute("ALTER TABLE maestro ADD COLUMN script_update TEXT")
            conn.commit()
            print("[OK] Columna 'script_update' agregada exitosamente")
        
        # Verificar resultado
        cursor.execute("PRAGMA table_info(maestro)")
        columnas = cursor.fetchall()
        print("\n[INFO] Columnas actuales en tabla 'maestro':")
        for col in columnas:
            print(f"   - {col[1]} ({col[2]})")
        
        print("\n[OK] Migración completada exitosamente")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error durante la migración: {e}")
        print(f"[INFO] Se puede restaurar desde el backup: {BACKUP_NAME}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
