"""
Script para modificar la restricción UNIQUE en la tabla variables.
Cambia de UNIQUE(id_nombre_variable) a UNIQUE(id_nombre_variable, nominal_o_real)
para permitir variables con el mismo nombre pero diferente tipo (nominal/real).
"""

import sqlite3
import os

DB_NAME = "series_tiempo.db"


def modificar_restriccion_unique(conn):
    """Modifica la restricción UNIQUE en la tabla variables."""
    cursor = conn.cursor()
    
    print("[INFO] Verificando estructura actual de la tabla variables...")
    
    # Obtener el SQL de creación actual
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='variables'")
    sql_actual = cursor.fetchone()
    
    if not sql_actual:
        raise ValueError("No se encontró la tabla 'variables'")
    
    print("[INFO] SQL actual de la tabla:")
    print(sql_actual[0])
    
    # Verificar si ya tiene la restricción compuesta
    if "UNIQUE(id_nombre_variable, nominal_o_real)" in sql_actual[0]:
        print("[OK] La tabla ya tiene la restricción UNIQUE compuesta correcta")
        return False
    
    print("\n[INFO] La tabla tiene restricción UNIQUE solo en id_nombre_variable")
    print("[INFO] Necesitamos modificarla para permitir mismo nombre con diferente nominal_o_real")
    
    # Crear tabla temporal con la nueva estructura
    print("\n[INFO] Creando tabla temporal con nueva estructura...")
    
    # Obtener todas las columnas
    cursor.execute("PRAGMA table_info(variables)")
    columnas = cursor.fetchall()
    
    # Construir nueva definición de tabla
    columnas_sql = []
    for col in columnas:
        col_name = col[1]
        col_type = col[2]
        col_notnull = "NOT NULL" if col[3] else ""
        col_default = f"DEFAULT {col[4]}" if col[4] is not None else ""
        col_pk = "PRIMARY KEY" if col[5] else ""
        
        # Construir definición de columna
        col_def = f"{col_name} {col_type}"
        if col_notnull:
            col_def += f" {col_notnull}"
        if col_default:
            col_def += f" {col_default}"
        if col_pk:
            col_def += f" {col_pk}"
        
        columnas_sql.append(col_def)
    
    # Crear nueva tabla con restricción compuesta
    nueva_tabla_sql = f"""
    CREATE TABLE variables_new (
        {', '.join(columnas_sql)},
        UNIQUE(id_nombre_variable, nominal_o_real)
    )
    """
    
    print("[INFO] Creando nueva tabla...")
    cursor.execute(nueva_tabla_sql)
    
    # Copiar datos
    print("[INFO] Copiando datos de la tabla antigua a la nueva...")
    cursor.execute("INSERT INTO variables_new SELECT * FROM variables")
    
    # Eliminar tabla antigua
    print("[INFO] Eliminando tabla antigua...")
    cursor.execute("DROP TABLE variables")
    
    # Renombrar nueva tabla
    print("[INFO] Renombrando nueva tabla...")
    cursor.execute("ALTER TABLE variables_new RENAME TO variables")
    
    # Recrear índices si existen
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='variables' AND sql IS NOT NULL")
    indices = cursor.fetchall()
    
    if indices:
        print(f"[INFO] Recreando {len(indices)} índices...")
        for idx_name, idx_sql in indices:
            if idx_sql:
                # Reemplazar nombre de tabla en el SQL del índice
                nuevo_sql = idx_sql.replace("variables", "variables")
                try:
                    cursor.execute(nuevo_sql)
                    print(f"  [OK] Índice '{idx_name}' recreado")
                except Exception as e:
                    print(f"  [WARN] No se pudo recrear índice '{idx_name}': {e}")
    
    conn.commit()
    print("\n[OK] Restricción UNIQUE modificada exitosamente")
    print("[OK] Ahora se puede tener el mismo nombre con diferente nominal_o_real")
    
    return True


def main():
    """Función principal."""
    print("=" * 80)
    print("MODIFICACIÓN DE RESTRICCIÓN UNIQUE EN TABLA VARIABLES".center(80))
    print("=" * 80)
    print(f"Base de datos: {DB_NAME}")
    print("=" * 80)
    
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] No se encontró la base de datos: {DB_NAME}")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        print(f"\n[OK] Conectado a la base de datos: {DB_NAME}")
        
        # Hacer backup antes de modificar
        print("\n[INFO] IMPORTANTE: Se recomienda hacer backup de la base de datos antes de continuar")
        print("[INFO] Procediendo automáticamente...")
        
        # Modificar restricción
        modificado = modificar_restriccion_unique(conn)
        
        if modificado:
            print("\n[SUCCESS] Proceso completado exitosamente")
        else:
            print("\n[INFO] No fue necesario modificar la tabla (ya tenía la restricción correcta)")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n[ERROR] Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if conn:
            conn.close()
            print("\n[OK] Conexión cerrada")


if __name__ == "__main__":
    main()
