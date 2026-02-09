"""
Script: leche_polvo_entera
--------------------------
Actualiza la base de datos con la serie de exportación leche en polvo entera (INALE).

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
URL_EXCEL_INALE = "https://www.inale.org/wp-content/uploads/2025/12/Exportacion-leche-en-polvo-entera.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "exportacion_leche_polvo_entera.xlsx"

# Configuración de base de datos
ID_VARIABLE = 10  # Leche en polvo - INALE (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 858  # Uruguay_database.xlsx Sheet1_old)


def leer_excel_desde_url():
    """
    Intenta leer el Excel directamente desde la URL con pandas.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL de INALE...")
    leche_polvo = pd.read_excel(
        URL_EXCEL_INALE,
        sheet_name="Listado Datos Mensuales",
        skiprows=19,  # empieza en fila 20
        usecols="B,E",  # B = fecha, E = precio
        header=None,
    )
    leche_polvo.columns = ["FECHA", "PRECIO"]
    # Filtrar filas donde la fecha no es válida (texto, notas, etc.)
    leche_polvo = leche_polvo.dropna(subset=["FECHA"])
    # Intentar parsear fechas y filtrar las que no se pueden parsear
    fechas_parseadas = pd.to_datetime(leche_polvo["FECHA"], errors="coerce")
    leche_polvo = leche_polvo[fechas_parseadas.notna()].copy()
    leche_polvo["FECHA"] = pd.to_datetime(leche_polvo["FECHA"])
    leche_polvo["VALOR"] = leche_polvo["PRECIO"]
    print(f"[OK] Leido desde URL: {len(leche_polvo)} registros válidos")
    return leche_polvo[["FECHA", "VALOR"]]


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/exportacion_leche_polvo_entera.xlsx.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (leche_polvo_entera en precios/download/productos/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    leche_polvo = pd.read_excel(
        ruta_local,
        sheet_name="Listado Datos Mensuales",
        skiprows=19,  # empieza en fila 20
        usecols="B,E",  # B = fecha, E = precio
        header=None,
    )
    leche_polvo.columns = ["FECHA", "PRECIO"]
    # Filtrar filas donde la fecha no es válida (texto, notas, etc.)
    leche_polvo = leche_polvo.dropna(subset=["FECHA"])
    # Intentar parsear fechas y filtrar las que no se pueden parsear
    fechas_parseadas = pd.to_datetime(leche_polvo["FECHA"], errors="coerce")
    leche_polvo = leche_polvo[fechas_parseadas.notna()].copy()
    leche_polvo["FECHA"] = pd.to_datetime(leche_polvo["FECHA"])
    leche_polvo["VALOR"] = leche_polvo["PRECIO"]
    print(f"[OK] Leido desde archivo local: {len(leche_polvo)} registros válidos")
    return leche_polvo[["FECHA", "VALOR"]]


def obtener_leche_polvo():
    """
    Lee desde data_raw (el script de descarga debe ejecutarse primero).
    """
    return leer_excel_desde_data_raw()


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: EXPORTACION LECHE EN POLVO ENTERA (INALE)")
    print("=" * 60)
    
    leche_polvo = obtener_leche_polvo()
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(leche_polvo.head())
    print("\nÚltimos datos:")
    print(leche_polvo.tail())
    
    leche_polvo = validar_fechas_unificado(leche_polvo)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, leche_polvo)


if __name__ == "__main__":
    main()
