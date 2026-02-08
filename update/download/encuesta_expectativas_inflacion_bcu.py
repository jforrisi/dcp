"""
Script: encuesta_expectativas_inflacion_bcu
--------------------------------------------
Descarga el Excel de Encuesta de Expectativas de Inflación desde el BCU.
Descarga directamente desde la URL del Excel y lo guarda en update/historicos.
"""

import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# URL directa al Excel
BCU_EXCEL_URL = "https://www.bcu.gub.uy/Estadisticas-e-Indicadores/Encuesta-Expectativas-Inflacion/IEES05I2.XLS?Mobile=1&Source=%2FEstadisticas%2De%2DIndicadores%2F%5Flayouts%2F15%2Fmobile%2Fviewa%2Easpx%3FList%3Df181d7a4%2De216%2D460b%2D834f%2D98f4642ef6ba%26View%3D34062e82%2D1d50%2D44cc%2D89c8%2Dbe0cef045523%26wdFCCState%3D1"

# Carpeta y nombre de archivo destino
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "expectativas_inflacion_uyu_bcu.xls"


def asegurar_historicos():
    """Crea la carpeta update/historicos si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    historicos_path = os.path.join(base_dir, HISTORICOS_DIR)
    os.makedirs(historicos_path, exist_ok=True)
    return historicos_path


def descargar_con_requests(url: str, destino: str) -> bool:
    """
    Intenta descargar el archivo usando requests.
    
    Returns:
        True si la descarga fue exitosa, False en caso contrario
    """
    try:
        print(f"[INFO] Intentando descargar con requests...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Deshabilitar verificación SSL para sitios con certificados problemáticos
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.get(url, headers=headers, timeout=30, stream=True, verify=False)
        response.raise_for_status()
        
        # Verificar que el contenido sea un Excel
        content_type = response.headers.get('Content-Type', '').lower()
        if 'excel' not in content_type and 'spreadsheet' not in content_type and 'application/octet-stream' not in content_type:
            print(f"[WARN] Content-Type inesperado: {content_type}")
            # Continuar de todas formas, puede ser un Excel aunque el Content-Type no lo indique
        
        # Guardar el archivo
        with open(destino, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Verificar que el archivo se descargó correctamente
        if os.path.exists(destino) and os.path.getsize(destino) > 0:
            print(f"[OK] Archivo descargado exitosamente con requests: {os.path.getsize(destino)} bytes")
            return True
        else:
            print(f"[ERROR] El archivo descargado está vacío o no existe")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[WARN] Error al descargar con requests: {e}")
        return False
    except Exception as e:
        print(f"[WARN] Error inesperado con requests: {e}")
        return False


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
    is_azure = os.getenv('WEBSITE_INSTANCE_ID') or os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') or os.getenv('CONTAINER_NAME')
    is_cloud = is_railway or is_azure
    
    if is_cloud:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        chrome_bin = os.getenv('CHROME_BIN')
        if not chrome_bin:
            possible_paths = [
                '/root/.nix-profile/bin/chromium',  # Railway/Nixpacks (prioridad)
                '/usr/bin/google-chrome',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
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
            print(f"[INFO] Usando ChromeDriver en: {chromedriver_path}")
        else:
            print(f"[WARNING] ChromeDriver no encontrado. CHROMEDRIVER_PATH={os.getenv('CHROMEDRIVER_PATH')}")
        
        if chromedriver_path and os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver


def descargar_con_selenium(url: str, destino: str) -> bool:
    """
    Descarga el archivo usando Selenium como fallback.
    
    Returns:
        True si la descarga fue exitosa, False en caso contrario
    """
    historicos_path = asegurar_historicos()
    driver = None
    
    try:
        print(f"[INFO] Intentando descargar con Selenium...")
        driver = configurar_driver_descargas(download_dir=historicos_path)
        
        # Obtener lista de archivos antes de la descarga
        archivos_antes = set(os.listdir(historicos_path))
        
        print(f"[INFO] Navegando a: {url}")
        driver.get(url)
        
        # Esperar un poco para que la página cargue
        time.sleep(3)
        
        # Esperar a que el archivo aparezca en la carpeta de descargas
        print("[INFO] Esperando a que termine la descarga...")
        tiempo_inicio = time.time()
        tiempo_max_espera = 60  # segundos máximo (aumentado)
        
        while True:
            time.sleep(2)  # Esperar 2 segundos entre checks
            try:
                archivos_ahora = set(os.listdir(historicos_path))
                archivos_nuevos = archivos_ahora - archivos_antes
                
                # Buscar archivos Excel nuevos (incluyendo .xls, .xlsx, .XLS, .XLSX)
                excel_nuevos = [
                    f for f in archivos_nuevos 
                    if f.lower().endswith((".xls", ".xlsx")) or f.upper().endswith((".XLS", ".XLSX"))
                ]
                
                if excel_nuevos:
                    print(f"[INFO] Archivo descargado detectado: {excel_nuevos[0]}")
                    break
            except Exception as e:
                print(f"[WARN] Error al verificar archivos: {e}")
            
            if time.time() - tiempo_inicio > tiempo_max_espera:
                raise RuntimeError(f"Timeout: No se detectó ningún archivo Excel descargado en {tiempo_max_espera} segundos")
        
        # Buscar el archivo más reciente que sea Excel
        candidatos = [
            f
            for f in os.listdir(historicos_path)
            if f.lower().endswith((".xls", ".xlsx")) or f.upper().endswith((".XLS", ".XLSX"))
        ]
        
        if not candidatos:
            raise RuntimeError("No se encontró ningún Excel descargado.")
        
        # Elegimos el más reciente por fecha de modificación
        candidatos_paths = [os.path.join(historicos_path, f) for f in candidatos]
        ultimo = max(candidatos_paths, key=os.path.getmtime)
        nombre_ultimo = os.path.basename(ultimo)
        
        # Si el archivo más reciente no es el destino, renombrarlo
        if os.path.abspath(ultimo) != os.path.abspath(destino):
            if os.path.exists(destino):
                try:
                    os.remove(destino)
                except Exception as e:
                    print(f"[WARN] No se pudo eliminar el archivo destino existente: {e}")
            
            try:
                os.replace(ultimo, destino)
                print(f"[INFO] Archivo '{nombre_ultimo}' renombrado a '{DEST_FILENAME}'")
            except Exception as e:
                print(f"[WARN] Error al renombrar archivo: {e}. Usando archivo con nombre original: '{nombre_ultimo}'")
                destino = ultimo
        
        if os.path.exists(destino) and os.path.getsize(destino) > 0:
            print(f"[OK] Archivo descargado exitosamente con Selenium: {os.path.getsize(destino)} bytes")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"[ERROR] Error al descargar con Selenium: {e}")
        return False
    finally:
        if driver:
            driver.quit()


def main():
    """Función principal."""
    print("=" * 80)
    print("DESCARGA DE ENCUESTA DE EXPECTATIVAS DE INFLACIÓN - BCU")
    print("=" * 80)
    
    historicos_path = asegurar_historicos()
    destino = os.path.join(historicos_path, DEST_FILENAME)
    
    print(f"[INFO] Carpeta de destino: {historicos_path}")
    print(f"[INFO] Archivo destino: {DEST_FILENAME}")
    print(f"[INFO] URL: {BCU_EXCEL_URL}")
    print("=" * 80)
    
    # Intentar primero con requests (más rápido y simple)
    if descargar_con_requests(BCU_EXCEL_URL, destino):
        print(f"\n[SUCCESS] Proceso completado. Archivo guardado en: {destino}")
        return
    
    # Si requests falla, intentar con Selenium
    print(f"\n[INFO] Falló la descarga con requests, intentando con Selenium...")
    if descargar_con_selenium(BCU_EXCEL_URL, destino):
        print(f"\n[SUCCESS] Proceso completado. Archivo guardado en: {destino}")
        return
    
    # Si ambos fallan
    raise RuntimeError("No se pudo descargar el archivo ni con requests ni con Selenium")


if __name__ == "__main__":
    main()
