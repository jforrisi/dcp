"""
Fase 3: Actualizar maestro desde Excel
========================================
Actualiza la tabla maestro con id_variable e id_pais desde maestro_database.xlsx
"""

import sqlite3
import os
import pandas as pd

DB_NAME = "series_tiempo.db"
EXCEL_FILE = "maestro_database.xlsx"


def actualizar_maestro_desde_excel():
    """
    Actualiza maestro con id_variable e id_pais desde el Excel.
    """
    print("=" * 80)
    print("FASE 3: Actualizar maestro desde Excel")
    print("=" * 80)
    
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] Base de datos '{DB_NAME}' no encontrada.")
        return False
    
    if not os.path.exists(EXCEL_FILE):
        print(f"[ERROR] Archivo Excel '{EXCEL_FILE}' no encontrado.")
        return False
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar que la columna id_variable existe
        cursor.execute("PRAGMA table_info(maestro)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'id_variable' not in columnas:
            print("[ERROR] Columna 'id_variable' no existe en maestro.")
            print("[INFO] Ejecuta primero 'migracion_maestro_precios_fase1_renombrar_columna.py'.")
            return False
        
        if 'id_pais' not in columnas:
            print("[ERROR] Columna 'id_pais' no existe en maestro.")
            print("[INFO] Ejecuta primero 'migracion_fase3_agregar_columnas.py'.")
            return False
        
        # Leer hoja maestro del Excel
        print(f"\n[INFO] Leyendo hoja 'maestro' de '{EXCEL_FILE}'...")
        try:
            df_maestro = pd.read_excel(EXCEL_FILE, sheet_name='maestro')
            print(f"[OK] {len(df_maestro)} registros leídos del Excel.")
        except Exception as e:
            print(f"[ERROR] Error al leer Excel: {e}")
            return False
        
        # Verificar columnas requeridas
        columnas_requeridas = ['id_variable', 'id_pais']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df_maestro.columns]
        
        if columnas_faltantes:
            print(f"[ERROR] Faltan columnas en Excel: {', '.join(columnas_faltantes)}")
            print(f"[INFO] Columnas disponibles: {', '.join(df_maestro.columns)}")
            return False
        
        # Verificar que hay una columna para identificar el registro en maestro
        # El Excel debe tener alguna forma de identificar el registro (id, nombre, etc.)
        # Asumimos que el Excel tiene una columna que permite hacer match con maestro.id
        # Por ahora, asumimos que el Excel tiene las columnas: id_variable, id_pais, y posiblemente otras
        
        # Obtener todos los registros de maestro
        cursor.execute("SELECT id FROM maestro")
        ids_maestro = [row[0] for row in cursor.fetchall()]
        print(f"[INFO] {len(ids_maestro)} registros en maestro.")
        
        # Si el Excel tiene una columna 'id' o similar, usarla para hacer match
        # Si no, necesitamos otra estrategia (por ejemplo, usar nombre + otras columnas)
        # Por ahora, asumimos que el Excel tiene un índice que corresponde a maestro.id
        # o que tiene una columna que permite hacer match
        
        # Estrategia: Si el Excel tiene menos filas que maestro, solo actualizamos esos
        # Si el Excel tiene una columna que identifica el registro, la usamos
        # Por defecto, asumimos que el orden del Excel corresponde al orden de maestro.id
        
        # Verificar si hay una columna que identifique el registro
        columnas_identificadoras = ['id', 'maestro_id', 'nombre']
        columna_id = None
        
        for col in columnas_identificadoras:
            if col in df_maestro.columns:
                columna_id = col
                break
        
        actualizados = 0
        sin_match = []
        
        print("\n[INFO] Actualizando registros...")
        print("-" * 80)
        
        for idx, row in df_maestro.iterrows():
            id_variable = row.get('id_variable')
            id_pais = row.get('id_pais')
            
            # Si id_variable o id_pais son NaN, saltar
            if pd.isna(id_variable) or pd.isna(id_pais):
                continue
            
            # Convertir a int
            try:
                id_variable = int(id_variable)
                id_pais = int(id_pais)
            except (ValueError, TypeError):
                print(f"[WARN] Fila {idx}: id_variable o id_pais no son numéricos. Saltando.")
                continue
            
            # Determinar qué registro de maestro actualizar
            maestro_id = None
            
            if columna_id:
                # Usar columna identificadora
                valor_id = row.get(columna_id)
                if columna_id == 'id':
                    maestro_id = int(valor_id) if not pd.isna(valor_id) else None
                elif columna_id == 'maestro_id':
                    maestro_id = int(valor_id) if not pd.isna(valor_id) else None
                elif columna_id == 'nombre':
                    # Buscar por nombre
                    nombre = str(valor_id) if not pd.isna(valor_id) else None
                    if nombre:
                        cursor.execute("SELECT id FROM maestro WHERE nombre = ?", (nombre,))
                        result = cursor.fetchone()
                        maestro_id = result[0] if result else None
            else:
                # Usar índice (asumiendo que el índice del Excel corresponde a maestro.id)
                # Esto es frágil, pero es una aproximación
                maestro_id = idx + 1 if (idx + 1) in ids_maestro else None
            
            if maestro_id is None:
                sin_match.append((idx, id_variable, id_pais))
                continue
            
            # Verificar que id_variable e id_pais existen en las tablas de referencia
            cursor.execute("SELECT COUNT(*) FROM variables WHERE id_variable = ?", (id_variable,))
            if cursor.fetchone()[0] == 0:
                print(f"[WARN] Fila {idx}: id_variable {id_variable} no existe en variables. Saltando.")
                continue
            
            cursor.execute("SELECT COUNT(*) FROM pais_grupo WHERE id_pais = ?", (id_pais,))
            if cursor.fetchone()[0] == 0:
                print(f"[WARN] Fila {idx}: id_pais {id_pais} no existe en pais_grupo. Saltando.")
                continue
            
            # Actualizar registro
            try:
                cursor.execute("""
                    UPDATE maestro 
                    SET id_variable = ?, id_pais = ?
                    WHERE id = ?
                """, (id_variable, id_pais, maestro_id))
                actualizados += 1
            except Exception as e:
                print(f"[WARN] Error al actualizar maestro.id={maestro_id}: {e}")
        
        conn.commit()
        
        # Reporte
        print("\n" + "=" * 80)
        print("REPORTE DE ACTUALIZACIÓN")
        print("=" * 80)
        print(f"\n[OK] Registros actualizados: {actualizados}")
        print(f"[WARN] Registros sin match: {len(sin_match)}")
        
        if sin_match:
            print(f"\n[INFO] Primeros 10 registros sin match:")
            for idx, id_var, id_pais in sin_match[:10]:
                print(f"  - Fila {idx}: id_variable={id_var}, id_pais={id_pais}")
        
        # Verificar resultados
        cursor.execute("SELECT COUNT(*) FROM maestro WHERE id_variable IS NOT NULL AND id_pais IS NOT NULL")
        con_ambos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM maestro WHERE id_variable IS NOT NULL OR id_pais IS NOT NULL")
        con_al_menos_uno = cursor.fetchone()[0]
        
        print(f"\n[VERIFICACIÓN]")
        print(f"  Registros con ambas FKs: {con_ambos}")
        print(f"  Registros con al menos una FK: {con_al_menos_uno}")
        print(f"  Total registros en maestro: {len(ids_maestro)}")
        
        print("\n" + "=" * 80)
        print("[OK] FASE 3 COMPLETADA: maestro actualizado desde Excel")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error al actualizar maestro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    actualizar_maestro_desde_excel()
