# -*- coding: utf-8 -*-
"""
Script: ipc_paraguay
--------------------
Actualiza la base de datos con la serie de IPC (Índice de Precios al Consumidor) mensual
de Paraguay desde el Excel del Banco Central del Paraguay (BCP).

Fuente: https://www.bcp.gov.py/
Hoja: CUADRO 4
- Columna A (desde fila 12): Fecha (mes año)
- Columna R (desde fila 12): IPC

1) Descargar Excel desde URL directa.
2) Leer hoja "CUADRO 4", columnas A (fecha) y R (IPC) desde fila 12.
3) Parsear fechas (formato mes año).
4) Validar valores numéricos.
5) Insertar directamente en SQLite.
"""

import os
import sqlite3
import sys
import time
from datetime import datetime
import re

import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# URL de la página del BCP con el IPC
BCP_IPC_PAGE_URL = "https://www.bcp.gov.py/"  # URL de la página donde está el enlace de descarga
BCP_IPC_DOWNLOAD_URL = "https://www.bcp.gov.py/documents/20117/2206232/AE_IPC.xlsx/4575c632-b9a3-edf6-fe3c-25210cd851bc?t=1767111625563"

# Carpeta para descargas temporales
DATA_RAW_DIR = "data_raw"
TEMP_EXCEL_NAME = "ipc_paraguay_bcp_temp.xlsx"

# Configuración de la serie (copiando estructura del ID 34)
MAESTRO_IPC_PARAGUAY = {
    "id": 37,
    "nombre": "IPC",
    "tipo": None,
    "fuente": "BCP",
    "periodicidad": "M",
    "unidad": "Índice",
    "categoria": "Macro - IPC",
    "activo": 1,
    "moneda": None,
    "nominal_real": "n",
    "pais": "Paraguay"
}


def crear_base_datos():
    """Crea la base de datos SQLite y las tablas según el esquema del README."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Agregar columnas adicionales si no existen
    try:
        cursor.execute("ALTER TABLE maestro ADD COLUMN es_cotizacion INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE maestro ADD COLUMN nominal_real VARCHAR(1)")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE maestro ADD COLUMN moneda VARCHAR(10)")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE maestro ADD COLUMN pais VARCHAR(100)")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


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


def asegurar_data_raw():
    """Crea la carpeta data_raw si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    os.makedirs(data_raw_path, exist_ok=True)
    return data_raw_path


def configurar_driver_descargas(download_dir: str):
    """
    Configura Chrome para que descargue archivos automáticamente
    en el directorio indicado, sin preguntar.
    """
    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # Deja visible el navegador para debugging
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def limpiar_archivos_anteriores(data_raw_path: str):
    """
    Elimina archivos anteriores relacionados (Excel del BCP).
    """
    destino = os.path.join(data_raw_path, TEMP_EXCEL_NAME)
    
    # Eliminar el archivo destino si ya existe
    if os.path.exists(destino):
        os.remove(destino)
        print(f"[INFO] Archivo anterior '{TEMP_EXCEL_NAME}' eliminado")
    
    # Eliminar archivos Excel que puedan ser del BCP
    for archivo in os.listdir(data_raw_path):
        if archivo.lower().endswith(".xlsx") and ("bcp" in archivo.lower() or "paraguay" in archivo.lower() or "AE_IPC" in archivo):
            archivo_path = os.path.join(data_raw_path, archivo)
            try:
                os.remove(archivo_path)
                print(f"[INFO] Archivo anterior '{archivo}' eliminado")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{archivo}': {e}")


def descargar_excel_bcp_selenium():
    """
    Descarga el Excel del BCP usando Selenium.
    Busca el enlace de descarga y hace clic en él.
    
    Returns:
        Bytes del archivo Excel o None si hay error
    """
    print(f"[INFO] Descargando Excel desde BCP usando Selenium...")
    
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    # Limpiar archivos anteriores
    limpiar_archivos_anteriores(data_raw_path)

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        # Opción 1: Intentar descargar directamente desde la URL
        print(f"[INFO] Intentando descarga directa desde URL...")
        driver.get(BCP_IPC_DOWNLOAD_URL)
        
        # Esperar a que se descargue el archivo
        print("[INFO] Esperando a que termine la descarga...")
        tiempo_inicio = time.time()
        tiempo_max_espera = 30  # segundos máximo
        
        # Obtener lista de archivos antes de la descarga
        archivos_antes = set(os.listdir(data_raw_path))
        
        while True:
            time.sleep(1)
            archivos_ahora = set(os.listdir(data_raw_path))
            archivos_nuevos = archivos_ahora - archivos_antes
            
            # Buscar archivos Excel nuevos
            xlsx_nuevos = [
                f for f in archivos_nuevos 
                if f.lower().endswith(".xlsx")
            ]
            
            if xlsx_nuevos:
                print(f"[INFO] Archivo descargado detectado: {xlsx_nuevos[0]}")
                break
            
            if time.time() - tiempo_inicio > tiempo_max_espera:
                # Si no se descargó automáticamente, intentar buscar el enlace en la página
                print("[INFO] No se descargó automáticamente, buscando enlace de descarga...")
                try:
                    wait = WebDriverWait(driver, 10)
                    # Buscar el enlace con el atributo download
                    enlace = wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "a[download], a.card__footer-link")
                        )
                    )
                    print("[INFO] Enlace encontrado, haciendo clic...")
                    enlace.click()
                    
                    # Esperar de nuevo
                    tiempo_inicio = time.time()
                    while True:
                        time.sleep(1)
                        archivos_ahora = set(os.listdir(data_raw_path))
                        archivos_nuevos = archivos_ahora - archivos_antes
                        xlsx_nuevos = [
                            f for f in archivos_nuevos 
                            if f.lower().endswith(".xlsx")
                        ]
                        if xlsx_nuevos:
                            print(f"[INFO] Archivo descargado detectado: {xlsx_nuevos[0]}")
                            break
                        if time.time() - tiempo_inicio > tiempo_max_espera:
                            raise RuntimeError(f"Timeout: No se detectó ningún archivo Excel descargado")
                except Exception as e:
                    print(f"[ERROR] Error al buscar enlace: {e}")
                    raise RuntimeError(f"Timeout: No se detectó ningún archivo Excel descargado en {tiempo_max_espera} segundos")

        # Buscar el archivo más reciente que sea Excel
        candidatos = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith(".xlsx")
        ]
        
        if not candidatos:
            raise RuntimeError("No se encontró ningún Excel descargado en data_raw.")

        # Elegir el más reciente por fecha de modificación
        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ultimo = max(candidatos_paths, key=os.path.getmtime)
        nombre_ultimo = os.path.basename(ultimo)

        # Leer el archivo
        print(f"[INFO] Leyendo archivo: {nombre_ultimo}")
        with open(ultimo, 'rb') as f:
            contenido = f.read()
        
        print(f"[OK] Excel descargado exitosamente ({len(contenido)} bytes)")
        return contenido

    finally:
        driver.quit()


def extraer_ipc_paraguay():
    """
    Extrae datos de IPC de Paraguay desde el Excel del BCP.
    
    Returns:
        DataFrame con columnas: Fecha, IPC
    """
    print(f"\n[INFO] Extrayendo IPC de Paraguay desde Excel del BCP...")
    
    # Descargar Excel usando Selenium
    excel_content = descargar_excel_bcp_selenium()
    if excel_content is None:
        return None
    
    try:
        # Leer Excel en memoria (usar BytesIO para evitar warning)
        from io import BytesIO
        excel_file = pd.ExcelFile(BytesIO(excel_content), engine='openpyxl')
        
        # Verificar que existe la hoja "CUADRO 4"
        if "CUADRO 4" not in excel_file.sheet_names:
            print(f"[ERROR] No se encontró la hoja 'CUADRO 4'")
            print(f"   Hojas disponibles: {excel_file.sheet_names}")
            return None
        
        print(f"[INFO] Leyendo hoja 'CUADRO 4'...")
        
        # Leer la hoja completa
        df = pd.read_excel(excel_file, sheet_name="CUADRO 4", header=None)
        
        print(f"[INFO] Dimensiones del Excel: {df.shape[0]} filas x {df.shape[1]} columnas")
        
        # Extraer datos desde la fila 12 (índice 11, ya que empieza en 0)
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
                # Si no se puede parsear, intentar con el valor tal cual
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
        
    except Exception as e:
        print(f"[ERROR] Error al procesar Excel: {e}")
        import traceback
        traceback.print_exc()
        return None


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valida que las fechas sean válidas y estén en el formato correcto.
    
    Args:
        df: DataFrame con columna 'Fecha'
        
    Returns:
        DataFrame con fechas validadas
    """
    print("\n[INFO] Validando fechas...")
    
    # Asegurar que Fecha sea datetime
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    
    # Eliminar filas con fechas inválidas
    antes = len(df)
    df = df.dropna(subset=['Fecha'])
    despues = len(df)
    
    if antes != despues:
        print(f"[INFO] Se eliminaron {antes - despues} registros con fechas inválidas")
    
    # Filtrar fechas desde 2010-01-01
    fecha_min = datetime(2010, 1, 1)
    df = df[df['Fecha'] >= fecha_min]
    
    print(f"[OK] {len(df)} registros con fechas válidas desde 2010-01-01")
    
    return df


def preparar_datos_maestro_precios(df_ipc: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """
    Prepara los datos para insertar en maestro_precios.
    
    Args:
        df_ipc: DataFrame con columnas Fecha e IPC
        maestro_id: ID del registro en maestro
        
    Returns:
        DataFrame con columnas maestro_id, fecha, valor
    """
    df_precios = pd.DataFrame({
        'maestro_id': maestro_id,
        'fecha': df_ipc['Fecha'],
        'valor': df_ipc['IPC']
    })
    
    # Asegurar que fecha sea string en formato YYYY-MM-DD
    df_precios['fecha'] = pd.to_datetime(df_precios['fecha']).dt.strftime('%Y-%m-%d')
    
    df_precios = df_precios.dropna(subset=["valor"])
    return df_precios


def mostrar_resumen(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Muestra un resumen de los datos a insertar."""
    print("\n" + "=" * 60)
    print("RESUMEN DE DATOS")
    print("=" * 60)
    print(f"\nMaestro (ID {df_maestro.iloc[0]['id']}):")
    print(f"  Nombre: {df_maestro.iloc[0]['nombre']}")
    print(f"  Fuente: {df_maestro.iloc[0]['fuente']}")
    print(f"  Periodicidad: {df_maestro.iloc[0]['periodicidad']}")
    
    print(f"\nPrecios:")
    print(f"  Total de registros: {len(df_precios)}")
    if len(df_precios) > 0:
        print(f"  Fecha inicial: {df_precios['fecha'].min()}")
        print(f"  Fecha final: {df_precios['fecha'].max()}")
        print(f"  Valor mínimo: {df_precios['valor'].min():.2f}")
        print(f"  Valor máximo: {df_precios['valor'].max():.2f}")
        print(f"  Valor promedio: {df_precios['valor'].mean():.2f}")
    print("=" * 60)


def insertar_en_bd(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> bool:
    """
    Inserta los datos en la base de datos SQLite.
    Retorna True si fue exitoso, False en caso contrario.
    """
    print("\n[INFO] Insertando datos en la base de datos...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        
        # Insertar en maestro (con campos adicionales, copiando estructura del ID 34)
        cursor.execute(
            """
            INSERT OR REPLACE INTO maestro 
            (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo, es_cotizacion, nominal_real, pais)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                maestro_id,
                maestro_row["nombre"],
                maestro_row.get("tipo"),  # None como ID 34
                maestro_row["fuente"],
                maestro_row["periodicidad"],
                maestro_row["unidad"],
                maestro_row["categoria"],
                maestro_row["activo"],
                0,  # es_cotizacion = 0 (no es cotización)
                maestro_row.get("nominal_real", "n"),  # "n" como ID 34
                maestro_row.get("pais", "Paraguay")  # "Paraguay"
            )
        )
        
        print(f"[OK] Insertado/actualizado registro en tabla 'maestro' (id={maestro_id})")

        # Eliminar registros existentes para este maestro_id
        cursor.execute(
            """
            DELETE FROM maestro_precios WHERE maestro_id = ?
            """,
            (maestro_id,)
        )
        registros_eliminados = cursor.rowcount
        if registros_eliminados > 0:
            print(f"[INFO] Se eliminaron {registros_eliminados} registros antiguos de 'maestro_precios'")

        # Insertar todos los precios nuevos
        if len(df_precios) > 0:
            print(f"[INFO] Insertando {len(df_precios)} registros en 'maestro_precios'...")
            df_precios.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios)} registro(s) en tabla 'maestro_precios'")
        else:
            print(f"[WARN] No hay datos para insertar")
            return False

        conn.commit()
        print(f"\n[OK] Datos insertados exitosamente en '{DB_NAME}'")
        return True
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] Error al insertar datos: {exc}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def main():
    """Función principal."""
    print("=" * 80)
    print("ACTUALIZACION DE DATOS: IPC - PARAGUAY")
    print("=" * 80)

    crear_base_datos()

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
    
    # Validar fechas
    df_ipc = validar_fechas(df_ipc)
    
    if len(df_ipc) == 0:
        print("\n[ERROR] No quedaron datos válidos después de la validación. Abortando.")
        return
    
    # Preparar datos
    df_maestro = pd.DataFrame([MAESTRO_IPC_PARAGUAY])
    df_precios = preparar_datos_maestro_precios(df_ipc, MAESTRO_IPC_PARAGUAY["id"])
    
    # Mostrar resumen
    mostrar_resumen(df_maestro, df_precios)
    
    # Insertar en BD
    insertar_en_bd(df_maestro, df_precios)
    
    print("\n" + "=" * 80)
    print("PROCESO COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    main()
