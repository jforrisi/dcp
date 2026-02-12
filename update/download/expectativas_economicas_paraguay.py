"""
Script: expectativas_economicas_paraguay
-----------------------------------------
Descarga el Excel de Encuesta de Expectativas de Variables Económicas (EVE) 
desde el Banco Central del Paraguay (BCP).
Scrapea la página web para encontrar el enlace de descarga más reciente.
El nombre del Excel cambia cada mes (ej: EVE_Anexo_Estadístico_enero_2026.xlsx).
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    import undetected_chromedriver as uc
except ImportError:
    uc = None

# Agregar el directorio raíz al path para importar utils
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from update.utils.logger import ScriptLogger

# URL de la página del BCP con la EVE
BCP_EVE_PAGE_URL = "https://www.bcp.gov.py/web/institucional/encuesta-de-expectativas-de-variables-econonicas-eve-"

# Carpeta y nombre de archivo destino
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "expectativas_economicas_paraguay.xlsx"


def asegurar_historicos():
    """Crea la carpeta update/historicos si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    historicos_path = os.path.join(base_dir, HISTORICOS_DIR)
    os.makedirs(historicos_path, exist_ok=True)
    return historicos_path


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

    # En GitHub Actions usar undetected-chromedriver para evitar Cloudflare "Just a moment..."
    in_ci = os.getenv("GITHUB_ACTIONS") == "true"
    chrome_bin = os.getenv("CHROME_BIN")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    if in_ci and uc and chrome_bin and chromedriver_path:
        uc_options = uc.ChromeOptions()
        uc_options.add_argument("--headless=new")
        uc_options.add_argument("--no-sandbox")
        uc_options.add_argument("--disable-dev-shm-usage")
        uc_options.add_argument("--disable-gpu")
        uc_options.add_argument("--window-size=1920,1080")
        driver = uc.Chrome(
            options=uc_options,
            browser_executable_path=chrome_bin,
            driver_executable_path=chromedriver_path,
        )
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": download_dir})
        return driver
    if in_ci and chrome_bin and chromedriver_path:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.binary_location = chrome_bin
        service = Service(chromedriver_path)
        return webdriver.Chrome(service=service, options=chrome_options)

    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY') or os.getenv('AZURE_ENVIRONMENT') or os.getenv('AZURE')
    
    if is_railway:
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
    Busca el elemento <a> con class="btn-alternative btn-base" que contenga "EVE_Anexo" en el href.
    """
    print(f"[INFO] Buscando enlace de descarga en la página...")
    
    # Verificar que el driver esté activo
    try:
        _ = driver.current_url
    except Exception as e:
        print(f"[ERROR] Driver no está activo: {e}")
        raise RuntimeError("Driver no está activo, no se puede buscar el enlace")
    
    try:
        # Esperar a que la página cargue
        wait = WebDriverWait(driver, 20)
        
        # Estrategia 1: Buscar por clase y atributo download
        try:
            enlace = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[@class='btn-alternative btn-base' and @download='']")
                )
            )
            href = enlace.get_attribute('href')
            if href and 'EVE_Anexo' in href:
                print(f"[OK] Enlace encontrado (método 1): {href}")
                # Si el href es relativo, convertirlo a absoluto
                if href.startswith('/'):
                    href = f"https://www.bcp.gov.py{href}"
                return href
        except Exception as e:
            print(f"[INFO] Método 1 falló: {e}")
        
        # Estrategia 2: Buscar por href que contenga "EVE_Anexo"
        try:
            enlace = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href, 'EVE_Anexo')]")
                )
            )
            href = enlace.get_attribute('href')
            if href:
                print(f"[OK] Enlace encontrado (método 2): {href}")
                # Si el href es relativo, convertirlo a absoluto
                if href.startswith('/'):
                    href = f"https://www.bcp.gov.py{href}"
                return href
        except Exception as e:
            print(f"[INFO] Método 2 falló: {e}")
        
        # Estrategia 3: Buscar por texto "Ver Cuadros EVE"
        try:
            enlace = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(text(), 'Ver Cuadros EVE')]")
                )
            )
            href = enlace.get_attribute('href')
            if href and 'EVE_Anexo' in href:
                print(f"[OK] Enlace encontrado (método 3): {href}")
                # Si el href es relativo, convertirlo a absoluto
                if href.startswith('/'):
                    href = f"https://www.bcp.gov.py{href}"
                return href
        except Exception as e:
            print(f"[INFO] Método 3 falló: {e}")
        
        # Estrategia 4: Buscar todos los enlaces y filtrar
        try:
            enlaces = driver.find_elements(By.TAG_NAME, "a")
            for enlace in enlaces:
                href = enlace.get_attribute('href')
                if href and 'EVE_Anexo' in href:
                    print(f"[OK] Enlace encontrado (método 4): {href}")
                    # Si el href es relativo, convertirlo a absoluto
                    if href.startswith('/'):
                        href = f"https://www.bcp.gov.py{href}"
                    return href
        except Exception as e:
            print(f"[INFO] Método 4 falló: {e}")

        # Estrategia 5: Cualquier enlace .xlsx que contenga EVE o documents
        try:
            enlaces = driver.find_elements(By.XPATH, "//a[contains(@href, '.xlsx')]")
            for enlace in enlaces:
                href = enlace.get_attribute('href')
                if href and ('EVE' in href or 'documents' in href):
                    if href.startswith('/'):
                        href = f"https://www.bcp.gov.py{href}"
                    print(f"[OK] Enlace encontrado (método 5): {href[:80]}...")
                    return href
        except Exception as e:
            print(f"[INFO] Método 5 falló: {e}")
        
        raise RuntimeError("No se pudo encontrar el enlace de descarga con ningún método")
        
    except Exception as e:
        print(f"[ERROR] No se pudo encontrar el enlace de descarga: {e}")
        raise RuntimeError(f"No se pudo encontrar el enlace de descarga en la página: {e}")


def descargar_excel_bcp():
    """
    Descarga el Excel de EVE de Paraguay desde el BCP.
    Usa Selenium para navegar y descargar (mantiene la sesión del navegador
    para evitar problemas con Cloudflare).
    """
    historicos_path = asegurar_historicos()
    historicos_path_abs = os.path.abspath(historicos_path)
    destino = os.path.join(historicos_path, DEST_FILENAME)
    print(f"[INFO] Carpeta de descargas configurada en: {historicos_path}")

    driver = configurar_driver_descargas(download_dir=historicos_path_abs)

    try:
        print(f"[INFO] Navegando a: {BCP_EVE_PAGE_URL}")
        driver.get(BCP_EVE_PAGE_URL)
        time.sleep(5)

        try:
            _ = driver.current_url
        except Exception as e:
            print(f"[ERROR] Chrome se cerró inesperadamente: {e}")
            raise RuntimeError("Chrome se cerró antes de poder encontrar el enlace")

        if detectar_anti_bot(driver):
            esperar_resolucion_anti_bot(driver)
            try:
                _ = driver.current_url
            except Exception as e:
                print(f"[ERROR] Chrome se cerró después de la espera del anti-bot: {e}")
                raise RuntimeError("Chrome se cerró después de la espera del anti-bot")
        time.sleep(2)

        url_descarga = encontrar_enlace_descarga(driver)
        print(f"[INFO] Descargando Excel desde: {url_descarga}")

        archivos_antes = set(os.listdir(historicos_path))
        driver.get(url_descarga)

        print("[INFO] Esperando a que termine la descarga...")
        tiempo_max_espera = 45
        tiempo_inicio = time.time()
        while True:
            time.sleep(1)
            archivos_ahora = set(os.listdir(historicos_path))
            archivos_nuevos = archivos_ahora - archivos_antes
            excel_nuevos = [f for f in archivos_nuevos if f.lower().endswith((".xls", ".xlsx"))]
            if excel_nuevos:
                print(f"[INFO] Archivo descargado detectado: {excel_nuevos[0]}")
                break
            if time.time() - tiempo_inicio > tiempo_max_espera:
                raise RuntimeError(f"Timeout: No se detectó ningún archivo Excel en {tiempo_max_espera} segundos")

        candidatos = [f for f in os.listdir(historicos_path) if f.lower().endswith((".xls", ".xlsx"))]
        if not candidatos:
            raise RuntimeError("No se encontró ningún Excel descargado")
        candidatos_paths = [os.path.join(historicos_path, f) for f in candidatos]
        ultimo = max(candidatos_paths, key=os.path.getmtime)
        nombre_ultimo = os.path.basename(ultimo)

        if os.path.abspath(ultimo) != os.path.abspath(destino):
            if os.path.exists(destino):
                os.remove(destino)
            os.replace(ultimo, destino)
            print(f"[INFO] Archivo '{nombre_ultimo}' renombrado a '{DEST_FILENAME}'")

        print(f"[OK] Excel guardado como: {destino}")
        return destino

    finally:
        if driver:
            driver.quit()


def main():
    """Función principal con logging mejorado."""
    script_name = "expectativas_economicas_paraguay"
    
    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("DESCARGA DE ENCUESTA DE EXPECTATIVAS ECONÓMICAS PARAGUAY - BCP")
            logger.info("=" * 80)
            
            historicos_path = asegurar_historicos()
            logger.info(f"Carpeta de descargas configurada en: {historicos_path}")
            logger.debug(f"CHROME_BIN={os.getenv('CHROME_BIN')}")
            logger.debug(f"CHROMEDRIVER_PATH={os.getenv('CHROMEDRIVER_PATH')}")
            logger.debug(f"RAILWAY_ENVIRONMENT={os.getenv('RAILWAY_ENVIRONMENT')}")

            destino = descargar_excel_bcp()
            logger.info(f"Excel guardado como: {destino}")
            logger.info("=" * 80)
            logger.info("PROCESO COMPLETADO EXITOSAMENTE")
            logger.info("=" * 80)
            return destino

        except Exception as e:
            logger.log_exception(e, "main()")
            raise


if __name__ == "__main__":
    main()
