"""
Script: precio_arroz_wb
-----------------------
Actualiza la base de datos con la serie de precios de arroz del Banco Mundial.

1) Intentar lectura directa del Excel con pandas desde la URL.
2) Si falla, leer desde data_raw/.
3) Validar fechas.
4) Actualizar automáticamente la base de datos.

NOTA: Los datos están en la hoja "Monthly Prices", empiezan en la fila 7.
Columna A tiene fechas en formato "2025M12" (diciembre 2025) o "2025M07" (julio 2025).
Columna AG es el precio de arroz.
"""

import os
import re

import pandas as pd
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de origen de datos
URL_EXCEL_WB = "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "cmo_historical_data_monthly_wb.xlsx"

# Configuración de base de datos
DB_NAME = "series_tiempo.db"
ID_VARIABLE = 2  # Arroz (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 999  # Economía internacional_database.xlsx Sheet1_old)


def parsear_fecha_wb(fecha_str):
    """
    Parsea fechas en formato del Banco Mundial: "2025M12" o "2025M07"
    Retorna un pd.Timestamp o None si no se puede parsear.
    """
    if pd.isna(fecha_str):
        return None
    
    fecha_str = str(fecha_str).strip()
    
    # Patrón: YYYYMM o YYYYM## (ej: 2025M12, 2025M07, 202512)
    patrones = [
        r'^(\d{4})M(\d{1,2})$',  # 2025M12, 2025M7
        r'^(\d{4})(\d{2})$',      # 202512
    ]
    
    for patron in patrones:
        match = re.match(patron, fecha_str)
        if match:
            año = int(match.group(1))
            mes = int(match.group(2))
            
            if 1 <= mes <= 12 and 1900 <= año <= 2100:
                return pd.Timestamp(year=año, month=mes, day=1)
    
    return None


def leer_excel_desde_url():
    """
    Intenta leer el Excel directamente desde la URL con pandas.
    Lee la hoja "Monthly Prices", fila 7 en adelante.
    Columna A = fechas (formato "2025M12"), Columna AG = precio arroz.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL del Banco Mundial...")
    print(f"   URL: {URL_EXCEL_WB}")
    
    try:
        # Leer la hoja "Monthly Prices", empezando desde la fila 7 (skiprows=6)
        # Columna A (índice 0) = fechas, Columna AG (índice 32) = arroz
        df = pd.read_excel(
            URL_EXCEL_WB,
            sheet_name="Monthly Prices",
            skiprows=6,  # Los datos empiezan en la fila 7
            usecols=[0, 32],  # Columna A (fechas) y Columna AG (arroz)
            header=None,
        )
        
        # Renombrar columnas
        df.columns = ["FECHA_STR", "ARROZ"]
        
        # Eliminar filas completamente vacías
        df = df.dropna(how="all")
        
        # Eliminar filas donde fecha o arroz sean nulos
        df = df.dropna(subset=["FECHA_STR", "ARROZ"])
        
        # Filtrar filas donde arroz no sea numérico
        df = df[pd.to_numeric(df["ARROZ"], errors="coerce").notna()]
        
        print(f"[OK] Leido desde URL: {len(df)} registros válidos")
        return df
        
    except Exception as e:
        print(f"[ERROR] Error al leer desde URL: {e}")
        raise


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/cmo_historical_data_monthly_wb.xlsx.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (precios/download/productos/precio_arroz_wb.py)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    
    try:
        # Leer la hoja "Monthly Prices", empezando desde la fila 7 (skiprows=6)
        # Columna A (índice 0) = fechas, Columna AG (índice 32) = arroz
        df = pd.read_excel(
            ruta_local,
            sheet_name="Monthly Prices",
            skiprows=6,  # Los datos empiezan en la fila 7
            usecols=[0, 32],  # Columna A (fechas) y Columna AG (arroz)
            header=None,
        )
        
        # Renombrar columnas
        df.columns = ["FECHA_STR", "ARROZ"]
        
        # Eliminar filas completamente vacías
        df = df.dropna(how="all")
        
        # Eliminar filas donde fecha o arroz sean nulos
        df = df.dropna(subset=["FECHA_STR", "ARROZ"])
        
        # Filtrar filas donde arroz no sea numérico
        df = df[pd.to_numeric(df["ARROZ"], errors="coerce").notna()]
        
        print(f"[OK] Leido desde archivo local: {len(df)} registros válidos")
        return df
        
    except Exception as e:
        print(f"[ERROR] Error al leer desde archivo local: {e}")
        raise


def convertir_fechas_wb(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte las fechas del formato del Banco Mundial ("2025M12") a datetime.
    """
    print("\n[INFO] Convirtiendo fechas del formato Banco Mundial...")
    
    fechas = []
    fechas_invalidas = []
    
    for idx, fecha_str in enumerate(df["FECHA_STR"]):
        fecha_parseada = parsear_fecha_wb(fecha_str)
        
        if fecha_parseada is None:
            fechas_invalidas.append((idx + 7, fecha_str, "Formato no reconocido"))
        else:
            fechas.append(fecha_parseada)
    
    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas inválidas:")
        for fila_excel, fecha, motivo in fechas_invalidas[:10]:
            print(f"   Fila Excel {fila_excel}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} más")
        raise ValueError("Hay fechas inválidas. No se puede continuar.")
    
    df = df.copy()
    df["FECHA"] = fechas
    df["VALOR"] = df["ARROZ"]
    print(f"[OK] {len(fechas)} fechas convertidas correctamente")
    return df[["FECHA", "VALOR"]]


def obtener_arroz():
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
    print("ACTUALIZACION DE DATOS: PRECIO ARROZ - BANCO MUNDIAL")
    print("=" * 60)

    arroz_df = obtener_arroz()
    
    # Mostrar primeros y últimos datos de la serie cruda
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(arroz_df.head())
    print("\nÚltimos datos:")
    print(arroz_df.tail())
    
    # Convertir fechas del formato Banco Mundial
    arroz_df = convertir_fechas_wb(arroz_df)
    arroz_df = validar_fechas_solo_nulas(arroz_df)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, arroz_df, DB_NAME)


if __name__ == "__main__":
    main()
