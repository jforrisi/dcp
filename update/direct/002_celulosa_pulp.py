"""
Script: celulosa_pulp
----------------------
Actualiza la base de datos con la serie de precios de celulosa (INSEE - Francia),
siguiendo el flujo del README:

1) Intentar lectura directa de la tabla HTML con pandas desde la URL.
2) Si falla, leer el archivo local desde data_raw/celulosa_pulp_insee.xlsx o .csv.
3) Validar fechas.
4) Actualizar automáticamente la base de datos.
"""

import os
import zipfile
import io
import requests

import pandas as pd
from _helpers import (
    validar_fechas_unificado,
    insertar_en_bd_unificado
)


# Configuración de origen de datos
URL_INSEE_PAGE = "https://www.insee.fr/en/statistiques/serie/010600341#Telechargement"
URL_EXCEL_DIRECTA = "https://bdm.insee.fr/series/010600341/xlsx?lang=en&ordre=antechronologico&transposition=donnees_colonne&periodeDebut=1&anneeDebut=1990&periodeFin=11&anneeFin=2025&revision=sans_revisions"
DATA_RAW_DIR = "data_raw"
LOCAL_FILE_NAME = "celulosa_pulp_insee.xlsx"

# Configuración de base de datos
ID_VARIABLE = 4  # Celulosa -indice- (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 999  # Economía internacional_database.xlsx Sheet1_old)


def leer_excel_desde_url():
    """
    Descarga el archivo desde la URL de INSEE (puede ser ZIP o Excel directo).
    Si es ZIP, extrae el Excel y lo lee.
    El Excel tiene los datos empezando en la fila 5:
    - Columna A = fecha
    - Columna B = valor (con texto adicional que hay que limpiar)
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Descargando archivo desde la URL de INSEE...")
    print(f"[INFO] URL: {URL_EXCEL_DIRECTA}")
    
    try:
        # Descargar el archivo
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(URL_EXCEL_DIRECTA, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"[OK] Archivo descargado ({len(response.content)} bytes)")
        
        # Verificar si es ZIP o Excel directo
        content_type = response.headers.get('Content-Type', '').lower()
        is_zip = content_type == 'application/zip' or response.content[:2] == b'PK'
        
        excel_data = None
        
        if is_zip:
            print("[INFO] El archivo es un ZIP, extrayendo el Excel...")
            # Es un ZIP, extraer el Excel
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # Buscar el archivo Excel dentro del ZIP
                excel_files = [f for f in zip_file.namelist() if f.endswith('.xlsx') or f.endswith('.xls')]
                if not excel_files:
                    raise ValueError("No se encontró ningún archivo Excel en el ZIP")
                
                # Usar el primer Excel encontrado
                excel_name = excel_files[0]
                print(f"[INFO] Extrayendo: {excel_name}")
                excel_data = zip_file.read(excel_name)
        else:
            print("[INFO] El archivo es un Excel directo")
            excel_data = response.content
        
        # Leer el Excel desde memoria
        # skiprows=4 porque los datos empiezan en la fila 5 (índice 4)
        # usecols="A,B" para leer solo fecha (A) y valor (B)
        df = pd.read_excel(
            io.BytesIO(excel_data),
            skiprows=4,  # Los datos empiezan en la fila 5
            usecols="A,B",  # Columna A = fecha, Columna B = valor
            header=None,
            engine='openpyxl'
        )
        
        # Asignar nombres a las columnas
        df.columns = ["FECHA_RAW", "VALOR_RAW"]
        
        print(f"[OK] Excel leído: {len(df)} filas")
        
        # Limpiar el valor: eliminar texto adicional (como "mcusho (A)") y convertir a numérico
        # El valor puede venir como "123.45 (A)" o similar, necesitamos extraer solo el número
        print("[INFO] Limpiando valores (eliminando texto adicional)...")
        
        # Convertir a string, extraer números (incluyendo decimales) y convertir a numérico
        df["VALOR"] = df["VALOR_RAW"].astype(str).str.extract(r'([\d,\.]+)')[0]
        # Reemplazar comas por puntos para formato decimal
        df["VALOR"] = df["VALOR"].str.replace(',', '.', regex=False)
        # Convertir a numérico
        df["VALOR"] = pd.to_numeric(df["VALOR"], errors='coerce')
        
        # Eliminar filas con valores nulos
        df = df.dropna(subset=["VALOR"])
        
        # Parsear fechas
        print("[INFO] Parseando fechas...")
        df["FECHA"] = pd.to_datetime(df["FECHA_RAW"], errors='coerce')
        
        # Si el parseo falla, intentar otros formatos
        if df["FECHA"].isna().any():
            # Intentar formato más flexible
            df["FECHA"] = pd.to_datetime(df["FECHA_RAW"], errors='coerce', infer_datetime_format=True)
        
        # Eliminar filas donde no se pudo parsear la fecha
        df = df.dropna(subset=["FECHA"])
        
        # Asegurar que las fechas sean el primer día del mes (si son mensuales)
        df["FECHA"] = df["FECHA"].dt.to_period('M').dt.to_timestamp()
        
        # Seleccionar solo las columnas necesarias
        df_limpio = df[["FECHA", "VALOR"]].copy()
        
        print(f"[OK] Procesados {len(df_limpio)} registros válidos")
        print(f"     Rango de fechas: {df_limpio['FECHA'].min()} a {df_limpio['FECHA'].max()}")
        print(f"     Rango de valores: {df_limpio['VALOR'].min():.2f} a {df_limpio['VALOR'].max():.2f}")
        
        return df_limpio
        
    except Exception as e:
        print(f"[ERROR] Error al leer Excel desde URL: {e}")
        raise


def leer_archivo_desde_data_raw():
    """
    Lee el archivo local desde data_raw.
    Intenta primero con el nombre estándar, luego busca automáticamente.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    
    # Primero intentar con el nombre estándar
    ruta_local = os.path.join(data_raw_path, LOCAL_FILE_NAME)
    
    if not os.path.exists(ruta_local):
        # Buscar automáticamente el archivo más reciente que contenga "celulosa" o "insee" o "pulp"
        print(f"\n[INFO] No se encontró {LOCAL_FILE_NAME}, buscando archivo alternativo...")
        
        if not os.path.exists(data_raw_path):
            raise FileNotFoundError(
                f"No existe la carpeta {data_raw_path}. "
                "Ejecutá primero el script de descarga (precios/download/productos/celulosa_pulp.py)."
            )
        
        # Buscar archivos que contengan palabras clave
        candidatos = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx", ".csv"))
            and any(term in f.lower() for term in ["celulosa", "pulp", "insee", "010600341"])
            and not f.startswith("~$")  # Excluir archivos temporales
        ]
        
        if not candidatos:
            raise FileNotFoundError(
                f"No se encontró ningún archivo de celulosa en {data_raw_path}. "
                "Ejecutá primero el script de descarga (precios/download/productos/celulosa_pulp.py)."
            )
        
        # Elegir el más reciente
        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ruta_local = max(candidatos_paths, key=os.path.getmtime)
        print(f"[INFO] Usando archivo encontrado: {os.path.basename(ruta_local)}")

    print(f"\n[INFO] Leyendo archivo local desde: {ruta_local}")
    
    # Leer Excel (mismo formato que desde URL)
    print(f"[INFO] Leyendo Excel local (formato INSEE)...")
    df = pd.read_excel(
        ruta_local,
        skiprows=4,  # Los datos empiezan en la fila 5
        usecols="A,B",  # Columna A = fecha, Columna B = valor
        header=None,
        engine='openpyxl'
    )
    
    df.columns = ["FECHA_RAW", "VALOR_RAW"]
    
    # Limpiar valores (igual que desde URL)
    df["VALOR"] = df["VALOR_RAW"].astype(str).str.extract(r'([\d,\.]+)')[0]
    df["VALOR"] = df["VALOR"].str.replace(',', '.', regex=False)
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors='coerce')
    
    df = df.dropna(subset=["VALOR"])
    df["FECHA"] = pd.to_datetime(df["FECHA_RAW"], errors='coerce')
    
    if df["FECHA"].isna().any():
        df["FECHA"] = pd.to_datetime(df["FECHA_RAW"], errors='coerce', infer_datetime_format=True)
    
    df = df.dropna(subset=["FECHA"])
    df["FECHA"] = df["FECHA"].dt.to_period('M').dt.to_timestamp()
    
    df_limpio = df[["FECHA", "VALOR"]].copy()
    
    print(f"[OK] Leido desde archivo local: {len(df_limpio)} registros válidos")
    return df_limpio


def obtener_celulosa_pulp():
    """
    Implementa el flujo:
    1) Intentar lectura directa del Excel desde URL.
    2) Si falla, intentar lectura desde data_raw.
    """
    try:
        return leer_excel_desde_url()
    except Exception as e:
        print(f"[WARN] No se pudo leer el Excel desde la URL: {e}")
        print("       Se intentara leer el archivo local en data_raw...")
        try:
            return leer_archivo_desde_data_raw()
        except Exception as e2:
            print(f"[ERROR] Tampoco se pudo leer desde data_raw: {e2}")
            print("\n[INFO] Según el flujo del README, si pandas falla se debe:")
            print("   - Avisar al usuario")
            print("   - Solicitar confirmación para usar Selenium")
            print("   - Si confirma: crear scripts de download y update con Selenium")
            raise


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: CELULOSA PULP (INSEE - FRANCIA)")
    print("=" * 60)

    try:
        celulosa_pulp = obtener_celulosa_pulp()
        celulosa_pulp = validar_fechas_unificado(celulosa_pulp)

        # Mostrar primeros y últimos datos
        print("\n[INFO] Datos obtenidos:")
        print("\nPrimeros datos:")
        print(celulosa_pulp.head())
        print("\nÚltimos datos:")
        print(celulosa_pulp.tail())

        # Verificar que ID_VARIABLE e ID_PAIS están configurados
        if ID_VARIABLE is None or ID_PAIS is None:
            print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
            print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
            return

        print("\n[INFO] Actualizando base de datos...")
        insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, celulosa_pulp)
            
    except Exception as e:
        print(f"\n[ERROR] Error durante la ejecución: {e}")
        print("\n[INFO] Si pandas no funciona, según el README se debe:")
        print("   1. Avisar al usuario del error")
        print("   2. Solicitar confirmación para usar Selenium")
        print("   3. Si confirma: crear scripts de download y update con Selenium")
        raise


if __name__ == "__main__":
    main()
