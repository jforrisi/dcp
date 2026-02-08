"""
Script: tipo_cambio_usd
------------------------
Actualiza la base de datos con la serie de tipo de cambio USD/UYU del INE.

1) Intentar lectura directa del Excel con pandas desde la URL.
2) Si falla, leer desde data_raw/.
3) Validar fechas.
4) Actualizar automáticamente la base de datos.

NOTA: El valor es el promedio entre compra (columna C) y venta (columna D).
"""

import os

import pandas as pd
from _helpers import (
    validar_fechas_unificado,
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de origen de datos
URL_EXCEL_INE = "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/SERIES%20Y%20OTROS/Cotizaci%C3%B3n%20monedas/Cotizaci%C3%B3n%20monedas.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "cotizacion_monedas_ine.xlsx"

# Configuración de base de datos
DB_NAME = "series_tiempo.db"
ID_VARIABLE = 20  # USD/LC (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 858  # Uruguay_database.xlsx Sheet1_old)


def leer_excel_desde_url():
    """
    Intenta leer el Excel directamente desde la URL con pandas.
    Lee columna A (fecha), C (compra USD), D (venta USD).
    Calcula el promedio entre compra y venta.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL del INE...")
    print(f"   URL: {URL_EXCEL_INE}")
    
    # Leer columnas A (fecha), C (compra USD), D (venta USD)
    try:
        tc_df = pd.read_excel(
            URL_EXCEL_INE,
            sheet_name=0,  # primera hoja
            usecols=[0, 2, 3],  # Columnas A (fecha), C (compra USD), D (venta USD)
            header=None,
        )
    except Exception as e:
        # Si falla con la primera hoja, intentar sin especificar hoja
        print(f"[WARN] Error al leer primera hoja: {e}")
        print("[INFO] Intentando leer sin especificar hoja...")
        tc_df = pd.read_excel(
            URL_EXCEL_INE,
            usecols=[0, 2, 3],  # Columnas A (fecha), C (compra USD), D (venta USD)
            header=None,
        )
    
    tc_df.columns = ["FECHA", "COMPRA_USD", "VENTA_USD"]
    
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
    tc_df["COMPRA_USD"] = pd.to_numeric(tc_df["COMPRA_USD"], errors="coerce")
    tc_df["VENTA_USD"] = pd.to_numeric(tc_df["VENTA_USD"], errors="coerce")
    
    # Calcular promedio solo si ambas columnas tienen valores válidos
    tc_df["VALOR"] = (tc_df["COMPRA_USD"] + tc_df["VENTA_USD"]) / 2
    
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
            "Ejecutá primero el script de descarga (tipo_cambio_usd en macro/download/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    tc_df = pd.read_excel(
        ruta_local,
        sheet_name=0,  # primera hoja
        usecols=[0, 2, 3],  # Columnas A (fecha), C (compra USD), D (venta USD)
        header=None,
    )
    
    tc_df.columns = ["FECHA", "COMPRA_USD", "VENTA_USD"]
    
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
    tc_df["COMPRA_USD"] = pd.to_numeric(tc_df["COMPRA_USD"], errors="coerce")
    tc_df["VENTA_USD"] = pd.to_numeric(tc_df["VENTA_USD"], errors="coerce")
    
    # Calcular promedio solo si ambas columnas tienen valores válidos
    tc_df["VALOR"] = (tc_df["COMPRA_USD"] + tc_df["VENTA_USD"]) / 2
    
    # Eliminar filas donde el promedio no se pudo calcular
    tc_df = tc_df.dropna(subset=["VALOR"])
    
    print(f"[OK] Leido desde archivo local: {len(tc_df)} registros válidos")
    return tc_df[["FECHA", "VALOR"]]


def obtener_tipo_cambio_usd():
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


def completar_dias_faltantes(df: pd.DataFrame, columna_fecha: str = 'FECHA', columna_valor: str = 'VALOR') -> pd.DataFrame:
    """
    Completa días faltantes en una serie diaria usando forward fill.
    """
    print("\n[INFO] Completando días faltantes en serie diaria...")
    
    df = df.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha])
    df = df.sort_values(columna_fecha).reset_index(drop=True)
    
    fecha_min = df[columna_fecha].min()
    fecha_max = df[columna_fecha].max()
    
    rango_completo = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
    df_completo = pd.DataFrame({columna_fecha: rango_completo})
    
    df_completo = df_completo.merge(
        df[[columna_fecha, columna_valor]], 
        on=columna_fecha, 
        how='left'
    )
    
    df_completo[columna_valor] = df_completo[columna_valor].ffill()
    
    dias_originales = len(df)
    dias_completados = len(df_completo)
    dias_agregados = dias_completados - dias_originales
    
    if dias_agregados > 0:
        print(f"[INFO] Se completaron {dias_agregados} días faltantes (de {dias_originales} a {dias_completados} días)")
        print(f"   Rango: {fecha_min.strftime('%d/%m/%Y')} a {fecha_max.strftime('%d/%m/%Y')}")
    else:
        print(f"[OK] No había días faltantes ({dias_originales} días en el rango)")
    
    return df_completo


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD (INE)")
    print("=" * 60)

    tc_df = obtener_tipo_cambio_usd()
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(tc_df.head())
    print("\nÚltimos datos:")
    print(tc_df.tail())
    
    # COMPLETAR DÍAS FALTANTES (OBLIGATORIO para series diarias)
    tc_df = completar_dias_faltantes(tc_df, columna_fecha='FECHA', columna_valor='VALOR')
    
    # Validar fechas (las fechas ya están parseadas, solo validar nulas)
    tc_df = validar_fechas_solo_nulas(tc_df)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, tc_df, DB_NAME)


if __name__ == "__main__":
    main()
