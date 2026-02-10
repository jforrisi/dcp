"""
Script: novillo_hacienda
-------------------------
Usa Selenium + Chrome para descargar el Excel de precios de hacienda de INAC
y guardarlo dentro de la carpeta `data_raw/` con el nombre estándar `precios_hacienda_inac.xlsx`,
según el flujo definido en 0_README.
"""

import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


# URL de la página donde está el enlace al Excel de precios de hacienda
INAC_PRECIOS_HACIENDA_URL = "https://www.inac.uy/innovaportal/v/10953/10/innova.front/serie-mensual-precios-de-hacienda"

# Carpeta y nombre de archivo destino dentro del proyecto
DATA_RAW_DIR = "data_raw"
DEST_FILENAME = "precios_hacienda_inac.xlsx"


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
    Detecta automáticamente si está en Railway y usa headless mode.
    """
    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Detectar si estamos en Railway (producción)
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY') or os.getenv('AZURE_ENVIRONMENT') or os.getenv('AZURE')
    
    if is_railway:
        # En Railway, usar headless y configurar Chrome/Chromium
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Intentar usar Chromium si está disponible (Railway/Nixpacks)
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
        
        # Configurar ChromeDriver si está en PATH de Railway/Nixpacks
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
        # En desarrollo local, usar Chrome normal (visible)
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver


def limpiar_archivos_anteriores(data_raw_path: str):
    """
    Elimina TODOS los archivos relacionados antes de descargar:
    - El archivo destino si existe
    - Cualquier archivo que empiece con "webinac---serie-mensual-precios-de-hacienda" (con o sin (1), (2), etc.)
    """
    destino = os.path.join(data_raw_path, DEST_FILENAME)
    
    # Eliminar el archivo destino si ya existe
    if os.path.exists(destino):
        os.remove(destino)
        print(f"[INFO] Archivo anterior '{DEST_FILENAME}' eliminado")
    
    # Eliminar archivos que empiecen con "webinac---serie-mensual-precios-de-hacienda" (con o sin (1), (2), etc.)
    for archivo in os.listdir(data_raw_path):
        archivo_lower = archivo.lower()
        if archivo_lower.startswith("webinac---serie-mensual-precios-de-hacienda") and archivo_lower.endswith((".xls", ".xlsx")):
            archivo_path = os.path.join(data_raw_path, archivo)
            try:
                os.remove(archivo_path)
                print(f"[INFO] Archivo anterior '{archivo}' eliminado")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{archivo}': {e}")


def descargar_excel_inac():
    """
    Descarga el Excel de precios de hacienda de INAC directamente desde la URL
    y lo guarda en data_raw con el nombre estándar.
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    # Limpiar archivos anteriores antes de descargar
    limpiar_archivos_anteriores(data_raw_path)

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Descargando Excel directamente desde: {INAC_PRECIOS_HACIENDA_URL}")
        # La URL descarga directamente el Excel, solo necesitamos navegar a ella
        # Obtener lista de archivos antes de la descarga
        archivos_antes = set(os.listdir(data_raw_path))
        
        driver.get(INAC_PRECIOS_HACIENDA_URL)
        
        # Esperar a que el archivo aparezca en la carpeta de descargas.
        # Esperamos activamente hasta que aparezca un archivo nuevo.
        print("[INFO] Esperando a que termine la descarga...")
        tiempo_inicio = time.time()
        tiempo_max_espera = 30  # segundos máximo
        
        while True:
            time.sleep(1)
            archivos_ahora = set(os.listdir(data_raw_path))
            archivos_nuevos = archivos_ahora - archivos_antes
            
            # Buscar archivos Excel nuevos (incluyendo los que tienen (1), (2), etc.)
            excel_nuevos = [
                f for f in archivos_nuevos 
                if f.lower().endswith((".xls", ".xlsx"))
            ]
            
            if excel_nuevos:
                print(f"[INFO] Archivo descargado detectado: {excel_nuevos[0]}")
                break
            
            if time.time() - tiempo_inicio > tiempo_max_espera:
                raise RuntimeError(f"Timeout: No se detecto ningun archivo Excel descargado en {tiempo_max_espera} segundos")

        # Buscar el archivo más reciente que sea Excel (puede ser webinac---serie-mensual-precios-de-hacienda.xlsx o con (1), (2), etc.)
        candidatos = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx"))
        ]
        
        if not candidatos:
            raise RuntimeError("No se encontro ningun Excel descargado en data_raw.")

        # Elegimos el más reciente por fecha de modificación
        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ultimo = max(candidatos_paths, key=os.path.getmtime)
        nombre_ultimo = os.path.basename(ultimo)

        destino = os.path.join(data_raw_path, DEST_FILENAME)
        
        # Si el archivo más reciente no es el destino, renombrarlo
        if os.path.abspath(ultimo) != os.path.abspath(destino):
            # Si el destino ya existe (por alguna razón), eliminarlo primero
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
    descargar_excel_inac()

