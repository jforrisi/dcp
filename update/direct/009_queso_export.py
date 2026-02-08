"""
Script: queso_export
--------------------
Actualiza la base de datos con la serie de exportación queso (INALE).

1) Intentar lectura directa del Excel con pandas desde la URL.
2) Si falla, leer desde data_raw/.
3) Validar fechas.
4) Actualizar automáticamente la base de datos.
"""

import os

import pandas as pd
from _helpers import (
    validar_fechas_unificado,
    insertar_en_bd_unificado
)


# Configuración de origen de datos
URL_EXCEL_INALE = "https://www.inale.org/wp-content/uploads/2025/12/Exportacion-queso.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "exportacion_queso.xlsx"

# Configuración de base de datos
DB_NAME = "series_tiempo.db"
ID_VARIABLE = 14  # Queso - INALE (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 858  # Uruguay_database.xlsx Sheet1_old)


def leer_excel_desde_url():
    """
    Intenta leer el Excel directamente desde la URL con pandas.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL de INALE...")
    queso = pd.read_excel(
        URL_EXCEL_INALE,
        sheet_name="Listado Datos Mensuales",
        skiprows=19,  # empieza en fila 20
        usecols="B,E",  # B = fecha, E = precio
        header=None,
    )
    queso.columns = ["FECHA", "PRECIO"]
    # Filtrar filas donde la fecha no es válida (texto, notas, etc.)
    queso = queso.dropna(subset=["FECHA"])
    # Intentar parsear fechas y filtrar las que no se pueden parsear
    fechas_parseadas = pd.to_datetime(queso["FECHA"], errors="coerce")
    queso = queso[fechas_parseadas.notna()].copy()
    queso["FECHA"] = pd.to_datetime(queso["FECHA"])
    queso["VALOR"] = queso["PRECIO"]
    print(f"[OK] Leido desde URL: {len(queso)} registros válidos")
    return queso[["FECHA", "VALOR"]]


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/exportacion_queso.xlsx.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (queso_export en precios/download/productos/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    queso = pd.read_excel(
        ruta_local,
        sheet_name="Listado Datos Mensuales",
        skiprows=19,  # empieza en fila 20
        usecols="B,E",  # B = fecha, E = precio
        header=None,
    )
    queso.columns = ["FECHA", "PRECIO"]
    # Filtrar filas donde la fecha no es válida (texto, notas, etc.)
    queso = queso.dropna(subset=["FECHA"])
    # Intentar parsear fechas y filtrar las que no se pueden parsear
    fechas_parseadas = pd.to_datetime(queso["FECHA"], errors="coerce")
    queso = queso[fechas_parseadas.notna()].copy()
    queso["FECHA"] = pd.to_datetime(queso["FECHA"])
    queso["VALOR"] = queso["PRECIO"]
    print(f"[OK] Leido desde archivo local: {len(queso)} registros válidos")
    return queso[["FECHA", "VALOR"]]


def obtener_queso():
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
    print("ACTUALIZACION DE DATOS: EXPORTACION QUESO (INALE)")
    print("=" * 60)
    
    queso = obtener_queso()
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(queso.head())
    print("\nÚltimos datos:")
    print(queso.tail())
    
    queso = validar_fechas_unificado(queso)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, queso, DB_NAME)


if __name__ == "__main__":
    main()
