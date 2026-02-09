"""Script para insertar datos de curva de pesos REALES en maestro_precios"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from db.connection import execute_query, execute_update, insert_dataframe

# Configuración
ID_PAIS_URUGUAY = 858
ARCHIVO_EXCEL_REAL = "update/historicos/curva_pesos_uyu_ui.xlsx"

# Mapeo de nombres de columnas a nombres de variables REALES (curva_pesos_uyu_ui.xlsx tiene mayúsculas)
# Nota: Las columnas tienen "1 AÑOS" (plural) pero las variables se llaman "1 año" (singular)
MAPEO_COLUMNAS_VARIABLES_REAL = {
    "3 MESES": "3 meses",
    "6 MESES": "6 meses",
    "1 AÑOS": "1 año",  # Columna en plural, variable en singular
    "1 AOS": "1 año",  # Por si hay problemas de encoding
    "2 AÑOS": "2 años",
    "2 AOS": "2 años",
    "3 AÑOS": "3 años",
    "3 AOS": "3 años",
    "4 AÑOS": "4 años",
    "4 AOS": "4 años",
    "5 AÑOS": "5 años",
    "5 AOS": "5 años",
    "6 AÑOS": "6 años",
    "6 AOS": "6 años",
    "7 AÑOS": "7 años",
    "7 AOS": "7 años",
    "8 AÑOS": "8 años",
    "8 AOS": "8 años",
    "9 AÑOS": "9 años",
    "9 AOS": "9 años",
    "10 AÑOS": "10 años",
    "10 AOS": "10 años",
    "15 AÑOS": "15 años",
    "15 AOS": "15 años",
    "20 AÑOS": "20 años",
    "20 AOS": "20 años",
    "25 AÑOS": "25 años",
    "25 AOS": "25 años",
    "30 AÑOS": "30 años",
    "30 AOS": "30 años",
}

def obtener_mapeo_variables():
    """
    Obtiene el mapeo de nombres de variables a id_variable desde maestro.
    Solo para variables REALES.
    """
    resultados = execute_query(
        """
        SELECT m.id_variable, v.id_nombre_variable, v.nominal_o_real
        FROM maestro m
        JOIN variables v ON m.id_variable = v.id_variable
        WHERE m.id_pais = ? AND m.fuente = 'BEVSA' AND v.nominal_o_real = 'r'
        ORDER BY m.id_variable
        """,
        (ID_PAIS_URUGUAY,),
    )

    mapeo = {}
    for row in resultados:
        nombre_var = row["id_nombre_variable"]
        id_var = row["id_variable"]
        mapeo[nombre_var] = id_var
        if "año" in str(nombre_var):
            nombre_var_alt = str(nombre_var).replace("año", "ao")
            mapeo[nombre_var_alt] = id_var

    print(f"[INFO] Mapeo obtenido (REALES): {len(mapeo)} variables encontradas")
    for nombre, id_var in sorted(mapeo.items()):
        print(f"  {nombre} -> id_variable {id_var}")

    return mapeo

def leer_excel(ruta_archivo):
    """Lee el archivo Excel y retorna el DataFrame."""
    ruta_excel = os.path.join(os.getcwd(), ruta_archivo)
    
    if not os.path.exists(ruta_excel):
        print(f"[ERROR] No se encontró el archivo: {ruta_excel}")
        return None
    
    print(f"[INFO] Leyendo archivo Excel REAL: {ruta_excel}")
    df = pd.read_excel(ruta_excel)
    
    print(f"[INFO] Archivo leído: {len(df)} filas, {len(df.columns)} columnas")
    print(f"[INFO] Columnas: {list(df.columns)}")
    
    return df

def transformar_a_formato_largo(df, mapeo_variables, mapeo_columnas):
    """
    Transforma el DataFrame de formato ancho a largo.
    """
    print(f"\n[INFO] Transformando datos de formato ancho a largo (REALES)...")
    
    # La primera columna es la fecha
    columna_fecha = df.columns[0]
    columnas_valores = [col for col in df.columns if col != columna_fecha]
    
    print(f"[INFO] Columna de fecha: '{columna_fecha}'")
    print(f"[INFO] Columnas de valores: {len(columnas_valores)}")
    
    # Verificar que todas las columnas tengan mapeo
    columnas_sin_mapeo = []
    for col in columnas_valores:
        nombre_normalizado = mapeo_columnas.get(col, col)
        if nombre_normalizado not in mapeo_variables:
            columnas_sin_mapeo.append(col)
    
    if columnas_sin_mapeo:
        print(f"[WARN] Columnas sin mapeo encontradas: {columnas_sin_mapeo}")
        print("[WARN] Estas columnas serán omitidas")
        columnas_valores = [col for col in columnas_valores if col not in columnas_sin_mapeo]
    
    # Hacer melt (transformar a formato largo)
    df_melted = df.melt(
        id_vars=[columna_fecha],
        value_vars=columnas_valores,
        var_name='nombre_variable',
        value_name='valor'
    )
    
    print(f"[INFO] Datos transformados: {len(df_melted)} filas")
    
    # Agregar id_variable
    def obtener_id_variable(nombre_col):
        nombre_normalizado = mapeo_columnas.get(nombre_col, nombre_col)
        return mapeo_variables.get(nombre_normalizado)
    
    df_melted['id_variable'] = df_melted['nombre_variable'].apply(obtener_id_variable)
    
    # Filtrar filas donde no se encontró id_variable
    filas_sin_id = df_melted['id_variable'].isna().sum()
    if filas_sin_id > 0:
        print(f"[WARN] {filas_sin_id} filas sin id_variable, serán omitidas")
        df_melted = df_melted.dropna(subset=['id_variable'])
    
    # Preparar DataFrame final
    df_final = pd.DataFrame({
        'id_variable': df_melted['id_variable'].astype(int),
        'id_pais': ID_PAIS_URUGUAY,
        'fecha': pd.to_datetime(df_melted[columna_fecha]),
        'valor': pd.to_numeric(df_melted['valor'], errors='coerce')
    })
    
    # Eliminar filas con valores nulos
    filas_antes = len(df_final)
    df_final = df_final.dropna(subset=['valor', 'fecha'])
    filas_despues = len(df_final)
    
    if filas_antes != filas_despues:
        print(f"[INFO] Eliminadas {filas_antes - filas_despues} filas con valores nulos")
    
    # Convertir fecha a string para SQLite
    df_final['fecha'] = df_final['fecha'].dt.strftime('%Y-%m-%d')
    
    print(f"[INFO] DataFrame final preparado: {len(df_final)} registros")
    print(f"[INFO] Rango de fechas: {df_final['fecha'].min()} a {df_final['fecha'].max()}")
    print(f"[INFO] Variables únicas: {df_final['id_variable'].nunique()}")
    
    return df_final

def insertar_en_bd(df_precios):
    """Inserta los datos en maestro_precios."""
    id_variables = df_precios["id_variable"].unique().tolist()

    print(f"\n[INFO] Eliminando registros existentes para {len(id_variables)} variables REALES...")

    placeholders = ",".join(["?"] * len(id_variables))
    success, error, _ = execute_update(
        f"DELETE FROM maestro_precios WHERE id_variable IN ({placeholders}) AND id_pais = ?",
        tuple(id_variables) + (ID_PAIS_URUGUAY,),
    )
    if not success:
        raise RuntimeError(error or "Error al eliminar registros")

    print(f"\n[INFO] Insertando {len(df_precios)} registros REALES en maestro_precios...")
    insert_dataframe("maestro_precios", df_precios, if_exists="append", index=False)
    print(f"[OK] {len(df_precios):,} registros REALES insertados exitosamente")


def verificar_insercion():
    """Verifica que los datos se insertaron correctamente."""
    rows = execute_query(
        """
        SELECT DISTINCT m.id_variable
        FROM maestro m
        JOIN variables v ON m.id_variable = v.id_variable
        WHERE m.id_pais = ? AND m.fuente = 'BEVSA' AND v.nominal_o_real = 'r'
        """,
        (ID_PAIS_URUGUAY,),
    )
    id_variables = [r["id_variable"] for r in rows]

    if not id_variables:
        print("[WARN] No se encontraron variables REALES de curva de pesos en maestro")
        return

    placeholders = ",".join(["?"] * len(id_variables))
    resultado = execute_query(
        f"""
        SELECT COUNT(*) as total_registros, COUNT(DISTINCT id_variable) as variables,
               MIN(fecha) as fecha_min, MAX(fecha) as fecha_max
        FROM maestro_precios
        WHERE id_variable IN ({placeholders}) AND id_pais = ?
        """,
        tuple(id_variables) + (ID_PAIS_URUGUAY,),
    )
    r = resultado[0] if resultado else {}

    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE INSERCIÓN - REALES")
    print("=" * 80)
    print(f"Total de registros: {r.get('total_registros', 0):,}")
    print(f"Variables: {r.get('variables', 0)}")
    print(f"Rango de fechas: {r.get('fecha_min')} a {r.get('fecha_max')}")
    print("=" * 80)

def main():
    print("=" * 80)
    print("INSERCIÓN DE DATOS DE CURVA DE PESOS REALES".center(80))
    print("=" * 80)
    print(f"Base de datos: PostgreSQL (Azure)")
    print(f"Archivo Excel REAL: {ARCHIVO_EXCEL_REAL}")
    print(f"País: Uruguay (id_pais = {ID_PAIS_URUGUAY})")
    print("=" * 80)

    try:
        # 1. Obtener mapeo de variables REALES
        print("\n" + "=" * 80)
        print("PROCESANDO VARIABLES REALES".center(80))
        print("=" * 80)
        mapeo_variables_real = obtener_mapeo_variables()

        if not mapeo_variables_real:
            raise ValueError("No se encontraron variables REALES de curva de pesos en maestro")

        # 2. Leer Excel REAL
        df_excel_real = leer_excel(ARCHIVO_EXCEL_REAL)
        if df_excel_real is None:
            raise ValueError(f"No se pudo leer el archivo: {ARCHIVO_EXCEL_REAL}")

        # 3. Transformar a formato largo
        df_precios_real = transformar_a_formato_largo(
            df_excel_real,
            mapeo_variables_real,
            MAPEO_COLUMNAS_VARIABLES_REAL,
        )

        if df_precios_real.empty:
            raise ValueError("No hay datos REALES para insertar")

        print(f"\n[INFO] Datos REALES preparados: {len(df_precios_real)} registros")
        print(f"[INFO] Variables únicas: {df_precios_real['id_variable'].nunique()}")

        # 4. Insertar en base de datos
        insertar_en_bd(df_precios_real)

        # 5. Verificar inserción
        verificar_insercion()

        print("\n[OK] Proceso completado exitosamente para datos REALES")

    except Exception as e:
        print(f"\n[ERROR] Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
