"""Script para insertar datos de curva de pesos REALES en maestro_precios"""

import sqlite3
import pandas as pd
import os
from datetime import datetime

# Configuración
DB_NAME = "series_tiempo.db"
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

def get_db_connection():
    """Establece conexión con la base de datos."""
    db_path = os.path.join(os.getcwd(), DB_NAME)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def obtener_mapeo_variables(conn):
    """
    Obtiene el mapeo de nombres de variables a id_variable desde maestro.
    Solo para variables REALES.
    """
    cursor = conn.cursor()
    
    # Obtener todas las variables de curva de pesos REALES para Uruguay
    cursor.execute("""
        SELECT m.id_variable, v.id_nombre_variable, v.nominal_o_real
        FROM maestro m
        JOIN variables v ON m.id_variable = v.id_variable
        WHERE m.id_pais = ? AND m.fuente = 'BEVSA' AND v.nominal_o_real = 'r'
        ORDER BY m.id_variable
    """, (ID_PAIS_URUGUAY,))
    
    resultados = cursor.fetchall()
    mapeo = {}
    
    for row in resultados:
        nombre_var = row['id_nombre_variable']
        id_var = row['id_variable']
        mapeo[nombre_var] = id_var
        # También mapear variantes con problemas de encoding
        if 'año' in nombre_var:
            nombre_var_alt = nombre_var.replace('año', 'ao')
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

def insertar_en_bd(conn, df_precios):
    """Inserta los datos en maestro_precios."""
    cursor = conn.cursor()
    
    # Obtener los id_variable únicos que se van a insertar
    id_variables = df_precios['id_variable'].unique().tolist()
    
    print(f"\n[INFO] Eliminando registros existentes para {len(id_variables)} variables REALES...")
    
    # Eliminar registros existentes para estas variables y Uruguay
    placeholders = ','.join(['?'] * len(id_variables))
    cursor.execute(f"""
        DELETE FROM maestro_precios 
        WHERE id_variable IN ({placeholders}) AND id_pais = ?
    """, id_variables + [ID_PAIS_URUGUAY])
    
    registros_eliminados = cursor.rowcount
    print(f"[INFO] Eliminados {registros_eliminados} registros existentes")
    
    # Insertar nuevos registros
    print(f"\n[INFO] Insertando {len(df_precios)} registros REALES en maestro_precios...")
    
    # Insertar en lotes para mejor performance
    batch_size = 1000
    total_insertados = 0
    
    for i in range(0, len(df_precios), batch_size):
        batch = df_precios.iloc[i:i+batch_size]
        batch.to_sql("maestro_precios", conn, if_exists="append", index=False, method='multi')
        total_insertados += len(batch)
        if (i + batch_size) % 5000 == 0 or i + batch_size >= len(df_precios):
            print(f"  Progreso: {total_insertados:,} / {len(df_precios):,} registros insertados")
    
    conn.commit()
    print(f"[OK] {total_insertados:,} registros REALES insertados exitosamente")

def verificar_insercion(conn):
    """Verifica que los datos se insertaron correctamente."""
    cursor = conn.cursor()
    
    # Obtener los id_variable de las variables REALES de curva de pesos
    cursor.execute("""
        SELECT DISTINCT m.id_variable
        FROM maestro m
        JOIN variables v ON m.id_variable = v.id_variable
        WHERE m.id_pais = ? AND m.fuente = 'BEVSA' AND v.nominal_o_real = 'r'
    """, (ID_PAIS_URUGUAY,))
    
    id_variables = [row['id_variable'] for row in cursor.fetchall()]
    
    if not id_variables:
        print("[WARN] No se encontraron variables REALES de curva de pesos en maestro")
        return
    
    placeholders = ','.join(['?'] * len(id_variables))
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total_registros,
            COUNT(DISTINCT id_variable) as variables,
            MIN(fecha) as fecha_min,
            MAX(fecha) as fecha_max
        FROM maestro_precios
        WHERE id_variable IN ({placeholders}) AND id_pais = ?
    """, id_variables + [ID_PAIS_URUGUAY])
    
    resultado = cursor.fetchone()
    
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE INSERCIÓN - REALES")
    print("=" * 80)
    print(f"Total de registros: {resultado['total_registros']:,}")
    print(f"Variables: {resultado['variables']}")
    print(f"Rango de fechas: {resultado['fecha_min']} a {resultado['fecha_max']}")
    print("=" * 80)

def main():
    print("=" * 80)
    print("INSERCIÓN DE DATOS DE CURVA DE PESOS REALES".center(80))
    print("=" * 80)
    print(f"Base de datos: {DB_NAME}")
    print(f"Archivo Excel REAL: {ARCHIVO_EXCEL_REAL}")
    print(f"País: Uruguay (id_pais = {ID_PAIS_URUGUAY})")
    print("=" * 80)
    
    conn = None
    try:
        # 1. Conectar a la base de datos
        conn = get_db_connection()
        print(f"\n[OK] Conectado a la base de datos: {DB_NAME}")
        
        # 2. Obtener mapeo de variables REALES
        print("\n" + "=" * 80)
        print("PROCESANDO VARIABLES REALES".center(80))
        print("=" * 80)
        mapeo_variables_real = obtener_mapeo_variables(conn)
        
        if not mapeo_variables_real:
            raise ValueError("No se encontraron variables REALES de curva de pesos en maestro")
        
        # 3. Leer Excel REAL
        df_excel_real = leer_excel(ARCHIVO_EXCEL_REAL)
        if df_excel_real is None:
            raise ValueError(f"No se pudo leer el archivo: {ARCHIVO_EXCEL_REAL}")
        
        # 4. Transformar a formato largo
        df_precios_real = transformar_a_formato_largo(
            df_excel_real, 
            mapeo_variables_real, 
            MAPEO_COLUMNAS_VARIABLES_REAL
        )
        
        if df_precios_real.empty:
            raise ValueError("No hay datos REALES para insertar")
        
        print(f"\n[INFO] Datos REALES preparados: {len(df_precios_real)} registros")
        print(f"[INFO] Variables únicas: {df_precios_real['id_variable'].nunique()}")
        
        # 5. Insertar en base de datos
        insertar_en_bd(conn, df_precios_real)
        
        # 6. Verificar inserción
        verificar_insercion(conn)
        
        print("\n[OK] Proceso completado exitosamente para datos REALES")
        
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
