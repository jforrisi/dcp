"""
Script de migración para simplificar la tabla maestro según el Excel maestro_database.xlsx

Cambios:
1. Eliminar columnas: id, nombre, tipo, unidad, categoria, moneda, nominal_real, mercado, es_cotizacion, pais
2. Mantener solo: id_variable, id_pais, fuente, periodicidad, activo, link
3. Cambiar PK de 'id' a (id_variable, id_pais) compuesta
4. maestro_precios ya usa id_variable e id_pais, no necesita cambios
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_NAME = "backend/series_tiempo.db"
EXCEL_MAESTRO = "maestro_database.xlsx"

def backup_database():
    """Crea un backup de la base de datos antes de la migración."""
    import shutil
    from datetime import datetime
    
    backup_name = f"backend/series_tiempo_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_NAME, backup_name)
    print(f"[OK] Backup creado: {backup_name}")
    return backup_name

def verificar_excel():
    """Verifica que el Excel existe y tiene la estructura correcta."""
    if not Path(EXCEL_MAESTRO).exists():
        raise FileNotFoundError(f"No se encuentra el archivo {EXCEL_MAESTRO}")
    
    df = pd.read_excel(EXCEL_MAESTRO, sheet_name='maestro')
    expected_cols = ['id_variable', 'id_pais', 'fuente', 'periodicidad', 'activo', 'link']
    
    if list(df.columns) != expected_cols:
        raise ValueError(f"El Excel no tiene las columnas esperadas. Esperadas: {expected_cols}, Encontradas: {list(df.columns)}")
    
    print(f"[OK] Excel verificado: {len(df)} registros")
    return df

def migrar_maestro():
    """Migra la tabla maestro a la nueva estructura."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        print("\n[INFO] Iniciando migración de tabla 'maestro'...")
        
        # 1. Eliminar tabla temporal si existe (de ejecuciones anteriores)
        cursor.execute("DROP TABLE IF EXISTS maestro_new")
        
        # 2. Crear tabla temporal con nueva estructura
        print("[INFO] Creando tabla temporal maestro_new...")
        cursor.execute("""
            CREATE TABLE maestro_new (
                id_variable INTEGER NOT NULL,
                id_pais INTEGER NOT NULL,
                fuente TEXT,
                periodicidad TEXT NOT NULL,
                activo INTEGER NOT NULL DEFAULT 1,
                link TEXT,
                PRIMARY KEY (id_variable, id_pais)
            )
        """)
        
        # 3. Cargar datos desde Excel (fuente de verdad)
        print("[INFO] Cargando datos desde Excel maestro_database.xlsx...")
        df_excel = pd.read_excel(EXCEL_MAESTRO, sheet_name='maestro')
        
        # Limpiar datos: convertir NaN a None, asegurar tipos correctos
        df_excel = df_excel.where(pd.notna(df_excel), None)
        df_excel['id_variable'] = df_excel['id_variable'].astype(int)
        df_excel['id_pais'] = df_excel['id_pais'].astype(int)
        df_excel['activo'] = df_excel['activo'].fillna(1).astype(int)
        df_excel['periodicidad'] = df_excel['periodicidad'].astype(str)
        
        # Insertar datos desde Excel
        for _, row in df_excel.iterrows():
            cursor.execute("""
                INSERT INTO maestro_new (id_variable, id_pais, fuente, periodicidad, activo, link)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                int(row['id_variable']),
                int(row['id_pais']),
                row['fuente'] if pd.notna(row['fuente']) else None,
                str(row['periodicidad']),
                int(row['activo']) if pd.notna(row['activo']) else 1,
                row['link'] if pd.notna(row['link']) else None
            ))
        
        rows_migrated = len(df_excel)
        print(f"[OK] Cargados {rows_migrated} registros desde Excel")
        
        # 4. Verificar que no hay duplicados
        cursor.execute("""
            SELECT id_variable, id_pais, COUNT(*) as cnt
            FROM maestro_new
            GROUP BY id_variable, id_pais
            HAVING cnt > 1
        """)
        duplicados = cursor.fetchall()
        if duplicados:
            print(f"[WARN] Se encontraron {len(duplicados)} duplicados en la nueva tabla:")
            for dup in duplicados:
                print(f"  id_variable={dup[0]}, id_pais={dup[1]}, count={dup[2]}")
        else:
            print("[OK] No hay duplicados")
        
        # 5. Verificar integridad referencial (opcional, solo si las tablas existen)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='variables'")
            if cursor.fetchone():
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM maestro_new m
                    WHERE NOT EXISTS (
                        SELECT 1 FROM variables v WHERE v.id_variable = m.id_variable
                    )
                """)
                vars_invalidas = cursor.fetchone()[0]
                if vars_invalidas > 0:
                    print(f"[WARN] {vars_invalidas} registros con id_variable que no existe en 'variables'")
        except Exception:
            print("[INFO] Tabla 'variables' no existe, omitiendo verificación")
        
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pais_grupo'")
            if cursor.fetchone():
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM maestro_new m
                    WHERE NOT EXISTS (
                        SELECT 1 FROM pais_grupo p WHERE p.id_pais = m.id_pais
                    )
                """)
                paises_invalidos = cursor.fetchone()[0]
                if paises_invalidos > 0:
                    print(f"[WARN] {paises_invalidos} registros con id_pais que no existe en 'pais_grupo'")
        except Exception:
            print("[INFO] Tabla 'pais_grupo' no existe, omitiendo verificación")
        
        # 6. Eliminar tabla antigua y renombrar nueva
        print("[INFO] Reemplazando tabla antigua...")
        cursor.execute("DROP TABLE maestro")
        cursor.execute("ALTER TABLE maestro_new RENAME TO maestro")
        
        conn.commit()
        print("[OK] Migración completada exitosamente")
        
        # 7. Verificar resultado
        cursor.execute("SELECT COUNT(*) FROM maestro")
        total = cursor.fetchone()[0]
        print(f"[OK] Tabla 'maestro' ahora tiene {total} registros")
        
        cursor.execute("PRAGMA table_info(maestro)")
        cols = cursor.fetchall()
        print("\n[INFO] Estructura final de 'maestro':")
        for col in cols:
            pk = " (PK)" if col[5] else ""
            print(f"  {col[1]} ({col[2]}){pk}")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error durante la migración: {e}")
        raise
    finally:
        conn.close()

def verificar_maestro_precios():
    """Verifica que maestro_precios puede relacionarse correctamente con la nueva estructura."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar si la tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_precios'")
        if not cursor.fetchone():
            print("\n[INFO] Tabla 'maestro_precios' no existe, omitiendo verificación")
            return
        
        print("\n[INFO] Verificando integridad de maestro_precios...")
        
        # Verificar que todos los registros de maestro_precios tienen correspondencia en maestro
        cursor.execute("""
            SELECT COUNT(*) 
            FROM maestro_precios mp
            WHERE NOT EXISTS (
                SELECT 1 FROM maestro m 
                WHERE m.id_variable = mp.id_variable 
                AND m.id_pais = mp.id_pais
            )
        """)
        orphanos = cursor.fetchone()[0]
        
        if orphanos > 0:
            print(f"[WARN] {orphanos} registros en maestro_precios sin correspondencia en maestro")
        else:
            print("[OK] Todos los registros de maestro_precios tienen correspondencia en maestro")
        
        # Contar registros por maestro
        cursor.execute("""
            SELECT m.id_variable, m.id_pais, COUNT(*) as cnt
            FROM maestro m
            LEFT JOIN maestro_precios mp ON m.id_variable = mp.id_variable AND m.id_pais = mp.id_pais
            GROUP BY m.id_variable, m.id_pais
            ORDER BY cnt DESC
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print("\n[INFO] Ejemplos de registros maestro con precios:")
        for s in samples:
            print(f"  id_variable={s[0]}, id_pais={s[1]}: {s[2]} precios")
        
    finally:
        conn.close()

def main():
    """Ejecuta la migración completa."""
    print("=" * 60)
    print("MIGRACIÓN: Simplificar tabla maestro")
    print("=" * 60)
    
    try:
        # 1. Backup
        backup_database()
        
        # 2. Verificar Excel
        df_excel = verificar_excel()
        print(f"\n[INFO] El Excel tiene {len(df_excel)} registros")
        
        # 3. Migrar
        migrar_maestro()
        
        # 4. Verificar maestro_precios
        verificar_maestro_precios()
        
        print("\n" + "=" * 60)
        print("[OK] MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print("\n[INFO] Próximos pasos:")
        print("  1. Actualizar scripts de actualización de precios")
        print("  2. Actualizar código backend que consulta maestro por 'id'")
        print("  3. Probar endpoints y funcionalidades")
        
    except Exception as e:
        print(f"\n[ERROR] La migración falló: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
