"""
Script: tipo_cambio_eur
------------------------
Actualiza la base de datos con la serie de tipo de cambio EUR/UYU del INE.

1) Intentar lectura directa del Excel desde la URL (requests + certifi; fallback sin verify en CI).
2) Si falla, leer desde data_raw/.
3) Validar fechas.
4) Actualizar automáticamente la base de datos.

NOTA: El valor es el promedio entre compra (columna E) y venta (columna F).
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
URL_EXCEL_INE = "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/SERIES%20Y%20OTROS/Cotizaci%C3%B3n%20monedas/Cotizaci%C3%B3n%20monedas.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "cotizacion_monedas_ine.xlsx"

# Configuración de base de datos
ID_VARIABLE = 6  # EUR/LC (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 858  # Uruguay_database.xlsx Sheet1_old)


def _descargar_excel_ine():
    """
    Descarga el Excel del INE por HTTP. Usa requests (certifi en CI).
    Si falla por SSL (p. ej. en GitHub Actions), reintenta con verify=False.
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
    Lee columna A (fecha), E (compra EUR), F (venta EUR).
    Calcula el promedio entre compra y venta.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL del INE...")
    print(f"   URL: {URL_EXCEL_INE}")
    
    content = _descargar_excel_ine()
    
    # Leer columnas A (fecha), E (compra EUR), F (venta EUR)
    try:
        tc_df = pd.read_excel(
            BytesIO(content),
            sheet_name=0,  # primera hoja
            usecols=[0, 4, 5],  # Columnas A (fecha), E (compra EUR), F (venta EUR)
            header=None,
        )
    except Exception as e:
        # Si falla con la primera hoja, intentar sin especificar hoja
        print(f"[WARN] Error al leer primera hoja: {e}")
        print("[INFO] Intentando leer sin especificar hoja...")
        tc_df = pd.read_excel(
            BytesIO(content),
            usecols=[0, 4, 5],  # Columnas A (fecha), E (compra EUR), F (venta EUR)
            header=None,
        )
    
    tc_df.columns = ["FECHA", "COMPRA_EUR", "VENTA_EUR"]
    
    # Eliminar filas completamente vacías
    tc_df = tc_df.dropna(how="all")
    
    # Eliminar filas donde fecha sea nula
    tc_df = tc_df.dropna(subset=["FECHA"])
    
    # Filtrar filas que parezcan encabezados o texto (fecha debe ser parseable)
    # Las fechas están en formato dd-mm-yyyy, usar dayfirst=True
    fechas_parseadas = pd.to_datetime(tc_df["FECHA"], errors="coerce", dayfirst=True)
    tc_df = tc_df[fechas_parseadas.notna()].copy()
    tc_df["FECHA"] = pd.to_datetime(tc_df["FECHA"], dayfirst=True)
    
    # Calcular promedio entre compra y venta
    tc_df["COMPRA_EUR"] = pd.to_numeric(tc_df["COMPRA_EUR"], errors="coerce")
    tc_df["VENTA_EUR"] = pd.to_numeric(tc_df["VENTA_EUR"], errors="coerce")
    
    # Calcular promedio solo si ambas columnas tienen valores válidos
    tc_df["VALOR"] = (tc_df["COMPRA_EUR"] + tc_df["VENTA_EUR"]) / 2
    
    # Eliminar filas donde el promedio no se pudo calcular
    tc_df = tc_df.dropna(subset=["VALOR"])
    
    print(f"[OK] Leido desde URL: {len(tc_df)} registros válidos")
    return tc_df[["FECHA", "VALOR"]]


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/cotizacion_monedas_ine.xlsx.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (tipo_cambio_eur en macro/download/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    tc_df = pd.read_excel(
        ruta_local,
        sheet_name=0,  # primera hoja
        usecols=[0, 4, 5],  # Columnas A (fecha), E (compra EUR), F (venta EUR)
        header=None,
    )
    
    tc_df.columns = ["FECHA", "COMPRA_EUR", "VENTA_EUR"]
    
    # Eliminar filas completamente vacías
    tc_df = tc_df.dropna(how="all")
    
    # Eliminar filas donde fecha sea nula
    tc_df = tc_df.dropna(subset=["FECHA"])
    
    # Filtrar filas que parezcan encabezados o texto (fecha debe ser parseable)
    # Las fechas están en formato dd-mm-yyyy, usar dayfirst=True
    fechas_parseadas = pd.to_datetime(tc_df["FECHA"], errors="coerce", dayfirst=True)
    tc_df = tc_df[fechas_parseadas.notna()].copy()
    tc_df["FECHA"] = pd.to_datetime(tc_df["FECHA"], dayfirst=True)
    
    # Calcular promedio entre compra y venta
    tc_df["COMPRA_EUR"] = pd.to_numeric(tc_df["COMPRA_EUR"], errors="coerce")
    tc_df["VENTA_EUR"] = pd.to_numeric(tc_df["VENTA_EUR"], errors="coerce")
    
    # Calcular promedio solo si ambas columnas tienen valores válidos
    tc_df["VALOR"] = (tc_df["COMPRA_EUR"] + tc_df["VENTA_EUR"]) / 2
    
    # Eliminar filas donde el promedio no se pudo calcular
    tc_df = tc_df.dropna(subset=["VALOR"])
    
    print(f"[OK] Leido desde archivo local: {len(tc_df)} registros válidos")
    return tc_df[["FECHA", "VALOR"]]


def obtener_tipo_cambio_eur():
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
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO EUR (INE)")
    print("=" * 60)

    try:
        tc_df = obtener_tipo_cambio_eur()
    except Exception as e:
        print(f"[ERROR] No se pudo obtener tipo de cambio EUR: {e}")
        print("[INFO] Verificar URL INE o data_raw/cotizacion_monedas_ine.xlsx.")
        sys.exit(1)
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(tc_df.head())
    print("\nÚltimos datos:")
    print(tc_df.tail())
    
    # Validar fechas (las fechas ya están parseadas, solo validar nulas)
    tc_df = validar_fechas_solo_nulas(tc_df)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, tc_df)


if __name__ == "__main__":
    main()
