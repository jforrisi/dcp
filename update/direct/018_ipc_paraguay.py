# -*- coding: utf-8 -*-
"""
Script: ipc_paraguay
--------------------
Actualiza la base de datos con la serie de IPC (Índice de Precios al Consumidor) mensual
de Paraguay desde el Excel del Banco Central del Paraguay (BCP).

1) Lee el Excel desde data_raw/ipc_paraguay.xlsx (debe ejecutarse primero el script de descarga).
2) Leer hoja "CUADRO 4", columnas A (fecha) y R (IPC) desde fila 12.
3) Parsear fechas (formato mes año).
4) Validar valores numéricos.
5) Actualizar automáticamente la base de datos.
"""

import os
import re
from datetime import datetime

import pandas as pd
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# Carpeta para leer archivos descargados
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "ipc_paraguay.xlsx"

# Configuración de IDs (desde maestro_database.xlsx Sheet1_old)
ID_VARIABLE = 9  # IPC Paraguay
ID_PAIS = 600  # Paraguay


def parsear_fecha_paraguay(fecha_str):
    """
    Parsea fecha en formato "mes año" de Paraguay.
    Ejemplos: "Enero 2024", "Dic 2023", "Ene 2024"
    
    Args:
        fecha_str: String con la fecha
        
    Returns:
        datetime object o None si no se puede parsear
    """
    if pd.isna(fecha_str) or not isinstance(fecha_str, str):
        return None
    
    fecha_str = str(fecha_str).strip()
    
    # Mapeo de meses en español
    meses_map = {
        'enero': 1, 'ene': 1,
        'febrero': 2, 'feb': 2,
        'marzo': 3, 'mar': 3,
        'abril': 4, 'abr': 4,
        'mayo': 5, 'may': 5,
        'junio': 6, 'jun': 6,
        'julio': 7, 'jul': 7,
        'agosto': 8, 'ago': 8,
        'septiembre': 9, 'sep': 9, 'setiembre': 9, 'set': 9,
        'octubre': 10, 'oct': 10,
        'noviembre': 11, 'nov': 11,
        'diciembre': 12, 'dic': 12
    }
    
    # Intentar diferentes formatos
    # Formato: "Enero 2024" o "Ene 2024"
    patron1 = r'([a-zA-ZáéíóúÁÉÍÓÚ]+)\s+(\d{4})'
    match1 = re.match(patron1, fecha_str, re.IGNORECASE)
    if match1:
        mes_str = match1.group(1).lower()
        año = int(match1.group(2))
        mes = meses_map.get(mes_str)
        if mes:
            try:
                return datetime(año, mes, 1)
            except ValueError:
                return None
    
    # Formato: "01/2024" o "1/2024"
    patron2 = r'(\d{1,2})[/-](\d{4})'
    match2 = re.match(patron2, fecha_str)
    if match2:
        mes = int(match2.group(1))
        año = int(match2.group(2))
        if 1 <= mes <= 12:
            try:
                return datetime(año, mes, 1)
            except ValueError:
                return None
    
    return None

def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/ipc_paraguay.xlsx.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (ipc_paraguay en update/download/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    return ruta_local

def extraer_ipc_paraguay():
    """
    Extrae datos de IPC de Paraguay desde el Excel del BCP.
    
    Returns:
        DataFrame con columnas: Fecha, IPC
    """
    print(f"\n[INFO] Extrayendo IPC de Paraguay desde Excel del BCP...")
    
    # Leer Excel desde data_raw
    ruta_excel = leer_excel_desde_data_raw()
    
    try:
        # Leer Excel desde archivo local
        excel_file = pd.ExcelFile(ruta_excel, engine='openpyxl')
        
        # Verificar que existe la hoja "CUADRO 4"
        if "CUADRO 4" not in excel_file.sheet_names:
            print(f"[ERROR] No se encontró la hoja 'CUADRO 4'")
            print(f"   Hojas disponibles: {excel_file.sheet_names}")
            return None
        
        print(f"[INFO] Leyendo hoja 'CUADRO 4'...")
        
        # Leer la hoja completa
        df = pd.read_excel(excel_file, sheet_name="CUADRO 4", header=None)
        
        print(f"[INFO] Dimensiones del Excel: {df.shape[0]} filas x {df.shape[1]} columnas")
        
        # Extraer datos desde la fila 12 (índice 11)
        # Columna A (índice 0): fecha
        # Columna R (índice 17): IPC
        datos = []
        inicio_fila = 11  # Fila 12 en Excel (índice 0-based = 11)
        
        print(f"[INFO] Extrayendo datos desde fila {inicio_fila + 1} (columna A=fecha, columna R=IPC)...")
        
        for idx in range(inicio_fila, len(df)):
            fecha_raw = df.iloc[idx, 0]  # Columna A
            ipc_raw = df.iloc[idx, 17]   # Columna R
            
            # Saltar filas vacías
            if pd.isna(fecha_raw) and pd.isna(ipc_raw):
                continue
            
            # Parsear fecha
            fecha = parsear_fecha_paraguay(fecha_raw)
            if fecha is None:
                if pd.notna(fecha_raw):
                    try:
                        fecha = pd.to_datetime(fecha_raw, errors='coerce')
                        if pd.isna(fecha):
                            continue
                    except:
                        continue
                else:
                    continue
            
            # Convertir IPC a numérico
            try:
                ipc_valor = pd.to_numeric(ipc_raw, errors='coerce')
                if pd.isna(ipc_valor):
                    continue
            except (ValueError, TypeError):
                continue
            
            datos.append({
                'Fecha': fecha,
                'IPC': ipc_valor
            })
        
        
        if not datos:
            print("[ERROR] No se encontraron datos válidos en el Excel")
            return None
        
        df_resultado = pd.DataFrame(datos)
        
        # Eliminar duplicados por fecha (mantener el último)
        df_resultado = df_resultado.drop_duplicates(subset='Fecha', keep='last')
        
        # Ordenar por fecha
        df_resultado = df_resultado.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] Se procesaron {len(df_resultado)} registros válidos")
        if len(df_resultado) > 0:
            print(f"   Rango: {df_resultado['Fecha'].min().strftime('%d/%m/%Y')} a {df_resultado['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df_resultado
        
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error al procesar Excel: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Función principal."""
    print("=" * 80)
    print("ACTUALIZACION DE DATOS: IPC - PARAGUAY")
    print("=" * 80)
    
    # Extraer datos
    df_ipc = extraer_ipc_paraguay()
    
    if df_ipc is None or len(df_ipc) == 0:
        print("\n[ERROR] No se pudieron extraer datos. Abortando.")
        return
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(df_ipc.head(10))
    print("\nÚltimos datos:")
    print(df_ipc.tail(10))
    
    # Filtrar fechas desde 2010-01-01
    fecha_min = datetime(2010, 1, 1)
    df_ipc = df_ipc[df_ipc['Fecha'] >= fecha_min].copy()
    
    # Renombrar columnas para el helper
    df_ipc = df_ipc.rename(columns={'Fecha': 'FECHA', 'IPC': 'VALOR'})
    
    # Validar fechas
    df_ipc = validar_fechas_solo_nulas(df_ipc)
    
    if len(df_ipc) == 0:
        print("\n[ERROR] No quedaron datos válidos después de la validación. Abortando.")
        return
    
    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return
    
    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, df_ipc, DB_NAME)
    
    print("\n" + "=" * 80)
    print("PROCESO COMPLETADO")
    print("=" * 80)

if __name__ == "__main__":
    main()
