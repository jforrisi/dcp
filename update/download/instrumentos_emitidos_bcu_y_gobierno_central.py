"""
Script: instrumentos_emitidos_bcu_y_gobierno_central
-----------------------------------------------------
Descarga el Excel "Operaciones BCU y MEF local.xlsx" desde la página del BCU.
Hace scraping con Selenium: abre la página, localiza el enlace en la tabla
y hace clic para descargar.
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
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# URL de la página (tabla con enlaces a documentos)
BCU_PAGE_URL = (
    "https://www.bcu.gub.uy/Politica-Economica-y-Mercados/Paginas/"
    "Instrumentos-emitidos-por-el-BCU-y-el-Gobierno-Central.aspx"
)

# Texto/atributo que identifica la celda del Excel a descargar
EXCEL_CELL_DATA_ORDER = "Operaciones BCU y MEF local.xlsx"
EXCEL_FILENAME_PATTERN = "Operaciones BCU y MEF local"

# Carpeta y nombre de archivo destino
DATA_RAW_DIR = "update/historicos"
DEST_FILENAME = "instrumentos_emitidos_bcu_y_gobierno_central.xlsx"


def asegurar_data_raw():
    """Crea la carpeta de descargas si no existe y devuelve su ruta absoluta."""
    data_raw_path = root_dir / DATA_RAW_DIR
    data_raw_path.mkdir(parents=True, exist_ok=True)
    return str(data_raw_path)


def configurar_driver_descargas(download_dir: str):
    """Configura Chrome para descargas automáticas (headless en cloud)."""
    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    is_cloud = (
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY")
        or os.getenv("AZURE_ENVIRONMENT")
        or os.getenv("AZURE")
    )

    if is_cloud:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        chrome_bin = os.getenv("CHROME_BIN")
        if not chrome_bin:
            for path in [
                "/root/.nix-profile/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/usr/bin/google-chrome",
            ]:
                if os.path.exists(path):
                    chrome_bin = path
                    break
        if chrome_bin and os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
            print(f"[INFO] Usando Chrome/Chromium en: {chrome_bin}")

        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        if not chromedriver_path:
            for path in [
                "/root/.nix-profile/bin/chromedriver",
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver",
            ]:
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


def limpiar_archivos_anteriores(data_raw_path: str):
    """Elimina archivos anteriores del mismo Excel si existen."""
    destino = os.path.join(data_raw_path, DEST_FILENAME)
    if os.path.exists(destino):
        for _ in range(3):
            try:
                os.remove(destino)
                print(f"[INFO] Archivo anterior '{DEST_FILENAME}' eliminado")
                break
            except PermissionError:
                time.sleep(2)
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{DEST_FILENAME}': {e}")
                break

    for name in os.listdir(data_raw_path):
        name_lower = name.lower()
        if (
            name_lower.startswith("instrumentos_emitidos")
            or "operaciones bcu" in name_lower
        ) and name_lower.endswith((".xls", ".xlsx")):
            p = os.path.join(data_raw_path, name)
            try:
                os.remove(p)
                print(f"[INFO] Archivo anterior '{name}' eliminado")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{name}': {e}")


def descargar_excel_bcu():
    """
    Abre la página del BCU, localiza la celda/enlace "Operaciones BCU y MEF local.xlsx"
    y hace clic para descargar. Renombra el archivo al nombre destino.
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas: {data_raw_path}")

    limpiar_archivos_anteriores(data_raw_path)

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Abriendo página: {BCU_PAGE_URL}")
        driver.get(BCU_PAGE_URL)
        time.sleep(3)

        wait = WebDriverWait(driver, 20)

        # Localizar la celda <td data-order="Operaciones BCU y MEF local.xlsx" class="gtm">
        # y el enlace <a> dentro para hacer clic y descargar
        td = None
        link = None

        try:
            td = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//td[@data-order='{EXCEL_CELL_DATA_ORDER}']")
                )
            )
        except Exception:
            try:
                td = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            f"//td[contains(@data-order, '{EXCEL_FILENAME_PATTERN}')]",
                        )
                    )
                )
            except Exception:
                pass

        if td:
            try:
                link = td.find_element(By.TAG_NAME, "a")
            except Exception:
                link = None
        else:
            # Fallback: buscar enlace por texto visible
            try:
                link = wait.until(
                    EC.element_to_be_clickable(
                        (By.PARTIAL_LINK_TEXT, EXCEL_FILENAME_PATTERN)
                    )
                )
            except Exception:
                link = None

        archivos_antes = set(os.listdir(data_raw_path))

        if link and link.get_attribute("href"):
            driver.execute_script("arguments[0].scrollIntoView(true);", link)
            time.sleep(0.5)
            print("[INFO] Enlace encontrado, haciendo clic para descargar...")
            link.click()
        elif td:
            driver.execute_script("arguments[0].scrollIntoView(true);", td)
            time.sleep(0.5)
            print("[INFO] Celda encontrada, haciendo clic...")
            td.click()
        else:
            raise RuntimeError(
                "No se encontró la celda ni el enlace 'Operaciones BCU y MEF local.xlsx' en la página."
            )

        # Esperar a que aparezca el archivo en la carpeta
        print("[INFO] Esperando a que termine la descarga...")
        tiempo_max = 45
        inicio = time.time()
        archivo_descargado = None
        while time.time() - inicio < tiempo_max:
            time.sleep(1)
            archivos_ahora = set(os.listdir(data_raw_path))
            nuevos = archivos_ahora - archivos_antes
            completos = [
                f
                for f in nuevos
                if f.lower().endswith((".xlsx", ".xls"))
                and not f.endswith(".crdownload")
                and not f.endswith(".tmp")
            ]
            if completos:
                archivo_descargado = completos[0]
                break

        if not archivo_descargado:
            raise RuntimeError(
                f"Timeout: no se detectó archivo Excel descargado en {tiempo_max}s"
            )

        # Esperar a que el archivo deje de escribirse (crdownload)
        time.sleep(2)
        path_descargado = os.path.join(data_raw_path, archivo_descargado)
        destino = os.path.join(data_raw_path, DEST_FILENAME)

        if os.path.abspath(path_descargado) != os.path.abspath(destino):
            if os.path.exists(destino):
                try:
                    os.remove(destino)
                except Exception as e:
                    print(f"[WARN] No se pudo eliminar destino existente: {e}")
            try:
                os.replace(path_descargado, destino)
                print(f"[INFO] Archivo renombrado a '{DEST_FILENAME}'")
            except Exception as e:
                print(f"[WARN] No se pudo renombrar: {e}. Usando: {archivo_descargado}")
                destino = path_descargado
        else:
            print(f"[INFO] Archivo ya tiene el nombre correcto: '{DEST_FILENAME}'")

        print(f"[OK] Excel guardado como: {destino}")
        return destino

    finally:
        driver.quit()


if __name__ == "__main__":
    descargar_excel_bcu()
