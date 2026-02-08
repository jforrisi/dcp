"""
Script: leche_polvo_entera
--------------------------
Descarga el Excel de exportación leche en polvo entera de INALE
y lo guarda en data_raw con el nombre estándar.
Busca automáticamente la URL más reciente probando diferentes años/meses.
"""

import os
import time
from datetime import datetime
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Base URL y nombre de archivo
BASE_URL_INALE = "https://www.inale.org/wp-content/uploads"
FILENAME_INALE = "Exportacion-leche-en-polvo-entera.xlsx"

# Carpeta y nombre de archivo destino
DATA_RAW_DIR = "data_raw"
DEST_FILENAME = "exportacion_leche_polvo_entera.xlsx"


def asegurar_data_raw():
    """Crea la carpeta data_raw si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    os.makedirs(data_raw_path, exist_ok=True)
    return data_raw_path


def encontrar_url_mas_reciente():
    """
    Encuentra la URL más reciente del Excel probando diferentes años/meses.
    Empieza desde el mes/año actual y retrocede hasta encontrar una URL válida.
    """
    ahora = datetime.now()
    año_actual = ahora.year
    mes_actual = ahora.month
    
    # Probar hasta 24 meses hacia atrás (2 años)
    for meses_atras in range(24):
        año = año_actual
        mes = mes_actual - meses_atras
        
        # Ajustar año si mes es negativo
        while mes <= 0:
            mes += 12
            año -= 1
        
        url = f"{BASE_URL_INALE}/{año}/{mes:02d}/{FILENAME_INALE}"
        
        # Verificar si la URL existe con HEAD request
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                print(f"[OK] URL encontrada: {url}")
                return url
        except Exception as e:
            continue
    
    # Si no se encuentra ninguna, usar la del año/mes actual como fallback
    url_fallback = f"{BASE_URL_INALE}/{año_actual}/{mes_actual:02d}/{FILENAME_INALE}"
    print(f"[WARN] No se encontró URL válida, usando fallback: {url_fallback}")
    return url_fallback


def configurar_driver_descargas(download_dir: str):
    """Configura Chrome para descargas automáticas."""
    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY')
    
    if is_railway:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        chrome_bin = os.getenv('CHROME_BIN')
        if not chrome_bin:
            # Intentar detectar automáticamente
            possible_paths = [
                '/root/.nix-profile/bin/chromium',  # Railway/Nixpacks (prioridad)
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/usr/bin/google-chrome',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    chrome_bin = path
                    break
        
        if chrome_bin and os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
            print(f"[INFO] Usando Chrome/Chromium en: {chrome_bin}")
        else:
            print(f"[WARNING] Chrome/Chromium no encontrado. CHROME_BIN={os.getenv('CHROME_BIN')}")
        
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
        if not chromedriver_path:
            # Intentar detectar automáticamente
            possible_paths = [
                '/root/.nix-profile/bin/chromedriver',  # Railway/Nixpacks (prioridad)
                '/usr/bin/chromedriver',
                '/usr/local/bin/chromedriver',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    chromedriver_path = path
                    break
        
        if chromedriver_path and os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
            print(f"[INFO] Usando ChromeDriver en: {chromedriver_path}")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            print(f"[WARNING] ChromeDriver no encontrado. CHROMEDRIVER_PATH={os.getenv('CHROMEDRIVER_PATH')}")
            driver = webdriver.Chrome(options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver


def limpiar_archivos_anteriores(data_raw_path: str):
    """Elimina archivos anteriores relacionados."""
    destino = os.path.join(data_raw_path, DEST_FILENAME)
    
    if os.path.exists(destino):
        os.remove(destino)
        print(f"[INFO] Archivo anterior '{DEST_FILENAME}' eliminado")
    
    # Eliminar archivos que empiecen con el nombre base
    for archivo in os.listdir(data_raw_path):
        archivo_lower = archivo.lower()
        if (archivo_lower.startswith("exportacion-leche-en-polvo-entera") or 
            archivo_lower.startswith("exportacion_leche_polvo_entera")) and \
           archivo_lower.endswith((".xls", ".xlsx")):
            archivo_path = os.path.join(data_raw_path, archivo)
            try:
                os.remove(archivo_path)
                print(f"[INFO] Archivo anterior '{archivo}' eliminado")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{archivo}': {e}")


def descargar_excel_inale():
    """
    Descarga el Excel de INALE directamente desde la URL más reciente
    y lo guarda en data_raw con el nombre estándar.
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    # Encontrar URL más reciente
    url = encontrar_url_mas_reciente()
    
    # Limpiar archivos anteriores
    limpiar_archivos_anteriores(data_raw_path)

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Descargando Excel desde: {url}")
        archivos_antes = set(os.listdir(data_raw_path))
        
        driver.get(url)
        
        print("[INFO] Esperando a que termine la descarga...")
        tiempo_inicio = time.time()
        tiempo_max_espera = 30
        
        while True:
            time.sleep(1)
            archivos_ahora = set(os.listdir(data_raw_path))
            archivos_nuevos = archivos_ahora - archivos_antes
            
            excel_nuevos = [
                f for f in archivos_nuevos 
                if f.lower().endswith((".xls", ".xlsx"))
            ]
            
            if excel_nuevos:
                print(f"[INFO] Archivo descargado detectado: {excel_nuevos[0]}")
                break
            
            if time.time() - tiempo_inicio > tiempo_max_espera:
                raise RuntimeError(f"Timeout: No se detectó ningún archivo Excel descargado en {tiempo_max_espera} segundos")

        # Buscar el archivo más reciente
        candidatos = [
            f for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx"))
        ]
        
        if not candidatos:
            raise RuntimeError("No se encontró ningún Excel descargado en data_raw.")

        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ultimo = max(candidatos_paths, key=os.path.getmtime)
        nombre_ultimo = os.path.basename(ultimo)

        destino = os.path.join(data_raw_path, DEST_FILENAME)
        
        if os.path.abspath(ultimo) != os.path.abspath(destino):
            if os.path.exists(destino):
                os.remove(destino)
            os.replace(ultimo, destino)
            print(f"[INFO] Archivo '{nombre_ultimo}' renombrado a '{DEST_FILENAME}'")
        else:
            print(f"[INFO] Archivo ya tiene el nombre correcto: '{DEST_FILENAME}'")

        print(f"[OK] Excel guardado como: {destino}")
        return destino

    finally:
        driver.quit()


if __name__ == "__main__":
    descargar_excel_inale()
