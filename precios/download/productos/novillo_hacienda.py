"""
Script: novillo_hacienda
-------------------------
Usa Selenium + Chrome para descargar el Excel de precios de hacienda de INAC
y guardarlo dentro de la carpeta `data_raw/` con el nombre estándar `precios_hacienda_inac.xlsx`,
según el flujo definido en 0_README.
"""

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
    """
    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # Deja visible el navegador para debugging; si se quiere headless se puede agregar:
    # chrome_options.add_argument("--headless=new")
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
    Abre la página de precios de hacienda de INAC con Selenium,
    hace clic en el enlace de descarga del Excel y lo guarda en data_raw.

    NOTA: Dependiendo de cómo esté construida la página, puede ser necesario
    ajustar el localizador (By.LINK_TEXT, By.PARTIAL_LINK_TEXT, XPATH, etc.).
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    # Limpiar archivos anteriores antes de descargar
    limpiar_archivos_anteriores(data_raw_path)

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Abriendo pagina de INAC: {INAC_PRECIOS_HACIENDA_URL}")
        driver.get(INAC_PRECIOS_HACIENDA_URL)

        wait = WebDriverWait(driver, 30)

        # Ejemplo de localización: enlace que contiene la palabra "Excel" o similar.
        # Es probable que esto haya que ajustarlo mirando el HTML real.
        link = wait.until(
            EC.element_to_be_clickable(
                (By.PARTIAL_LINK_TEXT, "Excel")
            )
        )

        print("[INFO] Haciendo clic en el enlace de descarga del Excel...")
        link.click()

        # Esperar a que el archivo aparezca en la carpeta de descargas.
        # Se puede mejorar con una espera activa que revise el directorio.
        import time

        print("[INFO] Esperando a que termine la descarga...")
        time.sleep(10)

        # Renombrar/mover el archivo descargado al nombre estándar si es necesario.
        # Aquí asumimos que es el archivo más reciente en data_raw con extensión .xls o .xlsx.
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

        destino = os.path.join(data_raw_path, DEST_FILENAME)
        if os.path.abspath(ultimo) != os.path.abspath(destino):
            os.replace(ultimo, destino)

        print(f"[OK] Excel guardado como: {destino}")
        return destino

    finally:
        driver.quit()


if __name__ == "__main__":
    descargar_excel_inac()

