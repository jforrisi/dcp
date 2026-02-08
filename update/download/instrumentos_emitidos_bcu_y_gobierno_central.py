"""
Script: instrumentos_emitidos_bcu_y_gobierno_central
-----------------------------------------------------
Descarga el Excel de "Operaciones BCU y MEF local.xlsx" desde el BCU.
Descarga directamente desde la URL del Excel.
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# URL directa al Excel
BCU_EXCEL_URL = "https://www.bcu.gub.uy/Politica-Economica-y-Mercados/Emisiones BCU/Operaciones BCU y MEF local.xlsx"

# Carpeta y nombre de archivo destino
DATA_RAW_DIR = "data_raw"
DEST_FILENAME = "instrumentos_emitidos_bcu_y_gobierno_central.xlsx"


def asegurar_data_raw():
    """Crea la carpeta data_raw si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    os.makedirs(data_raw_path, exist_ok=True)
    return data_raw_path


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
        
        chrome_bin = os.getenv('CHROME_BIN', '/usr/bin/chromium-browser')
        if os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
        
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
        if os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver


def limpiar_archivos_anteriores(data_raw_path: str):
    """Elimina archivos anteriores relacionados."""
    import time
    
    destino = os.path.join(data_raw_path, DEST_FILENAME)
    
    # Intentar eliminar el archivo destino con reintentos
    if os.path.exists(destino):
        max_intentos = 3
        for intento in range(max_intentos):
            try:
                os.remove(destino)
                print(f"[INFO] Archivo anterior '{DEST_FILENAME}' eliminado")
                break
            except PermissionError:
                if intento < max_intentos - 1:
                    print(f"[WARN] El archivo '{DEST_FILENAME}' está en uso. Esperando 2 segundos antes de reintentar...")
                    time.sleep(2)
                else:
                    print(f"[WARN] No se pudo eliminar '{DEST_FILENAME}' porque está en uso. El script continuará de todas formas.")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{DEST_FILENAME}': {e}")
    
    # Eliminar archivos que contengan "instrumentos_emitidos" o "Operaciones BCU"
    for archivo in os.listdir(data_raw_path):
        archivo_lower = archivo.lower()
        if (archivo_lower.startswith("instrumentos_emitidos") or 
            "operaciones bcu" in archivo_lower or
            "operaciones bcu y mef" in archivo_lower) and \
           archivo_lower.endswith((".xls", ".xlsx")):
            archivo_path = os.path.join(data_raw_path, archivo)
            try:
                os.remove(archivo_path)
                print(f"[INFO] Archivo anterior '{archivo}' eliminado")
            except PermissionError:
                print(f"[WARN] No se pudo eliminar '{archivo}' porque está en uso. Continuando...")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{archivo}': {e}")


def descargar_excel_bcu():
    """
    Descarga el Excel de instrumentos emitidos desde el BCU.
    Descarga directamente desde la URL del Excel.
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    # Limpiar archivos anteriores
    limpiar_archivos_anteriores(data_raw_path)

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Descargando Excel directamente desde: {BCU_EXCEL_URL}")
        # Obtener lista de archivos antes de la descarga
        archivos_antes = set(os.listdir(data_raw_path))
        
        driver.get(BCU_EXCEL_URL)
        
        # Esperar a que el archivo aparezca en la carpeta de descargas
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
                raise RuntimeError(f"Timeout: No se detectó ningún archivo Excel descargado en {tiempo_max_espera} segundos")

        # Buscar el archivo más reciente que sea Excel
        candidatos = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx"))
        ]
        
        if not candidatos:
            raise RuntimeError("No se encontró ningún Excel descargado en data_raw.")

        # Elegimos el más reciente por fecha de modificación
        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ultimo = max(candidatos_paths, key=os.path.getmtime)
        nombre_ultimo = os.path.basename(ultimo)

        destino = os.path.join(data_raw_path, DEST_FILENAME)
        
        # Si el archivo más reciente no es el destino, renombrarlo
        if os.path.abspath(ultimo) != os.path.abspath(destino):
            # Si el destino ya existe (por alguna razón), intentar eliminarlo primero
            if os.path.exists(destino):
                try:
                    os.remove(destino)
                except PermissionError:
                    print(f"[WARN] No se pudo eliminar el archivo destino existente porque está en uso. Intentando renombrar de todas formas...")
                except Exception as e:
                    print(f"[WARN] Error al eliminar archivo destino: {e}")
            
            try:
                os.replace(ultimo, destino)
                print(f"[INFO] Archivo '{nombre_ultimo}' renombrado a '{DEST_FILENAME}'")
            except PermissionError:
                # Si no se puede renombrar porque el destino está en uso, usar el nombre original
                print(f"[WARN] No se pudo renombrar el archivo porque el destino está en uso. Usando archivo con nombre original: '{nombre_ultimo}'")
                destino = ultimo
            except Exception as e:
                print(f"[WARN] Error al renombrar archivo: {e}. Usando archivo con nombre original: '{nombre_ultimo}'")
                destino = ultimo
        else:
            print(f"[INFO] Archivo ya tiene el nombre correcto: '{DEST_FILENAME}'")

        print(f"[OK] Excel guardado como: {destino}")
        return destino

    finally:
        driver.quit()


if __name__ == "__main__":
    descargar_excel_bcu()
