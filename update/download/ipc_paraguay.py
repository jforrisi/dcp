"""
Script: ipc_paraguay
--------------------
Descarga el Excel de IPC de Paraguay desde el Banco Central del Paraguay (BCP).
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

# Agregar el directorio raíz al path para importar utils
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from update.utils.logger import ScriptLogger

# URL de la página del BCP con el IPC
BCP_IPC_PAGE_URL = "https://www.bcp.gov.py/web/institucional/indice-precios-al-consumidor-ipc"

# Carpeta y nombre de archivo destino
DATA_RAW_DIR = "data_raw"
DEST_FILENAME = "ipc_paraguay.xlsx"

# Parte estable del enlace
STABLE_PATH = "/documents/20117/2275428/AE_IPC.xlsx"


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
    
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY') or os.getenv('AZURE_ENVIRONMENT') or os.getenv('AZURE')
    
    if is_railway:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-extensions")
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


def limpiar_archivos_anteriores(data_raw_path: str):
    """Elimina archivos anteriores relacionados."""
    destino = os.path.join(data_raw_path, DEST_FILENAME)
    
    if os.path.exists(destino):
        os.remove(destino)
        print(f"[INFO] Archivo anterior '{DEST_FILENAME}' eliminado")
    
    # Eliminar archivos que contengan "ipc_paraguay" o "AE_IPC"
    for archivo in os.listdir(data_raw_path):
        archivo_lower = archivo.lower()
        if (archivo_lower.startswith("ipc_paraguay") or 
            "ae_ipc" in archivo_lower) and \
           archivo_lower.endswith((".xls", ".xlsx")):
            archivo_path = os.path.join(data_raw_path, archivo)
            try:
                os.remove(archivo_path)
                print(f"[INFO] Archivo anterior '{archivo}' eliminado")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{archivo}': {e}")


def detectar_anti_bot(driver):
    """
    Detecta si hay un anti-bot/CAPTCHA en la página.
    Retorna True si detecta anti-bot, False si no.
    """
    try:
        from selenium.common.exceptions import NoSuchWindowException, WebDriverException
        try:
            _ = driver.current_url
        except (NoSuchWindowException, WebDriverException):
            return False
        
        try:
            page_source_lower = driver.page_source.lower()
            page_title_lower = driver.title.lower()
        except (NoSuchWindowException, WebDriverException):
            return False
        
        anti_bot_indicators = [
            "captcha", "cloudflare", "challenge", "verification",
            "bot detection", "security check", "hcaptcha", "recaptcha",
            "turnstile", "just a moment"
        ]
        
        for indicator in anti_bot_indicators:
            if indicator in page_source_lower or indicator in page_title_lower:
                print(f"[INFO] Posible anti-bot detectado: {indicator}")
                return True
        
        # Buscar por elementos comunes de Cloudflare
        try:
            driver.find_element(By.ID, "challenge-form")
            print("[INFO] Cloudflare challenge detectado")
            return True
        except:
            pass
        
        try:
            driver.find_element(By.CLASS_NAME, "cf-browser-verification")
            print("[INFO] Cloudflare verification detectado")
            return True
        except:
            pass
        
        return False
    except Exception as e:
        print(f"[WARN] Error al detectar anti-bot: {e}")
        return False


def esperar_resolucion_anti_bot(driver):
    """
    Espera automáticamente a que se resuelva el anti-bot/CAPTCHA.
    Espera hasta 60 segundos antes de continuar.
    Verifica periódicamente que Chrome sigue abierto.
    """
    print("\n" + "=" * 60)
    print("ANTI-BOT DETECTADO")
    print("=" * 60)
    print("[INFO] Esperando automáticamente hasta 60 segundos para que se resuelva...")
    print("[INFO] Si el anti-bot persiste, el script continuará de todas formas.")
    print("=" * 60 + "\n")
    
    from selenium.common.exceptions import NoSuchWindowException, WebDriverException
    total_wait = 60
    waited = 0
    check_interval = 5
    
    while waited < total_wait:
        try:
            _ = driver.current_url
            time.sleep(check_interval)
            waited += check_interval
            if waited % 15 == 0:
                print(f"[INFO] Esperando... ({waited}/{total_wait} segundos)")
        except (NoSuchWindowException, WebDriverException) as e:
            print(f"[ERROR] Chrome se cerró durante la espera: {e}")
            raise RuntimeError("Chrome se cerró inesperadamente durante la espera de Cloudflare")
    
    print("[INFO] Continuando...")
    
    try:
        _ = driver.current_url
        time.sleep(2)
    except (NoSuchWindowException, WebDriverException) as e:
        print(f"[ERROR] Chrome se cerró justo después de la espera: {e}")
        raise RuntimeError("Chrome se cerró inesperadamente después de la espera de Cloudflare")


def encontrar_enlace_descarga(driver):
    """
    Encuentra el enlace de descarga en la página del BCP.
    Busca el elemento <a> con class="card__footer-link" que contenga el path estable.
    """
    print(f"[INFO] Buscando enlace de descarga en la página...")
    
    try:
        # Esperar a que la página cargue
        wait = WebDriverWait(driver, 20)
        
        # Buscar el enlace que contiene el path estable
        enlace = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//a[contains(@href, '{STABLE_PATH}')]")
            )
        )
        
        href = enlace.get_attribute('href')
        print(f"[OK] Enlace encontrado: {href}")
        
        # Si el href es relativo, convertirlo a absoluto
        if href.startswith('/'):
            href = f"https://www.bcp.gov.py{href}"
        
        return href
        
    except Exception as e:
        print(f"[ERROR] No se pudo encontrar el enlace de descarga: {e}")
        # Intentar buscar cualquier enlace con "AE_IPC.xlsx"
        try:
            enlaces = driver.find_elements(By.XPATH, "//a[contains(@href, 'AE_IPC.xlsx')]")
            if enlaces:
                href = enlaces[0].get_attribute('href')
                if href.startswith('/'):
                    href = f"https://www.bcp.gov.py{href}"
                print(f"[OK] Enlace encontrado (método alternativo): {href}")
                return href
        except:
            pass
        
        raise RuntimeError(f"No se pudo encontrar el enlace de descarga en la página")


def descargar_excel_bcp():
    """
    Descarga el Excel de IPC de Paraguay desde el BCP.
    Scrapea la página para encontrar el enlace de descarga más reciente.
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    # Limpiar archivos anteriores
    limpiar_archivos_anteriores(data_raw_path)

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Navegando a: {BCP_IPC_PAGE_URL}")
        driver.get(BCP_IPC_PAGE_URL)
        
        # Esperar a que la página cargue completamente
        time.sleep(3)
        
        # Encontrar el enlace de descarga
        url_descarga = encontrar_enlace_descarga(driver)
        
        print(f"[INFO] Descargando Excel desde: {url_descarga}")
        archivos_antes = set(os.listdir(data_raw_path))
        
        # Navegar directamente a la URL de descarga
        driver.get(url_descarga)
        
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


def main():
    """Función principal con logging mejorado."""
    script_name = "ipc_paraguay"
    
    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("DESCARGA DE IPC PARAGUAY - BCP")
            logger.info("=" * 80)
            
            data_raw_path = asegurar_data_raw()
            logger.info(f"Carpeta de descargas configurada en: {data_raw_path}")

            # Limpiar archivos anteriores
            logger.info("Limpiando archivos anteriores...")
            limpiar_archivos_anteriores(data_raw_path)

            # Configurar driver con logging
            logger.info("Configurando Chrome/Chromium...")
            logger.debug(f"CHROME_BIN={os.getenv('CHROME_BIN')}")
            logger.debug(f"CHROMEDRIVER_PATH={os.getenv('CHROMEDRIVER_PATH')}")
            logger.debug(f"RAILWAY_ENVIRONMENT={os.getenv('RAILWAY_ENVIRONMENT')}")
            
            driver = configurar_driver_descargas(download_dir=data_raw_path)
            logger.info("Driver configurado exitosamente")

            try:
                logger.info(f"Navegando a: {BCP_IPC_PAGE_URL}")
                driver.get(BCP_IPC_PAGE_URL)
                
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
                
                # Verificar anti-bot/CAPTCHA antes de buscar el enlace
                logger.info("Verificando anti-bot/CAPTCHA...")
                if detectar_anti_bot(driver):
                    logger.warn("Anti-bot detectado, esperando resolución...")
                    esperar_resolucion_anti_bot(driver)
                    logger.log_selenium_state(driver, "Después de anti-bot")
                
                # Encontrar el enlace de descarga
                logger.info("Buscando enlace de descarga...")
                url_descarga = encontrar_enlace_descarga(driver)
                
                if not url_descarga:
                    logger.error("No se pudo encontrar el enlace de descarga")
                    logger.log_selenium_state(driver, "Estado al momento del error")
                    raise RuntimeError("No se pudo encontrar el enlace de descarga")
                
                logger.info(f"Enlace encontrado: {url_descarga}")
                logger.info("Descargando Excel...")
                archivos_antes = set(os.listdir(data_raw_path))
                
                # Navegar directamente a la URL de descarga
                driver.get(url_descarga)
                
                logger.info("Esperando a que termine la descarga...")
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
                        logger.info(f"Archivo descargado detectado: {excel_nuevos[0]}")
                        break
                    
                    if time.time() - tiempo_inicio > tiempo_max_espera:
                        logger.error(f"Timeout: No se detectó ningún archivo Excel descargado en {tiempo_max_espera} segundos")
                        raise RuntimeError(f"Timeout: No se detectó ningún archivo Excel descargado en {tiempo_max_espera} segundos")

                # Buscar el archivo más reciente
                candidatos = [
                    f for f in os.listdir(data_raw_path)
                    if f.lower().endswith((".xls", ".xlsx"))
                ]
                
                if not candidatos:
                    logger.error("No se encontró ningún Excel descargado")
                    raise RuntimeError("No se encontró ningún Excel descargado en data_raw.")

                candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
                ultimo = max(candidatos_paths, key=os.path.getmtime)
                nombre_ultimo = os.path.basename(ultimo)

                destino = os.path.join(data_raw_path, DEST_FILENAME)
                
                if os.path.abspath(ultimo) != os.path.abspath(destino):
                    if os.path.exists(destino):
                        os.remove(destino)
                    os.replace(ultimo, destino)
                    logger.info(f"Archivo '{nombre_ultimo}' renombrado a '{DEST_FILENAME}'")
                else:
                    logger.info(f"Archivo ya tiene el nombre correcto: '{DEST_FILENAME}'")

                logger.info(f"Excel guardado como: {destino}")
                logger.info("=" * 80)
                logger.info("PROCESO COMPLETADO EXITOSAMENTE")
                logger.info("=" * 80)
                
                return destino

            except Exception as e:
                logger.log_exception(e, "descargar_excel_bcp()")
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
                        
        except Exception as e:
            logger.log_exception(e, "main()")
            raise


if __name__ == "__main__":
    main()
