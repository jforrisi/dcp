"""
Script: salario_real
--------------------
Actualiza la base de datos con la serie de Salario Real (índice, sector privado) del INE.

1) Intentar lectura directa desde la URL (requests + fallback SSL para CI).
2) Si falla, leer desde data_raw/.
3) Validar fechas.
4) Actualizar automáticamente la base de datos.
"""

import os
import sys
from io import BytesIO

import pandas as pd
import requests
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de origen de datos
URL_EXCEL_INE = "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/SERIES%20Y%20OTROS/IMS/Base%20Julio%202008=100/IMS%20C1%20SR%20Gral%20P-P%20M%20emp%20B08.xls"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "salario_real_ine.xls"

# Configuración de base de datos
ID_VARIABLE = 15  # Salario real (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 858  # Uruguay_database.xlsx Sheet1_old)


def _descargar_excel_ine():
    """
    Descarga el Excel del INE por HTTP. Usa requests; si falla por SSL (CI), reintenta con verify=False.
    """
    try:
        r = requests.get(URL_EXCEL_INE, timeout=60)
        r.raise_for_status()
        return r.content
    except requests.exceptions.SSLError as e:
        print(f"[WARN] SSL al descargar INE: {e}")
        print("[INFO] Reintentando sin verificación SSL (entorno CI)...")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.get(URL_EXCEL_INE, timeout=60, verify=False)
        r.raise_for_status()
        return r.content


def leer_excel_desde_url():
    """
    Intenta leer el Excel directamente desde la URL (descarga con requests, luego pandas).
    Usa columnas A (fecha) y C (salario real privado), desde la fila 40.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL del INE...")
    print(f"   URL: {URL_EXCEL_INE}")

    content = _descargar_excel_ine()
    salario_df = pd.read_excel(
        BytesIO(content),
        sheet_name=0,
        usecols=[0, 2],  # Columnas A y C
        skiprows=39,  # comienza en la fila 40 (0-index)
        header=None,
        engine="xlrd",  # .xls
    )

    salario_df.columns = ["FECHA", "SALARIO_REAL"]

    # Eliminar filas completamente vacías
    salario_df = salario_df.dropna(how="all")

    # Eliminar filas donde fecha o salario sean nulos
    salario_df = salario_df.dropna(subset=["FECHA", "SALARIO_REAL"])
    
    # Parsear fechas
    salario_df["FECHA"] = pd.to_datetime(salario_df["FECHA"], errors="coerce")
    salario_df = salario_df[salario_df["FECHA"].notna()].copy()
    salario_df["VALOR"] = salario_df["SALARIO_REAL"]

    print(f"[OK] Leido desde URL: {len(salario_df)} registros válidos")
    return salario_df[["FECHA", "VALOR"]]


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/salario_real_ine.xls.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (salario_real en macro/download/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    salario_df = pd.read_excel(
        ruta_local,
        sheet_name=0,
        usecols=[0, 2],
        skiprows=39,
        header=None,
    )
    salario_df.columns = ["FECHA", "SALARIO_REAL"]

    # Eliminar filas completamente vacías
    salario_df = salario_df.dropna(how="all")

    # Eliminar filas donde fecha o salario sean nulos
    salario_df = salario_df.dropna(subset=["FECHA", "SALARIO_REAL"])
    
    # Parsear fechas
    salario_df["FECHA"] = pd.to_datetime(salario_df["FECHA"], errors="coerce")
    salario_df = salario_df[salario_df["FECHA"].notna()].copy()
    salario_df["VALOR"] = salario_df["SALARIO_REAL"]

    print(f"[OK] Leido desde archivo local: {len(salario_df)} registros válidos")
    return salario_df[["FECHA", "VALOR"]]


def obtener_salario_real():
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
    try:
        _main()
    except Exception as e:
        print(f"[ERROR] No se pudo actualizar salario real: {e}")
        print("[INFO] Verificar URL INE o data_raw/salario_real_ine.xls.")
        sys.exit(1)


def _main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: SALARIO REAL (INE)")
    print("=" * 60)

    salario_df = obtener_salario_real()
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(salario_df.head())
    print("\nÚltimos datos:")
    print(salario_df.tail())
    
    # Validar fechas
    salario_df = validar_fechas_solo_nulas(salario_df)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, salario_df)


if __name__ == "__main__":
    main()
