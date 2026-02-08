# -*- coding: utf-8 -*-
"""
Script: nxr_argy_cargar_historico
----------------------------------
Carga y actualiza datos de tipo de cambio USD/ARS (Argentina).

Flujo completo:
1) Lee CSV histórico desde data_raw/
2) Extrae datos nuevos desde Rava
3) Combina ambos (histórico + Rava)
4) Elimina fechas duplicadas (mantiene las últimas de Rava)
5) Reescribe CSV en data_raw/ con datos actualizados
6) Inserta todo en la base de datos
"""

import json
import os
import re
import shutil
import sqlite3
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
DB_NAME = "series_tiempo.db"

# Configuración de archivos
DATA_RAW_DIR = "data_raw"
HISTORICOS_DIR = "update/historicos"
CSV_HISTORICO_NAME = "historical_nxr_argy.csv"

# URL por defecto para extraer datos de Rava
URL_RAVA_DEFAULT = "https://www.rava.com/perfil/DOLAR%20CCL"

# Configuración de IDs
ID_VARIABLE = 21  # Tipo de cambio USD/ARS (Argentina)
ID_PAIS = 32  # Argentina (id_pais=32 en tabla pais_grupo de la base de datos)


def leer_csv_historico():
    """
    Lee el CSV histórico desde data_raw/.
    El CSV debe tener formato: fecha,valor (sin encabezados)
    Formato de fecha: YYYY-MM-DD
    
    Returns:
        DataFrame con columnas 'Fecha' y 'Cierre'
    """
    base_dir = Path.cwd()
    ruta_csv = base_dir / DATA_RAW_DIR / CSV_HISTORICO_NAME
    
    if not ruta_csv.exists():
        raise FileNotFoundError(
            f"No se encontró el CSV histórico en: {ruta_csv}"
        )
    
    print(f"\n[INFO] Leyendo CSV histórico desde: {ruta_csv}")
    
    try:
        # Leer CSV sin encabezados (formato: fecha,valor)
        df_historico = pd.read_csv(
            ruta_csv,
            header=None,
            names=['Fecha', 'Cierre'],
            encoding='utf-8'
        )
        
        # Convertir fecha a datetime
        df_historico['Fecha'] = pd.to_datetime(df_historico['Fecha'], errors='coerce')
        df_historico = df_historico.dropna(subset=['Fecha'])
        
        # Convertir valor a numérico
        df_historico['Cierre'] = pd.to_numeric(df_historico['Cierre'], errors='coerce')
        df_historico = df_historico.dropna(subset=['Cierre'])
        
        # Ordenar por fecha
        df_historico = df_historico.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] CSV histórico leído: {len(df_historico)} registros")
        if len(df_historico) > 0:
            print(f"      Rango: {df_historico['Fecha'].min().strftime('%d/%m/%Y')} a {df_historico['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df_historico
        
    except Exception as e:
        print(f"[ERROR] Error al leer CSV histórico: {e}")
        import traceback
        traceback.print_exc()
        raise


def extraer_rava(url):
    """
    Extrae cotizaciones de Rava desde una URL.
    Retorna DataFrame con columnas: Fecha, Cierre
    """
    print(f"\n[INFO] Extrayendo datos desde Rava: {url}")
    
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
    
    print("[WARN] No se pudieron extraer los datos de Rava")
    return None


def extraer_desde_api(url):
    """Intenta encontrar y usar la API de Rava"""
    try:
        simbolo = url.split('/')[-1]
        simbolo = simbolo.replace('%20', ' ')
        
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
        print(f"[WARN] Error al extraer con requests: {e}")
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
        print(f"[WARN] Error al extraer con BeautifulSoup: {e}")
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
        print(f"[WARN] Error al extraer con Selenium: {e}")
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


def combinar_y_eliminar_duplicados(df_historico: pd.DataFrame, df_rava: pd.DataFrame) -> pd.DataFrame:
    """
    Combina histórico y Rava, eliminando fechas duplicadas (mantiene las de Rava).
    
    Returns:
        DataFrame combinado y sin duplicados, ordenado por fecha
    """
    print("\n[INFO] Combinando datos históricos y de Rava...")
    
    if df_rava is None or df_rava.empty:
        print("[WARN] No hay datos de Rava, usando solo histórico")
        return df_historico.copy()
    
    # Combinar ambos DataFrames
    df_combinado = pd.concat([df_historico, df_rava], ignore_index=True)
    
    # Eliminar duplicados manteniendo las últimas (de Rava)
    # Ordenar por fecha descendente primero para que las de Rava queden al final
    df_combinado = df_combinado.sort_values('Fecha', ascending=False)
    df_combinado = df_combinado.drop_duplicates(subset='Fecha', keep='first')
    
    # Ordenar por fecha ascendente para el resultado final
    df_combinado = df_combinado.sort_values('Fecha', ascending=True).reset_index(drop=True)
    
    registros_antes = len(df_historico) + len(df_rava)
    registros_despues = len(df_combinado)
    duplicados_eliminados = registros_antes - registros_despues
    
    print(f"[OK] Datos combinados: {registros_despues} registros únicos")
    if duplicados_eliminados > 0:
        print(f"      Se eliminaron {duplicados_eliminados} fechas duplicadas (se mantuvieron las de Rava)")
    if len(df_combinado) > 0:
        print(f"      Rango: {df_combinado['Fecha'].min().strftime('%d/%m/%Y')} a {df_combinado['Fecha'].max().strftime('%d/%m/%Y')}")
    
    return df_combinado


def reescribir_csv_historico(df_completo: pd.DataFrame):
    """
    Reescribe el CSV histórico en data_raw/ con todos los datos actualizados.
    Hace backup del CSV anterior en update/historicos/ con timestamp.
    """
    print("\n[INFO] Reescribiendo CSV histórico en data_raw/...")
    
    base_dir = Path.cwd()
    data_raw_path = base_dir / DATA_RAW_DIR
    historicos_path = base_dir / HISTORICOS_DIR
    
    data_raw_path.mkdir(exist_ok=True)
    historicos_path.mkdir(exist_ok=True)
    
    csv_actual = data_raw_path / CSV_HISTORICO_NAME
    
    # Si existe el CSV actual, hacer backup en historicos/ con timestamp
    if csv_actual.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_backup = historicos_path / f"{CSV_HISTORICO_NAME.replace('.csv', '')}_{timestamp}.csv"
        shutil.copy2(str(csv_actual), str(csv_backup))
        print(f"[INFO] Backup del CSV anterior guardado en: {csv_backup}")
    
    # Preparar DataFrame para CSV (formato: fecha,valor sin encabezados)
    df_csv = df_completo[['Fecha', 'Cierre']].copy()
    df_csv['Fecha'] = df_csv['Fecha'].dt.strftime('%Y-%m-%d')
    df_csv = df_csv.rename(columns={'Fecha': 'fecha', 'Cierre': 'valor'})
    
    # Guardar CSV sin índice y sin encabezados
    df_csv.to_csv(csv_actual, index=False, header=False, encoding='utf-8')
    
    print(f"[OK] CSV histórico reescrito en: {csv_actual}")
    print(f"      Total de registros: {len(df_csv)}")


def main():
    print("=" * 80)
    print("CARGA Y ACTUALIZACIÓN: TIPO DE CAMBIO USD/ARS (ARGENTINA)")
    print("=" * 80)
    
    # 1. Leer CSV histórico desde data_raw/
    try:
        df_historico = leer_csv_historico()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        print("       El CSV histórico debe estar en data_raw/historical_nxr_argy.csv")
        return
    
    # 2. Extraer datos nuevos desde Rava
    df_rava = extraer_rava(URL_RAVA_DEFAULT)
    
    # 3. Combinar y eliminar duplicados (mantiene las últimas de Rava)
    df_combinado = combinar_y_eliminar_duplicados(df_historico, df_rava)
    
    if df_combinado.empty:
        print("[ERROR] No hay datos para procesar")
        return
    
    # 4. Completar días faltantes
    print("\n[INFO] Completando días faltantes...")
    fecha_min = df_combinado['Fecha'].min()
    fecha_max = df_combinado['Fecha'].max()
    rango_completo = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
    df_completo = pd.DataFrame({'Fecha': rango_completo})
    df_completo = df_completo.merge(df_combinado[['Fecha', 'Cierre']], on='Fecha', how='left')
    df_completo['Cierre'] = df_completo['Cierre'].ffill()
    
    dias_originales = len(df_combinado)
    dias_completados = len(df_completo)
    if dias_completados > dias_originales:
        print(f"[INFO] Se completaron {dias_completados - dias_originales} días faltantes")
    
    # 5. Preparar para BD
    df_final = df_completo.rename(columns={'Fecha': 'FECHA', 'Cierre': 'VALOR'})
    df_final = validar_fechas_solo_nulas(df_final)
    
    # 6. Reescribir CSV en data_raw/
    reescribir_csv_historico(df_completo)
    
    # 7. Insertar en BD
    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, df_final, DB_NAME)
    
    print("\n" + "=" * 80)
    print("PROCESO COMPLETADO")
    print("=" * 80)
    print(f"Total de registros en BD: {len(df_final)}")
    print(f"Rango: {df_final['FECHA'].min().strftime('%d/%m/%Y')} a {df_final['FECHA'].max().strftime('%d/%m/%Y')}")


if __name__ == "__main__":
    main()
