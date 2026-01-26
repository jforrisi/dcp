# -*- coding: utf-8 -*-
"""
Script: nxr_argy
----------------
Actualiza la base de datos con la serie de tipo de cambio USD/ARS (Argentina) desde Rava.
Este script se ejecuta periódicamente para actualizar con datos nuevos.

1) Extraer datos nuevos desde Rava (scraping).
2) Validar fechas.
3) Generar Excel de prueba.
4) Solicitar confirmación del usuario.
5) Insertar en SQLite eliminando duplicados (prioriza datos nuevos de Rava).

NOTA: Para la carga inicial del CSV histórico, usar nxr_argy_cargar_historico.py
"""

import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
import re
import requests
import json

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_tipo_cambio_argentina.xlsx"
DATA_RAW_DIR = "data_raw"

# URL por defecto para extraer datos
URL_RAVA_DEFAULT = "https://www.rava.com/perfil/DOLAR%20CCL"

# Datos del maestro
MAESTRO_TIPO_CAMBIO_ARGENTINA = {
    "id": 22,
    "nombre": "Tipo de cambio USD/ARS (Argentina - Dólar CCL)",
    "tipo": "M",  # variable macro
    "fuente": "Rava_Scraping",
    "periodicidad": "D",  # diario
    "unidad": "ARS por USD",
    "categoria": "Macro - Tipo de cambio",
    "activo": True,
}


def crear_base_datos():
    """Crea la base de datos SQLite y las tablas según el esquema del README."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS maestro (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            tipo CHAR(1) NOT NULL CHECK (tipo IN ('P', 'S', 'M')),
            fuente VARCHAR(255) NOT NULL,
            periodicidad CHAR(1) NOT NULL CHECK (periodicidad IN ('D', 'W', 'M')),
            unidad VARCHAR(100),
            categoria VARCHAR(255),
            activo BOOLEAN NOT NULL DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS maestro_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maestro_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            valor NUMERIC(18, 6) NOT NULL,
            FOREIGN KEY (maestro_id) REFERENCES maestro(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_maestro_id
        ON maestro_precios (maestro_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_fecha
        ON maestro_precios (fecha)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_maestro_fecha
        ON maestro_precios (maestro_id, fecha)
        """
    )

    conn.commit()
    conn.close()
    print(f"[OK] Base de datos '{DB_NAME}' creada/verificada con exito")


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
                    # Procesar datos JSON según estructura de Rava
                    return procesar_json_rava(data)
            except:
                continue
    except:
        pass
    
    return None


def procesar_json_rava(data):
    """Procesa datos JSON de la API de Rava"""
    # Esta función depende de la estructura real de la API
    # Por ahora retorna None
    return None


def extraer_desde_html_requests(url):
    """Extrae datos desde HTML usando requests"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
        
        # Buscar datos en el HTML
        patron = r'<td[^>]*>(\d{2}/\d{2}/\d{4})</td>\s*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>'
        matches = re.findall(patron, html, re.DOTALL)
        
        if matches:
            return crear_dataframe(matches)
        
        # Intentar con BeautifulSoup
        return extraer_con_beautifulsoup(html)
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def extraer_desde_selenium(url):
    """
    Extrae datos usando Selenium para renderizar JavaScript.
    Requiere tener Selenium y ChromeDriver instalados.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
    except ImportError:
        print("Selenium no está instalado. Instala con: pip install selenium")
        return None
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Esperar a que la tabla se cargue
        print("Esperando a que la página cargue...")
        time.sleep(5)
        
        # Intentar esperar a que aparezca la tabla
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
        except:
            pass
        
        html_content = driver.page_source
        driver.quit()
        
        # Extraer datos del HTML renderizado
        return extraer_con_beautifulsoup(html_content)
        
    except Exception as e:
        if driver:
            driver.quit()
        print(f"Error con Selenium: {e}")
        print("Asegúrate de tener ChromeDriver instalado y en el PATH")
        return None


def extraer_con_beautifulsoup(html):
    """Método alternativo usando BeautifulSoup"""
    soup = BeautifulSoup(html, 'html.parser')
    datos = []
    
    tablas = soup.find_all('table')
    for tabla in tablas:
        filas = tabla.find_all('tr')
        for fila in filas:
            celdas = fila.find_all('td')
            if len(celdas) >= 5:
                fecha_str = celdas[0].get_text(strip=True)
                cierre_str = celdas[4].get_text(strip=True)
                
                if not re.match(r'\d{2}/\d{2}/\d{4}', fecha_str):
                    continue
                
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


def extraer_desde_html_texto(html_texto):
    """
    Extrae datos desde HTML renderizado que copiaste del navegador.
    Útil cuando la página requiere JavaScript.
    
    Uso:
        # Copia el HTML de la tabla desde el navegador
        html = "<table>...</table>"
        df = extraer_desde_html_texto(html)
    """
    patron = r'<td[^>]*>(\d{2}/\d{2}/\d{4})</td>\s*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>\s*<td[^>]*>([\d.,\-]+)</td>'
    matches = re.findall(patron, html_texto, re.DOTALL)
    
    if not matches:
        return extraer_con_beautifulsoup(html_texto)
    
    return crear_dataframe(matches)


def completar_dias_faltantes(df: pd.DataFrame, columna_fecha: str = 'Fecha', columna_valor: str = 'Cierre') -> pd.DataFrame:
    """
    Completa días faltantes en una serie diaria usando forward fill.
    
    Para series diarias, garantiza que existan datos para todos los días del rango
    (lunes a domingo). Si un día no tiene datos (feriados, fines de semana), 
    usa el valor del día anterior.
    
    Args:
        df: DataFrame con columnas de fecha y valor
        columna_fecha: Nombre de la columna con fechas
        columna_valor: Nombre de la columna con valores
        
    Returns:
        DataFrame con todos los días completados (forward fill)
    """
    print("\n[INFO] Completando días faltantes en serie diaria...")
    
    # Asegurar que la columna de fecha sea datetime
    df = df.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha])
    
    # Ordenar por fecha
    df = df.sort_values(columna_fecha).reset_index(drop=True)
    
    # Obtener rango completo de fechas
    fecha_min = df[columna_fecha].min()
    fecha_max = df[columna_fecha].max()
    
    # Crear rango completo de días
    rango_completo = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
    df_completo = pd.DataFrame({columna_fecha: rango_completo})
    
    # Hacer merge con los datos originales
    df_completo = df_completo.merge(
        df[[columna_fecha, columna_valor]], 
        on=columna_fecha, 
        how='left'
    )
    
    # Aplicar forward fill (usar valor del día anterior)
    # Usar ffill() que es compatible con versiones recientes de pandas
    df_completo[columna_valor] = df_completo[columna_valor].ffill()
    
    # Contar cuántos días se completaron
    dias_originales = len(df)
    dias_completados = len(df_completo)
    dias_agregados = dias_completados - dias_originales
    
    if dias_agregados > 0:
        print(f"[INFO] Se completaron {dias_agregados} días faltantes (de {dias_originales} a {dias_completados} días)")
        print(f"   Rango: {fecha_min.strftime('%d/%m/%Y')} a {fecha_max.strftime('%d/%m/%Y')}")
    else:
        print(f"[OK] No había días faltantes ({dias_originales} días en el rango)")
    
    return df_completo


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
    print("\n[INFO] Validando fechas...")

    fechas_invalidas = []
    fechas_validas = []

    for idx, fecha in enumerate(df["Fecha"]):
        try:
            if pd.isna(fecha):
                fechas_invalidas.append((idx, fecha, "Fecha nula"))
            else:
                fecha_parseada = pd.to_datetime(fecha, errors="coerce")
                if pd.isna(fecha_parseada):
                    fechas_invalidas.append((idx, fecha, "No se pudo parsear"))
                else:
                    fechas_validas.append(fecha_parseada)
        except Exception as exc:
            fechas_invalidas.append((idx, fecha, str(exc)))

    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas invalidas:")
        for idx, fecha, motivo in fechas_invalidas[:10]:
            print(f"   Fila {idx}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} mas")
        raise ValueError("Hay fechas invalidas. No se puede continuar.")

    df["Fecha"] = pd.to_datetime(df["Fecha"])
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['Fecha'].min()} a {df['Fecha'].max()}")
    return df


def preparar_datos_maestro_precios(df_tc: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_tc.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "Fecha", "Cierre"]]
    df_precios.columns = ["maestro_id", "fecha", "valor"]
    
    # Asegurar que valor sea numérico
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    
    # Eliminar filas con valor nulo
    df_precios = df_precios.dropna(subset=["valor"])
    return df_precios


def generar_excel_prueba(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> str:
    """Genera el archivo Excel de prueba (OBLIGATORIO según README)."""
    print("\n[INFO] Generando archivo Excel de prueba...")

    excel_path = os.path.join(os.getcwd(), EXCEL_PRUEBA_NAME)
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_maestro.to_excel(writer, sheet_name="maestro", index=False)
        df_precios.to_excel(writer, sheet_name="maestro_precios", index=False)

    print(f"[OK] Archivo Excel generado: {excel_path}")
    print(f"   - Hoja 'maestro': {len(df_maestro)} fila(s)")
    print(f"   - Hoja 'maestro_precios': {len(df_precios)} fila(s)")
    return excel_path


def mostrar_resumen(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Muestra resumen de los datos que se van a insertar."""
    print("\n" + "=" * 60)
    print("RESUMEN DE DATOS A INSERTAR")
    print("=" * 60)

    print("\nTABLA: maestro")
    print("-" * 60)
    print(df_maestro.to_string(index=False))

    print("\nTABLA: maestro_precios")
    print("-" * 60)
    print(f"Total de registros: {len(df_precios)}")
    print("\nPrimeros 5 registros:")
    print(df_precios.head().to_string(index=False))
    print("\nÚltimos 5 registros:")
    print(df_precios.tail().to_string(index=False))
    print(f"\nRango de fechas: {df_precios['fecha'].min()} a {df_precios['fecha'].max()}")
    print(
        f"Valores: min={df_precios['valor'].min():.2f}, "
        f"max={df_precios['valor'].max():.2f}, "
        f"promedio={df_precios['valor'].mean():.2f}"
    )
    print("=" * 60)


def solicitar_confirmacion_usuario(excel_path: str) -> None:
    """
    Solicita confirmación explícita del usuario antes de insertar,
    cumpliendo el flujo del README.
    """
    print("\n" + "=" * 60)
    print("CONFIRMACION DEL USUARIO")
    print("=" * 60)
    print(f"Archivo Excel generado para validación: {excel_path}")
    print("Revisá el Excel (hojas 'maestro' y 'maestro_precios').")
    respuesta = input("¿Confirmás la inserción en la base de datos? (sí/no): ").strip().lower()
    if respuesta not in ["sí", "si", "yes", "y", "s"]:
        print("[INFO] Inserción cancelada por el usuario. No se realizaron cambios.")
        sys.exit(0)


def insertar_en_bd(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """
    Inserta los datos en la base de datos SQLite.
    Si hay fechas duplicadas, elimina las antiguas y prioriza los datos nuevos de Rava.
    """
    print("\n[INFO] Insertando datos en la base de datos...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Insertar en maestro usando INSERT OR IGNORE para evitar duplicados
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        
        cursor.execute(
            """
            INSERT OR IGNORE INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                maestro_id,
                maestro_row["nombre"],
                maestro_row["tipo"],
                maestro_row["fuente"],
                maestro_row["periodicidad"],
                maestro_row["unidad"],
                maestro_row["categoria"],
                maestro_row["activo"],
            )
        )
        
        if cursor.rowcount > 0:
            print(f"[OK] Insertado 1 registro en tabla 'maestro' (id={maestro_id})")
        else:
            print(f"[INFO] El registro con id={maestro_id} ya existe en 'maestro', se omite la inserción")

        # Verificar qué fechas ya existen
        cursor.execute(
            """
            SELECT fecha FROM maestro_precios 
            WHERE maestro_id = ?
            """,
            (maestro_id,)
        )
        fechas_existentes = {row[0] for row in cursor.fetchall()}
        
        # Identificar fechas nuevas y fechas a actualizar
        fechas_nuevas = set(pd.to_datetime(df_precios["fecha"]).dt.date)
        fechas_a_actualizar = fechas_nuevas.intersection(fechas_existentes)
        fechas_a_agregar = fechas_nuevas - fechas_existentes
        
        # Eliminar fechas duplicadas (priorizar datos nuevos de Rava)
        if fechas_a_actualizar:
            print(f"[INFO] Eliminando {len(fechas_a_actualizar)} registros antiguos para actualizar con datos nuevos de Rava...")
            for fecha in fechas_a_actualizar:
                cursor.execute(
                    """
                    DELETE FROM maestro_precios 
                    WHERE maestro_id = ? AND fecha = ?
                    """,
                    (maestro_id, fecha)
                )
            print(f"[OK] Eliminados {len(fechas_a_actualizar)} registros antiguos")
        
        # Insertar todos los datos nuevos (tanto nuevos como actualizados)
        if len(df_precios) > 0:
            print(f"[INFO] Insertando {len(df_precios)} registros (nuevos: {len(fechas_a_agregar)}, actualizados: {len(fechas_a_actualizar)})...")
            df_precios.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios)} registro(s) en tabla 'maestro_precios'")
        else:
            print(f"[INFO] No hay datos nuevos para insertar")

        conn.commit()
        print(f"\n[OK] Datos insertados exitosamente en '{DB_NAME}'")
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] Error al insertar datos: {exc}")
        raise
    finally:
        conn.close()


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/ARS (ARGENTINA) - RAVA")
    print("=" * 60)

    crear_base_datos()

    # Extraer datos nuevos desde Rava
    print("\n[INFO] Extrayendo datos nuevos desde Rava...")
    df = extraer_rava(URL_RAVA_DEFAULT)
    
    if df is None or df.empty:
        print("No se pudieron extraer los datos de Rava")
        return
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos de Rava:")
    print("\nPrimeros datos:")
    print(df.head())
    print("\nÚltimos datos:")
    print(df.tail())
    
    # NO completar días faltantes aquí - solo los datos que vienen de Rava
    # (los días faltantes ya están completados en la carga inicial del CSV)
    
    # Validar fechas
    df = validar_fechas(df)

    # Preparar datos para inserción
    df_maestro = pd.DataFrame([MAESTRO_TIPO_CAMBIO_ARGENTINA])
    df_precios = preparar_datos_maestro_precios(df, MAESTRO_TIPO_CAMBIO_ARGENTINA["id"])

    # Generar Excel de prueba
    excel_path = generar_excel_prueba(df_maestro, df_precios)
    
    # Mostrar resumen
    mostrar_resumen(df_maestro, df_precios)
    
    # Insertar en BD (elimina duplicados priorizando Rava) - Sin confirmación en producción
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
