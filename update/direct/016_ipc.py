"""
Script: ipc
-----------
Actualiza la base de datos con la serie de IPC (Índice de Precios al Consumo) del INE.

1) Descargar Excel con requests (fallback SSL en CI); leer con pandas desde BytesIO.
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
URL_EXCEL_INE = "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/SERIES%20Y%20OTROS/IPC/Base%20Octubre%202022=100/IPC%20gral%20y%20variaciones_base%202022.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "ipc_general_ine.xlsx"

# Configuración de base de datos
ID_VARIABLE = 9  # IPC (desde maestro_database.xlsx Sheet1_old)
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
    Descarga el Excel con requests y lo lee con pandas (BytesIO).
    Lee columnas A (fecha) y B (IPC) desde la fila 15.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel desde la URL del INE (requests + BytesIO)...")
    print(f"   URL: {URL_EXCEL_INE}")

    content = _descargar_excel_ine()
    try:
        ipc_df = pd.read_excel(
            BytesIO(content),
            sheet_name=0,
            usecols=[0, 1],
            skiprows=14,
            header=None,
        )
    except Exception as e:
        print(f"[WARN] Error al leer primera hoja: {e}")
        print("[INFO] Intentando leer sin especificar hoja...")
        ipc_df = pd.read_excel(
            BytesIO(content),
            usecols=[0, 1],
            skiprows=14,
            header=None,
        )

    ipc_df.columns = ["FECHA", "IPC"]
    
    # Eliminar filas completamente vacías
    ipc_df = ipc_df.dropna(how="all")
    
    # Eliminar filas donde fecha o IPC sean nulos
    ipc_df = ipc_df.dropna(subset=["FECHA", "IPC"])
    
    # Convertir fecha a datetime si no lo es
    ipc_df["FECHA"] = pd.to_datetime(ipc_df["FECHA"], errors="coerce")
    
    # Eliminar filas donde la fecha no se pudo parsear
    ipc_df = ipc_df.dropna(subset=["FECHA"])
    
    # Filtrar filas donde IPC no sea numérico
    ipc_df = ipc_df[pd.to_numeric(ipc_df["IPC"], errors="coerce").notna()]
    
    print(f"[OK] Leido desde URL: {len(ipc_df)} registros válidos")
    return ipc_df


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/ipc_general_ine.xlsx.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (ipc en macro/download/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    ipc_df = pd.read_excel(
        ruta_local,
        sheet_name=0,  # primera hoja
        usecols=[0, 1],  # Columnas A (fecha) y B (IPC)
        skiprows=14,  # Empezar desde fila 15
        header=None,
    )
    ipc_df.columns = ["FECHA", "IPC"]
    
    # Eliminar filas completamente vacías
    ipc_df = ipc_df.dropna(how="all")
    
    # Eliminar filas donde fecha o IPC sean nulos
    ipc_df = ipc_df.dropna(subset=["FECHA", "IPC"])
    
    # Convertir fecha a datetime si no lo es
    ipc_df["FECHA"] = pd.to_datetime(ipc_df["FECHA"], errors="coerce")
    
    # Eliminar filas donde la fecha no se pudo parsear
    ipc_df = ipc_df.dropna(subset=["FECHA"])
    
    # Filtrar filas donde IPC no sea numérico
    ipc_df = ipc_df[pd.to_numeric(ipc_df["IPC"], errors="coerce").notna()]
    
    print(f"[OK] Leido desde archivo local: {len(ipc_df)} registros válidos")
    return ipc_df


def obtener_ipc():
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
    print("ACTUALIZACION DE DATOS: IPC (INE)")
    print("=" * 60)

    try:
        ipc_df = obtener_ipc()
    except Exception as e:
        print(f"[ERROR] No se pudo obtener IPC (URL ni archivo local): {e}")
        print("[INFO] Verificar conexión o data_raw/ipc_general_ine.xlsx.")
        sys.exit(1)
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(ipc_df.head())
    print("\nÚltimos datos:")
    print(ipc_df.tail())
    
    # La fecha ya viene parseada, solo renombrar IPC a VALOR
    ipc_df["VALOR"] = ipc_df["IPC"]
    ipc_df = ipc_df[["FECHA", "VALOR"]]
    
    # Convertir FECHA a date (sin hora) si es datetime
    if ipc_df["FECHA"].dtype == "datetime64[ns]":
        ipc_df["FECHA"] = ipc_df["FECHA"].dt.date
    
    # Validar fechas
    ipc_df = validar_fechas_solo_nulas(ipc_df)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, ipc_df)


if __name__ == "__main__":
    main()
