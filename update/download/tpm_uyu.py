"""
Script: tpm_uyu (Tasa de Política Monetaria - Uruguay)
------------------------------------------------------
Descarga el Excel de "Tasa 1 Día" del BCU desde:
https://www.bcu.gub.uy/Politica-Economica-y-Mercados/Paginas/Tasa-1-Dia.aspx

Hace clic en el botón "Descargar Excel" y guarda el archivo como
update/historicos/tpm_uyu.xlsx
"""

import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Directorio raíz del proyecto
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

URL_PAGINA = "https://www.bcu.gub.uy/Politica-Economica-y-Mercados/Paginas/Tasa-1-Dia.aspx"
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "tpm_uyu.xlsx"


def asegurar_historicos():
    """Crea la carpeta update/historicos si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    historicos_path = os.path.join(base_dir, HISTORICOS_DIR)
    os.makedirs(historicos_path, exist_ok=True)
    return os.path.abspath(historicos_path)


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

    # Reducir carga y evitar timeouts/crashes (GCM, red, etc.)
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--disable-client-side-phishing-detection")

    # Estrategia: no esperar todos los recursos, solo DOM (carga más rápido)
    chrome_options.page_load_strategy = "eager"

    is_railway = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY") or os.getenv("AZURE_ENVIRONMENT") or os.getenv("AZURE")

    if is_railway:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        chrome_bin = os.getenv("CHROME_BIN")
        if not chrome_bin:
            possible_paths = [
                "/root/.nix-profile/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/usr/bin/google-chrome",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    chrome_bin = path
                    break

        if chrome_bin and os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
            print(f"[INFO] Usando Chrome/Chromium en: {chrome_bin}")

        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        if not chromedriver_path:
            possible_paths = [
                "/root/.nix-profile/bin/chromedriver",
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver",
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
    else:
        driver = webdriver.Chrome(options=chrome_options)

    return driver


def descargar_tpm_uyu():
    """
    Navega a la página Tasa 1 Día del BCU, hace clic en el botón Excel
    y guarda el archivo como update/historicos/tpm_uyu.xlsx
    """
    historicos_path = asegurar_historicos()
    destino = os.path.join(historicos_path, DEST_FILENAME)
    print(f"[INFO] Destino: {destino}")

    driver = configurar_driver_descargas(download_dir=historicos_path)

    # Timeout: 90 segundos máximo (falla rápido si la página no responde)
    driver.set_page_load_timeout(90)

    try:
        print(f"[INFO] Navegando a: {URL_PAGINA}")
        driver.get(URL_PAGINA)

        # Esperar a que cargue la tabla y el botón Excel (DataTables)
        # Selectores: buttons-excel, img con title Descargar Excel
        wait = WebDriverWait(driver, 30)
        try:
            boton_excel = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.buttons-excel, button.buttons-html5")
                )
            )
        except Exception:
            boton_excel = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class, 'buttons-excel') or .//img[contains(@title, 'Excel')]]")
                )
            )
        print("[INFO] Botón Excel encontrado, haciendo clic...")

        archivos_antes = set(os.listdir(historicos_path))
        boton_excel.click()

        # Esperar a que aparezca el archivo descargado
        print("[INFO] Esperando descarga...")
        tiempo_inicio = time.time()
        tiempo_max_espera = 45

        while True:
            time.sleep(1)
            archivos_ahora = set(os.listdir(historicos_path))
            archivos_nuevos = archivos_ahora - archivos_antes
            excel_nuevos = [f for f in archivos_nuevos if f.lower().endswith((".xls", ".xlsx"))]

            if excel_nuevos:
                # Asegurar que el archivo terminó de escribirse (no .crdownload)
                candidatos = [
                    f for f in excel_nuevos
                    if not f.endswith(".crdownload") and not f.endswith(".tmp")
                ]
                if candidatos:
                    print(f"[INFO] Archivo descargado: {candidatos[0]}")
                    break

            if time.time() - tiempo_inicio > tiempo_max_espera:
                raise RuntimeError(
                    f"Timeout: No se detectó archivo Excel en {tiempo_max_espera} segundos"
                )

        # Buscar el Excel más reciente
        candidatos = [
            os.path.join(historicos_path, f)
            for f in os.listdir(historicos_path)
            if f.lower().endswith((".xls", ".xlsx"))
            and not f.endswith(".crdownload")
        ]
        if not candidatos:
            raise RuntimeError("No se encontró ningún Excel descargado")

        ultimo = max(candidatos, key=os.path.getmtime)
        nombre_ultimo = os.path.basename(ultimo)

        if os.path.abspath(ultimo) != os.path.abspath(destino):
            if os.path.exists(destino):
                try:
                    os.remove(destino)
                except PermissionError:
                    print(f"[WARN] No se pudo eliminar destino existente")
            try:
                os.replace(ultimo, destino)
                print(f"[INFO] Archivo renombrado a {DEST_FILENAME}")
            except PermissionError:
                print(f"[WARN] Archivo en uso. Usando: {nombre_ultimo}")
                destino = ultimo

        print(f"[OK] Excel guardado: {destino}")
        return destino

    finally:
        driver.quit()


def main():
    """Función principal."""
    print("=" * 60)
    print("DESCARGA TASA 1 DÍA (TPM) - BCU Uruguay")
    print("=" * 60)
    descargar_tpm_uyu()
    print("[OK] Proceso completado")


if __name__ == "__main__":
    main()
