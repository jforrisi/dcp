"""
Template: Cómo migrar un script de actualización a la nueva estructura
========================================================================

Este archivo muestra un ejemplo de cómo modificar un script de actualización
para usar la nueva estructura normalizada con tablas de referencia.

ANTES (estructura antigua):
---------------------------
def insertar_en_bd(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    cursor.execute("""
        INSERT OR IGNORE INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (maestro_id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo))

DESPUÉS (estructura nueva con helpers):
----------------------------------------
"""

import sqlite3
import pandas as pd
import sys
import os

# Agregar helpers al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers.maestro_helper import (
    obtener_o_crear_variable,
    obtener_o_crear_pais_grupo,
    insertar_maestro_con_fks,
    obtener_fks_desde_maestro
)

DB_NAME = "series_tiempo.db"

# ============================================================================
# EJEMPLO: Script de actualización migrado
# ============================================================================

# Configuración del script (ejemplo)
MAESTRO_ID = 1
NOMBRE_VARIABLE = "Precio hacienda - INAC"
NOMBRE_PAIS = "Uruguay"
TIPO = "P"
FUENTE = "INAC - serie mensual precios de hacienda"
PERIODICIDAD = "M"
UNIDAD = "USD/kg"
CATEGORIA = "Precios Internacionales"
ID_SUB_FAMILIA = 3  # "Precio interno de cadena transable"
NOMINAL_REAL = "n"
MONEDA = "usd"


def insertar_en_bd_migrado(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """
    Versión migrada de insertar_en_bd que usa la nueva estructura normalizada.
    
    MANTIENE COMPATIBILIDAD: Si no se pueden obtener las FKs, inserta sin ellas
    (comportamiento hacia atrás compatible).
    """
    print("\n[INFO] Insertando datos en la base de datos (estructura normalizada)...")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        nombre = maestro_row["nombre"]
        tipo = maestro_row["tipo"]
        fuente = maestro_row["fuente"]
        periodicidad = maestro_row["periodicidad"]
        unidad = maestro_row.get("unidad")
        categoria = maestro_row.get("categoria")
        activo = maestro_row["activo"]
        pais = maestro_row.get("pais")  # Si existe en el DataFrame
        
        # PASO 1: Intentar obtener o crear variable
        id_variable = None
        try:
            id_variable = obtener_o_crear_variable(
                nombre_variable=nombre,
                id_sub_familia=ID_SUB_FAMILIA,  # Puedes obtenerlo de configuración o mapeo
                nominal_o_real=NOMINAL_REAL,
                moneda=MONEDA
            )
            print(f"[OK] Variable encontrada/creada: id_variable={id_variable}")
        except ValueError as e:
            print(f"[WARN] No se pudo obtener variable: {e}")
            print("[INFO] Continuando sin FK a variables (compatibilidad hacia atrás)")
        
        # PASO 2: Intentar obtener o crear país
        id_pais = None
        if pais:
            try:
                id_pais = obtener_o_crear_pais_grupo(nombre_pais=pais)
                if id_pais:
                    print(f"[OK] País encontrado/creado: id_pais={id_pais}")
            except Exception as e:
                print(f"[WARN] No se pudo obtener país: {e}")
                print("[INFO] Continuando sin FK a pais_grupo (compatibilidad hacia atrás)")
        
        # PASO 3: Insertar en maestro usando helper
        # El helper maneja automáticamente si las FKs están disponibles o no
        exito = insertar_maestro_con_fks(
            maestro_id=maestro_id,
            nombre=nombre,
            tipo=tipo,
            fuente=fuente,
            periodicidad=periodicidad,
            unidad=unidad,
            categoria=categoria,
            activo=activo,
            id_variable=id_variable,  # Usar id_variable (nuevo nombre)
            id_pais=id_pais,
            moneda=MONEDA,  # Mantener para compatibilidad
            nominal_real=NOMINAL_REAL  # Mantener para compatibilidad
        )
        
        if exito:
            print(f"[OK] Insertado/actualizado registro en tabla 'maestro' (id={maestro_id})")
            if id_variable:
                print(f"[INFO] Con FK a variables (id_variable={id_variable})")
            if id_pais:
                print(f"[INFO] Con FK a pais_grupo (id_pais={id_pais})")
        else:
            print(f"[ERROR] No se pudo insertar registro en maestro")
            return
        
        # PASO 4: Insertar precios (NUEVA ESTRUCTURA: usar id_variable e id_pais)
        # Verificar que tenemos las FKs necesarias
        if not id_variable or not id_pais:
            print("[ERROR] Se requieren id_variable e id_pais para insertar en maestro_precios")
            print("[INFO] Obtener FKs desde maestro si ya existen...")
            from helpers.maestro_helper import obtener_fks_desde_maestro
            id_var, id_p = obtener_fks_desde_maestro(maestro_id)
            if id_var and id_p:
                id_variable = id_var
                id_pais = id_p
                print(f"[OK] FKs obtenidas desde maestro: id_variable={id_variable}, id_pais={id_pais}")
            else:
                print("[ERROR] No se pueden insertar precios sin id_variable e id_pais")
                return
        
        # Eliminar registros existentes para este id_variable e id_pais
        cursor.execute("""
            DELETE FROM maestro_precios WHERE id_variable = ? AND id_pais = ?
        """, (id_variable, id_pais))
        registros_eliminados = cursor.rowcount
        if registros_eliminados > 0:
            print(f"[INFO] Se eliminaron {registros_eliminados} registros antiguos de 'maestro_precios'")
        
        # Preparar DataFrame para inserción (debe tener id_variable e id_pais)
        if len(df_precios) > 0:
            # Asegurar que df_precios tiene las columnas correctas
            if 'id_variable' not in df_precios.columns:
                df_precios['id_variable'] = id_variable
            if 'id_pais' not in df_precios.columns:
                df_precios['id_pais'] = id_pais
            
            # Seleccionar solo las columnas necesarias
            columnas_requeridas = ['id_variable', 'id_pais', 'fecha', 'valor']
            df_precios_final = df_precios[columnas_requeridas].copy()
            
            print(f"[INFO] Insertando {len(df_precios_final)} registros en 'maestro_precios'...")
            df_precios_final.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios_final)} registro(s) en tabla 'maestro_precios'")
        else:
            print(f"[WARN] No hay datos para insertar")
        
        conn.commit()
        print(f"\n[OK] Datos insertados exitosamente en '{DB_NAME}'")
        
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] Error al insertar datos: {exc}")
        raise
    finally:
        conn.close()


# ============================================================================
# NOTAS IMPORTANTES:
# ============================================================================
"""
1. COMPATIBILIDAD HACIA ATRÁS:
   - Si no se pueden obtener las FKs, el script sigue funcionando
   - Se inserta en maestro sin FKs (comportamiento antiguo)
   - El backend puede manejar ambos casos (con y sin FKs)

2. MAPPING DE VARIABLES:
   - Necesitas mapear cada script a su id_sub_familia correspondiente
   - Puedes crear un diccionario de configuración por script
   - O buscar automáticamente basándote en el nombre

3. MAPPING DE PAÍSES:
   - Si el script tiene información de país, úsala
   - Si no, puedes inferirla o dejarla como NULL

4. TESTING:
   - Probar primero con un script simple
   - Verificar que los datos se insertan correctamente
   - Verificar que las FKs se crean correctamente
   - Probar que el backend funciona con los nuevos datos

5. MIGRACIÓN GRADUAL:
   - Migrar un script a la vez
   - Probar cada script antes de pasar al siguiente
   - Mantener backups de scripts originales
"""
