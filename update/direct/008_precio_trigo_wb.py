"""
Script: precio_trigo_wb
-----------------------
Actualiza la base de datos con la serie de precios de trigo del Banco Mundial.

Lee desde update/historicos/commodities_banco_mundial.xlsx (generado por commodities_banco_mundial.py).
Ejecutá primero el script de descarga: update/download/commodities_banco_mundial.py

NOTA: Los datos están en la hoja "Monthly Prices", empiezan en la fila 7.
Columna A tiene fechas en formato "2025M12" (diciembre 2025) o "2025M07" (julio 2025).
Columna AL es el precio de trigo.
"""

import os
import re

import pandas as pd
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de origen de datos (Excel descargado por commodities_banco_mundial.py)
COMMODITIES_EXCEL = "update/historicos/commodities_banco_mundial.xlsx"

# Configuración de base de datos
ID_VARIABLE = 19  # Trigo (desde maestro_database.xlsx Sheet1_old)
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


def leer_excel_commodities():
    """
    Lee el Excel commodities_banco_mundial.xlsx desde update/historicos.
    Hoja "Monthly Prices", fila 7 en adelante.
    Columna A = fechas (formato "2025M12"), Columna AL = precio trigo.
    """
    base_dir = os.getcwd()
    ruta = os.path.join(base_dir, COMMODITIES_EXCEL)

    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"No se encontró: {ruta}. "
            "Ejecutá primero: python update/download/commodities_banco_mundial.py"
        )

    print(f"\n[INFO] Leyendo Excel: {ruta}")
    df = pd.read_excel(
        ruta,
        sheet_name="Monthly Prices",
        skiprows=6,
        usecols=[0, 37],  # Columna A (fechas) y Columna AL (trigo)
        header=None,
    )
    df.columns = ["FECHA_STR", "TRIGO"]
    df = df.dropna(how="all")
    df = df.dropna(subset=["FECHA_STR", "TRIGO"])
    df = df[pd.to_numeric(df["TRIGO"], errors="coerce").notna()]
    print(f"[OK] {len(df)} registros válidos")
    return df


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
    df["VALOR"] = df["TRIGO"]
    print(f"[OK] {len(fechas)} fechas convertidas correctamente")
    return df[["FECHA", "VALOR"]]


def obtener_trigo():
    """Lee el Excel de commodities desde update/historicos."""
    return leer_excel_commodities()


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: PRECIO TRIGO - BANCO MUNDIAL")
    print("=" * 60)

    trigo_df = obtener_trigo()
    
    # Mostrar primeros y últimos datos de la serie cruda
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(trigo_df.head())
    print("\nÚltimos datos:")
    print(trigo_df.tail())
    
    # Convertir fechas del formato Banco Mundial
    trigo_df = convertir_fechas_wb(trigo_df)
    trigo_df = validar_fechas_solo_nulas(trigo_df)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, trigo_df)


if __name__ == "__main__":
    main()
