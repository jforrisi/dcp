"""
Fase 3: Agregar Columnas Opcionales a maestro
==============================================
Agrega columnas opcionales a la tabla maestro para soportar la nueva estructura
sin afectar la funcionalidad existente.
"""

import sqlite3
import os

DB_NAME = "series_tiempo.db"


def agregar_columnas_maestro():
    """
    Agrega columnas opcionales a la tabla maestro.
    """
    print("=" * 80)
    print("FASE 3: Agregar Columnas Opcionales a maestro")
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
        
        # 1. Agregar id_nombre_variable (FK opcional a variables.id_variable)
        print("\n[INFO] Agregando columna 'id_nombre_variable'...")
        if 'id_nombre_variable' not in columnas_actuales:
            try:
                cursor.execute("ALTER TABLE maestro ADD COLUMN id_nombre_variable INTEGER")
                print("[OK] Columna 'id_nombre_variable' agregada")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Error al agregar 'id_nombre_variable': {e}")
        else:
            print("[INFO] Columna 'id_nombre_variable' ya existe")
        
        # 2. Agregar id_pais (FK opcional a pais_grupo.id_pais)
        print("\n[INFO] Agregando columna 'id_pais'...")
        if 'id_pais' not in columnas_actuales:
            try:
                cursor.execute("ALTER TABLE maestro ADD COLUMN id_pais INTEGER")
                print("[OK] Columna 'id_pais' agregada")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Error al agregar 'id_pais': {e}")
        else:
            print("[INFO] Columna 'id_pais' ya existe")
        
        # 3. Agregar link (opcional)
        print("\n[INFO] Agregando columna 'link'...")
        if 'link' not in columnas_actuales:
            try:
                cursor.execute("ALTER TABLE maestro ADD COLUMN link VARCHAR(500)")
                print("[OK] Columna 'link' agregada")
            except sqlite3.OperationalError as e:
                print(f"[WARN] Error al agregar 'link': {e}")
        else:
            print("[INFO] Columna 'link' ya existe")
        
        conn.commit()
        
        # Verificar columnas finales
        cursor.execute("PRAGMA table_info(maestro)")
        columnas_finales = [col[1] for col in cursor.fetchall()]
        print(f"\n[INFO] Columnas finales en 'maestro': {', '.join(columnas_finales)}")
        
        # Verificar que las nuevas columnas están presentes
        nuevas_columnas = ['id_nombre_variable', 'id_pais', 'link']
        columnas_agregadas = [col for col in nuevas_columnas if col in columnas_finales]
        columnas_faltantes = [col for col in nuevas_columnas if col not in columnas_finales]
        
        if columnas_faltantes:
            print(f"\n[WARN] Columnas no agregadas: {', '.join(columnas_faltantes)}")
        else:
            print(f"\n[OK] Todas las columnas nuevas agregadas: {', '.join(columnas_agregadas)}")
        
        # Verificar que queries existentes siguen funcionando
        print("\n[INFO] Verificando que queries existentes siguen funcionando...")
        try:
            cursor.execute("SELECT COUNT(*) FROM maestro")
            count = cursor.fetchone()[0]
            print(f"[OK] Query básico funciona. Total registros en maestro: {count}")
            
            cursor.execute("SELECT id, nombre, tipo FROM maestro LIMIT 1")
            resultado = cursor.fetchone()
            if resultado:
                print(f"[OK] Query con columnas existentes funciona. Ejemplo: id={resultado[0]}, nombre={resultado[1]}")
        except Exception as e:
            print(f"[ERROR] Query de verificación falló: {e}")
            return False
        
        print("\n" + "=" * 80)
        print("[OK] FASE 3 COMPLETADA: Columnas opcionales agregadas a maestro")
        print("=" * 80)
        print("\n[INFO] Las nuevas columnas son opcionales (pueden ser NULL).")
        print("[INFO] El sistema existente seguirá funcionando normalmente.")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error al agregar columnas: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    agregar_columnas_maestro()
