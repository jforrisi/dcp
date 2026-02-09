en # -*- coding: utf-8 -*-
"""
Script: nxr_argy
----------------
Actualiza la base de datos con la serie de tipo de cambio USD/ARS (Argentina) desde Rava.
Este script se ejecuta periódicamente para actualizar con datos nuevos.

1) Extraer datos nuevos desde Rava (scraping).
2) Validar fechas.
3) Actualizar automáticamente la base de datos.

NOTA: Para la carga inicial del CSV histórico, usar nxr_argy_cargar_historico.py
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de base de datos

# URL por defecto para extraer datos
URL_RAVA_DEFAULT = "https://www.rava.com/perfil/DOLAR%20CCL"

# Configuración de IDs (desde maestro_database.xlsx Sheet1_old)
ID_VARIABLE = 21  # Configurar cuando esté en maestro_database.xlsx
ID_PAIS = 32  # Argentina

# Configuración de archivos históricos
DATA_RAW_DIR = "data_raw"
HISTORICOS_DIR = "update/historicos"
CSV_HISTORICO_NAME = "historical_nxr_argy.csv"


def extraer_rava(url):
    """
    Extrae cotizaciones de Rava desde una URL.
    Retorna DataFrame con columnas: Fecha, Cierre
    
    Intenta diferentes métodos: API, requests, y finalmente Selenium si requiere JavaScript.
    """
    print(f"Extrayendo datos de: {url}")
    
    # Intentar encontrar la API de Rava
    df = extraer_desde_api(url)
    if df is not None and not df.empty:
        return df
    
    # Intentar con requests (puede no funcionar si requiere JS)
    df = extraer_desde_html_requests(url)
    if df is not None and not df.empty:
        return df
    
    # Si no funciona, intentar con Selenium (requiere JavaScript)
    print("Intentando con Selenium (puede tardar unos segundos)...")
    df = extraer_desde_selenium(url)
    if df is not None and not df.empty:
        return df
    
    print("No se pudieron extraer los datos. La página requiere JavaScript.")
    print("Puedes usar el HTML renderizado que copiaste del navegador.")
    return None

def extraer_desde_api(url):
    """Intenta encontrar y usar la API de Rava"""
    try:
        # Extraer el símbolo de la URL
        simbolo = url.split('/')[-1]
        simbolo = simbolo.replace('%20', ' ')
        
        # Intentar diferentes endpoints de API comunes
        posibles_apis = [
            f"https://www.rava.com/api/cotizaciones/{simbolo}",
            f"https://www.rava.com/api/historico/{simbolo}",
            f"https://api.rava.com/cotizaciones/{simbolo}",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        for api_url in posibles_apis:
            try:
                response = requests.get(api_url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return procesar_json_rava(data)
            except:
                continue
    except:
        pass
    
    return None

def procesar_json_rava(data):
    """Procesa datos JSON de la API de Rava"""
    try:
        if isinstance(data, list):
            datos = []
            for item in data:
                if 'fecha' in item and 'cierre' in item:
                    try:
                        fecha = pd.to_datetime(item['fecha'])
                        cierre = float(item['cierre'])
                        datos.append({'Fecha': fecha, 'Cierre': cierre})
                    except:
                        continue
            return crear_dataframe_desde_lista(datos)
        elif isinstance(data, dict):
            # Intentar diferentes estructuras posibles
            if 'data' in data:
                return procesar_json_rava(data['data'])
            elif 'cotizaciones' in data:
                return procesar_json_rava(data['cotizaciones'])
    except:
        pass
    
    return None

def extraer_desde_html_requests(url):
    """Extrae datos desde HTML usando requests (sin JavaScript)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        html = response.text
        
        # Intentar extraer con regex
        patron = r'(\d{2}/\d{2}/\d{4})[^<]*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>'
        matches = re.findall(patron, html, re.DOTALL)
        
        if matches:
            return crear_dataframe(matches)
        
        # Intentar con BeautifulSoup
        return extraer_con_beautifulsoup(html)
    except Exception as e:
        print(f"Error al extraer con requests: {e}")
        return None

def extraer_con_beautifulsoup(html):
    """Extrae datos usando BeautifulSoup"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        tabla = soup.find('table')
        
        if not tabla:
            return None
        
        datos = []
        filas = tabla.find_all('tr')
        
        for fila in filas:
            celdas = fila.find_all('td')
            if len(celdas) >= 5:
                fecha_str = celdas[0].get_text(strip=True)
                cierre_str = celdas[4].get_text(strip=True)
                
                if cierre_str == '-':
                    continue
                
                try:
                    fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
                    cierre_limpio = cierre_str.replace('.', '').replace(',', '.')
                    cierre = float(cierre_limpio)
                    
                    datos.append({
                        'Fecha': fecha,
                        'Cierre': cierre
                    })
                except (ValueError, IndexError):
                    continue
    
        if not datos:
            return None
        
        return crear_dataframe_desde_lista(datos)
    except Exception as e:
        print(f"Error al extraer con BeautifulSoup: {e}")
        return None

def extraer_desde_selenium(url):
    """Extrae datos usando Selenium (requiere JavaScript)"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            html = driver.page_source
            return extraer_con_beautifulsoup(html)
        finally:
            driver.quit()
    except Exception as e:
        print(f"Error al extraer con Selenium: {e}")
        return None

def crear_dataframe(matches):
    """Crea DataFrame desde matches de regex"""
    datos = []
    for match in matches:
        fecha_str = match[0]
        cierre_str = match[4]
        
        if cierre_str == '-':
            continue
        
        try:
            fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
            cierre_limpio = cierre_str.replace('.', '').replace(',', '.')
            cierre = float(cierre_limpio)
            
            datos.append({
                'Fecha': fecha,
                'Cierre': cierre
            })
        except (ValueError, IndexError):
            continue
    
    return crear_dataframe_desde_lista(datos)

def crear_dataframe_desde_lista(datos):
    """Crea DataFrame desde lista de diccionarios"""
    if not datos:
        return None
    
    df = pd.DataFrame(datos)
    df = df.drop_duplicates(subset='Fecha', keep='first')
    df = df.sort_values('Fecha', ascending=False).reset_index(drop=True)
    
    return df

def leer_desde_bd(id_variable: int, id_pais: int) -> pd.DataFrame:
    """
    Lee todos los datos desde la base de datos para una variable/pais específica.
    
    Returns:
        DataFrame con columnas: Fecha, Cierre
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from db.connection import execute_query

    print("\n[INFO] Leyendo todos los datos desde la base de datos...")

    rows = execute_query(
        "SELECT fecha, valor FROM maestro_precios WHERE id_variable = ? AND id_pais = ? ORDER BY fecha ASC",
        (id_variable, id_pais),
    )

    if not rows:
        print("[WARN] No se encontraron datos en la base de datos")
        return pd.DataFrame(columns=['Fecha', 'Cierre'])

    df = pd.DataFrame(rows)
    df = df.rename(columns={'fecha': 'Fecha', 'valor': 'Cierre'})
    df['Fecha'] = pd.to_datetime(df['Fecha'])

    print(f"[OK] Se leyeron {len(df)} registros desde la BD")
    print(f"   Rango: {df['Fecha'].min().strftime('%d/%m/%Y')} a {df['Fecha'].max().strftime('%d/%m/%Y')}")

    return df

def reescribir_csv_historico(df_completo: pd.DataFrame):
    """
    Reescribe el CSV histórico con todos los datos desde la BD.
    Mueve el CSV anterior a update/historicos/ con timestamp.
    """
    print("\n[INFO] Reescribiendo CSV histórico...")
    
    # Asegurar que existen las carpetas
    base_dir = Path.cwd()
    data_raw_path = base_dir / DATA_RAW_DIR
    historicos_path = base_dir / HISTORICOS_DIR
    
    data_raw_path.mkdir(exist_ok=True)
    historicos_path.mkdir(exist_ok=True)
    
    csv_actual = data_raw_path / CSV_HISTORICO_NAME
    
    # Si existe el CSV actual, moverlo a historicos/ con timestamp
    if csv_actual.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_backup = historicos_path / f"{CSV_HISTORICO_NAME.replace('.csv', '')}_{timestamp}.csv"
        shutil.move(str(csv_actual), str(csv_backup))
        print(f"[INFO] CSV anterior movido a: {csv_backup}")
    
    # Preparar DataFrame para CSV (formato: fecha,valor sin encabezados)
    df_csv = df_completo[['Fecha', 'Cierre']].copy()
    df_csv['Fecha'] = df_csv['Fecha'].dt.strftime('%Y-%m-%d')
    df_csv = df_csv.rename(columns={'Fecha': 'fecha', 'Cierre': 'valor'})
    
    # Guardar CSV sin índice y sin encabezados
    df_csv.to_csv(csv_actual, index=False, header=False, encoding='utf-8')
    
    print(f"[OK] CSV histórico reescrito: {csv_actual}")
    print(f"   Total de registros: {len(df_csv)}")

def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/ARS (ARGENTINA) - RAVA")
    print("=" * 60)
    
    # Extraer datos nuevos desde Rava
    print("\n[INFO] Extrayendo datos nuevos desde Rava...")
    df = extraer_rava(URL_RAVA_DEFAULT)
    
    if df is None or df.empty:
        print("[ERROR] No se pudieron extraer los datos de Rava")
        return
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos de Rava:")
    print("\nPrimeros datos:")
    print(df.head())
    print("\nÚltimos datos:")
    print(df.tail())
    
    # NO completar días faltantes aquí - solo los datos que vienen de Rava
    # (los días faltantes ya están completados en la carga inicial del CSV)
    
    # Renombrar columnas para el helper
    df = df.rename(columns={'Fecha': 'FECHA', 'Cierre': 'VALOR'})
    
    # Validar fechas
    df = validar_fechas_solo_nulas(df)
    
    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return
    
    print("\n[INFO] Actualizando base de datos...")
    # El helper ya elimina registros existentes antes de insertar, así que prioriza datos nuevos
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, df)
    
    # Después de actualizar, leer TODO desde la BD y reescribir el CSV histórico
    print("\n" + "=" * 60)
    print("ACTUALIZANDO CSV HISTÓRICO")
    print("=" * 60)
    
    df_completo = leer_desde_bd(ID_VARIABLE, ID_PAIS)
    
    if not df_completo.empty:
        reescribir_csv_historico(df_completo)
    else:
        print("[WARN] No se pudo actualizar el CSV histórico porque no hay datos en la BD")
    
    print("\n" + "=" * 60)
    print("PROCESO COMPLETADO")
    print("=" * 60)

if __name__ == "__main__":
    main()
