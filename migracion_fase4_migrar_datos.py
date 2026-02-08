"""
Fase 4: Migrar Datos Existentes
=================================
Migra los datos existentes en maestro a la nueva estructura normalizada.
Busca matches entre nombre/pais y las tablas de referencia.
"""

import sqlite3
import os
import pandas as pd
import unicodedata

DB_NAME = "series_tiempo.db"


def normalizar_texto(texto):
    """
    Normaliza texto para comparación: lowercase, trim, elimina acentos.
    """
    if pd.isna(texto) or texto is None:
        return ""
    texto = str(texto).strip().lower()
    # Eliminar acentos
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto


def buscar_variable_por_nombre(cursor, nombre):
    """
    Busca una variable en la tabla variables por nombre.
    Retorna id_variable si encuentra match, None si no.
    """
    nombre_norm = normalizar_texto(nombre)
    
    # Buscar coincidencia exacta
    cursor.execute("""
        SELECT id_variable, id_nombre_variable 
        FROM variables
    """)
    variables = cursor.fetchall()
    
    for id_var, nombre_var in variables:
        if normalizar_texto(nombre_var) == nombre_norm:
            return id_var
    
    # Si no hay match exacto, buscar coincidencias parciales
    for id_var, nombre_var in variables:
        nombre_var_norm = normalizar_texto(nombre_var)
        # Si el nombre normalizado contiene el nombre buscado o viceversa
        if nombre_norm in nombre_var_norm or nombre_var_norm in nombre_norm:
            return id_var
    
    return None


def buscar_pais_por_nombre(cursor, nombre_pais):
    """
    Busca un país en la tabla pais_grupo por nombre.
    Retorna id_pais si encuentra match, None si no.
    """
    if pd.isna(nombre_pais) or nombre_pais is None or nombre_pais == "":
        return None
    
    nombre_norm = normalizar_texto(nombre_pais)
    
    # Buscar coincidencia exacta
    cursor.execute("""
        SELECT id_pais, nombre_pais_grupo 
        FROM pais_grupo
    """)
    paises = cursor.fetchall()
    
    for id_pais, nombre_pais_db in paises:
        if normalizar_texto(nombre_pais_db) == nombre_norm:
            return id_pais
    
    # Si no hay match exacto, buscar coincidencias parciales
    for id_pais, nombre_pais_db in paises:
        nombre_pais_db_norm = normalizar_texto(nombre_pais_db)
        if nombre_norm in nombre_pais_db_norm or nombre_pais_db_norm in nombre_norm:
            return id_pais
    
    return None


def migrar_datos():
    """
    Migra datos existentes de maestro a la nueva estructura.
    """
    print("=" * 80)
    print("FASE 4: Migrar Datos Existentes")
    print("=" * 80)
    
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] Base de datos '{DB_NAME}' no encontrada.")
        return False
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar que las columnas nuevas existen
        cursor.execute("PRAGMA table_info(maestro)")
        columnas = [col[1] for col in cursor.fetchall()]
        # Verificar id_variable (nuevo nombre) o id_nombre_variable (nombre antiguo)
        tiene_id_variable = 'id_variable' in columnas or 'id_nombre_variable' in columnas
        if not tiene_id_variable or 'id_pais' not in columnas:
            print("[ERROR] Columnas nuevas no encontradas. Ejecuta primero 'migracion_fase3_agregar_columnas.py' y 'migracion_maestro_precios_fase1_renombrar_columna.py'.")
            return False
        
        # Leer todos los registros de maestro
        print("\n[INFO] Leyendo registros de 'maestro'...")
        # Usar id_variable si existe, sino id_nombre_variable
        columna_id_var = 'id_variable' if 'id_variable' in columnas else 'id_nombre_variable'
        cursor.execute(f"""
            SELECT id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo, 
                   pais, moneda, nominal_real, {columna_id_var}, id_pais
            FROM maestro
        """)
        registros = cursor.fetchall()
        print(f"[OK] {len(registros)} registros encontrados en 'maestro'")
        
        # Estadísticas
        migrados_exitosos = 0
        sin_match_variable = []
        sin_match_pais = []
        sin_match_ambos = []
        multiples_matches = []
        
        print("\n[INFO] Iniciando migración de datos...")
        print("-" * 80)
        
        for registro in registros:
            maestro_id = registro[0]
            nombre = registro[1]
            pais = registro[8] if len(registro) > 8 else None
            
            # Buscar variable por nombre
            id_nombre_variable = buscar_variable_por_nombre(cursor, nombre)
            
            # Buscar país por nombre
            id_pais = buscar_pais_por_nombre(cursor, pais)
            
            # Actualizar registro
            actualizado = False
            if id_nombre_variable is not None or id_pais is not None:
                try:
                    # Usar id_variable si existe, sino id_nombre_variable
                    columna_id_var = 'id_variable' if 'id_variable' in columnas else 'id_nombre_variable'
                    cursor.execute(f"""
                        UPDATE maestro 
                        SET {columna_id_var} = ?, id_pais = ?
                        WHERE id = ?
                    """, (id_nombre_variable, id_pais, maestro_id))
                    actualizado = True
                except Exception as e:
                    print(f"[WARN] Error al actualizar registro id={maestro_id}: {e}")
            
            # Registrar estadísticas
            if id_nombre_variable is not None and id_pais is not None:
                migrados_exitosos += 1
            elif id_nombre_variable is None and id_pais is None:
                sin_match_ambos.append((maestro_id, nombre, pais))
            elif id_nombre_variable is None:
                sin_match_variable.append((maestro_id, nombre, pais))
            elif id_pais is None:
                sin_match_pais.append((maestro_id, nombre, pais))
        
        conn.commit()
        
        # Generar reporte
        print("\n" + "=" * 80)
        print("REPORTE DE MIGRACIÓN")
        print("=" * 80)
        print(f"\n[OK] Registros migrados exitosamente: {migrados_exitosos}")
        print(f"[WARN] Registros sin match en variable: {len(sin_match_variable)}")
        print(f"[WARN] Registros sin match en pais: {len(sin_match_pais)}")
        print(f"[ERROR] Registros sin match en ambos: {len(sin_match_ambos)}")
        
        # Mostrar ejemplos de registros sin match
        if sin_match_variable:
            print(f"\n[INFO] Primeros 5 registros sin match en variable:")
            for maestro_id, nombre, pais in sin_match_variable[:5]:
                print(f"  - ID {maestro_id}: '{nombre}' (país: {pais})")
        
        if sin_match_pais:
            print(f"\n[INFO] Primeros 5 registros sin match en país:")
            for maestro_id, nombre, pais in sin_match_pais[:5]:
                print(f"  - ID {maestro_id}: '{nombre}' (país: {pais})")
        
        if sin_match_ambos:
            print(f"\n[INFO] Primeros 5 registros sin match en ambos:")
            for maestro_id, nombre, pais in sin_match_ambos[:5]:
                print(f"  - ID {maestro_id}: '{nombre}' (país: {pais})")
        
        # Guardar reporte detallado en archivo
        reporte_file = "migracion_fase4_reporte.txt"
        with open(reporte_file, 'w', encoding='utf-8') as f:
            f.write("REPORTE DE MIGRACIÓN - FASE 4\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Registros migrados exitosamente: {migrados_exitosos}\n")
            f.write(f"Registros sin match en variable: {len(sin_match_variable)}\n")
            f.write(f"Registros sin match en país: {len(sin_match_pais)}\n")
            f.write(f"Registros sin match en ambos: {len(sin_match_ambos)}\n\n")
            
            if sin_match_variable:
                f.write("\nREGISTROS SIN MATCH EN VARIABLE:\n")
                f.write("-" * 80 + "\n")
                for maestro_id, nombre, pais in sin_match_variable:
                    f.write(f"ID {maestro_id}: '{nombre}' (país: {pais})\n")
            
            if sin_match_pais:
                f.write("\nREGISTROS SIN MATCH EN PAÍS:\n")
                f.write("-" * 80 + "\n")
                for maestro_id, nombre, pais in sin_match_pais:
                    f.write(f"ID {maestro_id}: '{nombre}' (país: {pais})\n")
            
            if sin_match_ambos:
                f.write("\nREGISTROS SIN MATCH EN AMBOS:\n")
                f.write("-" * 80 + "\n")
                for maestro_id, nombre, pais in sin_match_ambos:
                    f.write(f"ID {maestro_id}: '{nombre}' (país: {pais})\n")
        
        print(f"\n[INFO] Reporte detallado guardado en '{reporte_file}'")
        
        # Verificar resultados
        columna_id_var = 'id_variable' if 'id_variable' in columnas else 'id_nombre_variable'
        cursor.execute(f"""
            SELECT COUNT(*) FROM maestro 
            WHERE {columna_id_var} IS NOT NULL OR id_pais IS NOT NULL
        """)
        con_fks = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM maestro 
            WHERE {columna_id_var} IS NOT NULL AND id_pais IS NOT NULL
        """)
        con_ambos_fks = cursor.fetchone()[0]
        
        print(f"\n[VERIFICACIÓN]")
        print(f"  Registros con al menos una FK: {con_fks}")
        print(f"  Registros con ambas FKs: {con_ambos_fks}")
        print(f"  Registros sin FKs: {len(registros) - con_fks}")
        
        print("\n" + "=" * 80)
        print("[OK] FASE 4 COMPLETADA: Migración de datos completada")
        print("=" * 80)
        print("\n[INFO] Los registros sin match mantienen NULL en las FKs.")
        print("[INFO] El sistema seguirá funcionando normalmente con estos registros.")
        print("[INFO] Revisa el reporte para decidir si necesitas crear registros faltantes.")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error al migrar datos: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    migrar_datos()
