"""
Script: expectativas_eme_analistas_banrep
-----------------------------------------
Descarga el Excel "Serie histórica (disponible desde 2001)" de la Encuesta Mensual de Expectativas
de analistas económicos (EME) desde BanRep (suameca.banrep.gov.co).

Flujo:
1) Navegar a la página de encuestas.
2) Expandir "1.1. Encuesta mensual de expectativas de analistas económicos (EME)".
3) Expandir sección "Datos" (clic en icono).
4) Encontrar y descargar "Serie histórica (disponible desde 2001)".
"""

import os
import sys
import time
import requests
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Agregar el directorio raíz al path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from update.utils.logger import ScriptLogger

BANREP_PAGE_URL = "https://suameca.banrep.gov.co/estadisticas-economicas/encuestas"
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "expectativas_eme_analistas_banrep.xlsx"

# ID del catálogo EME en BanRep
EME_CATALOG_ID = "100011"


def asegurar_historicos():
    """Crea la carpeta update/historicos si no existe."""
    base_dir = os.getcwd()
    historicos_path = os.path.join(base_dir, HISTORICOS_DIR)
    os.makedirs(historicos_path, exist_ok=True)
    return historicos_path


def descargar_con_requests(url: str, destino: str) -> bool:
    """Descarga archivo con requests."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=60, stream=True, verify=False)
        response.raise_for_status()
        with open(destino, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return os.path.exists(destino) and os.path.getsize(destino) > 0
    except Exception as e:
        print(f"[WARN] requests falló: {e}")
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
    if is_railway:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def hacer_clic_por_texto(driver, wait, texto, descripcion):
    """Busca elemento por texto y hace clic."""
    selectores = [
        f"//*[contains(text(), '{texto}')]",
        f"//*[contains(., '{texto}')]",
    ]
    for selector in selectores:
        try:
            elem = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", elem)
            time.sleep(2)
            print(f"[OK] Clic en: {descripcion}")
            return True
        except Exception:
            continue
    return False


def expandir_eme_y_datos(driver):
    """
    Expande siguiendo el flujo de expectativas_empresariales_colombia_banrep:
    1) "1. Encuestas sobre expectativas económicas"
    2) "1.1. Encuesta mensual de expectativas de analistas económicos (EME)"
    3) "Datos"
    """
    wait = WebDriverWait(driver, 25)

    # 1) Expandir "1. Encuestas sobre expectativas económicas"
    try:
        elem = driver.find_element(
            By.XPATH,
            "/html/body/app-root/div/div/div/div/app-estadistica-encuestas/div/div[3]/cdk-accordion/cdk-accordion-item[1]/div[1]"
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", elem)
        time.sleep(2)
        print("[OK] Sección principal expandida")
    except Exception:
        hacer_clic_por_texto(driver, wait, "Encuestas sobre expectativas económicas", "Sección principal")

    # 2) Expandir "1.1. EME"
    hacer_clic_por_texto(driver, wait, "1.1. Encuesta mensual de expectativas de analistas económicos", "EME")

    # 3) Expandir "Datos" (dentro de EME para evitar Documentos metodológicos)
    try:
        # Buscar Datos dentro del acordeón EME
        icono = driver.find_element(By.ID, f"span_icon_Datos_{EME_CATALOG_ID}")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icono)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", icono)
        time.sleep(2)
        print("[OK] Sección Datos expandida")
    except Exception:
        hacer_clic_por_texto(driver, wait, "Datos", "Datos")

    time.sleep(5)


def encontrar_enlace_serie_historica(driver):
    """Busca el enlace 'Serie histórica (disponible desde 2001)' dentro de la sección Datos de EME."""
    selectores = [
        f"//div[@id='div_tabla_Datos_{EME_CATALOG_ID}']//a[contains(@class, 'a-link-download-file') and contains(., 'Serie histórica') and contains(., '2001')]",
        f"//*[contains(@id, 'Datos_{EME_CATALOG_ID}')]//a[contains(@class, 'a-link-download-file') and contains(., 'Serie histórica')]",
        "//a[contains(@class, 'a-link-download-file') and contains(., 'Serie histórica') and contains(., '2001')]",
        "//a[contains(@class, 'a-link-download-file') and contains(., 'Serie histórica')]",
        "//a[contains(., 'Serie histórica') and contains(., '2001')]",
        "//a[contains(., 'Serie histórica')]",
    ]

    for selector in selectores:
        try:
            enlaces = driver.find_elements(By.XPATH, selector)
            for enlace in enlaces:
                try:
                    if enlace.is_displayed():
                        href = enlace.get_attribute("href")
                        if href and href not in ("", "#", "javascript:void(0)", "None", "null"):
                            print(f"[OK] Enlace encontrado: {href}")
                            return href
                        return enlace
                except Exception:
                    continue
        except Exception:
            continue

    # Fallback: todos los enlaces a-link-download-file y filtrar por texto
    try:
        enlaces = driver.find_elements(By.CSS_SELECTOR, "a.a-link-download-file")
        for enlace in enlaces:
            try:
                texto = enlace.text or ""
                if "Serie histórica" in texto and "2001" in texto:
                    if enlace.is_displayed():
                        href = enlace.get_attribute("href")
                        if href and href not in ("", "#", "javascript:void(0)"):
                            return href
                        return enlace
            except Exception:
                continue
    except Exception:
        pass

    return None


def descargar_excel():
    """Descarga el Excel de Rankings históricos EME."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    historicos_path = asegurar_historicos()
    historicos_path_abs = os.path.abspath(historicos_path)
    destino = os.path.join(historicos_path, DEST_FILENAME)

    driver = configurar_driver_descargas(download_dir=historicos_path_abs)

    try:
        print(f"[INFO] Navegando a: {BANREP_PAGE_URL}")
        driver.get(BANREP_PAGE_URL)
        time.sleep(5)

        expandir_eme_y_datos(driver)

        enlace_o_url = encontrar_enlace_serie_historica(driver)
        if not enlace_o_url:
            raise RuntimeError("No se encontró el enlace 'Serie histórica (disponible desde 2001)'")

        archivos_antes = set(os.listdir(historicos_path))
        ventanas_antes = len(driver.window_handles)

        # Hacer clic (abre nueva ventana con detalle-encuestas)
        enlace = enlace_o_url if not isinstance(enlace_o_url, str) else None
        if enlace:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", enlace)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", enlace)
        else:
            driver.get(enlace_o_url)

        time.sleep(4)

        # Si se abrió nueva ventana, buscar enlace de descarga ahí
        if len(driver.window_handles) > ventanas_antes:
            driver.switch_to.window(driver.window_handles[-1])
            nueva_url = driver.current_url
            print(f"[INFO] Nueva ventana: {nueva_url}")
            time.sleep(4)

            for tag in driver.find_elements(By.CSS_SELECTOR, "a.a-link-download-file"):
                href = tag.get_attribute("href")
                if href and ".xls" in href.lower():
                    if href.startswith("/"):
                        base = f"{urlparse(BANREP_PAGE_URL).scheme}://{urlparse(BANREP_PAGE_URL).netloc}"
                        href = urljoin(base, href)
                    elif not href.startswith("http"):
                        href = urljoin(nueva_url, href)
                    print(f"[INFO] Descargando desde: {href}")
                    if descargar_con_requests(href, destino):
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        print(f"[OK] Excel guardado: {destino}")
                        return destino

            for tag in driver.find_elements(By.XPATH, "//a[contains(@href, '.xls')]"):
                href = tag.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        base = f"{urlparse(nueva_url).scheme}://{urlparse(nueva_url).netloc}"
                        href = urljoin(base, href)
                    print(f"[INFO] Descargando desde: {href}")
                    if descargar_con_requests(href, destino):
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        print(f"[OK] Excel guardado: {destino}")
                        return destino

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        # Fallback: esperar descarga en folder
        for _ in range(45):
            time.sleep(1)
            archivos_ahora = set(os.listdir(historicos_path))
            excel_nuevos = [f for f in (archivos_ahora - archivos_antes) if f.lower().endswith((".xls", ".xlsx"))]
            if excel_nuevos:
                ultimo = max(
                    (os.path.join(historicos_path, f) for f in excel_nuevos),
                    key=os.path.getmtime
                )
                if os.path.abspath(ultimo) != os.path.abspath(destino):
                    if os.path.exists(destino):
                        os.remove(destino)
                    os.replace(ultimo, destino)
                print(f"[OK] Excel guardado: {destino}")
                return destino

        raise RuntimeError("No se pudo descargar el Excel")

    finally:
        if driver:
            driver.quit()


def main():
    script_name = "expectativas_eme_analistas_banrep"

    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("DESCARGA EME - SERIE HISTÓRICA (BanRep)")
            logger.info("=" * 80)

            historicos_path = asegurar_historicos()
            logger.info(f"Carpeta: {historicos_path}")

            destino = descargar_excel()
            logger.info(f"Excel guardado: {destino}")
            logger.info("PROCESO COMPLETADO EXITOSAMENTE")
            return destino

        except Exception as e:
            logger.log_exception(e, "main()")
            raise


if __name__ == "__main__":
    main()
