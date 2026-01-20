"""
Script: carne_exportacion
--------------------------
Usa Selenium + Chrome para descargar el Excel de ingreso medio de exportación de INAC
y guardarlo dentro de la carpeta `data_raw/` con el nombre estándar `serie_semanal_ingreso_medio_exportacion_inac.xlsx`,
según el flujo definido en 0_README.
"""

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# URL de la página donde está el enlace al Excel de ingreso medio de exportación
INAC_CARNE_EXPORTACION_URL = "https://www.inac.uy/innovaportal/v/9799/10/innova.front/serie-semanal-ingreso-medio-de-exportacion---bovino-ovino-y-otros-productos"

# Carpeta y nombre de archivo destino dentro del proyecto
DATA_RAW_DIR = "data_raw"
DEST_FILENAME = "serie_semanal_ingreso_medio_exportacion_inac.xlsx"


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
    Elimina archivos anteriores relacionados (evolucion-semanal-de-exportacion.xlsx,
    evolucion-semanal-de-exportacion (1).xlsx, etc.) y el archivo destino si existe.
    """
    destino = os.path.join(data_raw_path, DEST_FILENAME)
    
    # Eliminar el archivo destino si ya existe
    if os.path.exists(destino):
        os.remove(destino)
        print(f"[INFO] Archivo anterior '{DEST_FILENAME}' eliminado")
    
    # Eliminar archivos que empiecen con "evolucion-semanal" (con o sin (1), (2), etc.)
    for archivo in os.listdir(data_raw_path):
        if archivo.lower().startswith("evolucion-semanal") and archivo.lower().endswith((".xls", ".xlsx")):
            archivo_path = os.path.join(data_raw_path, archivo)
            try:
                os.remove(archivo_path)
                print(f"[INFO] Archivo anterior '{archivo}' eliminado")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{archivo}': {e}")


def descargar_excel_inac():
    """
    Abre la página de ingreso medio de exportación de INAC con Selenium,
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
        print(f"[INFO] Abriendo pagina de INAC: {INAC_CARNE_EXPORTACION_URL}")
        driver.get(INAC_CARNE_EXPORTACION_URL)

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
        # Esperamos activamente hasta que aparezca un archivo nuevo.
        import time

        print("[INFO] Esperando a que termine la descarga...")
        tiempo_inicio = time.time()
        tiempo_max_espera = 30  # segundos máximo
        
        # Obtener lista de archivos antes de la descarga
        archivos_antes = set(os.listdir(data_raw_path))
        
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
                raise RuntimeError(f"Timeout: No se detecto ningun archivo Excel descargado en {tiempo_max_espera} segundos")

        # Buscar el archivo más reciente que sea Excel (puede ser evolucion-semanal-de-exportacion.xlsx o con (1), (2), etc.)
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
        nombre_ultimo = os.path.basename(ultimo)

        destino = os.path.join(data_raw_path, DEST_FILENAME)
        
        # Si el archivo más reciente no es el destino, renombrarlo
        if os.path.abspath(ultimo) != os.path.abspath(destino):
            # Si el destino ya existe (por alguna razón), eliminarlo primero
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


if __name__ == "__main__":
    descargar_excel_inac()
