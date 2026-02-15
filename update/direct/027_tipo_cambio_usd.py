"""
Script: tipo_cambio_usd
------------------------
Actualiza la base de datos con la serie de tipo de cambio USD/UYU desde BEVSA.

Lee update/historicos/dolar_bevsa_uyu.xlsx:
- Columna A: FECHA
- Columna B: CIERRE BCU BILLETE (valor utilizado)

Ejecutá primero update/run_single.py dolar_bevsa_uyu para actualizar el Excel.
"""

import os

import pandas as pd
from _helpers import (
    completar_dias_faltantes,
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de origen de datos (BEVSA)
HISTORICOS_DIR = "update/historicos"
EXCEL_BEVSA = "dolar_bevsa_uyu.xlsx"
EXCEL_BEVSA_FALLBACK = "dolar_bevsa_uy.xlsx"

# Configuración de base de datos
ID_VARIABLE = 20  # USD/LC (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 858  # Uruguay


def leer_excel_bevsa():
    """
    Lee el Excel de BEVSA con columna A (FECHA) y B (CIERRE BCU BILLETE).
    Usa dolar_bevsa_uyu.xlsx o dolar_bevsa_uy.xlsx como fallback.
    """
    base_dir = os.getcwd()
    ruta_principal = os.path.join(base_dir, HISTORICOS_DIR, EXCEL_BEVSA)
    ruta_fallback = os.path.join(base_dir, HISTORICOS_DIR, EXCEL_BEVSA_FALLBACK)

    ruta = ruta_principal if os.path.exists(ruta_principal) else ruta_fallback
    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"No se encontró {EXCEL_BEVSA} ni {EXCEL_BEVSA_FALLBACK} en {HISTORICOS_DIR}. "
            "Ejecutá primero: python update/run_single.py dolar_bevsa_uyu"
        )

    print(f"\n[INFO] Leyendo Excel BEVSA desde: {ruta}")
    # Leer todo el sheet para elegir columnas por nombre (el orden de columnas puede variar)
    tc_df = pd.read_excel(ruta, sheet_name=0, header=0)

    # Buscar columna de fecha (A) y columna CIERRE BCU BILLETE (valor a usar; NO CANTIDAD)
    col_fecha = None
    col_valor = None
    for c in tc_df.columns:
        cstr = str(c).strip().upper()
        if "FECHA" in cstr or cstr == "FECHA":
            col_fecha = c
        if "CIERRE" in cstr and "BILLETE" in cstr:
            col_valor = c
    if col_fecha is None:
        col_fecha = tc_df.columns[0]
    if col_valor is None:
        raise ValueError(
            "No se encontró la columna 'CIERRE BCU BILLETE' en el Excel. "
            f"Columnas presentes: {list(tc_df.columns)}"
        )
    print(f"   Usando columna de valor: '{col_valor}' (CIERRE BCU BILLETE)")
    tc_df = tc_df[[col_fecha, col_valor]].copy()
    tc_df = tc_df.rename(columns={col_fecha: "FECHA", col_valor: "VALOR"})
    tc_df = tc_df.dropna(how="all")
    tc_df = tc_df.dropna(subset=["FECHA"])
    tc_df["FECHA"] = pd.to_datetime(tc_df["FECHA"], errors="coerce")
    tc_df = tc_df.dropna(subset=["FECHA"])
    tc_df["VALOR"] = pd.to_numeric(tc_df["VALOR"], errors="coerce")
    tc_df = tc_df.dropna(subset=["VALOR"])

    print(f"[OK] Leídos {len(tc_df)} registros válidos")
    return tc_df[["FECHA", "VALOR"]]


def obtener_tipo_cambio_usd():
    """Obtiene tipo de cambio USD/UYU desde el Excel BEVSA."""
    return leer_excel_bevsa()


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD (BEVSA - CIERRE BCU BILLETE)")
    print("=" * 60)

    tc_df = obtener_tipo_cambio_usd()
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(tc_df.head())
    print("\nÚltimos datos:")
    print(tc_df.tail())
    
    # COMPLETAR DÍAS FALTANTES y luego QUEDAR SOLO LUNES A VIERNES
    tc_df = completar_dias_faltantes(
        tc_df, columna_fecha='FECHA', columna_valor='VALOR', solo_lunes_a_viernes=True
    )
    
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
