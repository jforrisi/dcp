"""
Script: novillo_hacienda
-------------------------
Actualiza la base de datos con la serie de novillo hacienda (INAC).

1) Intentar lectura directa del Excel con pandas desde la URL.
2) Si falla, leer el Excel local desde data_raw/precios_hacienda_inac.xlsx.
3) Validar fechas.
4) Actualizar automáticamente la base de datos.
"""

import os

import pandas as pd
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de origen de datos
URL_EXCEL_INAC = "https://www.inac.uy/innovaportal/file/10953/1/precios-hacienda-mensual.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "precios_hacienda_inac.xlsx"

# Configuración de base de datos
DB_NAME = "series_tiempo.db"
ID_VARIABLE = 12  # Precio hacienda - INAC (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 858  # Uruguay (desde maestro_database.xlsx Sheet1_old)


def mapear_mes_espanol_a_numero(mes_str):
    """
    Mapea el mes en español abreviado a número de mes (1-12).
    Ene -> 1, Feb -> 2, ..., Dic -> 12
    """
    meses_espanol = {
        "Ene": 1,
        "Feb": 2,
        "Mar": 3,
        "Abr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Ago": 8,
        "Set": 9,
        "Oct": 10,
        "Nov": 11,
        "Dic": 12,
    }
    return meses_espanol.get(mes_str, None)


def leer_excel_desde_url():
    """
    Intenta leer el Excel directamente desde la URL con pandas.
    Devuelve un DataFrame o lanza excepción si falla.
    Estructura del Excel: Año (col A), Mes (col C), Precio 4ta balanza (col E).
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL de INAC...")
    df = pd.read_excel(
        URL_EXCEL_INAC,
        sheet_name="HACIENDA",
        skiprows=12,
        usecols="A,C,E",  # Año, Mes, Precio 4ta balanza
        header=None,
    )
    df.columns = ["AÑO", "MES", "NOVILLO_HACIENDA"]
    
    # Construir fecha a partir de Año y Mes (meses en español)
    df = df.dropna(subset=["AÑO", "MES", "NOVILLO_HACIENDA"])
    
    # Mapear meses en español a números
    df["MES_NUM"] = df["MES"].astype(str).str.strip().apply(mapear_mes_espanol_a_numero)
    df = df.dropna(subset=["MES_NUM"])
    
    # Construir fecha usando año y número de mes
    df["FECHA"] = pd.to_datetime(
        df["AÑO"].astype(int).astype(str)
        + "-"
        + df["MES_NUM"].astype(int).astype(str).str.zfill(2)
        + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    )
    df = df.dropna(subset=["FECHA"])
    df["VALOR"] = df["NOVILLO_HACIENDA"]
    print(f"[OK] Leido desde URL: {len(df)} registros")
    return df[["FECHA", "VALOR"]]


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw.
    Primero intenta usar el nombre estándar (precios_hacienda_inac.xlsx).
    Si no existe, busca automáticamente el Excel más reciente que contenga "hacienda" o "inac" en el nombre.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    
    # Primero intentar con el nombre estándar
    ruta_local = os.path.join(data_raw_path, LOCAL_EXCEL_NAME)
    
    if not os.path.exists(ruta_local):
        # Buscar automáticamente el archivo más reciente que contenga "hacienda" o "inac"
        print(f"\n[INFO] No se encontró {LOCAL_EXCEL_NAME}, buscando archivo alternativo...")
        
        if not os.path.exists(data_raw_path):
            raise FileNotFoundError(
                f"No existe la carpeta {data_raw_path}. "
                "Ejecutá primero el script de descarga (precios/download/productos/novillo_hacienda.py)."
            )
        
        # Buscar archivos que contengan palabras clave
        candidatos = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx", ".csv"))
            and any(term in f.lower() for term in ["hacienda", "inac", "novillo"])
            and not f.startswith("~$")  # Excluir archivos temporales
        ]
        
        if not candidatos:
            raise FileNotFoundError(
                f"No se encontró ningún archivo de hacienda en {data_raw_path}. "
                "Ejecutá primero el script de descarga (precios/download/productos/novillo_hacienda.py)."
            )
        
        # Elegir el más reciente
        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ruta_local = max(candidatos_paths, key=os.path.getmtime)
        print(f"[INFO] Usando archivo encontrado: {os.path.basename(ruta_local)}")

    print(f"\n[INFO] Leyendo archivo local desde: {ruta_local}")
    
    # Leer Excel (mismo formato que desde URL)
    df = pd.read_excel(
        ruta_local,
        sheet_name="HACIENDA",
        skiprows=12,
        usecols="A,C,E",  # Año, Mes, Precio 4ta balanza
        header=None,
    )
    df.columns = ["AÑO", "MES", "NOVILLO_HACIENDA"]
    
    # Construir fecha a partir de Año y Mes (meses en español)
    df = df.dropna(subset=["AÑO", "MES", "NOVILLO_HACIENDA"])
    
    # Mapear meses en español a números
    df["MES_NUM"] = df["MES"].astype(str).str.strip().apply(mapear_mes_espanol_a_numero)
    df = df.dropna(subset=["MES_NUM"])
    
    # Construir fecha usando año y número de mes
    df["FECHA"] = pd.to_datetime(
        df["AÑO"].astype(int).astype(str)
        + "-"
        + df["MES_NUM"].astype(int).astype(str).str.zfill(2)
        + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    )
    df = df.dropna(subset=["FECHA"])
    df["VALOR"] = df["NOVILLO_HACIENDA"]
    
    print(f"[OK] Leido desde archivo local: {len(df)} registros válidos")
    return df[["FECHA", "VALOR"]]


def obtener_novillo_hacienda():
    """
    Implementa el flujo:
    1) Intentar lectura directa desde URL.
    2) Si falla, leer desde data_raw.
    """
    try:
        return leer_excel_desde_url()
    except Exception as e:
        print(f"[WARN] No se pudo leer desde URL: {e}")
        print("       Intentando leer desde data_raw...")
        return leer_excel_desde_data_raw()


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: NOVILLO HACIENDA (INAC)")
    print("=" * 60)

    novillo_df = obtener_novillo_hacienda()
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(novillo_df.head())
    print("\nÚltimos datos:")
    print(novillo_df.tail())
    
    novillo_df = validar_fechas_solo_nulas(novillo_df)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, novillo_df, DB_NAME)


if __name__ == "__main__":
    main()
