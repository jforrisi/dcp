"""
Script: anexo_estadistico_paraguay
-----------------------------------
Descarga el Excel "Anexo Estadístico del Informe Económico" desde el BCP (Paraguay).
Misma lógica que expectativas_economicas_paraguay: navega a la página y descarga
el archivo desde el enlace con class="btn-alternative btn-base" y download.
El nombre del Excel cambia cada mes (ej: Anexo_Estadístico_del_Informe_Económico_05_02_2026.xlsx).
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

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from update.utils.logger import ScriptLogger

# URL de la página del BCP con el Anexo Estadístico
BCP_ANEXO_PAGE_URL = "https://www.bcp.gov.py/web/institucional/anexo-estadistico-"

HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "anexo_estadistico_paraguay.xlsx"


def asegurar_historicos():
    """Crea la carpeta update/historicos si no existe."""
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
            possible_paths = [
                '/root/.nix-profile/bin/chromium',
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

        chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
        if not chromedriver_path:
            possible_paths = [
                '/root/.nix-profile/bin/chromedriver',
                '/usr/bin/chromedriver',
                '/usr/local/bin/chromedriver',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    chromedriver_path = path
                    break

        if chromedriver_path and os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)

        time.sleep(2)
        try:
            driver.current_url
        except Exception:
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
    """Detecta si hay anti-bot/CAPTCHA."""
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
                return True

        try:
            driver.find_element(By.ID, "challenge-form")
            return True
        except:
            pass

        try:
            driver.find_element(By.CLASS_NAME, "cf-browser-verification")
            return True
        except:
            pass

        return False
    except Exception:
        return False


def esperar_resolucion_anti_bot(driver):
    """Espera hasta 60 segundos a que se resuelva el anti-bot."""
    from selenium.common.exceptions import NoSuchWindowException, WebDriverException
    total_wait = 60
    waited = 0
    check_interval = 5

    while waited < total_wait:
        try:
            _ = driver.current_url
            time.sleep(check_interval)
            waited += check_interval
        except (NoSuchWindowException, WebDriverException):
            raise RuntimeError("Chrome se cerró durante la espera de Cloudflare")

    time.sleep(2)


def encontrar_enlace_descarga(driver):
    """
    Encuentra el enlace de descarga del Anexo Estadístico.
    Busca el <a> con class="btn-alternative btn-base" y download.
    El href suele contener "Anexo_Estad" o "Anexo_Estadístico" o ".xlsx".
    """
    print("[INFO] Buscando enlace de descarga en la página...")

    try:
        _ = driver.current_url
    except Exception as e:
        raise RuntimeError(f"Driver no está activo: {e}")

    wait = WebDriverWait(driver, 20)

    # Estrategia 1: Buscar por clase btn-alternative btn-base con download
    try:
        enlace = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[@class='btn-alternative btn-base' and @download='']")
            )
        )
        href = enlace.get_attribute('href')
        if href and ('.xlsx' in href.lower() or '.xls' in href.lower() or 'Anexo' in href or 'anexo' in href):
            if href.startswith('/'):
                href = f"https://www.bcp.gov.py{href}"
            print(f"[OK] Enlace encontrado (método 1): {href[:80]}...")
            return href
    except Exception:
        pass

    # Estrategia 2: Buscar por href que contenga Anexo_Estadístico o Anexo_Estad
    try:
        enlace = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[contains(@href, 'Anexo_Estad') or contains(@href, 'anexo_estad')]")
            )
        )
        href = enlace.get_attribute('href')
        if href:
            if href.startswith('/'):
                href = f"https://www.bcp.gov.py{href}"
            print(f"[OK] Enlace encontrado (método 2): {href[:80]}...")
            return href
    except Exception:
        pass

    # Estrategia 3: Buscar por href que contenga "documents" y ".xlsx"
    try:
        enlaces = driver.find_elements(By.XPATH, "//a[contains(@href, 'documents') and contains(@href, '.xlsx')]")
        for enlace in enlaces:
            href = enlace.get_attribute('href')
            if href and ('Anexo' in href or 'anexo' in href or 'Informe' in href):
                if href.startswith('/'):
                    href = f"https://www.bcp.gov.py{href}"
                print(f"[OK] Enlace encontrado (método 3): {href[:80]}...")
                return href
    except Exception:
        pass

    # Estrategia 4: Buscar todos los enlaces con download y .xlsx
    try:
        enlaces = driver.find_elements(By.TAG_NAME, "a")
        for enlace in enlaces:
            href = enlace.get_attribute('href')
            download_attr = enlace.get_attribute('download')
            if href and (download_attr is not None or 'Anexo' in (href or '') or 'anexo' in (href or '')):
                if '.xlsx' in (href or '').lower() or '.xls' in (href or '').lower():
                    if href.startswith('/'):
                        href = f"https://www.bcp.gov.py{href}"
                    print(f"[OK] Enlace encontrado (método 4): {href[:80]}...")
                    return href
    except Exception:
        pass

    raise RuntimeError("No se pudo encontrar el enlace de descarga del Anexo Estadístico")


def descargar_excel_bcp():
    """Descarga el Excel del Anexo Estadístico desde el BCP."""
    historicos_path = asegurar_historicos()
    historicos_path_abs = os.path.abspath(historicos_path)
    destino = os.path.join(historicos_path, DEST_FILENAME)
    print(f"[INFO] Carpeta de descargas: {historicos_path}")

    driver = configurar_driver_descargas(download_dir=historicos_path_abs)

    try:
        print(f"[INFO] Navegando a: {BCP_ANEXO_PAGE_URL}")
        driver.get(BCP_ANEXO_PAGE_URL)
        time.sleep(5)

        try:
            _ = driver.current_url
        except Exception:
            raise RuntimeError("Chrome se cerró inesperadamente")

        if detectar_anti_bot(driver):
            esperar_resolucion_anti_bot(driver)
            time.sleep(2)

        url_descarga = encontrar_enlace_descarga(driver)
        print(f"[INFO] Descargando Excel desde: {url_descarga[:80]}...")

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
                print(f"[INFO] Archivo descargado: {excel_nuevos[0]}")
                break
            if time.time() - tiempo_inicio > tiempo_max_espera:
                raise RuntimeError(f"Timeout: No se detectó ningún archivo Excel en {tiempo_max_espera}s")

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
    """Función principal."""
    script_name = "anexo_estadistico_paraguay"

    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("DESCARGA DE ANEXO ESTADÍSTICO DEL INFORME ECONÓMICO - BCP PARAGUAY")
            logger.info("=" * 80)

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
