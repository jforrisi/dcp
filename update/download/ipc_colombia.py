"""
Script: ipc_colombia
--------------------
Descarga el Excel de Índices - series de empalme del IPC de Colombia desde el DANE.
Scrapea la página web para encontrar el enlace de descarga más reciente.
"""

import os
import sys
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse

# Agregar el directorio raíz al path para importar utils
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from update.utils.logger import ScriptLogger

# URL de la página del DANE con el IPC
DANE_IPC_PAGE_URL = "https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc"

# Carpeta y nombre de archivo destino
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "ipc_colombia.xlsx"


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


def configurar_driver():
    """Configura Chrome para scraping."""
    chrome_options = Options()
    
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY')
    is_azure = os.getenv('WEBSITE_INSTANCE_ID') or os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') or os.getenv('CONTAINER_NAME')
    is_cloud = is_railway or is_azure
    
    if is_cloud:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--remote-debugging-address=0.0.0.0")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-breakpad")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-hang-monitor")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-prompt-on-repost")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--no-crash-upload")
        chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        chrome_options.add_argument("--force-color-profile=srgb")
        chrome_options.add_argument("--hide-scrollbars")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--use-mock-keychain")
        
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
        
        # Esperar a que Chrome esté completamente inicializado
        time.sleep(2)
        
        # Verificar que el driver esté conectado
        try:
            driver.current_url
        except Exception as e:
            print(f"[WARN] Error al verificar conexión inicial: {e}")
            print("[INFO] Reintentando crear driver...")
            time.sleep(3)
            if chromedriver_path and os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            time.sleep(2)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver


def encontrar_enlace_excel(driver):
    """
    Encuentra el enlace al Excel "Índices - series de empalme" en la página.
    
    Returns:
        URL completa del Excel o None si no se encuentra
    """
    try:
        print(f"[INFO] Buscando enlace al Excel en la página...")
        
        # Esperar a que la página cargue
        time.sleep(3)
        
        # Buscar el enlace que contiene "Índices - series de empalme"
        # El enlace está en un elemento <a> con title="Índices - series de empalme en excel"
        try:
            # Intentar encontrar por el texto del botón
            wait = WebDriverWait(driver, 20)
            enlace = wait.until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//a[contains(@title, 'Índices - series de empalme') or contains(., 'Índices - series de empalme')]"
                ))
            )
            
            href = enlace.get_attribute('href')
            if href:
                # Si es una URL relativa, convertirla a absoluta
                if href.startswith('/'):
                    base_url = f"{urlparse(DANE_IPC_PAGE_URL).scheme}://{urlparse(DANE_IPC_PAGE_URL).netloc}"
                    href = urljoin(base_url, href)
                elif not href.startswith('http'):
                    href = urljoin(DANE_IPC_PAGE_URL, href)
                
                print(f"[OK] Enlace encontrado: {href}")
                return href
        except Exception as e:
            print(f"[WARN] No se encontró el enlace por XPath: {e}")
        
        # Intentar buscar por el patrón del href en el HTML
        try:
            page_source = driver.page_source
            # Buscar el patrón: href="/files/operaciones/IPC/.../anex-IPC-Indices-....xlsx"
            pattern = r'href=["\'](/files/operaciones/IPC/[^"\']*anex-IPC-Indices-[^"\']*\.xlsx)["\']'
            match = re.search(pattern, page_source)
            if match:
                href_relativo = match.group(1)
                base_url = f"{urlparse(DANE_IPC_PAGE_URL).scheme}://{urlparse(DANE_IPC_PAGE_URL).netloc}"
                href = urljoin(base_url, href_relativo)
                print(f"[OK] Enlace encontrado por regex: {href}")
                return href
        except Exception as e:
            print(f"[WARN] Error al buscar por regex: {e}")
        
        print("[ERROR] No se encontró el enlace al Excel")
        return None
        
    except Exception as e:
        print(f"[ERROR] Error al buscar el enlace: {e}")
        return None


def main():
    """Función principal con logging mejorado."""
    script_name = "ipc_colombia"
    
    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("DESCARGA DE IPC COLOMBIA - DANE")
            logger.info("=" * 80)
            
            historicos_path = asegurar_historicos()
            destino = os.path.join(historicos_path, DEST_FILENAME)
            
            logger.info(f"Carpeta de destino: {historicos_path}")
            logger.info(f"Archivo destino: {DEST_FILENAME}")
            logger.info(f"URL de la página: {DANE_IPC_PAGE_URL}")
            
            driver = None
            try:
                # Configurar driver
                logger.info("Configurando Chrome/Chromium...")
                logger.debug(f"CHROME_BIN={os.getenv('CHROME_BIN')}")
                logger.debug(f"CHROMEDRIVER_PATH={os.getenv('CHROMEDRIVER_PATH')}")
                logger.debug(f"RAILWAY_ENVIRONMENT={os.getenv('RAILWAY_ENVIRONMENT')}")
                
                driver = configurar_driver()
                logger.info("Driver configurado exitosamente")
                
                # Navegar a la página
                logger.info(f"Navegando a la página del DANE...")
                driver.get(DANE_IPC_PAGE_URL)
                
                # Esperar a que la página cargue completamente
                logger.info("Esperando a que la página cargue...")
                time.sleep(5)
                
                # Verificar que el driver sigue conectado
                try:
                    current_url = driver.current_url
                    logger.debug(f"URL después de navegar: {current_url}")
                except Exception as e:
                    logger.error(f"Chrome se desconectó después de navegar: {e}")
                    raise
                
                logger.log_selenium_state(driver, "Después de navegar")
                
                # Encontrar el enlace al Excel
                logger.info("Buscando enlace al Excel...")
                excel_url = encontrar_enlace_excel(driver)
                
                if not excel_url:
                    logger.error("No se pudo encontrar el enlace al Excel")
                    logger.log_selenium_state(driver, "Estado al momento del error")
                    raise RuntimeError("No se pudo encontrar el enlace al Excel en la página")
                
                logger.info(f"Enlace encontrado: {excel_url}")
                
                # Descargar el Excel
                logger.info("Descargando Excel...")
                if descargar_con_requests(excel_url, destino):
                    logger.info(f"Proceso completado. Archivo guardado en: {destino}")
                else:
                    logger.error("No se pudo descargar el archivo")
                    raise RuntimeError("No se pudo descargar el archivo")
                    
            except Exception as e:
                logger.log_exception(e, "main()")
                if driver:
                    logger.log_selenium_state(driver, "Estado al momento del error")
                raise
            finally:
                if driver:
                    try:
                        logger.info("Cerrando navegador...")
                        driver.quit()
                        logger.info("Navegador cerrado")
                    except Exception as e:
                        logger.warn(f"Error al cerrar navegador: {e}")


if __name__ == "__main__":
    main()
